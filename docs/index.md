---
layout: default
title: meetup-scheduler
---

<!-- markdownlint-disable MD013 MD025 MD033 -->
<!-- MD013: allow long lines; URLs and tables exceed 80 chars -->
<!-- MD025: allow multiple H1; Cayman theme adds title as H1, content has another -->
<!-- MD033: allow inline HTML; navigation links use HTML for centering -->

<p align="center">
  <a href="https://github.com/things-nyc/meetup-scheduler/releases/latest">Latest Release</a> •
  <a href="https://github.com/things-nyc/meetup-scheduler/issues/new">Report Issue</a> •
  <a href="https://github.com/things-nyc/meetup-scheduler">GitHub Repository</a>
</p>

---

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
git clone https://github.com/things-nyc/meetup-scheduler.git
cd meetup-scheduler
uv tool install -e .
```

If you prefer not to install globally, you can run commands from the source
directory using `uv run meetup-scheduler` instead.

## Authentication

Before using meetup-scheduler, you need to authenticate with your Meetup account:

```bash
meetup-scheduler login
```

This opens your browser to log in to Meetup and grant access. Your credentials
are stored securely and refreshed automatically.

To remove stored credentials:

```bash
meetup-scheduler logout
```

## Quick Start

```bash
# Initialize your project directory
meetup-scheduler init .

# Log in to your Meetup account
meetup-scheduler login

# Sync groups and venues from Meetup
meetup-scheduler sync

# Create events from a JSON file (dry-run first)
meetup-scheduler schedule events.json --dry-run

# Create events as drafts
meetup-scheduler schedule events.json
```

You can also initialize a new directory in one step from anywhere:

```bash
meetup-scheduler init ~/my-meetup-project
cd ~/my-meetup-project
```

## Commands

| Command | Description |
| ------- | ----------- |
| `login` | Authenticate with Meetup (opens browser) |
| `logout` | Remove stored Meetup credentials |
| `init [PATH]` | Initialize project directory with skeleton files |
| `config` | Get or set configuration values |
| `sync` | Fetch group/venue data from Meetup API |
| `schedule` | Create events from JSON file |
| `generate` | Generate event JSON from recurrence pattern |
| `readme` | Display this README (use `--raw` for markdown source) |

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

MIT License. See [LICENSE.md](https://github.com/things-nyc/meetup-scheduler/blob/main/LICENSE.md) for details.

## Meta

### Contributors

- [Terry Moore](https://github.com/terrillmoore)

### Support

This project is maintained by [The Things Network New York](https://thethings.nyc).

If you find this helpful, please support The Things Network New York by
joining, participating, or donating.
