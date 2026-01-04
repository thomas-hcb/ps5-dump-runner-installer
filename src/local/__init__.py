"""Local drive operations module.

This module provides:
- Volume detection for Windows, macOS, and Linux
- LocalScanner: Scan game dumps on local/portable drives
- LocalUploader: Copy dump_runner files to local folders
"""

from src.local.scanner import LocalScanner
from src.local.uploader import LocalUploader
from src.local.volumes import get_available_volumes, VolumeInfo

__all__ = ["LocalScanner", "LocalUploader", "get_available_volumes", "VolumeInfo"]
