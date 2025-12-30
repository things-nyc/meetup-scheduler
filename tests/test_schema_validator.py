##############################################################################
#
# Name: test_schema_validator.py
#
# Function:
#       Unit tests for SchemaValidator class
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

from meetup_scheduler.scheduler.validator import SchemaValidator, ValidationError


class TestSchemaValidatorLoadSchema:
    """Test schema loading."""

    def test_load_events_schema(self) -> None:
        """Test loading events schema."""
        validator = SchemaValidator()
        schema = validator.load_schema(SchemaValidator.EVENTS_SCHEMA)
        assert "$schema" in schema
        assert schema["type"] == "object"
        assert "events" in schema["required"]

    def test_load_config_schema(self) -> None:
        """Test loading config schema."""
        validator = SchemaValidator()
        schema = validator.load_schema(SchemaValidator.CONFIG_SCHEMA)
        assert "$schema" in schema
        assert schema["type"] == "object"

    def test_load_venues_schema(self) -> None:
        """Test loading venues schema."""
        validator = SchemaValidator()
        schema = validator.load_schema(SchemaValidator.VENUES_SCHEMA)
        assert "$schema" in schema
        assert schema["type"] == "object"

    def test_load_unknown_schema_raises_error(self) -> None:
        """Test loading unknown schema raises error."""
        validator = SchemaValidator()
        with pytest.raises(SchemaValidator.Error, match="Unknown schema"):
            validator.load_schema("unknown")

    def test_schema_is_cached(self) -> None:
        """Test schema is cached after loading."""
        validator = SchemaValidator()
        schema1 = validator.load_schema(SchemaValidator.EVENTS_SCHEMA)
        schema2 = validator.load_schema(SchemaValidator.EVENTS_SCHEMA)
        assert schema1 is schema2

    def test_all_schemas_have_required_fields(self) -> None:
        """Test all schemas have $schema and description fields."""
        validator = SchemaValidator()
        for schema_name in [
            SchemaValidator.EVENTS_SCHEMA,
            SchemaValidator.CONFIG_SCHEMA,
            SchemaValidator.VENUES_SCHEMA,
        ]:
            schema = validator.load_schema(schema_name)
            assert "$schema" in schema, f"{schema_name} missing $schema"
            assert "description" in schema, f"{schema_name} missing description"


class TestSchemaValidatorValidate:
    """Test JSON validation."""

    def test_valid_events_data(self) -> None:
        """Test valid events data passes validation."""
        validator = SchemaValidator()
        data = {
            "events": [{"title": "Test Event", "startDateTime": "2025-01-02T19:00:00-05:00"}]
        }
        errors = validator.validate(data, SchemaValidator.EVENTS_SCHEMA)
        assert errors == []

    def test_valid_events_with_all_fields(self) -> None:
        """Test valid events data with all fields."""
        validator = SchemaValidator()
        data = {
            "options": {"onConflict": "skip", "seriesMode": "link"},
            "defaults": {"groupUrlname": "test-group", "duration": "2h"},
            "events": [
                {
                    "title": "Full Event",
                    "startDateTime": "2025-01-02T19:00:00-05:00",
                    "description": "Test description",
                    "duration": 120,
                    "venue": "test-venue",
                    "isOnline": False,
                }
            ],
        }
        errors = validator.validate(data, SchemaValidator.EVENTS_SCHEMA)
        assert errors == []

    def test_missing_required_field(self) -> None:
        """Test missing required field fails validation."""
        validator = SchemaValidator()
        data = {"events": [{"title": "Test Event"}]}  # missing startDateTime
        errors = validator.validate(data, SchemaValidator.EVENTS_SCHEMA)
        assert len(errors) > 0
        assert any("startDateTime" in str(e) for e in errors)

    def test_invalid_type(self) -> None:
        """Test invalid type fails validation."""
        validator = SchemaValidator()
        data = {"events": "not an array"}
        errors = validator.validate(data, SchemaValidator.EVENTS_SCHEMA)
        assert len(errors) > 0

    def test_missing_events_key(self) -> None:
        """Test missing events key fails validation."""
        validator = SchemaValidator()
        data = {"other": "data"}
        errors = validator.validate(data, SchemaValidator.EVENTS_SCHEMA)
        assert len(errors) > 0
        assert any("events" in str(e) for e in errors)

    def test_invalid_enum_value(self) -> None:
        """Test invalid enum value fails validation."""
        validator = SchemaValidator()
        data = {"options": {"onConflict": "invalid_value"}, "events": []}
        errors = validator.validate(data, SchemaValidator.EVENTS_SCHEMA)
        assert len(errors) > 0

    def test_valid_config_data(self) -> None:
        """Test valid config data passes validation."""
        validator = SchemaValidator()
        data = {
            "organizer": {"name": "Test Organizer", "email": "test@example.com"},
            "defaultTimezone": "America/New_York",
        }
        errors = validator.validate(data, SchemaValidator.CONFIG_SCHEMA)
        assert errors == []

    def test_valid_venues_data(self) -> None:
        """Test valid venues data passes validation."""
        validator = SchemaValidator()
        data = {
            "venues": [
                {"id": "venue123", "name": "Test Venue", "city": "New York"},
                {"id": "venue456", "name": "Another Venue"},
            ]
        }
        errors = validator.validate(data, SchemaValidator.VENUES_SCHEMA)
        assert errors == []


