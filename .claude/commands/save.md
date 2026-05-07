Session checkpoint with analysis-driven triage. Do ALL steps in order.

**Recommended model:** Sonnet 4.6 or higher. Triage is checklist routing, not free-form reasoning — Sonnet executes reliably. Default policy: **when uncertain, archive verbatim — never silently drop content that future-me might need.**

---

### Step 1. Triage — route this session's content to the right layer

For every notable thing that happened this session, ask the routing questions IN ORDER. First "yes" wins. Anything not matched falls to the default (archive verbatim or drop).

| Q | Trigger | Destination |
|---|---|---|
| Q1 | Did a code-level constraint emerge that next-me MUST not break? | **CLAUDE.md** ARCHITECTURAL INVARIANTS section + motivation in **`docs/reference/INVARIANTS.md`** |
| Q2 | Did the user give a "from now on do/don't X" rule? | **memory** (write `feedback_*.md` + add bullet to `MEMORY.md`) |
| Q3 | Was a non-trivial architectural pivot decided? | **`docs/reference/DECISIONS.md`** — dated entry with motivation |
| Q4 | Was a non-obvious bug fixed where root cause won't be obvious from the diff alone? | **`ERRORS.md`** (skip if commit message + git blame already explain it) |
| Q5 | Did current state change — new WIP, blocker, recent decision worth surfacing, carry-over for next session? | **EDIT** (not append) the Living section of `SESSION_RESUME.md` |
| Q6 | Was a verbose retrospective worth replaying later (lessons, scoreboards, methodology evolutions, salvage anecdotes)? | **APPEND** verbatim to `docs/archive/session-resume-history/<YYYY-MM>.md` (create monthly bucket if missing) |
| **Drop** | Production HEAD ref, list of merged PRs, list of changed files, "what I did" narrative | **DO NOT WRITE ANYWHERE** — `git log`, `gh pr list`, and `git diff` are source of truth |

**Conservative bias:** if a piece of content could be Q5 or Q6 — pick Q6 (archive). If it could be Q1-Q4 promotion or just Q5 surface — pick the promotion (it's load-bearing across sessions). The drop bucket is ONLY for content trivially derivable from git/gh.

### Step 2. Update Living state in SESSION_RESUME.md

EDIT the existing Living-layer sections (no append). Required sections:

- **Current state (updated YYYY-MM-DD)** — 1-2 paragraphs: where are we, what's the focus right now.
- **In-flight (WIP, not yet merged/pushed)** — bullets for unmerged PRs, paused branches, blockers, unpushed commits.
- **Recent decisions** — last ~5 dated bullets, each ≤2 lines, each linking to DECISIONS.md / INVARIANTS.md / memory file.
- **Carry-overs for next session** — action bullets (`- [ ]` checkbox style).
- **Archive index** — chunk pointers (one bullet per chunk, no per-session sub-bullets).

**Target: ≤30k chars / ~250 lines for the whole file.** If you blow past this, your triage was insufficient — push more content into archive (Q6).

### Step 3. Update PLAN.md (prospective only)

PLAN is "what to do next", NOT retrospective. Touch only:

- **Active backlog (refreshed)** — if priorities shifted, edit the bullets.
- **Next Session — Start Here** — refresh the priority list.
- **Architectural findings (cumulative)** — only if a finding became wrong or a new cumulative truth emerged that doesn't fit a single INVARIANT (rare).
- **Pending — pick when needed** — only if a Pending item was completed (strike or remove).

**Forbidden:** adding `## Session N — ...` priority blocks. Per-session retrospective is SESSION_RESUME's job (Living-layer).

### Step 4. Promote to memory if Q2 fired

For each new feedback rule: write `~/.claude/projects/-Users-slabakov-dev-Layoutswitcher/memory/feedback_<slug>.md` with the standard frontmatter (name, description, type=feedback) + body. Add a one-line bullet to that directory's `MEMORY.md`. Format per the global memory protocol in CLAUDE.md user instructions.

### Step 5. Update reference files if Q1 / Q3 / Q4 fired

- Q1 (INVARIANT): edit CLAUDE.md `# ARCHITECTURAL INVARIANTS` section (add the constraint block) + extend `docs/reference/INVARIANTS.md` with motivation, introduced date, removal condition.
- Q3 (DECISION): prepend a dated entry to `docs/reference/DECISIONS.md` with: title, problem, alternatives considered, chose, why, artifacts.
- Q4 (ERROR): append to `ERRORS.md` with: symptom, root cause (non-obvious part), fix (or pointer to commit), how to recognize next time.

### Step 6. Size budget check (passive — warn but never block)

Run:

```bash
wc -lc CLAUDE.md SESSION_RESUME.md PLAN.md ERRORS.md docs/reference/DECISIONS.md docs/reference/INVARIANTS.md
```

Surface a warning line in the final summary for each over-budget file:

| File | Warn at | Suggested action |
|---|---|---|
| `CLAUDE.md` | ≥ 12k chars | run `/shrink-claude` |
| `SESSION_RESUME.md` | ≥ 30k chars | triage was insufficient — push more into archive next time |
| `PLAN.md` | ≥ 20k chars | trim Pending or move stale findings into a new INVARIANT |
| `ERRORS.md` | ≥ 50k chars | manual prune of stale fix-recipes (the fix is in code; only keep non-obvious recognition cues) |
| `docs/reference/DECISIONS.md` | ≥ 80k chars | archive shipped-phase decisions to `docs/archive/decisions/<YYYY-MM>.md` |
| `docs/reference/INVARIANTS.md` | ≥ 40k chars | move "Removed: …" entries to `docs/archive/invariants-removed.md` |

Warnings appear in summary, e.g. `⚠️ ERRORS.md at 52k chars — prune stale fix-recipes`. Do NOT pause `/save` for the user to act; they handle it next session.

### Step 7. Rotate HANDOFF.md (optional)

If this session's progress materially changed what the NEXT session must know first — rewrite top-level `HANDOFF.md`:

1. Archive current `HANDOFF.md` content → `docs/handoffs/YYYY-MM-DD-session-N-end.md`.
2. Overwrite top-level `HANDOFF.md` with fresh terse boot script (~1-2 KB) per the convention in HANDOFF.md itself.

Skip this step if nothing material has changed — orchestrator next session will fall through to the standard read-first list.

### Step 8. Commit

Stage explicit paths only (no `git add .` — would sweep up untracked diagnostic files). Use:

```bash
git add SESSION_RESUME.md PLAN.md \
  CLAUDE.md ERRORS.md HANDOFF.md \
  docs/reference/DECISIONS.md docs/reference/INVARIANTS.md \
  docs/archive/session-resume-history/ \
  docs/archive/plan-shipped-phases/ \
  docs/handoffs/ \
  .claude/commands/save.md 2>/dev/null

git commit -m "docs: session checkpoint"
git push
```

Memory files live OUTSIDE the repo (`~/.claude/projects/.../memory/`) and persist automatically — no `git add` needed.

### Step 9. Confirm

Output a 4-6 line summary:

1. `Session saved.`
2. Brief headline of what landed (1 sentence).
3. Triage outcomes: which buckets fired (e.g. `Triage: Q3 (1 decision), Q5 (state edited), Q6 (1 archive entry)`).
4. Sizes: `CLAUDE.md: Nk / Mk lines, SESSION_RESUME.md: Nk / Mk lines, PLAN.md: Nk / Mk lines.`
5. Any size warnings from Step 6 verbatim.
6. Confirmation that push succeeded (or noted failure).
