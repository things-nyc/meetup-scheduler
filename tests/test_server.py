##############################################################################
#
# Name: test_server.py
#
# Function:
#       Unit tests for CallbackServer class
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import contextlib
import threading
import time
from urllib.request import urlopen

import pytest

from meetup_scheduler.auth.server import CallbackServer


class TestCallbackServerProperties:
    """Test CallbackServer property methods."""

    def test_redirect_uri_default(self) -> None:
        """Test redirect_uri with default host and port."""
        server = CallbackServer()
        assert server.redirect_uri == "http://127.0.0.1:8080/callback"

    def test_redirect_uri_custom_port(self) -> None:
        """Test redirect_uri with custom port."""
        server = CallbackServer(port=9000)
        assert server.redirect_uri == "http://127.0.0.1:9000/callback"

    def test_redirect_uri_custom_host_and_port(self) -> None:
        """Test redirect_uri with custom host and port."""
        server = CallbackServer(host="localhost", port=3000)
        assert server.redirect_uri == "http://localhost:3000/callback"


class TestCallbackServerLifecycle:
    """Test CallbackServer start/stop lifecycle."""

    def test_start_creates_server(self) -> None:
        """Test that start creates the server."""
        server = CallbackServer(port=18080)
        try:
            server.start()
            assert server._server is not None
            assert server._thread is not None
            assert server._thread.is_alive()
        finally:
            server.stop()

    def test_stop_cleans_up(self) -> None:
        """Test that stop cleans up resources."""
        server = CallbackServer(port=18081)
        server.start()
        server.stop()
        assert server._server is None

    def test_double_start_raises(self) -> None:
        """Test that starting twice raises an error."""
        server = CallbackServer(port=18082)
        try:
            server.start()
            with pytest.raises(CallbackServer.Error, match="already running"):
                server.start()
        finally:
            server.stop()

    def test_start_with_port_in_use_raises(self) -> None:
        """Test that starting on a used port raises an error."""
        import sys

        server1 = CallbackServer(port=18083)
        server2 = CallbackServer(port=18083)
        try:
            server1.start()
            # On Windows, port binding behavior may differ (SO_REUSEADDR defaults)
            # So we check that at least one of these scenarios happens:
            # 1. The second server fails to start (expected on most platforms)
            # 2. The second server starts but would conflict on actual use
            try:
                server2.start()
                # If it doesn't raise, we're on Windows with permissive socket options
                # This is okay - the test validates the general mechanism
                if sys.platform != "win32":
                    pytest.fail("Expected port conflict on non-Windows platform")
            except CallbackServer.Error as e:
                assert "Failed to start" in str(e)
        finally:
            server1.stop()
            server2.stop()


class TestCallbackServerCallback:
    """Test CallbackServer callback handling."""

    def test_callback_success(self) -> None:
        """Test successful callback with code and state."""
        server = CallbackServer(port=18084)
        server.start()
        try:
            # Send callback in background thread
            def send_callback() -> None:
                time.sleep(0.1)
                url = "http://127.0.0.1:18084/callback?code=test_code&state=test_state"
                urlopen(url, timeout=5)

            thread = threading.Thread(target=send_callback)
            thread.start()

            code, state = server.wait_for_callback(timeout=5)
            assert code == "test_code"
            assert state == "test_state"
            thread.join()
        finally:
            server.stop()

    def test_callback_without_state(self) -> None:
        """Test callback without state parameter."""
        server = CallbackServer(port=18085)
        server.start()
        try:
            def send_callback() -> None:
                time.sleep(0.1)
                url = "http://127.0.0.1:18085/callback?code=test_code"
                urlopen(url, timeout=5)

            thread = threading.Thread(target=send_callback)
            thread.start()

            code, state = server.wait_for_callback(timeout=5)
            assert code == "test_code"
            assert state == ""
            thread.join()
        finally:
            server.stop()

    def test_callback_timeout(self) -> None:
        """Test callback timeout."""
        server = CallbackServer(port=18086)
        server.start()
        try:
            with pytest.raises(CallbackServer.TimeoutError, match="timed out"):
                server.wait_for_callback(timeout=0.1)
        finally:
            server.stop()

    def test_callback_with_error(self) -> None:
        """Test callback with OAuth error."""
        server = CallbackServer(port=18087)
        server.start()
        try:
            def send_callback() -> None:
                time.sleep(0.1)
                url = "http://127.0.0.1:18087/callback?error=access_denied&error_description=User%20denied"
                with contextlib.suppress(Exception):
                    urlopen(url, timeout=5)

            thread = threading.Thread(target=send_callback)
            thread.start()

            with pytest.raises(CallbackServer.Error, match="access_denied"):
                server.wait_for_callback(timeout=5)
            thread.join()
        finally:
            server.stop()

    def test_callback_missing_code(self) -> None:
        """Test callback without authorization code."""
        server = CallbackServer(port=18088)
        server.start()
        try:
            def send_callback() -> None:
                time.sleep(0.1)
                url = "http://127.0.0.1:18088/callback?state=test"
                with contextlib.suppress(Exception):
                    urlopen(url, timeout=5)

            thread = threading.Thread(target=send_callback)
            thread.start()

            with pytest.raises(CallbackServer.Error, match="No authorization code"):
                server.wait_for_callback(timeout=5)
            thread.join()
        finally:
            server.stop()

    def test_wait_without_start_raises(self) -> None:
        """Test that waiting without starting raises an error."""
        server = CallbackServer(port=18089)
        with pytest.raises(CallbackServer.Error, match="not started"):
            server.wait_for_callback()


class TestCallbackServerRouting:
    """Test CallbackServer path routing."""

    def test_non_callback_path_returns_404(self) -> None:
        """Test that non-callback paths return 404."""
        server = CallbackServer(port=18090)
        server.start()
        try:
            # Request to wrong path should return 404
            try:
                urlopen("http://127.0.0.1:18090/wrong-path", timeout=5)
                pytest.fail("Expected 404 error")
            except Exception as e:
                assert "404" in str(e)
        finally:
            server.stop()
