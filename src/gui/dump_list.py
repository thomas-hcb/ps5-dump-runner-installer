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
        self._filtered_dumps: List[GameDump] = []
        self._selected_paths: Set[str] = set()
        self._check_vars: dict[str, tk.BooleanVar] = {}
        self._search_var = tk.StringVar()
        self._search_placeholder = "Search for game name..."
        self._placeholder_active = True  # Initialize before trace
        self._search_var.trace_add("write", self._on_search_changed)

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

        # Search widgets
        self._create_search_widgets()

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

    def _create_search_widgets(self) -> None:
        """Create search entry and clear button."""
        # Search entry
        self._search_entry = ttk.Entry(
            self._toolbar,
            textvariable=self._search_var,
            width=25
        )

        # Set initial placeholder
        self._search_entry.insert(0, self._search_placeholder)
        self._search_entry.configure(foreground="gray")

        # Bind focus events for placeholder behavior
        self._search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self._search_entry.bind("<FocusOut>", self._on_search_focus_out)

        # Clear button
        self._clear_search_btn = ttk.Button(
            self._toolbar,
            text="✕",
            width=3,
            command=self._clear_search
        )

        # Bind Escape key to clear search
        self._search_entry.bind("<Escape>", lambda e: self._clear_search())

    def _layout_widgets(self) -> None:
        """Arrange widgets."""
        # Toolbar
        self._toolbar.pack(fill=tk.X, padx=5, pady=5)
        self._select_all_btn.pack(side=tk.LEFT, padx=2)
        self._select_none_btn.pack(side=tk.LEFT, padx=2)
        self._refresh_btn.pack(side=tk.LEFT, padx=10)

        # Search widgets
        self._search_entry.pack(side=tk.LEFT, padx=(10, 2))
        self._clear_search_btn.pack(side=tk.LEFT, padx=(0, 10))

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
        # Store full dump list
        self._dumps = dumps

        # Clear selection and checkbox state
        self._selected_paths.clear()
        self._check_vars.clear()

        # Initialize checkbox variables for all dumps
        for dump in dumps:
            var = tk.BooleanVar(value=False)
            self._check_vars[dump.path] = var

        # Apply current filter and update display
        self._apply_filter()
        self._update_display()

        # Notify that selection was cleared
        self._notify_selection_changed()

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

    def _clear_search(self) -> None:
        """Clear search field and show all dumps."""
        self._search_var.set("")
        self._placeholder_active = False  # Treat as cleared, not placeholder

    def _on_search_focus_in(self, event: tk.Event) -> None:
        """Handle focus in - remove placeholder."""
        if self._placeholder_active:
            self._search_entry.delete(0, tk.END)
            self._search_entry.configure(foreground="black")
            self._placeholder_active = False

    def _on_search_focus_out(self, event: tk.Event) -> None:
        """Handle focus out - restore placeholder if empty."""
        if not self._search_var.get().strip():
            self._show_placeholder()

    def _show_placeholder(self) -> None:
        """Show placeholder text in search entry."""
        self._search_var.set("")
        self._search_entry.delete(0, tk.END)
        self._search_entry.insert(0, self._search_placeholder)
        self._search_entry.configure(foreground="gray")
        self._placeholder_active = True

    def _apply_filter(self) -> None:
        """Filter dumps by current search term."""
        query = self._search_var.get().strip().lower()

        # Ignore placeholder text
        if self._placeholder_active or not query:
            # Empty search shows all
            self._filtered_dumps = self._dumps.copy()
        else:
            # Case-insensitive substring match on dump name
            self._filtered_dumps = [
                dump for dump in self._dumps
                if query in dump.name.lower()
            ]

    def _on_search_changed(self, *args) -> None:
        """Callback when search text changes."""
        # Guard against callback during initialization (before _tree exists)
        if not hasattr(self, '_tree'):
            return

        # If value changed from placeholder, deactivate placeholder mode
        current_value = self._search_var.get()
        if current_value and current_value != self._search_placeholder:
            self._placeholder_active = False

        self._apply_filter()
        self._update_display()

    def _update_display(self) -> None:
        """Refresh treeview with filtered dumps."""
        # Clear existing items
        children = self._tree.get_children()
        if children:
            self._tree.delete(*children)

        # Add filtered items
        for dump in self._filtered_dumps:
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
                # Granular USB devices
                LocationType.USB0: "USB0",
                LocationType.USB1: "USB1",
                LocationType.USB2: "USB2",
                LocationType.USB3: "USB3",
                LocationType.USB4: "USB4",
                LocationType.USB5: "USB5",
                LocationType.USB6: "USB6",
                LocationType.USB7: "USB7",
                # Granular external devices
                LocationType.EXT0: "EXT0",
                LocationType.EXT1: "EXT1",
                # Legacy/fallback types
                LocationType.USB: "USB",
                LocationType.EXTERNAL: "External",
                LocationType.LOCAL: "Local",
                LocationType.UNKNOWN: "Unknown",
            }.get(dump.location_type, "Unknown")

            # Determine checkbox text based on selection state
            checkbox_text = "☑" if dump.path in self._selected_paths else "☐"

            # Insert item
            self._tree.insert(
                "",
                tk.END,
                iid=dump.path,
                text=checkbox_text,
                values=(dump.name, location, status),
                tags=(dump.location_type.value,)
            )

        # Update count label
        self._update_count_label()

        # Configure tag colors
        self._configure_tag_colors()

    def _configure_tag_colors(self) -> None:
        """Configure tag colors for different location types."""
        self._tree.tag_configure("internal", foreground="#1e40af")
        # Granular USB devices (all green shades)
        self._tree.tag_configure("usb0", foreground="#047857")
        self._tree.tag_configure("usb1", foreground="#047857")
        self._tree.tag_configure("usb2", foreground="#047857")
        self._tree.tag_configure("usb3", foreground="#047857")
        self._tree.tag_configure("usb4", foreground="#047857")
        self._tree.tag_configure("usb5", foreground="#047857")
        self._tree.tag_configure("usb6", foreground="#047857")
        self._tree.tag_configure("usb7", foreground="#047857")
        # Granular external devices (different purple/magenta shades)
        self._tree.tag_configure("ext0", foreground="#c026d3")  # Fuchsia/magenta
        self._tree.tag_configure("ext1", foreground="#7c3aed")  # Purple
        # Legacy/fallback types
        self._tree.tag_configure("usb", foreground="#047857")
        self._tree.tag_configure("external", foreground="#7c3aed")
        self._tree.tag_configure("local", foreground="#dc2626")

    def _update_count_label(self) -> None:
        """Update count label with filter-aware text."""
        total = len(self._dumps)
        filtered = len(self._filtered_dumps)

        if filtered == total or total == 0:
            # No active filter
            self._count_label.config(text=f"{total} dumps found")
        else:
            # Active filter showing subset
            self._count_label.config(text=f"{filtered} of {total} dumps")
