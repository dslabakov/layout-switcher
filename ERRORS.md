# ERRORS — non-trivial bugs solved

> Append on every `/save` Q4 trigger. Format: `E-NNNN <short title>` with symptom / root cause / fix / recognition cue.
> Skip routine errors where commit message + git blame already explain the fix.
> Target size: ≤ 50k chars. Above that → manual prune of stale fix-recipes (the fix is in code; only keep non-obvious recognition cues).

---

*(no entries yet — first non-trivial bug will land here)*

---

## Format for new entries

```markdown
### E-NNNN <short title>

**Symptom.** <what the user / test / log saw>

**Root cause.** <the non-obvious part — why it happened>

**Fix.** <commit ref or one-line description>

**Recognize next time.** <stack-trace fragment, log line, or behavior signature>

**Date.** <YYYY-MM-DD, session N>
```

Numbering starts at `E-0001` and increments. Don't reuse numbers.
