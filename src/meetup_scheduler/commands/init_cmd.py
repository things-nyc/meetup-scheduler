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
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

from meetup_scheduler.commands.base import BaseCommand

if TYPE_CHECKING:
    import argparse

    from meetup_scheduler.app import App


class InitCommand(BaseCommand):
    """Initialize a project directory for meetup-scheduler.

    Creates the following structure:
    - .meetup-scheduler/         Project directory
    - .meetup-scheduler/cache/   API response cache
    - .meetup-scheduler/schemas/ JSON schemas for validation
    - .vscode/settings.json      VS Code JSON schema associations
    - meetup-scheduler-local.json   Project configuration file
    - events/                    Directory for event JSON files
    - Updates .gitignore with appropriate patterns
    """

    # Files and directories to create
    PROJECT_DIR = ".meetup-scheduler"
    CACHE_SUBDIR = "cache"
    SCHEMAS_SUBDIR = "schemas"
    VSCODE_DIR = ".vscode"
    EVENTS_DIR = "events"

    # Schema files to copy from package resources
    SCHEMA_FILES = [
        "config.schema.json",
        "events.schema.json",
        "venues.schema.json",
    ]

    # Patterns to add to .gitignore
    GITIGNORE_PATTERNS = [
        "# meetup-scheduler",
        ".meetup-scheduler/",
        "meetup-scheduler-local.json",
    ]

    # Default project config template (schema path updated in _create_project_config)
    DEFAULT_PROJECT_CONFIG = {
        "$schema": "./.meetup-scheduler/schemas/config.schema.json",
        "defaults": {
            "publishStatus": "DRAFT",
        },
        "venueAliases": {},
    }

    # VS Code settings for JSON schema associations
    VSCODE_SETTINGS = {
        "json.schemas": [
            {
                "fileMatch": ["meetup-scheduler-local.json"],
                "url": "./.meetup-scheduler/schemas/config.schema.json",
            },
            {
                "fileMatch": ["events/*.json"],
                "url": "./.meetup-scheduler/schemas/events.schema.json",
            },
        ]
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

        # Copy schemas from package resources
        self._copy_schemas(force=force)

        # Create .vscode/settings.json
        self._create_vscode_settings(force=force)

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
        cache_dir = self._project_dir / self.PROJECT_DIR / self.CACHE_SUBDIR
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.app.log.debug(f"Created cache directory: {cache_dir}")

        # Create .meetup-scheduler/schemas/
        schemas_dir = self._project_dir / self.PROJECT_DIR / self.SCHEMAS_SUBDIR
        schemas_dir.mkdir(parents=True, exist_ok=True)
        self.app.log.debug(f"Created schemas directory: {schemas_dir}")

        # Create .vscode/
        vscode_dir = self._project_dir / self.VSCODE_DIR
        vscode_dir.mkdir(exist_ok=True)
        self.app.log.debug(f"Created .vscode directory: {vscode_dir}")

        # Create events/
        events_dir = self._project_dir / self.EVENTS_DIR
        events_dir.mkdir(exist_ok=True)
        self.app.log.debug(f"Created events directory: {events_dir}")

    def _copy_schemas(self, *, force: bool = False) -> None:
        """Copy JSON schemas from package resources to project directory.

        Args:
            force: If True, overwrite existing schema files.
        """
        assert self._project_dir is not None
        schemas_dir = self._project_dir / self.PROJECT_DIR / self.SCHEMAS_SUBDIR

        # Get the schemas from package resources
        schema_package = resources.files("meetup_scheduler.resources.schemas")

        for schema_name in self.SCHEMA_FILES:
            dest_path = schemas_dir / schema_name

            if dest_path.exists() and not force:
                self.app.log.debug(f"Schema already exists: {dest_path}")
                continue

            # Read schema from package resources
            schema_file = schema_package.joinpath(schema_name)
            schema_content = schema_file.read_text(encoding="utf-8")

            # Write to project directory
            dest_path.write_text(schema_content, encoding="utf-8")
            self.app.log.debug(f"Copied schema: {schema_name}")

        self.app.log.info(f"Copied {len(self.SCHEMA_FILES)} schema files")

    def _create_vscode_settings(self, *, force: bool = False) -> None:
        """Create .vscode/settings.json with JSON schema associations.

        Args:
            force: If True, overwrite existing settings.
        """
        assert self._project_dir is not None
        settings_path = self._project_dir / self.VSCODE_DIR / "settings.json"

        if settings_path.exists() and not force:
            # Merge our settings with existing
            try:
                existing = json.loads(settings_path.read_text(encoding="utf-8"))
                # Check if our schemas are already configured
                existing_schemas = existing.get("json.schemas", [])
                our_schemas = self.VSCODE_SETTINGS["json.schemas"]

                # Simple check: if any of our fileMatches are present, skip
                existing_file_matches = set()
                for schema in existing_schemas:
                    existing_file_matches.update(schema.get("fileMatch", []))

                needs_update = False
                for schema in our_schemas:
                    for pattern in schema.get("fileMatch", []):
                        if pattern not in existing_file_matches:
                            needs_update = True
                            existing_schemas.append(schema)
                            break

                if needs_update:
                    existing["json.schemas"] = existing_schemas
                    with open(settings_path, "w", encoding="utf-8") as f:
                        json.dump(existing, f, indent=2)
                        f.write("\n")
                    self.app.log.info("Updated .vscode/settings.json with schema associations")
                else:
                    self.app.log.debug(".vscode/settings.json already has schema associations")
                return
            except (json.JSONDecodeError, KeyError):
                # If we can't parse existing, only overwrite with force
                self.app.log.info(
                    ".vscode/settings.json exists but couldn't merge "
                    "(use --force to overwrite)"
                )
                return

        # Create new settings file
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(self.VSCODE_SETTINGS, f, indent=2)
            f.write("\n")

        self.app.log.info("Created .vscode/settings.json with schema associations")

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
