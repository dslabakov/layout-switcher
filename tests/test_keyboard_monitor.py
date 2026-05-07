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
