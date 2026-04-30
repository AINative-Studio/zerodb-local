# ZeroDB Local - Cloud Sync Strategy

Complete guide to synchronizing data between ZeroDB Local and ZeroDB Cloud. Master bidirectional sync, conflict resolution, and hybrid workflows.

## Table of Contents

- [Overview](#overview)
- [Setup and Authentication](#setup-and-authentication)
- [Sync Workflows](#sync-workflows)
- [Conflict Resolution](#conflict-resolution)
- [Sync Modes](#sync-modes)
- [Performance Optimization](#performance-optimization)
- [Security Considerations](#security-considerations)
- [Advanced Patterns](#advanced-patterns)
- [Monitoring and Debugging](#monitoring-and-debugging)
- [Best Practices](#best-practices)

## Overview

ZeroDB Local supports bidirectional synchronization with ZeroDB Cloud, enabling:

- **Offline Development**: Work without internet, sync when ready
- **Hybrid Workflows**: Develop locally, deploy to cloud
- **Disaster Recovery**: Cloud backup of local data
- **Multi-Environment**: Sync between local, staging, and production
- **Collaboration**: Share data across team members via cloud

### Sync Architecture

```
┌─────────────────┐         ┌─────────────────┐
│  ZeroDB Local   │         │  ZeroDB Cloud   │
│                 │         │                 │
│  ┌───────────┐  │         │  ┌───────────┐  │
│  │ Projects  │  │◄───────►│  │ Projects  │  │
│  └───────────┘  │  Sync   │  └───────────┘  │
│  ┌───────────┐  │         │  ┌───────────┐  │
│  │  Vectors  │  │◄───────►│  │  Vectors  │  │
│  └───────────┘  │         │  └───────────┘  │
│  ┌───────────┐  │         │  ┌───────────┐  │
│  │  Tables   │  │◄───────►│  │  Tables   │  │
│  └───────────┘  │         │  └───────────┘  │
│  ┌───────────┐  │         │  ┌───────────┐  │
│  │   Files   │  │◄───────►│  │   Files   │  │
│  └───────────┘  │         │  └───────────┘  │
│  ┌───────────┐  │         │  ┌───────────┐  │
│  │  Events   │  │────────►│  │  Events   │  │
│  └───────────┘  │ (1-way) │  └───────────┘  │
└─────────────────┘         └─────────────────┘
```

### What Gets Synced

| Resource | Local → Cloud | Cloud → Local | Notes |
|----------|---------------|---------------|-------|
| Projects | Yes | Yes | Metadata only |
| Vectors | Yes | Yes | Full embeddings |
| Tables | Yes | Yes | Schema + data |
| Files | Yes | Yes | Via presigned URLs |
| Events | Yes | No | One-way only |
| User Auth | No | N/A | Cloud only |

## Setup and Authentication

### 1. Get API Key

Obtain your ZeroDB Cloud API key:

1. Visit https://www.ainative.studio/dashboard/api-keys
2. Click "Create New API Key"
3. Name it (e.g., "Local Development")
4. Copy the key (shown only once!)

### 2. Configure Environment

Add API key to `.env.local`:

```env
# ZeroDB Cloud Configuration
CLOUD_API_URL=https://api.ainative.studio
CLOUD_API_KEY=your-api-key-here
SYNC_ENABLED=true
SYNC_INTERVAL_SECONDS=300  # 5 minutes
```

### 3. Install CLI Tool

```bash
cd cli
pip install -e .
```

### 4. Login via CLI

```bash
# Login with API key
zerodb cloud login

# Or login interactively
zerodb cloud login --interactive

# Verify authentication
zerodb cloud whoami
```

**Output:**
```
Logged in as: user@example.com
Organization: My Organization
API Endpoint: https://api.ainative.studio
```

### 5. Link Local Project to Cloud

```bash
# List cloud projects
zerodb cloud projects

# Link local project to cloud project
zerodb cloud link proj_cloud_abc123

# Verify link
zerodb sync status
```

## Sync Workflows

### Workflow 1: Develop Locally, Deploy to Cloud

**Scenario**: Build features locally, push to cloud when ready.

```bash
# 1. Develop locally
curl -X POST http://localhost:8000/v1/projects \
  -d '{"name": "my-project"}'

# 2. Add vectors, tables, files
# ... work locally ...

# 3. Preview changes to be synced
zerodb sync plan

# 4. Push to cloud
zerodb sync apply

# 5. Verify in cloud dashboard
# https://www.ainative.studio/dashboard
```

### Workflow 2: Pull from Cloud, Work Locally

**Scenario**: Clone production data for local testing.

```bash
# 1. Link to cloud project
zerodb cloud link proj_production_xyz

# 2. Pull all data
zerodb cloud pull

# 3. Work with local copy
curl http://localhost:8000/v1/projects/{local_id}/database/vectors/search

# 4. Push changes back (optional)
zerodb sync apply
```

### Workflow 3: Continuous Sync

**Scenario**: Keep local and cloud in sync automatically.

Enable automatic sync in `.env.local`:

```env
SYNC_ENABLED=true
SYNC_INTERVAL_SECONDS=300  # Every 5 minutes
SYNC_AUTO_APPLY=true  # Auto-sync without confirmation
CONFLICT_RESOLUTION=newest-wins  # Auto-resolve conflicts
```

Restart API:
```bash
docker-compose restart api
```

Monitor sync:
```bash
# Watch sync logs
docker-compose logs -f api | grep -i sync

# Check sync status
zerodb sync status
```

### Workflow 4: Multi-Environment Sync

**Scenario**: Sync local → staging → production.

```bash
# Local → Staging
zerodb cloud link proj_staging_abc --alias staging
zerodb sync apply --target staging

# Verify in staging
curl https://staging-api.ainative.studio/v1/projects/{id}/health

# Staging → Production
zerodb cloud link proj_production_xyz --alias production
zerodb cloud pull --source staging
zerodb sync apply --target production
```

## Conflict Resolution

When both local and cloud have changes, conflicts may occur.

### Conflict Types

| Conflict Type | Example | Detection |
|---------------|---------|-----------|
| Update-Update | Both sides modified same vector | Compare timestamps |
| Delete-Update | One side deleted, other updated | Missing resource |
| Schema Conflict | Table schema changed differently | Schema comparison |
| ID Conflict | Same ID used for different resources | ID collision |

### Resolution Strategies

Configure in `.env.local`:

```env
CONFLICT_RESOLUTION=newest-wins  # Options below
```

#### 1. Local Wins (local-wins)

Always prefer local changes:

```env
CONFLICT_RESOLUTION=local-wins
```

**Use when:**
- You're the sole developer
- Local is source of truth
- Cloud is backup only

#### 2. Cloud Wins (cloud-wins)

Always prefer cloud changes:

```env
CONFLICT_RESOLUTION=cloud-wins
```

**Use when:**
- Pulling from production
- Cloud is source of truth
- Local is for testing only

#### 3. Newest Wins (newest-wins)

Prefer most recently modified:

```env
CONFLICT_RESOLUTION=newest-wins
```

**Use when:**
- Multiple developers syncing
- Want automatic conflict resolution
- Timestamp-based precedence acceptable

**How it works:**
- Compare `updated_at` timestamps
- Choose version with latest timestamp
- Log conflict resolution

#### 4. Manual Resolution (manual)

Prompt for each conflict:

```env
CONFLICT_RESOLUTION=manual
```

**Use when:**
- Need full control
- Can't afford data loss
- Critical production data

**Interactive prompt:**
```bash
zerodb sync apply

# Conflict detected: Vector vec_123
# Local updated_at: 2026-02-27T10:00:00Z
# Cloud updated_at: 2026-02-27T11:00:00Z
#
# Choose resolution:
# 1. Keep local version
# 2. Keep cloud version
# 3. Merge (manual edit)
# 4. Skip this resource
#
# Choice [1-4]:
```

### Conflict Resolution Examples

#### Example 1: Vector Update Conflict

**Scenario**: Same vector modified on both sides.

**Local version:**
```json
{
  "id": "vec_123",
  "document": "Local document text",
  "updated_at": "2026-02-27T10:00:00Z"
}
```

**Cloud version:**
```json
{
  "id": "vec_123",
  "document": "Cloud document text",
  "updated_at": "2026-02-27T11:00:00Z"
}
```

**Resolution with newest-wins:**
```bash
zerodb sync apply

# Output:
# Conflict: vec_123 (vector)
# Resolution: cloud-wins (newer timestamp)
# Applied cloud version
```

#### Example 2: Schema Conflict

**Scenario**: Table schema diverged.

**Local schema:**
```json
{
  "table": "users",
  "columns": {
    "id": "string",
    "name": "string",
    "email": "string"
  }
}
```

**Cloud schema:**
```json
{
  "table": "users",
  "columns": {
    "id": "string",
    "name": "string",
    "email": "string",
    "phone": "string"  // New column
  }
}
```

**Resolution:**
```bash
# Manual resolution required
zerodb sync apply

# Conflict: users table schema mismatch
# Choose:
# 1. Use local schema (drop phone column in cloud)
# 2. Use cloud schema (add phone column locally)
# 3. Merge schemas (keep both, migrate data)
```

### Viewing Sync Conflicts

```bash
# See all pending conflicts
zerodb sync conflicts

# Show conflict details
zerodb sync conflicts --verbose

# Export conflicts to JSON
zerodb sync conflicts --format json > conflicts.json
```

## Sync Modes

### 1. Full Sync

Sync all resources:

```bash
zerodb sync apply
```

### 2. Incremental Sync

Only sync changes since last sync:

```bash
zerodb sync apply --incremental
```

**Benefits:**
- Faster (only changed resources)
- Less bandwidth
- Lower API costs

**How it works:**
- Tracks last sync timestamp
- Queries resources with `updated_at > last_sync`
- Syncs delta only

### 3. Selective Sync

Sync specific resource types:

```bash
# Only vectors
zerodb sync apply --resources vectors

# Only tables
zerodb sync apply --resources tables

# Multiple resources
zerodb sync apply --resources vectors,tables,files
```

### 4. Project-Specific Sync

Sync only certain projects:

```bash
# Single project
zerodb sync apply --project proj_local_123

# Multiple projects
zerodb sync apply --projects proj_local_123,proj_local_456
```

### 5. Dry Run

Preview changes without applying:

```bash
# See what would be synced
zerodb sync plan

# Dry run with detailed diff
zerodb sync plan --verbose

# Export plan to JSON
zerodb sync plan --format json > sync-plan.json
```

**Example output:**
```
Sync Plan:
  Create in cloud:
    - 5 vectors
    - 2 tables
    - 3 files
  Update in cloud:
    - 10 vectors
    - 1 table
  Delete from cloud:
    - 2 vectors (deleted locally)
  Pull from cloud:
    - 3 vectors (newer in cloud)
    - 1 file

Total: 26 operations
Estimated sync time: 30 seconds
```

## Performance Optimization

### Batch Syncing

Sync in batches to avoid timeouts:

```env
# .env.local
SYNC_BATCH_SIZE=100  # Sync 100 resources at a time
SYNC_PARALLEL_REQUESTS=5  # 5 concurrent uploads
```

### Compression

Enable compression for large payloads:

```env
SYNC_COMPRESSION=true
SYNC_COMPRESSION_LEVEL=6  # 1-9, higher = better compression
```

### Bandwidth Limits

Limit sync bandwidth to avoid congestion:

```env
SYNC_MAX_BANDWIDTH_MBPS=10  # 10 Mbps max
```

### Scheduled Sync

Sync during off-peak hours:

```bash
# Crontab: Sync daily at 2 AM
0 2 * * * cd /path/to/zerodb-local && zerodb sync apply --quiet >> logs/sync.log 2>&1
```

### Smart File Sync

Only sync files that changed:

```env
SYNC_FILE_CHECKSUM=true  # Use MD5 checksums to detect changes
SYNC_FILE_DELTA=true  # Use binary delta for large files
```

## Security Considerations

### API Key Security

**Never commit API keys to git:**

```bash
# Ensure .env.local is gitignored
grep -q ".env.local" .gitignore || echo ".env.local" >> .gitignore

# Check for accidental commits
git log -S "CLOUD_API_KEY" --all
```

**Rotate keys regularly:**

```bash
# Generate new key in dashboard
# Update .env.local
# Test sync
zerodb sync plan

# Revoke old key in dashboard
```

### Encryption in Transit

All sync uses HTTPS/TLS:

```env
CLOUD_API_URL=https://api.ainative.studio  # Always HTTPS
SYNC_VERIFY_SSL=true  # Verify SSL certificates
```

### Encryption at Rest

Sensitive data in cloud:

```env
# Enable client-side encryption (enterprise feature)
SYNC_ENCRYPT_SENSITIVE_FIELDS=true
SYNC_ENCRYPTION_KEY=your-encryption-key
```

### Access Control

Limit sync to specific networks:

```bash
# Firewall: Only allow HTTPS to api.ainative.studio
sudo ufw allow out to api.ainative.studio port 443

# Or use VPN for sync
```

### Audit Logging

Track all sync operations:

```env
SYNC_AUDIT_LOG=true
SYNC_AUDIT_LOG_PATH=/var/log/zerodb/sync-audit.log
```

**Log format:**
```json
{
  "timestamp": "2026-02-27T15:00:00Z",
  "operation": "sync_apply",
  "user": "user@example.com",
  "resources": {"vectors": 10, "tables": 2},
  "status": "success",
  "duration_ms": 3450
}
```

## Advanced Patterns

### Pattern 1: Branch-Like Workflows

Create isolated sync branches:

```bash
# Create dev branch in cloud
zerodb cloud create-project --name "my-project-dev"

# Link local to dev branch
zerodb cloud link proj_dev_abc

# Work and sync to dev
zerodb sync apply

# When ready, promote to production
zerodb cloud promote proj_dev_abc --to proj_prod_xyz
```

### Pattern 2: Selective Bidirectional Sync

Sync different resources in different directions:

```bash
# Push vectors to cloud
zerodb sync apply --resources vectors --direction push

# Pull tables from cloud
zerodb sync apply --resources tables --direction pull

# Bidirectional for files
zerodb sync apply --resources files --direction both
```

### Pattern 3: Multi-Region Sync

Sync to multiple cloud regions:

```env
# .env.local
CLOUD_REGIONS=us-west-2,eu-central-1,ap-southeast-1
```

```bash
# Sync to all regions
zerodb sync apply --regions all

# Sync to specific region
zerodb sync apply --region eu-central-1
```

### Pattern 4: Sync Hooks

Run custom code before/after sync:

```bash
# .zerodb/hooks/pre-sync.sh
#!/bin/bash
echo "Running pre-sync validation..."
python scripts/validate_data.py

# .zerodb/hooks/post-sync.sh
#!/bin/bash
echo "Running post-sync cleanup..."
python scripts/cleanup_temp_data.py
```

Enable hooks:
```env
SYNC_HOOKS_ENABLED=true
```

### Pattern 5: Sync Webhooks

Get notified when sync completes:

```env
SYNC_WEBHOOK_URL=https://your-app.com/webhooks/sync-complete
```

**Webhook payload:**
```json
{
  "event": "sync.completed",
  "timestamp": "2026-02-27T15:00:00Z",
  "project_id": "proj_local_123",
  "resources": {
    "vectors": {"created": 5, "updated": 10, "deleted": 2},
    "tables": {"created": 1, "updated": 0, "deleted": 0}
  },
  "duration_ms": 3450,
  "status": "success"
}
```

## Monitoring and Debugging

### Sync Status

```bash
# Current sync status
zerodb sync status

# Detailed status
zerodb sync status --verbose

# Status for specific project
zerodb sync status --project proj_local_123
```

**Example output:**
```
Sync Status:
  Project: my-project (proj_local_123)
  Linked to: proj_cloud_abc (cloud)
  Last sync: 2026-02-27 14:55:00 (5 minutes ago)
  Next sync: 2026-02-27 15:00:00 (in 2 seconds)
  Status: In sync
  Pending changes: 0
  Conflicts: 0
```

### Sync History

```bash
# View sync history
zerodb sync history

# Last 10 syncs
zerodb sync history --limit 10

# Syncs in date range
zerodb sync history --from 2026-02-20 --to 2026-02-27

# Export history
zerodb sync history --format json > sync-history.json
```

### Debugging Failed Syncs

```bash
# Enable debug logging
export LOG_LEVEL=debug
zerodb sync apply --verbose

# Check sync logs
docker-compose logs api | grep -i sync

# Retry failed sync with backoff
zerodb sync retry --exponential-backoff
```

### Sync Metrics

Track sync performance:

```bash
# Sync metrics dashboard
zerodb sync metrics

# Prometheus metrics endpoint
curl http://localhost:8000/metrics | grep sync
```

**Metrics tracked:**
- `sync_operations_total` - Total sync operations
- `sync_duration_seconds` - Sync duration histogram
- `sync_errors_total` - Failed syncs
- `sync_conflicts_total` - Conflicts encountered
- `sync_resources_synced` - Resources synced by type

## Best Practices

### 1. Sync Frequently, in Small Batches

```bash
# Good: Frequent small syncs
zerodb sync apply --incremental

# Avoid: Infrequent large syncs
# (risk of conflicts, long sync times)
```

### 2. Use Incremental Sync

```env
SYNC_MODE=incremental  # Default to incremental
```

### 3. Set Appropriate Conflict Resolution

```env
# Development
CONFLICT_RESOLUTION=local-wins

# Production pull
CONFLICT_RESOLUTION=cloud-wins

# Collaboration
CONFLICT_RESOLUTION=newest-wins
```

### 4. Monitor Sync Health

```bash
# Set up alerts for sync failures
zerodb sync monitor --alert-email alerts@example.com
```

### 5. Test Sync in Staging First

```bash
# Test in staging
zerodb cloud link proj_staging_abc
zerodb sync apply

# If successful, promote to production
zerodb cloud promote proj_staging_abc --to proj_prod_xyz
```

### 6. Keep API Keys Secure

```bash
# Use environment variables, not .env files in production
export CLOUD_API_KEY=$(aws secretsmanager get-secret-value --secret-id zerodb-api-key --query SecretString --output text)
```

### 7. Use Selective Sync for Large Projects

```bash
# Don't sync everything if you don't need it
zerodb sync apply --resources vectors,tables --exclude-large-files
```

### 8. Enable Audit Logging

```env
SYNC_AUDIT_LOG=true
```

### 9. Backup Before Major Syncs

```bash
# Backup before pulling from production
./scripts/backup-local.sh
zerodb cloud pull --source production
```

### 10. Document Sync Workflows

Create `.zerodb/SYNC_WORKFLOW.md`:
```markdown
# Our Sync Workflow

1. Develop locally
2. Sync to staging: `zerodb sync apply --target staging`
3. Test in staging
4. Promote to production: `zerodb cloud promote staging --to production`
```

## Summary

ZeroDB Cloud Sync enables powerful hybrid workflows:

- **Bidirectional Sync**: Local ↔ Cloud
- **Conflict Resolution**: Multiple strategies
- **Selective Sync**: Choose what to sync
- **Incremental Sync**: Fast, efficient updates
- **Secure**: HTTPS, API keys, audit logs

Key commands:
```bash
# Setup
zerodb cloud login
zerodb cloud link proj_cloud_abc

# Sync
zerodb sync plan        # Preview changes
zerodb sync apply       # Apply changes
zerodb cloud pull       # Pull from cloud

# Monitor
zerodb sync status      # Current status
zerodb sync history     # Past syncs
```

For more information:
- [Quick Start](./QUICK_START.md) - Get started
- [Environment Setup](./ENVIRONMENT_SETUP.md) - Configuration
- [Data Management](./DATA_MANAGEMENT.md) - Backups and data lifecycle
- [Troubleshooting](./TROUBLESHOOTING.md) - Common sync issues
