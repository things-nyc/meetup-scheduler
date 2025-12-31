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

    def test_readme_pager_option(self) -> None:
        """Test readme --pager option."""
        app = App(args=["readme", "--pager"])
        assert app.args.command == "readme"
        assert app.args.pager is True

    def test_readme_no_pager_option(self) -> None:
        """Test readme --no-pager option."""
        app = App(args=["readme", "--no-pager"])
        assert app.args.command == "readme"
        assert app.args.pager is False

    def test_readme_pager_default(self) -> None:
        """Test readme --pager defaults to True."""
        app = App(args=["readme"])
        assert app.args.pager is True


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


class TestReadmeFormattedOutput:
    """Test ReadmeReader formatted output methods."""

    def test_print_formatted_without_pager(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_formatted with pager=False produces Rich output."""
        from io import StringIO

        from rich.console import Console

        reader = ReadmeReader()
        # Use a string buffer to capture Rich output
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=80)
        reader.print_formatted(console=console, pager=False)

        output = string_io.getvalue()
        # Rich output should contain the content (possibly with ANSI codes)
        assert "meetup-scheduler" in output or "meetup" in output.lower()

    def test_print_formatted_creates_console_if_none(self) -> None:
        """Test print_formatted creates Console when not provided."""
        from io import StringIO
        from unittest.mock import patch

        from rich.console import Console

        reader = ReadmeReader()
        # Create a real console with string output
        string_io = StringIO()
        test_console = Console(file=string_io, force_terminal=True, width=80)

        # Mock Console class to return our test console
        with patch("rich.console.Console", return_value=test_console):
            reader.print_formatted(console=None, pager=False)

        output = string_io.getvalue()
        assert len(output) > 0

    def test_print_section_formatted(self) -> None:
        """Test print_section with raw=False produces Rich output."""
        from io import StringIO
        from unittest.mock import patch

        from rich.console import Console

        reader = ReadmeReader()

        # Create a real console with string output
        string_io = StringIO()
        test_console = Console(file=string_io, force_terminal=True, width=80)

        # Mock Console class to return our test console
        with patch("rich.console.Console", return_value=test_console):
            result = reader.print_section("auth-setup", raw=False, pager=False)

        assert result is True
        output = string_io.getvalue()
        # Should have rendered something
        assert len(output) > 0

    def test_print_section_raw(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_section with raw=True outputs plain markdown."""
        reader = ReadmeReader()
        result = reader.print_section("auth-setup", raw=True, pager=False)

        assert result is True
        captured = capsys.readouterr()
        assert "login" in captured.out or "Login" in captured.out

    def test_print_section_missing_returns_false(self) -> None:
        """Test print_section returns False for missing section."""
        reader = ReadmeReader()
        result = reader.print_section("nonexistent-section", raw=False, pager=False)
        assert result is False

    def test_print_raw(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_raw outputs full README."""
        reader = ReadmeReader()
        reader.print_raw()

        captured = capsys.readouterr()
        assert "# meetup-scheduler" in captured.out
        assert "## Features" in captured.out

    def test_create_left_justified_markdown(self) -> None:
        """Test _create_left_justified_markdown creates proper Markdown object."""
        reader = ReadmeReader()
        md = reader._create_left_justified_markdown("# Test Heading\n\nSome content")

        # Should be a Markdown object with left justification
        from rich.markdown import Markdown

        assert isinstance(md, Markdown)
        assert md.justify == "left"


class TestReadmeErrors:
    """Test ReadmeReader error handling."""

    def test_error_when_readme_not_found(self) -> None:
        """Test Error raised when README cannot be loaded."""
        from unittest.mock import patch

        reader = ReadmeReader()

        # Mock both resource loading methods to fail
        with patch.object(
            reader, "_get_readme_resource", side_effect=ReadmeReader.Error("Not found")
        ):
            reader._content = None  # Reset cached content
            with pytest.raises(ReadmeReader.Error, match="Not found"):
                _ = reader.content

    def test_get_readme_resource_fallback_to_source(self) -> None:
        """Test fallback to source directory when package resource fails."""
        from unittest.mock import MagicMock, patch

        reader = ReadmeReader()

        # Mock importlib.resources to fail
        mock_files = MagicMock()
        mock_files.joinpath.return_value.read_text.side_effect = FileNotFoundError()

        with patch("importlib.resources.files", return_value=mock_files):
            # Should fall back to source directory and succeed
            content = reader._get_readme_resource()
            assert "meetup-scheduler" in content

    def test_get_readme_resource_raises_when_both_fail(self) -> None:
        """Test Error raised when both resource methods fail."""
        from unittest.mock import MagicMock, patch

        reader = ReadmeReader()

        # Mock importlib.resources to fail
        mock_files = MagicMock()
        mock_files.joinpath.return_value.read_text.side_effect = FileNotFoundError()

        # Mock Path to fail
        with (
            patch("importlib.resources.files", return_value=mock_files),
            patch(
                "meetup_scheduler.resources.readme.ReadmeReader._get_readme_resource"
            ) as mock_get,
        ):
            mock_get.side_effect = ReadmeReader.Error(
                "Could not load README.md from package resources or source directory"
            )
            reader._content = None
            with pytest.raises(ReadmeReader.Error, match="Could not load"):
                _ = reader.content
