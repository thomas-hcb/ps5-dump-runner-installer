r"""Platform-specific volume detection for local/portable drives.

Detects available volumes based on the operating system:
- Windows: Drive letters (C:\, D:\, E:\, etc.)
- macOS: Mounted volumes in /Volumes/
- Linux: Mount points in /mnt/ and /media/$USER/
"""

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger("ps5_dump_runner.volumes")


@dataclass
class VolumeInfo:
    """Information about a volume/drive."""
    path: Path
    is_removable: bool
    label: str = ""


def get_available_volumes() -> List[VolumeInfo]:
    """
    Get available volumes based on platform.

    Returns:
        List of VolumeInfo objects representing available volumes with metadata

    Examples:
        Windows: [VolumeInfo(Path("C:\\"), False, "Local Disk"), ...]
        macOS: [VolumeInfo(Path("/Volumes/USB"), True, "USB")]
        Linux: [VolumeInfo(Path("/mnt/usb0"), True, "usb0")]
    """
    if sys.platform == "win32":
        return _get_windows_drives()
    elif sys.platform == "darwin":
        return _get_macos_volumes()
    else:
        return _get_linux_mounts()


def _get_windows_drives() -> List[VolumeInfo]:
    """
    Get available drive letters on Windows with removable status.

    Returns:
        List of VolumeInfo objects for existing drives
    """
    import string

    drives = []
    for letter in string.ascii_uppercase:
        drive_path = Path(f"{letter}:\\")
        if not drive_path.exists():
            continue

        # Check if drive is removable using ctypes
        is_removable = False
        label = f"{letter}:"

        try:
            import ctypes
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(f"{letter}:\\")
            # DRIVE_REMOVABLE = 2, DRIVE_FIXED = 3, DRIVE_REMOTE = 4
            is_removable = (drive_type == 2)

            # Try to get volume label
            try:
                volume_name_buffer = ctypes.create_unicode_buffer(1024)
                ctypes.windll.kernel32.GetVolumeInformationW(
                    f"{letter}:\\",
                    volume_name_buffer,
                    ctypes.sizeof(volume_name_buffer),
                    None, None, None, None, 0
                )
                volume_label = volume_name_buffer.value
                if volume_label:
                    label = f"{letter}: ({volume_label})"
            except Exception:
                pass  # Keep default label

        except Exception as e:
            logger.debug(f"Could not determine drive type for {letter}:\\: {e}")

        volume_info = VolumeInfo(
            path=drive_path,
            is_removable=is_removable,
            label=label
        )
        drives.append(volume_info)
        logger.debug(f"Found Windows drive: {drive_path} (removable={is_removable})")

    return drives


def _get_macos_volumes() -> List[VolumeInfo]:
    """
    Get mounted volumes on macOS.

    Scans /Volumes/ directory for mounted filesystems.

    Returns:
        List of VolumeInfo objects for mounted volumes
    """
    volumes_path = Path("/Volumes")
    volumes = []

    if volumes_path.exists():
        for volume in volumes_path.iterdir():
            if volume.is_dir():
                # On macOS, external drives are usually in /Volumes
                # System drive is typically "Macintosh HD"
                is_removable = volume.name not in ["Macintosh HD", "System", "Data"]

                volume_info = VolumeInfo(
                    path=volume,
                    is_removable=is_removable,
                    label=volume.name
                )
                volumes.append(volume_info)
                logger.debug(f"Found macOS volume: {volume} (removable={is_removable})")

    return volumes


def _get_linux_mounts() -> List[VolumeInfo]:
    """
    Get mount points on Linux.

    Scans /mnt/ and /media/$USER/ for mounted filesystems.

    Returns:
        List of VolumeInfo objects for mount points
    """
    mounts = []

    # Check /mnt/
    mnt_path = Path("/mnt")
    if mnt_path.exists():
        for mount in mnt_path.iterdir():
            if mount.is_dir():
                # Mounts in /mnt are typically removable devices
                volume_info = VolumeInfo(
                    path=mount,
                    is_removable=True,
                    label=mount.name
                )
                mounts.append(volume_info)
                logger.debug(f"Found Linux mount: {mount} (removable=True)")

    # Check /media/$USER/
    try:
        username = os.getlogin()
        media_path = Path(f"/media/{username}")
        if media_path.exists():
            for mount in media_path.iterdir():
                if mount.is_dir():
                    # Mounts in /media/$USER are removable devices
                    volume_info = VolumeInfo(
                        path=mount,
                        is_removable=True,
                        label=mount.name
                    )
                    mounts.append(volume_info)
                    logger.debug(f"Found Linux media mount: {mount} (removable=True)")
    except Exception as e:
        logger.warning(f"Could not check /media/ directory: {e}")

    return mounts
