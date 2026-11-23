"""
Tables Service
Handles NoSQL table operations using PostgreSQL JSONB

Issue #1092: Added TTL-based table metadata cache to eliminate
redundant DB lookups on every query/update/delete request.
"""
import json
import os
import time
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

from lite.config import is_lite_mode
from lite.sql_compat import (
    equality_filter_clause,
    jsonb_cast_sql,
    log_cdc_change,
    merge_json_text,
    new_id,
    now_iso,
    now_sql,
    parse_json_column,
    to_isoformat,
)

# TTL cache for table metadata (project_id:table_name → metadata dict)
_TABLE_CACHE: Dict[str, Dict[str, Any]] = {}
_TABLE_CACHE_TTL = int(os.getenv("ZERODB_TABLE_CACHE_TTL", "300"))  # 5 min default
_TABLE_CACHE_TS: Dict[str, float] = {}  # timestamps


def _cache_key(project_id: UUID, table_name: str) -> str:
    return f"{project_id}:{table_name}"


class TablesService:
    """
    Service for NoSQL table operations

    Architecture:
    - PostgreSQL JSONB: Stores dynamic schema-less data
    - GIN indexes: Fast queries on JSONB fields
    """

    async def create_table(
        self,
        db: Session,
        project_id: UUID,
        table_name: str,
        schema: Dict[str, Any],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new NoSQL table

        Args:
            db: Database session
            project_id: Project UUID
            table_name: Table name (unique per project)
            schema: JSON schema definition
            description: Optional description

        Returns:
            Created table info
        """
        # Check if table already exists
        check_query = text("""
            SELECT id FROM tables
            WHERE project_id = :project_id
            AND name = :table_name
            AND deleted_at IS NULL
        """)

        existing = db.execute(
            check_query,
            {"project_id": str(project_id), "table_name": table_name}
        ).first()

        if existing:
            raise ValueError(f"Table '{table_name}' already exists")

        # Create table. In lite mode the `id` column has no SQL-level
        # default (unlike Postgres's DEFAULT gen_random_uuid()), so an id
        # must be generated and bound explicitly or SQLite silently stores
        # NULL for it.
        lite = is_lite_mode()
        columns = "project_id, name, schema, description"
        values = f":project_id, :name, {jsonb_cast_sql(':schema', lite)}, :description"
        params = {
            "project_id": str(project_id),
            "name": table_name,
            "schema": json.dumps(schema),
            "description": description
        }
        if lite:
            columns = "id, " + columns
            values = ":id, " + values
            params["id"] = new_id()

        insert_query = text(f"""
            INSERT INTO tables ({columns})
            VALUES ({values})
            RETURNING id, name, schema, description, created_at, updated_at
        """)

        result = db.execute(insert_query, params).first()

        db.commit()

        # Invalidate any negative cache entry for this table
        key = _cache_key(project_id, table_name)
        _TABLE_CACHE.pop(key, None)
        _TABLE_CACHE_TS.pop(key, None)

        return {
            "id": str(result.id),
            "name": result.name,
            "schema": parse_json_column(result.schema),
            "description": result.description,
            "created_at": to_isoformat(result.created_at),
            "updated_at": to_isoformat(result.updated_at)
        }

    async def list_tables(
        self,
        db: Session,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all tables

        Args:
            db: Database session
            project_id: Project UUID
            skip: Number to skip (pagination)
            limit: Max results

        Returns:
            List of tables
        """
        query = text("""
            SELECT id, name, schema, description, created_at, updated_at
            FROM tables
            WHERE project_id = :project_id
            AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        results = db.execute(
            query,
            {"project_id": str(project_id), "limit": limit, "offset": skip}
        ).fetchall()

        return [
            {
                "id": str(row.id),
                "name": row.name,
                "schema": parse_json_column(row.schema),
                "description": row.description,
                "created_at": to_isoformat(row.created_at),
                "updated_at": to_isoformat(row.updated_at)
            }
            for row in results
        ]

    async def get_table(
        self,
        db: Session,
        project_id: UUID,
        table_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get table by name (with TTL cache).

        Issue #1092: Caches table metadata to avoid a DB round-trip on
        every query/update/delete request.

        Args:
            db: Database session
            project_id: Project UUID
            table_name: Table name

        Returns:
            Table info or None
        """
        key = _cache_key(project_id, table_name)
        now = time.time()

        # Return cached entry if still valid
        if key in _TABLE_CACHE and (now - _TABLE_CACHE_TS.get(key, 0)) < _TABLE_CACHE_TTL:
            return _TABLE_CACHE[key]

        query = text("""
            SELECT id, name, schema, description, created_at, updated_at
            FROM tables
            WHERE project_id = :project_id
            AND name = :table_name
            AND deleted_at IS NULL
        """)

        result = db.execute(
            query,
            {"project_id": str(project_id), "table_name": table_name}
        ).first()

        if not result:
            # Cache negative result for a shorter period (30s)
            _TABLE_CACHE[key] = None
            _TABLE_CACHE_TS[key] = now - _TABLE_CACHE_TTL + 30
            return None

        table_info = {
            "id": str(result.id),
            "name": result.name,
            "schema": parse_json_column(result.schema),
            "description": result.description,
            "created_at": to_isoformat(result.created_at),
            "updated_at": to_isoformat(result.updated_at)
        }

        _TABLE_CACHE[key] = table_info
        _TABLE_CACHE_TS[key] = now
        return table_info

    async def delete_table(
        self,
        db: Session,
        project_id: UUID,
        table_name: str
    ) -> bool:
        """
        Delete a table (soft delete, cascade deletes rows)

        Args:
            db: Database session
            project_id: Project UUID
            table_name: Table name

        Returns:
            True if deleted, False if not found
        """
        delete_query = text(f"""
            UPDATE tables
            SET deleted_at = {now_sql()}
            WHERE project_id = :project_id
            AND name = :table_name
            AND deleted_at IS NULL
            RETURNING id
        """)

        params = {"project_id": str(project_id), "table_name": table_name}
        if is_lite_mode():
            params["now"] = now_iso()

        result = db.execute(delete_query, params).first()

        if not result:
            return False

        # Invalidate cache on delete
        key = _cache_key(project_id, table_name)
        _TABLE_CACHE.pop(key, None)
        _TABLE_CACHE_TS.pop(key, None)

        db.commit()
        return True

    async def insert_rows(
        self,
        db: Session,
        project_id: UUID,
        table_name: str,
        rows: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Insert rows into table

        Args:
            db: Database session
            project_id: Project UUID
            table_name: Table name
            rows: List of row data dicts

        Returns:
            Insert results with IDs
        """
        # Get table ID
        table_info = await self.get_table(db, project_id, table_name)
        if not table_info:
            raise ValueError(f"Table '{table_name}' not found")

        table_id = table_info["id"]

        # Insert rows. In lite mode `id` has no SQL-level default (see
        # create_table's comment above), so generate it explicitly.
        lite = is_lite_mode()
        inserted_ids = []
        for row_data in rows:
            columns = "table_id, project_id, data"
            values = f":table_id, :project_id, {jsonb_cast_sql(':data', lite)}"
            params = {
                "table_id": table_id,
                "project_id": str(project_id),
                "data": json.dumps(row_data)
            }
            if lite:
                columns = "id, " + columns
                values = ":id, " + values
                params["id"] = new_id()

            insert_query = text(f"""
                INSERT INTO table_rows ({columns})
                VALUES ({values})
                RETURNING id
            """)

            result = db.execute(insert_query, params).first()

            inserted_ids.append(str(result.id))

            # Application-level CDC (Refs #63): full mode gets this for free
            # from the table_rows INSERT trigger; lite mode has no trigger
            # support, so log the same change_log row explicitly here.
            if lite:
                log_cdc_change(
                    db, project_id, "table_row", result.id, "INSERT", row_data
                )

        db.commit()

        return {
            "table_name": table_name,
            "inserted_count": len(inserted_ids),
            "inserted_ids": inserted_ids
        }

    async def query_rows(
        self,
        db: Session,
        project_id: UUID,
        table_name: str,
        filter_data: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query rows from table

        Args:
            db: Database session
            project_id: Project UUID
            table_name: Table name
            filter_data: Optional JSONB filter
            skip: Number to skip (pagination)
            limit: Max results

        Returns:
            List of rows
        """
        # Get table ID
        table_info = await self.get_table(db, project_id, table_name)
        if not table_info:
            raise ValueError(f"Table '{table_name}' not found")

        table_id = table_info["id"]

        # Build query with optional equality filter on the JSON `data` column
        # (replaces PostgreSQL's @> containment operator, which SQLite lacks)
        filter_clause, filter_params = equality_filter_clause(filter_data)

        query = text(f"""
            SELECT id, data, created_at, updated_at
            FROM table_rows
            WHERE table_id = :table_id
            AND project_id = :project_id
            AND deleted_at IS NULL
            {filter_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        params = {
            "table_id": table_id,
            "project_id": str(project_id),
            "limit": limit,
            "offset": skip,
            **filter_params
        }

        results = db.execute(query, params).fetchall()

        return [
            {
                "id": str(row.id),
                "data": parse_json_column(row.data),
                "created_at": to_isoformat(row.created_at),
                "updated_at": to_isoformat(row.updated_at)
            }
            for row in results
        ]

    async def update_rows(
        self,
        db: Session,
        project_id: UUID,
        table_name: str,
        filter_data: Dict[str, Any],
        update_data: Dict[str, Any]
    ) -> int:
        """
        Update rows in table

        Args:
            db: Database session
            project_id: Project UUID
            table_name: Table name
            filter_data: JSONB filter to match rows
            update_data: Data to update (merged with existing data)

        Returns:
            Number of rows updated
        """
        # Get table ID
        table_info = await self.get_table(db, project_id, table_name)
        if not table_info:
            raise ValueError(f"Table '{table_name}' not found")

        table_id = table_info["id"]

        if not is_lite_mode():
            # Update rows using JSONB concatenation operator ||
            update_query = text("""
                UPDATE table_rows
                SET data = data || CAST(:update AS jsonb),
                    updated_at = NOW()
                WHERE table_id = :table_id
                AND project_id = :project_id
                AND deleted_at IS NULL
                AND data @> CAST(:filter AS jsonb)
            """)

            result = db.execute(
                update_query,
                {
                    "table_id": table_id,
                    "project_id": str(project_id),
                    "filter": json.dumps(filter_data),
                    "update": json.dumps(update_data)
                }
            )

            db.commit()
            return result.rowcount

        # SQLite has no || jsonb concatenation operator and no @> containment
        # operator: select matching rows, merge each row's JSON with
        # update_data in Python, and write the merged JSON back individually.
        filter_clause, filter_params = equality_filter_clause(filter_data)
        select_query = text(f"""
            SELECT id, data FROM table_rows
            WHERE table_id = :table_id
            AND project_id = :project_id
            AND deleted_at IS NULL
            {filter_clause}
        """)
        matching_rows = db.execute(
            select_query,
            {"table_id": table_id, "project_id": str(project_id), **filter_params}
        ).fetchall()

        now = now_iso()
        updated_count = 0
        for row in matching_rows:
            merged_data = merge_json_text(row.data, update_data)
            db.execute(
                text("""
                    UPDATE table_rows
                    SET data = :data, updated_at = :now
                    WHERE id = :id
                """),
                {"id": row.id, "data": merged_data, "now": now}
            )

            # Application-level CDC (Refs #63): this whole branch only runs
            # in lite mode (see early `if not is_lite_mode(): ... return`
            # above), so no is_lite_mode() guard is needed here.
            log_cdc_change(
                db, project_id, "table_row", row.id, "UPDATE",
                parse_json_column(merged_data)
            )
            updated_count += 1

        db.commit()
        return updated_count

    async def delete_rows(
        self,
        db: Session,
        project_id: UUID,
        table_name: str,
        filter_data: Dict[str, Any]
    ) -> int:
        """
        Delete rows from table (soft delete)

        Args:
            db: Database session
            project_id: Project UUID
            table_name: Table name
            filter_data: JSONB filter to match rows

        Returns:
            Number of rows deleted
        """
        # Get table ID
        table_info = await self.get_table(db, project_id, table_name)
        if not table_info:
            raise ValueError(f"Table '{table_name}' not found")

        table_id = table_info["id"]

        # Soft delete rows matching the equality filter (replaces
        # PostgreSQL's @> containment operator, which SQLite lacks)
        filter_clause, filter_params = equality_filter_clause(filter_data)

        lite = is_lite_mode()
        deleted_rows = []
        if lite:
            # Soft-delete is a SQL UPDATE, not a DELETE, in both modes (see
            # below) -- in full mode that fires the table_rows trigger with
            # TG_OP = 'UPDATE', so change_log records operation 'UPDATE', not
            # 'DELETE'. Select the matching rows first so lite mode can log
            # the same per-row change_log entries (Refs #63) with matching
            # ids/data, mirroring what the trigger would have recorded.
            select_query = text(f"""
                SELECT id, data FROM table_rows
                WHERE table_id = :table_id
                AND project_id = :project_id
                AND deleted_at IS NULL
                {filter_clause}
            """)
            deleted_rows = db.execute(
                select_query,
                {"table_id": table_id, "project_id": str(project_id), **filter_params}
            ).fetchall()

        delete_query = text(f"""
            UPDATE table_rows
            SET deleted_at = {now_sql()}
            WHERE table_id = :table_id
            AND project_id = :project_id
            AND deleted_at IS NULL
            {filter_clause}
        """)

        params = {
            "table_id": table_id,
            "project_id": str(project_id),
            **filter_params
        }
        if lite:
            params["now"] = now_iso()

        result = db.execute(delete_query, params)

        if lite:
            for row in deleted_rows:
                log_cdc_change(
                    db, project_id, "table_row", row.id, "UPDATE",
                    parse_json_column(row.data)
                )

        db.commit()
        return result.rowcount


# Global instance
tables_service = TablesService()
