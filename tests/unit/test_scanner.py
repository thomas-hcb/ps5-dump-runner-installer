"""Unit tests for DumpScanner.

Tests game dump discovery and status tracking.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from ftplib import error_perm

from src.ftp.scanner import (
    LocationType,
    InstallationStatus,
    GameDump,
    DumpScanner,
)
from src.ftp.connection import FTPConnectionManager, ConnectionState
from src.ftp.exceptions import FTPNotConnectedError


class TestLocationTypeEnum:
    """Tests for LocationType enum."""

    def test_enum_values(self):
        """Test enum has expected values."""
        assert LocationType.INTERNAL.value == "internal"
        assert LocationType.USB.value == "usb"
        assert LocationType.EXTERNAL.value == "external"
        assert LocationType.UNKNOWN.value == "unknown"


class TestInstallationStatusEnum:
    """Tests for InstallationStatus enum."""

    def test_enum_values(self):
        """Test enum has expected values."""
        assert InstallationStatus.NOT_INSTALLED.value == "not_installed"
        assert InstallationStatus.OFFICIAL.value == "official"
        assert InstallationStatus.EXPERIMENTAL.value == "experimental"
        assert InstallationStatus.UNKNOWN.value == "unknown"


class TestGameDump:
    """Tests for GameDump dataclass."""

    def test_from_path_internal(self):
        """Test creating GameDump from internal path."""
        dump = GameDump.from_path("/data/homebrew/GAME001")

        assert dump.path == "/data/homebrew/GAME001"
        assert dump.name == "GAME001"
        assert dump.location_type == LocationType.INTERNAL
        assert dump.installation_status == InstallationStatus.NOT_INSTALLED
        assert dump.is_experimental is False

    def test_from_path_usb(self):
        """Test creating GameDump from USB path."""
        dump = GameDump.from_path("/mnt/usb0/homebrew/MyGame")

        assert dump.path == "/mnt/usb0/homebrew/MyGame"
        assert dump.name == "MyGame"
        assert dump.location_type == LocationType.USB

    def test_from_path_external(self):
        """Test creating GameDump from external storage path."""
        dump = GameDump.from_path("/mnt/ext2/homebrew/AnotherGame")

        assert dump.path == "/mnt/ext2/homebrew/AnotherGame"
        assert dump.name == "AnotherGame"
        assert dump.location_type == LocationType.EXTERNAL

    def test_from_path_with_trailing_slash(self):
        """Test path handling with trailing slash."""
        dump = GameDump.from_path("/data/homebrew/GAME001/")

        assert dump.name == "GAME001"
        assert dump.path == "/data/homebrew/GAME001/"

    def test_display_name(self):
        """Test display name includes location prefix."""
        internal = GameDump.from_path("/data/homebrew/Game1")
        usb = GameDump.from_path("/mnt/usb0/homebrew/Game2")
        external = GameDump.from_path("/mnt/ext0/homebrew/Game3")

        assert internal.display_name == "[INT] Game1"
        assert usb.display_name == "[USB] Game2"
        assert external.display_name == "[EXT] Game3"

    def test_is_installed_property(self):
        """Test is_installed property."""
        not_installed = GameDump(
            path="/data/homebrew/Game1",
            name="Game1",
            location_type=LocationType.INTERNAL,
            installation_status=InstallationStatus.NOT_INSTALLED
        )
        installed = GameDump(
            path="/data/homebrew/Game2",
            name="Game2",
            location_type=LocationType.INTERNAL,
            installation_status=InstallationStatus.OFFICIAL
        )

        assert not_installed.is_installed is False
        assert installed.is_installed is True


class TestDumpScanner:
    """Tests for DumpScanner class."""

    def test_init(self):
        """Test scanner initialization."""
        mock_connection = Mock(spec=FTPConnectionManager)
        scanner = DumpScanner(mock_connection)

        assert scanner.last_scan is None
        assert scanner.dumps == []

    def test_scan_not_connected_raises_error(self):
        """Test scan raises error when not connected."""
        mock_connection = Mock(spec=FTPConnectionManager)
        mock_connection.is_connected = False

        scanner = DumpScanner(mock_connection)

        with pytest.raises(FTPNotConnectedError):
            scanner.scan()

    def test_scan_finds_dumps(self):
        """Test scan discovers game dumps."""
        mock_ftp = MagicMock()
        mock_connection = Mock(spec=FTPConnectionManager)
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # Mock nlst to return different results for different paths
        def mock_nlst(path):
            if path == "/data/homebrew/":
                return ["/data/homebrew/Game1", "/data/homebrew/Game2"]
            elif path in ["/data/homebrew/Game1", "/data/homebrew/Game2"]:
                return []  # Empty directories (valid game dumps)
            else:
                raise error_perm("550 No such directory")

        mock_ftp.nlst.side_effect = mock_nlst

        scanner = DumpScanner(mock_connection)
        dumps = scanner.scan()

        assert len(dumps) == 2
        assert dumps[0].name == "Game1"
        assert dumps[1].name == "Game2"
        assert scanner.last_scan is not None

    def test_scan_handles_missing_paths(self):
        """Test scan handles paths that don't exist."""
        mock_ftp = MagicMock()
        mock_connection = Mock(spec=FTPConnectionManager)
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # All paths raise permission error (don't exist)
        mock_ftp.nlst.side_effect = error_perm("550 No such directory")

        scanner = DumpScanner(mock_connection)
        dumps = scanner.scan()

        assert len(dumps) == 0

    def test_scan_checks_installation_status(self):
        """Test scan checks for dump_runner files."""
        mock_ftp = MagicMock()
        mock_connection = Mock(spec=FTPConnectionManager)
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        def mock_nlst(path):
            if path == "/data/homebrew/":
                return ["/data/homebrew/InstalledGame"]
            elif path == "/data/homebrew/InstalledGame":
                return ["dump_runner.elf", "homebrew.js", "other.txt"]
            else:
                raise error_perm("550 No such directory")

        mock_ftp.nlst.side_effect = mock_nlst

        scanner = DumpScanner(mock_connection)
        dumps = scanner.scan()

        assert len(dumps) == 1
        assert dumps[0].has_elf is True
        assert dumps[0].has_js is True
        assert dumps[0].installation_status == InstallationStatus.UNKNOWN

    def test_get_dump_by_path(self):
        """Test finding dump by path."""
        mock_connection = Mock(spec=FTPConnectionManager)
        mock_connection.is_connected = True

        scanner = DumpScanner(mock_connection)
        scanner._dumps = [
            GameDump.from_path("/data/homebrew/Game1"),
            GameDump.from_path("/data/homebrew/Game2"),
        ]

        found = scanner.get_dump_by_path("/data/homebrew/Game1")
        not_found = scanner.get_dump_by_path("/data/homebrew/Game99")

        assert found is not None
        assert found.name == "Game1"
        assert not_found is None

    def test_get_dumps_by_location(self):
        """Test filtering dumps by location type."""
        mock_connection = Mock(spec=FTPConnectionManager)
        scanner = DumpScanner(mock_connection)
        scanner._dumps = [
            GameDump.from_path("/data/homebrew/Game1"),
            GameDump.from_path("/mnt/usb0/homebrew/Game2"),
            GameDump.from_path("/data/homebrew/Game3"),
        ]

        internal = scanner.get_dumps_by_location(LocationType.INTERNAL)
        usb = scanner.get_dumps_by_location(LocationType.USB)

        assert len(internal) == 2
        assert len(usb) == 1

    def test_get_installed_dumps(self):
        """Test getting installed dumps."""
        mock_connection = Mock(spec=FTPConnectionManager)
        scanner = DumpScanner(mock_connection)

        installed = GameDump(
            path="/data/homebrew/Installed",
            name="Installed",
            location_type=LocationType.INTERNAL,
            installation_status=InstallationStatus.OFFICIAL
        )
        not_installed = GameDump(
            path="/data/homebrew/NotInstalled",
            name="NotInstalled",
            location_type=LocationType.INTERNAL,
            installation_status=InstallationStatus.NOT_INSTALLED
        )
        scanner._dumps = [installed, not_installed]

        result = scanner.get_installed_dumps()

        assert len(result) == 1
        assert result[0].name == "Installed"

    def test_refresh_not_connected_raises_error(self):
        """Test refresh raises error when not connected."""
        mock_connection = Mock(spec=FTPConnectionManager)
        mock_connection.is_connected = False

        scanner = DumpScanner(mock_connection)
        dump = GameDump.from_path("/data/homebrew/Game1")

        with pytest.raises(FTPNotConnectedError):
            scanner.refresh(dump)
