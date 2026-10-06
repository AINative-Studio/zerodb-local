-- Migration 006: fix vector/embedding column dimensions to match the local
-- embeddings service (BAAI/bge-small-en-v1.5, 384 dims), not the cloud/OpenAI
-- default of 1536 that 001_initial_schema.sql actually created.
--
-- Root cause: 001_initial_schema.sql's "vectors" and "memory" tables declare
-- "embedding vector(1536)" — a leftover from the cloud OpenAI ada-002
-- dimension — while vector_service.py/memory_service.py already correctly
-- read QDRANT_VECTOR_SIZE (384) from the environment. Any vector upsert
-- through the local embeddings service then fails with
-- "expected 1536 dimensions, not 384". schema.sql (not actually executed
-- first, see migration 005's note) has the correct vector(384) declaration,
-- which is what this migration brings the live table in line with.
--
-- Safe only because these tables are empty on a fresh/demo local stack; a
-- table with real 1536-dim rows would need those rows re-embedded, not just
-- a column swap.

ALTER TABLE vectors ALTER COLUMN embedding TYPE vector(384);
ALTER TABLE memory ALTER COLUMN embedding TYPE vector(384);

-- Keep new-project defaults consistent with the actual local model dimension.
ALTER TABLE projects ALTER COLUMN vector_dimensions SET DEFAULT 384;
ALTER TABLE projects ALTER COLUMN database_config SET DEFAULT '{"vector_dimensions": 384}'::jsonb;
