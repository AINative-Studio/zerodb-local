# ZeroLocal System Architecture

**Version**: 1.0
**Status**: Design Phase
**Last Updated**: 2026-02-10
**Related Issue**: #1133

---

## Executive Summary

### Vision
Transform ZeroLocal into a world-class developer experience that serves as the primary "moat" strategy for ZeroDB Cloud adoption. Make developers love the local experience so much that choosing ZeroDB Cloud for production becomes the natural, inevitable choice.

### Strategic Objective
**The LocalStack Model**: Just as LocalStack dominates AWS local development and drives production AWS adoption, ZeroLocal will become the de facto standard for local vector database development, driving ZeroDB Cloud adoption.

### Success Metrics
- **Setup Time**: < 60 seconds (from download to running)
- **Developer NPS**: > 50
- **Cloud Conversion Rate**: > 20% of local users
- **GitHub Stars Growth**: 100+ per month
- **Time to First Success**: < 5 minutes

### Key Differentiators
1. Native installers (not manual Docker setup)
2. Beautiful dashboard (not CLI-only)
3. Perfect API/UI parity with production
4. Agent-first (AgentX) design
5. Zero-cost local embeddings

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Current State Analysis](#2-current-state-analysis)
3. [Target Architecture](#3-target-architecture)
4. [Native Installer Architecture](#4-native-installer-architecture)
5. [Dashboard Architecture](#5-dashboard-architecture)
6. [CLI Wizard Architecture](#6-cli-wizard-architecture)
7. [Technology Stack](#7-technology-stack)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [Success Metrics & KPIs](#9-success-metrics--kpis)
10. [Risk Assessment](#10-risk-assessment)

---

## 1. System Overview

### 1.1 Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ZeroDB Local Stack                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐         ┌──────────────┐                   │
│  │  Dashboard  │◄────────┤   API Server │                   │
│  │ (Next.js)   │  REST   │   (FastAPI)  │                   │
│  └─────────────┘         └───────┬──────┘                   │
│   localhost:3000                 │                           │
│                                  │                           │
│          ┌───────────────────────┼───────────────────┐       │
│          │                       │                   │       │
│          ▼                       ▼                   ▼       │
│  ┌──────────────┐      ┌─────────────┐     ┌─────────────┐  │
│  │  PostgreSQL  │      │   Qdrant    │     │    MinIO    │  │
│  │  + pgvector  │      │  (Vectors)  │     │   (Files)   │  │
│  └──────────────┘      └─────────────┘     └─────────────┘  │
│   localhost:5432        localhost:6333      localhost:9000  │
│                                                              │
│          ┌───────────────────────┬──────────────────┐        │
│          │                       │                  │        │
│          ▼                       ▼                  ▼        │
│  ┌──────────────┐      ┌─────────────┐     ┌─────────────┐  │
│  │   RedPanda   │      │ Embeddings  │     │    CLI      │  │
│  │   (Events)   │      │   (BAAI)    │     │   (Typer)   │  │
│  └──────────────┘      └─────────────┘     └─────────────┘  │
│   localhost:9092        localhost:8001      zerodb command  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- 7 Docker containers
- FastAPI backend (128 endpoints)
- Next.js dashboard (in development)
- Python CLI (Typer-based)
- PostgreSQL (with pgvector extension)
- Qdrant (vector search)
- MinIO (S3-compatible storage)
- RedPanda (Kafka-compatible streaming)
- Local embeddings (BAAI BGE models)

### 1.2 Target User Personas

**Primary Persona: "DevOps Dan"**
- Wants to test AI workflows locally before deploying
- Values reproducibility and consistency
- Budget-conscious (prefers local dev, cloud prod)
- Technical but time-constrained

**Secondary Persona: "AI Engineer Amy"**
- Building RAG applications and AI agents
- Needs fast iteration cycles
- Wants production-like environment locally
- Agent/LLM framework user (LangChain, CrewAI, etc.)

**Tertiary Persona: "Startup Steve"**
- Cost-sensitive early-stage founder
- Wants to validate product-market fit locally
- Plans to scale to cloud when successful
- Needs simple, reliable tools

---

## 2. Current State Analysis

### 2.1 Current Setup Process (10+ minutes)

**Manual Steps Required:**
1. Clone repository (1 min)
2. Install Docker Desktop (5-10 min if not installed)
3. Copy `.env.local.example` to `.env.local` (30 sec)
4. Edit environment variables (2 min)
5. Run `docker-compose up -d` (2-3 min)
6. Wait for all services to be healthy (2 min)
7. Verify each service individually (2 min)
8. Install CLI separately `cd cli && pip install -e .` (1 min)
9. Configure CLI with local endpoint (1 min)

**Total Time:** 10-15 minutes
**Failure Points:** 7 (Docker install, env config, port conflicts, health checks, etc.)

### 2.2 Pain Points

| Pain Point | Impact | Severity |
|------------|--------|----------|
| No automated installer | High friction, many give up | CRITICAL |
| Manual Docker setup | Requires technical knowledge | HIGH |
| Port conflicts not detected | Silent failures | HIGH |
| No dashboard (yet) | CLI-only intimidating | CRITICAL |
| No setup wizard | Users miss configuration steps | HIGH |
| No health validation | Users don't know if it's working | MEDIUM |
| Separate CLI install | Extra step, easy to forget | MEDIUM |
| No auto-update mechanism | Users run outdated versions | LOW |

### 2.3 Competitor Benchmark

| Tool | Setup Time | Installer | Dashboard | Cloud Parity | Rating |
|------|-----------|-----------|-----------|--------------|--------|
| **Docker Desktop** | 60s | Native (.dmg, .exe) | ⭐⭐⭐⭐⭐ | N/A | 5/5 |
| **LocalStack** | 2 min | brew/pip + docker | ⭐⭐⭐⭐ | 95% | 4.5/5 |
| **Supabase Local** | 5 min | CLI + Docker | ⭐⭐⭐ | 90% | 4/5 |
| **Weaviate Local** | 5 min | Docker Compose | ⭐⭐ | 85% | 3/5 |
| **ZeroLocal (Current)** | 10 min | Manual Docker | ❌ None | 95% | 2/5 |
| **ZeroLocal (Target)** | 60s | Native + brew | ⭐⭐⭐⭐⭐ | 100% | 5/5 |

### 2.4 What Works Well

- Docker-based stack is reliable
- API parity with cloud (128 endpoints)
- Local embeddings eliminate API costs
- Comprehensive services (PostgreSQL, Qdrant, MinIO, RedPanda)
- Good documentation
- CLI has solid command structure

---

## 3. Target Architecture

### 3.1 60-Second Setup Flow

```
User Journey: Download → Run → Success (< 60 seconds)

┌──────────────┐
│   Download   │  Download native installer from website
│  Installer   │  macOS: ZeroLocal.dmg (200MB)
│              │  Windows: ZeroLocal-Setup.exe (220MB)
│              │  Linux: zerolocal.AppImage (210MB)
└──────┬───────┘
       │ 10 seconds
       ▼
┌──────────────┐
│   Install    │  Drag-and-drop (macOS) or Next-Next-Finish (Windows)
│   & Launch   │  Includes: Docker runtime, services, CLI, dashboard
└──────┬───────┘
       │ 20 seconds
       ▼
┌──────────────┐
│  Auto Setup  │  Wizard detects system, checks ports, configures
│   Wizard     │  Auto-resolves conflicts, downloads models
└──────┬───────┘
       │ 20 seconds
       ▼
┌──────────────┐
│  Dashboard   │  Dashboard opens automatically at localhost:3000
│    Opens     │  Shows all services healthy with green checkmarks
└──────┬───────┘
       │ 5 seconds
       ▼
┌──────────────┐
│   Success!   │  User can immediately start creating projects
│              │  Interactive tutorial guides first steps
└──────────────┘

Total: 55 seconds
```

### 3.2 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   Native Application Shell                       │
│  (Electron/Tauri - Platform-specific packaging)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │              Dashboard UI (Next.js)                     │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │     │
│  │  │ Projects │ │ Vectors  │ │  Tables  │ │  Files   │  │     │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │     │
│  │  │  Memory  │ │  Events  │ │   Sync   │ │ Settings │  │     │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │     │
│  └────────────────────────────────────────────────────────┘     │
│                          │ HTTP/WebSocket                        │
│  ┌────────────────────────────────────────────────────────┐     │
│  │         Service Orchestrator (Rust/Go)                  │     │
│  │  - Docker runtime management                            │     │
│  │  - Health monitoring                                    │     │
│  │  - Port conflict resolution                             │     │
│  │  - Auto-updates                                         │     │
│  │  - System tray integration                              │     │
│  └────────────────────────────────────────────────────────┘     │
│                          │                                       │
│  ┌────────────────────────────────────────────────────────┐     │
│  │      Embedded Docker Runtime (or use system Docker)     │     │
│  │                                                         │     │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐         │     │
│  │  │ PostgreSQL │ │  Qdrant    │ │   MinIO    │         │     │
│  │  └────────────┘ └────────────┘ └────────────┘         │     │
│  │                                                         │     │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐         │     │
│  │  │  RedPanda  │ │ Embeddings │ │  API Server│         │     │
│  │  └────────────┘ └────────────┘ └────────────┘         │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ Optional Cloud Sync
                          ▼
              ┌─────────────────────┐
              │  ZeroDB Cloud API   │
              │ api.ainative.studio │
              └─────────────────────┘
```

### 3.3 Component Breakdown

#### 3.3.1 Native Application Shell
**Technology**: Tauri (preferred) or Electron
**Responsibilities:**
- Platform-specific packaging (.dmg, .exe, .AppImage)
- System tray integration
- Auto-update mechanism
- Native file system access
- OS-level notifications
- Embedded web view for dashboard

**Why Tauri over Electron:**
- Smaller binary size (10-20MB vs 100MB+)
- Lower memory footprint (Rust vs Node.js)
- Better security model
- Native OS integration
- Still supports web technologies for UI

#### 3.3.2 Service Orchestrator
**Technology**: Rust or Go
**Responsibilities:**
- Docker container lifecycle management
- Health check aggregation
- Port conflict detection and resolution
- Automatic service recovery
- Resource monitoring
- Log aggregation and rotation
- Update management

**API Design:**
```rust
// Service Orchestrator API
POST   /api/orchestrator/start
POST   /api/orchestrator/stop
GET    /api/orchestrator/status
GET    /api/orchestrator/health
POST   /api/orchestrator/restart/{service}
GET    /api/orchestrator/logs/{service}
POST   /api/orchestrator/update
GET    /api/orchestrator/config
PUT    /api/orchestrator/config
```

#### 3.3.3 Dashboard (Next.js)
**Framework**: Next.js 14 with App Router
**UI Library**: Radix UI + Tailwind CSS (already in use)
**State Management**: TanStack Query (React Query)
**Real-time**: WebSocket + Server-Sent Events

**Key Features:**
- Project management dashboard
- Vector collection browser
- Real-time sync status
- Visual query builder
- Performance metrics
- Resource usage graphs
- Error tracking and alerts
- Interactive tutorials

#### 3.3.4 CLI (Enhanced)
**Framework**: Typer (current) + Rich
**Distribution**: Bundled with installer + standalone pip package

**Enhanced Commands:**
```bash
# Core commands (existing)
zerodb local up/down/status/logs
zerodb cloud login/sync/pull

# New commands
zerodb init                    # Interactive setup wizard
zerodb doctor                  # Diagnose and fix issues
zerodb update                  # Update all components
zerodb open                    # Open dashboard in browser
zerodb config                  # Configure settings
zerodb backup/restore          # Data management
zerodb export/import           # Project portability
```

---

## 4. Native Installer Architecture

### 4.1 macOS Installer (.dmg)

**Package Structure:**
```
ZeroLocal.dmg
├── ZeroLocal.app/
│   ├── Contents/
│   │   ├── MacOS/
│   │   │   └── zerolocal-binary (Tauri app)
│   │   ├── Resources/
│   │   │   ├── icon.icns
│   │   │   ├── docker-runtime/ (optional embedded)
│   │   │   ├── services/ (Docker images as .tar)
│   │   │   └── cli/ (Python CLI bundled)
│   │   └── Info.plist
│   └── CLI Installer.pkg (optional separate CLI install)
└── README.txt
```

**Installation Flow:**
1. User downloads `ZeroLocal.dmg` (200MB)
2. Opens DMG, drags `ZeroLocal.app` to Applications
3. First launch triggers:
   - Check for Docker Desktop (use if exists)
   - If not found, offer to install embedded runtime
   - Load pre-packaged Docker images (skip pull time)
   - Run setup wizard
   - Open dashboard

**Technical Details:**
- **Signing**: Apple Developer ID certificate required
- **Notarization**: Required for Gatekeeper
- **Permissions**: Request only necessary permissions upfront
- **Updates**: Sparkle framework for auto-updates

### 4.2 Windows Installer (.exe)

**Package Structure:**
```
ZeroLocal-Setup.exe (Inno Setup or NSIS)
├── Setup Files/
│   ├── zerolocal.exe (Tauri app)
│   ├── docker-runtime/ (Docker Desktop or embedded)
│   ├── services/ (Pre-loaded images)
│   └── cli/ (Bundled Python CLI)
└── Uninstaller/
```

**Installation Flow:**
1. User downloads `ZeroLocal-Setup.exe` (220MB)
2. Runs installer with admin privileges
3. Wizard prompts:
   - Installation location
   - Start menu shortcuts
   - Desktop shortcut
   - Add to PATH
4. Installs Docker Desktop (if needed) or uses existing
5. Loads Docker images
6. Launches setup wizard
7. Opens dashboard

**Technical Details:**
- **Signing**: Authenticode certificate required
- **Installer**: Inno Setup (simpler) or NSIS (more flexible)
- **Registry**: Minimal registry usage
- **Updates**: Built-in update mechanism

### 4.3 Linux Installer (AppImage + .deb + .rpm)

**AppImage Structure:**
```
ZeroLocal.AppImage (self-contained)
├── AppRun (entry script)
├── zerolocal-binary
├── usr/
│   ├── bin/
│   │   └── zerodb (CLI)
│   ├── share/
│   │   ├── applications/
│   │   │   └── zerolocal.desktop
│   │   └── icons/
│   └── lib/
│       └── docker/ (optional embedded runtime)
└── services/ (pre-loaded images)
```

**Distribution Formats:**
1. **AppImage**: Universal, no root required
2. **.deb**: For Debian/Ubuntu
3. **.rpm**: For Fedora/RHEL
4. **AUR package**: For Arch Linux
5. **snap/flatpak**: Sandboxed options

**Installation Flow:**
1. Download AppImage (210MB)
2. `chmod +x ZeroLocal.AppImage`
3. `./ZeroLocal.AppImage` (first run setup)
4. Desktop integration offered
5. Setup wizard runs
6. Dashboard opens

### 4.4 Alternative: Homebrew/Chocolatey (Quick Install)

**Homebrew (macOS/Linux):**
```bash
brew install zerolocal
# Automatically installs Docker, CLI, and launches setup
```

**Chocolatey (Windows):**
```bash
choco install zerolocal
# Same automated experience
```

**Implementation:**
- Tap/feed hosted on GitHub
- Downloads and extracts native package
- Runs post-install scripts
- Launches app and setup wizard

---

## 5. Dashboard Architecture

### 5.1 Dashboard Technology Stack

**Frontend Framework:**
- **Next.js 14** (App Router with React Server Components)
- **TypeScript** (strict mode)
- **Tailwind CSS** (utility-first styling)
- **Radix UI** (accessible component primitives)
- **Lucide React** (icon library)

**State Management:**
- **TanStack Query** (server state, caching)
- **Zustand** (local UI state)
- **Context API** (theme, auth)

**Data Visualization:**
- **Recharts** (charts and graphs)
- **React Flow** (node/edge visualizations for sync flows)

**Real-time:**
- **WebSocket** (health status, sync progress)
- **Server-Sent Events** (log streaming)

### 5.2 Dashboard Pages & Features

#### Home / Overview
```
┌─────────────────────────────────────────────────────────────┐
│  ZeroLocal Dashboard                          ⚙️ Settings   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  System Status: ✅ All Services Healthy                      │
│                                                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ ✅ API   │ │ ✅ DB   │ │ ✅ Vec  │ │ ✅ S3   │           │
│  │ 8000    │ │ 5432   │ │ 6333   │ │ 9000   │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│                                                              │
│  Quick Actions:                                              │
│  [+ New Project]  [📊 View Metrics]  [🔄 Sync to Cloud]     │
│                                                              │
│  Recent Projects:                                            │
│  📁 my-rag-app          5 collections    Last sync: 2h ago  │
│  📁 chatbot-backend     2 collections    Never synced       │
│  📁 agent-memory        8 collections    Syncing now...     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Projects View
- Create, update, delete projects
- Project settings (embeddings model, dimensions, etc.)
- Link to cloud project
- Export/import project bundle
- Usage statistics

#### Vectors View
- Browse collections by project
- Search vectors (semantic search UI)
- Inspect individual vectors
- Upload vectors (CSV, JSON, JSONL)
- Performance metrics (queries/sec, latency)

#### Tables View (NoSQL)
- Create/delete tables
- Browse rows with pagination
- Query builder UI
- Insert/update rows
- Schema viewer

#### Files View (S3-compatible)
- File browser UI
- Upload/download files
- Generate presigned URLs
- Storage usage visualization
- File metadata viewer

#### Memory View (Agent Memory)
- Conversation trees
- Memory search
- Context window visualization
- Agent session history

#### Events View (Streaming)
- Event log browser
- Create/consume events
- Topic management
- Real-time event stream

#### Sync View
- Sync status dashboard
- Conflict resolution UI
- Change history
- Plan vs apply view
- Cloud project linking

#### Settings
- Environment configuration
- Service settings (ports, resources)
- Cloud API key management
- Auto-update preferences
- Backup/restore

### 5.3 Real-time Updates Architecture

**WebSocket Connection:**
```typescript
// WebSocket API for real-time updates
ws://localhost:8000/ws

Messages:
{
  "type": "health_update",
  "service": "postgres",
  "status": "healthy",
  "timestamp": "2026-02-10T12:00:00Z"
}

{
  "type": "sync_progress",
  "project_id": "proj_123",
  "progress": 45,
  "message": "Syncing vectors: 450/1000"
}

{
  "type": "notification",
  "level": "info",
  "message": "Backup completed successfully"
}
```

**Server-Sent Events for Logs:**
```typescript
// SSE endpoint for log streaming
GET /api/logs/stream?service=api&follow=true

data: {"level": "info", "message": "Request received", "timestamp": "..."}
data: {"level": "error", "message": "Database timeout", "timestamp": "..."}
```

### 5.4 Dashboard Development Roadmap

**Phase 1: Core UI (Week 1-2)**
- Home/overview page with service status
- Projects CRUD
- Basic navigation
- Settings page

**Phase 2: Data Management (Week 3-4)**
- Vectors browser
- Tables browser
- Files browser
- Search functionality

**Phase 3: Advanced Features (Week 5-6)**
- Real-time updates (WebSocket)
- Sync UI
- Metrics/analytics
- Backup/restore UI

**Phase 4: Polish (Week 7-8)**
- Interactive tutorials
- Keyboard shortcuts
- Dark mode
- Responsive design
- Accessibility improvements

---

## 6. CLI Wizard Architecture

### 6.1 Interactive Setup Wizard

**Initial Launch Experience:**
```bash
$ zerolocal

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  Welcome to ZeroLocal!                          ┃
┃  The self-hosted AI database                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Let's get you set up in under 60 seconds...

✓ Checking Docker... Installed ✅
✓ Checking ports... Available ✅
✓ Downloading models... 42% [████████░░░░░░░░]

Services starting:
  ✓ PostgreSQL  (localhost:5432)
  ✓ Qdrant      (localhost:6333)
  ⏳ MinIO       (localhost:9000) starting...
  ⏳ RedPanda    (localhost:9092) starting...
  ⏳ Embeddings  (localhost:8001) loading model...
  ⏳ API Server  (localhost:8000) starting...
  ⏳ Dashboard   (localhost:3000) starting...

[████████████████████░░░░] 80% complete

Dashboard will open automatically when ready...
```

### 6.2 Wizard Flow Diagram

```
┌─────────────┐
│   Welcome   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Environment │  Check Docker, Python, Node.js
│   Check     │  Validate system requirements
└──────┬──────┘
       │
       ├──[FAIL]──→ ┌─────────────┐
       │            │   Offer     │  Install Docker? Download models?
       │            │   Fix       │  Allocate more RAM?
       │            └─────────────┘
       │
       ▼
┌─────────────┐
│    Port     │  Scan ports 5432, 6333, 8000, 8001, 9000, 9092, 3000
│   Check     │  Detect conflicts
└──────┬──────┘
       │
       ├──[CONFLICT]──→ ┌─────────────┐
       │                │   Suggest   │  Kill process? Use alt ports?
       │                │ Resolution  │  Skip conflicting service?
       │                └─────────────┘
       │
       ▼
┌─────────────┐
│ Model       │  Download BAAI/bge-small-en-v1.5 (if needed)
│ Download    │  Show progress bar, ETA
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Services   │  docker-compose up -d
│   Start     │  Wait for healthy status
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Health    │  Poll /health endpoints
│   Verify    │  Show per-service status
└──────┬──────┘
       │
       ├──[UNHEALTHY]──→ ┌─────────────┐
       │                 │  Show Logs  │  Display error logs
       │                 │  & Fix      │  Suggest fixes
       │                 └─────────────┘
       │
       ▼
┌─────────────┐
│   Success   │  "All services running!"
│   Message   │  "Dashboard: http://localhost:3000"
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Open        │  Open browser automatically
│ Dashboard   │  Or show CLI commands to get started
└─────────────┘
```

### 6.3 CLI Commands (Enhanced)

**Core Commands:**
```bash
# Setup & Management
zerodb init                     # Interactive setup wizard
zerodb doctor                   # Diagnose issues
zerodb update                   # Update ZeroLocal

# Service Control
zerodb start                    # Start all services
zerodb stop                     # Stop all services
zerodb restart [service]        # Restart service(s)
zerodb status                   # Show service status
zerodb logs [service]           # View logs

# Data Management
zerodb backup [path]            # Backup all data
zerodb restore <path>           # Restore from backup
zerodb reset                    # Reset to fresh state

# Cloud Integration
zerodb cloud login              # Authenticate with cloud
zerodb cloud link <project>     # Link local to cloud project
zerodb sync plan                # Show what will be synced
zerodb sync apply               # Push changes to cloud
zerodb sync pull                # Pull changes from cloud
zerodb cloud status             # Show sync status

# Project Management
zerodb project create <name>    # Create new project
zerodb project list             # List projects
zerodb project delete <id>      # Delete project
zerodb project export <id>      # Export project bundle
zerodb project import <path>    # Import project bundle

# Development
zerodb dev                      # Hot-reload mode
zerodb dev logs                 # Follow all logs
zerodb dev reset                # Quick reset for dev

# Utilities
zerodb open                     # Open dashboard in browser
zerodb config                   # Show configuration
zerodb version                  # Show version info
```

### 6.4 Doctor Command (Diagnostics)

```bash
$ zerodb doctor

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ZeroLocal Diagnostics                          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

System Checks:
  ✓ Docker installed (v24.0.5)
  ✓ Docker daemon running
  ✓ Python 3.11 detected
  ✓ Node.js 20.x detected
  ✓ 8GB RAM available (4GB in use)
  ✓ 50GB disk space available

Port Availability:
  ✓ 5432  PostgreSQL  (available)
  ✓ 6333  Qdrant      (available)
  ✗ 8000  API Server  (IN USE by process 1234)
  ✓ 8001  Embeddings  (available)
  ✓ 9000  MinIO       (available)
  ✓ 9092  RedPanda    (available)
  ✓ 3000  Dashboard   (available)

Service Health:
  ✓ postgres    healthy    (uptime: 2h 15m)
  ✓ qdrant      healthy    (uptime: 2h 14m)
  ⚠ zerodb-api  unhealthy  (port conflict)
  ✓ minio       healthy    (uptime: 2h 14m)
  ✓ redpanda    healthy    (uptime: 2h 13m)
  ✓ embeddings  healthy    (uptime: 2h 12m)
  ✗ dashboard   not running

Issues Detected: 2

1. Port 8000 conflict
   Process 1234 (/usr/bin/python3 -m http.server 8000)
   Suggested fix:
     $ kill 1234
     $ zerodb restart zerodb-api

2. Dashboard not running
   Suggested fix:
     $ docker-compose up dashboard -d

Run 'zerodb doctor --fix' to auto-fix issues.
```

---

## 7. Technology Stack

### 7.1 Native Application

**Desktop Framework:**
- **Primary**: Tauri 2.x
  - Pros: Small size, low memory, Rust security
  - Cons: Newer ecosystem
- **Fallback**: Electron
  - Pros: Mature, large community
  - Cons: Large binary, high memory

**System Orchestrator:**
- **Language**: Rust or Go
- **Libraries**:
  - Docker API: bollard (Rust) or docker/client (Go)
  - HTTP server: axum (Rust) or net/http (Go)
  - WebSocket: tokio-tungstenite (Rust) or gorilla/websocket (Go)

### 7.2 Dashboard

**Framework:**
- Next.js 14 (App Router)
- React 18
- TypeScript 5.x

**UI Components:**
- Radix UI (primitives)
- Tailwind CSS (styling)
- Lucide React (icons)
- shadcn/ui (component patterns)

**State Management:**
- TanStack Query (server state)
- Zustand (client state)
- React Context (global state)

**Data Viz:**
- Recharts (charts)
- React Flow (graph visualizations)

**Development:**
- Vitest (testing)
- Playwright (e2e tests)
- ESLint + Prettier (linting)

### 7.3 CLI

**Framework:**
- Typer (command framework)
- Rich (terminal UI)
- Click (argument parsing)

**Distribution:**
- PyPI package (pip install)
- Bundled in native app
- Homebrew formula (macOS)

### 7.4 Backend Services (Existing)

**API Server:**
- FastAPI 0.100+
- Python 3.11+
- Pydantic v2
- SQLAlchemy 2.x

**Databases:**
- PostgreSQL 16 (with pgvector)
- Qdrant (latest)
- MinIO (S3-compatible)
- RedPanda (Kafka-compatible)

**Embeddings:**
- sentence-transformers
- BAAI/bge-small-en-v1.5

### 7.5 Infrastructure

**Containerization:**
- Docker 24.0+
- Docker Compose v2

**Packaging:**
- Tauri bundler (native apps)
- Inno Setup (Windows)
- DMG Canvas (macOS)
- AppImage (Linux)

**Distribution:**
- GitHub Releases (binaries)
- Homebrew tap (macOS)
- Chocolatey feed (Windows)
- PyPI (CLI standalone)

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Sprint Goals:**
- Dashboard MVP with core pages
- Basic setup wizard in CLI
- Service health monitoring

**Deliverables:**
1. Dashboard UI framework
   - Home/overview page
   - Service status cards
   - Navigation shell
   - Settings page

2. Enhanced CLI wizard
   - `zerodb init` command
   - Docker detection
   - Port conflict detection
   - Service startup with progress

3. Service orchestrator (basic)
   - Health check aggregation
   - Status API
   - Log streaming

**Success Metrics:**
- Dashboard loads and shows service status
- CLI wizard completes without errors
- Setup time < 5 minutes

### Phase 2: Core Features (Week 3-4)

**Sprint Goals:**
- Complete dashboard CRUD operations
- Native installer prototype
- Real-time updates

**Deliverables:**
1. Dashboard data pages
   - Projects CRUD
   - Vectors browser
   - Tables browser
   - Files browser

2. Real-time features
   - WebSocket integration
   - Live health updates
   - Sync progress tracking

3. macOS native app (prototype)
   - Tauri shell
   - Embedded dashboard
   - System tray integration

**Success Metrics:**
- All CRUD operations work via dashboard
- Real-time updates visible
- macOS app launches and works
- Setup time < 3 minutes

### Phase 3: Native Installers (Week 5-6)

**Sprint Goals:**
- Production-ready native installers
- Auto-update mechanism
- Enhanced wizard

**Deliverables:**
1. macOS installer
   - Signed .dmg package
   - Notarized for Gatekeeper
   - Auto-update support

2. Windows installer
   - .exe with Inno Setup
   - Code-signed
   - Start menu integration

3. Linux packages
   - AppImage
   - .deb package
   - Flatpak (optional)

4. Enhanced setup wizard
   - Smarter error recovery
   - Resource allocation prompts
   - Interactive tutorials

**Success Metrics:**
- One-click install on all platforms
- Setup time < 2 minutes
- No Docker knowledge required

### Phase 4: Polish & Scale (Week 7-8)

**Sprint Goals:**
- Sub-60-second setup
- World-class UX
- Cloud parity verification

**Deliverables:**
1. Performance optimizations
   - Pre-loaded Docker images in installer
   - Parallel service startup
   - Caching and lazy loading

2. UX polish
   - Interactive tutorials
   - Onboarding flow
   - Error messages with fixes
   - Keyboard shortcuts

3. Cloud parity audit
   - API compatibility test suite
   - UI parity checklist
   - Feature flag system

4. Documentation
   - Video tutorials
   - Interactive docs
   - Troubleshooting guide
   - Developer API docs

**Success Metrics:**
- Setup time < 60 seconds
- Zero failed installations
- NPS score > 50
- 100% API parity with cloud

### Phase 5: Ecosystem (Week 9-10)

**Sprint Goals:**
- Homebrew/Chocolatey distribution
- Agent framework integrations
- Community building

**Deliverables:**
1. Package managers
   - Homebrew tap
   - Chocolatey package
   - AUR package (Linux)

2. Framework integrations
   - LangChain example
   - LlamaIndex example
   - CrewAI example
   - Haystack example

3. Developer resources
   - Starter templates
   - Code examples
   - Blog posts
   - Tutorial videos

4. Community
   - Discord server
   - GitHub discussions
   - Sample projects

**Success Metrics:**
- 100+ GitHub stars
- 10+ community contributions
- 5+ agent framework examples
- 1000+ downloads

---

## 9. Success Metrics & KPIs

### 9.1 Primary Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Setup Time** | 10+ min | < 60 sec | Time from download to working dashboard |
| **First Success Time** | 30 min | < 5 min | Time to first API call success |
| **Failed Installs** | ~30% | < 5% | Installation failures / total attempts |
| **Developer NPS** | Unknown | > 50 | Net Promoter Score survey |
| **Cloud Conversion** | 0% | > 20% | Local users who upgrade to cloud |
| **GitHub Stars** | 50 | 500 | Organic growth over 3 months |
| **Monthly Downloads** | 100 | 2000 | Unique downloads per month |

### 9.2 Technical KPIs

**Performance:**
- Dashboard load time: < 2 seconds
- API response time (local): < 50ms (p95)
- Vector search latency: < 100ms (10k vectors)
- Sync throughput: > 1000 vectors/sec

**Reliability:**
- Service uptime: > 99.9% (excluding deliberate stops)
- Health check success rate: > 99%
- Auto-recovery success: > 95%
- Data corruption rate: 0%

**Usability:**
- Setup wizard completion rate: > 95%
- Dashboard engagement: > 80% of users
- CLI usage: > 50% of users
- Cloud sync adoption: > 30% of users

### 9.3 Business Metrics

**Acquisition:**
- Website → Download conversion: > 30%
- Download → Install conversion: > 90%
- Install → Active use conversion: > 70%

**Activation:**
- First project created: < 5 minutes
- First vector upsert: < 10 minutes
- First search query: < 15 minutes

**Retention:**
- Day 1 retention: > 80%
- Week 1 retention: > 60%
- Month 1 retention: > 40%

**Revenue (Cloud Conversion):**
- Free → Paid (local to cloud): > 20%
- Average time to conversion: < 30 days
- Expansion revenue: 2x after 6 months

### 9.4 Monitoring & Alerting

**Telemetry (Privacy-Preserving):**
- Anonymous usage metrics (opt-in)
- Error reporting (Sentry)
- Performance metrics
- Feature adoption tracking

**Dashboard Metrics:**
```json
{
  "install_id": "uuid-anonymized",
  "version": "1.0.0",
  "platform": "darwin",
  "setup_time_seconds": 58,
  "services_started": 7,
  "errors_encountered": 0,
  "cloud_linked": false,
  "features_used": ["projects", "vectors"],
  "session_duration_minutes": 45
}
```

**Alerts:**
- Setup failure rate > 10%
- Average setup time > 90 seconds
- Service crash rate > 1%
- Sync failure rate > 5%

---

## 10. Risk Assessment

### 10.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Docker conflicts** | High | High | Detect and auto-resolve port conflicts; offer alternative ports |
| **Resource constraints** | Medium | Medium | Detect available RAM/CPU; adjust service limits; warn users |
| **Model download failures** | Medium | Low | Retry logic; mirror downloads; bundle models in installer |
| **Platform-specific bugs** | Medium | Medium | Extensive testing on all platforms; beta testing program |
| **Auto-update issues** | Low | High | Incremental rollout; rollback mechanism; staged updates |
| **Data loss** | Low | Critical | Auto-backup before updates; versioned data format |

### 10.2 UX Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Complex setup** | Low | High | Interactive wizard; one-click defaults; smart detection |
| **Confusing UI** | Medium | Medium | User testing; iterative design; tooltips and tutorials |
| **Poor error messages** | Medium | Medium | Contextual errors with fixes; `zerodb doctor` command |
| **Abandoned after install** | Medium | High | Interactive onboarding; sample projects; quick wins |

### 10.3 Business Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Low adoption** | Low | Critical | Marketing campaign; developer outreach; influencer partnerships |
| **No cloud conversion** | Medium | High | Seamless cloud upgrade path; trial credits; premium features |
| **Competitor response** | Medium | Medium | Move fast; build moat with UX; open-source community |
| **Support burden** | High | Medium | Comprehensive docs; community forum; self-service tools |

### 10.4 Timeline Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Delayed dashboard** | Medium | High | Start with MVP; iterate quickly; reuse existing Next.js setup |
| **Installer complexity** | High | Medium | Use proven tools (Tauri, Inno Setup); prioritize macOS first |
| **Scope creep** | Medium | Medium | Strict phase gates; MVP mindset; defer non-critical features |
| **Resource constraints** | Low | Medium | Focus on highest-impact features; leverage existing code |

---

## Appendix A: Competitive Analysis

### LocalStack Deep Dive

**What They Do Well:**
- One-command install: `pip install localstack && localstack start`
- Excellent documentation
- Active community (47k+ GitHub stars)
- Regular updates and new service support
- Enterprise tier for advanced features

**What We Can Learn:**
- Simplicity matters more than perfection
- Documentation is a feature, not an afterthought
- Community engagement drives adoption
- Freemium model works (free local, paid cloud)

**Our Advantages Over LocalStack:**
- Native installers (not just pip/docker)
- Beautiful dashboard (theirs is basic)
- Simpler use case (vector DB vs all of AWS)
- Better AI/agent integration

### Supabase Local

**What They Do Well:**
- Excellent CLI (`supabase init`, `supabase start`)
- Dashboard mirrors production exactly
- Great DX (developer experience)
- Seamless cloud migration

**What We Can Learn:**
- CLI-first approach works
- Parity between local and cloud is critical
- Migration path must be dead simple
- Open source builds trust

**Our Advantages:**
- Faster setup (no manual config needed)
- Native app (not just CLI + Docker)
- Vector-first (purpose-built for AI)
- Lower resource requirements

---

## Appendix B: User Stories

### Story 1: DevOps Dan (First-Time User)

**Goal**: Test AI app locally before deploying to production

**Journey:**
1. Hears about ZeroLocal on Hacker News
2. Visits website, downloads macOS .dmg (10 sec)
3. Drags app to Applications, launches (5 sec)
4. Setup wizard auto-detects everything (20 sec)
5. Dashboard opens showing all services green (5 sec)
6. Follows interactive tutorial to create first project (2 min)
7. Upserts test vectors, runs search (2 min)
8. Integrates with existing Python app (10 min)
9. Loves it, decides to use ZeroDB Cloud for production

**Total Time:** 15 minutes from discovery to production decision

### Story 2: AI Engineer Amy (Existing User)

**Goal**: Upgrade to new version with minimal disruption

**Journey:**
1. Notification: "ZeroLocal 1.1 available"
2. Clicks "Update now"
3. Background update downloads (30 sec)
4. "Update ready, restart to apply"
5. Clicks restart
6. App relaunches with new features (20 sec)
7. Changelog popup shows what's new
8. Continues working without data loss

**Total Time:** < 1 minute

### Story 3: Startup Steve (Cost-Conscious)

**Goal**: Build MVP locally, scale to cloud when profitable

**Journey:**
1. Starts with ZeroLocal free tier
2. Builds entire RAG app locally over 2 weeks
3. Launches to beta users
4. Reaches 1000 users, local instance struggles
5. Dashboard prompts: "Ready for production? Upgrade to ZeroDB Cloud"
6. Clicks upgrade, CLI syncs entire local project (5 min)
7. Cloud instance live, seamless cutover
8. Continues using ZeroLocal for dev/staging

**Result:** Customer acquired, recurring revenue secured

---

## Appendix C: Technical Specifications

### System Requirements

**Minimum:**
- OS: macOS 11+, Windows 10+, Ubuntu 20.04+
- RAM: 4GB available
- Disk: 10GB free space
- CPU: 2 cores, 2GHz+
- Docker: 20.10+ (or auto-installed)

**Recommended:**
- OS: macOS 13+, Windows 11+, Ubuntu 22.04+
- RAM: 8GB available
- Disk: 50GB free space (SSD preferred)
- CPU: 4 cores, 3GHz+
- Docker: 24.0+

### Port Allocation

| Service | Port | Alternative | Purpose |
|---------|------|-------------|---------|
| PostgreSQL | 5432 | 5433, 5434 | Database |
| Qdrant | 6333 | 6334, 6335 | Vector search API |
| Qdrant gRPC | 6334 | 6336, 6337 | gRPC endpoint |
| MinIO API | 9000 | 9001, 9002 | S3-compatible API |
| MinIO Console | 9001 | 9003, 9004 | Web console |
| RedPanda Kafka | 9092 | 9093, 9094 | Kafka API |
| RedPanda HTTP | 8082 | 8083, 8084 | HTTP proxy |
| API Server | 8000 | 8080, 8888 | REST API |
| Embeddings | 8001 | 8002, 8003 | Embeddings service |
| Dashboard | 3000 | 3001, 3002 | Web UI |

### Resource Limits (Docker)

```yaml
services:
  postgres:
    mem_limit: 512m
    cpus: 1.0
  qdrant:
    mem_limit: 1g
    cpus: 1.0
  minio:
    mem_limit: 256m
    cpus: 0.5
  redpanda:
    mem_limit: 1g
    cpus: 1.0
  embeddings:
    mem_limit: 2g
    cpus: 2.0  # CPU-intensive
  api:
    mem_limit: 512m
    cpus: 1.0
  dashboard:
    mem_limit: 256m
    cpus: 0.5
```

**Total Resource Usage:**
- Memory: ~5.5GB
- CPU: 7 cores (can run on 4-core with throttling)
- Disk: ~2GB (services) + variable data

---

## Appendix D: API Design (Service Orchestrator)

### REST API Specification

**Base URL:** `http://localhost:9999/api`

#### Health & Status

```http
GET /api/health
Response:
{
  "status": "healthy",
  "services": {
    "postgres": {"status": "healthy", "uptime": "2h15m"},
    "qdrant": {"status": "healthy", "uptime": "2h14m"},
    "minio": {"status": "healthy", "uptime": "2h14m"},
    "redpanda": {"status": "degraded", "uptime": "1h30m"},
    "embeddings": {"status": "healthy", "uptime": "2h12m"},
    "api": {"status": "healthy", "uptime": "2h10m"},
    "dashboard": {"status": "healthy", "uptime": "2h10m"}
  },
  "resources": {
    "memory_used": "5.2GB",
    "memory_available": "2.8GB",
    "cpu_usage": "35%",
    "disk_used": "8.5GB"
  }
}
```

#### Service Control

```http
POST /api/services/start
Body: {"services": ["postgres", "qdrant"]}  # empty array = all
Response: {"status": "starting", "job_id": "uuid"}

POST /api/services/stop
Body: {"services": ["api"], "force": false}
Response: {"status": "stopping", "job_id": "uuid"}

POST /api/services/{service}/restart
Response: {"status": "restarting", "job_id": "uuid"}
```

#### Logs

```http
GET /api/logs/{service}?lines=100&follow=true
Response: (SSE stream)
data: {"timestamp": "2026-02-10T12:00:00Z", "level": "info", "message": "..."}
```

#### Configuration

```http
GET /api/config
Response:
{
  "version": "1.0.0",
  "ports": {
    "postgres": 5432,
    "api": 8000,
    "dashboard": 3000
  },
  "resources": {
    "postgres_memory": "512m",
    "embeddings_cpu": "2.0"
  },
  "cloud": {
    "linked": false,
    "api_key_set": false
  }
}

PUT /api/config
Body: {"ports": {"api": 8080}}
Response: {"status": "updated", "restart_required": true}
```

#### Updates

```http
GET /api/updates/check
Response: {
  "current_version": "1.0.0",
  "latest_version": "1.1.0",
  "update_available": true,
  "release_notes": "...",
  "download_size": "45MB"
}

POST /api/updates/apply
Response: {"status": "downloading", "job_id": "uuid"}

GET /api/updates/status/{job_id}
Response: {
  "status": "downloading",
  "progress": 45,
  "eta_seconds": 30
}
```

---

## Appendix E: Release Checklist

### Pre-Release

- [ ] All phase goals completed
- [ ] Automated tests passing (unit, integration, e2e)
- [ ] Manual testing on all platforms (macOS, Windows, Linux)
- [ ] Performance benchmarks meet targets
- [ ] Security audit completed
- [ ] Documentation updated
- [ ] Changelog prepared
- [ ] Release notes written
- [ ] Demo video recorded

### Platform-Specific

**macOS:**
- [ ] .dmg built and tested
- [ ] Code signed with Developer ID
- [ ] Notarized by Apple
- [ ] Tested on macOS 11, 12, 13, 14
- [ ] Homebrew formula ready

**Windows:**
- [ ] .exe installer built
- [ ] Code signed with Authenticode
- [ ] Tested on Windows 10, 11
- [ ] Chocolatey package ready
- [ ] Silent install tested

**Linux:**
- [ ] AppImage built and tested
- [ ] .deb package created
- [ ] .rpm package created
- [ ] Tested on Ubuntu, Fedora, Arch
- [ ] Flatpak/Snap prepared (optional)

### Launch

- [ ] GitHub release created
- [ ] Binaries uploaded
- [ ] Website updated
- [ ] Blog post published
- [ ] Social media announced
- [ ] Hacker News post scheduled
- [ ] Reddit posts in relevant subs
- [ ] Discord/Slack communities notified
- [ ] Email list announcement
- [ ] Analytics/monitoring enabled

### Post-Launch

- [ ] Monitor error rates
- [ ] Respond to GitHub issues
- [ ] Track NPS scores
- [ ] Gather user feedback
- [ ] Plan next iteration

---

## Conclusion

This architecture transforms ZeroLocal from a developer tool into a **strategic moat** for ZeroDB Cloud. By delivering a world-class local experience with sub-60-second setup, beautiful dashboard, and perfect cloud parity, we create an inevitable upgrade path:

**Love local → Scale to cloud → Sticky revenue**

The key to success is **extreme simplicity** at every step. Developers should feel joy, not frustration. One-click install. Zero configuration. Instant success.

**This is how we win.**

---

**References:**
- Issue #1133: https://github.com/AINative-Studio/core/issues/1133
- ZeroLocal README: `/Users/aideveloper/core/zerodb-local/README.md`
- Docker Compose: `/Users/aideveloper/core/zerodb-local/docker-compose.yml`

**Document Owner:** System Architecture Team
**Reviewers:** Engineering, Product, DevRel
**Next Review:** 2026-02-17

Refs #1133
