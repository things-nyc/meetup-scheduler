##############################################################################
#
# Name: recurrence.py
#
# Function:
#       RecurrenceGenerator class for generating recurring event dates
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

from dateutil.relativedelta import FR, MO, SA, SU, TH, TU, WE, relativedelta

if TYPE_CHECKING:
    from dateutil.relativedelta import weekday


# Map weekday names to dateutil weekday objects
WEEKDAY_MAP: dict[str, weekday] = {
    "monday": MO,
    "tuesday": TU,
    "wednesday": WE,
    "thursday": TH,
    "friday": FR,
    "saturday": SA,
    "sunday": SU,
    # Short forms
    "mon": MO,
    "tue": TU,
    "wed": WE,
    "thu": TH,
    "fri": FR,
    "sat": SA,
    "sun": SU,
}

# Map ordinal words to numbers
ORDINAL_MAP: dict[str, int] = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "last": -1,
    "1st": 1,
    "2nd": 2,
    "3rd": 3,
    "4th": 4,
    "5th": 5,
}


@dataclass
class PatternSpec:
    """Specification for a recurrence pattern."""

    ordinal: int  # 1-5 for first-fifth, -1 for last
    weekday: weekday  # noqa: F811 - shadowing module-level weekday type
    after_ordinal: int | None = None  # For "first X after first Y" patterns
    after_weekday: weekday | None = None  # noqa: F811


