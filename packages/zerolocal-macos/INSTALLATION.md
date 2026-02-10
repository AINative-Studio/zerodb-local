# ZeroLocal.app Installation Guide

## System Requirements

- macOS 10.15 (Catalina) or later
- Docker Desktop for Mac
- 2GB free disk space
- Available ports: 8000, 3000, 5432, 6333, 9000

## Installation Steps

### 1. Install Docker Desktop

If you don't have Docker Desktop installed:

1. Download from https://www.docker.com/products/docker-desktop
2. Install and launch Docker Desktop
3. Verify installation: `docker --version`

### 2. Install ZeroLocal.app

#### Option A: Download DMG (Recommended)

1. Download `ZeroLocal.dmg` from releases
2. Double-click to open the DMG file
3. Drag `ZeroLocal.app` to the Applications folder
4. Eject the DMG

#### Option B: Build from Source

```bash
# Clone repository
git clone https://github.com/ainative/core.git
cd core/packages/zerolocal-macos

# Install dependencies
npm install

# Build the app
npm run tauri:build

# The app will be at:
# src-tauri/target/release/bundle/macos/ZeroLocal.app
```

### 3. First Launch

1. Open Applications folder
2. Find and double-click `ZeroLocal.app`
3. If you see "App can't be opened because it's from an unidentified developer":
   - Right-click the app
   - Select "Open"
   - Click "Open" in the dialog

4. The app will:
   - Check prerequisites (Docker, ports, disk space)
   - Create menu bar icon
   - Hide main window (access via menu bar)

### 4. Start Services

From the menu bar icon:

1. Click the ZeroLocal icon (🗄️)
2. Select "Start Services"
3. Wait for services to start (30-60 seconds)
4. Select "Dashboard" to open the web UI

## Menu Bar Reference

```
🗄️ ZeroLocal
├─ Dashboard (⌘D)          # Open web dashboard
├─ Status: ✅ Running       # Current status
├─ ─────────────
├─ Start Services          # Start all services
├─ Stop Services           # Stop all services
├─ Restart Services        # Restart all services
├─ ─────────────
├─ View Logs...            # Open logs viewer
├─ Preferences...          # Open preferences
├─ Check for Updates       # Check for app updates
└─ Quit ZeroLocal          # Exit application
```

## Troubleshooting

### Issue: Docker not found

**Solution**:
1. Install Docker Desktop
2. Launch Docker Desktop
3. Wait for Docker to fully start
4. Restart ZeroLocal.app

### Issue: Ports already in use

**Solution**:
```bash
# Check what's using the ports
lsof -i :8000
lsof -i :3000
lsof -i :5432

# Kill the processes
kill -9 <PID>
```

### Issue: Services won't start

**Solution**:
1. Open Logs viewer (menu bar → View Logs)
2. Check for error messages
3. Verify Docker has enough resources:
   - Docker Desktop → Preferences → Resources
   - Set CPUs: 4+
   - Set Memory: 4GB+
   - Set Disk: 20GB+

### Issue: App crashes on startup

**Solution**:
1. Open Console.app
2. Filter for "ZeroLocal"
3. Look for error messages
4. Common causes:
   - Missing Docker Desktop
   - Insufficient permissions
   - Corrupted preferences

Reset preferences:
```bash
rm -rf ~/Library/Application\ Support/com.ainative.zerolocal
```

### Issue: Can't access dashboard

**Solution**:
1. Verify services are running (check menu bar status)
2. Try manually opening: http://localhost:3000
3. Check firewall settings allow localhost connections
4. Restart services from menu bar

## Uninstallation

### Remove Application

```bash
# Remove app
rm -rf /Applications/ZeroLocal.app

# Remove preferences and data
rm -rf ~/Library/Application\ Support/com.ainative.zerolocal
rm -rf ~/Library/Caches/com.ainative.zerolocal
rm -rf ~/Library/Preferences/com.ainative.zerolocal.plist

# Remove ZeroLocal data (optional - keeps your databases)
rm -rf ~/.zerolocal
```

### Stop Services

Before uninstalling:
1. Open ZeroLocal menu
2. Select "Stop Services"
3. Wait for services to stop
4. Quit ZeroLocal

## Auto-Start on Login

To enable auto-start:

1. Open menu bar → Preferences
2. Check "Start services automatically on login"
3. Click "Save Preferences"

Or manually:

1. System Preferences → Users & Groups
2. Click your username
3. Go to Login Items tab
4. Click "+" and add ZeroLocal.app

## Updates

### Automatic Updates

If enabled in Preferences:
- App checks for updates on launch
- Notification appears when update available
- Click to download and install

### Manual Updates

1. Menu bar → Check for Updates
2. If update available, download will start
3. App will restart after installation

### Rollback

To rollback to previous version:
1. Keep old DMG files
2. Stop services
3. Quit ZeroLocal
4. Drag old version to Applications (replace)

## Advanced Configuration

### Custom Ports

1. Menu bar → Preferences
2. Update port numbers
3. Click Save
4. Restart services for changes to take effect

### Custom Docker Compose File

The app uses the docker-compose.yml from the zerodb-local directory.
To customize:

```bash
# Edit the compose file
nano ~/zerodb-local/docker-compose.yml

# Restart services from menu bar
```

### Logs Location

Application logs:
```bash
~/Library/Logs/com.ainative.zerolocal/
```

Service logs:
- View in-app via menu bar → View Logs
- Or via Docker Desktop

## Support

For issues not covered here:

1. Check [GitHub Issues](https://github.com/ainative/core/issues)
2. Create new issue with:
   - macOS version
   - Docker Desktop version
   - Error messages from Console.app
   - Steps to reproduce

## Refs

Issue #1131
