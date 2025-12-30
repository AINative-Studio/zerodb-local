# Inspect Commands - Environment Inspection and Debugging

**Story:** #423 - Add Environment Inspection Commands
**Epic:** 3 - CLI Development
**Status:** Implemented

## Overview

The `zerodb inspect` command group provides debugging and inspection capabilities for the local ZeroDB environment. These commands help developers understand the current state of their local database, monitor sync status, and verify system health.

## Commands

### `zerodb inspect sync`

Shows the current sync state between local and cloud environments.

**Usage:**
```bash
zerodb inspect sync
zerodb inspect sync --project-id abc123
zerodb inspect sync --json
```

**Output:**
```
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Attribute     ┃ Value               ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ Last Sync     │ 2025-12-29 14:30:00 │
│ Direction     │ bidirectional       │
│ Status        │ synced              │
│ Pending       │ 234 changes         │
│ Conflicts     │ 0                   │
│ Next Sync     │ ~5 minutes          │
└───────────────┴─────────────────────┘

Entity Counts:
┏━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━┓
┃ Entity     ┃ Local ┃ Cloud ┃ Delta ┃
┡━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━┩
│ vectors    │  1500 │  1400 │  +100 │
│ tables     │    10 │    10 │     0 │
│ files      │    25 │    20 │    +5 │
└────────────┴───────┴───────┴───────┘
```

**API Endpoint:** `GET /v1/projects/{id}/sync/state`

**Error Handling:**
- No project linked → "No project linked. Run 'zerodb cloud link <project_id>'"
- API not running → "Local API not running. Run 'zerodb local up'"

---

### `zerodb inspect projects`

Lists all local projects with their metadata and entity counts.

**Usage:**
```bash
zerodb inspect projects
zerodb inspect projects --json
```

**Output:**
```
Local Projects
┏━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━┓
┃ Project   ┃ Name        ┃ Created        ┃ Vector ┃ Table ┃ Files ┃ Status   ┃
┃ ID        ┃             ┃                ┃ s      ┃ s     ┃       ┃          ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━┩
│ proj-123  │ Main        │ 2025-12-01     │   1500 │    10 │    25 │ ✓ Current│
│ proj-456  │ Test        │ 2025-12-15     │    500 │     3 │     8 │          │
└───────────┴─────────────┴────────────────┴────────┴───────┴───────┴──────────┘

Total: 2 project(s)
```

**API Endpoint:** `GET /v1/projects`

**Features:**
- Highlights currently linked project
- Shows entity counts for quick overview
- Supports JSON output for scripting

---

### `zerodb inspect vectors`

Shows vector database statistics including count, dimensions, and storage usage.

**Usage:**
```bash
zerodb inspect vectors
zerodb inspect vectors --project-id abc123
zerodb inspect vectors --json
```

**Output:**
```
Vector Statistics - Project proj-123
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Metric       ┃ Value        ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Total        │ 1500         │
│ Dimensions   │ 1536         │
│ Storage      │ 100.00 MB    │
│ Namespaces   │ 3            │
│ Last Updated │ 2025-12-29   │
└──────────────┴──────────────┘

Recent Additions (Last 10):
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Vector ID        ┃ Namespace ┃ Added          ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ vec-abc123def... │ default   │ 2025-12-29     │
└──────────────────┴───────────┴────────────────┘
```

**API Endpoint:** `GET /v1/projects/{id}/database/vectors/stats`

**Metrics:**
- Total vectors stored
- Vector dimensions (typically 1536 for OpenAI embeddings)
- Storage size in bytes (formatted)
- Number of namespaces
- 10 most recent additions

---

### `zerodb inspect tables`

Lists all NoSQL tables with row counts and storage information.

**Usage:**
```bash
zerodb inspect tables
zerodb inspect tables --project-id abc123
zerodb inspect tables --json
```

**Output:**
```
Tables - Project proj-123
┏━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Table     ┃ Row Count ┃ Size     ┃ Last Modified  ┃
┃ Name      ┃           ┃          ┃                ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ users     │      1000 │ 50.00 MB │ 2025-12-29     │
│ products  │       500 │ 25.00 MB │ 2025-12-28     │
└───────────┴───────────┴──────────┴────────────────┘

Total: 2 table(s)
```

