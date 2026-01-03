"""FTP-specific exceptions for PS5 Dump Runner FTP Installer.

Custom exception hierarchy for FTP operations to provide
clear error handling and user-friendly messages.
"""


class FTPError(Exception):
    """Base exception for all FTP-related errors."""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.message = message
        self.original_error = original_error

    def __str__(self) -> str:
        if self.original_error:
            return f"{self.message}: {self.original_error}"
        return self.message


class FTPConnectionError(FTPError):
    """Failed to establish FTP connection."""

    def __init__(self, host: str, port: int, original_error: Exception = None):
        self.host = host
        self.port = port
        message = f"Failed to connect to {host}:{port}"
        super().__init__(message, original_error)


class FTPAuthenticationError(FTPError):
    """FTP authentication (login) failed."""

    def __init__(self, username: str, original_error: Exception = None):
        self.username = username
        message = f"Authentication failed for user '{username}'"
        super().__init__(message, original_error)


class FTPNotConnectedError(FTPError):
    """Operation attempted without active FTP connection."""

    def __init__(self, operation: str = "Operation"):
        message = f"{operation} requires an active FTP connection"
        super().__init__(message)


class FTPTimeoutError(FTPError):
    """FTP operation timed out."""

    def __init__(self, operation: str = "Operation", timeout: int = 30):
        self.timeout = timeout
        message = f"{operation} timed out after {timeout} seconds"
        super().__init__(message)


class FTPUploadError(FTPError):
    """Failed to upload file via FTP."""

    def __init__(
        self,
        file_name: str,
        remote_path: str,
        original_error: Exception = None
    ):
        self.file_name = file_name
        self.remote_path = remote_path
        message = f"Failed to upload '{file_name}' to '{remote_path}'"
        super().__init__(message, original_error)


class FTPPathError(FTPError):
    """FTP path operation failed (change directory, list, etc.)."""

    def __init__(self, path: str, operation: str, original_error: Exception = None):
        self.path = path
        self.operation = operation
        message = f"Failed to {operation} path '{path}'"
        super().__init__(message, original_error)


class FTPPermissionError(FTPError):
    """FTP permission denied for operation."""

    def __init__(self, path: str, operation: str, original_error: Exception = None):
        self.path = path
        self.operation = operation
        message = f"Permission denied: cannot {operation} '{path}'"
        super().__init__(message, original_error)
