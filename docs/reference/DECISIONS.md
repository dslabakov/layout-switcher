# DECISIONS — architectural decision log

> Newest entries on TOP. Each entry: **Problem / Alternatives considered / Chose / Why / Artifacts**.
> Triggered when a non-routine architectural pivot occurs (per `/save` Q3).

---

## 2026-05-07 — Stay on Python; fix via arm64 install + TCC target correction (no .app rebuild, no Swift rewrite)

**Problem.** Daemon under launchd logged `Permissions missing, monitor not started.` despite Accessibility + Input Monitoring being granted to `Python.app` in System Settings. After multiple permission re-grants, ad-hoc and Dev-cert re-signs of brew Python.app, and a TCC reset, the failure persisted. Considered whether to architecturally pivot off Python.

**Alternatives considered.**
- (a) **py2app `.app` bundle** — embed brew Python + deps into `Layoutswitcher.app` with stable bundle ID. Days of delegations; py2app's last release classifies up to Python 3.13 (3.14 unsupported on paper, installs but untested). Strong guess that bundling fixes the launchd-paradox, not proven.
- (b) **Swift + AppKit native rewrite** — drop Python entirely; weeks of work; loses pymorphy3 (no equivalent Russian morphology library in Swift; `NaturalLanguage.framework` is qualitatively weaker for our needs).
- (c) **Hammerspoon + Lua** — config on top of an existing signed automation host; no `.app` to maintain, but Lua has no morphology library, would need pymorphy3 helper subprocess.
- (d) **PyInstaller / Briefcase `.app` bundles** — alternatives to py2app, similar trade-offs.
- (e) **Diagnose the launchd-paradox first** — spend an hour on root-cause without architectural change; revisit pivots only if intractable.

**Chose.** (e) → confirmed root cause is environmental (Rosetta translation under launchd + responsible-process TCC attribution + 4 stale TCC entries from earlier re-signs). Fix delivered without a single source-file change: install arm64 Python (python.org universal2), recreate venv with `arch -arm64`, `tccutil reset Accessibility|ListenEvent|PostEvent org.python.python`, grant permissions to `bin/python3.14` (CLI binary, not Python.app).

**Why.**
- Days/weeks of architectural work avoided.
- Discovered three concrete pieces of load-bearing knowledge (INV-001 arm64 Python; INV-002 TCC target = CLI binary; the TCC log streaming diagnostic recipe) that survive into future sessions and would have re-bitten under any architectural pivot too.
- py2app option remains available if needed later — postponed, not rejected. Triggers for revisit: (i) Apple breaks the responsible-process attribution path, (ii) we want our own name in System Settings, (iii) we want isolation from brew updates / python.org installer drift.

**Artifacts.**
- `ERRORS.md` § E-0001 — full diagnostic trail (Rosetta detection via `vmmap`, TCC log streaming, attribution analysis).
- `docs/reference/INVARIANTS.md` § INV-001, INV-002.
- `docs/archive/session-resume-history/2026-05.md` — verbose saga retrospective with timeline and lessons.
- `docs/audits/upstream-2026-05-07.md` — informed first-feature pick after this issue resolved.

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
