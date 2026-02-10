# ZeroLocal CLI Wizard Design

**Version**: 1.0
**Status**: Design Phase
**Last Updated**: 2026-02-10
**Related**: ARCHITECTURE.md, Issue #1133

---

## Overview

Interactive CLI wizard for ZeroLocal setup and management. Goal: make complex Docker orchestration feel like magic.

---

## 1. Wizard Flow

### 1.1 Command Entry Point

```bash
# Primary command
$ zerodb init

# Alternative (if no args)
$ zerodb
Welcome to ZeroLocal! Run 'zerodb init' to get started.

# Force re-init
$ zerodb init --reset
```

### 1.2 Complete Setup Flow

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                  ┃
┃      ███████╗███████╗██████╗  ██████╗            ┃
┃      ╚══███╔╝██╔════╝██╔══██╗██╔═══██╗           ┃
┃        ███╔╝ █████╗  ██████╔╝██║   ██║           ┃
┃       ███╔╝  ██╔══╝  ██╔══██╗██║   ██║           ┃
┃      ███████╗███████╗██║  ██║╚██████╔╝           ┃
┃      ╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝            ┃
┃                                                  ┃
┃      Local AI Database • Zero API Costs         ┃
┃                                                  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Welcome! Let's set up ZeroLocal in under 60 seconds.

╭─ System Requirements ────────────────────────────╮
│ ✓ macOS 11+ detected                             │
│ ✓ 8.0 GB RAM available (4.2 GB in use)          │
│ ✓ 127.5 GB disk space available                 │
│ ✓ Internet connection active                     │
╰──────────────────────────────────────────────────╯

Press Enter to continue or Ctrl+C to abort...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Step 1/5] Checking Docker...

⠹ Checking Docker installation...
✓ Docker installed (v24.0.5)
✓ Docker daemon running
✓ Docker Compose available (v2.20.0)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Step 2/5] Checking ports...

⠹ Scanning ports 5432, 6333, 8000, 8001, 9000, 9092, 3000...

✓ Port 5432  (PostgreSQL)  Available
✓ Port 6333  (Qdrant)      Available
✓ Port 8000  (API Server)  Available
✓ Port 8001  (Embeddings)  Available
✓ Port 9000  (MinIO)       Available
✓ Port 9092  (RedPanda)    Available
✓ Port 3000  (Dashboard)   Available

All ports available!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Step 3/5] Downloading models...

⠹ Downloading BAAI/bge-small-en-v1.5 (133 MB)...

Model: bge-small-en-v1.5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╸━━━━━━━━  78%
89 MB / 133 MB • 12.3 MB/s • ETA: 4s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Step 4/5] Starting services...

⠹ Starting Docker containers...

╭─ Service Status ─────────────────────────────────╮
│ ✓ postgres      starting   →  healthy   (8s)    │
│ ✓ qdrant        starting   →  healthy   (6s)    │
│ ✓ minio         starting   →  healthy   (4s)    │
│ ✓ redpanda      starting   →  healthy   (12s)   │
│ ✓ embeddings    starting   →  healthy   (15s)   │
│ ✓ zerodb-api    starting   →  healthy   (7s)    │
│ ✓ dashboard     starting   →  healthy   (5s)    │
╰──────────────────────────────────────────────────╯

All services healthy!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Step 5/5] Finalizing setup...

✓ Created data directories
✓ Generated configuration
✓ Set up CLI shortcuts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

╭─ Setup Complete! ────────────────────────────────╮
│                                                  │
│  🎉 ZeroLocal is ready!                          │
│                                                  │
│  Dashboard:  http://localhost:3000               │
│  API Docs:   http://localhost:8000/docs          │
│  API Server: http://localhost:8000               │
│                                                  │
│  Next steps:                                     │
│  1. Create your first project                    │
│  2. Upsert some vectors                          │
│  3. Run semantic search                          │
│                                                  │
│  Run 'zerodb --help' to see all commands         │
│                                                  │
╰──────────────────────────────────────────────────╯

