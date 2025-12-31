##############################################################################
#
# Name: client.py
#
# Function:
#       Meetup GraphQL API client
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


class MeetupClient:
    """Client for the Meetup GraphQL API.

    Handles all GraphQL operations including fetching groups, events, and venues.
    Requires a valid access token for authentication.
    """

    class Error(Exception):
        """Exception raised for Meetup API errors."""

        pass

    # Meetup GraphQL API endpoint
    API_ENDPOINT = "https://api.meetup.com/gql"

    # Default timeout for API requests (seconds)
    DEFAULT_TIMEOUT = 30.0

    # Maximum items per page for pagination
    MAX_PAGE_SIZE = 50

    def __init__(self, access_token: str) -> None:
        """Initialize the Meetup client.

        Args:
            access_token: Valid OAuth access token for Meetup API.
        """
        self._access_token = access_token

    def _execute_query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query against the Meetup API.

        Args:
            query: GraphQL query string.
            variables: Optional variables for the query.

        Returns:
            The 'data' portion of the GraphQL response.

        Raises:
            Error: If the request fails or returns errors.
        """
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = httpx.post(
                self.API_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=self.DEFAULT_TIMEOUT,
            )
        except httpx.RequestError as e:
            raise self.Error(f"Network error: {e}") from e

        if response.status_code != 200:
            self._handle_http_error(response)

        try:
            result = response.json()
        except ValueError as e:
            raise self.Error(f"Invalid JSON response: {e}") from e

        # Check for GraphQL errors
        if "errors" in result:
            self._handle_graphql_errors(result["errors"])

        return result.get("data", {})

    def _handle_http_error(self, response: httpx.Response) -> None:
        """Handle non-200 HTTP responses.

        Args:
            response: The HTTP response.

        Raises:
            Error: Always raises with appropriate message.
        """
        # Try to extract error details from response
        try:
            error_data = response.json()
            if "errors" in error_data:
                self._handle_graphql_errors(error_data["errors"])
        except (ValueError, KeyError):
            pass

        raise self.Error(
            f"HTTP error {response.status_code}: {response.text[:200]}"
        )

    def _handle_graphql_errors(self, errors: list[dict[str, Any]]) -> None:
        """Handle GraphQL errors in the response.

        Args:
            errors: List of error objects from GraphQL response.

        Raises:
            Error: Always raises with appropriate message.
        """
        if not errors:
            return

        error = errors[0]
        message = error.get("message", "Unknown error")

        # Check for rate limiting
        extensions = error.get("extensions", {})
        if extensions.get("code") == "RATE_LIMITED":
            reset_at = extensions.get("resetAt")
            if reset_at:
                raise self.Error(f"Rate limited. Resets at: {reset_at}")
            raise self.Error("Rate limited. Try again later.")

        raise self.Error(f"API error: {message}")

    def get_self(self) -> dict[str, Any]:
        """Get information about the authenticated user.

        Returns:
            User information including id, name, and memberships.

        Raises:
            Error: If the request fails.
        """
        query = """
        query {
            self {
                id
                name
                memberships(input: { first: 100 }) {
                    count
                    edges {
                        node {
                            id
                            name
                            urlname
                            timezone
                            isOrganizer
                        }
                    }
                }
            }
        }
        """
        data = self._execute_query(query)
        return data.get("self", {})

    def get_organized_groups(self) -> list[dict[str, Any]]:
        """Get groups that the user organizes.

        Returns:
            List of group dictionaries with id, name, urlname, timezone.

        Raises:
            Error: If the request fails.
        """
        self_data = self.get_self()
        memberships = self_data.get("memberships", {})
        edges = memberships.get("edges", [])

        groups = []
        for edge in edges:
            node = edge.get("node", {})
            if node.get("isOrganizer"):
                groups.append({
                    "id": node.get("id"),
                    "name": node.get("name"),
                    "urlname": node.get("urlname"),
                    "timezone": node.get("timezone"),
                })

        return groups

    def get_past_events(
        self,
        urlname: str,
        years: int = 2,
    ) -> list[dict[str, Any]]:
        """Get past events for a group.

        Args:
            urlname: The group's URL name.
            years: Number of years to look back (default: 2).

        Returns:
            List of event dictionaries.

        Raises:
            Error: If the request fails.
        """
        query = """
        query($urlname: String!, $first: Int!, $after: String) {
            groupByUrlname(urlname: $urlname) {
                id
                name
                urlname
                pastEvents(input: { first: $first, after: $after }) {
                    count
                    pageInfo {
                        endCursor
                        hasNextPage
                    }
                    edges {
                        node {
                            id
                            title
                            dateTime
                            venue {
                                id
                                name
                                address
                                city
                                state
                                country
                            }
                        }
                    }
                }
            }
        }
        """

        # Calculate cutoff date
        cutoff = datetime.now(timezone.utc) - timedelta(days=years * 365)

        events: list[dict[str, Any]] = []
        cursor: str | None = None
        has_next = True

        while has_next:
            variables: dict[str, Any] = {
                "urlname": urlname,
                "first": self.MAX_PAGE_SIZE,
            }
            if cursor:
                variables["after"] = cursor

            data = self._execute_query(query, variables)
            group = data.get("groupByUrlname", {})

            if not group:
                raise self.Error(f"Group not found: {urlname}")

            past_events = group.get("pastEvents", {})
            edges = past_events.get("edges", [])

            for edge in edges:
                node = edge.get("node", {})
                event_dt = node.get("dateTime")

                # Check if event is within the time range
                if event_dt:
                    try:
                        # Parse ISO format datetime
                        dt = datetime.fromisoformat(event_dt.replace("Z", "+00:00"))
                        if dt < cutoff:
                            # Event is too old, stop pagination
                            has_next = False
                            break
                    except ValueError:
                        pass

                events.append(node)

            # Check for more pages
            page_info = past_events.get("pageInfo", {})
            if has_next:
                has_next = page_info.get("hasNextPage", False)
                cursor = page_info.get("endCursor")

        return events

    def extract_venues(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract unique venues from a list of events.

        Args:
            events: List of event dictionaries.

        Returns:
            List of unique venue dictionaries.
        """
        venues_by_id: dict[str, dict[str, Any]] = {}

        for event in events:
            venue = event.get("venue")
            if venue and venue.get("id"):
                venue_id = venue["id"]
                if venue_id not in venues_by_id:
                    venues_by_id[venue_id] = {
                        "id": venue_id,
                        "name": venue.get("name", ""),
                        "address": venue.get("address", ""),
                        "city": venue.get("city", ""),
                        "state": venue.get("state", ""),
                        "country": venue.get("country", ""),
                    }

        return list(venues_by_id.values())
