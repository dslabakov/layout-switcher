# Handoff (archived from session 1 end, 2026-05-07)

> Archived by `/save` at end of session 2 (2026-05-07). Was the boot script handed off from session 1 (bootstrap) to session 2.

## Status

**Bootstrap session (2026-05-07).** Fork created, orchestrator pattern infrastructure deployed. No code changes yet.

## Read first

1. `CLAUDE.md` — project description + orchestrator-only mode + read carve-outs + reference index.
2. `docs/reference/ORCHESTRATOR.md` — full orchestrator role spec.
3. `SESSION_RESUME.md` — current state (bootstrap, carry-overs).
4. `PLAN.md` → "Next Session — Start Here" — what to do first.

## Delta (what's new since last session)

Bootstrap — nothing was here before this session. All conventions deployed in a single bootstrap pass.

## How to start the next session

1. Run `git status` to see if bootstrap docs are committed yet — if untracked, first action is the bootstrap commit.
2. Smoke-test the upstream-as-forked: `bash setup.sh && source .venv/bin/activate && python3 -m src.main` — verify CGEventTap activates (requires Accessibility permission), test a few RU/EN auto-corrections.
3. Identify first feature/fix candidate (see Active backlog in PLAN.md).
4. Delegate via Sonnet agent on a `feature/<name>` branch.

## Known traps

- macOS Accessibility permission required before first run — terminal binary AND python interpreter need it.
- CGEventTap can freeze keyboard input system-wide if buggy — always test in foreground first, never deploy via launchd untested.
- Don't `git pull upstream main` directly into local main — always via `upstream-merge/<date>` branch + diff review (see `docs/reference/UPSTREAM-SYNC.md`).
- This is a fork — additive changes preferred over rewrites to keep upstream syncs clean.
