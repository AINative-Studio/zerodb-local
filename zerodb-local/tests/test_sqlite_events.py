"""
Test SQLite Event Queue Service
BDD-style tests for the lite SQLite-backed event queue.

Covers: publish, consume, topic filtering, FIFO ordering,
event count, empty queue handling, health check, and cleanup.
"""
import asyncio
import json
import os
import sqlite3
import tempfile
import uuid
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixture: isolated database per test
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary SQLite database path for test isolation."""
    return str(tmp_path / "test_zerodb.db")


@pytest.fixture
def service(db_path):
    """Create a fresh SQLiteEventsService instance with a temp database."""
    # Import here so the module can be tested even without installing
    # into the zerodb-local package path.
    import sys

    sys.path.insert(
        0,
        str(Path(__file__).resolve().parent.parent / "lite" / "services"),
    )
    from sqlite_events_service import SQLiteEventsService

    svc = SQLiteEventsService(db_path=db_path)
    yield svc
    svc.close()


@pytest.fixture
def project_id():
    """Generate a deterministic project UUID for tests."""
    return uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def run(request):
    """Helper to run async coroutines in sync tests."""
    loop = asyncio.new_event_loop()
    yield loop.run_until_complete
    loop.close()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------


class TestSchemaInitialisation:
    """Scenario: Service creates the events_queue table on startup."""

    def test_events_queue_table_exists(self, service, db_path):
        """Given a new service, the events_queue table should exist."""
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='events_queue'"
        )
        tables = cursor.fetchall()
        conn.close()
        assert len(tables) == 1

    def test_wal_mode_enabled(self, service, db_path):
        """Given a new service, WAL journal mode should be active."""
        conn = sqlite3.connect(db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"


# ---------------------------------------------------------------------------
# Publish events
# ---------------------------------------------------------------------------


class TestPublishEvent:
    """Scenario: Publishing events stores them in the SQLite queue."""

    def test_publish_single_event(self, service, project_id, run):
        """Given valid event data, publish_event returns True."""
        result = run(
            service.publish_event(
                project_id=project_id,
                event_type="vector.upserted",
                event_data={"vector_id": "v1"},
                source="test",
            )
        )
        assert result is True

    def test_published_event_persisted(self, service, project_id, db_path, run):
        """Given a published event, it should be stored in the database."""
        run(
            service.publish_event(
                project_id=project_id,
                event_type="table.created",
                event_data={"table": "users"},
            )
        )
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM events_queue LIMIT 1").fetchone()
        conn.close()

        assert row is not None
        payload = json.loads(row["payload"])
        assert payload["event_type"] == "table.created"
        assert payload["project_id"] == str(project_id)

    def test_publish_with_correlation_id(self, service, project_id, run):
        """Given a correlation_id, it should appear in the stored payload."""
        run(
            service.publish_event(
                project_id=project_id,
                event_type="test.event",
                event_data={},
                correlation_id="trace-abc-123",
            )
        )
        events = run(service.get_events())
        assert events[0]["payload"]["correlation_id"] == "trace-abc-123"

    def test_publish_uses_default_source(self, service, project_id, run):
        """Given no source, the default 'zerodb-local' should be used."""
        run(
            service.publish_event(
                project_id=project_id,
                event_type="test.event",
                event_data={},
            )
        )
        events = run(service.get_events())
        assert events[0]["payload"]["source"] == "zerodb-local"

    def test_publish_custom_topic(self, service, project_id, run):
        """Given a custom topic, the event should be stored under that topic."""
        run(
            service.publish_event(
                project_id=project_id,
                event_type="custom",
                event_data={},
                topic_name="my-custom-topic",
            )
        )
        events = run(service.get_events(topic_name="my-custom-topic"))
        assert len(events) == 1
        assert events[0]["topic"] == "my-custom-topic"


# ---------------------------------------------------------------------------
# Consume events
# ---------------------------------------------------------------------------


class TestConsumeEvents:
    """Scenario: Consuming events returns them in FIFO order with filters."""

    def test_consume_returns_fifo_order(self, service, project_id, run):
        """Given multiple events, consume returns oldest first."""
        for i in range(5):
            run(
                service.publish_event(
                    project_id=project_id,
                    event_type=f"event_{i}",
                    event_data={"index": i},
                )
            )

        events = run(service.consume_events())
        indices = [e["payload"]["event_data"]["index"] for e in events]
        assert indices == [0, 1, 2, 3, 4]

    def test_consume_with_project_filter(self, service, run):
        """Given events from two projects, filtering returns only the target project."""
        pid_a = uuid.UUID("aaaa1111-0000-0000-0000-000000000000")
        pid_b = uuid.UUID("bbbb2222-0000-0000-0000-000000000000")

        run(service.publish_event(pid_a, "e1", {"p": "a"}))
        run(service.publish_event(pid_b, "e2", {"p": "b"}))
        run(service.publish_event(pid_a, "e3", {"p": "a"}))

        events = run(service.consume_events(project_id=pid_a))
        assert len(events) == 2
        assert all(
            e["payload"]["project_id"] == str(pid_a) for e in events
        )

    def test_consume_with_event_type_filter(self, service, project_id, run):
        """Given mixed event types, filtering returns only matching types."""
        run(service.publish_event(project_id, "click", {}))
        run(service.publish_event(project_id, "view", {}))
        run(service.publish_event(project_id, "click", {}))

        events = run(
            service.consume_events(event_types=["click"])
        )
        assert len(events) == 2
        assert all(e["payload"]["event_type"] == "click" for e in events)

    def test_consume_with_limit(self, service, project_id, run):
        """Given a limit, consume returns at most that many events."""
        for i in range(10):
            run(service.publish_event(project_id, "evt", {"i": i}))

        events = run(service.consume_events(limit=3))
        assert len(events) == 3

    def test_consume_with_offset(self, service, project_id, run):
        """Given an offset, consume skips that many events."""
        for i in range(5):
            run(service.publish_event(project_id, "evt", {"i": i}))

        events = run(service.consume_events(offset=3))
        assert len(events) == 2
        assert events[0]["payload"]["event_data"]["i"] == 3

    def test_consume_with_topic_filter(self, service, project_id, run):
        """Given events on different topics, consume filters by topic."""
        run(
            service.publish_event(
                project_id, "a", {}, topic_name="topic-a"
            )
        )
        run(
            service.publish_event(
                project_id, "b", {}, topic_name="topic-b"
            )
        )

        events = run(service.consume_events(topic_name="topic-a"))
        assert len(events) == 1
        assert events[0]["payload"]["event_type"] == "a"


# ---------------------------------------------------------------------------
# Get events (unfiltered read)
# ---------------------------------------------------------------------------


class TestGetEvents:
    """Scenario: get_events returns raw events without payload filtering."""

    def test_get_events_returns_all_for_topic(self, service, project_id, run):
        """Given 3 events on the default topic, get_events returns all 3."""
        for i in range(3):
            run(service.publish_event(project_id, f"e{i}", {}))

        events = run(service.get_events())
        assert len(events) == 3

    def test_get_events_pagination(self, service, project_id, run):
        """Given events and pagination params, get_events paginates correctly."""
        for i in range(10):
            run(service.publish_event(project_id, "evt", {"i": i}))

        page1 = run(service.get_events(limit=4, offset=0))
        page2 = run(service.get_events(limit=4, offset=4))
        page3 = run(service.get_events(limit=4, offset=8))

        assert len(page1) == 4
        assert len(page2) == 4
        assert len(page3) == 2

        # No overlap between pages
        ids_1 = {e["id"] for e in page1}
        ids_2 = {e["id"] for e in page2}
        assert len(ids_1 & ids_2) == 0


# ---------------------------------------------------------------------------
# Event count
# ---------------------------------------------------------------------------


class TestGetEventCount:
    """Scenario: get_event_count returns accurate totals."""

    def test_count_zero_initially(self, service, run):
        """Given no events, count should be zero."""
        count = run(service.get_event_count())
        assert count == 0

    def test_count_after_publishes(self, service, project_id, run):
        """Given N published events, count returns N."""
        for _ in range(7):
            run(service.publish_event(project_id, "evt", {}))

        count = run(service.get_event_count())
        assert count == 7

    def test_count_filtered_by_topic(self, service, project_id, run):
        """Given events on multiple topics, count respects topic filter."""
        for _ in range(3):
            run(
                service.publish_event(
                    project_id, "a", {}, topic_name="alpha"
                )
            )
        for _ in range(5):
            run(
                service.publish_event(
                    project_id, "b", {}, topic_name="beta"
                )
            )

        assert run(service.get_event_count(topic_name="alpha")) == 3
        assert run(service.get_event_count(topic_name="beta")) == 5


# ---------------------------------------------------------------------------
# Empty queue handling
# ---------------------------------------------------------------------------


class TestEmptyQueueHandling:
    """Scenario: Operations on an empty queue behave gracefully."""

    def test_consume_empty_queue(self, service, run):
        """Given an empty queue, consume_events returns an empty list."""
        events = run(service.consume_events())
        assert events == []

    def test_get_events_empty_queue(self, service, run):
        """Given an empty queue, get_events returns an empty list."""
        events = run(service.get_events())
        assert events == []

    def test_count_empty_queue(self, service, run):
        """Given an empty queue, get_event_count returns zero."""
        count = run(service.get_event_count())
        assert count == 0


# ---------------------------------------------------------------------------
# Event ordering (FIFO guarantee)
# ---------------------------------------------------------------------------


class TestEventOrdering:
    """Scenario: Events are always returned in insertion order (FIFO)."""

    def test_strict_fifo_ordering(self, service, project_id, run):
        """Given 20 sequential inserts, events maintain strict FIFO order."""
        for i in range(20):
            run(
                service.publish_event(
                    project_id, "ordered", {"seq": i}
                )
            )

        events = run(service.get_events(limit=20))
        sequences = [e["payload"]["event_data"]["seq"] for e in events]
        assert sequences == list(range(20))

    def test_ids_monotonically_increasing(self, service, project_id, run):
        """Given sequential inserts, event IDs should increase monotonically."""
        for i in range(10):
            run(service.publish_event(project_id, "evt", {"i": i}))

        events = run(service.get_events(limit=10))
        ids = [e["id"] for e in events]
        assert ids == sorted(ids)
        assert len(set(ids)) == 10  # All unique


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """Scenario: Health check reports service status."""

    def test_healthy_status(self, service, run):
        """Given a working database, health_check returns healthy."""
        health = run(service.health_check())
        assert health["status"] == "healthy"
        assert health["backend"] == "sqlite"
        assert "total_events" in health

    def test_health_check_reflects_event_count(self, service, project_id, run):
        """Given published events, health_check total_events is accurate."""
        for _ in range(3):
            run(service.publish_event(project_id, "evt", {}))

        health = run(service.health_check())
        assert health["total_events"] == 3


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------


class TestConnectionLifecycle:
    """Scenario: Closing the service releases resources cleanly."""

    def test_close_and_reopen(self, db_path):
        """Given a closed service, a new instance can reuse the database."""
        import sys

        sys.path.insert(
            0,
            str(Path(__file__).resolve().parent.parent / "lite" / "services"),
        )
        from sqlite_events_service import SQLiteEventsService

        loop = asyncio.new_event_loop()

        svc1 = SQLiteEventsService(db_path=db_path)
        pid = uuid.UUID("11111111-2222-3333-4444-555555555555")
        loop.run_until_complete(
            svc1.publish_event(pid, "persist", {"data": "survives"})
        )
        svc1.close()

        svc2 = SQLiteEventsService(db_path=db_path)
        events = loop.run_until_complete(svc2.get_events())
        svc2.close()
        loop.close()

        assert len(events) == 1
        assert events[0]["payload"]["event_data"]["data"] == "survives"


# ---------------------------------------------------------------------------
# Complex payload
# ---------------------------------------------------------------------------


class TestComplexPayload:
    """Scenario: Events with deeply nested JSON payloads are stored and retrieved."""

    def test_nested_json_roundtrip(self, service, project_id, run):
        """Given a complex nested payload, it should survive serialisation."""
        complex_data = {
            "user": {
                "id": "u_123",
                "preferences": ["dark_mode", "compact"],
                "settings": {
                    "notifications": {"email": True, "push": False},
                    "quota": 1024,
                },
            },
            "items": [
                {"sku": "A1", "price": 9.99},
                {"sku": "B2", "price": 14.50},
            ],
        }

        run(
            service.publish_event(
                project_id, "purchase", complex_data
            )
        )

        events = run(service.get_events())
        assert events[0]["payload"]["event_data"] == complex_data
