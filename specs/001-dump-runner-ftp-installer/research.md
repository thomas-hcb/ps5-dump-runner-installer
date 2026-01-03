# Research: PS5 Dump Runner FTP Installer

**Feature Branch**: `001-dump-runner-ftp-installer`
**Created**: 2026-01-03
**Status**: Complete

## Research Topics

### 1. Python FTP Library Selection

**Decision**: Use `ftplib` from Python standard library

**Rationale**:
- Part of Python standard library - no external dependencies
- Supports both active and passive FTP modes (required by FR-005)
- Full support for binary file transfers (STOR command)
- Built-in timeout handling
- Widely documented and battle-tested

**Alternatives Considered**:
- `ftputil`: Higher-level abstraction but adds external dependency
- `pyftpdlib`: Great for testing (mock server) but not needed for client operations
- `paramiko/SFTP`: Overkill - PS5 uses FTP, not SFTP

**Implementation Notes**:
```python
from ftplib import FTP
ftp = FTP()
ftp.connect(host, port, timeout=30)
ftp.login(user, passwd)
ftp.set_pasv(True)  # Passive mode
with open(local_file, 'rb') as f:
    ftp.storbinary(f'STOR {remote_path}', f)
```

### 2. GUI Framework Selection

**Decision**: Use `tkinter` (standard library)

**Rationale**:
- Standard library - ships with Python, no installation needed
- Sufficient for form inputs, lists, progress bars, and dialogs
- Windows-native look with ttk themed widgets
- Simpler distribution (no Qt/PySide DLLs to bundle)
- Constitution preference: "Minimize external dependencies"

**Alternatives Considered**:
- PyQt6/PySide6: Richer UI but adds ~100MB+ to distribution, licensing complexity
- wxPython: Cross-platform but external dependency
- Dear PyGui: Modern but less mature, overkill for form-based app

**Implementation Notes**:
- Use `ttk` themed widgets for modern appearance
- Use `threading` for non-blocking FTP operations
- Use `queue.Queue` for thread-safe GUI updates

### 3. Secure Credential Storage

**Decision**: Use `keyring` library with system keyring backend

**Rationale**:
- Cross-platform secure storage (Windows Credential Manager, macOS Keychain, Linux Secret Service)
- Industry standard for desktop credential storage
- Constitution requirement: "Store credentials securely (not in plaintext)"
- Simple API: `keyring.set_password()` / `keyring.get_password()`

**Alternatives Considered**:
- Manual encryption (cryptography library): Complex key management, we'd need to store the key somewhere
- Environment variables: Not persistent across sessions
- Encrypted JSON file: Still need to manage encryption key securely

**Implementation Notes**:
```python
import keyring

SERVICE_NAME = "ps5-dump-runner-installer"

def save_credentials(host: str, username: str, password: str):
    keyring.set_password(SERVICE_NAME, f"{host}:{username}", password)

def get_credentials(host: str, username: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, f"{host}:{username}")
```

### 4. GitHub API Integration

**Decision**: Use `requests` library with GitHub REST API v3

**Rationale**:
- `requests` is the de-facto standard for HTTP in Python
- GitHub REST API is simple for release checking (no GraphQL needed)
- Only need: GET latest release, download assets
- No authentication required for public repos (EchoStretch/dump_runner is public)

**Alternatives Considered**:
- `urllib` (standard library): More verbose, less ergonomic
- `httpx`: Async support unnecessary for this use case
- `PyGithub`: Full API wrapper is overkill for just releases

**Implementation Notes**:
```python
GITHUB_API = "https://api.github.com/repos/EchoStretch/dump_runner/releases/latest"

def get_latest_release():
    response = requests.get(GITHUB_API, timeout=10)
    response.raise_for_status()
    data = response.json()
    return {
        "tag": data["tag_name"],
        "published": data["published_at"],
        "assets": [
            {"name": a["name"], "url": a["browser_download_url"]}
            for a in data["assets"]
        ]
    }
```

### 5. PS5 FTP Directory Structure

**Decision**: Scan these directories at 1-level depth per spec requirements

**Research Findings**:
- `/data/homebrew/` - Internal storage homebrew directory
- `/mnt/usb0/homebrew/` through `/mnt/usb7/homebrew/` - USB storage devices
- `/mnt/ext0/homebrew/` through `/mnt/ext7/homebrew/` - Extended storage devices

