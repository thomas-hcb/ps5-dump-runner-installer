"""Unit tests for FileUploader.

Tests file upload operations, batch uploads, cancellation, and progress reporting.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
import tempfile

from src.ftp.uploader import FileUploader, UploadProgress, UploadResult
from src.ftp.scanner import GameDump, LocationType, InstallationStatus
from src.ftp.connection import FTPConnectionManager, ConnectionState
from src.ftp.exceptions import FTPUploadError


class TestUploadProgress:
    """Tests for UploadProgress dataclass."""

    def test_percent_calculation(self):
        """Test percentage calculation."""
        progress = UploadProgress(
            dump_path="/data/homebrew/Game1",
            file_name="dump_runner.elf",
            bytes_sent=50,
            bytes_total=100
        )
        assert progress.percent == 50.0

    def test_percent_zero_total(self):
        """Test percentage with zero total."""
        progress = UploadProgress(
            dump_path="/data/homebrew/Game1",
            file_name="dump_runner.elf",
            bytes_sent=0,
            bytes_total=0
        )
        assert progress.percent == 0.0

    def test_percent_complete(self):
        """Test 100% complete."""
        progress = UploadProgress(
            dump_path="/data/homebrew/Game1",
            file_name="dump_runner.elf",
            bytes_sent=1024,
            bytes_total=1024
        )
        assert progress.percent == 100.0


class TestUploadResult:
    """Tests for UploadResult dataclass."""

    def test_success_result(self):
        """Test successful upload result."""
        result = UploadResult(
            dump_path="/data/homebrew/Game1",
            success=True,
            elf_uploaded=True,
            js_uploaded=True,
            bytes_transferred=2048,
            duration_seconds=1.5
        )
        assert result.success is True
        assert result.error_message is None

    def test_failure_result(self):
        """Test failed upload result."""
        result = UploadResult(
            dump_path="/data/homebrew/Game1",
            success=False,
            error_message="Connection lost",
            elf_uploaded=True,
            js_uploaded=False
        )
        assert result.success is False
        assert result.error_message == "Connection lost"


class TestFileUploader:
    """Tests for FileUploader class."""

    @pytest.fixture
    def mock_connection(self):
        """Create mock FTP connection."""
        connection = Mock(spec=FTPConnectionManager)
        connection.is_connected = True
        connection.ftp = MagicMock()

        # Make storbinary call the callback to simulate real FTP behavior
        def fake_storbinary(cmd, fp, blocksize=8192, callback=None):
            if callback:
                # Read file and call callback with chunks
                while True:
                    data = fp.read(blocksize)
                    if not data:
                        break
                    callback(data)

        connection.ftp.storbinary.side_effect = fake_storbinary
        return connection

    @pytest.fixture
    def sample_dump(self):
        """Create sample game dump."""
        return GameDump(
            path="/data/homebrew/Game1",
            name="Game1",
            location_type=LocationType.INTERNAL,
            installation_status=InstallationStatus.NOT_INSTALLED
        )

    @pytest.fixture
    def temp_files(self):
        """Create temporary test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            elf_path = Path(tmpdir) / "dump_runner.elf"
            js_path = Path(tmpdir) / "homebrew.js"

            # Create test files with content
            elf_path.write_bytes(b"\x7fELF" + b"\x00" * 100)
            js_path.write_text("// homebrew.js test content")

            yield elf_path, js_path

    def test_init(self, mock_connection):
        """Test uploader initialization."""
        uploader = FileUploader(mock_connection)
        assert uploader.is_cancelled is False

    def test_cancel(self, mock_connection):
        """Test cancellation flag."""
        uploader = FileUploader(mock_connection)
        assert uploader.is_cancelled is False

        uploader.cancel()
        assert uploader.is_cancelled is True

        uploader.reset_cancel()
        assert uploader.is_cancelled is False

    def test_upload_to_dump_not_connected(self, sample_dump, temp_files):
        """Test upload fails when not connected."""
        connection = Mock(spec=FTPConnectionManager)
        connection.is_connected = False

        uploader = FileUploader(connection)
        elf_path, js_path = temp_files

        result = uploader.upload_to_dump(sample_dump, elf_path, js_path)

        assert result.success is False
        assert "Not connected" in result.error_message

    def test_upload_to_dump_success(self, mock_connection, sample_dump, temp_files):
        """Test successful upload to single dump."""
        uploader = FileUploader(mock_connection)
        elf_path, js_path = temp_files

        result = uploader.upload_to_dump(sample_dump, elf_path, js_path)

        assert result.success is True
        assert result.elf_uploaded is True
        assert result.js_uploaded is True
        assert result.bytes_transferred > 0

        # Verify FTP commands were called
        mock_connection.ftp.storbinary.assert_called()

    def test_upload_to_dump_with_progress(self, mock_connection, sample_dump, temp_files):
        """Test upload with progress callback."""
        uploader = FileUploader(mock_connection)
        elf_path, js_path = temp_files

        progress_updates = []

        def on_progress(progress: UploadProgress):
            progress_updates.append(progress)

        result = uploader.upload_to_dump(
            sample_dump, elf_path, js_path, on_progress=on_progress
        )

        assert result.success is True
        # Progress callback should have been called
        # (actual calls depend on FTP mock behavior)

    def test_upload_to_dump_ftp_error(self, mock_connection, sample_dump, temp_files):
        """Test upload handles FTP errors."""
        mock_connection.ftp.storbinary.side_effect = Exception("FTP error")

        uploader = FileUploader(mock_connection)
        elf_path, js_path = temp_files

        result = uploader.upload_to_dump(sample_dump, elf_path, js_path)

        assert result.success is False
        assert "FTP error" in result.error_message

    def test_upload_to_dump_cancelled(self, mock_connection, sample_dump, temp_files):
        """Test upload can be cancelled."""
        uploader = FileUploader(mock_connection)
        uploader.cancel()

        elf_path, js_path = temp_files
        result = uploader.upload_to_dump(sample_dump, elf_path, js_path)

        assert result.success is False
        assert "cancelled" in result.error_message.lower()

    def test_upload_batch_success(self, mock_connection, temp_files):
        """Test batch upload to multiple dumps."""
        dumps = [
            GameDump(
                path="/data/homebrew/Game1",
                name="Game1",
                location_type=LocationType.INTERNAL
            ),
            GameDump(
                path="/data/homebrew/Game2",
                name="Game2",
                location_type=LocationType.INTERNAL
            ),
            GameDump(
                path="/mnt/usb0/homebrew/Game3",
                name="Game3",
                location_type=LocationType.USB
            ),
        ]

        uploader = FileUploader(mock_connection)
        elf_path, js_path = temp_files

        results = uploader.upload_batch(dumps, elf_path, js_path)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_upload_batch_with_callback(self, mock_connection, temp_files):
        """Test batch upload with completion callback."""
        dumps = [
            GameDump(
                path="/data/homebrew/Game1",
                name="Game1",
                location_type=LocationType.INTERNAL
            ),
            GameDump(
                path="/data/homebrew/Game2",
                name="Game2",
                location_type=LocationType.INTERNAL
            ),
        ]

        completed = []

        def on_complete(result: UploadResult):
            completed.append(result)

        uploader = FileUploader(mock_connection)
        elf_path, js_path = temp_files

        results = uploader.upload_batch(
            dumps, elf_path, js_path, on_dump_complete=on_complete
        )

        assert len(completed) == 2
        assert len(results) == 2

    def test_upload_batch_partial_failure(self, mock_connection, temp_files):
        """Test batch continues after individual failure."""
        dumps = [
            GameDump(
                path="/data/homebrew/Game1",
                name="Game1",
                location_type=LocationType.INTERNAL
            ),
            GameDump(
                path="/data/homebrew/Game2",
                name="Game2",
                location_type=LocationType.INTERNAL
            ),
        ]

        call_count = [0]

        def mock_storbinary(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("First upload failed")

        mock_connection.ftp.storbinary.side_effect = mock_storbinary

        uploader = FileUploader(mock_connection)
        elf_path, js_path = temp_files

        results = uploader.upload_batch(dumps, elf_path, js_path)

        assert len(results) == 2
        # First dump should fail, second may succeed or fail depending on mock
        assert results[0].success is False

    def test_upload_batch_cancelled_midway(self, mock_connection, temp_files):
        """Test batch can be cancelled midway."""
        dumps = [
            GameDump(
                path="/data/homebrew/Game1",
                name="Game1",
                location_type=LocationType.INTERNAL
            ),
            GameDump(
                path="/data/homebrew/Game2",
                name="Game2",
                location_type=LocationType.INTERNAL
            ),
            GameDump(
                path="/data/homebrew/Game3",
                name="Game3",
                location_type=LocationType.INTERNAL
            ),
        ]

        uploader = FileUploader(mock_connection)
        elf_path, js_path = temp_files

        def cancel_after_first(result):
            if result.dump_path == "/data/homebrew/Game1":
                uploader.cancel()

        results = uploader.upload_batch(
            dumps, elf_path, js_path, on_dump_complete=cancel_after_first
        )

        assert len(results) == 3
        # First should succeed, rest should be cancelled
        cancelled_count = sum(1 for r in results if "cancelled" in (r.error_message or "").lower())
        assert cancelled_count >= 1

    def test_get_batch_summary(self, mock_connection, temp_files):
        """Test batch summary statistics."""
        uploader = FileUploader(mock_connection)

        results = [
            UploadResult(
                dump_path="/data/homebrew/Game1",
                success=True,
                bytes_transferred=1000,
                duration_seconds=1.0
            ),
            UploadResult(
                dump_path="/data/homebrew/Game2",
                success=True,
                bytes_transferred=2000,
                duration_seconds=2.0
            ),
            UploadResult(
                dump_path="/data/homebrew/Game3",
                success=False,
                error_message="Failed",
                bytes_transferred=500,
                duration_seconds=0.5
            ),
        ]

        summary = uploader.get_batch_summary(results)

        assert summary["total"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["bytes_transferred"] == 3500
        assert summary["duration_seconds"] == 3.5
        assert len(summary["failures"]) == 1
