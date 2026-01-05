# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PS5 Dump Runner FTP Installer - macOS version.

This spec file is configured for local macOS builds (no code signing).

Build command (on macOS):
    pyinstaller build/macos.spec --clean

Output: build/dist/PS5DumpRunnerInstaller.app

Platform support:
- macOS 11 (Big Sur) and later
- Both Apple Silicon (arm64) and Intel (x86_64)

Note: For distribution, you may want to:
1. Code sign with: codesign -s "Developer ID" PS5DumpRunnerInstaller.app
2. Notarize with Apple: xcrun notarytool submit
3. Package as DMG: create-dmg or hdiutil
"""

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

# Get the absolute path to the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

block_cipher = None

a = Analysis(
    [os.path.join(project_root, 'src', 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=[
        # Include icon resources
        (os.path.join(project_root, 'resources', 'icons', '*.icns'), 'resources/icons'),
        (os.path.join(project_root, 'resources', 'icons', '*.png'), 'resources/icons'),
    ],
    hiddenimports=[
        # Keyring - automatically collect all submodules and backends
        'keyring',
    ] + collect_submodules('keyring') + [
        # Tkinter components
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        # macOS-specific imports
        '_tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude test modules
        'pytest',
        'pytest_mock',
        'pyftpdlib',
        # Exclude unused modules to reduce bundle size
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        # Exclude Windows-specific modules
        'win32api',
        'win32con',
        'win32gui',
        'winreg',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PS5DumpRunnerInstaller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed application, no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,  # No code signing for local builds
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PS5DumpRunnerInstaller',
)

app = BUNDLE(
    coll,
    name='PS5DumpRunnerInstaller.app',
    icon=os.path.join(project_root, 'resources', 'icons', 'app_icon.icns'),
    bundle_identifier='com.ps5.dumprunnerinstaller',
    info_plist={
        'CFBundleName': 'PS5 Dump Runner Installer',
        'CFBundleDisplayName': 'PS5 Dump Runner Installer',
        'CFBundleVersion': '1.2.0',
        'CFBundleShortVersionString': '1.2.0',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '11.0',  # macOS Big Sur minimum
        'NSAppleEventsUsageDescription': 'This app needs to access FTP servers to manage PS5 game dumps.',
        'NSNetworkVolumesUsageDescription': 'This app needs to access network volumes to scan for game dumps.',
    },
)
