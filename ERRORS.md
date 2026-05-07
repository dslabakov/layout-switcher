# ERRORS — non-trivial bugs solved

> Append on every `/save` Q4 trigger. Format: `E-NNNN <short title>` with symptom / root cause / fix / recognition cue.
> Skip routine errors where commit message + git blame already explain the fix.
> Target size: ≤ 50k chars. Above that → manual prune of stale fix-recipes (the fix is in code; only keep non-obvious recognition cues).

---

### E-0001 Daemon "Permissions missing" under launchd despite UI grants

**Symptom.** Daemon under launchd LaunchAgent logs `[WARNING] Permissions missing, monitor not started.` Granting Accessibility AND Input Monitoring to Python.app in System Settings does not help. Same Python binary spawned via Terminal probe (or `launchctl asuser` from Terminal) returns `CGPreflightListenEventAccess: True / CGPreflightPostEventAccess: True` — but a clean launchd-context probe (one-shot temp plist bootstrapped into the same `gui/$UID` domain as the daemon) returns `False / False`.

**Root cause (three layers, ordered as discovered).**

1. **Rosetta translation under launchd.** Initial setup used Intel-only Homebrew Python (`/usr/local/Cellar/python@3.14/...`) on Apple Silicon (M3 Pro). Daemon ran as `Code Type: X86-64 (translated)` (verified via `vmmap -summary <pid>`). Rosetta-translated processes have a different TCC identity context than native arm64; UI grants are stored against the architecture-translated process state and don't match the launchd-spawned, Rosetta-translated runtime. Terminal-spawned probes "worked" because they piggy-backed on Terminal's pre-existing TCC scope (parent inheritance), masking the underlying mismatch.

2. **Stale TCC entries with overlapping bundle ID.** Each ad-hoc / Dev-cert `codesign --force --sign` of brew Python.app created a NEW TCC identity (different cdhash); old entries weren't replaced — they accumulated. After the architecture switch, **four** entries existed for `org.python.python` per service (verified: `tccutil reset Accessibility org.python.python` printed "Successfully reset" four times), conflicting and possibly shadowing the fresh python.org Python.app entry the user later added.

3. **Responsible-process attribution.** macOS TCC attributes permission requests to the **responsible process** (first non-launchd process in the exec chain), NOT the running re-exec'd process. Python interpreter chain: `launchd → bin/python3.14 → Python.app/Contents/MacOS/Python` (re-exec via `__PYVENV_LAUNCHER__`). Responsible = `bin/python3.14` (CLI launcher); `Python.app` is just the "requesting" process. TCC attribution log (`log stream --predicate 'subsystem == "com.apple.TCC"' --info --debug`):
   ```
   AttributionChain: responsible={identifier=python3, responsible_path=.../bin/python3.14},
                     requesting={identifier=org.python.python, binary_path=.../Python.app/.../Python}
   IDENTITY_ATTRIBUTION: starting for: /Library/Frameworks/.../bin/python3.14
   BUNDLE_ATTRIBUTION: candidateBundle(.../bin) is nil or has no identifier
   AUTHREQ_SUBJECT: subject=/Library/Frameworks/.../bin/python3.14
   Auth Right: Unknown (None)
   ```
   So even with `Python.app` added in System Settings UI, the lookup happens for `bin/python3.14` — for which there's no entry — and returns `Unknown` → False.

**Fix.**

1. Install **native arm64 Python** (python.org universal2 installer, Python 3.14.4 → `/Library/Frameworks/Python.framework/Versions/3.14/`). Removes Rosetta translation entirely.
2. Recreate venv with arm64 forcing on a x86_64 shell (Claude Code's terminal session is x86_64-spawned; default `pip install` would pull x86_64 wheels for compiled deps like `pyobjc-core` and break arm64 launchd execution):
   ```bash
   arch -arm64 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m venv .venv
   arch -arm64 .venv/bin/python3 -m pip install -r requirements.txt
   ```
3. Reset stale TCC entries:
   ```bash
   tccutil reset Accessibility org.python.python
   tccutil reset ListenEvent org.python.python
   tccutil reset PostEvent  org.python.python
   ```
4. Grant TCC permission to **`/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14`** (the CLI binary, NOT `Python.app`) in BOTH Accessibility and Input Monitoring lists. `+`, `Cmd+Shift+G`, paste path, toggle `On`. INV-002.
5. `launchctl bootout gui/$(id -u)/com.layout-switcher && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.layout-switcher.plist`.

**Recognize next time.**

- "Permissions missing" persists after every "obvious" grant of `Python.app` in System Settings.
- `vmmap -summary <daemon_pid> | grep "Code Type"` shows `X86-64 (translated)` instead of `ARM64`.
- `log stream --predicate 'subsystem == "com.apple.TCC"' --info --debug` during a fresh probe shows `AUTHREQ_SUBJECT` pointing at a CLI Python binary path, not at a `.app/Contents/MacOS/...` path. The path TCC attributes to is what must be granted.
- `tccutil reset Accessibility <bundle-id>` prints "Successfully reset" more than once → stale entries from prior re-signs, accumulating.
- Clean launchd-context probe (temp plist) returns False even when Terminal-launched probe returns True → contamination by Terminal's TCC inheritance, not a real grant.

**Date.** 2026-05-07, session 2.

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
