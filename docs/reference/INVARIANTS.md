# INVARIANTS — load-bearing design constraints

> Constraints that next-me MUST not break without re-derivation. Surface in `CLAUDE.md` § ARCHITECTURAL INVARIANTS as one-line summary; full motivation here.
> Triggered when a code-level constraint emerges (per `/save` Q1).

---

### INV-001: Daemon must run on native arm64 Python on Apple Silicon

**Constraint.** The interpreter at the end of `.venv/bin/python3` symlink chain must be **native arm64** — either python.org universal2 installer (`/Library/Frameworks/Python.framework/Versions/X.Y/bin/python3.Y`) or `/opt/homebrew/Cellar/python@X.Y/.../bin/python3.Y`. **Intel Homebrew Python at `/usr/local/Cellar/...` is forbidden** for the daemon's interpreter.

When recreating the venv from a Bash session that may itself be x86_64-spawned (Claude Code's Terminal often is), force arm64 explicitly:
```bash
arch -arm64 <python.org python3> -m venv .venv
arch -arm64 .venv/bin/python3 -m pip install -r requirements.txt
```
Otherwise pip will pull x86_64 wheels for `pyobjc-core` etc., even though the Python binary itself is universal2 — and arm64 launchd execution will fail to load them.

**Motivation.** Rosetta-translated Python under launchd produces a TCC identity that does not match grants made via System Settings UI — `CGPreflightListenEventAccess` / `CGPreflightPostEventAccess` return `False` even with explicit grants. Terminal-spawned probes mask the issue via TCC parent inheritance, so the failure surfaces only under launchd. See `ERRORS.md` E-0001 layer 1.

**Introduced.** 2026-05-07, session 2. See `ERRORS.md` E-0001, `docs/reference/DECISIONS.md` 2026-05-07 entry "Stay Python; resolve via arm64 + TCC target correction".

**Removal requires.** Either (a) the project switches off Python entirely (Swift native rewrite), (b) Apple changes Rosetta-launchd-TCC interaction so grants survive the translation boundary, or (c) the project ships a properly bundled `.app` whose CGEventTap chain doesn't go through a separate-architecture interpreter.

---

### INV-002: TCC permissions target the CLI Python binary, not Python.app

**Constraint.** Accessibility and Input Monitoring grants for the daemon must be added against the **CLI launcher path** — `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14` (or whichever native arm64 Python's CLI binary is in use), **NOT** against `/Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app`.

`setup.sh` and onboarding documentation must reflect this. The CLI binary appears in System Settings without an `.app`-style icon (just generic executable icon labeled `python3.14`); that's expected.

**Motivation.** macOS TCC attributes requests to the **responsible process** — the first non-launchd process in the exec chain. Daemon chain: `launchd → bin/python3.14 → Python.app/Contents/MacOS/Python` (re-exec via `__PYVENV_LAUNCHER__`). TCC checks `bin/python3.14`'s entry, not Python.app's. Adding Python.app to TCC has no effect; only adding the CLI binary works. Verified via `log stream --predicate 'subsystem == "com.apple.TCC"'` showing `AUTHREQ_SUBJECT: subject=.../bin/python3.14` and `BUNDLE_ATTRIBUTION: candidateBundle(.../bin) is nil or has no identifier`. See `ERRORS.md` E-0001 layer 3.

**Introduced.** 2026-05-07, session 2. See `ERRORS.md` E-0001.

**Removal requires.** Either (a) launchd plist changes to invoke `Python.app/Contents/MacOS/Python` directly as `ProgramArguments[0]`, bypassing the `bin/python3.14` re-exec — then `Python.app` becomes the responsible process and that grant target works; or (b) Apple changes TCC attribution model to use the running process's bundle identity instead of the responsible process; or (c) project switches off Python entirely.

---

### INV-003: Auto-correction must skip the first word after any external buffer-loss event

**Constraint.** `KeyboardMonitor._can_correct_next_word: bool` (initial value `True`) must be set to `False` whenever the daemon's `_word_buffer` is reset by an external event:

- `_tap_callback` on `kCGEventLeftMouseDown` (mouse click)
- `_tap_callback` on `_is_cursor_move(keycode)` (arrow keys, Home/End, PgUp/PgDn)
- `_tap_callback` when `flags & kCGEventFlagMaskCommand` is set (Cmd+V paste, Cmd+X cut, Cmd+A select-all, Cmd+Z undo, Cmd+Tab, Cmd+arrow, etc.)
- `_handle_queue_item("clear")` (NSWorkspace app-switch observer)

The `_check_and_correct` method must, at entry, check the flag — if `False`, log a `skipping correction (no observed boundary before word=...)` line, update `_last_completed_word` (so the manual hotkey path remains armed), and return early WITHOUT calling correction logic. The flag must be re-armed to `True` in a `try/finally` block surrounding the body, so subsequent words behave normally regardless of which path returned.

**Motivation.** Two independent gaps combine into a tail-of-word mangle bug:
1. Validator false-positives at length 2-3: 157 Latin → Russian + 115 Russian → Latin pairs where the layout-converted form is "valid" enough by either pymorphy3 (RU) or the english wordlist (EN) to trigger correction. Examples observed in user logs: `cv → см`, `ог → ju`, `gh → пр`, `dc → вс`, `ut → ге`. Full enumeration in session-4 archive.
2. WordBuffer-cursor desync: `_word_buffer` is a counter without on-screen visibility. External events that reset the buffer (mouse, cursor-move, app-switch, paste/Cmd-shortcut) leave the on-screen cursor in a position the daemon doesn't track. The next chars typed start a "fresh word" in the buffer, but on-screen they may be inserted inside an existing word. When the validator green-lights a 2-3 letter false-positive, `correct()` issues backspaces that eat real chars from a longer on-screen word, then types the false-positive replacement.

The flag closes (2). Without it, every cursor-move/click/paste followed by typing a 2-3 letter false-positive pair mangles surrounding on-screen text. CGEventTap cannot read text-field contents, so we cannot verify boundary on the on-screen side; the only reliable signal is "did I myself observe the boundary that completed the previous word?".

**Trade-off.** First word after any reset event is never auto-corrected even if the user genuinely typed it from scratch (e.g., user clicks at end of empty document and types `ghbdtn ` — no correction). This is intentional and was explicitly accepted by the user as the cost of correctness.

**Introduced.** 2026-05-08, session 4. PR #18 (commit `1aef293`, `fix/skip-correction-after-buffer-loss`) added the flag with mouse / cursor-move / app-switch coverage. PR #19 (commit `79f7f9e`, `fix/cmd-modifier-buffer-loss`) extended with the Cmd-modifier branch. See `docs/reference/DECISIONS.md` 2026-05-08 (late) entry "Trust model: validate only when boundary directly observed" and `ERRORS.md` E-0004.

**Removal requires.** A reliable on-screen-cursor context source (e.g., Accessibility API integration that works in terminals, Electron, web inputs, etc.) — at which point the daemon can verify "is there a non-space char immediately before the start of my buffer?" and decide on a per-word basis whether to suppress. Until then, the binary flag is the only reliable signal.

---

## Format for new invariants

When adding a new INV-NNN:

```markdown
### INV-NNN: <one-line constraint>

**Constraint.** <what code/design must do or not do>

**Motivation.** <why this is load-bearing — what breaks if removed>

**Introduced.** <YYYY-MM-DD, session N, link to commit / DECISIONS entry / ERROR>

**Removal requires.** <specific condition that must be true to remove this invariant>
```

Then mirror a one-line summary in `CLAUDE.md` § ARCHITECTURAL INVARIANTS.

---

## Removed invariants

> When an invariant is removed (its removal condition met), move it here verbatim with `**Removed:** <date, session, reason>` appended. **Do not delete.** This file is the audit trail.

*(none yet)*
