"""Main application window for PS5 Dump Runner FTP Installer.

Provides the primary UI with connection panel, dump list, and status bar.
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, List, Optional, Protocol
from pathlib import Path

from src.gui.connection_panel import ConnectionPanel
from src.gui.dump_list import DumpList
from src.gui.upload_dialog import UploadDialog
from src.ftp.scanner import GameDump
from src.ftp.connection import ConnectionState
from src.ftp.uploader import UploadProgress, UploadResult
from src.core.scanner_base import ScanMode
from src.local import get_available_volumes
from src.local.volumes import VolumeInfo

logger = logging.getLogger("ps5_dump_runner.main_window")


class AppCallbacks(Protocol):
    """Protocol defining callbacks from GUI to application logic."""

    def on_connect(self, host: str, port: int, username: str, password: str) -> None:
        """Called when user clicks Connect."""
        ...

    def on_disconnect(self) -> None:
        """Called when user clicks Disconnect."""
        ...

    def on_scan(self) -> None:
        """Called when user requests dump scan."""
        ...

    def on_upload(self, selected_dumps: List[GameDump]) -> None:
        """Called when user wants to upload to selected dumps."""
        ...

    def on_download_release(self) -> None:
        """Called when user wants to download latest official release."""
        ...

    def on_upload_official(self, selected_dumps: List[GameDump]) -> None:
        """Called when user wants to upload official release to selected dumps."""
        ...

    def on_show_settings(self) -> None:
        """Called when user opens settings dialog."""
        ...

    def on_scan_local(self, volume_path: Path) -> None:
        """Called when user requests local volume scan."""
        ...

    def on_upload_local(self, selected_dumps: List[GameDump]) -> None:
        """Called when user wants to upload to local dumps."""
        ...

    def on_upload_official_local(self, selected_dumps: List[GameDump]) -> None:
        """Called when user wants to upload official release to local dumps."""
        ...

    def on_clear_credentials(self) -> None:
        """Called when user clears saved credentials."""
        ...


class MainWindow:
    """
    Main application window.

    Provides the primary user interface with:
    - Connection panel for FTP credentials
    - Dump list showing discovered game dumps
    - Upload button for batch operations
    - Status bar for messages
    """

    APP_VERSION = "1.1.0"
    AUTHOR_NAME = "Thomas H"
    AUTHOR_TWITTER = "https://x.com/thomas_hcb"
    AUTHOR_GITHUB = "https://github.com/thomas-hcb"
    WINDOW_TITLE = f"PS5 Dump Runner Installer v{APP_VERSION} - by {AUTHOR_NAME} ({AUTHOR_TWITTER})"
    DEFAULT_WIDTH = 800
    DEFAULT_HEIGHT = 600

    def __init__(self, root: tk.Tk, callbacks: Optional[AppCallbacks] = None):
        """
        Initialize the main window.

        Args:
            root: Tkinter root window
            callbacks: Application callbacks for handling user actions
        """
        self._root = root
        self._callbacks = callbacks
        self._available_volumes: List[VolumeInfo] = []

        self._setup_window()
        self._create_menu()
        self._create_widgets()
        self._layout_widgets()

    def _setup_window(self) -> None:
        """Configure the main window."""
        self._root.title(self.WINDOW_TITLE)
        self._root.geometry(f"{self.DEFAULT_WIDTH}x{self.DEFAULT_HEIGHT}")
        self._root.minsize(600, 400)

        # Configure grid weights for resizing
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(1, weight=1)

    def _create_menu(self) -> None:
        """Create the menu bar."""
        self._menubar = tk.Menu(self._root)
        self._root.config(menu=self._menubar)

        # File menu
        file_menu = tk.Menu(self._menubar, tearoff=0)
        self._menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings...", command=self._show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit)

        # Author menu
        author_menu = tk.Menu(self._menubar, tearoff=0)
        self._menubar.add_cascade(label="Author", menu=author_menu)
        author_menu.add_command(label="About Me", command=self._show_about_me)

        # Help menu
        help_menu = tk.Menu(self._menubar, tearoff=0)
        self._menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_widgets(self) -> None:
        """Create all child widgets."""
        # Mode selector frame
        self._mode_frame = ttk.LabelFrame(self._root, text="Mode")
        self._scan_mode = tk.StringVar(value=ScanMode.FTP.value)
        self._ftp_radio = ttk.Radiobutton(
            self._mode_frame,
            text="FTP Connection",
            variable=self._scan_mode,
            value=ScanMode.FTP.value,
            command=self._on_mode_change
        )
        self._local_radio = ttk.Radiobutton(
            self._mode_frame,
            text="Local Drive",
            variable=self._scan_mode,
            value=ScanMode.LOCAL.value,
            command=self._on_mode_change
        )

        # Connection panel (for FTP mode)
        self._connection_panel = ConnectionPanel(
            self._root,
            on_connect=self._handle_connect,
            on_disconnect=self._handle_disconnect
        )

        # Volume selector frame (for Local mode)
        self._volume_frame = ttk.LabelFrame(self._root, text="Volume Selection")

        # Warning label
        self._volume_warning = ttk.Label(
            self._volume_frame,
            text="⚠ Choose the Removable USB Drive that will be plugged into your PS5",
            foreground="#dc2626",
            font=("TkDefaultFont", 9, "bold")
        )

        # Controls frame for label, combo, and button
        self._volume_controls_frame = ttk.Frame(self._volume_frame)

        self._volume_label = ttk.Label(self._volume_controls_frame, text="Select Drive:")
        self._volume_var = tk.StringVar()
        self._volume_combo = ttk.Combobox(
            self._volume_controls_frame,
            textvariable=self._volume_var,
            state="readonly",
            width=50
        )
        self._refresh_volumes_btn = ttk.Button(
            self._volume_controls_frame,
            text="Refresh",
            command=self._refresh_volumes
        )

        # Main content frame
        self._content_frame = ttk.Frame(self._root)

        # Dump list
        self._dump_list = DumpList(
            self._content_frame,
            on_selection_changed=self._handle_selection_changed
        )

        # Button panel
        self._button_panel = ttk.Frame(self._content_frame)

        self._upload_official_btn = ttk.Button(
            self._button_panel,
            text="Upload Downloaded Files",
            command=self._handle_upload_official,
            state=tk.DISABLED
        )
        self._upload_custom_btn = ttk.Button(
            self._button_panel,
            text="Upload Custom Files...",
            command=self._handle_upload,
            state=tk.DISABLED
        )
        self._download_btn = ttk.Button(
            self._button_panel,
            text="Download from GitHub",
            command=self._handle_download_release
        )
        self._scan_btn = ttk.Button(
            self._button_panel,
            text="Scan for Dumps",
            command=self._handle_scan,
            state=tk.DISABLED
        )

        self._selected_label = ttk.Label(
            self._button_panel,
            text="0 selected"
        )

        # Track if official release is available
        self._has_official_release = False
        self._official_version = ""

        # Status bar
        self._status_frame = ttk.Frame(self._root)
        self._status_var = tk.StringVar(value="Ready")
        self._status_label = ttk.Label(
            self._status_frame,
            textvariable=self._status_var,
            anchor=tk.W
        )

    def _layout_widgets(self) -> None:
        """Arrange widgets in the window."""
        # Mode selector at top
        self._mode_frame.pack(fill=tk.X, padx=10, pady=5)
        self._ftp_radio.pack(side=tk.LEFT, padx=10, pady=5)
        self._local_radio.pack(side=tk.LEFT, padx=10, pady=5)

        # Connection panel (initially visible for FTP mode)
        self._connection_panel.pack(fill=tk.X, padx=10, pady=5)

        # Volume selector frame (initially hidden)
        # Layout widgets inside volume frame
        self._volume_warning.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(5, 10))

        # Pack the controls frame that was created in _create_widgets
        self._volume_controls_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0, 5))

        # Pack controls into the controls frame
        self._volume_label.pack(side=tk.LEFT, padx=(0, 5))
        self._volume_combo.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        self._refresh_volumes_btn.pack(side=tk.LEFT)

        # Main content in middle (expandable)
        self._content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Dump list
        self._dump_list.pack(fill=tk.BOTH, expand=True)

        # Button panel
        self._button_panel.pack(fill=tk.X, pady=5)
        self._scan_btn.pack(side=tk.LEFT, padx=5)
        self._download_btn.pack(side=tk.LEFT, padx=5)
        self._upload_official_btn.pack(side=tk.LEFT, padx=5)
        self._upload_custom_btn.pack(side=tk.LEFT, padx=5)
        self._selected_label.pack(side=tk.RIGHT, padx=10)

        # Status bar at bottom
        self._status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Separator(self._status_frame, orient=tk.HORIZONTAL).pack(fill=tk.X)
        self._status_label.pack(fill=tk.X, padx=5, pady=2)

        # Set refresh callback
        self._dump_list.set_refresh_callback(self._handle_scan)

        # Initialize volumes
        self._refresh_volumes()

    def _on_mode_change(self) -> None:
        """Handle mode change between FTP and Local Drive."""
        mode = ScanMode(self._scan_mode.get())

        if mode == ScanMode.FTP:
            # Show connection panel, hide volume selector
            self._volume_frame.pack_forget()
            self._connection_panel.pack(fill=tk.X, padx=10, pady=5, after=self._mode_frame)

            # Update scan button state based on connection
            # (handled by set_connection_state)
            self.update_status("Switched to FTP mode")
        else:  # LOCAL
            # Hide connection panel, show volume selector
            self._connection_panel.pack_forget()
            self._volume_frame.pack(fill=tk.X, padx=10, pady=5, after=self._mode_frame)

            # Enable scan button in local mode if volume is selected
            if self._volume_var.get():
                self._scan_btn.config(state=tk.NORMAL)
            else:
                self._scan_btn.config(state=tk.DISABLED)

            self.update_status("Switched to Local Drive mode")

    def _refresh_volumes(self) -> None:
        """Refresh available volumes list."""
        try:
            volumes = get_available_volumes()
            self._available_volumes = volumes

            # Create display strings with USB indicator for removable drives
            volume_strings = []
            for vol in volumes:
                if vol.is_removable:
                    display = f"[USB] {vol.label}"
                else:
                    display = vol.label
                volume_strings.append(display)

            self._volume_combo['values'] = volume_strings

            # Select first removable volume if available, otherwise first volume
            removable_idx = next((i for i, v in enumerate(volumes) if v.is_removable), None)
            if removable_idx is not None:
                self._volume_combo.current(removable_idx)
            elif volume_strings:
                self._volume_combo.current(0)

            # Enable scan button if in local mode and volume is selected
            if volume_strings and ScanMode(self._scan_mode.get()) == ScanMode.LOCAL:
                self._scan_btn.config(state=tk.NORMAL)
            elif ScanMode(self._scan_mode.get()) == ScanMode.LOCAL:
                self._volume_var.set("")
                self._scan_btn.config(state=tk.DISABLED)

            logger.debug(f"Found {len(volumes)} volumes: {volume_strings}")
        except Exception as e:
            logger.error(f"Error refreshing volumes: {e}")
            self.show_error("Volume Error", f"Failed to detect volumes:\n{e}")

    def _handle_connect(self, host: str, port: int, username: str, password: str) -> None:
        """Handle Connect button click."""
        if self._callbacks:
            self._callbacks.on_connect(host, port, username, password)

    def _handle_disconnect(self) -> None:
        """Handle Disconnect button click."""
        if self._callbacks:
            self._callbacks.on_disconnect()

    def _handle_scan(self) -> None:
        """Handle Scan button click."""
        if not self._callbacks:
            return

        mode = ScanMode(self._scan_mode.get())
        if mode == ScanMode.FTP:
            self._callbacks.on_scan()
        else:  # LOCAL
            # Get the selected volume from the combobox index
            selected_idx = self._volume_combo.current()
            if selected_idx < 0 or selected_idx >= len(self._available_volumes):
                messagebox.showwarning(
                    "No Volume Selected",
                    "Please select a volume to scan."
                )
                return
            volume_info = self._available_volumes[selected_idx]
            self._callbacks.on_scan_local(volume_info.path)

    def _handle_upload(self) -> None:
        """Handle Upload Custom button click."""
        selected = self._dump_list.get_selected_dumps()
        if not selected:
            messagebox.showwarning(
                "No Selection",
                "Please select at least one dump to upload to."
            )
            return

        if not self._callbacks:
            return

        mode = ScanMode(self._scan_mode.get())
        if mode == ScanMode.FTP:
            self._callbacks.on_upload(selected)
        else:  # LOCAL
            self._callbacks.on_upload_local(selected)

    def _handle_upload_official(self) -> None:
        """Handle Upload Official button click."""
        selected = self._dump_list.get_selected_dumps()
        if not selected:
            messagebox.showwarning(
                "No Selection",
                "Please select at least one dump to upload to."
            )
            return

        if not self._callbacks:
            return

        mode = ScanMode(self._scan_mode.get())
        if mode == ScanMode.FTP:
            self._callbacks.on_upload_official(selected)
        else:  # LOCAL
            self._callbacks.on_upload_official_local(selected)

    def _handle_download_release(self) -> None:
        """Handle Download Latest Release button/menu click."""
        if self._callbacks:
            self._callbacks.on_download_release()

    def _handle_selection_changed(self, selected: List[GameDump]) -> None:
        """Handle selection change in dump list."""
        count = len(selected)
        self._selected_label.config(text=f"{count} selected")

        # Enable/disable upload buttons based on selection and available release
        if count > 0:
            self._upload_custom_btn.config(state=tk.NORMAL)
            if self._has_official_release:
                self._upload_official_btn.config(state=tk.NORMAL)
        else:
            self._upload_custom_btn.config(state=tk.DISABLED)
            self._upload_official_btn.config(state=tk.DISABLED)

    def _show_settings(self) -> None:
        """Show settings dialog."""
        if self._callbacks:
            self._callbacks.on_show_settings()

    def _show_about(self) -> None:
        """Show about dialog."""
        messagebox.showinfo(
            "About",
            "PS5 Dump Runner Installer\n\n"
            "Batch upload dump_runner files to PS5 game dumps via FTP.\n\n"
            "https://github.com/EchoStretch/dump_runner"
        )

    def _show_about_me(self) -> None:
        """Show about me (author) dialog."""
        messagebox.showinfo(
            "About Me",
            f"Author: {self.AUTHOR_NAME}\n\n"
            f"Twitter/X: {self.AUTHOR_TWITTER}\n\n"
            f"GitHub: {self.AUTHOR_GITHUB}"
        )

    def _on_exit(self) -> None:
        """Handle exit request."""
        self._root.quit()

    # Public methods for controller

    def set_connection_state(self, state: ConnectionState) -> None:
        """
        Update UI based on connection state.

        Args:
            state: Current connection state
        """
        self._connection_panel.set_state(state)

        if state == ConnectionState.CONNECTED:
            self._scan_btn.config(state=tk.NORMAL)
            self.update_status("Connected to PS5")
        else:
            self._scan_btn.config(state=tk.DISABLED)
            self._upload_custom_btn.config(state=tk.DISABLED)
            self._upload_official_btn.config(state=tk.DISABLED)
            self._dump_list.clear()

            if state == ConnectionState.DISCONNECTED:
                self.update_status("Disconnected")
            elif state == ConnectionState.ERROR:
                self.update_status("Connection error")

    def set_dumps(self, dumps: List[GameDump]) -> None:
        """
        Update the dump list.

        Args:
            dumps: List of discovered game dumps
        """
        self._dump_list.set_dumps(dumps)
        self.update_status(f"Found {len(dumps)} game dumps")

    def set_connection_values(
        self,
        host: str = "",
        port: int = 1337,
        username: str = "anonymous",
        password: str = ""
    ) -> None:
        """Pre-populate connection fields with saved values."""
        self._connection_panel.set_values(host, port, username, password)

    def clear_password(self) -> None:
        """Clear the password field."""
        self._connection_panel.clear_password()

    def update_status(self, message: str) -> None:
        """
        Update status bar message.

        Args:
            message: Status message to display
        """
        self._status_var.set(message)

    def show_error(self, title: str, message: str) -> None:
        """
        Display error dialog.

        Args:
            title: Error dialog title
            message: Error message
        """
        messagebox.showerror(title, message)

    def show_warning(self, title: str, message: str) -> bool:
        """
        Display warning with OK/Cancel.

        Args:
            title: Warning dialog title
            message: Warning message

        Returns:
            True if user clicked OK
        """
        return messagebox.askokcancel(title, message)

    def show_info(self, title: str, message: str) -> None:
        """
        Display info dialog.

        Args:
            title: Info dialog title
            message: Info message
        """
        messagebox.showinfo(title, message)

    def set_official_release_available(self, available: bool, version: str = "") -> None:
        """
        Update UI to reflect official release availability.

        Args:
            available: True if official release files are available
            version: Version string of the available release (stored but not displayed)
        """
        self._has_official_release = available
        self._official_version = version

        if available:
            # Enable upload official if there's a selection
            if self._dump_list.get_selected_count() > 0:
                self._upload_official_btn.config(state=tk.NORMAL)
        else:
            self._upload_official_btn.config(state=tk.DISABLED)

    def get_scan_mode(self) -> ScanMode:
        """
        Get the current scan mode.

        Returns:
            Current scan mode (FTP or LOCAL)
        """
        return ScanMode(self._scan_mode.get())

    def get_selected_volume(self) -> Optional[Path]:
        """
        Get the currently selected volume path.

        Returns:
            Path to selected volume, or None if no volume selected
        """
        selected_idx = self._volume_combo.current()
        if selected_idx < 0 or selected_idx >= len(self._available_volumes):
            return None
        return self._available_volumes[selected_idx].path

    def run(self) -> None:
        """Start the main event loop."""
        self._root.mainloop()
