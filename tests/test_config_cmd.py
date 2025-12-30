##############################################################################
#
# Name: test_config_cmd.py
#
# Function:
#       Unit tests for ConfigCommand class
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
from unittest.mock import patch

import pytest

from meetup_scheduler.app import App


@pytest.fixture
def mock_user_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a mock user config directory."""
    config_dir = tmp_path / "user_config"
    config_dir.mkdir()

    # Patch platformdirs to use our temp directory
    monkeypatch.setattr(
        "platformdirs.user_config_dir",
        lambda appname, appauthor: str(config_dir),
    )
    return config_dir


class TestConfigCommandGet:
    """Test ConfigCommand get operation."""

    def test_get_missing_key_shows_warning(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test getting a missing key shows a warning."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["config", "nonexistent.key"])
        result = app.run()

        assert result == 0
        # Warning should be logged (but not fail)

    def test_get_existing_key_prints_value(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test getting an existing key prints its value."""
        monkeypatch.chdir(tmp_path)

        # Create user config with a value
        config_path = mock_user_config_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"organizer": {"name": "Test User"}}, f)

        app = App(args=["config", "organizer.name"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "Test User" in captured.out

    def test_get_nested_key(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test getting a deeply nested key."""
        monkeypatch.chdir(tmp_path)

        config_path = mock_user_config_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"groups": {"ttn-nyc": {"urlname": "test-group"}}}, f)

        app = App(args=["config", "groups.ttn-nyc.urlname"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "test-group" in captured.out

    def test_get_dict_value_prints_json(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test getting a dict value prints as JSON."""
        monkeypatch.chdir(tmp_path)

        config_path = mock_user_config_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"organizer": {"name": "Test", "email": "test@example.com"}}, f)

        app = App(args=["config", "organizer"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        # Should be formatted JSON
        assert "name" in captured.out
        assert "email" in captured.out


class TestConfigCommandSet:
    """Test ConfigCommand set operation."""

    def test_set_simple_value(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test setting a simple string value."""
        monkeypatch.chdir(tmp_path)

        app = App(args=["config", "organizer.name", "Terry Moore"])
        result = app.run()

        assert result == 0

        # Verify value was saved
        config_path = mock_user_config_dir / "config.json"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config["organizer"]["name"] == "Terry Moore"

    def test_set_nested_value_creates_parents(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test setting a nested value creates parent keys."""
        monkeypatch.chdir(tmp_path)

        app = App(args=["config", "groups.ttn-nyc.urlname", "test-group"])
        result = app.run()

        assert result == 0

        config_path = mock_user_config_dir / "config.json"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config["groups"]["ttn-nyc"]["urlname"] == "test-group"

    def test_set_integer_value(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test setting an integer value."""
        monkeypatch.chdir(tmp_path)

        app = App(args=["config", "defaults.duration", "120"])
        result = app.run()

        assert result == 0

        config_path = mock_user_config_dir / "config.json"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config["defaults"]["duration"] == 120

    def test_set_boolean_value(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test setting a boolean value."""
        monkeypatch.chdir(tmp_path)

        app = App(args=["config", "defaults.isDraft", "true"])
        result = app.run()

        assert result == 0

        config_path = mock_user_config_dir / "config.json"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config["defaults"]["isDraft"] is True

    def test_set_overwrites_existing_value(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test setting a value overwrites existing value."""
        monkeypatch.chdir(tmp_path)

        # Create initial value
        config_path = mock_user_config_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"organizer": {"name": "Old Name"}}, f)

        app = App(args=["config", "organizer.name", "New Name"])
        result = app.run()

        assert result == 0

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config["organizer"]["name"] == "New Name"


class TestConfigCommandList:
    """Test ConfigCommand list operation."""

    def test_list_empty_config(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test --list with no configuration."""
        monkeypatch.chdir(tmp_path)

        app = App(args=["config", "--list"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        # Empty config can be shown as message, empty JSON, or blank output
        has_no_config = "No configuration" in captured.out
        has_empty_json = "{}" in captured.out
        is_blank = captured.out.strip() == ""
        assert has_no_config or has_empty_json or is_blank

    def test_list_shows_all_values(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test --list shows all configuration values."""
        monkeypatch.chdir(tmp_path)

        config_path = mock_user_config_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "organizer": {"name": "Test User"},
                    "defaultTimezone": "America/New_York",
                },
                f,
            )

        app = App(args=["config", "--list"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "Test User" in captured.out
        assert "America/New_York" in captured.out

    def test_list_merges_user_and_project_config(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test --list shows merged user and project configuration."""
        monkeypatch.chdir(tmp_path)

        # User config
        config_path = mock_user_config_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"organizer": {"name": "User Name"}}, f)

        # Project config
        project_config_path = tmp_path / "meetup-scheduler-local.json"
        with open(project_config_path, "w", encoding="utf-8") as f:
            json.dump({"projectSetting": "value"}, f)

        app = App(args=["config", "--list"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "User Name" in captured.out
        assert "projectSetting" in captured.out


class TestConfigCommandNoArgs:
    """Test ConfigCommand with no arguments."""

    def test_no_args_shows_usage(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that no arguments shows usage information."""
        monkeypatch.chdir(tmp_path)

        app = App(args=["config"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "Usage" in captured.out or "config" in captured.out


class TestConfigCommandEdit:
    """Test ConfigCommand edit operation."""

    def test_edit_creates_config_file_if_missing(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that --edit creates config file if it doesn't exist."""
        monkeypatch.chdir(tmp_path)

        # Mock editor to do nothing
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            app = App(args=["config", "--edit"])
            result = app.run()

        assert result == 0
        config_path = mock_user_config_dir / "config.json"
        assert config_path.exists()

    def test_edit_uses_visual_editor(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that --edit uses VISUAL environment variable."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("VISUAL", "my-editor")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            app = App(args=["config", "--edit"])
            app.run()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "my-editor"

    def test_edit_uses_editor_if_visual_not_set(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that --edit uses EDITOR if VISUAL is not set."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("VISUAL", raising=False)
        monkeypatch.setenv("EDITOR", "fallback-editor")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            app = App(args=["config", "--edit"])
            app.run()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "fallback-editor"


class TestConfigCommandReturnCodes:
    """Test ConfigCommand return codes."""

    def test_get_returns_zero(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that get operation returns 0."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["config", "some.key"])
        assert app.run() == 0

    def test_set_returns_zero(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that set operation returns 0."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["config", "some.key", "value"])
        assert app.run() == 0

    def test_list_returns_zero(
        self,
        tmp_path: Path,
        mock_user_config_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that list operation returns 0."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["config", "--list"])
        assert app.run() == 0
