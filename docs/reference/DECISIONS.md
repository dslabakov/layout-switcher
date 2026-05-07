# DECISIONS — architectural decision log

> Newest entries on TOP. Each entry: **Problem / Alternatives considered / Chose / Why / Artifacts**.
> Triggered when a non-routine architectural pivot occurs (per `/save` Q3).

---

## 2026-05-07 — Bootstrap: orchestrator pattern adopted

**Problem.** Forking moiz2306/layout-switcher for personal customization. Need a workflow that scales beyond ad-hoc commits, surfaces architectural pivots, and keeps upstream syncs cleanly diffable.

**Alternatives considered.**
- (a) Casual workflow: edit-commit-push directly on `main`, sync upstream with `git pull upstream main`.
- (b) Branch-per-task only: PRs but no orchestrator delegation.
- (c) Full orchestrator pattern (matches coronium-clone-iii / voice-adapt convention): main session = orchestrator only; agents do source edits; PRs reviewed at diff level.

**Chose.** (c). Strict orchestrator-only with read carve-outs adapted to Python project. Agent pipeline (issue-queue + opencode + verifier) deferred until project size justifies it.

**Why.**
- Consistency with other projects on this Mac (same mental model).
- Per-PR diff review forces explicit intent on every change.
- Sync workflow with upstream becomes auditable (`upstream-merge/<date>` branches with diff review).
- Even on solo project, INVARIANTS.md / DECISIONS.md / structure scale linearly — no harm in starting small.

**Artifacts.**
- `CLAUDE.md`
- `docs/reference/ORCHESTRATOR.md`
- `docs/reference/STRUCTURE.md`
- `docs/reference/COMMANDS.md`
- `docs/reference/UPSTREAM-SYNC.md`
- `docs/reference/INVARIANTS.md` (empty stub)
- This file (empty stub for future entries)
- `SESSION_RESUME.md`, `PLAN.md`, `ERRORS.md`, `HANDOFF.md` (empty stubs / templates)
- `.claude/commands/save.md` (Living-layer Q1-Q6 protocol)
- `.claude/commands/shrink-claude.md`
