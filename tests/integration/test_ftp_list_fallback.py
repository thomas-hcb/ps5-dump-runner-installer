"""Integration tests for FTP NLST/LIST fallback behavior.

Tests the scanner's ability to fall back to LIST command when NLST is not supported.
"""

import pytest
from ftplib import error_perm
from unittest.mock import Mock, MagicMock, patch, call

from src.ftp.scanner import DumpScanner


class TestNLSTListFallback:
    """Test NLST to LIST fallback integration."""

    def test_uses_nlst_when_available(self):
        """Should use NLST command when it succeeds."""
        # Setup
        mock_connection = Mock()
        mock_ftp = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # NLST succeeds - should not fall back to LIST
        mock_ftp.nlst.return_value = ["/data/homebrew/CUSA12345"]
        mock_ftp.voidcmd.return_value = None

        scanner = DumpScanner(mock_connection)

        # Execute
        result = scanner._nlst_with_retry(mock_ftp, "/data/homebrew")

        # Verify NLST was called
        mock_ftp.nlst.assert_called_once_with("/data/homebrew")
        # Verify LIST was NOT called (no fallback)
        mock_ftp.retrlines.assert_not_called()
        assert result == ["/data/homebrew/CUSA12345"]

    def test_falls_back_to_list_on_nlst_error_perm(self):
        """Should fall back to LIST when NLST raises error_perm."""
        # Setup
        mock_connection = Mock()
        mock_ftp = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # NLST fails with error_perm (command not supported)
        mock_ftp.nlst.side_effect = error_perm("500 NLST not supported")
        mock_ftp.pwd.return_value = "/"

        # LIST succeeds with Unix-style output via ftp.dir()
        def dir_side_effect(callback):
            lines = [
                "drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345",
                "drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA67890"
            ]
            for line in lines:
                callback(line)

        mock_ftp.dir.side_effect = dir_side_effect

        scanner = DumpScanner(mock_connection)

        # Execute
        result = scanner._nlst_with_retry(mock_ftp, "/data/homebrew")

        # Verify NLST was attempted
        mock_ftp.nlst.assert_called_once()
        # Verify LIST fallback was used (via cwd + dir)
        mock_ftp.cwd.assert_called()
        mock_ftp.dir.assert_called_once()

        # Verify result contains parsed directories as full paths
        assert len(result) == 2
        assert "/data/homebrew/CUSA12345" in result
        assert "/data/homebrew/CUSA67890" in result

    def test_list_fallback_parses_output_correctly(self):
        """Should correctly parse LIST output in fallback."""
        # Setup
        mock_connection = Mock()
        mock_ftp = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # NLST fails
        mock_ftp.nlst.side_effect = error_perm("500 NLST not supported")
        mock_ftp.pwd.return_value = "/"

        # LIST returns mixed content (files and directories) via ftp.dir()
        def dir_side_effect(callback):
            lines = [
                "drwxr-xr-x  2 root root 4096 Jan  1 12:00 GameDir1",
                "-rw-r--r--  1 root root 1024 Jan  1 12:00 file.txt",
                "drwxr-xr-x  2 root root 4096 Jan  1 12:00 GameDir2",
                "-rw-r--r--  1 root root 2048 Jan  1 12:00 another.bin"
            ]
            for line in lines:
                callback(line)

        mock_ftp.dir.side_effect = dir_side_effect

        scanner = DumpScanner(mock_connection)

        # Execute
        result = scanner._nlst_with_retry(mock_ftp, "/data/homebrew")

        # Verify only directories are returned, not files
        assert len(result) == 2
        assert "/data/homebrew/GameDir1" in result
        assert "/data/homebrew/GameDir2" in result

    def test_list_fallback_handles_empty_directory(self):
        """Should handle empty directory in LIST fallback."""
        # Setup
        mock_connection = Mock()
        mock_ftp = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # NLST fails
        mock_ftp.nlst.side_effect = error_perm("500 NLST not supported")
        mock_ftp.pwd.return_value = "/"

        # LIST returns empty output via ftp.dir()
        mock_ftp.dir.side_effect = lambda callback: None

        scanner = DumpScanner(mock_connection)

        # Execute
        result = scanner._nlst_with_retry(mock_ftp, "/data/homebrew")

        # Verify empty list returned
        assert result == []

    def test_list_fallback_handles_names_with_spaces(self):
        """Should handle directory names containing spaces."""
        # Setup
        mock_connection = Mock()
        mock_ftp = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # NLST fails
        mock_ftp.nlst.side_effect = error_perm("500 NLST not supported")
        mock_ftp.pwd.return_value = "/"

        # LIST returns directories with spaces in names via ftp.dir()
        def dir_side_effect(callback):
            lines = [
                "drwxr-xr-x  2 root root 4096 Jan  1 12:00 Game Folder One",
                "drwxr-xr-x  2 root root 4096 Jan  1 12:00 Another Game Folder"
            ]
            for line in lines:
                callback(line)

        mock_ftp.dir.side_effect = dir_side_effect

        scanner = DumpScanner(mock_connection)

        # Execute
        result = scanner._nlst_with_retry(mock_ftp, "/mnt/usb0")

        # Verify spaces preserved in directory names
        assert len(result) == 2
        assert "/mnt/usb0/Game Folder One" in result
        assert "/mnt/usb0/Another Game Folder" in result

    def test_raises_error_when_both_nlst_and_list_fail(self):
        """Should raise error when both NLST and LIST fail."""
        # Setup
        mock_connection = Mock()
        mock_ftp = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # NLST fails with error_perm
        mock_ftp.nlst.side_effect = error_perm("500 NLST not supported")
        mock_ftp.pwd.return_value = "/"

        # CWD also fails (path doesn't exist)
        mock_ftp.cwd.side_effect = error_perm("550 Permission denied")

        scanner = DumpScanner(mock_connection)

        # Execute and verify error raised
        with pytest.raises(error_perm):
            scanner._nlst_with_retry(mock_ftp, "/data/homebrew")

    def test_list_fallback_ignores_special_directories(self):
        """Should ignore . and .. special directories in LIST output."""
        # Setup
        mock_connection = Mock()
        mock_ftp = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # NLST fails
        mock_ftp.nlst.side_effect = error_perm("500 NLST not supported")
        mock_ftp.pwd.return_value = "/"

        # LIST returns . and .. along with real directories via ftp.dir()
        def dir_side_effect(callback):
            lines = [
                "drwxr-xr-x  2 root root 4096 Jan  1 12:00 .",
                "drwxr-xr-x  2 root root 4096 Jan  1 12:00 ..",
                "drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345"
            ]
            for line in lines:
                callback(line)

        mock_ftp.dir.side_effect = dir_side_effect

        scanner = DumpScanner(mock_connection)

        # Execute
        result = scanner._nlst_with_retry(mock_ftp, "/data/homebrew")

        # Verify only real directory returned, not . or ..
        assert len(result) == 1
        assert "/data/homebrew/CUSA12345" in result

    def test_nlst_retry_still_works_with_fallback(self):
        """Should still retry NLST before falling back to LIST."""
        # Setup
        mock_connection = Mock()
        mock_ftp = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # NLST fails with transient error first, then error_perm
        mock_ftp.nlst.side_effect = [
            Exception("Transient error"),  # First attempt fails
            error_perm("500 NLST not supported")  # Retry fails with error_perm
        ]

        # LIST succeeds via ftp.dir()
        def dir_side_effect(callback):
            callback("drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345")

        mock_ftp.dir.side_effect = dir_side_effect
        mock_ftp.pwd.return_value = "/"
        mock_ftp.voidcmd.return_value = None

        scanner = DumpScanner(mock_connection)

        # Execute
        result = scanner._nlst_with_retry(mock_ftp, "/data/homebrew", retries=1)

        # Verify NLST was attempted twice before fallback
        assert mock_ftp.nlst.call_count == 2
        # Verify LIST fallback was eventually used via cwd + dir
        mock_ftp.dir.assert_called_once()
        assert len(result) == 1


