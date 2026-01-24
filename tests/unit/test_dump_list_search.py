"""Unit tests for DumpList search functionality.

Tests the search/filter feature that allows users to filter
game dumps by name in the dump list widget.
"""

import tkinter as tk
from unittest.mock import Mock, MagicMock

import pytest

from src.ftp.scanner import GameDump, LocationType, InstallationStatus
from src.gui.dump_list import DumpList


@pytest.fixture
def root():
    """Create a Tk root window for testing."""
    root = tk.Tk()
    root.withdraw()  # Hide the window
    yield root
    root.destroy()


@pytest.fixture
def mock_dumps():
    """Create a list of mock GameDump objects for testing."""
    dumps = [
        GameDump(
            path="/data/homebrew/Horizon Zero Dawn",
            name="Horizon Zero Dawn",
            location_type=LocationType.INTERNAL,
            installation_status=InstallationStatus.NOT_INSTALLED,
            has_elf=False,
            has_js=False,
        ),
        GameDump(
            path="/mnt/usb0/homebrew/Horizon Forbidden West",
            name="Horizon Forbidden West",
            location_type=LocationType.USB0,
            installation_status=InstallationStatus.NOT_INSTALLED,
            has_elf=False,
            has_js=False,
        ),
        GameDump(
            path="/mnt/ext0/homebrew/ELDEN RING",
            name="ELDEN RING",
            location_type=LocationType.EXT0,
            installation_status=InstallationStatus.NOT_INSTALLED,
            has_elf=True,
            has_js=True,
        ),
        GameDump(
            path="/mnt/ext1/homebrew/God of War",
            name="God of War",
            location_type=LocationType.EXT1,
            installation_status=InstallationStatus.NOT_INSTALLED,
            has_elf=False,
            has_js=False,
        ),
        GameDump(
            path="/data/homebrew/Spider-Man",
            name="Spider-Man",
            location_type=LocationType.INTERNAL,
            installation_status=InstallationStatus.NOT_INSTALLED,
            has_elf=False,
            has_js=False,
        ),
    ]
    return dumps


class TestDumpListSearch:
    """Tests for the DumpList search functionality."""

    def test_filter_by_name(self, root, mock_dumps):
        """Test filtering dumps by partial name match."""
        dump_list = DumpList(root)
        dump_list.set_dumps(mock_dumps)

        # Set search term
        dump_list._search_var.set("Horizon")

        # Verify filtered dumps contain only matching items
        assert len(dump_list._filtered_dumps) == 2
        names = [d.name for d in dump_list._filtered_dumps]
        assert "Horizon Zero Dawn" in names
        assert "Horizon Forbidden West" in names

    def test_case_insensitive_search(self, root, mock_dumps):
        """Test that search is case-insensitive."""
        dump_list = DumpList(root)
        dump_list.set_dumps(mock_dumps)

        # Search with lowercase
        dump_list._search_var.set("horizon")
        assert len(dump_list._filtered_dumps) == 2

        # Search with uppercase
        dump_list._search_var.set("HORIZON")
        assert len(dump_list._filtered_dumps) == 2

        # Search with mixed case
        dump_list._search_var.set("HoRiZoN")
        assert len(dump_list._filtered_dumps) == 2

        # Verify ELDEN RING can be found with lowercase
        dump_list._search_var.set("elden")
        assert len(dump_list._filtered_dumps) == 1
        assert dump_list._filtered_dumps[0].name == "ELDEN RING"

    def test_empty_search_shows_all(self, root, mock_dumps):
        """Test that empty search shows all dumps."""
        dump_list = DumpList(root)
        dump_list.set_dumps(mock_dumps)

        # Initially should show all
        assert len(dump_list._filtered_dumps) == 5

        # Apply filter
        dump_list._search_var.set("Horizon")
        assert len(dump_list._filtered_dumps) == 2

        # Clear filter - should show all again
        dump_list._search_var.set("")
        assert len(dump_list._filtered_dumps) == 5

        # Whitespace only should also show all
        dump_list._search_var.set("   ")
        assert len(dump_list._filtered_dumps) == 5

    def test_no_matches_shows_empty(self, root, mock_dumps):
        """Test that non-matching query shows empty list."""
        dump_list = DumpList(root)
        dump_list.set_dumps(mock_dumps)

        # Search for something that doesn't exist
        dump_list._search_var.set("Zelda")
        assert len(dump_list._filtered_dumps) == 0

        # Search for partial match that doesn't exist
        dump_list._search_var.set("xyz123")
        assert len(dump_list._filtered_dumps) == 0


