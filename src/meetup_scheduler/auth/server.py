##############################################################################
#
# Name: server.py
#
# Function:
#       Local HTTP server for OAuth callback handling
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import html
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


class CallbackServer:
    """Local HTTP server for receiving OAuth callbacks.

    Starts a simple HTTP server on localhost to receive the OAuth redirect
    after the user authenticates with Meetup.
    """

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 8080
    CALLBACK_PATH = "/callback"

    class Error(Exception):
        """Exception raised for callback server errors."""

        pass

    class TimeoutError(Error):
        """Exception raised when callback times out."""

        pass

    def __init__(
        self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT
    ) -> None:
        """Initialize the callback server.

        Args:
            host: Host to bind to (default: 127.0.0.1).
            port: Port to listen on (default: 8080).
        """
        self._host = host
        self._port = port
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._result: dict[str, str] | None = None
        self._error: str | None = None
        self._event = threading.Event()

    @property
    def redirect_uri(self) -> str:
        """Return the redirect URI for OAuth configuration."""
        return f"http://{self._host}:{self._port}{self.CALLBACK_PATH}"

    def start(self) -> None:
        """Start the callback server in a background thread."""
        if self._server is not None:
            raise self.Error("Server already running")

        # Create request handler that captures the callback
        server_instance = self

        class CallbackHandler(BaseHTTPRequestHandler):
            """Handler for OAuth callback requests."""

            def log_message(self, format: str, *args: Any) -> None:
                """Suppress default logging."""
                pass

            def do_GET(self) -> None:  # noqa: N802 -- allow uppercase name; override from BaseHTTPRequestHandler
                """Handle GET request (OAuth callback)."""
                parsed = urlparse(self.path)

                if parsed.path != CallbackServer.CALLBACK_PATH:
                    self.send_error(404, "Not Found")
                    return

                # Parse query parameters
                params = parse_qs(parsed.query)

                # Check for error response from OAuth provider
                if "error" in params:
                    error = params["error"][0]
                    error_desc = params.get("error_description", ["Unknown error"])[0]
                    server_instance._error = f"{error}: {error_desc}"
                    self._send_error_page(error_desc)
                    server_instance._event.set()
                    return

                # Extract code and state
                code = params.get("code", [None])[0]
                state = params.get("state", [None])[0]

                if not code:
                    server_instance._error = "No authorization code received"
                    self._send_error_page("No authorization code received")
                    server_instance._event.set()
                    return

                # Success - store result
                server_instance._result = {"code": code, "state": state or ""}
                self._send_success_page()
                server_instance._event.set()

            def _send_success_page(self) -> None:
                """Send a success HTML page."""
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                html_content = """<!DOCTYPE html>
<html>
<head><title>Authentication Successful</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 50px;">
<h1>&#10003; Authentication Successful</h1>
<p>You can close this window and return to the terminal.</p>
</body>
</html>"""
                self.wfile.write(html_content.encode("utf-8"))

            def _send_error_page(self, message: str) -> None:
                """Send an error HTML page."""
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                safe_message = html.escape(message)
                html_content = f"""<!DOCTYPE html>
<html>
<head><title>Authentication Failed</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 50px;">
<h1>&#10007; Authentication Failed</h1>
<p>{safe_message}</p>
<p>Please close this window and try again.</p>
</body>
</html>"""
                self.wfile.write(html_content.encode("utf-8"))

        # Create and start server
        try:
            self._server = HTTPServer((self._host, self._port), CallbackHandler)
        except OSError as e:
            raise self.Error(f"Failed to start server on {self._host}:{self._port}: {e}") from e

        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def wait_for_callback(self, timeout: float = 300) -> tuple[str, str]:
        """Wait for the OAuth callback.

        Args:
            timeout: Maximum time to wait in seconds (default: 5 minutes).

        Returns:
            Tuple of (authorization_code, state).

        Raises:
            TimeoutError: If callback not received within timeout.
            Error: If callback contains an error.
        """
        if self._server is None:
            raise self.Error("Server not started")

        # Wait for callback
        if not self._event.wait(timeout):
            raise self.TimeoutError(
                f"Authentication timed out after {timeout} seconds. "
                "Please try again."
            )

        # Check for error
        if self._error:
            raise self.Error(self._error)

        # Return result
        if self._result is None:
            raise self.Error("No callback received")

        return self._result["code"], self._result["state"]

    def stop(self) -> None:
        """Stop the callback server."""
        if self._server is not None:
            self._server.shutdown()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
