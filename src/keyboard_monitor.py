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
    kCGEventFlagMaskControl,
    kCGEventFlagMaskShift,
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

    def start(self):
        NSWorkspace.sharedWorkspace().notificationCenter().addObserver_selector_name_object_(
            self, "_appDidActivate:", NSWorkspaceDidActivateApplicationNotification, None
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

    def _appDidActivate_(self, notification):
        self._auto_corrector.invalidate_undo()
        self._word_buffer.clear()

    def _tap_callback(self, proxy, event_type, event, refcon):
        if event_type == kCGEventTapDisabledByTimeout:
            logger.warning("Event tap disabled by timeout, re-enabling...")
            if self._tap:
                CGEventTapEnable(self._tap, True)
            return event

        if event_type == kCGEventLeftMouseDown:
            self._auto_corrector.invalidate_undo()
            self._word_buffer.clear()
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
            self._detection_queue.put(("hotkey", None))
            return None

        if self._is_cursor_move(keycode):
            self._auto_corrector.invalidate_undo()
            self._word_buffer.clear()
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
            self._last_completed_word = (word, boundary)
            if len(word) >= 2 and not self._language_detector.is_ignored(word) and self._could_be_word(word):
                self._detection_queue.put(("check", (word, boundary)))

        return event

    def _detection_worker(self):
        while True:
            action, data = self._detection_queue.get()
            if action == "hotkey":
                self._handle_hotkey()
            elif action == "check":
                word, boundary = data
                # Skip stale corrections — if queue has newer words, this word
                # is no longer adjacent to the cursor, backspaces would hit wrong text.
                if not self._is_stale():
                    self._check_and_correct(word, boundary)
                else:
                    logger.debug("Skipping stale correction for '%s'", word)
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
        if self._auto_corrector.has_undoable_correction():
            self._auto_corrector.undo()
        elif self._last_completed_word is not None:
            word, boundary = self._last_completed_word
            en_version, ru_version = self._layout_mapper.convert_word(word)
            if self._layout_mapper.is_cyrillic(word):
                self._auto_corrector.manual_convert(word, en_version, boundary)
            else:
                self._auto_corrector.manual_convert(word, ru_version, boundary)

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
        ctrl = flags & kCGEventFlagMaskControl
        shift = flags & kCGEventFlagMaskShift
        return bool(ctrl and shift and keycode == SPACE_KEYCODE)

    def _is_cursor_move(self, keycode: int) -> bool:
        return keycode in ARROW_KEYCODES