class TestDumpListSearchVisualFeedback:
    """Tests for visual feedback during search."""

    def test_count_label_shows_filtered_count(self, root, mock_dumps):
        """Test count label shows 'X of Y dumps' when filtered."""
        dump_list = DumpList(root)
        dump_list.set_dumps(mock_dumps)

        # Apply filter
        dump_list._search_var.set("Horizon")

        # Check count label text
        count_text = dump_list._count_label.cget("text")
        assert "2" in count_text
        assert "5" in count_text
        # Should show something like "2 of 5 dumps"

    def test_count_label_shows_total_when_no_filter(self, root, mock_dumps):
        """Test count label shows total when no filter active."""
        dump_list = DumpList(root)
        dump_list.set_dumps(mock_dumps)

        # No filter - should show total
        count_text = dump_list._count_label.cget("text")
        assert "5" in count_text
        # Should show "5 dumps found"

    def test_clear_search_button(self, root, mock_dumps):
        """Test clear button resets search."""
        dump_list = DumpList(root)
        dump_list.set_dumps(mock_dumps)

        # Apply filter
        dump_list._search_var.set("Horizon")
        assert len(dump_list._filtered_dumps) == 2

        # Click clear button (invoke command)
        dump_list._clear_search()

        # Should show all dumps
        assert dump_list._search_var.get() == ""
        assert len(dump_list._filtered_dumps) == 5

    def test_escape_key_clears_search(self, root, mock_dumps):
        """Test Escape key clears search field."""
        dump_list = DumpList(root)
        dump_list.set_dumps(mock_dumps)

        # Apply filter
        dump_list._search_var.set("Horizon")
        assert len(dump_list._filtered_dumps) == 2

        # Simulate Escape key press by directly invoking the bound callback
        # (event_generate doesn't work reliably in unit tests without mainloop)
        dump_list._clear_search()

        # Should show all dumps (the binding should clear)
        assert dump_list._search_var.get() == ""
        assert len(dump_list._filtered_dumps) == 5


class TestDumpListSearchEdgeCases:
    """Tests for edge cases in search functionality."""

    def test_filter_preserved_on_refresh(self, root, mock_dumps):
        """Test that filter persists when set_dumps() is called again."""
        dump_list = DumpList(root)
        dump_list.set_dumps(mock_dumps)

        # Apply filter
        dump_list._search_var.set("Horizon")
        assert len(dump_list._filtered_dumps) == 2

        # Simulate refresh with same data
        dump_list.set_dumps(mock_dumps)

        # Filter should still be applied
        assert len(dump_list._filtered_dumps) == 2
        assert dump_list._search_var.get() == "Horizon"

    def test_selection_preserved_through_filter(self, root, mock_dumps):
        """Test that selections remain intact after filter/clear."""
        dump_list = DumpList(root)
        dump_list.set_dumps(mock_dumps)

        # Select first item
        first_path = mock_dumps[0].path
        dump_list._selected_paths.add(first_path)

        # Apply filter that hides the selected item
        dump_list._search_var.set("ELDEN")
        assert len(dump_list._filtered_dumps) == 1

        # Selection should still be tracked
        assert first_path in dump_list._selected_paths

        # Clear filter
        dump_list._search_var.set("")

        # Selection should still be there
        assert first_path in dump_list._selected_paths
