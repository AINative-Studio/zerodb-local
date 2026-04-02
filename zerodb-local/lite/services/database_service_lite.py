"""
Database Service - SQLite Backend
Drop-in replacement for PostgreSQL database_service.py using SQLite.

Matches the same interface as zerodb-local/api/services/database_service.py
with SQLite-specific optimizations: WAL mode, StaticPool, application-level
CDC (replacing PL/pgSQL triggers), and uuid4 defaults.

Refs #1706
"""
import json
import os
import pathlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from lite.services.cdc_service import CDCService


# Default data directory: ~/.zerodb/data/
DEFAULT_DATA_DIR = os.path.join(pathlib.Path.home(), ".zerodb", "data")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DATA_DIR, "zerodb.db")

SCHEMA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "db",
    "schema_lite.sql",
)


def _generate_uuid() -> str:
    """Generate a new UUID4 string (replaces gen_random_uuid())."""
    return str(uuid.uuid4())


def _now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse_json(value: Optional[str]) -> Any:
    """Safely parse a JSON string, returning the value or empty dict on failure."""
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _dump_json(value: Any) -> str:
    """Serialize a value to JSON string for storage."""
    if isinstance(value, str):
        try:
            json.loads(value)
            return value
        except (json.JSONDecodeError, TypeError):
            return json.dumps(value)
    return json.dumps(value, default=str)


