# DECISIONS — architectural decision log

> Newest entries on TOP. Each entry: **Problem / Alternatives considered / Chose / Why / Artifacts**.
> Triggered when a non-routine architectural pivot occurs (per `/save` Q3).

---

## 2026-05-08 — Threading-fragility resolution via queue-based ownership (no locks)

**Problem.** Audit § 3 flagged 4 threading fragilities in the daemon:
1. `_appDidActivate_` observer registered on tap thread, but `NSWorkspace` notifications deliver on main → observer likely never fires → `_word_buffer` not cleared on app-switch → stale buffer state contaminating future corrections.
2. `_word_buffer` written by both tap thread (`add_char`) and worker thread (replay drain) — interleaving racy under GIL.
3. `_last_completed_word` written by tap thread, read by worker thread (`_handle_hotkey`) → cross-thread read may see torn tuple.
4. `AutoCorrector._is_correcting` flipped to False in `correct()` finally BEFORE worker drains the replay buffer → race window where tap thread sees `False`, writes new keystrokes to `_word_buffer` directly, while worker simultaneously replays via `add_char`.

**Alternatives considered.**
- (a) **Lock-based.** Single mutex protecting `_word_buffer` shared between tap callback, worker, and observer. Reaches into the AutoCorrector lock's encapsulation; risks priority-inversion-style stalls in CGEventTap callback (event tap calls block keyboard input system-wide if held); doesn't address FRAGILITY 4 elegantly (still need to coordinate flag flip with drain).
- (b) **Per-fragility ad-hoc fixes.** E.g. dispatch observer to main thread for #1, add `RLock` for #2, etc. Mixed approach; harder to test; harder to extend later.
- (c) **Queue-based ownership pattern.** Extend the existing `_detection_queue` (already a thread-safe `queue.Queue`) to carry state-update messages alongside detection requests. Worker thread becomes the SINGLE consumer of state-changing messages (`("clear",)`, `("complete", ...)`). Observer dispatched to main thread but doesn't touch state directly — only enqueues. PR-EY's deferred-flip pattern (move `is_correcting=False` from `correct().finally` into a new `finalize_correction()` called by worker after drain) closes #4 without locks.

