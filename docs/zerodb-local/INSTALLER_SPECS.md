# ZeroLocal Native Installer Specifications

**Version**: 1.0
**Status**: Design Phase
**Last Updated**: 2026-02-10
**Related**: ARCHITECTURE.md, Issue #1133

---

## Overview

Detailed technical specifications for building native installers across all platforms. Target: sub-60-second setup from download to working dashboard.

---

## 1. macOS Installer

### 1.1 Package Format

**Type**: .dmg (Apple Disk Image)
**Target Size**: 200-250 MB
**Minimum OS**: macOS 11.0 (Big Sur)
**Architecture**: Universal Binary (x86_64 + ARM64)

### 1.2 Build Process

**Tools:**
- Tauri 2.x (app framework)
- create-dmg (DMG creation)
- Apple Developer tools (signing/notarization)

**Build Command:**
```bash
# Build Tauri app
cd native-app
cargo tauri build --target universal-apple-darwin

# Create DMG with create-dmg
create-dmg \
  --volname "ZeroLocal" \
  --volicon "assets/icon.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "ZeroLocal.app" 200 190 \
  --hide-extension "ZeroLocal.app" \
  --app-drop-link 600 185 \
  --background "assets/dmg-background.png" \
  "ZeroLocal-1.0.0-universal.dmg" \
  "target/universal-apple-darwin/release/bundle/macos/ZeroLocal.app"
```

### 1.3 Signing & Notarization

**Developer Certificate:**
```bash
# Sign the app
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: AINative Studio" \
  --options runtime \
  --entitlements entitlements.plist \
  ZeroLocal.app

# Sign the DMG
codesign --sign "Developer ID Application: AINative Studio" \
  ZeroLocal-1.0.0-universal.dmg

# Notarize with Apple
xcrun notarytool submit ZeroLocal-1.0.0-universal.dmg \
  --apple-id "dev@ainative.studio" \
  --team-id "TEAM_ID" \
  --password "@keychain:notarization-password" \
  --wait

# Staple the ticket
xcrun stapler staple ZeroLocal-1.0.0-universal.dmg
```

**Entitlements (entitlements.plist):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
</dict>
</plist>
```

### 1.4 App Bundle Structure

```
ZeroLocal.app/
├── Contents/
│   ├── Info.plist
│   ├── MacOS/
│   │   └── zerolocal (Tauri binary)
│   ├── Resources/
│   │   ├── icon.icns
│   │   ├── assets/ (dashboard static files)
│   │   ├── docker-images/
│   │   │   ├── postgres.tar.gz
│   │   │   ├── qdrant.tar.gz
│   │   │   ├── minio.tar.gz
│   │   │   ├── redpanda.tar.gz
│   │   │   ├── embeddings.tar.gz
│   │   │   └── zerodb-api.tar.gz
│   │   ├── models/
│   │   │   └── bge-small-en-v1.5.tar.gz
│   │   └── cli/
│   │       └── zerodb (Python CLI binary)
│   └── _CodeSignature/
│       └── CodeResources
└── README.txt
```

### 1.5 Info.plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>ZeroLocal</string>
    <key>CFBundleDisplayName</key>
    <string>ZeroLocal</string>
    <key>CFBundleIdentifier</key>
    <string>com.ainative.zerolocal</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleExecutable</key>
    <string>zerolocal</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
```

### 1.6 First Launch Sequence

```
User double-clicks ZeroLocal.app
     │
     ▼
[Gatekeeper check] → Signature verified ✅
     │
     ▼
[App launches] → Tauri window opens
     │
     ▼
[Check Docker]
     ├─[Installed] → Use existing
     └─[Not found] → Prompt to install Docker Desktop
                      (link to docker.com/products/docker-desktop)
     │
     ▼
[Extract Docker images] (30-40 sec)
  - Load from Resources/docker-images/*.tar.gz
  - docker load < postgres.tar.gz
  - Progress bar shows extraction status
     │
     ▼
[Start services] (15-20 sec)
  - docker-compose up -d
  - Health checks
     │
     ▼
[Open dashboard] → http://localhost:3000
     │
     ▼
✅ Success - Interactive tutorial starts
```

### 1.7 Homebrew Distribution (Alternative)

