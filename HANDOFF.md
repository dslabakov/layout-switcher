# Handoff

> Top-level boot script for the next Claude Code session. Terse, ~1-2 KB.
> Rotated at the end of each session — current contents archived to `docs/handoffs/YYYY-MM-DD-session-N-end.md`, then this file overwritten with fresh handoff for next session.

## Status

**Session 3 complete (2026-05-08).** 14+1 PRs merged (PR-A through PR-J + 2 hotfixes + a PR-I test-fix follow-up). All 4 audit-flagged threading fragilities closed. 2 pre-existing upstream bugs found via interactive smoke-test (E-0002 modifier-flag bleed, E-0003 Tab-as-boundary on Cmd+Tab). 117 → 195 tests. Daemon comprehensively defended across thread, exception, permission, and install paths.

## Read first

1. `CLAUDE.md` — orchestrator-only mode + ARCHITECTURAL INVARIANTS (INV-001/INV-002 unchanged).
2. `SESSION_RESUME.md` — current state + carry-overs after the campaign.
3. `PLAN.md` → "Next Session — Start Here" — pick next scope.
4. `docs/reference/DECISIONS.md` § 2026-05-08 — threading-fragility resolution architecture (queue-based ownership pattern); read this if touching `_handle_queue_item`, `_detection_worker`, or `AutoCorrector.correct/undo/finalize_correction`.
5. `ERRORS.md` § E-0002, E-0003 — recently-fixed pre-existing bugs; both have regression-guard tests.

## Delta (since session 2 end)

- Diagnostic logging available via `debug: true` in `~/.config/layout-switcher/config.yaml` or `--debug` CLI flag. PR-A.
- Configurable hotkey now actually wired (`config.hotkey_convert` parsed; PR-C). Parser rejects malformed strings gracefully.
- Persistent correction stats at `~/.config/layout-switcher/stats.json` — atomic write, JSON `{"count": N, "date": "YYYY-MM-DD"}`. PR-D.
- Threading fixes via queue-message pattern — `("clear",)`, `("complete",)`, plus `finalize_correction()` deferred-flip. See DECISIONS § 2026-05-08.
- Permission watchdog: NSTimer on main thread polls `CGPreflight*` every 10s; status-bar icon goes orange on revocation, green on restore. PR-F.
- Exception safety: `_tap_callback` and `_detection_worker` have try/except; worker calls `finalize_correction()` in `finally` (idempotent). PR-G.
- Preflight TCC guard at entry of `correct()` and `undo()` — prevents partial-deletion garbage if permissions revoked mid-session. PR-H.
- `setup.sh` now enforces INV-001 — refuses to proceed if `python3` in PATH is not arm64 on Apple Silicon. PR-I.
- `build_wordlist.py` exits 1 with loud warning if `/usr/share/dict/words` missing. PR-I.
- `docs/reference/DELEGATION.md` — centralized delegation-prompt boilerplate (no-destructive block, wordlist trap, smoke-gate criteria, branch naming).
- Memory: `feedback_step_by_step_smoke_testing.md` — drive interactive smoke-tests step-by-step instead of dumping the full pipeline.

## How to start session 4

1. `git status` — should be clean on `main` at `2f5a179` or later. `launchctl print gui/$(id -u)/com.layout-switcher` → `state = running` (daemon was restarted at session 3 end). If not, bootstrap.
2. Tail log: `tail -5 ~/.config/layout-switcher/layout-switcher.log` should show "started with full permissions" + the new debug entries (since `debug: true` is now on in user's config).
3. Read `SESSION_RESUME.md` carry-overs and `PLAN.md` "Next Session — Start Here". Most campaign-driven work is done; remaining items are minor follow-ups + audit candidates that weren't picked up.
4. If you're about to touch threading code in `keyboard_monitor.py` or `auto_corrector.py` — read `docs/reference/DECISIONS.md` § 2026-05-08 first. The queue-ownership pattern is load-bearing.

## Known traps

- All session-2 traps (INV-001 arm64, INV-002 TCC target, no `Python.app` grant) still apply.
- **Synthetic CGEvents must clear modifier flags** (`CGEventSetFlags(ev, 0)`) before `CGEventPost`. Removed in any future refactor → manual hotkey breaks again with delete-by-word + app-shortcut artifacts. Regression-guarded by tests in `test_auto_corrector.py`. ERRORS.md E-0002.
- **`\t` (Tab) must NOT be in `WordBuffer.BOUNDARIES`** — Cmd+Tab triggers Tab keydown; if Tab is a word boundary, phantom corrections fire in destination apps. Regression-guarded. ERRORS.md E-0003.
- **`AutoCorrector.correct()` and `undo()` no longer flip `_is_correcting=False` on return** — caller (worker) MUST call `finalize_correction()` after replay drain. Worker does this in `finally`. If a future caller invokes `correct()` outside the worker pattern, it must pair with `finalize_correction()` or the daemon silently freezes (tap routes all keys to replay buffer).
- **`_tap_callback` exceptions are swallowed and logged** — if behavior gets weird and unit tests are silent, grep the log for `Unhandled exception in _tap_callback`.
- **Cwd inheritance across chained Bash calls is unreliable after agent worktrees** — explicit `cd /Users/slabakov/dev/Layoutswitcher` at the top of merge-and-sync chains.
- **Test that touches install/output paths must take an `output_path` parameter** — never let a test write to shared state via worktree symlink. Wordlist clobber incident in PR-I.

---

## Convention (how to use this file)

**Purpose:** terse boot script for next session. Reading time: < 5 minutes. Functions as "start here" pointer + delta from last session.

**Strict rules:**
1. **No duplication of content** that lives in `SESSION_RESUME.md`, `PLAN.md`, `DECISIONS.md`, `ERRORS.md`. Pointer + 1-line gloss only.
2. **Genuine added value sections:** `## Read first`, `## Delta`, `## Known traps`, `## How to start session N+1`.
3. **Target size:** under 2 KB. If growing, content belongs elsewhere.
4. **Rotation:** at the end of each session, orchestrator (a) archives this file's current contents to `docs/handoffs/YYYY-MM-DD-session-N-end.md`, (b) overwrites this file with fresh handoff for next session.

When this file is the empty/template version, it's a signal that the previous session ended without filing a fresh handoff — orchestrator falls through to the standard read-first list (CLAUDE.md → SESSION_RESUME.md → PLAN.md).
