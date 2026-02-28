-- Migration: Add schema_comparisons and sync_plans tables
-- Issue: #1249 - Implement schema diff caching and sync plan persistence
-- Date: 2026-02-27

-- Create schema_comparisons table for caching schema comparison results
CREATE TABLE IF NOT EXISTS schema_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Schema snapshots as JSONB
    local_schema JSONB NOT NULL,
    cloud_schema JSONB NOT NULL,

    -- Comparison results
    diff_result JSONB NOT NULL,
    total_changes INTEGER NOT NULL DEFAULT 0,
    has_breaking_changes BOOLEAN NOT NULL DEFAULT FALSE,
    breaking_changes_count INTEGER NOT NULL DEFAULT 0,

    -- Optional migration plan
    migration_plan JSONB,

    -- Summary
    comparison_summary TEXT,

    -- Timestamps
    compared_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Indexes
    CONSTRAINT schema_comparisons_project_id_fkey FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Indexes for schema_comparisons
CREATE INDEX IF NOT EXISTS idx_schema_comparisons_project_id ON schema_comparisons(project_id);
CREATE INDEX IF NOT EXISTS idx_schema_comparisons_compared_at ON schema_comparisons(compared_at);
CREATE INDEX IF NOT EXISTS idx_schema_comparisons_expires_at ON schema_comparisons(expires_at);
CREATE INDEX IF NOT EXISTS idx_schema_comparisons_breaking ON schema_comparisons(project_id, has_breaking_changes);

-- Create sync_plans table for storing generated sync plans
CREATE TABLE IF NOT EXISTS sync_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Plan metadata
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('push', 'pull')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'approved', 'executing', 'completed', 'failed', 'expired')
    ),

    -- Sync steps and entity counts stored as JSONB
    steps JSONB NOT NULL,
    total_steps INTEGER NOT NULL DEFAULT 0,
    entity_counts JSONB NOT NULL,

    -- Estimates
    estimated_duration_seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    estimated_data_size_bytes BIGINT NOT NULL DEFAULT 0,

    -- Schema changes and conflicts
    schema_changes JSONB NOT NULL,
    conflicts JSONB NOT NULL,

    -- Warnings and flags
    warnings TEXT[],
    requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
    can_rollback BOOLEAN NOT NULL DEFAULT TRUE,

    -- Approval tracking
    approved_by VARCHAR(255),
    approved_at TIMESTAMP,

    -- Execution tracking
    executed_at TIMESTAMP,
    completed_at TIMESTAMP,
    sync_result_id UUID,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP,

    -- Constraints
    CONSTRAINT sync_plans_project_id_fkey FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Indexes for sync_plans
CREATE INDEX IF NOT EXISTS idx_sync_plans_plan_id ON sync_plans(plan_id);
CREATE INDEX IF NOT EXISTS idx_sync_plans_project_id ON sync_plans(project_id);
CREATE INDEX IF NOT EXISTS idx_sync_plans_status ON sync_plans(status);
CREATE INDEX IF NOT EXISTS idx_sync_plans_created_at ON sync_plans(created_at);
CREATE INDEX IF NOT EXISTS idx_sync_plans_expires_at ON sync_plans(expires_at);
CREATE INDEX IF NOT EXISTS idx_sync_plans_project_status ON sync_plans(project_id, status);

-- Add comments for documentation
COMMENT ON TABLE schema_comparisons IS 'Caches schema comparison results between local and cloud schemas';
COMMENT ON TABLE sync_plans IS 'Stores generated sync plans for later execution and tracking';

COMMENT ON COLUMN schema_comparisons.diff_result IS 'Complete SchemaDiff object stored as JSON';
COMMENT ON COLUMN schema_comparisons.expires_at IS 'Expiration time for cache invalidation (typically 24 hours)';

COMMENT ON COLUMN sync_plans.steps IS 'Array of SyncStep objects as JSON';
COMMENT ON COLUMN sync_plans.entity_counts IS 'EntityCount object as JSON with counts per entity type';
COMMENT ON COLUMN sync_plans.schema_changes IS 'SchemaChangeInfo object as JSON';
COMMENT ON COLUMN sync_plans.conflicts IS 'ConflictInfo object as JSON';
COMMENT ON COLUMN sync_plans.expires_at IS 'Expiration time for plan (typically 24 hours after creation)';
COMMENT ON COLUMN sync_plans.sync_result_id IS 'Link to sync_history entry if plan was executed';
