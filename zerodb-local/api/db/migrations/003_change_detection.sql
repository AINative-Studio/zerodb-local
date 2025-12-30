-- Migration: 003_change_detection
-- Description: Add missing CDC triggers for files, events, and memory tables
-- Created: 2025-12-29
-- Dependencies: 001_initial_schema.sql

-- This migration adds Change Data Capture triggers for:
-- - files table
-- - events table
-- - memory table
-- (vectors and table_rows already have triggers from 001_initial_schema.sql)

\echo 'Running migration 003_change_detection...'

-- ==========================================
-- UP MIGRATION
-- ==========================================

-- CDC trigger for files table
CREATE OR REPLACE FUNCTION log_file_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO change_log (project_id, entity_type, entity_id, operation, data)
        VALUES (OLD.project_id, 'file', OLD.id, 'DELETE', row_to_json(OLD)::jsonb);
        RETURN OLD;
    ELSE
        INSERT INTO change_log (project_id, entity_type, entity_id, operation, data)
        VALUES (NEW.project_id, 'file', NEW.id, TG_OP, row_to_json(NEW)::jsonb);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER file_change_trigger
    AFTER INSERT OR UPDATE OR DELETE ON files
    FOR EACH ROW EXECUTE FUNCTION log_file_change();

\echo 'Created CDC trigger for files table'

-- CDC trigger for events table
CREATE OR REPLACE FUNCTION log_event_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO change_log (project_id, entity_type, entity_id, operation, data)
        VALUES (OLD.project_id, 'event', OLD.id, 'DELETE', row_to_json(OLD)::jsonb);
        RETURN OLD;
    ELSE
        INSERT INTO change_log (project_id, entity_type, entity_id, operation, data)
        VALUES (NEW.project_id, 'event', NEW.id, TG_OP, row_to_json(NEW)::jsonb);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER event_change_trigger
    AFTER INSERT OR UPDATE OR DELETE ON events
    FOR EACH ROW EXECUTE FUNCTION log_event_change();

\echo 'Created CDC trigger for events table'

-- CDC trigger for memory table
CREATE OR REPLACE FUNCTION log_memory_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO change_log (project_id, entity_type, entity_id, operation, data)
        VALUES (OLD.project_id, 'memory', OLD.id, 'DELETE', row_to_json(OLD)::jsonb);
        RETURN OLD;
    ELSE
        INSERT INTO change_log (project_id, entity_type, entity_id, operation, data)
        VALUES (NEW.project_id, 'memory', NEW.id, TG_OP, row_to_json(NEW)::jsonb);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER memory_change_trigger
    AFTER INSERT OR UPDATE OR DELETE ON memory
    FOR EACH ROW EXECUTE FUNCTION log_memory_change();

\echo 'Created CDC trigger for memory table'

-- Add comments
COMMENT ON FUNCTION log_file_change() IS 'CDC trigger function for files table';
COMMENT ON FUNCTION log_event_change() IS 'CDC trigger function for events table';
COMMENT ON FUNCTION log_memory_change() IS 'CDC trigger function for memory table';

\echo 'Migration 003_change_detection completed successfully!'

-- ==========================================
-- DOWN MIGRATION (for rollback)
-- ==========================================
-- Uncomment to rollback this migration:
/*
DROP TRIGGER IF EXISTS memory_change_trigger ON memory;
DROP TRIGGER IF EXISTS event_change_trigger ON events;
DROP TRIGGER IF EXISTS file_change_trigger ON files;

DROP FUNCTION IF EXISTS log_memory_change();
DROP FUNCTION IF EXISTS log_event_change();
DROP FUNCTION IF EXISTS log_file_change();

\echo 'Migration 003_change_detection rolled back'
*/
