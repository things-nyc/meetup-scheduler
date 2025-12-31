##############################################################################
#
# Name: test_e2e_schedule.py
#
# Function:
#       End-to-end tests for schedule command workflow
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


class TestScheduleDryRunWorkflow:
    """End-to-end tests for dry-run scheduling workflow."""

    def test_dry_run_shows_preview_with_all_event_details(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test complete dry-run workflow shows all event details."""
        # Create a comprehensive event file
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {
                "groupUrlname": "nyc-tech-meetup",
                "duration": "2h",
                "publishStatus": "DRAFT",
            },
            "events": [
                {
                    "title": "January Tech Talk",
                    "startDateTime": "2025-01-09T19:00:00-05:00",
                    "description": "Monthly tech talk and networking",
                    "venue": "main-office",
                },
                {
                    "title": "February Workshop",
                    "startDateTime": "2025-02-06T18:30:00-05:00",
                    "duration": "3h",
                    "publishStatus": "PUBLISHED",
                },
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path)])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()

        # Verify all events are shown
        assert "January Tech Talk" in captured.out
        assert "February Workshop" in captured.out

        # Verify group is applied from defaults
        assert "nyc-tech-meetup" in captured.out

        # Verify durations are parsed correctly
        assert "120" in captured.out  # 2h = 120 minutes
        assert "180" in captured.out  # 3h = 180 minutes

        # Verify statuses
        assert "DRAFT" in captured.out
        assert "PUBLISHED" in captured.out

        # Verify dry-run indicator
        assert "DRY RUN" in captured.out
        assert "Would create 2 event(s)" in captured.out

    def test_dry_run_with_minimal_event(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test dry-run with minimal required fields."""
        file_path = tmp_path / "minimal.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "Minimal Event",
                    "startDateTime": "2025-03-01T10:00:00Z",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path)])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "Minimal Event" in captured.out
        # Default duration should be applied
        assert "120" in captured.out  # Default 2h = 120 minutes


