##############################################################################
#
# Name: login_cmd.py
#
# Function:
#       LoginCommand class for Meetup authentication
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING

from rich.console import Console

from meetup_scheduler.auth.oauth import OAuthFlow
from meetup_scheduler.auth.server import CallbackServer
from meetup_scheduler.auth.tokens import TokenManager
from meetup_scheduler.commands.base import BaseCommand

if TYPE_CHECKING:
    import argparse

    from meetup_scheduler.app import App


class LoginCommand(BaseCommand):
    """Authenticate with Meetup via browser-based OAuth flow.

    Opens the user's browser to Meetup's authorization page. After the user
    grants permission, the callback is captured by a local server and tokens
    are stored securely.
    """

    # Default timeout for waiting for callback (5 minutes)
    DEFAULT_TIMEOUT = 300

    def __init__(self, app: App, args: argparse.Namespace) -> None:
        """Initialize the command."""
        super().__init__(app, args)
        self._console = Console()

    def execute(self) -> int:
        """Execute the login command.

        Returns:
            0 on success, 1 on failure.
        """
        oauth = OAuthFlow()
        token_manager = TokenManager(self.app.config_manager)

        # Check if OAuth is configured
        if not oauth.is_configured:
            raise self.Error(
                "OAuth credentials not configured.\n"
                "Set MEETUP_CLIENT_ID and MEETUP_CLIENT_SECRET environment variables."
            )

        # Check if already authenticated
        if token_manager.is_authenticated:
            self._console.print(
                "[green]Already authenticated with Meetup.[/green]"
            )
            self._console.print(
                "Run [bold]meetup-scheduler logout[/bold] first to re-authenticate."
            )
            return 0

        # Get port from args
        port = getattr(self.args, "port", CallbackServer.DEFAULT_PORT)

        # Start callback server
        server = CallbackServer(port=port)
        try:
            server.start()
        except CallbackServer.Error as e:
            raise self.Error(str(e)) from e

        try:
            # Generate state for CSRF protection
            state = oauth.generate_state()

            # Build authorization URL
            auth_url = oauth.get_authorize_url(state, server.redirect_uri)

            # Open browser
            self._console.print()
            self._console.print(
                "[bold]Opening browser for Meetup authentication...[/bold]"
            )
            self._console.print()
            self._console.print(
                "If the browser doesn't open, visit this URL:"
            )
            self._console.print(f"  [link]{auth_url}[/link]")
            self._console.print()

            if not webbrowser.open(auth_url):
                self.app.log.warning("Failed to open browser automatically")

            # Wait for callback
            self._console.print("Waiting for authentication...")
            try:
                code, returned_state = server.wait_for_callback(
                    timeout=self.DEFAULT_TIMEOUT
                )
            except CallbackServer.TimeoutError as e:
                raise self.Error(str(e)) from e
            except CallbackServer.Error as e:
                raise self.Error(f"Authentication failed: {e}") from e

            # Verify state
            if returned_state != state:
                raise self.Error(
                    "Security error: State mismatch. "
                    "This could indicate a CSRF attack. Please try again."
                )

            # Exchange code for tokens
            self._console.print("Exchanging authorization code for tokens...")
            try:
                tokens = oauth.exchange_code(code, server.redirect_uri)
            except OAuthFlow.Error as e:
                raise self.Error(str(e)) from e

            # Save tokens
            token_manager.save_tokens(tokens)

            self._console.print()
            self._console.print(
                "[bold green]Successfully authenticated with Meetup![/bold green]"
            )
            self._console.print()
            self._console.print("You can now use meetup-scheduler commands.")
            self._console.print()

            return 0

        finally:
            server.stop()
