# ZeroDB CLI

**Official command-line tool for ZeroDB Local and ZeroDB Cloud**

A powerful CLI for managing your local ZeroDB environment, syncing data between local and cloud, and interacting with ZeroDB Cloud services.

---

## 🚀 Quick Start

### Installation

Install from PyPI:

```bash
pip install zerodb-cli
```

### Basic Usage

```bash
# Show version
zerodb version

# Initialize local environment
zerodb local init
zerodb local up

# Login to ZeroDB Cloud
zerodb cloud login --email your@email.com

# Link to cloud project
zerodb cloud link <project-id>

# Sync data
zerodb sync plan    # Preview changes
zerodb sync apply   # Apply sync
```

---

## 📋 Table of Contents

- [Installation](#installation)
- [Features](#features)
- [Commands](#commands)
  - [Sync Commands](#sync-commands)
  - [Local Environment](#local-environment)
  - [Cloud Commands](#cloud-commands)
  - [Environment Management](#environment-management)
  - [Inspect Commands](#inspect-commands)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Conflict Resolution](#conflict-resolution)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [License](#license)

---

## ✨ Features

### 🔄 Bidirectional Sync
- **Push**: Local → Cloud synchronization
- **Pull**: Cloud → Local synchronization
- **Plan**: Preview changes before applying
- **Conflict Resolution**: Multiple strategies (local-wins, cloud-wins, newest-wins, manual)

### 🐳 Local Environment Management
- Docker Compose orchestration
- Service health monitoring
- Log streaming
- One-command startup/shutdown

### ☁️ Cloud Integration
- Secure authentication (JWT)
- Project linking
- Environment switching
- Create cloud projects from local data

### 🔍 Database Inspection
- Schema visualization
- Vector statistics
- Event stream monitoring
- Sync state tracking

### 🎨 Rich Terminal UI
- Beautiful progress bars
- Color-coded output
- Interactive prompts
- Real-time status updates

---

## 📦 Installation

### Requirements

- **Python**: 3.9 or higher
- **Docker**: For local environment (docker-compose)
- **ZeroDB Cloud Account**: For cloud sync features

### Install via pip

```bash
pip install zerodb-cli
```

### Verify Installation

```bash
zerodb --help
zerodb version
```

Expected output:
```
ZeroDB Local CLI v1.0.0
```

---

## 🛠️ Commands

### Sync Commands

Synchronize data between local ZeroDB and ZeroDB Cloud.

#### `zerodb sync plan`

Generate and display sync plan showing differences between local and cloud.

```bash
# Full sync plan
zerodb sync plan

# Schema diff only
zerodb sync plan --schema

# Data diff only
zerodb sync plan --data

# Vectors diff only
zerodb sync plan --vectors

# JSON output
zerodb sync plan --json

# Project-specific
zerodb sync plan --project-id <id>
```

**Options:**
- `--schema` - Show only schema differences
- `--data` - Show only data differences
- `--vectors` - Show only vector differences
- `--json` - Output as JSON
- `--project-id TEXT` - Specify project ID

#### `zerodb sync apply`

Execute sync plan and apply changes.

```bash
# Interactive (with confirmation)
zerodb sync apply

# Auto-confirm
zerodb sync apply --yes

# Dry run (preview only)
zerodb sync apply --dry-run

# Conflict resolution strategy
zerodb sync apply --strategy cloud-wins
```

**Options:**
- `--yes` - Skip confirmation prompts
- `--dry-run` - Preview without executing
- `--strategy` - Conflict resolution: `local-wins`, `cloud-wins`, `newest-wins`, `manual`
- `--project-id TEXT` - Specify project ID

**Conflict Strategies:**
- **local-wins**: Always use local version
- **cloud-wins**: Always use cloud version
- **newest-wins**: Use version with latest timestamp
- **manual**: Interactive conflict resolution

#### `zerodb sync push`

Push local changes to cloud (shorthand for push-only sync).

```bash
# Push with confirmation
zerodb sync push

# Push without confirmation
zerodb sync push --yes

# Force push (overwrite cloud)
zerodb sync push --force
```

**Options:**
- `--yes` - Skip confirmation
- `--force` - Force push, overwriting cloud data
- `--project-id TEXT` - Specify project ID

#### `zerodb sync pull`

Pull cloud changes to local (shorthand for pull-only sync).

```bash
# Pull with confirmation
zerodb sync pull

# Pull without confirmation
zerodb sync pull --yes
```

**Options:**
- `--yes` - Skip confirmation
- `--project-id TEXT` - Specify project ID

---

### Local Environment

Manage local ZeroDB environment (Docker Compose).

#### `zerodb local init`

Initialize local environment (create data directories).

```bash
zerodb local init
```

Creates:
- `~/.zerodb/` - Configuration directory
- `./data/` - Local database data
- `./logs/` - Service logs

#### `zerodb local up`

Start all services (PostgreSQL, Qdrant, MinIO, RedPanda, API, UI).

```bash
# Start in background
zerodb local up

# Start with logs
zerodb local up --logs

# Start specific services
zerodb local up --service api --service postgres
```

**Options:**
- `--logs` - Show logs instead of detaching
- `--service TEXT` - Start specific service (can be used multiple times)

**Services:**
- `postgres` - PostgreSQL database
- `qdrant` - Vector database
- `minio` - Object storage
- `redpanda` - Event streaming
- `embeddings` - Embeddings API
- `api` - FastAPI backend
- `ui` - React frontend

#### `zerodb local down`

Stop all services.

```bash
# Stop services
zerodb local down

# Stop and remove volumes
zerodb local down --volumes
```

**Options:**
- `--volumes` - Also remove data volumes

#### `zerodb local status`

Show service status and health.

```bash
zerodb local status
```

Output:
```
┏━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Service   ┃ Status ┃ Health ┃ URL              ┃
┡━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ postgres  │ Up     │ Healthy│ localhost:5432   │
│ qdrant    │ Up     │ Healthy│ localhost:6333   │
│ minio     │ Up     │ Healthy│ localhost:9000   │
│ api       │ Up     │ Healthy│ localhost:8000   │
└───────────┴────────┴────────┴──────────────────┘
```

#### `zerodb local logs`

View service logs.

```bash
# All services (follow mode)
zerodb local logs

# Specific service
zerodb local logs api

# No follow (show recent only)
zerodb local logs --no-follow

# Last 100 lines
zerodb local logs --tail 100
```

**Options:**
- `--no-follow` - Don't follow logs (show recent and exit)
- `--tail INTEGER` - Number of lines to show

#### `zerodb local restart`

Restart services.

```bash
# Restart all services
zerodb local restart

# Restart specific service
zerodb local restart --service api
```

**Options:**
- `--service TEXT` - Restart specific service

#### `zerodb local reset`

Reset environment (stop services, remove volumes and data).

```bash
# Reset with confirmation
zerodb local reset

# Reset without confirmation (dangerous!)
zerodb local reset --yes
```

**Options:**
- `--yes` - Skip confirmation prompt

⚠️ **Warning**: This removes all local data permanently!

---

### Cloud Commands

Interact with ZeroDB Cloud.

#### `zerodb cloud login`

Login to ZeroDB Cloud.

```bash
# Login with email/password
zerodb cloud login --email your@email.com

# Login with API key
zerodb cloud login --api-key YOUR_API_KEY
```

**Options:**
- `--email TEXT` - Email address
- `--password TEXT` - Password (prompted if not provided)
- `--api-key TEXT` - API key (alternative to email/password)

Credentials are stored in `~/.zerodb/credentials.json`.

#### `zerodb cloud logout`

Logout from ZeroDB Cloud.

```bash
zerodb cloud logout
```

Removes stored credentials.

#### `zerodb cloud whoami`

Show current logged-in user.

```bash
zerodb cloud whoami
```

Output:
```
Logged in as: user@example.com
Organization: AINative Studio
Project: my-project (abc123)
```

#### `zerodb cloud link`

Link local project to cloud project.

```bash
zerodb cloud link <project-id>
```

Creates `.zerodb/project.json` with project link.

#### `zerodb cloud unlink`

Unlink current project.

```bash
zerodb cloud unlink
```

Removes project link (local data remains).

#### `zerodb cloud create-from-local`

Create cloud project from local data.

```bash
# Create new cloud project
zerodb cloud create-from-local --name "My Project"

# With description
zerodb cloud create-from-local --name "My Project" --description "Production database"
```

**Options:**
- `--name TEXT` - Project name (required)
- `--description TEXT` - Project description

---

### Environment Management

Manage CLI environments (dev, staging, production).

#### `zerodb env list`

List all configured environments.

```bash
zerodb env list
```

Output:
```
Environments:
  * dev (current)
  staging
  production
```

#### `zerodb env switch`

Switch to a different environment.

```bash
zerodb env switch staging
```

#### `zerodb env current`

Show current environment.

```bash
zerodb env current
```

Output:
```
Current environment: dev
API URL: http://localhost:8000
```

---

### Inspect Commands

Inspect local database state.

#### `zerodb inspect sync`

Show sync state for project.

```bash
zerodb inspect sync
```

Output:
```
Last Sync: 2025-12-29 10:30:45 UTC
Direction: push
Status: completed
Operations: 150 (142 succeeded, 8 skipped)
```

#### `zerodb inspect projects`

List all local projects.

```bash
zerodb inspect projects
```

#### `zerodb inspect vectors`

Show vector count and storage statistics.

```bash
zerodb inspect vectors
```

Output:
```
Vector Statistics:
  Total vectors: 1,234,567
  Namespaces: 5
  Storage: 2.3 GB
```

#### `zerodb inspect tables`

List tables and row counts.

```bash
zerodb inspect tables
```

Output:
```
┏━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┓
┃ Table     ┃ Rows    ┃ Size      ┃
┡━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━┩
│ users     │ 10,234  │ 5.2 MB    │
│ products  │ 45,678  │ 12.1 MB   │
└───────────┴─────────┴───────────┘
```

#### `zerodb inspect files`

List files and sizes.

```bash
zerodb inspect files
```

#### `zerodb inspect events`

Show event count and latest events.

```bash
zerodb inspect events
```

#### `zerodb inspect health`

Overall system health check.

```bash
zerodb inspect health
```

Output:
```
System Health: ✓ Healthy

Services:
  ✓ PostgreSQL - Healthy
  ✓ Qdrant - Healthy
  ✓ MinIO - Healthy
  ✓ API - Healthy
```

---

## 🔧 How It Works

### Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  ZeroDB CLI     │  sync   │  ZeroDB Cloud    │
│  (Local)        │◄───────►│  (Production)    │
└────────┬────────┘         └──────────────────┘
         │
         │ manages
         ▼
┌─────────────────┐
│ Docker Compose  │
│  Environment    │
├─────────────────┤
│ • PostgreSQL    │
│ • Qdrant        │
│ • MinIO         │
│ • RedPanda      │
│ • API Server    │
│ • React UI      │
└─────────────────┘
```

### Sync Engine

The CLI uses a sophisticated sync engine that:

1. **Detects Changes**: Compares local and cloud state
2. **Generates Plan**: Creates operations (insert, update, delete)
3. **Resolves Conflicts**: Applies chosen strategy
4. **Executes Operations**: Applies changes atomically
5. **Rollback on Error**: Automatic rollback if sync fails

### Authentication

- **JWT Tokens**: Stored in `~/.zerodb/credentials.json`
- **API Keys**: Alternative authentication method
- **Auto-Refresh**: Tokens automatically refreshed when expired

---

## ⚙️ Configuration

Configuration is stored in `~/.zerodb/`:

### `config.json`

```json
{
  "current_environment": "dev",
  "environments": {
    "dev": {
      "local_api_url": "http://localhost:8000",
      "cloud_api_url": "https://api.ainative.studio"
    },
    "production": {
      "local_api_url": "http://localhost:8000",
      "cloud_api_url": "https://api.ainative.studio"
    }
  }
}
```

### `credentials.json`

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "api_key": "YOUR_API_KEY"
}
```

### `project.json`

```json
{
  "project_id": "abc123",
  "project_name": "My Project",
  "linked_at": "2025-12-29T10:30:45Z"
}
```

---

## 🔀 Conflict Resolution

When conflicts are detected during sync, you can choose how to resolve them:

### Automatic Strategies

#### Local Wins
```bash
zerodb sync apply --strategy local-wins
```
Always uses the local version when conflicts occur.

#### Cloud Wins
```bash
zerodb sync apply --strategy cloud-wins
```
Always uses the cloud version when conflicts occur.

#### Newest Wins
```bash
zerodb sync apply --strategy newest-wins
```
Uses the version with the latest `updated_at` timestamp.

### Manual Resolution

```bash
zerodb sync apply --strategy manual
```

Interactive UI shows both versions:

```
⚠️  Conflict Detected

Table: users
Row ID: 550e8400-e29b-41d4-a716-446655440000

Local:  {"name": "Alice Smith", "email": "alice@local.com", "updated_at": "2025-12-29T10:00:00Z"}
Cloud:  {"name": "Alice Johnson", "email": "alice@cloud.com", "updated_at": "2025-12-29T09:00:00Z"}

Choose resolution:
  1) Use local version (newer)
  2) Use cloud version
  3) Merge manually
  4) Skip this conflict

>
```

---

## 🐛 Troubleshooting

### CLI Not Found

```bash
$ zerodb: command not found
```

**Solution**: Install with pip
```bash
pip install zerodb-cli
```

### Authentication Failed

```bash
$ zerodb cloud login
Error: Authentication failed
```

**Solution**: Check credentials
```bash
# Re-login
zerodb cloud logout
zerodb cloud login --email your@email.com
```

### Local Services Not Starting

```bash
$ zerodb local up
Error: docker-compose not found
```

**Solution**: Install Docker Desktop
- macOS: https://docs.docker.com/desktop/install/mac-install/
- Windows: https://docs.docker.com/desktop/install/windows-install/
- Linux: https://docs.docker.com/desktop/install/linux-install/

### Sync Conflicts

```bash
$ zerodb sync apply
Error: 42 conflicts detected
```

**Solution**: Choose conflict strategy
```bash
# Use newest version
zerodb sync apply --strategy newest-wins

# Or resolve manually
zerodb sync apply --strategy manual
```

### Reset Everything

If you encounter persistent issues:

```bash
# Stop services and remove all data
zerodb local reset --yes

# Re-initialize
zerodb local init
zerodb local up
```

---

## 🧑‍💻 Development

### Repository Structure

```
zerodb-cli/
├── main.py              # CLI entry point
├── config.py            # Configuration management
├── sync_planner.py      # Sync plan generation
├── sync_executor.py     # Sync execution
├── conflict_resolver.py # Conflict resolution
├── commands/
│   ├── __init__.py
│   ├── sync.py          # Sync commands
│   ├── local.py         # Local environment commands
│   ├── cloud.py         # Cloud commands
│   ├── env.py           # Environment management
│   └── inspect.py       # Inspection commands
├── tests/
│   ├── test_sync_plan.py
│   ├── test_sync_apply.py
│   ├── test_integration.py
│   └── test_e2e.py
├── setup.py             # Package configuration
├── requirements.txt     # Dependencies
└── README.md            # This file
```

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=term-missing

# Run E2E tests (requires API running)
pytest tests/test_e2e.py -v -m e2e
```

### Local Development

```bash
# Clone repo
git clone https://github.com/AINative-Studio/zerodb-cli.git
cd zerodb-cli

# Install in editable mode
pip install -e .

# Run CLI
zerodb --help
```

### Integration with ZeroDB Local

The CLI works with ZeroDB Local environment which includes:

- **PostgreSQL**: Main database (port 5432)
- **Qdrant**: Vector database (port 6333)
- **MinIO**: Object storage (port 9000)
- **RedPanda**: Event streaming (port 9092)
- **Embeddings API**: Text embeddings (port 8001)
- **FastAPI**: Backend API (port 8000)
- **React UI**: Web interface (port 3000)

All services are managed via Docker Compose.

---

## 📄 License

MIT License - Copyright (c) 2025 AINative Studio

---

## 🔗 Links

- **Website**: https://www.ainative.studio
- **Documentation**: https://docs.ainative.studio/zerodb-local
- **Support**: hello@ainative.studio
- **PyPI**: https://pypi.org/project/zerodb-cli/

---

## 🙏 Support

For issues, questions, or feature requests:

- Email: hello@ainative.studio
- Documentation: https://docs.ainative.studio/zerodb-local

---

**Built with ❤️ by AINative Studio**
