# INVARIANTS — load-bearing design constraints

> Constraints that next-me MUST not break without re-derivation. Surface in `CLAUDE.md` § ARCHITECTURAL INVARIANTS as one-line summary; full motivation here.
> Triggered when a code-level constraint emerges (per `/save` Q1).

---

### INV-001: Daemon must run on native arm64 Python on Apple Silicon

**Constraint.** The interpreter at the end of `.venv/bin/python3` symlink chain must be **native arm64** — either python.org universal2 installer (`/Library/Frameworks/Python.framework/Versions/X.Y/bin/python3.Y`) or `/opt/homebrew/Cellar/python@X.Y/.../bin/python3.Y`. **Intel Homebrew Python at `/usr/local/Cellar/...` is forbidden** for the daemon's interpreter.

When recreating the venv from a Bash session that may itself be x86_64-spawned (Claude Code's Terminal often is), force arm64 explicitly:
```bash
arch -arm64 <python.org python3> -m venv .venv
arch -arm64 .venv/bin/python3 -m pip install -r requirements.txt
```
Otherwise pip will pull x86_64 wheels for `pyobjc-core` etc., even though the Python binary itself is universal2 — and arm64 launchd execution will fail to load them.

**Motivation.** Rosetta-translated Python under launchd produces a TCC identity that does not match grants made via System Settings UI — `CGPreflightListenEventAccess` / `CGPreflightPostEventAccess` return `False` even with explicit grants. Terminal-spawned probes mask the issue via TCC parent inheritance, so the failure surfaces only under launchd. See `ERRORS.md` E-0001 layer 1.

**Introduced.** 2026-05-07, session 2. See `ERRORS.md` E-0001, `docs/reference/DECISIONS.md` 2026-05-07 entry "Stay Python; resolve via arm64 + TCC target correction".

**Removal requires.** Either (a) the project switches off Python entirely (Swift native rewrite), (b) Apple changes Rosetta-launchd-TCC interaction so grants survive the translation boundary, or (c) the project ships a properly bundled `.app` whose CGEventTap chain doesn't go through a separate-architecture interpreter.

---

### INV-002: TCC permissions target the CLI Python binary, not Python.app

**Constraint.** Accessibility and Input Monitoring grants for the daemon must be added against the **CLI launcher path** — `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14` (or whichever native arm64 Python's CLI binary is in use), **NOT** against `/Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app`.

`setup.sh` and onboarding documentation must reflect this. The CLI binary appears in System Settings without an `.app`-style icon (just generic executable icon labeled `python3.14`); that's expected.

**Motivation.** macOS TCC attributes requests to the **responsible process** — the first non-launchd process in the exec chain. Daemon chain: `launchd → bin/python3.14 → Python.app/Contents/MacOS/Python` (re-exec via `__PYVENV_LAUNCHER__`). TCC checks `bin/python3.14`'s entry, not Python.app's. Adding Python.app to TCC has no effect; only adding the CLI binary works. Verified via `log stream --predicate 'subsystem == "com.apple.TCC"'` showing `AUTHREQ_SUBJECT: subject=.../bin/python3.14` and `BUNDLE_ATTRIBUTION: candidateBundle(.../bin) is nil or has no identifier`. See `ERRORS.md` E-0001 layer 3.

**Introduced.** 2026-05-07, session 2. See `ERRORS.md` E-0001.

**Removal requires.** Either (a) launchd plist changes to invoke `Python.app/Contents/MacOS/Python` directly as `ProgramArguments[0]`, bypassing the `bin/python3.14` re-exec — then `Python.app` becomes the responsible process and that grant target works; or (b) Apple changes TCC attribution model to use the running process's bundle identity instead of the responsible process; or (c) project switches off Python entirely.

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
