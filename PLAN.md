# meetup-scheduler: Detailed Implementation Plan

## Executive Summary

A Python CLI tool for batch-creating Meetup.com events from JSON specifications, with JSON Schema validation, recurrence pattern templates, and markdown summary generation.

---

## 1. Project Structure

```
meetup-scheduler/
├── pyproject.toml                    # uv/pip packaging, entry points
├── uv.lock                           # Locked dependencies
├── Makefile                          # Build automation
├── README.md
├── LICENSE
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # pytest fixtures, API mocks
│   ├── test_app.py
│   ├── test_config.py
│   ├── test_meetup_client.py
│   ├── test_scheduler.py
│   ├── test_schema_validator.py
│   ├── test_recurrence.py
│   └── fixtures/                     # Sample JSON files for testing
│       ├── sample_events.json
│       ├── sample_config.json
│       └── mock_api_responses/
└── src/
    └── meetup_scheduler/
        ├── __init__.py
        ├── __main__.py               # Single main() function → App.run()
        ├── __version__.py
        ├── app.py                    # Main App class (command dispatcher)
        ├── commands/                 # Command classes
        │   ├── __init__.py
        │   ├── base.py               # BaseCommand abstract class
        │   ├── init_cmd.py           # InitCommand class
        │   ├── config_cmd.py         # ConfigCommand class
        │   ├── sync_cmd.py           # SyncCommand class
        │   ├── schedule_cmd.py       # ScheduleCommand class
        │   └── generate_cmd.py       # GenerateCommand class (templates)
        ├── config/
        │   ├── __init__.py
        │   ├── manager.py            # ConfigManager class
        │   ├── user_settings.py      # UserSettings class
        │   └── project_settings.py   # ProjectSettings class
        ├── meetup/
        │   ├── __init__.py
        │   ├── client.py             # MeetupClient class (GraphQL)
        │   ├── auth.py               # AuthManager class (OAuth2)
        │   └── types.py              # Event, Venue, Group dataclasses
        ├── scheduler/
        │   ├── __init__.py
        │   ├── parser.py             # EventParser class
        │   ├── validator.py          # SchemaValidator class
        │   └── recurrence.py         # RecurrenceGenerator class
        ├── output/
        │   ├── __init__.py
        │   ├── markdown.py           # MarkdownGenerator class
        │   └── console.py            # ConsoleOutput class
        └── resources/                # Bundled as package data
            ├── schemas/
            │   ├── events.schema.json
            │   ├── config.schema.json
            │   └── venues.schema.json
            └── templates/
                ├── event_template.json
                └── config_template.json
```

---

## 2. Class Architecture

### 2.1 Entry Point (`__main__.py`)

```python
import sys
from meetup_scheduler.app import App

def main() -> int:
    """Single entry point - creates App and runs it."""
    try:
        app = App()
        return app.run()
    except KeyboardInterrupt:
        return 130

if __name__ == "__main__":
    sys.exit(main())
```

### 2.2 Core Classes

| Class | Responsibility |
|-------|---------------|
| `App` | Parse CLI args, dispatch to command classes, manage logging |
| `ConfigManager` | Load/save user and project settings, manage paths via `platformdirs` |
| `UserSettings` | User-level config (API credentials, defaults, organizer info) |
| `ProjectSettings` | Project directory config (groups, venues, schema overrides) |
| `MeetupClient` | GraphQL API calls (createEvent, editEvent, getGroup, getVenues) |
| `AuthManager` | OAuth2 flow, token storage, refresh logic |
| `SchemaValidator` | JSON Schema validation using `jsonschema` library |
| `EventParser` | Parse event JSON, resolve defaults, normalize durations |
| `RecurrenceGenerator` | Generate dates from patterns ("first Thursday", etc.) |
| `MarkdownGenerator` | Create markdown summaries of scheduled events |

### 2.3 Command Classes

Each command inherits from `BaseCommand`:

```python
class BaseCommand(ABC):
    def __init__(self, app: "App", args: argparse.Namespace):
        self._app = app
        self._args = args

    @abstractmethod
    def execute(self) -> int:
        """Execute the command, return exit code."""
        pass
```

