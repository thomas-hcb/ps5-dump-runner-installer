"""FTP connection management for PS5 Dump Runner FTP Installer.

Provides ConnectionState enum, FTPConnectionConfig dataclass,
and FTPConnectionManager class for managing FTP connections.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from ftplib import FTP, error_perm, error_temp
from typing import Optional
import socket

from src.ftp.exceptions import (
    FTPConnectionError,
    FTPAuthenticationError,
    FTPNotConnectedError,
    FTPTimeoutError,
)


class ConnectionState(Enum):
    """FTP connection state."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class FTPConnectionConfig:
    """FTP connection configuration."""
    host: str
    port: int = 1337
    username: str = "anonymous"
    passive_mode: bool = True
    timeout: int = 30

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.host:
            raise ValueError("Host is required")
        if not 1 <= self.port <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {self.port}")
        if not 5 <= self.timeout <= 300:
            raise ValueError(f"Timeout must be between 5 and 300, got {self.timeout}")


class FTPConnectionManager:
    """Manages FTP connection lifecycle."""

    def __init__(self):
        """Initialize the connection manager."""
        self._ftp: Optional[FTP] = None
        self._config: Optional[FTPConnectionConfig] = None
        self._state = ConnectionState.DISCONNECTED
        self._connected_at: Optional[datetime] = None
        self._last_activity: Optional[datetime] = None
        self._error_message: Optional[str] = None

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """True if currently connected."""
        return self._state == ConnectionState.CONNECTED

    @property
    def config(self) -> Optional[FTPConnectionConfig]:
        """Current connection configuration."""
        return self._config

    @property
    def connected_at(self) -> Optional[datetime]:
        """Timestamp when connection was established."""
        return self._connected_at

    @property
    def last_activity(self) -> Optional[datetime]:
        """Timestamp of last successful operation."""
        return self._last_activity

    @property
    def error_message(self) -> Optional[str]:
        """Last error message if state is ERROR."""
        return self._error_message

    @property
    def ftp(self) -> FTP:
        """
        Get the underlying FTP object.

        Raises:
            FTPNotConnectedError: If not connected
        """
        if not self.is_connected or self._ftp is None:
            raise FTPNotConnectedError("FTP access")
        return self._ftp

    def connect(self, config: FTPConnectionConfig, password: str = "") -> None:
        """
        Establish FTP connection.

        Args:
            config: Connection configuration
            password: FTP password

        Raises:
            FTPConnectionError: If connection fails
            FTPAuthenticationError: If login fails
            FTPTimeoutError: If connection times out
        """
        self._config = config
        self._state = ConnectionState.CONNECTING
        self._error_message = None

        try:
            # Create FTP instance
            self._ftp = FTP()
            self._ftp.set_debuglevel(0)

            # Connect to server
            try:
                self._ftp.connect(
                    host=config.host,
                    port=config.port,
                    timeout=config.timeout
                )
            except socket.timeout:
                raise FTPTimeoutError("Connection", config.timeout)
            except (socket.error, OSError) as e:
                raise FTPConnectionError(config.host, config.port, e)

            # Login
            try:
                self._ftp.login(user=config.username, passwd=password)
            except error_perm as e:
                raise FTPAuthenticationError(config.username, e)

            # Set passive mode
            self._ftp.set_pasv(config.passive_mode)

            # Connection successful
            self._state = ConnectionState.CONNECTED
            self._connected_at = datetime.now()
            self._last_activity = self._connected_at

        except (FTPConnectionError, FTPAuthenticationError, FTPTimeoutError):
            self._state = ConnectionState.ERROR
            self._ftp = None
            raise
        except Exception as e:
            self._state = ConnectionState.ERROR
            self._error_message = str(e)
            self._ftp = None
            raise FTPConnectionError(config.host, config.port, e)

    def disconnect(self) -> None:
        """Close FTP connection gracefully."""
        if self._ftp:
            try:
                self._ftp.quit()
            except Exception:
                # Best effort close
                try:
                    self._ftp.close()
                except Exception:
                    pass

        self._ftp = None
        self._state = ConnectionState.DISCONNECTED
        self._connected_at = None

    def _update_activity(self) -> None:
        """Update last activity timestamp."""
        self._last_activity = datetime.now()

    def list_directory(self, path: str = ".") -> list[str]:
        """
        List directory contents.

        Args:
            path: Directory path to list

        Returns:
            List of file/directory names

        Raises:
            FTPNotConnectedError: If not connected
        """
        self._update_activity()
        return self.ftp.nlst(path)

    def change_directory(self, path: str) -> None:
        """
        Change current working directory.

        Args:
            path: Directory path

        Raises:
            FTPNotConnectedError: If not connected
        """
        self.ftp.cwd(path)
        self._update_activity()

    def get_current_directory(self) -> str:
        """
        Get current working directory.

        Returns:
            Current directory path

        Raises:
            FTPNotConnectedError: If not connected
        """
        self._update_activity()
        return self.ftp.pwd()
