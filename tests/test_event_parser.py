##############################################################################
#
# Name: test_event_parser.py
#
# Function:
#       Unit tests for EventParser class
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
from unittest.mock import MagicMock

import pytest

from meetup_scheduler.scheduler.parser import EventParser, ParsedEvent, ParsedEventFile


class TestParseDuration:
    """Test duration parsing."""

    def test_integer_minutes(self) -> None:
        """Test parsing integer minutes."""
        parser = EventParser()
        assert parser.parse_duration(60) == 60
        assert parser.parse_duration(90) == 90
        assert parser.parse_duration(120) == 120

    def test_hours_only(self) -> None:
        """Test parsing hours-only format."""
        parser = EventParser()
        assert parser.parse_duration("1h") == 60
        assert parser.parse_duration("2h") == 120
        assert parser.parse_duration("3h") == 180

    def test_minutes_only(self) -> None:
        """Test parsing minutes-only format."""
        parser = EventParser()
        assert parser.parse_duration("30m") == 30
        assert parser.parse_duration("90m") == 90
        assert parser.parse_duration("120m") == 120

    def test_hours_and_minutes(self) -> None:
        """Test parsing combined hours and minutes."""
        parser = EventParser()
        assert parser.parse_duration("1h30m") == 90
        assert parser.parse_duration("2h30m") == 150
        assert parser.parse_duration("1h15m") == 75

    def test_invalid_format_raises_error(self) -> None:
        """Test that invalid formats raise Error."""
        parser = EventParser()
        with pytest.raises(EventParser.Error):
            parser.parse_duration("invalid")
        with pytest.raises(EventParser.Error):
            parser.parse_duration("2 hours")
        with pytest.raises(EventParser.Error):
            parser.parse_duration("2h 30m")  # Space not allowed

    def test_zero_duration_raises_error(self) -> None:
        """Test that zero duration raises Error."""
        parser = EventParser()
        with pytest.raises(EventParser.Error):
            parser.parse_duration(0)
        with pytest.raises(EventParser.Error):
            parser.parse_duration("0h")
        with pytest.raises(EventParser.Error):
            parser.parse_duration("0m")

    def test_negative_duration_raises_error(self) -> None:
        """Test that negative duration raises Error."""
        parser = EventParser()
        with pytest.raises(EventParser.Error):
            parser.parse_duration(-60)

    def test_empty_string_raises_error(self) -> None:
        """Test that empty string raises Error."""
        parser = EventParser()
        with pytest.raises(EventParser.Error):
            parser.parse_duration("")


class TestApplyDefaults:
    """Test defaults application."""

    def test_event_values_take_priority(self) -> None:
        """Test that event values override defaults."""
        parser = EventParser()
        event = {"title": "Event Title", "duration": "2h"}
        defaults = {"title": "Default Title", "duration": "1h", "groupUrlname": "test"}
        result = parser.apply_defaults(event, defaults)
        assert result["title"] == "Event Title"
        assert result["duration"] == "2h"
        assert result["groupUrlname"] == "test"

    def test_defaults_fill_missing_values(self) -> None:
        """Test that defaults fill in missing event values."""
        parser = EventParser()
        event = {"title": "Event Title"}
        defaults = {"groupUrlname": "test-group", "duration": "2h"}
        result = parser.apply_defaults(event, defaults)
        assert result["title"] == "Event Title"
        assert result["groupUrlname"] == "test-group"
        assert result["duration"] == "2h"

    def test_config_defaults_applied(self) -> None:
        """Test that config defaults are applied as lowest priority."""
        mock_config = MagicMock()
        mock_config.get.return_value = {"publishStatus": "PUBLISHED"}
        parser = EventParser(config=mock_config)

        event = {"title": "Test"}
        file_defaults = {"groupUrlname": "test"}
        result = parser.apply_defaults(event, file_defaults)

        assert result["publishStatus"] == "PUBLISHED"

    def test_file_defaults_override_config(self) -> None:
        """Test that file defaults override config defaults."""
        mock_config = MagicMock()
        mock_config.get.return_value = {"publishStatus": "PUBLISHED", "duration": "1h"}
        parser = EventParser(config=mock_config)

        event = {"title": "Test"}
        file_defaults = {"groupUrlname": "test", "publishStatus": "DRAFT"}
        result = parser.apply_defaults(event, file_defaults)

        assert result["publishStatus"] == "DRAFT"  # File default wins
        assert result["duration"] == "1h"  # Config default used


