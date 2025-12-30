##############################################################################
#
# Name: test_config.py
#
# Function:
#       Unit tests for ConfigManager class
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
from pathlib import Path

import pytest

from meetup_scheduler.config.manager import ConfigManager


class TestConfigManagerPaths:
    """Test ConfigManager path handling."""

    def test_user_config_dir_is_path(self, tmp_project_dir: Path) -> None:
        """Test user_config_dir returns a Path."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        assert isinstance(manager.user_config_dir, Path)

    def test_user_config_dir_contains_app_name(self, tmp_project_dir: Path) -> None:
        """Test user_config_dir contains the app name."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        assert "meetup-scheduler" in str(manager.user_config_dir)

    def test_project_dir_uses_provided_path(self, tmp_project_dir: Path) -> None:
        """Test project_dir uses the provided path."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        assert manager.project_dir == tmp_project_dir

    def test_project_config_path(self, tmp_project_dir: Path) -> None:
        """Test project_config_path is correct."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        expected = tmp_project_dir / "meetup-scheduler-local.json"
        assert manager.project_config_path == expected

    def test_user_config_path(self, tmp_project_dir: Path) -> None:
        """Test user_config_path is in user_config_dir."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        assert manager.user_config_path.parent == manager.user_config_dir
        assert manager.user_config_path.name == "config.json"

    def test_credentials_path(self, tmp_project_dir: Path) -> None:
        """Test credentials_path is in user_config_dir."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        assert manager.credentials_path.parent == manager.user_config_dir
        assert manager.credentials_path.name == "credentials.json"


class TestConfigManagerUserConfig:
    """Test user configuration handling."""

    def test_load_user_config_returns_empty_if_missing(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading missing user config returns empty dict."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        # Point to a non-existent directory
        monkeypatch.setattr(manager, "_user_config_dir", tmp_project_dir / "nonexistent")
        config = manager.load_user_config()
        assert config == {}

    def test_save_and_load_user_config(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test saving and loading user config."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        # Use tmp_project_dir as user config dir for testing
        monkeypatch.setattr(manager, "_user_config_dir", tmp_project_dir)

        config = {"organizer": {"name": "Test User"}}
        manager.save_user_config(config)

        # Clear cache and reload
        manager._user_config = None
        loaded = manager.load_user_config()

        assert loaded == config

    def test_load_invalid_json_raises_error(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading invalid JSON raises ConfigManager.Error."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        monkeypatch.setattr(manager, "_user_config_dir", tmp_project_dir)

        # Write invalid JSON
        config_path = tmp_project_dir / "config.json"
        config_path.write_text("not valid json")

        with pytest.raises(ConfigManager.Error, match="Invalid JSON"):
            manager.load_user_config()


class TestConfigManagerProjectConfig:
    """Test project configuration handling."""

    def test_load_project_config_returns_empty_if_missing(
        self, tmp_project_dir: Path
    ) -> None:
        """Test loading missing project config returns empty dict."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        config = manager.load_project_config()
        assert config == {}

    def test_load_project_config_from_file(self, tmp_project_dir: Path) -> None:
        """Test loading project config from file."""
        config_path = tmp_project_dir / "meetup-scheduler-local.json"
        config = {"defaultTimezone": "America/New_York"}
        config_path.write_text(json.dumps(config))

        manager = ConfigManager(project_dir=tmp_project_dir)
        loaded = manager.load_project_config()

        assert loaded == config

    def test_project_config_is_cached(self, tmp_project_dir: Path) -> None:
        """Test project config is cached after loading."""
        config_path = tmp_project_dir / "meetup-scheduler-local.json"
        config = {"key": "value"}
        config_path.write_text(json.dumps(config))

        manager = ConfigManager(project_dir=tmp_project_dir)
        config1 = manager.load_project_config()
        config2 = manager.load_project_config()

        assert config1 is config2


class TestConfigManagerCredentials:
    """Test credentials handling."""

    def test_load_credentials_returns_empty_if_missing(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading missing credentials returns empty dict."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        monkeypatch.setattr(manager, "_user_config_dir", tmp_project_dir / "nonexistent")
        creds = manager.load_credentials()
        assert creds == {}

    def test_save_and_load_credentials(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test saving and loading credentials."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        monkeypatch.setattr(manager, "_user_config_dir", tmp_project_dir)

        creds = {"access_token": "test_token", "refresh_token": "test_refresh"}
        manager.save_credentials(creds)

        loaded = manager.load_credentials()
        assert loaded == creds


class TestConfigManagerGet:
    """Test ConfigManager.get() method."""

    def test_get_returns_default_for_missing_key(self, tmp_project_dir: Path) -> None:
        """Test get() returns default for missing key."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        result = manager.get("missing.key", default="default_value")
        assert result == "default_value"

    def test_get_returns_none_for_missing_key_no_default(
        self, tmp_project_dir: Path
    ) -> None:
        """Test get() returns None for missing key with no default."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        result = manager.get("missing.key")
        assert result is None

    def test_get_nested_key(self, tmp_project_dir: Path) -> None:
        """Test get() with nested dot-notation key."""
        config_path = tmp_project_dir / "meetup-scheduler-local.json"
        config = {"organizer": {"name": "Test User"}}
        config_path.write_text(json.dumps(config))

        manager = ConfigManager(project_dir=tmp_project_dir)
        result = manager.get("organizer.name")

        assert result == "Test User"

    def test_get_top_level_key(self, tmp_project_dir: Path) -> None:
        """Test get() with top-level key."""
        config_path = tmp_project_dir / "meetup-scheduler-local.json"
        config = {"defaultTimezone": "America/Chicago"}
        config_path.write_text(json.dumps(config))

        manager = ConfigManager(project_dir=tmp_project_dir)
        result = manager.get("defaultTimezone")

        assert result == "America/Chicago"

    def test_get_deeply_nested_key(self, tmp_project_dir: Path) -> None:
        """Test get() with deeply nested key."""
        config_path = tmp_project_dir / "meetup-scheduler-local.json"
        config = {"a": {"b": {"c": {"d": "deep_value"}}}}
        config_path.write_text(json.dumps(config))

        manager = ConfigManager(project_dir=tmp_project_dir)
        result = manager.get("a.b.c.d")

        assert result == "deep_value"

    def test_project_config_takes_priority(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test project config takes priority over user config."""
        manager = ConfigManager(project_dir=tmp_project_dir)

        # Set up user config
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)
        user_config = {"setting": "user_value"}
        (user_dir / "config.json").write_text(json.dumps(user_config))

        # Set up project config (higher priority)
        project_config = {"setting": "project_value"}
        (tmp_project_dir / "meetup-scheduler-local.json").write_text(
            json.dumps(project_config)
        )

        result = manager.get("setting")
        assert result == "project_value"

    def test_user_config_used_if_project_missing(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test user config is used if project config doesn't have key."""
        manager = ConfigManager(project_dir=tmp_project_dir)

        # Set up user config
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)
        user_config = {"user_only": "user_value"}
        (user_dir / "config.json").write_text(json.dumps(user_config))

        # Project config doesn't have the key
        project_config = {"other_key": "other_value"}
        (tmp_project_dir / "meetup-scheduler-local.json").write_text(
            json.dumps(project_config)
        )

        result = manager.get("user_only")
        assert result == "user_value"
