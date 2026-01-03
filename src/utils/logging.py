"""Logging configuration for PS5 Dump Runner FTP Installer.

Provides centralized logging with PII redaction to ensure passwords
and sensitive data are never written to log files.
"""

import logging
import re
import sys
from pathlib import Path
from typing import Optional


# PII patterns to redact from logs
PII_PATTERNS = [
    # Password in various formats
    (re.compile(r'(password["\s:=]+)[^\s,}\]]+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(passwd["\s:=]+)[^\s,}\]]+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(pass["\s:=]+)[^\s,}\]]+', re.IGNORECASE), r'\1[REDACTED]'),
    # FTP URLs with credentials
    (re.compile(r'ftp://[^:]+:[^@]+@'), 'ftp://[REDACTED]@'),
    # IP addresses (partial redaction for privacy)
    (re.compile(r'(\d+\.\d+\.)\d+\.\d+'), r'\1*.*'),
]


class PIIRedactingFormatter(logging.Formatter):
    """Custom formatter that redacts PII from log messages."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record, redacting any PII."""
        message = super().format(record)
        for pattern, replacement in PII_PATTERNS:
            message = pattern.sub(replacement, message)
        return message


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    console: bool = True
) -> logging.Logger:
    """
    Configure application logging with PII redaction.

    Args:
        level: Logging level (default INFO)
        log_file: Optional file path for log output
        console: Whether to output to console (default True)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("ps5_dump_runner")
    logger.setLevel(level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatter with PII redaction
    formatter = PIIRedactingFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "ps5_dump_runner") -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (default is app logger)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
