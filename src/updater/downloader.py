"""Release downloader for dump_runner files.

Downloads and caches official releases from GitHub.
"""

import io
import json
import logging
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from src.config.paths import get_releases_cache_dir
from src.updater.github_client import (
    GitHubClient,
    GitHubRelease,
    GitHubConnectionError,
    GitHubError,
)
from src.updater.release import DumpRunnerRelease, ReleaseSource

logger = logging.getLogger("ps5_dump_runner.downloader")


@dataclass
class DownloadProgress:
    """Progress information for a download operation."""
    asset_name: str
    bytes_downloaded: int
    total_bytes: int
    current_file: int
    total_files: int

    @property
    def percentage(self) -> float:
        """Download progress as percentage."""
        if self.total_bytes == 0:
            return 0.0
        return (self.bytes_downloaded / self.total_bytes) * 100

    @property
    def overall_percentage(self) -> float:
        """Overall progress including all files."""
        if self.total_files == 0:
            return 0.0
        file_progress = (self.current_file - 1) / self.total_files
        current_progress = self.percentage / 100 / self.total_files
        return (file_progress + current_progress) * 100


# Progress callback type
ProgressCallback = Callable[[DownloadProgress], None]


class ReleaseDownloader:
    """Downloads and caches dump_runner releases from GitHub."""

    METADATA_FILE = "release_metadata.json"
    ELF_FILE = "dump_runner.elf"
    JS_FILE = "homebrew.js"

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the downloader.

        Args:
            cache_dir: Directory for caching releases (default: app cache dir)
        """
        self._cache_dir = cache_dir or get_releases_cache_dir()
        self._client: Optional[GitHubClient] = None

    def _get_client(self) -> GitHubClient:
        """Get or create GitHub client."""
        if self._client is None:
            self._client = GitHubClient()
        return self._client

    def _get_release_dir(self, version: str) -> Path:
        """Get the cache directory for a specific release version."""
        # Sanitize version for use as directory name
        safe_version = "".join(c if c.isalnum() or c in "._-" else "_" for c in version)
        return self._cache_dir / safe_version

    def _read_metadata(self, release_dir: Path) -> Optional[dict]:
        """Read cached release metadata."""
        metadata_path = release_dir / self.METADATA_FILE
        if not metadata_path.exists():
            return None
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to read metadata: {e}")
            return None

    def _write_metadata(self, release_dir: Path, release: GitHubRelease) -> None:
        """Write release metadata to cache."""
        metadata = {
            "version": release.tag_name,
            "name": release.name,
            "published_at": release.published_at.isoformat() if release.published_at else None,
            "body": release.body,
            "html_url": release.html_url,
            "downloaded_at": datetime.now().isoformat(),
        }
        metadata_path = release_dir / self.METADATA_FILE
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    def get_cached_release(self, version: Optional[str] = None) -> Optional[DumpRunnerRelease]:
        """
        Get a cached release if available.

        Args:
            version: Specific version to get, or None for latest cached

        Returns:
            DumpRunnerRelease if cached and valid, None otherwise
        """
        if version:
            release_dir = self._get_release_dir(version)
            return self._load_cached_release(release_dir)
        else:
            # Find the most recently downloaded release
            latest = self._find_latest_cached()
            if latest:
                return self._load_cached_release(latest)
        return None

    def _find_latest_cached(self) -> Optional[Path]:
        """Find the most recently downloaded release directory."""
        if not self._cache_dir.exists():
            return None

        latest_time = None
        latest_dir = None

        for release_dir in self._cache_dir.iterdir():
            if not release_dir.is_dir():
                continue
            metadata = self._read_metadata(release_dir)
            if not metadata:
                continue

            # Check if files exist
            elf_path = release_dir / self.ELF_FILE
            js_path = release_dir / self.JS_FILE
            if not (elf_path.exists() and js_path.exists()):
                continue

            # Get download time
            downloaded_at = metadata.get("downloaded_at")
            if downloaded_at:
                try:
                    download_time = datetime.fromisoformat(downloaded_at)
                    if latest_time is None or download_time > latest_time:
                        latest_time = download_time
                        latest_dir = release_dir
                except ValueError:
                    pass

        return latest_dir

    def _load_cached_release(self, release_dir: Path) -> Optional[DumpRunnerRelease]:
        """Load a release from cache directory."""
        if not release_dir.exists():
            return None

        elf_path = release_dir / self.ELF_FILE
        js_path = release_dir / self.JS_FILE

        if not (elf_path.exists() and js_path.exists()):
            logger.debug(f"Cached release missing files: {release_dir}")
            return None

        metadata = self._read_metadata(release_dir)
        if not metadata:
            logger.debug(f"Cached release missing metadata: {release_dir}")
            return None

        # Parse release date
        release_date = None
        if metadata.get("published_at"):
            try:
                release_date = datetime.fromisoformat(metadata["published_at"])
            except ValueError:
                pass

        return DumpRunnerRelease.from_github(
            version=metadata.get("version", release_dir.name),
            elf_path=elf_path,
            js_path=js_path,
            release_date=release_date,
            release_notes=metadata.get("body"),
            download_url=metadata.get("html_url"),
        )

    def _extract_zip(self, content: bytes, release_dir: Path) -> None:
        """
        Extract dump_runner.zip contents to release directory.

        Looks for dump_runner.elf and homebrew.js in the zip file,
        handling nested directories if present.

        Args:
            content: Zip file content as bytes
            release_dir: Directory to extract files to

        Raises:
            ValueError: If required files not found in zip
        """
        elf_path = release_dir / self.ELF_FILE
        js_path = release_dir / self.JS_FILE

        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            # List all files in the zip
            file_list = zf.namelist()
            logger.debug(f"Zip contains: {file_list}")

            # Find dump_runner.elf and homebrew.js (may be in subdirectories)
            elf_found = None
            js_found = None

            for name in file_list:
                basename = name.split("/")[-1]
                if basename == self.ELF_FILE:
                    elf_found = name
                elif basename == self.JS_FILE:
                    js_found = name

            if not elf_found:
                raise ValueError(f"{self.ELF_FILE} not found in zip file")
            if not js_found:
                raise ValueError(f"{self.JS_FILE} not found in zip file")

            # Extract the files
            logger.debug(f"Extracting {elf_found} -> {elf_path}")
            with zf.open(elf_found) as src, open(elf_path, "wb") as dst:
                dst.write(src.read())

            logger.debug(f"Extracting {js_found} -> {js_path}")
            with zf.open(js_found) as src, open(js_path, "wb") as dst:
                dst.write(src.read())

            logger.info(f"Extracted {self.ELF_FILE} and {self.JS_FILE} from zip")

    def download_release(
        self,
        release: GitHubRelease,
        progress_callback: Optional[ProgressCallback] = None,
        force: bool = False
    ) -> DumpRunnerRelease:
        """
        Download a release from GitHub.

        Args:
            release: GitHubRelease to download
            progress_callback: Optional callback for progress updates
            force: Force download even if already cached

        Returns:
            DumpRunnerRelease with local file paths

        Raises:
            GitHubConnectionError: If download fails
            GitHubError: For other errors
            ValueError: If release doesn't have required files
        """
        if not release.is_complete:
            raise ValueError(
                f"Release {release.tag_name} is missing required files "
                f"(has_elf={release.has_elf}, has_js={release.has_js}, has_zip={release.has_zip})"
            )

        release_dir = self._get_release_dir(release.tag_name)

        # Check if already cached
        if not force:
            cached = self._load_cached_release(release_dir)
            if cached and cached.files_valid:
                logger.info(f"Using cached release: {release.tag_name}")
                return cached

        # Create release directory
        release_dir.mkdir(parents=True, exist_ok=True)

        client = self._get_client()
        elf_path = release_dir / self.ELF_FILE
        js_path = release_dir / self.JS_FILE

        try:
            # Check if release has a zip file (bundled assets)
            zip_asset = release.get_zip_asset()
            if zip_asset:
                logger.info(f"Downloading dump_runner.zip...")

                def zip_progress(downloaded: int, total: int):
                    if progress_callback:
                        progress_callback(DownloadProgress(
                            asset_name="dump_runner.zip",
                            bytes_downloaded=downloaded,
                            total_bytes=total,
                            current_file=1,
                            total_files=1,
                        ))

                content = client.download_asset(zip_asset, callback=zip_progress)

                # Extract the zip file
                logger.info("Extracting dump_runner.zip...")
                self._extract_zip(content, release_dir)

            else:
                # Download individual files
                # Download ELF file
                elf_asset = release.get_elf_asset()
                if elf_asset:
                    logger.info(f"Downloading {self.ELF_FILE}...")

                    def elf_progress(downloaded: int, total: int):
                        if progress_callback:
                            progress_callback(DownloadProgress(
                                asset_name=self.ELF_FILE,
                                bytes_downloaded=downloaded,
                                total_bytes=total,
                                current_file=1,
                                total_files=2,
                            ))

                    content = client.download_asset(elf_asset, callback=elf_progress)
                    with open(elf_path, "wb") as f:
                        f.write(content)

                # Download JS file
                js_asset = release.get_js_asset()
                if js_asset:
                    logger.info(f"Downloading {self.JS_FILE}...")

                    def js_progress(downloaded: int, total: int):
                        if progress_callback:
                            progress_callback(DownloadProgress(
                                asset_name=self.JS_FILE,
                                bytes_downloaded=downloaded,
                                total_bytes=total,
                                current_file=2,
                                total_files=2,
                            ))

                    content = client.download_asset(js_asset, callback=js_progress)
                    with open(js_path, "wb") as f:
                        f.write(content)

            # Write metadata
            self._write_metadata(release_dir, release)

            logger.info(f"Downloaded release {release.tag_name} to {release_dir}")

            return DumpRunnerRelease.from_github(
                version=release.tag_name,
                elf_path=elf_path,
                js_path=js_path,
                release_date=release.published_at,
                release_notes=release.body,
                download_url=release.html_url,
            )

        except Exception as e:
            # Clean up partial download
            logger.error(f"Download failed: {e}")
            if release_dir.exists():
                try:
                    shutil.rmtree(release_dir)
                except OSError:
                    pass
            raise

    def download_latest(
        self,
        progress_callback: Optional[ProgressCallback] = None,
        force: bool = False
    ) -> DumpRunnerRelease:
        """
        Download the latest release from GitHub.

        Args:
            progress_callback: Optional callback for progress updates
            force: Force download even if already cached

        Returns:
            DumpRunnerRelease with local file paths

        Raises:
            GitHubConnectionError: If download fails
            GitHubError: For other errors
        """
        client = self._get_client()
        release = client.get_latest_release()
        return self.download_release(release, progress_callback, force)

    def get_latest_release_info(self) -> GitHubRelease:
        """
        Get information about the latest release without downloading.

        Returns:
            GitHubRelease with release information

        Raises:
            GitHubConnectionError: If unable to connect
            GitHubError: For other errors
        """
        client = self._get_client()
        return client.get_latest_release()

    def clear_cache(self, version: Optional[str] = None) -> int:
        """
        Clear cached releases.

        Args:
            version: Specific version to clear, or None for all

        Returns:
            Number of releases cleared
        """
        if version:
            release_dir = self._get_release_dir(version)
            if release_dir.exists():
                shutil.rmtree(release_dir)
                logger.info(f"Cleared cache for version: {version}")
                return 1
            return 0
        else:
            count = 0
            if self._cache_dir.exists():
                for release_dir in self._cache_dir.iterdir():
                    if release_dir.is_dir() and release_dir.name != ".":
                        try:
                            shutil.rmtree(release_dir)
                            count += 1
                        except OSError as e:
                            logger.warning(f"Failed to clear {release_dir}: {e}")
            logger.info(f"Cleared {count} cached releases")
            return count

    def list_cached_versions(self) -> list[str]:
        """
        List all cached release versions.

        Returns:
            List of version strings
        """
        versions = []
        if self._cache_dir.exists():
            for release_dir in self._cache_dir.iterdir():
                if release_dir.is_dir():
                    metadata = self._read_metadata(release_dir)
                    if metadata:
                        versions.append(metadata.get("version", release_dir.name))
        return sorted(versions, reverse=True)

    def close(self) -> None:
        """Clean up resources."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "ReleaseDownloader":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