class TestResolveVenue:
    """Test venue alias resolution."""

    def test_no_config_returns_as_is(self) -> None:
        """Test that without config, venue is returned as-is."""
        parser = EventParser()
        assert parser.resolve_venue("venue-123") == "venue-123"

    def test_resolves_alias_to_id(self) -> None:
        """Test resolving a venue alias to its ID."""
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "main-office": {"venueId": "venue-456", "description": "Main Office"},
        }
        parser = EventParser(config=mock_config)
        assert parser.resolve_venue("main-office") == "venue-456"

    def test_unknown_alias_returns_as_is(self) -> None:
        """Test that unknown alias is returned as-is (assumed to be ID)."""
        mock_config = MagicMock()
        mock_config.get.return_value = {}
        parser = EventParser(config=mock_config)
        assert parser.resolve_venue("unknown-venue") == "unknown-venue"

    def test_direct_id_passed_through(self) -> None:
        """Test that direct venue IDs pass through unchanged."""
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "main-office": {"venueId": "venue-456"},
        }
        parser = EventParser(config=mock_config)
        # A venue ID that's not an alias should pass through
        assert parser.resolve_venue("venue-789") == "venue-789"


class TestParseData:
    """Test parsing event data dictionaries."""

    def test_valid_minimal_event(self) -> None:
        """Test parsing a minimal valid event."""
        parser = EventParser()
        data = {
            "events": [
                {
                    "title": "Test Event",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                    "groupUrlname": "test-group",
                }
            ]
        }
        result = parser.parse_data(data)
        assert len(result.events) == 1
        assert result.events[0].title == "Test Event"
        assert result.events[0].group_urlname == "test-group"
        assert result.events[0].duration_minutes == 120  # Default

    def test_event_with_duration(self) -> None:
        """Test parsing event with duration."""
        parser = EventParser()
        data = {
            "events": [
                {
                    "title": "Test Event",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                    "groupUrlname": "test-group",
                    "duration": "2h30m",
                }
            ]
        }
        result = parser.parse_data(data)
        assert result.events[0].duration_minutes == 150

    def test_applies_file_defaults(self) -> None:
        """Test that file defaults are applied to events."""
        parser = EventParser()
        data = {
            "defaults": {
                "groupUrlname": "default-group",
                "duration": "1h30m",
                "publishStatus": "PUBLISHED",
            },
            "events": [
                {
                    "title": "Test Event",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                }
            ],
        }
        result = parser.parse_data(data)
        assert result.events[0].group_urlname == "default-group"
        assert result.events[0].duration_minutes == 90
        assert result.events[0].publish_status == "PUBLISHED"

    def test_event_overrides_defaults(self) -> None:
        """Test that event values override file defaults."""
        parser = EventParser()
        data = {
            "defaults": {
                "groupUrlname": "default-group",
                "duration": "1h",
            },
            "events": [
                {
                    "title": "Test Event",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                    "duration": "3h",
                }
            ],
        }
        result = parser.parse_data(data)
        assert result.events[0].duration_minutes == 180  # Event value wins

    def test_options_preserved(self) -> None:
        """Test that file options are preserved."""
        parser = EventParser()
        data = {
            "options": {"onConflict": "skip", "seriesMode": "link"},
            "events": [
                {
                    "title": "Test",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                    "groupUrlname": "test",
                }
            ],
        }
        result = parser.parse_data(data)
        assert result.options["onConflict"] == "skip"
        assert result.options["seriesMode"] == "link"

    def test_multiple_events(self) -> None:
        """Test parsing multiple events."""
        parser = EventParser()
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {"title": "Event 1", "startDateTime": "2025-02-01T19:00:00-05:00"},
                {"title": "Event 2", "startDateTime": "2025-02-08T19:00:00-05:00"},
                {"title": "Event 3", "startDateTime": "2025-02-15T19:00:00-05:00"},
            ],
        }
        result = parser.parse_data(data)
        assert len(result.events) == 3
        assert result.events[0].title == "Event 1"
        assert result.events[1].title == "Event 2"
        assert result.events[2].title == "Event 3"

    def test_missing_title_raises_error(self) -> None:
        """Test that missing title raises error."""
        parser = EventParser()
        data = {
            "events": [
                {
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                    "groupUrlname": "test",
                }
            ]
        }
        with pytest.raises(EventParser.Error) as exc_info:
            parser.parse_data(data)
        assert "title" in str(exc_info.value).lower()

    def test_missing_start_datetime_raises_error(self) -> None:
        """Test that missing startDateTime raises error."""
        parser = EventParser()
        data = {
            "events": [
                {
                    "title": "Test",
                    "groupUrlname": "test",
                }
            ]
        }
        with pytest.raises(EventParser.Error) as exc_info:
            parser.parse_data(data)
        assert "startDateTime" in str(exc_info.value)

    def test_missing_group_raises_error(self) -> None:
        """Test that missing groupUrlname raises error."""
        parser = EventParser()
        data = {
            "events": [
                {
                    "title": "Test",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                }
            ]
        }
        with pytest.raises(EventParser.Error) as exc_info:
            parser.parse_data(data)
        assert "groupUrlname" in str(exc_info.value)