class TestFullScanWithListFallback:
    """Test full scan workflow with LIST fallback."""

    @patch('src.ftp.scanner.SCAN_PATHS', ["/data/homebrew"])
    def test_scan_completes_with_list_fallback(self):
        """Should complete full scan using LIST fallback when NLST not supported."""
        # Setup
        mock_connection = Mock()
        mock_ftp = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # NOOP succeeds (connection alive)
        mock_ftp.voidcmd.return_value = None
        mock_ftp.pwd.return_value = "/"

        # NLST fails with error_perm for base path scan
        nlst_call_count = [0]

        def nlst_side_effect(path):
            nlst_call_count[0] += 1
            if nlst_call_count[0] == 1:
                # First call: scanning base path - use fallback
                raise error_perm("500 NLST not supported")
            else:
                # Subsequent calls: checking if entries are directories
                raise error_perm("550 Not a directory")

        mock_ftp.nlst.side_effect = nlst_side_effect

        # Track which directory we're listing
        current_path = ["/data/homebrew"]

        def cwd_side_effect(path):
            if path == "/":
                current_path[0] = "/"
            elif path.startswith("/"):
                current_path[0] = path
            else:
                current_path[0] = f"{current_path[0].rstrip('/')}/{path}"

        mock_ftp.cwd.side_effect = cwd_side_effect

        # LIST fallback returns directories via ftp.dir()
        def dir_side_effect(callback):
            if "homebrew" in current_path[0]:
                lines = [
                    "drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345",
                    "drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA67890"
                ]
                for line in lines:
                    callback(line)

        mock_ftp.dir.side_effect = dir_side_effect

        scanner = DumpScanner(mock_connection)

        # Execute
        result = scanner.scan()

        # Verify scan completed and found dumps
        assert len(result) == 2
        dump_names = [d.name for d in result]
        assert "CUSA12345" in dump_names
        assert "CUSA67890" in dump_names

    @patch('src.ftp.scanner.SCAN_PATHS', ["/data/homebrew", "/mnt/usb0/homebrew"])
    def test_scan_uses_list_fallback_for_multiple_paths(self):
        """Should use LIST fallback consistently across multiple scan paths."""
        # Setup
        mock_connection = Mock()
        mock_ftp = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # NOOP succeeds
        mock_ftp.voidcmd.return_value = None
        mock_ftp.pwd.return_value = "/"

        # NLST always fails
        mock_ftp.nlst.side_effect = error_perm("500 NLST not supported")

        # Track which directory we're in
        current_path = ["/"]

        def cwd_side_effect(path):
            if path == "/":
                current_path[0] = "/"
            elif path.startswith("/"):
                current_path[0] = path
            else:
                current_path[0] = f"{current_path[0].rstrip('/')}/{path}"

        mock_ftp.cwd.side_effect = cwd_side_effect

        # LIST returns different directories for different paths via ftp.dir()
        def dir_side_effect(callback):
            if "/data/homebrew" in current_path[0]:
                callback("drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345")
            elif "/mnt/usb0/homebrew" in current_path[0]:
                callback("drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA67890")

        mock_ftp.dir.side_effect = dir_side_effect

        scanner = DumpScanner(mock_connection)

        # Execute
        result = scanner.scan()

        # Verify dumps found from both paths using LIST fallback
        assert len(result) == 2
        paths = [d.path for d in result]
        assert "/data/homebrew/CUSA12345" in paths
        assert "/mnt/usb0/homebrew/CUSA67890" in paths