**API Endpoint:** `GET /v1/projects/{id}/database/tables`

**Information:**
- Table names
- Row counts
- Storage size
- Last modification timestamp

---

### `zerodb inspect files`

Shows file storage statistics and breakdown by file type.

**Usage:**
```bash
zerodb inspect files
zerodb inspect files --project-id abc123
zerodb inspect files --json
```

**Output:**
```
File Storage - Project proj-123
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Metric      ┃ Value      ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Total Files │ 25         │
│ Total Size  │ 100.00 MB  │
│ Average     │ 4.00 MB    │
└─────────────┴────────────┘

File Types:
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Type              ┃ Count ┃ Size     ┃ Percentage ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━┩
│ image/png         │    10 │ 50.00 MB │       40.0%│
│ application/pdf   │     8 │ 40.00 MB │       32.0%│
│ text/plain        │     7 │ 10.00 MB │       28.0%│
└───────────────────┴───────┴──────────┴────────────┘
```

**API Endpoint:** `GET /v1/projects/{id}/database/files`

**Metrics:**
- Total file count
- Total storage size
- Average file size
- Breakdown by MIME type

---

### `zerodb inspect events`

Shows event stream statistics and recent events.

**Usage:**
```bash
zerodb inspect events
zerodb inspect events --project-id abc123
zerodb inspect events --json
```

**Output:**
```
Event Stream - Project proj-123
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Metric      ┃ Value          ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Total       │ 5000           │
│ Event Types │ 4              │
│ Oldest      │ 2025-12-01     │
│ Newest      │ 2025-12-29     │
└─────────────┴────────────────┘

Event Types:
┏━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┓
┃ Type            ┃ Count ┃ Percentage ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━┩
│ vector.created  │  2000 │       40.0%│
│ table.updated   │  1500 │       30.0%│
│ file.uploaded   │  1000 │       20.0%│
│ sync.completed  │   500 │       10.0%│
└─────────────────┴───────┴────────────┘

Latest Events (Last 5):
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Timestamp      ┃ Type          ┃ Source    ┃ Description ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ 2025-12-29     │ sync.complete │ sync-eng  │ Sync done   │
└────────────────┴───────────────┴───────────┴─────────────┘
```

**API Endpoint:** `GET /v1/projects/{id}/database/events`

**Information:**
- Total event count
- Event types breakdown with percentages
- 5 most recent events
- Oldest and newest event timestamps

---

### `zerodb inspect health`

Performs a comprehensive health check of all local services.

**Usage:**
```bash
zerodb inspect health
zerodb inspect health --json
```

**Output:**
```
System Health: ✅ Healthy

┏━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Service     ┃ Status ┃ Response     ┃ Details      ┃
┃             ┃        ┃ Time         ┃              ┃
┡━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ PostgreSQL  │ ✅     │ 5ms          │ Connected    │
│ Qdrant      │ ✅     │ 12ms         │ All OK       │
│ MinIO       │ ✅     │ 8ms          │ Available    │
│ RedPanda    │ ✅     │ 15ms         │ Active       │
│ Embeddings  │ ✅     │ 120ms        │ Model loaded │
└─────────────┴────────┴──────────────┴──────────────┘

Last checked: 2025-12-29 14:30:00
```

**API Endpoint:** `GET /health`

**Status Indicators:**
- ✅ **Healthy** (Green) - Service is fully operational
- ⚠️ **Degraded** (Yellow) - Service is operational but slow or limited
- ❌ **Down** (Red) - Service is unavailable

**Services Checked:**
1. **PostgreSQL** - Relational database for metadata
2. **Qdrant** - Vector database for embeddings
3. **MinIO** - Object storage for files
4. **RedPanda** - Event streaming platform
5. **Embeddings** - Local embedding model service

---

## Common Options

All inspect commands support the following options:

### `--json`
Output results in JSON format for programmatic processing.

**Example:**
```bash
zerodb inspect health --json
```

