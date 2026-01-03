"""GitHub API client for dump_runner releases.

Fetches release information and assets from the EchoStretch/dump_runner repository.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests

logger = logging.getLogger("ps5_dump_runner.github_client")


# GitHub API constants
GITHUB_API_BASE = "https://api.github.com"
REPO_OWNER = "EchoStretch"
REPO_NAME = "dump_runner"
RELEASES_URL = f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/releases"

# Request timeout in seconds
REQUEST_TIMEOUT = 30


class GitHubError(Exception):
    """Base exception for GitHub API errors."""
    pass


class GitHubConnectionError(GitHubError):
    """Raised when unable to connect to GitHub."""
    pass


class GitHubRateLimitError(GitHubError):
    """Raised when GitHub rate limit is exceeded."""
    pass


class GitHubNotFoundError(GitHubError):
    """Raised when repository or release is not found."""
    pass


@dataclass
class ReleaseAsset:
    """Represents a downloadable asset from a GitHub release."""
    name: str
    download_url: str
    size: int
    content_type: str

    @classmethod
    def from_api_response(cls, data: dict) -> "ReleaseAsset":
        """Create ReleaseAsset from GitHub API response."""
        return cls(
            name=data.get("name", ""),
            download_url=data.get("browser_download_url", ""),
            size=data.get("size", 0),
            content_type=data.get("content_type", ""),
        )


@dataclass
class GitHubRelease:
    """Represents a GitHub release with its assets."""
    tag_name: str
    name: str
    published_at: Optional[datetime]
    body: str
    html_url: str
    assets: List[ReleaseAsset]
    prerelease: bool
    draft: bool

    @property
    def version(self) -> str:
        """Get version string from tag name."""
        return self.tag_name

    @property
    def release_notes(self) -> str:
        """Get release notes (body)."""
        return self.body

    @property
    def has_elf(self) -> bool:
        """Check if release has dump_runner.elf asset."""
        return any(a.name == "dump_runner.elf" for a in self.assets)

    @property
    def has_js(self) -> bool:
        """Check if release has homebrew.js asset."""
        return any(a.name == "homebrew.js" for a in self.assets)

    @property
    def has_zip(self) -> bool:
        """Check if release has dump_runner.zip asset (bundled files)."""
        return any(a.name == "dump_runner.zip" for a in self.assets)

    @property
    def is_complete(self) -> bool:
        """Check if release has required files (either separate or bundled in zip)."""
        return (self.has_elf and self.has_js) or self.has_zip

    def get_asset(self, name: str) -> Optional[ReleaseAsset]:
        """Get asset by name."""
        for asset in self.assets:
            if asset.name == name:
                return asset
        return None

    def get_elf_asset(self) -> Optional[ReleaseAsset]:
        """Get the dump_runner.elf asset."""
        return self.get_asset("dump_runner.elf")

    def get_js_asset(self) -> Optional[ReleaseAsset]:
        """Get the homebrew.js asset."""
        return self.get_asset("homebrew.js")

    def get_zip_asset(self) -> Optional[ReleaseAsset]:
        """Get the dump_runner.zip asset (bundled files)."""
        return self.get_asset("dump_runner.zip")

    @classmethod
    def from_api_response(cls, data: dict) -> "GitHubRelease":
        """Create GitHubRelease from GitHub API response."""
        # Parse published_at date
        published_at = None
        if data.get("published_at"):
            try:
                published_at = datetime.fromisoformat(
                    data["published_at"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Parse assets
        assets = [
            ReleaseAsset.from_api_response(a)
            for a in data.get("assets", [])
        ]

        return cls(
            tag_name=data.get("tag_name", ""),
            name=data.get("name", ""),
            published_at=published_at,
            body=data.get("body", ""),
            html_url=data.get("html_url", ""),
            assets=assets,
            prerelease=data.get("prerelease", False),
            draft=data.get("draft", False),
        )


class GitHubClient:
    """Client for interacting with GitHub API for dump_runner releases."""

    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        """
        Initialize GitHub client.

        Args:
            timeout: Request timeout in seconds
        """
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PS5DumpRunnerInstaller/1.0",
        })

    def _make_request(self, url: str) -> dict:
        """
        Make a GET request to GitHub API.

        Args:
            url: Full URL to request

        Returns:
            JSON response as dict

        Raises:
            GitHubConnectionError: If unable to connect
            GitHubRateLimitError: If rate limit exceeded
            GitHubNotFoundError: If resource not found
            GitHubError: For other errors
        """
        try:
            logger.debug(f"Making request to: {url}")
            response = self._session.get(url, timeout=self._timeout)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                raise GitHubNotFoundError(f"Resource not found: {url}")
            elif response.status_code == 403:
                # Check for rate limiting
                if "rate limit" in response.text.lower():
                    raise GitHubRateLimitError("GitHub API rate limit exceeded")
                raise GitHubError(f"Access denied: {response.text}")
            else:
                raise GitHubError(
                    f"GitHub API error {response.status_code}: {response.text}"
                )

        except requests.exceptions.Timeout:
            logger.error("GitHub request timed out")
            raise GitHubConnectionError("Request timed out connecting to GitHub")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"GitHub connection error: {e}")
            raise GitHubConnectionError(
                "Unable to connect to GitHub. Check your internet connection."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub request error: {e}")
            raise GitHubError(f"Request failed: {e}")

    def get_latest_release(self) -> GitHubRelease:
        """
        Get the latest release from the repository.

        Returns:
            GitHubRelease representing the latest release

        Raises:
            GitHubConnectionError: If unable to connect
            GitHubNotFoundError: If no releases found
            GitHubError: For other errors
        """
        url = f"{RELEASES_URL}/latest"
        logger.info("Fetching latest release from GitHub")

        data = self._make_request(url)
        release = GitHubRelease.from_api_response(data)

        logger.info(f"Found latest release: {release.tag_name}")
        return release

    def get_releases(self, limit: int = 10) -> List[GitHubRelease]:
        """
        Get recent releases from the repository.

        Args:
            limit: Maximum number of releases to fetch

        Returns:
            List of GitHubRelease objects

        Raises:
            GitHubConnectionError: If unable to connect
            GitHubError: For other errors
        """
        url = f"{RELEASES_URL}?per_page={limit}"
        logger.info(f"Fetching up to {limit} releases from GitHub")

        data = self._make_request(url)

        if isinstance(data, list):
            releases = [
                GitHubRelease.from_api_response(r)
                for r in data
                if not r.get("draft", False)  # Skip drafts
            ]
            logger.info(f"Found {len(releases)} releases")
            return releases
        else:
            return []

    def get_release_by_tag(self, tag: str) -> GitHubRelease:
        """
        Get a specific release by tag name.

        Args:
            tag: Release tag (e.g., "v1.0.0")

        Returns:
            GitHubRelease for the specified tag

        Raises:
            GitHubNotFoundError: If release not found
            GitHubError: For other errors
        """
        url = f"{RELEASES_URL}/tags/{tag}"
        logger.info(f"Fetching release with tag: {tag}")

        data = self._make_request(url)
        release = GitHubRelease.from_api_response(data)

        logger.info(f"Found release: {release.tag_name}")
        return release

    def download_asset(
        self,
        asset: ReleaseAsset,
        callback: Optional[callable] = None
    ) -> bytes:
        """
        Download a release asset.

        Args:
            asset: ReleaseAsset to download
            callback: Optional progress callback(bytes_downloaded, total_bytes)

        Returns:
            Downloaded file content as bytes

        Raises:
            GitHubConnectionError: If unable to connect
            GitHubError: For other errors
        """
        try:
            logger.info(f"Downloading asset: {asset.name} ({asset.size} bytes)")

            response = self._session.get(
                asset.download_url,
                stream=True,
                timeout=self._timeout
            )
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", asset.size))
            chunks = []
            downloaded = 0

            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    if callback:
                        callback(downloaded, total_size)

            content = b"".join(chunks)
            logger.info(f"Downloaded {len(content)} bytes for {asset.name}")
            return content

        except requests.exceptions.Timeout:
            raise GitHubConnectionError("Download timed out")
        except requests.exceptions.ConnectionError as e:
            raise GitHubConnectionError(f"Download failed: {e}")
        except requests.exceptions.RequestException as e:
            raise GitHubError(f"Download failed: {e}")

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self) -> "GitHubClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
