##############################################################################
#
# Name: test_recurrence.py
#
# Function:
#       Unit tests for RecurrenceGenerator class
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

from datetime import date

import pytest
from dateutil.relativedelta import FR, MO, TH, TU, WE

from meetup_scheduler.scheduler.recurrence import PatternSpec, RecurrenceGenerator


class TestParsePattern:
    """Test pattern string parsing."""

    def test_first_thursday(self) -> None:
        """Test parsing 'first Thursday'."""
        generator = RecurrenceGenerator()
        spec = generator.parse_pattern("first Thursday")

        assert spec.ordinal == 1
        assert spec.weekday == TH
        assert spec.after_ordinal is None
        assert spec.after_weekday is None

    def test_second_wednesday(self) -> None:
        """Test parsing 'second Wednesday'."""
        generator = RecurrenceGenerator()
        spec = generator.parse_pattern("second Wednesday")

        assert spec.ordinal == 2
        assert spec.weekday == WE

    def test_third_monday(self) -> None:
        """Test parsing 'third Monday'."""
        generator = RecurrenceGenerator()
        spec = generator.parse_pattern("third Monday")

        assert spec.ordinal == 3
        assert spec.weekday == MO

    def test_fourth_friday(self) -> None:
        """Test parsing 'fourth Friday'."""
        generator = RecurrenceGenerator()
        spec = generator.parse_pattern("fourth Friday")

        assert spec.ordinal == 4
        assert spec.weekday == FR

    def test_last_friday(self) -> None:
        """Test parsing 'last Friday'."""
        generator = RecurrenceGenerator()
        spec = generator.parse_pattern("last Friday")

        assert spec.ordinal == -1
        assert spec.weekday == FR

    def test_numeric_ordinals(self) -> None:
        """Test parsing numeric ordinals like '1st', '2nd'."""
        generator = RecurrenceGenerator()

        spec = generator.parse_pattern("1st Thursday")
        assert spec.ordinal == 1

        spec = generator.parse_pattern("2nd Tuesday")
        assert spec.ordinal == 2

        spec = generator.parse_pattern("3rd Wednesday")
        assert spec.ordinal == 3

        spec = generator.parse_pattern("4th Friday")
        assert spec.ordinal == 4

    def test_short_weekday_names(self) -> None:
        """Test parsing short weekday names."""
        generator = RecurrenceGenerator()

        spec = generator.parse_pattern("first Mon")
        assert spec.weekday == MO

        spec = generator.parse_pattern("second Tue")
        assert spec.weekday == TU

        spec = generator.parse_pattern("third Wed")
        assert spec.weekday == WE

        spec = generator.parse_pattern("fourth Thu")
        assert spec.weekday == TH

        spec = generator.parse_pattern("last Fri")
        assert spec.weekday == FR

    def test_case_insensitive(self) -> None:
        """Test pattern parsing is case insensitive."""
        generator = RecurrenceGenerator()

        spec = generator.parse_pattern("FIRST THURSDAY")
        assert spec.ordinal == 1
        assert spec.weekday == TH

        spec = generator.parse_pattern("First thursday")
        assert spec.ordinal == 1
        assert spec.weekday == TH

    def test_complex_pattern_first_after_first(self) -> None:
        """Test parsing 'first Thursday after first Tuesday'."""
        generator = RecurrenceGenerator()
        spec = generator.parse_pattern("first Thursday after first Tuesday")

        assert spec.ordinal == 1
        assert spec.weekday == TH
        assert spec.after_ordinal == 1
        assert spec.after_weekday == TU

    def test_complex_pattern_second_after_first(self) -> None:
        """Test parsing 'second Friday after first Monday'."""
        generator = RecurrenceGenerator()
        spec = generator.parse_pattern("second Friday after first Monday")

        assert spec.ordinal == 2
        assert spec.weekday == FR
        assert spec.after_ordinal == 1
        assert spec.after_weekday == MO

    def test_invalid_pattern_raises_error(self) -> None:
        """Test that invalid patterns raise error."""
        generator = RecurrenceGenerator()

        with pytest.raises(RecurrenceGenerator.Error, match="Invalid pattern"):
            generator.parse_pattern("invalid")

        with pytest.raises(RecurrenceGenerator.Error, match="Invalid pattern"):
            generator.parse_pattern("sixth Thursday")

        with pytest.raises(RecurrenceGenerator.Error, match="Invalid pattern"):
            generator.parse_pattern("first Funday")

    def test_pattern_with_extra_whitespace(self) -> None:
        """Test pattern parsing handles extra whitespace."""
        generator = RecurrenceGenerator()
        spec = generator.parse_pattern("  first  Thursday  ")

        # Should handle leading/trailing but not internal
        # The regex requires single space between words
        # For simplicity, leading/trailing is stripped
        assert spec.ordinal == 1
        assert spec.weekday == TH