**Chose.** (c) — queue-based ownership across 3 PRs (PR-E for #1+#2 via observer→main + queue-based clear; PR-EX for #3 via `("complete",)` message; PR-EY for #4 via deferred flip). PR-G later added `try/except/finally` around the worker loop body with `finalize_correction()` in `finally` to guard the exception path that PR-EY's deferred flip newly exposed.

**Why.**
- No new locks introduced — preserves existing thread topology (tap, worker, main).
- `_handle_queue_item` becomes a clear, testable dispatch point. Each new state-change message is one branch + one test.
- Tap thread still writes `_word_buffer` directly via `add_char` (this is the dominant write path; consolidating it would require redirecting the entire keystroke pipeline through the queue, which dramatically increases latency and is overkill for the actual race surface).
- Worker single-ownership of state-update messages eliminates 3 of 4 fragilities outright; PR-EY's deferred flip closes the 4th.
- Smoke-testing the merged campaign surfaced TWO pre-existing upstream bugs (E-0002 modifier-flag bleed, E-0003 Tab-as-boundary on Cmd+Tab) that unit tests didn't catch — these were unrelated to the audit's findings but caught during interactive verification of the threading fixes.

**Trade-offs / known minor follow-ups.**
- `_is_stale()` checks `not self._detection_queue.empty()`. With `("complete",)` enqueues now firing on every word boundary (not just qualifying ones), the queue has slightly more items at staleness-check time. In practice the staleness signal is binary and this didn't change observed behavior on common typing patterns; documented as a "marginal eagerness" trade-off. A precise fix would iterate `queue.queue` and count only `("check", ...)` items — deferred.
- Cross-app replay leak: if user types during a correction, then app-switches before worker drains, replay-buffer chars get typed into the destination app on next correction trigger. Pre-existing behavior; not addressed by this campaign. Fix would be to discard (not drain) `_replay_buffer` in the `("clear",)` handler.

**Artifacts.**
- Source changes:
  - `src/keyboard_monitor.py` — `_handle_queue_item` (dispatch helper), `_detection_worker` (try/finally + `finalize_correction`), `_appDidActivate_` (queue-based clear), `start()` (observer dispatched to main via `NSOperationQueue.mainQueue().addOperationWithBlock_`), `_register_app_observer` (extracted main-thread method), `_tap_callback` (try/except + `kCGEventTapDisabledByUserInput` handling).
  - `src/auto_corrector.py` — `correct()` and `undo()` no longer flip `_is_correcting=False` in finally; `finalize_correction()` (idempotent) added; preflight TCC guard at entry.
- Tests: ~30 new tests across `test_keyboard_monitor.py`, `test_auto_corrector.py`. Total suite: 117 → 195.
- 4 PRs merged: `db98efb` (PR-E FRAGILITY 1+2), `cfd4691` (PR-EX #3), `c63abb7` (PR-EY #4), `af40e39` (PR-G exception safety).
- ERRORS.md § E-0002, E-0003 — pre-existing bugs surfaced during smoke-test verification.

---

## 2026-05-07 — Stay on Python; fix via arm64 install + TCC target correction (no .app rebuild, no Swift rewrite)

**Problem.** Daemon under launchd logged `Permissions missing, monitor not started.` despite Accessibility + Input Monitoring being granted to `Python.app` in System Settings. After multiple permission re-grants, ad-hoc and Dev-cert re-signs of brew Python.app, and a TCC reset, the failure persisted. Considered whether to architecturally pivot off Python.

**Alternatives considered.**
- (a) **py2app `.app` bundle** — embed brew Python + deps into `Layoutswitcher.app` with stable bundle ID. Days of delegations; py2app's last release classifies up to Python 3.13 (3.14 unsupported on paper, installs but untested). Strong guess that bundling fixes the launchd-paradox, not proven.
- (b) **Swift + AppKit native rewrite** — drop Python entirely; weeks of work; loses pymorphy3 (no equivalent Russian morphology library in Swift; `NaturalLanguage.framework` is qualitatively weaker for our needs).
- (c) **Hammerspoon + Lua** — config on top of an existing signed automation host; no `.app` to maintain, but Lua has no morphology library, would need pymorphy3 helper subprocess.
- (d) **PyInstaller / Briefcase `.app` bundles** — alternatives to py2app, similar trade-offs.
- (e) **Diagnose the launchd-paradox first** — spend an hour on root-cause without architectural change; revisit pivots only if intractable.

**Chose.** (e) → confirmed root cause is environmental (Rosetta translation under launchd + responsible-process TCC attribution + 4 stale TCC entries from earlier re-signs). Fix delivered without a single source-file change: install arm64 Python (python.org universal2), recreate venv with `arch -arm64`, `tccutil reset Accessibility|ListenEvent|PostEvent org.python.python`, grant permissions to `bin/python3.14` (CLI binary, not Python.app).

**Why.**
- Days/weeks of architectural work avoided.
- Discovered three concrete pieces of load-bearing knowledge (INV-001 arm64 Python; INV-002 TCC target = CLI binary; the TCC log streaming diagnostic recipe) that survive into future sessions and would have re-bitten under any architectural pivot too.
- py2app option remains available if needed later — postponed, not rejected. Triggers for revisit: (i) Apple breaks the responsible-process attribution path, (ii) we want our own name in System Settings, (iii) we want isolation from brew updates / python.org installer drift.

**Artifacts.**
- `ERRORS.md` § E-0001 — full diagnostic trail (Rosetta detection via `vmmap`, TCC log streaming, attribution analysis).
- `docs/reference/INVARIANTS.md` § INV-001, INV-002.
- `docs/archive/session-resume-history/2026-05.md` — verbose saga retrospective with timeline and lessons.
- `docs/audits/upstream-2026-05-07.md` — informed first-feature pick after this issue resolved.

---

## 2026-05-07 — Bootstrap: orchestrator pattern adopted

**Problem.** Forking moiz2306/layout-switcher for personal customization. Need a workflow that scales beyond ad-hoc commits, surfaces architectural pivots, and keeps upstream syncs cleanly diffable.

**Alternatives considered.**
- (a) Casual workflow: edit-commit-push directly on `main`, sync upstream with `git pull upstream main`.
- (b) Branch-per-task only: PRs but no orchestrator delegation.
- (c) Full orchestrator pattern (matches coronium-clone-iii / voice-adapt convention): main session = orchestrator only; agents do source edits; PRs reviewed at diff level.

**Chose.** (c). Strict orchestrator-only with read carve-outs adapted to Python project. Agent pipeline (issue-queue + opencode + verifier) deferred until project size justifies it.

**Why.**
- Consistency with other projects on this Mac (same mental model).
- Per-PR diff review forces explicit intent on every change.
- Sync workflow with upstream becomes auditable (`upstream-merge/<date>` branches with diff review).
- Even on solo project, INVARIANTS.md / DECISIONS.md / structure scale linearly — no harm in starting small.

**Artifacts.**
- `CLAUDE.md`
- `docs/reference/ORCHESTRATOR.md`
- `docs/reference/STRUCTURE.md`
- `docs/reference/COMMANDS.md`
- `docs/reference/UPSTREAM-SYNC.md`
- `docs/reference/INVARIANTS.md` (empty stub)
- This file (empty stub for future entries)
- `SESSION_RESUME.md`, `PLAN.md`, `ERRORS.md`, `HANDOFF.md` (empty stubs / templates)
- `.claude/commands/save.md` (Living-layer Q1-Q6 protocol)
- `.claude/commands/shrink-claude.md`