**Homebrew Cask:**
```ruby
cask "zerolocal" do
  version "1.0.0"
  sha256 "abc123..."

  url "https://github.com/AINative-Studio/core/releases/download/v#{version}/ZeroLocal-#{version}-universal.dmg"
  name "ZeroLocal"
  desc "Self-hosted AI database with zero API costs"
  homepage "https://www.ainative.studio/zerolocal"

  app "ZeroLocal.app"

  binary "#{appdir}/ZeroLocal.app/Contents/Resources/cli/zerodb"

  postflight do
    system "#{appdir}/ZeroLocal.app/Contents/MacOS/zerolocal", "--setup"
  end

  uninstall quit: "com.ainative.zerolocal"

  zap trash: [
    "~/Library/Application Support/com.ainative.zerolocal",
    "~/Library/Caches/com.ainative.zerolocal",
    "~/Library/Preferences/com.ainative.zerolocal.plist",
    "~/Library/Saved Application State/com.ainative.zerolocal.savedState",
  ]
end
```

**Install Command:**
```bash
brew install --cask zerolocal
```

---

## 2. Windows Installer

### 2.1 Package Format

**Type**: .exe (Inno Setup installer)
**Target Size**: 220-270 MB
**Minimum OS**: Windows 10 (1809+)
**Architecture**: x86_64

### 2.2 Build Process

**Tools:**
- Tauri 2.x (app framework)
- Inno Setup 6.x (installer)
- SignTool.exe (code signing)

**Inno Setup Script (zerolocal.iss):**
```ini
[Setup]
AppName=ZeroLocal
AppVersion=1.0.0
AppPublisher=AINative Studio
AppPublisherURL=https://www.ainative.studio
AppSupportURL=https://www.ainative.studio/support
AppUpdatesURL=https://www.ainative.studio/zerolocal/updates
DefaultDirName={autopf}\ZeroLocal
DefaultGroupName=ZeroLocal
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir=output
OutputBaseFilename=ZeroLocal-Setup-1.0.0
SetupIconFile=assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
Name: "quicklaunchicon"; Description: "Create a &Quick Launch icon"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "addtopath"; Description: "Add CLI to PATH"; GroupDescription: "Environment:"

[Files]
Source: "target\release\zerolocal.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs
Source: "docker-images\*"; DestDir: "{app}\docker-images"; Flags: ignoreversion
Source: "models\*"; DestDir: "{app}\models"; Flags: ignoreversion
Source: "cli\zerodb.exe"; DestDir: "{app}\cli"; Flags: ignoreversion

[Icons]
Name: "{group}\ZeroLocal"; Filename: "{app}\zerolocal.exe"
Name: "{group}\{cm:UninstallProgram,ZeroLocal}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\ZeroLocal"; Filename: "{app}\zerolocal.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\ZeroLocal"; Filename: "{app}\zerolocal.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\zerolocal.exe"; Description: "Launch ZeroLocal"; Flags: nowait postinstall skipifsilent

[Code]
function CheckDockerInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('docker', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

procedure InitializeWizard;
begin
  if not CheckDockerInstalled() then
  begin
    MsgBox('Docker Desktop is required but not installed. ' +
           'Please install Docker Desktop from docker.com ' +
           'before continuing.', mbInformation, MB_OK);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Load Docker images
    Exec('cmd.exe', '/C ' + ExpandConstant('{app}\scripts\load-images.bat'), '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
```

### 2.3 Code Signing

**Sign with Authenticode:**
```cmd
signtool sign /f "AINative-CodeSign.pfx" /p "%SIGN_PASSWORD%" ^
  /t http://timestamp.digicert.com ^
  /fd sha256 ^
  /d "ZeroLocal Installer" ^
  /du "https://www.ainative.studio" ^
  ZeroLocal-Setup-1.0.0.exe
```

### 2.4 Directory Structure

```
C:\Program Files\ZeroLocal\
├── zerolocal.exe (Tauri app)
├── assets\
│   ├── icon.ico
│   └── dashboard\
├── docker-images\
│   ├── postgres.tar.gz
│   ├── qdrant.tar.gz
│   ├── minio.tar.gz
│   ├── redpanda.tar.gz
│   ├── embeddings.tar.gz
│   └── zerodb-api.tar.gz
├── models\
│   └── bge-small-en-v1.5.tar.gz
├── cli\
│   └── zerodb.exe
├── scripts\
│   ├── load-images.bat
│   └── start-services.bat
└── unins000.exe
```

### 2.5 Registry Keys

```ini
[Registry]
Root: HKLM; Subkey: "Software\AINative\ZeroLocal"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\AINative\ZeroLocal"; ValueType: string; ValueName: "Version"; ValueData: "1.0.0"; Flags: uninsdeletekey

; Add CLI to PATH (if task selected)
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\cli"; Tasks: addtopath
```

### 2.6 Chocolatey Distribution (Alternative)

