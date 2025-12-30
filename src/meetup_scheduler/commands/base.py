##############################################################################
#
# Name: base.py
#
# Function:
#       Base command class for meetup-scheduler CLI commands
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
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meetup_scheduler.app import App


class CommandError(Exception):
    """Exception raised by commands to indicate failure with a message."""

    pass


class BaseCommand(ABC):
    """Base class for all CLI commands."""

    # Nested exception class for command errors
    Error = CommandError

    def __init__(self, app: App, args: argparse.Namespace) -> None:
        """Initialize the command.

        Args:
            app: The parent App instance.
            args: Parsed command-line arguments.
        """
        self._app = app
        self._args = args

    @property
    def app(self) -> App:
        """Return the parent App instance."""
        return self._app

    @property
    def args(self) -> argparse.Namespace:
        """Return parsed arguments."""
        return self._args

    @abstractmethod
    def execute(self) -> int:
        """Execute the command, return exit code.

        Commands should raise BaseCommand.Error for expected failures
        (e.g., invalid input, API errors) rather than returning non-zero.
        The App class catches these and displays the error message.

        Returns:
            Exit code (0 for success).

        Raises:
            CommandError: For expected command failures.
        """
        raise self.Error("Subclass does not implement execute()")
