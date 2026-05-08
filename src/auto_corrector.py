import time
import threading
from dataclasses import dataclass

from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    CGEventSetIntegerValueField,
    CGEventSourceCreate,
    kCGEventSourceStateHIDSystemState,
    kCGHIDEventTap,
    kCGEventFlagMaskShift,
)


UNDO_TIMEOUT = 10  # seconds

# Marker to identify our synthetic events in the CGEventTap callback.
# Field 42 = kCGEventSourceUserData. We tag all synthetic events so the
# keyboard monitor can let them pass through instead of blocking them.
SYNTHETIC_MARKER_FIELD = 42
SYNTHETIC_MARKER_VALUE = 0x4C53  # "LS" — Layout Switcher

# Minimal delay between individual synthetic events (keep low for speed).
EVENT_DELAY = 0.001  # 1 ms
# Delay between backspace block and typing block (let app process deletions).
BLOCK_DELAY = 0.008  # 8 ms


@dataclass
class CorrectionRecord:
    original: str
    corrected: str
    boundary: str
    timestamp: float

    @property
    def char_count(self) -> int:
        return len(self.original)


BACKSPACE_KEYCODE = 51
RETURN_KEYCODE = 36
SPACE_KEYCODE = 49
TAB_KEYCODE = 48


class AutoCorrector:
    """Simulates keyboard input to correct words via CGEvent."""

    def __init__(self):
        self._last_correction: CorrectionRecord | None = None
        self._is_correcting = False
        self._lock = threading.Lock()
        self._replay_buffer: list[str] = []
        self._source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)

    @property
    def is_correcting(self) -> bool:
        return self._is_correcting

    def has_undoable_correction(self) -> bool:
        if self._last_correction is None:
            return False
        return (time.time() - self._last_correction.timestamp) < UNDO_TIMEOUT

    def invalidate_undo(self):
        self._last_correction = None

    def add_to_replay_buffer(self, char: str):
        """Buffer a keystroke that arrived during correction."""
        self._replay_buffer.append(char)

    def drain_replay_buffer(self) -> list[str]:
        """Return and clear all buffered keystrokes."""
        chars = self._replay_buffer[:]
        self._replay_buffer.clear()
        return chars

    def correct(self, original: str, corrected: str, boundary: str, extra: str = ""):
        """Delete the original word + boundary + extra, type corrected + boundary + extra.

        NOTE: does NOT flip _is_correcting back to False on return. The caller
        (KeyboardMonitor._detection_worker) must call finalize_correction() after
        draining the replay buffer. This keeps _is_correcting True for the entire
        correct-then-drain cycle, closing FRAGILITY 4 (replay race).
        """
        with self._lock:
            self._is_correcting = True
            delete_count = len(original) + len(boundary) + len(extra)
            self._send_backspaces(delete_count)
            time.sleep(BLOCK_DELAY)
            self._type_string(corrected)
            self._type_string(boundary)
            if extra:
                self._type_string(extra)
            self._last_correction = CorrectionRecord(
                original=original,
                corrected=corrected,
                boundary=boundary,
                timestamp=time.time(),
            )

    def undo(self):
        """Undo the last correction.

        NOTE: same deferred-flag contract as correct() — does NOT flip
        _is_correcting back to False. Caller must call finalize_correction()
        after drain (closes the same FRAGILITY 4 race on the undo path).
        """
        if not self.has_undoable_correction():
            return
        rec = self._last_correction
        with self._lock:
            self._is_correcting = True
            delete_count = len(rec.corrected) + len(rec.boundary)
            self._send_backspaces(delete_count)
            time.sleep(BLOCK_DELAY)
            self._type_string(rec.original)
            self._type_string(rec.boundary)
            self._last_correction = None

    def finalize_correction(self):
        """Flip _is_correcting back to False after the caller has drained the replay buffer.

        Idempotent: safe to call when already False (no-op, no exception).
        Must be called unconditionally by the worker after every drain, including
        cases where no correction occurred (flag was never set True) and cases
        where drain returned an empty list.
        """
        with self._lock:
            self._is_correcting = False

    def manual_convert(self, original: str, converted: str, boundary: str):
        """Manually convert last word (triggered by hotkey)."""
        self.correct(original, converted, boundary)

    def _mark_synthetic(self, event):
        """Tag event as ours so the CGEventTap callback lets it through."""
        CGEventSetIntegerValueField(event, SYNTHETIC_MARKER_FIELD, SYNTHETIC_MARKER_VALUE)

    def _send_backspaces(self, count: int):
        for _ in range(count):
            ev_down = CGEventCreateKeyboardEvent(self._source, BACKSPACE_KEYCODE, True)
            ev_up = CGEventCreateKeyboardEvent(self._source, BACKSPACE_KEYCODE, False)
            self._mark_synthetic(ev_down)
            self._mark_synthetic(ev_up)
            CGEventSetFlags(ev_down, 0)
            CGEventSetFlags(ev_up, 0)
            CGEventPost(kCGHIDEventTap, ev_down)
            CGEventPost(kCGHIDEventTap, ev_up)

    def _type_string(self, text: str):
        """Type a string by creating keyboard events with unicode characters."""
        from Quartz import CGEventKeyboardSetUnicodeString
        for char in text:
            ev_down = CGEventCreateKeyboardEvent(self._source, 0, True)
            ev_up = CGEventCreateKeyboardEvent(self._source, 0, False)
            CGEventKeyboardSetUnicodeString(ev_down, len(char), char)
            CGEventKeyboardSetUnicodeString(ev_up, len(char), char)
            self._mark_synthetic(ev_down)
            self._mark_synthetic(ev_up)
            CGEventSetFlags(ev_down, 0)
            CGEventSetFlags(ev_up, 0)
            CGEventPost(kCGHIDEventTap, ev_down)
            CGEventPost(kCGHIDEventTap, ev_up)
