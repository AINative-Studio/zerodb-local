"""
RedPanda Event Streaming Service
Handles event publishing and consumption using RedPanda (Kafka-compatible)
"""
import os
import json
from typing import List, Dict, Any, Optional, Callable
from uuid import UUID
from datetime import datetime

try:
    from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
    from kafka.admin import NewTopic
    from kafka.errors import KafkaError, TopicAlreadyExistsError
    _KAFKA_AVAILABLE = True
except ImportError:
    _KAFKA_AVAILABLE = False


class RedPandaService:
    """Service for interacting with RedPanda event streaming"""

    def __init__(self):
        """Initialize RedPanda (Kafka) client"""
        self.bootstrap_servers = os.getenv("REDPANDA_URL", "localhost:9092")
        self.default_topic = os.getenv("REDPANDA_TOPIC", "zerodb-events")
        self.testing = os.getenv("TESTING", "false").lower() == "true"

        # Initialize producer (lazy - created on first publish)
        self._producer = None

        # Initialize admin client (lazy - created on first use)
        self._admin_client = None

    def _get_admin_client(self):
        """Get or create Kafka admin client"""
        if self._admin_client is None:
            if not _KAFKA_AVAILABLE or self.testing:
                # Mock admin client for testing or lite mode
                from unittest.mock import MagicMock
                self._admin_client = MagicMock()
        return self._admin_client

    def _get_producer(self) -> KafkaProducer:
        """Get or create Kafka producer"""
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                retries=3
            )
        return self._producer

    async def initialize_topic(
        self,
        topic_name: str = None,
        num_partitions: int = 3,
        replication_factor: int = 1
    ) -> bool:
        """
        Create topic if it doesn't exist

        Args:
            topic_name: Topic name (default: zerodb-events)
            num_partitions: Number of partitions
            replication_factor: Replication factor

        Returns:
            bool: True if created/exists, False on error
        """
        if topic_name is None:
            topic_name = self.default_topic

        try:
            # Get admin client (lazy initialization)
            admin_client = self._get_admin_client()

            # Check if topic exists
            existing_topics = admin_client.list_topics()

            if topic_name in existing_topics:
                print(f"✅ Topic '{topic_name}' already exists")
                return True

            # Create topic
            topic = NewTopic(
                name=topic_name,
                num_partitions=num_partitions,
                replication_factor=replication_factor
            )

            admin_client.create_topics([topic], validate_only=False)
            print(f"✅ Created topic '{topic_name}' with {num_partitions} partitions")
            return True

        except TopicAlreadyExistsError:
            print(f"✅ Topic '{topic_name}' already exists")
            return True

        except KafkaError as e:
            print(f"❌ Error creating topic: {e}")
            return False

    async def publish_event(
        self,
        project_id: UUID,
        event_type: str,
        event_data: Dict[str, Any],
        source: str = None,
        correlation_id: str = None,
        topic_name: str = None
    ) -> bool:
        """
        Publish event to RedPanda

        Args:
            project_id: Project UUID
            event_type: Event type (e.g., 'vector.upserted', 'table.created')
            event_data: Event payload
            source: Event source
            correlation_id: Correlation ID for tracking
            topic_name: Topic name

        Returns:
            bool: Success status
        """
        if topic_name is None:
            topic_name = self.default_topic

        try:
            # Build event payload
            event = {
                "project_id": str(project_id),
                "event_type": event_type,
                "source": source or "zerodb-local",
                "correlation_id": correlation_id,
                "event_data": event_data,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Publish to RedPanda
            producer = self._get_producer()
            future = producer.send(
                topic=topic_name,
                key=str(project_id),  # Partition by project_id
                value=event
            )

            # Wait for confirmation (with timeout)
            record_metadata = future.get(timeout=10)

            print(f"✅ Published event '{event_type}' to topic '{topic_name}' "
                  f"(partition {record_metadata.partition}, offset {record_metadata.offset})")
            return True

        except KafkaError as e:
            print(f"❌ Error publishing event: {e}")
            return False

    async def publish_batch(
        self,
        events: List[Dict[str, Any]],
        topic_name: str = None
    ) -> int:
        """
        Publish batch of events

        Args:
            events: List of event dicts
            topic_name: Topic name

        Returns:
            int: Number of events successfully published
        """
        if topic_name is None:
            topic_name = self.default_topic

        success_count = 0
        producer = self._get_producer()

        for event in events:
            try:
                # Add timestamp if not present
                if "timestamp" not in event:
                    event["timestamp"] = datetime.utcnow().isoformat()

                # Publish
                future = producer.send(
                    topic=topic_name,
                    key=event.get("project_id"),
                    value=event
                )

                # Don't wait for individual confirmations (faster)
                success_count += 1

            except KafkaError as e:
                print(f"❌ Error publishing event in batch: {e}")
                continue

        # Flush to ensure all messages sent
        producer.flush()

        print(f"✅ Published {success_count}/{len(events)} events to topic '{topic_name}'")
        return success_count

    def create_consumer(
        self,
        project_id: UUID = None,
        event_types: List[str] = None,
        group_id: str = None,
        topic_name: str = None,
        auto_offset_reset: str = "earliest"
    ) -> KafkaConsumer:
        """
        Create event consumer

        Args:
            project_id: Filter by project UUID
            event_types: Filter by event types
            group_id: Consumer group ID
            topic_name: Topic name
            auto_offset_reset: Where to start reading ('earliest' or 'latest')

        Returns:
            KafkaConsumer instance
        """
        if topic_name is None:
            topic_name = self.default_topic

        if group_id is None:
            group_id = f"zerodb-consumer-{str(project_id) if project_id else 'all'}"

        consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )

        return consumer

    async def consume_events(
        self,
        project_id: UUID = None,
        event_types: List[str] = None,
        limit: int = 100,
        timeout_ms: int = 5000,
        topic_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        Consume events (blocking until limit or timeout)

        Args:
            project_id: Filter by project UUID
            event_types: Filter by event types
            limit: Max events to consume
            timeout_ms: Timeout in milliseconds
            topic_name: Topic name

        Returns:
            List of events
        """
        consumer = self.create_consumer(
            project_id=project_id,
            event_types=event_types,
            topic_name=topic_name
        )

        events = []
        try:
            for message in consumer:
                event = message.value

                # Apply filters
                if project_id and event.get("project_id") != str(project_id):
                    continue

                if event_types and event.get("event_type") not in event_types:
                    continue

                events.append(event)

                if len(events) >= limit:
                    break

        except KeyboardInterrupt:
            pass
        finally:
            consumer.close()

        return events

    async def get_topic_offsets(
        self,
        topic_name: str = None
    ) -> Dict[int, Dict[str, int]]:
        """
        Get topic partition offsets

        Args:
            topic_name: Topic name

        Returns:
            Dict mapping partition to {beginning, end} offsets
        """
        if topic_name is None:
            topic_name = self.default_topic

        try:
            consumer = KafkaConsumer(
                topic_name,
                bootstrap_servers=self.bootstrap_servers
            )

            partitions = consumer.partitions_for_topic(topic_name)
            offsets = {}

            for partition in partitions:
                tp = (topic_name, partition)

                # Get beginning and end offsets
                beginning = consumer.beginning_offsets([tp])[tp]
                end = consumer.end_offsets([tp])[tp]

                offsets[partition] = {
                    "beginning": beginning,
                    "end": end,
                    "lag": end - beginning
                }

            consumer.close()
            return offsets

        except KafkaError as e:
            print(f"❌ Error getting topic offsets: {e}")
            return {}

    async def health_check(self) -> Dict[str, Any]:
        """
        Check RedPanda health

        Returns:
            Health status dict
        """
        try:
            # Get admin client (lazy initialization)
            admin_client = self._get_admin_client()

            # Try to list topics
            topics = admin_client.list_topics()

            # Get cluster brokers
            cluster = admin_client._client.cluster
            brokers = cluster.brokers()

            return {
                "status": "healthy",
                "bootstrap_servers": self.bootstrap_servers,
                "topics": topics,
                "brokers": len(brokers)
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "bootstrap_servers": self.bootstrap_servers,
                "error": str(e)
            }

    def close(self):
        """Close producer and admin client"""
        if self._producer:
            self._producer.close()
        if self._admin_client:
            self._admin_client.close()


# Global instance
def _create_redpanda_service():
    try:
        from lite.config import is_lite_mode
        if is_lite_mode():
            from lite.services.sqlite_events_service import SQLiteEventsService
            return SQLiteEventsService()
    except ImportError:
        pass
    return RedPandaService()

redpanda_service = _create_redpanda_service()
