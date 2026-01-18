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
from src.config.paths import SCAN_PATHS, get_location_type_from_path


class TestLocationTypeEnum:
    """Tests for LocationType enum."""

    def test_enum_values(self):
        """Test enum has expected values."""
        assert LocationType.INTERNAL.value == "internal"
        assert LocationType.USB.value == "usb"
        assert LocationType.EXTERNAL.value == "external"
        assert LocationType.UNKNOWN.value == "unknown"

    def test_granular_usb_enum_values(self):
        """Test USB device-specific enum values."""
        assert LocationType.USB0.value == "usb0"
        assert LocationType.USB1.value == "usb1"
        assert LocationType.USB2.value == "usb2"
        assert LocationType.USB3.value == "usb3"
        assert LocationType.USB4.value == "usb4"
        assert LocationType.USB5.value == "usb5"
        assert LocationType.USB6.value == "usb6"
        assert LocationType.USB7.value == "usb7"

    def test_granular_ext_enum_values(self):
        """Test external device-specific enum values."""
        assert LocationType.EXT0.value == "ext0"
        assert LocationType.EXT1.value == "ext1"


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
        assert dump.location_type == LocationType.USB0

    def test_from_path_usb_various_devices(self):
        """Test creating GameDump from various USB device paths."""
        dump1 = GameDump.from_path("/mnt/usb1/homebrew/Game1")
        dump5 = GameDump.from_path("/mnt/usb5/homebrew/Game5")
        dump7 = GameDump.from_path("/mnt/usb7/homebrew/Game7")

        assert dump1.location_type == LocationType.USB1
        assert dump5.location_type == LocationType.USB5
        assert dump7.location_type == LocationType.USB7

    def test_from_path_external(self):
        """Test creating GameDump from external storage path."""
        dump0 = GameDump.from_path("/mnt/ext0/homebrew/Game0")
        dump1 = GameDump.from_path("/mnt/ext1/homebrew/Game1")

        assert dump0.path == "/mnt/ext0/homebrew/Game0"
        assert dump0.name == "Game0"
        assert dump0.location_type == LocationType.EXT0

        assert dump1.path == "/mnt/ext1/homebrew/Game1"
        assert dump1.name == "Game1"
        assert dump1.location_type == LocationType.EXT1

    def test_from_path_external_fallback(self):
        """Test creating GameDump from unsupported external device falls back."""
        dump = GameDump.from_path("/mnt/ext5/homebrew/AnotherGame")

        assert dump.path == "/mnt/ext5/homebrew/AnotherGame"
        assert dump.name == "AnotherGame"
        assert dump.location_type == LocationType.EXTERNAL

    def test_from_path_etahen_internal(self):
        """Test creating GameDump from etaHEN internal path."""
        dump = GameDump.from_path("/data/etaHEN/games/GAME001")

        assert dump.path == "/data/etaHEN/games/GAME001"
        assert dump.name == "GAME001"
        assert dump.location_type == LocationType.INTERNAL

    def test_from_path_etahen_usb(self):
        """Test creating GameDump from etaHEN USB path."""
        dump = GameDump.from_path("/mnt/usb0/etaHEN/games/MyGame")

        assert dump.path == "/mnt/usb0/etaHEN/games/MyGame"
        assert dump.name == "MyGame"
        assert dump.location_type == LocationType.USB0

    def test_from_path_etahen_external(self):
        """Test creating GameDump from etaHEN external storage path."""
        dump = GameDump.from_path("/mnt/ext1/etaHEN/games/AnotherGame")

        assert dump.path == "/mnt/ext1/etaHEN/games/AnotherGame"
        assert dump.name == "AnotherGame"
        assert dump.location_type == LocationType.EXT1

    def test_from_path_with_trailing_slash(self):
        """Test path handling with trailing slash."""
        dump = GameDump.from_path("/data/homebrew/GAME001/")

        assert dump.name == "GAME001"
        assert dump.path == "/data/homebrew/GAME001/"

    def test_display_name(self):
        """Test display name includes location prefix."""
        internal = GameDump.from_path("/data/homebrew/Game1")
        usb0 = GameDump.from_path("/mnt/usb0/homebrew/Game2")
        usb3 = GameDump.from_path("/mnt/usb3/homebrew/Game3")
        ext0 = GameDump.from_path("/mnt/ext0/homebrew/Game4")
        ext1 = GameDump.from_path("/mnt/ext1/homebrew/Game5")

        assert internal.display_name == "[INT] Game1"
        assert usb0.display_name == "[USB0] Game2"
        assert usb3.display_name == "[USB3] Game3"
        assert ext0.display_name == "[EXT0] Game4"
        assert ext1.display_name == "[EXT1] Game5"

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

        # Mock pwd to return current directory
        mock_ftp.pwd.return_value = "/"

        # Mock cwd - only /data/homebrew/ and its subdirs exist
        def mock_cwd(path):
            if path in ["/", "/data/homebrew/", "/data/homebrew/Game1", "/data/homebrew/Game2"]:
                return  # Success
            else:
                raise error_perm("550 No such directory")

        mock_ftp.cwd.side_effect = mock_cwd

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

        # Mock pwd to return current directory
        mock_ftp.pwd.return_value = "/"

        # All paths raise permission error in CWD check (don't exist)
        def mock_cwd(path):
            if path == "/":
                return  # Root always works
            raise error_perm("550 No such directory")

        mock_ftp.cwd.side_effect = mock_cwd

        scanner = DumpScanner(mock_connection)
        dumps = scanner.scan()

        assert len(dumps) == 0

    def test_scan_checks_installation_status(self):
        """Test scan checks for dump_runner files."""
        mock_ftp = MagicMock()
        mock_connection = Mock(spec=FTPConnectionManager)
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # Mock pwd to return current directory
        mock_ftp.pwd.return_value = "/"

        # Mock cwd - only /data/homebrew/ exists
        def mock_cwd(path):
            if path == "/" or path == "/data/homebrew/" or path == "/data/homebrew/InstalledGame":
                return  # Success
            else:
                raise error_perm("550 No such directory")

        mock_ftp.cwd.side_effect = mock_cwd

        def mock_nlst(path):
            if path == "/data/homebrew/":
                return ["/data/homebrew/InstalledGame"]
            elif path == "/data/homebrew/InstalledGame":
                return ["dump_runner.elf", "homebrew.js", "other.txt"]
            else:
                raise error_perm("550 No such directory")

        mock_ftp.nlst.side_effect = mock_nlst

        # Mock dir for _list_files_in_dir (used by _check_installation_status)
        def mock_dir(callback):
            # Simulate LIST output for /data/homebrew/InstalledGame
            callback("-rw-r--r-- 1 root root 12345 Jan 01 00:00 dump_runner.elf")
            callback("-rw-r--r-- 1 root root 1234 Jan 01 00:00 homebrew.js")
            callback("-rw-r--r-- 1 root root 100 Jan 01 00:00 other.txt")

        mock_ftp.dir.side_effect = mock_dir

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
        usb0 = scanner.get_dumps_by_location(LocationType.USB0)

        assert len(internal) == 2
        assert len(usb0) == 1

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


