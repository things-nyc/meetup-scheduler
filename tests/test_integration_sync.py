##############################################################################
#
# Name: test_integration_sync.py
#
# Function:
#       Integration tests for sync command with mocked Meetup API
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
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx
from httpx import Response

from meetup_scheduler.app import App


class TestSyncIntegrationFullFlow:
    """Integration tests for the complete sync command flow."""

    def test_sync_full_flow_with_respx(
        self,
        mock_sync_environment: tuple[Path, respx.MockRouter],
    ) -> None:
        """Test complete sync flow: auth check -> fetch groups -> fetch events."""
        tmp_path, router = mock_sync_environment

        app = App(args=["-q", "sync"])
        result = app.run()

        assert result == 0

        # Verify API was called (self query + 2 group event queries)
        assert router.calls.call_count >= 3

    def test_sync_saves_groups_to_project_config(
        self,
        mock_sync_environment: tuple[Path, respx.MockRouter],
    ) -> None:
        """Test that sync saves groups to project config file."""
        tmp_path, _ = mock_sync_environment

        app = App(args=["-q", "sync"])
        result = app.run()

        assert result == 0

        # Check project config was created
        config_file = tmp_path / "meetup-scheduler-local.json"
        assert config_file.exists()

        config_data = json.loads(config_file.read_text())
        assert "groups" in config_data
        assert "test-group-one" in config_data["groups"]
        assert "test-group-two" in config_data["groups"]

        # Verify group data
        group_one = config_data["groups"]["test-group-one"]
        assert group_one["name"] == "Test Group One"
        assert group_one["timezone"] == "America/New_York"

    def test_sync_saves_venues_to_project_config(
        self,
        mock_sync_environment: tuple[Path, respx.MockRouter],
    ) -> None:
        """Test that sync extracts and saves venues from past events."""
        tmp_path, _ = mock_sync_environment

        app = App(args=["-q", "sync"])
        result = app.run()

        assert result == 0

        # Check venues were saved
        config_file = tmp_path / "meetup-scheduler-local.json"
        config_data = json.loads(config_file.read_text())

        assert "venues" in config_data
        # v1 (Venue One), v2 (Venue Two), v3 (Chicago Venue)
        assert len(config_data["venues"]) == 3
        assert "v1" in config_data["venues"]
        assert "v2" in config_data["venues"]
        assert "v3" in config_data["venues"]

        # Verify venue data
        venue_one = config_data["venues"]["v1"]
        assert venue_one["name"] == "Venue One"
        assert venue_one["city"] == "New York"

    def test_sync_saves_last_sync_timestamp(
        self,
        mock_sync_environment: tuple[Path, respx.MockRouter],
    ) -> None:
        """Test that sync saves a lastSync timestamp."""
        tmp_path, _ = mock_sync_environment

        app = App(args=["-q", "sync"])
        result = app.run()

        assert result == 0

        config_file = tmp_path / "meetup-scheduler-local.json"
        config_data = json.loads(config_file.read_text())

        assert "lastSync" in config_data
        # Should be an ISO format timestamp
        assert "T" in config_data["lastSync"]


class TestSyncIntegrationGroupFilter:
    """Test sync with --group filter option."""

    def test_sync_specific_group_only(
        self,
        mock_sync_environment: tuple[Path, respx.MockRouter],
    ) -> None:
        """Test that --group filters to a specific group."""
        tmp_path, _ = mock_sync_environment

        app = App(args=["-q", "sync", "--group", "test-group-one"])
        result = app.run()

        assert result == 0

        # Check only test-group-one was saved
        config_file = tmp_path / "meetup-scheduler-local.json"
        config_data = json.loads(config_file.read_text())

        assert "groups" in config_data
        assert "test-group-one" in config_data["groups"]
        assert "test-group-two" not in config_data["groups"]