class TestSchemaValidatorIsValid:
    """Test is_valid() method."""

    def test_is_valid_returns_true_for_valid_data(self) -> None:
        """Test is_valid returns True for valid data."""
        validator = SchemaValidator()
        data = {"events": [{"title": "Event", "startDateTime": "2025-01-01T10:00:00Z"}]}
        assert validator.is_valid(data, SchemaValidator.EVENTS_SCHEMA) is True

    def test_is_valid_returns_false_for_invalid_data(self) -> None:
        """Test is_valid returns False for invalid data."""
        validator = SchemaValidator()
        data = {"invalid": "data"}
        assert validator.is_valid(data, SchemaValidator.EVENTS_SCHEMA) is False

    def test_is_valid_with_empty_events(self) -> None:
        """Test is_valid with empty events array."""
        validator = SchemaValidator()
        data = {"events": []}
        assert validator.is_valid(data, SchemaValidator.EVENTS_SCHEMA) is True


class TestSchemaValidatorValidateFile:
    """Test file validation."""

    def test_validate_valid_file(self, tmp_path: Path) -> None:
        """Test validating a valid JSON file."""
        file_path = tmp_path / "events.json"
        data = {"events": [{"title": "Event", "startDateTime": "2025-01-01T10:00:00Z"}]}
        file_path.write_text(json.dumps(data))

        validator = SchemaValidator()
        errors = validator.validate_file(file_path, SchemaValidator.EVENTS_SCHEMA)
        assert errors == []

    def test_validate_invalid_file(self, tmp_path: Path) -> None:
        """Test validating an invalid JSON file."""
        file_path = tmp_path / "events.json"
        data = {"invalid": "data"}
        file_path.write_text(json.dumps(data))

        validator = SchemaValidator()
        errors = validator.validate_file(file_path, SchemaValidator.EVENTS_SCHEMA)
        assert len(errors) > 0

    def test_validate_nonexistent_file_raises_error(self, tmp_path: Path) -> None:
        """Test validating nonexistent file raises error."""
        file_path = tmp_path / "nonexistent.json"
        validator = SchemaValidator()
        with pytest.raises(SchemaValidator.Error, match="Cannot read file"):
            validator.validate_file(file_path, SchemaValidator.EVENTS_SCHEMA)

    def test_validate_invalid_json_raises_error(self, tmp_path: Path) -> None:
        """Test validating invalid JSON raises error."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("not valid json")

        validator = SchemaValidator()
        with pytest.raises(SchemaValidator.Error, match="Invalid JSON"):
            validator.validate_file(file_path, SchemaValidator.EVENTS_SCHEMA)

    def test_validate_empty_file_raises_error(self, tmp_path: Path) -> None:
        """Test validating empty file raises error."""
        file_path = tmp_path / "empty.json"
        file_path.write_text("")

        validator = SchemaValidator()
        with pytest.raises(SchemaValidator.Error, match="Invalid JSON"):
            validator.validate_file(file_path, SchemaValidator.EVENTS_SCHEMA)


class TestValidationError:
    """Test ValidationError dataclass."""

    def test_str_with_path(self) -> None:
        """Test string representation with path."""
        error = ValidationError(path="events.0.title", message="is required")
        assert str(error) == "events.0.title: is required"

    def test_str_without_path(self) -> None:
        """Test string representation without path."""
        error = ValidationError(path="", message="is required")
        assert str(error) == "is required"

    def test_validation_error_fields(self) -> None:
        """Test ValidationError has correct fields."""
        error = ValidationError(path="test.path", message="test message")
        assert error.path == "test.path"
        assert error.message == "test message"
