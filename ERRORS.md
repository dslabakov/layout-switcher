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

### E-0002 Manual hotkey deletes word + preceding chars and types nothing back

**Symptom.** User types valid Russian word (e.g. `привет `) in a real text field (Notes / NSTextView). Auto-correction does not fire (valid word). User presses configured hotkey `Ctrl+Shift+Space` to manually toggle layout. Expected: `привет ` → `ghbdtn `. Actual: `привет ` is **deleted** (along with several characters of preceding text), and **nothing is typed back**. Auto-correction itself works fine — only the manual hotkey path is broken.

**Root cause (pre-existing upstream — since first commit `26d4f9a`).** `AutoCorrector._send_backspaces()` and `_type_string()` create CGEvents and post them at `kCGHIDEventTap` without explicitly clearing modifier flags. At HID injection, macOS re-derives modifier state from **currently-held physical keys**, NOT from any flags set on the synthetic event itself. The hotkey is `Ctrl+Shift+Space`. The worker thread fires synthetic events within milliseconds of the hotkey keydown — while the user still physically holds Ctrl+Shift (human release latency 50-100ms).

Result: synthetic backspace events become **Ctrl+Shift+Backspace** in NSTextView → delete-by-word semantics, eats more text than intended. Synthetic letter events become **Ctrl+Shift+letter** → triggers app keyboard shortcuts (Cmd-equivalents in Cocoa) instead of inserting characters. Auto-correction (triggered by Space boundary, not hotkey) didn't expose this because by the time `correct()` fires, user has released Space and modifiers are clear.

`CGEventSetFlags` was imported in the very first commit (`auto_corrector.py:8`) but never called — dead import for the entire history of the repo. `kCGEventFlagMaskShift` similarly imported but unused.

