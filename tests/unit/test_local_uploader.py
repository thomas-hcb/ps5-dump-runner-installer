"""Unit tests for LocalUploader.

Tests local file copying to game dumps.
"""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from src.core.scanner_base import UploadResult
from src.ftp.scanner import GameDump, LocationType
from src.local.uploader import LocalUploader


class TestLocalUploaderInit:
    """Test LocalUploader initialization."""

    def test_initializes_correctly(self):
        """Should initialize with cancellation flag cleared."""
        uploader = LocalUploader()

        assert uploader._cancelled.is_set() is False
        assert uploader.is_cancelled is False


class TestCancellation:
    """Test cancellation functionality."""

    def test_cancel_sets_flag(self):
        """Should set cancellation flag when cancel() called."""
        uploader = LocalUploader()

        uploader.cancel()

        assert uploader.is_cancelled is True
        assert uploader._cancelled.is_set() is True

    def test_reset_cancel_clears_flag(self):
        """Should clear cancellation flag when reset_cancel() called."""
        uploader = LocalUploader()
        uploader.cancel()

        uploader.reset_cancel()

        assert uploader.is_cancelled is False
        assert uploader._cancelled.is_set() is False


class TestUploadToDump:
    """Test LocalUploader.upload_to_dump() method."""

    def test_successful_upload(self):
        """Should successfully copy both files to dump folder."""
        uploader = LocalUploader()
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2") as mock_copy:
                    result = uploader.upload_to_dump(dump, elf_path, js_path)

                    assert result.success is True
                    assert result.dump_path == dump.path
                    assert result.error_message is None
                    assert mock_copy.call_count == 2

    def test_accepts_string_paths(self):
        """Should accept string paths and convert to Path objects."""
        uploader = LocalUploader()
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2"):
                    result = uploader.upload_to_dump(
                        dump,
                        "C:\\Downloads\\dump_runner.elf",
                        "C:\\Downloads\\homebrew.js"
                    )

                    assert result.success is True

    def test_destination_not_exists(self):
        """Should fail if destination folder doesn't exist."""
        uploader = LocalUploader()
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        with patch("pathlib.Path.exists", return_value=False):
            result = uploader.upload_to_dump(dump, elf_path, js_path)

            assert result.success is False
            assert "does not exist" in result.error_message

    def test_destination_not_directory(self):
        """Should fail if destination is not a directory."""
        uploader = LocalUploader()
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=False):
                result = uploader.upload_to_dump(dump, elf_path, js_path)

                assert result.success is False
                assert "not a directory" in result.error_message

    def test_permission_error(self):
        """Should handle permission errors gracefully."""
        uploader = LocalUploader()
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2", side_effect=PermissionError("Access denied")):
                    result = uploader.upload_to_dump(dump, elf_path, js_path)

                    assert result.success is False
                    assert "Permission denied" in result.error_message

    def test_no_space_left_error(self):
        """Should handle disk full errors with specific message."""
        uploader = LocalUploader()
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2", side_effect=OSError("No space left on device")):
                    result = uploader.upload_to_dump(dump, elf_path, js_path)

                    assert result.success is False
                    assert "Not enough space" in result.error_message

    def test_read_only_filesystem_error(self):
        """Should handle read-only filesystem errors."""
        uploader = LocalUploader()
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2", side_effect=OSError("Read-only file system")):
                    result = uploader.upload_to_dump(dump, elf_path, js_path)

                    assert result.success is False
                    assert "read-only" in result.error_message

    def test_cancellation_during_upload(self):
        """Should stop upload and return cancelled status when cancelled."""
        uploader = LocalUploader()
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        # Cancel before first file copy
        uploader.cancel()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2") as mock_copy:
                    result = uploader.upload_to_dump(dump, elf_path, js_path)

                    assert result.success is False
                    assert "cancelled" in result.error_message.lower()
                    # Should still attempt first copy before checking cancellation
                    assert mock_copy.call_count <= 2

    def test_copies_to_correct_paths(self):
        """Should copy files to correct destination paths."""
        uploader = LocalUploader()
        dump = GameDump(
            path="E:\\homebrew\\CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL,
        )
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2") as mock_copy:
                    result = uploader.upload_to_dump(dump, elf_path, js_path)

                    # Check copy2 was called with correct paths
                    calls = mock_copy.call_args_list
                    assert len(calls) == 2

                    # First call should be elf file
                    assert calls[0][0][0] == elf_path
                    assert str(calls[0][0][1]).endswith("dump_runner.elf")

                    # Second call should be js file
                    assert calls[1][0][0] == js_path
                    assert str(calls[1][0][1]).endswith("homebrew.js")


