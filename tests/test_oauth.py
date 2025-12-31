##############################################################################
#
# Name: test_oauth.py
#
# Function:
#       Unit tests for OAuthFlow class
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

from meetup_scheduler.auth.oauth import OAuthFlow


class TestOAuthFlowConfiguration:
    """Test OAuthFlow configuration."""

    def test_default_credentials_from_environment(self) -> None:
        """Test that credentials are read from environment."""
        with patch.dict(
            "os.environ",
            {"MEETUP_CLIENT_ID": "env_id", "MEETUP_CLIENT_SECRET": "env_secret"},
        ):
            oauth = OAuthFlow()
            assert oauth.client_id == "env_id"
            assert oauth._client_secret == "env_secret"

    def test_explicit_credentials_override_environment(self) -> None:
        """Test that explicit credentials override environment."""
        with patch.dict(
            "os.environ",
            {"MEETUP_CLIENT_ID": "env_id", "MEETUP_CLIENT_SECRET": "env_secret"},
        ):
            oauth = OAuthFlow(client_id="explicit_id", client_secret="explicit_secret")
            assert oauth.client_id == "explicit_id"
            assert oauth._client_secret == "explicit_secret"

    def test_is_configured_true_when_both_set(self) -> None:
        """Test is_configured is True when both credentials are set."""
        oauth = OAuthFlow(client_id="id", client_secret="secret")
        assert oauth.is_configured is True

    def test_is_configured_false_when_client_id_missing(self) -> None:
        """Test is_configured is False when client_id is missing."""
        with patch.dict("os.environ", {}, clear=True):
            oauth = OAuthFlow(client_id="", client_secret="secret")
            assert oauth.is_configured is False

    def test_is_configured_false_when_client_secret_missing(self) -> None:
        """Test is_configured is False when client_secret is missing."""
        with patch.dict("os.environ", {}, clear=True):
            oauth = OAuthFlow(client_id="id", client_secret="")
            assert oauth.is_configured is False


class TestOAuthFlowState:
    """Test OAuthFlow state generation."""

    def test_generate_state_returns_string(self) -> None:
        """Test that generate_state returns a string."""
        oauth = OAuthFlow(client_id="id", client_secret="secret")
        state = oauth.generate_state()
        assert isinstance(state, str)
        assert len(state) > 20  # Should be a reasonably long random string

    def test_generate_state_is_unique(self) -> None:
        """Test that generate_state returns unique values."""
        oauth = OAuthFlow(client_id="id", client_secret="secret")
        states = {oauth.generate_state() for _ in range(100)}
        assert len(states) == 100  # All should be unique


class TestOAuthFlowAuthorizeUrl:
    """Test OAuthFlow.get_authorize_url method."""

    def test_authorize_url_contains_required_params(self) -> None:
        """Test that authorize URL contains all required parameters."""
        oauth = OAuthFlow(client_id="test_client", client_secret="secret")
        url = oauth.get_authorize_url(
            state="test_state", redirect_uri="http://localhost:8080/callback"
        )

        assert "secure.meetup.com/oauth2/authorize" in url
        assert "client_id=test_client" in url
        assert "response_type=code" in url
        assert "state=test_state" in url
        assert "redirect_uri=http" in url

    def test_authorize_url_encodes_redirect_uri(self) -> None:
        """Test that redirect URI is properly encoded."""
        oauth = OAuthFlow(client_id="id", client_secret="secret")
        url = oauth.get_authorize_url(
            state="state", redirect_uri="http://127.0.0.1:8080/callback"
        )
        # Colon and slashes should be encoded
        assert "redirect_uri=http%3A%2F%2F127.0.0.1%3A8080%2Fcallback" in url


class TestOAuthFlowExchangeCode:
    """Test OAuthFlow.exchange_code method."""

    def test_exchange_code_success(self) -> None:
        """Test successful code exchange."""
        oauth = OAuthFlow(client_id="id", client_secret="secret")

        # Create mock response
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "access_123",
            "refresh_token": "refresh_456",
            "expires_in": 3600,
            "token_type": "bearer",
        }

        with patch("httpx.post", return_value=mock_response):
            tokens = oauth.exchange_code(
                code="auth_code", redirect_uri="http://localhost:8080/callback"
            )

        assert tokens["access_token"] == "access_123"
        assert tokens["refresh_token"] == "refresh_456"
        assert tokens["expires_in"] == 3600

    def test_exchange_code_oauth_error(self) -> None:
        """Test code exchange with OAuth error response."""
        oauth = OAuthFlow(client_id="id", client_secret="secret")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Authorization code expired",
        }

        with (
            patch("httpx.post", return_value=mock_response),
            pytest.raises(OAuthFlow.Error, match="invalid_grant"),
        ):
            oauth.exchange_code(
                code="expired_code", redirect_uri="http://localhost:8080/callback"
            )

    def test_exchange_code_network_error(self) -> None:
        """Test code exchange with network error."""
        oauth = OAuthFlow(client_id="id", client_secret="secret")

        with (
            patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")),
            pytest.raises(OAuthFlow.Error, match="Network error"),
        ):
            oauth.exchange_code(
                code="code", redirect_uri="http://localhost:8080/callback"
            )

    def test_exchange_code_non_json_error(self) -> None:
        """Test code exchange with non-JSON error response."""
        oauth = OAuthFlow(client_id="id", client_secret="secret")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.text = "Internal Server Error"

        with (
            patch("httpx.post", return_value=mock_response),
            pytest.raises(OAuthFlow.Error, match="HTTP 500"),
        ):
            oauth.exchange_code(
                code="code", redirect_uri="http://localhost:8080/callback"
            )


class TestOAuthFlowRefreshTokens:
    """Test OAuthFlow.refresh_tokens method."""

    def test_refresh_tokens_success(self) -> None:
        """Test successful token refresh."""
        oauth = OAuthFlow(client_id="id", client_secret="secret")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
            "token_type": "bearer",
        }

        with patch("httpx.post", return_value=mock_response):
            tokens = oauth.refresh_tokens(refresh_token="old_refresh")

        assert tokens["access_token"] == "new_access"
        assert tokens["refresh_token"] == "new_refresh"

    def test_refresh_tokens_invalid_token(self) -> None:
        """Test refresh with invalid token."""
        oauth = OAuthFlow(client_id="id", client_secret="secret")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Refresh token is invalid",
        }

        with (
            patch("httpx.post", return_value=mock_response),
            pytest.raises(OAuthFlow.Error, match="invalid_grant"),
        ):
            oauth.refresh_tokens(refresh_token="invalid_token")

    def test_refresh_tokens_network_error(self) -> None:
        """Test refresh with network error."""
        oauth = OAuthFlow(client_id="id", client_secret="secret")

        with (
            patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")),
            pytest.raises(OAuthFlow.Error, match="Network error"),
        ):
            oauth.refresh_tokens(refresh_token="token")
