"""Local filesystem scanner for game dumps.

Scans local/portable drives for PS5 game dumps without requiring FTP connection.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.ftp.scanner import GameDump, InstallationStatus, LocationType

logger = logging.getLogger("ps5_dump_runner.local_scanner")

# Predefined subpaths to scan on selected volume
PREDEFINED_PATHS = ["homebrew", "etaHEN/games"]


class LocalScanner:
    """Scans local directories for game dumps.

    Implements ScannerProtocol for compatibility with UI code.
    """

    def __init__(self, base_volume: Path):
        """
        Initialize the local scanner.

        Args:
            base_volume: Base volume/drive to scan (e.g., Path("E:\\") on Windows)
        """
        self._base_volume = base_volume
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
        Scan predefined paths on the base volume for game dumps.

        Scans: homebrew/ and etaHEN/games/ subdirectories.

        Returns:
            List of discovered GameDump objects
        """
        self._dumps = []

        for subpath in PREDEFINED_PATHS:
            scan_path = self._base_volume / subpath
            logger.debug(f"Scanning local path: {scan_path}")

            if not scan_path.exists():
                logger.debug(f"Path does not exist: {scan_path}")
                continue

            if not scan_path.is_dir():
                logger.debug(f"Path is not a directory: {scan_path}")
                continue

            try:
                for entry in scan_path.iterdir():
                    if entry.is_dir():
                        dump = self._check_dump_folder(entry)
                        if dump:
                            self._dumps.append(dump)
                            logger.debug(f"Found dump: {dump.name}")
            except PermissionError as e:
                logger.warning(f"Permission denied accessing {scan_path}: {e}")
            except Exception as e:
                logger.error(f"Error scanning {scan_path}: {e}")

        self._last_scan = datetime.now()
        logger.info(f"Local scan complete: found {len(self._dumps)} dumps")
        return self._dumps

    def _check_dump_folder(self, folder_path: Path) -> Optional[GameDump]:
        """
        Check if a folder is a valid game dump directory.

        Any folder with an eboot.bin file is considered a valid dump.
        Users can name their folders however they want.

        Args:
            folder_path: Path to potential game dump folder

        Returns:
            GameDump if valid, None otherwise
        """
        folder_name = folder_path.name

        # Check for eboot.bin file (indicates a game dump)
        eboot_file = folder_path / "eboot.bin"
        if not eboot_file.exists():
            logger.debug(f"No eboot.bin found in {folder_name}, skipping")
            return None

        # Create GameDump with LOCAL location type
        dump = GameDump(
            path=str(folder_path),
            name=folder_name,
            location_type=LocationType.LOCAL,
        )

        # Check installation status
        self._check_installation_status(dump, folder_path)

        return dump

    def _check_installation_status(
        self, dump: GameDump, folder_path: Path
    ) -> None:
        """
        Check if dump_runner files are installed in a dump.

        Args:
            dump: GameDump to check (modified in place)
            folder_path: Path to the dump folder
        """
        try:
            elf_file = folder_path / "dump_runner.elf"
            js_file = folder_path / "homebrew.js"

            dump.has_elf = elf_file.exists()
            dump.has_js = js_file.exists()

            if dump.has_elf and dump.has_js:
                dump.installation_status = InstallationStatus.UNKNOWN
            elif dump.has_elf or dump.has_js:
                # Partial installation
                dump.installation_status = InstallationStatus.UNKNOWN
            else:
                dump.installation_status = InstallationStatus.NOT_INSTALLED

        except Exception as e:
            logger.warning(f"Error checking installation status for {dump.name}: {e}")
            dump.installation_status = InstallationStatus.UNKNOWN

    def refresh(self, dump: GameDump) -> GameDump:
        """
        Refresh status of a single dump.

        Args:
            dump: GameDump to refresh

        Returns:
            Updated GameDump with current status
        """
        folder_path = Path(dump.path)
        if folder_path.exists():
            self._check_installation_status(dump, folder_path)
        return dump
