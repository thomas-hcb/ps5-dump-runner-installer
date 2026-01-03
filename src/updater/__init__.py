"""Updater module for GitHub integration.

This module handles dump_runner release management:
- GitHubClient: GitHub API integration for release checking
- ReleaseDownloader: Asset download and caching
- Release models: DumpRunnerRelease, ReleaseAsset dataclasses
"""

from src.updater.release import DumpRunnerRelease, ReleaseSource
from src.updater.github_client import (
    GitHubClient,
    GitHubRelease,
    ReleaseAsset,
    GitHubError,
    GitHubConnectionError,
    GitHubRateLimitError,
    GitHubNotFoundError,
)
from src.updater.downloader import (
    ReleaseDownloader,
    DownloadProgress,
    ProgressCallback,
)

__all__ = [
    # Release models
    "DumpRunnerRelease",
    "ReleaseSource",
    # GitHub client
    "GitHubClient",
    "GitHubRelease",
    "ReleaseAsset",
    "GitHubError",
    "GitHubConnectionError",
    "GitHubRateLimitError",
    "GitHubNotFoundError",
    # Downloader
    "ReleaseDownloader",
    "DownloadProgress",
    "ProgressCallback",
]
