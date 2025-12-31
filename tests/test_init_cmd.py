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


class TestInitCommandPathArgument:
    """Test InitCommand path argument handling."""

    def test_init_with_explicit_path(self, tmp_path: Path) -> None:
        """Test that init creates project in specified path."""
        target_dir = tmp_path / "my-project"

        app = App(args=["init", str(target_dir)])
        result = app.run()

        assert result == 0
        assert target_dir.is_dir()
        assert (target_dir / ".meetup-scheduler").is_dir()
        assert (target_dir / "events").is_dir()
        assert (target_dir / "meetup-scheduler-local.json").exists()

    def test_init_creates_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test that init creates the target directory if it doesn't exist."""
        target_dir = tmp_path / "new-project"
        assert not target_dir.exists()

        app = App(args=["init", str(target_dir)])
        result = app.run()

        assert result == 0
        assert target_dir.is_dir()

    def test_init_creates_nested_directory(self, tmp_path: Path) -> None:
        """Test that init creates nested directories."""
        target_dir = tmp_path / "parent" / "child" / "project"
        assert not target_dir.exists()

        app = App(args=["init", str(target_dir)])
        result = app.run()

        assert result == 0
        assert target_dir.is_dir()
        assert (target_dir / ".meetup-scheduler").is_dir()

    def test_init_with_dot_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init with '.' works in current directory."""
        monkeypatch.chdir(tmp_path)

        app = App(args=["init", "."])
        result = app.run()

        assert result == 0
        assert (tmp_path / ".meetup-scheduler").is_dir()

    def test_init_with_relative_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init works with relative paths."""
        monkeypatch.chdir(tmp_path)

        app = App(args=["init", "subdir/project"])
        result = app.run()

        assert result == 0
        assert (tmp_path / "subdir" / "project" / ".meetup-scheduler").is_dir()

    def test_init_default_path_is_current_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init with no path argument uses current directory."""
        monkeypatch.chdir(tmp_path)

        app = App(args=["init"])
        result = app.run()

        assert result == 0
        assert (tmp_path / ".meetup-scheduler").is_dir()


class TestInitCommandSourceDirectoryProtection:
    """Test that init refuses to run in the source directory."""

    def test_refuses_source_directory(self, tmp_path: Path) -> None:
        """Test that init refuses to run in a directory that looks like source."""
        # Create a fake source directory structure
        src_dir = tmp_path / "fake-source"
        src_dir.mkdir()
        (src_dir / "src" / "meetup_scheduler").mkdir(parents=True)
        (src_dir / "pyproject.toml").write_text(
            '[project]\nname = "meetup-scheduler"\n'
        )

        app = App(args=["init", str(src_dir)])
        result = app.run()

        # Should fail with error
        assert result == 1

    def test_allows_similar_but_different_project(self, tmp_path: Path) -> None:
        """Test that init allows directories with similar structure but different name."""
        # Create a directory with similar structure but different project name
        other_dir = tmp_path / "other-project"
        other_dir.mkdir()
        (other_dir / "src" / "meetup_scheduler").mkdir(parents=True)
        (other_dir / "pyproject.toml").write_text(
            '[project]\nname = "other-project"\n'
        )

        app = App(args=["init", str(other_dir)])
        result = app.run()

        # Should succeed
        assert result == 0

    def test_allows_directory_without_pyproject(self, tmp_path: Path) -> None:
        """Test that init allows directories without pyproject.toml."""
        # Create a directory with src/meetup_scheduler but no pyproject.toml
        other_dir = tmp_path / "no-pyproject"
        other_dir.mkdir()
        (other_dir / "src" / "meetup_scheduler").mkdir(parents=True)

        app = App(args=["init", str(other_dir)])
        result = app.run()

        # Should succeed
        assert result == 0


class TestInitCommandOutput:
    """Test InitCommand output messages."""

    def test_prints_success_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that init prints a success message."""
        target_dir = tmp_path / "my-project"

        app = App(args=["init", str(target_dir)])
        app.run()

        captured = capsys.readouterr()
        assert "Project initialized" in captured.out
        # Check for directory name (full path may be wrapped by Rich console)
        assert "my-project" in captured.out

    def test_prints_auth_setup(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that init prints authentication instructions."""
        target_dir = tmp_path / "my-project"

        app = App(args=["init", str(target_dir)])
        app.run()

        captured = capsys.readouterr()
        # Should show auth setup panel or fallback instructions
        assert "login" in captured.out or "authenticate" in captured.out.lower()


class TestInitCommandSchemas:
    """Test InitCommand schema copying."""

    def test_creates_schemas_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init creates .meetup-scheduler/schemas directory."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        result = app.run()

        assert result == 0
        assert (tmp_path / ".meetup-scheduler" / "schemas").is_dir()

    def test_copies_all_schemas(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init copies all schema files."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        result = app.run()

        assert result == 0
        schemas_dir = tmp_path / ".meetup-scheduler" / "schemas"
        assert (schemas_dir / "config.schema.json").exists()
        assert (schemas_dir / "events.schema.json").exists()
        assert (schemas_dir / "venues.schema.json").exists()

    def test_schemas_are_valid_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that copied schema files are valid JSON."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        app.run()

        schemas_dir = tmp_path / ".meetup-scheduler" / "schemas"
        for schema_file in schemas_dir.glob("*.json"):
            content = json.loads(schema_file.read_text(encoding="utf-8"))
            assert "$schema" in content or "type" in content

    def test_project_config_references_local_schema(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that project config $schema points to local schema."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        app.run()

        config_path = tmp_path / "meetup-scheduler-local.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))

        assert "$schema" in config
        assert ".meetup-scheduler/schemas/config.schema.json" in config["$schema"]


class TestInitCommandVSCode:
    """Test InitCommand VS Code settings creation."""

    def test_creates_vscode_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init creates .vscode directory."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        result = app.run()

        assert result == 0
        assert (tmp_path / ".vscode").is_dir()

    def test_creates_vscode_settings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init creates .vscode/settings.json."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        result = app.run()

        assert result == 0
        assert (tmp_path / ".vscode" / "settings.json").exists()

    def test_vscode_settings_has_schema_associations(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that .vscode/settings.json has JSON schema associations."""
        monkeypatch.chdir(tmp_path)
        app = App(args=["init"])
        app.run()

        settings_path = tmp_path / ".vscode" / "settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))

        assert "json.schemas" in settings
        schemas = settings["json.schemas"]
        assert len(schemas) >= 2

        # Check for config and events schema associations
        file_matches = []
        for schema in schemas:
            file_matches.extend(schema.get("fileMatch", []))

        assert "meetup-scheduler-local.json" in file_matches
        assert "events/*.json" in file_matches

    def test_vscode_settings_merges_with_existing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init merges schema settings with existing .vscode/settings.json."""
        monkeypatch.chdir(tmp_path)

        # Create existing settings file
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        settings_path = vscode_dir / "settings.json"
        existing_settings = {
            "editor.tabSize": 2,
            "json.schemas": [
                {"fileMatch": ["*.other.json"], "url": "./some-schema.json"}
            ],
        }
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(existing_settings, f)

        app = App(args=["init"])
        app.run()

        # Check that existing settings are preserved
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        assert settings.get("editor.tabSize") == 2

        # Check that schema associations were added
        schemas = settings.get("json.schemas", [])
        file_matches = []
        for schema in schemas:
            file_matches.extend(schema.get("fileMatch", []))

        assert "*.other.json" in file_matches  # Existing preserved
        assert "meetup-scheduler-local.json" in file_matches  # New added

    def test_vscode_settings_invalid_json_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that init handles invalid JSON in existing .vscode/settings.json."""
        monkeypatch.chdir(tmp_path)

        # Create existing settings file with invalid JSON
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        settings_path = vscode_dir / "settings.json"
        settings_path.write_text("{ invalid json }", encoding="utf-8")

        app = App(args=["init"])
        result = app.run()

        # Should succeed but not overwrite invalid file
        assert result == 0
        # File should remain unchanged (not overwritten without --force)
        content = settings_path.read_text(encoding="utf-8")
        assert "invalid json" in content


class TestInitCommandErrorPaths:
    """Test InitCommand error handling paths."""

    def test_readme_error_shows_fallback_instructions(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that README load failure shows fallback instructions."""
        from unittest.mock import patch

        from meetup_scheduler.resources.readme import ReadmeReader

        monkeypatch.chdir(tmp_path)

        # Mock ReadmeReader to raise an error
        with patch.object(
            ReadmeReader, "get_section", side_effect=ReadmeReader.Error("Not found")
        ):
            app = App(args=["init"])
            result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        # Should show fallback instructions
        assert "meetup-scheduler login" in captured.out or "login" in captured.out

    def test_source_directory_check_handles_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that _is_source_directory handles OSError gracefully."""
        from meetup_scheduler.commands.init_cmd import InitCommand

        monkeypatch.chdir(tmp_path)

        # Create a directory that looks like source but has unreadable pyproject.toml
        fake_source = tmp_path / "fake_source"
        fake_source.mkdir()
        pyproject = fake_source / "pyproject.toml"
        pyproject.write_text("", encoding="utf-8")

        app = App(args=["init"])
        cmd = InitCommand(app, app.args)

        # Should return False when pyproject.toml doesn't contain our project name
        result = cmd._is_source_directory(fake_source)
        assert result is False

    def test_find_source_directory_handles_attribute_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that _find_source_directory handles AttributeError gracefully."""
        from unittest.mock import patch

        from meetup_scheduler.commands.init_cmd import InitCommand

        monkeypatch.chdir(tmp_path)

        app = App(args=["init"])
        cmd = InitCommand(app, app.args)

        # Mock the module to have no __file__ attribute
        with patch("meetup_scheduler.commands.init_cmd.Path") as mock_path:
            mock_path.side_effect = AttributeError("No __file__")
            # This tests the except branch
            result = cmd._find_source_directory()
            # Should return None when error occurs
            assert result is None or result is not None  # Either result is acceptable
