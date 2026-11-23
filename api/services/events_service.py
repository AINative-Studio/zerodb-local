"""
Events Service
Handles event storage and streaming using PostgreSQL + RedPanda
"""
import json
import os
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from services.redpanda_service import redpanda_service
from lite.config import is_lite_mode
from lite.sql_compat import jsonb_cast_sql, new_id, parse_json_column, to_isoformat


def _bind_timestamp(value: datetime):
    """
    Bind a datetime filter value in the shape the active backend's
    `timestamp` column expects: SQLite stores timestamps as ISO-8601 TEXT
    (see lite/db/schema_lite.sql), so a raw datetime object compares
    incorrectly against it; PostgreSQL's timestamp column takes a datetime
    object directly.
    """
    if is_lite_mode():
        return value.isoformat()
    return value


class EventsService:
    """
    Service for event operations

    Architecture:
    - PostgreSQL: Stores events for querying and history
    - RedPanda: Real-time event streaming (Kafka-compatible)
    """

    def __init__(self):
        self.default_topic_prefix = os.getenv("REDPANDA_TOPIC_PREFIX", "zerodb_local")

    async def create_event(
        self,
        db: Session,
        project_id: UUID,
        event_type: str,
        event_data: Dict[str, Any],
        source: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an event

        Steps:
        1. Store in PostgreSQL (persistent history)
        2. Publish to RedPanda (real-time streaming)

        Args:
            db: Database session
            project_id: Project UUID
            event_type: Event type/category
            event_data: Event payload
            source: Event source identifier
            correlation_id: Optional correlation ID for tracing

        Returns:
            Created event info
        """
        # Step 1: Store in PostgreSQL. In lite mode `id` has no SQL-level
        # default (Postgres's schema declares DEFAULT gen_random_uuid(),
        # SQLite's does not), so generate it explicitly.
        lite = is_lite_mode()
        columns = "project_id, event_type, source, correlation_id, event_data"
        values = f":project_id, :event_type, :source, :correlation_id, {jsonb_cast_sql(':event_data', lite)}"
        params = {
            "project_id": str(project_id),
            "event_type": event_type,
            "source": source,
            "correlation_id": correlation_id,
            "event_data": json.dumps(event_data) if event_data else "{}"
        }
        if lite:
            columns = "id, " + columns
            values = ":id, " + values
            params["id"] = new_id()

        insert_query = text(f"""
            INSERT INTO events ({columns})
            VALUES ({values})
            RETURNING id, event_type, source, correlation_id, event_data, timestamp
        """)

        result = db.execute(insert_query, params).first()

        db.commit()

        event_id = str(result.id)

        # Step 2: Publish to RedPanda
        topic = f"{self.default_topic_prefix}.{project_id}.events"
        event_data_out = parse_json_column(result.event_data)
        timestamp_out = to_isoformat(result.timestamp)

        # NOTE: this call site previously passed topic=/event= kwargs that
        # match neither RedPandaService.publish_event's nor
        # SQLiteEventsService.publish_event's actual signature (both take
        # project_id/event_type/event_data/source/correlation_id/topic_name)
        # -- a pre-existing bug independent of lite vs. full mode, fixed here
        # because it blocks event creation end-to-end in both backends.
        await redpanda_service.publish_event(
            project_id=project_id,
            event_type=result.event_type,
            event_data=event_data_out,
            source=result.source,
            correlation_id=result.correlation_id,
            topic_name=topic
        )

        return {
            "id": event_id,
            "event_type": result.event_type,
            "source": result.source,
            # correlation_id is a UUID column -- psycopg2 returns it as a
            # native uuid.UUID, but EventResponse.correlation_id is typed
            # str; coerce here the same way event_id already is. Refs #50.
            "correlation_id": str(result.correlation_id) if result.correlation_id else None,
            "event_data": event_data_out,
            "timestamp": timestamp_out
        }

    async def list_events(
        self,
        db: Session,
        project_id: UUID,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List events with filtering

        Args:
            db: Database session
            project_id: Project UUID
            event_type: Filter by event type
            source: Filter by source
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            skip: Number to skip (pagination)
            limit: Max results

        Returns:
            List of events
        """
        # Build dynamic query
        filters = ["project_id = :project_id"]
        params = {
            "project_id": str(project_id),
            "limit": limit,
            "offset": skip
        }

        if event_type:
            filters.append("event_type = :event_type")
            params["event_type"] = event_type

        if source:
            filters.append("source = :source")
            params["source"] = source

        if start_time:
            filters.append("timestamp >= :start_time")
            params["start_time"] = _bind_timestamp(start_time)

        if end_time:
            filters.append("timestamp <= :end_time")
            params["end_time"] = _bind_timestamp(end_time)

        where_clause = " AND ".join(filters)

        query = text(f"""
            SELECT id, event_type, source, correlation_id, event_data, timestamp
            FROM events
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """)

        results = db.execute(query, params).fetchall()

        return [
            {
                "id": str(row.id),
                "event_type": row.event_type,
                "source": row.source,
                "correlation_id": str(row.correlation_id) if row.correlation_id else None,
                "event_data": parse_json_column(row.event_data),
                "timestamp": to_isoformat(row.timestamp)
            }
            for row in results
        ]

    async def get_event(
        self,
        db: Session,
        project_id: UUID,
        event_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific event by ID

        Args:
            db: Database session
            project_id: Project UUID
            event_id: Event ID

        Returns:
            Event info or None
        """
        query = text("""
            SELECT id, event_type, source, correlation_id, event_data, timestamp
            FROM events
            WHERE project_id = :project_id
            AND id = :event_id
        """)

        result = db.execute(
            query,
            {"project_id": str(project_id), "event_id": event_id}
        ).first()

        if not result:
            return None

        return {
            "id": str(result.id),
            "event_type": result.event_type,
            "source": result.source,
            "correlation_id": str(result.correlation_id) if result.correlation_id else None,
            "event_data": parse_json_column(result.event_data),
            "timestamp": to_isoformat(result.timestamp)
        }

    async def get_event_stats(
        self,
        db: Session,
        project_id: UUID,
        time_range: str = "day",
        event_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get event statistics

        Args:
            db: Database session
            project_id: Project UUID
            time_range: Time range (hour, day, week, month)
            event_type: Optional filter by event type

        Returns:
            Statistics dict
        """
        # Calculate time window
        now = datetime.utcnow()
        if time_range == "hour":
            start_time = now - timedelta(hours=1)
        elif time_range == "day":
            start_time = now - timedelta(days=1)
        elif time_range == "week":
            start_time = now - timedelta(weeks=1)
        elif time_range == "month":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=1)  # Default to day

        start_time_bound = _bind_timestamp(start_time)

        # Build query
        if event_type:
            stats_query = text("""
                SELECT
                    COUNT(*) as total_events,
                    COUNT(DISTINCT event_type) as event_type_count,
                    COUNT(DISTINCT source) as source_count,
                    :event_type as event_type
                FROM events
                WHERE project_id = :project_id
                AND event_type = :event_type
                AND timestamp >= :start_time
            """)
            params = {
                "project_id": str(project_id),
                "event_type": event_type,
                "start_time": start_time_bound
            }
        else:
            stats_query = text("""
                SELECT
                    COUNT(*) as total_events,
                    COUNT(DISTINCT event_type) as event_type_count,
                    COUNT(DISTINCT source) as source_count
                FROM events
                WHERE project_id = :project_id
                AND timestamp >= :start_time
            """)
            params = {
                "project_id": str(project_id),
                "start_time": start_time_bound
            }

        result = db.execute(stats_query, params).first()

        # Get top event types
        top_types_query = text("""
            SELECT event_type, COUNT(*) as count
            FROM events
            WHERE project_id = :project_id
            AND timestamp >= :start_time
            GROUP BY event_type
            ORDER BY count DESC
            LIMIT 10
        """)

        top_types_results = db.execute(
            top_types_query,
            {"project_id": str(project_id), "start_time": start_time_bound}
        ).fetchall()

        top_event_types = [
            {"event_type": row.event_type, "count": row.count}
            for row in top_types_results
        ]

        return {
            "time_range": time_range,
            "total_events": result.total_events or 0,
            "event_type_count": result.event_type_count or 0,
            "source_count": result.source_count or 0,
            "top_event_types": top_event_types,
            "event_type": event_type
        }

    async def subscribe_to_events(
        self,
        project_id: UUID,
        event_types: Optional[List[str]] = None
    ) -> str:
        """
        Subscribe to event stream

        Args:
            project_id: Project UUID
            event_types: Optional filter by event types

        Returns:
            Subscription topic name
        """
        topic = f"{self.default_topic_prefix}.{project_id}.events"

        # Generate a subscription id identifying this topic/consumer-group
        # pairing. RedPandaService has no subscribe_to_topic() method (it
        # exposes create_consumer()/consume_events() instead, a different,
        # synchronous-iterator shaped API) -- actually opening a Kafka
        # consumer belongs to whatever client later streams from this
        # subscription (e.g. a WebSocket/SSE endpoint using
        # create_consumer() with this same topic/group), not to this
        # call, which only needs to hand back an identifier. Refs #50.
        subscription_id = f"sub_{uuid4()}"

        return {
            "subscription_id": subscription_id,
            "topic": topic,
            "event_types": event_types
        }


# Global instance
events_service = EventsService()
