##############################################################################
#
# Name: __init__.py
#
# Function:
#       Meetup API package initialization for meetup_scheduler
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

from meetup_scheduler.meetup.client import MeetupClient

__all__ = ["MeetupClient"]
