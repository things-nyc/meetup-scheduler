##############################################################################
#
# Name: test_login_cmd.py
#
# Function:
#       Unit tests for LoginCommand class
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
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from meetup_scheduler.app import App


@pytest.fixture
def mock_oauth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up mock OAuth environment variables."""
    monkeypatch.setenv("MEETUP_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("MEETUP_CLIENT_SECRET", "test_client_secret")


class TestLoginCommandParsing:
    """Test login command argument parsing."""

    def test_login_command_parsed(self) -> None:
        """Test that login command is parsed."""
        app = App(args=["login"])
        assert app.args.command == "login"

    def test_login_port_option(self) -> None:
        """Test login --port option."""
        app = App(args=["login", "--port", "9000"])
        assert app.args.port == 9000

    def test_login_port_default(self) -> None:
        """Test login port default is 8080."""
        app = App(args=["login"])
        assert app.args.port == 8080


class TestLoginCommandAlreadyAuthenticated:
    """Test login when already authenticated."""

    def test_already_authenticated_returns_zero(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        mock_oauth_env: None,
    ) -> None:
        """Test that login returns 0 when already authenticated."""
        monkeypatch.chdir(tmp_path)

        # Create credentials file with valid tokens
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Set up app with mocked config dir
        with patch(
            "platformdirs.user_config_dir", return_value=str(config_dir)
        ):
            app = App(args=["login"])

            # Create valid credentials
            expires_at = datetime.now(timezone.utc).timestamp() + 3600
            credentials = {
                "access_token": "valid_token",
                "refresh_token": "refresh_token",
                "expires_at": expires_at,
            }
            import json

            creds_file = config_dir / "credentials.json"
            creds_file.write_text(json.dumps(credentials))

            result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "Already authenticated" in captured.out


class TestLoginCommandNotConfigured:
    """Test login when OAuth is not configured."""

    def test_not_configured_returns_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that login returns error when OAuth not configured."""
        monkeypatch.chdir(tmp_path)
        # Clear any OAuth environment variables
        monkeypatch.delenv("MEETUP_CLIENT_ID", raising=False)
        monkeypatch.delenv("MEETUP_CLIENT_SECRET", raising=False)

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        with patch(
            "platformdirs.user_config_dir", return_value=str(config_dir)
        ):
            app = App(args=["login"])
            result = app.run()

        assert result == 1


class TestLoginCommandFlow:
    """Test login command OAuth flow."""

    def test_login_success_flow(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        mock_oauth_env: None,
    ) -> None:
        """Test successful login flow."""
        monkeypatch.chdir(tmp_path)

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Mock the OAuth components
        mock_server = MagicMock()
        mock_server.redirect_uri = "http://127.0.0.1:8080/callback"
        mock_server.wait_for_callback.return_value = ("auth_code", "test_state")

        with (
            patch("platformdirs.user_config_dir", return_value=str(config_dir)),
            patch(
                "meetup_scheduler.commands.login_cmd.CallbackServer",
                return_value=mock_server,
            ),
            patch(
                "meetup_scheduler.commands.login_cmd.OAuthFlow"
            ) as mock_oauth_class,
            patch("webbrowser.open", return_value=True) as mock_browser,
        ):
            mock_oauth = mock_oauth_class.return_value
            mock_oauth.is_configured = True
            mock_oauth.generate_state.return_value = "test_state"
            mock_oauth.get_authorize_url.return_value = "https://meetup.com/oauth"
            mock_oauth.exchange_code.return_value = {
                "access_token": "access_token",
                "refresh_token": "refresh_token",
                "expires_in": 3600,
            }

            app = App(args=["login"])
            result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "Successfully authenticated" in captured.out

        # Verify browser was opened
        mock_browser.assert_called_once()

        # Verify server was started and stopped
        mock_server.start.assert_called_once()
        mock_server.stop.assert_called_once()

    def test_login_state_mismatch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
    ) -> None:
        """Test that login fails on state mismatch."""
        monkeypatch.chdir(tmp_path)

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        mock_server = MagicMock()
        mock_server.redirect_uri = "http://127.0.0.1:8080/callback"
        # Return mismatched state
        mock_server.wait_for_callback.return_value = ("auth_code", "wrong_state")

        with (
            patch("platformdirs.user_config_dir", return_value=str(config_dir)),
            patch(
                "meetup_scheduler.commands.login_cmd.CallbackServer",
                return_value=mock_server,
            ),
            patch(
                "meetup_scheduler.commands.login_cmd.OAuthFlow"
            ) as mock_oauth_class,
            patch("webbrowser.open", return_value=True),
        ):
            mock_oauth = mock_oauth_class.return_value
            mock_oauth.is_configured = True
            mock_oauth.generate_state.return_value = "correct_state"
            mock_oauth.get_authorize_url.return_value = "https://meetup.com/oauth"

            app = App(args=["login"])
            result = app.run()

        assert result == 1

    def test_login_server_port_option(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_oauth_env: None,
    ) -> None:
        """Test that custom port is passed to server."""
        monkeypatch.chdir(tmp_path)

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        mock_server = MagicMock()
        mock_server.redirect_uri = "http://127.0.0.1:9000/callback"
        mock_server.wait_for_callback.return_value = ("code", "state")

        with (
            patch("platformdirs.user_config_dir", return_value=str(config_dir)),
            patch(
                "meetup_scheduler.commands.login_cmd.CallbackServer",
                return_value=mock_server,
            ) as mock_server_class,
            patch(
                "meetup_scheduler.commands.login_cmd.OAuthFlow"
            ) as mock_oauth_class,
            patch("webbrowser.open", return_value=True),
        ):
            mock_oauth = mock_oauth_class.return_value
            mock_oauth.is_configured = True
            mock_oauth.generate_state.return_value = "state"
            mock_oauth.get_authorize_url.return_value = "https://meetup.com/oauth"
            mock_oauth.exchange_code.return_value = {
                "access_token": "token",
                "expires_in": 3600,
            }

            app = App(args=["login", "--port", "9000"])
            app.run()

        # Verify port was passed to server
        mock_server_class.assert_called_once_with(port=9000)
