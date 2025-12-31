##############################################################################
#
# Name: test_schedule_cmd.py
#
# Function:
#       Unit tests for ScheduleCommand class
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


class TestScheduleCommandParsing:
    """Test schedule command argument parsing."""

    def test_schedule_command_parsed(self) -> None:
        """Test that schedule command is parsed."""
        app = App(args=["schedule", "events.json"])
        assert app.args.command == "schedule"
        assert app.args.file == "events.json"

    def test_schedule_output_option(self) -> None:
        """Test schedule --output option."""
        app = App(args=["schedule", "events.json", "--output", "markdown"])
        assert app.args.output == "markdown"

    def test_schedule_output_default(self) -> None:
        """Test schedule --output defaults to summary."""
        app = App(args=["schedule", "events.json"])
        assert app.args.output == "summary"

    def test_schedule_on_conflict_option(self) -> None:
        """Test schedule --on-conflict option."""
        app = App(args=["schedule", "events.json", "--on-conflict", "skip"])
        assert app.args.on_conflict == "skip"

    def test_schedule_on_conflict_default(self) -> None:
        """Test schedule --on-conflict defaults to prompt."""
        app = App(args=["schedule", "events.json"])
        assert app.args.on_conflict == "prompt"

    def test_schedule_dry_run_option(self) -> None:
        """Test schedule with global --dry-run option."""
        app = App(args=["--dry-run", "schedule", "events.json"])
        assert app.args.dry_run is True


class TestScheduleCommandExecution:
    """Test schedule command execution."""

    def test_missing_file_argument_raises_error(
        self, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that missing file argument raises error."""
        app = App(args=["schedule"])
        result = app.run()
        assert result == 1
        captured = capsys.readouterr()
        has_error = (
            "No event file" in captured.err
            or "No event file" in captured.out
            or "No event file" in caplog.text
        )
        assert has_error

    def test_nonexistent_file_raises_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that nonexistent file raises error."""
        app = App(args=["schedule", str(tmp_path / "nonexistent.json")])
        result = app.run()
        assert result == 1
        captured = capsys.readouterr()
        has_error = (
            "not found" in captured.err.lower()
            or "not found" in captured.out.lower()
            or "not found" in caplog.text.lower()
        )
        assert has_error

    def test_schedule_dry_run_valid_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test dry-run with valid file."""
        # Create test event file
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "Test Meeting",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                    "duration": "2h",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path)])
        result = app.run()
        assert result == 0

        captured = capsys.readouterr()
        assert "Test Meeting" in captured.out
        assert "test-group" in captured.out
        assert "120" in captured.out  # Duration in minutes

    def test_schedule_multiple_events(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test scheduling multiple events."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test-group", "duration": "2h"},
            "events": [
                {"title": "Event 1", "startDateTime": "2025-02-01T19:00:00-05:00"},
                {"title": "Event 2", "startDateTime": "2025-02-08T19:00:00-05:00"},
                {"title": "Event 3", "startDateTime": "2025-02-15T19:00:00-05:00"},
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path)])
        result = app.run()
        assert result == 0

        captured = capsys.readouterr()
        assert "Event 1" in captured.out
        assert "Event 2" in captured.out
        assert "Event 3" in captured.out
        assert "3 event" in captured.out


class TestScheduleCommandOutput:
    """Test schedule command output formats."""

    @pytest.fixture
    def valid_event_file(self, tmp_path: Path) -> Path:
        """Create a valid event file for testing."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "Test Event",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                    "duration": "2h",
                    "publishStatus": "DRAFT",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")
        return file_path

    def test_summary_output(
        self, valid_event_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test summary output format."""
        app = App(args=["--dry-run", "schedule", str(valid_event_file), "--output", "summary"])
        result = app.run()
        assert result == 0

        captured = capsys.readouterr()
        assert "Schedule Summary" in captured.out
        assert "Test Event" in captured.out
        assert "DRAFT" in captured.out

    def test_markdown_output(
        self, valid_event_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test markdown output format."""
        app = App(args=["--dry-run", "schedule", str(valid_event_file), "--output", "markdown"])
        result = app.run()
        assert result == 0

        captured = capsys.readouterr()
        # Check for markdown table headers
        assert "| #" in captured.out
        assert "| Date" in captured.out
        assert "| Title" in captured.out
        assert "Test Event" in captured.out

    def test_json_output(
        self, valid_event_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test JSON output format."""
        app = App(args=["--dry-run", "schedule", str(valid_event_file), "--output", "json"])
        result = app.run()
        assert result == 0

        captured = capsys.readouterr()
        # Parse JSON output
        output = json.loads(captured.out)
        assert output["mode"] == "dry_run"
        assert output["count"] == 1
        assert len(output["events"]) == 1
        assert output["events"][0]["title"] == "Test Event"

    def test_json_output_has_duration_minutes(
        self, valid_event_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that JSON output includes parsed duration in minutes."""
        app = App(args=["--dry-run", "schedule", str(valid_event_file), "--output", "json"])
        app.run()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["events"][0]["durationMinutes"] == 120


class TestScheduleCommandValidation:
    """Test schedule command validation."""

    def test_invalid_json_raises_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that invalid JSON raises error."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("{ not valid json }", encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path)])
        result = app.run()
        assert result == 1

        captured = capsys.readouterr()
        has_error = (
            "Invalid JSON" in captured.err
            or "Invalid JSON" in captured.out
            or "Invalid JSON" in caplog.text
        )
        assert has_error

    def test_missing_required_field_raises_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that missing required fields raise error."""
        file_path = tmp_path / "events.json"
        data = {
            "events": [
                {"description": "Missing title and startDateTime"}
            ]
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path)])
        result = app.run()
        assert result == 1

        captured = capsys.readouterr()
        # Should have validation error
        has_error = (
            "title" in captured.err.lower()
            or "title" in captured.out.lower()
            or "title" in caplog.text.lower()
        )
        assert has_error

    def test_empty_events_array(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test handling of empty events array."""
        file_path = tmp_path / "events.json"
        data = {"events": []}
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path)])
        result = app.run()
        assert result == 0  # Empty is valid, just nothing to do


