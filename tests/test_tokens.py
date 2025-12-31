##############################################################################
#
# Name: test_tokens.py
#
# Function:
#       Unit tests for TokenManager class
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

from meetup_scheduler.auth.tokens import TokenManager
from meetup_scheduler.config.manager import ConfigManager


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    """Create a ConfigManager with temporary directories."""
    manager = ConfigManager(project_dir=tmp_path)
    # Override user config dir to temp directory
    manager._user_config_dir = tmp_path / "config"
    manager._user_config_dir.mkdir(parents=True, exist_ok=True)
    return manager


@pytest.fixture
def token_manager(config_manager: ConfigManager) -> TokenManager:
    """Create a TokenManager instance."""
    return TokenManager(config_manager)


class TestTokenManagerAuthentication:
    """Test TokenManager authentication state."""

    def test_not_authenticated_when_no_tokens(self, token_manager: TokenManager) -> None:
        """Test that is_authenticated is False with no tokens."""
        assert token_manager.is_authenticated is False

    def test_authenticated_with_valid_tokens(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test that is_authenticated is True with valid tokens."""
        # Save tokens that expire in the future
        expires_at = datetime.now(timezone.utc).timestamp() + 3600
        config_manager.save_credentials({
            "access_token": "test_access",
            "refresh_token": "test_refresh",
            "expires_at": expires_at,
        })
        assert token_manager.is_authenticated is True

    def test_authenticated_with_expired_but_refreshable(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test that is_authenticated is True if expired but has refresh token."""
        # Save expired tokens with refresh token
        expires_at = datetime.now(timezone.utc).timestamp() - 3600
        config_manager.save_credentials({
            "access_token": "test_access",
            "refresh_token": "test_refresh",
            "expires_at": expires_at,
        })
        assert token_manager.is_authenticated is True

    def test_not_authenticated_with_expired_no_refresh(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test that is_authenticated is False if expired without refresh token."""
        # Save expired tokens without refresh token
        expires_at = datetime.now(timezone.utc).timestamp() - 3600
        config_manager.save_credentials({
            "access_token": "test_access",
            "expires_at": expires_at,
        })
        assert token_manager.is_authenticated is False


class TestTokenManagerHasTokens:
    """Test TokenManager has_tokens property."""

    def test_has_tokens_false_when_empty(self, token_manager: TokenManager) -> None:
        """Test has_tokens is False when no tokens stored."""
        assert token_manager.has_tokens is False

    def test_has_tokens_true_with_access_token(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test has_tokens is True with access token."""
        config_manager.save_credentials({"access_token": "test"})
        assert token_manager.has_tokens is True

    def test_has_tokens_false_with_empty_access_token(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test has_tokens is False with empty access token."""
        config_manager.save_credentials({"access_token": ""})
        assert token_manager.has_tokens is False


class TestTokenManagerGetAccessToken:
    """Test TokenManager.get_access_token method."""

    def test_returns_none_when_no_tokens(self, token_manager: TokenManager) -> None:
        """Test get_access_token returns None with no tokens."""
        assert token_manager.get_access_token() is None

    def test_returns_token_when_valid(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test get_access_token returns token when valid."""
        expires_at = datetime.now(timezone.utc).timestamp() + 3600
        config_manager.save_credentials({
            "access_token": "valid_token",
            "expires_at": expires_at,
        })
        assert token_manager.get_access_token() == "valid_token"

    def test_refreshes_expired_token(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test get_access_token refreshes expired token."""
        # Save expired tokens
        expires_at = datetime.now(timezone.utc).timestamp() - 3600
        config_manager.save_credentials({
            "access_token": "old_token",
            "refresh_token": "refresh_token",
            "expires_at": expires_at,
        })

        # Mock the OAuthFlow refresh
        mock_oauth = MagicMock()
        mock_oauth.refresh_tokens.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
        }

        with patch.object(token_manager, "_oauth_flow", mock_oauth):
            result = token_manager.get_access_token()

        assert result == "new_token"
        mock_oauth.refresh_tokens.assert_called_once_with("refresh_token")

    def test_returns_none_when_expired_no_refresh(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test get_access_token returns None when expired without refresh."""
        expires_at = datetime.now(timezone.utc).timestamp() - 3600
        config_manager.save_credentials({
            "access_token": "old_token",
            "expires_at": expires_at,
        })
        assert token_manager.get_access_token() is None


class TestTokenManagerSaveTokens:
    """Test TokenManager.save_tokens method."""

    def test_saves_tokens_with_expiration(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test save_tokens stores tokens with calculated expiration."""
        tokens = {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": 3600,
            "token_type": "bearer",
        }
        token_manager.save_tokens(tokens)

        creds = config_manager.load_credentials()
        assert creds["access_token"] == "access"
        assert creds["refresh_token"] == "refresh"
        assert creds["token_type"] == "bearer"
        assert "expires_at" in creds
        # Check expiration is approximately correct (within a few seconds)
        expected = datetime.now(timezone.utc).timestamp() + 3600
        assert abs(creds["expires_at"] - expected) < 5

    def test_saves_with_default_expiration(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test save_tokens uses default expiration if not provided."""
        tokens = {"access_token": "access"}
        token_manager.save_tokens(tokens)

        creds = config_manager.load_credentials()
        # Default is 3600 seconds
        expected = datetime.now(timezone.utc).timestamp() + 3600
        assert abs(creds["expires_at"] - expected) < 5


class TestTokenManagerClearTokens:
    """Test TokenManager.clear_tokens method."""

    def test_clears_all_tokens(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test clear_tokens removes all stored tokens."""
        config_manager.save_credentials({
            "access_token": "access",
            "refresh_token": "refresh",
        })
        assert token_manager.has_tokens is True

        token_manager.clear_tokens()

        assert token_manager.has_tokens is False
        assert config_manager.load_credentials() == {}


class TestTokenManagerExpiration:
    """Test TokenManager expiration detection."""

    def test_token_expiring_soon_triggers_refresh(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test that token expiring within buffer is treated as expired."""
        # Token expires in 100 seconds (less than 5-minute buffer)
        expires_at = datetime.now(timezone.utc).timestamp() + 100
        config_manager.save_credentials({
            "access_token": "about_to_expire",
            "refresh_token": "refresh",
            "expires_at": expires_at,
        })

        # Mock the OAuthFlow refresh
        mock_oauth = MagicMock()
        mock_oauth.refresh_tokens.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
        }

        with patch.object(token_manager, "_oauth_flow", mock_oauth):
            result = token_manager.get_access_token()

        # Should have refreshed
        assert result == "new_token"
        mock_oauth.refresh_tokens.assert_called_once()

    def test_token_not_expiring_soon_no_refresh(
        self, token_manager: TokenManager, config_manager: ConfigManager
    ) -> None:
        """Test that token with time remaining is not refreshed."""
        # Token expires in 1 hour (more than 5-minute buffer)
        expires_at = datetime.now(timezone.utc).timestamp() + 3600
        config_manager.save_credentials({
            "access_token": "valid_token",
            "refresh_token": "refresh",
            "expires_at": expires_at,
        })

        # If refresh was attempted, this would fail
        result = token_manager.get_access_token()
        assert result == "valid_token"
