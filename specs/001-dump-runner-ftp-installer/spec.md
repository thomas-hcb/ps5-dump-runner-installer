# Feature Specification: PS5 Dump Runner FTP Installer

**Feature Branch**: `001-dump-runner-ftp-installer`
**Created**: 2026-01-03
**Status**: Draft
**Input**: User description: "Python GUI application for uploading and overwriting dump_runner.elf & homebrew.js (from https://github.com/EchoStretch/dump_runner) across multiple PS5 game dumps via FTP connection. Also allow a feature to upload experimental dump_runner.elf & homebrew.js files. The below directories in PS5 FTP should be scanned by 1-level depth: /data/homebrew/, /mnt/usb#/homebrew/ (replace # with your USB number, e.g., usb0, usb1, etc.), /mnt/ext#/homebrew/ (replace # with your EXT number, e.g., ext0, ext1, etc.)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Connect to PS5 and Discover Game Dumps (Priority: P1)

As a PS5 user, I want to connect to my PS5 via FTP and automatically discover all available game dumps so that I can see which games can receive dump_runner updates.

**Why this priority**: Without FTP connection and game discovery, no other features can function. This is the foundational capability that enables all subsequent operations.

**Independent Test**: Can be fully tested by entering FTP credentials and verifying the application displays a list of discovered game dumps from the PS5.

**Acceptance Scenarios**:

1. **Given** the user has their PS5's IP address and FTP is enabled, **When** they enter FTP connection details (IP, port, username, password), **Then** the application establishes a connection and displays connection status.

2. **Given** an active FTP connection, **When** the application scans for game dumps, **Then** it discovers all game directories at 1-level depth under:
   - /data/homebrew/
   - /mnt/usb0/homebrew/, /mnt/usb1/homebrew/, etc.
   - /mnt/ext0/homebrew/, /mnt/ext1/homebrew/, etc.

3. **Given** no FTP server is available at the specified address, **When** the user attempts to connect, **Then** the application displays a clear error message and allows retry.

---

### User Story 2 - Install Official dump_runner Files to Selected Dumps (Priority: P1)

As a PS5 user, I want to upload the official dump_runner.elf and homebrew.js files to multiple selected game dumps at once so that I can efficiently update all my games without manual file copying.

**Why this priority**: This is the core value proposition of the application - batch installation of dump_runner files.

**Independent Test**: Can be fully tested by selecting multiple game dumps and initiating an upload, then verifying both files exist in each selected dump's directory.

**Acceptance Scenarios**:

1. **Given** a list of discovered game dumps, **When** the user selects multiple dumps, **Then** they can initiate a batch upload operation.

2. **Given** selected game dumps and official dump_runner files available, **When** the user confirms the upload, **Then** dump_runner.elf and homebrew.js are uploaded to each selected dump with progress indication per dump.

3. **Given** an upload is in progress, **When** one dump fails but others succeed, **Then** the application continues with remaining dumps and reports which specific dumps failed with reasons.

4. **Given** existing dump_runner files in a game dump, **When** the user uploads new files, **Then** the existing files are overwritten after user confirmation.

---

### User Story 3 - Upload Experimental/Custom Files (Priority: P2)

As a PS5 developer or tester, I want to upload my own experimental dump_runner.elf and homebrew.js files so that I can test custom modifications across my game dumps.

**Why this priority**: Enables power users and developers to test custom builds, but not required for basic functionality.

**Independent Test**: Can be fully tested by selecting local experimental files and uploading them to selected dumps, then verifying the custom files are present.

**Acceptance Scenarios**:

1. **Given** the user has local experimental dump_runner.elf and/or homebrew.js files, **When** they choose "Upload Experimental Files", **Then** they can browse and select their custom files.

2. **Given** experimental files selected, **When** initiating upload, **Then** the application displays a warning that these are non-official files and requires explicit confirmation.

3. **Given** experimental files uploaded to dumps, **When** viewing dump status, **Then** these dumps are visually marked as having "Experimental" versions installed.

4. **Given** a dump has experimental files, **When** the user wants to revert, **Then** they can easily restore official files with one action.

---

### User Story 4 - Download Latest Official Files from GitHub (Priority: P2)

As a PS5 user, I want the application to automatically check for and download the latest dump_runner releases from GitHub so that I always have access to the newest official version.

**Why this priority**: Convenience feature that eliminates manual downloading, but users could manually provide files if needed.

**Independent Test**: Can be fully tested by triggering an update check and verifying the latest release is downloaded from the official repository.

**Acceptance Scenarios**:

