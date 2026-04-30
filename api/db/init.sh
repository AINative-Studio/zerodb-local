#!/bin/bash
# ZeroDB Local Database Initialization Script
# This script runs when the PostgreSQL container starts for the first time

set -e

echo "========================================"
echo "ZeroDB Local Database Initialization"
echo "========================================"

# Execute schema creation
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    \echo 'Initializing ZeroDB Local database...'
    \echo ''

    -- Enable extensions
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    \echo 'Extensions installed: vector, uuid-ossp'
    \echo ''
EOSQL

# Run migration
echo "Running initial schema migration..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" < /docker-entrypoint-initdb.d/migrations/001_initial_schema.sql

echo ""
echo "========================================"
echo "Database initialization completed!"
echo "========================================"
echo ""
echo "Database: $POSTGRES_DB"
echo "User: $POSTGRES_USER"
echo ""
echo "Tables created:"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "\dt"
echo ""
echo "Ready to accept connections!"
