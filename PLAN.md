# PLAN — Layoutswitcher

> Prospective ("what to do next"), NOT retrospective. Per-session retrospectives live in `SESSION_RESUME.md`.
> Target size: ≤ 20k chars.

---

## Next Session — Start Here

Session 4 closed the user-visible "tail-of-word mangle" bug class via INV-003 (boundary-observation flag). Currently monitoring in production — user is using the daemon and will report regressions or remaining manifestations.

Pick from backlog by appetite:

1. **Adjacent gaps to INV-003 (S, ~1 PR each):** backspace-into-empty-buffer fix (stripping unknown on-screen text); Ctrl-modifier shortcut coverage. Both are exact-shape extensions of PR #18 + PR #19. Ship when user reports a reproduction.
2. **Quick cleanup wins (S, < 30 min each):** hoist `CGEventKeyboardSetUnicodeString` import; mock `frontmostApplication` in `test_get_active_app_returns_string`; delete `.venv-old-x86`.
3. **Quality improvements carried over from session 3 (S):** `_is_stale()` precision; cross-app replay-buffer leak fix.
4. **CI setup (M):** GitHub Actions running pytest on PR. Prerequisite: `test_get_active_app_returns_string` mocked. The 205-test safety net makes CI now very attractive — every additional behavior change since session 3 has expanded the test base.
5. **Audit candidates not yet picked up (S/M):** per-app exclusion list UI; "hotkey to toggle enabled".

## Active backlog (refreshed)

- [ ] Backspace into empty buffer should set `_can_correct_next_word=False` — adjacent gap to INV-003.
- [ ] Ctrl-modifier shortcuts (non-hotkey) should set `_can_correct_next_word=False` — adjacent gap to INV-003.
- [ ] Hoist `CGEventKeyboardSetUnicodeString` out of `_type_string` per-iter loop — PR-J agent flagged.
- [ ] Replace `test_get_active_app_returns_string` real `NSWorkspace` call with mock — needed for headless CI.
- [ ] `_is_stale()` count only `("check",)` items, not all queue messages — precision improvement.
- [ ] Cross-app replay-buffer leak — discard replay buffer in `("clear",)` handler.
- [ ] Eventually delete `.venv-old-x86` backup.

## Pending — pick when needed

- [ ] CI setup (GitHub Actions, run pytest on PR). The 205-test safety net is now very strong; INV-003 specifically benefits from CI guarding the boundary-observation flag against accidental removal.
- [ ] Accessibility API integration for on-screen cursor context. Long-term enhancement that would let the daemon make per-word decisions instead of the binary `_can_correct_next_word` flag — and would be the eventual removal condition for INV-003. Out of scope unless tail-of-word symptoms persist after the adjacent-gap fixes land.
- [ ] Decide on agent pipeline adoption — small project may not justify; revisit if delegation volume picks up.
- [ ] `docs/reference/ENV.md` if env-vars / paths get non-trivial.
- [ ] Per-app exclusion list UI in Settings — audit candidate, not done.
- [ ] "Hotkey to toggle enabled" — second hotkey or triple-press to pause/resume.

## Architectural findings (cumulative across pilots)

- **Smoke-test catches what unit tests cannot.** Session 3's hotfixes (E-0002, E-0003) were both interactive-only bugs. Lesson hardened in `feedback_step_by_step_smoke_testing.md`.
- **User-driven diagnostics outperform top-down theory when symptoms are subjective.** Session 4: orchestrator constructed an elaborate "cursor desync via mouse + paste" theory that the user repeatedly corrected from a simpler vantage point. Theory eventually converged when a single live reproduction showed `arrow + backspace + retype → ог→ju mangle` directly in the now-instrumented log. Lesson: when the user says "у меня всё не так", treat it as evidence the hypothesis is hostile to reality, not as a dispute about details.
- **CGEventTap cannot bridge the buffer-cursor frame-of-reference gap.** Layout-switcher correction is fundamentally a "type now, correct on boundary" pipeline; without on-screen visibility (Accessibility API, never universal across mac apps), the daemon's only safe trust signal is "did I directly observe the boundary that ended the previous word?". This is now codified as INV-003.

---

## Archive index

*(no chunks yet — first archive triggers if PLAN exceeds ~20k chars)*

- `docs/archive/plan-shipped-phases/` — empty.
