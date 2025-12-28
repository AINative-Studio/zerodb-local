# ZeroDB Local CLI

Command-line interface for managing ZeroDB Local environment and syncing with ZeroDB Cloud.

## Installation

```bash
cd /Users/aideveloper/core/zerodb-local/cli
pip install -e .
```

## Quick Start

### 1. Start Local Environment

```bash
zerodb local up
```

### 2. Login to Cloud

```bash
zerodb cloud login --email your@email.com
```

### 3. Link Project

```bash
zerodb cloud link <project-id>
```

### 4. Sync Data

```bash
# Generate sync plan
zerodb sync plan

# Apply sync (with confirmation)
zerodb sync apply

# Push to cloud (shorthand)
zerodb sync push

# Pull from cloud (shorthand)
zerodb sync pull
```

## Commands

### Sync Commands

- `zerodb sync plan` - Generate and display sync plan
  - `--schema` - Show schema diff only
  - `--data` - Show data diff only
  - `--vectors` - Show vector diff only
  - `--json` - Output as JSON

- `zerodb sync apply` - Execute sync plan
  - `--yes` - Skip confirmation
  - `--dry-run` - Preview without executing
  - `--strategy` - Conflict resolution strategy (local-wins, cloud-wins, newest-wins, manual)

- `zerodb sync push` - Push local changes to cloud
  - `--yes` - Skip confirmation
  - `--force` - Force push, overwriting cloud data

- `zerodb sync pull` - Pull cloud changes to local
  - `--yes` - Skip confirmation

### Local Environment Commands

- `zerodb local init` - Initialize local environment
- `zerodb local up` - Start all services
- `zerodb local down` - Stop all services
- `zerodb local status` - Show service status
- `zerodb local logs` - View service logs

### Cloud Commands

- `zerodb cloud login` - Login to ZeroDB Cloud
- `zerodb cloud logout` - Logout from ZeroDB Cloud
- `zerodb cloud whoami` - Show current user
- `zerodb cloud link <project-id>` - Link to cloud project
- `zerodb cloud unlink` - Unlink current project

### Environment Commands

- `zerodb env list` - List all environments
- `zerodb env switch <env>` - Switch environment
- `zerodb env current` - Show current environment

### Inspect Commands

- `zerodb inspect schema` - Show local schema tree
- `zerodb inspect vectors` - Vector namespace summary
- `zerodb inspect events` - Event lag and offsets
- `zerodb inspect sync-state` - Last sync time and status

## Features

### Conflict Resolution

When conflicts are detected during sync, you can choose how to resolve them:

- **local-wins** - Always use local version
- **cloud-wins** - Always use cloud version
- **newest-wins** - Use the version with the latest timestamp
- **manual** - Interactively choose for each conflict

Example:

```bash
zerodb sync apply --strategy=local-wins
```

### Interactive Conflict UI

When using manual conflict resolution, you'll see an interactive prompt:

```
⚠️  Conflict Detected

Table: users
Row ID: 550e8400-e29b-41d4-a716-446655440000

Local:  {"name": "Alice Smith", "email": "alice@local.com"}
Cloud:  {"name": "Alice Johnson", "email": "alice@cloud.com"}

Choose resolution:
  1) Use local version
  2) Use cloud version
  3) Merge manually
  4) Skip this conflict
>
```

### Progress Indicators

Long-running operations show progress bars:

```
Syncing push... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
```

### Rollback on Error

If sync fails, all changes are automatically rolled back to prevent partial sync states.

## Configuration

Configuration is stored in `~/.zerodb/`:

- `config.json` - CLI configuration
- `credentials.json` - Cloud credentials (JWT tokens)

## Development

Story 3.5 and Story 3.6 from the ZeroDB Local Implementation Backlog.

- **Story 3.5**: Sync Plan Command
- **Story 3.6**: Sync Apply Command

## License

MIT