Opening dashboard in your browser...

Setup completed in 58 seconds ⚡
```

---

## 2. Error Handling & Recovery

### 2.1 Docker Not Installed

```
[Step 1/5] Checking Docker...

⠹ Checking Docker installation...
✗ Docker not found

╭─ Docker Required ────────────────────────────────╮
│                                                  │
│  ZeroLocal requires Docker to run.               │
│                                                  │
│  Please install Docker Desktop:                  │
│  → https://www.docker.com/products/docker-desktop│
│                                                  │
│  Then run 'zerodb init' again.                   │
│                                                  │
╰──────────────────────────────────────────────────╯

[Open Docker website] [Exit]

? Open Docker website in browser? (Y/n):
```

### 2.2 Docker Daemon Not Running

```
[Step 1/5] Checking Docker...

⠹ Checking Docker installation...
✓ Docker installed (v24.0.5)
✗ Docker daemon not running

╭─ Docker Not Running ─────────────────────────────╮
│                                                  │
│  Docker is installed but not running.            │
│                                                  │
│  Please start Docker Desktop, then run:          │
│    $ zerodb init                                 │
│                                                  │
│  Or, attempt to start Docker now:                │
│    $ open -a Docker                              │
│                                                  │
╰──────────────────────────────────────────────────╯

? Try to start Docker now? (Y/n):
```

### 2.3 Port Conflicts

```
[Step 2/5] Checking ports...

⠹ Scanning ports...

✓ Port 5432  (PostgreSQL)  Available
✓ Port 6333  (Qdrant)      Available
✗ Port 8000  (API Server)  IN USE by process 1234 (python3)
✓ Port 8001  (Embeddings)  Available
✗ Port 9000  (MinIO)       IN USE by process 5678 (minio)
✓ Port 9092  (RedPanda)    Available
✓ Port 3000  (Dashboard)   Available

╭─ Port Conflicts Detected ────────────────────────╮
│                                                  │
│  Some ports are in use by other processes:       │
│                                                  │
│  Port 8000: python3 (PID 1234)                   │
│    $ kill 1234                                   │
│                                                  │
│  Port 9000: minio (PID 5678)                     │
│    $ kill 5678                                   │
│                                                  │
╰──────────────────────────────────────────────────╯

What would you like to do?
  1. Kill conflicting processes (recommended)
  2. Use alternative ports (8080, 9001)
  3. Skip conflicting services
  4. Abort setup

Choice (1-4): _
```

**If user chooses option 1:**
```
⠹ Stopping conflicting processes...
✓ Killed process 1234 (python3)
✓ Killed process 5678 (minio)

Retrying port check...
✓ All ports now available!

Continuing setup...
```

**If user chooses option 2:**
```
Using alternative ports:
  API Server: 8000 → 8080
  MinIO:      9000 → 9001

Updated configuration saved.

Continuing setup...
```

### 2.4 Insufficient Resources

```
[Step 1/5] System check...

╭─ Resource Warning ───────────────────────────────╮
│                                                  │
│  ⚠  Low available RAM detected                   │
│                                                  │
│  Available: 2.1 GB                               │
│  Required:  4.0 GB (minimum)                     │
│  Recommended: 8.0 GB                             │
│                                                  │
│  ZeroLocal may run slowly or fail to start.      │
│                                                  │
╰──────────────────────────────────────────────────╯

What would you like to do?
  1. Continue anyway (not recommended)
  2. Use lightweight mode (fewer services)
  3. Abort and free up RAM first

Choice (1-3): _
```

**If user chooses option 2:**
```
Lightweight mode enabled:
  ✓ PostgreSQL (required)
  ✓ Qdrant (required)
  ✓ API Server (required)
  ✓ Dashboard (required)
  ✗ MinIO (disabled - file storage unavailable)
  ✗ RedPanda (disabled - events unavailable)
  ✗ Embeddings (disabled - use cloud API for embeddings)

