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
        self._project_dir: Path | None = None

    def execute(self) -> int:
        """Execute the init command.

        Returns:
            0 on success.

        Raises:
            CommandError: If initialization fails.
        """
        # Resolve target directory from path argument
        path_arg = getattr(self.args, "path", ".") or "."
        target_dir = Path(path_arg).resolve()

        # Check if target is the meetup-scheduler source directory
        if self._is_source_directory(target_dir):
            raise self.Error(
                f"Cannot initialize in the meetup-scheduler source directory: "
                f"{target_dir}\n"
                f"Please specify a different directory, e.g.:\n"
                f"  meetup-scheduler init ../my-meetup-project"
            )

        # Create target directory if it doesn't exist
        if not target_dir.exists():
            target_dir.mkdir(parents=True)
            self.app.log.info(f"Created directory: {target_dir}")

        self._project_dir = target_dir
        force = getattr(self.args, "force", False) or False

        # Create directories
        self._create_directories()

        # Create project config file
        self._create_project_config(force=force)

        # Update .gitignore
        self._update_gitignore()

        # Print success message with helpful instructions
        self._print_success_message()

        return 0

    def _is_source_directory(self, path: Path) -> bool:
        """Check if the given path is the meetup-scheduler source directory.

        Detects the source directory by checking for:
        - src/meetup_scheduler/ directory exists
        - pyproject.toml exists and contains 'name = "meetup-scheduler"'

        Args:
            path: Directory path to check.

        Returns:
            True if this appears to be the source directory.
        """
        # Check for src/meetup_scheduler/ directory
        src_dir = path / "src" / "meetup_scheduler"
        if not src_dir.is_dir():
            return False

        # Check for pyproject.toml with our project name
        pyproject = path / "pyproject.toml"
        if not pyproject.exists():
            return False

        try:
            content = pyproject.read_text(encoding="utf-8")
            # Simple check - look for our project name in the file
            if 'name = "meetup-scheduler"' in content:
                return True
        except OSError:
            pass

        return False

    def _create_directories(self) -> None:
        """Create the project directory structure."""
        assert self._project_dir is not None

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
        assert self._project_dir is not None
        config_path = self._project_dir / "meetup-scheduler-local.json"

        if config_path.exists() and not force:
            self.app.log.info(
                f"Project config already exists: {config_path} "
                f"(use --force to overwrite)"
            )
            return

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.DEFAULT_PROJECT_CONFIG, f, indent=2)
            f.write("\n")

        self.app.log.info(f"Created project config: {config_path}")

    def _update_gitignore(self) -> None:
        """Update .gitignore with meetup-scheduler patterns."""
        assert self._project_dir is not None
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

    def _print_success_message(self) -> None:
        """Print a success message with helpful next steps from README."""
        assert self._project_dir is not None

        from rich.console import Console
        from rich.markdown import Markdown
        from rich.panel import Panel

        from meetup_scheduler.resources.readme import ReadmeReader

        console = Console()

        # Print success header
        console.print(f"\n[bold green]Project initialized at:[/bold green] {self._project_dir}\n")

        # Show install instructions if running from source
        source_dir = self._find_source_directory()
        if source_dir:
            console.print(
                f"[yellow]Tip:[/yellow] If you haven't installed meetup-scheduler globally:\n"
                f"  uv tool install -e {source_dir}\n"
            )

        # Try to load auth setup instructions from README
        try:
            reader = ReadmeReader()
            auth_section = reader.get_section("auth-setup")
            if auth_section:
                panel = Panel(Markdown(auth_section), title="Next Steps", border_style="blue")
                console.print(panel)
                console.print()
        except ReadmeReader.Error:
            # Fall back to basic instructions if README not available
            console.print("[bold]Next steps:[/bold]")
            console.print()
            console.print("  Log in to your Meetup account:")
            console.print("    meetup-scheduler login")
            console.print()
            console.print("  For more information, run:")
            console.print("    meetup-scheduler readme")
            console.print()

    def _find_source_directory(self) -> Path | None:
        """Try to find the meetup-scheduler source directory.

        Returns:
            Path to source directory if found and we're in dev mode, None otherwise.
        """
        # Check if we're running from a source checkout by looking at
        # the module's file location
        try:
            import meetup_scheduler

            module_path = Path(meetup_scheduler.__file__).resolve()
            # module_path is something like .../src/meetup_scheduler/__init__.py
            # Go up to find the repo root
            potential_root = module_path.parent.parent.parent
            if self._is_source_directory(potential_root):
                return potential_root
        except (AttributeError, IndexError):
            pass

        return None
