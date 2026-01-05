# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PS5 Dump Runner FTP Installer.

Build command:
    pyinstaller build/ps5-dump-runner-installer.spec

Output: build/dist/PS5DumpRunnerInstaller.exe
"""

import os
import sys

# Get the absolute path to the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

block_cipher = None

a = Analysis(
    [os.path.join(project_root, 'src', 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=[
        # Include icon resources
        (os.path.join(project_root, 'resources', 'icons', '*.ico'), 'resources/icons'),
        (os.path.join(project_root, 'resources', 'icons', '*.png'), 'resources/icons'),
    ],
    hiddenimports=[
        # Ensure keyring backends are included
        'keyring.backends',
        'keyring.backends.Windows',
        # Tkinter components
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude test modules
        'pytest',
        'pytest_mock',
        'pyftpdlib',
        # Exclude unused modules
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PS5DumpRunnerInstaller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed application, no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_root, 'resources', 'icons', 'app_icon.ico'),
)
