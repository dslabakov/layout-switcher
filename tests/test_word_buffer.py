from word_buffer import WordBuffer

# True boundaries — excludes all chars that map to Russian letters (both shift levels)
WORD_BOUNDARIES = {" ", "\n", "\r", "!", "?", "(", ")"}


def test_add_regular_char():
    buf = WordBuffer()
    result = buf.add_char("h")
    assert result is None
    assert buf.current_word() == "h"


def test_word_boundary_returns_word():
    buf = WordBuffer()
    buf.add_char("h")
    buf.add_char("i")
    result = buf.add_char(" ")
    assert result == ("hi", " ")


def test_buffer_cleared_after_boundary():
    buf = WordBuffer()
    buf.add_char("h")
    buf.add_char("i")
    buf.add_char(" ")
    assert buf.current_word() == ""


def test_multiple_words():
    buf = WordBuffer()
    buf.add_char("h")
    buf.add_char("i")
    result1 = buf.add_char(" ")
    buf.add_char("o")
    buf.add_char("k")
    result2 = buf.add_char("\n")
    assert result1 == ("hi", " ")
    assert result2 == ("ok", "\n")


def test_punctuation_is_boundary():
    buf = WordBuffer()
    buf.add_char("h")
    buf.add_char("i")
    result = buf.add_char("!")
    assert result == ("hi", "!")


def test_empty_word_on_consecutive_boundaries():
    buf = WordBuffer()
    buf.add_char(" ")
    result = buf.add_char(" ")
    assert result is None


def test_backspace_removes_last_char():
    buf = WordBuffer()
    buf.add_char("h")
    buf.add_char("e")
    buf.add_char("l")
    buf.handle_backspace()
    assert buf.current_word() == "he"


def test_backspace_on_empty():
    buf = WordBuffer()
    buf.handle_backspace()
    assert buf.current_word() == ""


def test_clear():
    buf = WordBuffer()
    buf.add_char("h")
    buf.add_char("i")
    buf.clear()
    assert buf.current_word() == ""


def test_has_digits_or_special():
    buf = WordBuffer()
    for ch in "abc123":
        buf.add_char(ch)
    result = buf.add_char(" ")
    assert result == ("abc123", " ")


def test_word_with_only_boundaries():
    buf = WordBuffer()
    result = buf.add_char(".")
    assert result is None


# --- Bug fix: layout-mapped chars must NOT be word boundaries ---
# On ЙЦУКЕН layout: , → б, . → ю, ' → э, ; → ж, [ → х, ] → ъ, ` → ё


def test_comma_is_not_boundary():
    """Comma maps to 'б' on ЙЦУКЕН — should NOT split words."""
    buf = WordBuffer()
    for ch in "hf,jnftn":
        buf.add_char(ch)
    result = buf.add_char(" ")
    assert result == ("hf,jnftn", " ")


def test_period_is_not_boundary():
    """Period maps to 'ю' on ЙЦУКЕН — should NOT split words."""
    buf = WordBuffer()
    for ch in "k.,jdm":
        buf.add_char(ch)
    result = buf.add_char(" ")
    assert result == ("k.,jdm", " ")


def test_apostrophe_is_not_boundary():
    """Apostrophe maps to 'э' on ЙЦУКЕН — should NOT split words."""
    buf = WordBuffer()
    for ch in "'nj":
        buf.add_char(ch)
    result = buf.add_char(" ")
    assert result == ("'nj", " ")


def test_semicolon_is_not_boundary():
    """Semicolon maps to 'ж' on ЙЦУКЕН — should NOT split words."""
    buf = WordBuffer()
    for ch in ";bpym":
        buf.add_char(ch)
    result = buf.add_char(" ")
    assert result == (";bpym", " ")


def test_brackets_are_not_boundaries():
    """[ maps to 'х', ] maps to 'ъ' on ЙЦУКЕН."""
    buf = WordBuffer()
    for ch in "[jhjij":
        buf.add_char(ch)
    result = buf.add_char(" ")
    assert result == ("[jhjij", " ")


def test_backtick_is_not_boundary():
    """Backtick maps to 'ё' on ЙЦУКЕН."""
    buf = WordBuffer()
    for ch in "`krf":
        buf.add_char(ch)
    result = buf.add_char(" ")
    assert result == ("`krf", " ")


def test_slash_is_still_boundary():
    """/ maps to '.' (period) on ЙЦУКЕН, not a letter — stays boundary."""
    buf = WordBuffer()
    buf.add_char("a")
    buf.add_char("b")
    result = buf.add_char("/")
    assert result == ("ab", "/")


def test_exclamation_still_boundary():
    """! is not a layout-mapped letter — stays boundary."""
    buf = WordBuffer()
    buf.add_char("a")
    result = buf.add_char("!")
    assert result == ("a", "!")


def test_layout_letter_keys_constant():
    """Verify LAYOUT_LETTER_KEYS contains all 14 layout-mapped chars (both shift levels)."""
    expected = frozenset(",.';[]`~{}:" + '"' + "<>")
    assert WordBuffer.LAYOUT_LETTER_KEYS == expected


# --- Shift-level layout chars ---


def test_shift_chars_not_boundaries():
    """~ { } : \" < > map to Ё Х Ъ Ж Э Б Ю — not boundaries."""
    buf = WordBuffer()
    for ch in "f~b":  # а + ё + и
        buf.add_char(ch)
    result = buf.add_char(" ")
    assert result == ("f~b", " ")

    buf2 = WordBuffer()
    for ch in 'g"h':  # п + э + р
        buf2.add_char(ch)
    result2 = buf2.add_char(" ")
    assert result2 == ('g"h', " ")


def test_question_mark_is_still_boundary():
    """? maps to , (comma punctuation), stays boundary."""
    buf = WordBuffer()
    for ch in "ghbdtn":
        buf.add_char(ch)
    result = buf.add_char("?")
    assert result == ("ghbdtn", "?")


def test_at_sign_is_still_boundary():
    """@ maps to \" (punctuation), stays boundary."""
    buf = WordBuffer()
    buf.add_char("a")
    result = buf.add_char("@")
    assert result == ("a", "@")


def test_tab_does_not_complete_word():
    """Tab is not a word boundary — Cmd+Tab app-switch must not trigger correction.

    Regression guard for the bug where pressing Cmd+Tab after typing a partial word
    caused the daemon to fire correction in the destination app.
    """
    buf = WordBuffer()
    for c in "ghbd":
        result = buf.add_char(c)
        assert result is None
    # Tab should NOT trigger boundary
    result = buf.add_char("\t")
    assert result is None, "Tab must not be a word boundary (would trigger Cmd+Tab false correction)"
    # Real boundary (space) still works — flushes accumulated buffer (ghbd + tab)
    result = buf.add_char(" ")
    assert result is not None
    assert result[0].startswith("ghbd")
