-- Migration 002: Sync State Tracking
-- Adds support for tracking synchronization state between local and cloud

-- Note: The sync_state table already exists in the main schema.sql
-- This migration file serves as documentation and can be used for
-- incremental deployments where the main schema hasn't been applied yet.

-- ==========================================
-- SYNC STATE TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS sync_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,  -- 'vectors', 'tables', 'memory', 'files', 'events'
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_cloud_export_id UUID,
    last_cloud_import_id UUID,
    watermark JSONB,  -- CDC offsets, event positions, etc.
    sync_strategy VARCHAR(50) DEFAULT 'full' NOT NULL,  -- 'full', 'incremental', 'selective'
    sync_direction VARCHAR(20) DEFAULT 'bidirectional' NOT NULL,  -- 'push', 'pull', 'bidirectional'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    CONSTRAINT sync_state_project_entity_unique UNIQUE (project_id, entity_type),
    CONSTRAINT sync_state_strategy_check CHECK (sync_strategy IN ('full', 'incremental', 'selective')),
    CONSTRAINT sync_state_direction_check CHECK (sync_direction IN ('push', 'pull', 'bidirectional'))
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_sync_state_project_id ON sync_state(project_id);
CREATE INDEX IF NOT EXISTS idx_sync_state_entity_type ON sync_state(entity_type);
CREATE INDEX IF NOT EXISTS idx_sync_state_last_sync ON sync_state(last_sync_at DESC) WHERE last_sync_at IS NOT NULL;

-- Add updated_at trigger if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'sync_state_updated_at'
    ) THEN
        CREATE TRIGGER sync_state_updated_at
            BEFORE UPDATE ON sync_state
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END$$;

-- Add comment
COMMENT ON TABLE sync_state IS 'Tracks synchronization state between local and cloud for each entity type per project';
COMMENT ON COLUMN sync_state.watermark IS 'Stores incremental sync markers like last_id, last_timestamp, CDC offsets, etc.';
COMMENT ON COLUMN sync_state.sync_strategy IS 'Determines sync approach: full (complete resync), incremental (delta sync), or selective (filtered sync)';
COMMENT ON COLUMN sync_state.sync_direction IS 'Controls sync flow: push (local to cloud), pull (cloud to local), or bidirectional (both ways)';
