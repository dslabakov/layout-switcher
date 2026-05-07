import json
import os
import time
import threading
from datetime import date, datetime
from correction_tracker import CorrectionTracker, CorrectionEvent


# ---------------------------------------------------------------------------
# Existing tests — updated to pass tmp_path so they don't touch real config
# ---------------------------------------------------------------------------

def test_initial_state(tmp_path):
    tracker = CorrectionTracker(stats_path=str(tmp_path / "stats.json"))
    assert tracker.today_count == 0
    assert tracker.recent == []


def test_record_increments_count(tmp_path):
    tracker = CorrectionTracker(stats_path=str(tmp_path / "stats.json"))
    tracker.record("ghbdtn", "привет")
    assert tracker.today_count == 1
    tracker.record("реьд", "html")
    assert tracker.today_count == 2


def test_recent_stores_events(tmp_path):
    tracker = CorrectionTracker(stats_path=str(tmp_path / "stats.json"))
    tracker.record("ghbdtn", "привет")
    recent = tracker.recent
    assert len(recent) == 1
    assert recent[0].original == "ghbdtn"
    assert recent[0].corrected == "привет"
    assert isinstance(recent[0].timestamp, datetime)


def test_recent_max_10(tmp_path):
    tracker = CorrectionTracker(stats_path=str(tmp_path / "stats.json"))
    for i in range(15):
        tracker.record(f"word{i}", f"слово{i}")
    assert len(tracker.recent) == 10
    assert tracker.recent[0].original == "word5"
    assert tracker.recent[-1].original == "word14"


def test_date_rollover_resets_count(tmp_path):
    tracker = CorrectionTracker(stats_path=str(tmp_path / "stats.json"))
    tracker.record("test", "тест")
    assert tracker.today_count == 1
    tracker._today_date = date(2020, 1, 1)
    assert tracker.today_count == 0


def test_thread_safety(tmp_path):
    tracker = CorrectionTracker(stats_path=str(tmp_path / "stats.json"))
    errors = []

    def writer():
        try:
            for i in range(100):
                tracker.record(f"w{i}", f"с{i}")
        except Exception as e:
            errors.append(e)

    def reader():
        try:
            for _ in range(100):
                _ = tracker.today_count
                _ = tracker.recent
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer) for _ in range(3)]
    threads += [threading.Thread(target=reader) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert tracker.today_count == 300


# ---------------------------------------------------------------------------
# New persistence tests
# ---------------------------------------------------------------------------

def test_fresh_no_file_count_zero(tmp_path):
    """No stats.json → count starts at 0."""
    tracker = CorrectionTracker(stats_path=str(tmp_path / "stats.json"))
    assert tracker.today_count == 0


def test_first_record_creates_file(tmp_path):
    """First record() creates stats.json with count=1."""
    stats_file = tmp_path / "stats.json"
    tracker = CorrectionTracker(stats_path=str(stats_file))
    tracker.record("ghbdtn", "привет")
    assert stats_file.exists()
    data = json.loads(stats_file.read_text())
    assert data["count"] == 1
    assert data["date"] == date.today().isoformat()


def test_loads_existing_today_stats(tmp_path):
    """File with today's date and count=5 → tracker loads count=5."""
    stats_file = tmp_path / "stats.json"
    stats_file.write_text(json.dumps({"count": 5, "date": date.today().isoformat()}))
    tracker = CorrectionTracker(stats_path=str(stats_file))
    assert tracker.today_count == 5


def test_loads_and_increments(tmp_path):
    """Loaded count=5, then record() → count=6 on disk."""
    stats_file = tmp_path / "stats.json"
    stats_file.write_text(json.dumps({"count": 5, "date": date.today().isoformat()}))
    tracker = CorrectionTracker(stats_path=str(stats_file))
    tracker.record("test", "тест")
    assert tracker.today_count == 6
    data = json.loads(stats_file.read_text())
    assert data["count"] == 6


def test_date_rollover_on_read_resets(tmp_path):
    """File with yesterday's date → tracker resets to count=0."""
    from datetime import timedelta
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    stats_file = tmp_path / "stats.json"
    stats_file.write_text(json.dumps({"count": 5, "date": yesterday}))
    tracker = CorrectionTracker(stats_path=str(stats_file))
    assert tracker.today_count == 0


def test_malformed_json_logs_warning_and_resets(tmp_path, caplog):
    """Malformed JSON → warning logged, count=0."""
    import logging
    stats_file = tmp_path / "stats.json"
    stats_file.write_text("not valid json {{{")
    with caplog.at_level(logging.WARNING, logger="correction_tracker"):
        tracker = CorrectionTracker(stats_path=str(stats_file))
    assert tracker.today_count == 0
    assert any("malformed" in rec.message.lower() or "starting fresh" in rec.message.lower()
               for rec in caplog.records)


def test_missing_keys_logs_warning_and_resets(tmp_path, caplog):
    """Empty dict {} → warning logged, count=0."""
    import logging
    stats_file = tmp_path / "stats.json"
    stats_file.write_text(json.dumps({}))
    with caplog.at_level(logging.WARNING, logger="correction_tracker"):
        tracker = CorrectionTracker(stats_path=str(stats_file))
    assert tracker.today_count == 0
    assert any("starting fresh" in rec.message.lower() for rec in caplog.records)


def test_partial_keys_logs_warning_and_resets(tmp_path, caplog):
    """Dict with only count, missing date → warning logged, count=0."""
    import logging
    stats_file = tmp_path / "stats.json"
    stats_file.write_text(json.dumps({"count": 5}))
    with caplog.at_level(logging.WARNING, logger="correction_tracker"):
        tracker = CorrectionTracker(stats_path=str(stats_file))
    assert tracker.today_count == 0
    assert any("starting fresh" in rec.message.lower() for rec in caplog.records)


def test_wrong_types_logs_warning_and_resets(tmp_path, caplog):
    """count is string not int → warning logged, count=0."""
    import logging
    stats_file = tmp_path / "stats.json"
    stats_file.write_text(json.dumps({"count": "five", "date": date.today().isoformat()}))
    with caplog.at_level(logging.WARNING, logger="correction_tracker"):
        tracker = CorrectionTracker(stats_path=str(stats_file))
    assert tracker.today_count == 0
    assert any("starting fresh" in rec.message.lower() for rec in caplog.records)


def test_no_tmp_file_lingers_after_record(tmp_path):
    """After record(), stats.json.tmp must not exist (atomic rename succeeded)."""
    stats_file = tmp_path / "stats.json"
    tracker = CorrectionTracker(stats_path=str(stats_file))
    tracker.record("ghbdtn", "привет")
    tmp_file = tmp_path / "stats.json.tmp"
    assert not tmp_file.exists()


def test_io_error_on_write_does_not_crash(tmp_path, monkeypatch, caplog):
    """os.replace raises OSError → record() still completes, count incremented in memory, warning logged."""
    import logging
    stats_file = tmp_path / "stats.json"
    tracker = CorrectionTracker(stats_path=str(stats_file))

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with caplog.at_level(logging.WARNING, logger="correction_tracker"):
        tracker.record("ghbdtn", "привет")  # must not raise

    assert tracker.today_count == 1  # in-memory count still updated
    assert any("Failed to persist" in rec.message or "disk full" in rec.message
               for rec in caplog.records)