class TestGenerateSimplePatterns:
    """Test generating dates for simple patterns."""

    def test_first_thursday_january_2025(self) -> None:
        """Test first Thursday of January 2025."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "first Thursday",
            start=date(2025, 1, 1),
            count=1,
        )

        assert len(dates) == 1
        assert dates[0] == date(2025, 1, 2)  # First Thursday of Jan 2025

    def test_first_thursday_multiple_months(self) -> None:
        """Test first Thursday across multiple months."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "first Thursday",
            start=date(2025, 1, 1),
            count=6,
        )

        assert len(dates) == 6
        assert dates[0] == date(2025, 1, 2)
        assert dates[1] == date(2025, 2, 6)
        assert dates[2] == date(2025, 3, 6)
        assert dates[3] == date(2025, 4, 3)
        assert dates[4] == date(2025, 5, 1)
        assert dates[5] == date(2025, 6, 5)

    def test_second_wednesday(self) -> None:
        """Test second Wednesday of month."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "second Wednesday",
            start=date(2025, 1, 1),
            count=3,
        )

        assert len(dates) == 3
        assert dates[0] == date(2025, 1, 8)  # Second Wed of Jan 2025
        assert dates[1] == date(2025, 2, 12)  # Second Wed of Feb 2025
        assert dates[2] == date(2025, 3, 12)  # Second Wed of Mar 2025

    def test_third_monday(self) -> None:
        """Test third Monday of month."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "third Monday",
            start=date(2025, 1, 1),
            count=3,
        )

        assert len(dates) == 3
        assert dates[0] == date(2025, 1, 20)
        assert dates[1] == date(2025, 2, 17)
        assert dates[2] == date(2025, 3, 17)

    def test_last_friday(self) -> None:
        """Test last Friday of month."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "last Friday",
            start=date(2025, 1, 1),
            count=6,
        )

        assert len(dates) == 6
        assert dates[0] == date(2025, 1, 31)
        assert dates[1] == date(2025, 2, 28)
        assert dates[2] == date(2025, 3, 28)
        assert dates[3] == date(2025, 4, 25)
        assert dates[4] == date(2025, 5, 30)
        assert dates[5] == date(2025, 6, 27)

    def test_fourth_thursday_thanksgiving(self) -> None:
        """Test fourth Thursday (US Thanksgiving pattern)."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "fourth Thursday",
            start=date(2025, 11, 1),
            count=1,
        )

        assert dates[0] == date(2025, 11, 27)  # Thanksgiving 2025


class TestGenerateWithEndDate:
    """Test generating with end date instead of count."""

    def test_generate_with_end_date(self) -> None:
        """Test generating dates up to end date."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "first Thursday",
            start=date(2025, 1, 1),
            end=date(2025, 4, 1),
        )

        assert len(dates) == 3
        assert dates[0] == date(2025, 1, 2)
        assert dates[1] == date(2025, 2, 6)
        assert dates[2] == date(2025, 3, 6)
        # April 3 is not included (end date is exclusive)

    def test_end_date_exclusive(self) -> None:
        """Test that end date is exclusive."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "first Thursday",
            start=date(2025, 1, 1),
            end=date(2025, 1, 2),  # Same as first occurrence
        )

        assert len(dates) == 0

    def test_must_specify_limit(self) -> None:
        """Test that either end or count must be specified."""
        generator = RecurrenceGenerator()

        with pytest.raises(RecurrenceGenerator.Error, match="Must specify"):
            generator.generate("first Thursday", start=date(2025, 1, 1))