| Command | Description |
|---------|-------------|
| `InitCommand` | Set up project directory, create skeleton files |
| `ConfigCommand` | Get/set configuration values (git-like interface) |
| `SyncCommand` | Fetch groups/venues from Meetup, generate VS Code schemas |
| `ScheduleCommand` | Read JSON, validate, create/update events or dry-run |
| `GenerateCommand` | Generate event JSON from recurrence patterns |

---

## 3. Data Storage Strategy

### 3.1 User-Level Settings (via `platformdirs`)

Location: `platformdirs.user_config_dir("meetup-scheduler", "meetup-scheduler")`
- Linux: `~/.config/meetup-scheduler/`
- macOS: `~/Library/Application Support/meetup-scheduler/`
- Windows: `%APPDATA%\meetup-scheduler\meetup-scheduler\`

**Files:**
```
~/.config/meetup-scheduler/
├── config.json           # User settings (organizer name, defaults)
├── credentials.json      # OAuth tokens (600 permissions on Unix)
└── cache/
    └── groups/           # Cached group/venue data
```

### 3.2 Project-Level Settings (working directory)

Created by `meetup-scheduler init`:
```
./
├── .meetup-scheduler/
│   ├── project.json      # Project-specific overrides
│   └── cache/            # API response cache
├── .vscode/
│   └── settings.json     # JSON Schema associations (generated by sync)
└── events/               # User's event definition files
    └── 2025-q1.json
```

### 3.3 Security for OAuth Tokens

1. Store tokens in `credentials.json` with restricted permissions (0600 on Unix)
2. Support `MEETUP_ACCESS_TOKEN` environment variable override
3. Support reading token from file path via `MEETUP_TOKEN_FILE` env var
4. Never log or display token values
5. Offer `meetup-scheduler config --show-sensitive` for debugging (masked by default)

---

## 4. JSON Schemas

### 4.1 Event Definition Schema (`events.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://meetup-scheduler/events.schema.json",
  "type": "object",
  "required": ["events"],
  "properties": {
    "$schema": { "type": "string" },
    "defaults": {
      "type": "object",
      "properties": {
        "groupUrlname": { "type": "string" },
        "venueId": { "type": "string" },
        "duration": { "$ref": "#/$defs/duration" },
        "publishStatus": { "enum": ["DRAFT", "PUBLISHED"], "default": "DRAFT" },
        "rsvpSettings": { "$ref": "#/$defs/rsvpSettings" }
      }
    },
    "events": {
      "type": "array",
      "items": { "$ref": "#/$defs/event" }
    }
  },
  "$defs": {
    "duration": {
      "oneOf": [
        { "type": "integer", "minimum": 1, "description": "Duration in minutes" },
        { "type": "string", "pattern": "^(\\d+h)?(\\d+m)?$", "description": "e.g., '2h', '2h30m', '90m'" }
      ]
    },
    "event": {
      "type": "object",
      "required": ["title", "startDateTime"],
      "properties": {
        "title": { "type": "string", "minLength": 1 },
        "description": { "type": "string" },
        "startDateTime": { "type": "string", "format": "date-time" },
        "duration": { "$ref": "#/$defs/duration" },
        "groupUrlname": { "type": "string" },
        "venueId": { "type": "string" },
        "publishStatus": { "enum": ["DRAFT", "PUBLISHED"] },
        "eventHosts": {
          "type": "array",
          "items": { "type": "string", "description": "Member ID" }
        },
        "featuredPhotoId": { "type": "string" },
        "rsvpSettings": { "$ref": "#/$defs/rsvpSettings" },
        "question": { "type": "string", "description": "RSVP question" },
        "howToFindUs": { "type": "string" },
        "selfRsvp": { "type": "boolean" },
        "isOnline": { "type": "boolean" },
        "eventUrl": { "type": "string", "format": "uri", "description": "For online events" },
        "series": { "type": "string", "description": "Tag for grouping (e.g., 'business', 'hacking')" }
      }
    },
    "rsvpSettings": {
      "type": "object",
      "properties": {
        "rsvpOpenTime": { "type": "string", "format": "date-time" },
        "rsvpCloseTime": { "type": "string", "format": "date-time" },
        "rsvpLimit": { "type": "integer", "minimum": 0 },
        "guestLimit": { "type": "integer", "minimum": 0, "maximum": 5 }
      }
    }
  }
}
```

### 4.2 Config Schema (`config.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "organizer": {
      "type": "object",
      "required": ["name"],
      "properties": {
        "name": { "type": "string" },
        "email": { "type": "string", "format": "email" }
      }
    },
    "groups": {
      "type": "object",
      "additionalProperties": {
        "$ref": "#/$defs/groupConfig"
      }
    },
    "defaultTimezone": { "type": "string", "default": "America/New_York" }
  },
  "$defs": {
    "groupConfig": {
      "type": "object",
      "properties": {
        "urlname": { "type": "string" },
        "defaultVenueId": { "type": "string" },
        "defaultDuration": { "$ref": "#/$defs/duration" },
        "series": {
          "type": "object",
          "additionalProperties": {
            "$ref": "#/$defs/seriesConfig"
          }
        }
      }
    },
    "seriesConfig": {
      "type": "object",
      "properties": {
        "pattern": { "type": "string", "description": "e.g., 'first Thursday'" },
        "defaultDuration": { "$ref": "#/$defs/duration" },
        "defaultVenueId": { "type": "string" },
        "titleTemplate": { "type": "string" },
        "descriptionTemplate": { "type": "string" }
      }
    }
  }
}
```

---

## 5. CLI Interface

```
meetup-scheduler <command> [options]

