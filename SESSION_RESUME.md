# SESSION_RESUME — Layoutswitcher

> Living-layer state. Update on every `/save` (Q5 routes here for current state).
> Target size: ≤ 30k chars. If growing, archive older sessions to `docs/archive/session-resume-history/`.

---

## Current state (updated 2026-05-08)

**Daemon hardened.** Session 3 shipped a 14+1 PR cleanup campaign (PR-A through PR-J + 2 hotfixes + a follow-up commit on PR-I). All 4 audit-flagged threading fragilities are closed via the queue-based ownership pattern (see `docs/reference/DECISIONS.md` § 2026-05-08). Defense-in-depth in place: permission watchdog (orange icon on TCC revocation), `_tap_callback` + `_detection_worker` exception swallowing, TCC preflight guards in `correct()`/`undo()`. Install scripts now enforce INV-001. `setup.sh` rerun on Apple Silicon refuses Intel/Rosetta Python.

**Test suite: 117 → 195** (+78). Audit § 5 coverage gaps closed (CGEventPost posting sequence, replay drain, app_filter integration). Diagnostic logging available via `debug: true` in `~/.config/layout-switcher/config.yaml` or `--debug` CLI flag — currently ON in user's config.

**Two pre-existing upstream bugs** found during interactive smoke-test of the campaign and fixed: E-0002 (synthetic events inheriting modifier flags from physically-held keys) and E-0003 (Tab in word boundaries triggering phantom corrections on Cmd+Tab). Both regression-guarded by tests.

## In-flight (WIP, not yet merged/pushed)

- `.venv-old-x86` — backup of the broken Intel/Rosetta venv at repo root. Safe to delete now (sessions 2 + 3 prove fresh setup works); kept for a few more days as rollback insurance. Not committed.
- No open feature branches; no unpushed commits beyond what `/save` produces.

## Recent decisions

- **2026-05-08** — Threading-fragility resolution via queue-based ownership (no locks). 4 PRs (E + EX + EY + G). See `docs/reference/DECISIONS.md`.
- **2026-05-07** — Stay on Python; resolve permission failure via arm64 Python install + TCC target correction. See `docs/reference/DECISIONS.md`.
- **2026-05-07** — Bootstrap orchestrator pattern adopted. See `docs/reference/DECISIONS.md`.

## Recent invariants

- **INV-001** — Daemon must run on native arm64 Python on Apple Silicon. NOW ENFORCED at install time by `setup.sh` (PR-I). See `docs/reference/INVARIANTS.md`.
- **INV-002** — TCC grants target CLI `bin/python3.X`, not `Python.app`. See `docs/reference/INVARIANTS.md`.

## Carry-overs for next session

- [ ] **Hoist `CGEventKeyboardSetUnicodeString` import out of `_type_string` loop body** — currently re-imported on every char (no functional issue, minor cleanup; PR-J agent flagged this).
- [ ] **`test_get_active_app_returns_string` in `test_app_filter.py`** — calls real `NSWorkspace.frontmostApplication()`; will fail in headless CI (when GitHub Actions is added). Replace with mocked frontmost.
- [ ] **`_is_stale()` precision improvement** — currently `not self._detection_queue.empty()`; with `("complete",)` enqueues now firing on every word boundary, queue has more items. Iterate `queue.queue` and count only `("check", ...)` items for sharper staleness signal. Marginal user-facing impact today.
- [ ] **Cross-app replay leak** — if user types during a correction in app A, then Cmd+Tab to app B before worker drains, replay-buffer chars get typed into app B on next correction trigger. Pre-existing; not in audit. Fix: discard `_replay_buffer` in the `("clear",)` handler instead of leaving it for next drain.
- [ ] **CI setup (GitHub Actions, run pytest on PR)** — Pending list item; the 195-test safety net makes this more attractive than at session-2 end. Mock `frontmostApplication` test (above) is a prerequisite for headless CI to be green.
- [ ] **Audit candidates not yet picked up:** per-app exclusion list UI; "hotkey to toggle enabled" (separate hotkey to pause/resume).
- [ ] **Eventually delete `.venv-old-x86`** — rollback insurance, low priority.

## Archive index

- `docs/archive/session-resume-history/2026-05.md` — sessions 2 and 3 verbose sagas (E-0001 diagnostic walk; campaign of 14+1 PRs with smoke-test methodology + wordlist-pollution incident + 2 pre-existing bug discoveries).
