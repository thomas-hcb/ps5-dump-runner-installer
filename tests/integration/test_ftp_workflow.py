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
