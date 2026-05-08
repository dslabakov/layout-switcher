#!/usr/bin/env python3
"""Layout Switcher — auto-detect and correct wrong keyboard layout."""
import argparse
import logging
import sys
import threading
from pathlib import Path

import objc
from AppKit import NSApplication, NSApp, NSApplicationActivationPolicyAccessory
from Foundation import NSObject
from PyObjCTools import AppHelper
from Quartz import CGPreflightListenEventAccess, CGPreflightPostEventAccess

from config import Config
from correction_tracker import CorrectionTracker
from keyboard_monitor import KeyboardMonitor
from onboarding_window import OnboardingWindow, onboarding_done
from settings_window import get_settings_window
from permission_watchdog import PermissionWatchdog
from status_bar import StatusBar


class AppDelegate(NSObject):
    def applicationWillTerminate_(self, notification):
        logging.getLogger("layout-switcher").info("Layout Switcher stopped.")


def setup_logging(config: Config, debug: bool = False):
    log_dir = Path.home() / ".config" / "layout-switcher"
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers = [logging.StreamHandler()]
    if config.log_errors:
        handlers.append(logging.FileHandler(log_dir / "layout-switcher.log"))
    level = logging.DEBUG if (debug or config.debug) else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def main():
    parser = argparse.ArgumentParser(description="Layout Switcher daemon")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args, _ = parser.parse_known_args()

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    config = Config()
    setup_logging(config, debug=args.debug)
    logger = logging.getLogger("layout-switcher")

    tracker = CorrectionTracker()

    # Check permissions
    has_listen = CGPreflightListenEventAccess()
    has_post = CGPreflightPostEventAccess()

    # Show onboarding on first launch
    if not onboarding_done():
        onboarding = OnboardingWindow.alloc().init()
        onboarding.run_modal()
        has_listen = CGPreflightListenEventAccess()
        has_post = CGPreflightPostEventAccess()

    # Create settings window (lazy singleton)
    settings = get_settings_window(config)

    # Create status bar
    status_bar = StatusBar.alloc().initWithConfig_tracker_(config, tracker)
    status_bar.set_settings_callback(settings.show)

    # Start monitor only if permissions are granted
    if has_listen and has_post:
        monitor = KeyboardMonitor(config, tracker)

        # Register LanguageDetector reload on config change
        config.add_observer(monitor._language_detector.reload_ignore_words)

        monitor_thread = threading.Thread(target=monitor.start, daemon=True)
        monitor_thread.start()
        status_bar.set_active()
        logger.info("Layout Switcher started with full permissions.")
    else:
        status_bar.set_error()
        logger.warning("Permissions missing, monitor not started.")

    # Start permission watchdog (NSTimer on main thread)
    watchdog = PermissionWatchdog.alloc().initWithStatusBar_interval_(status_bar, 10.0)
    watchdog.start()

    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
