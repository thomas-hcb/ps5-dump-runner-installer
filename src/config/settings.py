"""Application settings management for PS5 Dump Runner FTP Installer.

Provides AppSettings dataclass and SettingsManager for persistence.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from src.config.paths import get_settings_path


@dataclass
class AppSettings:
    """Application settings that persist between sessions."""

    # FTP connection defaults
    last_host: str = ""
    last_port: int = 1337
    last_username: str = "anonymous"
    passive_mode: bool = True
    timeout: int = 30

    # Window settings
    window_width: int = 800
    window_height: int = 600

    # Download settings
    download_path: str = ""

    # Update settings
    auto_check_updates: bool = True

    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        """Create settings from dictionary, ignoring unknown keys."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


class SettingsManager:
    """Manages application settings persistence."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize settings manager.

        Args:
            config_path: Optional custom path, defaults to platform standard
        """
        self._config_path = config_path or get_settings_path()
        self._settings: Optional[AppSettings] = None

    @property
    def config_path(self) -> Path:
        """Path to settings file."""
        return self._config_path

    def load(self) -> AppSettings:
        """
        Load settings from disk.

        Returns:
            AppSettings instance (defaults if file not found)
        """
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._settings = AppSettings.from_dict(data)
            except (json.JSONDecodeError, IOError):
                # Invalid or unreadable file, use defaults
                self._settings = AppSettings()
        else:
            self._settings = AppSettings()

        return self._settings

    def save(self, settings: AppSettings) -> None:
        """
        Persist settings to disk.

        Args:
            settings: Settings to save
        """
        self._settings = settings

        # Ensure parent directory exists
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, indent=2)

    def reset(self) -> AppSettings:
        """
        Reset to default settings.

        Returns:
            Default AppSettings instance
        """
        self._settings = AppSettings()

        # Remove existing file
        if self._config_path.exists():
            self._config_path.unlink()

        return self._settings

    def update(self, **kwargs) -> AppSettings:
        """
        Update specific settings fields.

        Args:
            **kwargs: Field names and new values

        Returns:
            Updated AppSettings instance
        """
        if self._settings is None:
            self.load()

        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)

        self.save(self._settings)
        return self._settings