class TestSyncIntegrationErrorHandling:
    """Test sync command error handling."""

    def test_sync_not_authenticated_returns_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
    ) -> None:
        """Test that sync returns error when not authenticated."""
        monkeypatch.chdir(tmp_path)

        # Create empty config dir (no credentials)
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        with patch("platformdirs.user_config_dir", return_value=str(config_dir)):
            app = App(args=["sync"])
            result = app.run()

        assert result == 1

    def test_sync_network_error_handling(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
        mock_credentials_data: dict[str, Any],
    ) -> None:
        """Test that sync handles network errors gracefully."""
        monkeypatch.chdir(tmp_path)

        # Set up credentials
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        creds_file = config_dir / "credentials.json"
        creds_file.write_text(json.dumps(mock_credentials_data))

        with (
            patch("platformdirs.user_config_dir", return_value=str(config_dir)),
            respx.mock() as router,
        ):
            # Mock network error
            router.post("https://api.meetup.com/gql").mock(
                side_effect=httpx.RequestError("Connection failed")
            )

            app = App(args=["sync"])
            result = app.run()

        assert result == 1

    def test_sync_api_error_handling(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
        mock_credentials_data: dict[str, Any],
    ) -> None:
        """Test that sync handles API errors gracefully."""
        monkeypatch.chdir(tmp_path)

        # Set up credentials
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        creds_file = config_dir / "credentials.json"
        creds_file.write_text(json.dumps(mock_credentials_data))

        with (
            patch("platformdirs.user_config_dir", return_value=str(config_dir)),
            respx.mock() as router,
        ):
            # Mock API error response
            error_response = {
                "errors": [{"message": "Invalid authentication token"}],
                "data": None,
            }
            router.post("https://api.meetup.com/gql").mock(
                return_value=Response(200, json=error_response)
            )

            app = App(args=["sync"])
            result = app.run()

        assert result == 1

    def test_sync_rate_limit_handling(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
        mock_credentials_data: dict[str, Any],
    ) -> None:
        """Test that sync handles rate limiting."""
        monkeypatch.chdir(tmp_path)

        # Set up credentials
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        creds_file = config_dir / "credentials.json"
        creds_file.write_text(json.dumps(mock_credentials_data))

        with (
            patch("platformdirs.user_config_dir", return_value=str(config_dir)),
            respx.mock() as router,
        ):
            # Mock rate limit response
            error_response = {
                "errors": [
                    {
                        "message": "Too many requests",
                        "extensions": {
                            "code": "RATE_LIMITED",
                            "resetAt": "2025-01-01T00:00:00Z",
                        },
                    }
                ],
                "data": None,
            }
            router.post("https://api.meetup.com/gql").mock(
                return_value=Response(200, json=error_response)
            )

            app = App(args=["sync"])
            result = app.run()

        assert result == 1

    def test_sync_http_error_handling(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
        mock_credentials_data: dict[str, Any],
    ) -> None:
        """Test that sync handles HTTP errors."""
        monkeypatch.chdir(tmp_path)

        # Set up credentials
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        creds_file = config_dir / "credentials.json"
        creds_file.write_text(json.dumps(mock_credentials_data))

        with (
            patch("platformdirs.user_config_dir", return_value=str(config_dir)),
            respx.mock() as router,
        ):
            # Mock 500 error
            router.post("https://api.meetup.com/gql").mock(
                return_value=Response(500, text="Internal Server Error")
            )

            app = App(args=["sync"])
            result = app.run()

        assert result == 1


class TestSyncIntegrationNoGroups:
    """Test sync when user has no organized groups."""

    def test_sync_no_organized_groups_returns_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
        mock_credentials_data: dict[str, Any],
    ) -> None:
        """Test that sync returns error when user has no organized groups."""
        monkeypatch.chdir(tmp_path)

        # Set up credentials
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        creds_file = config_dir / "credentials.json"
        creds_file.write_text(json.dumps(mock_credentials_data))

        with (
            patch("platformdirs.user_config_dir", return_value=str(config_dir)),
            respx.mock() as router,
        ):
            # Mock response with no organizer groups
            no_groups_response: dict[str, Any] = {
                "data": {
                    "self": {
                        "id": "user123",
                        "name": "Test User",
                        "memberships": {
                            "count": 1,
                            "edges": [
                                {
                                    "node": {
                                        "id": "g1",
                                        "name": "Member Only",
                                        "urlname": "member-only",
                                        "timezone": "America/New_York",
                                        "isOrganizer": False,
                                    }
                                }
                            ],
                        },
                    }
                }
            }
            router.post("https://api.meetup.com/gql").mock(
                return_value=Response(200, json=no_groups_response)
            )

            app = App(args=["sync"])
            result = app.run()

        assert result == 1


class TestSyncIntegrationVenueDeduplication:
    """Test that venues are properly deduplicated across groups."""

    def test_sync_deduplicates_venues_across_groups(
        self,
        mock_sync_environment: tuple[Path, respx.MockRouter],
    ) -> None:
        """Test that venues appearing in multiple groups are deduplicated."""
        tmp_path, _ = mock_sync_environment

        # Note: v1 (Venue One) appears in both groups' events

        app = App(args=["-q", "sync"])
        result = app.run()

        assert result == 0

        config_file = tmp_path / "meetup-scheduler-local.json"
        config_data = json.loads(config_file.read_text())

        # Should have exactly 3 unique venues (v1, v2, v3)
        # v1 appears in both groups but should only be stored once
        assert len(config_data["venues"]) == 3

        # Verify v1 exists only once with correct data
        assert config_data["venues"]["v1"]["name"] == "Venue One"