**Rationale**:
- These are the standard locations where PS5 homebrew/game dumps are placed
- 1-level depth scanning means: list directories directly under these paths
- Each subdirectory represents a game dump that can receive dump_runner files

**Implementation Notes**:
```python
SCAN_PATHS = [
    "/data/homebrew/",
    *[f"/mnt/usb{i}/homebrew/" for i in range(8)],
    *[f"/mnt/ext{i}/homebrew/" for i in range(8)],
]

def scan_for_dumps(ftp: FTP) -> list[str]:
    dumps = []
    for base_path in SCAN_PATHS:
        try:
            ftp.cwd(base_path)
            for name in ftp.nlst():
                if is_directory(ftp, name):  # Check if it's a directory
                    dumps.append(f"{base_path}{name}")
        except error_perm:
            continue  # Path doesn't exist, skip
    return dumps
```

### 6. Threading Model for Non-Blocking GUI

**Decision**: Use `threading.Thread` with `queue.Queue` for GUI updates

**Rationale**:
- tkinter is not thread-safe - GUI updates must happen on main thread
- Background threads for FTP operations, queue for passing results back
- `after()` method to poll queue and update GUI safely

**Alternatives Considered**:
- `asyncio`: Would require async FTP library, more complex
- `concurrent.futures`: Good for batch operations, but queue pattern still needed for GUI
- `multiprocessing`: Overkill, process overhead unnecessary

**Implementation Pattern**:
```python
import threading
import queue

class UploadWorker(threading.Thread):
    def __init__(self, ftp_params, files, dumps, progress_queue):
        super().__init__(daemon=True)
        self.progress_queue = progress_queue
        # ... store params

    def run(self):
        for dump in self.dumps:
            # Upload files
            self.progress_queue.put(("progress", dump, percent))
        self.progress_queue.put(("complete", results))

# In GUI:
def poll_progress(self):
    try:
        msg = self.progress_queue.get_nowait()
        # Update GUI based on msg
    except queue.Empty:
        pass
    self.after(100, self.poll_progress)  # Poll every 100ms
```

### 7. Application Settings Storage

**Decision**: JSON file for non-sensitive settings, keyring for credentials

**Rationale**:
- JSON is human-readable and easy to debug
- Standard library `json` module, no dependencies
- Settings include: last used host, port, passive mode preference, window size
- Credentials stored separately in system keyring (see topic 3)

**Storage Location**:
- Windows: `%APPDATA%\PS5DumpRunnerInstaller\settings.json`
- Cross-platform: Use `platformdirs` or `appdirs` library

**Implementation Notes**:
```python
import json
from pathlib import Path

def get_settings_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ["APPDATA"])
    else:
        base = Path.home() / ".config"
    return base / "PS5DumpRunnerInstaller" / "settings.json"
```

### 8. PyInstaller Distribution

**Decision**: Use PyInstaller for single-executable distribution

**Rationale**:
- Creates standalone .exe for Windows users
- Bundles Python interpreter and all dependencies
- Constitution requirement: "Portable executable option (no installation required)"
- Well-documented for tkinter applications

**Considerations**:
- Use `--onefile` for single executable
- Include `resources/` directory with `--add-data`
- May need to handle keyring backend detection at runtime

**Build Command**:
```bash
pyinstaller --onefile --windowed --name "PS5DumpRunnerInstaller" \
    --add-data "resources:resources" \
    --icon "resources/icons/app_icon.ico" \
    src/main.py
```

## Summary of Technology Decisions

| Component | Technology | Type |
|-----------|------------|------|
| Language | Python 3.11+ | Standard |
| GUI | tkinter + ttk | Standard Library |
| FTP Client | ftplib | Standard Library |
| HTTP Client | requests | External (pinned) |
| Credentials | keyring | External (pinned) |
| Testing | pytest + pyftpdlib | Dev Dependency |
| Distribution | PyInstaller | Dev Dependency |

## Dependencies Summary

**Runtime Dependencies** (requirements.txt):
```
requests>=2.31.0,<3.0.0
keyring>=24.0.0,<26.0.0
```

**Development Dependencies** (requirements-dev.txt):
```
pytest>=7.4.0
pytest-mock>=3.11.0
pyftpdlib>=1.5.0
pyinstaller>=6.0.0
```