**Fix.** Commit `8e82d45` (HOTFIX-1, PR #9). After `_mark_synthetic(ev_down)` and `_mark_synthetic(ev_up)` calls in `_send_backspaces` and `_type_string`, explicitly call `CGEventSetFlags(ev_down, 0)` and `CGEventSetFlags(ev_up, 0)` before `CGEventPost`. Tests use `patch.object(acm, "CGEventSetFlags")` and assert `call_count == expected_event_count` (asserting `CGEventGetFlags(ev) == 0` would be a wrong test — fresh CGEvents default to flags=0, so the assertion would pass even without the SetFlags call).

**Recognize next time.**
- Synthetic typing produces unexpected app-shortcut behavior (e.g. typing 'g' opens a menu) or word-level deletions instead of single-char deletions.
- Bug only manifests when user is HOLDING modifier keys at synthetic-event-fire time. Auto-correct (space boundary) works; hotkey-driven path breaks.
- Test that should catch a regression: assert `CGEventSetFlags` is called once per `ev_down` and once per `ev_up`, with second arg = 0.
- If `SetFlags(0)` is added but bug persists, fallback is to switch CGEventPost target from `kCGHIDEventTap` to `kCGSessionEventTap` (also imported in the file).

**Date.** 2026-05-08, session 3.

---

### E-0003 Cmd+Tab triggers phantom correction in destination app

**Symptom.** User types a partial word (e.g. `ghbd`) in app A, presses **Cmd+Tab** to switch to app B. In app B, `прив` (or similar Russian-layout-equivalent of the partial word) appears automatically without user typing it. PR-E's app-switch observer DOES fire (in fact this saga confirmed PR-E works) — but the correction fires BEFORE the observer's `("clear",)` message reaches the worker, so observer's clearing is too late.

**Root cause (pre-existing upstream).** `WordBuffer.BOUNDARIES` (`src/word_buffer.py`) included `\t` (Tab character). When user presses Cmd+Tab:
1. The Tab keydown event reaches `_tap_callback` (Cmd is a modifier; it doesn't suppress Tab key delivery).
2. `_tap_callback` does NOT filter Tab (it's not in `ARROW_KEYCODES`, not the synthetic marker, not the configured hotkey).
3. `_word_buffer.add_char('\t')` is called. Tab is in `BOUNDARIES` → returns `("ghbd", "\t")` — word completion triggered.
4. Tap callback enqueues `("complete", ("ghbd", "\t"))` and `("check", ("ghbd", "\t"))`.
5. Worker dequeues `("check", ...)`, runs detection: `ghbd` (4 chars) → `прив` in Russian layout, detector confirms `прив` ≈ valid (or trim-and-retry hits something), correction fires.
6. By the time synthetic backspaces+chars post, focus has switched to app B. `прив` lands in app B.

The PR-E app-switch observer's `("clear",)` enqueue ARRIVES on the queue, but AFTER the `("check",)` that already triggered the correction. Order in queue: `complete` → `check` → (worker processing check, including drain) → `clear`. Too late.

**Fix.** Commit `d6392de` (HOTFIX-2, PR #10). Remove `\t` from `WordBuffer.BOUNDARIES`. Tab is now appended to the buffer as a regular character (gets filtered out by `_could_be_word` later). PR-E's observer `("clear",)` then does its job correctly. Test: `test_tab_does_not_complete_word` in `test_word_buffer.py`.

**Trade-off.** Tab no longer completes a word. In practice Tab is rarely used mid-word — typically for indentation or focus-change — so this trade-off is acceptable. If a user needs Tab as a word-completer for some workflow, the fix would be to ignore Tab in tap callback specifically when modifiers (Cmd) are held, rather than removing from BOUNDARIES universally.

**Recognize next time.**
- Phantom Russian/English text appearing in destination app immediately after Cmd+Tab.
- Log shows `_check_and_correct: word='<partial>' boundary='\t'` immediately followed by an `app_filter.should_process: app='<destination_app>'` debug entry.
- If the bug recurs after another upstream merge: check whether `BOUNDARIES` reverted to include `\t` again.

**Date.** 2026-05-08, session 3.

---

### E-0004 Tail-of-word mangle after edit/paste/click — short false-positive corrections fired on desynced buffer

**Symptom.** User pastes a long text and immediately types `cv ` (or `gh `, `dc `, etc.) → on screen, the last 2 characters of the pasted text are silently replaced with `см` (or layout-equivalent). Same effect via: arrow keys to mid-word + backspace + retype tail; click mid-word + type. User describes it as "two letters at the tail of a long word changed to nonsense, but I never typed those letters there" — and confirms not touching mouse or trackpad in some reproductions.

**Root cause.** Two independent gaps combine — neither is sufficient alone:

1. **Validator false-positives at length 2-3.** Layout-mapping produces 272 short pairs that pass either dictionary on conversion: 157 Latin→Russian (`cv→см`, `gh→пр`, `dc→вс`, `ог→ju` reverse, full table archived in session-4 retrospective) + 115 Russian→Latin. pymorphy3 is permissive on 2-letter morphological fragments; English wordlist accepts many 2-letter tokens. Any 2-3-letter word that hits one of these pairs and reaches `_check_and_correct` will be "corrected".

2. **WordBuffer-cursor desync via external buffer-loss.** `_word_buffer` is a keystroke counter; it has no on-screen cursor visibility. macOS doesn't deliver paste content as keystrokes (NSPasteboard insert), so paste invisible to event tap. Cursor-move keystrokes (arrows, Home/End), mouse clicks, app-switches, and Cmd-modifier shortcuts (including Cmd+V paste) all signal a desync — the daemon clears its buffer because it knows it's lost sync. After clear, the next chars accumulate as a "fresh word" in the daemon's buffer — but on-screen the cursor is somewhere else (after pasted text, mid-word, etc.). When boundary fires, `_check_and_correct` happily processes the 2-3 letter buffer content, hits a false-positive pair, and `correct()` issues backspaces. Backspaces eat **on-screen** chars (last 2-3 chars left of cursor — not the chars in the daemon's buffer), then types the false-positive replacement. Result: tail of an unrelated word mangled.

The tricky part: from the daemon's `correct: 'cv' -> 'см' (extra='', deleted=3)` log line, behavior looks correct — exactly 3 chars stripped, exactly 3 typed. The mismatch lives in the gap between the daemon's buffer-frame-of-reference and the on-screen frame-of-reference, which the daemon cannot see.

**Discovery path.** Initial misdiagnosis: orchestrator constructed an elaborate "cursor desync via mouse-click followed by paste" theory across two long advisor calls. User pushback ("у меня всё не так", "я ничего не делаю") repeatedly corrected direction. The breakthrough was a single live reproduction of `ог → ju` after the user's `arrow + backspace + retype` sequence — confirmed by the now-instrumented `word_buffer.clear: reason=cursor-move` log lines from PR #17. Lesson: the symptom (`tail of word mangled`) is one user-perceived event but two technical causes — both need to be present for the bug to reach the screen.

**Fix.** Boundary-observation flag — see DECISIONS.md 2026-05-08 (late) entry. PR #18 (commit `1aef293`) and PR #19 (commit `79f7f9e`). `KeyboardMonitor._can_correct_next_word: bool` set False at every external buffer-loss site; checked at `_check_and_correct` entry; skip + log + re-arm via `try/finally`. INV-003 codifies the constraint.

**Recognize next time.**

- Log shows `_check_and_correct: skipping correction (no observed boundary before word=...)` after a `word_buffer.clear: reason=...` event — that's the new fix path firing correctly. Absence of these in scenarios where you'd expect them = regression.
- Pre-fix log signature: `correct: 'XX' -> 'YY' (extra='', deleted=3)` for 2-character X, immediately preceded (within seconds) by one or more `word_buffer.clear: reason=mouse-down|cursor-move|app-switch|cmd-shortcut` lines. The combination is the smoking gun: short word + recent external clear.
- User report style: "two letters at the tail of [long word] turned into [short Russian/Latin sequence]" — visually the change is on the wrong characters because of the on-screen cursor position.
- 272-pair false-positive enumeration: latin→russian and russian→latin tables archived in `docs/archive/session-resume-history/2026-05.md` under session-4 retrospective. Useful when assessing whether a newly-observed pair is novel or part of the known set.

**Date.** 2026-05-08, session 4.

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
