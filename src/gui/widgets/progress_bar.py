"""Progress bar widget with speed and ETA display.

Provides a progress bar with additional information like
transfer speed and estimated time remaining.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
import time


class ProgressBar(ttk.Frame):
    """
    Progress bar widget with speed and ETA display.

    Shows:
    - Progress bar (percentage)
    - Current file name
    - Transfer speed (KB/s or MB/s)
    - Estimated time remaining
    """

    def __init__(self, parent: tk.Widget, **kwargs):
        """
        Initialize the progress bar.

        Args:
            parent: Parent widget
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._bytes_total = 0
        self._bytes_sent = 0
        self._start_time: Optional[float] = None
        self._last_update_time: Optional[float] = None
        self._last_bytes: int = 0

        self._create_widgets()
        self._layout_widgets()

    def _create_widgets(self) -> None:
        """Create child widgets."""
        # File name label
        self._file_var = tk.StringVar(value="")
        self._file_label = ttk.Label(
            self,
            textvariable=self._file_var,
            anchor=tk.W
        )

        # Progress bar
        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(
            self,
            variable=self._progress_var,
            maximum=100,
            mode="determinate"
        )

        # Info frame for stats
        self._info_frame = ttk.Frame(self)

        # Percentage
        self._percent_var = tk.StringVar(value="0%")
        self._percent_label = ttk.Label(
            self._info_frame,
            textvariable=self._percent_var,
            width=6
        )

        # Speed
        self._speed_var = tk.StringVar(value="")
        self._speed_label = ttk.Label(
            self._info_frame,
            textvariable=self._speed_var,
            width=12
        )

        # ETA
        self._eta_var = tk.StringVar(value="")
        self._eta_label = ttk.Label(
            self._info_frame,
            textvariable=self._eta_var,
            width=15
        )

        # Bytes transferred
        self._bytes_var = tk.StringVar(value="")
        self._bytes_label = ttk.Label(
            self._info_frame,
            textvariable=self._bytes_var
        )

    def _layout_widgets(self) -> None:
        """Arrange widgets."""
        self._file_label.pack(fill=tk.X, pady=(0, 2))
        self._progress_bar.pack(fill=tk.X, pady=2)

        self._info_frame.pack(fill=tk.X, pady=(2, 0))
        self._percent_label.pack(side=tk.LEFT)
        self._speed_label.pack(side=tk.LEFT, padx=10)
        self._eta_label.pack(side=tk.LEFT, padx=10)
        self._bytes_label.pack(side=tk.RIGHT)

    def start(self, total_bytes: int = 0) -> None:
        """
        Start progress tracking.

        Args:
            total_bytes: Total bytes expected
        """
        self._bytes_total = total_bytes
        self._bytes_sent = 0
        self._start_time = time.time()
        self._last_update_time = self._start_time
        self._last_bytes = 0

        self._progress_var.set(0)
        self._percent_var.set("0%")
        self._speed_var.set("")
        self._eta_var.set("")
        self._bytes_var.set(self._format_bytes(0, total_bytes))

    def update(
        self,
        bytes_sent: int,
        bytes_total: Optional[int] = None,
        file_name: Optional[str] = None
    ) -> None:
        """
        Update progress.

        Args:
            bytes_sent: Bytes transferred so far
            bytes_total: Total bytes (optional update)
            file_name: Current file name (optional)
        """
        if bytes_total is not None:
            self._bytes_total = bytes_total

        self._bytes_sent = bytes_sent

        # Update file name
        if file_name:
            self._file_var.set(file_name)

        # Calculate percentage
        if self._bytes_total > 0:
            percent = (bytes_sent / self._bytes_total) * 100
        else:
            percent = 0

        self._progress_var.set(percent)
        self._percent_var.set(f"{percent:.1f}%")

        # Calculate speed
        now = time.time()
        if self._last_update_time and now > self._last_update_time:
            elapsed = now - self._last_update_time
            bytes_diff = bytes_sent - self._last_bytes

            if elapsed > 0.1:  # Update speed every 100ms
                speed = bytes_diff / elapsed
                self._speed_var.set(self._format_speed(speed))
                self._last_update_time = now
                self._last_bytes = bytes_sent

                # Calculate ETA
                if speed > 0 and self._bytes_total > bytes_sent:
                    remaining_bytes = self._bytes_total - bytes_sent
                    eta_seconds = remaining_bytes / speed
                    self._eta_var.set(f"ETA: {self._format_time(eta_seconds)}")

        # Update bytes display
        self._bytes_var.set(self._format_bytes(bytes_sent, self._bytes_total))

    def complete(self) -> None:
        """Mark progress as complete."""
        self._progress_var.set(100)
        self._percent_var.set("100%")
        self._eta_var.set("Complete")

        if self._start_time:
            elapsed = time.time() - self._start_time
            self._speed_var.set(f"Time: {self._format_time(elapsed)}")

    def reset(self) -> None:
        """Reset progress bar to initial state."""
        self._bytes_total = 0
        self._bytes_sent = 0
        self._start_time = None

        self._progress_var.set(0)
        self._percent_var.set("0%")
        self._speed_var.set("")
        self._eta_var.set("")
        self._bytes_var.set("")
        self._file_var.set("")

    def set_file_name(self, name: str) -> None:
        """Set the current file name."""
        self._file_var.set(name)

    @staticmethod
    def _format_bytes(current: int, total: int) -> str:
        """Format bytes as human-readable string."""
        def fmt(b: int) -> str:
            if b >= 1024 * 1024:
                return f"{b / (1024 * 1024):.1f} MB"
            elif b >= 1024:
                return f"{b / 1024:.1f} KB"
            else:
                return f"{b} B"

        if total > 0:
            return f"{fmt(current)} / {fmt(total)}"
        else:
            return fmt(current)

    @staticmethod
    def _format_speed(bytes_per_sec: float) -> str:
        """Format speed as human-readable string."""
        if bytes_per_sec >= 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
        elif bytes_per_sec >= 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec:.0f} B/s"

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format time as human-readable string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"
