import logging
import pytest
from language_detector import LanguageDetector


@pytest.fixture(scope="module")
def detector():
    return LanguageDetector()


def test_russian_word_valid(detector):
    assert detector.is_russian("привет") is True


def test_russian_inflected_form(detector):
    assert detector.is_russian("делаешь") is True
    assert detector.is_russian("сделали") is True
    assert detector.is_russian("бежавший") is True


def test_russian_nonsense(detector):
    assert detector.is_russian("кпвлд") is False


def test_english_word_valid(detector):
    assert detector.is_english("hello") is True
    assert detector.is_english("world") is True


def test_english_tech_terms(detector):
    assert detector.is_english("html") is True
    assert detector.is_english("json") is True
    assert detector.is_english("pytest") is True


def test_english_nonsense(detector):
    assert detector.is_english("ghbdtn") is False
    assert detector.is_english("xkcd") is False


def test_should_correct_wrong_en_layout(detector):
    # Typed "ghbdtn" in EN layout, meant "привет" in RU
    result = detector.check("ghbdtn", "привет")
    assert result == "correct"


def test_should_keep_valid_english(detector):
    # Typed "hello" in EN layout, maps to "руддщ" in RU
    result = detector.check("hello", "руддщ")
    assert result == "keep"


def test_should_keep_ambiguous(detector):
    result = detector.check("but", "ищт")
    assert result == "keep"


def test_should_keep_unknown(detector):
    result = detector.check("xkcd", "чксв")
    assert result == "keep"


def test_should_correct_wrong_ru_layout(detector):
    # Typed "реьд" in RU layout, meant "html" in EN
    result = detector.check("реьд", "html")
    assert result == "correct"


def test_ignore_words(detector):
    assert detector.is_ignored("gg") is True
    assert detector.is_ignored("ok") is True
    assert detector.is_ignored("hello") is False


def test_reload_ignore_words():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("ignore_words:\n  - custom1\n  - custom2\n")
        f.flush()
        from config import Config
        cfg = Config(path=f.name)
    os.unlink(f.name)
    det = LanguageDetector(config=cfg)
    assert det.is_ignored("custom1") is True
    assert det.is_ignored("custom2") is True
    cfg._data["ignore_words"] = ["newword"]
    det.reload_ignore_words()
    assert det.is_ignored("custom1") is False
    assert det.is_ignored("newword") is True


def test_check_emits_debug_log_at_debug_level(detector, caplog):
    with caplog.at_level(logging.DEBUG, logger="layout-switcher"):
        result = detector.check("ghbdtn", "привет")
    assert result == "correct"
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) >= 1
    record_text = debug_records[0].getMessage()
    assert "ghbdtn" in record_text
    assert "привет" in record_text
    assert "correct" in record_text


def test_check_no_debug_log_at_info_level(detector, caplog):
    with caplog.at_level(logging.INFO, logger="layout-switcher"):
        detector.check("ghbdtn", "привет")
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) == 0
