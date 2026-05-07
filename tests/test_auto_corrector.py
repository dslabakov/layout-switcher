import time
from auto_corrector import AutoCorrector, CorrectionRecord


def test_correction_record_creation():
    rec = CorrectionRecord(
        original="ghbdtn",
        corrected="привет",
        boundary=" ",
        timestamp=time.time(),
    )
    assert rec.original == "ghbdtn"
    assert rec.corrected == "привет"
    assert rec.char_count == 6


def test_undo_state_valid_within_timeout():
    ac = AutoCorrector()
    ac._last_correction = CorrectionRecord(
        original="ghbdtn",
        corrected="привет",
        boundary=" ",
        timestamp=time.time(),
    )
    assert ac.has_undoable_correction() is True


def test_undo_state_expired():
    ac = AutoCorrector()
    ac._last_correction = CorrectionRecord(
        original="ghbdtn",
        corrected="привет",
        boundary=" ",
        timestamp=time.time() - 15,
    )
    assert ac.has_undoable_correction() is False


def test_invalidate_undo():
    ac = AutoCorrector()
    ac._last_correction = CorrectionRecord(
        original="ghbdtn",
        corrected="привет",
        boundary=" ",
        timestamp=time.time(),
    )
    ac.invalidate_undo()
    assert ac.has_undoable_correction() is False


def test_correcting_flag():
    ac = AutoCorrector()
    assert ac.is_correcting is False


# --- Bug fixes: synthetic markers, delays, extra chars ---


def test_event_delay_constant():
    """Verify EVENT_DELAY constant exists and is reasonable."""
    from auto_corrector import EVENT_DELAY
    assert EVENT_DELAY > 0
    assert EVENT_DELAY < 0.1


def test_synthetic_marker_constants():
    """Verify synthetic event marker constants exist."""
    from auto_corrector import SYNTHETIC_MARKER_FIELD, SYNTHETIC_MARKER_VALUE
    assert SYNTHETIC_MARKER_FIELD == 42
    assert SYNTHETIC_MARKER_VALUE > 0


def test_correct_accepts_extra_param():
    """correct() should accept extra parameter for race condition fix."""
    import inspect
    sig = inspect.signature(AutoCorrector.correct)
    params = list(sig.parameters.keys())
    assert "extra" in params


def test_drain_replay_buffer():
    """drain_replay_buffer() returns and clears buffered chars."""
    ac = AutoCorrector()
    ac.add_to_replay_buffer("a")
    ac.add_to_replay_buffer("b")
    result = ac.drain_replay_buffer()
    assert result == ["a", "b"]
    assert ac.drain_replay_buffer() == []


# --- Fast typing optimizations ---


def test_block_delay_constant():
    """BLOCK_DELAY should exist and be larger than EVENT_DELAY for inter-block pauses."""
    from auto_corrector import BLOCK_DELAY, EVENT_DELAY
    assert BLOCK_DELAY > EVENT_DELAY
    assert BLOCK_DELAY < 0.05  # reasonable upper bound


# ────────────────────────────────────────────────────────────────────────────
# PR-EY: deferred _is_correcting flip — FRAGILITY 4 (replay race)
# ────────────────────────────────────────────────────────────────────────────


def test_correct_leaves_is_correcting_true(monkeypatch):
    """correct() must NOT flip _is_correcting to False — flag stays True for drain cycle.

    New contract (PR-EY): caller must call finalize_correction() after drain.
    """
    ac = AutoCorrector()
    # Stub out the CGEvent calls so correct() doesn't touch real hardware.
    monkeypatch.setattr(ac, "_send_backspaces", lambda n: None)
    monkeypatch.setattr(ac, "_type_string", lambda s: None)
    import auto_corrector as acm
    monkeypatch.setattr(acm, "time", type("T", (), {"sleep": staticmethod(lambda s: None), "time": staticmethod(lambda: 1.0)})())

    ac.correct("ghbdtn", "привет", " ")

    assert ac.is_correcting is True, (
        "correct() must leave _is_correcting=True; caller calls finalize_correction() after drain"
    )


def test_undo_leaves_is_correcting_true(monkeypatch):
    """undo() must NOT flip _is_correcting to False — same deferred contract as correct()."""
    ac = AutoCorrector()
    monkeypatch.setattr(ac, "_send_backspaces", lambda n: None)
    monkeypatch.setattr(ac, "_type_string", lambda s: None)
    import auto_corrector as acm
    monkeypatch.setattr(acm, "time", type("T", (), {"sleep": staticmethod(lambda s: None), "time": staticmethod(lambda: 1.0)})())

    # Seed a correction record so undo() proceeds past the early return.
    ac._last_correction = CorrectionRecord(
        original="ghbdtn",
        corrected="привет",
        boundary=" ",
        timestamp=time.time(),
    )
    ac.undo()

    assert ac.is_correcting is True, (
        "undo() must leave _is_correcting=True; caller calls finalize_correction() after drain"
    )


def test_finalize_correction_flips_flag():
    """finalize_correction() flips _is_correcting from True to False."""
    ac = AutoCorrector()
    ac._is_correcting = True
    ac.finalize_correction()
    assert ac.is_correcting is False


def test_finalize_correction_idempotent():
    """finalize_correction() is a no-op (no exception) when flag is already False."""
    ac = AutoCorrector()
    assert ac.is_correcting is False  # starts False
    ac.finalize_correction()          # must not raise
    assert ac.is_correcting is False


def test_correct_then_finalize_full_cycle(monkeypatch):
    """correct() → finalize_correction() leaves state identical to old correct() contract.

    - _is_correcting is False after finalize.
    - _last_correction is set (undo info intact).
    - replay buffer unchanged.
    """
    ac = AutoCorrector()
    monkeypatch.setattr(ac, "_send_backspaces", lambda n: None)
    monkeypatch.setattr(ac, "_type_string", lambda s: None)
    import auto_corrector as acm
    monkeypatch.setattr(acm, "time", type("T", (), {"sleep": staticmethod(lambda s: None), "time": staticmethod(lambda: 1.0)})())

    ac.add_to_replay_buffer("x")  # pre-existing buffer content

    ac.correct("ghbdtn", "привет", " ")
    ac.finalize_correction()

    assert ac.is_correcting is False
    assert ac._last_correction is not None
    assert ac._last_correction.original == "ghbdtn"
    assert ac._last_correction.corrected == "привет"
    # Replay buffer was NOT touched by correct() or finalize_correction()
    assert ac.drain_replay_buffer() == ["x"]
