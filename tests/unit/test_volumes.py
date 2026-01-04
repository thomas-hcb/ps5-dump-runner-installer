"""Unit tests for volume detection module.

Tests platform-specific volume detection for Windows, macOS, and Linux.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.local.volumes import (
    get_available_volumes,
    _get_windows_drives,
    _get_macos_volumes,
    _get_linux_mounts,
)


class TestGetAvailableVolumes:
    """Test get_available_volumes() dispatches to correct platform function."""

    @patch("src.local.volumes.sys.platform", "win32")
    @patch("src.local.volumes._get_windows_drives")
    def test_windows_platform(self, mock_windows):
        """Should call Windows implementation on win32 platform."""
        mock_windows.return_value = [Path("C:\\"), Path("D:\\")]

        result = get_available_volumes()

        mock_windows.assert_called_once()
        assert result == [Path("C:\\"), Path("D:\\")]

    @patch("src.local.volumes.sys.platform", "darwin")
    @patch("src.local.volumes._get_macos_volumes")
    def test_macos_platform(self, mock_macos):
        """Should call macOS implementation on darwin platform."""
        mock_macos.return_value = [Path("/Volumes/Macintosh HD"), Path("/Volumes/USB")]

        result = get_available_volumes()

        mock_macos.assert_called_once()
        assert result == [Path("/Volumes/Macintosh HD"), Path("/Volumes/USB")]

    @patch("src.local.volumes.sys.platform", "linux")
    @patch("src.local.volumes._get_linux_mounts")
    def test_linux_platform(self, mock_linux):
        """Should call Linux implementation on linux platform."""
        mock_linux.return_value = [Path("/mnt/usb0"), Path("/media/user/USB")]

        result = get_available_volumes()

        mock_linux.assert_called_once()
        assert result == [Path("/mnt/usb0"), Path("/media/user/USB")]


class TestWindowsDrives:
    """Test _get_windows_drives() implementation."""

    def test_finds_existing_drives(self):
        """Should return list of existing drive letters."""
        # Mock exists as an instance method that receives self
        def mock_exists(self):
            return str(self) in ["C:\\", "D:\\"]

        with patch.object(Path, "exists", mock_exists):
            result = _get_windows_drives()

            # Should find C and D drives
            assert Path("C:\\") in result
            assert Path("D:\\") in result
            assert len(result) == 2

    def test_returns_empty_when_no_drives(self):
        """Should return empty list when no drives exist."""
        with patch("pathlib.Path.exists", return_value=False):
            result = _get_windows_drives()
            assert result == []

    def test_returns_path_objects(self):
        """Should return Path objects, not strings."""
        def mock_exists(self):
            return str(self) == "C:\\"

        with patch.object(Path, "exists", mock_exists):
            result = _get_windows_drives()

            assert len(result) == 1
            assert isinstance(result[0], Path)
            assert str(result[0]) == "C:\\"


class TestMacOSVolumes:
    """Test _get_macos_volumes() implementation."""

    def test_finds_volumes_directory(self):
        """Should scan /Volumes directory for mounted volumes."""
        mock_volumes = [
            MagicMock(spec=Path, is_dir=lambda: True, __str__=lambda self: "/Volumes/Macintosh HD"),
            MagicMock(spec=Path, is_dir=lambda: True, __str__=lambda self: "/Volumes/USB"),
            MagicMock(spec=Path, is_dir=lambda: False, __str__=lambda self: "/Volumes/file.txt"),
        ]

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.iterdir", return_value=mock_volumes):
                result = _get_macos_volumes()

                # Should only include directories
                assert len(result) == 2

    def test_returns_empty_when_volumes_not_exist(self):
        """Should return empty list when /Volumes doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            result = _get_macos_volumes()
            assert result == []

    def test_filters_non_directories(self):
        """Should only return directories, not files."""
        mock_volumes = [
            MagicMock(spec=Path, is_dir=lambda: False),
        ]

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.iterdir", return_value=mock_volumes):
                result = _get_macos_volumes()
                assert result == []


class TestLinuxMounts:
    """Test _get_linux_mounts() implementation."""

    def test_scans_mnt_directory(self):
        """Should scan /mnt directory for mount points."""
        # Create mock mounts with proper is_dir() method
        mock_mount1 = MagicMock(spec=Path)
        mock_mount1.is_dir.return_value = True
        mock_mount2 = MagicMock(spec=Path)
        mock_mount2.is_dir.return_value = True
        mock_mounts = [mock_mount1, mock_mount2]

        def mock_exists(self):
            # On Windows, Path converts /mnt to \mnt
            return str(self) in ["/mnt", "\\mnt"]

        def mock_iterdir(self):
            # On Windows, Path converts /mnt to \mnt
            if str(self) in ["/mnt", "\\mnt"]:
                return mock_mounts
            return []

        with patch.object(Path, "exists", mock_exists):
            with patch.object(Path, "iterdir", mock_iterdir):
                with patch("os.getlogin", return_value="testuser"):
                    result = _get_linux_mounts()

                    assert len(result) >= 2

    def test_scans_media_user_directory(self):
        """Should scan /media/$USER directory for mount points."""
        # /mnt doesn't exist, but /media/testuser does
        def mock_exists(self):
            # On Windows, Path converts /media/testuser to \media\testuser
            return str(self) in ["/media/testuser", "\\media\\testuser"]

        mock_media_mount = MagicMock(spec=Path)
        mock_media_mount.is_dir.return_value = True
        mock_media_mounts = [mock_media_mount]

        def mock_iterdir(self):
            # On Windows, Path converts /media/testuser to \media\testuser
            if str(self) in ["/media/testuser", "\\media\\testuser"]:
                return mock_media_mounts
            return []

        with patch.object(Path, "exists", mock_exists):
            with patch.object(Path, "iterdir", mock_iterdir):
                with patch("os.getlogin", return_value="testuser"):
                    result = _get_linux_mounts()

                    assert len(result) == 1

    def test_handles_getlogin_failure(self):
        """Should handle gracefully when os.getlogin() fails."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch("os.getlogin", side_effect=Exception("No login")):
                result = _get_linux_mounts()

                # Should return empty list, not crash
                assert result == []

    def test_returns_empty_when_no_mounts(self):
        """Should return empty list when no mount directories exist."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch("os.getlogin", return_value="testuser"):
                result = _get_linux_mounts()
                assert result == []

    def test_filters_non_directories(self):
        """Should only return directories from mount points."""
        # One is a file, one is a directory
        mock_file = MagicMock(spec=Path)
        mock_file.is_dir.return_value = False
        mock_dir = MagicMock(spec=Path)
        mock_dir.is_dir.return_value = True
        mock_mounts = [mock_file, mock_dir]

        def mock_exists(self):
            # On Windows, Path converts /mnt to \mnt
            return str(self) in ["/mnt", "\\mnt"]

        def mock_iterdir(self):
            # On Windows, Path converts /mnt to \mnt
            if str(self) in ["/mnt", "\\mnt"]:
                return mock_mounts
            return []

        with patch.object(Path, "exists", mock_exists):
            with patch.object(Path, "iterdir", mock_iterdir):
                with patch("os.getlogin", return_value="testuser"):
                    result = _get_linux_mounts()

                    # Should only include the directory
                    assert len(result) == 1