class TestUploadBatch:
    """Test LocalUploader.upload_batch() method."""

    def test_uploads_to_multiple_dumps(self):
        """Should upload to multiple dumps successfully."""
        uploader = LocalUploader()
        dumps = [
            GameDump(
                path="E:\\homebrew\\CUSA12345",
                name="CUSA12345",
                location_type=LocationType.LOCAL,
            ),
            GameDump(
                path="E:\\homebrew\\CUSA67890",
                name="CUSA67890",
                location_type=LocationType.LOCAL,
            ),
        ]
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2"):
                    results = uploader.upload_batch(dumps, elf_path, js_path)

                    assert len(results) == 2
                    assert all(r.success for r in results)

    def test_accepts_string_paths(self):
        """Should accept string paths for batch upload."""
        uploader = LocalUploader()
        dumps = [
            GameDump(
                path="E:\\homebrew\\CUSA12345",
                name="CUSA12345",
                location_type=LocationType.LOCAL,
            ),
        ]

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2"):
                    results = uploader.upload_batch(
                        dumps,
                        "C:\\Downloads\\dump_runner.elf",
                        "C:\\Downloads\\homebrew.js"
                    )

                    assert len(results) == 1
                    assert results[0].success is True

    def test_continues_on_individual_failures(self):
        """Should continue with remaining dumps if one fails."""
        uploader = LocalUploader()
        dumps = [
            GameDump(
                path="E:\\homebrew\\CUSA12345",
                name="CUSA12345",
                location_type=LocationType.LOCAL,
            ),
            GameDump(
                path="E:\\homebrew\\CUSA67890",
                name="CUSA67890",
                location_type=LocationType.LOCAL,
            ),
        ]
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        call_count = [0]

        def copy_side_effect(src, dest):
            call_count[0] += 1
            # Fail on first dump only
            if "CUSA12345" in str(dest):
                raise PermissionError("Access denied")
            # Second dump succeeds
            return None

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_dir", return_value=True):
                with patch("shutil.copy2", side_effect=copy_side_effect):
                    results = uploader.upload_batch(dumps, elf_path, js_path)

                    assert len(results) == 2
                    assert results[0].success is False
                    assert "Permission denied" in results[0].error_message
                    assert results[1].success is True

    def test_resets_cancel_flag_before_batch(self):
        """Should reset cancellation flag at start of batch."""
        uploader = LocalUploader()
        dumps = [
            GameDump(
                path="E:\\homebrew\\CUSA12345",
                name="CUSA12345",
                location_type=LocationType.LOCAL,
            ),
        ]
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        # Cancel before batch
        uploader.cancel()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2"):
                    # reset_cancel should be called internally
                    results = uploader.upload_batch(dumps, elf_path, js_path)

                    # Should complete successfully after reset
                    assert results[0].success is True

    def test_calls_on_complete_callback(self):
        """Should call on_complete callback for each dump."""
        uploader = LocalUploader()
        dumps = [
            GameDump(
                path="E:\\homebrew\\CUSA12345",
                name="CUSA12345",
                location_type=LocationType.LOCAL,
            ),
            GameDump(
                path="E:\\homebrew\\CUSA67890",
                name="CUSA67890",
                location_type=LocationType.LOCAL,
            ),
        ]
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        callback_calls = []

        def on_complete(dump, result):
            callback_calls.append((dump, result))

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2"):
                    results = uploader.upload_batch(
                        dumps, elf_path, js_path, on_complete=on_complete
                    )

                    assert len(callback_calls) == 2
                    assert callback_calls[0][0] == dumps[0]
                    assert callback_calls[1][0] == dumps[1]

    def test_cancellation_during_batch(self):
        """Should stop batch and mark remaining dumps as cancelled."""
        uploader = LocalUploader()
        dumps = [
            GameDump(
                path="E:\\homebrew\\CUSA12345",
                name="CUSA12345",
                location_type=LocationType.LOCAL,
            ),
            GameDump(
                path="E:\\homebrew\\CUSA67890",
                name="CUSA67890",
                location_type=LocationType.LOCAL,
            ),
        ]
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        call_count = [0]

        def copy_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Cancel after first dump completes
            if call_count[0] == 2:
                uploader.cancel()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2", side_effect=copy_side_effect):
                    results = uploader.upload_batch(dumps, elf_path, js_path)

                    assert len(results) == 2
                    # Second dump should be cancelled
                    assert results[1].success is False
                    assert "cancelled" in results[1].error_message.lower()

    def test_returns_results_for_all_dumps(self):
        """Should return UploadResult for each dump in order."""
        uploader = LocalUploader()
        dumps = [
            GameDump(
                path="E:\\homebrew\\CUSA12345",
                name="CUSA12345",
                location_type=LocationType.LOCAL,
            ),
            GameDump(
                path="E:\\homebrew\\CUSA67890",
                name="CUSA67890",
                location_type=LocationType.LOCAL,
            ),
        ]
        elf_path = Path("C:\\Downloads\\dump_runner.elf")
        js_path = Path("C:\\Downloads\\homebrew.js")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("shutil.copy2"):
                    results = uploader.upload_batch(dumps, elf_path, js_path)

                    assert len(results) == len(dumps)
                    assert results[0].dump_path == dumps[0].path
                    assert results[1].dump_path == dumps[1].path
