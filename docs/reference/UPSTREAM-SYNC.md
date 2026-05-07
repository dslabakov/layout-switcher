# Upstream sync workflow

> How to keep `dslabakov/layout-switcher` in sync with `moiz2306/layout-switcher` while preserving local doptweaks.

## Why a procedure

This is a **fork**. Two pressures:
- **Pull bug fixes / features from upstream** — don't reinvent.
- **Preserve local doptweaks** — own customizations shouldn't be lost.

A casual `git pull upstream main` can:
- Hide upstream changes inside a merge commit (no per-line diff review).
- Conflict-merge into local code without intent.
- Clobber un-pushed local work.

So: **always sync via a `upstream-merge/YYYY-MM-DD` branch + diff review**, even if the diff is "boring".

---

## Remotes (one-time, already configured)

```bash
git remote -v
# origin    https://github.com/dslabakov/layout-switcher.git (fetch)
# origin    https://github.com/dslabakov/layout-switcher.git (push)
# upstream  https://github.com/moiz2306/layout-switcher.git  (fetch)
# upstream  https://github.com/moiz2306/layout-switcher.git  (push)
```

If `upstream` missing: `git remote add upstream https://github.com/moiz2306/layout-switcher.git`.

---

## Sync procedure

### Step 1 — Snapshot what's incoming

```bash
cd /Users/slabakov/dev/Layoutswitcher
git fetch upstream

# What's new upstream since our last sync
git log --oneline HEAD..upstream/main

# What's local-only
git log --oneline upstream/main..HEAD

# Diff stat
git diff --stat upstream/main..HEAD
```

If `HEAD..upstream/main` is empty → no upstream changes, skip the rest.

### Step 2 — Decide: merge or rebase

- **Merge** (default): preserves local commit graph. Use this most of the time. The merge commit documents the sync.
- **Rebase**: cleaner linear history. Use when local commits should "stay on top" of upstream (e.g. you have local feature branches that should appear after the upstream snapshot in `git log`).

For solo project, **merge is simpler** (no force-push concerns). Use rebase only when graph cleanliness matters for a specific PR.

### Step 3 — Branch + merge (orchestrator delegates the actual work)

Orchestrator briefs Sonnet agent:

```
Sync upstream into a fresh branch.

1. cd /Users/slabakov/dev/Layoutswitcher
2. git checkout main && git pull origin main   # ensure local main is up to date
3. git checkout -b upstream-merge/$(date +%Y-%m-%d)
4. git merge upstream/main
5. If conflicts:
   - For src/ conflicts: prefer keeping local logic, but apply upstream bug fixes within the same hunk.
   - For docs (README.md, LICENSE): prefer upstream verbatim unless we've intentionally diverged.
   - For config (config.example.yaml, requirements.txt): merge by union (combine entries from both).
   - For tests: keep both — local tests + upstream new tests.
6. After resolution: git status --short, ensure no remaining U (unmerged) entries.
7. Run pytest. Report failures.
8. If pytest passes: git add -A && git commit -m "upstream-merge: $(date +%Y-%m-%d)"
9. If any conflict resolution was non-trivial, document the choices in the merge commit body.
10. git push origin upstream-merge/$(date +%Y-%m-%d)
11. gh pr create --base main --title "upstream-merge: <date>" --body "Sync from moiz2306/layout-switcher@<upstream-HEAD>"
12. Report: PR number + pytest result + conflict summary.
```

### Step 4 — Diff review

Orchestrator runs `gh pr diff <num>`. **Read every changed file at diff level** — this is the only review surface.

Specifically watch for:
- **Behavior changes in CGEventTap setup** (`keyboard_monitor.py`) — high-stakes, can freeze keyboard.
- **Layout map edits** (`layout_mapper.py`) — wrong mapping = wrong corrections.
- **API changes** in pyobjc or pymorphy3 — sync may bring new dep versions, check `requirements.txt` diff.
- **README/install changes** — docs may have shifted assumptions.

If a hunk needs deeper context: send Sonnet follow-up brief: "review PR #N around [file] [line range], explain why upstream made this change and whether it's safe to take."

### Step 5 — Merge

```bash
gh pr merge <num> --merge --delete-branch
git checkout main && git pull origin main
```

Squash-merge is also fine, but `--merge` preserves the per-commit history from upstream which is useful for future bisects.

---

## Conflict-resolution heuristics

| File / area | Default policy |
|---|---|
| `src/main.py` | Manual review — entry point, prone to conflict. Take upstream framework changes; preserve local feature toggles. |
| `src/auto_corrector.py` / `src/keyboard_monitor.py` | High-stakes. Manual review. Prefer upstream bug fixes; never blanket-take rewrites. |
| `src/layout_mapper.py` | Manual review — both sides may have added language tables. Union them carefully. |
| `src/language_detector.py` | Manual — pymorphy3 API changes can land. |
| `src/status_bar.py` / UI files | Often just upstream visual tweaks. Default-take upstream unless a local feature was added. |
| `tests/` | Union — keep all tests from both sides. |
| `requirements.txt` | Union with version-bump preference (take upstream's higher minor where compatible). |
| `config.example.yaml` | Union by key. Preserve local default values where we explicitly diverged. |
| `README.md` | Default-take upstream verbatim unless we have a local fork-specific note (note should live in CLAUDE.md instead). |
| `LICENSE` | Take upstream verbatim. |
| `install.sh` | Manual — upstream installer assumes upstream URL. Local fork may want its own install path. |
| `setup.sh` | Manual — usually safe to take upstream + re-apply our local tweaks. |
| `com.layout-switcher.plist` | Manual — placeholders shouldn't change but app label might. |
| `docs/**`, `CLAUDE.md`, `PLAN.md`, `SESSION_RESUME.md`, etc. | These don't exist upstream. Conflict shouldn't arise — if it does (someone created an `docs/` upstream), keep local + investigate. |

---

## Common scenarios

### Upstream has a critical bug fix in `auto_corrector.py`

1. Sync via the procedure above.
2. In diff review, focus on the `auto_corrector.py` hunks.
3. Verify the test suite has a regression test for the fix (upstream usually adds one).
4. Run pytest with extra attention: `pytest tests/test_auto_corrector.py -v`.
5. If passes → merge.

### Upstream introduces a new dep

1. Sync.
2. `requirements.txt` will have new line.
3. Re-run `setup.sh` to install the new dep into `.venv`.
4. Run pytest.
5. Audit briefly — is the new dep heavy? Adds attack surface? Decide whether to keep or drop (drop = keep upstream code path but maintain local `requirements.txt` without the dep).

### Local doptweak conflicts with upstream's redesign

E.g. we added a custom feature to `auto_corrector.py`; upstream rewrote the same module.

1. Don't blanket-take either side.
2. Spawn Opus agent with full context: "upstream rewrote X; we have local feature Y; design merger that preserves Y on top of upstream's new structure."
3. Review the proposal before applying.
4. Document the merger decision in `docs/reference/DECISIONS.md`.

### Upstream goes silent / abandoned

If `moiz2306/layout-switcher` stops accepting PRs / stops publishing:
- Disconnect `upstream` remote (or leave for archive).
- Update CLAUDE.md "Origin" to remove "fork of" framing.
- Document in DECISIONS.md.

---

## Sync cadence

- **Casual:** check `git fetch upstream && git log --oneline HEAD..upstream/main` once a week.
- **Active feature work upstream:** sync more often (every 2-3 days if upstream is shipping daily).
- **No upstream changes:** skip until next check.

Don't sync just for the sake of syncing — wait until there's at least one upstream commit, OR a known security/bug fix.
