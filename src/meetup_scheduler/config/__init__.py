##############################################################################
#
# Name: __init__.py
#
# Function:
#       Configuration package initialization for meetup_scheduler
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

from meetup_scheduler.config.manager import ConfigManager

__all__ = ["ConfigManager"]
