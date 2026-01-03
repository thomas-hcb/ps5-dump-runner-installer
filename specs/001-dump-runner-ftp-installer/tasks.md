# Tasks: PS5 Dump Runner FTP Installer

**Input**: Design documents from `/specs/001-dump-runner-ftp-installer/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/module-interfaces.md

**Tests**: Tests are included per Constitution Principle VI (Testing Requirements - NON-NEGOTIABLE)

**Organization**: Tasks grouped by user story for independent implementation and testing

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3, US4, US5 (maps to user stories from spec.md)
- Exact file paths included in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Structure follows constitution-mandated layout: src/gui/, src/ftp/, src/updater/, src/config/, src/utils/

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure and install dependencies

- [x] T001 Create project directory structure per plan.md in src/, tests/, resources/, build/
- [x] T002 [P] Create src/__init__.py with package metadata
- [x] T003 [P] Create src/gui/__init__.py
- [x] T004 [P] Create src/ftp/__init__.py
- [x] T005 [P] Create src/updater/__init__.py
- [x] T006 [P] Create src/config/__init__.py
- [x] T007 [P] Create src/utils/__init__.py
- [x] T008 Create requirements.txt with: requests>=2.31.0, keyring>=24.0.0
- [x] T009 Create requirements-dev.txt with: pytest>=7.4.0, pytest-mock>=3.11.0, pyftpdlib>=1.5.0, pyinstaller>=6.0.0
- [x] T010 [P] Create .gitignore with Python, IDE, build artifacts patterns
- [x] T011 [P] Create resources/icons/ directory with placeholder icons
- [x] T012 Create tests/__init__.py and tests/conftest.py with base fixtures

**Checkpoint**: Project structure ready for implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Utils Module (Cross-Cutting)

- [x] T013 [P] Implement logging configuration in src/utils/logging.py with PII redaction
- [x] T014 [P] Implement input validators in src/utils/validators.py (IP address, port, path validation)
- [x] T015 [P] Implement background task helpers in src/utils/threading.py (ThreadedTask class, queue-based GUI updates)

### Config Module (Settings Infrastructure)

- [x] T016 [P] Implement path constants and discovery in src/config/paths.py (APPDATA paths, SCAN_PATHS list)
- [x] T017 Implement AppSettings dataclass in src/config/settings.py per data-model.md
- [x] T018 Implement SettingsManager in src/config/settings.py (load, save, reset methods)
- [x] T019 [P] Implement CredentialManager in src/config/credentials.py using keyring library

### FTP Module (Core Exceptions)

- [x] T020 [P] Define FTP exceptions in src/ftp/exceptions.py (ConnectionError, AuthenticationError, NotConnectedError, UploadError)

### Data Types (Shared Enums and Dataclasses)

- [x] T021 [P] Implement ConnectionState enum in src/ftp/connection.py
- [x] T022 [P] Implement FTPConnectionConfig dataclass in src/ftp/connection.py
- [x] T023 [P] Implement LocationType enum in src/ftp/scanner.py
- [x] T024 [P] Implement InstallationStatus enum in src/ftp/scanner.py
- [x] T025 [P] Implement GameDump dataclass in src/ftp/scanner.py
- [x] T026 [P] Implement UploadProgress and UploadResult dataclasses in src/ftp/uploader.py
- [x] T027 [P] Implement ReleaseSource enum in src/updater/release.py
- [x] T028 [P] Implement DumpRunnerRelease dataclass in src/updater/release.py

### Base Tests Setup

- [x] T029 Create tests/unit/__init__.py
- [x] T030 Create tests/integration/__init__.py
- [x] T031 [P] Create tests/fixtures/ directory with mock_dumps/, sample_releases/, test_configs/

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Connect to PS5 and Discover Game Dumps (Priority: P1) 🎯 MVP

**Goal**: Enable users to connect to PS5 FTP and discover all game dumps in predefined directories

**Independent Test**: Enter FTP credentials, verify connection status, see list of discovered dumps

### Tests for User Story 1

- [x] T032 [P] [US1] Unit test for FTPConnectionManager in tests/unit/test_connection.py (connect, disconnect, state transitions)
- [x] T033 [P] [US1] Unit test for DumpScanner in tests/unit/test_scanner.py (scan paths, parse directories)
- [x] T034 [P] [US1] Integration test with mock FTP server in tests/integration/test_ftp_workflow.py
- [x] T035 [P] [US1] Create mock FTP server helper in tests/integration/mock_ftp_server.py using pyftpdlib

### Implementation for User Story 1

- [x] T036 [US1] Implement FTPConnectionManager class in src/ftp/connection.py (connect, disconnect, state property, is_connected property)
- [x] T037 [US1] Implement DumpScanner class in src/ftp/scanner.py (scan method iterating SCAN_PATHS, refresh method)
- [x] T038 [P] [US1] Create StatusIndicator widget in src/gui/widgets/status_indicator.py (connected/disconnected icons)
- [x] T039 [P] [US1] Create ConnectionPanel widget in src/gui/connection_panel.py (IP, port, username, password fields, connect button)
- [x] T040 [US1] Create DumpList widget in src/gui/dump_list.py (TreeView/Listbox with checkboxes, select all)
- [x] T041 [US1] Create MainWindow class in src/gui/main_window.py (layout with connection panel, dump list, status bar)
- [x] T042 [US1] Create application controller in src/main.py (wire GUI callbacks to FTP module)
- [x] T043 [US1] Add connection error handling with user-friendly messages
- [x] T044 [US1] Add logging for connection and scan operations

**Checkpoint**: User Story 1 complete - can connect to PS5 and see discovered game dumps

---

## Phase 4: User Story 2 - Install dump_runner Files (Priority: P1)

**Goal**: Enable batch upload of dump_runner.elf and homebrew.js to multiple selected game dumps (supports both official releases and custom/experimental files)

**Independent Test**: Select multiple dumps, click upload, verify files transferred with progress

**Note**: This phase also covers User Story 3 (Experimental Files) - the file dialog allows selecting ANY local .elf/.js files, inherently supporting custom/experimental uploads without separate workflow.

### Tests for User Story 2

- [x] T045 [P] [US2] Unit test for FileUploader in tests/unit/test_uploader.py (upload_to_dump, upload_batch, cancel)
- [x] T046 [P] [US2] Integration test for batch upload in tests/integration/test_ftp_workflow.py

### Implementation for User Story 2

- [x] T047 [US2] Implement FileUploader class in src/ftp/uploader.py (upload_to_dump, upload_batch, cancel methods)
- [x] T048 [P] [US2] Create ProgressBar widget in src/gui/widgets/progress_bar.py (percentage, speed, ETA)
- [x] T049 [US2] Create UploadDialog in src/gui/upload_dialog.py (per-dump progress, overall progress, cancel button)
- [x] T050 [US2] Add upload button and selection handling to MainWindow in src/gui/main_window.py
- [x] T051 [US2] Implement threaded upload with queue-based progress updates in src/main.py
- [x] T052 [US2] Add overwrite confirmation dialog before upload
- [x] T053 [US2] Handle partial failures (continue with remaining dumps, report failures separately)
- [x] T054 [US2] Add logging for upload operations with per-dump status

### Experimental/Custom File Support (User Story 3 - merged into US2)

- [x] T054-US3a [US2] Browse and select local custom files via file dialog in src/gui/main_window.py (covered by T050)
- [x] T054-US3b [US2] Upload any user-selected .elf/.js files to dumps in src/ftp/uploader.py (covered by T047)
- [x] T054-US3c [US2] Progress indication for custom file uploads in src/gui/upload_dialog.py (covered by T048, T049)

### GitHub Integration for User Story 2 (Official Release Download)

- [x] T054a [P] [US2] Implement GitHubClient class in src/updater/github_client.py (get_latest_release from https://github.com/EchoStretch/dump_runner/releases)
- [x] T054b [P] [US2] Implement ReleaseDownloader class in src/updater/downloader.py (download dump_runner.elf and homebrew.js assets)
- [x] T054c [US2] Add "Download Latest Release" button to MainWindow in src/gui/main_window.py
- [x] T054d [US2] Create download progress dialog for GitHub downloads
- [x] T054e [US2] Cache downloaded releases in local cache directory (src/config/paths.py: get_releases_cache_dir)
- [x] T054f [US2] Update upload workflow to use downloaded official files as default source
- [x] T054g [P] [US2] Unit test for GitHubClient in tests/unit/test_github_client.py
- [x] T054h [US2] Handle GitHub unreachable gracefully (fallback to manual file selection)

**Checkpoint**: User Stories 1, 2, AND 3 complete - MVP functional (connect + batch upload with GitHub download + custom file support)

---

## Phase 5: User Story 5 - Save and Restore Settings (Priority: P3)

**Goal**: Persist FTP connection settings between sessions with secure credential storage

**Independent Test**: Enter settings, close app, reopen, verify settings pre-populated

### Tests for User Story 5

- [x] T055 [P] [US5] Unit test for SettingsManager in tests/unit/test_settings.py (load, save, defaults)
- [x] T056 [P] [US5] Unit test for CredentialManager in tests/unit/test_settings.py (save, get, delete password)

### Implementation for User Story 5

- [x] T057 [US5] Create SettingsDialog in src/gui/settings_dialog.py (preferences, clear credentials button)
- [x] T058 [US5] Add Settings menu item to MainWindow
- [x] T059 [US5] Load saved settings on app startup in src/main.py
- [x] T060 [US5] Save settings on successful connection in src/main.py
- [x] T061 [US5] Pre-populate connection form with saved values in ConnectionPanel
- [x] T062 [US5] Implement "Clear Saved Credentials" action

**Checkpoint**: User Story 5 complete - settings persist across sessions

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements affecting multiple user stories

- [x] T063 [P] Add application icon to resources/icons/app_icon.ico
- [x] T064 [P] Add connected/disconnected status icons to resources/icons/
- [x] T065 [P] Add official/experimental version icons to resources/icons/
- [x] T066 Create PyInstaller spec file in build/ps5-dump-runner-installer.spec
- [x] T067 Build Windows executable with PyInstaller
- [x] T068 [P] Update README.md with usage instructions
- [x] T069 Run full test suite and ensure all tests pass
- [x] T070 Test quickstart.md workflow end-to-end
- [x] T071 Code cleanup: remove debug prints, ensure consistent error messages
- [x] T072 Security review: verify no credentials logged, keyring integration correct

**Checkpoint**: Phase 6 complete - Application polished and production-ready

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 - BLOCKS all user stories
- **User Stories (Phases 3-5)**: All depend on Phase 2 completion
  - Can proceed sequentially (P1 → P1 → P3)
  - Or in parallel if team capacity allows
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

| Story | Depends On | Can Start After |
|-------|------------|-----------------|
| US1 (Connect + Scan) | Foundational | Phase 2 complete |
| US2+US3 (Upload + Custom Files + GitHub) | US1 (needs connection + dump list) | Phase 3 complete |
| US5 (Settings) | Foundational only | Phase 2 complete (parallel with US1) |

### Within Each User Story

1. Tests written first (must FAIL before implementation)
2. Core classes/models
3. Service logic
4. GUI components
5. Integration and error handling
6. Logging

### Parallel Opportunities

**Phase 1 (all [P] tasks):**
```
T002, T003, T004, T005, T006, T007 (package __init__.py files)
T010, T011 (gitignore, resources)
```

**Phase 2 (all [P] tasks):**
```
T013, T014, T015 (utils module)
T016, T019 (config paths, credentials)
T020 (exceptions)
T021-T028 (all data types)
T029, T030, T031 (test setup)
```

**Phase 3 User Story 1:**
```
T032, T033, T034, T035 (all tests)
T038, T039 (widgets)
```

**Phases 4-5 can run in parallel if staffed:**
- Developer A: US2+US3+GitHub (upload + custom files + official releases)
- Developer B: US5 (settings) - independent

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests in parallel:
Task: "Unit test for FTPConnectionManager in tests/unit/test_connection.py"
Task: "Unit test for DumpScanner in tests/unit/test_scanner.py"
Task: "Integration test with mock FTP server in tests/integration/test_ftp_workflow.py"
Task: "Create mock FTP server helper in tests/integration/mock_ftp_server.py"

# Launch parallel GUI widgets:
Task: "Create StatusIndicator widget in src/gui/widgets/status_indicator.py"
Task: "Create ConnectionPanel widget in src/gui/connection_panel.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. ✅ Complete Phase 1: Setup
2. ✅ Complete Phase 2: Foundational
3. ✅ Complete Phase 3: User Story 1 (Connect + Scan)
4. ✅ Complete Phase 4: User Story 2 (Upload)
5. **STOP and VALIDATE**: Test connecting to PS5 and uploading files
6. Deploy/demo MVP

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Connect) → Test → **Milestone: Can discover dumps**
3. Add US2+US3+GitHub (Upload + Custom + Official) → Test → **Milestone: MVP - full upload workflow!**
4. Add US5 (Settings) → Test → **Milestone: Convenience features**
5. Polish → Test → **Milestone: Production-ready**

---

## Task Summary

| Phase | Task Count | User Story | Status |
|-------|------------|------------|--------|
| Phase 1: Setup | 12 | - | ✅ Complete |
| Phase 2: Foundational | 19 | - | ✅ Complete |
| Phase 3: US1 (Connect + Scan) | 13 | P1 | ✅ Complete |
| Phase 4: US2+US3 (Upload + Custom Files + GitHub) | 21 | P1+P2 | ✅ Complete |
| Phase 5: US5 (Settings) | 8 | P3 | ✅ Complete |
| Phase 6: Polish | 10 | - | ✅ Complete |
| **Total** | **83** | | ✅ ALL COMPLETE |

---

## Notes

- [P] tasks = different files, no dependencies on other tasks
- [US#] label maps task to specific user story
- Each user story independently completable and testable
- Constitution Principle VI requires tests - included in each user story
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
