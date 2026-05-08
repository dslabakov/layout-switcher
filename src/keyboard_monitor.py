import threading
import queue
import logging
import time

from Quartz import (
    CGEventTapCreate,
    CGEventTapEnable,
    CGEventGetIntegerValueField,
    CGEventGetFlags,
    CFMachPortCreateRunLoopSource,
    CFRunLoopGetCurrent,
    CFRunLoopAddSource,
    CFRunLoopRun,
    CGEventMaskBit,
    kCGSessionEventTap,
    kCGHeadInsertEventTap,
    kCGEventTapOptionDefault,
    kCGEventKeyDown,
    kCGEventFlagsChanged,
    kCGEventLeftMouseDown,
    kCGKeyboardEventKeycode,
    kCFRunLoopCommonModes,
    kCGEventTapDisabledByTimeout,
    kCGEventTapDisabledByUserInput,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskShift,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskAlternate,
)
from AppKit import (
    NSWorkspace,
    NSWorkspaceDidActivateApplicationNotification,
    NSNotificationCenter,
)
from Foundation import NSOperationQueue, NSUserNotification, NSUserNotificationCenter

from word_buffer import WordBuffer
from layout_mapper import LayoutMapper
from language_detector import LanguageDetector
from auto_corrector import AutoCorrector, SYNTHETIC_MARKER_FIELD, SYNTHETIC_MARKER_VALUE
from app_filter import AppFilter
from config import Config

logger = logging.getLogger("layout-switcher")

SPACE_KEYCODE = 49
BACKSPACE_KEYCODE = 51
ARROW_KEYCODES = frozenset({123, 124, 125, 126})
RETURN_KEYCODE = 36
TAB_KEYCODE = 48

# Mask covering all four real modifier keys — used for exact-match comparison
# in _is_hotkey. Noise bits (NumericPad, NonCoalesced, etc.) are below 0x20000
# and are excluded by this mask, so the test value 0x60104 (ctrl+shift + noise)
# correctly matches ctrl+shift.
_MODIFIER_MASK = (
    kCGEventFlagMaskControl
    | kCGEventFlagMaskShift
    | kCGEventFlagMaskCommand
    | kCGEventFlagMaskAlternate
)

# Virtual keycodes for the US keyboard layout (HIToolbox/Events.h).
# These are physical key positions, not character values.
_KEY_KEYCODES: dict[str, int] = {
    "space": 49,
    "return": 36,
    "tab": 48,
    "escape": 53,
    "a": 0, "s": 1, "d": 2, "f": 3, "g": 5, "h": 4, "j": 38, "k": 40, "l": 37,
    "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "n": 45, "m": 46,
    "q": 12, "w": 13, "e": 14, "r": 15, "t": 17, "y": 16, "u": 32, "i": 34,
    "o": 31, "p": 35,
    "0": 29, "1": 18, "2": 19, "3": 20, "4": 21, "5": 23,
    "6": 22, "7": 26, "8": 28, "9": 25,
}

_MODIFIER_FLAGS: dict[str, int] = {
    "ctrl": kCGEventFlagMaskControl,
    "cmd": kCGEventFlagMaskCommand,
    "command": kCGEventFlagMaskCommand,
    "shift": kCGEventFlagMaskShift,
    "opt": kCGEventFlagMaskAlternate,
    "option": kCGEventFlagMaskAlternate,
    "alt": kCGEventFlagMaskAlternate,
}

_DEFAULT_HOTKEY_SPEC = "ctrl+shift+space"
_DEFAULT_HOTKEY_MODIFIERS = kCGEventFlagMaskControl | kCGEventFlagMaskShift
_DEFAULT_HOTKEY_KEYCODE = SPACE_KEYCODE


def parse_hotkey(spec: str) -> tuple[int, int] | None:
    """Parse a hotkey string like 'ctrl+shift+space' into (modifier_flags, keycode).

    Returns None on any malformed input (no exception raised).

    Rules:
    - Tokens joined by '+'. Whitespace trimmed around each token.
    - Modifiers (case-insensitive): ctrl, cmd/command, shift, opt/option/alt.
    - Key: exactly one non-modifier token mapped via _KEY_KEYCODES.
    - At least one modifier and exactly one key required.
    - Unknown modifiers, unknown keys, two keys, or duplicate modifiers → None.
    """
    if not isinstance(spec, str) or not spec:
        return None

    tokens = [t.strip().lower() for t in spec.split("+")]

    # Reject empty tokens (caused by leading/trailing/double '+')
    if any(t == "" for t in tokens):
        return None

    modifier_flags = 0
    key_tokens: list[str] = []

    for token in tokens:
        if token in _MODIFIER_FLAGS:
            modifier_flags |= _MODIFIER_FLAGS[token]
        elif token in _KEY_KEYCODES:
            key_tokens.append(token)
        else:
            # Unknown token — not a modifier and not a known key
            return None

    if not modifier_flags:
        return None  # No modifier present

    if len(key_tokens) != 1:
        return None  # Zero or multiple keys

    return (modifier_flags, _KEY_KEYCODES[key_tokens[0]])


