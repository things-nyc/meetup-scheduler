##############################################################################
#
# Name: oauth.py
#
# Function:
#       Meetup OAuth 2.0 Server Flow implementation
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import os
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx


class OAuthFlow:
    """Meetup OAuth 2.0 Server Flow handler.

    Handles the OAuth authorization flow for Meetup API access.
    Uses Server Flow (not PKCE, which Meetup doesn't support).
    """

    # Meetup OAuth endpoints
    AUTHORIZE_URL = "https://secure.meetup.com/oauth2/authorize"
    TOKEN_URL = "https://secure.meetup.com/oauth2/access"

    # Default OAuth credentials (can be overridden via environment)
    # These are placeholder values - real values are set by app developers
    _DEFAULT_CLIENT_ID = ""
    _DEFAULT_CLIENT_SECRET = ""

    class Error(Exception):
        """Exception raised for OAuth errors."""

        pass

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        """Initialize the OAuth flow.

        Args:
            client_id: OAuth client ID. Defaults to environment variable
                MEETUP_CLIENT_ID or built-in default.
            client_secret: OAuth client secret. Defaults to environment variable
                MEETUP_CLIENT_SECRET or built-in default.
        """
        self._client_id = (
            client_id
            or os.environ.get("MEETUP_CLIENT_ID")
            or self._DEFAULT_CLIENT_ID
        )
        self._client_secret = (
            client_secret
            or os.environ.get("MEETUP_CLIENT_SECRET")
            or self._DEFAULT_CLIENT_SECRET
        )

    @property
    def client_id(self) -> str:
        """Return the OAuth client ID."""
        return self._client_id

    @property
    def is_configured(self) -> bool:
        """Check if OAuth credentials are configured.

        Returns:
            True if both client_id and client_secret are set.
        """
        return bool(self._client_id and self._client_secret)

    def generate_state(self) -> str:
        """Generate a random state parameter for CSRF protection.

        Returns:
            URL-safe random string.
        """
        return secrets.token_urlsafe(32)

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        """Build the OAuth authorization URL.

        Args:
            state: Random state parameter for CSRF protection.
            redirect_uri: URI to redirect to after authorization.

        Returns:
            Full authorization URL to open in browser.
        """
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    def exchange_code(
        self, code: str, redirect_uri: str
    ) -> dict[str, Any]:
        """Exchange authorization code for access tokens.

        Args:
            code: Authorization code from OAuth callback.
            redirect_uri: Same redirect URI used in authorization request.

        Returns:
            Token response dictionary containing:
                - access_token: The access token
                - refresh_token: The refresh token
                - expires_in: Token lifetime in seconds
                - token_type: Token type (usually "bearer")

        Raises:
            Error: If token exchange fails.
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }

        try:
            response = httpx.post(
                self.TOKEN_URL,
                data=data,
                headers={"Accept": "application/json"},
                timeout=30.0,
            )
        except httpx.RequestError as e:
            raise self.Error(f"Network error during token exchange: {e}") from e

        if response.status_code != 200:
            self._handle_error_response(response)

        return response.json()

    def refresh_tokens(self, refresh_token: str) -> dict[str, Any]:
        """Refresh access token using refresh token.

        Args:
            refresh_token: The refresh token.

        Returns:
            Token response dictionary (same format as exchange_code).

        Raises:
            Error: If token refresh fails.
        """
        data = {
            "grant_type": "refresh_token",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": refresh_token,
        }

        try:
            response = httpx.post(
                self.TOKEN_URL,
                data=data,
                headers={"Accept": "application/json"},
                timeout=30.0,
            )
        except httpx.RequestError as e:
            raise self.Error(f"Network error during token refresh: {e}") from e

        if response.status_code != 200:
            self._handle_error_response(response)

        return response.json()

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error response from OAuth server.

        Args:
            response: The error response.

        Raises:
            Error: Always raises with appropriate message.
        """
        try:
            error_data = response.json()
            error = error_data.get("error", "unknown_error")
            error_desc = error_data.get("error_description", "Unknown error")
            raise self.Error(f"OAuth error: {error} - {error_desc}")
        except (ValueError, KeyError):
            raise self.Error(
                f"OAuth error: HTTP {response.status_code} - {response.text}"
            ) from None
