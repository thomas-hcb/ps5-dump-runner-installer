"""Game dump scanner for PS5 Dump Runner FTP Installer.

Scans PS5 directories for game dumps and tracks their status.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from ftplib import error_perm
from typing import List, Optional

from src.config.paths import SCAN_PATHS, get_location_type_from_path
from src.ftp.connection import FTPConnectionManager
from src.ftp.exceptions import FTPNotConnectedError
from src.ftp.list_parser import parse_list_output

logger = logging.getLogger("ps5_dump_runner.scanner")


class LocationType(Enum):
    """Location where a game dump is stored."""
    INTERNAL = "internal"
    # USB storage devices (usb0-usb7)
    USB0 = "usb0"
    USB1 = "usb1"
    USB2 = "usb2"
    USB3 = "usb3"
    USB4 = "usb4"
    USB5 = "usb5"
    USB6 = "usb6"
    USB7 = "usb7"
    # External storage devices (ext0-ext1)
    EXT0 = "ext0"
    EXT1 = "ext1"
    # Legacy/fallback types
    USB = "usb"  # Generic USB (for backward compatibility)
    EXTERNAL = "external"  # Generic external (for backward compatibility)
    LOCAL = "local"
    UNKNOWN = "unknown"


class InstallationStatus(Enum):
    """Installation status of dump_runner files."""
    NOT_INSTALLED = "not_installed"
    OFFICIAL = "official"
    EXPERIMENTAL = "experimental"
    UNKNOWN = "unknown"


@dataclass
class GameDump:
    """Represents a discovered game dump directory on the PS5."""
    path: str
    name: str
    location_type: LocationType
    installation_status: InstallationStatus = InstallationStatus.NOT_INSTALLED
    installed_version: Optional[str] = None
    installed_at: Optional[datetime] = None
    is_experimental: bool = False
    has_elf: bool = False
    has_js: bool = False

    @classmethod
    def from_path(cls, full_path: str) -> "GameDump":
        """
        Create a GameDump from an FTP path.

        Args:
            full_path: Full FTP path to the dump directory

        Returns:
            GameDump instance
        """
        # Extract directory name from path
        name = full_path.rstrip("/").split("/")[-1]

        # Determine location type
        location_str = get_location_type_from_path(full_path)
        location_type = LocationType(location_str) if location_str != "unknown" else LocationType.UNKNOWN

        return cls(
            path=full_path,
            name=name,
            location_type=location_type,
        )

    @property
    def display_name(self) -> str:
        """Human-readable name with location indicator."""
        location_prefix = {
            LocationType.INTERNAL: "[INT]",
            # USB storage devices
            LocationType.USB0: "[USB0]",
            LocationType.USB1: "[USB1]",
            LocationType.USB2: "[USB2]",
            LocationType.USB3: "[USB3]",
            LocationType.USB4: "[USB4]",
            LocationType.USB5: "[USB5]",
            LocationType.USB6: "[USB6]",
            LocationType.USB7: "[USB7]",
            # External storage devices
            LocationType.EXT0: "[EXT0]",
            LocationType.EXT1: "[EXT1]",
            # Legacy/fallback types
            LocationType.USB: "[USB]",
            LocationType.EXTERNAL: "[EXT]",
            LocationType.LOCAL: "[LOC]",
            LocationType.UNKNOWN: "[???]",
        }
        return f"{location_prefix[self.location_type]} {self.name}"

    @property
    def is_installed(self) -> bool:
        """True if dump_runner files are installed."""
        return self.installation_status != InstallationStatus.NOT_INSTALLED


class DumpScanner:
    """Scans PS5 directories for game dumps."""

    def __init__(self, connection: FTPConnectionManager):
        """
        Initialize the scanner.

        Args:
            connection: Active FTP connection manager
        """
        self._connection = connection
        self._last_scan: Optional[datetime] = None
        self._dumps: List[GameDump] = []

    @property
    def last_scan(self) -> Optional[datetime]:
        """Timestamp of last scan."""
        return self._last_scan

    @property
    def dumps(self) -> List[GameDump]:
        """List of discovered dumps from last scan."""
        return self._dumps.copy()

    def scan(self) -> List[GameDump]:
        """
        Scan all configured paths for game dumps.

        Returns:
            List of discovered GameDump objects

        Raises:
            FTPNotConnectedError: If FTP not connected
        """
        if not self._connection.is_connected:
            raise FTPNotConnectedError("Scan")

        self._dumps = []
        ftp = self._connection.ftp

        # Send NOOP to verify connection is still alive
        try:
            ftp.voidcmd("NOOP")
        except Exception:
            # Connection is dead, re-raise as connection error
            raise OSError("[WinError 10061] Connection lost - FTP server not responding")

        for base_path in SCAN_PATHS:
            try:
                logger.debug(f"Scanning path: {base_path}")

                # Quick existence check using CWD before trying to list
                # This is safer than NLST/LIST which can cause connection issues
                try:
                    current_dir = ftp.pwd()
                    ftp.cwd(base_path)
                    ftp.cwd(current_dir)  # Return to original dir
                except error_perm:
                    # Directory doesn't exist, skip it
                    logger.debug(f"Path does not exist: {base_path}")
                    continue

                # Try to list the directory with retry
                entries = self._nlst_with_retry(ftp, base_path)
                logger.debug(f"Found {len(entries)} entries in {base_path}")

                for entry in entries:
                    # Skip if it's the base path itself
                    if entry == base_path.rstrip("/"):
                        continue

                    # Extract just the directory name (last part of path)
                    entry_name = entry.rstrip("/").split("/")[-1]

                    # Skip special directories and system folders
                    if entry_name in ('.', '..', 'OffAct', 'system', 'System'):
                        logger.debug(f"Skipping system directory: {entry_name}")
                        continue

                    # Construct full path
                    if entry.startswith("/"):
                        full_path = entry
                    else:
                        full_path = f"{base_path.rstrip('/')}/{entry}"

                    # Check if it's a directory by trying to list it
                    try:
                        self._nlst_with_retry(ftp, full_path)
                        # If we can list it, it's a directory
                        dump = GameDump.from_path(full_path)
                        self._check_installation_status(dump)
                        self._dumps.append(dump)
                        logger.debug(f"Added dump: {dump.name}")
                    except error_perm:
                        # Not a directory or can't access, skip
                        continue
                    except Exception as e:
                        # Log but continue with other entries
                        logger.warning(f"Error checking {full_path}: {e}")
                        continue

            except error_perm:
                # Path doesn't exist or can't access, skip
                logger.debug(f"Path not accessible: {base_path}")
                continue
            except OSError as e:
                # Connection was lost (WinError 10053, etc.)
                error_str = str(e)
                if "10053" in error_str or "10054" in error_str:
                    # Try to check if connection is still alive with NOOP
                    try:
                        ftp.voidcmd("NOOP")
                        # Connection still alive, just skip this path
                        logger.warning(f"Error scanning {base_path}: {e} (connection recovered)")
                        continue
                    except Exception:
                        # Connection is truly dead
                        logger.warning(f"Connection lost while scanning {base_path}, skipping remaining paths")
                        break
                logger.warning(f"Error scanning {base_path}: {e}")
                continue
            except Exception as e:
                # Check for "150 Opening data transfer" error - PS5 FTP server quirk
                error_str = str(e)
                if "150" in error_str:
                    # This is a failed data transfer, try to recover
                    try:
                        ftp.voidcmd("NOOP")
                        logger.debug(f"Path {base_path} failed with 150 error, but connection still alive")
                        continue
                    except Exception:
                        logger.warning(f"Connection lost after 150 error on {base_path}, skipping remaining paths")
                        break
                # Log other errors but continue scanning other paths
                logger.warning(f"Error scanning {base_path}: {e}")
                continue

        self._last_scan = datetime.now()
        logger.info(f"Scan complete: found {len(self._dumps)} dumps")
        return self._dumps

    def _nlst_with_retry(self, ftp, path: str, retries: int = 2) -> list:
        """
        List directory with retry on transient connection errors.

        Some FTP servers (like PS5) may drop data connections intermittently.
        If NLST command fails (e.g., on macOS), automatically falls back to LIST command.

        Args:
            ftp: FTP connection object
            path: Directory path to list
            retries: Number of retry attempts

        Returns:
            List of entries from nlst or LIST (fallback)

        Raises:
            error_perm: If path doesn't exist or permission denied
            Exception: If all retries fail
        """
        import time
        last_error = None

        for attempt in range(retries + 1):
            try:
                return ftp.nlst(path)
            except error_perm:
                # NLST may not be supported - try LIST fallback
                logger.debug(f"NLST failed for {path}, attempting LIST fallback")
                try:
                    return self._list_with_fallback(ftp, path)
                except error_perm:
                    # Permission error on LIST too, don't retry
                    raise
                except Exception as list_error:
                    # LIST also failed, raise original error
                    logger.warning(f"Both NLST and LIST failed for {path}")
                    raise
            except Exception as e:
                last_error = e
                if attempt < retries:
                    # Small delay before retry
                    time.sleep(0.3)
                    # Try to keep connection alive
                    try:
                        ftp.voidcmd("NOOP")
                    except Exception:
                        pass
                    continue

        # All retries failed
        raise last_error

    def _list_with_fallback(self, ftp, path: str) -> list:
        """
        List directory using LIST command (fallback when NLST not supported).

        The LIST command returns full directory listings with metadata.
        This method parses the output to extract directory names only.

        Args:
            ftp: FTP connection object
            path: Directory path to list

        Returns:
            List of directory names (parsed from LIST output)

        Raises:
            error_perm: If path doesn't exist or permission denied
            Exception: If LIST command fails
        """
        logger.info(f"Using LIST fallback for {path} (NLST not supported)")

        # Execute LIST command and capture output
        listing = []

        def capture_line(line):
            listing.append(line)

        # FTP servers often can't handle paths with special characters (like [ ] in game names)
        # Solution: Change directory first, then list current directory
        current_dir = ftp.pwd()  # Save current directory
        try:
            ftp.cwd(path)  # Change to target directory
            ftp.dir(capture_line)  # List current directory (no path argument)
            ftp.cwd(current_dir)  # Return to original directory
        except Exception as dir_error:
            # Try to restore original directory even if listing failed
            try:
                ftp.cwd(current_dir)
            except:
                pass
            raise  # Re-raise the exception

        # Parse the LIST output to extract directory names
        list_output = '\n'.join(listing)

        directories = parse_list_output(list_output)

        # Convert directory names to full paths (matching NLST behavior)
        full_paths = []
        for dirname in directories:
            if dirname.startswith("/"):
                full_paths.append(dirname)
            else:
                full_paths.append(f"{path.rstrip('/')}/{dirname}")

        logger.debug(f"LIST fallback found {len(full_paths)} directories in {path}")
        return full_paths

    def _list_files_in_dir(self, ftp, dir_path: str) -> list:
        """
        List all files (not directories) in a directory using CWD + LIST.

        Args:
            ftp: FTP connection object
            dir_path: Directory path to list

        Returns:
            List of filenames (not full paths, just names)
        """
        current_dir = ftp.pwd()
        files = []
        try:
            ftp.cwd(dir_path)
            listing = []
            ftp.dir(lambda line: listing.append(line))

            for line in listing:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) < 8:
                    continue
                permissions = parts[0]
                # Files start with '-', directories start with 'd'
                if permissions.startswith('-'):
                    # Extract filename (last part, may contain spaces)
                    filename = ' '.join(parts[8:])
                    files.append(filename)

            return files
        except Exception as e:
            logger.debug(f"Failed to list files in {dir_path}: {e}")
            return []
        finally:
            try:
                ftp.cwd(current_dir)
            except Exception:
                pass

    def _check_installation_status(self, dump: GameDump) -> None:
        """
        Check if dump_runner files are installed in a dump.

        Args:
            dump: GameDump to check (modified in place)
        """
        if not self._connection.is_connected:
            return

        ftp = self._connection.ftp

        try:
            # List all files in the dump directory
            files = self._list_files_in_dir(ftp, dump.path)

            dump.has_elf = "dump_runner.elf" in files
            dump.has_js = "homebrew.js" in files

            if dump.has_elf and dump.has_js:
                # Files present, but we can't easily determine official vs experimental
                dump.installation_status = InstallationStatus.UNKNOWN
            elif dump.has_elf or dump.has_js:
                # Partial installation
                dump.installation_status = InstallationStatus.UNKNOWN
            else:
                dump.installation_status = InstallationStatus.NOT_INSTALLED

            logger.debug(f"Installation status for {dump.name}: has_elf={dump.has_elf}, has_js={dump.has_js}")

        except error_perm:
            # Can't access directory
            dump.installation_status = InstallationStatus.UNKNOWN
        except Exception as e:
            # Other errors (like connection issues)
            logger.warning(f"Failed to check installation status for {dump.name}: {e}")
            dump.installation_status = InstallationStatus.UNKNOWN

    def refresh(self, dump: GameDump) -> GameDump:
        """
        Refresh status of a single dump.

        Args:
            dump: GameDump to refresh

        Returns:
            Updated GameDump with current status

        Raises:
            FTPNotConnectedError: If FTP not connected
        """
        if not self._connection.is_connected:
            raise FTPNotConnectedError("Refresh")

        self._check_installation_status(dump)
        return dump

    def get_dump_by_path(self, path: str) -> Optional[GameDump]:
        """
        Find a dump by its path.

        Args:
            path: FTP path to search for

        Returns:
            GameDump if found, None otherwise
        """
        for dump in self._dumps:
            if dump.path == path:
                return dump
        return None

    def get_dumps_by_location(self, location: LocationType) -> List[GameDump]:
        """
        Get all dumps from a specific location.

        Args:
            location: LocationType to filter by

        Returns:
            List of matching GameDump objects
        """
        return [d for d in self._dumps if d.location_type == location]

    def get_installed_dumps(self) -> List[GameDump]:
        """Get all dumps with dump_runner installed."""
        return [d for d in self._dumps if d.is_installed]

    def get_uninstalled_dumps(self) -> List[GameDump]:
        """Get all dumps without dump_runner installed."""
        return [d for d in self._dumps if not d.is_installed]
