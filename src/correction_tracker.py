import json
import logging
import os
import threading
from collections import deque
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_STATS_PATH = os.path.expanduser("~/.config/layout-switcher/stats.json")


@dataclass
class CorrectionEvent:
    original: str
    corrected: str
    timestamp: datetime


class CorrectionTracker:
    """Thread-safe correction event tracker with persistent daily count."""

    def __init__(self, stats_path: str | None = None):
        self._lock = threading.Lock()
        self._stats_path = Path(stats_path) if stats_path else Path(_DEFAULT_STATS_PATH)
        self._today_count: int = 0
        self._today_date: date = date.today()
        self._recent: deque[CorrectionEvent] = deque(maxlen=10)
        self._load()

    def _load(self) -> None:
        """Read persisted stats from disk; silently start fresh on any problem."""
        if not self._stats_path.exists():
            return

        try:
            with open(self._stats_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("stats.json malformed or unreadable (%s): %s — starting fresh", self._stats_path, exc)
            return

        if not isinstance(data, dict):
            logger.warning("stats.json has unexpected format (%s) — starting fresh", self._stats_path)
            return

        count = data.get("count")
        saved_date_str = data.get("date")

        if not isinstance(count, int) or not isinstance(saved_date_str, str):
            logger.warning(
                "stats.json missing or wrong-typed keys (%s) — starting fresh", self._stats_path
            )
            return

        try:
            saved_date = date.fromisoformat(saved_date_str)
        except ValueError:
            logger.warning("stats.json has invalid date value %r (%s) — starting fresh", saved_date_str, self._stats_path)
            return

        today = date.today()
        if saved_date == today:
            self._today_count = count
            self._today_date = today

    def _persist(self) -> None:
        """Write count + date atomically to disk. Must be called while holding _lock."""
        tmp_path = self._stats_path.with_suffix(".json.tmp")
        try:
            self._stats_path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump({"count": self._today_count, "date": self._today_date.isoformat()}, fh)
            os.replace(tmp_path, self._stats_path)
        except OSError as exc:
            logger.warning("Failed to persist stats to %s: %s", self._stats_path, exc)

    def record(self, original: str, corrected: str):
        with self._lock:
            self._check_date_rollover()
            self._today_count += 1
            self._recent.append(CorrectionEvent(original, corrected, datetime.now()))
            self._persist()

    @property
    def today_count(self) -> int:
        with self._lock:
            self._check_date_rollover()
            return self._today_count

    @property
    def recent(self) -> list[CorrectionEvent]:
        with self._lock:
            return list(self._recent)

    def _check_date_rollover(self):
        today = date.today()
        if today != self._today_date:
            self._today_count = 0
            self._today_date = today
