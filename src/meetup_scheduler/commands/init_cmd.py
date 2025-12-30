##############################################################################
#
# Name: init_cmd.py
#
# Function:
#       InitCommand class for project directory initialization
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
from pathlib import Path
from typing import TYPE_CHECKING

from meetup_scheduler.commands.base import BaseCommand

if TYPE_CHECKING:
    import argparse

    from meetup_scheduler.app import App


class InitCommand(BaseCommand):
    """Initialize a project directory for meetup-scheduler.

    Creates the following structure:
    - .meetup-scheduler/         Project cache directory
    - .meetup-scheduler/cache/   API response cache
    - meetup-scheduler-local.json   Project configuration file
    - events/                    Directory for event JSON files
    - Updates .gitignore with appropriate patterns
    """

    # Files and directories to create
    CACHE_DIR = ".meetup-scheduler"
    CACHE_SUBDIR = "cache"
    EVENTS_DIR = "events"

    # Patterns to add to .gitignore
    GITIGNORE_PATTERNS = [
        "# meetup-scheduler",
        ".meetup-scheduler/",
        "meetup-scheduler-local.json",
    ]

    # Default project config template
    DEFAULT_PROJECT_CONFIG = {
        "$schema": "./node_modules/meetup-scheduler/schemas/config.schema.json",
        "defaults": {
            "publishStatus": "DRAFT",
        },
        "venueAliases": {},
    }

    def __init__(self, app: App, args: argparse.Namespace) -> None:
        """Initialize the command."""
        super().__init__(app, args)
        self._project_dir = Path.cwd()

    def execute(self) -> int:
        """Execute the init command.

        Returns:
            0 on success.

        Raises:
            CommandError: If initialization fails.
        """
        force = getattr(self.args, "force", False) or False

        # Create directories
        self._create_directories()

        # Create project config file
        self._create_project_config(force=force)

        # Update .gitignore
        self._update_gitignore()

        self.app.log.info("Project initialized successfully")
        return 0

    def _create_directories(self) -> None:
        """Create the project directory structure."""
        # Create .meetup-scheduler/cache/
        cache_dir = self._project_dir / self.CACHE_DIR / self.CACHE_SUBDIR
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.app.log.debug(f"Created cache directory: {cache_dir}")

        # Create events/
        events_dir = self._project_dir / self.EVENTS_DIR
        events_dir.mkdir(exist_ok=True)
        self.app.log.debug(f"Created events directory: {events_dir}")

    def _create_project_config(self, *, force: bool = False) -> None:
        """Create the project configuration file.

        Args:
            force: If True, overwrite existing file.
        """
        config_path = self._project_dir / "meetup-scheduler-local.json"

        if config_path.exists() and not force:
            self.app.log.info(
                f"Project config already exists: {config_path} (use --force to overwrite)"
            )
            return

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.DEFAULT_PROJECT_CONFIG, f, indent=2)
            f.write("\n")

        self.app.log.info(f"Created project config: {config_path}")

    def _update_gitignore(self) -> None:
        """Update .gitignore with meetup-scheduler patterns."""
        gitignore_path = self._project_dir / ".gitignore"

        # Read existing content
        existing_lines: set[str] = set()
        if gitignore_path.exists():
            with open(gitignore_path, encoding="utf-8") as f:
                existing_lines = {line.rstrip() for line in f}

        # Find patterns that need to be added
        patterns_to_add = [
            p for p in self.GITIGNORE_PATTERNS if p not in existing_lines
        ]

        if not patterns_to_add:
            self.app.log.debug(".gitignore already has all required patterns")
            return

        # Append new patterns
        with open(gitignore_path, "a", encoding="utf-8") as f:
            # Add blank line if file exists and doesn't end with newline
            if existing_lines:
                f.write("\n")
            for pattern in patterns_to_add:
                f.write(f"{pattern}\n")

        self.app.log.info(f"Updated .gitignore with {len(patterns_to_add)} patterns")
