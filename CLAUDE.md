# PS5 Dump Runner Installer Development Guidelines

Auto-generated from all feature plans. **Last updated**: 2026-01-03

## Active Technologies

- Python 3.11+ (001-dump-runner-ftp-installer)
- tkinter + ftplib + keyring + requests (001-dump-runner-ftp-installer)

## Project Structure

```text
src/
├── main.py              # Application entry point
├── gui/                 # GUI components (tkinter)
├── ftp/                 # FTP operations (ftplib)
├── updater/             # GitHub integration (requests)
├── config/              # Settings & credentials (keyring)
└── utils/               # Shared utilities

tests/
├── unit/                # pytest unit tests
├── integration/         # Mock FTP server tests
└── fixtures/            # Test data
```

## Commands

```bash
# Development
cd src; pytest; ruff check .

# Run application
python -m src.main

# Run tests
pytest
pytest --cov=src --cov-report=html

# Build executable
pyinstaller --onefile --windowed --name "PS5DumpRunnerInstaller" src/main.py
```

## Code Style

Python: Follow standard conventions
- Type hints required for all function signatures (PEP 484)
- Docstrings for all public methods (Google style)
- PEP 8 compliance (enforced via linter)
- Error messages must be user-friendly

## Recent Changes

- 001-dump-runner-ftp-installer: Added Python 3.11+ + tkinter + ftplib + keyring + requests

<!-- MANUAL ADDITIONS START -->
## Constitution Reference

See `.specify/memory/constitution.md` for project principles:
- I. User Safety First - Confirmations before file operations
- II. GUI-First Design - Progress indicators, non-blocking UI
- III. FTP Operations Best Practices - Passive mode, retry logic
- IV. Modular Architecture - Separate gui/ftp/updater/config modules
- V. Version Management & Experimental Builds - GitHub integration, experimental warnings
- VI. Testing Requirements (NON-NEGOTIABLE) - pytest with mock FTP server
<!-- MANUAL ADDITIONS END -->
