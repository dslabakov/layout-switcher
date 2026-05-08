# SESSION_RESUME — Layoutswitcher

> Living-layer state. Update on every `/save` (Q5 routes here for current state).
> Target size: ≤ 30k chars. If growing, archive older sessions to `docs/archive/session-resume-history/`.

---

## Current state (updated 2026-05-08, session 5 close)

**Discussion-only session.** No source changes. Daemon still on session-4 code (PR #19, commit `79f7f9e`); 205 tests; INV-003 (tail-of-word mangle gate) under production monitoring. User using daemon, will report regressions.

Session 5 explored adding on-the-fly spell-correction (separate from layout-switching): architecturally trivial in current pipeline (same `boundary trigger → check → backspace+retype`, just different engine in middle). Surveyed open-source niche via fork agent — closest analog is closed-source Charm ($9.99); FOSS Python-daemon for system-wide macOS spell correction does not exist. Recommended engine: `NSSpellChecker` via pyobjc (zero new deps, auto language detection, mostly free multilingual support).

Re-evaluated 2026-05-07 Swift-rejection in distribution context: that decision was personal-use-scoped. For community distribution, Swift objectively better (native `.app`, eliminates TCC-on-CLI-binary footgun); `pymorphy3` ceases to be blocker if NSSpellChecker takes over validity check. **Two-track strategy adopted (deferred until motivation):** Python prototype → use daily → spec accumulates → Swift port → open-source publication.

User explicitly deferred all action: «пока ничего не хочу делать». Findings captured in `docs/research/spell-correction-strategy.md`.

## In-flight (WIP, not yet merged/pushed)

- `.venv-old-x86` — backup of broken Intel/Rosetta venv at repo root. Carried over from session 3. Still safe to delete; deferred.
- No open feature branches; no unpushed commits beyond what `/save` produces.

## Recent decisions

- **2026-05-08 (session 5)** — Spell-correction & Swift-port: two-track strategy adopted (Python prototype → Swift port → publish), all action deferred. Scope-clarification of 2026-05-07: that decision was personal-use-scoped, not absolute. See `docs/reference/DECISIONS.md`.
- **2026-05-08 (late)** — Trust model: validate only when boundary directly observed. `_can_correct_next_word` flag covers mouse / cursor-move / app-switch / Cmd-modifier paths. PR #18 + #19. See `docs/reference/DECISIONS.md`.
- **2026-05-08** — Threading-fragility resolution via queue-based ownership (no locks). 4 PRs. See `docs/reference/DECISIONS.md`.
- **2026-05-07** — Stay on Python; resolve permission failure via arm64 Python install + TCC target correction. See `docs/reference/DECISIONS.md`.
- **2026-05-07** — Bootstrap orchestrator pattern adopted. See `docs/reference/DECISIONS.md`.

## Recent invariants

- **INV-003** — Auto-correction must skip when boundary not directly observed. Implemented via `_can_correct_next_word` flag in `KeyboardMonitor`. See `docs/reference/INVARIANTS.md`.
- **INV-001** — Daemon must run on native arm64 Python on Apple Silicon. See `docs/reference/INVARIANTS.md`.
- **INV-002** — TCC grants target CLI `bin/python3.X`, not `Python.app`. See `docs/reference/INVARIANTS.md`.

## Carry-overs for next session

- [ ] **Spell-correction Track 1 pickup** (when motivation returns) — prototype `spell_corrector.py` per spec in `docs/research/spell-correction-strategy.md` § 8. MVP: 4-8h Sonnet PR using `NSSpellChecker` via pyobjc, hooked after layout-check on boundary trigger, behind config flag.
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

- `docs/archive/session-resume-history/2026-05.md` — sessions 2, 3, 4, and 5 verbose retrospectives. Session 5 entry: discussion-only (no code changes), spell-correction architectural fit + competitive research inventory + NSSpellChecker engine recommendation + multilingual analysis + feature roadmap (5 groups for open-source distribution lens) + Swift-port reconsideration + pymorphy3 portability nuance + framing-error episode and correction + two-track strategy methodology. Session 4 entry includes: 4-PR delegation chain (16 → 17 → 18 → 19), advisor-aided distinguishing of "cursor desync vs script-switch reset" hypotheses, the 272-pair false-positive enumeration table (latin↔russian), the upstream-PR misroute incident (gh defaulting to upstream when origin is a fork), and the user-corrected hypothesis pivot from elaborate desync theory back to the simpler observed truth.
