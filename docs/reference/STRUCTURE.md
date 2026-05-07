# Project Structure

> Last updated: 2026-05-07 (bootstrap, fork @ upstream HEAD `2e7ff6c`)

## Directory Tree

```
Layoutswitcher/
├── CLAUDE.md, PLAN.md, SESSION_RESUME.md, ERRORS.md, HANDOFF.md
├── README.md (from upstream — describes app for end users)
├── LICENSE (MIT)
│
├── docs/
│   ├── reference/         — orchestrator, structure, commands, decisions, invariants, upstream-sync
│   ├── handoffs/          — past per-session boot scripts
│   └── archive/
│       ├── session-resume-history/  — archived session retrospectives
│       └── plan-shipped-phases/     — archived per-session priorities
│
├── src/                   — Python application sources
│   ├── __init__.py
│   ├── main.py                    — entry point (run as `python3 -m src.main`)
│   ├── auto_corrector.py          — orchestrates correction workflow
│   ├── keyboard_monitor.py        — CGEventTap setup, key event capture
│   ├── word_buffer.py             — running buffer of typed chars
│   ├── language_detector.py       — uses pymorphy3 (RU) + EN wordlist to classify
│   ├── layout_mapper.py           — physical-key ↔ char mapping for RU/EN
│   ├── correction_tracker.py      — undo log + daily stats
│   ├── config.py                  — yaml config loader
│   ├── app_filter.py              — excluded-apps logic
│   ├── status_bar.py              — NSStatusItem menu-bar UI
│   ├── settings_window.py         — Cocoa NSWindow settings UI
│   └── onboarding_window.py       — first-run setup wizard
│
├── tests/                 — pytest suite (10 modules, integration + unit)
│   ├── conftest.py
│   ├── test_app_filter.py
│   ├── test_auto_corrector.py
│   ├── test_config.py
│   ├── test_correction_tracker.py
│   ├── test_integration.py
│   ├── test_keyboard_monitor.py
│   ├── test_language_detector.py
│   ├── test_layout_mapper.py
│   └── test_word_buffer.py
│
├── scripts/
│   └── build_wordlist.py          — builds EN wordlist from macOS dict + tech terms
│
├── install.sh             — one-liner installer (curl | bash) for end users
├── setup.sh               — local venv + deps + wordlist build (called by install.sh)
├── requirements.txt       — pyobjc-framework-Quartz, pyobjc-framework-Cocoa, pymorphy3, pyyaml, pytest
├── config.example.yaml    — config template (copied to ~/.config/layout-switcher/config.yaml)
└── com.layout-switcher.plist  — launchd LaunchAgent template (placeholders __VENV_PYTHON__, __SRC_MAIN__, __LOG_DIR__)
```

## Quick-Map: Where Do I Find X?

| What I'm looking for | Where to look |
|---|---|
| Application entry point | `src/main.py` |
| Correction logic (when/how to fix a word) | `src/auto_corrector.py` |
| Keyboard event capture (CGEventTap) | `src/keyboard_monitor.py` |
| Char buffer (what the user just typed) | `src/word_buffer.py` |
| Language detection (RU vs EN classification) | `src/language_detector.py` (uses `pymorphy3` for RU, wordlist for EN) |
| RU↔EN keyboard layout mapping | `src/layout_mapper.py` |
| Undo log + correction history | `src/correction_tracker.py` |
| Per-app exclude logic | `src/app_filter.py` |
| Menu-bar UI | `src/status_bar.py` |
| Settings window | `src/settings_window.py` |
| First-run onboarding | `src/onboarding_window.py` |
| Config loading | `src/config.py` |
| YAML config defaults | `config.example.yaml` |
| User config (per-user, NOT in repo) | `~/.config/layout-switcher/config.yaml` |
| Built wordlist (per-user, NOT in repo) | `~/.config/layout-switcher/wordlist.txt` (or wherever `build_wordlist.py` writes) |
| Logs (when running via launchd) | `__LOG_DIR__` placeholder, typically `~/Library/Logs/layout-switcher/` |
| LaunchAgent plist (installed) | `~/Library/LaunchAgents/com.layout-switcher.plist` |
| Tests | `tests/test_<module>.py` mirroring `src/<module>.py` |

## Runtime layout (when installed)

```
~/.venv-layout-switcher/        OR  $INSTALL_DIR/.venv          — Python virtual environment
~/.config/layout-switcher/
  ├── config.yaml                                                — user-specific config (gitignored, outside repo)
  └── wordlist.txt                                               — built EN wordlist
~/Library/LaunchAgents/
  └── com.layout-switcher.plist                                  — installed LaunchAgent (substituted plist)
~/Library/Logs/layout-switcher/                                  — stdout/stderr from launchd
  ├── stdout.log
  └── stderr.log
```

## Stack at a glance

| Layer | Technology |
|---|---|
| Runtime | Python 3 |
| Keyboard capture | `pyobjc-framework-Quartz` → CGEventTap |
| UI | `pyobjc-framework-Cocoa` → NSStatusItem, NSWindow |
| RU morphology | `pymorphy3` |
| EN dictionary | macOS system dict + tech wordlist (built by `scripts/build_wordlist.py`) |
| Config | YAML via `pyyaml` |
| Tests | `pytest` |
| Process management | `launchd` LaunchAgent |
