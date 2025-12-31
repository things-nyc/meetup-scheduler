##############################################################################
#
# Name: test_generate_cmd.py
#
# Function:
#       Unit tests for GenerateCommand class
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


class TestGenerateCommandParsing:
    """Test generate command argument parsing."""

    def test_generate_command_parsed(self) -> None:
        """Test that generate command is parsed."""
        app = App(args=["generate"])
        assert app.args.command == "generate"

    def test_generate_pattern_option(self) -> None:
        """Test generate --pattern option."""
        app = App(args=["generate", "--pattern", "first Thursday"])
        assert app.args.pattern == "first Thursday"

    def test_generate_group_option(self) -> None:
        """Test generate --group option."""
        app = App(args=["generate", "--group", "test-group"])
        assert app.args.group == "test-group"

    def test_generate_count_option(self) -> None:
        """Test generate --count option."""
        app = App(args=["generate", "--count", "6"])
        assert app.args.count == 6

    def test_generate_count_default(self) -> None:
        """Test generate --count defaults to 12."""
        app = App(args=["generate"])
        assert app.args.count == 12

    def test_generate_start_option(self) -> None:
        """Test generate --start option."""
        app = App(args=["generate", "--start", "2025-01-01"])
        assert app.args.start == "2025-01-01"

    def test_generate_end_option(self) -> None:
        """Test generate --end option."""
        app = App(args=["generate", "--end", "2025-12-31"])
        assert app.args.end == "2025-12-31"

    def test_generate_output_option(self) -> None:
        """Test generate --output option."""
        app = App(args=["generate", "--output", "events.json"])
        assert app.args.output == "events.json"

    def test_generate_series_option(self) -> None:
        """Test generate --series option."""
        app = App(args=["generate", "--series", "weekly-meetup"])
        assert app.args.series == "weekly-meetup"


