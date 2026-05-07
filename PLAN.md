# PLAN — Layoutswitcher

> Prospective ("what to do next"), NOT retrospective. Per-session retrospectives live in `SESSION_RESUME.md`.
> Target size: ≤ 20k chars.

---

## Next Session — Start Here

1. **Daemon restart pending:** `show_notifications` shipped (PR #1 merged 2026-05-07, commit `8db1531`). Code is on local `main` but the running daemon still has the old binary loaded — restart via `launchctl bootout gui/$(id -u)/com.layout-switcher && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.layout-switcher.plist` to activate. Toggle the flag in the Settings UI to verify (`ghbdtn ` → notification appears).
2. **Pick next feature** from "Active backlog" or audit's "Personal-fit candidates" (`docs/audits/upstream-2026-05-07.md`, table § 4). Recommended next: fix `config.hotkey_convert` ignored bug (S, additive) OR diagnostic-mode logging (S, would 10×-up E-0001-class debugging).

## Active backlog (refreshed)

- [ ] **Daemon restart** to activate `show_notifications` (see Next Session step 1). User-side action.
- [ ] Fix `config.hotkey_convert` ignored bug — UI/config setting is read for display only; actual hotkey is hardcoded at `keyboard_monitor.py:256-259`. Audit § 3 BUG 1.
- [ ] `setup.sh` audit — currently assumes brew Python; needs to handle python.org arm64 install (or document arm64 Python prerequisite). Otherwise `setup.sh` rerun re-creates the broken state we just escaped from.
- [ ] Diagnostic-mode logging — log RU/EN classification decisions / when correction was suppressed; would have made `E-0001` debug 10× faster.
- [ ] Eventually delete `.venv-old-x86` backup (keeping ~ a few days as rollback insurance).

## Pending — pick when needed

- [ ] CI setup (GitHub Actions, run pytest on PR). Currently no CI.
- [ ] Decide on agent pipeline adoption — small project may not justify; revisit if delegation volume picks up.
- [ ] `docs/reference/ENV.md` if env-vars / paths get non-trivial.

## Architectural findings (cumulative across pilots)

*(none yet — load-bearing learnings have promoted to INV-001/INV-002 in `docs/reference/INVARIANTS.md`. This section will fill if a future cumulative truth doesn't fit a single invariant.)*

## Pending — pick when needed

- [ ] CI setup (GitHub Actions, run pytest on PR). Currently no CI.
- [ ] Decide on agent pipeline adoption — small project may not justify; revisit if delegation volume picks up.
- [ ] `docs/reference/ENV.md` if env-vars / paths get non-trivial.
- [ ] Add a "diagnostic mode" to log decisions (RU/EN classification, when correction was suppressed) for debugging.

## Architectural findings (cumulative across pilots)

*(none yet — this section accumulates load-bearing learnings as project matures)*

---

## Archive index

*(no chunks yet — first archive triggers if PLAN exceeds ~20k chars)*

- `docs/archive/plan-shipped-phases/` — empty.
