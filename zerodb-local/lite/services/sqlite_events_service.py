"""
SQLite Event Queue Service
Lightweight event queue backed by SQLite, replacing RedPanda/Kafka dependency
for the zerodb-local lite backend. Uses WAL mode for concurrent read performance.

Events are stored in an append-only queue ordered by timestamp.
Consumption is polling-based (no WebSocket push).
"""
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID


class SQLiteEventsService:
    """
    SQLite-backed event queue that mirrors the RedPandaService interface.

    Stores events in the shared zerodb.db database at ~/.zerodb/data/zerodb.db,
    using an append-only events_queue table with FIFO ordering.
    """

    _local = threading.local()

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the SQLite events service.

        Args:
            db_path: Override path to the SQLite database file.
                     Defaults to ~/.zerodb/data/zerodb.db
        """
        if db_path is None:
            db_path = os.path.join(
                Path.home(), ".zerodb", "data", "zerodb.db"
            )
        self.db_path = db_path
        self.default_topic = os.getenv("ZERODB_EVENT_TOPIC", "zerodb-events")
        self._ensure_db_dir()
        self._initialize_schema()

    def _ensure_db_dir(self) -> None:
        """Create the database directory if it does not exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a thread-local SQLite connection with WAL mode enabled.

        Returns:
            sqlite3.Connection configured for WAL mode
        """
        # Ensure the thread-local connection matches this instance's db_path.
        # Multiple service instances (e.g. in tests) may share the class-level
        # threading.local, so we track which path the connection belongs to.
        current_path = getattr(self._local, "db_path", None)
        if (
            not hasattr(self._local, "conn")
            or self._local.conn is None
            or current_path != self.db_path
        ):
            # Close stale connection from a different db_path
            old_conn = getattr(self._local, "conn", None)
            if old_conn is not None:
                try:
                    old_conn.close()
                except sqlite3.Error:
                    pass

            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
            self._local.db_path = self.db_path
        return self._local.conn

    def _initialize_schema(self) -> None:
        """Create the events_queue table if it does not already exist."""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                payload JSON NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_queue_topic
            ON events_queue (topic)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_queue_created_at
            ON events_queue (created_at)
        """)
        conn.commit()

    async def publish_event(
        self,
        project_id: UUID,
        event_type: str,
        event_data: Dict[str, Any],
        source: Optional[str] = None,
        correlation_id: Optional[str] = None,
        topic_name: Optional[str] = None,
    ) -> bool:
        """
        Publish an event to the SQLite event queue.

        Args:
            project_id: Project UUID
            event_type: Event type (e.g., 'vector.upserted', 'table.created')
            event_data: Event payload
            source: Event source identifier
            correlation_id: Correlation ID for distributed tracing
            topic_name: Topic/channel name (defaults to zerodb-events)

        Returns:
            True on success, False on failure
        """
        if topic_name is None:
            topic_name = self.default_topic

        payload = {
            "project_id": str(project_id),
            "event_type": event_type,
            "source": source or "zerodb-local",
            "correlation_id": correlation_id,
            "event_data": event_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            conn = self._get_connection()
            conn.execute(
                "INSERT INTO events_queue (topic, payload) VALUES (?, ?)",
                (topic_name, json.dumps(payload)),
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False

    async def consume_events(
        self,
        project_id: Optional[UUID] = None,
        event_types: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
        topic_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Consume events from the queue using polling.

        Events are returned in FIFO order (oldest first). This is a
        non-destructive read; events remain in the table for replay.

        Args:
            project_id: Filter by project UUID
            event_types: Filter by event type strings
            limit: Maximum number of events to return
            offset: Number of events to skip (for pagination)
            topic_name: Topic/channel filter

        Returns:
            List of event dicts ordered by creation time ascending
        """
        if topic_name is None:
            topic_name = self.default_topic

        conn = self._get_connection()
        rows = conn.execute(
            "SELECT id, topic, payload, created_at FROM events_queue "
            "WHERE topic = ? ORDER BY created_at ASC, id ASC LIMIT ? OFFSET ?",
            (topic_name, limit, offset),
        ).fetchall()

        events = []
        for row in rows:
            payload = json.loads(row["payload"])

            # Apply project_id filter
            if project_id and payload.get("project_id") != str(project_id):
                continue

            # Apply event_types filter
            if event_types and payload.get("event_type") not in event_types:
                continue

            events.append(
                {
                    "id": row["id"],
                    "topic": row["topic"],
                    "payload": payload,
                    "created_at": row["created_at"],
                }
            )

        return events

    async def get_events(
        self,
        topic_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get events from the queue without any payload-level filtering.

        Args:
            topic_name: Topic/channel filter
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            List of event dicts ordered by creation time ascending
        """
        if topic_name is None:
            topic_name = self.default_topic

        conn = self._get_connection()
        rows = conn.execute(
            "SELECT id, topic, payload, created_at FROM events_queue "
            "WHERE topic = ? ORDER BY created_at ASC, id ASC LIMIT ? OFFSET ?",
            (topic_name, limit, offset),
        ).fetchall()

        return [
            {
                "id": row["id"],
                "topic": row["topic"],
                "payload": json.loads(row["payload"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    async def get_event_count(
        self,
        topic_name: Optional[str] = None,
    ) -> int:
        """
        Get the total number of events for a topic.

        Args:
            topic_name: Topic/channel filter

        Returns:
            Integer count of events
        """
        if topic_name is None:
            topic_name = self.default_topic

        conn = self._get_connection()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM events_queue WHERE topic = ?",
            (topic_name,),
        ).fetchone()

        return row["cnt"] if row else 0

    async def health_check(self) -> Dict[str, Any]:
        """
        Check SQLite event queue health.

        Returns:
            Health status dict
        """
        try:
            conn = self._get_connection()
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM events_queue"
            ).fetchone()
            return {
                "status": "healthy",
                "backend": "sqlite",
                "db_path": self.db_path,
                "total_events": row["cnt"] if row else 0,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "sqlite",
                "db_path": self.db_path,
                "error": str(e),
            }

    def close(self) -> None:
        """Close the thread-local SQLite connection."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None


# Global instance
sqlite_events_service = SQLiteEventsService()