class TestScanPaths:
    """Tests for SCAN_PATHS configuration."""

    def test_scan_paths_includes_homebrew_internal(self):
        """Test SCAN_PATHS includes internal homebrew path."""
        assert "/data/homebrew/" in SCAN_PATHS

    def test_scan_paths_includes_etahen_internal(self):
        """Test SCAN_PATHS includes internal etaHEN path."""
        assert "/data/etaHEN/games/" in SCAN_PATHS

    def test_scan_paths_includes_homebrew_usb(self):
        """Test SCAN_PATHS includes USB homebrew paths."""
        for i in range(8):
            assert f"/mnt/usb{i}/homebrew/" in SCAN_PATHS

    def test_scan_paths_includes_etahen_usb(self):
        """Test SCAN_PATHS includes USB etaHEN paths."""
        for i in range(7):
            assert f"/mnt/usb{i}/etaHEN/games/" in SCAN_PATHS

    def test_scan_paths_prioritizes_common_paths(self):
        """Test SCAN_PATHS has common paths first to minimize connection issues."""
        # usb0, ext0, ext1 should come before usb1-usb7
        usb0_idx = SCAN_PATHS.index("/mnt/usb0/homebrew/")
        ext0_idx = SCAN_PATHS.index("/mnt/ext0/homebrew/")
        ext1_idx = SCAN_PATHS.index("/mnt/ext1/homebrew/")
        usb1_idx = SCAN_PATHS.index("/mnt/usb1/homebrew/")

        assert usb0_idx < usb1_idx, "usb0 should be scanned before usb1"
        assert ext0_idx < usb1_idx, "ext0 should be scanned before usb1"
        assert ext1_idx < usb1_idx, "ext1 should be scanned before usb1"

    def test_scan_paths_includes_homebrew_external(self):
        """Test SCAN_PATHS includes external homebrew paths (ext0-ext1 only)."""
        for i in range(2):
            assert f"/mnt/ext{i}/homebrew/" in SCAN_PATHS
        # ext2-ext7 should NOT be in SCAN_PATHS (PS5 only supports ext0-ext1)
        for i in range(2, 8):
            assert f"/mnt/ext{i}/homebrew/" not in SCAN_PATHS

    def test_scan_paths_includes_etahen_external(self):
        """Test SCAN_PATHS includes external etaHEN paths."""
        for i in range(2):
            assert f"/mnt/ext{i}/etaHEN/games/" in SCAN_PATHS


