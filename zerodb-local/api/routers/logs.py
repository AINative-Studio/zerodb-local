"""
Logs Router - System logs and service logs viewing
Provides real-time access to application and service logs
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from pydantic import BaseModel
import logging
import subprocess
import re

router = APIRouter()


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


def parse_docker_logs(service_name: str, limit: int = 100) -> List[LogEntry]:
    """
    Parse Docker Compose logs for a specific service
    Extracts timestamp, level, and message from logs
    """
    logs = []

    try:
        # Try to get logs from Docker Compose
        result = subprocess.run(
            ["docker", "compose", "logs", "--tail", str(limit), service_name],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/Users/aideveloper/core/zerodb-local"
        )

        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue

                # Parse log line - format: service_name | timestamp | level | message
                # Example: zerodb-api-1  | 2026-02-27 10:30:45 | INFO | Server started
                parsed = parse_log_line(line, service_name)
                if parsed:
                    logs.append(parsed)

    except subprocess.TimeoutExpired:
        logging.warning(f"Docker logs timeout for service: {service_name}")
    except FileNotFoundError:
        # Docker not available - return synthetic logs for development
        logging.warning("Docker not available, returning synthetic logs")
        return get_synthetic_logs(service_name, limit)
    except Exception as e:
        logging.error(f"Error fetching Docker logs: {e}")

    return logs


def parse_log_line(line: str, service_name: str) -> Optional[LogEntry]:
    """
    Parse a single log line into LogEntry
    Handles multiple log formats (Docker, uvicorn, generic)
    """
    # Pattern 1: Docker Compose format
    # service-1  | 2026-02-27 10:30:45 | INFO | message
    docker_pattern = r'^[\w-]+\s+\|\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\|\s+(\w+)\s+\|\s+(.+)$'

    # Pattern 2: Python logging format
    # 2026-02-27 10:30:45,123 - service - INFO - message
    python_pattern = r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),\d+\s+-\s+\w+\s+-\s+(\w+)\s+-\s+(.+)$'

    # Pattern 3: Simple timestamp format
    # [2026-02-27 10:30:45] INFO: message
    simple_pattern = r'^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+(\w+):\s+(.+)$'

    for pattern in [docker_pattern, python_pattern, simple_pattern]:
        match = re.match(pattern, line.strip())
        if match:
            try:
                timestamp_str, level, message = match.groups()
                timestamp = datetime.fromisoformat(timestamp_str.replace(',', '.'))

                return LogEntry(
                    timestamp=timestamp,
                    level=level.upper(),
                    service=service_name,
                    message=message.strip(),
                    source=service_name
                )
            except Exception as e:
                logging.debug(f"Failed to parse matched log line: {e}")
                continue

    # If no pattern matches, create basic entry with current timestamp
    return LogEntry(
        timestamp=datetime.now(),
        level="INFO",
        service=service_name,
        message=line.strip(),
        source=service_name
    )


def get_synthetic_logs(service_name: str, limit: int) -> List[LogEntry]:
    """
    Generate synthetic logs for development/demo purposes
    Used when Docker is not available
    """
    base_time = datetime.now()
    logs = []

    messages = {
        "postgres": [
            "Database connection established",
            "Query executed in 12ms",
            "Connection pool size: 8/20",
            "Checkpoint completed",
            "Vacuum process completed",
        ],
        "qdrant": [
            "Vector collection initialized",
            "Search query completed in 45ms",
            "Index built successfully",
            "Collection size: 1024 vectors",
            "Memory usage: 128MB",
        ],
        "minio": [
            "Object uploaded: file_123.txt",
            "Bucket created: project-files",
            "Storage usage: 2.5GB",
            "Object download completed",
            "Cleanup job completed",
        ],
        "redpanda": [
            "Topic created: events",
            "Message published to topic",
            "Consumer group registered",
            "Partition rebalance completed",
            "Throughput: 1000 msg/s",
        ],
        "embeddings": [
            "Model loaded: BAAI/bge-base-en-v1.5",
            "Embedding generated in 23ms",
            "Batch size: 32 documents",
            "GPU memory: 512MB",
            "Model warmup completed",
        ],
        "api": [
            "Server started on port 8000",
            "Request: GET /v1/projects",
            "Response time: 15ms",
            "WebSocket connection established",
            "Authentication successful",
        ],
        "dashboard": [
            "React app initialized",
            "User navigated to /logs",
            "API client connected",
            "State updated successfully",
            "Component rendered in 8ms",
        ]
    }

    levels = ["DEBUG", "INFO", "INFO", "INFO", "WARNING", "ERROR"]
    service_messages = messages.get(service_name, ["Generic log message"])

    for i in range(min(limit, 50)):
        logs.append(LogEntry(
            timestamp=base_time - timedelta(seconds=i * 10),
            level=levels[i % len(levels)],
            service=service_name,
            message=service_messages[i % len(service_messages)],
            source=f"{service_name}-1"
        ))

    return sorted(logs, key=lambda x: x.timestamp, reverse=True)


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
    all_services = ["postgres", "qdrant", "minio", "redpanda", "embeddings", "api", "dashboard"]
    services_to_query = [service] if service else all_services

    all_logs = []

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
