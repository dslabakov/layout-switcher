# Handoff

> Top-level boot script for the next Claude Code session. Terse, ~1-2 KB.
> Rotated at the end of each session — current contents archived to `docs/handoffs/YYYY-MM-DD-session-N-end.md`, then this file overwritten with fresh handoff for next session.

## Status

**Session 5 complete (2026-05-08).** Discussion-only — no source changes. Explored adding spell-correction layer (architecturally trivial in current pipeline; recommended `NSSpellChecker` via pyobjc), surveyed open-source niche (closest analog Charm; FOSS Python-daemon gap exists), reconsidered Swift-port for distribution context (correction to 2026-05-07 entry: that decision was personal-use scoped; for community distribution Swift objectively better), adopted two-track strategy (Python prototype → Swift → publish). User explicitly deferred all action: «пока ничего не хочу делать».

Code state unchanged from session 4 end. INV-003 still under production monitoring (205 tests, daemon on commit `79f7f9e`).

## Read first

1. `CLAUDE.md` — orchestrator-only mode + INV-001/002/003.
2. `SESSION_RESUME.md` — current state + carry-overs (note new spell-correction Track 1 carry-over at top).
3. `PLAN.md` → "Next Session — Start Here" + "Pending — pick when needed". The new pending entry points to the spell-correction strategy doc.
4. **NEW: `docs/research/spell-correction-strategy.md`** — full findings (9 sections + how-to-revisit). Read before any spell-correction or Swift-port discussion.
5. `docs/reference/DECISIONS.md` § 2026-05-08 (session 5) — meta-decision (defer + two-track-when-revisited) + scope-clarification of 2026-05-07 Swift entry.
6. New memory: `feedback_verify_past_decisions_before_paraphrasing.md` — re-read source before paraphrasing past decisions.

## Delta (since session 4 end)

- **No source changes.** Daemon, tests, INV-003 implementation all unchanged.
- **New:** `docs/research/` directory + `spell-correction-strategy.md` (comprehensive 9-section findings).
- **DECISIONS.md** session-5 entry: meta-decision to defer with two-track contingent strategy; scope-clarifies 2026-05-07 Swift entry as personal-use-bound (not absolute "no Swift").
- **Memory:** `feedback_verify_past_decisions_before_paraphrasing.md`.
- **HANDOFF rotation:** previous (session-4-end) HANDOFF archived to `docs/handoffs/2026-05-08-session-4-end.md` (was missing — session 4 close skipped the rotation).

## How to start session 6

1. `git status` should be clean on `main`. Daemon should still be `state = running` on session-4 code.
2. If user reports a fresh tail-of-word mangle: same playbook as session-5 boot (see archived `docs/handoffs/2026-05-08-session-4-end.md`). Cross-reference timestamp with log; check whether preceding event was covered by INV-003 or is one of the known adjacent gaps (backspace-into-empty, Ctrl-shortcut).
3. If user wants to start spell-correction Track 1: read `docs/research/spell-correction-strategy.md` § 8 (strategic plan) + § 3 (NSSpellChecker rec). Spec a Sonnet agent with MVP scope per § «How to revisit».
4. If user references a past decision — re-read source first per new feedback memory. Do NOT paraphrase 2026-05-07 Swift entry as absolute «no Swift»; it's personal-use-scoped.

## Known traps

- All session-2/3/4 traps still apply: INV-001 arm64 Python; INV-002 TCC target = CLI binary; INV-003 boundary-observation flag (re-armed via try/finally — easy to lose on refactor); `gh pr create` defaults to upstream when origin is fork (always pass `--repo dslabakov/layout-switcher`); E-0002 modifier-flag clearing for synthetic CGEvents; E-0003 Tab-not-in-BOUNDARIES for Cmd+Tab.
- **`docs/research/`** is a new directory, only contains `spell-correction-strategy.md`. Other exploratory findings should go here too going forward, not into `docs/reference/` (reference is for load-bearing facts, not exploration).
- **Swift-port discussion:** the 2026-05-07 entry is personal-use-scoped. Don't paraphrase it as «Swift won't work». For community-distribution context, Swift is the recommended path per session-5 entry.

---

## Convention (how to use this file)

**Purpose:** terse boot script for next session. Reading time: < 5 minutes. Functions as "start here" pointer + delta from last session.

**Strict rules:**
1. **No duplication of content** that lives in `SESSION_RESUME.md`, `PLAN.md`, `DECISIONS.md`, `ERRORS.md`. Pointer + 1-line gloss only.
2. **Genuine added value sections:** `## Read first`, `## Delta`, `## Known traps`, `## How to start session N+1`.
3. **Target size:** under 2 KB. If growing, content belongs elsewhere.
4. **Rotation:** at the end of each session, orchestrator (a) archives this file's current contents to `docs/handoffs/YYYY-MM-DD-session-N-end.md`, (b) overwrites this file with fresh handoff for next session.

When this file is the empty/template version, it's a signal that the previous session ended without filing a fresh handoff — orchestrator falls through to the standard read-first list (CLAUDE.md → SESSION_RESUME.md → PLAN.md).
