# Changelog

All notable changes to ZeroDB CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-29

### Added
- Initial release of ZeroDB CLI
- Bidirectional sync between local and cloud (push/pull)
- Sync plan generation with schema, data, and vector diffs
- Conflict resolution strategies (local-wins, cloud-wins, newest-wins, manual)
- Interactive conflict resolution UI
- Local environment management via Docker Compose
- Service health monitoring and status checks
- Cloud authentication (JWT tokens and API keys)
- Project linking between local and cloud
- Environment management (dev, staging, production)
- Database inspection commands (schema, vectors, tables, files, events, health)
- Progress bars and rich terminal UI
- Automatic rollback on sync failures
- Real-time log streaming
- Configuration management

### Commands Added
- `zerodb sync plan` - Generate sync plan
- `zerodb sync apply` - Execute sync with conflict resolution
- `zerodb sync push` - Push local changes to cloud
- `zerodb sync pull` - Pull cloud changes to local
- `zerodb local init` - Initialize local environment
- `zerodb local up` - Start all services
- `zerodb local down` - Stop all services
- `zerodb local status` - Show service health
- `zerodb local logs` - View service logs
- `zerodb local restart` - Restart services
- `zerodb local reset` - Reset environment
- `zerodb cloud login` - Login to ZeroDB Cloud
- `zerodb cloud logout` - Logout from cloud
- `zerodb cloud whoami` - Show current user
- `zerodb cloud link` - Link to cloud project
- `zerodb cloud unlink` - Unlink project
- `zerodb cloud create-from-local` - Create cloud project from local
- `zerodb env list` - List environments
- `zerodb env switch` - Switch environment
- `zerodb env current` - Show current environment
- `zerodb inspect sync` - Show sync state
- `zerodb inspect projects` - List local projects
- `zerodb inspect vectors` - Show vector statistics
- `zerodb inspect tables` - List tables and row counts
- `zerodb inspect files` - List files and sizes
- `zerodb inspect events` - Show event stream stats
- `zerodb inspect health` - System health check

### Dependencies
- typer >= 0.9.0 - CLI framework
- rich >= 13.0.0 - Rich terminal UI
- requests >= 2.31.0 - HTTP client
- httpx >= 0.24.0 - Async HTTP client

### Technical Details
- Python 3.9+ support
- Full integration with ZeroDB Local API
- Real-time status polling during long operations
- Comprehensive E2E integration tests
- Zero-downtime sync with rollback capability
