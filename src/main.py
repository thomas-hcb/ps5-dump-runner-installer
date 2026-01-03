"""Main application entry point for PS5 Dump Runner FTP Installer.

Initializes the application, wires up components, and starts the GUI.
"""

import sys
import tkinter as tk
from typing import List, Optional

from .config.paths import get_log_file_path
from .config.settings import AppSettings, SettingsManager
from .config.credentials import CredentialManager
from .ftp.connection import FTPConnectionConfig, FTPConnectionManager, ConnectionState
from .ftp.scanner import DumpScanner, GameDump
from .ftp.exceptions import (
    FTPError,
    FTPConnectionError,
    FTPAuthenticationError,
    FTPTimeoutError,
    FTPNotConnectedError,
)
from .gui.main_window import MainWindow, AppCallbacks
from .utils.logging import setup_logging, get_logger
from .utils.threading import ThreadedTask, GUIUpdateQueue


class Application(AppCallbacks):
    """
    Main application controller.

    Coordinates between GUI and backend modules, handling user
    actions and updating the UI accordingly.
    """

    def __init__(self):
        """Initialize the application."""
        # Set up logging first
        self._logger = setup_logging(log_file=get_log_file_path())
        self._logger.info("Application starting")

        # Initialize settings
        self._settings_manager = SettingsManager()
        self._settings = self._settings_manager.load()
        self._credential_manager = CredentialManager()

        # Initialize FTP components
        self._connection_manager = FTPConnectionManager()
        self._scanner: Optional[DumpScanner] = None

        # Initialize GUI
        self._root = tk.Tk()
        self._window = MainWindow(self._root, callbacks=self)

        # Update queue for thread-safe GUI updates
        self._update_queue = GUIUpdateQueue()

        # Apply saved settings to GUI
        self._apply_settings()

        self._logger.info("Application initialized")

    def _apply_settings(self) -> None:
        """Apply saved settings to the GUI."""
        # Pre-populate connection fields
        password = ""
        if self._settings.last_host and self._settings.last_username:
            saved_pass = self._credential_manager.get_password(
                self._settings.last_host,
                self._settings.last_username
            )
            if saved_pass:
                password = saved_pass

        self._window.set_connection_values(
            host=self._settings.last_host,
            port=self._settings.last_port,
            username=self._settings.last_username,
            password=password
        )

        # Apply window size
        if self._settings.window_width and self._settings.window_height:
            self._root.geometry(
                f"{self._settings.window_width}x{self._settings.window_height}"
            )

    def _save_connection_settings(
        self,
        host: str,
        port: int,
        username: str,
        password: str
    ) -> None:
        """Save successful connection settings."""
        self._settings.last_host = host
        self._settings.last_port = port
        self._settings.last_username = username
        self._settings_manager.save(self._settings)

        # Save password securely
        if password:
            self._credential_manager.save_password(host, username, password)

        self._logger.info(f"Saved connection settings for {host}")

    # AppCallbacks implementation

    def on_connect(self, host: str, port: int, username: str, password: str) -> None:
        """Handle connect request from GUI."""
        self._logger.info(f"Connect requested to {host}:{port}")

        # Validate inputs
        if not host:
            self._window.show_error("Connection Error", "Please enter a host address.")
            return

        # Update UI to connecting state
        self._window.set_connection_state(ConnectionState.CONNECTING)
        self._window.update_status(f"Connecting to {host}...")

        # Run connection in background to keep UI responsive
        def connect_task():
            try:
                config = FTPConnectionConfig(
                    host=host,
                    port=port,
                    username=username,
                    passive_mode=self._settings.passive_mode,
                    timeout=self._settings.timeout
                )
                self._connection_manager.connect(config, password)
                return True, None
            except Exception as e:
                return False, e

        def on_connect_complete(result):
            success, error = result.result if result.result else (False, None)
            # Schedule GUI update on main thread
            self._root.after(0, lambda: self._handle_connect_result(
                success, error, host, port, username, password
            ))

        task = ThreadedTask(connect_task, on_complete=on_connect_complete)
        task.start()

    def _handle_connect_result(
        self,
        success: bool,
        error: Optional[Exception],
        host: str,
        port: int,
        username: str,
        password: str
    ) -> None:
        """Handle connection result on main thread."""
        if success:
            self._logger.info(f"Connected to {host}:{port}")
            self._window.set_connection_state(ConnectionState.CONNECTED)
            self._save_connection_settings(host, port, username, password)

            # Initialize scanner and auto-scan
            self._scanner = DumpScanner(self._connection_manager)
            self.on_scan()
        else:
            self._logger.error(f"Connection failed: {error}")
            self._window.set_connection_state(ConnectionState.ERROR)

            # Show user-friendly error message
            if isinstance(error, FTPAuthenticationError):
                message = "Authentication failed. Please check your username and password."
            elif isinstance(error, FTPTimeoutError):
                message = f"Connection timed out. Is the PS5 FTP server running?"
            elif isinstance(error, FTPConnectionError):
                message = f"Could not connect to {host}:{port}. Please check the address and ensure the PS5 FTP server is running."
            else:
                message = f"Connection failed: {error}"

            self._window.show_error("Connection Error", message)

    def on_disconnect(self) -> None:
        """Handle disconnect request from GUI."""
        self._logger.info("Disconnect requested")
        self._connection_manager.disconnect()
        self._scanner = None
        self._window.set_connection_state(ConnectionState.DISCONNECTED)
        self._window.update_status("Disconnected")

    def on_scan(self) -> None:
        """Handle scan request from GUI."""
        if not self._scanner:
            self._window.show_error("Error", "Not connected to FTP server.")
            return

        self._logger.info("Scanning for game dumps")
        self._window.update_status("Scanning for game dumps...")

        def scan_task():
            try:
                dumps = self._scanner.scan()
                return dumps, None
            except Exception as e:
                return None, e

        def on_scan_complete(result):
            dumps, error = result.result if result.result else (None, None)
            self._root.after(0, lambda: self._handle_scan_result(dumps, error))

        task = ThreadedTask(scan_task, on_complete=on_scan_complete)
        task.start()

    def _handle_scan_result(
        self,
        dumps: Optional[List[GameDump]],
        error: Optional[Exception]
    ) -> None:
        """Handle scan result on main thread."""
        if error:
            self._logger.error(f"Scan failed: {error}")
            self._window.show_error("Scan Error", f"Failed to scan for game dumps: {error}")
            return

        if dumps is not None:
            self._logger.info(f"Found {len(dumps)} game dumps")
            self._window.set_dumps(dumps)

    def on_upload(self, selected_dumps: List[GameDump]) -> None:
        """Handle upload request from GUI."""
        # This will be fully implemented in US2 (Phase 4)
        self._logger.info(f"Upload requested for {len(selected_dumps)} dumps")
        self._window.show_info(
            "Upload",
            f"Upload functionality will be implemented in Phase 4 (US2).\n\n"
            f"Selected {len(selected_dumps)} dumps for upload."
        )

    def run(self) -> None:
        """Start the application."""
        self._logger.info("Starting main event loop")

        # Handle window close
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        try:
            self._window.run()
        except Exception as e:
            self._logger.exception(f"Unhandled exception: {e}")
            raise
        finally:
            self._cleanup()

    def _on_close(self) -> None:
        """Handle window close event."""
        # Save window size
        self._settings.window_width = self._root.winfo_width()
        self._settings.window_height = self._root.winfo_height()
        self._settings_manager.save(self._settings)

        # Disconnect if connected
        if self._connection_manager.is_connected:
            self._connection_manager.disconnect()

        self._logger.info("Application closing")
        self._root.quit()

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._connection_manager.is_connected:
            self._connection_manager.disconnect()
        self._logger.info("Application cleanup complete")


def main() -> int:
    """
    Application entry point.

    Returns:
        Exit code (0 for success)
    """
    try:
        app = Application()
        app.run()
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
