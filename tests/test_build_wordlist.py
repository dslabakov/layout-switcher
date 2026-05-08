"""Tests for scripts/build_wordlist.py — warning path when /usr/share/dict/words is absent."""
import sys
from pathlib import Path

import pytest

# Add scripts/ to path so we can import build_wordlist directly.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import build_wordlist


def test_build_wordlist_warns_on_missing_dict(tmp_path, capsys):
    """build() must print a warning to stderr and exit 1 when the dict file is absent."""
    missing = tmp_path / "nonexistent_words"
    # Sanity: the path we pass must not exist.
    assert not missing.exists()

    with pytest.raises(SystemExit) as exc_info:
        build_wordlist.build(dict_path=missing)

    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "English word detection will be severely degraded" in captured.err
    assert "xcode-select --install" in captured.err


def test_build_wordlist_uses_dict_when_present(tmp_path, capsys):
    """build() must incorporate words from the dict file when it exists."""
    sample_words = ["hello", "world", "python", "keyboard"]
    dict_file = tmp_path / "words"
    dict_file.write_text("\n".join(sample_words) + "\n")

    output_file = tmp_path / "wordlist.txt"  # write to tmp, not shared data/

    build_wordlist.build(dict_path=dict_file, output_path=output_file)

    captured = capsys.readouterr()
    assert "WARNING" not in captured.err

    assert output_file.exists()
    content = output_file.read_text()
    for word in sample_words:
        assert word in content, f"Expected '{word}' in wordlist"
