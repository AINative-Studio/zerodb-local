-- Migration 005: add columns to projects that 001_initial_schema.sql omitted
-- but schema.sql (and the application code in routers/projects.py) expect.
--
-- Root cause: init.sh runs 001_initial_schema.sql directly, then Postgres's
-- docker-entrypoint-initdb.d convention also auto-runs schema.sql (any .sql
-- file in that directory runs alphabetically) as a *second*, independent
-- pass. Because the projects table (and its indexes) already exist by then,
-- schema.sql's "CREATE TABLE IF NOT EXISTS projects (...)" silently no-ops
-- instead of adding the columns 001 was missing, and its very next statement
-- ("CREATE INDEX idx_projects_user_id ...", no IF NOT EXISTS) hard-fails on
-- the duplicate index — aborting schema.sql entirely, including every
-- CREATE TABLE statement after that point in the file. See issue filed on
-- AINative-Studio/zerodb-local for the real fix (idempotent schema.sql /
-- init.sh no longer double-applying). This migration repairs projects on an
-- already-initialized database without requiring a fresh volume.

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS tier VARCHAR(20) DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ACTIVE',
    ADD COLUMN IF NOT EXISTS database_enabled BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS database_config JSONB DEFAULT '{"vector_dimensions": 1536}'::jsonb,
    ADD COLUMN IF NOT EXISTS vector_dimensions INTEGER DEFAULT 1536,
    ADD COLUMN IF NOT EXISTS quantum_enabled BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS mcp_enabled BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS railway_project_id VARCHAR(255);
