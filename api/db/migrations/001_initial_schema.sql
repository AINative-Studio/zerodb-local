-- Migration: 001_initial_schema
-- Description: Create initial database schema for ZeroDB Local
-- Created: 2025-12-28
-- Dependencies: None

-- This migration creates all base tables, indexes, and triggers for ZeroDB Local

\echo 'Running migration 001_initial_schema...'

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\echo 'Extensions enabled: vector, uuid-ossp'

-- ==========================================
-- UP MIGRATION
-- ==========================================

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    user_id UUID NOT NULL,
    organization_id UUID,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT projects_name_check CHECK (char_length(name) > 0)
);

CREATE INDEX idx_projects_user_id ON projects(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_projects_org_id ON projects(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

\echo 'Created table: projects'

-- Vectors table
CREATE TABLE IF NOT EXISTS vectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    namespace VARCHAR(255) DEFAULT 'default',
    vector_id VARCHAR(512),
    embedding vector(1536),
    document TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT vectors_project_namespace_vector_id_unique UNIQUE (project_id, namespace, vector_id)
);

CREATE INDEX idx_vectors_project_id ON vectors(project_id);
CREATE INDEX idx_vectors_project_namespace ON vectors(project_id, namespace);
CREATE INDEX idx_vectors_embedding ON vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_vectors_metadata ON vectors USING gin(metadata);
CREATE INDEX idx_vectors_created_at ON vectors(project_id, created_at DESC);

\echo 'Created table: vectors'

-- Memory table
CREATE TABLE IF NOT EXISTS memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    session_id VARCHAR(255),
    agent_id VARCHAR(255),
    role VARCHAR(50),
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT memory_role_check CHECK (role IN ('user', 'assistant', 'system'))
);

CREATE INDEX idx_memory_project_id ON memory(project_id);
CREATE INDEX idx_memory_session_id ON memory(project_id, session_id);
CREATE INDEX idx_memory_agent_id ON memory(project_id, agent_id);
CREATE INDEX idx_memory_embedding ON memory USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_memory_created_at ON memory(project_id, created_at DESC);

\echo 'Created table: memory'

-- Tables (NoSQL schemas)
CREATE TABLE IF NOT EXISTS tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    schema JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT tables_project_name_unique UNIQUE (project_id, name)
);

CREATE INDEX idx_tables_project_id ON tables(project_id) WHERE deleted_at IS NULL;

\echo 'Created table: tables'

