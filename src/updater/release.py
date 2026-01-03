"""Release data models for PS5 Dump Runner FTP Installer.

Defines enums and dataclasses for dump_runner releases.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class ReleaseSource(Enum):
    """Source of dump_runner files."""
    GITHUB = "github"  # Official release from EchoStretch/dump_runner
    LOCAL = "local"    # User-provided experimental files


@dataclass
class DumpRunnerRelease:
    """Represents a version of dump_runner files."""
    version: str
    source: ReleaseSource
    elf_path: Path
    js_path: Path
    release_date: Optional[datetime] = None
    release_notes: Optional[str] = None
    download_url: Optional[str] = None

    @property
    def is_official(self) -> bool:
        """True if this is an official GitHub release."""
        return self.source == ReleaseSource.GITHUB

    @property
    def is_experimental(self) -> bool:
        """True if this is a local/experimental release."""
        return self.source == ReleaseSource.LOCAL

    @property
    def display_version(self) -> str:
        """Human-readable version string."""
        if self.is_experimental:
            return f"{self.version} (Experimental)"
        return self.version

    @property
    def files_exist(self) -> bool:
        """True if both required files exist."""
        return self.elf_path.exists() and self.js_path.exists()

    @property
    def files_valid(self) -> bool:
        """True if files exist and have content."""
        if not self.files_exist:
            return False
        return self.elf_path.stat().st_size > 0 and self.js_path.stat().st_size > 0

    @classmethod
    def from_local_files(
        cls,
        elf_path: Path,
        js_path: Path,
        version: str = "experimental"
    ) -> "DumpRunnerRelease":
        """
        Create a release from local files.

        Args:
            elf_path: Path to dump_runner.elf
            js_path: Path to homebrew.js
            version: Version string (default: "experimental")

        Returns:
            DumpRunnerRelease instance
        """
        return cls(
            version=version,
            source=ReleaseSource.LOCAL,
            elf_path=elf_path,
            js_path=js_path,
        )

    @classmethod
    def from_github(
        cls,
        version: str,
        elf_path: Path,
        js_path: Path,
        release_date: Optional[datetime] = None,
        release_notes: Optional[str] = None,
        download_url: Optional[str] = None
    ) -> "DumpRunnerRelease":
        """
        Create a release from GitHub download.

        Args:
            version: Version tag (e.g., "v1.2.3")
            elf_path: Path to downloaded dump_runner.elf
            js_path: Path to downloaded homebrew.js
            release_date: GitHub release date
            release_notes: Release notes/changelog
            download_url: Original download URL

        Returns:
            DumpRunnerRelease instance
        """
        return cls(
            version=version,
            source=ReleaseSource.GITHUB,
            elf_path=elf_path,
            js_path=js_path,
            release_date=release_date,
            release_notes=release_notes,
            download_url=download_url,
        )
