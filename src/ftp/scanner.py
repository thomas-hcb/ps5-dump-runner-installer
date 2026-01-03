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

logger = logging.getLogger("ps5_dump_runner.scanner")


class LocationType(Enum):
    """Location where a game dump is stored."""
    INTERNAL = "internal"
    USB = "usb"
    EXTERNAL = "external"
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
            LocationType.USB: "[USB]",
            LocationType.EXTERNAL: "[EXT]",
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
                # Try to list the directory with retry
                entries = self._nlst_with_retry(ftp, base_path)
                logger.debug(f"Found {len(entries)} entries in {base_path}")

                for entry in entries:
                    # Skip if it's the base path itself
                    if entry == base_path.rstrip("/"):
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
            except Exception as e:
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

        Args:
            ftp: FTP connection object
            path: Directory path to list
            retries: Number of retry attempts

        Returns:
            List of entries from nlst

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
                # Permission error, don't retry
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
            files = self._nlst_with_retry(ftp, dump.path)
            file_names = [f.split("/")[-1] for f in files]

            dump.has_elf = "dump_runner.elf" in file_names
            dump.has_js = "homebrew.js" in file_names

            if dump.has_elf and dump.has_js:
                # Files present, but we can't easily determine official vs experimental
                dump.installation_status = InstallationStatus.UNKNOWN
            elif dump.has_elf or dump.has_js:
                # Partial installation
                dump.installation_status = InstallationStatus.UNKNOWN
            else:
                dump.installation_status = InstallationStatus.NOT_INSTALLED

        except error_perm:
            # Can't access directory
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
