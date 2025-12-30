##############################################################################
#
# Name: app.py
#
# Function:
#       Main application class for meetup-scheduler CLI
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import argparse
import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from meetup_scheduler.__version__ import __version__


class App:
    """Main application class for meetup-scheduler."""

    class Error(Exception):
        """Exception raised for application errors."""

        pass

    def __init__(self, args: Sequence[str] | None = None) -> None:
        """Initialize the application.

        Args:
            args: Command-line arguments. If None, uses sys.argv[1:].
        """
        self._raw_args = args if args is not None else sys.argv[1:]
        self._args: argparse.Namespace | None = None
        self._logger: logging.Logger | None = None

    @property
    def args(self) -> argparse.Namespace:
        """Return parsed arguments, parsing if needed."""
        if self._args is None:
            self._args = self._parse_arguments()
        return self._args

    @property
    def log(self) -> logging.Logger:
        """Return the application logger."""
        if self._logger is None:
            self._logger = self._setup_logging()
        return self._logger

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all options."""
        parser = argparse.ArgumentParser(
            prog="meetup-scheduler",
            description="Batch-create Meetup.com events from JSON specifications",
        )

        # Version
        parser.add_argument(
            "--version",
            action="version",
            version=f"%(prog)s {__version__}",
        )

        # Global options
        parser.add_argument(
            "-v",
            "--verbose",
            action="count",
            default=0,
            help="Increase verbosity (can repeat: -vv)",
        )
        parser.add_argument(
            "-q",
            "--quiet",
            action="store_true",
            help="Suppress non-error output",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug mode (show stack traces)",
        )
        parser.add_argument(
            "--config",
            metavar="PATH",
            help="Override config file location",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without making changes",
        )

        # Subcommands
        subparsers = parser.add_subparsers(
            dest="command",
            title="commands",
            description="Available commands",
        )

        # init command
        init_parser = subparsers.add_parser(
            "init",
            help="Initialize project directory",
        )
        init_parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing files",
        )

        # config command
        config_parser = subparsers.add_parser(
            "config",
            help="Get or set configuration values",
        )
        config_parser.add_argument(
            "key",
            nargs="?",
            help="Configuration key (e.g., organizer.name)",
        )
        config_parser.add_argument(
            "value",
            nargs="?",
            help="Value to set (omit to get current value)",
        )
        config_parser.add_argument(
            "--list",
            action="store_true",
            help="List all configuration values",
        )
        config_parser.add_argument(
            "--edit",
            action="store_true",
            help="Open configuration in editor",
        )

        # sync command
        sync_parser = subparsers.add_parser(
            "sync",
            help="Fetch group/venue data from Meetup API",
        )
        sync_parser.add_argument(
            "--group",
            metavar="URLNAME",
            help="Sync specific group (default: all configured)",
        )
        sync_parser.add_argument(
            "--years",
            type=int,
            default=2,
            help="Look back N years for venues (default: 2)",
        )
        sync_parser.add_argument(
            "--venues-only",
            action="store_true",
            help="Only fetch venue information",
        )

        # schedule command
        schedule_parser = subparsers.add_parser(
            "schedule",
            help="Create events from JSON file",
        )
        schedule_parser.add_argument(
            "file",
            nargs="?",
            help="JSON file with event definitions",
        )
        schedule_parser.add_argument(
            "--output",
            choices=["summary", "markdown", "json"],
            default="summary",
            help="Output format (default: summary)",
        )
        schedule_parser.add_argument(
            "--on-conflict",
            choices=["error", "skip", "update", "prompt"],
            default="prompt",
            help="Behavior for existing events (default: prompt)",
        )
        schedule_parser.add_argument(
            "--series-mode",
            choices=["link", "independent"],
            default="independent",
            help="Series linking mode (default: independent)",
        )

        # generate command
        generate_parser = subparsers.add_parser(
            "generate",
            help="Generate event JSON from recurrence pattern",
        )
        generate_parser.add_argument(
            "--group",
            metavar="URLNAME",
            help="Group URL name",
        )
        generate_parser.add_argument(
            "--series",
            metavar="NAME",
            help="Series name (from config)",
        )
        generate_parser.add_argument(
            "--pattern",
            metavar="PATTERN",
            help='Recurrence pattern (e.g., "first Thursday")',
        )
        generate_parser.add_argument(
            "--start",
            metavar="DATE",
            help="Start date (default: today)",
        )
        generate_parser.add_argument(
            "--end",
            metavar="DATE",
            help="End date",
        )
        generate_parser.add_argument(
            "--count",
            type=int,
            default=12,
            help="Number of occurrences (default: 12)",
        )
        generate_parser.add_argument(
            "--output",
            metavar="FILE",
            help="Output file (default: stdout)",
        )

        return parser

    def _parse_arguments(self) -> argparse.Namespace:
        """Parse command-line arguments."""
        parser = self._create_parser()
        return parser.parse_args(self._raw_args)

    def _setup_logging(self) -> logging.Logger:
        """Configure and return the application logger."""
        logger = logging.getLogger("meetup_scheduler")

        # Determine log level from args
        if self.args.debug:
            level = logging.DEBUG
        elif self.args.quiet:
            level = logging.ERROR
        elif self.args.verbose >= 2:
            level = logging.DEBUG
        elif self.args.verbose >= 1:
            level = logging.INFO
        else:
            level = logging.WARNING

        logger.setLevel(level)

        # Add console handler if none exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(level)
            formatter = logging.Formatter("%(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def run(self) -> int:
        """Run the application and return exit code."""
        try:
            # Parse arguments (triggers parsing if not done)
            _ = self.args

            # Dispatch to command
            command = self.args.command

            if command is None:
                # No command specified, show help
                self._create_parser().print_help()
                return 0

            # Command stubs for Phase 1
            self.log.info(f"Command '{command}' is not yet implemented")
            return 0

        except self.Error as e:
            self.log.error(str(e))
            return 1
        except Exception as e:
            if self.args.debug:
                raise
            self.log.error(f"Unexpected error: {e}")
            return 1
