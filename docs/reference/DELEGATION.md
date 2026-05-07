# DELEGATION.md — Standard agent prompt building blocks

> Reusable snippets for delegating worktree-isolated Sonnet/Opus agents.
> When writing a delegation prompt, copy the relevant blocks below verbatim.
> Reduces drift between prompts and saves orchestrator time.

---

## 1. No-destructive-commands block (always include)

Every agent that runs Bash needs the system-state hazard list. Adapt the
"touching `~/.config/layout-switcher/`" line to the specific PR if its tests
legitimately need to write to that path (none so far do — tests should always
use `tmp_path` or similar).

```
## ⛔ NEVER run destructive system commands

This daemon depends on macOS TCC and launchd state. You are in a separate
worktree from main. DO NOT run any of:

- `tccutil reset …`, `launchctl bootout|bootstrap|kickstart`
- `codesign …`, `pkill -f Python`, `killall Python`
- `rm -rf .venv*`, `rm` on anything outside your worktree
- `git push --force`, `git reset --hard`
- Touching `~/Library/LaunchAgents/com.layout-switcher.plist` or
  `~/.config/layout-switcher/`
- **DO NOT run `python3 -m src.main`** — launchd daemon is running on
  `main` simultaneously; double CGEventTap registration would freeze
  keyboard input system-wide.

If a destructive command seems needed — STOP and report back. Orchestrator
decides.
```

**Memory backing:** the rule "any agent touching TCC/launchd/codesign needs an
explicit no-destructive block at top of prompt" is a saved feedback memory
(`feedback_diagnostic_agent_destructive_commands.md`).

---

## 2. Worktree wordlist trap (always include for any pytest-running agent)

`data/en_wordlist.txt` is gitignored — built by `install.sh` at install time
from `/usr/share/dict/words` + `tech_terms`. A fresh worktree is missing it;
pytest fails **4 false-positive** tests in `test_language_detector.py` and
`test_integration.py` (e.g. `is_english("hello") is False`). PR-1's agent
misreported these as "pre-existing flaky failures" — they're not.

```
## ⚠ Worktree wordlist trap (one-time setup before pytest)

```bash
[ ! -e data ] && ln -s /Users/slabakov/dev/Layoutswitcher/data data
```

The N-test baseline only holds with the symlink in place. **DO NOT commit
the symlink.** After committing real changes, remove it (`rm data`) so
`git status --short` shows only your real changes.
```

Update the baseline number per PR (currently 138 after PR-A/B/C; 117 after
PR-A/B; 110 after PR-1; 107 pre-PR-1).

---

## 3. Architectural invariants (include for any code-touching PR)

```
## Architectural invariants

- **INV-001** — daemon must run on native arm64 Python on Apple Silicon.
  The venv at `/Users/slabakov/dev/Layoutswitcher/.venv` is already arm64.
  For pytest:
  `source /Users/slabakov/dev/Layoutswitcher/.venv/bin/activate && \
   arch -arm64 python3 -m pytest -q`.
  Sanity: `arch -arm64 python3 -c 'import platform; print(platform.machine())'`
  must print `arm64`.
- **INV-002** — TCC grants target the CLI binary
  `/Library/Frameworks/.../bin/python3.X`, NOT `Python.app`. Only relevant
  if your PR touches TCC / install flow.
```

---

## 4. Smoke gate — when to require foreground smoke

CLAUDE.md Anti-patterns: "Running daemon (`launchctl bootstrap …`) without
first verifying the source change builds + tests pass." For privileged
event-tap paths, pytest is not enough — runtime behavior must be verified.

| PR type | Foreground smoke required? |
|---|---|
| Pure parser / logic, no `_tap_callback` change | **No** — pytest sufficient |
| Touches `_tap_callback`, `_detection_worker`, or `AutoCorrector.correct()` | **Yes** — but agent **MUST NOT** run `python3 -m src.main` while launchd daemon is active. See below. |
| Docs / dead code removal / config additions only | **No** |
| Logging additions (no behavior change) | **No** |
| `_appDidActivate_` / NSWorkspace observer changes | **Yes** — same constraint |
| Permission-recovery / status-bar changes | **Yes** — same constraint |

### Smoke under launchd-active constraint

The launchd daemon is permanently running on `main` for the user. An agent
foreground-running `python3 -m src.main` from its worktree creates a second
CGEventTap on the same session — keyboard input freezes.

Two viable strategies:
1. **(Preferred for medium-risk)** Skip foreground smoke in the agent.
   Comprehensive unit tests + orchestrator runtime smoke after merge (user
   triggers a few corrections; orchestrator checks log + behavior).
2. **(Required for high-risk hot-path)** Orchestrator boots out the launchd
   daemon, agent runs foreground smoke, agent kills foreground, orchestrator
   bootstraps launchd back. Coordinate this in the prompt: "do not run
   foreground until orchestrator confirms launchd is stopped." Treat as
   high-risk gate (user approval per CLAUDE.md merge rubric).

For the threading-fix campaign (PR-E/EX/EY/F/G/H), strategy #1 is the
default; #2 only if a fix breaks runtime smoke that #1 would have caught.

---

## 5. Reporting-back template

Tell the agent:

```
### Reporting back

Concise, under 250 words:
- Branch + PR URL.
- Files changed + LOC.
- Test results (pass count vs. baseline; report the baseline you observed).
- Schema / architectural choices made.
- Any deviations from this spec + reasoning.
- Anything that surprised you about the existing code or that the
  orchestrator should know before merging.
```

The "report the baseline you observed" line catches cases where the agent
saw a non-baseline test count due to a missed wordlist symlink.

---

## 6. Branch naming reminder

Per CLAUDE.md § GitHub workflow:

| Prefix | Use |
|---|---|
| `feature/<short-name>` | own additions / new features |
| `fix/<short-name>` | bug fixes |
| `task/<short-name>` | orchestrator-dispatched mechanical work |
| `upstream-merge/<YYYY-MM-DD>` | syncing from upstream `moiz2306/layout-switcher` |
| `wip/<topic>` | in-progress / parked diagnostic |

---

## 7. Co-author trailer (per CLAUDE.md commit policy)

For Sonnet:
```
Co-Authored-By: Claude Sonnet (Sonnet) <noreply@anthropic.com>
```

For Opus:
```
Co-Authored-By: Claude Opus (Opus) <noreply@anthropic.com>
```

---

## 8. Common spec sections

These reusable pieces should appear in most prompts:

- **Branch creation step** — "Create branch `<branch>` from current HEAD
  (should be `main` at commit `<sha>` or later)."
- **Out-of-scope list** — explicit; cite which PR-letters cover the deferred
  scopes so agent knows the work is scheduled, not abandoned.
- **PR body checklist** — Summary / Why / Limitation / Test plan / Risks.

---

## When this doc updates

Update when a new repeating snippet emerges across ≥ 2 prompts. If a snippet
applies to one PR only, inline it. Avoid bloat — this doc must remain
faster-than-rewriting-from-scratch.
