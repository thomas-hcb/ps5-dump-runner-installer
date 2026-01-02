# Module Interface Contracts

**Feature Branch**: `001-dump-runner-ftp-installer`
**Created**: 2026-01-03

This document defines the public interfaces between modules. Each module exposes a clean API that other modules depend on. Implementation details are hidden.

---

## 1. FTP Module (`src/ftp/`)

### Connection Interface

```python
# src/ftp/connection.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

@dataclass
class FTPConnectionConfig:
    host: str
    port: int = 2121
    username: str = "anonymous"
    passive_mode: bool = True
    timeout: int = 30

class FTPConnectionManager:
    """Manages FTP connection lifecycle."""

    def connect(self, config: FTPConnectionConfig, password: str) -> None:
        """
        Establish FTP connection.

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If login fails
            TimeoutError: If connection times out
        """
        ...

    def disconnect(self) -> None:
        """Close FTP connection gracefully."""
        ...

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        ...

    @property
    def is_connected(self) -> bool:
        """True if currently connected."""
        ...
```

### Scanner Interface

```python
# src/ftp/scanner.py

from dataclasses import dataclass
from enum import Enum
from typing import List

class LocationType(Enum):
    INTERNAL = "internal"
    USB = "usb"
    EXTERNAL = "external"

@dataclass
class GameDump:
    path: str
    name: str
    location_type: LocationType

class DumpScanner:
    """Scans PS5 directories for game dumps."""

    def __init__(self, connection: FTPConnectionManager):
        ...

    def scan(self) -> List[GameDump]:
        """
        Scan all configured paths for game dumps.

        Returns:
            List of discovered GameDump objects

        Raises:
            NotConnectedError: If FTP not connected
        """
        ...

    def refresh(self, dump: GameDump) -> GameDump:
        """
        Refresh status of a single dump.

        Returns:
            Updated GameDump with current status
        """
        ...
```

### Uploader Interface

```python
# src/ftp/uploader.py

from dataclasses import dataclass
from typing import Callable, List, Optional
from pathlib import Path

@dataclass
class UploadProgress:
    dump_path: str
    file_name: str
    bytes_sent: int
    bytes_total: int
    percent: float

@dataclass
class UploadResult:
    dump_path: str
    success: bool
    error_message: Optional[str] = None

ProgressCallback = Callable[[UploadProgress], None]

class FileUploader:
    """Handles file uploads to game dumps."""

    def __init__(self, connection: FTPConnectionManager):
        ...

    def upload_to_dump(
        self,
        dump: GameDump,
        elf_path: Path,
        js_path: Path,
        on_progress: Optional[ProgressCallback] = None
    ) -> UploadResult:
        """
        Upload dump_runner files to a single dump.

        Args:
            dump: Target game dump
            elf_path: Local path to dump_runner.elf
            js_path: Local path to homebrew.js
            on_progress: Optional callback for progress updates

        Returns:
            UploadResult with success/failure status
        """
        ...

    def upload_batch(
        self,
        dumps: List[GameDump],
        elf_path: Path,
        js_path: Path,
        on_progress: Optional[ProgressCallback] = None,
        on_dump_complete: Optional[Callable[[UploadResult], None]] = None
    ) -> List[UploadResult]:
        """
        Upload files to multiple dumps.

        Continues on individual failures, collects all results.
        """
        ...

    def cancel(self) -> None:
        """Cancel current upload operation."""
        ...
```

---

## 2. Updater Module (`src/updater/`)

### GitHub Client Interface

```python
# src/updater/github_client.py

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class ReleaseAsset:
    name: str
    download_url: str
    size: int

@dataclass
class GitHubRelease:
    tag_name: str
    published_at: datetime
    body: str  # Release notes
    assets: List[ReleaseAsset]

class GitHubClient:
    """Interacts with GitHub API for release information."""

    REPO = "EchoStretch/dump_runner"

    def get_latest_release(self) -> Optional[GitHubRelease]:
        """
        Fetch latest release from GitHub.

        Returns:
            GitHubRelease or None if unavailable

        Raises:
            NetworkError: If GitHub unreachable
        """
        ...

    def get_releases(self, limit: int = 10) -> List[GitHubRelease]:
        """Fetch recent releases."""
        ...
```

### Downloader Interface

```python
# src/updater/downloader.py

from pathlib import Path
from typing import Callable, Optional

DownloadProgress = Callable[[int, int], None]  # bytes_downloaded, bytes_total

class ReleaseDownloader:
    """Downloads release assets from GitHub."""

    def __init__(self, cache_dir: Path):
        ...

    def download_release(
        self,
        release: GitHubRelease,
        on_progress: Optional[DownloadProgress] = None
    ) -> tuple[Path, Path]:
        """
        Download dump_runner.elf and homebrew.js.

        Returns:
            Tuple of (elf_path, js_path) to downloaded files

        Raises:
            DownloadError: If download fails
            AssetNotFoundError: If expected files not in release
        """
        ...

    def get_cached_release(self, tag: str) -> Optional[tuple[Path, Path]]:
        """Get paths to cached release files if available."""
        ...

    def clear_cache(self) -> None:
        """Remove all cached downloads."""
        ...
```

