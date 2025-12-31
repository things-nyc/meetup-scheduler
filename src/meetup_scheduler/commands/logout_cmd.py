##############################################################################
#
# Name: logout_cmd.py
#
# Function:
#       LogoutCommand class for removing stored credentials
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

from rich.console import Console

from meetup_scheduler.auth.tokens import TokenManager
from meetup_scheduler.commands.base import BaseCommand

if TYPE_CHECKING:
    import argparse

    from meetup_scheduler.app import App


class LogoutCommand(BaseCommand):
    """Remove stored Meetup credentials.

    Clears all stored OAuth tokens from the credentials file.
    """

    def __init__(self, app: App, args: argparse.Namespace) -> None:
        """Initialize the command."""
        super().__init__(app, args)
        self._console = Console()

    def execute(self) -> int:
        """Execute the logout command.

        Returns:
            0 on success.
        """
        token_manager = TokenManager(self.app.config_manager)

        # Check if we have any tokens
        if not token_manager.has_tokens:
            self._console.print("Not currently logged in.")
            return 0

        # Clear tokens
        token_manager.clear_tokens()

        self._console.print("[green]Successfully logged out.[/green]")
        self._console.print()
        self._console.print(
            "Run [bold]meetup-scheduler login[/bold] to authenticate again."
        )

        return 0
