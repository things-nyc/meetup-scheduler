##############################################################################
#
# Name: metadata.py
#
# Function:
#       Project metadata utilities - single source of truth from pyproject.toml
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

from functools import lru_cache
from importlib import metadata


@lru_cache(maxsize=1)
def get_project_urls() -> dict[str, str]:
    """Get project URLs from package metadata.

    Returns:
        Dictionary mapping URL type to URL string.
        Example: {"Homepage": "https://github.com/...", "Repository": "..."}
    """
    try:
        meta = metadata.metadata("meetup-scheduler")
        urls: dict[str, str] = {}
        # Project-URL fields are formatted as "Label, URL"
        for url_entry in meta.get_all("Project-URL") or []:
            if ", " in url_entry:
                label, url = url_entry.split(", ", 1)
                urls[label] = url
        return urls
    except metadata.PackageNotFoundError:
        return {}


def get_homepage_url() -> str:
    """Get the project homepage URL.

    Returns:
        Homepage URL or empty string if not available.
    """
    return get_project_urls().get("Homepage", "")


def get_repository_url() -> str:
    """Get the project repository URL.

    Returns:
        Repository URL or empty string if not available.
    """
    return get_project_urls().get("Repository", "")
