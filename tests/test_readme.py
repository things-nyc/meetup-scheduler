##############################################################################
#
# Name: test_readme.py
#
# Function:
#       Unit tests for ReadmeReader and ReadmeCommand
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import pytest

from meetup_scheduler.app import App
from meetup_scheduler.resources.readme import ReadmeReader


class TestReadmeReader:
    """Test ReadmeReader class."""

    def test_content_loads_readme(self) -> None:
        """Test that content property loads README."""
        reader = ReadmeReader()
        content = reader.content
        assert "meetup-scheduler" in content
        assert "# meetup-scheduler" in content

    def test_content_is_cached(self) -> None:
        """Test that content is cached after first load."""
        reader = ReadmeReader()
        content1 = reader.content
        content2 = reader.content
        assert content1 is content2

    def test_get_section_returns_content(self) -> None:
        """Test that get_section extracts marked sections."""
        reader = ReadmeReader()
        section = reader.get_section("auth-setup")
        assert section is not None
        assert "login" in section or "authenticate" in section.lower()

    def test_get_section_returns_none_for_missing(self) -> None:
        """Test that get_section returns None for unknown sections."""
        reader = ReadmeReader()
        section = reader.get_section("nonexistent-section")
        assert section is None

    def test_get_all_sections_returns_dict(self) -> None:
        """Test that get_all_sections returns a dictionary."""
        reader = ReadmeReader()
        sections = reader.get_all_sections()
        assert isinstance(sections, dict)
        assert "auth-setup" in sections
        assert "getting-started" in sections

    def test_section_content_excludes_markers(self) -> None:
        """Test that extracted sections don't include marker comments."""
        reader = ReadmeReader()
        section = reader.get_section("auth-setup")
        assert section is not None
        assert "<!-- meetup-scheduler:" not in section


class TestReadmeCommand:
    """Test readme command parsing."""

    def test_readme_command_parsed(self) -> None:
        """Test that readme command is parsed."""
        app = App(args=["readme"])
        assert app.args.command == "readme"

    def test_readme_raw_option(self) -> None:
        """Test readme --raw option."""
        app = App(args=["readme", "--raw"])
        assert app.args.command == "readme"
        assert app.args.raw is True

    def test_readme_raw_default(self) -> None:
        """Test readme --raw defaults to False."""
        app = App(args=["readme"])
        assert app.args.raw is False

    def test_readme_section_option(self) -> None:
        """Test readme --section option."""
        app = App(args=["readme", "--section", "oauth-setup"])
        assert app.args.command == "readme"
        assert app.args.section == "oauth-setup"

    def test_readme_section_default(self) -> None:
        """Test readme --section defaults to None."""
        app = App(args=["readme"])
        assert app.args.section is None


class TestReadmeCommandExecution:
    """Test readme command execution."""

    def test_readme_returns_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that readme command returns 0."""
        app = App(args=["readme", "--raw"])
        result = app.run()
        assert result == 0

        captured = capsys.readouterr()
        assert "meetup-scheduler" in captured.out

    def test_readme_raw_outputs_markdown(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that --raw outputs markdown source."""
        app = App(args=["readme", "--raw"])
        app.run()

        captured = capsys.readouterr()
        assert "# meetup-scheduler" in captured.out
        assert "## Features" in captured.out

    def test_readme_section_outputs_section(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that --section outputs specific section."""
        app = App(args=["readme", "--section", "auth-setup", "--raw"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "login" in captured.out or "authenticate" in captured.out.lower()

    def test_readme_invalid_section_returns_one(
        self, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that invalid section returns 1."""
        app = App(args=["readme", "--section", "nonexistent"])
        result = app.run()

        assert result == 1
        # Error may be in stderr, stdout, or logged
        captured = capsys.readouterr()
        has_error_message = (
            "not found" in captured.err
            or "not found" in captured.out
            or "not found" in caplog.text.lower()
            or "Available sections" in captured.out  # Shows available sections on error
        )
        assert has_error_message
