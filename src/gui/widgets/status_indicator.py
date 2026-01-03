"""Status indicator widget for connection status.

Displays connected/disconnected status with color coding.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from src.ftp.connection import ConnectionState


class StatusIndicator(ttk.Frame):
    """
    Visual indicator for FTP connection status.

    Displays a colored circle and text indicating the current
    connection state (Connected, Disconnected, Connecting, Error).
    """

    # Status colors
    COLORS = {
        ConnectionState.CONNECTED: "#22c55e",      # Green
        ConnectionState.DISCONNECTED: "#6b7280",   # Gray
        ConnectionState.CONNECTING: "#f59e0b",     # Yellow/Orange
        ConnectionState.ERROR: "#ef4444",          # Red
    }

    # Status text
    TEXTS = {
        ConnectionState.CONNECTED: "Connected",
        ConnectionState.DISCONNECTED: "Disconnected",
        ConnectionState.CONNECTING: "Connecting...",
        ConnectionState.ERROR: "Error",
    }

    def __init__(self, parent: tk.Widget, **kwargs):
        """
        Initialize the status indicator.

        Args:
            parent: Parent widget
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._state = ConnectionState.DISCONNECTED

        # Create canvas for status circle
        # Use system default background color
        self._canvas = tk.Canvas(
            self,
            width=16,
            height=16,
            highlightthickness=0,
            bg="SystemButtonFace"  # Windows default background
        )
        self._canvas.pack(side=tk.LEFT, padx=(0, 5))

        # Draw status circle
        self._circle = self._canvas.create_oval(
            2, 2, 14, 14,
            fill=self.COLORS[self._state],
            outline=""
        )

        # Status text label
        self._label = ttk.Label(self, text=self.TEXTS[self._state])
        self._label.pack(side=tk.LEFT)

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    def set_state(self, state: ConnectionState) -> None:
        """
        Update the displayed connection state.

        Args:
            state: New connection state
        """
        self._state = state
        self._canvas.itemconfig(self._circle, fill=self.COLORS[state])
        self._label.config(text=self.TEXTS[state])

    def set_connected(self) -> None:
        """Set status to connected."""
        self.set_state(ConnectionState.CONNECTED)

    def set_disconnected(self) -> None:
        """Set status to disconnected."""
        self.set_state(ConnectionState.DISCONNECTED)

    def set_connecting(self) -> None:
        """Set status to connecting."""
        self.set_state(ConnectionState.CONNECTING)

    def set_error(self, message: Optional[str] = None) -> None:
        """
        Set status to error.

        Args:
            message: Optional error message to display
        """
        self._state = ConnectionState.ERROR
        self._canvas.itemconfig(self._circle, fill=self.COLORS[ConnectionState.ERROR])
        if message:
            self._label.config(text=f"Error: {message[:30]}")
        else:
            self._label.config(text=self.TEXTS[ConnectionState.ERROR])
