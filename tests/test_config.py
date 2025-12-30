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


class TestConfigManagerSet:
    """Test ConfigManager.set() method."""

    def test_set_simple_key(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test set() with a simple key."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)

        manager.set("setting", "value")

        # Verify saved
        config_path = user_dir / "config.json"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert config["setting"] == "value"

    def test_set_nested_key(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test set() with a nested key creates intermediate dicts."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)

        manager.set("organizer.name", "Test User")

        config_path = user_dir / "config.json"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert config["organizer"]["name"] == "Test User"

    def test_set_deeply_nested_key(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test set() with deeply nested key."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)

        manager.set("a.b.c.d", "deep_value")

        config_path = user_dir / "config.json"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert config["a"]["b"]["c"]["d"] == "deep_value"

    def test_set_overwrites_existing(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test set() overwrites existing values."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)

        # Write initial config
        config_path = user_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"setting": "old_value"}, f)

        manager.set("setting", "new_value")

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert config["setting"] == "new_value"

    def test_set_to_project_config(self, tmp_project_dir: Path) -> None:
        """Test set() with user_level=False saves to project config."""
        manager = ConfigManager(project_dir=tmp_project_dir)

        manager.set("project_setting", "value", user_level=False)

        config_path = tmp_project_dir / "meetup-scheduler-local.json"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert config["project_setting"] == "value"


class TestConfigManagerUnset:
    """Test ConfigManager.unset() method."""

    def test_unset_existing_key(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test unset() removes an existing key."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)

        # Write initial config
        config_path = user_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"setting": "value", "keep": "this"}, f)

        result = manager.unset("setting")

        assert result is True
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert "setting" not in config
        assert config["keep"] == "this"

    def test_unset_missing_key_returns_false(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test unset() returns False for missing key."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)

        result = manager.unset("nonexistent")
        assert result is False

    def test_unset_nested_key(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test unset() with nested key."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)

        # Write initial config
        config_path = user_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"organizer": {"name": "Test", "email": "test@example.com"}}, f)

        result = manager.unset("organizer.name")

        assert result is True
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert "name" not in config["organizer"]
        assert config["organizer"]["email"] == "test@example.com"


class TestConfigManagerGetAll:
    """Test ConfigManager.get_all() method."""

    def test_get_all_user_config(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_all() returns user config."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)

        config = {"key": "value"}
        (user_dir / "config.json").write_text(json.dumps(config))

        result = manager.get_all(user_level=True)
        assert result == config

    def test_get_all_project_config(self, tmp_project_dir: Path) -> None:
        """Test get_all() returns project config."""
        manager = ConfigManager(project_dir=tmp_project_dir)

        config = {"project_key": "project_value"}
        (tmp_project_dir / "meetup-scheduler-local.json").write_text(json.dumps(config))

        result = manager.get_all(user_level=False)
        assert result == config


class TestConfigManagerGetMerged:
    """Test ConfigManager.get_merged() method."""

    def test_get_merged_combines_configs(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_merged() combines user and project config."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)

        # User config
        user_config = {"user_setting": "user_value"}
        (user_dir / "config.json").write_text(json.dumps(user_config))

        # Project config
        project_config = {"project_setting": "project_value"}
        (tmp_project_dir / "meetup-scheduler-local.json").write_text(
            json.dumps(project_config)
        )

        result = manager.get_merged()
        assert result["user_setting"] == "user_value"
        assert result["project_setting"] == "project_value"

    def test_get_merged_project_overrides_user(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_merged() with project config overriding user config."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)

        # User config
        user_config = {"setting": "user_value"}
        (user_dir / "config.json").write_text(json.dumps(user_config))

        # Project config overrides
        project_config = {"setting": "project_value"}
        (tmp_project_dir / "meetup-scheduler-local.json").write_text(
            json.dumps(project_config)
        )

        result = manager.get_merged()
        assert result["setting"] == "project_value"

    def test_get_merged_deep_merge(
        self, tmp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_merged() performs deep merge."""
        manager = ConfigManager(project_dir=tmp_project_dir)
        user_dir = tmp_project_dir / "user"
        user_dir.mkdir()
        monkeypatch.setattr(manager, "_user_config_dir", user_dir)

        # User config with nested structure
        user_config = {"organizer": {"name": "User Name", "email": "user@example.com"}}
        (user_dir / "config.json").write_text(json.dumps(user_config))

        # Project config with partial override
        project_config = {"organizer": {"name": "Project Name"}}
        (tmp_project_dir / "meetup-scheduler-local.json").write_text(
            json.dumps(project_config)
        )

        result = manager.get_merged()
        assert result["organizer"]["name"] == "Project Name"
        assert result["organizer"]["email"] == "user@example.com"


class TestConfigManagerSaveProjectConfig:
    """Test ConfigManager.save_project_config() method."""

    def test_save_project_config_creates_file(self, tmp_project_dir: Path) -> None:
        """Test save_project_config() creates the file."""
        manager = ConfigManager(project_dir=tmp_project_dir)

        config = {"setting": "value"}
        manager.save_project_config(config)

        config_path = tmp_project_dir / "meetup-scheduler-local.json"
        assert config_path.exists()

    def test_save_project_config_writes_correct_content(
        self, tmp_project_dir: Path
    ) -> None:
        """Test save_project_config() writes correct content."""
        manager = ConfigManager(project_dir=tmp_project_dir)

        config = {"setting": "value", "nested": {"key": "val"}}
        manager.save_project_config(config)

        config_path = tmp_project_dir / "meetup-scheduler-local.json"
        with open(config_path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == config

    def test_save_project_config_updates_cache(self, tmp_project_dir: Path) -> None:
        """Test save_project_config() updates the internal cache."""
        manager = ConfigManager(project_dir=tmp_project_dir)

        config = {"setting": "value"}
        manager.save_project_config(config)

        # Should be cached
        assert manager._project_config == config
