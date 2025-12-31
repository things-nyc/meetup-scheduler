##############################################################################
#
# Name: test_markdown_generator.py
#
# Function:
#       Unit tests for MarkdownGenerator class
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

from pathlib import Path

import pytest

from meetup_scheduler.output.markdown import MarkdownGenerator
from meetup_scheduler.scheduler.parser import ParsedEvent, ParsedEventFile


@pytest.fixture
def sample_event() -> ParsedEvent:
    """Create a sample parsed event."""
    return ParsedEvent(
        title="Test Meeting",
        start_datetime="2025-02-01T19:00:00-05:00",
        duration_minutes=120,
        group_urlname="test-group",
        publish_status="DRAFT",
    )


@pytest.fixture
def sample_events() -> list[ParsedEvent]:
    """Create a list of sample events across multiple months."""
    return [
        ParsedEvent(
            title="January Meeting",
            start_datetime="2025-01-09T19:00:00-05:00",
            duration_minutes=120,
            group_urlname="test-group",
            publish_status="DRAFT",
        ),
        ParsedEvent(
            title="February Meeting",
            start_datetime="2025-02-06T19:00:00-05:00",
            duration_minutes=90,
            group_urlname="test-group",
            publish_status="PUBLISHED",
        ),
        ParsedEvent(
            title="March Meeting",
            start_datetime="2025-03-06T19:00:00-05:00",
            duration_minutes=120,
            group_urlname="test-group",
            publish_status="DRAFT",
        ),
    ]


class TestGenerateTable:
    """Test table generation."""

    def test_empty_events_list(self) -> None:
        """Test output for empty events list."""
        generator = MarkdownGenerator()
        output = generator.generate_table([])
        assert "No events to display" in output

    def test_single_event(self, sample_event: ParsedEvent) -> None:
        """Test table with single event."""
        generator = MarkdownGenerator()
        output = generator.generate_table([sample_event])

        assert "# Events" in output
        assert "| # |" in output  # Header with index
        assert "Test Meeting" in output
        assert "2025-02-01" in output
        assert "19:00" in output
        assert "120m" in output
        assert "DRAFT" in output

    def test_multiple_events(self, sample_events: list[ParsedEvent]) -> None:
        """Test table with multiple events."""
        generator = MarkdownGenerator()
        output = generator.generate_table(sample_events)

        assert "January Meeting" in output
        assert "February Meeting" in output
        assert "March Meeting" in output
        assert "3 event(s)" in output

    def test_dry_run_mode(self, sample_event: ParsedEvent) -> None:
        """Test dry run indicator in output."""
        generator = MarkdownGenerator()
        output = generator.generate_table([sample_event], dry_run=True)
        assert "(Dry Run)" in output

    def test_custom_title(self, sample_event: ParsedEvent) -> None:
        """Test custom title."""
        generator = MarkdownGenerator()
        output = generator.generate_table([sample_event], title="Custom Title")
        assert "# Custom Title" in output

    def test_no_index_column(self, sample_event: ParsedEvent) -> None:
        """Test table without index column."""
        generator = MarkdownGenerator()
        output = generator.generate_table([sample_event], show_index=False)
        # Header should not have # column
        assert "| # |" not in output
        assert "| Date |" in output

    def test_escapes_pipe_characters(self) -> None:
        """Test that pipe characters in titles are escaped."""
        event = ParsedEvent(
            title="Event | With | Pipes",
            start_datetime="2025-02-01T19:00:00-05:00",
            duration_minutes=120,
            group_urlname="test-group",
        )
        generator = MarkdownGenerator()
        output = generator.generate_table([event])
        assert "Event \\| With \\| Pipes" in output


class TestGenerateMonthly:
    """Test monthly grouped generation."""

    def test_empty_events_list(self) -> None:
        """Test output for empty events list."""
        generator = MarkdownGenerator()
        output = generator.generate_monthly([])
        assert "No events to display" in output

    def test_groups_by_month(self, sample_events: list[ParsedEvent]) -> None:
        """Test that events are grouped by month."""
        generator = MarkdownGenerator()
        output = generator.generate_monthly(sample_events)

        assert "## January 2025" in output
        assert "## February 2025" in output
        assert "## March 2025" in output

    def test_shows_summary(self, sample_events: list[ParsedEvent]) -> None:
        """Test that summary shows counts."""
        generator = MarkdownGenerator()
        output = generator.generate_monthly(sample_events)

        assert "3 event(s)" in output
        assert "3 month(s)" in output

    def test_dry_run_mode(self, sample_event: ParsedEvent) -> None:
        """Test dry run indicator."""
        generator = MarkdownGenerator()
        output = generator.generate_monthly([sample_event], dry_run=True)
        assert "(Dry Run)" in output


class TestGenerateFromFile:
    """Test generation from ParsedEventFile."""

    def test_includes_source_path(
        self, sample_event: ParsedEvent, tmp_path: Path
    ) -> None:
        """Test that source path is included in output."""
        parsed = ParsedEventFile(
            events=[sample_event],
            source_path=tmp_path / "events.json",
        )
        generator = MarkdownGenerator()
        output = generator.generate_from_file(parsed)

        assert "**Source:**" in output
        assert "events.json" in output

    def test_table_mode(self, sample_event: ParsedEvent) -> None:
        """Test table output mode."""
        parsed = ParsedEventFile(events=[sample_event])
        generator = MarkdownGenerator()
        output = generator.generate_from_file(parsed, grouped=False)

        assert "| # |" in output
        assert "## " not in output  # No month headers

    def test_grouped_mode(self, sample_events: list[ParsedEvent]) -> None:
        """Test grouped output mode."""
        parsed = ParsedEventFile(events=sample_events)
        generator = MarkdownGenerator()
        output = generator.generate_from_file(parsed, grouped=True)

        assert "## January 2025" in output
        assert "## February 2025" in output

    def test_dry_run_flag(self, sample_event: ParsedEvent) -> None:
        """Test dry run flag is passed through."""
        parsed = ParsedEventFile(events=[sample_event])
        generator = MarkdownGenerator()
        output = generator.generate_from_file(parsed, dry_run=True)
        assert "(Dry Run)" in output


class TestMonthFormatting:
    """Test month key extraction and formatting."""

    def test_get_month_key(self) -> None:
        """Test month key extraction."""
        generator = MarkdownGenerator()
        assert generator._get_month_key("2025-02-01T19:00:00-05:00") == "2025-02"
        assert generator._get_month_key("2025-12-31") == "2025-12"

    def test_format_month_name(self) -> None:
        """Test month name formatting."""
        generator = MarkdownGenerator()
        assert generator._format_month_name("2025-01") == "January 2025"
        assert generator._format_month_name("2025-12") == "December 2025"

    def test_format_invalid_month(self) -> None:
        """Test handling of invalid month key."""
        generator = MarkdownGenerator()
        # Invalid key should be returned as-is
        assert generator._format_month_name("invalid") == "invalid"
