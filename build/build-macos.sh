#!/bin/bash
################################################################################
# PS5 Dump Runner Installer - macOS Build Script
#
# This script builds a local development version of the application for macOS.
# No code signing or notarization is performed.
#
# Requirements:
#   - macOS 11 (Big Sur) or later
#   - Python 3.11+
#   - PyInstaller installed (pip install pyinstaller)
#
# Usage:
#   ./build/build-macos.sh
#
# Output:
#   build/dist/PS5DumpRunnerInstaller.app
#
# Notes:
#   - This creates an unsigned .app bundle for local testing only
#   - For distribution, you'll need to code sign and notarize separately
#   - The app may show "unidentified developer" warnings on other Macs
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "======================================================================"
echo "PS5 Dump Runner Installer - macOS Build Script"
echo "======================================================================"
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This script must be run on macOS${NC}"
    exit 1
fi

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.11"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo -e "${RED}Error: Python $REQUIRED_VERSION or higher required (found $PYTHON_VERSION)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# Check if PyInstaller is installed
echo "Checking PyInstaller..."
if ! python3 -m PyInstaller --version &> /dev/null; then
    echo -e "${RED}Error: PyInstaller not found${NC}"
    echo "Install with: pip install pyinstaller"
    exit 1
fi
PYINSTALLER_VERSION=$(python3 -m PyInstaller --version)
echo -e "${GREEN}✓ PyInstaller $PYINSTALLER_VERSION${NC}"

# Check for required dependencies
echo "Checking dependencies..."
if ! python3 -c "import tkinter" &> /dev/null; then
    echo -e "${RED}Error: tkinter not found${NC}"
    echo "Install with: brew install python-tk@3.11"
    exit 1
fi

# Check for keyring (critical dependency)
if ! python3 -c "import keyring" &> /dev/null; then
    echo -e "${RED}Error: keyring not found${NC}"
    echo "Install dependencies with: pip3 install -r requirements.txt"
    exit 1
fi

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check for icon file
ICON_FILE="$PROJECT_ROOT/resources/icons/app_icon.icns"
if [ ! -f "$ICON_FILE" ]; then
    echo -e "${YELLOW}Warning: app_icon.icns not found${NC}"
    echo "The app will build without a custom icon."
    echo "To create one, convert app_icon.png to .icns format:"
    echo "  mkdir app_icon.iconset"
    echo "  sips -z 512 512 app_icon.png --out app_icon.iconset/icon_512x512.png"
    echo "  iconutil -c icns app_icon.iconset"
fi

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
rm -rf "$PROJECT_ROOT/build/dist"
rm -rf "$PROJECT_ROOT/build/build"
echo -e "${GREEN}✓ Clean complete${NC}"

# Build the application
echo ""
echo "Building application..."
cd "$PROJECT_ROOT"
python3 -m PyInstaller build/macos.spec \
    --distpath "$PROJECT_ROOT/build/dist" \
    --workpath "$PROJECT_ROOT/build/build" \
    --clean --noconfirm

# Check if build succeeded
if [ ! -d "$PROJECT_ROOT/build/dist/PS5DumpRunnerInstaller.app" ]; then
    echo -e "${RED}Error: Build failed - .app bundle not created${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Build complete${NC}"

# Display build info
APP_PATH="$PROJECT_ROOT/build/dist/PS5DumpRunnerInstaller.app"
APP_SIZE=$(du -sh "$APP_PATH" | awk '{print $1}')

echo ""
echo "======================================================================"
echo -e "${GREEN}Build successful!${NC}"
echo "======================================================================"
echo ""
echo "Output: build/dist/PS5DumpRunnerInstaller.app"
echo "Size: $APP_SIZE"
echo ""
echo "To run the application:"
echo "  open build/dist/PS5DumpRunnerInstaller.app"
echo ""
echo "To test from command line:"
echo "  build/dist/PS5DumpRunnerInstaller.app/Contents/MacOS/PS5DumpRunnerInstaller"
echo ""
echo -e "${YELLOW}Note: This is an unsigned build for local testing only.${NC}"
echo "If you see \"unidentified developer\" warnings:"
echo "  1. Right-click the app and select 'Open'"
echo "  2. Or: System Preferences > Security & Privacy > Allow anyway"
echo ""
echo "For distribution, you'll need to:"
echo "  1. Code sign: codesign -s \"Developer ID\" PS5DumpRunnerInstaller.app"
echo "  2. Notarize: xcrun notarytool submit ..."
echo "  3. Package as DMG: hdiutil create -volname \"PS5 Dump Runner\" ..."
echo "======================================================================"
