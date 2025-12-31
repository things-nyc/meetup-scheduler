<!-- markdownlint-disable MD013 -->
<!-- MD013: allow long lines; issue descriptions benefit from single-line readability -->

# Future Issues

Tracking enhancements and improvements for future development.

## Issue Queue

### 1. Better error message for missing default group URL

**Command**: `meetup-scheduler schedule`

**Problem**: When no default group URL is set, the error message doesn't explain
how to fix it.

**Solution**: Error should explain both options:

- Add `groupUrlName` to the `defaults` section of the JSON file
- Use `meetup-scheduler config groupUrlName <value>` to set it globally

---

### 2. Add config instructions to schedule command help

**Command**: `meetup-scheduler schedule`

**Problem**: For consistency, help/docs should mention using
`meetup-scheduler config` to globally set the default `groupUrlName`.

---

### 3. Improve config --list output format

**Command**: `meetup-scheduler config --list`

**Problem**: Currently dumps raw JSON, which isn't user-friendly.

**Solution**:

- Default: Display settings in the format used to enter them
  (e.g., `groupUrlName = TTN-NYC`)
- Add `--json` or `--raw` flag to get current JSON dump behavior

---

### 4. Enhanced config display options

**Command**: `meetup-scheduler config`

**Problem**: No way to see all possible settings or where values come from.

**Solution**: Add options for:

- Display all possible config keys with descriptions
- Display current values with source identification (default, global, project)

---

### 5. Compact date list output for schedule command

**Command**: `meetup-scheduler schedule`

**Problem**: Sometimes you just want a brief comma-separated list of dates.

**Solution**: Add option to generate one-line output with smart formatting:

- Only show year on first date, or when year changes
- Omit times if all times are the same
- Omit duration if all durations are the same

Example: `Jan 2, Feb 6, Mar 6, Apr 3, 2026 Jan 8`

---

### 6. Human-friendly time formatting

**Commands**: `meetup-scheduler schedule`, `meetup-scheduler generate`

**Problem**: Times display in ISO8601 format with `T` separator, which is
machine-friendly but awkward for humans.

**Solution**: Use friendlier format:

- Format: `Weekday YYYY-MM-DD, starttime to finishtime`
- Use locale preference for 12h/24h clock
- If all timezones are the same, omit timezone
- If timezones differ, append standard abbreviation (EST, EDT, PST, CST, etc.)

Example: `Thursday 2025-02-06, 7:00 PM to 9:00 PM EST`

---

## Completed

(Move issues here when done)
