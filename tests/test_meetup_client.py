##############################################################################
#
# Name: test_meetup_client.py
#
# Function:
#       Unit tests for MeetupClient class
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from meetup_scheduler.meetup.client import MeetupClient


class TestMeetupClientInit:
    """Test MeetupClient initialization."""

    def test_init_stores_access_token(self) -> None:
        """Test that access token is stored."""
        client = MeetupClient("test_token")
        assert client._access_token == "test_token"


class TestMeetupClientExecuteQuery:
    """Test MeetupClient._execute_query method."""

    def test_execute_query_success(self) -> None:
        """Test successful query execution."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"self": {"id": "123", "name": "Test User"}}
        }

        with patch("httpx.post", return_value=mock_response):
            client = MeetupClient("test_token")
            result = client._execute_query("query { self { id name } }")

        assert result == {"self": {"id": "123", "name": "Test User"}}

    def test_execute_query_includes_auth_header(self) -> None:
        """Test that Authorization header is included."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}

        with patch("httpx.post", return_value=mock_response) as mock_post:
            client = MeetupClient("my_token")
            client._execute_query("query { self { id } }")

        # Check that Authorization header was passed
        call_kwargs = mock_post.call_args.kwargs
        assert "Bearer my_token" in call_kwargs["headers"]["Authorization"]

    def test_execute_query_network_error(self) -> None:
        """Test handling of network errors."""
        with patch("httpx.post", side_effect=httpx.RequestError("Connection failed")):
            client = MeetupClient("test_token")
            with pytest.raises(MeetupClient.Error) as exc_info:
                client._execute_query("query { self { id } }")

        assert "Network error" in str(exc_info.value)

    def test_execute_query_http_error(self) -> None:
        """Test handling of HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.side_effect = ValueError("Not JSON")

        with patch("httpx.post", return_value=mock_response):
            client = MeetupClient("test_token")
            with pytest.raises(MeetupClient.Error) as exc_info:
                client._execute_query("query { self { id } }")

        assert "HTTP error 500" in str(exc_info.value)

    def test_execute_query_graphql_error(self) -> None:
        """Test handling of GraphQL errors."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [{"message": "Field 'xyz' doesn't exist"}],
            "data": None,
        }

        with patch("httpx.post", return_value=mock_response):
            client = MeetupClient("test_token")
            with pytest.raises(MeetupClient.Error) as exc_info:
                client._execute_query("query { xyz }")

        assert "Field 'xyz' doesn't exist" in str(exc_info.value)

    def test_execute_query_rate_limited(self) -> None:
        """Test handling of rate limiting."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [{
                "message": "Too many requests",
                "extensions": {
                    "code": "RATE_LIMITED",
                    "resetAt": "2025-01-01T00:00:00Z",
                },
            }],
            "data": None,
        }

        with patch("httpx.post", return_value=mock_response):
            client = MeetupClient("test_token")
            with pytest.raises(MeetupClient.Error) as exc_info:
                client._execute_query("query { self { id } }")

        assert "Rate limited" in str(exc_info.value)


class TestMeetupClientGetSelf:
    """Test MeetupClient.get_self method."""

    def test_get_self_returns_user_data(self) -> None:
        """Test that get_self returns user data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "self": {
                    "id": "user123",
                    "name": "Test User",
                    "memberships": {
                        "count": 2,
                        "edges": [
                            {"node": {"id": "g1", "name": "Group 1", "isOrganizer": True}},
                            {"node": {"id": "g2", "name": "Group 2", "isOrganizer": False}},
                        ],
                    },
                }
            }
        }

        with patch("httpx.post", return_value=mock_response):
            client = MeetupClient("test_token")
            result = client.get_self()

        assert result["id"] == "user123"
        assert result["name"] == "Test User"
        assert result["memberships"]["count"] == 2


class TestMeetupClientGetOrganizedGroups:
    """Test MeetupClient.get_organized_groups method."""

    def test_get_organized_groups_filters_by_organizer(self) -> None:
        """Test that only organizer groups are returned."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "self": {
                    "id": "user123",
                    "name": "Test User",
                    "memberships": {
                        "count": 3,
                        "edges": [
                            {
                                "node": {
                                    "id": "g1",
                                    "name": "Organized Group",
                                    "urlname": "organized-group",
                                    "timezone": "America/New_York",
                                    "isOrganizer": True,
                                }
                            },
                            {
                                "node": {
                                    "id": "g2",
                                    "name": "Member Group",
                                    "urlname": "member-group",
                                    "timezone": "America/New_York",
                                    "isOrganizer": False,
                                }
                            },
                            {
                                "node": {
                                    "id": "g3",
                                    "name": "Another Organized",
                                    "urlname": "another-organized",
                                    "timezone": "America/Chicago",
                                    "isOrganizer": True,
                                }
                            },
                        ],
                    },
                }
            }
        }

        with patch("httpx.post", return_value=mock_response):
            client = MeetupClient("test_token")
            groups = client.get_organized_groups()

        assert len(groups) == 2
        assert groups[0]["urlname"] == "organized-group"
        assert groups[1]["urlname"] == "another-organized"

    def test_get_organized_groups_empty_when_no_organizer(self) -> None:
        """Test that empty list is returned when not an organizer."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "self": {
                    "id": "user123",
                    "memberships": {
                        "count": 1,
                        "edges": [
                            {"node": {"id": "g1", "isOrganizer": False}},
                        ],
                    },
                }
            }
        }

        with patch("httpx.post", return_value=mock_response):
            client = MeetupClient("test_token")
            groups = client.get_organized_groups()

        assert groups == []


