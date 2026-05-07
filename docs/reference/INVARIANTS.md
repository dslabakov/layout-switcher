# INVARIANTS — load-bearing design constraints

> Constraints that next-me MUST not break without re-derivation. Surface in `CLAUDE.md` § ARCHITECTURAL INVARIANTS as one-line summary; full motivation here.
> Triggered when a code-level constraint emerges (per `/save` Q1).

---

*(no invariants yet — this file will fill as the project evolves)*

---

## Format for new invariants

When adding a new INV-NNN:

```markdown
### INV-NNN: <one-line constraint>

**Constraint.** <what code/design must do or not do>

**Motivation.** <why this is load-bearing — what breaks if removed>

**Introduced.** <YYYY-MM-DD, session N, link to commit / DECISIONS entry / ERROR>

**Removal requires.** <specific condition that must be true to remove this invariant>
```

Then mirror a one-line summary in `CLAUDE.md` § ARCHITECTURAL INVARIANTS.

---

## Removed invariants

> When an invariant is removed (its removal condition met), move it here verbatim with `**Removed:** <date, session, reason>` appended. **Do not delete.** This file is the audit trail.

*(none yet)*
