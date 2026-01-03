"""Input validators for PS5 Dump Runner FTP Installer.

Provides validation functions for user inputs like IP addresses,
ports, and file paths.
"""

import re
from pathlib import Path
from typing import Optional, Tuple


# IPv4 address pattern
IPV4_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)

# Hostname pattern (simplified)
HOSTNAME_PATTERN = re.compile(
    r'^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$'
)


def validate_ip_address(ip: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an IPv4 address.

    Args:
        ip: IP address string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not ip or not ip.strip():
        return False, "IP address is required"

    ip = ip.strip()

    if IPV4_PATTERN.match(ip):
        return True, None

    return False, f"Invalid IP address format: {ip}"


def validate_hostname(hostname: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a hostname.

    Args:
        hostname: Hostname string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not hostname or not hostname.strip():
        return False, "Hostname is required"

    hostname = hostname.strip()

    if HOSTNAME_PATTERN.match(hostname):
        return True, None

    return False, f"Invalid hostname format: {hostname}"


def validate_host(host: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a host (IP address or hostname).

    Args:
        host: Host string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not host or not host.strip():
        return False, "Host is required"

    host = host.strip()

    # Try IP first
    is_valid_ip, _ = validate_ip_address(host)
    if is_valid_ip:
        return True, None

    # Try hostname
    is_valid_hostname, _ = validate_hostname(host)
    if is_valid_hostname:
        return True, None

    return False, f"Invalid host: {host}. Must be a valid IP address or hostname."


def validate_port(port: int) -> Tuple[bool, Optional[str]]:
    """
    Validate a port number.

    Args:
        port: Port number to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(port, int):
        try:
            port = int(port)
        except (ValueError, TypeError):
            return False, "Port must be a number"

    if port < 1 or port > 65535:
        return False, f"Port must be between 1 and 65535, got {port}"

    return True, None


def validate_timeout(timeout: int) -> Tuple[bool, Optional[str]]:
    """
    Validate a timeout value in seconds.

    Args:
        timeout: Timeout in seconds

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(timeout, int):
        try:
            timeout = int(timeout)
        except (ValueError, TypeError):
            return False, "Timeout must be a number"

    if timeout < 5 or timeout > 300:
        return False, f"Timeout must be between 5 and 300 seconds, got {timeout}"

    return True, None


def validate_file_path(path: Path, must_exist: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate a file path.

    Args:
        path: Path to validate
        must_exist: If True, file must exist

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return False, "File path is required"

    if isinstance(path, str):
        path = Path(path)

    if must_exist:
        if not path.exists():
            return False, f"File does not exist: {path}"
        if not path.is_file():
            return False, f"Path is not a file: {path}"

    return True, None


def validate_dump_runner_files(
    elf_path: Path,
    js_path: Path
) -> Tuple[bool, Optional[str]]:
    """
    Validate dump_runner.elf and homebrew.js files.

    Args:
        elf_path: Path to dump_runner.elf
        js_path: Path to homebrew.js

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate ELF file
    is_valid, error = validate_file_path(elf_path, must_exist=True)
    if not is_valid:
        return False, f"dump_runner.elf: {error}"

    if elf_path.stat().st_size == 0:
        return False, "dump_runner.elf is empty"

    # Validate JS file
    is_valid, error = validate_file_path(js_path, must_exist=True)
    if not is_valid:
        return False, f"homebrew.js: {error}"

    if js_path.stat().st_size == 0:
        return False, "homebrew.js is empty"

    return True, None


def validate_ftp_path(path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an FTP path format.

    Args:
        path: FTP path to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path or not path.strip():
        return False, "FTP path is required"

    path = path.strip()

    if not path.startswith("/"):
        return False, "FTP path must be absolute (start with /)"

    # Check for path traversal attempts
    if ".." in path:
        return False, "FTP path cannot contain '..'"

    return True, None
