##############################################################################
#
# Name: parser.py
#
# Function:
#       EventParser class for parsing and validating event JSON files
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
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from meetup_scheduler.scheduler.validator import SchemaValidator, ValidationError

if TYPE_CHECKING:
    from meetup_scheduler.config.manager import ConfigManager


@dataclass
class ParsedEvent:
    """A fully parsed and resolved event ready for scheduling."""

    title: str
    start_datetime: str
    duration_minutes: int
    group_urlname: str
    description: str | None = None
    venue_id: str | None = None
    publish_status: str = "DRAFT"
    event_hosts: list[str] = field(default_factory=list)
    featured_photo_id: str | None = None
    rsvp_settings: dict[str, Any] | None = None
    question: str | None = None
    how_to_find_us: str | None = None
    self_rsvp: bool | None = None
    is_online: bool | None = None
    event_url: str | None = None
    series: str | None = None

    # Original raw data for reference
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedEventFile:
    """A fully parsed event file with all events resolved."""

    events: list[ParsedEvent]
    options: dict[str, Any] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None


class EventParser:
    """Parse and validate event JSON files.

    Handles:
    - Loading JSON event files
    - Validating against schema
    - Parsing duration strings to minutes
    - Applying defaults (file-level, then config-level)
    - Resolving venue aliases to venue IDs
    """

    # Duration pattern: captures hours and/or minutes
    DURATION_PATTERN = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?$")

    class Error(Exception):
        """Exception raised for parsing errors."""

        pass

    def __init__(self, config: ConfigManager | None = None) -> None:
        """Initialize the event parser.

        Args:
            config: Configuration manager for resolving venue aliases
                   and config-level defaults. If None, venue aliases
                   won't be resolved and config defaults won't be applied.
        """
        self._config = config
        self._validator = SchemaValidator()

    def parse_file(self, file_path: Path) -> ParsedEventFile:
        """Parse an event JSON file.

        Args:
            file_path: Path to the JSON event file.

        Returns:
            ParsedEventFile containing all parsed events.

        Raises:
            Error: If file cannot be read, parsed, or validated.
        """
        # Load JSON
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except OSError as e:
            raise self.Error(f"Cannot read file {file_path}: {e}") from e
        except json.JSONDecodeError as e:
            raise self.Error(f"Invalid JSON in {file_path}: {e}") from e

        return self.parse_data(data, source_path=file_path)

    def parse_data(
        self, data: dict[str, Any], *, source_path: Path | None = None
    ) -> ParsedEventFile:
        """Parse event data from a dictionary.

        Args:
            data: The event data dictionary.
            source_path: Optional source file path for error messages.

        Returns:
            ParsedEventFile containing all parsed events.

        Raises:
            Error: If data is invalid.
        """
        # Validate against schema
        errors = self._validator.validate(data, SchemaValidator.EVENTS_SCHEMA)
        if errors:
            error_msgs = [str(e) for e in errors]
            raise self.Error(
                "Validation errors:\n  " + "\n  ".join(error_msgs)
            )

        # Extract file-level options and defaults
        options = data.get("options", {})
        file_defaults = data.get("defaults", {})

        # Parse each event
        events: list[ParsedEvent] = []
        raw_events = data.get("events", [])

        for i, raw_event in enumerate(raw_events):
            try:
                parsed = self._parse_event(raw_event, file_defaults)
                events.append(parsed)
            except self.Error as e:
                raise self.Error(f"Event {i}: {e}") from e

        return ParsedEventFile(
            events=events,
            options=options,
            defaults=file_defaults,
            source_path=source_path,
        )

    def _parse_event(
        self, event: dict[str, Any], file_defaults: dict[str, Any]
    ) -> ParsedEvent:
        """Parse a single event with defaults applied.

        Args:
            event: Raw event dictionary.
            file_defaults: File-level defaults to apply.

        Returns:
            Parsed event with all values resolved.

        Raises:
            Error: If event is invalid or missing required fields.
        """
        # Apply defaults (file defaults, then config defaults)
        merged = self.apply_defaults(event, file_defaults)

        # Required fields
        title = merged.get("title")
        start_datetime = merged.get("startDateTime")

        if not title:
            raise self.Error("Missing required field: title")
        if not start_datetime:
            raise self.Error("Missing required field: startDateTime")

        # Parse duration (default 2 hours)
        duration_raw = merged.get("duration")
        duration_minutes = (
            self.parse_duration(duration_raw) if duration_raw is not None else 120
        )

        # Resolve venue
        venue_raw = merged.get("venue")
        venue_id = self.resolve_venue(venue_raw) if venue_raw else None

        # Get group urlname
        group_urlname = merged.get("groupUrlname")
        if not group_urlname:
            raise self.Error("Missing required field: groupUrlname (not in event or defaults)")

        return ParsedEvent(
            title=title,
            start_datetime=start_datetime,
            duration_minutes=duration_minutes,
            group_urlname=group_urlname,
            description=merged.get("description"),
            venue_id=venue_id,
            publish_status=merged.get("publishStatus", "DRAFT"),
            event_hosts=merged.get("eventHosts", []),
            featured_photo_id=merged.get("featuredPhotoId"),
            rsvp_settings=merged.get("rsvpSettings"),
            question=merged.get("question"),
            how_to_find_us=merged.get("howToFindUs"),
            self_rsvp=merged.get("selfRsvp"),
            is_online=merged.get("isOnline"),
            event_url=merged.get("eventUrl"),
            series=merged.get("series"),
            raw=event,
        )

    def parse_duration(self, value: str | int) -> int:
        """Parse a duration value to minutes.

        Args:
            value: Duration as integer (minutes) or string ("2h", "2h30m", "90m").

        Returns:
            Duration in minutes.

        Raises:
            Error: If duration format is invalid.
        """
        if isinstance(value, int):
            if value < 1:
                raise self.Error(f"Duration must be positive: {value}")
            return value

        if not isinstance(value, str):
            raise self.Error(f"Invalid duration type: {type(value)}")

        if not value:
            raise self.Error("Duration cannot be empty")

        match = self.DURATION_PATTERN.match(value)
        if not match:
            raise self.Error(f"Invalid duration format: {value}")

        hours_str, minutes_str = match.groups()
        hours = int(hours_str) if hours_str else 0
        minutes = int(minutes_str) if minutes_str else 0

        total = hours * 60 + minutes
        if total < 1:
            raise self.Error(f"Duration must be positive: {value}")

        return total

    def resolve_venue(self, alias_or_id: str) -> str:
        """Resolve a venue alias to a venue ID.

        Args:
            alias_or_id: Venue alias or direct venue ID.

        Returns:
            The venue ID (either resolved from alias or passed through).
        """
        if not self._config:
            # No config, assume it's already a venue ID
            return alias_or_id

        # Check if it's an alias in the config
        venue_aliases = self._config.get("venueAliases", default={})
        if alias_or_id in venue_aliases:
            alias_data = venue_aliases[alias_or_id]
            if isinstance(alias_data, dict) and "venueId" in alias_data:
                return alias_data["venueId"]

        # Not an alias, return as-is (assumed to be venue ID)
        return alias_or_id

    def apply_defaults(
        self, event: dict[str, Any], file_defaults: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply defaults to an event.

        Priority order (highest to lowest):
        1. Event-level values
        2. File-level defaults
        3. Config-level defaults (from group or global config)

        Args:
            event: The event dictionary.
            file_defaults: File-level defaults.

        Returns:
            Merged dictionary with all defaults applied.
        """
        # Start with config defaults (lowest priority)
        result: dict[str, Any] = {}

        if self._config:
            # Get config-level defaults
            config_defaults = self._config.get("defaults", default={})
            if isinstance(config_defaults, dict):
                result.update(config_defaults)

        # Apply file-level defaults (medium priority)
        result.update(file_defaults)

        # Apply event values (highest priority)
        result.update(event)

        return result

    def validate_file(self, file_path: Path) -> list[ValidationError]:
        """Validate an event file without fully parsing it.

        This is a lighter-weight validation that only checks schema compliance.

        Args:
            file_path: Path to the JSON event file.

        Returns:
            List of validation errors (empty if valid).

        Raises:
            Error: If file cannot be read.
        """
        return self._validator.validate_file(file_path, SchemaValidator.EVENTS_SCHEMA)
