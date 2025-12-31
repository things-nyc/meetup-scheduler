##############################################################################
#
# Name: sync_cmd.py
#
# Function:
#       SyncCommand class for fetching Meetup group and venue data
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from rich.console import Console

from meetup_scheduler.auth.tokens import TokenManager
from meetup_scheduler.commands.base import BaseCommand
from meetup_scheduler.meetup.client import MeetupClient

if TYPE_CHECKING:
    import argparse

    from meetup_scheduler.app import App


class SyncCommand(BaseCommand):
    """Sync group and venue data from Meetup API.

    Fetches groups the user organizes and extracts venue information from
    past events. Data is cached locally for use by schedule and generate
    commands.
    """

    def __init__(self, app: App, args: argparse.Namespace) -> None:
        """Initialize the command."""
        super().__init__(app, args)
        self._console = Console()

    def execute(self) -> int:
        """Execute the sync command.

        Returns:
            0 on success, 1 on failure.
        """
        # Check authentication
        token_manager = TokenManager(self.app.config_manager)
        if not token_manager.is_authenticated:
            raise self.Error(
                "Not authenticated. Run: meetup-scheduler login"
            )

        # Get access token (with auto-refresh)
        try:
            access_token = token_manager.get_access_token()
        except TokenManager.Error as e:
            raise self.Error(f"Failed to get access token: {e}") from e

        if not access_token:
            raise self.Error(
                "No access token available. Run: meetup-scheduler login"
            )

        # Create client
        client = MeetupClient(access_token)

        # Get options from args
        specific_group = getattr(self.args, "group", None)
        years = getattr(self.args, "years", 2)
        venues_only = getattr(self.args, "venues_only", False)

        if not self.args.quiet:
            self._console.print()
            self._console.print("[bold]Syncing Meetup data...[/bold]")
            self._console.print()

        # Fetch groups
        if not venues_only:
            groups = self._sync_groups(client, specific_group)
        else:
            # For venues-only, still need to know which groups to query
            groups = self._get_configured_groups(specific_group)

        if not groups:
            if specific_group:
                raise self.Error(f"Group not found: {specific_group}")
            raise self.Error(
                "No organized groups found. "
                "Make sure you have organizer privileges on at least one group."
            )

        # Fetch venues
        all_venues = self._sync_venues(client, groups, years)

        # Save sync timestamp
        self.app.config_manager.set(
            "lastSync",
            datetime.now(timezone.utc).isoformat(),
            user_level=False,
        )

        # Summary
        if not self.args.quiet:
            self._console.print()
            self._console.print("[bold green]Sync complete![/bold green]")
            if not venues_only:
                self._console.print(f"  Groups: {len(groups)}")
            self._console.print(f"  Venues: {len(all_venues)}")
            self._console.print()

        return 0

    def _sync_groups(
        self,
        client: MeetupClient,
        specific_group: str | None,
    ) -> list[dict[str, Any]]:
        """Sync group data from Meetup.

        Args:
            client: Meetup API client.
            specific_group: Optional specific group urlname to sync.

        Returns:
            List of synced groups.
        """
        if not self.args.quiet:
            self._console.print("Fetching groups...", end=" ")

        try:
            groups = client.get_organized_groups()
        except MeetupClient.Error as e:
            raise self.Error(str(e)) from e

        # Filter to specific group if requested
        if specific_group:
            groups = [g for g in groups if g.get("urlname") == specific_group]

        if not self.args.quiet:
            self._console.print(f"found {len(groups)} organized groups")
            for group in groups:
                self._console.print(f"  - {group.get('name')} ({group.get('urlname')})")

        # Save groups to config
        groups_data: dict[str, Any] = {}
        for group in groups:
            urlname = group.get("urlname", "")
            if urlname:
                groups_data[urlname] = {
                    "id": group.get("id"),
                    "name": group.get("name"),
                    "urlname": urlname,
                    "timezone": group.get("timezone"),
                }

        if groups_data:
            self.app.config_manager.set("groups", groups_data, user_level=False)

        return groups

    def _get_configured_groups(
        self,
        specific_group: str | None,
    ) -> list[dict[str, Any]]:
        """Get groups from existing configuration.

        Args:
            specific_group: Optional specific group urlname.

        Returns:
            List of configured groups.
        """
        groups_config = self.app.config_manager.get("groups", {})
        if not groups_config:
            return []

        groups = []
        for urlname, data in groups_config.items():
            if specific_group and urlname != specific_group:
                continue
            groups.append({
                "urlname": urlname,
                "name": data.get("name", urlname),
                **data,
            })

        return groups

    def _sync_venues(
        self,
        client: MeetupClient,
        groups: list[dict[str, Any]],
        years: int,
    ) -> list[dict[str, Any]]:
        """Sync venue data from past events.

        Args:
            client: Meetup API client.
            groups: List of groups to fetch venues from.
            years: Number of years to look back.

        Returns:
            List of all unique venues.
        """
        all_venues: dict[str, dict[str, Any]] = {}

        for group in groups:
            urlname = group.get("urlname", "")
            name = group.get("name", urlname)

            if not self.args.quiet:
                self._console.print()
                self._console.print(
                    f"Fetching venues from {name} (last {years} years)..."
                )

            try:
                events = client.get_past_events(urlname, years=years)
            except MeetupClient.Error as e:
                self.app.log.warning(f"Failed to fetch events for {urlname}: {e}")
                continue

            venues = client.extract_venues(events)

            if not self.args.quiet:
                self._console.print(f"  - Found {len(events)} past events")
                self._console.print(f"  - Extracted {len(venues)} unique venues")

            # Merge venues (using venue ID as key)
            for venue in venues:
                venue_id = venue.get("id")
                if venue_id and venue_id not in all_venues:
                    all_venues[venue_id] = venue

        # Save venues to config
        if all_venues:
            self.app.config_manager.set("venues", all_venues, user_level=False)

        return list(all_venues.values())
