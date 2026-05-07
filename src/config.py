from pathlib import Path

import yaml


class Config:
    """Loads and manages configuration from YAML file."""

    DEFAULT_PATH = Path.home() / ".config" / "layout-switcher" / "config.yaml"
    DEFAULT_IGNORE_WORDS = ["gg", "ok", "lol", "bb", "wp", "gl", "hf"]

    def __init__(self, path: str | None = None):
        self._path = Path(path) if path else self.DEFAULT_PATH
        self._data = self._load()
        self._observers: list[callable] = []

    def _load(self) -> dict:
        if self._path.exists():
            with open(self._path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    def add_observer(self, callback: callable):
        self._observers.append(callback)

    def _notify_observers(self):
        for cb in self._observers:
            cb()

    @property
    def enabled(self) -> bool:
        return self._data.get("enabled", True)

    @property
    def hotkey(self) -> str:
        return self._data.get("hotkey_convert", "ctrl+shift+space")

    @property
    def excluded_apps(self) -> list[str]:
        return self._data.get("excluded_apps", [])

    @property
    def ignore_words(self) -> list[str]:
        return self._data.get("ignore_words", self.DEFAULT_IGNORE_WORDS)

    @property
    def log_errors(self) -> bool:
        return self._data.get("log_errors", True)

    @property
    def debug(self) -> bool:
        return self._data.get("debug", False)

    @property
    def show_notifications(self) -> bool:
        return self._data.get("show_notifications", False)

    @property
    def launch_at_login(self) -> bool:
        return self._data.get("launch_at_login", False)

    def set_enabled(self, value: bool):
        self._data["enabled"] = value
        self.save()
        self._notify_observers()

    def set_excluded_apps(self, value: list[str]):
        self._data["excluded_apps"] = value
        self.save()
        self._notify_observers()

    def set_ignore_words(self, value: list[str]):
        self._data["ignore_words"] = value
        self.save()
        self._notify_observers()

    def set_show_notifications(self, value: bool):
        self._data["show_notifications"] = value
        self.save()
        self._notify_observers()

    def set_launch_at_login(self, value: bool):
        self._data["launch_at_login"] = value
        self.save()
        self._notify_observers()
