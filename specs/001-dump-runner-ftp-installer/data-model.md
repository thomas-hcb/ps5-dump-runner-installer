# Data Model: PS5 Dump Runner FTP Installer

**Feature Branch**: `001-dump-runner-ftp-installer`
**Created**: 2026-01-03

## Entity Definitions

### 1. FTPConnectionConfig

Represents FTP connection parameters for connecting to a PS5.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| host | str | Yes | PS5 IP address (e.g., "192.168.1.100") |
| port | int | No | FTP port, default 2121 |
| username | str | No | FTP username, default "anonymous" |
| password | str | No | FTP password (stored in keyring, not here) |
| passive_mode | bool | No | Use passive FTP mode, default True |
| timeout | int | No | Connection timeout in seconds, default 30 |

**Validation Rules**:
- `host`: Valid IPv4 address or hostname
- `port`: Integer between 1-65535
- `timeout`: Integer between 5-300

**State Transitions**: N/A (configuration object)

---

### 2. FTPConnection

Represents an active FTP connection session.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| config | FTPConnectionConfig | Yes | Connection configuration |
| state | ConnectionState | Yes | Current connection state |
| connected_at | datetime | No | Timestamp when connected |
| last_activity | datetime | No | Last successful operation timestamp |

**ConnectionState Enum**:
- `DISCONNECTED` - No active connection
- `CONNECTING` - Connection in progress
- `CONNECTED` - Successfully connected
- `ERROR` - Connection failed

**Validation Rules**:
- State must be `CONNECTED` before any FTP operations

---

### 3. GameDump

Represents a discovered game dump directory on the PS5.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| path | str | Yes | Full FTP path (e.g., "/data/homebrew/GAME123") |
| name | str | Yes | Directory name (e.g., "GAME123") |
| location_type | LocationType | Yes | Where the dump is located |
| installation_status | InstallationStatus | Yes | Current dump_runner status |
| installed_version | str | No | Version of installed dump_runner |
| installed_at | datetime | No | When dump_runner was installed |
| is_experimental | bool | No | True if experimental files installed |

**LocationType Enum**:
- `INTERNAL` - /data/homebrew/
- `USB` - /mnt/usb#/homebrew/
- `EXTERNAL` - /mnt/ext#/homebrew/

**InstallationStatus Enum**:
- `NOT_INSTALLED` - No dump_runner files present
- `OFFICIAL` - Official version installed
- `EXPERIMENTAL` - Experimental version installed
- `UNKNOWN` - Files present but version unknown

**Validation Rules**:
- `path` must start with a valid scan path prefix
- `name` must not be empty or contain path separators

---

### 4. DumpRunnerRelease

Represents a version of dump_runner files (official or experimental).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | str | Yes | Version identifier (e.g., "v1.2.3" or "experimental") |
| source | ReleaseSource | Yes | Where the files came from |
| elf_path | str | Yes | Local path to dump_runner.elf |
| js_path | str | Yes | Local path to homebrew.js |
| release_date | datetime | No | GitHub release date (official only) |
| release_notes | str | No | Release notes/changelog |
| download_url | str | No | Original download URL (official only) |

**ReleaseSource Enum**:
- `GITHUB` - Official release from EchoStretch/dump_runner
- `LOCAL` - User-provided experimental files

**Validation Rules**:
- `elf_path` must point to an existing file with .elf extension
- `js_path` must point to an existing file with .js extension
- Both files must have size > 0 (basic integrity check)

---

### 5. UploadOperation

Represents a batch upload job.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str | Yes | Unique operation identifier (UUID) |
| release | DumpRunnerRelease | Yes | Files being uploaded |
| target_dumps | list[GameDump] | Yes | Selected dumps to receive files |
| state | OperationState | Yes | Current operation state |
| started_at | datetime | No | When operation started |
| completed_at | datetime | No | When operation finished |
| results | list[UploadResult] | No | Per-dump results |

**OperationState Enum**:
- `PENDING` - Not yet started
- `IN_PROGRESS` - Currently uploading
- `COMPLETED` - All uploads finished (may include failures)
- `CANCELLED` - User cancelled operation

---

### 6. UploadResult

Represents the result of uploading to a single dump.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| dump | GameDump | Yes | Target dump |
| success | bool | Yes | Whether upload succeeded |
| error_message | str | No | Error details if failed |
| elf_uploaded | bool | Yes | dump_runner.elf upload status |
| js_uploaded | bool | Yes | homebrew.js upload status |
| bytes_transferred | int | No | Total bytes transferred |
| duration_seconds | float | No | Time taken for this dump |

---

### 7. AppSettings

Represents persisted application settings.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| last_host | str | No | Last used FTP host |
| last_port | int | No | Last used FTP port |
| last_username | str | No | Last used username |
| passive_mode | bool | No | Preferred FTP mode |
| timeout | int | No | Preferred timeout |
| window_width | int | No | Main window width |
| window_height | int | No | Main window height |
| download_path | str | No | Path for downloaded releases |
| auto_check_updates | bool | No | Check for updates on startup |

**Storage**: JSON file at platform-specific config location

---

## Entity Relationships

```
FTPConnectionConfig ──1:1──▶ FTPConnection
                                   │
                                   ▼
                              GameDump (many discovered)
                                   │
                                   ▼
UploadOperation ◀──────────────────┘
       │                    (selected for upload)
       │
       ├── DumpRunnerRelease (files to upload)
       │
       └── UploadResult (per-dump outcome)
```

## State Diagrams

### FTPConnection State Machine

```
     ┌──────────────────────────────────────┐
     │                                      │
     ▼                                      │
DISCONNECTED ──connect()──▶ CONNECTING ─────┤
     ▲                          │           │
     │                          │           │
     │                   success│   failure │
     │                          ▼           │
     │                     CONNECTED        │
     │                          │           │
     │              disconnect()│           │
     └──────────────────────────┘           │
     ▲                                      │
     │                                      │
     └───────────ERROR◀─────────────────────┘
```

### UploadOperation State Machine

```
PENDING ──start()──▶ IN_PROGRESS ──finish()──▶ COMPLETED
                          │
                          │ cancel()
                          ▼
                      CANCELLED
```

## Persistence Strategy

| Entity | Storage Location | Format |
|--------|------------------|--------|
| AppSettings | `%APPDATA%/PS5DumpRunnerInstaller/settings.json` | JSON |
| FTP Password | System Keyring | Encrypted by OS |
| DumpRunnerRelease (cached) | `%APPDATA%/PS5DumpRunnerInstaller/releases/` | Binary files + metadata.json |
| GameDump | In-memory only | N/A (discovered fresh each session) |
| UploadOperation | In-memory only | N/A (transient) |
