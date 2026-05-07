# SESSION_RESUME — Layoutswitcher

> Living-layer state. Update on every `/save` (Q5 routes here for current state).
> Target size: ≤ 30k chars. If growing, archive older sessions to `docs/archive/session-resume-history/`.

---

## Current state (updated 2026-05-07)

Bootstrap session — fork created from `moiz2306/layout-switcher` @ `2e7ff6c`, orchestrator pattern infrastructure deployed. No code changes yet; project conventions only.

## In-flight (WIP, not yet merged/pushed)

- All bootstrap docs untracked in working tree (`CLAUDE.md`, `docs/`, etc.) — to be committed as the first project-conventions commit.

## Recent decisions

- **2026-05-07** — Bootstrap orchestrator pattern adopted. See `docs/reference/DECISIONS.md` top entry.

## Carry-overs for next session

- [ ] Commit the bootstrap docs (single commit: `chore: project conventions bootstrap`).
- [ ] Decide first feature / fix to delegate via orchestrator pattern. Likely candidates:
  - Audit upstream code for personal-fit gaps (what behavior would I want different).
  - Add a "Quick disable" toggle if missing.
  - Add custom hotkey configuration if not yet exposed.
  - Smoke-test current upstream as installed (run `setup.sh` + foreground `python3 -m src.main`).
- [ ] First smoke: install via `setup.sh`, run in foreground, verify auto-correction works on a few RU/EN test inputs. **Before** any source modification.

## Archive index

*(no chunks yet — first archive will land when SESSION_RESUME exceeds ~30k chars)*

- `docs/archive/session-resume-history/` — empty.
