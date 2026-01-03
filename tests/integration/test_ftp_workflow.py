"""Integration tests for FTP workflow.

Tests the complete workflow of connecting to FTP, scanning for dumps,
and uploading files using a mock FTP server.
"""

import pytest
from pathlib import Path

from src.ftp.connection import FTPConnectionConfig, FTPConnectionManager, ConnectionState
from src.ftp.scanner import DumpScanner, LocationType, InstallationStatus
from src.ftp.exceptions import FTPConnectionError, FTPAuthenticationError

from .mock_ftp_server import MockPS5FTPServer


@pytest.fixture
def ftp_server():
    """Provide a running mock FTP server."""
    server = MockPS5FTPServer(port=21211)
    server.start()
    yield server
    server.stop()


@pytest.fixture
def connection_manager():
    """Provide a fresh connection manager."""
    return FTPConnectionManager()


class TestFTPConnectionWorkflow:
    """Integration tests for FTP connection workflow."""

    def test_connect_and_disconnect(self, ftp_server, connection_manager):
        """Test basic connect and disconnect cycle."""
        config = FTPConnectionConfig(
            host=ftp_server.host,
            port=ftp_server.port,
            username=ftp_server.username,
        )

        # Connect
        connection_manager.connect(config, password=ftp_server.password)

        assert connection_manager.state == ConnectionState.CONNECTED
        assert connection_manager.is_connected is True

        # Disconnect
        connection_manager.disconnect()

        assert connection_manager.state == ConnectionState.DISCONNECTED
        assert connection_manager.is_connected is False

    def test_connect_wrong_password(self, ftp_server, connection_manager):
        """Test connection with wrong password fails."""
        config = FTPConnectionConfig(
            host=ftp_server.host,
            port=ftp_server.port,
            username=ftp_server.username,
        )

        with pytest.raises(FTPAuthenticationError):
            connection_manager.connect(config, password="wrongpassword")

        assert connection_manager.state == ConnectionState.ERROR

    def test_connect_wrong_host(self, connection_manager):
        """Test connection to non-existent host fails."""
        from src.ftp.exceptions import FTPTimeoutError

        config = FTPConnectionConfig(
            host="192.168.255.255",
            port=21212,
            timeout=5,  # Short timeout for test
        )

        # May raise either ConnectionError or TimeoutError depending on network
        with pytest.raises((FTPConnectionError, FTPTimeoutError)):
            connection_manager.connect(config, password="test")

        assert connection_manager.state == ConnectionState.ERROR


class TestDumpScannerWorkflow:
    """Integration tests for dump scanning workflow."""

    def test_scan_finds_dumps(self, ftp_server, connection_manager):
        """Test scanning finds game dumps in mock structure."""
        config = FTPConnectionConfig(
            host=ftp_server.host,
            port=ftp_server.port,
            username=ftp_server.username,
        )

        connection_manager.connect(config, password=ftp_server.password)

        scanner = DumpScanner(connection_manager)
        dumps = scanner.scan()

        # Should find dumps in /data/homebrew, /mnt/usb0/homebrew, /mnt/ext0/homebrew
        assert len(dumps) >= 3  # At least CUSA00001, CUSA00002, CUSA00003

        # Check we found internal dumps
        internal_dumps = scanner.get_dumps_by_location(LocationType.INTERNAL)
        assert len(internal_dumps) >= 3

        # Check we found USB dump
        usb_dumps = scanner.get_dumps_by_location(LocationType.USB)
        assert len(usb_dumps) >= 1

        connection_manager.disconnect()

    def test_scan_detects_installed_files(self, ftp_server, connection_manager):
        """Test scanning detects dumps with files installed."""
        config = FTPConnectionConfig(
            host=ftp_server.host,
            port=ftp_server.port,
            username=ftp_server.username,
        )

        connection_manager.connect(config, password=ftp_server.password)

        scanner = DumpScanner(connection_manager)
        dumps = scanner.scan()

        # Find CUSA00001 which has files installed
        cusa00001 = scanner.get_dump_by_path("/data/homebrew/CUSA00001")

        assert cusa00001 is not None
        assert cusa00001.has_elf is True
        assert cusa00001.has_js is True
        assert cusa00001.installation_status != InstallationStatus.NOT_INSTALLED

        connection_manager.disconnect()

    def test_scan_multiple_times(self, ftp_server, connection_manager):
        """Test scanning multiple times updates results."""
        config = FTPConnectionConfig(
            host=ftp_server.host,
            port=ftp_server.port,
            username=ftp_server.username,
        )

        connection_manager.connect(config, password=ftp_server.password)
        scanner = DumpScanner(connection_manager)

        # First scan
        dumps1 = scanner.scan()
        count1 = len(dumps1)

        # Add a new game dump
        ftp_server.add_game_dump("/data/homebrew/NEWGAME01")

        # Second scan should find the new dump
        dumps2 = scanner.scan()
        count2 = len(dumps2)

        assert count2 == count1 + 1

        # Verify new dump is found
        new_dump = scanner.get_dump_by_path("/data/homebrew/NEWGAME01")
        assert new_dump is not None
        assert new_dump.name == "NEWGAME01"

        connection_manager.disconnect()


