"""
Logs Router - System logs and service logs viewing
Provides real-time access to application and service logs
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from pydantic import BaseModel
import logging
import re

router = APIRouter()

_LEVEL_PATTERN = re.compile(
    r"\b(CRITICAL|FATAL|ERROR|WARN(?:ING)?|INFO|DEBUG)\b", re.IGNORECASE
)
_LEVEL_ALIASES = {"WARN": "WARNING", "FATAL": "CRITICAL"}


class LogEntry(BaseModel):
    """Individual log entry from services"""
    timestamp: datetime
    level: str  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    service: str  # postgres, qdrant, minio, redpanda, embeddings, api, dashboard
    message: str
    source: Optional[str] = None  # Container name or process


class LogsResponse(BaseModel):
    """Response containing log entries"""
    logs: List[LogEntry]
    total_count: int
    service: Optional[str]
    level: Optional[str]
    time_range_start: datetime
    time_range_end: datetime


# Refs #126: zerodb-api runs inside a Docker container with neither the
# `docker` CLI binary nor /var/run/docker.sock mounted by default -- a
# previous version of parse_docker_logs() shelled out to
# `docker compose logs`, which always raised FileNotFoundError in that
# environment (confirmed live: every real deployment hit this, not just a
# rare edge case) and silently fell back to a canned message generator
# (get_synthetic_logs(), now removed) that produced data completely
# disconnected from real service behavior -- the same message text
# appeared under every severity level depending on list position, not
# message content. docker-compose.yml now mounts the host's Docker socket
# into zerodb-api specifically so this endpoint can read real container
# logs via the Docker Engine API instead.
_docker_client = None


def _get_docker_client():
    """
    Lazily create the module-level Docker client. Deferred rather than
    created at import time so importing this router doesn't require a
    reachable Docker socket (e.g. under lite mode, or in tests that don't
    exercise this endpoint).
    """
    global _docker_client
    if _docker_client is None:
        import docker
        _docker_client = docker.from_env()
    return _docker_client


def _extract_level(line: str) -> str:
    """
    Best-effort severity extraction from a raw container log line. Real
    services each use their own log format (Postgres's "LOG:"/"ERROR:",
    uvicorn's "INFO:", etc.) -- this looks for a recognizable level token
    anywhere in the line rather than assuming one fixed format, and falls
    back to INFO (not ERROR) for a line that doesn't name one, since most
    unlabeled output is routine (e.g. Postgres's multi-line DETAIL/STATEMENT
    continuation lines for an error already reported on the line above).
    """
    match = _LEVEL_PATTERN.search(line)
    if not match:
        return "INFO"
    level = match.group(1).upper()
    return _LEVEL_ALIASES.get(level, level)


def parse_docker_logs(service_name: str, limit: int = 100) -> List[LogEntry]:
    """
    Fetch real logs for a service's container via the Docker Engine API.

    Args:
        service_name: Service name as used in docker-compose.yml
            (postgres, qdrant, minio, redpanda, embeddings, api, dashboard)
        limit: Maximum number of lines to fetch

    Returns:
        list: Parsed, real log entries for this service, most recent last
        (matches Docker's own `logs()` ordering; get_logs() re-sorts).
        Empty if the container can't be reached -- logged, not fabricated.
    """
    container_name = f"zerodb-{service_name}"

    try:
        client = _get_docker_client()
        container = client.containers.get(container_name)
        raw = container.logs(tail=limit, timestamps=True).decode(
            "utf-8", errors="replace"
        )
    except Exception as e:
        logging.warning(
            "Could not fetch real logs for %s (container %s): %s",
            service_name, container_name, e,
        )
        return []

    logs = []
    for line in raw.split("\n"):
        if not line.strip():
            continue
        # Docker's `timestamps=True` prefixes every line with its own
        # RFC3339Nano timestamp and a single space, independent of
        # whatever timestamp format (or none) the service itself writes --
        # e.g. "2026-11-23T23:44:28.678555631Z 2026-11-23 23:44:28.678 UTC ...".
        ts_str, _, rest = line.partition(" ")
        try:
            # get_logs()'s cutoff_time and the lite-mode path's own parsed
            # timestamps (lite/log_capture.py's read_logs(), via naive
            # strptime with no %z) are both timezone-naive -- stripping
            # tzinfo here (the value is already real UTC from Docker, just
            # represented without an explicit offset) keeps LogEntry.timestamp
            # comparable across both code paths instead of crashing with
            # "can't compare offset-naive and offset-aware datetimes".
            timestamp = datetime.fromisoformat(
                ts_str.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except ValueError:
            timestamp = datetime.utcnow()
            rest = line

        logs.append(LogEntry(
            timestamp=timestamp,
            level=_extract_level(rest),
            service=service_name,
            message=rest.strip(),
            source=container_name,
        ))

    return logs


@router.get("/logs", response_model=LogsResponse, tags=["Logs"])
async def get_logs(
    service: Optional[str] = Query(None, description="Filter by service name"),
    level: Optional[str] = Query(None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of log entries to return"),
    since_minutes: int = Query(60, ge=1, le=1440, description="Get logs from last N minutes")
) -> LogsResponse:
    """
    Get system logs with filtering options

    **Parameters:**
    - `service`: Filter logs by service (postgres, qdrant, minio, redpanda, embeddings, api, dashboard)
    - `level`: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - `limit`: Maximum number of entries to return (default: 100, max: 1000)
    - `since_minutes`: Time window in minutes (default: 60, max: 1440/24h)

    **Returns:**
    - List of log entries matching the filters
    - Total count of matching entries
    - Time range of the query
    """
    from lite.config import DATA_DIR, is_lite_mode

    all_logs = []

    if is_lite_mode():
        # Refs #97: lite mode has no Docker containers to read
        # `docker compose logs` from at all -- read back this process's
        # own captured output instead (installed at startup by
        # lite.log_capture, api/main.py).
        from lite.log_capture import read_logs as read_captured_logs

        for entry in read_captured_logs(DATA_DIR, level=level, limit=limit, since_minutes=since_minutes):
            if service and entry.get("service") != service:
                continue
            try:
                all_logs.append(LogEntry(**entry))
            except Exception:
                continue
    else:
        all_services = ["postgres", "qdrant", "minio", "redpanda", "embeddings", "api", "dashboard"]
        services_to_query = [service] if service else all_services

        # Gather logs from all requested services
        for svc in services_to_query:
            service_logs = parse_docker_logs(svc, limit)
            all_logs.extend(service_logs)

    # Apply level filter
    if level:
        all_logs = [log for log in all_logs if log.level == level.upper()]

    # Apply time filter
    cutoff_time = datetime.now() - timedelta(minutes=since_minutes)
    all_logs = [log for log in all_logs if log.timestamp >= cutoff_time]

    # Sort by timestamp (most recent first)
    all_logs = sorted(all_logs, key=lambda x: x.timestamp, reverse=True)

    # Apply limit
    limited_logs = all_logs[:limit]

    time_end = datetime.now()
    time_start = time_end - timedelta(minutes=since_minutes)

    return LogsResponse(
        logs=limited_logs,
        total_count=len(all_logs),
        service=service,
        level=level,
        time_range_start=time_start,
        time_range_end=time_end
    )


@router.get("/logs/services", tags=["Logs"])
async def get_available_services() -> List[str]:
    """
    Get list of available services that have logs

    **Returns:**
    - List of service names
    """
    return ["postgres", "qdrant", "minio", "redpanda", "embeddings", "api", "dashboard"]


@router.get("/logs/levels", tags=["Logs"])
async def get_log_levels() -> List[str]:
    """
    Get list of available log levels

    **Returns:**
    - List of log level names
    """
    return ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
