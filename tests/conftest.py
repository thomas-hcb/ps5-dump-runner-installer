"""Pytest configuration and shared fixtures for PS5 Dump Runner FTP Installer tests."""

import pytest
from pathlib import Path
from typing import Generator
from dataclasses import dataclass


# Test constants
TEST_FTP_HOST = "127.0.0.1"
TEST_FTP_PORT = 2121
TEST_FTP_USER = "testuser"
TEST_FTP_PASS = "testpass"


@dataclass
class MockFTPConfig:
    """Configuration for mock FTP server in tests."""
    host: str = TEST_FTP_HOST
    port: int = TEST_FTP_PORT
    username: str = TEST_FTP_USER
    password: str = TEST_FTP_PASS


@pytest.fixture
def ftp_config() -> MockFTPConfig:
    """Provide mock FTP configuration for tests."""
    return MockFTPConfig()


@pytest.fixture
def fixtures_path() -> Path:
    """Return the path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_dumps_path(fixtures_path: Path) -> Path:
    """Return the path to mock dumps fixtures."""
    return fixtures_path / "mock_dumps"


@pytest.fixture
def sample_releases_path(fixtures_path: Path) -> Path:
    """Return the path to sample releases fixtures."""
    return fixtures_path / "sample_releases"


@pytest.fixture
def test_configs_path(fixtures_path: Path) -> Path:
    """Return the path to test configuration fixtures."""
    return fixtures_path / "test_configs"


@pytest.fixture
def temp_settings_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary settings file path for testing."""
    settings_file = tmp_path / "settings.json"
    yield settings_file
    # Cleanup handled by tmp_path fixture


@pytest.fixture
def sample_dump_runner_elf(tmp_path: Path) -> Path:
    """Create a mock dump_runner.elf file for testing."""
    elf_file = tmp_path / "dump_runner.elf"
    elf_file.write_bytes(b"\x7fELF" + b"\x00" * 100)  # Mock ELF header
    return elf_file


@pytest.fixture
def sample_homebrew_js(tmp_path: Path) -> Path:
    """Create a mock homebrew.js file for testing."""
    js_file = tmp_path / "homebrew.js"
    js_file.write_text("// Mock homebrew.js for testing\nconsole.log('test');")
    return js_file
