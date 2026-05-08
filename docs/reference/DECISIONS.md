# DECISIONS — architectural decision log

> Newest entries on TOP. Each entry: **Problem / Alternatives considered / Chose / Why / Artifacts**.
> Triggered when a non-routine architectural pivot occurs (per `/save` Q3).

---

## 2026-05-08 (session 5) — Spell-correction & Swift-port: two-track strategy + scope clarification of 2026-05-07

**Problem.** Discussion-only session. User asked feasibility of on-the-fly spell-correction (separate from layout-switching), broadened to: hypothetical open-source distribution; whether Swift-port should happen first; multilingual support. User questioned whether the 2026-05-07 Swift-rejection had been over-absolutized in subsequent paraphrasing.

**Alternatives considered.**

- (a) **Implement spell-correction now in Python.** Risk: spec unknown without daily-use accumulation; premature feature design likely (per-app exclusion, code-aware exclusions, confidence threshold all need real-world calibration).
- (b) **Rewrite to Swift now, then add spell.** Same spec-unknown risk; weeks of work invested in moving target. Loses the iteration speed Python gives during exploration phase.
- (c) **Two-track: Python prototype → daily use → Swift port → open-source publication.** Each track unblocks the next. Spec accumulates on cheap Python; mechanical translation to Swift once stable; publish as native `.app` bundle when distribution polish exists.
- (d) **Defer entirely until next bug or motivation surfaces.** Honor user's stated lack of motivation; revisit naturally.

**Chose.** (d) for the immediate session — user said «пока ничего не хочу делать». When revisited, **(c) is the strategy.**

**Scope-clarification of 2026-05-07 Swift entry.** That decision was personal-use-context bound: «environmental fix took hours instead of weeks; pymorphy3 essential to current layout-detection logic; NaturalLanguage.framework qualitatively weaker for our specific morphology needs.» **In a community-distribution context, the calculus shifts:** pymorphy3 ceases to be a blocker if NSSpellChecker takes over the validity check (spell-correction core), and Python-daemon's TCC-attribution-on-CLI-binary footgun is itself an adoption barrier most users won't cross. Native Swift `.app` is the right shape for distribution. The 2026-05-07 entry remains valid for current personal-use trajectory, but should NOT be paraphrased as an absolute "no Swift".

**Why (c) when revisited.**

- **Spec is unknown without daily use.** Writing Swift now = architecturally clean code that misbehaves where you didn't predict.
- **Cost-of-change much lower in Python during exploration.** Reload daemon → test in 5 seconds. Swift has rebuild + relink + relaunch + permissions cycle.
- **`pymorphy3` retirement matures naturally.** As spell-correction takes over, layout-detection's pymorphy3 dependency becomes more isolated — easier to drop or re-implement on Swift port.
- **Open-source publication deferred to Swift.** Premature Python-daemon publication = support burden on TCC/arm64 setup issues, distracts from feature iteration.

**Trade-offs / known constraints.**

- Two-track requires sustained motivation across months. If motivation fizzles after Track 1, project ends with «good for me, never published» — acceptable outcome, baseline goal already met.
- Swift-port estimated several weeks, mostly mechanical translation once Track 1 spec stabilizes. Not «extremely hard» — a one-time investment.
- `pymorphy3` portability nuance: it's library + OpenCorpora dictionary (compiled DAWG, several MB) + heuristic model. Algorithmically transferable to Swift, but weeks of work + lifetime maintenance burden. For spell-correction via NSSpellChecker, pymorphy3 isn't needed — dilemma only matters if Swift port keeps layout-detection in current form.

**Artifacts.**

- `docs/research/spell-correction-strategy.md` — full findings: architecture fit, competitive research (Charm, Caramba, Espanso, KeySwitcher, LanguageTool, Grammarly), engine recommendation (NSSpellChecker via pyobjc), multilingual notes, feature roadmap (5 groups), pitfalls, Swift-port reconsideration with pymorphy3 nuance, two-track strategy details, comparison metrics, how-to-revisit instruction.
- `PLAN.md` "Pending — pick when needed" — single-line pointer.
- 2026-05-07 entry in this file: still valid for personal-use context; not reversed.
- Memory: `feedback_verify_past_decisions_before_paraphrasing.md` — re-read source before paraphrasing past decisions; don't compress context-bound recommendations into absolute statements.

---

## 2026-05-08 (late) — Trust model: validate only when boundary directly observed

