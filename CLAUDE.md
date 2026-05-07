# Layoutswitcher — CLAUDE.md

## PROJECT

**Type:** macOS keyboard-layout corrector (auto-detects wrong-layout typing, e.g. `ghbdtn` → `привет`).
**Origin:** Fork of [moiz2306/layout-switcher](https://github.com/moiz2306/layout-switcher) (MIT).
**My fork:** [dslabakov/layout-switcher](https://github.com/dslabakov/layout-switcher).
**Stack:** Python 3 + pyobjc (Quartz CGEventTap, Cocoa NSStatusItem), pymorphy3 (RU morphology), pyyaml, pytest.
**Runs as:** launchd LaunchAgent (`com.layout-switcher.plist`) — daemon-style, menu-bar UI, always-on.
**User:** Single person, personal use. Not distributed beyond own Mac.

## ORCHESTRATOR MODE

Main session = **orchestrator only**. Plans, delegates, reviews PRs at diff level, calls advisor on high-stakes calls. Worker agents do source-file reading and editing on Sonnet by default; orchestrator escalates to Opus for high-stakes work.

Rationale: even on a small solo project, the discipline keeps main session context clean, makes intent explicit (issue → branch → PR → diff review), and surfaces architectural pivots through DECISIONS.md rather than buried in commits.

**Read carve-outs:**
- **MAY read:** `PLAN.md`, `SESSION_RESUME.md`, `ERRORS.md`, `MEMORY.md`, `docs/**`, `gh pr diff/view/checks`, agent results, test logs, `git log/status/show` (metadata).
- **MUST NOT read:** `*.py`, `*.sh` source bodies, `setup.sh`/`install.sh` bodies, `com.layout-switcher.plist`, `requirements.txt` body. Names + line counts via `ls`/`wc -l` are fine.
- **MUST NOT write** any source/config file. Always delegate.

**Single-line trivial-fix exception:** if a fix is a single line in a doc/config, write it directly. For anything that touches Python source — delegate.

## Model selection (when invoking `Agent`)

| Class | Default | When |
|---|---|---|
| **Default execution** | Sonnet | log/grep, doc/handoff updates, mechanical refactor with clear scope, build-error fix with concrete stack trace, PR-diff review, routine commits, test writing for spec'd behavior |
| **High-stakes** | Opus | architecture changes, root-cause hunting on ambiguous bugs (event-tap, IPC, pyobjc threading), security/permissions/keychain, prompt-engineering with cost or quality stakes, decisions where "wrong choice costs hours" |
| **Open-ended research** | Fork (no `subagent_type`) | "where is X used", multi-file lookups — keeps tool noise out of orchestrator context, shares prompt cache |

**When unsure → call advisor before launching.** Always set `model:` explicitly.

## GitHub workflow

**One task = one branch = one PR.**

- Branch naming:
  - `feature/<short-name>` for own additions / new features.
  - `fix/<short-name>` for bug fixes.
  - `task/<short-name>` for orchestrator-dispatched mechanical work.
  - `upstream-merge/<YYYY-MM-DD>` for syncing from upstream `moiz2306/layout-switcher`.
  - `wip/<topic>` for in-progress / parked diagnostic work.
- Worktree isolation by default for any task that edits files.
- Agent pushes branch + creates PR via `gh pr create`.

### Merge gates (no CI configured yet)

| PR class | Approval | Action |
|---|---|---|
| Low-risk (docs, tests, isolated mechanical refactor) | local pytest green | Orchestrator auto-merges |
| Medium-risk (feature work, refactor) | local pytest green + orchestrator diff-review | Orchestrator merges |
| High-risk (event-tap, accessibility permissions, install/uninstall scripts, plist) | local smoke + orchestrator review + **user approval** | User merges, or instructs orchestrator |

**No CI yet.** Tests run locally via `pytest`. If we add GitHub Actions later, this rubric tightens (CI must be green for medium+).

## Upstream sync workflow

See `docs/reference/UPSTREAM-SYNC.md` for the full procedure. TL;DR:

```bash
git fetch upstream
git log --oneline HEAD..upstream/main          # what's new
git checkout -b upstream-merge/YYYY-MM-DD
git merge upstream/main                         # OR rebase if local commits should stay on top
# resolve conflicts, run pytest, commit, push, open PR for review even if it's me-merging-me
```

Never `git pull upstream main` directly into local main — always via a sync branch + PR for diff review.

## Anti-patterns (forbidden in main session)

- ✗ Reading source `.py` files in main session "just to check one thing."
- ✗ Writing a "small fix" directly to source.
- ✗ Approving an agent PR without reading the diff.
- ✗ Merging upstream into main without going through a `upstream-merge/` branch + diff review.
- ✗ Bundling unrelated work in one task → unreviewable PR.
- ✗ Skipping advisor on high-stakes architectural decisions.
- ✗ Defaulting to Opus for everything (cost/speed) or Sonnet for everything (depth).
- ✗ Running daemon (`launchctl bootstrap …`) without first verifying the source change builds + tests pass.

## Project-specific guards

- **Accessibility permission** — the app uses CGEventTap which requires Accessibility access in macOS System Settings. Any change that touches `keyboard_monitor.py` or `auto_corrector.py` must be tested with permission granted **and** revoked (graceful degradation expected).
- **CGEventTap is privileged** — runaway code in the event tap can freeze keyboard input system-wide. Don't deploy untested changes via launchd. Test in foreground first (`python3 -m src.main`).
- **launchd plist `__VENV_PYTHON__` / `__SRC_MAIN__` / `__LOG_DIR__` placeholders** are filled by `setup.sh` at install time. Do not commit a plist with absolute paths substituted in.
- **`pymorphy3` data files are large** — they live under `~/.config/layout-switcher/` (or wherever the wordlist build writes), not in repo. Don't accidentally commit them.
- **`config.example.yaml`** is the canonical template. Real config lives at `~/.config/layout-switcher/config.yaml` (per-user, gitignored by being outside repo). Don't commit a personalized config to repo.
- **Forked nature:** when modifying upstream code paths, prefer additive changes (new modules / new options) over rewrites — easier to keep upstream merges clean. If a rewrite is necessary, document in `docs/reference/DECISIONS.md` why we diverged.

## ARCHITECTURAL INVARIANTS — do not remove without re-derivation

> Load-bearing decisions. Removing any requires meeting the stated removal condition.
> See `docs/reference/INVARIANTS.md` for full motivation history.

- **INV-001:** Daemon must run on **native arm64 Python** on Apple Silicon. Intel Homebrew Python (`/usr/local/Cellar/...`) is forbidden — runs under Rosetta and breaks launchd-TCC. When recreating the venv on Apple Silicon, force `arch -arm64` for both `python -m venv` and `pip install` (Claude Code's Bash session is x86_64). See `docs/reference/INVARIANTS.md`.
- **INV-002:** TCC grants (Accessibility + Input Monitoring) must target the **CLI binary** `/Library/Frameworks/.../bin/python3.X`, NOT `Python.app`. macOS TCC attributes to the responsible process (first non-launchd in exec chain), and the CLI launcher is what gets attributed — the `Python.app` re-exec is the requesting process. See `docs/reference/INVARIANTS.md`.

## AT SESSION START (mandatory)

1. Read `PLAN.md` — current status + Next Session — Start Here pointer.
2. Read `SESSION_RESUME.md` — what was done last session.
3. Read `HANDOFF.md` — boot-script for next session (or fall through to standard list if empty).
4. Read `ERRORS.md` if encountering bugs.
5. Report: "Ready. Continuing with [current task]."

## REFERENCE MATERIALS (read on demand)

| File | When |
|---|---|
| **`docs/reference/ORCHESTRATOR.md`** | Always at session start (orchestrator role spec) |
| `PLAN.md` | Always at session start |
| `SESSION_RESUME.md` | When resuming work |
| `ERRORS.md` | Always at session start + when encountering bugs |
| `HANDOFF.md` | Boot script (or pass-through if empty) |
| `docs/reference/DECISIONS.md` | For architectural questions |
| `docs/reference/STRUCTURE.md` | For finding files |
| `docs/reference/COMMANDS.md` | For build/install/run commands |
| `docs/reference/UPSTREAM-SYNC.md` | When syncing from upstream |
| `docs/reference/INVARIANTS.md` | Context for invariants in CLAUDE.md |
| `docs/handoffs/` | Past per-session boot scripts (archived) |
| `docs/archive/session-resume-history/` | Archived session retrospectives |
| `docs/archive/plan-shipped-phases/` | Archived per-session priority logs |

## WORKFLOW RULES

- Max 2 clarifying questions if unclear.
- Don't try same solution more than 2 times — call advisor.
- Don't rewrite working code without reason.
- After each task: update PLAN.md (only "Next Session — Start Here" + "Active backlog (refreshed)" — no per-session priority blocks per /save 2.0 rule).
- Non-trivial error → ERRORS.md.
- Architectural choice → ask user → `docs/reference/DECISIONS.md`.
- Run `/save` at session end — it triages content via Q1-Q6 routing into the right files.