class TestParseFile:
    """Test parsing event files."""

    def test_parse_valid_file(self, tmp_path: Path) -> None:
        """Test parsing a valid JSON file."""
        parser = EventParser()
        file_path = tmp_path / "events.json"
        data = {
            "defaults": {"groupUrlname": "test-group"},
            "events": [
                {"title": "Test", "startDateTime": "2025-02-01T19:00:00-05:00"}
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        result = parser.parse_file(file_path)
        assert len(result.events) == 1
        assert result.source_path == file_path

    def test_file_not_found_raises_error(self, tmp_path: Path) -> None:
        """Test that missing file raises error."""
        parser = EventParser()
        with pytest.raises(EventParser.Error) as exc_info:
            parser.parse_file(tmp_path / "nonexistent.json")
        assert "Cannot read file" in str(exc_info.value)

    def test_invalid_json_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid JSON raises error."""
        parser = EventParser()
        file_path = tmp_path / "invalid.json"
        file_path.write_text("{ not valid json }", encoding="utf-8")

        with pytest.raises(EventParser.Error) as exc_info:
            parser.parse_file(file_path)
        assert "Invalid JSON" in str(exc_info.value)

    def test_schema_validation_error(self, tmp_path: Path) -> None:
        """Test that schema validation errors are reported."""
        parser = EventParser()
        file_path = tmp_path / "invalid.json"
        # Missing required "events" field
        data = {"defaults": {}}
        file_path.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(EventParser.Error) as exc_info:
            parser.parse_file(file_path)
        assert "Validation errors" in str(exc_info.value)


class TestValidateFile:
    """Test file validation without full parsing."""

    def test_valid_file_returns_empty_list(self, tmp_path: Path) -> None:
        """Test that valid file returns no errors."""
        parser = EventParser()
        file_path = tmp_path / "events.json"
        data = {
            "events": [
                {
                    "title": "Test",
                    "startDateTime": "2025-02-01T19:00:00-05:00",
                }
            ]
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        errors = parser.validate_file(file_path)
        assert errors == []

    def test_invalid_file_returns_errors(self, tmp_path: Path) -> None:
        """Test that invalid file returns errors."""
        parser = EventParser()
        file_path = tmp_path / "events.json"
        data = {"events": [{"description": "Missing title and startDateTime"}]}
        file_path.write_text(json.dumps(data), encoding="utf-8")

        errors = parser.validate_file(file_path)
        assert len(errors) > 0


class TestParsedEvent:
    """Test ParsedEvent dataclass."""

    def test_default_values(self) -> None:
        """Test ParsedEvent default values."""
        event = ParsedEvent(
            title="Test",
            start_datetime="2025-02-01T19:00:00-05:00",
            duration_minutes=120,
            group_urlname="test",
        )
        assert event.publish_status == "DRAFT"
        assert event.event_hosts == []
        assert event.description is None
        assert event.venue_id is None

    def test_all_fields(self) -> None:
        """Test ParsedEvent with all fields."""
        event = ParsedEvent(
            title="Full Event",
            start_datetime="2025-02-01T19:00:00-05:00",
            duration_minutes=180,
            group_urlname="test",
            description="A description",
            venue_id="venue-123",
            publish_status="PUBLISHED",
            event_hosts=["host-1", "host-2"],
            is_online=True,
            event_url="https://example.com",
        )
        assert event.title == "Full Event"
        assert event.is_online is True
        assert len(event.event_hosts) == 2


class TestParsedEventFile:
    """Test ParsedEventFile dataclass."""

    def test_default_values(self) -> None:
        """Test ParsedEventFile default values."""
        result = ParsedEventFile(events=[])
        assert result.events == []
        assert result.options == {}
        assert result.defaults == {}
        assert result.source_path is None
