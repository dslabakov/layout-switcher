# Handoff

> Top-level boot script for the next Claude Code session. Terse, ~1-2 KB.
> Rotated at the end of each session — current contents archived to `docs/handoffs/YYYY-MM-DD-session-N-end.md`, then this file overwritten with fresh handoff for next session.

## Status

**Session 4 complete (2026-05-08).** Tail-of-word mangle bug class closed via INV-003 (boundary-observation flag). 4 PRs landed: #16 + #17 instrumented hotkey/undo and WordBuffer paths; #18 added the flag with mouse / cursor-move / app-switch coverage; #19 extended with Cmd-modifier branch. 195 → 205 tests. User is monitoring in production for regressions.

## Read first

1. `CLAUDE.md` — orchestrator-only mode + INV-001/INV-002/**INV-003** (the new one).
2. `SESSION_RESUME.md` — current state + carry-overs. **Read this before touching `_check_and_correct` or `_tap_callback`** — INV-003's `_can_correct_next_word` flag is load-bearing.
3. `PLAN.md` → "Next Session — Start Here". Adjacent gaps to INV-003 (backspace-into-empty, Ctrl-shortcuts) are the natural next pickups when user reports them.
4. `docs/reference/DECISIONS.md` § 2026-05-08 (late) — trust model rationale and rejected alternatives (validator length threshold; Accessibility API).
5. `ERRORS.md` § E-0004 — bug class this session closed; recognition cues for regressions.

## Delta (since session 3 end)

- **INV-003** added: `KeyboardMonitor._can_correct_next_word` flag — gates `_check_and_correct` against firing when the daemon didn't directly observe the preceding boundary. Set False by mouse-down / cursor-move / app-switch / Cmd-modifier; re-armed True via `try/finally` in `_check_and_correct`.
- Logging instrumentation: `_handle_hotkey` entry + branches, `correct()` / `undo()` happy-paths, `invalidate_undo` with `reason=`, `WordBuffer.clear` with `reason=` and `prev_buffer=`, `add_char` empty→non-empty transition. PRs #16 + #17.
- 272-pair false-positive table (latin↔russian 2-letter pairs that pass the dictionary check): enumeration archived in `docs/archive/session-resume-history/2026-05.md` session-4 entry.
- Memory: `feedback_listen_when_user_says_off_track.md` — when user says "у меня всё не так", treat as evidence the hypothesis is hostile to reality, not as a dispute about details.

## How to start session 5

1. `git status` clean on main at `79f7f9e` or later. Daemon should be `state = running` (rebooted at session 4 end on new code).
2. `tail -10 ~/.config/layout-switcher/layout-switcher.log` should show recent typing activity. Look for `_check_and_correct: skipping correction (no observed boundary before word=...)` lines after edit/paste/click events — those confirm INV-003 is firing in production.
3. If user reports a fresh tail-of-word mangle: cross-reference timestamp with log; check whether the preceding event was covered (mouse-down / cursor-move / app-switch / Cmd-shortcut → INV-003 should have fired, regression). If preceding event was backspace-into-empty or Ctrl-shortcut → that's the known adjacent gap, ship the corresponding extension.
4. If touching `_check_and_correct` or `_tap_callback` for any reason: re-read INV-003 in `INVARIANTS.md` and the test cases in `tests/test_keyboard_monitor.py` (search for `_can_correct_next_word`). The `try/finally` re-arm is critical — easy to miss on refactor.

## Known traps

- All session-2 + session-3 traps still apply (INV-001 arm64, INV-002 TCC target, synthetic CGEvent flag clearing for E-0002, Tab-not-in-BOUNDARIES for E-0003, queue-ownership pattern for thread safety, output_path test parameterization).
- **`_can_correct_next_word` re-arm via `try/finally`** — if a future refactor moves the flag-set-True out of the `finally` block, exception paths in `_check_and_correct` will leave the flag False forever and corrections will silently never fire again. Regression-guarded by tests but easy to miss in code review.
- **The flag covers 4 reset paths only**: mouse-down, cursor-move, app-switch, Cmd-modifier. Backspace into empty buffer and Ctrl-modifier are KNOWN GAPS (deliberately deferred). Don't claim INV-003 closes those without extending the implementation.
- **`gh pr create` defaults to upstream when origin is a fork.** Always pass `--repo dslabakov/layout-switcher` explicitly. Session 4 hit this once: PR #18's first attempt landed in moiz2306/layout-switcher#2 and had to be closed and re-opened. Now in DELEGATION.md prompt boilerplate as a reminder.

---

## Convention (how to use this file)

**Purpose:** terse boot script for next session. Reading time: < 5 minutes. Functions as "start here" pointer + delta from last session.

**Strict rules:**
1. **No duplication of content** that lives in `SESSION_RESUME.md`, `PLAN.md`, `DECISIONS.md`, `ERRORS.md`. Pointer + 1-line gloss only.
2. **Genuine added value sections:** `## Read first`, `## Delta`, `## Known traps`, `## How to start session N+1`.
3. **Target size:** under 2 KB. If growing, content belongs elsewhere.
4. **Rotation:** at the end of each session, orchestrator (a) archives this file's current contents to `docs/handoffs/YYYY-MM-DD-session-N-end.md`, (b) overwrites this file with fresh handoff for next session.

When this file is the empty/template version, it's a signal that the previous session ended without filing a fresh handoff — orchestrator falls through to the standard read-first list (CLAUDE.md → SESSION_RESUME.md → PLAN.md).