---

## 3. Config Module (`src/config/`)

### Settings Interface

```python
# src/config/settings.py

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class AppSettings:
    last_host: str = ""
    last_port: int = 2121
    last_username: str = "anonymous"
    passive_mode: bool = True
    timeout: int = 30
    window_width: int = 800
    window_height: int = 600
    download_path: str = ""
    auto_check_updates: bool = True

class SettingsManager:
    """Manages application settings persistence."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize settings manager.

        Args:
            config_path: Optional custom path, defaults to platform standard
        """
        ...

    def load(self) -> AppSettings:
        """Load settings from disk, return defaults if not found."""
        ...

    def save(self, settings: AppSettings) -> None:
        """Persist settings to disk."""
        ...

    def reset(self) -> AppSettings:
        """Reset to default settings."""
        ...
```

### Credentials Interface

```python
# src/config/credentials.py

from typing import Optional

class CredentialManager:
    """Secure credential storage using system keyring."""

    SERVICE_NAME = "ps5-dump-runner-installer"

    def save_password(self, host: str, username: str, password: str) -> None:
        """
        Save FTP password securely.

        Uses system keyring (Windows Credential Manager, etc.)
        """
        ...

    def get_password(self, host: str, username: str) -> Optional[str]:
        """
        Retrieve saved password.

        Returns:
            Password string or None if not found
        """
        ...

    def delete_password(self, host: str, username: str) -> None:
        """Remove saved password."""
        ...

    def clear_all(self) -> None:
        """Remove all saved credentials for this app."""
        ...
```

---

## 4. GUI Module (`src/gui/`)

### Main Window Interface

```python
# src/gui/main_window.py

import tkinter as tk
from typing import Optional

class MainWindow:
    """Main application window."""

    def __init__(self, root: tk.Tk):
        ...

    def show_connection_panel(self) -> None:
        """Display FTP connection form."""
        ...

    def show_dump_list(self, dumps: List[GameDump]) -> None:
        """Display discovered game dumps."""
        ...

    def show_upload_dialog(
        self,
        selected_dumps: List[GameDump],
        release: DumpRunnerRelease
    ) -> None:
        """Show upload progress dialog."""
        ...

    def show_error(self, title: str, message: str) -> None:
        """Display error dialog."""
        ...

    def show_warning(self, title: str, message: str) -> bool:
        """Display warning with OK/Cancel, return True if OK."""
        ...

    def update_status(self, message: str) -> None:
        """Update status bar message."""
        ...
```

### Event Callbacks (GUI → Business Logic)

```python
# src/gui/callbacks.py

from typing import Protocol, List
from pathlib import Path

class AppCallbacks(Protocol):
    """Callbacks from GUI to application logic."""

    def on_connect(self, host: str, port: int, username: str, password: str) -> None:
        """User clicked Connect."""
        ...

    def on_disconnect(self) -> None:
        """User clicked Disconnect."""
        ...

    def on_scan(self) -> None:
        """User requested dump scan."""
        ...

    def on_upload_official(self, selected_dumps: List[GameDump]) -> None:
        """User wants to upload official files."""
        ...

    def on_upload_experimental(
        self,
        selected_dumps: List[GameDump],
        elf_path: Path,
        js_path: Path
    ) -> None:
        """User wants to upload experimental files."""
        ...

    def on_check_updates(self) -> None:
        """User requested update check."""
        ...

    def on_cancel_upload(self) -> None:
        """User cancelled upload."""
        ...
```

---

## 5. Cross-Module Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                         GUI Module                          │
│  (main_window, connection_panel, dump_list, upload_dialog) │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼ AppCallbacks
┌─────────────────────────────────────────────────────────────┐
│                    Application Controller                    │
│                      (src/main.py)                          │
└───────┬─────────────────┬─────────────────┬─────────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  FTP Module   │ │Updater Module │ │ Config Module │
│ - connection  │ │ - github      │ │ - settings    │
│ - scanner     │ │ - downloader  │ │ - credentials │
│ - uploader    │ │               │ │               │
└───────────────┘ └───────────────┘ └───────────────┘
```

**Dependency Rules**:
1. GUI Module depends on data types from FTP and Updater, but not implementations
2. Application Controller orchestrates all modules
3. FTP, Updater, and Config modules are independent of each other
4. Utils module provides cross-cutting concerns (logging, validation)