class TestGenerateCommandExecution:
    """Test generate command execution."""

    def test_missing_pattern_raises_error(
        self, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that missing pattern raises error."""
        app = App(args=["generate"])
        result = app.run()

        assert result == 1
        captured = capsys.readouterr()
        has_error = (
            "Pattern is required" in captured.err
            or "Pattern is required" in captured.out
            or "Pattern is required" in caplog.text
        )
        assert has_error

    def test_generate_first_thursday(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test generating first Thursday events."""
        app = App(
            args=[
                "generate",
                "--pattern",
                "first Thursday",
                "--start",
                "2025-01-01",
                "--count",
                "3",
            ]
        )
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()

        # Parse JSON output
        output = json.loads(captured.out)
        assert "events" in output
        assert len(output["events"]) == 3

        # Verify dates
        assert output["events"][0]["startDateTime"].startswith("2025-01-02")
        assert output["events"][1]["startDateTime"].startswith("2025-02-06")
        assert output["events"][2]["startDateTime"].startswith("2025-03-06")

    def test_generate_with_group(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test generating events with group specified."""
        app = App(
            args=[
                "generate",
                "--pattern",
                "first Thursday",
                "--group",
                "test-group",
                "--start",
                "2025-01-01",
                "--count",
                "1",
            ]
        )
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["defaults"]["groupUrlname"] == "test-group"

    def test_generate_with_end_date(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test generating events with end date."""
        app = App(
            args=[
                "generate",
                "--pattern",
                "first Thursday",
                "--start",
                "2025-01-01",
                "--end",
                "2025-04-01",
            ]
        )
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        # Should have 3 events (Jan, Feb, Mar - not April)
        assert len(output["events"]) == 3

    def test_generate_complex_pattern(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test generating with complex 'after' pattern."""
        app = App(
            args=[
                "generate",
                "--pattern",
                "first Thursday after first Tuesday",
                "--start",
                "2025-01-01",
                "--count",
                "3",
            ]
        )
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert len(output["events"]) == 3
        # January: First Tuesday = Jan 7, First Thursday after = Jan 9
        assert output["events"][0]["startDateTime"].startswith("2025-01-09")


class TestGenerateCommandOutput:
    """Test generate command output formats."""

    def test_output_to_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test outputting to a file."""
        output_file = tmp_path / "events.json"

        app = App(
            args=[
                "generate",
                "--pattern",
                "first Thursday",
                "--start",
                "2025-01-01",
                "--count",
                "2",
                "--output",
                str(output_file),
            ]
        )
        result = app.run()

        assert result == 0
        assert output_file.exists()

        # Read and verify output file
        content = output_file.read_text(encoding="utf-8")
        output = json.loads(content)
        assert len(output["events"]) == 2

    def test_output_is_valid_json(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that output is valid JSON."""
        app = App(
            args=[
                "generate",
                "--pattern",
                "first Thursday",
                "--start",
                "2025-01-01",
                "--count",
                "1",
            ]
        )
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()

        # Should be valid JSON
        output = json.loads(captured.out)
        assert "events" in output

    def test_events_have_title_and_datetime(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that generated events have title and startDateTime."""
        app = App(
            args=[
                "generate",
                "--pattern",
                "first Thursday",
                "--start",
                "2025-01-01",
                "--count",
                "1",
            ]
        )
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        event = output["events"][0]
        assert "title" in event
        assert "startDateTime" in event
        assert event["title"]  # Not empty
        assert event["startDateTime"]  # Not empty


class TestGenerateCommandDateParsing:
    """Test date parsing in generate command."""

    def test_iso_date_format(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test ISO date format parsing."""
        app = App(
            args=[
                "generate",
                "--pattern",
                "first Thursday",
                "--start",
                "2025-06-01",
                "--count",
                "1",
            ]
        )
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        # First Thursday of June 2025 is June 5
        assert output["events"][0]["startDateTime"].startswith("2025-06-05")

    def test_today_keyword(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test 'today' keyword for start date."""
        app = App(
            args=[
                "generate",
                "--pattern",
                "first Thursday",
                "--start",
                "today",
                "--count",
                "1",
            ]
        )
        result = app.run()

        # Should succeed - we can't verify exact date but it should work
        assert result == 0

    def test_invalid_date_raises_error(
        self, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test invalid date format raises error."""
        app = App(
            args=[
                "generate",
                "--pattern",
                "first Thursday",
                "--start",
                "not-a-date",
                "--count",
                "1",
            ]
        )
        result = app.run()

        assert result == 1
        captured = capsys.readouterr()
        all_output = captured.err + captured.out + caplog.text
        assert "invalid" in all_output.lower() or "date" in all_output.lower()


class TestGenerateCommandPatterns:
    """Test various recurrence patterns."""

    def test_last_friday_pattern(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test last Friday pattern."""
        app = App(
            args=[
                "generate",
                "--pattern",
                "last Friday",
                "--start",
                "2025-01-01",
                "--count",
                "3",
            ]
        )
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert len(output["events"]) == 3
        # Last Fridays: Jan 31, Feb 28, Mar 28
        assert output["events"][0]["startDateTime"].startswith("2025-01-31")
        assert output["events"][1]["startDateTime"].startswith("2025-02-28")
        assert output["events"][2]["startDateTime"].startswith("2025-03-28")

    def test_second_wednesday_pattern(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test second Wednesday pattern."""
        app = App(
            args=[
                "generate",
                "--pattern",
                "second Wednesday",
                "--start",
                "2025-01-01",
                "--count",
                "3",
            ]
        )
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert len(output["events"]) == 3
        assert output["events"][0]["startDateTime"].startswith("2025-01-08")
        assert output["events"][1]["startDateTime"].startswith("2025-02-12")
        assert output["events"][2]["startDateTime"].startswith("2025-03-12")

    def test_invalid_pattern_raises_error(
        self, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test invalid pattern raises error."""
        app = App(
            args=[
                "generate",
                "--pattern",
                "invalid pattern",
                "--start",
                "2025-01-01",
                "--count",
                "1",
            ]
        )
        result = app.run()

        assert result == 1
        captured = capsys.readouterr()
        all_output = captured.err + captured.out + caplog.text
        assert "invalid" in all_output.lower() or "pattern" in all_output.lower()


class TestGenerateCommandIntegration:
    """Integration tests for generate command workflow."""

    def test_generate_then_schedule_dry_run(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that generated output can be used by schedule command."""
        output_file = tmp_path / "events.json"

        # Generate events
        app = App(
            args=[
                "generate",
                "--pattern",
                "first Thursday",
                "--group",
                "test-group",
                "--start",
                "2025-01-01",
                "--count",
                "3",
                "--output",
                str(output_file),
            ]
        )
        result = app.run()
        assert result == 0

        # Read generated file
        content = output_file.read_text(encoding="utf-8")
        data = json.loads(content)

        # Add title to events (if not already present with meaningful value)
        for i, event in enumerate(data["events"], 1):
            if not event.get("title") or event["title"].startswith("Event on"):
                event["title"] = f"Test Event {i}"

        # Write back
        output_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Clear capsys
        capsys.readouterr()

        # Schedule the generated events (dry-run)
        app2 = App(args=["--dry-run", "schedule", str(output_file), "--output", "json"])
        result = app2.run()

        assert result == 0
        captured = capsys.readouterr()
        schedule_output = json.loads(captured.out)

        assert schedule_output["mode"] == "dry_run"
        assert schedule_output["count"] == 3