Memory required: ~2.5 GB

? Proceed with lightweight mode? (Y/n):
```

### 2.5 Model Download Failure

```
[Step 3/5] Downloading models...

⠹ Downloading BAAI/bge-small-en-v1.5 (133 MB)...

Model: bge-small-en-v1.5
━━━━━━━━━━━━━━━╸━━━━━━━━━━━━━━━━━━━━━━  45%
60 MB / 133 MB • Connection lost

✗ Download failed: Network timeout

╭─ Model Download Failed ──────────────────────────╮
│                                                  │
│  Failed to download embeddings model.            │
│                                                  │
│  You can:                                        │
│  1. Retry download                               │
│  2. Skip embeddings (use cloud API)              │
│  3. Download manually later                      │
│                                                  │
│  Note: Without local embeddings, you'll need     │
│  a ZeroDB Cloud API key for embeddings.          │
│                                                  │
╰──────────────────────────────────────────────────╯

? What would you like to do? (1-3): _
```

### 2.6 Service Startup Failure

```
[Step 4/5] Starting services...

╭─ Service Status ─────────────────────────────────╮
│ ✓ postgres      starting   →  healthy   (8s)    │
│ ✓ qdrant        starting   →  healthy   (6s)    │
│ ✓ minio         starting   →  healthy   (4s)    │
│ ✗ redpanda      starting   →  unhealthy (30s)   │
│ ⏸ embeddings    waiting...                       │
│ ⏸ zerodb-api    waiting...                       │
│ ⏸ dashboard     waiting...                       │
╰──────────────────────────────────────────────────╯

✗ Service failed to start: redpanda

╭─ Service Failure ────────────────────────────────╮
│                                                  │
│  RedPanda failed to start after 30 seconds.      │
│                                                  │
│  Common causes:                                  │
│  • Port conflict (9092)                          │
│  • Insufficient memory                           │
│  • Corrupted data directory                      │
│                                                  │
│  View logs:                                      │
│    $ zerodb logs redpanda                        │
│                                                  │
╰──────────────────────────────────────────────────╯

What would you like to do?
  1. View logs and retry
  2. Skip RedPanda (events unavailable)
  3. Reset RedPanda data and retry
  4. Abort setup

Choice (1-4): _
```

---

## 3. Interactive Commands

### 3.1 `zerodb doctor` - Diagnostics

```bash
$ zerodb doctor

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ZeroLocal Diagnostics                           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Running comprehensive health check...

╭─ System ─────────────────────────────────────────╮
│ ✓ Operating System: macOS 14.1 (arm64)          │
│ ✓ Docker: 24.0.5 (running)                       │
│ ✓ Docker Compose: 2.20.0                         │
│ ✓ Python: 3.11.5                                 │
│ ✓ Node.js: 20.9.0                                │
╰──────────────────────────────────────────────────╯

╭─ Resources ──────────────────────────────────────╮
│ ✓ RAM: 8.0 GB total, 5.3 GB available           │
│ ✓ Disk: 500 GB total, 127.5 GB available        │
│ ✓ CPU: 8 cores @ 3.2 GHz                        │
╰──────────────────────────────────────────────────╯

╭─ Ports ──────────────────────────────────────────╮
│ ✓ 5432  PostgreSQL  Available                    │
│ ✓ 6333  Qdrant      Available                    │
│ ✗ 8000  API Server  IN USE (PID 1234: python3)  │
│ ✓ 8001  Embeddings  Available                    │
│ ✓ 9000  MinIO       Available                    │
│ ✓ 9092  RedPanda    Available                    │
│ ✓ 3000  Dashboard   Available                    │
╰──────────────────────────────────────────────────╯