-- Table rows (NoSQL data)
CREATE TABLE IF NOT EXISTS table_rows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id UUID NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_table_rows_table_id ON table_rows(table_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_table_rows_project_id ON table_rows(project_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_table_rows_data ON table_rows USING gin(data);

\echo 'Created table: table_rows'

-- Files table
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_name VARCHAR(512) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    content_type VARCHAR(255),
    file_size BIGINT,
    folder VARCHAR(512),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_files_project_id ON files(project_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_files_folder ON files(project_id, folder) WHERE deleted_at IS NULL;
CREATE INDEX idx_files_created_at ON files(project_id, created_at DESC);

\echo 'Created table: files'

-- Events table
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    source VARCHAR(255),
    correlation_id UUID,
    event_data JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT events_event_type_check CHECK (char_length(event_type) > 0)
);

CREATE INDEX idx_events_project_id ON events(project_id);
CREATE INDEX idx_events_event_type ON events(project_id, event_type);
CREATE INDEX idx_events_timestamp ON events(project_id, timestamp DESC);
CREATE INDEX idx_events_correlation_id ON events(correlation_id) WHERE correlation_id IS NOT NULL;

\echo 'Created table: events'

-- Sync state table
CREATE TABLE IF NOT EXISTS sync_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_cloud_export_id UUID,
    last_cloud_import_id UUID,
    watermark JSONB,
    sync_strategy VARCHAR(50) DEFAULT 'full',
    sync_direction VARCHAR(20) DEFAULT 'bidirectional',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT sync_state_project_entity_unique UNIQUE (project_id, entity_type),
    CONSTRAINT sync_state_strategy_check CHECK (sync_strategy IN ('full', 'incremental', 'selective')),
    CONSTRAINT sync_state_direction_check CHECK (sync_direction IN ('push', 'pull', 'bidirectional'))
);

CREATE INDEX idx_sync_state_project_id ON sync_state(project_id);

\echo 'Created table: sync_state'

-- Change log table
CREATE TABLE IF NOT EXISTS change_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    operation VARCHAR(10) NOT NULL,
    data JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    synced BOOLEAN DEFAULT FALSE,
    CONSTRAINT change_log_operation_check CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX idx_change_log_project_id ON change_log(project_id);
CREATE INDEX idx_change_log_entity ON change_log(project_id, entity_type, entity_id);
CREATE INDEX idx_change_log_timestamp ON change_log(project_id, timestamp DESC);
CREATE INDEX idx_change_log_synced ON change_log(project_id, synced) WHERE synced = FALSE;

\echo 'Created table: change_log'

-- Sync history table
CREATE TABLE IF NOT EXISTS sync_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sync_direction VARCHAR(20) NOT NULL,
    sync_mode VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    records_synced INTEGER DEFAULT 0,
    errors JSONB,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT sync_history_direction_check CHECK (sync_direction IN ('push', 'pull')),
    CONSTRAINT sync_history_status_check CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE INDEX idx_sync_history_project_id ON sync_history(project_id);
CREATE INDEX idx_sync_history_started_at ON sync_history(project_id, started_at DESC);

\echo 'Created table: sync_history'

-- Conflict log table
CREATE TABLE IF NOT EXISTS conflict_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    local_value JSONB,
    cloud_value JSONB,
    local_timestamp TIMESTAMP WITH TIME ZONE,
    cloud_timestamp TIMESTAMP WITH TIME ZONE,
    resolution_strategy VARCHAR(50),
    resolved_value JSONB,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_conflict_log_project_id ON conflict_log(project_id);
CREATE INDEX idx_conflict_log_entity ON conflict_log(project_id, entity_type, entity_id);
CREATE INDEX idx_conflict_log_created_at ON conflict_log(project_id, created_at DESC);

\echo 'Created table: conflict_log'

-- Create trigger function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER vectors_updated_at BEFORE UPDATE ON vectors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER tables_updated_at BEFORE UPDATE ON tables
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER table_rows_updated_at BEFORE UPDATE ON table_rows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER files_updated_at BEFORE UPDATE ON files
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER sync_state_updated_at BEFORE UPDATE ON sync_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

\echo 'Created updated_at triggers'

-- Create change log trigger functions
CREATE OR REPLACE FUNCTION log_vector_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO change_log (project_id, entity_type, entity_id, operation, data)
        VALUES (OLD.project_id, 'vector', OLD.id, 'DELETE', row_to_json(OLD)::jsonb);
        RETURN OLD;
    ELSE
        INSERT INTO change_log (project_id, entity_type, entity_id, operation, data)
        VALUES (NEW.project_id, 'vector', NEW.id, TG_OP, row_to_json(NEW)::jsonb);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER vector_change_trigger
    AFTER INSERT OR UPDATE OR DELETE ON vectors
    FOR EACH ROW EXECUTE FUNCTION log_vector_change();

CREATE OR REPLACE FUNCTION log_table_row_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO change_log (project_id, entity_type, entity_id, operation, data)
        VALUES (OLD.project_id, 'table_row', OLD.id, 'DELETE', row_to_json(OLD)::jsonb);
        RETURN OLD;
    ELSE
        INSERT INTO change_log (project_id, entity_type, entity_id, operation, data)
        VALUES (NEW.project_id, 'table_row', NEW.id, TG_OP, row_to_json(NEW)::jsonb);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER table_row_change_trigger
    AFTER INSERT OR UPDATE OR DELETE ON table_rows
    FOR EACH ROW EXECUTE FUNCTION log_table_row_change();

\echo 'Created change log triggers'

-- Add comments
COMMENT ON TABLE projects IS 'ZeroDB projects - top-level container for all data';
COMMENT ON TABLE vectors IS 'Vector embeddings with metadata for semantic search';
COMMENT ON TABLE memory IS 'Agent memory records for conversational AI';
COMMENT ON TABLE tables IS 'Dynamic NoSQL table schemas';
COMMENT ON TABLE table_rows IS 'NoSQL table data stored as JSONB';
COMMENT ON TABLE files IS 'File metadata (files stored in MinIO)';
COMMENT ON TABLE events IS 'Event stream records (events also in RedPanda)';
COMMENT ON TABLE sync_state IS 'Tracks sync state between local and cloud';
COMMENT ON TABLE change_log IS 'Change data capture log for incremental sync';
COMMENT ON TABLE sync_history IS 'Audit log of sync operations';
COMMENT ON TABLE conflict_log IS 'Conflict resolution history';

\echo 'Migration 001_initial_schema completed successfully!'

-- ==========================================
-- DOWN MIGRATION (for rollback)
-- ==========================================
-- Uncomment to rollback this migration:
/*
DROP TRIGGER IF EXISTS table_row_change_trigger ON table_rows;
DROP TRIGGER IF EXISTS vector_change_trigger ON vectors;
DROP TRIGGER IF EXISTS sync_state_updated_at ON sync_state;
DROP TRIGGER IF EXISTS files_updated_at ON files;
DROP TRIGGER IF EXISTS table_rows_updated_at ON table_rows;
DROP TRIGGER IF EXISTS tables_updated_at ON tables;
DROP TRIGGER IF EXISTS vectors_updated_at ON vectors;
DROP TRIGGER IF EXISTS projects_updated_at ON projects;

DROP FUNCTION IF EXISTS log_table_row_change();
DROP FUNCTION IF EXISTS log_vector_change();
DROP FUNCTION IF EXISTS update_updated_at_column();

DROP TABLE IF EXISTS conflict_log CASCADE;
DROP TABLE IF EXISTS sync_history CASCADE;
DROP TABLE IF EXISTS change_log CASCADE;
DROP TABLE IF EXISTS sync_state CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS files CASCADE;
DROP TABLE IF EXISTS table_rows CASCADE;
DROP TABLE IF EXISTS tables CASCADE;
DROP TABLE IF EXISTS memory CASCADE;
DROP TABLE IF EXISTS vectors CASCADE;
DROP TABLE IF EXISTS projects CASCADE;

DROP EXTENSION IF EXISTS "uuid-ossp";
DROP EXTENSION IF EXISTS vector;

\echo 'Migration 001_initial_schema rolled back'
*/
