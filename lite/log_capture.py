"""
Real log capture for lite mode.

api/routers/logs.py's only log source was `docker compose logs <service>` --
lite mode has no containers at all (SQLite + FAISS + filesystem, one
process), so GET /v1/logs always returned zero entries regardless of real
server activity (Refs #97). This module installs a file handler on the
root logger so every log record the running process emits -- uvicorn's own
request/error logs, and every module's `logging.getLogger(__name__)` calls
(e.g. api/services/sync_orchestrator.py's real sync-step logging) -- lands
in one structured, readable-back file under the server's own --data-dir,
consistent with where sqlite/faiss data for that data dir already lives.
"""
import json
import logging
import logging.handlers
from pathlib import Path
from typing import List, Optional

LOG_FILENAME = "server.log"
_installed = False


class _JsonLineFormatter(logging.Formatter):
    """One JSON object per line, so it can be parsed back without the
    fragile multi-pattern regex guessing logs.py used against Docker's
    pass-through text (Refs #97)."""

    def format(self, record: logging.LogRecord) -> str:
        # logging.Formatter.formatTime's datefmt goes through time.strftime,
        # which has no %f (microseconds) directive -- that's a formatTime-
        # only convenience %(msecs)03d normally supplies via the default
        # format string, not via datefmt. Build the ISO timestamp manually
        # so round-tripping through datetime.strptime("%Y-%m-%dT%H:%M:%S.%f")
        # in read_logs() below actually works.
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return json.dumps({
            "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "level": record.levelname,
            "service": "api",
            "message": record.getMessage(),
            "source": record.name,
        })


def install(data_dir: Path) -> Path:
    """
    Attach a rotating file handler to the root logger, writing to
    `data_dir / LOG_FILENAME`. Idempotent: safe to call more than once
    (e.g. under uvicorn --reload re-importing this module) -- only
    installs the handler the first time per process.

    Returns the log file path.
    """
    global _installed
    log_path = Path(data_dir) / LOG_FILENAME

    if not _installed:
        handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=3,
        )
        handler.setFormatter(_JsonLineFormatter())
        root = logging.getLogger()
        root.addHandler(handler)
        if root.level > logging.INFO or root.level == logging.NOTSET:
            root.setLevel(logging.INFO)
        _installed = True

    return log_path


def read_logs(
    data_dir: Path,
    level: Optional[str] = None,
    limit: int = 100,
    since_minutes: int = 60,
) -> List[dict]:
    """
    Read back captured log entries from `data_dir / LOG_FILENAME`,
    newest first, applying the same level/time-window filters
    GET /v1/logs already exposes for the Docker-backed path.

    Tolerant of a missing file (server just started, nothing logged yet)
    and of any non-JSON line (e.g. a stray print() that bypassed logging)
    by skipping it rather than failing the whole read.
    """
    from datetime import datetime, timedelta

    log_path = Path(data_dir) / LOG_FILENAME
    if not log_path.exists():
        return []

    cutoff = datetime.now() - timedelta(minutes=since_minutes)
    entries = []

    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            try:
                ts = datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S.%f")
            except (KeyError, ValueError):
                continue
            if ts < cutoff:
                continue

            if level and entry.get("level") != level.upper():
                continue

            entries.append(entry)

    entries.sort(key=lambda e: e["timestamp"], reverse=True)
    return entries[:limit]
