import logging

from AppKit import NSWorkspace

from config import Config

logger = logging.getLogger("layout-switcher")


class AppFilter:
    """Checks if the active application is in the exclusion list."""

    def __init__(self, config: Config):
        self._config = config

    def get_active_app(self) -> str:
        """Returns the name of the currently active application."""
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return app.localizedName() if app else ""

    def is_excluded(self, app_name: str) -> bool:
        excluded = set(name.lower() for name in self._config.excluded_apps)
        return app_name.lower() in excluded

    def should_process(self) -> bool:
        app_name = self.get_active_app()
        result = not self.is_excluded(app_name)
        logger.debug("app_filter.should_process: app=%r allowed=%s", app_name, result)
        return result
