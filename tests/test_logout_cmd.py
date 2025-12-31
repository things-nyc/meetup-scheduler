##############################################################################
#
# Name: test_logout_cmd.py
#
# Function:
#       Unit tests for LogoutCommand class
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
from unittest.mock import patch

import pytest

from meetup_scheduler.app import App


class TestLogoutCommandParsing:
    """Test logout command argument parsing."""

    def test_logout_command_parsed(self) -> None:
        """Test that logout command is parsed."""
        app = App(args=["logout"])
        assert app.args.command == "logout"


class TestLogoutCommandExecution:
    """Test logout command execution."""

    def test_logout_not_logged_in(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test logout when not logged in."""
        monkeypatch.chdir(tmp_path)

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        with patch("platformdirs.user_config_dir", return_value=str(config_dir)):
            app = App(args=["logout"])
            result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "Not currently logged in" in captured.out

    def test_logout_success(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test successful logout."""
        monkeypatch.chdir(tmp_path)

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create credentials file
        expires_at = datetime.now(timezone.utc).timestamp() + 3600
        credentials = {
            "access_token": "test_token",
            "refresh_token": "refresh_token",
            "expires_at": expires_at,
        }
        creds_file = config_dir / "credentials.json"
        creds_file.write_text(json.dumps(credentials))

        with patch("platformdirs.user_config_dir", return_value=str(config_dir)):
            app = App(args=["logout"])
            result = app.run()

        assert result == 0
        captured = capsys.readouterr()
        assert "Successfully logged out" in captured.out

        # Verify credentials were cleared
        assert json.loads(creds_file.read_text()) == {}

    def test_logout_clears_tokens(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that logout clears stored tokens."""
        monkeypatch.chdir(tmp_path)

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create credentials file
        credentials = {
            "access_token": "test_token",
            "refresh_token": "refresh_token",
            "expires_at": 12345678,
            "token_type": "bearer",
        }
        creds_file = config_dir / "credentials.json"
        creds_file.write_text(json.dumps(credentials))

        with patch("platformdirs.user_config_dir", return_value=str(config_dir)):
            app = App(args=["logout"])
            app.run()

        # Verify all token data was removed
        saved = json.loads(creds_file.read_text())
        assert "access_token" not in saved or saved.get("access_token") == ""
        assert saved == {}

    def test_logout_returns_zero(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that logout always returns 0."""
        monkeypatch.chdir(tmp_path)

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        with patch("platformdirs.user_config_dir", return_value=str(config_dir)):
            # Without tokens
            app1 = App(args=["logout"])
            assert app1.run() == 0

            # Create tokens
            creds_file = config_dir / "credentials.json"
            creds_file.write_text('{"access_token": "test"}')

            # With tokens
            app2 = App(args=["logout"])
            assert app2.run() == 0
