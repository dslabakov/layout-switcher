import logging
import queue as q
from unittest.mock import MagicMock, patch
from keyboard_monitor import (
    KeyboardMonitor,
    parse_hotkey,
    _DEFAULT_HOTKEY_MODIFIERS,
    _DEFAULT_HOTKEY_KEYCODE,
)
from Quartz import (
    kCGEventFlagMaskControl,
    kCGEventFlagMaskShift,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskAlternate,
)


def _make_monitor_with_default_hotkey():
    """Build a KeyboardMonitor via __new__ with default hotkey fields pre-set."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._hotkey_modifiers = _DEFAULT_HOTKEY_MODIFIERS
    monitor._hotkey_keycode = _DEFAULT_HOTKEY_KEYCODE
    return monitor


def test_hotkey_detection():
    monitor = _make_monitor_with_default_hotkey()
    ctrl_shift = 0x60104
    assert monitor._is_hotkey(ctrl_shift, 49) is True


def test_hotkey_not_detected_without_modifiers():
    monitor = _make_monitor_with_default_hotkey()
    assert monitor._is_hotkey(0, 49) is False


def test_cursor_moving_keys():
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    assert monitor._is_cursor_move(123) is True
    assert monitor._is_cursor_move(124) is True
    assert monitor._is_cursor_move(125) is True
    assert monitor._is_cursor_move(126) is True
    assert monitor._is_cursor_move(0) is False


# --- Bug fixes: could_be_word, synthetic marker ---


def test_could_be_word_regular():
    """Regular alphabetic words pass the check."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    assert monitor._could_be_word("hello") is True
    assert monitor._could_be_word("ghbdtn") is True


def test_could_be_word_with_layout_chars():
    """Words containing layout-mapped chars (,.';[]`) pass the check."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    assert monitor._could_be_word("hf,jnftn") is True  # работает
    assert monitor._could_be_word("'nj") is True  # это
    assert monitor._could_be_word(";bpym") is True  # жизнь
    assert monitor._could_be_word("[jhjij") is True  # хорошо
    assert monitor._could_be_word("`krf") is True  # ёлка
    assert monitor._could_be_word("k.,jdm") is True  # любовь


def test_could_be_word_rejects_digits():
    """Words with digits should NOT pass."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    assert monitor._could_be_word("abc123") is False


def test_could_be_word_rejects_special_chars():
    """Words with non-layout-mapped special chars should NOT pass."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    assert monitor._could_be_word("hello!") is False
    assert monitor._could_be_word("a@b") is False
    assert monitor._could_be_word("test#") is False


def test_synthetic_marker_in_monitor():
    """SYNTHETIC_MARKER constants available in keyboard_monitor."""
    from keyboard_monitor import SYNTHETIC_MARKER_FIELD, SYNTHETIC_MARKER_VALUE
    assert SYNTHETIC_MARKER_FIELD == 42
    assert SYNTHETIC_MARKER_VALUE > 0


# --- Fast typing optimizations ---


def test_should_skip_stale_correction():
    """_is_stale() should return True when queue has newer items."""
    import queue as q
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._detection_queue = q.Queue()
    # Empty queue — not stale
    assert monitor._is_stale() is False
    # Queue has items — stale
    monitor._detection_queue.put(("check", ("abc", " ")))
    assert monitor._is_stale() is True


# --- Notification feature: show_notifications flag ---


def test_notify_correction_dispatches_when_flag_true():
    """_notify_correction dispatches to main queue when show_notifications=True."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._config = MagicMock(show_notifications=True)
    with patch("keyboard_monitor.NSOperationQueue") as mock_nsopq:
        mock_mq = MagicMock()
        mock_nsopq.mainQueue.return_value = mock_mq
        monitor._notify_correction("ghbdtn", "привет")
        mock_nsopq.mainQueue.assert_called_once()
        mock_mq.addOperationWithBlock_.assert_called_once()


