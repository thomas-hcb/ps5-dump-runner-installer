"""Main application entry point for PS5 Dump Runner FTP Installer.

Initializes the application, wires up components, and starts the GUI.
"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
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
    FTPUploadError,
)
from .ftp.uploader import FileUploader, UploadProgress, UploadResult
from .gui.main_window import MainWindow, AppCallbacks
from .gui.upload_dialog import UploadDialog
from .gui.download_dialog import DownloadDialog
from .updater.downloader import ReleaseDownloader, DownloadProgress
from .updater.github_client import GitHubConnectionError, GitHubError
from .updater.release import DumpRunnerRelease
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
        self._uploader: Optional[FileUploader] = None
        self._upload_dialog: Optional[UploadDialog] = None
        self._scan_in_progress: bool = False

        # Initialize updater components
        self._release_downloader = ReleaseDownloader()
        self._current_release: Optional[DumpRunnerRelease] = None
        self._download_dialog: Optional[DownloadDialog] = None
        self._download_cancelled: bool = False

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

        # Check for cached release
        self._check_cached_release()

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

        # Prevent concurrent scans
        if self._scan_in_progress:
            self._logger.debug("Scan already in progress, ignoring request")
            return

        self._scan_in_progress = True
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
        # Reset scan flag
        self._scan_in_progress = False

        if error:
            self._logger.error(f"Scan failed: {error}")

            # Provide user-friendly error messages
            error_str = str(error)
            if "10061" in error_str or "Connection refused" in error_str:
                message = (
                    "Connection refused. The FTP server may have disconnected.\n\n"
                    "Please check that:\n"
                    "• The PS5 FTP server is still running\n"
                    "• Your PS5 is still connected to the network\n\n"
                    "Try disconnecting and reconnecting."
                )
                # Reset connection state since it's clearly broken
                self._connection_manager.disconnect()
                self._scanner = None
                self._window.set_connection_state(ConnectionState.DISCONNECTED)
            elif "10054" in error_str or "forcibly closed" in error_str:
                message = (
                    "Connection was closed by the PS5.\n\n"
                    "The FTP server may have timed out or been stopped.\n"
                    "Try disconnecting and reconnecting."
                )
                self._connection_manager.disconnect()
                self._scanner = None
                self._window.set_connection_state(ConnectionState.DISCONNECTED)
            elif "timed out" in error_str.lower():
                message = (
                    "Connection timed out while scanning.\n\n"
                    "The PS5 may be busy or the network is slow.\n"
                    "Try scanning again."
                )
            else:
                message = f"Failed to scan for game dumps:\n\n{error}"

            self._window.show_error("Scan Error", message)
            return

        if dumps is not None:
            self._logger.info(f"Found {len(dumps)} game dumps")
            self._window.set_dumps(dumps)

    def on_upload(self, selected_dumps: List[GameDump]) -> None:
        """Handle upload request from GUI."""
        self._logger.info(f"Upload requested for {len(selected_dumps)} dumps")

        if not self._connection_manager.is_connected:
            self._window.show_error("Error", "Not connected to FTP server.")
            return

        # Ask user to select dump_runner files
        elf_path = self._select_file(
            "Select dump_runner.elf",
            [("ELF files", "*.elf"), ("All files", "*.*")]
        )
        if not elf_path:
            return

        js_path = self._select_file(
            "Select homebrew.js",
            [("JavaScript files", "*.js"), ("All files", "*.*")]
        )
        if not js_path:
            return

        # Check if files already exist (overwrite confirmation)
        dumps_with_existing = self._check_existing_files(selected_dumps)
        if dumps_with_existing:
            dump_names = "\n".join([d.display_name for d in dumps_with_existing[:5]])
            if len(dumps_with_existing) > 5:
                dump_names += f"\n... and {len(dumps_with_existing) - 5} more"

            if not self._window.show_warning(
                "Overwrite Confirmation",
                f"The following dumps already have dump_runner files:\n\n"
                f"{dump_names}\n\n"
                f"Do you want to overwrite them?"
            ):
                return

        # Start the upload
        self._start_upload(selected_dumps, Path(elf_path), Path(js_path))

    def on_download_release(self) -> None:
        """Handle download latest release request from GUI."""
        self._logger.info("Download latest release requested")

        self._download_cancelled = False

        # Create and show download dialog
        self._download_dialog = DownloadDialog(
            self._root,
            title="Downloading Latest Release",
            on_cancel=self._handle_download_cancel,
            on_close=self._handle_download_dialog_closed
        )

        # Run download in background thread
        def download_task():
            try:
                release = self._release_downloader.download_latest(
                    progress_callback=self._on_download_progress
                )
                return release, None
            except Exception as e:
                return None, e

        def on_download_complete(result):
            release, error = result.result if result.result else (None, None)
            self._root.after(0, lambda: self._handle_download_complete(release, error))

        task = ThreadedTask(download_task, on_complete=on_download_complete)
        task.start()

    def _on_download_progress(self, progress: DownloadProgress) -> None:
        """Handle download progress (called from background thread)."""
        if self._download_cancelled:
            return
        self._root.after(0, lambda: self._update_download_progress(progress))

    def _update_download_progress(self, progress: DownloadProgress) -> None:
        """Update download progress in dialog (main thread)."""
        if self._download_dialog:
            self._download_dialog.update_progress(progress)

    def _handle_download_cancel(self) -> None:
        """Handle download cancel button."""
        self._logger.info("Download cancelled by user")
        self._download_cancelled = True

    def _handle_download_dialog_closed(self) -> None:
        """Handle download dialog being closed after completion."""
        self._logger.info("Download dialog closed")

        # Ensure button states are updated correctly after dialog closes
        if self._current_release and self._current_release.files_valid:
            self._window.set_official_release_available(True, self._current_release.version)
            self._logger.info(
                f"Refreshed official release availability: {self._current_release.version}"
            )

    def _handle_download_complete(
        self,
        release: Optional[DumpRunnerRelease],
        error: Optional[Exception]
    ) -> None:
        """Handle download completion (main thread)."""
        if not self._download_dialog:
            return

        if self._download_cancelled:
            self._download_dialog.complete(success=False, message="Download cancelled")
            return

        if error:
            self._logger.error(f"Download failed: {error}")

            # User-friendly error messages
            if isinstance(error, GitHubConnectionError):
                message = (
                    "Could not connect to GitHub.\n\n"
                    "Please check your internet connection and try again."
                )
            elif isinstance(error, GitHubError):
                message = f"GitHub error: {error}"
            else:
                message = f"Download failed: {error}"

            self._download_dialog.complete(success=False, message=message)
            self._window.update_status("Download failed")
            return

        if release:
            self._current_release = release
            self._logger.info(f"Downloaded release: {release.version}")
            self._logger.info(f"Files: ELF={release.elf_path}, JS={release.js_path}")
            self._logger.info(f"Files valid: {release.files_valid}")

            self._download_dialog.complete(
                success=True,
                message=f"Downloaded {release.version}"
            )

            # Update UI to show release is available
            self._window.set_official_release_available(True, release.version)
            self._window.update_status(f"Downloaded release {release.version} - click 'Upload Downloaded Files' to install")

    def on_upload_official(self, selected_dumps: List[GameDump]) -> None:
        """Handle upload official release request from GUI."""
        self._logger.info(f"on_upload_official called with {len(selected_dumps)} dumps")

        if not self._current_release:
            self._logger.warning("No current release available")
            self._window.show_error(
                "No Release",
                "No official release downloaded.\n\n"
                "Please click 'Download Latest' first."
            )
            return

        self._logger.info(f"Current release: {self._current_release.version}")
        self._logger.info(f"ELF path: {self._current_release.elf_path}")
        self._logger.info(f"JS path: {self._current_release.js_path}")
        self._logger.info(f"Files valid: {self._current_release.files_valid}")

        if not self._current_release.files_valid:
            self._logger.error("Release files are not valid")
            self._window.show_error(
                "Invalid Release",
                "The downloaded release files are missing or invalid.\n\n"
                "Please download the release again."
            )
            return

        self._logger.info(
            f"Upload official release {self._current_release.version} "
            f"to {len(selected_dumps)} dumps"
        )

        if not self._connection_manager.is_connected:
            self._window.show_error("Error", "Not connected to FTP server.")
            return

        # Check if files already exist (overwrite confirmation)
        dumps_with_existing = self._check_existing_files(selected_dumps)
        if dumps_with_existing:
            dump_names = "\n".join([d.display_name for d in dumps_with_existing[:5]])
            if len(dumps_with_existing) > 5:
                dump_names += f"\n... and {len(dumps_with_existing) - 5} more"

            if not self._window.show_warning(
                "Overwrite Confirmation",
                f"The following dumps already have dump_runner files:\n\n"
                f"{dump_names}\n\n"
                f"Do you want to overwrite them?"
            ):
                return

        # Start the upload with official release files
        self._start_upload(
            selected_dumps,
            self._current_release.elf_path,
            self._current_release.js_path
        )

    def _check_cached_release(self) -> None:
        """Check for cached release on startup."""
        try:
            cached = self._release_downloader.get_cached_release()
            if cached and cached.files_valid:
                self._current_release = cached
                self._logger.info(f"Found cached release: {cached.version}")
                self._window.set_official_release_available(True, cached.version)
        except Exception as e:
            self._logger.warning(f"Failed to check cached release: {e}")

    def _select_file(self, title: str, filetypes: list) -> Optional[str]:
        """Open file dialog to select a file."""
        return filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            parent=self._root
        )

    def _check_existing_files(self, dumps: List[GameDump]) -> List[GameDump]:
        """Check which dumps already have dump_runner files installed."""
        from .ftp.scanner import InstallationStatus
        # Check for any installed status (OFFICIAL, EXPERIMENTAL, or UNKNOWN with files present)
        return [d for d in dumps if d.installation_status != InstallationStatus.NOT_INSTALLED]

    def _start_upload(
        self,
        dumps: List[GameDump],
        elf_path: Path,
        js_path: Path
    ) -> None:
        """Start the upload process with progress dialog."""
        self._logger.info(
            f"Starting upload of {elf_path.name} and {js_path.name} "
            f"to {len(dumps)} dumps"
        )

        # Create uploader
        self._uploader = FileUploader(self._connection_manager)

        # Create and show upload dialog
        self._upload_dialog = UploadDialog(
            self._root,
            dumps,
            on_cancel=self._handle_upload_cancel
        )

        # Run upload in background thread
        def upload_task():
            results = []
            for i, dump in enumerate(dumps):
                if self._uploader.is_cancelled:
                    # Add cancelled result for remaining dumps
                    results.append(UploadResult(
                        dump_path=dump.path,
                        success=False,
                        error_message="Upload cancelled"
                    ))
                    continue

                # Update current dump in dialog
                self._root.after(0, lambda d=dump: self._update_current_dump(d))

                # Upload to this dump
                result = self._uploader.upload_to_dump(
                    dump,
                    elf_path,
                    js_path,
                    on_progress=self._on_upload_progress
                )
                results.append(result)

                # Log per-dump result
                if result.success:
                    self._logger.info(
                        f"Upload to {dump.display_name} succeeded: "
                        f"{result.bytes_transferred} bytes in {result.duration_seconds:.1f}s"
                    )
                else:
                    self._logger.error(
                        f"Upload to {dump.display_name} failed: {result.error_message}"
                    )

                # Update dialog with result
                self._root.after(0, lambda r=result: self._add_upload_result(r))

            return results

        def on_upload_complete(task_result):
            results = task_result.result if task_result.result else []
            self._root.after(0, lambda: self._handle_upload_complete(results))

        task = ThreadedTask(upload_task, on_complete=on_upload_complete)
        task.start()

    def _update_current_dump(self, dump: GameDump) -> None:
        """Update current dump in upload dialog (main thread)."""
        if self._upload_dialog:
            self._upload_dialog.set_current_dump(dump)

    def _on_upload_progress(self, progress: UploadProgress) -> None:
        """Handle upload progress (called from background thread)."""
        # Schedule GUI update on main thread
        self._root.after(0, lambda: self._update_upload_progress(progress))

    def _update_upload_progress(self, progress: UploadProgress) -> None:
        """Update upload progress in dialog (main thread)."""
        if self._upload_dialog:
            self._upload_dialog.update_progress(progress)

    def _add_upload_result(self, result: UploadResult) -> None:
        """Add upload result to dialog (main thread)."""
        if self._upload_dialog:
            self._upload_dialog.add_result(result)

    def _handle_upload_cancel(self) -> None:
        """Handle upload cancel button."""
        self._logger.info("Upload cancelled by user")
        if self._uploader:
            self._uploader.cancel()

    def _handle_upload_complete(self, results: List[UploadResult]) -> None:
        """Handle upload completion (main thread)."""
        if not self._upload_dialog:
            return

        cancelled = self._uploader and self._uploader.is_cancelled

        # Complete the dialog
        self._upload_dialog.complete(cancelled=cancelled)

        # Log summary
        if results:
            summary = FileUploader(self._connection_manager).get_batch_summary(results)
            self._logger.info(
                f"Upload batch complete: {summary['successful']}/{summary['total']} successful, "
                f"{summary['bytes_transferred']} bytes in {summary['duration_seconds']:.1f}s"
            )

            # Show summary in status bar
            if cancelled:
                self._window.update_status(
                    f"Upload cancelled: {summary['successful']}/{summary['total']} completed"
                )
            elif summary['failed'] > 0:
                self._window.update_status(
                    f"Upload complete with {summary['failed']} failures"
                )
            else:
                self._window.update_status(
                    f"Upload complete: {summary['successful']} dumps updated"
                )

        # Refresh dump list to show updated installation status
        self.on_scan()

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
        if self._release_downloader:
            self._release_downloader.close()
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
