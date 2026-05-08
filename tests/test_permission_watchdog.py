"""Unit tests for PermissionWatchdog state machine.

NSTimer is NOT instantiated — tests call checkPermissions_(None) directly.
CGPreflight* functions are mocked at the module where they are imported
(permission_watchdog), not at the Quartz package level.
"""
import logging
from unittest.mock import MagicMock, patch

import pytest

from permission_watchdog import PermissionWatchdog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_watchdog(has_listen=True, has_post=True):
    """Build a PermissionWatchdog with mocked status_bar and mocked preflight."""
    status_bar = MagicMock()
    with patch("permission_watchdog.CGPreflightListenEventAccess", return_value=has_listen), \
         patch("permission_watchdog.CGPreflightPostEventAccess", return_value=has_post):
        watchdog = PermissionWatchdog.alloc().initWithStatusBar_interval_(status_bar, 10.0)
    return watchdog, status_bar


def _poll(watchdog, has_listen=True, has_post=True):
    """Drive one watchdog poll with the given permission values."""
    with patch("permission_watchdog.CGPreflightListenEventAccess", return_value=has_listen), \
         patch("permission_watchdog.CGPreflightPostEventAccess", return_value=has_post):
        watchdog.checkPermissions_(None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPermissionWatchdog:

    def test_initial_state_active(self):
        """Both preflight True → watchdog inits in active state, no status-bar calls."""
        watchdog, status_bar = _make_watchdog(has_listen=True, has_post=True)
        assert watchdog._last_state == "active"
        status_bar.set_active.assert_not_called()
        status_bar.set_error.assert_not_called()

    def test_initial_state_error(self):
        """At least one preflight False → watchdog inits in error state, no status-bar calls."""
        watchdog, status_bar = _make_watchdog(has_listen=False, has_post=True)
        assert watchdog._last_state == "error"
        status_bar.set_active.assert_not_called()
        status_bar.set_error.assert_not_called()

    def test_transition_active_to_error(self, caplog):
        """Active → revoke permissions → state becomes error, set_error called, WARNING logged."""
        watchdog, status_bar = _make_watchdog(has_listen=True, has_post=True)

        with caplog.at_level(logging.WARNING, logger="layout-switcher"):
            _poll(watchdog, has_listen=False, has_post=True)

        assert watchdog._last_state == "error"
        status_bar.set_error.assert_called_once()
        status_bar.set_active.assert_not_called()
        assert any("Input Monitoring" in r.message for r in caplog.records)

    def test_transition_error_to_active(self, caplog):
        """Error → restore permissions → state becomes active, set_active called, INFO logged."""
        watchdog, status_bar = _make_watchdog(has_listen=False, has_post=True)

        with caplog.at_level(logging.INFO, logger="layout-switcher"):
            _poll(watchdog, has_listen=True, has_post=True)

        assert watchdog._last_state == "active"
        status_bar.set_active.assert_called_once()
        status_bar.set_error.assert_not_called()
        assert any("restored" in r.message.lower() for r in caplog.records)

    def test_no_log_on_steady_state_active(self, caplog):
        """Active + repeated polls with True, True → no status-bar mutations."""
        watchdog, status_bar = _make_watchdog(has_listen=True, has_post=True)

        with caplog.at_level(logging.DEBUG, logger="layout-switcher"):
            _poll(watchdog, has_listen=True, has_post=True)
            _poll(watchdog, has_listen=True, has_post=True)
            _poll(watchdog, has_listen=True, has_post=True)

        status_bar.set_active.assert_not_called()
        status_bar.set_error.assert_not_called()
        assert len(caplog.records) == 0

    def test_partial_revocation_listen_missing(self, caplog):
        """Accessibility True, Input Monitoring False → error + log identifies Input Monitoring."""
        watchdog, status_bar = _make_watchdog(has_listen=True, has_post=True)

        with caplog.at_level(logging.WARNING, logger="layout-switcher"):
            _poll(watchdog, has_listen=False, has_post=True)

        assert watchdog._last_state == "error"
        status_bar.set_error.assert_called_once()
        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert warning_messages, "Expected at least one WARNING"
        assert any("Input Monitoring" in msg for msg in warning_messages)
        # Accessibility should NOT appear (it's still OK)
        assert not any("Accessibility" in msg for msg in warning_messages)

    def test_partial_revocation_post_missing(self, caplog):
        """Input Monitoring True, Accessibility False → error + log identifies Accessibility."""
        watchdog, status_bar = _make_watchdog(has_listen=True, has_post=True)

        with caplog.at_level(logging.WARNING, logger="layout-switcher"):
            _poll(watchdog, has_listen=True, has_post=False)

        assert watchdog._last_state == "error"
        status_bar.set_error.assert_called_once()
        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert warning_messages, "Expected at least one WARNING"
        assert any("Accessibility" in msg for msg in warning_messages)
        # Input Monitoring should NOT appear (it's still OK)
        assert not any("Input Monitoring" in msg for msg in warning_messages)
