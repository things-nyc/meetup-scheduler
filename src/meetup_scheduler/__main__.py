##############################################################################
#
# Name: __main__.py
#
# Function:
#       Entry point for meetup-scheduler CLI
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import sys


def main() -> int:
    """Single entry point - creates App and runs it."""
    from meetup_scheduler.app import App

    try:
        app = App()
        return app.run()
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
