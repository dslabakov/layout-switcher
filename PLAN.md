# PLAN — Layoutswitcher

> Prospective ("what to do next"), NOT retrospective. Per-session retrospectives live in `SESSION_RESUME.md`.
> Target size: ≤ 20k chars.

---

## Next Session — Start Here

1. **Read audit report** at `docs/audits/upstream-2026-05-07.md` for full code map + bug list + feature candidates.
2. **First-feature pick:** audit recommends wiring `config.show_notifications` (currently no-op stub at `keyboard_monitor.py` post-correction path) — small, safe, valuable. Branch `feature/notifications`, delegate to Sonnet.
3. **Alternative first-features** if you want a different scope: fix `config.hotkey_convert` ignored bug (hardcoded at `keyboard_monitor.py:256-259`), add diagnostic-mode logging, or per-app exclusion list.

## Active backlog (refreshed)

- [ ] First feature delegation: wire `show_notifications` (or pick from audit's "Personal-fit candidates" section).
- [ ] `setup.sh` audit — currently assumes brew Python; needs to handle python.org arm64 install (or document arm64 Python prerequisite). Otherwise `setup.sh` rerun re-creates the broken state we just escaped from.
- [ ] Diagnostic-mode logging (audit's idea) — log RU/EN classification decisions / when correction was suppressed; would have made `E-0001` debug 10× faster.
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