Commands:
  init              Initialize project directory with skeleton files
  config            Get or set configuration values
  sync              Fetch group/venue data from Meetup API
  schedule          Create events from JSON file
  generate          Generate event JSON from recurrence pattern

Global Options:
  --verbose, -v     Increase verbosity (can repeat: -vv)
  --quiet, -q       Suppress non-error output
  --config PATH     Override config file location
  --dry-run         Show what would happen without making changes

init:
  meetup-scheduler init [--force]

config:
  meetup-scheduler config <key> [value]
  meetup-scheduler config --list
  meetup-scheduler config --edit
  Examples:
    meetup-scheduler config organizer.name "Terry Moore"
    meetup-scheduler config groups.ttn-nyc.urlname "the-things-network-nyc-community-meetup"

sync:
  meetup-scheduler sync [--group URLNAME] [--years N]
  Options:
    --group URLNAME   Sync specific group (default: all configured)
    --years N         Look back N years for venues (default: 2)
    --venues-only     Only fetch venue information

schedule:
  meetup-scheduler schedule <FILE.json> [options]
  Options:
    --dry-run         Validate and show summary, don't create events
    --output FORMAT   Output format: summary, markdown, json (default: summary)
    --update          Update existing events instead of creating new

generate:
  meetup-scheduler generate [options]
  Options:
    --group URLNAME   Group URL name
    --series NAME     Series name (from config)
    --pattern PATTERN Recurrence pattern (e.g., "first Thursday")
    --start DATE      Start date (default: today)
    --end DATE        End date
    --count N         Number of occurrences (default: 12)
    --output FILE     Output file (default: stdout)
```

---

## 6. Recurrence Pattern Syntax

The `RecurrenceGenerator` class will support these patterns:

| Pattern | Description |
|---------|-------------|
| `first Monday` | First Monday of each month |
| `second Tuesday` | Second Tuesday of each month |
| `third Wednesday` | Third Wednesday of each month |
| `fourth Thursday` | Fourth Thursday of each month |
| `last Friday` | Last Friday of each month |
| `first Thursday after first Tuesday` | First Thursday occurring after the first Tuesday |
| `second Saturday` | Second Saturday of each month |

Implementation will use `dateutil.rrule` with custom logic for complex patterns.

---

## 7. Meetup GraphQL API Integration

### 7.1 Key Mutations

```graphql
# Create Event
mutation CreateEvent($input: CreateEventInput!) {
  createEvent(input: $input) {
    event {
      id
      eventUrl
      title
      dateTime
      status
    }
    errors {
      message
      code
      field
    }
  }
}

# Edit Event
mutation EditEvent($input: EditEventInput!) {
  editEvent(input: $input) {
    event { id eventUrl }
    errors { message code field }
  }
}
```

### 7.2 Key Queries

```graphql
# Get Group Info
query GetGroup($urlname: String!) {
  groupByUrlname(urlname: $urlname) {
    id
    name
    urlname
    timezone
    venues(first: 100) {
      edges {
        node {
          id
          name
          address
          city
          state
          country
        }
      }
    }
  }
}

