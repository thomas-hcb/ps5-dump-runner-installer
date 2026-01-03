"""Background task helpers for PS5 Dump Runner FTP Installer.

Provides thread-safe utilities for running background operations
and updating the GUI from worker threads.
"""

import queue
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Generic, Optional, TypeVar


T = TypeVar("T")


class TaskStatus(Enum):
    """Status of a background task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult(Generic[T]):
    """Result of a background task."""
    status: TaskStatus
    result: Optional[T] = None
    error: Optional[Exception] = None


class ThreadedTask(Generic[T]):
    """
    Runs a callable in a background thread with progress reporting.

    Usage:
        def long_operation(on_progress):
            for i in range(100):
                # Do work...
                on_progress(i / 100)
            return "done"

        task = ThreadedTask(long_operation)
        task.start()

        # In GUI update loop:
        while task.is_running:
            progress = task.get_progress()
            if progress:
                update_progress_bar(progress)

        result = task.get_result()
    """

    def __init__(
        self,
        target: Callable[..., T],
        args: tuple = (),
        kwargs: Optional[dict] = None,
        on_complete: Optional[Callable[[TaskResult[T]], None]] = None
    ):
        """
        Initialize a threaded task.

        Args:
            target: Callable to run in background
            args: Positional arguments for target
            kwargs: Keyword arguments for target
            on_complete: Callback when task finishes (called from worker thread)
        """
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}
        self._on_complete = on_complete

        self._thread: Optional[threading.Thread] = None
        self._progress_queue: queue.Queue[float] = queue.Queue()
        self._result: Optional[TaskResult[T]] = None
        self._cancelled = threading.Event()
        self._status = TaskStatus.PENDING

    @property
    def status(self) -> TaskStatus:
        """Current task status."""
        return self._status

    @property
    def is_running(self) -> bool:
        """True if task is currently running."""
        return self._status == TaskStatus.RUNNING

    @property
    def is_cancelled(self) -> bool:
        """True if task was cancelled."""
        return self._cancelled.is_set()

    def start(self) -> None:
        """Start the background task."""
        if self._status != TaskStatus.PENDING:
            raise RuntimeError("Task already started")

        self._status = TaskStatus.RUNNING
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        """Request cancellation of the task."""
        self._cancelled.set()

    def _run(self) -> None:
        """Internal method that runs in the background thread."""
        try:
            # Inject progress callback into kwargs if target expects it
            result = self._target(*self._args, **self._kwargs)

            if self._cancelled.is_set():
                self._result = TaskResult(status=TaskStatus.CANCELLED)
                self._status = TaskStatus.CANCELLED
            else:
                self._result = TaskResult(status=TaskStatus.COMPLETED, result=result)
                self._status = TaskStatus.COMPLETED

        except Exception as e:
            self._result = TaskResult(status=TaskStatus.FAILED, error=e)
            self._status = TaskStatus.FAILED

        if self._on_complete:
            self._on_complete(self._result)

    def report_progress(self, progress: float) -> None:
        """
        Report progress from within the task.

        Args:
            progress: Progress value between 0.0 and 1.0
        """
        self._progress_queue.put(min(1.0, max(0.0, progress)))

    def get_progress(self) -> Optional[float]:
        """
        Get the latest progress update.

        Returns:
            Progress value (0.0-1.0) or None if no update available
        """
        try:
            return self._progress_queue.get_nowait()
        except queue.Empty:
            return None

    def get_all_progress(self) -> list[float]:
        """Get all pending progress updates."""
        updates = []
        while True:
            try:
                updates.append(self._progress_queue.get_nowait())
            except queue.Empty:
                break
        return updates

    def get_result(self, timeout: Optional[float] = None) -> TaskResult[T]:
        """
        Wait for task completion and return result.

        Args:
            timeout: Maximum time to wait (None = forever)

        Returns:
            TaskResult with status and result/error

        Raises:
            TimeoutError: If timeout expires before task completes
        """
        if self._thread:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                raise TimeoutError("Task did not complete within timeout")

        return self._result or TaskResult(status=TaskStatus.PENDING)


class GUIUpdateQueue:
    """
    Thread-safe queue for passing updates from worker threads to GUI.

    Usage:
        # In main thread:
        update_queue = GUIUpdateQueue()

        # In worker thread:
        update_queue.put("status", "Connecting...")
        update_queue.put("progress", 0.5)

        # In GUI update loop (main thread):
        def poll_updates():
            for update_type, data in update_queue.get_all():
                if update_type == "status":
                    status_label.config(text=data)
                elif update_type == "progress":
                    progress_bar.set(data)
            root.after(100, poll_updates)
    """

    def __init__(self):
        """Initialize the update queue."""
        self._queue: queue.Queue[tuple[str, Any]] = queue.Queue()

    def put(self, update_type: str, data: Any) -> None:
        """
        Put an update in the queue (thread-safe).

        Args:
            update_type: Type identifier for the update
            data: Update data
        """
        self._queue.put((update_type, data))

    def get(self) -> Optional[tuple[str, Any]]:
        """
        Get a single update from the queue.

        Returns:
            Tuple of (update_type, data) or None if empty
        """
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def get_all(self) -> list[tuple[str, Any]]:
        """
        Get all pending updates from the queue.

        Returns:
            List of (update_type, data) tuples
        """
        updates = []
        while True:
            try:
                updates.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return updates

    def clear(self) -> None:
        """Clear all pending updates."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
