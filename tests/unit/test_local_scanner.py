"""Unit tests for LocalScanner.

Tests local filesystem scanning for game dumps.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ftp.scanner import GameDump, InstallationStatus, LocationType
from src.local.scanner import LocalScanner, PREDEFINED_PATHS


class TestLocalScannerInit:
    """Test LocalScanner initialization."""

    def test_initializes_with_base_volume(self):
        """Should initialize with base volume path."""
        volume = Path("E:\\")
        scanner = LocalScanner(volume)

        assert scanner._base_volume == volume
        assert scanner._last_scan is None
        assert scanner._dumps == []

    def test_dumps_property_returns_copy(self):
        """Should return copy of dumps list to prevent external modification."""
        scanner = LocalScanner(Path("E:\\"))
        scanner._dumps = [MagicMock(spec=GameDump)]

        dumps1 = scanner.dumps
        dumps2 = scanner.dumps

        assert dumps1 == dumps2
        assert dumps1 is not dumps2  # Different list objects


class TestLocalScannerScan:
    """Test LocalScanner.scan() method."""

    def test_scans_predefined_paths(self):
        """Should scan all predefined paths on the volume."""
        volume = Path("E:\\")
        scanner = LocalScanner(volume)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("pathlib.Path.iterdir", return_value=[]):
                    result = scanner.scan()

                    assert scanner._last_scan is not None
                    assert isinstance(scanner._last_scan, datetime)

    def test_finds_valid_dump_folders(self):
        """Should find any folder with eboot.bin file."""
        volume = Path("E:\\")
        scanner = LocalScanner(volume)

        # Mock folder structure - any folder name is acceptable
        mock_dump = MagicMock(spec=Path)
        mock_dump.name = "Game 1"
        mock_dump.is_dir.return_value = True
        mock_dump.__truediv__ = lambda self, other: MagicMock(spec=Path, exists=lambda: True)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("pathlib.Path.iterdir", return_value=[mock_dump]):
                    result = scanner.scan()

                    assert len(result) > 0
                    assert all(isinstance(d, GameDump) for d in result)

    def test_skips_folders_without_eboot_bin(self):
        """Should skip folders without eboot.bin file."""
        volume = Path("E:\\")
        scanner = LocalScanner(volume)

        mock_dump = MagicMock(spec=Path)
        mock_dump.name = "Game 1"
        mock_dump.is_dir.return_value = True
        mock_dump.__truediv__ = lambda self, other: MagicMock(spec=Path, exists=lambda: False)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("pathlib.Path.iterdir", return_value=[mock_dump]):
                    result = scanner.scan()

                    assert len(result) == 0

    def test_accepts_any_folder_name_with_eboot_bin(self):
        """Should accept any folder name as long as eboot.bin exists."""
        volume = Path("E:\\")
        scanner = LocalScanner(volume)

        # Create folders with various names - all should be accepted if they have eboot.bin
        mock_folder1 = MagicMock(spec=Path)
        mock_folder1.name = "Game 1"
        mock_folder1.is_dir.return_value = True
        mock_folder1.__truediv__ = lambda self, other: MagicMock(spec=Path, exists=lambda: True)

        mock_folder2 = MagicMock(spec=Path)
        mock_folder2.name = "My Custom Game"
        mock_folder2.is_dir.return_value = True
        mock_folder2.__truediv__ = lambda self, other: MagicMock(spec=Path, exists=lambda: True)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("pathlib.Path.iterdir", return_value=[mock_folder1, mock_folder2]):
                    result = scanner.scan()

                    # Scanner scans 2 predefined paths, so 2 folders * 2 paths = 4 results
                    assert len(result) == 4
                    # Check that both folder names appear in results
                    names = [dump.name for dump in result]
                    assert names.count("Game 1") == 2
                    assert names.count("My Custom Game") == 2

    def test_handles_permission_errors(self):
        """Should handle permission errors gracefully."""
        volume = Path("E:\\")
        scanner = LocalScanner(volume)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("pathlib.Path.iterdir", side_effect=PermissionError("Access denied")):
                    result = scanner.scan()

                    # Should return empty list, not crash
                    assert result == []

    def test_handles_missing_paths(self):
        """Should handle non-existent predefined paths gracefully."""
        volume = Path("E:\\")
        scanner = LocalScanner(volume)

        with patch("pathlib.Path.exists", return_value=False):
            result = scanner.scan()

            assert result == []
            assert scanner._last_scan is not None

    def test_sets_location_type_to_local(self):
        """Should set location_type to LOCAL for all found dumps."""
        volume = Path("E:\\")
        scanner = LocalScanner(volume)

        mock_dump = MagicMock(spec=Path)
        mock_dump.name = "CUSA12345"
        mock_dump.is_dir.return_value = True
        mock_dump.__str__.return_value = "E:\\homebrew\\CUSA12345"
        mock_sfo = MagicMock(spec=Path)
        mock_sfo.exists.return_value = True
        mock_dump.__truediv__.return_value = mock_sfo

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("pathlib.Path.iterdir", return_value=[mock_dump]):
                    result = scanner.scan()

                    assert len(result) > 0
                    for dump in result:
                        assert dump.location_type == LocationType.LOCAL


class TestCheckDumpFolder:
    """Test LocalScanner._check_dump_folder() method."""

    def test_accepts_any_folder_name_with_eboot_bin(self):
        """Should accept any folder name as long as eboot.bin exists."""
        scanner = LocalScanner(Path("E:\\"))

        valid_folders = [
            Path("E:\\homebrew\\CUSA12345"),
            Path("E:\\homebrew\\Game 1"),
            Path("E:\\homebrew\\My Custom Game"),
            Path("E:\\homebrew\\Spider-Man"),
        ]

        for folder in valid_folders:
            with patch("pathlib.Path.exists", return_value=True):
                result = scanner._check_dump_folder(folder)
                assert result is not None
                assert result.name == folder.name

    def test_rejects_folders_without_eboot_bin(self):
        """Should reject folders that don't have eboot.bin file."""
        scanner = LocalScanner(Path("E:\\"))

        test_folders = [
            Path("E:\\homebrew\\CUSA12345"),
            Path("E:\\homebrew\\Game 1"),
            Path("E:\\homebrew\\Random Folder"),
        ]

        for folder in test_folders:
            with patch("pathlib.Path.exists", return_value=False):
                result = scanner._check_dump_folder(folder)
                assert result is None

    def test_requires_eboot_bin(self):
        """Should require eboot.bin file to be present."""
        scanner = LocalScanner(Path("E:\\"))
        folder = Path("E:\\homebrew\\CUSA12345")

        with patch("pathlib.Path.exists", return_value=False):
            result = scanner._check_dump_folder(folder)
            assert result is None


