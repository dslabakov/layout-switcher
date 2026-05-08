class WordBuffer:
    """Buffers keystrokes and detects word boundaries."""

    # QWERTY keys that map to Russian LETTERS on ЙЦУКЕН layout.
    # Without Shift: , → б, . → ю, ' → э, ; → ж, [ → х, ] → ъ, ` → ё
    # With Shift:    ~ → Ё, { → Х, } → Ъ, : → Ж, " → Э, < → Б, > → Ю
    LAYOUT_LETTER_KEYS = frozenset(",.';[]`~{}:" + '"' + "<>")

    # True word boundaries — excludes ALL chars that map to Russian letters.
    # Shift-punctuation that maps to punctuation (? @ # $ ^ &) stays as boundary.
    BOUNDARIES = frozenset(" \n\r!?()/\\|@#$%^&*+-=")

    def __init__(self):
        self._buffer: list[str] = []

    def add_char(self, char: str) -> tuple[str, str] | None:
        """Add a character. Returns (word, boundary_char) if word boundary hit, else None."""
        if char in self.BOUNDARIES:
            word = "".join(self._buffer)
            self._buffer.clear()
            if word:
                return (word, char)
            return None
        self._buffer.append(char)
        return None

    def handle_backspace(self):
        if self._buffer:
            self._buffer.pop()

    def current_word(self) -> str:
        return "".join(self._buffer)

    def clear(self):
        self._buffer.clear()
