# Implementation Plan: PS5 Dump Runner FTP Installer

**Branch**: `001-dump-runner-ftp-installer` | **Date**: 2026-01-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-dump-runner-ftp-installer/spec.md`

## Summary

Build a Python GUI application that enables PS5 users to batch-upload dump_runner.elf and homebrew.js files to multiple game dumps via FTP connection. The application will scan predefined PS5 directories (/data/homebrew/, /mnt/usb#/homebrew/, /mnt/ext#/homebrew/) to discover game dumps, allow batch selection for uploads, support both official releases from GitHub and experimental custom builds, and persist FTP connection settings securely.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- tkinter (standard library) - GUI framework
- ftplib (standard library) - FTP operations
- keyring - Secure credential storage
- requests - GitHub API integration
**Storage**: Local JSON file for settings (non-sensitive), system keyring for credentials
**Testing**: pytest with pytest-mock for unit tests, pyftpdlib for mock FTP server integration tests
**Target Platform**: Windows 10/11 (primary), cross-platform compatible
**Project Type**: Single desktop application
**Performance Goals**: Connection within 5 seconds, 10 dumps uploaded in under 5 minutes
**Constraints**: Single PS5 connection at a time, local network only, <100MB memory footprint
**Scale/Scope**: Personal use tool, single user, ~50 game dumps maximum typical

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Implementation Notes |
|-----------|--------|---------------------|
| I. User Safety First | ✅ PASS | FR-014 confirms before overwrite; error isolation per dump (FR-015); connection validation (FR-002) |
| II. GUI-First Design | ✅ PASS | tkinter GUI with progress indicators (FR-013); non-blocking uploads via threading; persistent settings (FR-026) |
| III. FTP Operations Best Practices | ✅ PASS | ftplib with passive mode support (FR-005); retry logic; secure credentials via keyring (FR-027) |
| IV. Modular Architecture | ✅ PASS | Separate modules: src/gui/, src/ftp/, src/updater/, src/config/ per constitution structure |
| V. Version Management & Experimental | ✅ PASS | GitHub integration (FR-022-025); experimental file support with warnings (FR-017-021); visual distinction (FR-020) |
| VI. Testing Requirements | ✅ PASS | pytest for unit tests; pyftpdlib mock server for integration; coverage of FTP ops, batch uploads, config |

**Gate Status**: PASSED - All constitution principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/001-dump-runner-ftp-installer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal module interfaces)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── main.py              # Application entry point
├── gui/
│   ├── __init__.py
│   ├── main_window.py   # Main application window
│   ├── connection_panel.py  # FTP connection form
│   ├── dump_list.py     # Game dump selection list
│   ├── upload_dialog.py # Upload progress dialog
│   ├── settings_dialog.py # Settings management
│   └── widgets/         # Reusable UI components
│       ├── __init__.py
│       ├── progress_bar.py
│       └── status_indicator.py
├── ftp/
│   ├── __init__.py
│   ├── connection.py    # FTP connection management
│   ├── scanner.py       # Game dump discovery
│   ├── uploader.py      # File upload operations
│   └── exceptions.py    # FTP-specific exceptions
├── updater/
│   ├── __init__.py
│   ├── github_client.py # GitHub API integration
│   ├── release.py       # Release data models
│   └── downloader.py    # Asset download logic
├── config/
│   ├── __init__.py
│   ├── settings.py      # Application settings
│   ├── credentials.py   # Secure credential storage
│   └── paths.py         # Path constants and discovery
└── utils/
    ├── __init__.py
    ├── logging.py       # Logging configuration
    ├── validators.py    # Input validation helpers
    └── threading.py     # Background task helpers

tests/
├── __init__.py
├── conftest.py          # pytest fixtures
├── unit/
│   ├── __init__.py
│   ├── test_connection.py
│   ├── test_scanner.py
│   ├── test_uploader.py
│   ├── test_github_client.py
│   └── test_settings.py
├── integration/
│   ├── __init__.py
│   ├── test_ftp_workflow.py
│   └── mock_ftp_server.py
└── fixtures/
    ├── mock_dumps/
    ├── sample_releases/
    └── test_configs/

resources/
├── icons/
│   ├── app_icon.ico
│   ├── connected.png
│   ├── disconnected.png
│   ├── official.png
│   └── experimental.png
└── themes/

build/
├── ps5-dump-runner-installer.spec  # PyInstaller spec
└── dist/                           # Built executables
```

**Structure Decision**: Single desktop application following the constitution's mandated project structure. The src/ directory contains four main modules (gui, ftp, updater, config) plus utils, ensuring loose coupling between GUI and business logic per Principle IV.

## Complexity Tracking

> No violations - all principles satisfied with standard patterns

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| GUI Framework | tkinter | Standard library, no extra dependencies, sufficient for this use case |
| FTP Library | ftplib | Standard library, full FTP support including passive mode |
| Threading | threading module | Standard library, simple for GUI background tasks |
| Credential Storage | keyring | Industry standard, cross-platform secure storage |
