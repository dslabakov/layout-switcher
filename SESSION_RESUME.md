# SESSION_RESUME — Layoutswitcher

> Living-layer state. Update on every `/save` (Q5 routes here for current state).
> Target size: ≤ 30k chars. If growing, archive older sessions to `docs/archive/session-resume-history/`.

---

## Current state (updated 2026-05-07)

**Daemon operational.** Auto-correction verified working end-to-end (`ghbdtn ` → `привет ` confirmed by user). LaunchAgent runs on **native arm64 python.org Python 3.14.4** at `/Library/Frameworks/Python.framework/Versions/3.14/`, with Accessibility + Input Monitoring granted to the **CLI binary** `bin/python3.14` (per INV-002). Bootstrap is over — ready for first feature delegation.

**Audit done.** Report at `docs/audits/upstream-2026-05-07.md` — full code map, behavior trace, code-quality observations (3 threading races, `config.hotkey_convert` ignored bug, `config.show_notifications` no-op stub), 6 personal-fit candidates ranked S/M/L. Recommended first delegation: wire up `show_notifications` (small, safe, valuable, doesn't touch CGEventTap).

## In-flight (WIP, not yet merged/pushed)

- `.venv-old-x86` — backup of the broken Intel/Rosetta venv at repo root. Keep ~ a few days as rollback insurance, then delete. Not committed (gitignored via `.venv*`-style pattern).
- No open feature branches; no unpushed commits beyond what `/save` produces.

## Recent decisions

- **2026-05-07** — Stay on Python; resolve permission failure via arm64 Python install + TCC target correction. Rejected py2app, PyInstaller, Briefcase, Hammerspoon, Swift rewrite. See `docs/reference/DECISIONS.md`.
- **2026-05-07** — Bootstrap orchestrator pattern adopted. See `docs/reference/DECISIONS.md`.

## Recent invariants

- **INV-001** — Daemon must run on native arm64 Python on Apple Silicon. See `docs/reference/INVARIANTS.md`.
- **INV-002** — TCC grants target CLI `bin/python3.X`, not `Python.app`. See `docs/reference/INVARIANTS.md`.

## Carry-overs for next session

- [ ] First feature delegation: wire `show_notifications` (audit recommendation) on `feature/notifications` via Sonnet agent in worktree isolation.
- [ ] `setup.sh` audit — currently assumes brew Python; needs to either bake in arm64 Python prerequisite or document it in `README.md` / `setup.sh` preamble. Without this, a `setup.sh` rerun re-creates the broken state.
- [ ] Diagnostic-mode logging (audit's idea) — log RU/EN classification decisions and when correction was suppressed; would have made `E-0001` debug 10× faster.
- [ ] Eventually delete `.venv-old-x86` backup (rollback insurance, low priority).

## Archive index

- `docs/archive/session-resume-history/2026-05.md` — session 2 verbose saga (E-0001 diagnostic walk, lessons, methodology evolutions).
