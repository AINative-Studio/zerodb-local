-- Migration: 004_sync_history
-- Description: Add sync history and audit logging tables
-- Created: 2025-12-29
-- Dependencies: 002_sync_state.sql

\echo 'Running migration 004_sync_history...'

-- ==========================================
-- UP MIGRATION
-- ==========================================

-- Sync history table for audit trail
CREATE TABLE IF NOT EXISTS sync_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sync_id UUID NOT NULL UNIQUE,

    -- Sync configuration
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('push', 'pull', 'bidirectional')),
    mode VARCHAR(20) NOT NULL CHECK (mode IN ('full', 'incremental', 'selective')),

    -- Status and timing
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'rolled_back')),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds NUMERIC(10, 3) GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (completed_at - started_at))
    ) STORED,

    -- Sync results
    records_synced JSONB NOT NULL DEFAULT '{}'::jsonb,
    bytes_transferred BIGINT DEFAULT 0,

    -- Error handling
    error_message TEXT,
    error_stack TEXT,

    -- Rollback support
    snapshot_id UUID,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX idx_sync_history_project_id ON sync_history(project_id);
CREATE INDEX idx_sync_history_status ON sync_history(status);
CREATE INDEX idx_sync_history_started_at ON sync_history(started_at DESC);
CREATE INDEX idx_sync_history_project_started ON sync_history(project_id, started_at DESC);
CREATE INDEX idx_sync_history_sync_id ON sync_history(sync_id);

-- GIN index for records_synced JSONB queries
CREATE INDEX idx_sync_history_records_synced ON sync_history USING GIN(records_synced);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_sync_history_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_history_update_trigger
    BEFORE UPDATE ON sync_history
    FOR EACH ROW EXECUTE FUNCTION update_sync_history_timestamp();

-- Add comments for documentation
COMMENT ON TABLE sync_history IS 'Audit trail for all sync operations';
COMMENT ON COLUMN sync_history.sync_id IS 'Unique identifier for this sync operation';
COMMENT ON COLUMN sync_history.direction IS 'Sync direction: push (local→cloud), pull (cloud→local), bidirectional';
COMMENT ON COLUMN sync_history.mode IS 'Sync mode: full (all data), incremental (changes only), selective (specific entities)';
COMMENT ON COLUMN sync_history.records_synced IS 'Per-entity-type record counts as JSON: {"vectors": 500, "tables": 150}';
COMMENT ON COLUMN sync_history.bytes_transferred IS 'Total bytes transferred during sync';
COMMENT ON COLUMN sync_history.snapshot_id IS 'Snapshot ID for rollback capability';
COMMENT ON COLUMN sync_history.duration_seconds IS 'Computed sync duration in seconds';

\echo 'Created sync_history table with indexes and triggers'

-- ==========================================
-- EXAMPLE USAGE
-- ==========================================
-- Insert a sync history record:
/*
INSERT INTO sync_history (project_id, sync_id, direction, mode, status)
VALUES (
    '123e4567-e89b-12d3-a456-426614174000',
    '987fcdeb-51a2-43f7-8b9a-9c8d7e6f5a4b',
    'push',
    'incremental',
    'running'
);

-- Update with completion details:
UPDATE sync_history
SET status = 'completed',
    completed_at = NOW(),
    records_synced = '{"vectors": 500, "tables": 150, "events": 50}'::jsonb,
    bytes_transferred = 5242880
WHERE sync_id = '987fcdeb-51a2-43f7-8b9a-9c8d7e6f5a4b';
*/

\echo 'Migration 004_sync_history completed successfully!'

-- ==========================================
-- DOWN MIGRATION (for rollback)
-- ==========================================
-- Uncomment to rollback this migration:
/*
DROP TRIGGER IF EXISTS sync_history_update_trigger ON sync_history;
DROP FUNCTION IF EXISTS update_sync_history_timestamp();
DROP INDEX IF EXISTS idx_sync_history_records_synced;
DROP INDEX IF EXISTS idx_sync_history_project_started;
DROP INDEX IF EXISTS idx_sync_history_started_at;
DROP INDEX IF EXISTS idx_sync_history_status;
DROP INDEX IF EXISTS idx_sync_history_project_id;
DROP INDEX IF EXISTS idx_sync_history_sync_id;
DROP TABLE IF EXISTS sync_history;

\echo 'Migration 004_sync_history rolled back'
*/
