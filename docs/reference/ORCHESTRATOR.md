# ORCHESTRATOR.md — Main session role spec

> Adopted at project bootstrap. Adapted from coronium-clone-iii / voice-adapt orchestrator pattern, scaled down to single-dev fork project.

## Role

Main session = **orchestrator only**. Plans, delegates, reviews PRs at diff level, calls advisor on high-stakes calls, closes the user-feedback loop.

**Worker agents do all source-file reading and editing.** They run on Sonnet by default; orchestrator escalates to Opus for high-stakes work.

---

## Read carve-outs

### Main session MAY read:
- `PLAN.md`, `SESSION_RESUME.md`, `ERRORS.md`, `HANDOFF.md`.
- `~/.claude/projects/<proj>/memory/MEMORY.md` and the memory files it indexes.
- `docs/**` (all documentation, handoffs, archive, reference).
- `gh pr diff <num>`, `gh pr view <num>`, `gh pr checks <num>`.
- Test logs, agent result messages.
- `git log`, `git status --short`, `git show <sha>` (commit metadata; not full source bodies of touched files).
- This file (`ORCHESTRATOR.md`).
- `requirements.txt` (a few lines is fine to glance at — but avoid reading source bodies).
- File names + line counts via `ls`/`wc -l`.

### Main session MUST NOT read:
- **Source files:** `src/**/*.py`, `tests/**/*.py`, `scripts/**/*.py`, `*.sh` bodies (`install.sh`, `setup.sh`).
- **Project config bodies:** `com.layout-switcher.plist`, `config.example.yaml`, `requirements.txt` (full body).
- **Build artifacts:** anything under `.venv/`, `__pycache__/`, `.pytest_cache/`.

### Main session MUST NOT write:
Any source or config file. **Always delegate.**

### One-shot exceptions:
- The initial setup that creates this `ORCHESTRATOR.md` and the surrounding doc structure is performed by the orchestrator directly (these are docs, not source).
- Single-line fixes in `docs/**` may be performed directly by orchestrator.

After bootstrap, the rule is hard for source/config files.

---

## Model selection

| Class | Default model | When to use |
|---|---|---|
| **Default execution** | Sonnet | log/grep, doc/handoff updates, mechanical refactor with clear scope, build-error fix with concrete stack trace, PR-diff review, routine commits, test writing for spec'd behavior |
| **High-stakes** | Opus | architecture changes, root-cause hunting on ambiguous bugs (CGEventTap timing, pyobjc threading, accessibility permissions), security/keychain work, prompt-engineering with cost or quality stakes, decisions where "wrong choice costs hours" |
| **Open-ended research** | Fork (no `subagent_type`) | "where is X used", multi-file lookups, surveying repo state — keeps tool noise out of orchestrator context |

**When unsure: call advisor with full context before launching.**

### Model override syntax
When invoking the `Agent` tool, set `model: "sonnet"` or `model: "opus"` explicitly. Do not rely on inheritance — make the choice visible.

---

## GitHub workflow

**One task = one branch = one PR.** See `CLAUDE.md` § GitHub workflow for branch-naming convention.

### PR review at orchestrator level

The orchestrator reviews via `gh pr diff <num>`. **This is allowed** — it is reading the diff produced by the agent, not the source files directly. The diff exposes only the changed lines plus minimal context.

If a diff requires reading surrounding source to evaluate, send a follow-up brief to a Sonnet agent: "review PR #N for issue X, report back."

### Merge gates

| PR class | Approval | Action |
|---|---|---|
| **Low-risk** (docs, tests, isolated mechanical refactor, formatting) | local pytest green | Orchestrator auto-merges |
| **Medium-risk** (feature work, non-critical fixes, refactor) | local pytest green + orchestrator diff-review | Orchestrator merges |
| **High-risk** (CGEventTap changes, accessibility permission flow, install/uninstall scripts, plist) | local smoke + orchestrator review + **user approval** | User merges, or instructs orchestrator |

When in doubt about risk class: ask user.

---

## Standard Operating Procedures

### Fix (concrete bug with known root cause)
1. Brief Sonnet agent: file path, line numbers (from ERRORS.md or stack trace), expected change, test to add.
2. Worktree isolation.
3. Agent commits + opens PR.
4. Orchestrator reviews diff + test logs.
5. Merge or send back for revision.

