##############################################################################
#
# Name: schedule_cmd.py
#
# Function:
#       ScheduleCommand class for creating Meetup events from JSON files
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
from typing import TYPE_CHECKING

from meetup_scheduler.commands.base import BaseCommand
from meetup_scheduler.output.markdown import MarkdownGenerator
from meetup_scheduler.scheduler.parser import EventParser, ParsedEvent, ParsedEventFile

if TYPE_CHECKING:
    import argparse

    from meetup_scheduler.app import App


class ScheduleCommand(BaseCommand):
    """Create Meetup events from a JSON event file.

    Parses the event file, validates against schema, applies defaults,
    and creates events via the Meetup API (or shows a dry-run preview).
    """

    def __init__(self, app: App, args: argparse.Namespace) -> None:
        """Initialize the command."""
        super().__init__(app, args)
        self._parser = EventParser(config=app.config_manager)

    def execute(self) -> int:
        """Execute the schedule command.

        Returns:
            0 on success.

        Raises:
            CommandError: If scheduling fails.
        """
        # Get command arguments
        file_arg = getattr(self.args, "file", None)
        output_format = getattr(self.args, "output", "summary") or "summary"
        on_conflict = getattr(self.args, "on_conflict", "prompt") or "prompt"
        dry_run = getattr(self.args, "dry_run", False) or False

        if not file_arg:
            raise self.Error(
                "No event file specified. Usage: meetup-scheduler schedule <file.json>"
            )

        file_path = Path(file_arg)
        if not file_path.exists():
            raise self.Error(f"File not found: {file_path}")

        # Parse the event file
        try:
            parsed = self._parser.parse_file(file_path)
        except EventParser.Error as e:
            raise self.Error(str(e)) from e

        if not parsed.events:
            self.app.log.warning("No events found in file")
            return 0

        # Apply file-level options
        file_options = parsed.options
        if "onConflict" in file_options:
            on_conflict = file_options["onConflict"]

        # Output based on format
        if output_format == "json":
            self._output_json(parsed, dry_run=dry_run)
        elif output_format == "markdown":
            self._output_markdown(parsed, dry_run=dry_run)
        else:
            self._output_summary(parsed, dry_run=dry_run, on_conflict=on_conflict)

        # In dry-run mode, we're done
        if dry_run:
            return 0

        # TODO: Implement actual event creation via MeetupClient
        # For now, we just show what would be created
        self.app.log.info("Event creation not yet implemented. Use --dry-run to preview.")
        return 0

    def _output_summary(
        self,
        parsed: ParsedEventFile,
        *,
        dry_run: bool,
        on_conflict: str,
    ) -> None:
        """Output events in summary format.

        Args:
            parsed: Parsed event file.
            dry_run: Whether this is a dry run.
            on_conflict: Conflict resolution strategy.
        """
        mode = "DRY RUN - " if dry_run else ""
        print(f"\n{mode}Schedule Summary")
        print("=" * 60)

        if parsed.source_path:
            print(f"Source: {parsed.source_path}")
        print(f"Events: {len(parsed.events)}")
        print(f"On conflict: {on_conflict}")
        print()

        for i, event in enumerate(parsed.events, 1):
            self._print_event_summary(i, event)

        print("=" * 60)
        if dry_run:
            print(f"Would create {len(parsed.events)} event(s)")
        else:
            print(f"Ready to create {len(parsed.events)} event(s)")

    def _print_event_summary(self, index: int, event: ParsedEvent) -> None:
        """Print a single event summary.

        Args:
            index: Event index (1-based).
            event: The parsed event.
        """
        print(f"[{index}] {event.title}")
        print(f"    Group: {event.group_urlname}")
        print(f"    Date:  {event.start_datetime}")
        print(f"    Duration: {event.duration_minutes} minutes")
        if event.venue_id:
            print(f"    Venue: {event.venue_id}")
        print(f"    Status: {event.publish_status}")
        if event.description:
            # Truncate long descriptions
            desc = event.description[:100]
            if len(event.description) > 100:
                desc += "..."
            print(f"    Description: {desc}")
        print()

    def _output_markdown(self, parsed: ParsedEventFile, *, dry_run: bool) -> None:
        """Output events in markdown table format.

        Args:
            parsed: Parsed event file.
            dry_run: Whether this is a dry run.
        """
        generator = MarkdownGenerator()
        output = generator.generate_from_file(parsed, dry_run=dry_run)
        print(output, end="")

    def _output_json(self, parsed: ParsedEventFile, *, dry_run: bool) -> None:
        """Output events in JSON format.

        Args:
            parsed: Parsed event file.
            dry_run: Whether this is a dry run.
        """
        output = {
            "mode": "dry_run" if dry_run else "schedule",
            "source": str(parsed.source_path) if parsed.source_path else None,
            "count": len(parsed.events),
            "events": [self._event_to_dict(e) for e in parsed.events],
        }
        print(json.dumps(output, indent=2))

    def _event_to_dict(self, event: ParsedEvent) -> dict:
        """Convert a ParsedEvent to a dictionary for JSON output.

        Args:
            event: The parsed event.

        Returns:
            Dictionary representation.
        """
        result = {
            "title": event.title,
            "startDateTime": event.start_datetime,
            "durationMinutes": event.duration_minutes,
            "groupUrlname": event.group_urlname,
            "publishStatus": event.publish_status,
        }

        if event.description:
            result["description"] = event.description
        if event.venue_id:
            result["venueId"] = event.venue_id
        if event.event_hosts:
            result["eventHosts"] = event.event_hosts
        if event.is_online is not None:
            result["isOnline"] = event.is_online
        if event.event_url:
            result["eventUrl"] = event.event_url

        return result