class TestScheduleCommandTimezone:
    """Test timezone handling in schedule command."""

    def test_datetime_with_explicit_timezone_used_as_is(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that datetime with explicit timezone offset is used as-is."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test", "timezone": "America/Chicago"},
            "events": [
                {
                    "title": "Test",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        app.run()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        # Should keep the original timezone offset, not change to Chicago time
        assert output["events"][0]["startDateTime"] == "2025-02-01T19:00:00-05:00"

    def test_datetime_without_timezone_uses_file_defaults(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that datetime without timezone uses defaults.timezone from file."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test", "timezone": "America/New_York"},
            "events": [
                {
                    "title": "Test",
                    "startDateTime": "2025-02-01T19:00",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        app.run()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        # Should add the timezone offset from defaults.timezone
        # February in EST is -05:00
        assert "-05:00" in output["events"][0]["startDateTime"]

    def test_datetime_without_timezone_uses_config_default(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that datetime uses config defaultTimezone when not in file."""
        from meetup_scheduler.config.manager import ConfigManager

        # Patch ConfigManager.get to return our test timezone
        original_get = ConfigManager.get

        def patched_get(
            self: ConfigManager, key: str, *, default: object = None
        ) -> object:
            if key == "defaultTimezone":
                return "America/Los_Angeles"
            return original_get(self, key, default=default)

        monkeypatch.setattr(ConfigManager, "get", patched_get)

        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test"},
            "events": [
                {
                    "title": "Test",
                    "startDateTime": "2025-02-01T19:00",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        app.run()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        # Should add the timezone offset from config defaultTimezone
        # February in PST is -08:00
        assert "-08:00" in output["events"][0]["startDateTime"]


class TestScheduleCommandDurations:
    """Test duration parsing in schedule command."""

    def test_duration_hours(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test hours-only duration parsing."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test"},
            "events": [
                {
                    "title": "Test",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                    "duration": "3h",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        app.run()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["events"][0]["durationMinutes"] == 180

    def test_duration_minutes(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test minutes-only duration parsing."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test"},
            "events": [
                {
                    "title": "Test",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                    "duration": "90m",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        app.run()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["events"][0]["durationMinutes"] == 90

    def test_duration_hours_and_minutes(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test combined hours and minutes duration parsing."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test"},
            "events": [
                {
                    "title": "Test",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                    "duration": "1h30m",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        app.run()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["events"][0]["durationMinutes"] == 90

    def test_duration_integer(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test integer duration (minutes)."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test"},
            "events": [
                {
                    "title": "Test",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                    "duration": 45,
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        app.run()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["events"][0]["durationMinutes"] == 45