class TestGenerateStartInMiddleOfMonth:
    """Test generating when start date is middle of month."""

    def test_start_after_first_occurrence(self) -> None:
        """Test when start is after first occurrence of month."""
        generator = RecurrenceGenerator()
        # First Thursday of Jan 2025 is Jan 2
        # Start on Jan 5 should skip Jan 2
        dates = generator.generate(
            "first Thursday",
            start=date(2025, 1, 5),
            count=2,
        )

        assert len(dates) == 2
        assert dates[0] == date(2025, 2, 6)  # First Feb occurrence
        assert dates[1] == date(2025, 3, 6)

    def test_start_on_occurrence_day(self) -> None:
        """Test when start is on an occurrence day."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "first Thursday",
            start=date(2025, 1, 2),  # This IS first Thursday
            count=2,
        )

        assert len(dates) == 2
        assert dates[0] == date(2025, 1, 2)  # Should include start
        assert dates[1] == date(2025, 2, 6)


class TestComplexPatterns:
    """Test complex 'X after Y' patterns."""

    def test_first_thursday_after_first_tuesday(self) -> None:
        """Test 'first Thursday after first Tuesday' pattern."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "first Thursday after first Tuesday",
            start=date(2025, 1, 1),
            count=6,
        )

        # January 2025: First Tuesday = Jan 7, First Thursday after = Jan 9
        # February 2025: First Tuesday = Feb 4, First Thursday after = Feb 6
        # March 2025: First Tuesday = Mar 4, First Thursday after = Mar 6
        # April 2025: First Tuesday = Apr 1, First Thursday after = Apr 3
        # May 2025: First Tuesday = May 6, First Thursday after = May 8
        # June 2025: First Tuesday = Jun 3, First Thursday after = Jun 5

        assert len(dates) == 6
        assert dates[0] == date(2025, 1, 9)
        assert dates[1] == date(2025, 2, 6)
        assert dates[2] == date(2025, 3, 6)
        assert dates[3] == date(2025, 4, 3)
        assert dates[4] == date(2025, 5, 8)
        assert dates[5] == date(2025, 6, 5)

    def test_first_thursday_after_first_tuesday_edge_case(self) -> None:
        """Test when first Tuesday is late in first week.

        In some months, first Tuesday might be day 7, making
        first Thursday after be in the second week.
        """
        generator = RecurrenceGenerator()
        # September 2025: First day is Monday
        # First Tuesday = Sep 2, First Thursday after = Sep 4
        dates = generator.generate(
            "first Thursday after first Tuesday",
            start=date(2025, 9, 1),
            count=1,
        )

        assert dates[0] == date(2025, 9, 4)

    def test_second_friday_after_first_monday(self) -> None:
        """Test 'second Friday after first Monday'."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "second Friday after first Monday",
            start=date(2025, 1, 1),
            count=3,
        )

        # January: First Monday = Jan 6, First Friday after = Jan 10, Second = Jan 17
        # February: First Monday = Feb 3, First Friday after = Feb 7, Second = Feb 14
        # March: First Monday = Mar 3, First Friday after = Mar 7, Second = Mar 14

        assert len(dates) == 3
        assert dates[0] == date(2025, 1, 17)
        assert dates[1] == date(2025, 2, 14)
        assert dates[2] == date(2025, 3, 14)


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_fifth_occurrence_skips_short_months(self) -> None:
        """Test that months without fifth occurrence are skipped."""
        generator = RecurrenceGenerator()
        # Look for fifth Thursday - not every month has one
        dates = generator.generate(
            "fifth Thursday",
            start=date(2025, 1, 1),
            count=3,
        )

        # January 2025 has 5 Thursdays (2, 9, 16, 23, 30)
        # February 2025 has only 4 Thursdays - skipped
        # March 2025 has 4 Thursdays - skipped
        # April 2025 has 4 Thursdays - skipped
        # May 2025 has 5 Thursdays (1, 8, 15, 22, 29)
        # June 2025 has 4 Thursdays - skipped
        # July 2025 has 5 Thursdays (3, 10, 17, 24, 31)

        assert len(dates) == 3
        assert dates[0] == date(2025, 1, 30)
        assert dates[1] == date(2025, 5, 29)
        assert dates[2] == date(2025, 7, 31)

    def test_leap_year_february(self) -> None:
        """Test February in leap year."""
        generator = RecurrenceGenerator()
        # 2024 is a leap year
        dates = generator.generate(
            "last Friday",
            start=date(2024, 2, 1),
            count=1,
        )

        # February 2024 has 29 days, last Friday is Feb 23
        assert dates[0] == date(2024, 2, 23)

    def test_non_leap_year_february(self) -> None:
        """Test February in non-leap year."""
        generator = RecurrenceGenerator()
        # 2025 is not a leap year
        dates = generator.generate(
            "last Friday",
            start=date(2025, 2, 1),
            count=1,
        )

        # February 2025 has 28 days, last Friday is Feb 28
        assert dates[0] == date(2025, 2, 28)

    def test_last_day_of_month_variations(self) -> None:
        """Test last weekday across months with different lengths."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "last Friday",
            start=date(2025, 1, 1),
            end=date(2025, 5, 1),
        )

        # 31-day month (Jan): Last Friday = Jan 31
        # 28-day month (Feb): Last Friday = Feb 28
        # 31-day month (Mar): Last Friday = Mar 28
        # 30-day month (Apr): Last Friday = Apr 25

        assert len(dates) == 4
        assert dates[0] == date(2025, 1, 31)
        assert dates[1] == date(2025, 2, 28)
        assert dates[2] == date(2025, 3, 28)
        assert dates[3] == date(2025, 4, 25)


