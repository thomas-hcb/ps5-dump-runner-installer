"""Unit tests for settings and credentials management."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config.settings import AppSettings, SettingsManager
from src.config.credentials import CredentialManager


class TestAppSettings:
    """Tests for AppSettings dataclass."""

    def test_default_values(self):
        """Test default settings values."""
        settings = AppSettings()
        assert settings.last_host == ""
        assert settings.last_port == 1337
        assert settings.last_username == "anonymous"
        assert settings.passive_mode is True
        assert settings.timeout == 30
        assert settings.window_width == 800
        assert settings.window_height == 600
        assert settings.download_path == ""
        assert settings.auto_check_updates is True

    def test_custom_values(self):
        """Test creating settings with custom values."""
        settings = AppSettings(
            last_host="192.168.1.100",
            last_port=2121,
            last_username="admin",
            passive_mode=False,
            timeout=60
        )
        assert settings.last_host == "192.168.1.100"
        assert settings.last_port == 2121
        assert settings.last_username == "admin"
        assert settings.passive_mode is False
        assert settings.timeout == 60

    def test_to_dict(self):
        """Test converting settings to dictionary."""
        settings = AppSettings(last_host="test.local", last_port=1234)
        data = settings.to_dict()

        assert isinstance(data, dict)
        assert data["last_host"] == "test.local"
        assert data["last_port"] == 1234
        assert "passive_mode" in data

    def test_from_dict(self):
        """Test creating settings from dictionary."""
        data = {
            "last_host": "192.168.1.50",
            "last_port": 9999,
            "last_username": "user1",
            "passive_mode": False
        }
        settings = AppSettings.from_dict(data)

        assert settings.last_host == "192.168.1.50"
        assert settings.last_port == 9999
        assert settings.last_username == "user1"
        assert settings.passive_mode is False

    def test_from_dict_ignores_unknown_keys(self):
        """Test that from_dict ignores unknown keys."""
        data = {
            "last_host": "test.local",
            "unknown_field": "should be ignored",
            "another_unknown": 123
        }
        settings = AppSettings.from_dict(data)

        assert settings.last_host == "test.local"
        assert not hasattr(settings, "unknown_field")

    def test_from_dict_with_missing_keys(self):
        """Test that from_dict uses defaults for missing keys."""
        data = {"last_host": "partial.local"}
        settings = AppSettings.from_dict(data)

        assert settings.last_host == "partial.local"
        assert settings.last_port == 1337  # default value


class TestSettingsManager:
    """Tests for SettingsManager class."""

    @pytest.fixture
    def temp_settings_path(self, tmp_path):
        """Create a temporary settings path."""
        return tmp_path / "settings.json"

    @pytest.fixture
    def manager(self, temp_settings_path):
        """Create a SettingsManager with temp path."""
        return SettingsManager(config_path=temp_settings_path)

    def test_config_path_property(self, manager, temp_settings_path):
        """Test config_path property returns correct path."""
        assert manager.config_path == temp_settings_path

    def test_load_returns_defaults_when_file_missing(self, manager, temp_settings_path):
        """Test loading settings when file doesn't exist."""
        assert not temp_settings_path.exists()

        settings = manager.load()

        assert isinstance(settings, AppSettings)
        assert settings.last_host == ""
        assert settings.last_port == 1337

    def test_save_creates_file(self, manager, temp_settings_path):
        """Test saving settings creates the file."""
        settings = AppSettings(last_host="saved.local", last_port=5555)

        manager.save(settings)

        assert temp_settings_path.exists()

        # Verify file contents
        with open(temp_settings_path, "r") as f:
            data = json.load(f)
        assert data["last_host"] == "saved.local"
        assert data["last_port"] == 5555

    def test_save_creates_parent_directories(self, tmp_path):
        """Test that save creates parent directories if needed."""
        nested_path = tmp_path / "deep" / "nested" / "settings.json"
        manager = SettingsManager(config_path=nested_path)

        settings = AppSettings(last_host="nested.local")
        manager.save(settings)

        assert nested_path.exists()

    def test_load_restores_saved_settings(self, manager, temp_settings_path):
        """Test that load restores previously saved settings."""
        # Save settings
        original = AppSettings(
            last_host="restore.local",
            last_port=7777,
            last_username="testuser",
            passive_mode=False
        )
        manager.save(original)

        # Create new manager and load
        new_manager = SettingsManager(config_path=temp_settings_path)
        loaded = new_manager.load()

        assert loaded.last_host == "restore.local"
        assert loaded.last_port == 7777
        assert loaded.last_username == "testuser"
        assert loaded.passive_mode is False

    def test_load_handles_corrupted_file(self, manager, temp_settings_path):
        """Test loading settings from corrupted file returns defaults."""
        # Write invalid JSON
        temp_settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_settings_path, "w") as f:
            f.write("not valid json {{{")

        settings = manager.load()

        assert isinstance(settings, AppSettings)
        assert settings.last_host == ""  # default value

    def test_reset_returns_defaults(self, manager):
        """Test reset returns default settings."""
        settings = manager.reset()

        assert isinstance(settings, AppSettings)
        assert settings.last_host == ""
        assert settings.last_port == 1337

    def test_reset_removes_file(self, manager, temp_settings_path):
        """Test reset removes the settings file."""
        # Save some settings first
        manager.save(AppSettings(last_host="to.delete"))
        assert temp_settings_path.exists()

        manager.reset()

        assert not temp_settings_path.exists()

    def test_update_modifies_specific_fields(self, manager):
        """Test update modifies only specified fields."""
        # Load defaults
        manager.load()

        # Update specific fields
        updated = manager.update(last_host="updated.local", last_port=8888)

        assert updated.last_host == "updated.local"
        assert updated.last_port == 8888
        assert updated.last_username == "anonymous"  # unchanged

    def test_update_ignores_unknown_fields(self, manager):
        """Test update ignores unknown field names."""
        manager.load()

        # Should not raise even with unknown field
        updated = manager.update(
            last_host="valid.local",
            nonexistent_field="ignored"
        )

        assert updated.last_host == "valid.local"

    def test_update_loads_if_not_loaded(self, manager):
        """Test update loads settings if not already loaded."""
        # Don't call load() first
        updated = manager.update(last_host="auto.loaded")

        assert updated.last_host == "auto.loaded"


