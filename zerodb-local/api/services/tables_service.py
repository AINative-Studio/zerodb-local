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

        # Create table
        insert_query = text("""
            INSERT INTO tables (project_id, name, schema, description)
            VALUES (:project_id, :name, :schema::jsonb, :description)
            RETURNING id, name, schema, description, created_at, updated_at
        """)

        result = db.execute(
            insert_query,
            {
                "project_id": str(project_id),
                "name": table_name,
                "schema": json.dumps(schema),
                "description": description
            }
        ).first()

        db.commit()

        # Invalidate any negative cache entry for this table
        key = _cache_key(project_id, table_name)
        _TABLE_CACHE.pop(key, None)
        _TABLE_CACHE_TS.pop(key, None)

        return {
            "id": str(result.id),
            "name": result.name,
            "schema": result.schema,
            "description": result.description,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "updated_at": result.updated_at.isoformat() if result.updated_at else None
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
                "schema": row.schema,
                "description": row.description,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None
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
            "schema": result.schema,
            "description": result.description,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "updated_at": result.updated_at.isoformat() if result.updated_at else None
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
        delete_query = text("""
            UPDATE tables
            SET deleted_at = NOW()
            WHERE project_id = :project_id
            AND name = :table_name
            AND deleted_at IS NULL
            RETURNING id
        """)

        result = db.execute(
            delete_query,
            {"project_id": str(project_id), "table_name": table_name}
        ).first()

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

        # Insert rows
        inserted_ids = []
        for row_data in rows:
            insert_query = text("""
                INSERT INTO table_rows (table_id, project_id, data)
                VALUES (:table_id, :project_id, :data::jsonb)
                RETURNING id
            """)

            result = db.execute(
                insert_query,
                {
                    "table_id": table_id,
                    "project_id": str(project_id),
                    "data": json.dumps(row_data)
                }
            ).first()

            inserted_ids.append(str(result.id))

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

        # Build query with optional filter
        if filter_data:
            # Use JSONB containment operator @>
            query = text("""
                SELECT id, data, created_at, updated_at
                FROM table_rows
                WHERE table_id = :table_id
                AND project_id = :project_id
                AND deleted_at IS NULL
                AND data @> :filter::jsonb
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            params = {
                "table_id": table_id,
                "project_id": str(project_id),
                "filter": json.dumps(filter_data),
                "limit": limit,
                "offset": skip
            }
        else:
            query = text("""
                SELECT id, data, created_at, updated_at
                FROM table_rows
                WHERE table_id = :table_id
                AND project_id = :project_id
                AND deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            params = {
                "table_id": table_id,
                "project_id": str(project_id),
                "limit": limit,
                "offset": skip
            }

        results = db.execute(query, params).fetchall()

        return [
            {
                "id": str(row.id),
                "data": row.data,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None
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

        # Update rows using JSONB concatenation operator ||
        update_query = text("""
            UPDATE table_rows
            SET data = data || :update::jsonb,
                updated_at = NOW()
            WHERE table_id = :table_id
            AND project_id = :project_id
            AND deleted_at IS NULL
            AND data @> :filter::jsonb
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

        # Soft delete rows
        delete_query = text("""
            UPDATE table_rows
            SET deleted_at = NOW()
            WHERE table_id = :table_id
            AND project_id = :project_id
            AND deleted_at IS NULL
            AND data @> :filter::jsonb
        """)

        result = db.execute(
            delete_query,
            {
                "table_id": table_id,
                "project_id": str(project_id),
                "filter": json.dumps(filter_data)
            }
        )

        db.commit()
        return result.rowcount


# Global instance
tables_service = TablesService()
