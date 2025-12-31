##############################################################################
#
# Name: test_sync_cmd.py
#
# Function:
#       Unit tests for SyncCommand class
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
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from meetup_scheduler.app import App


@pytest.fixture
def mock_oauth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up mock OAuth environment variables."""
    monkeypatch.setenv("MEETUP_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("MEETUP_CLIENT_SECRET", "test_client_secret")


@pytest.fixture
def mock_credentials(tmp_path: Path) -> Path:
    """Create mock credentials file."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    expires_at = datetime.now(timezone.utc).timestamp() + 3600
    credentials = {
        "access_token": "valid_token",
        "refresh_token": "refresh_token",
        "expires_at": expires_at,
    }

    creds_file = config_dir / "credentials.json"
    creds_file.write_text(json.dumps(credentials))

    return config_dir


class TestSyncCommandParsing:
    """Test sync command argument parsing."""

    def test_sync_command_parsed(self) -> None:
        """Test that sync command is parsed."""
        app = App(args=["sync"])
        assert app.args.command == "sync"

    def test_sync_group_option(self) -> None:
        """Test sync --group option."""
        app = App(args=["sync", "--group", "test-group"])
        assert app.args.group == "test-group"

    def test_sync_years_option(self) -> None:
        """Test sync --years option."""
        app = App(args=["sync", "--years", "3"])
        assert app.args.years == 3

    def test_sync_years_default(self) -> None:
        """Test sync --years default is 2."""
        app = App(args=["sync"])
        assert app.args.years == 2

    def test_sync_venues_only_option(self) -> None:
        """Test sync --venues-only option."""
        app = App(args=["sync", "--venues-only"], _testing=True)
        assert app.args.venues_only is True


class TestSyncCommandNotAuthenticated:
    """Test sync when not authenticated."""

    def test_not_authenticated_returns_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
    ) -> None:
        """Test that sync returns error when not authenticated."""
        monkeypatch.chdir(tmp_path)

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        with patch("platformdirs.user_config_dir", return_value=str(config_dir)):
            app = App(args=["sync"])
            result = app.run()

        assert result == 1


class TestSyncCommandSuccess:
    """Test sync command success scenarios."""

    def test_sync_fetches_groups_and_venues(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
        mock_credentials: Path,
    ) -> None:
        """Test that sync fetches groups and venues."""
        monkeypatch.chdir(tmp_path)

        # Create mock Meetup client
        mock_client_class = MagicMock()
        mock_client = mock_client_class.return_value

        # Mock get_organized_groups
        mock_client.get_organized_groups.return_value = [
            {
                "id": "g1",
                "name": "Test Group",
                "urlname": "test-group",
                "timezone": "America/New_York",
            }
        ]

        # Mock get_past_events
        mock_client.get_past_events.return_value = [
            {
                "id": "e1",
                "title": "Event 1",
                "venue": {"id": "v1", "name": "Venue 1", "city": "NYC"},
            }
        ]

        # Mock extract_venues
        mock_client.extract_venues.return_value = [
            {"id": "v1", "name": "Venue 1", "city": "NYC"}
        ]

        with (
            patch("platformdirs.user_config_dir", return_value=str(mock_credentials)),
            patch(
                "meetup_scheduler.commands.sync_cmd.MeetupClient",
                mock_client_class,
            ),
        ):
            app = App(args=["-q", "sync"])
            result = app.run()

        assert result == 0
        mock_client.get_organized_groups.assert_called_once()
        mock_client.get_past_events.assert_called()
        mock_client.extract_venues.assert_called()

    def test_sync_saves_groups_to_config(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
        mock_credentials: Path,
    ) -> None:
        """Test that sync saves groups to project config."""
        monkeypatch.chdir(tmp_path)

        # Create mock Meetup client
        mock_client_class = MagicMock()
        mock_client = mock_client_class.return_value

        mock_client.get_organized_groups.return_value = [
            {
                "id": "g1",
                "name": "Test Group",
                "urlname": "test-group",
                "timezone": "America/New_York",
            }
        ]
        mock_client.get_past_events.return_value = []
        mock_client.extract_venues.return_value = []

        with (
            patch("platformdirs.user_config_dir", return_value=str(mock_credentials)),
            patch(
                "meetup_scheduler.commands.sync_cmd.MeetupClient",
                mock_client_class,
            ),
        ):
            app = App(args=["-q", "sync"])
            result = app.run()

        assert result == 0

        # Check that project config was saved
        project_config = tmp_path / "meetup-scheduler-local.json"
        if project_config.exists():
            config_data = json.loads(project_config.read_text())
            assert "groups" in config_data
            assert "test-group" in config_data["groups"]


class TestSyncCommandSpecificGroup:
    """Test sync with specific group option."""

    def test_sync_specific_group(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
        mock_credentials: Path,
    ) -> None:
        """Test that sync filters to specific group."""
        monkeypatch.chdir(tmp_path)

        # Create mock Meetup client
        mock_client_class = MagicMock()
        mock_client = mock_client_class.return_value

        mock_client.get_organized_groups.return_value = [
            {"id": "g1", "name": "Group 1", "urlname": "group-1", "timezone": "UTC"},
            {"id": "g2", "name": "Group 2", "urlname": "group-2", "timezone": "UTC"},
        ]
        mock_client.get_past_events.return_value = []
        mock_client.extract_venues.return_value = []

        with (
            patch("platformdirs.user_config_dir", return_value=str(mock_credentials)),
            patch(
                "meetup_scheduler.commands.sync_cmd.MeetupClient",
                mock_client_class,
            ),
        ):
            app = App(args=["-q", "sync", "--group", "group-1"])
            result = app.run()

        assert result == 0
        # Should only call get_past_events for group-1
        calls = mock_client.get_past_events.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == "group-1"


class TestSyncCommandNoGroups:
    """Test sync when no groups are found."""

    def test_sync_no_organized_groups(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
        mock_credentials: Path,
    ) -> None:
        """Test that sync returns error when no organized groups."""
        monkeypatch.chdir(tmp_path)

        # Create mock Meetup client
        mock_client_class = MagicMock()
        mock_client = mock_client_class.return_value
        mock_client.get_organized_groups.return_value = []

        with (
            patch("platformdirs.user_config_dir", return_value=str(mock_credentials)),
            patch(
                "meetup_scheduler.commands.sync_cmd.MeetupClient",
                mock_client_class,
            ),
        ):
            app = App(args=["sync"])
            result = app.run()

        assert result == 1
