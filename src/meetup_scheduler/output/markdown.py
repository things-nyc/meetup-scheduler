##############################################################################
#
# Name: markdown.py
#
# Function:
#       MarkdownGenerator class for generating markdown output from events
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from io import StringIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meetup_scheduler.scheduler.parser import ParsedEvent, ParsedEventFile


class MarkdownGenerator:
    """Generate markdown output from parsed events.

    Supports multiple output formats:
    - Simple table listing all events
    - Monthly grouped calendar view
    - Summary statistics
    """

    def __init__(self) -> None:
        """Initialize the markdown generator."""
        pass

    def generate_table(
        self,
        events: list[ParsedEvent],
        *,
        title: str = "Events",
        show_index: bool = True,
        dry_run: bool = False,
    ) -> str:
        """Generate a markdown table of events.

        Args:
            events: List of parsed events.
            title: Title for the table.
            show_index: Whether to show event index.
            dry_run: Whether this is a dry run preview.

        Returns:
            Markdown table string.
        """
        output = StringIO()

        # Title
        mode = " (Dry Run)" if dry_run else ""
        output.write(f"# {title}{mode}\n\n")

        if not events:
            output.write("*No events to display.*\n")
            return output.getvalue()

        # Table header
        if show_index:
            output.write("| # | Date | Time | Title | Group | Duration | Status |\n")
            output.write("|---|------|------|-------|-------|----------|--------|\n")
        else:
            output.write("| Date | Time | Title | Group | Duration | Status |\n")
            output.write("|------|------|-------|-------|----------|--------|\n")

        # Table rows
        for i, event in enumerate(events, 1):
            row = self._format_event_row(event, index=i if show_index else None)
            output.write(row + "\n")

        # Summary
        output.write(f"\n**Total:** {len(events)} event(s)\n")

        return output.getvalue()

    def generate_monthly(
        self,
        events: list[ParsedEvent],
        *,
        title: str = "Events by Month",
        dry_run: bool = False,
    ) -> str:
        """Generate events grouped by month.

        Args:
            events: List of parsed events.
            title: Title for the output.
            dry_run: Whether this is a dry run preview.

        Returns:
            Markdown string with monthly sections.
        """
        output = StringIO()

        # Title
        mode = " (Dry Run)" if dry_run else ""
        output.write(f"# {title}{mode}\n\n")

        if not events:
            output.write("*No events to display.*\n")
            return output.getvalue()

        # Group by month
        by_month: dict[str, list[tuple[int, ParsedEvent]]] = defaultdict(list)
        for i, event in enumerate(events, 1):
            month_key = self._get_month_key(event.start_datetime)
            by_month[month_key].append((i, event))

        # Sort months chronologically
        sorted_months = sorted(by_month.keys())

        # Generate each month section
        for month_key in sorted_months:
            month_events = by_month[month_key]
            month_name = self._format_month_name(month_key)

            output.write(f"## {month_name}\n\n")
            output.write("| # | Date | Time | Title | Duration | Status |\n")
            output.write("|---|------|------|-------|----------|--------|\n")

            for idx, event in month_events:
                row = self._format_event_row(event, index=idx, include_group=False)
                output.write(row + "\n")

            output.write("\n")

        # Summary
        output.write(f"**Total:** {len(events)} event(s) across {len(sorted_months)} month(s)\n")

        return output.getvalue()

    def generate_from_file(
        self,
        parsed: ParsedEventFile,
        *,
        grouped: bool = False,
        dry_run: bool = False,
    ) -> str:
        """Generate markdown from a parsed event file.

        Args:
            parsed: Parsed event file.
            grouped: Whether to group by month.
            dry_run: Whether this is a dry run.

        Returns:
            Markdown output string.
        """
        output = StringIO()

        # Source info
        if parsed.source_path:
            output.write(f"**Source:** `{parsed.source_path}`\n\n")

        # Generate content
        if grouped:
            content = self.generate_monthly(
                parsed.events, title="Scheduled Events", dry_run=dry_run
            )
        else:
            content = self.generate_table(
                parsed.events, title="Scheduled Events", dry_run=dry_run
            )

        output.write(content)
        return output.getvalue()

    def _format_event_row(
        self,
        event: ParsedEvent,
        *,
        index: int | None = None,
        include_group: bool = True,
    ) -> str:
        """Format a single event as a markdown table row.

        Args:
            event: The event to format.
            index: Optional index number.
            include_group: Whether to include group column.

        Returns:
            Markdown table row string.
        """
        # Parse datetime for display
        dt_str = event.start_datetime
        date_part = dt_str[:10] if len(dt_str) >= 10 else dt_str
        time_part = dt_str[11:16] if len(dt_str) >= 16 else ""

        # Escape pipe characters in title
        title = event.title.replace("|", "\\|")

        # Build row
        parts = []
        if index is not None:
            parts.append(str(index))
        parts.append(date_part)
        parts.append(time_part)
        parts.append(title)
        if include_group:
            parts.append(event.group_urlname)
        parts.append(f"{event.duration_minutes}m")
        parts.append(event.publish_status)

        return "| " + " | ".join(parts) + " |"

    def _get_month_key(self, datetime_str: str) -> str:
        """Extract month key from datetime string.

        Args:
            datetime_str: ISO format datetime string.

        Returns:
            Month key in YYYY-MM format.
        """
        # Just take the first 7 characters (YYYY-MM)
        if len(datetime_str) >= 7:
            return datetime_str[:7]
        return datetime_str

    def _format_month_name(self, month_key: str) -> str:
        """Format month key as human-readable name.

        Args:
            month_key: Month key in YYYY-MM format.

        Returns:
            Formatted month name like "February 2025".
        """
        try:
            dt = datetime.strptime(month_key, "%Y-%m")
            return dt.strftime("%B %Y")
        except ValueError:
            return month_key