╭─ Services ───────────────────────────────────────╮
│ ✓ postgres      healthy    (uptime: 2h 15m)     │
│ ✓ qdrant        healthy    (uptime: 2h 14m)     │
│ ⚠ zerodb-api    unhealthy  (port conflict)       │
│ ✓ minio         healthy    (uptime: 2h 14m)     │
│ ✓ redpanda      healthy    (uptime: 2h 13m)     │
│ ✓ embeddings    healthy    (uptime: 2h 12m)     │
│ ✗ dashboard     not running                      │
╰──────────────────────────────────────────────────╯

╭─ Configuration ──────────────────────────────────╮
│ ✓ Config file: ~/.zerolocal/config.yml          │
│ ✓ Data directory: ~/.zerolocal/data (8.5 GB)    │
│ ✓ Logs directory: ~/.zerolocal/logs (142 MB)    │
│ ⚠ Cloud API key not configured                   │
╰──────────────────────────────────────────────────╯

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Issues detected: 3

1. 🔴 Critical: Port 8000 conflict
   Process 1234 (/usr/bin/python3 -m http.server 8000)
   is using port 8000, preventing API server from starting.

   Fix:
     $ kill 1234
     $ zerodb restart zerodb-api

2. 🟡 Warning: Dashboard not running
   Dashboard container is stopped.

   Fix:
     $ zerodb start dashboard

3. 🟡 Warning: Cloud API key not set
   Cloud sync features unavailable.

   Fix:
     $ zerodb config set cloud.api_key YOUR_KEY_HERE
     Or get a key: https://www.ainative.studio/api-keys

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

? Auto-fix issues? (Y/n):
```

**If user selects "Yes":**
```
⠹ Applying fixes...

✓ Killed process 1234
✓ Restarted zerodb-api (now healthy)
✓ Started dashboard (now healthy)

⚠ Cloud API key requires manual setup.
  Visit: https://www.ainative.studio/api-keys

All fixable issues resolved!

Run 'zerodb doctor' again to verify.
```

### 3.2 `zerodb config` - Configuration

```bash
$ zerodb config

╭─ ZeroLocal Configuration ────────────────────────╮
│                                                  │
│  Installation: /Users/dev/.zerolocal             │
│  Version: 1.0.0                                  │
│  Environment: local                              │
│                                                  │
╰──────────────────────────────────────────────────╯

╭─ Services ───────────────────────────────────────╮
│  postgres.port:      5432                        │
│  qdrant.port:        6333                        │
│  api.port:           8000                        │
│  embeddings.port:    8001                        │
│  minio.port:         9000                        │
│  redpanda.port:      9092                        │
│  dashboard.port:     3000                        │
╰──────────────────────────────────────────────────╯

╭─ Resources ──────────────────────────────────────╮
│  postgres.memory:    512m                        │
│  qdrant.memory:      1g                          │
│  embeddings.memory:  2g                          │
│  total_memory:       5.5g                        │
╰──────────────────────────────────────────────────╯

╭─ Cloud Sync ─────────────────────────────────────╮
│  cloud.enabled:      false                       │
│  cloud.api_key:      not set                     │
│  cloud.api_url:      https://api.ainative.studio │
╰──────────────────────────────────────────────────╯

Commands:
  zerodb config get <key>             Get value
  zerodb config set <key> <value>     Set value
  zerodb config edit                  Edit in $EDITOR
  zerodb config reset                 Reset to defaults
```

**Set a value:**
```bash
$ zerodb config set cloud.api_key sk_test_abc123

✓ Configuration updated: cloud.api_key
✓ Cloud sync enabled

Restart required for some changes.
Run: zerodb restart
```

**Interactive edit:**
```bash
$ zerodb config edit

# Opens in $EDITOR (vim/nano/etc)
# User edits YAML, saves, exits

⠹ Validating configuration...
✓ Configuration valid
✓ Changes saved

? Restart services now? (Y/n):
```

### 3.3 `zerodb open` - Open Dashboard

```bash
$ zerodb open

