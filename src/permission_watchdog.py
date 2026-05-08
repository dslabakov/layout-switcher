"""Periodic watchdog that polls CGPreflight* and updates the status-bar icon."""
import logging

import objc
from Foundation import NSObject, NSTimer
from Quartz import CGPreflightListenEventAccess, CGPreflightPostEventAccess

logger = logging.getLogger("layout-switcher")

_STATE_ACTIVE = "active"
_STATE_ERROR = "error"


def _preflight_state():
    """Return (state, has_listen, has_post) from current OS check."""
    has_listen = CGPreflightListenEventAccess()
    has_post = CGPreflightPostEventAccess()
    state = _STATE_ACTIVE if (has_listen and has_post) else _STATE_ERROR
    return state, has_listen, has_post


class PermissionWatchdog(NSObject):
    """Polls Accessibility/Input-Monitoring permissions every *interval* seconds.

    Must be started from the main thread so that the NSTimer attaches to the
    main runloop (which is driven by NSApplication / AppHelper.runEventLoop).
    """

    def initWithStatusBar_interval_(self, status_bar, interval):
        self = objc.super(PermissionWatchdog, self).init()
        if self is None:
            return None
        self._status_bar = status_bar
        self._interval = interval
        self._timer = None
        # Capture initial state without triggering any status-bar mutation —
        # main.py already set the icon before handing off to us.
        initial_state, _, _ = _preflight_state()
        self._last_state = initial_state
        return self

    def start(self):
        """Schedule the repeating NSTimer on the calling (main) thread's runloop."""
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            self._interval,
            self,
            b"checkPermissions:",
            None,
            True,
        )

    def stop(self):
        """Invalidate the timer; safe to call even if never started."""
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None

    @objc.typedSelector(b"v@:@")
    def checkPermissions_(self, timer):
        """NSTimer selector — fires on main thread every *interval* seconds."""
        new_state, has_listen, has_post = _preflight_state()

        if new_state == self._last_state:
            # Steady state — no action needed.
            return

        if new_state == _STATE_ERROR:
            missing = []
            if not has_listen:
                missing.append("Input Monitoring (listen)")
            if not has_post:
                missing.append("Accessibility (post)")
            logger.warning(
                "Permissions revoked: %s", ", ".join(missing)
            )
            self._status_bar.set_error()
        else:
            logger.info("Permissions restored — resuming active state.")
            self._status_bar.set_active()

        self._last_state = new_state