# Get Past Events (for venue discovery)
query GetPastEvents($urlname: String!, $after: String) {
  groupByUrlname(urlname: $urlname) {
    pastEvents(first: 50, after: $after) {
      pageInfo { hasNextPage endCursor }
      edges {
        node {
          id
          title
          venue { id name address city }
        }
      }
    }
  }
}
```

### 7.3 Authentication Flow

1. User creates OAuth consumer at meetup.com (requires Pro subscription)
2. `meetup-scheduler config oauth.client_id <ID>`
3. `meetup-scheduler config oauth.client_secret <SECRET>`
4. `meetup-scheduler sync` triggers browser-based OAuth flow
5. Tokens stored in `credentials.json`
6. Auto-refresh on expiration

---

## 8. Example Workflow

### 8.1 Initial Setup

```bash
# Install the tool
uv pip install meetup-scheduler

# Create a working directory for a scheduling project
mkdir my-meetup-planning && cd my-meetup-planning

# Initialize (creates .meetup-scheduler/, prompts for missing config)
meetup-scheduler init
# Output: "Missing required configuration. Please run:"
#   meetup-scheduler config organizer.name "Your Name"
#   meetup-scheduler config oauth.client_id "YOUR_CLIENT_ID"
#   meetup-scheduler config oauth.client_secret "YOUR_CLIENT_SECRET"

# Configure
meetup-scheduler config organizer.name "Terry Moore"
meetup-scheduler config oauth.client_id "abc123"
meetup-scheduler config oauth.client_secret "secret456"

# Sync groups and venues (triggers OAuth if needed)
meetup-scheduler sync
# Output: "Authenticated as Terry Moore"
#         "Found 3 groups you organize:"
#         "  - the-things-network-nyc-community-meetup"
#         "  - the-things-network-ithaca-community-meetup"
#         "  - finger-lakes-film-photography-group"
#         "Synced 12 venues across all groups"
#         "VS Code schemas written to .vscode/settings.json"
```

### 8.2 Generate Template Events

```bash
# Generate business meeting dates for TTN NYC
meetup-scheduler generate \
  --group the-things-network-nyc-community-meetup \
  --pattern "first Thursday" \
  --start 2025-01-01 \
  --count 12 \
  --output events/ttn-nyc-business-2025.json

# Generate hacking sessions
meetup-scheduler generate \
  --group the-things-network-nyc-community-meetup \
  --pattern "third Thursday" \
  --start 2025-01-01 \
  --count 12 \
  --output events/ttn-nyc-hacking-2025.json
```

### 8.3 Edit and Schedule

```bash
# Edit the generated files in VS Code (with schema validation)
code events/ttn-nyc-business-2025.json

# Dry-run to verify
meetup-scheduler schedule events/ttn-nyc-business-2025.json --dry-run
# Output: "Would create 12 events:"
#         "  2025-01-02 19:00 - TTN NYC Business Meeting"
#         "  2025-02-06 19:00 - TTN NYC Business Meeting"
#         ...

# Generate markdown summary
meetup-scheduler schedule events/ttn-nyc-business-2025.json --dry-run --output markdown > schedule.md

# Create the events as drafts
meetup-scheduler schedule events/ttn-nyc-business-2025.json
# Output: "Created 12 draft events"
#         "  https://www.meetup.com/the-things-network-nyc.../events/123..."
```

---

## 9. Testing Strategy

### 9.1 Test Categories

| Category | Coverage |
|----------|----------|
| Unit Tests | All classes in isolation with mocked dependencies |
| Integration Tests | Command classes with mocked Meetup API |
| Schema Tests | JSON Schema validation edge cases |
| Recurrence Tests | All pattern types, edge cases (leap years, DST) |

### 9.2 Mocking Strategy

```python
# conftest.py
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_meetup_client():
    """Mock MeetupClient for testing without API calls."""
    with patch('meetup_scheduler.meetup.client.MeetupClient') as mock:
        client = MagicMock()
        client.get_group.return_value = {
            'id': 'group123',
            'name': 'Test Group',
            'urlname': 'test-group',
            'timezone': 'America/New_York'
        }
        client.create_event.return_value = {
            'event': {'id': 'event123', 'eventUrl': 'https://meetup.com/...'},
            'errors': []
        }
        mock.return_value = client
        yield client

