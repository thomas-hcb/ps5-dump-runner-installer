"""File uploader for PS5 Dump Runner FTP Installer.

Handles uploading dump_runner files to game dumps via FTP.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional
import threading

from src.ftp.connection import FTPConnectionManager
from src.ftp.scanner import GameDump
from src.ftp.exceptions import FTPNotConnectedError, FTPUploadError


@dataclass
class UploadProgress:
    """Progress information for an upload operation."""
    dump_path: str
    file_name: str
    bytes_sent: int
    bytes_total: int

    @property
    def percent(self) -> float:
        """Upload progress as percentage (0-100)."""
        if self.bytes_total == 0:
            return 0.0
        return (self.bytes_sent / self.bytes_total) * 100.0


@dataclass
class UploadResult:
    """Result of uploading to a single dump."""
    dump_path: str
    success: bool
    error_message: Optional[str] = None
    elf_uploaded: bool = False
    js_uploaded: bool = False
    bytes_transferred: int = 0
    duration_seconds: float = 0.0


# Type alias for progress callback
ProgressCallback = Callable[[UploadProgress], None]


class FileUploader:
    """Handles file uploads to game dumps."""

    # Block size for FTP transfers (8KB)
    BLOCK_SIZE = 8192

    def __init__(self, connection: FTPConnectionManager):
        """
        Initialize the uploader.

        Args:
            connection: Active FTP connection manager
        """
        self._connection = connection
        self._cancelled = threading.Event()
        self._current_upload: Optional[str] = None

    @property
    def is_cancelled(self) -> bool:
        """True if current operation was cancelled."""
        return self._cancelled.is_set()

    def cancel(self) -> None:
        """Cancel current upload operation."""
        self._cancelled.set()

    def reset_cancel(self) -> None:
        """Reset cancellation flag for new operation."""
        self._cancelled.clear()

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
        if not self._connection.is_connected:
            return UploadResult(
                dump_path=dump.path,
                success=False,
                error_message="Not connected to FTP"
            )

        import time
        start_time = time.time()
        total_bytes = 0
        elf_uploaded = False
        js_uploaded = False

        try:
            ftp = self._connection.ftp

            # Upload dump_runner.elf
            if not self._cancelled.is_set():
                bytes_sent = self._upload_file(
                    ftp,
                    elf_path,
                    f"{dump.path}/dump_runner.elf",
                    on_progress
                )
                total_bytes += bytes_sent
                elf_uploaded = True

            # Upload homebrew.js
            if not self._cancelled.is_set():
                bytes_sent = self._upload_file(
                    ftp,
                    js_path,
                    f"{dump.path}/homebrew.js",
                    on_progress
                )
                total_bytes += bytes_sent
                js_uploaded = True

            duration = time.time() - start_time

            if self._cancelled.is_set():
                return UploadResult(
                    dump_path=dump.path,
                    success=False,
                    error_message="Upload cancelled",
                    elf_uploaded=elf_uploaded,
                    js_uploaded=js_uploaded,
                    bytes_transferred=total_bytes,
                    duration_seconds=duration
                )

            return UploadResult(
                dump_path=dump.path,
                success=True,
                elf_uploaded=True,
                js_uploaded=True,
                bytes_transferred=total_bytes,
                duration_seconds=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            return UploadResult(
                dump_path=dump.path,
                success=False,
                error_message=str(e),
                elf_uploaded=elf_uploaded,
                js_uploaded=js_uploaded,
                bytes_transferred=total_bytes,
                duration_seconds=duration
            )

    def _upload_file(
        self,
        ftp,
        local_path: Path,
        remote_path: str,
        on_progress: Optional[ProgressCallback]
    ) -> int:
        """
        Upload a single file via FTP.

        Args:
            ftp: FTP connection
            local_path: Local file path
            remote_path: Remote FTP path
            on_progress: Progress callback

        Returns:
            Number of bytes transferred

        Raises:
            FTPUploadError: If upload fails
        """
        file_size = local_path.stat().st_size
        bytes_sent = 0
        file_name = local_path.name

        def callback(block: bytes) -> None:
            nonlocal bytes_sent
            bytes_sent += len(block)

            if on_progress and not self._cancelled.is_set():
                progress = UploadProgress(
                    dump_path=remote_path.rsplit("/", 1)[0],
                    file_name=file_name,
                    bytes_sent=bytes_sent,
                    bytes_total=file_size
                )
                on_progress(progress)

        try:
            with open(local_path, "rb") as f:
                ftp.storbinary(
                    f"STOR {remote_path}",
                    f,
                    blocksize=self.BLOCK_SIZE,
                    callback=callback
                )
        except Exception as e:
            raise FTPUploadError(file_name, remote_path, e)

        return bytes_sent

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

        Args:
            dumps: List of target game dumps
            elf_path: Local path to dump_runner.elf
            js_path: Local path to homebrew.js
            on_progress: Optional callback for progress updates
            on_dump_complete: Optional callback when each dump completes

        Returns:
            List of UploadResult for each dump
        """
        self.reset_cancel()
        results: List[UploadResult] = []

        for dump in dumps:
            if self._cancelled.is_set():
                # Add cancelled result for remaining dumps
                results.append(UploadResult(
                    dump_path=dump.path,
                    success=False,
                    error_message="Upload cancelled"
                ))
                continue

            result = self.upload_to_dump(dump, elf_path, js_path, on_progress)
            results.append(result)

            if on_dump_complete:
                on_dump_complete(result)

        return results

    def get_batch_summary(self, results: List[UploadResult]) -> dict:
        """
        Get summary statistics for a batch upload.

        Args:
            results: List of upload results

        Returns:
            Dictionary with summary statistics
        """
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        total_bytes = sum(r.bytes_transferred for r in results)
        total_time = sum(r.duration_seconds for r in results)

        return {
            "total": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "bytes_transferred": total_bytes,
            "duration_seconds": total_time,
            "failures": [(r.dump_path, r.error_message) for r in failed]
        }
