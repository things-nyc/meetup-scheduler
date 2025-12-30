# meetup-scheduler

Batch-create Meetup.com events from JSON specifications.

## Features

- Create multiple Meetup events from a single JSON file
- JSON Schema validation for event definitions
- Recurrence pattern support (e.g., "first Thursday of each month")
- Venue aliases for quick reference
- Draft mode for review before publishing
- Markdown summary generation

## Installation

```bash
uv tool install meetup-scheduler
```

Or install from source:

```bash
git clone https://github.com/terrillmoore/meetup-scheduler.git
cd meetup-scheduler
uv tool install -e .
```

If you prefer not to install globally, you can run commands from the source
directory using `uv run meetup-scheduler` instead.

## Quick Start

```bash
# Create and initialize a new project directory
mkdir ~/my-meetup-project
cd ~/my-meetup-project
meetup-scheduler init .

# Or initialize in one step from anywhere
meetup-scheduler init ~/my-meetup-project

# Configure your Meetup OAuth credentials
meetup-scheduler config oauth.client_id "YOUR_CLIENT_ID"
meetup-scheduler config oauth.client_secret "YOUR_CLIENT_SECRET"

# Sync groups and venues from Meetup
meetup-scheduler sync

# Create events from a JSON file (dry-run first)
meetup-scheduler schedule events.json --dry-run

# Create events as drafts
meetup-scheduler schedule events.json
```

## Commands

| Command | Description |
| ------- | ----------- |
| `init [PATH]` | Initialize project directory with skeleton files |
| `config` | Get or set configuration values |
| `sync` | Fetch group/venue data from Meetup API |
| `schedule` | Create events from JSON file |
| `generate` | Generate event JSON from recurrence pattern |

## Global Options

| Option | Description |
| ------ | ----------- |
| `-v, --verbose` | Increase verbosity (can repeat: -vv) |
| `-q, --quiet` | Suppress non-error output |
| `--debug` | Enable debug mode (show stack traces) |
| `--config PATH` | Override config file location |
| `--dry-run` | Show what would happen without making changes |

Boolean options can be explicitly negated with `--no-` prefix (e.g., `--no-debug`,
`--no-dry-run`). This is useful for overriding defaults or config file settings.

## Configuration

Configuration is stored in platform-specific locations:

- Linux: `~/.config/meetup-scheduler/`
- macOS: `~/Library/Application Support/meetup-scheduler/`
- Windows: `%APPDATA%\meetup-scheduler\`

Project-specific settings go in `meetup-scheduler-local.json` in your
project directory.

## License

MIT License. See [LICENSE.md](LICENSE.md) for details.

## Meta

### Contributors

- [Terry Moore](https://github.com/terrillmoore)

### Support

This project is maintained by [The Things Network New York](https://thethings.nyc).

If you find this helpful, please support The Things Network New York by
joining, participating, or donating.