class TestGetLocationTypeFromPath:
    """Tests for get_location_type_from_path function."""

    def test_homebrew_internal_path(self):
        """Test homebrew internal path returns internal."""
        assert get_location_type_from_path("/data/homebrew/Game1") == "internal"

    def test_etahen_internal_path(self):
        """Test etaHEN internal path returns internal."""
        assert get_location_type_from_path("/data/etaHEN/games/Game1") == "internal"

    def test_homebrew_usb_path_specific_device(self):
        """Test homebrew USB paths return specific device type."""
        assert get_location_type_from_path("/mnt/usb0/homebrew/Game1") == "usb0"
        assert get_location_type_from_path("/mnt/usb1/homebrew/Game1") == "usb1"
        assert get_location_type_from_path("/mnt/usb5/homebrew/Game1") == "usb5"
        assert get_location_type_from_path("/mnt/usb7/homebrew/Game1") == "usb7"

    def test_etahen_usb_path_specific_device(self):
        """Test etaHEN USB paths return specific device type."""
        assert get_location_type_from_path("/mnt/usb0/etaHEN/games/Game1") == "usb0"
        assert get_location_type_from_path("/mnt/usb3/etaHEN/games/Game1") == "usb3"

    def test_usb_fallback_for_invalid_device_number(self):
        """Test USB paths with device number > 7 fall back to 'usb'."""
        assert get_location_type_from_path("/mnt/usb8/homebrew/Game1") == "usb"
        assert get_location_type_from_path("/mnt/usb99/homebrew/Game1") == "usb"

    def test_homebrew_external_path_specific_device(self):
        """Test homebrew external paths return specific device type."""
        assert get_location_type_from_path("/mnt/ext0/homebrew/Game1") == "ext0"
        assert get_location_type_from_path("/mnt/ext1/homebrew/Game1") == "ext1"

    def test_etahen_external_path_specific_device(self):
        """Test etaHEN external paths return specific device type."""
        assert get_location_type_from_path("/mnt/ext0/etaHEN/games/Game1") == "ext0"
        assert get_location_type_from_path("/mnt/ext1/etaHEN/games/Game1") == "ext1"

    def test_external_fallback_for_invalid_device_number(self):
        """Test external paths with device number > 1 fall back to 'external'."""
        assert get_location_type_from_path("/mnt/ext2/homebrew/Game1") == "external"
        assert get_location_type_from_path("/mnt/ext5/homebrew/Game1") == "external"

    def test_unknown_path(self):
        """Test unknown path returns unknown."""
        assert get_location_type_from_path("/some/other/path") == "unknown"
