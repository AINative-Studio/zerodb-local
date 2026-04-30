-- ZeroDB Lite Database Schema
-- SQLite-compatible version of the PostgreSQL schema
-- Refs #1706: SQLite backend for database_service.py

-- Enable WAL mode for better concurrent read performance
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ==========================================
-- PROJECTS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK(length(name) > 0),
    description TEXT,
    user_id TEXT NOT NULL,
    organization_id TEXT,
    tier TEXT DEFAULT 'free',
    status TEXT DEFAULT 'ACTIVE',
    database_enabled INTEGER DEFAULT 1,
    database_config TEXT DEFAULT '{"vector_dimensions": 1536}',
    vector_dimensions INTEGER DEFAULT 1536,
    quantum_enabled INTEGER DEFAULT 0,
    mcp_enabled INTEGER DEFAULT 0,
    railway_project_id TEXT,
    settings TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_projects_org_id ON projects(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);

-- ==========================================
-- VECTORS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS vectors (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    namespace TEXT DEFAULT 'default',
    vector_id TEXT,
    embedding BLOB,
    document TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (project_id, namespace, vector_id)
);

CREATE INDEX IF NOT EXISTS idx_vectors_project_id ON vectors(project_id);
CREATE INDEX IF NOT EXISTS idx_vectors_project_namespace ON vectors(project_id, namespace);
CREATE INDEX IF NOT EXISTS idx_vectors_created_at ON vectors(project_id, created_at DESC);

-- ==========================================
-- MEMORY TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS memory (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    session_id TEXT,
    agent_id TEXT,
    role TEXT CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    embedding BLOB,
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_memory_project_id ON memory(project_id);
CREATE INDEX IF NOT EXISTS idx_memory_session_id ON memory(project_id, session_id);
CREATE INDEX IF NOT EXISTS idx_memory_agent_id ON memory(project_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_memory_created_at ON memory(project_id, created_at DESC);

-- ==========================================
-- TABLES (NoSQL Tables)
-- ==========================================
CREATE TABLE IF NOT EXISTS tables (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    schema TEXT NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TEXT,
    UNIQUE (project_id, name)
);

CREATE INDEX IF NOT EXISTS idx_tables_project_id ON tables(project_id) WHERE deleted_at IS NULL;

-- ==========================================
-- TABLE ROWS (Dynamic NoSQL Data)
-- ==========================================
CREATE TABLE IF NOT EXISTS table_rows (
    id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_table_rows_table_id ON table_rows(table_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_table_rows_project_id ON table_rows(project_id) WHERE deleted_at IS NULL;

-- ==========================================
-- FILES TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content_type TEXT,
    file_size INTEGER,
    folder TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_files_project_id ON files(project_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_files_folder ON files(project_id, folder) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(project_id, created_at DESC);

-- ==========================================
-- EVENTS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK(length(event_type) > 0),
    source TEXT,
    correlation_id TEXT,
    event_data TEXT NOT NULL,
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_events_project_id ON events(project_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(project_id, event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(project_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_correlation_id ON events(correlation_id) WHERE correlation_id IS NOT NULL;

-- ==========================================
-- SYNC STATE TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS sync_state (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    last_sync_at TEXT,
    last_cloud_export_id TEXT,
    last_cloud_import_id TEXT,
    watermark TEXT,
    sync_strategy TEXT DEFAULT 'full' CHECK(sync_strategy IN ('full', 'incremental', 'selective')),
    sync_direction TEXT DEFAULT 'bidirectional' CHECK(sync_direction IN ('push', 'pull', 'bidirectional')),
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (project_id, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_sync_state_project_id ON sync_state(project_id);

-- ==========================================
-- CHANGE LOG TABLE (application-level CDC)
-- ==========================================
CREATE TABLE IF NOT EXISTS change_log (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL CHECK(operation IN ('INSERT', 'UPDATE', 'DELETE')),
    data TEXT,
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    synced INTEGER DEFAULT 0,
    synced_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_change_log_project_id ON change_log(project_id);
CREATE INDEX IF NOT EXISTS idx_change_log_entity ON change_log(project_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_change_log_timestamp ON change_log(project_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_change_log_synced ON change_log(project_id, synced) WHERE synced = 0;

-- ==========================================
-- SYNC HISTORY TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS sync_history (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sync_direction TEXT NOT NULL CHECK(sync_direction IN ('push', 'pull')),
    sync_mode TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'completed', 'failed')),
    records_synced INTEGER DEFAULT 0,
    errors TEXT,
    started_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sync_history_project_id ON sync_history(project_id);
CREATE INDEX IF NOT EXISTS idx_sync_history_started_at ON sync_history(project_id, started_at DESC);

-- ==========================================
-- CONFLICT LOG TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS conflict_log (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    local_value TEXT,
    cloud_value TEXT,
    local_timestamp TEXT,
    cloud_timestamp TEXT,
    resolution_strategy TEXT,
    resolved_value TEXT,
    resolved_at TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_conflict_log_project_id ON conflict_log(project_id);
CREATE INDEX IF NOT EXISTS idx_conflict_log_entity ON conflict_log(project_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_conflict_log_created_at ON conflict_log(project_id, created_at DESC);
