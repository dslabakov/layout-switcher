# docs/handoffs/

Per-session boot scripts archived after rotation.

## What's here

Each file = the top-level `HANDOFF.md` content as it stood at the end of one session, archived when the next session's `HANDOFF.md` replaced it.

Naming: `YYYY-MM-DD-session-N-end.md` (or `YYYY-MM-DD-<topic-slug>.md` if session was strongly themed).

These are historical artifacts — useful for reconstructing session-by-session reading paths, but **not** the place to look for current state. For current state see `SESSION_RESUME.md` top entry + `PLAN.md` top entry.

## Convention recap (full version in top-level `HANDOFF.md`)

- Top-level `HANDOFF.md` = current session boot script (~1-2 KB, terse pointer + delta).
- At end of each session: orchestrator archives current `HANDOFF.md` here, then overwrites top-level with a fresh one for the next session.
- This file is documentation of the directory itself.

## Don't archive here

- Per-spec docs (those live in `docs/specs/` or archived there if any).
- Session retrospectives (those live in `SESSION_RESUME.md`, with rolling archive in `docs/archive/session-resume-history/`).
