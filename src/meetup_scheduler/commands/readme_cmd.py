##############################################################################
#
# Name: readme_cmd.py
#
# Function:
#       ReadmeCommand class for displaying README documentation
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

from typing import TYPE_CHECKING

from meetup_scheduler.commands.base import BaseCommand
from meetup_scheduler.resources.readme import ReadmeReader

if TYPE_CHECKING:
    import argparse

    from meetup_scheduler.app import App


class ReadmeCommand(BaseCommand):
    """Display the README documentation.

    Shows the bundled README.md either formatted for the terminal
    or as raw markdown source.
    """

    def __init__(self, app: App, args: argparse.Namespace) -> None:
        """Initialize the command."""
        super().__init__(app, args)
        self._reader = ReadmeReader()

    def execute(self) -> int:
        """Execute the readme command.

        Returns:
            0 on success, 1 on error.
        """
        raw = getattr(self.args, "raw", False) or False
        pager = getattr(self.args, "pager", True)
        section = getattr(self.args, "section", None)

        # Use pager for formatted output if --pager is enabled (default)
        # pager can be None in testing mode, treat as True
        use_pager = not raw and (pager if pager is not None else True)

        try:
            if section:
                # Print a specific section
                if not self._reader.print_section(section, raw=raw, pager=use_pager):
                    self.app.log.error(f"Section not found: {section}")
                    self._print_available_sections()
                    return 1
            elif raw:
                # Print raw markdown
                self._reader.print_raw()
            else:
                # Print formatted markdown with pager
                self._reader.print_formatted(pager=use_pager)

            return 0

        except ReadmeReader.Error as e:
            self.app.log.error(str(e))
            return 1

    def _print_available_sections(self) -> None:
        """Print list of available sections."""
        try:
            sections = self._reader.get_all_sections()
            if sections:
                print("\nAvailable sections:")
                for name in sorted(sections.keys()):
                    print(f"  - {name}")
        except ReadmeReader.Error:
            pass