### Feature (additive change)
1. Brief Sonnet agent: scope, files touched, acceptance criteria.
2. For high-stakes (touching CGEventTap, plist, install) — Opus agent with `isolation: worktree`.
3. Agent ships PR.
4. Orchestrator reviews + smoke (run `python3 -m src.main` in foreground, verify no regression on a few test inputs).
5. Merge.

### Upstream sync (most common ongoing flow)
1. Orchestrator runs `git fetch upstream`.
2. Reviews `git log --oneline HEAD..upstream/main` to see what's new.
3. Branches `upstream-merge/YYYY-MM-DD` from local `main`.
4. Sonnet agent runs `git merge upstream/main` (or rebase, decide first).
5. If conflicts: agent resolves, ideally preferring local logic + applying upstream's bug fixes.
6. Agent runs `pytest`, reports.
7. Orchestrator reviews diff + test result.
8. Merge to `main`, push.

Full procedure: `docs/reference/UPSTREAM-SYNC.md`.

### Refactor (cross-cutting)
1. Opus agent in fork mode: produce migration plan as a written doc.
2. Orchestrator + advisor review the plan.
3. Sonnet agents execute per-module in parallel worktrees if independent.
4. Each PR reviewed independently.

### Doc refresh
1. Sonnet agent reads project state (commits since last refresh, files added/removed, env config).
2. Updates targeted doc on its own branch.
3. PR reviewed at diff level.

### Audit (security, accessibility, performance)
1. Pick an agent type (general-purpose Sonnet for most; Opus for security review).
2. Launch agent **without** worktree (read-only).
3. Receive findings; file as `docs/audits/<date>-<topic>.md` via a follow-up Sonnet doc-write task if findings are extensive.
4. For each finding: priority + fix strategy + spawn fix task.

---

## Anti-patterns

- ✗ Reading source files in main session "just to check one thing."
- ✗ Writing a "small fix" directly in main session for source/config.
- ✗ Approving an agent PR without reading the diff.
- ✗ Trusting an agent's "done" message without verifying via test logs / `git show`.
- ✗ Bundling unrelated work in one task → unreviewable PR.
- ✗ Skipping advisor before high-stakes architectural decisions.
- ✗ Defaulting to Opus for everything (cost/speed) or Sonnet for everything (depth).
- ✗ Merging upstream directly into `main` without going through `upstream-merge/<date>` branch.
- ✗ Deploying via `launchctl bootstrap` without first running tests + foreground smoke.
- ✗ Bypassing accessibility permission flow without acknowledging the runtime risk.

---

## Project-specific guards

- **CGEventTap is privileged**: untested changes can freeze keyboard input system-wide. Always test in foreground first (`python3 -m src.main`), not via launchd.
- **Accessibility permission**: required by macOS for the event tap. Test with permission granted **and** revoked (graceful-degradation expected).
- **launchd plist placeholders** (`__VENV_PYTHON__`, etc.) are substituted by `setup.sh`. Don't commit substituted plist.
- **pymorphy3 / wordlist data is large** and lives outside repo. Don't `git add` `.config/` or `.venv/` directories.
- **Architectural invariants** (CLAUDE.md INVARIANTS section + `docs/reference/INVARIANTS.md`) cannot be removed without meeting the stated removal condition.

---

## When to call advisor (orchestrator-side)

- Before committing to a multi-task plan.
- Before launching Opus on something ambiguous.
- When two reasonable approaches exist and user input doesn't disambiguate.
- When agent results conflict with prior knowledge in PLAN.md / ERRORS.md / DECISIONS.md.
- Before declaring a multi-PR initiative "done."
- When considering a change of approach mid-flight.

The advisor sees full context — task description, every tool call, every result. Use it.

---

## Bootstrap state (2026-05-07, project init)

- Forked from `moiz2306/layout-switcher` at HEAD `2e7ff6c`.
- No CI yet. No agent pipeline yet (single-dev project, may be added later if scale justifies).
- `main` tracks `origin/main`; `upstream` configured.
- Bootstrap docs: this file + CLAUDE.md + STRUCTURE / COMMANDS / DECISIONS / INVARIANTS / UPSTREAM-SYNC stubs.

Subsequent sessions inherit the orchestrator role automatically via CLAUDE.md.