def test_notify_correction_skips_when_flag_false():
    """_notify_correction does NOT dispatch when show_notifications=False."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._config = MagicMock(show_notifications=False)
    with patch("keyboard_monitor.NSOperationQueue") as mock_nsopq:
        monitor._notify_correction("ghbdtn", "привет")
        mock_nsopq.mainQueue.assert_not_called()


def test_post_correction_notification_content():
    """_post_correction_notification sets correct title and body and delivers."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    with patch("keyboard_monitor.NSUserNotification") as mock_notif_cls, \
         patch("keyboard_monitor.NSUserNotificationCenter") as mock_center_cls:
        mock_notif = MagicMock()
        mock_notif_cls.alloc.return_value.init.return_value = mock_notif
        mock_center = MagicMock()
        mock_center_cls.defaultUserNotificationCenter.return_value = mock_center

        monitor._post_correction_notification("ghbdtn", "привет")

        mock_notif.setTitle_.assert_called_once_with("Layout Switcher")
        mock_notif.setInformativeText_.assert_called_once_with("ghbdtn → привет")
        mock_center.deliverNotification_.assert_called_once_with(mock_notif)


# --- Debug logging for _check_and_correct ---


def _make_monitor_for_check():
    """Build a minimal KeyboardMonitor with mocked deps for _check_and_correct tests."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._config = MagicMock(show_notifications=False)
    monitor._tracker = None
    monitor._detection_queue = q.Queue()
    # Mock word_buffer with stable current_word
    monitor._word_buffer = MagicMock()
    monitor._word_buffer.current_word.return_value = ""
    # Mock layout_mapper
    monitor._layout_mapper = MagicMock()
    monitor._layout_mapper.is_cyrillic.return_value = False
    monitor._layout_mapper.convert_word.return_value = ("ghbdtn", "привет")
    monitor._layout_mapper.convert.return_value = " "
    # Mock language detector — will return "correct" to trigger a correction
    monitor._language_detector = MagicMock()
    monitor._language_detector.check.return_value = "correct"
    # Mock auto_corrector
    monitor._auto_corrector = MagicMock()
    return monitor


def test_check_and_correct_emits_debug_at_debug_level(caplog):
    """_check_and_correct emits debug entries when log level is DEBUG."""
    monitor = _make_monitor_for_check()
    with caplog.at_level(logging.DEBUG, logger="layout-switcher"):
        monitor._check_and_correct("ghbdtn", " ")
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) >= 1
    messages = " ".join(r.getMessage() for r in debug_records)
    assert "ghbdtn" in messages


def test_check_and_correct_no_debug_at_info_level(caplog):
    """_check_and_correct emits no debug entries when log level is INFO."""
    monitor = _make_monitor_for_check()
    with caplog.at_level(logging.INFO, logger="layout-switcher"):
        monitor._check_and_correct("ghbdtn", " ")
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) == 0


# ────────────────────────────────────────────────────────────────────────────
# parse_hotkey — valid inputs
# ────────────────────────────────────────────────────────────────────────────

CTRL_SHIFT = kCGEventFlagMaskControl | kCGEventFlagMaskShift
CTRL = kCGEventFlagMaskControl
CMD = kCGEventFlagMaskCommand
ALT = kCGEventFlagMaskAlternate

# Keycode constants (HIToolbox/Events.h virtual key codes)
KC_SPACE = 49
KC_A = 0
KC_ESCAPE = 53
KC_TAB = 48
KC_1 = 18


def test_parse_hotkey_ctrl_shift_space():
    """Standard ctrl+shift+space parses correctly."""
    result = parse_hotkey("ctrl+shift+space")
    assert result == (CTRL_SHIFT, KC_SPACE)


def test_parse_hotkey_modifier_order_does_not_matter():
    """Modifier order (shift+ctrl vs ctrl+shift) produces same flags."""
    assert parse_hotkey("shift+ctrl+space") == parse_hotkey("ctrl+shift+space")


def test_parse_hotkey_case_insensitive():
    """CTRL+SHIFT+SPACE is same as ctrl+shift+space."""
    assert parse_hotkey("CTRL+SHIFT+SPACE") == (CTRL_SHIFT, KC_SPACE)


def test_parse_hotkey_whitespace_around_tokens():
    """Whitespace around tokens is trimmed."""
    assert parse_hotkey("  ctrl + shift + space  ") == (CTRL_SHIFT, KC_SPACE)


def test_parse_hotkey_cmd_a():
    """cmd+a parses to command flag + keycode for 'a'."""
    result = parse_hotkey("cmd+a")
    assert result == (CMD, KC_A)


def test_parse_hotkey_option_escape():
    """option+escape parses to alternate flag + keycode for escape."""
    result = parse_hotkey("option+escape")
    assert result == (ALT, KC_ESCAPE)


def test_parse_hotkey_alt_tab():
    """alt is an alias for option."""
    assert parse_hotkey("alt+tab") == (ALT, KC_TAB)


def test_parse_hotkey_ctrl_1():
    """ctrl+1 parses to control flag + keycode for '1'."""
    result = parse_hotkey("ctrl+1")
    assert result == (CTRL, KC_1)


# ────────────────────────────────────────────────────────────────────────────
# parse_hotkey — invalid inputs (all must return None, no exception)
# ────────────────────────────────────────────────────────────────────────────


def test_parse_hotkey_empty_string():
    assert parse_hotkey("") is None


def test_parse_hotkey_none_input():
    assert parse_hotkey(None) is None


def test_parse_hotkey_no_modifier():
    """A key with no modifier is invalid."""
    assert parse_hotkey("space") is None


def test_parse_hotkey_modifier_only():
    """Modifier alone with no key is invalid."""
    assert parse_hotkey("ctrl") is None


def test_parse_hotkey_trailing_plus():
    """Trailing + creates an empty token → invalid."""
    assert parse_hotkey("ctrl+") is None


def test_parse_hotkey_leading_plus():
    """Leading + creates an empty token → invalid."""
    assert parse_hotkey("+space") is None


def test_parse_hotkey_double_plus():
    """Double + creates an empty token → invalid."""
    assert parse_hotkey("ctrl++space") is None


def test_parse_hotkey_unknown_extra_token():
    """An extra unknown token makes the spec invalid."""
    assert parse_hotkey("ctrl+shift+space+extra") is None


def test_parse_hotkey_unknown_modifier():
    """meta is not a recognized modifier."""
    assert parse_hotkey("meta+space") is None


def test_parse_hotkey_unknown_key():
    """foo is not a recognized key."""
    assert parse_hotkey("ctrl+foo") is None


def test_parse_hotkey_two_keys():
    """Two keys (a and b) with one modifier is invalid."""
    assert parse_hotkey("ctrl+shift+a+b") is None


# ────────────────────────────────────────────────────────────────────────────
# Wiring tests — KeyboardMonitor reads config.hotkey and stores fields
# ────────────────────────────────────────────────────────────────────────────


def _make_config_mock(hotkey_value: str) -> MagicMock:
    """Return a minimal Config mock with the given hotkey value."""
    cfg = MagicMock()
    cfg.hotkey = hotkey_value
    return cfg


def test_keyboard_monitor_init_stores_parsed_hotkey():
    """KeyboardMonitor.__init__ parses config.hotkey and stores the fields."""
    cfg = _make_config_mock("ctrl+a")
    with patch("keyboard_monitor.WordBuffer"), \
         patch("keyboard_monitor.LayoutMapper"), \
         patch("keyboard_monitor.LanguageDetector"), \
         patch("keyboard_monitor.AutoCorrector"), \
         patch("keyboard_monitor.AppFilter"):
        monitor = KeyboardMonitor(cfg)

    assert monitor._hotkey_modifiers == CTRL
    assert monitor._hotkey_keycode == KC_A


def test_keyboard_monitor_init_fallback_on_bad_hotkey(caplog):
    """KeyboardMonitor.__init__ falls back to ctrl+shift+space on bad hotkey and logs warning."""
    cfg = _make_config_mock("garbage")
    with patch("keyboard_monitor.WordBuffer"), \
         patch("keyboard_monitor.LayoutMapper"), \
         patch("keyboard_monitor.LanguageDetector"), \
         patch("keyboard_monitor.AutoCorrector"), \
         patch("keyboard_monitor.AppFilter"), \
         caplog.at_level(logging.WARNING, logger="layout-switcher"):
        monitor = KeyboardMonitor(cfg)

    assert monitor._hotkey_modifiers == _DEFAULT_HOTKEY_MODIFIERS
    assert monitor._hotkey_keycode == _DEFAULT_HOTKEY_KEYCODE
    warning_messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("garbage" in m for m in warning_messages)


# ────────────────────────────────────────────────────────────────────────────
# PR-E: observer main-thread dispatch + queue-based buffer clear
# ────────────────────────────────────────────────────────────────────────────


def test_start_dispatches_observer_registration_to_main_queue():
    """start() dispatches _register_app_observer to the main NSOperationQueue."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._hotkey_modifiers = _DEFAULT_HOTKEY_MODIFIERS
    monitor._hotkey_keycode = _DEFAULT_HOTKEY_KEYCODE
    monitor._detection_queue = q.Queue()

    with patch("keyboard_monitor.NSOperationQueue") as mock_nsopq, \
         patch("keyboard_monitor.threading"), \
         patch("keyboard_monitor.CGEventTapCreate"), \
         patch("keyboard_monitor.CFMachPortCreateRunLoopSource"), \
         patch("keyboard_monitor.CFRunLoopGetCurrent"), \
         patch("keyboard_monitor.CFRunLoopAddSource"), \
         patch("keyboard_monitor.CGEventTapEnable"), \
         patch("keyboard_monitor.CFRunLoopRun"):
        mock_mq = MagicMock()
        mock_nsopq.mainQueue.return_value = mock_mq
        # Prevent RuntimeError from None tap
        import keyboard_monitor as km
        with patch.object(km, "CGEventTapCreate", return_value=MagicMock()):
            monitor.start()

        mock_nsopq.mainQueue.assert_called()
        mock_mq.addOperationWithBlock_.assert_called_once_with(monitor._register_app_observer)


