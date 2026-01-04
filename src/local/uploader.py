"""Local file uploader for game dumps.

Handles copying dump_runner files to local game dump directories.
"""

import logging
import shutil
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional, Union

from src.core.scanner_base import CompletionCallback, UploadResult
from src.ftp.scanner import GameDump

logger = logging.getLogger("ps5_dump_runner.local_uploader")


class LocalUploader:
    """Handles copying files to local game dumps.

    Implements UploaderProtocol for compatibility with UI code.
    """

    def __init__(self):
        """Initialize the local uploader."""
        self._cancelled = threading.Event()

    @property
    def is_cancelled(self) -> bool:
        """True if current operation was cancelled."""
        return self._cancelled.is_set()

    def cancel(self) -> None:
        """Cancel current upload operation."""
        self._cancelled.set()
        logger.info("Local upload cancelled by user")

    def reset_cancel(self) -> None:
        """Reset cancellation flag for new operation."""
        self._cancelled.clear()

    def upload_to_dump(
        self,
        dump: GameDump,
        elf_path: Union[str, Path],
        js_path: Union[str, Path],
        on_progress: Optional[Callable] = None,
    ) -> UploadResult:
        """
        Copy dump_runner files to a single game dump.

        Args:
            dump: Target game dump
            elf_path: Local path to dump_runner.elf (str or Path)
            js_path: Local path to homebrew.js (str or Path)
            on_progress: Optional callback for progress updates (ignored for local)

        Returns:
            UploadResult with success/failure status
        """
        # Convert to Path if needed
        elf_path = Path(elf_path) if isinstance(elf_path, str) else elf_path
        js_path = Path(js_path) if isinstance(js_path, str) else js_path

        start_time = time.time()
        dest_folder = Path(dump.path)

        try:
            # Verify destination folder exists
            if not dest_folder.exists():
                return UploadResult(
                    dump_path=dump.path,
                    success=False,
                    error_message=f"Destination folder does not exist: {dest_folder}",
                )

            if not dest_folder.is_dir():
                return UploadResult(
                    dump_path=dump.path,
                    success=False,
                    error_message=f"Destination is not a directory: {dest_folder}",
                )

            # Copy dump_runner.elf
            if not self._cancelled.is_set():
                dest_elf = dest_folder / "dump_runner.elf"
                logger.debug(f"Copying {elf_path.name} to {dest_elf}")
                shutil.copy2(elf_path, dest_elf)

            # Copy homebrew.js
            if not self._cancelled.is_set():
                dest_js = dest_folder / "homebrew.js"
                logger.debug(f"Copying {js_path.name} to {dest_js}")
                shutil.copy2(js_path, dest_js)

            if self._cancelled.is_set():
                return UploadResult(
                    dump_path=dump.path,
                    success=False,
                    error_message="Upload cancelled",
                )

            duration = time.time() - start_time
            logger.info(f"Successfully copied files to {dump.name} in {duration:.2f}s")

            return UploadResult(dump_path=dump.path, success=True)

        except PermissionError as e:
            duration = time.time() - start_time
            error_msg = (
                f"Permission denied: Cannot write to {dest_folder}. "
                f"Please check folder permissions."
            )
            logger.error(f"Permission error for {dump.name}: {e}")
            return UploadResult(
                dump_path=dump.path, success=False, error_message=error_msg
            )

        except OSError as e:
            duration = time.time() - start_time
            # Check for common OSError causes
            if "No space left on device" in str(e):
                error_msg = f"Not enough space on drive to copy files"
            elif "Read-only file system" in str(e):
                error_msg = f"Drive is read-only. Cannot write files."
            else:
                error_msg = f"File system error: {str(e)}"

            logger.error(f"OS error for {dump.name}: {e}")
            return UploadResult(
                dump_path=dump.path, success=False, error_message=error_msg
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error for {dump.name}: {e}", exc_info=True)
            return UploadResult(
                dump_path=dump.path, success=False, error_message=error_msg
            )

    def upload_batch(
        self,
        dumps: List[GameDump],
        elf_path: Union[str, Path],
        js_path: Union[str, Path],
        on_progress: Optional[Callable] = None,
        on_complete: Optional[CompletionCallback] = None,
    ) -> List[UploadResult]:
        """
        Copy files to multiple game dumps.

        Continues on individual failures, collects all results.

        Args:
            dumps: List of target game dumps
            elf_path: Local path to dump_runner.elf (str or Path)
            js_path: Local path to homebrew.js (str or Path)
            on_progress: Optional callback for progress updates (ignored for local)
            on_complete: Optional callback when each dump completes

        Returns:
            List of UploadResult for each dump
        """
        # Convert to Path if needed
        elf_path = Path(elf_path) if isinstance(elf_path, str) else elf_path
        js_path = Path(js_path) if isinstance(js_path, str) else js_path

        self.reset_cancel()
        results: List[UploadResult] = []

        for dump in dumps:
            if self._cancelled.is_set():
                # Add cancelled result for remaining dumps
                results.append(
                    UploadResult(
                        dump_path=dump.path,
                        success=False,
                        error_message="Upload cancelled",
                    )
                )
                continue

            result = self.upload_to_dump(dump, elf_path, js_path, on_progress)
            results.append(result)

            if on_complete:
                on_complete(dump, result)

        return results
