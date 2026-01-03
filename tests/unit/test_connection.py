"""Unit tests for FTPConnectionManager.

Tests connection lifecycle, state transitions, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import socket

from src.ftp.connection import (
    ConnectionState,
    FTPConnectionConfig,
    FTPConnectionManager,
)
from src.ftp.exceptions import (
    FTPConnectionError,
    FTPAuthenticationError,
    FTPTimeoutError,
    FTPNotConnectedError,
)


class TestFTPConnectionConfig:
    """Tests for FTPConnectionConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = FTPConnectionConfig(host="192.168.1.100")
        assert config.host == "192.168.1.100"
        assert config.port == 2121
        assert config.username == "anonymous"
        assert config.passive_mode is True
        assert config.timeout == 30

    def test_custom_values(self):
        """Test custom configuration values."""
        config = FTPConnectionConfig(
            host="10.0.0.1",
            port=21,
            username="ps5user",
            passive_mode=False,
            timeout=60
        )
        assert config.host == "10.0.0.1"
        assert config.port == 21
        assert config.username == "ps5user"
        assert config.passive_mode is False
        assert config.timeout == 60

    def test_empty_host_raises_error(self):
        """Test that empty host raises ValueError."""
        with pytest.raises(ValueError, match="Host is required"):
            FTPConnectionConfig(host="")

    def test_invalid_port_raises_error(self):
        """Test that invalid port raises ValueError."""
        with pytest.raises(ValueError, match="Port must be between"):
            FTPConnectionConfig(host="192.168.1.1", port=0)
        with pytest.raises(ValueError, match="Port must be between"):
            FTPConnectionConfig(host="192.168.1.1", port=70000)

    def test_invalid_timeout_raises_error(self):
        """Test that invalid timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be between"):
            FTPConnectionConfig(host="192.168.1.1", timeout=1)
        with pytest.raises(ValueError, match="Timeout must be between"):
            FTPConnectionConfig(host="192.168.1.1", timeout=500)


class TestFTPConnectionManager:
    """Tests for FTPConnectionManager class."""

    def test_initial_state_is_disconnected(self):
        """Test that initial state is DISCONNECTED."""
        manager = FTPConnectionManager()
        assert manager.state == ConnectionState.DISCONNECTED
        assert manager.is_connected is False
        assert manager.config is None

    @patch("src.ftp.connection.FTP")
    def test_connect_success(self, mock_ftp_class):
        """Test successful connection."""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp

        manager = FTPConnectionManager()
        config = FTPConnectionConfig(host="192.168.1.100")

        manager.connect(config, password="testpass")

        assert manager.state == ConnectionState.CONNECTED
        assert manager.is_connected is True
        assert manager.config == config
        assert manager.connected_at is not None

        mock_ftp.connect.assert_called_once_with(
            host="192.168.1.100",
            port=2121,
            timeout=30
        )
        mock_ftp.login.assert_called_once_with(user="anonymous", passwd="testpass")
        mock_ftp.set_pasv.assert_called_once_with(True)

    @patch("src.ftp.connection.FTP")
    def test_connect_socket_error(self, mock_ftp_class):
        """Test connection failure due to socket error."""
        mock_ftp = MagicMock()
        mock_ftp.connect.side_effect = socket.error("Connection refused")
        mock_ftp_class.return_value = mock_ftp

        manager = FTPConnectionManager()
        config = FTPConnectionConfig(host="192.168.1.100")

        with pytest.raises(FTPConnectionError):
            manager.connect(config, password="testpass")

        assert manager.state == ConnectionState.ERROR
        assert manager.is_connected is False

    @patch("src.ftp.connection.FTP")
    def test_connect_timeout(self, mock_ftp_class):
        """Test connection timeout."""
        mock_ftp = MagicMock()
        mock_ftp.connect.side_effect = socket.timeout("Connection timed out")
        mock_ftp_class.return_value = mock_ftp

        manager = FTPConnectionManager()
        config = FTPConnectionConfig(host="192.168.1.100")

        with pytest.raises(FTPTimeoutError):
            manager.connect(config, password="testpass")

        assert manager.state == ConnectionState.ERROR

    @patch("src.ftp.connection.FTP")
    def test_connect_auth_failure(self, mock_ftp_class):
        """Test authentication failure."""
        from ftplib import error_perm

        mock_ftp = MagicMock()
        mock_ftp.login.side_effect = error_perm("530 Login incorrect")
        mock_ftp_class.return_value = mock_ftp

        manager = FTPConnectionManager()
        config = FTPConnectionConfig(host="192.168.1.100")

        with pytest.raises(FTPAuthenticationError):
            manager.connect(config, password="wrongpass")

        assert manager.state == ConnectionState.ERROR

    @patch("src.ftp.connection.FTP")
    def test_disconnect(self, mock_ftp_class):
        """Test disconnection."""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp

        manager = FTPConnectionManager()
        config = FTPConnectionConfig(host="192.168.1.100")

        manager.connect(config, password="testpass")
        assert manager.is_connected is True

        manager.disconnect()

        assert manager.state == ConnectionState.DISCONNECTED
        assert manager.is_connected is False
        mock_ftp.quit.assert_called_once()

    @patch("src.ftp.connection.FTP")
    def test_disconnect_graceful_on_error(self, mock_ftp_class):
        """Test disconnect handles errors gracefully."""
        mock_ftp = MagicMock()
        mock_ftp.quit.side_effect = Exception("Already closed")
        mock_ftp_class.return_value = mock_ftp

        manager = FTPConnectionManager()
        config = FTPConnectionConfig(host="192.168.1.100")

        manager.connect(config, password="testpass")
        manager.disconnect()  # Should not raise

        assert manager.state == ConnectionState.DISCONNECTED

    def test_ftp_property_raises_when_not_connected(self):
        """Test that accessing ftp property raises when not connected."""
        manager = FTPConnectionManager()

        with pytest.raises(FTPNotConnectedError):
            _ = manager.ftp

    @patch("src.ftp.connection.FTP")
    def test_list_directory(self, mock_ftp_class):
        """Test listing directory contents."""
        mock_ftp = MagicMock()
        mock_ftp.nlst.return_value = ["game1", "game2", "game3"]
        mock_ftp_class.return_value = mock_ftp

        manager = FTPConnectionManager()
        config = FTPConnectionConfig(host="192.168.1.100")
        manager.connect(config, password="testpass")

        result = manager.list_directory("/data/homebrew")

        assert result == ["game1", "game2", "game3"]
        mock_ftp.nlst.assert_called_with("/data/homebrew")

    @patch("src.ftp.connection.FTP")
    def test_change_directory(self, mock_ftp_class):
        """Test changing directory."""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp

        manager = FTPConnectionManager()
        config = FTPConnectionConfig(host="192.168.1.100")
        manager.connect(config, password="testpass")

        manager.change_directory("/data/homebrew/game1")

        mock_ftp.cwd.assert_called_with("/data/homebrew/game1")


class TestConnectionStateEnum:
    """Tests for ConnectionState enum."""

    def test_enum_values(self):
        """Test enum has expected values."""
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.ERROR.value == "error"

    def test_all_states_exist(self):
        """Test all expected states exist."""
        states = [s.value for s in ConnectionState]
        assert "disconnected" in states
        assert "connecting" in states
        assert "connected" in states
        assert "error" in states
