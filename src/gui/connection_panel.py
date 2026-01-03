"""Connection panel widget for FTP credentials.

Provides input fields for FTP host, port, username, and password,
along with connect/disconnect buttons.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from src.gui.widgets.status_indicator import StatusIndicator
from src.ftp.connection import ConnectionState


class ConnectionPanel(ttk.LabelFrame):
    """
    Panel for entering FTP connection credentials.

    Contains input fields for host, port, username, password,
    and connect/disconnect buttons.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_connect: Optional[Callable[[str, int, str, str], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """
        Initialize the connection panel.

        Args:
            parent: Parent widget
            on_connect: Callback when Connect is clicked (host, port, user, pass)
            on_disconnect: Callback when Disconnect is clicked
            **kwargs: Additional LabelFrame options
        """
        super().__init__(parent, text="FTP Connection", **kwargs)

        self._on_connect = on_connect
        self._on_disconnect = on_disconnect

        self._create_widgets()
        self._layout_widgets()

    def _create_widgets(self) -> None:
        """Create all child widgets."""
        # Host
        self._host_label = ttk.Label(self, text="Host:")
        self._host_var = tk.StringVar(value="")
        self._host_entry = ttk.Entry(self, textvariable=self._host_var, width=20)

        # Port
        self._port_label = ttk.Label(self, text="Port:")
        self._port_var = tk.StringVar(value="1337")
        self._port_entry = ttk.Entry(self, textvariable=self._port_var, width=8)

        # Username
        self._user_label = ttk.Label(self, text="Username:")
        self._user_var = tk.StringVar(value="anonymous")
        self._user_entry = ttk.Entry(self, textvariable=self._user_var, width=15)

        # Password
        self._pass_label = ttk.Label(self, text="Password:")
        self._pass_var = tk.StringVar(value="")
        self._pass_entry = ttk.Entry(self, textvariable=self._pass_var, width=15, show="*")

        # Buttons
        self._connect_btn = ttk.Button(
            self,
            text="Connect & Scan",
            command=self._handle_connect
        )
        self._disconnect_btn = ttk.Button(
            self,
            text="Disconnect",
            command=self._handle_disconnect,
            state=tk.DISABLED
        )

        # Status indicator
        self._status = StatusIndicator(self)

    def _layout_widgets(self) -> None:
        """Arrange widgets using grid layout."""
        # Row 0: Host and Port
        self._host_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self._host_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        self._port_label.grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self._port_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)

        # Row 1: Username and Password
        self._user_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self._user_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        self._pass_label.grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self._pass_entry.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)

        # Row 2: Buttons and Status (use grid for consistency)
        self._connect_btn.grid(row=2, column=0, padx=5, pady=10)
        self._disconnect_btn.grid(row=2, column=1, padx=5, pady=10)
        self._status.grid(row=2, column=2, columnspan=2, padx=20, pady=10, sticky=tk.W)

    def _handle_connect(self) -> None:
        """Handle Connect button click."""
        if self._on_connect:
            try:
                port = int(self._port_var.get())
            except ValueError:
                port = 1337

            self._on_connect(
                self._host_var.get().strip(),
                port,
                self._user_var.get().strip(),
                self._pass_var.get()
            )

    def _handle_disconnect(self) -> None:
        """Handle Disconnect button click."""
        if self._on_disconnect:
            self._on_disconnect()

    def set_state(self, state: ConnectionState) -> None:
        """
        Update UI based on connection state.

        Args:
            state: Current connection state
        """
        self._status.set_state(state)

        if state == ConnectionState.CONNECTED:
            self._connect_btn.config(state=tk.DISABLED)
            self._disconnect_btn.config(state=tk.NORMAL)
            self._set_inputs_enabled(False)
        elif state == ConnectionState.CONNECTING:
            self._connect_btn.config(state=tk.DISABLED)
            self._disconnect_btn.config(state=tk.DISABLED)
            self._set_inputs_enabled(False)
        else:  # DISCONNECTED or ERROR
            self._connect_btn.config(state=tk.NORMAL)
            self._disconnect_btn.config(state=tk.DISABLED)
            self._set_inputs_enabled(True)

    def _set_inputs_enabled(self, enabled: bool) -> None:
        """Enable or disable input fields."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self._host_entry.config(state=state)
        self._port_entry.config(state=state)
        self._user_entry.config(state=state)
        self._pass_entry.config(state=state)

    def set_values(
        self,
        host: str = "",
        port: int = 1337,
        username: str = "anonymous",
        password: str = ""
    ) -> None:
        """
        Pre-populate connection fields.

        Args:
            host: FTP host
            port: FTP port
            username: FTP username
            password: FTP password
        """
        self._host_var.set(host)
        self._port_var.set(str(port))
        self._user_var.set(username)
        self._pass_var.set(password)

    def get_values(self) -> tuple[str, int, str, str]:
        """
        Get current field values.

        Returns:
            Tuple of (host, port, username, password)
        """
        try:
            port = int(self._port_var.get())
        except ValueError:
            port = 1337

        return (
            self._host_var.get().strip(),
            port,
            self._user_var.get().strip(),
            self._pass_var.get()
        )

    def clear_password(self) -> None:
        """Clear the password field."""
        self._pass_var.set("")

    def focus_host(self) -> None:
        """Set focus to the host input field."""
        self._host_entry.focus_set()
