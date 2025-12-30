##############################################################################
#
# Name: test_init_cmd.py
#
# Function:
#       Unit tests for InitCommand class
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

from meetup_scheduler.app import App


class TestInitCommandDirectories:
    """Test InitCommand directory creation."""

    def test_creates_cache_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that init creates .meetup-scheduler/cache directory."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        result = app.run()

        assert result == 0
        assert (tmp_path / ".meetup-scheduler").is_dir()
        assert (tmp_path / ".meetup-scheduler" / "cache").is_dir()

    def test_creates_events_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init creates events directory."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        result = app.run()

        assert result == 0
        assert (tmp_path / "events").is_dir()

    def test_directories_created_with_parents(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init creates parent directories as needed."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        app.run()

        # Verify nested structure
        cache_dir = tmp_path / ".meetup-scheduler" / "cache"
        assert cache_dir.exists()
        assert cache_dir.is_dir()


class TestInitCommandProjectConfig:
    """Test InitCommand project config file creation."""

    def test_creates_project_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that init creates meetup-scheduler-local.json."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        result = app.run()

        assert result == 0
        config_path = tmp_path / "meetup-scheduler-local.json"
        assert config_path.exists()

    def test_project_config_is_valid_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that created project config is valid JSON."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        app.run()

        config_path = tmp_path / "meetup-scheduler-local.json"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        assert isinstance(config, dict)

    def test_project_config_has_expected_structure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that project config has expected keys."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        app.run()

        config_path = tmp_path / "meetup-scheduler-local.json"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        assert "$schema" in config
        assert "defaults" in config
        assert "venueAliases" in config

    def test_project_config_not_overwritten_without_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that existing project config is not overwritten without --force."""
        monkeypatch.chdir(tmp_path)

        # Create existing config
        config_path = tmp_path / "meetup-scheduler-local.json"
        original_content = {"custom": "value"}
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(original_content, f)

        # Run init without --force
        app = App(args=["init"])
        app.run()

        # Verify original content preserved
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config == original_content

    def test_project_config_overwritten_with_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that --force overwrites existing project config."""
        monkeypatch.chdir(tmp_path)

        # Create existing config
        config_path = tmp_path / "meetup-scheduler-local.json"
        original_content = {"custom": "value"}
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(original_content, f)

        # Run init with --force
        app = App(args=["init", "--force"])
        app.run()

        # Verify new content
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config != original_content
        assert "defaults" in config


class TestInitCommandGitignore:
    """Test InitCommand .gitignore updates."""

    def test_creates_gitignore_if_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init creates .gitignore if it doesn't exist."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        app.run()

        gitignore_path = tmp_path / ".gitignore"
        assert gitignore_path.exists()

    def test_adds_patterns_to_gitignore(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init adds required patterns to .gitignore."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        app.run()

        gitignore_path = tmp_path / ".gitignore"
        with open(gitignore_path, encoding="utf-8") as f:
            content = f.read()

        assert ".meetup-scheduler/" in content
        assert "meetup-scheduler-local.json" in content

    def test_appends_to_existing_gitignore(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init appends to existing .gitignore."""
        monkeypatch.chdir(tmp_path)

        # Create existing .gitignore
        gitignore_path = tmp_path / ".gitignore"
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("*.pyc\n__pycache__/\n")

        app = App(args=["init"])
        app.run()

        with open(gitignore_path, encoding="utf-8") as f:
            content = f.read()

        # Original content preserved
        assert "*.pyc" in content
        assert "__pycache__/" in content
        # New patterns added
        assert ".meetup-scheduler/" in content

    def test_does_not_duplicate_patterns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that running init twice doesn't duplicate .gitignore patterns."""
        monkeypatch.chdir(tmp_path)

        # Run init twice
        App(args=["init"]).run()
        App(args=["init"]).run()

        gitignore_path = tmp_path / ".gitignore"
        with open(gitignore_path, encoding="utf-8") as f:
            content = f.read()

        # Count occurrences - should only appear once
        assert content.count(".meetup-scheduler/") == 1


class TestInitCommandReturnCode:
    """Test InitCommand return codes."""

    def test_returns_zero_on_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that init returns 0 on success."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        result = app.run()

        assert result == 0

    def test_returns_zero_when_already_initialized(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init returns 0 even if already initialized."""
        monkeypatch.chdir(tmp_path)

        # Run init twice
        App(args=["init"]).run()
        result = App(args=["init"]).run()

        assert result == 0


class TestInitCommandIdempotent:
    """Test that InitCommand is idempotent."""

    def test_can_run_multiple_times(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that init can be run multiple times without error."""
        monkeypatch.chdir(tmp_path)

        for _ in range(3):
            app = App(args=["init"])
            result = app.run()
            assert result == 0

    def test_preserves_existing_files_on_rerun(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that running init again preserves user-modified files."""
        monkeypatch.chdir(tmp_path)

        # Initial run
        App(args=["init"]).run()

        # Modify project config
        config_path = tmp_path / "meetup-scheduler-local.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"modified": True}, f)

        # Add file to events directory
        (tmp_path / "events" / "my-events.json").write_text('{"events": []}')

        # Run init again
        App(args=["init"]).run()

        # Verify modifications preserved
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert config.get("modified") is True

        assert (tmp_path / "events" / "my-events.json").exists()
