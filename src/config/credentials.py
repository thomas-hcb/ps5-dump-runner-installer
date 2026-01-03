"""Secure credential storage for PS5 Dump Runner FTP Installer.

Uses the system keyring (Windows Credential Manager, macOS Keychain,
Linux Secret Service) to securely store FTP passwords.
"""

from typing import Optional

import keyring
from keyring.errors import KeyringError


class CredentialManager:
    """Secure credential storage using system keyring."""

    SERVICE_NAME = "ps5-dump-runner-installer"

    def _make_key(self, host: str, username: str) -> str:
        """
        Create a unique key for the credential.

        Args:
            host: FTP host
            username: FTP username

        Returns:
            Unique key string
        """
        return f"{host}:{username}"

    def save_password(self, host: str, username: str, password: str) -> bool:
        """
        Save FTP password securely.

        Args:
            host: FTP host
            username: FTP username
            password: Password to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            key = self._make_key(host, username)
            keyring.set_password(self.SERVICE_NAME, key, password)
            return True
        except KeyringError:
            return False

    def get_password(self, host: str, username: str) -> Optional[str]:
        """
        Retrieve saved password.

        Args:
            host: FTP host
            username: FTP username

        Returns:
            Password string or None if not found
        """
        try:
            key = self._make_key(host, username)
            return keyring.get_password(self.SERVICE_NAME, key)
        except KeyringError:
            return None

    def delete_password(self, host: str, username: str) -> bool:
        """
        Remove saved password.

        Args:
            host: FTP host
            username: FTP username

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            key = self._make_key(host, username)
            keyring.delete_password(self.SERVICE_NAME, key)
            return True
        except KeyringError:
            return False

    def has_password(self, host: str, username: str) -> bool:
        """
        Check if a password is saved.

        Args:
            host: FTP host
            username: FTP username

        Returns:
            True if password exists
        """
        return self.get_password(host, username) is not None

    def clear_all(self) -> None:
        """
        Remove all saved credentials for this app.

        Note: This is a best-effort operation. Some keyring backends
        don't support listing all credentials, so we can only delete
        known credentials.
        """
        # Keyring doesn't have a list/clear all feature by default
        # This method exists for future use if we track saved hosts
        pass