Opening ZeroLocal dashboard...

✓ Dashboard: http://localhost:3000
✓ Opened in default browser

Press Ctrl+C to return to terminal.
```

### 3.4 `zerodb logs` - View Logs

```bash
$ zerodb logs

# Follow all logs (default)
⠹ Following logs from all services...
Press Ctrl+C to stop

[postgres]    LOG:  database system is ready to accept connections
[qdrant]      INFO: Starting Qdrant HTTP server on 0.0.0.0:6333
[api]         INFO: Application startup complete
[dashboard]   ready - started server on 0.0.0.0:3000

# Follow specific service
$ zerodb logs api -f

[12:34:56] INFO     Application startup complete
[12:34:57] INFO     GET /health - 200 OK (2ms)
[12:34:58] INFO     POST /v1/projects - 201 Created (45ms)

# Show last N lines
$ zerodb logs redpanda --tail 50

# No follow (dump and exit)
$ zerodb logs postgres --no-follow
```

### 3.5 `zerodb status` - Service Status

```bash
$ zerodb status

╭─ ZeroLocal Status ───────────────────────────────╮
│                                                  │
│  Overall: ✓ Healthy                              │
│  Uptime: 2 hours 15 minutes                      │
│                                                  │
╰──────────────────────────────────────────────────╯

╭─ Services ───────────────────────────────────────╮
│                                                  │
│  Service      Status     Uptime    CPU   Memory │
│  ────────────────────────────────────────────────│
│  postgres     ✓ healthy  2h 15m    5%    412 MB │
│  qdrant       ✓ healthy  2h 14m    8%    856 MB │
│  minio        ✓ healthy  2h 14m    2%    124 MB │
│  redpanda     ✓ healthy  2h 13m    12%   923 MB │
│  embeddings   ✓ healthy  2h 12m    45%   1.8 GB │
│  zerodb-api   ✓ healthy  2h 10m    3%    245 MB │
│  dashboard    ✓ healthy  2h 10m    1%    87 MB  │
│                                                  │
│  Total                            76%   4.2 GB  │
│                                                  │
╰──────────────────────────────────────────────────╯

╭─ Endpoints ──────────────────────────────────────╮
│  Dashboard:  http://localhost:3000               │
│  API:        http://localhost:8000               │
│  API Docs:   http://localhost:8000/docs          │
│  Qdrant:     http://localhost:6333/dashboard     │
│  MinIO:      http://localhost:9001               │
╰──────────────────────────────────────────────────╯

╭─ Quick Actions ──────────────────────────────────╮
│  zerodb open        Open dashboard               │
│  zerodb logs        View logs                    │
│  zerodb restart     Restart services             │
│  zerodb stop        Stop all services            │
╰──────────────────────────────────────────────────╯
```

---

## 4. Progress Indicators

### 4.1 Spinner (Indeterminate)

```python
from rich.spinner import Spinner

spinner_styles = {
    "dots": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",  # Default
    "line": "⎯⎟⎜⎯⎟⎜",
    "arc": "◜◠◝◞◡◟",
    "arrow": "←↖↑↗→↘↓↙",
}

# Usage
with console.status("⠹ Checking Docker...", spinner="dots"):
    check_docker()
```

### 4.2 Progress Bar (Determinate)

```python
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn

progress = Progress(
    "[progress.description]{task.description}",
    BarColumn(),
    "[progress.percentage]{task.percentage:>3.0f}%",
    DownloadColumn(),
    TransferSpeedColumn(),
    "•",
    TimeRemainingColumn(),
)

# Download progress
with progress:
    task = progress.add_task("Downloading model", total=133_000_000)
    while not progress.finished:
        progress.update(task, advance=1_024_000)  # 1 MB chunks
