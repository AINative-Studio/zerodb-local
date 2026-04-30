-- Migration: 004_conflict_log
-- Description: Create conflict_log table for tracking conflict resolutions during sync
-- Dependencies: Requires projects table (from core schema)
-- Story: #439 - Conflict Resolution Engine

CREATE TABLE IF NOT EXISTS conflict_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,

    -- Entity identification
    entity_type VARCHAR(50) NOT NULL,  -- 'vector', 'table_row', 'memory', 'event', 'file'
    entity_id VARCHAR(512) NOT NULL,

    -- Conflict details
    local_version JSONB NOT NULL,      -- Local version of data
    cloud_version JSONB NOT NULL,      -- Cloud version of data

    -- Resolution details
    resolution_strategy VARCHAR(50) NOT NULL,  -- 'local_wins', 'cloud_wins', 'newest_wins', 'manual'
    chosen_version JSONB NOT NULL,     -- The version that was chosen after resolution

    -- Timestamps
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Optional metadata and notes
    conflict_metadata JSONB DEFAULT '{}',
    notes TEXT,

    -- Indexes for common queries
    CONSTRAINT fk_conflict_log_project FOREIGN KEY (project_id)
        REFERENCES projects(id) ON DELETE CASCADE
);

-- Index for querying conflicts by project
CREATE INDEX IF NOT EXISTS idx_conflict_log_project_id ON conflict_log(project_id);

-- Index for sorting by resolution time
CREATE INDEX IF NOT EXISTS idx_conflict_log_resolved_at ON conflict_log(resolved_at);

-- Index for querying by entity type
CREATE INDEX IF NOT EXISTS idx_conflict_log_entity_type ON conflict_log(project_id, entity_type);

-- Index for finding conflicts for specific entities
CREATE INDEX IF NOT EXISTS idx_conflict_log_entity ON conflict_log(project_id, entity_type, entity_id);

-- Add comment for documentation
COMMENT ON TABLE conflict_log IS 'Tracks conflicts detected during sync operations and their resolutions';
COMMENT ON COLUMN conflict_log.entity_type IS 'Type of entity that had a conflict: vector, table_row, memory, event, file';
COMMENT ON COLUMN conflict_log.resolution_strategy IS 'Strategy used to resolve: local_wins, cloud_wins, newest_wins, manual';
COMMENT ON COLUMN conflict_log.local_version IS 'Local version of the entity data at time of conflict';
COMMENT ON COLUMN conflict_log.cloud_version IS 'Cloud version of the entity data at time of conflict';
COMMENT ON COLUMN conflict_log.chosen_version IS 'The version that was selected after applying resolution strategy';
