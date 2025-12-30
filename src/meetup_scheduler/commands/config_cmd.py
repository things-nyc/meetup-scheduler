##############################################################################
#
# Name: config_cmd.py
#
# Function:
#       ConfigCommand class for configuration management
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING

from meetup_scheduler.commands.base import BaseCommand

if TYPE_CHECKING:
    import argparse

    from meetup_scheduler.app import App


class ConfigCommand(BaseCommand):
    """Get or set configuration values.

    Usage:
        config <key>              Get a configuration value
        config <key> <value>      Set a configuration value
        config --list             List all configuration values
        config --edit             Open configuration in editor
    """

    def __init__(self, app: App, args: argparse.Namespace) -> None:
        """Initialize the command."""
        super().__init__(app, args)

    def execute(self) -> int:
        """Execute the config command.

        Returns:
            0 on success.

        Raises:
            CommandError: If the operation fails.
        """
        # Determine which mode we're in
        if getattr(self.args, "list", False):
            return self._list_config()
        elif getattr(self.args, "edit", False):
            return self._edit_config()
        elif getattr(self.args, "key", None):
            key = self.args.key
            value = getattr(self.args, "value", None)
            if value is not None:
                return self._set_value(key, value)
            else:
                return self._get_value(key)
        else:
            # No arguments - show help
            self._print_usage()
            return 0

    def _get_value(self, key: str) -> int:
        """Get and display a configuration value.

        Args:
            key: Dot-separated configuration key.

        Returns:
            0 on success.
        """
        config_manager = self.app.config_manager
        value = config_manager.get(key)

        if value is None:
            self.app.log.warning(f"Key '{key}' is not set")
            return 0

        # Format output based on type
        if isinstance(value, dict):
            print(json.dumps(value, indent=2))
        else:
            print(value)

        return 0

    def _set_value(self, key: str, value: str) -> int:
        """Set a configuration value.

        Args:
            key: Dot-separated configuration key.
            value: Value to set (as string, will be parsed).

        Returns:
            0 on success.
        """
        config_manager = self.app.config_manager

        # Try to parse value as JSON, fall back to string
        parsed_value = self._parse_value(value)

        # By default, set in user config (use --local for project config)
        # Note: --local option would need to be added to argument parser
        config_manager.set(key, parsed_value, user_level=True)

        self.app.log.info(f"Set {key} = {parsed_value!r}")
        return 0

    def _parse_value(self, value: str) -> str | int | float | bool | list | dict:
        """Parse a string value into an appropriate type.

        Attempts to parse as JSON first, then falls back to string.

        Args:
            value: String value to parse.

        Returns:
            Parsed value.
        """
        # Try parsing as JSON for complex types
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # Not valid JSON, return as string
            return value

    def _list_config(self) -> int:
        """List all configuration values.

        Returns:
            0 on success.
        """
        config_manager = self.app.config_manager

        # Get merged config (project overrides user)
        merged = config_manager.get_merged()

        if not merged:
            print("No configuration values set")
            return 0

        # Output as formatted JSON
        print(json.dumps(merged, indent=2))
        return 0

    def _edit_config(self) -> int:
        """Open configuration file in editor.

        Returns:
            0 on success.

        Raises:
            CommandError: If no editor is available.
        """
        config_manager = self.app.config_manager

        # Ensure user config directory exists
        config_manager.ensure_user_config_dir()

        # Create config file if it doesn't exist
        config_path = config_manager.user_config_path
        if not config_path.exists():
            config_manager.save_user_config({})

        # Get editor from environment
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")

        if not editor:
            # Try common defaults
            if sys.platform == "win32":
                editor = "notepad"
            else:
                # Try common Unix editors
                for candidate in ["nano", "vi", "vim"]:
                    try:
                        subprocess.run(
                            ["which", candidate],
                            capture_output=True,
                            check=True,
                        )
                        editor = candidate
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue

        if not editor:
            raise self.Error(
                "No editor found. Set VISUAL or EDITOR environment variable."
            )

        self.app.log.info(f"Opening {config_path} in {editor}")

        try:
            subprocess.run([editor, str(config_path)], check=True)
        except subprocess.CalledProcessError as e:
            raise self.Error(f"Editor exited with error: {e.returncode}") from e
        except FileNotFoundError:
            raise self.Error(f"Editor not found: {editor}") from None

        # Invalidate cache so next read picks up changes
        config_manager._user_config = None

        return 0

    def _print_usage(self) -> None:
        """Print usage information."""
        print(
            """Usage: meetup-scheduler config [OPTIONS] [KEY] [VALUE]

Get or set configuration values.

Examples:
  meetup-scheduler config organizer.name           # Get a value
  meetup-scheduler config organizer.name "Terry"   # Set a value
  meetup-scheduler config --list                   # List all values
  meetup-scheduler config --edit                   # Open in editor

Keys use dot notation for nested values (e.g., groups.ttn-nyc.urlname)."""
        )