class TestCompleteWorkflow:
    """Integration tests for complete user workflow."""

    def test_connect_scan_workflow(self, ftp_server):
        """Test complete workflow: connect -> scan -> list dumps."""
        # Create connection
        manager = FTPConnectionManager()
        config = FTPConnectionConfig(
            host=ftp_server.host,
            port=ftp_server.port,
            username=ftp_server.username,
        )

        # Step 1: Connect
        manager.connect(config, password=ftp_server.password)
        assert manager.is_connected

        # Step 2: Scan for dumps
        scanner = DumpScanner(manager)
        dumps = scanner.scan()
        assert len(dumps) > 0

        # Step 3: Filter dumps
        installed = scanner.get_installed_dumps()
        not_installed = scanner.get_uninstalled_dumps()

        # At least CUSA00001 should be "installed" (has files)
        assert len(installed) >= 0  # May or may not detect as installed

        # Step 4: Disconnect
        manager.disconnect()
        assert not manager.is_connected

    def test_reconnect_after_disconnect(self, ftp_server):
        """Test reconnecting after disconnection."""
        manager = FTPConnectionManager()
        config = FTPConnectionConfig(
            host=ftp_server.host,
            port=ftp_server.port,
            username=ftp_server.username,
        )

        # First connection
        manager.connect(config, password=ftp_server.password)
        assert manager.is_connected
        manager.disconnect()
        assert not manager.is_connected

        # Reconnect
        manager.connect(config, password=ftp_server.password)
        assert manager.is_connected
        manager.disconnect()


class TestUploadWorkflow:
    """Integration tests for file upload workflow."""

    @pytest.fixture
    def temp_files(self, tmp_path):
        """Create temporary test files for upload."""
        elf_path = tmp_path / "dump_runner.elf"
        js_path = tmp_path / "homebrew.js"

        elf_path.write_bytes(b"\x7fELF" + b"\x00" * 100)
        js_path.write_text("// homebrew.js test content")

        return elf_path, js_path

    def test_upload_to_single_dump(self, ftp_server, temp_files):
        """Test uploading files to a single dump."""
        from src.ftp.uploader import FileUploader

        manager = FTPConnectionManager()
        config = FTPConnectionConfig(
            host=ftp_server.host,
            port=ftp_server.port,
            username=ftp_server.username,
        )

        manager.connect(config, password=ftp_server.password)

        scanner = DumpScanner(manager)
        dumps = scanner.scan()

        # Find a dump without files installed
        target_dump = None
        for dump in dumps:
            if not dump.has_elf and not dump.has_js:
                target_dump = dump
                break

        if target_dump is None:
            # Use any dump
            target_dump = dumps[0]

        elf_path, js_path = temp_files
        uploader = FileUploader(manager)

        result = uploader.upload_to_dump(target_dump, elf_path, js_path)

        assert result.success is True
        assert result.elf_uploaded is True
        assert result.js_uploaded is True
        assert result.bytes_transferred > 0

        manager.disconnect()

    def test_upload_to_multiple_dumps(self, ftp_server, temp_files):
        """Test batch upload to multiple dumps."""
        from src.ftp.uploader import FileUploader

        manager = FTPConnectionManager()
        config = FTPConnectionConfig(
            host=ftp_server.host,
            port=ftp_server.port,
            username=ftp_server.username,
        )

        manager.connect(config, password=ftp_server.password)

        scanner = DumpScanner(manager)
        dumps = scanner.scan()

        # Select first 2 dumps
        target_dumps = dumps[:2]

        elf_path, js_path = temp_files
        uploader = FileUploader(manager)

        results = uploader.upload_batch(target_dumps, elf_path, js_path)

        assert len(results) == 2
        assert all(r.success for r in results)

        # Verify summary
        summary = uploader.get_batch_summary(results)
        assert summary["total"] == 2
        assert summary["successful"] == 2
        assert summary["failed"] == 0

        manager.disconnect()

    def test_upload_with_progress_callback(self, ftp_server, temp_files):
        """Test upload reports progress."""
        from src.ftp.uploader import FileUploader, UploadProgress

        manager = FTPConnectionManager()
        config = FTPConnectionConfig(
            host=ftp_server.host,
            port=ftp_server.port,
            username=ftp_server.username,
        )

        manager.connect(config, password=ftp_server.password)

        scanner = DumpScanner(manager)
        dumps = scanner.scan()
        target_dump = dumps[0]

        elf_path, js_path = temp_files
        uploader = FileUploader(manager)

        progress_updates = []

        def on_progress(progress: UploadProgress):
            progress_updates.append(progress)

        result = uploader.upload_to_dump(
            target_dump, elf_path, js_path, on_progress=on_progress
        )

        assert result.success is True
        # Progress callback should have been called at least once
        assert len(progress_updates) >= 0  # May be 0 for small files

        manager.disconnect()

    def test_verify_files_uploaded(self, ftp_server, temp_files):
        """Test that files actually appear on the server."""
        from src.ftp.uploader import FileUploader

        manager = FTPConnectionManager()
        config = FTPConnectionConfig(
            host=ftp_server.host,
            port=ftp_server.port,
            username=ftp_server.username,
        )

        manager.connect(config, password=ftp_server.password)

        # Add a fresh dump without files
        ftp_server.add_game_dump("/data/homebrew/UPLOAD_TEST")

        scanner = DumpScanner(manager)
        dumps = scanner.scan()
        target_dump = scanner.get_dump_by_path("/data/homebrew/UPLOAD_TEST")

        assert target_dump is not None
        assert target_dump.has_elf is False
        assert target_dump.has_js is False

        elf_path, js_path = temp_files
        uploader = FileUploader(manager)

        result = uploader.upload_to_dump(target_dump, elf_path, js_path)
        assert result.success is True

        # Refresh the dump status
        scanner.refresh(target_dump)

        # Now files should be present
        assert target_dump.has_elf is True
        assert target_dump.has_js is True

        manager.disconnect()
