# Quickstart Guide: PS5 Dump Runner FTP Installer

**Feature Branch**: `001-dump-runner-ftp-installer`
**Created**: 2026-01-03

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git (for cloning repository)

## Development Setup

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/ps5-dump-runner-installer.git
cd ps5-dump-runner-installer

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Project Structure

```
ps5-dump-runner-installer/
├── src/                    # Source code
│   ├── main.py            # Application entry point
│   ├── gui/               # GUI components
│   ├── ftp/               # FTP operations
│   ├── updater/           # GitHub integration
│   ├── config/            # Settings & credentials
│   └── utils/             # Utilities
├── tests/                 # Test suite
├── resources/             # Icons and assets
├── specs/                 # Feature specifications
└── requirements.txt       # Dependencies
```

### 3. Run the Application

```bash
# From project root with venv activated
python -m src.main

# Or directly
python src/main.py
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_connection.py

# Run integration tests (requires no real PS5)
pytest tests/integration/

# With coverage report
python -m pytest --cov=src --cov-report=html -v

# Run specific test file
python -m pytest tests/unit/test_connection.py -v

# Run tests matching a pattern
python -m pytest -k "test_connect" -v

# Stop on first failure
python -m pytest -x -v
```

## Key Development Tasks

### Adding a New FTP Operation

1. Add method to appropriate class in `src/ftp/`
2. Add corresponding test in `tests/unit/`
3. If it affects GUI, update callbacks in `src/gui/callbacks.py`

### Modifying Settings

1. Update `AppSettings` dataclass in `src/config/settings.py`
2. Settings are auto-persisted to JSON
3. Credentials use `src/config/credentials.py` (keyring-backed)

### Adding GUI Elements

1. Create new widget/dialog in `src/gui/`
2. Register callbacks in `AppCallbacks` protocol
3. Connect to main controller in `src/main.py`

## Testing with Mock FTP Server

For integration tests without a real PS5:

```python
# tests/integration/mock_ftp_server.py provides a pyftpdlib-based mock

from tests.integration.mock_ftp_server import MockPS5FTPServer
from src.ftp.connection import FTPConnectionManager, FTPConnectionConfig

def test_with_mock():
    with MockPS5FTPServer(port=2121) as server:
        # Default credentials: username='testuser', password='testpass'
        config = FTPConnectionConfig(
            host='127.0.0.1',
            port=2121,
            username='testuser'
        )
        mgr = FTPConnectionManager()
        mgr.connect(config, password='testpass')
        # Your test code...
        mgr.disconnect()
```

## Building Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build single-file executable
pyinstaller --onefile --windowed \
    --name "PS5DumpRunnerInstaller" \
    --add-data "resources:resources" \
    --icon "resources/icons/app_icon.ico" \
    src/main.py

# Output in dist/PS5DumpRunnerInstaller.exe
```

## Common Development Commands

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/

# Run single test with verbose output
pytest tests/unit/test_scanner.py -v

# Run tests matching pattern
pytest -k "test_connect"
```

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `PS5_FTP_HOST` | Override default host for testing | None |
| `PS5_FTP_PORT` | Override default port | 2121 |
| `LOG_LEVEL` | Logging verbosity | INFO |

## Troubleshooting

### "tkinter not found"

Install tkinter for your Python version:
- Windows: Should be included with Python installer
- Ubuntu: `sudo apt install python3-tk`
- macOS: `brew install python-tk`

### Keyring errors on Linux

Install a keyring backend:
```bash
sudo apt install gnome-keyring
# or
pip install keyrings.alt
```

### FTP connection issues

1. Verify PS5 FTP is enabled and accessible
2. Check firewall settings
3. Try passive mode if active fails
4. Default PS5 FTP port is 2121, not 21

## Next Steps

1. Review [spec.md](spec.md) for feature requirements
2. Check [data-model.md](data-model.md) for entity definitions
3. See [contracts/module-interfaces.md](contracts/module-interfaces.md) for API design
4. Use `/speckit.tasks` to generate implementation tasks
