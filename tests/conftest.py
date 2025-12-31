##############################################################################
#
# Name: conftest.py
#
# Function:
#       Pytest fixtures for meetup-scheduler tests
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import json
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import respx
from httpx import Response


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_project_dir(tmp_path: Path) -> Path:
    """Return a temporary project directory."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    return project_dir


# =============================================================================
# OAuth Environment Fixtures
# =============================================================================


@pytest.fixture
def mock_oauth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up mock OAuth environment variables."""
    monkeypatch.setenv("MEETUP_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("MEETUP_CLIENT_SECRET", "test_client_secret")


# =============================================================================
# Credentials Fixtures
# =============================================================================


@pytest.fixture
def mock_credentials_data() -> dict[str, Any]:
    """Return mock OAuth credentials data."""
    expires_at = datetime.now(timezone.utc).timestamp() + 3600  # 1 hour from now
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_at": expires_at,
    }


@pytest.fixture
def mock_credentials_dir(
    tmp_path: Path, mock_credentials_data: dict[str, Any]
) -> Path:
    """Create a temporary config directory with mock credentials."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    creds_file = config_dir / "credentials.json"
    creds_file.write_text(json.dumps(mock_credentials_data))

    return config_dir


@pytest.fixture
def mock_user_config_dir(
    mock_credentials_dir: Path,
) -> Generator[Path, None, None]:
    """Patch platformdirs to use mock config directory."""
    with patch("platformdirs.user_config_dir", return_value=str(mock_credentials_dir)):
        yield mock_credentials_dir


# =============================================================================
# Meetup API Response Fixtures
# =============================================================================


@pytest.fixture
def mock_self_response() -> dict[str, Any]:
    """Return a mock response for the self query."""
    return {
        "data": {
            "self": {
                "id": "user123",
                "name": "Test User",
                "memberships": {
                    "count": 2,
                    "edges": [
                        {
                            "node": {
                                "id": "g1",
                                "name": "Test Group One",
                                "urlname": "test-group-one",
                                "timezone": "America/New_York",
                                "isOrganizer": True,
                            }
                        },
                        {
                            "node": {
                                "id": "g2",
                                "name": "Test Group Two",
                                "urlname": "test-group-two",
                                "timezone": "America/Chicago",
                                "isOrganizer": True,
                            }
                        },
                        {
                            "node": {
                                "id": "g3",
                                "name": "Member Only Group",
                                "urlname": "member-only",
                                "timezone": "America/Los_Angeles",
                                "isOrganizer": False,
                            }
                        },
                    ],
                },
            }
        }
    }


@pytest.fixture
def mock_past_events_response() -> dict[str, Any]:
    """Return a mock response for past events query."""
    return {
        "data": {
            "groupByUrlname": {
                "id": "g1",
                "name": "Test Group One",
                "urlname": "test-group-one",
                "pastEvents": {
                    "count": 3,
                    "pageInfo": {"endCursor": None, "hasNextPage": False},
                    "edges": [
                        {
                            "node": {
                                "id": "e1",
                                "title": "Event One",
                                "dateTime": "2025-01-15T19:00:00-05:00",
                                "venue": {
                                    "id": "v1",
                                    "name": "Venue One",
                                    "address": "123 Main St",
                                    "city": "New York",
                                    "state": "NY",
                                    "country": "US",
                                },
                            }
                        },
                        {
                            "node": {
                                "id": "e2",
                                "title": "Event Two",
                                "dateTime": "2025-01-08T19:00:00-05:00",
                                "venue": {
                                    "id": "v2",
                                    "name": "Venue Two",
                                    "address": "456 Oak Ave",
                                    "city": "Brooklyn",
                                    "state": "NY",
                                    "country": "US",
                                },
                            }
                        },
                        {
                            "node": {
                                "id": "e3",
                                "title": "Online Event",
                                "dateTime": "2025-01-01T19:00:00-05:00",
                                "venue": None,
                            }
                        },
                    ],
                },
            }
        }
    }


@pytest.fixture
def mock_past_events_response_group2() -> dict[str, Any]:
    """Return a mock response for past events from group 2."""
    return {
        "data": {
            "groupByUrlname": {
                "id": "g2",
                "name": "Test Group Two",
                "urlname": "test-group-two",
                "pastEvents": {
                    "count": 2,
                    "pageInfo": {"endCursor": None, "hasNextPage": False},
                    "edges": [
                        {
                            "node": {
                                "id": "e4",
                                "title": "Group Two Event",
                                "dateTime": "2025-01-20T18:00:00-06:00",
                                "venue": {
                                    "id": "v3",
                                    "name": "Chicago Venue",
                                    "address": "789 Lake Dr",
                                    "city": "Chicago",
                                    "state": "IL",
                                    "country": "US",
                                },
                            }
                        },
                        {
                            "node": {
                                "id": "e5",
                                "title": "Same Venue Event",
                                "dateTime": "2025-01-10T18:00:00-06:00",
                                "venue": {
                                    "id": "v1",
                                    "name": "Venue One",
                                    "address": "123 Main St",
                                    "city": "New York",
                                    "state": "NY",
                                    "country": "US",
                                },
                            }
                        },
                    ],
                },
            }
        }
    }


# =============================================================================
# Respx Mock Fixtures
# =============================================================================


def create_meetup_api_handler(
    mock_self_response: dict[str, Any],
    mock_past_events_response: dict[str, Any],
    mock_past_events_response_group2: dict[str, Any],
) -> Any:
    """Create a handler function for mocking the Meetup GraphQL API."""

    def route_handler(request: Any) -> Response:
        """Route requests to appropriate mock responses."""
        body = json.loads(request.content)
        query = body.get("query", "")
        variables = body.get("variables", {})

        # Self query (get user info and groups)
        if "self" in query and "memberships" in query:
            return Response(200, json=mock_self_response)

        # Past events query
        if "groupByUrlname" in query and "pastEvents" in query:
            urlname = variables.get("urlname", "")
            if urlname == "test-group-one":
                return Response(200, json=mock_past_events_response)
            elif urlname == "test-group-two":
                return Response(200, json=mock_past_events_response_group2)
            else:
                # Group not found
                return Response(200, json={"data": {"groupByUrlname": None}})

        # Default: return empty data
        return Response(200, json={"data": {}})

    return route_handler


@pytest.fixture
def mock_meetup_api(
    mock_self_response: dict[str, Any],
    mock_past_events_response: dict[str, Any],
    mock_past_events_response_group2: dict[str, Any],
) -> Generator[respx.MockRouter, None, None]:
    """Create a respx mock for the Meetup GraphQL API.

    This fixture intercepts all HTTP requests to the Meetup API and returns
    appropriate mock responses based on the query content.
    """
    handler = create_meetup_api_handler(
        mock_self_response,
        mock_past_events_response,
        mock_past_events_response_group2,
    )

    with respx.mock(assert_all_called=False) as router:
        router.post("https://api.meetup.com/gql").mock(side_effect=handler)
        yield router


@pytest.fixture
def mock_sync_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_oauth_env: None,
    mock_credentials_data: dict[str, Any],
    mock_self_response: dict[str, Any],
    mock_past_events_response: dict[str, Any],
    mock_past_events_response_group2: dict[str, Any],
) -> Generator[tuple[Path, respx.MockRouter], None, None]:
    """Set up complete environment for sync command integration tests.

    This fixture combines:
    - Temporary working directory
    - OAuth environment variables
    - Mock credentials
    - Mocked Meetup API

    Yields:
        Tuple of (working directory, respx router)
    """
    # Set up working directory
    monkeypatch.chdir(tmp_path)

    # Set up credentials
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    creds_file = config_dir / "credentials.json"
    creds_file.write_text(json.dumps(mock_credentials_data))

    # Create API handler
    handler = create_meetup_api_handler(
        mock_self_response,
        mock_past_events_response,
        mock_past_events_response_group2,
    )

    # Set up respx mock with route BEFORE starting
    router = respx.mock(assert_all_called=False)
    router.post("https://api.meetup.com/gql").mock(side_effect=handler)
    router.start()

    # Start platformdirs patch
    patcher = patch("platformdirs.user_config_dir", return_value=str(config_dir))
    patcher.start()

    try:
        yield tmp_path, router
    finally:
        patcher.stop()
        router.stop()
