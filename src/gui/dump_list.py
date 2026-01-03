"""Dump list widget for displaying discovered game dumps.

Provides a Treeview-based list with checkboxes for selecting
dumps for batch operations.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional, Set

from src.ftp.scanner import GameDump, LocationType


class DumpList(ttk.Frame):
    """
    List widget for displaying and selecting game dumps.

    Uses a Treeview with checkboxes to allow users to select
    multiple dumps for batch upload operations.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_selection_changed: Optional[Callable[[List[GameDump]], None]] = None,
        **kwargs
    ):
        """
        Initialize the dump list.

        Args:
            parent: Parent widget
            on_selection_changed: Callback when selection changes
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._on_selection_changed = on_selection_changed
        self._dumps: List[GameDump] = []
        self._selected_paths: Set[str] = set()
        self._check_vars: dict[str, tk.BooleanVar] = {}

        self._create_widgets()
        self._layout_widgets()

    def _create_widgets(self) -> None:
        """Create all child widgets."""
        # Toolbar
        self._toolbar = ttk.Frame(self)

        self._select_all_btn = ttk.Button(
            self._toolbar,
            text="Select All",
            command=self._select_all
        )
        self._select_none_btn = ttk.Button(
            self._toolbar,
            text="Select None",
            command=self._select_none
        )
        self._refresh_btn = ttk.Button(
            self._toolbar,
            text="Refresh",
            command=self._request_refresh
        )

        self._count_label = ttk.Label(self._toolbar, text="0 dumps found")

        # Treeview with columns
        columns = ("name", "location", "status")
        self._tree = ttk.Treeview(
            self,
            columns=columns,
            show="tree headings",
            selectmode="extended"
        )

        # Configure columns
        self._tree.heading("#0", text="✓", anchor=tk.W)
        self._tree.heading("name", text="Game Dump", anchor=tk.W)
        self._tree.heading("location", text="Location", anchor=tk.W)
        self._tree.heading("status", text="Status", anchor=tk.W)

        self._tree.column("#0", width=40, stretch=False)
        self._tree.column("name", width=200, stretch=True)
        self._tree.column("location", width=80, stretch=False)
        self._tree.column("status", width=100, stretch=False)

        # Scrollbar
        self._scrollbar = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL,
            command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=self._scrollbar.set)

        # Bind events
        self._tree.bind("<Button-1>", self._on_click)
        self._tree.bind("<space>", self._toggle_selected)

    def _layout_widgets(self) -> None:
        """Arrange widgets."""
        # Toolbar
        self._toolbar.pack(fill=tk.X, padx=5, pady=5)
        self._select_all_btn.pack(side=tk.LEFT, padx=2)
        self._select_none_btn.pack(side=tk.LEFT, padx=2)
        self._refresh_btn.pack(side=tk.LEFT, padx=10)
        self._count_label.pack(side=tk.RIGHT, padx=5)

        # Tree and scrollbar
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def set_dumps(self, dumps: List[GameDump]) -> None:
        """
        Update the list with new dumps.

        Args:
            dumps: List of GameDump objects to display
        """
        # Clear existing items - delete all at once to avoid iteration issues
        children = self._tree.get_children()
        if children:
            self._tree.delete(*children)

        self._dumps = dumps
        self._selected_paths.clear()
        self._check_vars.clear()

        # Add new items
        for dump in dumps:
            # Determine status text based on actual file presence
            if dump.has_elf and dump.has_js:
                status = "Installed"
            elif dump.has_elf or dump.has_js:
                status = "Partial"
            else:
                status = "Not Installed"

            # Determine location text
            location = {
                LocationType.INTERNAL: "Internal",
                LocationType.USB: "USB",
                LocationType.EXTERNAL: "External",
                LocationType.UNKNOWN: "Unknown",
            }.get(dump.location_type, "Unknown")

            # Create checkbox variable
            var = tk.BooleanVar(value=False)
            self._check_vars[dump.path] = var

            # Insert item
            self._tree.insert(
                "",
                tk.END,
                iid=dump.path,
                text="☐",
                values=(dump.name, location, status),
                tags=(dump.location_type.value,)
            )

        # Update count
        self._count_label.config(text=f"{len(dumps)} dumps found")

        # Notify that selection was cleared
        self._notify_selection_changed()

        # Configure tag colors
        self._tree.tag_configure("internal", foreground="#1e40af")
        self._tree.tag_configure("usb", foreground="#047857")
        self._tree.tag_configure("external", foreground="#7c3aed")

    def _on_click(self, event: tk.Event) -> None:
        """Handle click events to toggle checkboxes."""
        region = self._tree.identify_region(event.x, event.y)
        if region == "tree":  # Clicked on checkbox column
            item = self._tree.identify_row(event.y)
            if item:
                self._toggle_item(item)

    def _toggle_selected(self, event: tk.Event) -> None:
        """Toggle checkbox for currently selected items."""
        for item in self._tree.selection():
            self._toggle_item(item)

    def _toggle_item(self, item: str) -> None:
        """Toggle the checkbox state of an item."""
        if item in self._selected_paths:
            self._selected_paths.discard(item)
            self._tree.item(item, text="☐")
            if item in self._check_vars:
                self._check_vars[item].set(False)
        else:
            self._selected_paths.add(item)
            self._tree.item(item, text="☑")
            if item in self._check_vars:
                self._check_vars[item].set(True)

        self._notify_selection_changed()

    def _select_all(self) -> None:
        """Select all dumps."""
        for item in self._tree.get_children():
            self._selected_paths.add(item)
            self._tree.item(item, text="☑")
            if item in self._check_vars:
                self._check_vars[item].set(True)

        self._notify_selection_changed()

    def _select_none(self) -> None:
        """Deselect all dumps."""
        for item in self._tree.get_children():
            self._tree.item(item, text="☐")
            if item in self._check_vars:
                self._check_vars[item].set(False)

        self._selected_paths.clear()
        self._notify_selection_changed()

    def _request_refresh(self) -> None:
        """Request a refresh of the dump list."""
        # This will be connected to the controller
        pass

    def _notify_selection_changed(self) -> None:
        """Notify listener of selection change."""
        if self._on_selection_changed:
            selected = self.get_selected_dumps()
            self._on_selection_changed(selected)

    def get_selected_dumps(self) -> List[GameDump]:
        """
        Get list of selected dumps.

        Returns:
            List of selected GameDump objects
        """
        return [d for d in self._dumps if d.path in self._selected_paths]

    def get_selected_count(self) -> int:
        """Get number of selected dumps."""
        return len(self._selected_paths)

    def clear(self) -> None:
        """Clear the dump list."""
        children = self._tree.get_children()
        if children:
            self._tree.delete(*children)

        self._dumps = []
        self._selected_paths.clear()
        self._check_vars.clear()
        self._count_label.config(text="0 dumps found")

        # Notify that selection was cleared
        self._notify_selection_changed()

    def set_refresh_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback for refresh button."""
        self._refresh_btn.config(command=callback)
