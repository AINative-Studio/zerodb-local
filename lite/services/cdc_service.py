"""
Change Data Capture (CDC) Service - Application-Level

Replaces PL/pgSQL trigger-based CDC from the PostgreSQL schema.
Since SQLite does not support server-side triggers with the same
row_to_json / TG_OP semantics, CDC is handled at the application
layer by explicitly logging changes after each write operation.

Refs #1706
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text


class CDCService:
    """
    Application-level change data capture for SQLite.

    Records INSERT, UPDATE, and DELETE operations into the change_log table,
    mirroring the behavior of the PostgreSQL CDC triggers defined in
    migrations 001 and 003.
    """

    def __init__(self, db_service):
        """
        Args:
            db_service: DatabaseServiceLite instance that owns the engine.
        """
        self._db_service = db_service

    @property
    def engine(self):
        return self._db_service.engine

    def log_change(
        self,
        conn,
        project_id: str,
        entity_type: str,
        entity_id: str,
        operation: str,
        data: Any = None,
    ) -> str:
        """
        Record a change in the change_log table.

        This is called within an existing connection/transaction context,
        so it does NOT commit -- the caller is responsible for committing.

        Args:
            conn: Active SQLAlchemy connection (within a transaction).
            project_id: The owning project UUID.
            entity_type: One of 'vector', 'table_row', 'memory', 'event', 'file'.
            entity_id: The UUID of the changed entity.
            operation: One of 'INSERT', 'UPDATE', 'DELETE'.
            data: The entity data at the time of the change (dict or JSON string).

        Returns:
            The UUID of the new change_log entry.
        """
        change_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if data is not None and not isinstance(data, str):
            data = json.dumps(data, default=str)

        conn.execute(
            text(
                """
                INSERT INTO change_log (id, project_id, entity_type, entity_id,
                                        operation, data, timestamp, synced)
                VALUES (:id, :project_id, :entity_type, :entity_id,
                        :operation, :data, :timestamp, 0)
                """
            ),
            {
                "id": change_id,
                "project_id": project_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "operation": operation,
                "data": data,
                "timestamp": now,
            },
        )

        return change_id

    def get_unsynced_changes(
        self,
        project_id: str,
        entity_type: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve unsynced change_log entries for a project.

        Args:
            project_id: Filter by project.
            entity_type: Optionally filter by entity type.
            limit: Max number of entries to return.

        Returns:
            List of change_log dicts ordered by timestamp ascending.
        """
        query = """
            SELECT * FROM change_log
            WHERE project_id = :project_id AND synced = 0
        """
        params: Dict[str, Any] = {"project_id": project_id}

        if entity_type:
            query += " AND entity_type = :entity_type"
            params["entity_type"] = entity_type

        query += " ORDER BY timestamp ASC LIMIT :limit"
        params["limit"] = limit

        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            rows = result.mappings().fetchall()

        return [self._row_to_change(r) for r in rows]

    def mark_synced(self, change_ids: List[str]) -> int:
        """
        Mark change_log entries as synced.

        Args:
            change_ids: List of change_log UUIDs to mark.

        Returns:
            Number of rows updated.
        """
        if not change_ids:
            return 0

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # SQLite does not support array parameters, so use IN with placeholders
        placeholders = ", ".join(f":id_{i}" for i in range(len(change_ids)))
        params = {f"id_{i}": cid for i, cid in enumerate(change_ids)}
        params["synced_at"] = now

        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    f"""
                    UPDATE change_log
                    SET synced = 1, synced_at = :synced_at
                    WHERE id IN ({placeholders})
                    """
                ),
                params,
            )
            conn.commit()

        return result.rowcount

    def get_change_count(
        self,
        project_id: str,
        synced: Optional[bool] = None,
    ) -> int:
        """
        Count change_log entries for a project.

        Args:
            project_id: Filter by project.
            synced: If set, filter by synced status.

        Returns:
            Count of matching entries.
        """
        query = "SELECT COUNT(*) FROM change_log WHERE project_id = :project_id"
        params: Dict[str, Any] = {"project_id": project_id}

        if synced is not None:
            query += " AND synced = :synced"
            params["synced"] = 1 if synced else 0

        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            return result.scalar() or 0

    def purge_synced(self, project_id: str, older_than_days: int = 30) -> int:
        """
        Delete synced change_log entries older than a threshold.

        Args:
            project_id: Filter by project.
            older_than_days: Delete entries older than this many days.

        Returns:
            Number of rows deleted.
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    DELETE FROM change_log
                    WHERE project_id = :project_id
                      AND synced = 1
                      AND timestamp < datetime('now', :age_modifier)
                    """
                ),
                {
                    "project_id": project_id,
                    "age_modifier": f"-{older_than_days} days",
                },
            )
            conn.commit()

        return result.rowcount

    @staticmethod
    def _row_to_change(row) -> Dict[str, Any]:
        """Convert a database row to a change_log dict."""
        data = row["data"]
        if data and isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "operation": row["operation"],
            "data": data,
            "timestamp": row["timestamp"],
            "synced": bool(row["synced"]),
        }
