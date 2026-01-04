r"""Platform-specific volume detection for local/portable drives.

Detects available volumes based on the operating system:
- Windows: Drive letters (C:\, D:\, E:\, etc.)
- macOS: Mounted volumes in /Volumes/
- Linux: Mount points in /mnt/ and /media/$USER/
"""

import logging
import os
import sys
from pathlib import Path
from typing import List

logger = logging.getLogger("ps5_dump_runner.volumes")


def get_available_volumes() -> List[Path]:
    """
    Get available volumes based on platform.

    Returns:
        List of Path objects representing available volumes

    Examples:
        Windows: [Path("C:\\"), Path("D:\\"), Path("E:\\")]
        macOS: [Path("/Volumes/Macintosh HD"), Path("/Volumes/USB")]
        Linux: [Path("/mnt/usb0"), Path("/media/user/USB")]
    """
    if sys.platform == "win32":
        return _get_windows_drives()
    elif sys.platform == "darwin":
        return _get_macos_volumes()
    else:
        return _get_linux_mounts()


def _get_windows_drives() -> List[Path]:
    """
    Get available drive letters on Windows.

    Returns:
        List of Path objects for existing drives
    """
    import string

    drives = []
    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:\\")
        if drive.exists():
            drives.append(drive)
            logger.debug(f"Found Windows drive: {drive}")

    return drives


def _get_macos_volumes() -> List[Path]:
    """
    Get mounted volumes on macOS.

    Scans /Volumes/ directory for mounted filesystems.

    Returns:
        List of Path objects for mounted volumes
    """
    volumes_path = Path("/Volumes")
    volumes = []

    if volumes_path.exists():
        for volume in volumes_path.iterdir():
            if volume.is_dir():
                volumes.append(volume)
                logger.debug(f"Found macOS volume: {volume}")

    return volumes


def _get_linux_mounts() -> List[Path]:
    """
    Get mount points on Linux.

    Scans /mnt/ and /media/$USER/ for mounted filesystems.

    Returns:
        List of Path objects for mount points
    """
    mounts = []

    # Check /mnt/
    mnt_path = Path("/mnt")
    if mnt_path.exists():
        for mount in mnt_path.iterdir():
            if mount.is_dir():
                mounts.append(mount)
                logger.debug(f"Found Linux mount: {mount}")

    # Check /media/$USER/
    try:
        username = os.getlogin()
        media_path = Path(f"/media/{username}")
        if media_path.exists():
            for mount in media_path.iterdir():
                if mount.is_dir():
                    mounts.append(mount)
                    logger.debug(f"Found Linux media mount: {mount}")
    except Exception as e:
        logger.warning(f"Could not check /media/ directory: {e}")

    return mounts