def test_register_app_observer_calls_add_observer():
    """_register_app_observer registers self as NSWorkspace notification observer."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    with patch("keyboard_monitor.NSWorkspace") as mock_ws, \
         patch("keyboard_monitor.NSWorkspaceDidActivateApplicationNotification", new="FakeNotificationName"):
        mock_nc = MagicMock()
        mock_ws.sharedWorkspace.return_value.notificationCenter.return_value = mock_nc

        monitor._register_app_observer()

        mock_nc.addObserver_selector_name_object_.assert_called_once_with(
            monitor,
            "_appDidActivate:",
            "FakeNotificationName",
            None,
        )


def test_app_did_activate_enqueues_clear_sentinel():
    """_appDidActivate_ enqueues ("clear",) and does NOT write _word_buffer directly."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._detection_queue = MagicMock()
    monitor._word_buffer = MagicMock()

    monitor._appDidActivate_(MagicMock())

    monitor._detection_queue.put.assert_called_once_with(("clear",))
    monitor._word_buffer.clear.assert_not_called()


def test_handle_queue_item_clear_calls_invalidate_and_clear():
    """_handle_queue_item(("clear",)) calls invalidate_undo and _word_buffer.clear()."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._word_buffer = MagicMock()
    monitor._auto_corrector = MagicMock()

    should_drain = monitor._handle_queue_item(("clear",))

    monitor._auto_corrector.invalidate_undo.assert_called_once()
    monitor._word_buffer.clear.assert_called_once()
    assert should_drain is False, "_handle_queue_item clear must return False (skip drain)"


def test_handle_queue_item_check_routes_to_check_pipeline():
    """_handle_queue_item(("check", ...)) triggers check-and-correct and returns True."""
    monitor = _make_monitor_for_check()
    monitor._last_completed_word = None

    should_drain = monitor._handle_queue_item(("check", ("ghbdtn", " ")))

    assert should_drain is True
    # check_and_correct should have been called — auto_corrector.correct is the signal
    monitor._auto_corrector.correct.assert_called_once()


# ────────────────────────────────────────────────────────────────────────────
# PR-EX: _last_completed_word routed through worker queue (FRAGILITY 3)
# ────────────────────────────────────────────────────────────────────────────


def test_handle_queue_item_complete_updates_last_completed_word():
    """_handle_queue_item(("complete", ...)) sets _last_completed_word and returns False."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._last_completed_word = None

    should_drain = monitor._handle_queue_item(("complete", ("ghbdtn", "привет")))

    assert monitor._last_completed_word == ("ghbdtn", "привет")
    assert should_drain is False, "complete message must return False (no drain)"


