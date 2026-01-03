"""Path constants and discovery for PS5 Dump Runner FTP Installer.

Defines PS5 FTP scan paths and application data directories.
"""

import os
import sys
from pathlib import Path
from typing import List


# Application name for config directories
APP_NAME = "PS5DumpRunnerInstaller"


# PS5 FTP scan paths (directories containing game dumps)
SCAN_PATHS: List[str] = [
    # Internal storage
    "/data/homebrew/",
    # USB storage devices (usb0-usb7)
    *[f"/mnt/usb{i}/homebrew/" for i in range(8)],
    # Extended storage devices (ext0-ext7)
    *[f"/mnt/ext{i}/homebrew/" for i in range(8)],
]


# Files to upload to each dump
DUMP_RUNNER_FILES = [
    "dump_runner.elf",
    "homebrew.js",
]


def get_app_data_dir() -> Path:
    """
    Get the application data directory.

    Returns:
        Path to app data directory (created if not exists)

    Platform-specific locations:
        - Windows: %APPDATA%/PS5DumpRunnerInstaller
        - Linux: ~/.config/PS5DumpRunnerInstaller
        - macOS: ~/Library/Application Support/PS5DumpRunnerInstaller
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    app_dir = base / APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_settings_path() -> Path:
    """
    Get the path to the settings JSON file.

    Returns:
        Path to settings.json
    """
    return get_app_data_dir() / "settings.json"


def get_cache_dir() -> Path:
    """
    Get the cache directory for downloaded releases.

    Returns:
        Path to cache directory (created if not exists)
    """
    cache_dir = get_app_data_dir() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_releases_cache_dir() -> Path:
    """
    Get the directory for cached release downloads.

    Returns:
        Path to releases cache directory (created if not exists)
    """
    releases_dir = get_cache_dir() / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)
    return releases_dir


def get_log_dir() -> Path:
    """
    Get the directory for log files.

    Returns:
        Path to logs directory (created if not exists)
    """
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file_path() -> Path:
    """
    Get the path to the main log file.

    Returns:
        Path to application log file
    """
    return get_log_dir() / "app.log"


def get_location_type_from_path(ftp_path: str) -> str:
    """
    Determine the location type from an FTP path.

    Args:
        ftp_path: FTP path to analyze

    Returns:
        'internal', 'usb', or 'external'
    """
    if ftp_path.startswith("/data/"):
        return "internal"
    elif ftp_path.startswith("/mnt/usb"):
        return "usb"
    elif ftp_path.startswith("/mnt/ext"):
        return "external"
    else:
        return "unknown"