class TestSpecialCharacterPaths:
    """Test handling of paths with special characters like brackets."""

    def test_list_fallback_handles_brackets_in_names(self):
        """Should handle directory names containing brackets via incremental CWD."""
        # Setup
        mock_connection = Mock()
        mock_ftp = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = mock_ftp

        # NLST fails
        mock_ftp.nlst.side_effect = error_perm("500 NLST not supported")
        mock_ftp.pwd.return_value = "/"

        # Track navigation path
        navigated_parts = []

        def cwd_side_effect(path):
            navigated_parts.append(path)

        mock_ftp.cwd.side_effect = cwd_side_effect

        # LIST returns directory with brackets in name via ftp.dir()
        def dir_side_effect(callback):
            lines = [
                "drwxr-xr-x  2 root root 4096 Jan  1 12:00 Remnant 2 [ PPSA06693 ][ 1.37 ] [ 7.XX ]"
            ]
            for line in lines:
                callback(line)

        mock_ftp.dir.side_effect = dir_side_effect

        scanner = DumpScanner(mock_connection)

        # Execute
        result = scanner._nlst_with_retry(mock_ftp, "/mnt/ext1/homebrew")

        # Verify directory with brackets was found
        assert len(result) == 1
        assert "/mnt/ext1/homebrew/Remnant 2 [ PPSA06693 ][ 1.37 ] [ 7.XX ]" in result

