import logging
from pathlib import Path

import pymorphy3

from config import Config

logger = logging.getLogger("layout-switcher")


class LanguageDetector:
    """Detects whether a word is valid Russian or English."""

    def __init__(self, config: Config | None = None):
        self._config = config or Config()
        self._morph = pymorphy3.MorphAnalyzer()
        self._morph.parse("тест")  # warmup — preload dictionary data
        self._en_words = self._load_english_wordlist()
        self._ignore = set(w.lower() for w in self._config.ignore_words)

    def _load_english_wordlist(self) -> set[str]:
        wordlist_path = Path(__file__).parent.parent / "data" / "en_wordlist.txt"
        if wordlist_path.exists():
            return set(wordlist_path.read_text().splitlines())
        return set()

    def is_russian(self, word: str) -> bool:
        parsed = self._morph.parse(word.lower())
        if not parsed:
            return False
        best = parsed[0]
        # Only trust results that come from the actual dictionary, not guesses
        is_dict_word = type(best.methods_stack[0][0]).__name__ == "DictionaryAnalyzer"
        return is_dict_word and best.tag.POS is not None

    def is_english(self, word: str) -> bool:
        return word.lower() in self._en_words

    def is_ignored(self, word: str) -> bool:
        return word.lower() in self._ignore

    def reload_ignore_words(self):
        self._ignore = set(w.lower() for w in self._config.ignore_words)

    def check(self, original: str, converted: str) -> str:
        """Check if correction is needed.
        Returns 'correct' if should replace, 'keep' if should keep original."""
        orig_is_cyrillic = any("\u0400" <= ch <= "\u04ff" for ch in original)

        if orig_is_cyrillic:
            orig_valid = self.is_russian(original.lower())
            conv_valid = self.is_english(converted.lower())
        else:
            orig_valid = self.is_english(original.lower())
            conv_valid = self.is_russian(converted.lower())

        decision = "correct" if not orig_valid and conv_valid else "keep"
        logger.debug(
            "check(%r, %r): orig_valid=%s conv_valid=%s \u2192 %s",
            original, converted, orig_valid, conv_valid, decision,
        )
        return decision