class TestMeetupClientGetPastEvents:
    """Test MeetupClient.get_past_events method."""

    def test_get_past_events_returns_events(self) -> None:
        """Test that past events are returned."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "groupByUrlname": {
                    "id": "g1",
                    "name": "Test Group",
                    "urlname": "test-group",
                    "pastEvents": {
                        "count": 2,
                        "pageInfo": {"endCursor": None, "hasNextPage": False},
                        "edges": [
                            {
                                "node": {
                                    "id": "e1",
                                    "title": "Event 1",
                                    "dateTime": "2025-01-01T19:00:00Z",
                                    "venue": {"id": "v1", "name": "Venue 1"},
                                }
                            },
                            {
                                "node": {
                                    "id": "e2",
                                    "title": "Event 2",
                                    "dateTime": "2025-01-15T19:00:00Z",
                                    "venue": None,
                                }
                            },
                        ],
                    },
                }
            }
        }

        with patch("httpx.post", return_value=mock_response):
            client = MeetupClient("test_token")
            events = client.get_past_events("test-group", years=1)

        assert len(events) == 2
        assert events[0]["title"] == "Event 1"
        assert events[1]["title"] == "Event 2"

    def test_get_past_events_group_not_found(self) -> None:
        """Test error when group is not found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"groupByUrlname": None}
        }

        with patch("httpx.post", return_value=mock_response):
            client = MeetupClient("test_token")
            with pytest.raises(MeetupClient.Error) as exc_info:
                client.get_past_events("nonexistent-group")

        assert "Group not found" in str(exc_info.value)

    def test_get_past_events_pagination(self) -> None:
        """Test that pagination works correctly."""
        # First page response
        first_response = MagicMock()
        first_response.status_code = 200
        first_response.json.return_value = {
            "data": {
                "groupByUrlname": {
                    "id": "g1",
                    "name": "Test Group",
                    "urlname": "test-group",
                    "pastEvents": {
                        "count": 100,
                        "pageInfo": {"endCursor": "cursor1", "hasNextPage": True},
                        "edges": [
                            {
                                "node": {
                                    "id": "e1",
                                    "title": "Event 1",
                                    "dateTime": "2025-01-01T19:00:00Z",
                                    "venue": None,
                                }
                            },
                        ],
                    },
                }
            }
        }

        # Second page response
        second_response = MagicMock()
        second_response.status_code = 200
        second_response.json.return_value = {
            "data": {
                "groupByUrlname": {
                    "id": "g1",
                    "name": "Test Group",
                    "urlname": "test-group",
                    "pastEvents": {
                        "count": 100,
                        "pageInfo": {"endCursor": None, "hasNextPage": False},
                        "edges": [
                            {
                                "node": {
                                    "id": "e2",
                                    "title": "Event 2",
                                    "dateTime": "2025-01-15T19:00:00Z",
                                    "venue": None,
                                }
                            },
                        ],
                    },
                }
            }
        }

        with patch("httpx.post", side_effect=[first_response, second_response]):
            client = MeetupClient("test_token")
            events = client.get_past_events("test-group", years=1)

        assert len(events) == 2


class TestMeetupClientExtractVenues:
    """Test MeetupClient.extract_venues method."""

    def test_extract_venues_from_events(self) -> None:
        """Test extracting venues from events."""
        client = MeetupClient("test_token")
        events = [
            {"id": "e1", "venue": {"id": "v1", "name": "Venue 1", "city": "NYC"}},
            {"id": "e2", "venue": {"id": "v2", "name": "Venue 2", "city": "LA"}},
            {"id": "e3", "venue": None},
            {"id": "e4", "venue": {"id": "v1", "name": "Venue 1", "city": "NYC"}},
        ]

        venues = client.extract_venues(events)

        assert len(venues) == 2
        venue_ids = {v["id"] for v in venues}
        assert venue_ids == {"v1", "v2"}

    def test_extract_venues_empty_when_no_venues(self) -> None:
        """Test empty list when no venues."""
        client = MeetupClient("test_token")
        events = [
            {"id": "e1", "venue": None},
            {"id": "e2"},
        ]

        venues = client.extract_venues(events)

        assert venues == []

    def test_extract_venues_handles_missing_venue_id(self) -> None:
        """Test handling of venues without ID."""
        client = MeetupClient("test_token")
        events = [
            {"id": "e1", "venue": {"name": "No ID Venue"}},
            {"id": "e2", "venue": {"id": "v1", "name": "Has ID"}},
        ]

        venues = client.extract_venues(events)

        assert len(venues) == 1
        assert venues[0]["id"] == "v1"
