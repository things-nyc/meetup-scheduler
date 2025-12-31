##############################################################################
#
# Name: tokens.py
#
# Function:
#       OAuth token storage and management
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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from meetup_scheduler.config.manager import ConfigManager


class TokenManager:
    """Manages OAuth token storage and automatic refresh.

    Tokens are stored in the credentials.json file via ConfigManager.
    Handles token expiration detection and automatic refresh.
    """

    class Error(Exception):
        """Exception raised for token management errors."""

        pass

    # Buffer before expiration to trigger refresh (5 minutes)
    EXPIRATION_BUFFER_SECONDS = 300

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize the token manager.

        Args:
            config_manager: ConfigManager instance for credential storage.
        """
        self._config_manager = config_manager
        self._oauth_flow: Any = None  # Lazy import to avoid circular dependency

    @property
    def is_authenticated(self) -> bool:
        """Check if valid tokens exist.

        Returns:
            True if we have tokens and they're not expired (or can be refreshed).
        """
        credentials = self._config_manager.load_credentials()

        # Check if we have basic token data
        if not credentials.get("access_token"):
            return False

        # If expired but we have refresh token, we can still authenticate
        if credentials.get("refresh_token"):
            return True

        # No refresh token - check if access token is still valid
        return not self._is_expired(credentials)

    @property
    def has_tokens(self) -> bool:
        """Check if any tokens are stored (may be expired).

        Returns:
            True if credentials file contains token data.
        """
        credentials = self._config_manager.load_credentials()
        return bool(credentials.get("access_token"))

    def get_access_token(self) -> str | None:
        """Get a valid access token, refreshing if necessary.

        Returns:
            Access token string, or None if not authenticated.

        Raises:
            Error: If token refresh fails.
        """
        credentials = self._config_manager.load_credentials()

        if not credentials.get("access_token"):
            return None

        # Check if token needs refresh
        if self._is_expired(credentials):
            if not credentials.get("refresh_token"):
                return None

            # Refresh the tokens
            self._refresh(credentials["refresh_token"])
            credentials = self._config_manager.load_credentials()

        return credentials.get("access_token")

    def save_tokens(self, tokens: dict[str, Any]) -> None:
        """Save tokens from OAuth response.

        Args:
            tokens: Token response from OAuth provider containing:
                - access_token: The access token
                - refresh_token: The refresh token
                - expires_in: Token lifetime in seconds
                - token_type: Token type (usually "bearer")
        """
        # Calculate expiration time
        expires_in = tokens.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc).timestamp() + expires_in

        credentials = {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token", ""),
            "expires_at": expires_at,
            "token_type": tokens.get("token_type", "bearer"),
        }

        self._config_manager.save_credentials(credentials)

    def clear_tokens(self) -> None:
        """Remove all stored tokens."""
        self._config_manager.save_credentials({})

    def _is_expired(self, credentials: dict[str, Any]) -> bool:
        """Check if the access token is expired or expiring soon.

        Args:
            credentials: Credentials dictionary with expires_at field.

        Returns:
            True if token is expired or will expire within buffer time.
        """
        expires_at = credentials.get("expires_at")
        if not expires_at:
            # No expiration time - assume not expired
            return False

        # Check if expired (with buffer)
        now = datetime.now(timezone.utc).timestamp()
        return now >= (expires_at - self.EXPIRATION_BUFFER_SECONDS)

    def _refresh(self, refresh_token: str) -> None:
        """Refresh the access token using the refresh token.

        Args:
            refresh_token: The refresh token.

        Raises:
            Error: If refresh fails.
        """
        # Lazy import to avoid circular dependency
        if self._oauth_flow is None:
            from meetup_scheduler.auth.oauth import OAuthFlow

            self._oauth_flow = OAuthFlow()

        try:
            tokens = self._oauth_flow.refresh_tokens(refresh_token)
            self.save_tokens(tokens)
        except Exception as e:
            raise self.Error(f"Failed to refresh token: {e}") from e
