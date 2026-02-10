# ZeroLocal.app - Native macOS Application

Native macOS application for managing ZeroLocal development environment.

## Features

- **Menu Bar Integration**: Quick access from macOS menu bar
- **Docker Management**: Start/stop/restart services with one click
- **Service Monitoring**: Real-time health status for all services
- **Log Viewer**: View logs from any service in-app
- **Preferences Panel**: Configure ports and auto-start behavior
- **Auto-Updates**: Automatic update checking and installation

## Architecture

- **Frontend**: React + TypeScript + Vite
- **Backend**: Rust + Tauri
- **Docker SDK**: Bollard (official Docker SDK for Rust)
- **Size**: <100MB installer
- **Launch Time**: <5 seconds

## Project Structure

```
packages/zerolocal-macos/
├── src/                      # React frontend
│   ├── components/           # UI components
│   │   ├── Dashboard.tsx     # Main dashboard view
│   │   ├── Logs.tsx          # Log viewer
│   │   └── Preferences.tsx   # Preferences panel
│   ├── App.tsx               # Main app component
│   ├── main.tsx              # React entry point
│   └── styles.css            # Global styles
├── src-tauri/                # Rust backend
│   ├── src/
│   │   ├── docker.rs         # Docker management module
│   │   └── main.rs           # Tauri main process
│   ├── icons/                # App icons
│   ├── Cargo.toml            # Rust dependencies
│   ├── tauri.conf.json       # Tauri configuration
│   └── build.rs              # Build script
├── tests/                    # Integration tests
├── package.json              # Node.js dependencies
├── vite.config.ts            # Vite configuration
└── tsconfig.json             # TypeScript configuration
```

## Development

### Prerequisites

- Node.js 18+
- Rust 1.70+
- Docker Desktop

### Install Dependencies

```bash
npm install
```

### Run in Development Mode

```bash
npm run tauri:dev
```

### Build for Production

```bash
npm run tauri:build
```

This creates:
- `src-tauri/target/release/bundle/dmg/ZeroLocal_0.1.0_aarch64.dmg`
- `src-tauri/target/release/bundle/macos/ZeroLocal.app`

## Testing

### Run Unit Tests (Rust)

```bash
cd src-tauri
cargo test
```

### Run with Coverage

```bash
cd src-tauri
cargo tarpaulin --out Lcov --output-dir coverage
```

### Integration Tests

```bash
npm run test
```

## Features Implemented

### Docker Management
- Check Docker status
- Start/stop/restart services
- Monitor container health
- View service logs
- Port information display

### System Tray
- Menu bar icon with status indicator
- Quick actions menu
- Dashboard access
- Service control
- Log viewer access
- Preferences access
- Update checking

### User Interface
- Clean, native macOS design
- Tab navigation (Dashboard, Logs, Preferences)
- Real-time service status
- Color-coded health indicators
- Responsive layout

### Preferences
- Auto-start on login
- Show notifications
- Custom port configuration
- Auto-update settings

## Installation

### For End Users

1. Download `ZeroLocal.dmg`
2. Open the DMG file
3. Drag `ZeroLocal.app` to Applications folder
4. Launch from Applications or Spotlight

### System Requirements

- macOS 10.15 (Catalina) or later
- Docker Desktop installed
- 2GB free disk space
- Ports 8000, 3000, 5432, 6333, 9000 available

## Troubleshooting

### App won't start
- Check that Docker Desktop is installed and running
- Verify required ports are available
- Check Console.app for error messages

### Services won't start
- Ensure docker-compose.yml is in correct location
- Verify Docker Desktop has enough resources allocated
- Check logs in the Logs tab

### Performance issues
- Allocate more resources to Docker Desktop
- Close unnecessary Docker containers
- Check disk space availability

## Building the DMG

The DMG is automatically created during the build process with:
- Drag-and-drop installer UI
- Custom background image
- Application icon
- Volume icon
- License agreement

## Auto-Updates

Auto-update endpoint: `https://api.ainative.studio/zerolocal/updates/{target}/{version}`

Updates are checked:
- On app launch (if enabled in preferences)
- Via "Check for Updates" menu item
- Automatically every 24 hours (if enabled)

## Security

- App is sandboxed via Tauri security model
- Docker commands run with user permissions
- No root access required
- File system access limited to specific directories
- HTTP requests limited to localhost

## Contributing

See main repository CLAUDE.md for contribution guidelines.

## License

MIT

## Refs

Issue #1131
