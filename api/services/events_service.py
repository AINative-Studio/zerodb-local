"""
Events Service
Handles event storage and streaming using PostgreSQL + RedPanda
"""
import json
import os
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from services.redpanda_service import redpanda_service


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
        # Step 1: Store in PostgreSQL
        insert_query = text("""
            INSERT INTO events (project_id, event_type, source, correlation_id, event_data)
            VALUES (:project_id, :event_type, :source, :correlation_id, CAST(:event_data AS jsonb))
            RETURNING id, event_type, source, correlation_id, event_data, timestamp
        """)

        result = db.execute(
            insert_query,
            {
                "project_id": str(project_id),
                "event_type": event_type,
                "source": source,
                "correlation_id": correlation_id,
                "event_data": json.dumps(event_data) if event_data else "{}"
            }
        ).first()

        db.commit()

        event_id = str(result.id)

        # Step 2: Publish to RedPanda
        topic = f"{self.default_topic_prefix}.{project_id}.events"
        event_message = {
            "id": event_id,
            "project_id": str(project_id),
            "event_type": result.event_type,
            "source": result.source,
            "correlation_id": result.correlation_id,
            "event_data": result.event_data,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None
        }

        await redpanda_service.publish_event(
            topic=topic,
            event=event_message
        )

        return {
            "id": event_id,
            "event_type": result.event_type,
            "source": result.source,
            "correlation_id": result.correlation_id,
            "event_data": result.event_data,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None
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
            params["start_time"] = start_time

        if end_time:
            filters.append("timestamp <= :end_time")
            params["end_time"] = end_time

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
                "correlation_id": row.correlation_id,
                "event_data": row.event_data,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None
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
            "correlation_id": result.correlation_id,
            "event_data": result.event_data,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None
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
                "start_time": start_time
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
                "start_time": start_time
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
            {"project_id": str(project_id), "start_time": start_time}
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

        # Subscribe to RedPanda topic
        subscription_id = await redpanda_service.subscribe_to_topic(
            topic=topic,
            consumer_group=f"project_{project_id}"
        )

        return {
            "subscription_id": subscription_id,
            "topic": topic,
            "event_types": event_types
        }


# Global instance
events_service = EventsService()