class DatabaseServiceLite:
    """
    SQLite-backed database service for ZeroDB Local.

    Provides the same interface as the PostgreSQL DatabaseService,
    with SQLite-specific optimizations for local-first operation.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("ZERODB_LITE_DB_PATH", DEFAULT_DB_PATH)

        # Ensure the data directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            pathlib.Path(db_dir).mkdir(parents=True, exist_ok=True)

        database_url = f"sqlite:///{self.db_path}"

        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=bool(os.getenv("ZERODB_SQL_ECHO", "")),
        )

        # Enable WAL mode and foreign keys on every connection
        @event.listens_for(self.engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

        self.cdc = CDCService(self)

        # Initialize schema on first use
        self._init_schema()

    def _init_schema(self):
        """Apply the SQLite schema file to create tables if they do not exist."""
        with open(SCHEMA_FILE, "r") as f:
            schema_sql = f.read()

        with self.engine.connect() as conn:
            for statement in schema_sql.split(";"):
                stmt = statement.strip()
                if stmt and not stmt.upper().startswith("PRAGMA"):
                    try:
                        conn.execute(text(stmt))
                    except Exception:
                        pass
            conn.commit()

    def get_db(self) -> Generator[Session, None, None]:
        """
        Get database session.
        Use with FastAPI Depends for dependency injection.
        """
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def health_check(self) -> Dict[str, Any]:
        """
        Check SQLite database health.

        Returns:
            Health status dict
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

            file_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

            return {
                "status": "healthy",
                "message": "SQLite database connection successful",
                "backend": "sqlite",
                "db_path": self.db_path,
                "db_size_bytes": file_size,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "backend": "sqlite",
            }

    # ------------------------------------------------------------------
    # Project CRUD
    # ------------------------------------------------------------------

    def create_project(
        self,
        name: str,
        user_id: str,
        description: Optional[str] = None,
        organization_id: Optional[str] = None,
        settings: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Create a new project."""
        project_id = _generate_uuid()
        now = _now_iso()
        settings_json = _dump_json(settings or {})
        db_config = _dump_json({"vector_dimensions": 1536})

        with self.engine.connect() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO projects (id, name, description, user_id, organization_id,
                                          settings, database_config, created_at, updated_at)
                    VALUES (:id, :name, :description, :user_id, :organization_id,
                            :settings, :database_config, :created_at, :updated_at)
                    """
                ),
                {
                    "id": project_id,
                    "name": name,
                    "description": description,
                    "user_id": user_id,
                    "organization_id": organization_id,
                    "settings": settings_json,
                    "database_config": db_config,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            conn.commit()

        return self.get_project(project_id)

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a project by ID."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM projects WHERE id = :id AND deleted_at IS NULL"),
                {"id": project_id},
            )
            row = result.mappings().fetchone()

        if not row:
            return None

        return self._row_to_project(row)

    def list_projects(
        self,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List projects, optionally filtered by user_id."""
        query = "SELECT * FROM projects WHERE deleted_at IS NULL"
        params: Dict[str, Any] = {}

        if user_id:
            query += " AND user_id = :user_id"
            params["user_id"] = user_id

        query += " ORDER BY created_at DESC LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip

        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            rows = result.mappings().fetchall()

        return [self._row_to_project(r) for r in rows]

    def update_project(self, project_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a project. Pass field names as keyword arguments."""
        existing = self.get_project(project_id)
        if not existing:
            return None

        allowed = {"name", "description", "settings", "status", "tier"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}

        if not updates:
            return existing

        set_clauses = []
        params: Dict[str, Any] = {"id": project_id, "updated_at": _now_iso()}

        for key, value in updates.items():
            if key in ("settings",):
                params[key] = _dump_json(value)
            else:
                params[key] = value
            set_clauses.append(f"{key} = :{key}")

        set_clauses.append("updated_at = :updated_at")
        set_sql = ", ".join(set_clauses)

        with self.engine.connect() as conn:
            conn.execute(
                text(f"UPDATE projects SET {set_sql} WHERE id = :id AND deleted_at IS NULL"),
                params,
            )
            conn.commit()

        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> bool:
        """Soft-delete a project."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "UPDATE projects SET deleted_at = :now WHERE id = :id AND deleted_at IS NULL"
                ),
                {"id": project_id, "now": _now_iso()},
            )
            conn.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Table CRUD
    # ------------------------------------------------------------------

    def create_table(
        self,
        project_id: str,
        name: str,
        schema: Dict,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a NoSQL table definition."""
        table_id = _generate_uuid()
        now = _now_iso()

        with self.engine.connect() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO tables (id, project_id, name, schema, description,
                                        created_at, updated_at)
                    VALUES (:id, :project_id, :name, :schema, :description,
                            :created_at, :updated_at)
                    """
                ),
                {
                    "id": table_id,
                    "project_id": project_id,
                    "name": name,
                    "schema": _dump_json(schema),
                    "description": description,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            conn.commit()

        return self.get_table(project_id, name)

    def get_table(self, project_id: str, name: str) -> Optional[Dict[str, Any]]:
        """Get a table by project ID and name."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT * FROM tables
                    WHERE project_id = :project_id AND name = :name AND deleted_at IS NULL
                    """
                ),
                {"project_id": project_id, "name": name},
            )
            row = result.mappings().fetchone()

        if not row:
            return None

        return self._row_to_table(row)

    def get_table_by_id(self, table_id: str) -> Optional[Dict[str, Any]]:
        """Get a table by its ID."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM tables WHERE id = :id AND deleted_at IS NULL"),
                {"id": table_id},
            )
            row = result.mappings().fetchone()

        if not row:
            return None

        return self._row_to_table(row)

    def list_tables(
        self,
        project_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List tables for a project."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT * FROM tables
                    WHERE project_id = :project_id AND deleted_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :skip
                    """
                ),
                {"project_id": project_id, "limit": limit, "skip": skip},
            )
            rows = result.mappings().fetchall()

        return [self._row_to_table(r) for r in rows]

    def delete_table(self, project_id: str, name: str) -> bool:
        """Soft-delete a table by name."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE tables SET deleted_at = :now
                    WHERE project_id = :project_id AND name = :name AND deleted_at IS NULL
                    """
                ),
                {"project_id": project_id, "name": name, "now": _now_iso()},
            )
            conn.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Row CRUD
    # ------------------------------------------------------------------

    def insert_rows(
        self,
        project_id: str,
        table_name: str,
        rows: List[Dict],
    ) -> Dict[str, Any]:
        """Insert rows into a NoSQL table. Returns inserted count and IDs."""
        table = self.get_table(project_id, table_name)
        if not table:
            raise ValueError(f"Table '{table_name}' not found in project {project_id}")

        table_id = table["id"]
        inserted_ids = []
        now = _now_iso()

        with self.engine.connect() as conn:
            for row_data in rows:
                row_id = _generate_uuid()
                inserted_ids.append(row_id)

                conn.execute(
                    text(
                        """
                        INSERT INTO table_rows (id, table_id, project_id, data,
                                                created_at, updated_at)
                        VALUES (:id, :table_id, :project_id, :data,
                                :created_at, :updated_at)
                        """
                    ),
                    {
                        "id": row_id,
                        "table_id": table_id,
                        "project_id": project_id,
                        "data": _dump_json(row_data),
                        "created_at": now,
                        "updated_at": now,
                    },
                )

                # Application-level CDC
                self.cdc.log_change(
                    conn, project_id, "table_row", row_id, "INSERT", row_data
                )

            conn.commit()

        return {
            "inserted_count": len(inserted_ids),
            "inserted_ids": inserted_ids,
        }

    def query_rows(
        self,
        project_id: str,
        table_name: str,
        filter_dict: Optional[Dict] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query rows from a table, optionally filtered by JSON data fields."""
        table = self.get_table(project_id, table_name)
        if not table:
            raise ValueError(f"Table '{table_name}' not found in project {project_id}")

        table_id = table["id"]

        query = """
            SELECT * FROM table_rows
            WHERE table_id = :table_id AND project_id = :project_id AND deleted_at IS NULL
        """
        params: Dict[str, Any] = {
            "table_id": table_id,
            "project_id": project_id,
        }

        if filter_dict:
            for i, (key, value) in enumerate(filter_dict.items()):
                param_name = f"filter_{i}"
                query += f" AND json_extract(data, '$.{key}') = :{param_name}"
                if isinstance(value, bool):
                    params[param_name] = 1 if value else 0
                else:
                    params[param_name] = value

        query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            rows = result.mappings().fetchall()

        return [self._row_to_table_row(r) for r in rows]

    def update_rows(
        self,
        project_id: str,
        table_name: str,
        filter_dict: Dict,
        update_data: Dict,
    ) -> Dict[str, Any]:
        """Update rows matching a filter with new data fields."""
        table = self.get_table(project_id, table_name)
        if not table:
            raise ValueError(f"Table '{table_name}' not found in project {project_id}")

        table_id = table["id"]

        select_query = """
            SELECT id, data FROM table_rows
            WHERE table_id = :table_id AND project_id = :project_id AND deleted_at IS NULL
        """
        params: Dict[str, Any] = {
            "table_id": table_id,
            "project_id": project_id,
        }

        if filter_dict:
            for i, (key, value) in enumerate(filter_dict.items()):
                param_name = f"filter_{i}"
                select_query += f" AND json_extract(data, '$.{key}') = :{param_name}"
                if isinstance(value, bool):
                    params[param_name] = 1 if value else 0
                else:
                    params[param_name] = value

        now = _now_iso()
        updated_count = 0

        with self.engine.connect() as conn:
            result = conn.execute(text(select_query), params)
            matching_rows = result.mappings().fetchall()

            for row in matching_rows:
                existing_data = _parse_json(row["data"])
                if isinstance(existing_data, dict):
                    existing_data.update(update_data)
                else:
                    existing_data = update_data

                conn.execute(
                    text(
                        """
                        UPDATE table_rows
                        SET data = :data, updated_at = :updated_at
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": row["id"],
                        "data": _dump_json(existing_data),
                        "updated_at": now,
                    },
                )

                self.cdc.log_change(
                    conn, project_id, "table_row", row["id"], "UPDATE", existing_data
                )
                updated_count += 1

            conn.commit()

        return {"updated_count": updated_count}

    def delete_rows(
        self,
        project_id: str,
        table_name: str,
        filter_dict: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Soft-delete rows matching a filter."""
        table = self.get_table(project_id, table_name)
        if not table:
            raise ValueError(f"Table '{table_name}' not found in project {project_id}")

        table_id = table["id"]

        select_query = """
            SELECT id, data FROM table_rows
            WHERE table_id = :table_id AND project_id = :project_id AND deleted_at IS NULL
        """
        params: Dict[str, Any] = {
            "table_id": table_id,
            "project_id": project_id,
        }

        if filter_dict:
            for i, (key, value) in enumerate(filter_dict.items()):
                param_name = f"filter_{i}"
                select_query += f" AND json_extract(data, '$.{key}') = :{param_name}"
                if isinstance(value, bool):
                    params[param_name] = 1 if value else 0
                else:
                    params[param_name] = value

        now = _now_iso()
        deleted_count = 0

        with self.engine.connect() as conn:
            result = conn.execute(text(select_query), params)
            matching_rows = result.mappings().fetchall()

            for row in matching_rows:
                conn.execute(
                    text(
                        "UPDATE table_rows SET deleted_at = :now WHERE id = :id"
                    ),
                    {"id": row["id"], "now": now},
                )

                self.cdc.log_change(
                    conn,
                    project_id,
                    "table_row",
                    row["id"],
                    "DELETE",
                    _parse_json(row["data"]),
                )
                deleted_count += 1

            conn.commit()

        return {"deleted_count": deleted_count}

    # ------------------------------------------------------------------
    # Project Stats
    # ------------------------------------------------------------------

    def get_project_stats(self, project_id: str) -> Dict[str, int]:
        """Get counts of all entity types for a project."""
        with self.engine.connect() as conn:
            counts = {}
            for entity, tbl in [
                ("vector_count", "vectors"),
                ("memory_count", "memory"),
                ("table_count", "tables"),
                ("file_count", "files"),
                ("event_count", "events"),
            ]:
                if tbl in ("tables", "files"):
                    q = f"SELECT COUNT(*) as cnt FROM {tbl} WHERE project_id = :pid AND deleted_at IS NULL"
                else:
                    q = f"SELECT COUNT(*) as cnt FROM {tbl} WHERE project_id = :pid"

                result = conn.execute(text(q), {"pid": project_id})
                counts[entity] = result.scalar() or 0

        return counts

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_project(row) -> Dict[str, Any]:
        """Convert a database row to a project dict."""
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "user_id": row["user_id"],
            "organization_id": row["organization_id"],
            "tier": row["tier"],
            "status": row["status"],
            "database_enabled": bool(row["database_enabled"]),
            "database_config": _parse_json(row["database_config"]),
            "vector_dimensions": row["vector_dimensions"],
            "quantum_enabled": bool(row["quantum_enabled"]),
            "mcp_enabled": bool(row["mcp_enabled"]),
            "settings": _parse_json(row["settings"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _row_to_table(row) -> Dict[str, Any]:
        """Convert a database row to a table dict."""
        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "name": row["name"],
            "schema": _parse_json(row["schema"]),
            "description": row["description"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _row_to_table_row(row) -> Dict[str, Any]:
        """Convert a database row to a table_row dict."""
        return {
            "id": row["id"],
            "table_id": row["table_id"],
            "project_id": row["project_id"],
            "data": _parse_json(row["data"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


def get_database_service() -> DatabaseServiceLite:
    """
    Factory function for the database service.
    Checks ZERODB_BACKEND env var to decide which backend to use.
    """
    backend = os.getenv("ZERODB_BACKEND", "postgres")
    if backend == "lite":
        return DatabaseServiceLite()
    else:
        from api.services.database_service import DatabaseService
        return DatabaseService()
