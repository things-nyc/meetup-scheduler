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

## OAuth Setup

<!-- meetup-scheduler:oauth-setup:start -->
Before using meetup-scheduler, you need Meetup API credentials:

1. Log in to your Meetup account at <https://www.meetup.com>

2. Go to the OAuth Consumers page: <https://www.meetup.com/api/oauth/list/>

3. Click "Create New Consumer" (note: requires Meetup Pro subscription)

4. Fill in the required fields:
   - **Consumer Name**: A name for your application (e.g., "My Event Scheduler")
   - **Application Website**: `https://github.com/things-nyc/meetup-scheduler`
   - **Redirect URI**: `http://127.0.0.1:8080/callback` (for local development)

5. After creating, you'll receive:
   - **Key** (this is your `client_id`)
   - **Secret** (this is your `client_secret`)

6. Configure meetup-scheduler with your credentials:

   ```bash
   meetup-scheduler config oauth.client_id "YOUR_KEY"
   meetup-scheduler config oauth.client_secret "YOUR_SECRET"
   ```
<!-- meetup-scheduler:oauth-setup:end -->

## Quick Start

<!-- meetup-scheduler:getting-started:start -->
```bash
# Initialize your project directory
meetup-scheduler init .

# Configure your Meetup OAuth credentials (see OAuth Setup above)
meetup-scheduler config oauth.client_id "YOUR_CLIENT_ID"
meetup-scheduler config oauth.client_secret "YOUR_CLIENT_SECRET"

# Sync groups and venues from Meetup
meetup-scheduler sync

# Create events from a JSON file (dry-run first)
meetup-scheduler schedule events.json --dry-run

# Create events as drafts
meetup-scheduler schedule events.json
```
<!-- meetup-scheduler:getting-started:end -->

You can also initialize a new directory in one step from anywhere:

```bash
meetup-scheduler init ~/my-meetup-project
cd ~/my-meetup-project
```

## Commands

| Command | Description |
| ------- | ----------- |
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

MIT License. See [LICENSE.md](LICENSE.md) for details.

## Meta

### Contributors

- [Terry Moore](https://github.com/terrillmoore)

### Support

This project is maintained by [The Things Network New York](https://thethings.nyc).

If you find this helpful, please support The Things Network New York by
joining, participating, or donating.
