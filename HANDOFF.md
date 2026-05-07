# Handoff

> Top-level boot script for the next Claude Code session. Terse, ~1-2 KB.
> Rotated at the end of each session — current contents archived to `docs/handoffs/YYYY-MM-DD-session-N-end.md`, then this file overwritten with fresh handoff for next session.

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

---

## Convention (how to use this file)

**Purpose:** terse boot script for next session. Reading time: < 5 minutes. Functions as "start here" pointer + delta from last session.

**Strict rules:**
1. **No duplication of content** that lives in `SESSION_RESUME.md`, `PLAN.md`, `DECISIONS.md`, `ERRORS.md`. Pointer + 1-line gloss only.
2. **Genuine added value sections:** `## Read first`, `## Delta`, `## Known traps`, `## How to start session N+1`.
3. **Target size:** under 2 KB. If growing, content belongs elsewhere.
4. **Rotation:** at the end of each session, orchestrator (a) archives this file's current contents to `docs/handoffs/YYYY-MM-DD-session-N-end.md`, (b) overwrites this file with fresh handoff for next session.

When this file is the empty/template version, it's a signal that the previous session ended without filing a fresh handoff — orchestrator falls through to the standard read-first list (CLAUDE.md → SESSION_RESUME.md → PLAN.md).
