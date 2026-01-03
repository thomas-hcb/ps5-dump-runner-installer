"""Download progress dialog for GitHub releases.

Shows progress while downloading official dump_runner releases.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from src.updater.downloader import DownloadProgress


class DownloadDialog(tk.Toplevel):
    """
    Dialog showing download progress for GitHub releases.

    Displays:
    - Current file being downloaded
    - Progress bar with percentage
    - Download speed and ETA
    - Cancel button
    """

    def __init__(
        self,
        parent: tk.Widget,
        title: str = "Downloading Release",
        on_cancel: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """
        Initialize the download dialog.

        Args:
            parent: Parent widget
            title: Dialog title
            on_cancel: Callback when cancel is clicked
            on_close: Callback when dialog is closed after completion
            **kwargs: Additional toplevel options
        """
        super().__init__(parent, **kwargs)

        self._on_cancel = on_cancel
        self._on_close = on_close
        self._cancelled = False
        self._download_complete = False

        self._setup_window(title)
        self._create_widgets()
        self._layout_widgets()

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._handle_cancel)

    def _setup_window(self, title: str) -> None:
        """Configure the dialog window."""
        self.title(title)
        self.resizable(False, False)

        # Center on parent
        self.geometry("400x220")
        self.update_idletasks()

        # Center on parent window
        parent = self.master
        if parent:
            x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
            y = parent.winfo_y() + (parent.winfo_height() - 220) // 2
            self.geometry(f"+{x}+{y}")

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Main frame
        self._main_frame = ttk.Frame(self, padding=20)

        # Title label
        self._title_label = ttk.Label(
            self._main_frame,
            text="Downloading latest release...",
            font=("TkDefaultFont", 11, "bold")
        )

        # Current file label
        self._file_label = ttk.Label(
            self._main_frame,
            text="Preparing download..."
        )

        # Progress bar
        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(
            self._main_frame,
            variable=self._progress_var,
            maximum=100,
            length=350
        )

        # Progress text
        self._progress_label = ttk.Label(
            self._main_frame,
            text="0%"
        )

        # Status label (speed, etc.)
        self._status_label = ttk.Label(
            self._main_frame,
            text=""
        )

        # Button frame
        self._button_frame = ttk.Frame(self._main_frame)

        self._cancel_btn = ttk.Button(
            self._button_frame,
            text="Cancel",
            command=self._handle_cancel,
            width=10
        )

        self._close_btn = ttk.Button(
            self._button_frame,
            text="Close",
            command=self._handle_close,
            state=tk.DISABLED,
            width=10
        )

    def _layout_widgets(self) -> None:
        """Arrange widgets in the dialog."""
        self._main_frame.pack(fill=tk.BOTH, expand=True)

        self._title_label.pack(anchor=tk.W, pady=(0, 10))
        self._file_label.pack(anchor=tk.W, pady=(0, 5))
        self._progress_bar.pack(fill=tk.X, pady=5)

        # Progress and status on same line
        progress_frame = ttk.Frame(self._main_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        self._progress_label.pack(in_=progress_frame, side=tk.LEFT)
        self._status_label.pack(in_=progress_frame, side=tk.RIGHT)

        self._button_frame.pack(fill=tk.X, pady=(10, 0))
        self._cancel_btn.pack(side=tk.RIGHT, padx=5)
        self._close_btn.pack(side=tk.RIGHT, padx=5)

    def _handle_cancel(self) -> None:
        """Handle cancel button or window close."""
        if self._download_complete:
            self._handle_close()
            return

        if self._cancelled:
            return

        self._cancelled = True
        self._cancel_btn.config(state=tk.DISABLED, text="Cancelling...")

        if self._on_cancel:
            self._on_cancel()

    def _handle_close(self) -> None:
        """Handle close button click."""
        if self._on_close:
            self._on_close()
        self.destroy()

    def update_progress(self, progress: DownloadProgress) -> None:
        """
        Update the progress display.

        Args:
            progress: DownloadProgress with current status
        """
        if self._cancelled:
            return

        # Update file label
        self._file_label.config(
            text=f"Downloading: {progress.asset_name} ({progress.current_file}/{progress.total_files})"
        )

        # Update progress bar (use overall percentage)
        self._progress_var.set(progress.overall_percentage)

        # Update progress text
        self._progress_label.config(text=f"{progress.overall_percentage:.1f}%")

        # Update status with size info
        if progress.total_bytes > 0:
            downloaded_kb = progress.bytes_downloaded / 1024
            total_kb = progress.total_bytes / 1024
            if total_kb > 1024:
                downloaded_mb = downloaded_kb / 1024
                total_mb = total_kb / 1024
                self._status_label.config(text=f"{downloaded_mb:.1f} / {total_mb:.1f} MB")
            else:
                self._status_label.config(text=f"{downloaded_kb:.0f} / {total_kb:.0f} KB")

        self.update_idletasks()

    def complete(self, success: bool = True, message: str = "") -> None:
        """
        Mark download as complete.

        Args:
            success: True if download succeeded
            message: Optional completion message
        """
        self._download_complete = True

        if success:
            self._title_label.config(text="Download Complete!")
            self._file_label.config(text=message or "Files downloaded successfully")
            self._progress_var.set(100)
            self._progress_label.config(text="100%")
        else:
            self._title_label.config(text="Download Failed")
            self._file_label.config(text=message or "Download was cancelled or failed")

        self._cancel_btn.pack_forget()
        self._close_btn.config(state=tk.NORMAL)
        self._close_btn.focus_set()

    @property
    def is_cancelled(self) -> bool:
        """True if download was cancelled."""
        return self._cancelled
