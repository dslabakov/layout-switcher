Shrink CLAUDE.md when it has crossed the size budget (≥ 12k chars in this project).

Goal: keep CLAUDE.md as a fast-loading top-level pointer + invariants + carve-outs. Push everything else into `docs/reference/` files which are loaded on demand.

---

### Step 1 — Measure

```bash
wc -lc CLAUDE.md
```

If under 12k chars: nothing to do. Confirm and exit.

If over: continue.

### Step 2 — Identify what to extract

Read CLAUDE.md fully. Classify each top-level section:

| Section type | Stay in CLAUDE.md | Extract to docs/reference/ |
|---|---|---|
| Project description (1 paragraph) | ✅ | |
| Stack summary (1 small table) | ✅ | |
| ARCHITECTURAL INVARIANTS (one-line summaries) | ✅ | full motivation already in `docs/reference/INVARIANTS.md` |
| Orchestrator-only mode + read carve-outs | ✅ | full procedural detail to `docs/reference/ORCHESTRATOR.md` |
| Model selection rubric | ✅ (small table) | full rationale to ORCHESTRATOR.md |
| GitHub workflow basics | ✅ (table) | detailed merge gates, PR review SOPs to ORCHESTRATOR.md |
| Anti-patterns | ✅ (bullet list) | examples + counter-examples to ORCHESTRATOR.md |
| Project-specific guards | ✅ if short | else to a new `docs/reference/PROJECT-GUARDS.md` |
| Reference materials index | ✅ | |
| Workflow rules | ✅ (short) | |
| AT SESSION START | ✅ (short) | |
| Long sub-procedures (e.g. detailed sync workflow) | ❌ | move to dedicated reference doc |
| SOP descriptions (Audit / Fix / Refactor / etc.) | ❌ | already in ORCHESTRATOR.md |

### Step 3 — Extract

For each section being extracted:

1. Locate the canonical destination (often `docs/reference/ORCHESTRATOR.md` or `docs/reference/INVARIANTS.md`).
2. If destination doesn't have an equivalent section, **create** it. Verbatim copy of the CLAUDE.md content + any cross-references.
3. In CLAUDE.md, replace the extracted section with a **one-line pointer**: e.g. `See \`docs/reference/ORCHESTRATOR.md\` § Standard Operating Procedures.`

### Step 4 — Verify

```bash
wc -lc CLAUDE.md
```

Should be under 12k chars now. If still over: re-classify (Step 2) and extract more.

### Step 5 — Spot-check

Read CLAUDE.md top to bottom. The flow should be:
- 30-second project description.
- Stack tag-line.
- Invariants (one-liners with pointers to INVARIANTS.md for full motivation).
- Mode + carve-outs (full because every session needs these).
- Model selection (full because every Agent invocation needs this).
- GitHub workflow basics (full because every PR uses this).
- Anti-patterns (full because every session needs awareness).
- Reference materials index.
- AT SESSION START checklist.

If a reader can answer "what is this project, how do I work in it, what must I never do, where do I look for X?" from CLAUDE.md alone — the shrink succeeded.

### Step 6 — Commit

```bash
git add CLAUDE.md docs/reference/
git commit -m "docs: shrink CLAUDE.md — extract <sections> to docs/reference/"
git push
```

### Step 7 — Confirm

Output a 3-5 line summary:
1. `CLAUDE.md shrunk: <before>k → <after>k chars (-<delta>k).`
2. `Extracted to: <list>`.
3. `New reference files (if any): <list>`.
4. `Verify: read CLAUDE.md top-to-bottom, ensure flow still answers "what is this project, how to work, what to avoid, where to look".`
