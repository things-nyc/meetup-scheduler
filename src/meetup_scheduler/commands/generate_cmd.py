##############################################################################
#
# Name: generate_cmd.py
#
# Function:
#       GenerateCommand class for generating event JSON from recurrence patterns
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
from datetime import date, datetime, time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from meetup_scheduler.commands.base import BaseCommand
from meetup_scheduler.scheduler.recurrence import RecurrenceGenerator

if TYPE_CHECKING:
    import argparse

    from meetup_scheduler.app import App


class GenerateCommand(BaseCommand):
    """Generate event JSON from a recurrence pattern.

    Uses RecurrenceGenerator to create dates based on patterns like
    "first Thursday" or "first Thursday after first Tuesday",
    then outputs JSON suitable for the schedule command.
    """

    def __init__(self, app: App, args: argparse.Namespace) -> None:
        """Initialize the command."""
        super().__init__(app, args)
        self._recurrence = RecurrenceGenerator()

    def execute(self) -> int:
        """Execute the generate command.

        Returns:
            0 on success.

        Raises:
            CommandError: If generation fails.
        """
        # Get command arguments
        pattern = getattr(self.args, "pattern", None)
        group_urlname = getattr(self.args, "group", None)
        series_name = getattr(self.args, "series", None)
        start_str = getattr(self.args, "start", None)
        end_str = getattr(self.args, "end", None)
        count = getattr(self.args, "count", 12)
        output_file = getattr(self.args, "output", None)
        duration_str = getattr(self.args, "duration", None)
        time_str = getattr(self.args, "time", None)

        # Validate required arguments
        if not pattern:
            raise self.Error(
                "Pattern is required. "
                'Usage: meetup-scheduler generate --pattern "first Thursday"'
            )

        # Parse start date
        if start_str:
            try:
                start = self._parse_date(start_str)
            except ValueError as e:
                raise self.Error(f"Invalid start date: {e}") from e
        else:
            start = date.today()

        # Parse end date if provided
        end: date | None = None
        if end_str:
            try:
                end = self._parse_date(end_str)
            except ValueError as e:
                raise self.Error(f"Invalid end date: {e}") from e

        # Get defaults from config or series
        defaults = self._get_defaults(group_urlname, series_name, duration_str, time_str)

        # Generate dates
        try:
            if end:
                dates = self._recurrence.generate(pattern, start, end=end)
            else:
                dates = self._recurrence.generate(pattern, start, count=count)
        except RecurrenceGenerator.Error as e:
            raise self.Error(str(e)) from e

        if not dates:
            self.app.log.warning("No dates generated for the given pattern and range")
            return 0

        # Generate event JSON
        output = self._generate_output(dates, defaults)

        # Write output
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(
                json.dumps(output, indent=2) + "\n", encoding="utf-8"
            )
            self.app.log.info(f"Generated {len(dates)} events to {output_path}")
        else:
            print(json.dumps(output, indent=2))

        return 0

    def _parse_duration(self, duration_str: str) -> int:
        """Parse a duration string into minutes.

        Supports formats:
        - Integer (minutes): "120"
        - Hours: "2h"
        - Minutes: "90m"
        - Combined: "1h30m", "2h15m"

        Args:
            duration_str: Duration string to parse.

        Returns:
            Duration in minutes.

        Raises:
            ValueError: If duration format is invalid.
        """
        duration_str = duration_str.strip().lower()

        # Try integer first
        try:
            return int(duration_str)
        except ValueError:
            pass

        # Try pattern matching for h/m format
        pattern = r"^(?:(\d+)h)?(?:(\d+)m)?$"
        match = re.match(pattern, duration_str)
        if match and (match.group(1) or match.group(2)):
            hours = int(match.group(1)) if match.group(1) else 0
            minutes = int(match.group(2)) if match.group(2) else 0
            return hours * 60 + minutes

        raise ValueError(
            f"Invalid duration format: {duration_str}. "
            "Use integer minutes, or formats like '2h', '90m', '1h30m'."
        )

    def _parse_date(self, date_str: str) -> date:
        """Parse a date string.

        Supports formats:
        - YYYY-MM-DD (ISO format)
        - today
        - tomorrow

        Args:
            date_str: Date string to parse.

        Returns:
            Parsed date.

        Raises:
            ValueError: If date format is invalid.
        """
        date_str = date_str.strip().lower()

        if date_str == "today":
            return date.today()
        if date_str == "tomorrow":
            return date.today().replace(day=date.today().day + 1)

        # Try ISO format
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

        raise ValueError(
            f"Invalid date format: {date_str}. "
            "Use YYYY-MM-DD, 'today', or 'tomorrow'."
        )

    def _get_defaults(
        self,
        group_urlname: str | None,
        series_name: str | None,
        duration_str: str | None,
        time_str: str | None,
    ) -> dict[str, Any]:
        """Get defaults from config or series configuration.

        Args:
            group_urlname: Group URL name (overrides config).
            series_name: Series name to look up in config.
            duration_str: Duration string from command line (overrides config).
            time_str: Time string from command line (overrides config).

        Returns:
            Dictionary of default values.
        """
        defaults: dict[str, Any] = {}

        # Try to get config defaults
        if self.app.config_manager:
            config_defaults = self.app.config_manager.get("defaults", default={})
            if isinstance(config_defaults, dict):
                defaults.update(config_defaults)

            # If series specified, get series config
            if series_name:
                series_config = self.app.config_manager.get(
                    f"series.{series_name}", default={}
                )
                if isinstance(series_config, dict):
                    defaults.update(series_config)

        # Command line group overrides config
        if group_urlname:
            defaults["groupUrlname"] = group_urlname

        # Command line duration overrides config
        if duration_str:
            try:
                defaults["duration"] = self._parse_duration(duration_str)
            except ValueError as e:
                raise self.Error(str(e)) from e

        # Command line time overrides config
        if time_str:
            defaults["defaultTime"] = time_str

        return defaults

    def _generate_output(
        self, dates: list[date], defaults: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate the output JSON structure.

        Args:
            dates: List of dates for events.
            defaults: Default values to include.

        Returns:
            Event file structure.
        """
        # Get default time from config or use 19:00
        default_time_str = defaults.pop("defaultTime", "19:00:00")
        try:
            default_time = time.fromisoformat(default_time_str)
        except ValueError:
            default_time = time(19, 0, 0)

        # Get title template
        title_template = defaults.pop("titleTemplate", "Event on {date}")

        # Build events list
        events: list[dict[str, Any]] = []
        for event_date in dates:
            event_datetime = datetime.combine(event_date, default_time)
            # Format as ISO with timezone placeholder (local)
            datetime_str = event_datetime.strftime("%Y-%m-%dT%H:%M:%S")

            # Format title
            title = title_template.format(
                date=event_date.strftime("%B %d, %Y"),
                month=event_date.strftime("%B"),
                year=event_date.strftime("%Y"),
                day=event_date.strftime("%d"),
                weekday=event_date.strftime("%A"),
            )

            event: dict[str, Any] = {
                "title": title,
                "startDateTime": datetime_str,
            }
            events.append(event)

        # Build output structure
        output: dict[str, Any] = {}

        # Add defaults section if we have any
        if defaults:
            output["defaults"] = defaults

        output["events"] = events

        return output
