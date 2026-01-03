"""Settings dialog for PS5 Dump Runner FTP Installer.

Provides a dialog for managing application preferences and credentials.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from src.config.settings import AppSettings


class SettingsDialog(tk.Toplevel):
    """
    Dialog for managing application settings.

    Provides controls for:
    - FTP connection defaults (timeout, passive mode)
    - Clear saved credentials
    - Reset all settings to defaults
    """

    def __init__(
        self,
        parent: tk.Widget,
        settings: AppSettings,
        on_save: Optional[Callable[[AppSettings], None]] = None,
        on_clear_credentials: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """
        Initialize the settings dialog.

        Args:
            parent: Parent widget
            settings: Current application settings
            on_save: Callback when settings are saved
            on_clear_credentials: Callback to clear saved credentials
            **kwargs: Additional toplevel options
        """
        super().__init__(parent, **kwargs)

        self._settings = settings
        self._on_save = on_save
        self._on_clear_credentials = on_clear_credentials

        self._setup_window()
        self._create_widgets()
        self._layout_widgets()
        self._load_values()

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._handle_cancel)

    def _setup_window(self) -> None:
        """Configure the dialog window."""
        self.title("Settings")
        self.resizable(False, False)

        # Center on parent
        self.geometry("400x350")
        self.update_idletasks()

        # Center on parent window
        parent = self.master
        if parent:
            x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
            y = parent.winfo_y() + (parent.winfo_height() - 350) // 2
            self.geometry(f"+{x}+{y}")

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Main frame
        self._main_frame = ttk.Frame(self, padding=20)

        # Connection Settings Frame
        self._connection_frame = ttk.LabelFrame(
            self._main_frame,
            text="FTP Connection Settings",
            padding=10
        )

        # Timeout
        self._timeout_label = ttk.Label(
            self._connection_frame,
            text="Connection Timeout (seconds):"
        )
        self._timeout_var = tk.StringVar()
        self._timeout_spinbox = ttk.Spinbox(
            self._connection_frame,
            from_=5,
            to=120,
            width=10,
            textvariable=self._timeout_var
        )

        # Passive Mode
        self._passive_var = tk.BooleanVar()
        self._passive_check = ttk.Checkbutton(
            self._connection_frame,
            text="Use Passive Mode (recommended)",
            variable=self._passive_var
        )

        # Auto Check Updates
        self._auto_update_var = tk.BooleanVar()
        self._auto_update_check = ttk.Checkbutton(
            self._connection_frame,
            text="Automatically check for updates",
            variable=self._auto_update_var
        )

        # Credentials Frame
        self._credentials_frame = ttk.LabelFrame(
            self._main_frame,
            text="Saved Credentials",
            padding=10
        )

        self._credentials_info = ttk.Label(
            self._credentials_frame,
            text="Saved passwords are stored securely in your\nsystem's credential manager.",
            justify=tk.LEFT
        )

        self._clear_credentials_btn = ttk.Button(
            self._credentials_frame,
            text="Clear Saved Credentials",
            command=self._handle_clear_credentials
        )

        # Reset Frame
        self._reset_frame = ttk.LabelFrame(
            self._main_frame,
            text="Reset",
            padding=10
        )

        self._reset_info = ttk.Label(
            self._reset_frame,
            text="Reset all settings to their default values.\nThis will not clear saved credentials.",
            justify=tk.LEFT
        )

        self._reset_btn = ttk.Button(
            self._reset_frame,
            text="Reset to Defaults",
            command=self._handle_reset
        )

        # Button frame
        self._button_frame = ttk.Frame(self._main_frame)

        self._save_btn = ttk.Button(
            self._button_frame,
            text="Save",
            command=self._handle_save,
            width=10
        )

        self._cancel_btn = ttk.Button(
            self._button_frame,
            text="Cancel",
            command=self._handle_cancel,
            width=10
        )

    def _layout_widgets(self) -> None:
        """Arrange widgets in the dialog."""
        self._main_frame.pack(fill=tk.BOTH, expand=True)

        # Connection Settings
        self._connection_frame.pack(fill=tk.X, pady=(0, 10))

        self._timeout_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        self._timeout_spinbox.grid(row=0, column=1, sticky=tk.W, padx=10, pady=2)
        self._passive_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        self._auto_update_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Credentials
        self._credentials_frame.pack(fill=tk.X, pady=(0, 10))
        self._credentials_info.pack(anchor=tk.W, pady=(0, 5))
        self._clear_credentials_btn.pack(anchor=tk.W)

        # Reset
        self._reset_frame.pack(fill=tk.X, pady=(0, 10))
        self._reset_info.pack(anchor=tk.W, pady=(0, 5))
        self._reset_btn.pack(anchor=tk.W)

        # Buttons
        self._button_frame.pack(fill=tk.X, pady=(10, 0))
        self._cancel_btn.pack(side=tk.RIGHT, padx=5)
        self._save_btn.pack(side=tk.RIGHT, padx=5)

    def _load_values(self) -> None:
        """Load current settings into the form."""
        self._timeout_var.set(str(self._settings.timeout))
        self._passive_var.set(self._settings.passive_mode)
        self._auto_update_var.set(self._settings.auto_check_updates)

    def _handle_save(self) -> None:
        """Handle Save button click."""
        try:
            # Validate timeout
            timeout = int(self._timeout_var.get())
            if timeout < 5 or timeout > 120:
                messagebox.showerror(
                    "Invalid Value",
                    "Timeout must be between 5 and 120 seconds."
                )
                return
        except ValueError:
            messagebox.showerror(
                "Invalid Value",
                "Please enter a valid number for timeout."
            )
            return

        # Update settings
        self._settings.timeout = timeout
        self._settings.passive_mode = self._passive_var.get()
        self._settings.auto_check_updates = self._auto_update_var.get()

        # Notify callback
        if self._on_save:
            self._on_save(self._settings)

        self.destroy()

    def _handle_cancel(self) -> None:
        """Handle Cancel button or window close."""
        self.destroy()

    def _handle_clear_credentials(self) -> None:
        """Handle Clear Credentials button click."""
        if messagebox.askyesno(
            "Clear Credentials",
            "Are you sure you want to clear all saved credentials?\n\n"
            "You will need to re-enter your password next time you connect."
        ):
            if self._on_clear_credentials:
                self._on_clear_credentials()
            messagebox.showinfo(
                "Credentials Cleared",
                "Saved credentials have been cleared."
            )

    def _handle_reset(self) -> None:
        """Handle Reset to Defaults button click."""
        if messagebox.askyesno(
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\n\n"
            "This will not clear saved credentials."
        ):
            # Reset to defaults
            self._settings.timeout = 30
            self._settings.passive_mode = True
            self._settings.auto_check_updates = True

            # Reload form
            self._load_values()

            messagebox.showinfo(
                "Settings Reset",
                "Settings have been reset to defaults.\n\n"
                "Click Save to keep these changes."
            )
