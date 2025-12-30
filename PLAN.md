<!-- markdownlint-disable MD013 -->

# meetup-scheduler: Detailed Implementation Plan

## Executive Summary

A Python CLI tool for batch-creating Meetup.com events from JSON specifications, with JSON Schema validation, recurrence pattern templates, and markdown summary generation.

---

## 1. Project Structure

```text
meetup-scheduler/
├── pyproject.toml                    # uv/pip packaging, entry points
├── uv.lock                           # Locked dependencies
├── Makefile                          # Build automation (GNU Make)
├── README.md                         # User-oriented documentation
├── LICENSE.md                        # MIT License (markdown format)
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
| ----- | -------------- |
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
| ------- | ----------- |
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

```text
~/.config/meetup-scheduler/
├── config.json           # User settings (organizer name, defaults)
├── credentials.json      # OAuth tokens (600 permissions on Unix)
└── cache/
    └── groups/           # Cached group/venue data
```

### 3.2 Project-Level Settings (working directory)

Created by `meetup-scheduler init`:

```text
./
├── .meetup-scheduler/
│   ├── project.json      # Project-specific overrides
│   └── cache/            # API response cache
├── .vscode/
│   └── settings.json     # JSON Schema associations (generated by sync)
└── events/               # User's event definition files
    └── 2025-q1.json
```

### 3.3 Venue Aliases

Organizers can define shorthand aliases for venues in their configuration. The alias
is whatever makes sense to the organizer (e.g., "wework", "fatcat", "online").

**User-level venue aliases** (`~/.config/meetup-scheduler/config.json`):

```json
{
  "venueAliases": {
    "wework-37th": {
      "venueId": "abc123",
      "description": "WeWork 500 7th Ave (37th St)"
    },
    "fatcat": {
      "venueId": "def456",
      "description": "Fat Cat Fab Lab"
    }
  }
}
```

**Project-level venue aliases** (`.meetup-scheduler/project.json`):

```json
{
  "venueAliases": {
    "clubhouse": {
      "venueId": "xyz789",
      "description": "Ithaca Generator Clubhouse"
    }
  }
}
```

**Resolution order**: Project aliases override user aliases. In event JSON files,
use the alias directly in the `venue` field:

```json
{
  "events": [
    {
      "title": "TTN NYC Business Meeting",
      "venue": "wework-37th",
      "startDateTime": "2025-01-02T19:00:00-05:00"
    }
  ]
}
```

The `sync` command auto-generates alias suggestions from discovered venues.

### 3.4 Security for OAuth Tokens

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
    "options": {
      "type": "object",
      "description": "File-level scheduling options (highest priority; overrides CLI flags)",
      "properties": {
        "onConflict": {
          "enum": ["error", "skip", "update", "prompt"],
          "default": "prompt",
          "description": "Behavior when event already exists at same time/group"
        },
        "seriesMode": {
          "enum": ["link", "independent"],
          "default": "independent",
          "description": "Whether to link related events as a Meetup series"
        }
      }
    },
    "defaults": {
      "type": "object",
      "properties": {
        "groupUrlname": { "type": "string" },
        "venue": { "type": "string", "description": "Venue ID or alias" },
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
        "venue": { "type": "string", "description": "Venue ID or alias" },
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

```text
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
    --dry-run             Validate and show summary, don't create events
    --output FORMAT       Output format: summary, markdown, json (default: summary)
    --on-conflict MODE    Behavior for existing events: error, skip, update, prompt
                          (default: prompt; overridden by JSON file "options.onConflict")
    --series-mode MODE    Series linking: link, independent
                          (default: independent; overridden by JSON file "options.seriesMode")

  Priority order: JSON file options > CLI flags > defaults

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
| ------- | ----------- |
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

### 7.3 Authentication Setup

Meetup requires OAuth2 authentication for API access. This section documents the
complete setup process.

**Important**: All credential and configuration files are stored in the **task
directory** (the working directory where you run the tool) or in the user-level
config directory. The tool never writes to its own installation/source directory.

#### Prerequisites

- A Meetup Pro subscription (required to create OAuth consumers)
- Organizer role on at least one Meetup group

#### Step 1: Create an OAuth Consumer

1. Log in to Meetup.com with your organizer account
2. Navigate to your OAuth consumers page (via API settings)
3. Click "Create OAuth Consumer"
4. Fill in the required fields:
   - **Consumer Name**: `meetup-scheduler` (or your preferred name)
   - **Application Website**: Your website or repository URL
   - **Redirect URI**: `http://localhost:8400/callback` (for local OAuth flow)
   - **Description**: Brief description of your scheduling tool
5. Save and note your **Client ID** and **Client Secret**

#### Step 2: Configure meetup-scheduler

```bash
meetup-scheduler config oauth.client_id "YOUR_CLIENT_ID"
meetup-scheduler config oauth.client_secret "YOUR_CLIENT_SECRET"
```

Configuration is stored in the user-level config directory (see Section 3.1).

#### Step 3: Authorize (First Run)

When you first run a command that requires API access (e.g., `sync`), the tool will:

1. Start a temporary local HTTP server on port 8400
2. Open your default browser to Meetup's authorization page
3. After you authorize, Meetup redirects to `localhost:8400/callback`
4. The tool captures the authorization code and exchanges it for tokens
5. Tokens are stored in `credentials.json` in the **user-level config directory**

#### Token Management

- **Access tokens** expire after 1 hour
- **Refresh tokens** are used automatically to obtain new access tokens
- Refresh tokens are single-use; each refresh provides a new refresh token
- If refresh fails, the tool prompts for re-authorization

