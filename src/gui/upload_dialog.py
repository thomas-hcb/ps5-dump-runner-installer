"""Upload progress dialog for batch uploads.

Shows per-dump progress, overall progress, and provides cancel functionality.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional

from src.gui.widgets.progress_bar import ProgressBar
from src.ftp.scanner import GameDump
from src.ftp.uploader import UploadProgress, UploadResult


class UploadDialog(tk.Toplevel):
    """
    Dialog showing upload progress for batch operations.

    Displays:
    - Overall progress (dumps completed / total)
    - Current dump being uploaded
    - Per-file progress with speed and ETA
    - List of completed dumps with status
    - Cancel button
    """

    def __init__(
        self,
        parent: tk.Widget,
        dumps: List[GameDump],
        on_cancel: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """
        Initialize the upload dialog.

        Args:
            parent: Parent window
            dumps: List of dumps to upload to
            on_cancel: Callback when cancel is clicked
            **kwargs: Additional toplevel options
        """
        super().__init__(parent, **kwargs)

        self._dumps = dumps
        self._on_cancel = on_cancel
        self._cancelled = False
        self._completed_count = 0
        self._results: List[UploadResult] = []
        self._upload_complete = False

        self._setup_window()
        self._create_widgets()
        self._layout_widgets()

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

    def _setup_window(self) -> None:
        """Configure the dialog window."""
        self.title("Uploading Files")
        self.geometry("500x400")
        self.minsize(400, 300)
        self.resizable(True, True)

        # Center on parent
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_x() + (parent.winfo_width() - 500) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 400) // 2
        self.geometry(f"+{x}+{y}")

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._handle_cancel)

    def _create_widgets(self) -> None:
        """Create child widgets."""
        # Header frame
        self._header_frame = ttk.Frame(self)

        self._title_label = ttk.Label(
            self._header_frame,
            text="Uploading dump_runner files...",
            font=("TkDefaultFont", 10, "bold")
        )

        self._overall_var = tk.StringVar(value=f"0 / {len(self._dumps)} dumps")
        self._overall_label = ttk.Label(
            self._header_frame,
            textvariable=self._overall_var
        )

        # Overall progress bar
        self._overall_progress_var = tk.DoubleVar(value=0)
        self._overall_progress = ttk.Progressbar(
            self._header_frame,
            variable=self._overall_progress_var,
            maximum=100
        )

        # Current dump frame
        self._current_frame = ttk.LabelFrame(self, text="Current Upload")

        self._current_dump_var = tk.StringVar(value="")
        self._current_dump_label = ttk.Label(
            self._current_frame,
            textvariable=self._current_dump_var,
            font=("TkDefaultFont", 9, "bold")
        )

        self._progress_bar = ProgressBar(self._current_frame)

        # Results list frame
        self._results_frame = ttk.LabelFrame(self, text="Completed")

        # Treeview for results
        columns = ("dump", "status", "time")
        self._results_tree = ttk.Treeview(
            self._results_frame,
            columns=columns,
            show="headings",
            height=6
        )

        self._results_tree.heading("dump", text="Dump")
        self._results_tree.heading("status", text="Status")
        self._results_tree.heading("time", text="Time")

        self._results_tree.column("dump", width=200)
        self._results_tree.column("status", width=100)
        self._results_tree.column("time", width=80)

        self._results_scrollbar = ttk.Scrollbar(
            self._results_frame,
            orient=tk.VERTICAL,
            command=self._results_tree.yview
        )
        self._results_tree.configure(yscrollcommand=self._results_scrollbar.set)

        # Configure tags for status colors
        self._results_tree.tag_configure("success", foreground="#22c55e")
        self._results_tree.tag_configure("failed", foreground="#ef4444")

        # Button frame
        self._button_frame = ttk.Frame(self)

        self._cancel_btn = ttk.Button(
            self._button_frame,
            text="Cancel",
            command=self._handle_cancel
        )

        self._close_btn = ttk.Button(
            self._button_frame,
            text="Close",
            command=self._handle_close,
            state=tk.DISABLED
        )

    def _layout_widgets(self) -> None:
        """Arrange widgets in the dialog."""
        # Header
        self._header_frame.pack(fill=tk.X, padx=10, pady=10)
        self._title_label.pack(anchor=tk.W)
        self._overall_label.pack(anchor=tk.W, pady=(5, 2))
        self._overall_progress.pack(fill=tk.X, pady=2)

        # Current dump
        self._current_frame.pack(fill=tk.X, padx=10, pady=5)
        self._current_dump_label.pack(anchor=tk.W, padx=5, pady=2)
        self._progress_bar.pack(fill=tk.X, padx=5, pady=5)

        # Results list
        self._results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self._results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        self._button_frame.pack(fill=tk.X, padx=10, pady=10)
        self._cancel_btn.pack(side=tk.RIGHT, padx=5)
        self._close_btn.pack(side=tk.RIGHT, padx=5)

    def _handle_cancel(self) -> None:
        """Handle cancel button click or window close."""
        # If upload is complete, just close the dialog
        if self._upload_complete:
            self.destroy()
            return

        if self._cancelled:
            return

        self._cancelled = True
        self._cancel_btn.config(state=tk.DISABLED, text="Cancelling...")

        if self._on_cancel:
            self._on_cancel()

    def _handle_close(self) -> None:
        """Handle close button click."""
        self.destroy()

    # Public methods for controller

    def set_current_dump(self, dump: GameDump) -> None:
        """
        Set the current dump being uploaded.

        Args:
            dump: Current dump
        """
        self._current_dump_var.set(dump.display_name)

    def update_progress(self, progress: UploadProgress) -> None:
        """
        Update the current file progress.

        Args:
            progress: Upload progress info
        """
        self._progress_bar.update(
            bytes_sent=progress.bytes_sent,
            bytes_total=progress.bytes_total,
            file_name=progress.file_name
        )

    def add_result(self, result: UploadResult) -> None:
        """
        Add a completed upload result.

        Args:
            result: Upload result
        """
        self._results.append(result)
        self._completed_count += 1

        # Update overall progress
        percent = (self._completed_count / len(self._dumps)) * 100
        self._overall_progress_var.set(percent)
        self._overall_var.set(f"{self._completed_count} / {len(self._dumps)} dumps")

        # Add to results list
        dump_name = result.dump_path.split("/")[-1]
        if result.success:
            status = "Success"
            tag = "success"
        else:
            status = "Failed"
            tag = "failed"

        time_str = f"{result.duration_seconds:.1f}s"

        self._results_tree.insert(
            "",
            tk.END,
            values=(dump_name, status, time_str),
            tags=(tag,)
        )

        # Auto-scroll to bottom
        children = self._results_tree.get_children()
        if children:
            self._results_tree.see(children[-1])

    def complete(self, cancelled: bool = False) -> None:
        """
        Mark upload as complete.

        Args:
            cancelled: True if upload was cancelled
        """
        self._upload_complete = True

        if cancelled:
            self._title_label.config(text="Upload Cancelled")
        else:
            successful = sum(1 for r in self._results if r.success)
            failed = len(self._results) - successful

            if failed == 0:
                self._title_label.config(text="Upload Complete!")
            else:
                self._title_label.config(text=f"Upload Complete ({failed} failed)")

        self._progress_bar.complete()
        self._cancel_btn.config(state=tk.DISABLED)
        self._close_btn.config(state=tk.NORMAL)

        # Update overall to 100% if all done
        if not cancelled:
            self._overall_progress_var.set(100)

    def get_results(self) -> List[UploadResult]:
        """Get all upload results."""
        return self._results.copy()

    @property
    def is_cancelled(self) -> bool:
        """True if upload was cancelled."""
        return self._cancelled