@pytest.fixture
def sample_events_json():
    """Load sample events fixture."""
    return Path(__file__).parent / 'fixtures' / 'sample_events.json'
```

### 9.3 Test Examples

```python
class TestRecurrenceGenerator:
    def test_first_thursday(self):
        gen = RecurrenceGenerator()
        dates = gen.generate("first Thursday", start=date(2025, 1, 1), count=3)
        assert dates == [date(2025, 1, 2), date(2025, 2, 6), date(2025, 3, 6)]

    def test_first_thursday_after_first_tuesday(self):
        gen = RecurrenceGenerator()
        dates = gen.generate(
            "first Thursday after first Tuesday",
            start=date(2025, 1, 1),
            count=3
        )
        # Jan: 1st Tue = Jan 7, 1st Thu after = Jan 9
        # Feb: 1st Tue = Feb 4, 1st Thu after = Feb 6
        assert dates[0] == date(2025, 1, 9)

class TestEventParser:
    def test_duration_parsing(self):
        parser = EventParser()
        assert parser.parse_duration("2h") == 120
        assert parser.parse_duration("2h30m") == 150
        assert parser.parse_duration("90m") == 90
        assert parser.parse_duration(120) == 120
```

---

## 10. Dependencies

```toml
# pyproject.toml
[project]
name = "meetup-scheduler"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "httpx>=0.27",           # HTTP client for GraphQL
    "jsonschema>=4.20",      # JSON Schema validation
    "python-dateutil>=2.8",  # Date parsing and recurrence
    "platformdirs>=4.0",     # Cross-platform config dirs
    "rich>=13.0",            # Console output formatting
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "pytest-mock>=3.12",
    "respx>=0.21",           # Mock httpx requests
    "ruff>=0.3",             # Linting
    "mypy>=1.8",             # Type checking
]

[project.scripts]
meetup-scheduler = "meetup_scheduler.__main__:main"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "pytest-mock>=3.12",
    "respx>=0.21",
]
```

---

## 11. Implementation Order

### Phase 1: Foundation
1. Project scaffolding (pyproject.toml, src layout, tests/)
2. `App` class with argument parsing
3. `ConfigManager` with `platformdirs` integration
4. JSON Schema files as bundled resources
5. `SchemaValidator` class

### Phase 2: Core Commands
6. `InitCommand` - project initialization
7. `ConfigCommand` - configuration management
8. Unit tests for Phase 1-2

### Phase 3: Meetup Integration
9. `AuthManager` - OAuth2 flow
10. `MeetupClient` - GraphQL operations
11. `SyncCommand` - fetch groups/venues
12. Integration tests with mocked API

### Phase 4: Scheduling
13. `EventParser` - JSON parsing, duration normalization
14. `ScheduleCommand` - create/update events
15. `MarkdownGenerator` - summary output
16. End-to-end tests

### Phase 5: Template Generation
17. `RecurrenceGenerator` - date pattern parsing
18. `GenerateCommand` - template creation
19. Full test coverage

---

## 12. Open Questions for User

1. **OAuth Consumer**: Do you already have a Meetup OAuth consumer created, or do we need to document that setup process in detail?

2. **Venue Aliases**: Would you like support for venue aliases (e.g., "wework" → full venue ID) in the event JSON?

3. **Event Updates**: When running `schedule` on events that already exist, should the tool:
   - Skip them (default)?
   - Update them (require `--update` flag)?
   - Prompt for each?

4. **Notification**: Should the tool have an option to notify you (desktop notification, email template) when events are created?

5. **Series Linking**: Meetup supports event series. Should we attempt to link related events as a series in Meetup?

---

## Sources

- [Meetup API Introduction](https://www.meetup.com/graphql/)
- [Meetup API Guide](https://www.meetup.com/api/guide/)
- [Meetup API Authentication](https://www.meetup.com/api/authentication/)
- [platformdirs on GitHub](https://github.com/tox-dev/platformdirs)
- [annotate_film_scans reference](https://github.com/terrillmoore/annotate_film_scans)