class TestCredentialManager:
    """Tests for CredentialManager class."""

    @pytest.fixture
    def credential_manager(self):
        """Create a CredentialManager instance."""
        return CredentialManager()

    def test_make_key(self, credential_manager):
        """Test _make_key creates unique key."""
        key = credential_manager._make_key("192.168.1.100", "admin")
        assert key == "192.168.1.100:admin"

        key2 = credential_manager._make_key("other.host", "user")
        assert key2 == "other.host:user"

    @patch("keyring.set_password")
    def test_save_password_success(self, mock_set, credential_manager):
        """Test successful password save."""
        result = credential_manager.save_password("host.local", "user", "secret123")

        assert result is True
        mock_set.assert_called_once_with(
            CredentialManager.SERVICE_NAME,
            "host.local:user",
            "secret123"
        )

    @patch("keyring.set_password")
    def test_save_password_failure(self, mock_set, credential_manager):
        """Test password save failure."""
        from keyring.errors import KeyringError
        mock_set.side_effect = KeyringError("Backend error")

        result = credential_manager.save_password("host.local", "user", "secret")

        assert result is False

    @patch("keyring.get_password")
    def test_get_password_found(self, mock_get, credential_manager):
        """Test retrieving existing password."""
        mock_get.return_value = "my_secret"

        result = credential_manager.get_password("host.local", "user")

        assert result == "my_secret"
        mock_get.assert_called_once_with(
            CredentialManager.SERVICE_NAME,
            "host.local:user"
        )

    @patch("keyring.get_password")
    def test_get_password_not_found(self, mock_get, credential_manager):
        """Test retrieving non-existent password."""
        mock_get.return_value = None

        result = credential_manager.get_password("host.local", "unknown")

        assert result is None

    @patch("keyring.get_password")
    def test_get_password_error(self, mock_get, credential_manager):
        """Test get_password returns None on error."""
        from keyring.errors import KeyringError
        mock_get.side_effect = KeyringError("Backend error")

        result = credential_manager.get_password("host.local", "user")

        assert result is None

    @patch("keyring.delete_password")
    def test_delete_password_success(self, mock_delete, credential_manager):
        """Test successful password deletion."""
        result = credential_manager.delete_password("host.local", "user")

        assert result is True
        mock_delete.assert_called_once_with(
            CredentialManager.SERVICE_NAME,
            "host.local:user"
        )

    @patch("keyring.delete_password")
    def test_delete_password_failure(self, mock_delete, credential_manager):
        """Test password deletion failure."""
        from keyring.errors import KeyringError
        mock_delete.side_effect = KeyringError("Backend error")

        result = credential_manager.delete_password("host.local", "user")

        assert result is False

    @patch("keyring.get_password")
    def test_has_password_true(self, mock_get, credential_manager):
        """Test has_password returns True when password exists."""
        mock_get.return_value = "secret"

        result = credential_manager.has_password("host.local", "user")

        assert result is True

    @patch("keyring.get_password")
    def test_has_password_false(self, mock_get, credential_manager):
        """Test has_password returns False when no password."""
        mock_get.return_value = None

        result = credential_manager.has_password("host.local", "user")

        assert result is False

    def test_clear_all_does_not_raise(self, credential_manager):
        """Test clear_all completes without error."""
        # This is a placeholder method, should not raise
        credential_manager.clear_all()