class TestScheduleMarkdownOutput:
    """End-to-end tests for markdown output format."""

    def test_markdown_output_generates_valid_table(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test markdown output generates a valid markdown table."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "First Event",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                    "duration": "2h",
                    "publishStatus": "DRAFT",
                },
                {
                    "title": "Second Event",
                    "startDateTime": "2025-02-15T19:00:00-05:00",
                    "duration": "90m",
                    "publishStatus": "PUBLISHED",
                },
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "markdown"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()

        # Verify markdown table structure
        assert "| # |" in captured.out
        assert "| Date |" in captured.out
        assert "| Time |" in captured.out
        assert "| Title |" in captured.out
        assert "| Duration |" in captured.out
        assert "| Status |" in captured.out

        # Verify separator row
        assert "|---" in captured.out or "| ---" in captured.out

        # Verify event data in table
        assert "First Event" in captured.out
        assert "Second Event" in captured.out
        assert "2025-01-15" in captured.out
        assert "2025-02-15" in captured.out

        # Verify dry-run indicator
        assert "(Dry Run)" in captured.out

    def test_markdown_output_escapes_special_characters(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that pipe characters in event titles are escaped."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "Event | With | Pipes",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "markdown"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        # Pipes should be escaped to not break the table
        assert "Event \\| With \\| Pipes" in captured.out


class TestScheduleJsonOutput:
    """End-to-end tests for JSON output format."""

    def test_json_output_is_valid_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test JSON output is valid and parseable."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "JSON Test Event",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                    "duration": "2h30m",
                    "publishStatus": "DRAFT",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()

        # Parse the JSON output
        output = json.loads(captured.out)

        # Verify structure
        assert output["mode"] == "dry_run"
        assert output["count"] == 1
        assert len(output["events"]) == 1

        # Verify event data
        event = output["events"][0]
        assert event["title"] == "JSON Test Event"
        assert event["startDateTime"] == "2025-01-15T19:00:00-05:00"
        assert event["durationMinutes"] == 150  # 2h30m = 150 minutes
        assert event["groupUrlname"] == "test-group"
        assert event["publishStatus"] == "DRAFT"

    def test_json_output_includes_all_fields(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test JSON output includes all relevant fields when present."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "Full Event",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                    "duration": 90,
                    "description": "A comprehensive event",
                    "venue": "venue-123",
                    "publishStatus": "PUBLISHED",
                    "eventHosts": ["host1", "host2"],
                    "isOnline": False,
                    "eventUrl": "https://example.com/event",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        event = output["events"][0]
        assert event["title"] == "Full Event"
        assert event["durationMinutes"] == 90
        assert event["description"] == "A comprehensive event"
        assert event["venueId"] == "venue-123"
        assert event["publishStatus"] == "PUBLISHED"
        assert event["eventHosts"] == ["host1", "host2"]
        assert event["isOnline"] is False
        assert event["eventUrl"] == "https://example.com/event"


class TestScheduleValidationErrors:
    """End-to-end tests for validation error handling."""

    def test_missing_title_shows_clear_error(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that missing title produces a clear error message."""
        file_path = tmp_path / "invalid.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                    "description": "Event without title",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path)])
        result = app.run()

        assert result == 1
        captured = capsys.readouterr()
        all_output = captured.err + captured.out + caplog.text
        assert "title" in all_output.lower()

    def test_missing_group_shows_clear_error(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that missing groupUrlname produces a clear error message."""
        file_path = tmp_path / "no_group.json"
        data = {
            "events": [
                {
                    "title": "Event Without Group",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path)])
        result = app.run()

        assert result == 1
        captured = capsys.readouterr()
        all_output = captured.err + captured.out + caplog.text
        assert "groupurlname" in all_output.lower()

    def test_invalid_duration_shows_clear_error(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that invalid duration format produces a clear error message."""
        file_path = tmp_path / "bad_duration.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "Bad Duration Event",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                    "duration": "invalid",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path)])
        result = app.run()

        assert result == 1
        captured = capsys.readouterr()
        all_output = captured.err + captured.out + caplog.text
        assert "duration" in all_output.lower() or "invalid" in all_output.lower()


class TestScheduleDefaultsApplication:
    """End-to-end tests for defaults application."""

    def test_file_defaults_override_config_defaults(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that file-level defaults are applied correctly."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {
                "groupUrlname": "file-level-group",
                "duration": "3h",
                "publishStatus": "PUBLISHED",
            },
            "events": [
                {
                    "title": "Event Using Defaults",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        event = output["events"][0]
        assert event["groupUrlname"] == "file-level-group"
        assert event["durationMinutes"] == 180  # 3h from defaults
        assert event["publishStatus"] == "PUBLISHED"

    def test_event_values_override_defaults(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that event-level values override file defaults."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {
                "groupUrlname": "default-group",
                "duration": "2h",
                "publishStatus": "DRAFT",
            },
            "events": [
                {
                    "title": "Overridden Event",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                    "duration": "90m",
                    "publishStatus": "PUBLISHED",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        event = output["events"][0]
        # Group from defaults
        assert event["groupUrlname"] == "default-group"
        # Duration and status overridden at event level
        assert event["durationMinutes"] == 90
        assert event["publishStatus"] == "PUBLISHED"


class TestScheduleMultipleEventsWorkflow:
    """End-to-end tests for scheduling multiple events."""

    def test_schedule_quarterly_events(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test scheduling quarterly events across a year."""
        file_path = tmp_path / "quarterly.json"
        data = {
            "defaults": {
                "groupUrlname": "quarterly-meetup",
                "duration": "2h",
                "publishStatus": "DRAFT",
            },
            "events": [
                {"title": "Q1 Meeting", "startDateTime": "2025-01-15T19:00:00-05:00"},
                {"title": "Q2 Meeting", "startDateTime": "2025-04-15T19:00:00-04:00"},
                {"title": "Q3 Meeting", "startDateTime": "2025-07-15T19:00:00-04:00"},
                {"title": "Q4 Meeting", "startDateTime": "2025-10-15T19:00:00-04:00"},
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path)])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()

        # All events should be listed
        assert "Q1 Meeting" in captured.out
        assert "Q2 Meeting" in captured.out
        assert "Q3 Meeting" in captured.out
        assert "Q4 Meeting" in captured.out

        # Summary should show count
        assert "4 event" in captured.out

    def test_schedule_events_with_varying_durations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test events with different duration formats."""
        file_path = tmp_path / "varied.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "Short Meeting",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                    "duration": 30,  # Integer minutes
                },
                {
                    "title": "Standard Meeting",
                    "startDateTime": "2025-01-22T19:00:00-05:00",
                    "duration": "1h",  # Hours only
                },
                {
                    "title": "Extended Meeting",
                    "startDateTime": "2025-01-29T19:00:00-05:00",
                    "duration": "90m",  # Minutes only
                },
                {
                    "title": "Full Day Workshop",
                    "startDateTime": "2025-02-01T09:00:00-05:00",
                    "duration": "6h30m",  # Hours and minutes
                },
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        # Verify all durations parsed correctly
        assert output["events"][0]["durationMinutes"] == 30
        assert output["events"][1]["durationMinutes"] == 60
        assert output["events"][2]["durationMinutes"] == 90
        assert output["events"][3]["durationMinutes"] == 390  # 6h30m


class TestScheduleOnConflictOption:
    """End-to-end tests for --on-conflict option."""

    def test_on_conflict_from_command_line(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --on-conflict option from command line."""
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "Test Event",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--on-conflict", "skip"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "On conflict: skip" in captured.out

    def test_on_conflict_from_file_options(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test onConflict option from file takes priority."""
        file_path = tmp_path / "events.json"
        data = {
            "options": {"onConflict": "error"},
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "Test Event",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        # Command line says "skip", but file says "error" - file should win
        app = App(args=["--dry-run", "schedule", str(file_path), "--on-conflict", "skip"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        # File-level option should take priority
        assert "On conflict: error" in captured.out


class TestScheduleSourceTracking:
    """End-to-end tests for source file tracking."""

    def test_output_includes_source_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that output includes source file path."""
        file_path = tmp_path / "my_events.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "Test Event",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path)])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "my_events.json" in captured.out

    def test_json_output_includes_source_path(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that JSON output includes source path."""
        file_path = tmp_path / "tracked.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {
                    "title": "Test Event",
                    "startDateTime": "2025-01-15T19:00:00-05:00",
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        app = App(args=["--dry-run", "schedule", str(file_path), "--output", "json"])
        result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["source"] is not None
        assert "tracked.json" in output["source"]