**Output:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-29T14:30:00Z",
  "services": {
    "postgresql": {
      "status": "healthy",
      "response_time_ms": 5,
      "details": "Connected"
    }
  }
}
```

### `--project-id` / `-p`
Specify a project ID instead of using the currently linked project.

**Example:**
```bash
zerodb inspect vectors --project-id abc123
```

---

## Error Messages

### API Not Running
```
Error: Local API not running at http://localhost:8000.
Run 'zerodb local up' to start the local environment.
```

**Solution:** Start the local environment with `zerodb local up`

### No Project Linked
```
Error: No project linked.
Run 'zerodb cloud link <project_id>' or use --project-id flag.
```

**Solution:** Link a project or specify `--project-id`

### Resource Not Found
```
Error: Resource not found: /v1/projects/invalid-id/database/vectors/stats
```

**Solution:** Verify the project ID exists

### API Error
```
Error: API error: 500 - Internal Server Error
```

**Solution:** Check API logs with `zerodb local logs api`

---

## Environment Variables

### `ZERODB_LOCAL_API_URL`
Override the default local API URL.

**Default:** `http://localhost:8000`

**Example:**
```bash
export ZERODB_LOCAL_API_URL=http://localhost:9000
zerodb inspect health
```

---

## Configuration

Inspect commands read configuration from `~/.zerodb/config.json`:

```json
{
  "active_env": "local",
  "project_id": "proj-123",
  "local_api_url": "http://localhost:8000",
  "cloud_api_url": "https://api.ainative.studio"
}
```

**Key Fields:**
- `project_id` - Currently linked project (used when `--project-id` not specified)
- `local_api_url` - Local API endpoint

---

## Use Cases

### 1. Pre-Deployment Health Check
```bash
# Verify all services are healthy before deploying
zerodb inspect health

# Check data is ready to sync
zerodb inspect sync
```

### 2. Storage Monitoring
```bash
# Monitor storage growth
zerodb inspect vectors
zerodb inspect files
zerodb inspect tables
```

### 3. Debugging Sync Issues
```bash
# Check sync state
zerodb inspect sync

# Verify entity counts match
zerodb inspect sync --json | jq '.entity_counts'
```

### 4. Project Overview
```bash
# List all projects and their sizes
zerodb inspect projects

# Get detailed stats for specific project
zerodb inspect vectors --project-id proj-123
```

### 5. Event Monitoring
```bash
# Monitor recent activity
zerodb inspect events

# Check for specific event types
zerodb inspect events --json | jq '.event_types'
```

---

## Implementation Details

### API Client
- **Library:** httpx (modern async-capable HTTP client)
- **Timeout:** 10 seconds
- **Retries:** 3 attempts with exponential backoff
- **Error Handling:** User-friendly messages for common errors

### Retry Logic
```python
for attempt in range(MAX_RETRIES):
    try:
        response = client.request(method, url)
        return response.json()
    except httpx.ConnectError:
        if attempt == MAX_RETRIES - 1:
            raise Exception("Local API not running...")
```

### Formatting Utilities
- `format_bytes()` - Converts bytes to human-readable (KB, MB, GB)
- `format_timestamp()` - ISO 8601 to readable datetime
- `estimate_next_sync()` - Smart sync time estimation

---

## Testing

Run tests with:
```bash
cd /Users/aideveloper/core/zerodb-local/cli
python3 -m pytest test_inspect_commands.py -v
```

**Test Coverage:**
- ✅ Utility functions (formatting, estimation)
- ✅ Project ID resolution logic
- ✅ API client error handling
- ✅ Data structure validation
- ✅ Endpoint correctness

---

## Next Steps

Future enhancements planned:
1. **Watch mode** - `zerodb inspect health --watch` (auto-refresh)
2. **Export** - `zerodb inspect sync --export sync-report.json`
3. **Filters** - `zerodb inspect events --type sync.completed`
4. **Alerts** - `zerodb inspect health --alert-on-degraded`

---

## Related Documentation

- [CLI Overview](./CLI_OVERVIEW.md)
- [Sync Commands](./SYNC_COMMANDS.md)
- [Local Environment Management](./LOCAL_COMMANDS.md)
- [API Reference](/docs/api/LOCAL_API.md)

---

**Last Updated:** 2025-12-29
**Story:** #423
**Status:** Complete
