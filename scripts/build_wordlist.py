#!/usr/bin/env python3
"""Build English wordlist from macOS system dictionary + common tech terms."""
import sys
from pathlib import Path


def build(dict_path: Path = Path("/usr/share/dict/words"),
          output_path: Path | None = None) -> None:
    if output_path is None:
        output_path = Path(__file__).parent.parent / "data" / "en_wordlist.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    words = set()

    # macOS system dictionary (~236k words)
    if dict_path.exists():
        for line in dict_path.read_text().splitlines():
            word = line.strip().lower()
            if word and word.isalpha():
                words.add(word)
    else:
        print(
            f"WARNING: {dict_path} is missing. The English wordlist will be limited "
            "to ~100 tech terms only — English word detection will be severely degraded.",
            file=sys.stderr,
        )
        print(
            "Fix: install Xcode Command Line Tools (`xcode-select --install`), then re-run.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Common tech terms not in standard dictionaries
    tech_terms = {
        "html", "css", "js", "json", "xml", "api", "url", "http", "https",
        "sql", "npm", "git", "ssh", "tcp", "udp", "dns", "ip", "ftp",
        "cli", "gui", "ide", "sdk", "cdn", "ci", "cd", "qa", "ui", "ux",
        "div", "img", "src", "href", "async", "await", "const", "var", "let",
        "func", "def", "str", "int", "bool", "dict", "list", "tuple",
        "args", "kwargs", "init", "self", "cls", "repr", "iter", "enum",
        "stdin", "stdout", "stderr", "chmod", "chown", "mkdir", "rmdir",
        "grep", "sed", "awk", "curl", "wget", "sudo", "apt", "brew",
        "pytest", "venv", "pip", "conda", "docker", "nginx", "redis",
        "postgres", "mysql", "mongo", "sqlite", "yaml", "toml", "csv",
        "localhost", "webhook", "middleware", "frontend", "backend",
        "fullstack", "devops", "regex", "config", "env", "repo", "diff",
        "merge", "rebase", "stash", "refactor", "debug", "deploy", "prod",
        "dev", "staging", "admin", "auth", "login", "logout", "signup",
        "username", "password", "email", "timestamp", "uuid", "changelog",
    }
    words.update(tech_terms)

    sorted_words = sorted(words)
    output_path.write_text("\n".join(sorted_words) + "\n")
    print(f"Written {len(sorted_words)} words to {output_path}")


if __name__ == "__main__":
    build()
