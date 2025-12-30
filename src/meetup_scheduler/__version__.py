##############################################################################
#
# Name: __version__.py
#
# Function:
#       Provide package version from pyproject.toml metadata
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

try:
    from importlib.metadata import version as _version

    __version__ = _version("meetup-scheduler")
except Exception:
    # Package not installed, use development version
    __version__ = "0.1.0.dev0"