class TestNextOccurrence:
    """Test finding next occurrence after a date."""

    def test_next_occurrence_from_start_of_month(self) -> None:
        """Test next occurrence from start of month."""
        generator = RecurrenceGenerator()
        next_date = generator.next_occurrence(
            "first Thursday",
            after=date(2025, 1, 1),
        )

        assert next_date == date(2025, 1, 2)

    def test_next_occurrence_from_middle_of_month(self) -> None:
        """Test next occurrence from middle of month."""
        generator = RecurrenceGenerator()
        next_date = generator.next_occurrence(
            "first Thursday",
            after=date(2025, 1, 5),  # After first Thursday
        )

        assert next_date == date(2025, 2, 6)

    def test_next_occurrence_from_occurrence_day(self) -> None:
        """Test next occurrence when 'after' is an occurrence day."""
        generator = RecurrenceGenerator()
        # January 2, 2025 is the first Thursday
        next_date = generator.next_occurrence(
            "first Thursday",
            after=date(2025, 1, 2),
        )

        # Should return February's first Thursday, not the same day
        assert next_date == date(2025, 2, 6)


class TestPatternSpec:
    """Test PatternSpec dataclass."""

    def test_simple_pattern_spec(self) -> None:
        """Test creating simple pattern spec."""
        spec = PatternSpec(ordinal=1, weekday=TH)

        assert spec.ordinal == 1
        assert spec.weekday == TH
        assert spec.after_ordinal is None
        assert spec.after_weekday is None

    def test_complex_pattern_spec(self) -> None:
        """Test creating complex pattern spec."""
        spec = PatternSpec(
            ordinal=1,
            weekday=TH,
            after_ordinal=1,
            after_weekday=TU,
        )

        assert spec.ordinal == 1
        assert spec.weekday == TH
        assert spec.after_ordinal == 1
        assert spec.after_weekday == TU


class TestComplexPatternEdgeCases:
    """Test edge cases in complex patterns."""

    def test_last_friday_after_first_monday(self) -> None:
        """Test 'last Friday after first Monday' pattern."""
        generator = RecurrenceGenerator()
        dates = generator.generate(
            "last Friday after first Monday",
            start=date(2025, 1, 1),
            count=2,
        )

        # January 2025: First Monday = Jan 6, last Friday in Jan = Jan 31
        # February 2025: First Monday = Feb 3, last Friday in Feb = Feb 28
        assert len(dates) == 2
        assert dates[0] == date(2025, 1, 31)
        assert dates[1] == date(2025, 2, 28)

    def test_next_occurrence_late_in_month(self) -> None:
        """Test next occurrence when querying late in month."""
        generator = RecurrenceGenerator()
        # Query from Jan 30 - should find Feb occurrence
        next_date = generator.next_occurrence(
            "first Thursday",
            after=date(2025, 1, 30),
        )

        assert next_date == date(2025, 2, 6)

    def test_generate_with_both_end_and_count(self) -> None:
        """Test that end date takes precedence when both specified."""
        generator = RecurrenceGenerator()
        # Request 12 events but end date limits to 3
        dates = generator.generate(
            "first Thursday",
            start=date(2025, 1, 1),
            end=date(2025, 4, 1),
            count=12,
        )

        # End date should limit the results
        assert len(dates) == 3