class KeyboardMonitor:
    """Global keyboard monitor using CGEventTap."""

    def __init__(self, config: Config, tracker=None):
        self._config = config
        self._tracker = tracker
        self._word_buffer = WordBuffer()
        self._layout_mapper = LayoutMapper()
        self._language_detector = LanguageDetector(config)
        self._auto_corrector = AutoCorrector()
        self._app_filter = AppFilter(config)
        self._detection_queue: queue.Queue = queue.Queue()
        self._last_completed_word: tuple[str, str] | None = None
        self._tap = None

        # Parse hotkey_convert from config once at construction time.
        # Hotkey changes require a daemon restart — no live observer.
        hotkey_spec = config.hotkey
        result = parse_hotkey(hotkey_spec)
        if result is None:
            logger.warning(
                "Invalid hotkey_convert %r — falling back to default '%s'",
                hotkey_spec,
                _DEFAULT_HOTKEY_SPEC,
            )
            self._hotkey_modifiers = _DEFAULT_HOTKEY_MODIFIERS
            self._hotkey_keycode = _DEFAULT_HOTKEY_KEYCODE
        else:
            self._hotkey_modifiers, self._hotkey_keycode = result

    def start(self):
        NSOperationQueue.mainQueue().addOperationWithBlock_(
            self._register_app_observer
        )

        worker = threading.Thread(target=self._detection_worker, daemon=True)
        worker.start()

        events = (
            CGEventMaskBit(kCGEventKeyDown)
            | CGEventMaskBit(kCGEventFlagsChanged)
            | CGEventMaskBit(kCGEventLeftMouseDown)
        )
        self._tap = CGEventTapCreate(
            kCGSessionEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
            events, self._tap_callback, None,
        )

        if self._tap is None:
            logger.error("Failed to create event tap.")
            raise RuntimeError("Failed to create CGEventTap")

        source = CFMachPortCreateRunLoopSource(None, self._tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)
        CGEventTapEnable(self._tap, True)
        logger.info("Layout Switcher started.")
        CFRunLoopRun()

    def _register_app_observer(self):
        """Register the NSWorkspace observer. Must be called on the main thread."""
        NSWorkspace.sharedWorkspace().notificationCenter().addObserver_selector_name_object_(
            self, "_appDidActivate:", NSWorkspaceDidActivateApplicationNotification, None
        )

    def _appDidActivate_(self, notification):
        """NSWorkspace observer: app-switch — enqueue clear via worker queue.

        Enqueues a sentinel so the worker thread is the single writer of _word_buffer.
        Also carries the invalidate_undo side-effect (moved from direct call to queue).
        """
        self._detection_queue.put(("clear",))

    def _tap_callback(self, proxy, event_type, event, refcon):
        if event_type in (kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput):
            logger.warning(
                "Event tap disabled (%s), re-enabling...",
                "timeout" if event_type == kCGEventTapDisabledByTimeout else "user input",
            )
            CGEventTapEnable(self._tap, True)
            return event

        try:
            if event_type == kCGEventLeftMouseDown:
                self._auto_corrector.invalidate_undo(reason="mouse-down")
                self._word_buffer.clear(reason="mouse-down")
                return event

            if event_type != kCGEventKeyDown:
                return event

            # Let our own synthetic events (corrections) pass through untouched.
            # Without this, we block our own backspaces and typed characters.
            if CGEventGetIntegerValueField(event, SYNTHETIC_MARKER_FIELD) == SYNTHETIC_MARKER_VALUE:
                return event

            if self._auto_corrector.is_correcting:
                char = self._get_char_from_event(event)
                if char:
                    self._auto_corrector.add_to_replay_buffer(char)
                return None

            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            flags = CGEventGetFlags(event)

            if self._is_hotkey(flags, keycode):
                logger.debug("hotkey detected, enqueuing")
                self._detection_queue.put(("hotkey", None))
                return None

            if self._is_cursor_move(keycode):
                self._auto_corrector.invalidate_undo(reason="cursor-move")
                self._word_buffer.clear(reason="cursor-move")
                return event

            if not self._app_filter.should_process():
                return event

            if keycode == BACKSPACE_KEYCODE:
                self._word_buffer.handle_backspace()
                return event

            char = self._get_char_from_event(event)
            if char is None:
                return event

            result = self._word_buffer.add_char(char)
            if result is not None:
                word, boundary = result
                # Route _last_completed_word update through worker queue so that
                # both writes and reads happen on the worker thread (FRAGILITY 3).
                # Enqueue "complete" unconditionally — before the conditional "check"
                # so worker always sees freshest value when hotkey fires.
                self._detection_queue.put(("complete", (word, boundary)))
                if len(word) >= 2 and not self._language_detector.is_ignored(word) and self._could_be_word(word):
                    self._detection_queue.put(("check", (word, boundary)))

            return event
        except Exception:
            logger.exception("Unhandled exception in _tap_callback")
            return event

    def _handle_queue_item(self, item: tuple) -> bool:
        """Dispatch a single queue item. Returns True if drain should follow, False to skip.

        Handles:
          ("clear",)              — clear word buffer + invalidate undo; no drain.
          ("complete", (w, b))    — update _last_completed_word; no drain (state-update only).
          ("hotkey", None)        — run hotkey handler; drain follows.
          ("check", (word, b))    — run stale check + correction; drain follows.
        """
        msg_type = item[0]
        if msg_type == "clear":
            self._auto_corrector.invalidate_undo(reason="app-switch")
            self._word_buffer.clear(reason="app-switch")
            return False
        if msg_type == "complete":
            self._last_completed_word = item[1]
            return False
        if msg_type == "hotkey":
            self._handle_hotkey()
            return True
        if msg_type == "check":
            word, boundary = item[1]
            # Skip stale corrections — if queue has newer words, this word
            # is no longer adjacent to the cursor, backspaces would hit wrong text.
            if not self._is_stale():
                self._check_and_correct(word, boundary)
            else:
                logger.debug("Skipping stale correction for '%s'", word)
            return True
        return True

    def _detection_worker(self):
        while True:
            item = self._detection_queue.get()
            try:
                should_drain = self._handle_queue_item(item)
                if not should_drain:
                    continue
                # Replay any user keystrokes buffered during correction and
                # feed them back into word_buffer so detection stays in sync.
                replayed = self._auto_corrector.drain_replay_buffer()
                for char in replayed:
                    self._auto_corrector._type_string(char)
                    result = self._word_buffer.add_char(char)
                    if result is not None:
                        rword, rboundary = result
                        self._last_completed_word = (rword, rboundary)
                        if len(rword) >= 2 and not self._language_detector.is_ignored(rword) and self._could_be_word(rword):
                            self._check_and_correct(rword, rboundary)
            except Exception:
                logger.exception("Unhandled exception in _detection_worker")
            finally:
                # finalize_correction is idempotent — calling on every iteration
                # ensures _is_correcting cannot stick True if anything raised mid-cycle.
                # Also runs on continue (no-drain) path — harmless when _is_correcting
                # is already False (no-op flip).
                self._auto_corrector.finalize_correction()

    def _check_and_correct(self, word: str, boundary: str):
        extra = self._word_buffer.current_word()
        logger.debug("_check_and_correct: word=%r boundary=%r", word, boundary)

        # Try full word first
        result = self._try_detect(word)
        if result:
            original, corrected = result
            logger.debug("_check_and_correct: detected correction %r → %r", original, corrected)
            conv_boundary = self._convert_boundary(boundary, word)
            self._auto_corrector.correct(original, corrected, conv_boundary, extra)
            self._notify_correction(original, corrected)
            if self._tracker:
                self._tracker.record(original, corrected)
            return

        # Trailing trimming: if full word fails, strip trailing ambiguous chars
        # (e.g. "ghbdtn," → "приветб" fails → trim "," → "ghbdtn" → "привет")
        trimmed = word
        trailing = ""
        trim_attempts = 0
        while trimmed and trimmed[-1] in WordBuffer.LAYOUT_LETTER_KEYS:
            trailing = trimmed[-1] + trailing
            trimmed = trimmed[:-1]
            trim_attempts += 1
            if len(trimmed) >= 2 and self._could_be_word(trimmed):
                result = self._try_detect(trimmed)
                logger.debug(
                    "_check_and_correct: trim attempt %d: trimmed=%r result=%s",
                    trim_attempts, trimmed, "hit" if result else "miss",
                )
                if result:
                    original, corrected = result
                    # trailing stays as typed (punctuation), boundary gets converted
                    conv_boundary = self._convert_boundary(boundary, trimmed)
                    full_boundary = trailing + conv_boundary
                    self._auto_corrector.correct(original, corrected, full_boundary, extra)
                    self._notify_correction(original, corrected)
                    if self._tracker:
                        self._tracker.record(original, corrected)
                    return

        logger.debug("_check_and_correct: no correction for %r (trim_attempts=%d)", word, trim_attempts)

    def _try_detect(self, word: str) -> tuple[str, str] | None:
        """Try to detect if word needs correction. Returns (original, corrected) or None."""
        en_version, ru_version = self._layout_mapper.convert_word(word)
        if self._layout_mapper.is_cyrillic(word):
            if self._language_detector.check(word, en_version) == "correct":
                return (word, en_version)
        else:
            if self._language_detector.check(word, ru_version) == "correct":
                return (word, ru_version)
        return None

    def _convert_boundary(self, boundary: str, word: str) -> str:
        """Convert boundary char through layout mapper (e.g. '/' → '.')."""
        if self._layout_mapper.is_cyrillic(word):
            return self._layout_mapper.convert(boundary, "ru_to_en")
        else:
            return self._layout_mapper.convert(boundary, "en_to_ru")

    def _handle_hotkey(self):
        has_undoable = self._auto_corrector.has_undoable_correction()
        last_word = self._last_completed_word
        logger.debug("_handle_hotkey: has_undoable=%s, last_completed_word=%r", has_undoable, last_word)
        if has_undoable:
            logger.debug("_handle_hotkey: routing to undo()")
            self._auto_corrector.undo()
        elif last_word is not None:
            word, boundary = last_word
            en_version, ru_version = self._layout_mapper.convert_word(word)
            if self._layout_mapper.is_cyrillic(word):
                logger.debug("_handle_hotkey: routing to manual_convert(%r -> %r), boundary=%r", word, en_version, boundary)
                self._auto_corrector.manual_convert(word, en_version, boundary)
            else:
                logger.debug("_handle_hotkey: routing to manual_convert(%r -> %r), boundary=%r", word, ru_version, boundary)
                self._auto_corrector.manual_convert(word, ru_version, boundary)
        else:
            logger.debug("_handle_hotkey: no undoable, no last_completed_word — no-op")

    def _get_char_from_event(self, event) -> str | None:
        from Quartz import CGEventKeyboardGetUnicodeString
        length, chars = CGEventKeyboardGetUnicodeString(event, 4, None, None)
        if length > 0 and chars:
            return chars[0]
        return None

    def _is_stale(self) -> bool:
        """Return True if detection queue has more items (word is not the latest)."""
        return not self._detection_queue.empty()

    def _notify_correction(self, original: str, corrected: str):
        """Dispatch a correction notification to the main thread if enabled."""
        if not self._config.show_notifications:
            return
        NSOperationQueue.mainQueue().addOperationWithBlock_(
            lambda: self._post_correction_notification(original, corrected)
        )

    def _post_correction_notification(self, original: str, corrected: str):
        """Post a native macOS notification for a completed correction."""
        notification = NSUserNotification.alloc().init()
        notification.setTitle_("Layout Switcher")
        notification.setInformativeText_(f"{original} → {corrected}")
        NSUserNotificationCenter.defaultUserNotificationCenter().deliverNotification_(notification)

    def _could_be_word(self, word: str) -> bool:
        """Check if word could be a real word — letters + layout-mapped chars only."""
        return all(c.isalpha() or c in WordBuffer.LAYOUT_LETTER_KEYS for c in word)

    def _is_hotkey(self, flags: int, keycode: int) -> bool:
        # Exact-match on the four real modifier flags (ignores noise bits like
        # NumericPad or NonCoalesced which sit below 0x20000 and are not in
        # _MODIFIER_MASK). This preserves upstream's semantics while using
        # the configured hotkey instead of a hardcoded one.
        return (flags & _MODIFIER_MASK) == self._hotkey_modifiers and keycode == self._hotkey_keycode

    def _is_cursor_move(self, keycode: int) -> bool:
        return keycode in ARROW_KEYCODES
