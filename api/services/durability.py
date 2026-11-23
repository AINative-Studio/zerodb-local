"""
DBOS durable-execution setup.

Refs #107: makes VectorService's upsert/delete workflow resumable after a
crash between its SQL write and its Qdrant/FAISS write, instead of the two
stores silently drifting out of sync.

DBOS checkpoints workflow/step progress to its own system database, kept
entirely separate from the app's own data (the `vectors` table, the FAISS
index, etc.) -- a crash mid-write still leaves the app's own stores in
whatever state they were in; DBOS's job is only to know which step to
resume from, not to be the source of truth for the data itself. SQLite is
used in both lite and full mode: it needs no setup, and keeping DBOS's own
schema out of the app's Postgres database in full mode avoids coupling two
independently-evolving schemas together for no real benefit -- DBOS runs
fine on SQLite regardless of which backend the rest of the app is using.
"""
from pathlib import Path

from dbos import DBOS, DBOSConfig

from lite.config import DATA_DIR

_DBOS_DB_FILENAME = "dbos_durability.sqlite"
_launched = False


def launch(data_dir: Path = DATA_DIR) -> None:
    """
    Initialize and launch DBOS. Idempotent -- safe to call more than once
    (e.g. if api/main.py's lifespan runs more than once in a test), since
    DBOS itself would otherwise raise on a second DBOS(config=...) call in
    the same process.
    """
    global _launched
    if _launched:
        return

    db_path = Path(data_dir) / _DBOS_DB_FILENAME
    config: DBOSConfig = {
        "name": "zerodb-local",
        "system_database_url": f"sqlite:///{db_path}",
    }
    DBOS(config=config)
    DBOS.launch()
    _launched = True
