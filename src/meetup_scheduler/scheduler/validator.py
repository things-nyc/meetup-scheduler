##############################################################################
#
# Name: validator.py
#
# Function:
#       JSON Schema validation for meetup-scheduler
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import importlib.resources
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator


@dataclass
class ValidationError:
    """Represents a single validation error."""

    path: str
    message: str

    def __str__(self) -> str:
        """Return human-readable error string."""
        if self.path:
            return f"{self.path}: {self.message}"
        return self.message


class SchemaValidator:
    """Validate JSON documents against bundled schemas."""

    # Available schema names
    EVENTS_SCHEMA = "events"
    CONFIG_SCHEMA = "config"
    VENUES_SCHEMA = "venues"

    class Error(Exception):
        """Exception raised for validation errors."""

        pass

    def __init__(self) -> None:
        """Initialize the schema validator."""
        self._schemas: dict[str, dict[str, Any]] = {}

    def _get_schema_resource(self, schema_name: str) -> Any:
        """Get the resource handle for a bundled schema file.

        Args:
            schema_name: Name of the schema (without .schema.json suffix).

        Returns:
            Resource handle for the schema file.

        Raises:
            Error: If schema name is unknown.
        """
        valid_names = [self.EVENTS_SCHEMA, self.CONFIG_SCHEMA, self.VENUES_SCHEMA]
        if schema_name not in valid_names:
            raise self.Error(f"Unknown schema: {schema_name}")

        return importlib.resources.files("meetup_scheduler.resources.schemas").joinpath(
            f"{schema_name}.schema.json"
        )

    def load_schema(self, schema_name: str) -> dict[str, Any]:
        """Load a schema from package resources.

        Args:
            schema_name: Name of the schema to load.

        Returns:
            Parsed schema dictionary.

        Raises:
            Error: If schema cannot be loaded.
        """
        if schema_name in self._schemas:
            return self._schemas[schema_name]

        schema_resource = self._get_schema_resource(schema_name)

        try:
            schema_text = schema_resource.read_text(encoding="utf-8")
            schema: dict[str, Any] = json.loads(schema_text)
        except (OSError, json.JSONDecodeError) as e:
            raise self.Error(f"Failed to load schema '{schema_name}': {e}") from e

        self._schemas[schema_name] = schema
        return schema

    def validate(
        self,
        data: dict[str, Any],
        schema_name: str,
    ) -> list[ValidationError]:
        """Validate data against a schema.

        Args:
            data: JSON data to validate.
            schema_name: Name of the schema to validate against.

        Returns:
            List of validation errors (empty if valid).
        """
        schema = self.load_schema(schema_name)
        validator = Draft7Validator(schema)

        errors: list[ValidationError] = []
        for error in validator.iter_errors(data):
            path = ".".join(str(p) for p in error.absolute_path)
            errors.append(ValidationError(path=path, message=error.message))

        return errors

    def validate_file(
        self,
        file_path: Path,
        schema_name: str,
    ) -> list[ValidationError]:
        """Validate a JSON file against a schema.

        Args:
            file_path: Path to the JSON file.
            schema_name: Name of the schema to validate against.

        Returns:
            List of validation errors (empty if valid).

        Raises:
            Error: If file cannot be read or parsed.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except OSError as e:
            raise self.Error(f"Cannot read file {file_path}: {e}") from e
        except json.JSONDecodeError as e:
            raise self.Error(f"Invalid JSON in {file_path}: {e}") from e

        return self.validate(data, schema_name)

    def is_valid(self, data: dict[str, Any], schema_name: str) -> bool:
        """Check if data is valid against a schema.

        Args:
            data: JSON data to validate.
            schema_name: Name of the schema to validate against.

        Returns:
            True if valid, False otherwise.
        """
        return len(self.validate(data, schema_name)) == 0
