##############################################################################
#
# Name: manager.py
#
# Function:
#       Configuration management with platformdirs integration
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

import platformdirs


class ConfigManager:
    """Manage user and project configuration files."""

    # Application identifiers for platformdirs
    APP_NAME = "meetup-scheduler"
    APP_AUTHOR = "meetup-scheduler"

    # File names
    CONFIG_FILE = "config.json"
    CREDENTIALS_FILE = "credentials.json"
    PROJECT_CONFIG_FILE = "meetup-scheduler-local.json"

    class Error(Exception):
        """Exception raised for configuration errors."""

        pass

    def __init__(self, project_dir: Path | None = None) -> None:
        """Initialize the configuration manager.

        Args:
            project_dir: Project directory. Defaults to current working directory.
        """
        self._project_dir = project_dir or Path.cwd()
        self._user_config_dir: Path | None = None
        self._user_config: dict[str, Any] | None = None
        self._project_config: dict[str, Any] | None = None

    @property
    def user_config_dir(self) -> Path:
        """Return the user-level configuration directory.

        Uses platformdirs to determine the appropriate location:
        - Linux: ~/.config/meetup-scheduler/
        - macOS: ~/Library/Application Support/meetup-scheduler/
        - Windows: %APPDATA%/meetup-scheduler/meetup-scheduler/
        """
        if self._user_config_dir is None:
            self._user_config_dir = Path(
                platformdirs.user_config_dir(
                    appname=self.APP_NAME,
                    appauthor=self.APP_AUTHOR,
                )
            )
        return self._user_config_dir

    @property
    def project_dir(self) -> Path:
        """Return the project directory."""
        return self._project_dir

    @property
    def user_config_path(self) -> Path:
        """Return path to user config file."""
        return self.user_config_dir / self.CONFIG_FILE

    @property
    def credentials_path(self) -> Path:
        """Return path to credentials file."""
        return self.user_config_dir / self.CREDENTIALS_FILE

    @property
    def project_config_path(self) -> Path:
        """Return path to project config file."""
        return self._project_dir / self.PROJECT_CONFIG_FILE

    def ensure_user_config_dir(self) -> Path:
        """Ensure user config directory exists and return it."""
        self.user_config_dir.mkdir(parents=True, exist_ok=True)
        return self.user_config_dir

    def load_user_config(self) -> dict[str, Any]:
        """Load user-level configuration.

        Returns:
            Configuration dictionary. Empty dict if file doesn't exist.
        """
        if self._user_config is not None:
            return self._user_config

        if self.user_config_path.exists():
            try:
                with open(self.user_config_path, encoding="utf-8") as f:
                    self._user_config = json.load(f)
            except json.JSONDecodeError as e:
                raise self.Error(
                    f"Invalid JSON in {self.user_config_path}: {e}"
                ) from e
        else:
            self._user_config = {}

        return self._user_config

    def save_user_config(self, config: dict[str, Any]) -> None:
        """Save user-level configuration.

        Args:
            config: Configuration dictionary to save.
        """
        self.ensure_user_config_dir()
        with open(self.user_config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        self._user_config = config

    def load_credentials(self) -> dict[str, Any]:
        """Load credentials from file.

        Returns:
            Credentials dictionary. Empty dict if file doesn't exist.
        """
        if self.credentials_path.exists():
            try:
                with open(self.credentials_path, encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                raise self.Error(
                    f"Invalid JSON in {self.credentials_path}: {e}"
                ) from e
        return {}

    def save_credentials(self, credentials: dict[str, Any]) -> None:
        """Save credentials with restricted permissions.

        Args:
            credentials: Credentials dictionary to save.
        """
        self.ensure_user_config_dir()

        # Write to file
        with open(self.credentials_path, "w", encoding="utf-8") as f:
            json.dump(credentials, f, indent=2)

        # Set restrictive permissions on Unix (0600)
        if os.name != "nt":
            os.chmod(self.credentials_path, stat.S_IRUSR | stat.S_IWUSR)

    def load_project_config(self) -> dict[str, Any]:
        """Load project-level configuration.

        Returns:
            Configuration dictionary. Empty dict if file doesn't exist.
        """
        if self._project_config is not None:
            return self._project_config

        if self.project_config_path.exists():
            try:
                with open(self.project_config_path, encoding="utf-8") as f:
                    self._project_config = json.load(f)
            except json.JSONDecodeError as e:
                raise self.Error(
                    f"Invalid JSON in {self.project_config_path}: {e}"
                ) from e
        else:
            self._project_config = {}

        return self._project_config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Checks project config first, then user config.

        Args:
            key: Dot-separated key path (e.g., "organizer.name").
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        # Check project config first (higher priority)
        value = self._get_nested(self.load_project_config(), key)
        if value is not None:
            return value

        # Fall back to user config
        value = self._get_nested(self.load_user_config(), key)
        if value is not None:
            return value

        return default

    def _get_nested(self, data: dict[str, Any], key: str) -> Any:
        """Get a nested value from a dictionary using dot notation.

        Args:
            data: Dictionary to search.
            key: Dot-separated key path.

        Returns:
            Value at the key path, or None if not found.
        """
        parts = key.split(".")
        current: Any = data
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current
