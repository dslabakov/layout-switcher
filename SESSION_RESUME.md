# SESSION_RESUME — Layoutswitcher

> Living-layer state. Update on every `/save` (Q5 routes here for current state).
> Target size: ≤ 30k chars. If growing, archive older sessions to `docs/archive/session-resume-history/`.

---

## Current state (updated 2026-05-08)

**Tail-of-word mangle bug class closed.** Session 4 traced and fixed the recurring "two letters at the end of a long word silently replaced with garbage" bug. Root cause was twofold (validator false-positives on 272 enumerated 2-3-letter layout pairs + WordBuffer-cursor desync after any external buffer-loss event); fix locks down the desync side via `_can_correct_next_word` boundary-observation flag. Manifestations covered: arrow-keys-to-mid-word + edit, mouse-click mid-word, NSWorkspace app-switch, all Cmd-modifier shortcuts including Cmd+V paste.

**Test suite: 195 → 205** (+10 across PR #18 + #19). Diagnostic infrastructure expanded substantially: hotkey/undo path logged (PR #16), `WordBuffer.clear/add_char` logged with reason and prev_buffer (PR #17). Without those instrumentations, the diagnostic chain that pinned the bug class would have been impossible.

**Known gaps still in scope.** Backspace-into-empty-buffer (stripping text the daemon didn't write) and Ctrl-modifier shortcuts beyond the configured hotkey are not yet covered by the boundary-observation flag. Both are deliberate follow-ups; user has been asked to flag them when reproduced.

## In-flight (WIP, not yet merged/pushed)

- `.venv-old-x86` — backup of the broken Intel/Rosetta venv at repo root. Carried over from session 3. Still safe to delete; deferred.
- No open feature branches; no unpushed commits beyond what `/save` produces.

## Recent decisions

- **2026-05-08 (late)** — Trust model: validate only when boundary directly observed. `_can_correct_next_word` flag covers mouse / cursor-move / app-switch / Cmd-modifier paths. PR #18 + #19. See `docs/reference/DECISIONS.md`.
- **2026-05-08** — Threading-fragility resolution via queue-based ownership (no locks). 4 PRs. See `docs/reference/DECISIONS.md`.
- **2026-05-07** — Stay on Python; resolve permission failure via arm64 Python install + TCC target correction. See `docs/reference/DECISIONS.md`.
- **2026-05-07** — Bootstrap orchestrator pattern adopted. See `docs/reference/DECISIONS.md`.

## Recent invariants

- **INV-003** — Auto-correction must skip when boundary not directly observed. Implemented via `_can_correct_next_word` flag in `KeyboardMonitor`. See `docs/reference/INVARIANTS.md`.
- **INV-001** — Daemon must run on native arm64 Python on Apple Silicon. See `docs/reference/INVARIANTS.md`.
- **INV-002** — TCC grants target CLI `bin/python3.X`, not `Python.app`. See `docs/reference/INVARIANTS.md`.

## Carry-overs for next session

- [ ] **Backspace into empty buffer not yet covered by INV-003.** When the user backspaces over text the daemon didn't write (typical after manual paste or moving back into existing text), buffer is already empty so no `clear()` fires and `_can_correct_next_word` stays True. Next word can mangle. Fix: in `_tap_callback`, when keycode is Backspace AND `_word_buffer._buffer` is empty → set flag False (treat as desync signal).
- [ ] **Ctrl-modifier shortcuts beyond hotkey not covered by INV-003.** E.g., terminal users hitting Ctrl+A (beginning of line), Ctrl+E (end of line), Ctrl+W (delete word). Same shape as Cmd-modifier branch in PR #19. Defer until user reports a real reproduction.
- [ ] **Hoist `CGEventKeyboardSetUnicodeString` import out of `_type_string` loop body** — minor cleanup carried over from session 3.
- [ ] **`test_get_active_app_returns_string` mock** — needed for headless CI; carried over.
- [ ] **`_is_stale()` precision** — count only `("check",)` items; carried over.
- [ ] **Cross-app replay-buffer leak** — discard buffer in `("clear",)` handler; carried over.
- [ ] **CI setup (GitHub Actions)** — 205-test safety net makes this very attractive; mock-frontmost prerequisite still standing.
- [ ] **Eventually delete `.venv-old-x86`** — rollback insurance, low priority.
- [ ] **Audit candidates not yet picked up:** per-app exclusion list UI; "hotkey to toggle enabled".

## Archive index

- `docs/archive/session-resume-history/2026-05.md` — sessions 2, 3, and 4 verbose retrospectives. Session 4 entry includes: 4-PR delegation chain (16 → 17 → 18 → 19), advisor-aided distinguishing of "cursor desync vs script-switch reset" hypotheses, the 272-pair false-positive enumeration table (latin↔russian), the upstream-PR misroute incident (gh defaulting to upstream when origin is a fork), and the user-corrected hypothesis pivot from elaborate desync theory back to the simpler observed truth.