```

### 4.3 Service Health Animation

```
Frame 1 (t=0s):
╭─ Starting Services ──────────────────────────────╮
│ ⏳ postgres      starting...                     │
│ ⏳ qdrant        starting...                     │
│ ⏳ minio         starting...                     │
│ ⏸  redpanda      waiting...                      │
│ ⏸  embeddings    waiting...                      │
│ ⏸  api           waiting...                      │
│ ⏸  dashboard     waiting...                      │
╰──────────────────────────────────────────────────╯

Frame 2 (t=5s):
╭─ Starting Services ──────────────────────────────╮
│ ⏳ postgres      starting... (5s)                │
│ ⏳ qdrant        starting... (5s)                │
│ ⏳ minio         starting... (5s)                │
│ ⏸  redpanda      waiting...                      │
│ ⏸  embeddings    waiting...                      │
│ ⏸  api           waiting...                      │
│ ⏸  dashboard     waiting...                      │
╰──────────────────────────────────────────────────╯

Frame 3 (t=8s):
╭─ Starting Services ──────────────────────────────╮
│ ✓  postgres      healthy    (8s)                │
│ ✓  qdrant        healthy    (6s)                │
│ ✓  minio         healthy    (4s)                │
│ ⏳ redpanda      starting... (2s)                │
│ ⏳ embeddings    starting... (1s)                │
│ ⏸  api           waiting...                      │
│ ⏸  dashboard     waiting...                      │
╰──────────────────────────────────────────────────╯

Frame 4 (t=20s):
╭─ Starting Services ──────────────────────────────╮
│ ✓  postgres      healthy    (8s)                │
│ ✓  qdrant        healthy    (6s)                │
│ ✓  minio         healthy    (4s)                │
│ ✓  redpanda      healthy    (12s)               │
│ ✓  embeddings    healthy    (15s)               │
│ ✓  api           healthy    (7s)                │
│ ✓  dashboard     healthy    (5s)                │
╰──────────────────────────────────────────────────╯
```

---

## 5. Color Scheme

### 5.1 Status Colors

```python
# Rich color names
STATUS_COLORS = {
    "success": "green",
    "error": "red",
    "warning": "yellow",
    "info": "cyan",
    "dim": "dim",
    "highlight": "bright_blue",
}

# Symbols
SYMBOLS = {
    "success": "✓",
    "error": "✗",
    "warning": "⚠",
    "info": "ℹ",
    "spinner": "⠹",
    "arrow": "→",
    "bullet": "•",
}
```

### 5.2 Console Output Examples

```python
# Success
console.print("✓ Docker installed", style="green")

# Error
console.print("✗ Port conflict detected", style="red bold")

# Warning
console.print("⚠ Low memory available", style="yellow")

# Info
console.print("ℹ Setup completed in 58 seconds", style="cyan")