**Package Manifest (zerolocal.nuspec):**
```xml
<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd">
  <metadata>
    <id>zerolocal</id>
    <version>1.0.0</version>
    <title>ZeroLocal</title>
    <authors>AINative Studio</authors>
    <projectUrl>https://www.ainative.studio/zerolocal</projectUrl>
    <iconUrl>https://www.ainative.studio/zerolocal-icon.png</iconUrl>
    <licenseUrl>https://github.com/AINative-Studio/core/blob/main/LICENSE</licenseUrl>
    <requireLicenseAcceptance>false</requireLicenseAcceptance>
    <description>Self-hosted AI database with zero API costs</description>
    <summary>Local development environment for ZeroDB</summary>
    <tags>ai database vector zerodb local docker</tags>
    <dependencies>
      <dependency id="docker-desktop" version="4.0.0" />
    </dependencies>
  </metadata>
  <files>
    <file src="tools\**" target="tools" />
  </files>
</package>
```

**Install Script (chocolateyinstall.ps1):**
```powershell
$packageName = 'zerolocal'
$installerType = 'exe'
$url64 = 'https://github.com/AINative-Studio/core/releases/download/v1.0.0/ZeroLocal-Setup-1.0.0.exe'
$silentArgs = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
$validExitCodes = @(0)

Install-ChocolateyPackage `
  -PackageName $packageName `
  -FileType $installerType `
  -Url64bit $url64 `
  -SilentArgs $silentArgs `
  -ValidExitCodes $validExitCodes
```

**Install Command:**
```cmd
choco install zerolocal
```

---

## 3. Linux Installer

### 3.1 AppImage (Universal)

**Build Process:**
```bash
# Build Tauri app
cd native-app
cargo tauri build --target x86_64-unknown-linux-gnu

# Create AppImage with linuxdeploy
linuxdeploy-x86_64.AppImage \
  --appdir AppDir \
  --executable target/x86_64-unknown-linux-gnu/release/zerolocal \
  --desktop-file assets/zerolocal.desktop \
  --icon-file assets/icon.png \
  --output appimage

# Result: ZeroLocal-1.0.0-x86_64.AppImage
```

**AppImage Structure:**
```
ZeroLocal-1.0.0-x86_64.AppImage
├── AppRun (entry script)
├── zerolocal.desktop
├── icon.png
├── usr/
│   ├── bin/
│   │   ├── zerolocal
│   │   └── zerodb (CLI)
│   ├── lib/
│   │   └── (shared libraries)
│   └── share/
│       ├── applications/
│       │   └── zerolocal.desktop
│       └── icons/
└── docker-images/
    └── (pre-loaded images)
```

**Desktop Entry (zerolocal.desktop):**
```ini
[Desktop Entry]
Name=ZeroLocal
Comment=Self-hosted AI database
Exec=zerolocal
Icon=zerolocal
Type=Application
Categories=Development;Database;
Terminal=false
StartupWMClass=ZeroLocal
```

### 3.2 .deb Package (Debian/Ubuntu)

**Build Process:**
```bash
# Create package structure
mkdir -p zerolocal_1.0.0/DEBIAN
mkdir -p zerolocal_1.0.0/usr/bin
mkdir -p zerolocal_1.0.0/usr/share/applications
mkdir -p zerolocal_1.0.0/usr/share/icons/hicolor/256x256/apps
mkdir -p zerolocal_1.0.0/opt/zerolocal

# Copy files
cp target/release/zerolocal zerolocal_1.0.0/opt/zerolocal/
cp assets/zerolocal.desktop zerolocal_1.0.0/usr/share/applications/
cp assets/icon.png zerolocal_1.0.0/usr/share/icons/hicolor/256x256/apps/zerolocal.png
cp -r docker-images zerolocal_1.0.0/opt/zerolocal/

# Create symlink
ln -s /opt/zerolocal/zerolocal zerolocal_1.0.0/usr/bin/zerolocal

# Build package
dpkg-deb --build zerolocal_1.0.0
```

**Control File (DEBIAN/control):**
```
Package: zerolocal
Version: 1.0.0
Section: devel
Priority: optional
Architecture: amd64
Depends: docker.io (>= 20.10) | docker-ce (>= 20.10)
Maintainer: AINative Studio <hello@ainative.studio>
Description: Self-hosted AI database with zero API costs
 ZeroLocal provides a complete local development environment
 for ZeroDB, including PostgreSQL, Qdrant, MinIO, and more.
Homepage: https://www.ainative.studio/zerolocal
```

**Install Command:**
```bash
sudo dpkg -i zerolocal_1.0.0.deb
sudo apt-get install -f  # Fix dependencies
```

### 3.3 .rpm Package (Fedora/RHEL)

**Spec File (zerolocal.spec):**
```spec
Name:           zerolocal
Version:        1.0.0
Release:        1%{?dist}
Summary:        Self-hosted AI database

