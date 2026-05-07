# PLAN — Layoutswitcher

> Prospective ("what to do next"), NOT retrospective. Per-session retrospectives live in `SESSION_RESUME.md`.
> Target size: ≤ 20k chars.

---

## Next Session — Start Here

1. **Smoke the upstream as-is** before any modification — install, run in foreground, verify auto-correction works for a few RU/EN test inputs.
2. **Commit the bootstrap docs** as a single commit `chore: project conventions bootstrap` if not yet done.
3. **Identify first feature gap** — what behavior would I want changed vs upstream? Document in this file's Active backlog.

## Active backlog (refreshed)

- [ ] Local install + foreground smoke (Accessibility permission flow).
- [ ] Audit upstream behavior — list what's good / what to change for personal fit.
- [ ] First feature/fix delegation via orchestrator pattern.

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