**Problem.** User reported repeated tail-of-word mangles after edit operations: paste long text + type `cv ` → last 2 chars of pasted text get replaced with `см`; arrow-key to mid-word + backspace + retype tail → tail mangled; click in mid-word + type → garbage. Logs across the session showed the pattern: `_check_and_correct: word='cv' boundary=' '` → `correct: 'cv' -> 'см' (extra='', deleted=3)`. The 3 deleted chars in `correct()` are exactly the 2-letter word + boundary as the daemon believes; but on-screen they hit text the user never intended to delete because the cursor was elsewhere.

Root cause split: (1) validator false-positive on 2-3 letter pairs — 272 enumerated false-positive pairs (157 Latin→Russian + 115 Russian→Latin) where the layout conversion is "valid enough" for either pymorphy3 or the english wordlist; (2) WordBuffer is a keystroke counter with no view of on-screen cursor — external resets (mouse, cursor-move, app-switch, paste/Cmd-V) silently desync buffer from cursor.

**Alternatives considered.**

- (a) **Raise minimum word length to 3 or 4.** Closes the 272 enumerated 2-letter false-positives at the cost of disabling all 2-3 letter correction. User pushed back: doesn't fix the *fundamental* desync — the same class of bug recurs whenever editing 4+ letter words and replacing the last N chars produces a false-positive fragment. Rejected.

- (b) **Accessibility API integration.** Query the on-screen text field for chars immediately left of cursor. Ideal accuracy: the daemon can decide per-word whether to suppress. But: doesn't work in iTerm2 / Terminal / VS Code / Electron / web inputs; asynchronous (5-30ms per query, latency-killing on hot path); requires a separate AX permission that's already in our trust budget but adds runtime overhead. Out of scope for first fix; reserved as future enhancement (and the eventual removal condition for INV-003).

- (c) **Boundary-observation flag (chose this).** Add `_can_correct_next_word: bool` in `KeyboardMonitor`. Set False on every external buffer-loss event (mouse-down, cursor-move keystroke, app-switch via observer, Cmd-modifier keystroke). At `_check_and_correct` entry, if False, log + skip + re-arm via `try/finally`. ~10 lines of behavior change + 10 new tests. Trade-off: first word after any reset event is never corrected (user explicitly accepted this).

**Chose.** (c). User-articulated rule: *"Если перед словом не было пробела — программа не должна пытаться угадывать"* — translates one-to-one to "skip correction unless the daemon directly observed the preceding boundary".

**Why.**

- Single behavioral change, ~10 lines of source diff, comprehensive test coverage (10 new tests across 2 PRs).
- Closes the entire observed bug class: cursor-move-mid-word, mouse-click-mid-word, Cmd+V paste followed by typing, app-switch followed by typing.
- Raising the length threshold (option a) was the user's first instinct after the false-positive list was shown, but the user themselves rejected it on the grounds that desync is the deeper issue. This is the lesson: don't optimize the validator if the trust model is the actual gap.
- Cost (first word after reset never corrected) matches the user's mental model: after editing or pasting, you're working with on-screen text the daemon didn't see — don't trust correction until a clean boundary establishes new sync.

**Trade-offs / known gaps.**

- **Backspace into empty buffer**: not yet covered. If user backspaces over text the daemon didn't write, the buffer was already empty so no `clear()` fires, flag stays True. Next word can mangle. Separate follow-up.
- **Ctrl-modifier shortcuts** beyond the configured hotkey (e.g., Ctrl+A in terminal): not covered. Less impactful in practice but a known gap.
- **Option-modifier**: deliberately not covered — Option commonly produces letter input (`Option+E + a → á`).

**Artifacts.**

- Source: PR #18 (commit `1aef293`, `fix/skip-correction-after-buffer-loss`) — adds flag, sets False at 3 sites (mouse-down, cursor-move, app-switch), checks at `_check_and_correct` entry, re-arms via `try/finally`. PR #19 (commit `79f7f9e`, `fix/cmd-modifier-buffer-loss`) — adds Cmd-modifier branch in `_tap_callback`.
- Tests: 195 → 205 (+10 across both PRs). Covers normal flow, each reset path, re-arm-after-skip.
- Diagnostic infrastructure: PR #16 (commit `a0d6b76`) instrumented hotkey/undo path; PR #17 (commit `b9de6b9`) instrumented `WordBuffer.clear/add_char` with `prev_buffer` and `reason=` parameters. Without these the diagnostic was untraceable.
- `INVARIANTS.md` § INV-003.
- `ERRORS.md` § E-0004.
- 272-pair false-positive enumeration: archived in `docs/archive/session-resume-history/2026-05.md` session-4 entry.

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