1. **Given** the application is running, **When** the user checks for updates, **Then** the application queries the GitHub repository (https://github.com/EchoStretch/dump_runner) for the latest release.

2. **Given** a newer version is available, **When** displayed to the user, **Then** they see the version number, release date, and changelog/release notes.

3. **Given** the user chooses to download, **When** download completes, **Then** the files are stored locally and ready for installation.

---

### User Story 5 - Save and Restore FTP Connection Settings (Priority: P3)

As a returning user, I want my FTP connection settings to be remembered so that I don't have to re-enter them each time I use the application.

**Why this priority**: Quality-of-life improvement, not essential for core functionality.

**Independent Test**: Can be fully tested by entering settings, closing the application, reopening, and verifying settings are pre-populated.

**Acceptance Scenarios**:

1. **Given** the user enters FTP connection settings, **When** they successfully connect, **Then** the settings are saved for future sessions (credentials stored securely, not in plaintext).

2. **Given** saved connection settings exist, **When** the application starts, **Then** the settings are pre-populated in the connection form.

3. **Given** saved credentials, **When** the user wants to clear them, **Then** they can delete saved settings through the application.

---

### Edge Cases

- What happens when the PS5 disconnects mid-transfer? Application detects connection loss, stops remaining uploads, and reports partial completion status with option to retry failed uploads.

- What happens when a game dump directory is read-only or locked? Application reports the specific permission error for that dump and continues with other selected dumps.

- What happens when disk space is insufficient on the PS5? Application detects and reports the storage error before or during upload with clear messaging.

- What happens when scanning finds no game dumps in any location? Application displays a message explaining no dumps were found and suggests checking FTP paths or dump installation.

- What happens when the GitHub repository is unreachable? Application displays connectivity error and allows users to manually select local files instead.

- What happens when experimental files are corrupted or invalid? Application validates file presence and basic integrity (file size > 0) before upload; warns user if files appear invalid.

## Requirements *(mandatory)*

### Functional Requirements

**FTP Connection**
- **FR-001**: System MUST allow users to enter FTP connection details: IP address, port (default 2121), username, and password.
- **FR-002**: System MUST validate connection parameters before attempting connection.
- **FR-003**: System MUST display clear connection status (connecting, connected, failed, disconnected).
- **FR-004**: System MUST handle connection timeouts gracefully with configurable timeout duration.
- **FR-005**: System MUST support both active and passive FTP modes.

**Game Dump Discovery**
- **FR-006**: System MUST scan /data/homebrew/ at 1-level depth for game dump directories.
- **FR-007**: System MUST scan /mnt/usb0/homebrew/ through /mnt/usb7/homebrew/ at 1-level depth for game dump directories.
- **FR-008**: System MUST scan /mnt/ext0/homebrew/ through /mnt/ext7/homebrew/ at 1-level depth for game dump directories.
- **FR-009**: System MUST display discovered game dumps in a selectable list with their location path.
- **FR-010**: System MUST allow users to select/deselect individual dumps or select all.

**File Upload Operations**
- **FR-011**: System MUST upload dump_runner.elf to selected game dump directories.
- **FR-012**: System MUST upload homebrew.js to selected game dump directories.
- **FR-013**: System MUST display per-dump progress during batch uploads (percentage, current file, speed).
- **FR-014**: System MUST confirm before overwriting existing files.
- **FR-015**: System MUST continue batch operations even if individual dumps fail, reporting failures separately.
- **FR-016**: System MUST allow cancellation of in-progress uploads.

**Experimental File Support**
- **FR-017**: System MUST allow users to select local experimental dump_runner.elf file.
- **FR-018**: System MUST allow users to select local experimental homebrew.js file.
- **FR-019**: System MUST display warning dialog before uploading experimental files.
- **FR-020**: System MUST visually distinguish dumps with experimental versions from those with official versions.
- **FR-021**: System MUST track which version type (official/experimental) is installed per dump.

**GitHub Integration**
- **FR-022**: System MUST check for latest release from https://github.com/EchoStretch/dump_runner.
- **FR-023**: System MUST display available version information (version number, release date).
- **FR-024**: System MUST download release assets (dump_runner.elf, homebrew.js) when requested.
- **FR-025**: System MUST store downloaded official files locally for installation.

**Settings & Persistence**
- **FR-026**: System MUST save FTP connection settings between sessions.
- **FR-027**: System MUST store credentials securely (not in plaintext configuration files).
- **FR-028**: System MUST allow users to clear saved settings.

### Key Entities

- **FTP Connection**: Represents the connection to a PS5 console (IP address, port, credentials, connection state, current session).

- **Game Dump**: A discovered game directory on the PS5 that can receive dump_runner files (path, name/title if detectable, current dump_runner version status, installation type: official/experimental/none).

- **Dump Runner Release**: A version of dump_runner files from the official repository (version identifier, release date, dump_runner.elf file, homebrew.js file, source: official GitHub / experimental local).

- **Upload Operation**: A batch upload job targeting multiple game dumps (target dumps list, source files, progress per dump, overall status, failures list).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can connect to PS5 FTP and view discovered game dumps within 30 seconds of entering connection details.

- **SC-002**: Users can upload dump_runner files to 10 selected game dumps in under 5 minutes (assuming stable network connection).

- **SC-003**: 95% of upload operations complete successfully without requiring user intervention for error recovery.

- **SC-004**: Users can identify experimental vs. official installations at a glance through clear visual differentiation.

- **SC-005**: Application handles network interruptions gracefully, allowing users to resume or retry failed operations without restarting the application.

- **SC-006**: First-time users can complete their first successful batch upload within 5 minutes of launching the application (intuitive workflow).

- **SC-007**: Saved FTP credentials remain secure and are not exposed in configuration files or logs.

## Assumptions

- PS5 FTP server is accessible on the local network when enabled (typically port 2121).
- USB and EXT mount points follow the standard numbering convention (usb0-usb7, ext0-ext7).
- Game dump directories contain identifiable structure at the expected paths.
- The official dump_runner repository maintains consistent release asset naming.
- Users have sufficient permissions on the PS5 FTP to write files to homebrew directories.
- Network conditions are generally stable for file transfers (home network environment).

## Out of Scope

- Automatic PS5 FTP server detection/discovery (user must know their PS5 IP).
- Game dump creation or management (only file upload to existing dumps).
- dump_runner.elf or homebrew.js functionality verification after upload.
- Multi-console management (one PS5 connection at a time).
- Remote access over internet (local network only assumed).
