# Handoff — session 2 end (archived 2026-05-08)

> Original boot script written at end of session 2 (2026-05-07), used to start session 3.
> Archived verbatim by `/save` at the end of session 3.

## Status

**Session 2 complete (2026-05-07).** Daemon operational on native arm64 python.org Python 3.14.4 after a three-layer permission saga (`E-0001`). Audit done. Two new invariants in place. Ready for first feature delegation.

## Read first

1. `CLAUDE.md` — project description + orchestrator-only mode + ARCHITECTURAL INVARIANTS now contains INV-001/INV-002.
2. `SESSION_RESUME.md` — current state + carry-overs.
3. `PLAN.md` → "Next Session — Start Here" — pick first feature.
4. `docs/audits/upstream-2026-05-07.md` — code map + bug list + feature candidates. Recommends `show_notifications` wiring.

## Delta (since session 1 / bootstrap end)

- Native arm64 python.org Python 3.14.4 at `/Library/Frameworks/Python.framework/Versions/3.14/`. venv recreated against it with `arch -arm64`.
- TCC grants for daemon now target **`bin/python3.14`** (CLI binary), NOT `Python.app` — INV-002.
- `ERRORS.md` E-0001 — full diagnostic trail (Rosetta + stale TCC entries + responsible-process attribution).
- `docs/reference/INVARIANTS.md` § INV-001, INV-002.
- `docs/reference/DECISIONS.md` 2026-05-07 entry (stay on Python; no `.app` rebuild / Swift pivot).
- `.venv-old-x86` backup directory in repo working tree (not committed; rollback insurance for a few days).
- Memory: `~/.claude/projects/.../memory/feedback_diagnostic_agent_destructive_commands.md` — every diagnostic agent prompt touching macOS system state needs explicit "do not run" block.

## How to start session 3

1. `git status` — should be clean. Daemon should already be running (`launchctl print gui/$(id -u)/com.layout-switcher` → `state = running`). If not, `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.layout-switcher.plist`.
2. Sanity probe: `tail -5 ~/.config/layout-switcher/layout-switcher.log` should show "started with full permissions" not "Permissions missing".
3. Read audit's "Recommended first delegation" section. Default: wire `show_notifications`.
4. `git checkout -b feature/notifications` (or whichever scope you pick from `PLAN.md` Active backlog).
5. Delegate to Sonnet in worktree: read `keyboard_monitor.py` post-correction path + how `config.show_notifications` is consumed (currently nothing) + add NSUserNotification call. Tests for the new path.

## Known traps

- **NEVER recreate the venv with default `pip install`** — Claude Code's Bash session is x86_64; pip will pull x86_64 wheels for `pyobjc-core` and reintroduce Rosetta. Always: `arch -arm64 .venv/bin/python3 -m pip install ...`. Sanity check: `arch -arm64 .venv/bin/python3 -c 'import platform; print(platform.machine())'` should print `arm64`. INV-001.
- **NEVER re-sign Python.app or change Python interpreter** without expecting to re-grant TCC. Each fresh codesign / interpreter switch creates a new TCC identity. Old grants accumulate as stale entries; fresh grant required. (`tccutil reset Accessibility|ListenEvent|PostEvent org.python.python` printing "Successfully reset" >1 time per service is the smoking-gun signal.)
- **NEVER grant Accessibility/Input Monitoring to `Python.app`** — must be the CLI `bin/python3.14`. INV-002. macOS TCC attributes to the responsible process (first non-launchd in chain), and the CLI binary is what gets attributed.
- macOS permission check happens at startup (`main.py:54-72`), not at runtime — daemon must be killed and restarted (`launchctl bootout` + `bootstrap`, not just `kickstart -k`) for fresh permission re-evaluation, especially after TCC changes.
- CGEventTap can freeze keyboard input system-wide if buggy — test source changes in foreground first (`python3 -m src.main`), not via launchd.
- This is a fork — additive changes preferred over rewrites; new modules > restructured ones, to keep upstream merges clean.