class RecurrenceGenerator:
    """Generate recurring dates from pattern strings.

    Supported patterns:
    - "first Thursday" - first Thursday of each month
    - "second Wednesday" - second Wednesday of each month
    - "third Friday" - third Friday of each month
    - "fourth Monday" - fourth Monday of each month
    - "last Friday" - last Friday of each month
    - "first Thursday after first Tuesday" - first Thursday after first Tuesday
    """

    # Pattern for simple recurrence: "first Thursday", "last Friday"
    SIMPLE_PATTERN = re.compile(
        r"^(first|second|third|fourth|fifth|last|1st|2nd|3rd|4th|5th)\s+"
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
        r"mon|tue|wed|thu|fri|sat|sun)$",
        re.IGNORECASE,
    )

    # Pattern for complex recurrence: "first Thursday after first Tuesday"
    COMPLEX_PATTERN = re.compile(
        r"^(first|second|third|fourth|fifth|last|1st|2nd|3rd|4th|5th)\s+"
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
        r"mon|tue|wed|thu|fri|sat|sun)\s+after\s+"
        r"(first|second|third|fourth|fifth|last|1st|2nd|3rd|4th|5th)\s+"
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
        r"mon|tue|wed|thu|fri|sat|sun)$",
        re.IGNORECASE,
    )

    class Error(Exception):
        """Exception raised for recurrence generation errors."""

        pass

    def parse_pattern(self, pattern: str) -> PatternSpec:
        """Parse a pattern string into a PatternSpec.

        Args:
            pattern: Pattern string like "first Thursday" or
                    "first Thursday after first Tuesday".

        Returns:
            PatternSpec with parsed values.

        Raises:
            Error: If pattern format is invalid.
        """
        pattern = pattern.strip()

        # Try complex pattern first (more specific)
        match = self.COMPLEX_PATTERN.match(pattern)
        if match:
            ordinal_str, weekday_str, after_ordinal_str, after_weekday_str = (
                match.groups()
            )
            return PatternSpec(
                ordinal=ORDINAL_MAP[ordinal_str.lower()],
                weekday=WEEKDAY_MAP[weekday_str.lower()],
                after_ordinal=ORDINAL_MAP[after_ordinal_str.lower()],
                after_weekday=WEEKDAY_MAP[after_weekday_str.lower()],
            )

        # Try simple pattern
        match = self.SIMPLE_PATTERN.match(pattern)
        if match:
            ordinal_str, weekday_str = match.groups()
            return PatternSpec(
                ordinal=ORDINAL_MAP[ordinal_str.lower()],
                weekday=WEEKDAY_MAP[weekday_str.lower()],
            )

        raise self.Error(f"Invalid pattern format: {pattern}")

    def generate(
        self,
        pattern: str,
        start: date,
        end: date | None = None,
        count: int | None = None,
    ) -> list[date]:
        """Generate dates matching the pattern.

        Args:
            pattern: Pattern string like "first Thursday".
            start: Start date for generation.
            end: Optional end date (exclusive).
            count: Optional maximum number of dates to generate.

        Returns:
            List of dates matching the pattern.

        Raises:
            Error: If pattern is invalid or no limit specified.
        """
        if end is None and count is None:
            raise self.Error("Must specify either end date or count")

        spec = self.parse_pattern(pattern)
        dates: list[date] = []

        # Start from the first day of the start month
        current_month = date(start.year, start.month, 1)

        while True:
            # Calculate the date for this month
            occurrence = self._get_occurrence_for_month(spec, current_month)

            if occurrence is not None and occurrence >= start:
                if end is not None and occurrence >= end:
                    break
                dates.append(occurrence)
                if count is not None and len(dates) >= count:
                    break

            # Move to next month
            current_month = current_month + relativedelta(months=1)

            # Safety limit to prevent infinite loops
            if current_month.year > start.year + 100:
                break

        return dates

    def _get_occurrence_for_month(self, spec: PatternSpec, month: date) -> date | None:
        """Get the occurrence date for a specific month.

        Args:
            spec: The pattern specification.
            month: First day of the month to check.

        Returns:
            The occurrence date, or None if not valid for this month.
        """
        if spec.after_ordinal is not None and spec.after_weekday is not None:
            # Complex pattern: "first X after first Y"
            return self._get_complex_occurrence(spec, month)
        else:
            # Simple pattern: "first Thursday"
            return self._get_simple_occurrence(spec, month)

    def _get_simple_occurrence(self, spec: PatternSpec, month: date) -> date | None:
        """Get simple pattern occurrence for a month.

        Args:
            spec: Pattern specification.
            month: First day of the month.

        Returns:
            The occurrence date, or None if ordinal doesn't exist.
        """
        # Use relativedelta to find the nth weekday
        if spec.ordinal == -1:
            # Last weekday of month - go to next month and back
            next_month = month + relativedelta(months=1)
            occurrence = next_month + relativedelta(
                days=-1, weekday=spec.weekday(-1)
            )
        else:
            # Nth weekday of month
            occurrence = month + relativedelta(
                weekday=spec.weekday(spec.ordinal)
            )

        # Verify the occurrence is in the correct month
        if occurrence.month != month.month:
            return None

        return occurrence

    def _get_complex_occurrence(self, spec: PatternSpec, month: date) -> date | None:
        """Get complex pattern occurrence for a month.

        For patterns like "first Thursday after first Tuesday".

        Args:
            spec: Pattern specification with after_* fields set.
            month: First day of the month.

        Returns:
            The occurrence date, or None if not valid.
        """
        # First, get the "after" date (e.g., "first Tuesday")
        after_spec = PatternSpec(
            ordinal=spec.after_ordinal,  # type: ignore[arg-type]
            weekday=spec.after_weekday,  # type: ignore[arg-type]
        )
        after_date = self._get_simple_occurrence(after_spec, month)

        if after_date is None:
            return None

        # Now find the Nth target weekday after that date
        # Start from the day after the "after" date
        search_start = after_date + timedelta(days=1)

        # Find the first target weekday on or after search_start
        target_weekday = spec.weekday.weekday  # type: ignore[union-attr]
        days_ahead = target_weekday - search_start.weekday()
        if days_ahead < 0:
            days_ahead += 7

        first_target = search_start + timedelta(days=days_ahead)

        # If we need more than the first occurrence
        if spec.ordinal == -1:
            # "last X after Y" - find last occurrence in month
            occurrence = first_target
            while True:
                next_occurrence = occurrence + timedelta(days=7)
                if next_occurrence.month != month.month:
                    break
                occurrence = next_occurrence
        elif spec.ordinal > 1:
            # Add weeks to get to nth occurrence
            occurrence = first_target + timedelta(weeks=spec.ordinal - 1)
        else:
            occurrence = first_target

        # Verify in same month
        if occurrence.month != month.month:
            return None

        return occurrence

    def next_occurrence(self, pattern: str, after: date) -> date:
        """Get the next occurrence of a pattern after a given date.

        Args:
            pattern: Pattern string.
            after: Date to search after.

        Returns:
            The next occurrence date.

        Raises:
            Error: If pattern is invalid or no occurrence found.
        """
        # Generate a few occurrences starting from the given date
        # and return the first one strictly after the given date
        dates = self.generate(pattern, after, count=2)

        for d in dates:
            if d > after:
                return d

        # Try generating from next month if the after date is late in month
        next_month = date(after.year, after.month, 1) + relativedelta(months=1)
        dates = self.generate(pattern, next_month, count=1)
        if dates:
            return dates[0]

        raise self.Error(f"Could not find next occurrence for pattern: {pattern}")
