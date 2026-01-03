"""Mock FTP server for integration testing.

Uses pyftpdlib to create a local FTP server that simulates
the PS5 FTP directory structure.
"""

import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


class MockPS5FTPServer:
    """
    Mock FTP server that simulates PS5 directory structure.

    Usage:
        with MockPS5FTPServer(port=2121) as server:
            # Connect to localhost:2121
            # server.root_dir contains the mock filesystem
            pass
    """

    DEFAULT_USER = "testuser"
    DEFAULT_PASS = "testpass"

    def __init__(
        self,
        port: int = 2121,
        username: str = DEFAULT_USER,
        password: str = DEFAULT_PASS,
    ):
        """
        Initialize the mock FTP server.

        Args:
            port: Port to listen on
            username: FTP username
            password: FTP password
        """
        self.port = port
        self.username = username
        self.password = password

        self._server: Optional[FTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self._root_dir: Optional[Path] = None

    @property
    def root_dir(self) -> Path:
        """Root directory of the mock filesystem."""
        if self._root_dir is None:
            raise RuntimeError("Server not started")
        return self._root_dir

    @property
    def host(self) -> str:
        """Server host address."""
        return "127.0.0.1"

    def _create_ps5_structure(self) -> None:
        """Create mock PS5 directory structure."""
        root = self._root_dir

        # Create /data/homebrew/ with some game dumps
        data_homebrew = root / "data" / "homebrew"
        data_homebrew.mkdir(parents=True)

        # Create sample game dumps
        for game in ["CUSA00001", "CUSA00002", "CUSA00003"]:
            game_dir = data_homebrew / game
            game_dir.mkdir()

        # Create one dump with files already installed
        installed_game = data_homebrew / "CUSA00001"
        (installed_game / "dump_runner.elf").write_bytes(b"\x7fELF" + b"\x00" * 100)
        (installed_game / "homebrew.js").write_text("// homebrew.js")

        # Create USB paths (just the structure, fewer games)
        usb_homebrew = root / "mnt" / "usb0" / "homebrew"
        usb_homebrew.mkdir(parents=True)
        (usb_homebrew / "USB_GAME01").mkdir()

        # Create external storage path
        ext_homebrew = root / "mnt" / "ext0" / "homebrew"
        ext_homebrew.mkdir(parents=True)
        (ext_homebrew / "EXT_GAME01").mkdir()

    def add_game_dump(self, path: str, with_files: bool = False) -> Path:
        """
        Add a game dump to the mock filesystem.

        Args:
            path: FTP path (e.g., "/data/homebrew/NEWGAME")
            with_files: If True, add dump_runner files

        Returns:
            Path to the created directory
        """
        # Convert FTP path to local path
        local_path = self._root_dir / path.lstrip("/")
        local_path.mkdir(parents=True, exist_ok=True)

        if with_files:
            (local_path / "dump_runner.elf").write_bytes(b"\x7fELF" + b"\x00" * 100)
            (local_path / "homebrew.js").write_text("// homebrew.js")

        return local_path

    def start(self) -> None:
        """Start the FTP server in a background thread."""
        # Create temporary directory for mock filesystem
        self._temp_dir = tempfile.TemporaryDirectory(prefix="mock_ps5_ftp_")
        self._root_dir = Path(self._temp_dir.name)

        # Create PS5-like structure
        self._create_ps5_structure()

        # Set up authorizer
        authorizer = DummyAuthorizer()
        authorizer.add_user(
            self.username,
            self.password,
            str(self._root_dir),
            perm="elradfmw"  # Full permissions
        )

        # Set up handler
        handler = FTPHandler
        handler.authorizer = authorizer
        handler.passive_ports = range(60000, 60100)

        # Create server
        self._server = FTPServer((self.host, self.port), handler)

        # Start in background thread
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        # Give server time to start
        time.sleep(0.2)

    def stop(self) -> None:
        """Stop the FTP server and clean up."""
        if self._server:
            self._server.close_all()

        if self._temp_dir:
            self._temp_dir.cleanup()

        self._server = None
        self._thread = None
        self._temp_dir = None
        self._root_dir = None

    def __enter__(self) -> "MockPS5FTPServer":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


# Pytest fixture
import pytest

@pytest.fixture
def mock_ftp_server():
    """Pytest fixture providing a mock FTP server."""
    server = MockPS5FTPServer(port=21210)  # Use non-standard port for tests
    server.start()
    yield server
    server.stop()