# Dim (less important)
console.print("Press Ctrl+C to abort...", style="dim")
```

---

## 6. Implementation

### 6.1 Tech Stack

**Framework:** Typer (current)
**UI Library:** Rich (current)
**Additional:** Click (prompts), questionary (interactive)

### 6.2 Project Structure

```
cli/
├── commands/
│   ├── __init__.py
│   ├── init.py         # Main setup wizard
│   ├── doctor.py       # Diagnostics
│   ├── config.py       # Configuration
│   ├── local.py        # Service control
│   ├── cloud.py        # Cloud sync
│   └── utils.py        # Shared utilities
├── ui/
│   ├── __init__.py
│   ├── progress.py     # Progress bars/spinners
│   ├── tables.py       # Table formatting
│   ├── prompts.py      # Interactive prompts
│   └── theme.py        # Colors and styling
├── checks/
│   ├── __init__.py
│   ├── docker.py       # Docker checks
│   ├── ports.py        # Port availability
│   ├── resources.py    # RAM/disk checks
│   └── services.py     # Service health
├── config.py           # Config management
├── main.py             # CLI entry point
└── __init__.py
```

### 6.3 Key Functions

**init.py:**
```python
@app.command()
def init(
    reset: bool = typer.Option(False, "--reset", help="Reset existing setup"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmations"),
    lightweight: bool = typer.Option(False, "--lightweight", help="Use minimal services"),
):
    """Initialize ZeroLocal environment"""

    # Show welcome screen
    show_welcome()

    # Step 1: System checks
    check_system_requirements()

    # Step 2: Docker check
    check_docker()

    # Step 3: Port check
    check_ports(auto_fix=True)

    # Step 4: Download models
    download_models(skip_if_exists=True)

    # Step 5: Start services
    start_services(lightweight=lightweight)

    # Step 6: Verify health
    verify_health()

    # Success!
    show_success()
    open_dashboard()
```

**doctor.py:**
```python
@app.command()
def doctor(
    fix: bool = typer.Option(False, "--fix", help="Auto-fix issues"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
):
    """Diagnose and fix issues"""

    issues = []

    # Run all checks
    issues.extend(check_system())
    issues.extend(check_ports())
    issues.extend(check_services())
    issues.extend(check_config())

    # Display results
    display_diagnostic_results(issues)

    # Offer to fix
    if issues and (fix or typer.confirm("Auto-fix issues?")):
        fix_issues(issues)
```

---

## 7. Testing

### 7.1 Test Scenarios

**Happy Path:**
- [ ] Fresh install with no conflicts
- [ ] All services start successfully
- [ ] Dashboard opens automatically

**Error Scenarios:**
- [ ] Docker not installed
- [ ] Docker daemon not running
- [ ] Port conflicts (various)
- [ ] Insufficient RAM
- [ ] Insufficient disk space
- [ ] Network timeout during model download
- [ ] Service fails to start

**Edge Cases:**
- [ ] User aborts during setup (Ctrl+C)
- [ ] Retry after failure
- [ ] Reset existing installation
- [ ] Lightweight mode
- [ ] Alternative ports

### 7.2 User Acceptance Criteria

- [ ] Setup completes in < 60 seconds (no conflicts)
- [ ] Clear error messages with actionable fixes
- [ ] Progress visible at all times
- [ ] Can abort cleanly at any point
- [ ] No leftover processes/containers after abort
- [ ] Auto-recovery works for common issues

---

## 8. Future Enhancements

### Phase 2 Features

**Interactive Tutorials:**
```bash
$ zerodb tutorial

Choose a tutorial:
  1. Create your first project
  2. Upsert and search vectors
  3. Use agent memory
  4. Upload files to storage
  5. Stream events
  6. Sync with cloud

Selection: _
```

**Project Templates:**
```bash
$ zerodb project create --template rag

Creating RAG project from template...
  ✓ Created project "my-rag-app"
  ✓ Created collection "documents" (768 dims)
  ✓ Uploaded sample documents (3)
  ✓ Generated embeddings

Next steps:
  $ zerodb project show my-rag-app
  $ curl http://localhost:8000/v1/projects/{id}/database/vectors/search
```

**Health Monitoring:**
```bash
$ zerodb monitor

Live monitoring (press 'q' to quit)

╭─ Service Health ─────────────────────────────────╮
│ postgres     ✓  Response: 2ms   Load: 5%        │
│ qdrant       ✓  Response: 5ms   Load: 8%        │
│ api          ✓  Response: 3ms   Load: 12%       │
╰──────────────────────────────────────────────────╯

╭─ Resource Usage ─────────────────────────────────╮
│ CPU:    ████████░░ 45%     RAM: ███████░░░ 4.2GB │
│ Disk:   ████░░░░░░ 8.5GB   Net: ↓ 2MB/s ↑ 1MB/s │
╰──────────────────────────────────────────────────╯
```

---

**Next Steps:**
1. Implement init wizard
2. Add doctor command
3. Build progress UI components
4. Add error recovery logic
5. User testing

Refs #1133