def test_handle_queue_item_complete_overwrites_previous_value():
    """_handle_queue_item(("complete", ...)) overwrites any previous value."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._last_completed_word = ("old_word", "старое")

    monitor._handle_queue_item(("complete", ("ghbdtn", "привет")))

    assert monitor._last_completed_word == ("ghbdtn", "привет")


def _make_monitor_for_tap_callback(word_buffer_result, is_ignored=False):
    """Build a KeyboardMonitor wired for tap-callback tests.

    word_buffer_result: value returned by _word_buffer.add_char (or None)
    is_ignored: whether language_detector.is_ignored returns True
    """
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._detection_queue = MagicMock()
    monitor._auto_corrector = MagicMock()
    monitor._auto_corrector.is_correcting = False
    monitor._word_buffer = MagicMock()
    monitor._word_buffer.add_char.return_value = word_buffer_result
    monitor._app_filter = MagicMock()
    monitor._app_filter.should_process.return_value = True
    monitor._language_detector = MagicMock()
    monitor._language_detector.is_ignored.return_value = is_ignored
    monitor._hotkey_modifiers = _DEFAULT_HOTKEY_MODIFIERS
    monitor._hotkey_keycode = _DEFAULT_HOTKEY_KEYCODE
    monitor._tap = None
    return monitor


def _fire_regular_keydown(monitor, char="a", keycode=65):
    """Fire a simulated regular KeyDown event through _tap_callback.

    Patches CGEventGetIntegerValueField and CGEventGetFlags at the module level
    (both are top-level imports in keyboard_monitor). Mocks _get_char_from_event
    as a method since CGEventKeyboardGetUnicodeString is imported locally inside it.
    """
    import unittest.mock as um
    from keyboard_monitor import SYNTHETIC_MARKER_FIELD

    def gif_side_effect(event, field):
        if field == SYNTHETIC_MARKER_FIELD:
            return 0  # not synthetic
        return keycode  # keycode — must not be hotkey/cursor/backspace

    with patch("keyboard_monitor.CGEventGetIntegerValueField", side_effect=gif_side_effect), \
         patch("keyboard_monitor.CGEventGetFlags", return_value=0), \
         um.patch.object(monitor, "_get_char_from_event", return_value=char):
        monitor._tap_callback(None, 10, MagicMock(), None)  # 10 == kCGEventKeyDown


def test_tap_callback_enqueues_complete_before_check():
    """Tap callback enqueues ("complete", ...) before ("check", ...) when word qualifies."""
    import unittest.mock as um
    monitor = _make_monitor_for_tap_callback(word_buffer_result=("ghbdtn", " "), is_ignored=False)

    _fire_regular_keydown(monitor)

    calls = monitor._detection_queue.put.call_args_list
    assert len(calls) == 2, f"Expected 2 put calls, got {len(calls)}: {calls}"
    assert calls[0] == um.call(("complete", ("ghbdtn", " "))), \
        f"First call must be ('complete', ...), got {calls[0]}"
    assert calls[1] == um.call(("check", ("ghbdtn", " "))), \
        f"Second call must be ('check', ...), got {calls[1]}"


def test_tap_callback_enqueues_complete_even_when_word_fails_filter():
    """Tap callback enqueues ("complete", ...) even when word is too short or ignored."""
    import unittest.mock as um
    # Single char word "a" — fails len >= 2 filter; also is_ignored=True for extra coverage
    monitor = _make_monitor_for_tap_callback(word_buffer_result=("a", " "), is_ignored=True)

    _fire_regular_keydown(monitor)

    calls = monitor._detection_queue.put.call_args_list
    # Only complete — no check (word too short and ignored)
    assert len(calls) == 1, f"Expected 1 put call (only complete), got {len(calls)}: {calls}"
    assert calls[0] == um.call(("complete", ("a", " "))), \
        f"Must be ('complete', ...), got {calls[0]}"


def test_handle_hotkey_reads_last_completed_word_set_by_worker():
    """_handle_hotkey uses _last_completed_word set on the worker thread."""
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._last_completed_word = ("ghbdtn", " ")
    monitor._auto_corrector = MagicMock()
    monitor._auto_corrector.has_undoable_correction.return_value = False
    monitor._layout_mapper = MagicMock()
    monitor._layout_mapper.is_cyrillic.return_value = False
    monitor._layout_mapper.convert_word.return_value = ("ghbdtn", "привет")

    monitor._handle_hotkey()

    monitor._auto_corrector.manual_convert.assert_called_once_with("ghbdtn", "привет", " ")


# ────────────────────────────────────────────────────────────────────────────
# PR-EY: finalize_correction() called unconditionally after drain (FRAGILITY 4)
# ────────────────────────────────────────────────────────────────────────────


def _make_worker_monitor(drain_result=None, correction_triggered=True):
    """Build a minimal KeyboardMonitor for _detection_worker drain-path tests.

    drain_result:           list returned by drain_replay_buffer (default: [])
    correction_triggered:   if True, _handle_queue_item returns True (drain path taken)
    """
    import queue as q
    monitor = KeyboardMonitor.__new__(KeyboardMonitor)
    monitor._detection_queue = q.Queue()
    monitor._auto_corrector = MagicMock()
    monitor._auto_corrector.drain_replay_buffer.return_value = drain_result or []
    monitor._word_buffer = MagicMock()
    monitor._word_buffer.add_char.return_value = None  # no completed word from replay
    monitor._language_detector = MagicMock()
    monitor._last_completed_word = None
    return monitor


def _run_worker_one_item(monitor, item):
    """Feed one item into the worker loop and stop after it processes that item.

    Patches _handle_queue_item so we can control the return value, feeds the
    item via the queue, then runs the worker in a thread with a sentinel to stop.
    """
    import threading
    import queue as q
    from unittest.mock import patch

    results = {}

    original_handle = monitor._handle_queue_item.__func__ if hasattr(monitor._handle_queue_item, '__func__') else None

    # We need to inject a stop mechanism. We'll replace _detection_queue with one
    # that raises after the first item, via a sentinel pattern.
    stop = threading.Event()
    orig_get = monitor._detection_queue.get

    call_count = [0]

    def patched_get():
        result = orig_get()
        call_count[0] += 1
        return result

    monitor._detection_queue.get = patched_get

    # Run the worker in a daemon thread; it will block on the second queue.get()
    monitor._detection_queue.put(item)
    worker_thread = threading.Thread(target=monitor._detection_worker, daemon=True)
    worker_thread.start()
    # Wait for the item to be consumed (finalize_correction should have been called by then)
    import time
    deadline = time.time() + 2.0
    while time.time() < deadline:
        if call_count[0] >= 1:
            break
        time.sleep(0.01)
    # Give the worker a moment to finish the drain + finalize_correction() call
    time.sleep(0.05)
    return worker_thread


def test_worker_calls_finalize_after_drain_with_correction():
    """Worker calls finalize_correction() after drain when a correction occurred.

    Simulates: ("check", ...) → _handle_queue_item returns True → drain → finalize.
    """
    monitor = _make_worker_monitor(drain_result=["a", "b"])

    # Override _handle_queue_item to return True (drain path) for our check item
    call_order = []
    original_drain = monitor._auto_corrector.drain_replay_buffer

    def recording_drain():
        call_order.append("drain")
        return original_drain()

    def recording_finalize():
        call_order.append("finalize")

    monitor._auto_corrector.drain_replay_buffer = recording_drain
    monitor._auto_corrector.finalize_correction = recording_finalize

    # Patch _handle_queue_item to return True without doing real correction logic
    monitor._handle_queue_item = lambda item: True

    _run_worker_one_item(monitor, ("check", ("ghbdtn", " ")))

    assert "drain" in call_order, "drain_replay_buffer must be called"
    assert "finalize" in call_order, "finalize_correction must be called after drain"
    assert call_order.index("drain") < call_order.index("finalize"), \
        "drain must happen before finalize"


def test_worker_calls_finalize_when_drain_empty():
    """Worker calls finalize_correction() even when replay buffer is empty.

    This is the common case: hotkey or check where no keys were typed during correction.
    finalize must be unconditional — not guarded by 'if replayed'.
    """
    monitor = _make_worker_monitor(drain_result=[])  # empty drain

    finalize_called = []
    monitor._auto_corrector.finalize_correction = lambda: finalize_called.append(True)
    monitor._handle_queue_item = lambda item: True  # drain path, no correction

    _run_worker_one_item(monitor, ("hotkey", None))

    assert finalize_called, "finalize_correction must be called even when drain returns []"


def test_worker_skips_finalize_when_should_drain_false():
    """Worker does NOT call finalize_correction() for items that skip drain (e.g. 'clear', 'complete').

    finalize is only appropriate after the drain path. For no-drain items (should_drain=False),
    _is_correcting was never set True and calling finalize is harmless (idempotent), but the
    worker should still exercise the 'continue' branch correctly without calling drain or finalize.
    """
    monitor = _make_worker_monitor(drain_result=[])

    drain_called = []
    finalize_called = []
    monitor._auto_corrector.drain_replay_buffer = lambda: drain_called.append(True) or []
    monitor._auto_corrector.finalize_correction = lambda: finalize_called.append(True)

    # Override _handle_queue_item to return False (no-drain path)
    monitor._handle_queue_item = lambda item: False

    _run_worker_one_item(monitor, ("clear",))

    assert not drain_called, "drain_replay_buffer must NOT be called for no-drain items"
    assert not finalize_called, "finalize_correction must NOT be called for no-drain items"