#### Alternative: Environment Variables

For CI/CD or automated environments:

```bash
export MEETUP_ACCESS_TOKEN="your_access_token"
# Or point to a file containing the token:
export MEETUP_TOKEN_FILE="/path/to/token.txt"
```

#### Security Best Practices

1. Never commit credentials to version control
2. When `init` creates a task directory, it adds credential patterns to `.gitignore`
3. On Unix systems, `credentials.json` is created with mode 0600
4. Use environment variables in shared/CI environments
5. Rotate credentials periodically via Meetup's OAuth management page

#### File Location Summary

| File | Location | Purpose |
| ---- | -------- | ------- |
| `config.json` | User config dir | OAuth client ID, organizer info |
| `credentials.json` | User config dir | OAuth tokens (access, refresh) |
| `.gitignore` | Task directory | Updated by `init` to exclude secrets |

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
| -------- | -------- |
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

## 10. Project Metadata and Dependencies

### 10.1 Repository

- **Hosting**: GitHub
- **License**: MIT (see LICENSE.md)
- **License format**: Markdown format per [IQAndreas/markdown-licenses](https://github.com/IQAndreas/markdown-licenses)

### 10.2 README.md

The README is oriented toward the end user (Meetup organizers), not implementation
details. It should convey the motivation:

> Setting up dozens of recurring Meetup events manually is error-prone, slow, and
> tedious. This tool automates batch creation of Meetup events from JSON
> specifications, with support for recurrence patterns, venue aliases, and
> draft review before publishing.

Key sections for README:

- **Features**: What the tool does (batch scheduling, recurrence, drafts, etc.)
- **Installation**: How to install via uv/pip
- **Quick Start**: Basic usage example
- **Configuration**: How to set up OAuth and organizer settings
- **Usage**: Command reference (init, config, sync, schedule, generate)
- **License**: MIT

### 10.3 pyproject.toml

```toml
[project]
name = "meetup-scheduler"
version = "0.1.0"
description = "Batch-create Meetup.com events from JSON specifications"
readme = "README.md"
license = { file = "LICENSE.md" }
requires-python = ">=3.10"
authors = [
    { name = "Terry Moore", email = "terry@thethings.nyc" }
]
dependencies = [
    "httpx>=0.27, ==0.*",             # HTTP client for GraphQL
    "jsonschema>=4.20, ==4.*",        # JSON Schema validation
    "python-dateutil>=2.8, ==2.*",    # Date parsing and recurrence
    "platformdirs>=4.0, ==4.*",       # Cross-platform config dirs
    "rich>=13.0, ==13.*",             # Console output formatting
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0, ==8.*",
    "pytest-cov>=4.0, ==4.*",
    "pytest-mock>=3.12, ==3.*",
    "respx>=0.21, ==0.21.*",          # Mock httpx requests (pre-1.0)
    "ruff>=0.8, ==0.8.*",             # Linting (pre-1.0)
    "mypy>=1.8, ==1.*",               # Type checking
]

[project.scripts]
meetup-scheduler = "meetup_scheduler.__main__:main"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0, ==8.*",
    "pytest-cov>=4.0, ==4.*",
    "pytest-mock>=3.12, ==3.*",
    "respx>=0.21, ==0.21.*",
]
```

---

## 11. Implementation Order

<!-- markdownlint-save -->
<!-- markdownlint-disable MD029 -->

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

<!-- markdownlint-restore -->

---

## 12. Design Decisions (Resolved)

The following decisions have been made and are reflected throughout this plan:

### 12.1 OAuth Setup

OAuth consumer setup documentation is included in Section 7.3. The tool uses the
OAuth2 Server Flow with a local callback server for the authorization step.

### 12.2 Venue Aliases

Venue aliases are supported (Section 3.3). Organizers define shorthand names that
make sense to them (e.g., "wework", "fatcat"). The `sync` command auto-generates
alias suggestions from discovered venues.

### 12.3 Conflict Handling

When scheduling events that conflict with existing events, behavior is controlled
by the `onConflict` option with four modes:

- `error`: Fail immediately on conflict
- `skip`: Skip conflicting events silently
- `update`: Update the existing event
- `prompt`: Ask the user for each conflict (default)

This can be set in the JSON file (`options.onConflict`) or via CLI (`--on-conflict`).
Priority: JSON file > CLI flag > default.

### 12.4 Series Linking

Meetup series linking is controlled by the `seriesMode` option:

- `independent`: Events are created as standalone (default)
- `link`: Events with the same `series` tag are linked as a Meetup series

This can be set in the JSON file (`options.seriesMode`) or via CLI (`--series-mode`).
Priority: JSON file > CLI flag > default.

### 12.5 File Location Constraints

**Critical design constraint**: The tool never writes files to its own installation
or source directory. All outputs go to:

- **User config directory**: User-level settings, OAuth credentials, cached data
- **Task directory**: Project-specific files, `.gitignore` updates, VS Code schemas

This ensures the tool works correctly whether installed via pip/uv or run from a
local checkout.

---

## Sources

- [Meetup API Introduction](https://www.meetup.com/graphql/)
- [Meetup API Guide](https://www.meetup.com/api/guide/)
- [Meetup API Authentication](https://www.meetup.com/api/authentication/)
- [platformdirs on GitHub](https://github.com/tox-dev/platformdirs)
- [annotate_film_scans reference](https://github.com/terrillmoore/annotate_film_scans)
