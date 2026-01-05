# macOS Build Guide - PS5 Dump Runner Installer

This guide explains how to build the PS5 Dump Runner Installer application locally on macOS for development and testing purposes.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Build Process Details](#build-process-details)
- [Troubleshooting](#troubleshooting)
- [Distribution Notes](#distribution-notes)

---

## Prerequisites

### System Requirements

- **Operating System**: macOS 11 (Big Sur) or later
- **Architecture**: Both Apple Silicon (arm64) and Intel (x86_64) are supported
- **Python**: Python 3.11 or higher

### Required Software

1. **Python 3.11+**
   ```bash
   # Check your Python version
   python3 --version

   # Install Python if needed (using Homebrew)
   brew install python@3.11
   ```

2. **PyInstaller**
   ```bash
   # Install PyInstaller
   pip install pyinstaller

   # Verify installation
   python3 -m PyInstaller --version
   ```

3. **Tkinter** (GUI framework)
   ```bash
   # Verify tkinter is available
   python3 -c "import tkinter"

   # If missing, install with Homebrew
   brew install python-tk@3.11
   ```

### Optional: Icon File

The build script expects an `.icns` icon file at `resources/icons/app_icon.icns`. If you don't have one:

```bash
# Convert PNG to ICNS format
# 1. Create an iconset directory
mkdir app_icon.iconset

# 2. Generate required icon sizes from your PNG
sips -z 512 512 resources/icons/app_icon.png --out app_icon.iconset/icon_512x512.png
sips -z 256 256 resources/icons/app_icon.png --out app_icon.iconset/icon_256x256.png
sips -z 128 128 resources/icons/app_icon.png --out app_icon.iconset/icon_128x128.png
sips -z 64 64 resources/icons/app_icon.png --out app_icon.iconset/icon_64x64.png
sips -z 32 32 resources/icons/app_icon.png --out app_icon.iconset/icon_32x32.png
sips -z 16 16 resources/icons/app_icon.png --out app_icon.iconset/icon_16x16.png

# 3. Convert to ICNS
iconutil -c icns app_icon.iconset -o resources/icons/app_icon.icns

# 4. Clean up
rm -rf app_icon.iconset
```

If the icon is missing, the build will succeed but the app will use a generic icon.

---

## Quick Start

```bash
# Navigate to project root
cd /path/to/ps5-dump-runner-installer

# Make build script executable
chmod +x build/build-macos.sh

# Run the build
./build/build-macos.sh
```

The application will be built to: `build/dist/PS5DumpRunnerInstaller.app`

---

## Build Process Details

### What the Build Script Does

The `build/build-macos.sh` script performs the following steps:

1. **Platform Validation**: Verifies the script is running on macOS
2. **Python Version Check**: Ensures Python 3.11+ is installed
3. **PyInstaller Check**: Verifies PyInstaller is available
4. **Dependency Check**: Validates tkinter and other required modules
5. **Icon Check**: Warns if the `.icns` icon file is missing
6. **Clean Build**: Removes previous build artifacts
7. **PyInstaller Build**: Runs PyInstaller with the macOS spec file
8. **Success Message**: Displays build location and usage instructions

### Build Configuration

The build is configured by `build/macos.spec`, which specifies:

- **Entry Point**: `src/main.py`
- **Application Name**: PS5DumpRunnerInstaller
- **Bundle Identifier**: com.ps5.dumprunnerinstaller
- **Minimum macOS Version**: 11.0 (Big Sur)
- **Icon**: `resources/icons/app_icon.icns`
- **Hidden Imports**:
  - Keyring backends (macOS Keychain integration)
  - tkinter components
- **Excluded Modules**: Test frameworks, Windows-specific modules
- **Code Signing**: None (local builds only)

### Output Structure

After a successful build, you'll find:

```
build/
├── dist/
│   └── PS5DumpRunnerInstaller.app/
│       ├── Contents/
│       │   ├── MacOS/
│       │   │   └── PS5DumpRunnerInstaller  # Main executable
│       │   ├── Resources/
│       │   │   ├── app_icon.icns
│       │   │   └── resources/icons/
│       │   ├── Frameworks/
│       │   └── Info.plist
│       └── ...
└── build/
    └── (temporary build files)
```

---

## Running the Application

### Method 1: Double-Click

Navigate to `build/dist/` in Finder and double-click `PS5DumpRunnerInstaller.app`.

**First Launch Warning**: Since this is an unsigned build, macOS will show an "unidentified developer" warning.

To bypass this:
1. Right-click the app and select **Open**
2. Click **Open** in the security dialog

Or:
1. Go to **System Preferences** > **Security & Privacy**
2. Click **Allow anyway** next to the warning message
3. Try opening the app again

### Method 2: Command Line

```bash
# Run from command line
open build/dist/PS5DumpRunnerInstaller.app

# Or run the executable directly
build/dist/PS5DumpRunnerInstaller.app/Contents/MacOS/PS5DumpRunnerInstaller
```

---

## Troubleshooting

### Issue: "Python version too old"

**Error**: `Error: Python 3.11 or higher required (found 3.9.x)`

**Solution**: Install Python 3.11+ using Homebrew:
```bash
brew install python@3.11
# Make sure python3 points to the correct version
which python3
python3 --version
```

### Issue: "PyInstaller not found"

**Error**: `Error: PyInstaller not found`

**Solution**: Install PyInstaller:
```bash
pip install pyinstaller
# Or with specific Python version
python3 -m pip install pyinstaller
```

### Issue: "tkinter not found"

**Error**: `Error: tkinter not found`

**Solution**: Install tkinter via Homebrew:
```bash
brew install python-tk@3.11
```

### Issue: Build succeeds but app doesn't launch

**Symptoms**: App icon bounces in dock but doesn't open

**Solutions**:
1. Check Console.app for error messages
2. Run from command line to see errors:
   ```bash
   build/dist/PS5DumpRunnerInstaller.app/Contents/MacOS/PS5DumpRunnerInstaller
   ```
3. Verify all dependencies are included in the build
4. Check that Python version matches between build and runtime

### Issue: "Operation not permitted"

**Error**: When trying to run `build-macos.sh`

**Solution**: Make the script executable:
```bash
chmod +x build/build-macos.sh
```

### Issue: Large application size

**Observation**: The .app bundle is larger than expected

**Explanation**: PyInstaller bundles the entire Python runtime and all dependencies. This is normal for bundled applications.

**Optimization** (optional):
- The spec file uses `upx=True` for compression
- You can manually run UPX on the executable if needed
- For production, consider code signing which also optimizes the bundle

---

## Distribution Notes

### Important: This is a Local Build Only

The build script creates an **unsigned** .app bundle suitable for:
- ✅ Local development and testing
- ✅ Internal team distribution
- ❌ Public distribution
- ❌ Mac App Store submission

### For Production Distribution

To distribute the app publicly, you must:

#### 1. Code Sign with Apple Developer Certificate

```bash
# Sign the application
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  build/dist/PS5DumpRunnerInstaller.app
```

#### 2. Notarize with Apple

```bash
# Create a ZIP for notarization
ditto -c -k --keepParent \
  build/dist/PS5DumpRunnerInstaller.app \
  PS5DumpRunnerInstaller.zip

# Submit for notarization
xcrun notarytool submit PS5DumpRunnerInstaller.zip \
  --apple-id "your@email.com" \
  --team-id "TEAM_ID" \
  --password "app-specific-password" \
  --wait

# Staple the notarization ticket
xcrun stapler staple build/dist/PS5DumpRunnerInstaller.app
```

#### 3. Create a DMG (Optional but Recommended)

```bash
# Create a DMG for distribution
hdiutil create -volname "PS5 Dump Runner Installer" \
  -srcfolder build/dist/PS5DumpRunnerInstaller.app \
  -ov -format UDZO \
  PS5DumpRunnerInstaller.dmg
```

### Apple Developer Account Required

Code signing and notarization require:
- Apple Developer Account ($99/year)
- Developer ID Application certificate
- App-specific password for notarization

See the [Constitution Principle VII](../.specify/memory/constitution.md#vii-multi-platform-release-strategy) for release coordination strategy.

---

## Build Script Reference

### Usage

```bash
./build/build-macos.sh
```

### Exit Codes

- `0`: Success
- `1`: Error (platform check, version check, missing dependencies, or build failure)

### Environment Variables

The script respects standard environment variables:
- `PYTHON3`: Override Python executable (default: `python3`)

### Output

The script uses colored output:
- 🟢 Green: Success messages
- 🟡 Yellow: Warnings
- 🔴 Red: Error messages

### Logs

PyInstaller logs are written to:
- `build/build/PS5DumpRunnerInstaller/warn-PS5DumpRunnerInstaller.txt`

---

## Related Documentation

- [Windows Build Guide](../build/windows.spec) (Windows-specific instructions)
- [README.md](../README.md) (General project documentation)
- [Constitution](../.specify/memory/constitution.md) (Project principles and release strategy)

---

## Support

For build issues:
1. Check the [Troubleshooting](#troubleshooting) section above
2. Review PyInstaller logs in `build/build/`
3. Run the executable from command line to see error messages
4. Check GitHub Issues for known build problems

For macOS-specific FTP issues, see the [FTP LIST Parser documentation](../src/ftp/list_parser.py).