class TestCheckInstallationStatus:
    """Test LocalScanner._check_installation_status() method."""

    def test_detects_full_installation(self):
        """Should detect when both dump_runner.elf and homebrew.js exist."""
        scanner = LocalScanner(Path("E:\\"))
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )

        with patch("pathlib.Path.exists", return_value=True):
            scanner._check_installation_status(dump, Path(dump.path))

            assert dump.has_elf is True
            assert dump.has_js is True
            assert dump.installation_status == InstallationStatus.UNKNOWN

    def test_detects_partial_installation(self):
        """Should detect when only one file is present."""
        scanner = LocalScanner(Path("E:\\"))
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )

        # Mock only elf file exists
        def exists_side_effect(path_self):
            return "dump_runner.elf" in str(path_self)

        with patch.object(Path, "exists", exists_side_effect):
            scanner._check_installation_status(dump, Path(dump.path))

            assert dump.has_elf is True
            assert dump.has_js is False
            assert dump.installation_status == InstallationStatus.UNKNOWN

    def test_detects_not_installed(self):
        """Should detect when neither file is present."""
        scanner = LocalScanner(Path("E:\\"))
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )

        with patch("pathlib.Path.exists", return_value=False):
            scanner._check_installation_status(dump, Path(dump.path))

            assert dump.has_elf is False
            assert dump.has_js is False
            assert dump.installation_status == InstallationStatus.NOT_INSTALLED

    def test_handles_errors_gracefully(self):
        """Should handle file system errors without crashing."""
        scanner = LocalScanner(Path("E:\\"))
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )

        with patch("pathlib.Path.exists", side_effect=Exception("Disk error")):
            scanner._check_installation_status(dump, Path(dump.path))

            assert dump.installation_status == InstallationStatus.UNKNOWN


class TestRefresh:
    """Test LocalScanner.refresh() method."""

    def test_refreshes_single_dump_status(self):
        """Should refresh installation status of a single dump."""
        scanner = LocalScanner(Path("E:\\"))
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )

        with patch("pathlib.Path.exists", return_value=True):
            refreshed = scanner.refresh(dump)

            assert refreshed.has_elf is True
            assert refreshed.has_js is True

    def test_handles_missing_dump_folder(self):
        """Should handle case when dump folder no longer exists."""
        scanner = LocalScanner(Path("E:\\"))
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )

        with patch("pathlib.Path.exists", return_value=False):
            refreshed = scanner.refresh(dump)

            # Should return dump unchanged (status will be stale)
            assert refreshed == dump
