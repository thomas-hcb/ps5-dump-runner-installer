"""Unit tests for GitHubClient and ReleaseDownloader.

Tests GitHub API integration and release download/caching functionality.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

from src.updater.github_client import (
    GitHubClient,
    GitHubRelease,
    ReleaseAsset,
    GitHubError,
    GitHubConnectionError,
    GitHubRateLimitError,
    GitHubNotFoundError,
    RELEASES_URL,
)
from src.updater.downloader import (
    ReleaseDownloader,
    DownloadProgress,
)
from src.updater.release import DumpRunnerRelease, ReleaseSource


# Sample API responses
SAMPLE_RELEASE_RESPONSE = {
    "tag_name": "v1.0.0",
    "name": "Release v1.0.0",
    "published_at": "2024-01-15T10:30:00Z",
    "body": "Release notes here",
    "html_url": "https://github.com/EchoStretch/dump_runner/releases/tag/v1.0.0",
    "prerelease": False,
    "draft": False,
    "assets": [
        {
            "name": "dump_runner.elf",
            "browser_download_url": "https://github.com/EchoStretch/dump_runner/releases/download/v1.0.0/dump_runner.elf",
            "size": 102400,
            "content_type": "application/octet-stream",
        },
        {
            "name": "homebrew.js",
            "browser_download_url": "https://github.com/EchoStretch/dump_runner/releases/download/v1.0.0/homebrew.js",
            "size": 5120,
            "content_type": "application/javascript",
        },
    ],
}

SAMPLE_RELEASES_RESPONSE = [
    SAMPLE_RELEASE_RESPONSE,
    {
        "tag_name": "v0.9.0",
        "name": "Release v0.9.0",
        "published_at": "2024-01-01T08:00:00Z",
        "body": "Previous release",
        "html_url": "https://github.com/EchoStretch/dump_runner/releases/tag/v0.9.0",
        "prerelease": False,
        "draft": False,
        "assets": [
            {
                "name": "dump_runner.elf",
                "browser_download_url": "https://github.com/EchoStretch/dump_runner/releases/download/v0.9.0/dump_runner.elf",
                "size": 98000,
                "content_type": "application/octet-stream",
            },
        ],
    },
]


class TestReleaseAsset:
    """Tests for ReleaseAsset dataclass."""

    def test_from_api_response(self):
        """Test creating ReleaseAsset from API response."""
        data = {
            "name": "dump_runner.elf",
            "browser_download_url": "https://example.com/file.elf",
            "size": 1024,
            "content_type": "application/octet-stream",
        }
        asset = ReleaseAsset.from_api_response(data)

        assert asset.name == "dump_runner.elf"
        assert asset.download_url == "https://example.com/file.elf"
        assert asset.size == 1024
        assert asset.content_type == "application/octet-stream"

    def test_from_api_response_missing_fields(self):
        """Test creating ReleaseAsset with missing fields."""
        asset = ReleaseAsset.from_api_response({})

        assert asset.name == ""
        assert asset.download_url == ""
        assert asset.size == 0
        assert asset.content_type == ""


class TestGitHubRelease:
    """Tests for GitHubRelease dataclass."""

    def test_from_api_response(self):
        """Test creating GitHubRelease from API response."""
        release = GitHubRelease.from_api_response(SAMPLE_RELEASE_RESPONSE)

        assert release.tag_name == "v1.0.0"
        assert release.name == "Release v1.0.0"
        assert release.body == "Release notes here"
        assert release.prerelease is False
        assert release.draft is False
        assert len(release.assets) == 2

    def test_version_property(self):
        """Test version property returns tag_name."""
        release = GitHubRelease.from_api_response(SAMPLE_RELEASE_RESPONSE)
        assert release.version == "v1.0.0"

    def test_has_elf_property(self):
        """Test has_elf property."""
        release = GitHubRelease.from_api_response(SAMPLE_RELEASE_RESPONSE)
        assert release.has_elf is True

    def test_has_js_property(self):
        """Test has_js property."""
        release = GitHubRelease.from_api_response(SAMPLE_RELEASE_RESPONSE)
        assert release.has_js is True

    def test_is_complete_property(self):
        """Test is_complete property when both files present."""
        release = GitHubRelease.from_api_response(SAMPLE_RELEASE_RESPONSE)
        assert release.is_complete is True

    def test_is_complete_missing_js(self):
        """Test is_complete property when JS is missing."""
        data = SAMPLE_RELEASE_RESPONSE.copy()
        data["assets"] = [a for a in data["assets"] if a["name"] != "homebrew.js"]
        release = GitHubRelease.from_api_response(data)
        assert release.is_complete is False

    def test_get_asset(self):
        """Test get_asset method."""
        release = GitHubRelease.from_api_response(SAMPLE_RELEASE_RESPONSE)

        elf = release.get_asset("dump_runner.elf")
        assert elf is not None
        assert elf.name == "dump_runner.elf"

        missing = release.get_asset("nonexistent.txt")
        assert missing is None

    def test_get_elf_asset(self):
        """Test get_elf_asset convenience method."""
        release = GitHubRelease.from_api_response(SAMPLE_RELEASE_RESPONSE)
        asset = release.get_elf_asset()
        assert asset is not None
        assert asset.name == "dump_runner.elf"

    def test_get_js_asset(self):
        """Test get_js_asset convenience method."""
        release = GitHubRelease.from_api_response(SAMPLE_RELEASE_RESPONSE)
        asset = release.get_js_asset()
        assert asset is not None
        assert asset.name == "homebrew.js"

    def test_published_at_parsing(self):
        """Test published_at date parsing."""
        release = GitHubRelease.from_api_response(SAMPLE_RELEASE_RESPONSE)
        assert release.published_at is not None
        assert release.published_at.year == 2024
        assert release.published_at.month == 1
        assert release.published_at.day == 15


class TestGitHubClient:
    """Tests for GitHubClient."""

    @pytest.fixture
    def client(self):
        """Create a GitHubClient instance."""
        return GitHubClient(timeout=10)

    @pytest.fixture
    def mock_response(self):
        """Create a mock response object."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = SAMPLE_RELEASE_RESPONSE
        return response

    def test_get_latest_release_success(self, client, mock_response):
        """Test successful get_latest_release."""
        with patch.object(client._session, 'get', return_value=mock_response):
            release = client.get_latest_release()

            assert release.tag_name == "v1.0.0"
            assert release.is_complete is True

    def test_get_latest_release_not_found(self, client):
        """Test get_latest_release when no releases exist."""
        response = MagicMock()
        response.status_code = 404

        with patch.object(client._session, 'get', return_value=response):
            with pytest.raises(GitHubNotFoundError):
                client.get_latest_release()

    def test_get_latest_release_rate_limited(self, client):
        """Test get_latest_release when rate limited."""
        response = MagicMock()
        response.status_code = 403
        response.text = "API rate limit exceeded"

        with patch.object(client._session, 'get', return_value=response):
            with pytest.raises(GitHubRateLimitError):
                client.get_latest_release()

    def test_get_latest_release_connection_error(self, client):
        """Test get_latest_release with connection error."""
        import requests

        with patch.object(
            client._session,
            'get',
            side_effect=requests.exceptions.ConnectionError("Network error")
        ):
            with pytest.raises(GitHubConnectionError):
                client.get_latest_release()

    def test_get_latest_release_timeout(self, client):
        """Test get_latest_release with timeout."""
        import requests

        with patch.object(
            client._session,
            'get',
            side_effect=requests.exceptions.Timeout("Request timed out")
        ):
            with pytest.raises(GitHubConnectionError):
                client.get_latest_release()

    def test_get_releases_success(self, client):
        """Test successful get_releases."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = SAMPLE_RELEASES_RESPONSE

        with patch.object(client._session, 'get', return_value=response):
            releases = client.get_releases(limit=10)

            assert len(releases) == 2
            assert releases[0].tag_name == "v1.0.0"
            assert releases[1].tag_name == "v0.9.0"

    def test_get_releases_filters_drafts(self, client):
        """Test that get_releases filters out drafts."""
        data = SAMPLE_RELEASES_RESPONSE.copy()
        data.append({
            "tag_name": "v0.8.0",
            "name": "Draft Release",
            "draft": True,
            "assets": [],
        })

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = data

        with patch.object(client._session, 'get', return_value=response):
            releases = client.get_releases()
            # Should not include the draft
            assert len(releases) == 2

    def test_get_release_by_tag_success(self, client, mock_response):
        """Test successful get_release_by_tag."""
        with patch.object(client._session, 'get', return_value=mock_response):
            release = client.get_release_by_tag("v1.0.0")
            assert release.tag_name == "v1.0.0"

    def test_get_release_by_tag_not_found(self, client):
        """Test get_release_by_tag with non-existent tag."""
        response = MagicMock()
        response.status_code = 404

        with patch.object(client._session, 'get', return_value=response):
            with pytest.raises(GitHubNotFoundError):
                client.get_release_by_tag("nonexistent")

    def test_download_asset_success(self, client):
        """Test successful asset download."""
        asset = ReleaseAsset(
            name="dump_runner.elf",
            download_url="https://example.com/file.elf",
            size=1024,
            content_type="application/octet-stream",
        )

        response = MagicMock()
        response.headers = {"content-length": "1024"}
        response.iter_content = MagicMock(return_value=[b"test content"])
        response.raise_for_status = MagicMock()

        with patch.object(client._session, 'get', return_value=response):
            content = client.download_asset(asset)
            assert content == b"test content"

    def test_download_asset_with_progress_callback(self, client):
        """Test asset download with progress callback."""
        asset = ReleaseAsset(
            name="dump_runner.elf",
            download_url="https://example.com/file.elf",
            size=1024,
            content_type="application/octet-stream",
        )

        response = MagicMock()
        response.headers = {"content-length": "1024"}
        response.iter_content = MagicMock(return_value=[b"chunk1", b"chunk2"])
        response.raise_for_status = MagicMock()

        progress_calls = []
        def callback(downloaded, total):
            progress_calls.append((downloaded, total))

        with patch.object(client._session, 'get', return_value=response):
            client.download_asset(asset, callback=callback)
            assert len(progress_calls) == 2

    def test_context_manager(self):
        """Test GitHubClient as context manager."""
        with GitHubClient() as client:
            assert client._session is not None

    def test_close(self, client):
        """Test closing the client."""
        client.close()
        # Session should still exist but be closed


class TestDownloadProgress:
    """Tests for DownloadProgress dataclass."""

    def test_percentage_calculation(self):
        """Test percentage property."""
        progress = DownloadProgress(
            asset_name="test.elf",
            bytes_downloaded=500,
            total_bytes=1000,
            current_file=1,
            total_files=2,
        )
        assert progress.percentage == 50.0

    def test_percentage_zero_total(self):
        """Test percentage with zero total bytes."""
        progress = DownloadProgress(
            asset_name="test.elf",
            bytes_downloaded=0,
            total_bytes=0,
            current_file=1,
            total_files=2,
        )
        assert progress.percentage == 0.0

    def test_overall_percentage(self):
        """Test overall_percentage property."""
        # First file, 50% done
        progress = DownloadProgress(
            asset_name="file1.elf",
            bytes_downloaded=500,
            total_bytes=1000,
            current_file=1,
            total_files=2,
        )
        # Should be 25% overall (0% complete files + 50%/2 current)
        assert progress.overall_percentage == 25.0

        # Second file, 50% done
        progress2 = DownloadProgress(
            asset_name="file2.js",
            bytes_downloaded=500,
            total_bytes=1000,
            current_file=2,
            total_files=2,
        )
        # Should be 75% overall (50% complete files + 50%/2 current)
        assert progress2.overall_percentage == 75.0


class TestReleaseDownloader:
    """Tests for ReleaseDownloader."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create a temporary cache directory."""
        cache_dir = tmp_path / "releases"
        cache_dir.mkdir()
        return cache_dir

    @pytest.fixture
    def downloader(self, temp_cache_dir):
        """Create a ReleaseDownloader with temp cache."""
        return ReleaseDownloader(cache_dir=temp_cache_dir)

    def test_get_cached_release_none(self, downloader):
        """Test get_cached_release when no cache exists."""
        result = downloader.get_cached_release()
        assert result is None

    def test_get_cached_release_exists(self, downloader, temp_cache_dir):
        """Test get_cached_release when cache exists."""
        # Create cached release
        release_dir = temp_cache_dir / "v1.0.0"
        release_dir.mkdir()

        # Create files
        (release_dir / "dump_runner.elf").write_bytes(b"elf content")
        (release_dir / "homebrew.js").write_bytes(b"js content")

        # Create metadata
        metadata = {
            "version": "v1.0.0",
            "name": "Release v1.0.0",
            "published_at": "2024-01-15T10:30:00+00:00",
            "body": "Release notes",
            "html_url": "https://example.com",
            "downloaded_at": datetime.now().isoformat(),
        }
        (release_dir / "release_metadata.json").write_text(json.dumps(metadata))

        # Get cached release
        result = downloader.get_cached_release("v1.0.0")
        assert result is not None
        assert result.version == "v1.0.0"
        assert result.files_exist

    def test_download_release_success(self, downloader, temp_cache_dir):
        """Test successful release download."""
        release = GitHubRelease.from_api_response(SAMPLE_RELEASE_RESPONSE)

        # Mock the client
        mock_client = MagicMock()
        mock_client.download_asset.side_effect = [
            b"elf file content",
            b"js file content",
        ]

        with patch.object(downloader, '_get_client', return_value=mock_client):
            result = downloader.download_release(release)

            assert result is not None
            assert result.version == "v1.0.0"
            assert result.elf_path.exists()
            assert result.js_path.exists()
            assert result.elf_path.read_bytes() == b"elf file content"
            assert result.js_path.read_bytes() == b"js file content"

    def test_download_release_uses_cache(self, downloader, temp_cache_dir):
        """Test that download uses cached release when available."""
        release = GitHubRelease.from_api_response(SAMPLE_RELEASE_RESPONSE)

        # Create cached release
        release_dir = temp_cache_dir / "v1.0.0"
        release_dir.mkdir()
        (release_dir / "dump_runner.elf").write_bytes(b"cached elf")
        (release_dir / "homebrew.js").write_bytes(b"cached js")
        metadata = {
            "version": "v1.0.0",
            "downloaded_at": datetime.now().isoformat(),
        }
        (release_dir / "release_metadata.json").write_text(json.dumps(metadata))

        # Mock client should not be called
        mock_client = MagicMock()

        with patch.object(downloader, '_get_client', return_value=mock_client):
            result = downloader.download_release(release)

            assert result is not None
            assert result.version == "v1.0.0"
            # Client should not have been called (used cache)
            mock_client.download_asset.assert_not_called()

    def test_download_release_force_redownload(self, downloader, temp_cache_dir):
        """Test force redownload even when cached."""
        release = GitHubRelease.from_api_response(SAMPLE_RELEASE_RESPONSE)

        # Create cached release
        release_dir = temp_cache_dir / "v1.0.0"
        release_dir.mkdir()
        (release_dir / "dump_runner.elf").write_bytes(b"old elf")
        (release_dir / "homebrew.js").write_bytes(b"old js")
        metadata = {"version": "v1.0.0", "downloaded_at": datetime.now().isoformat()}
        (release_dir / "release_metadata.json").write_text(json.dumps(metadata))

        # Mock client
        mock_client = MagicMock()
        mock_client.download_asset.side_effect = [
            b"new elf content",
            b"new js content",
        ]

        with patch.object(downloader, '_get_client', return_value=mock_client):
            result = downloader.download_release(release, force=True)

            assert result is not None
            assert result.elf_path.read_bytes() == b"new elf content"
            assert result.js_path.read_bytes() == b"new js content"

    def test_download_release_incomplete_fails(self, downloader):
        """Test that incomplete releases raise error."""
        # Create release without JS file
        data = SAMPLE_RELEASE_RESPONSE.copy()
        data["assets"] = [a for a in data["assets"] if a["name"] != "homebrew.js"]
        release = GitHubRelease.from_api_response(data)

        with pytest.raises(ValueError, match="missing required files"):
            downloader.download_release(release)

    def test_clear_cache_specific_version(self, downloader, temp_cache_dir):
        """Test clearing cache for specific version."""
        # Create cached release
        release_dir = temp_cache_dir / "v1.0.0"
        release_dir.mkdir()
        (release_dir / "dump_runner.elf").write_bytes(b"content")

        assert release_dir.exists()

        count = downloader.clear_cache("v1.0.0")
        assert count == 1
        assert not release_dir.exists()

    def test_clear_cache_all(self, downloader, temp_cache_dir):
        """Test clearing all cached releases."""
        # Create multiple cached releases
        for version in ["v1.0.0", "v0.9.0", "v0.8.0"]:
            release_dir = temp_cache_dir / version
            release_dir.mkdir()
            (release_dir / "dump_runner.elf").write_bytes(b"content")

        count = downloader.clear_cache()
        assert count == 3
        assert len(list(temp_cache_dir.iterdir())) == 0

    def test_list_cached_versions(self, downloader, temp_cache_dir):
        """Test listing cached versions."""
        # Create cached releases with metadata
        for version in ["v1.0.0", "v0.9.0"]:
            release_dir = temp_cache_dir / version
            release_dir.mkdir()
            metadata = {"version": version}
            (release_dir / "release_metadata.json").write_text(json.dumps(metadata))

        versions = downloader.list_cached_versions()
        assert len(versions) == 2
        assert "v1.0.0" in versions
        assert "v0.9.0" in versions

    def test_context_manager(self, temp_cache_dir):
        """Test ReleaseDownloader as context manager."""
        with ReleaseDownloader(cache_dir=temp_cache_dir) as downloader:
            assert downloader._cache_dir == temp_cache_dir

    def test_download_release_from_zip(self, downloader, temp_cache_dir):
        """Test downloading release from zip file."""
        import io
        import zipfile

        # Create release with zip asset
        data = {
            "tag_name": "v1.0.0",
            "name": "Release v1.0.0",
            "published_at": "2024-01-15T10:30:00Z",
            "body": "Release notes",
            "html_url": "https://example.com",
            "prerelease": False,
            "draft": False,
            "assets": [
                {
                    "name": "dump_runner.zip",
                    "browser_download_url": "https://example.com/dump_runner.zip",
                    "size": 1024,
                    "content_type": "application/zip",
                },
            ],
        }
        release = GitHubRelease.from_api_response(data)
        assert release.has_zip is True
        assert release.is_complete is True

        # Create a mock zip file with the required files
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("dump_runner/dump_runner.elf", b"elf content from zip")
            zf.writestr("dump_runner/homebrew.js", b"js content from zip")
        zip_content = zip_buffer.getvalue()

        # Mock the client
        mock_client = MagicMock()
        mock_client.download_asset.return_value = zip_content

        with patch.object(downloader, '_get_client', return_value=mock_client):
            result = downloader.download_release(release)

            assert result is not None
            assert result.version == "v1.0.0"
            assert result.elf_path.exists()
            assert result.js_path.exists()
            assert result.elf_path.read_bytes() == b"elf content from zip"
            assert result.js_path.read_bytes() == b"js content from zip"