License:        MIT
URL:            https://www.ainative.studio/zerolocal
Source0:        zerolocal-1.0.0.tar.gz

Requires:       docker >= 20.10

%description
ZeroLocal provides a complete local development environment
for ZeroDB, including PostgreSQL, Qdrant, MinIO, and more.

%prep
%setup -q

%install
mkdir -p %{buildroot}/opt/zerolocal
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/256x256/apps

cp zerolocal %{buildroot}/opt/zerolocal/
cp zerolocal.desktop %{buildroot}%{_datadir}/applications/
cp icon.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/zerolocal.png
ln -s /opt/zerolocal/zerolocal %{buildroot}%{_bindir}/zerolocal

%files
/opt/zerolocal/*
%{_bindir}/zerolocal
%{_datadir}/applications/zerolocal.desktop
%{_datadir}/icons/hicolor/256x256/apps/zerolocal.png

%changelog
* Mon Feb 10 2026 AINative Studio <hello@ainative.studio> - 1.0.0-1
- Initial release
```

**Build Command:**
```bash
rpmbuild -ba zerolocal.spec
```

---

## 4. Size Optimization

### 4.1 Docker Image Pre-loading

**Compress images:**
```bash
# Export Docker images
docker save postgres:16-alpine | gzip > postgres.tar.gz
docker save qdrant/qdrant:latest | gzip > qdrant.tar.gz
docker save minio/minio:latest | gzip > minio.tar.gz
docker save redpandadata/redpanda:latest | gzip > redpanda.tar.gz

# Custom images
docker save zerolocal/api:latest | gzip > zerodb-api.tar.gz
docker save zerolocal/embeddings:latest | gzip > embeddings.tar.gz
```

**Expected sizes (compressed):**
- postgres: ~50MB
- qdrant: ~45MB
- minio: ~35MB
- redpanda: ~60MB
- zerodb-api: ~40MB
- embeddings: ~500MB (includes model)

**Total: ~730MB → ~200MB in installer (better compression)**

### 4.2 Model Bundling

**Option 1: Bundle in installer (slower download, faster first run)**
- Include bge-small-en-v1.5 in installer
- Installer size: ~200-250MB

**Option 2: Download on first run (faster download, slower first run)**
- Installer size: ~80-100MB
- Download model on setup (adds 30-40 seconds)

**Recommendation:** Bundle model for best UX (one-time download)

---

## 5. Auto-Update Mechanism

### 5.1 Update Check

**Endpoint:**
```http
GET https://api.ainative.studio/v1/zerolocal/updates/check
Response:
{
  "current_version": "1.0.0",
  "latest_version": "1.1.0",
  "update_available": true,
  "required": false,
  "release_date": "2026-03-01",
  "download_url": "https://github.com/AINative-Studio/core/releases/download/v1.1.0/...",
  "release_notes": "...",
  "size_bytes": 52428800
}
```

### 5.2 Update Flow

```
[Background check] Every 24 hours
      │
      ├─[No update] → Continue
      │
      └─[Update available]
            │
            ▼
    [Show notification]
    "ZeroLocal 1.1.0 available"
    [Update now] [Later] [Details]
            │
            ▼
    [User clicks "Update now"]
            │
            ▼
    [Download in background]
    Progress: 45% (23MB / 50MB)
            │
            ▼
    [Download complete]
    "Update ready. Restart to apply?"
    [Restart] [Later]
            │
            ▼
    [Restart app]
            │
            ▼
    [Apply update]
      - Stop services
      - Replace binaries
      - Migrate data (if needed)
      - Restart services
            │
            ▼
    [Success]
    "Updated to 1.1.0"
    [Show changelog]
```

### 5.3 Rollback Mechanism

**Backup before update:**
```
/Applications/ZeroLocal.app → /Applications/ZeroLocal.app.backup
```

**If update fails:**
```
1. Detect failure (health checks don't pass)
2. Stop failed version
3. Restore backup
4. Restart old version
5. Notify user of failure
6. Report error to telemetry
```

---

## 6. Testing Matrix

### 6.1 Platform Coverage

| Platform | Version | Architecture | Priority |
|----------|---------|--------------|----------|
| macOS 14 Sonoma | 14.x | ARM64 | P0 |
| macOS 13 Ventura | 13.x | ARM64 | P0 |
| macOS 13 Ventura | 13.x | x86_64 | P1 |
| macOS 12 Monterey | 12.x | x86_64 | P1 |
| macOS 11 Big Sur | 11.x | x86_64 | P2 |
| Windows 11 | 23H2 | x86_64 | P0 |
| Windows 11 | 22H2 | x86_64 | P1 |
| Windows 10 | 22H2 | x86_64 | P1 |
| Ubuntu 24.04 LTS | Noble | x86_64 | P0 |
| Ubuntu 22.04 LTS | Jammy | x86_64 | P0 |
| Ubuntu 20.04 LTS | Focal | x86_64 | P1 |
| Fedora 39 | - | x86_64 | P1 |
| Arch Linux | Rolling | x86_64 | P2 |

### 6.2 Test Cases

**Installation:**
- [ ] Clean install
- [ ] Install over existing version
- [ ] Install with Docker already installed
- [ ] Install without Docker
- [ ] Install with port conflicts
- [ ] Install with insufficient disk space
- [ ] Install with insufficient RAM

**First Run:**
- [ ] Setup wizard completes
- [ ] All services start successfully
- [ ] Dashboard opens automatically
- [ ] Health checks pass
- [ ] Can create first project
- [ ] Can upsert first vector

**Updates:**
- [ ] Update notification appears
- [ ] Download completes
- [ ] Update applies successfully
- [ ] No data loss after update
- [ ] Rollback works if update fails

**Uninstall:**
- [ ] App uninstalls completely
- [ ] Data preserved (optional)
- [ ] Docker containers stopped
- [ ] CLI removed from PATH

---

## 7. Release Process

### 7.1 Build Pipeline

```yaml
# GitHub Actions workflow
name: Build Installers
on:
  push:
    tags:
      - 'v*'

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions-rs/toolchain@v1
      - name: Build macOS installer
        run: ./scripts/build-macos.sh
      - name: Sign and notarize
        run: ./scripts/sign-macos.sh
      - name: Upload artifact
        uses: actions/upload-artifact@v3

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Windows installer
        run: .\scripts\build-windows.ps1
      - name: Sign installer
        run: .\scripts\sign-windows.ps1
      - name: Upload artifact
        uses: actions/upload-artifact@v3

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build AppImage
        run: ./scripts/build-appimage.sh
      - name: Build .deb
        run: ./scripts/build-deb.sh
      - name: Build .rpm
        run: ./scripts/build-rpm.sh
      - name: Upload artifacts
        uses: actions/upload-artifact@v3

  release:
    needs: [build-macos, build-windows, build-linux]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v3
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            ZeroLocal-*-universal.dmg
            ZeroLocal-Setup-*.exe
            ZeroLocal-*-x86_64.AppImage
            zerolocal_*.deb
            zerolocal-*.rpm
```

### 7.2 Release Checklist

**Pre-release:**
- [ ] Version bumped in all files
- [ ] Changelog updated
- [ ] Tests passing on all platforms
- [ ] Docker images built and tagged
- [ ] Release notes written

**Build:**
- [ ] macOS .dmg built and signed
- [ ] Windows .exe built and signed
- [ ] Linux AppImage built
- [ ] .deb package built
- [ ] .rpm package built

**Publish:**
- [ ] GitHub release created
- [ ] Binaries uploaded
- [ ] Homebrew cask updated
- [ ] Chocolatey package published
- [ ] Website download links updated

**Post-release:**
- [ ] Announcement blog post
- [ ] Social media posts
- [ ] Discord announcement
- [ ] Email newsletter
- [ ] Monitor error rates

---

## Appendix: File Sizes

### Estimated Sizes (Compressed)

| Component | Size |
|-----------|------|
| Tauri binary (macOS) | 15 MB |
| Tauri binary (Windows) | 18 MB |
| Tauri binary (Linux) | 20 MB |
| Dashboard assets | 5 MB |
| Docker images (all, compressed) | 150 MB |
| Embeddings model (compressed) | 40 MB |
| CLI binary | 10 MB |
| **Total macOS .dmg** | **~200 MB** |
| **Total Windows .exe** | **~220 MB** |
| **Total Linux AppImage** | **~210 MB** |

### Download Times (Typical)

| Connection | 200 MB | 220 MB | 210 MB |
|------------|--------|--------|--------|
| 100 Mbps | 16 sec | 18 sec | 17 sec |
| 50 Mbps | 32 sec | 35 sec | 34 sec |
| 25 Mbps | 64 sec | 70 sec | 67 sec |
| 10 Mbps | 160 sec | 176 sec | 168 sec |

**Target:** 50+ Mbps (most developers) → ~30-35 seconds

---

**Next Steps:**
1. Build Tauri app shell
2. Create packaging scripts
3. Test on all platforms
4. Set up CI/CD pipeline
5. Beta testing program

Refs #1133
