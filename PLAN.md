# PLAN — Layoutswitcher

> Prospective ("what to do next"), NOT retrospective. Per-session retrospectives live in `SESSION_RESUME.md`.
> Target size: ≤ 20k chars.

---

## Next Session — Start Here

The campaign of session 3 is complete (14+1 PRs, all merged, daemon comprehensively defended). No urgent must-do items. Pick from the backlog by appetite:

1. **Quick cleanup wins (S, < 30 min each):** hoist `CGEventKeyboardSetUnicodeString` import, mock `frontmostApplication` in `test_get_active_app_returns_string`, delete `.venv-old-x86`.
2. **Quality improvements (S, audit-leftover):** `_is_stale()` count only `("check",)` items; cross-app replay-buffer leak fix in `("clear",)` handler.
3. **Audit candidates not yet picked up (S/M):** per-app exclusion list UI; "hotkey to toggle enabled" (separate hotkey for pause/resume).
4. **CI (M):** GitHub Actions running pytest on PR. Prerequisite: `test_get_active_app_returns_string` mocked. The 195-test safety net makes CI now meaningfully valuable.

## Active backlog (refreshed)

- [ ] Hoist `CGEventKeyboardSetUnicodeString` out of `_type_string` per-iter loop — PR-J agent flagged.
- [ ] Replace `test_get_active_app_returns_string` real `NSWorkspace` call with mock — needed for headless CI.
- [ ] `_is_stale()` count only `("check",)` items, not all queue messages — precision improvement.
- [ ] Cross-app replay-buffer leak — discard replay buffer in `("clear",)` handler so chars typed in app A during correction don't get retyped into app B after Cmd+Tab.
- [ ] Eventually delete `.venv-old-x86` backup.

## Pending — pick when needed

- [ ] CI setup (GitHub Actions, run pytest on PR). Now meaningfully valuable thanks to 195 tests.
- [ ] Decide on agent pipeline adoption — small project may not justify; revisit if delegation volume picks up. Single-session campaigns of session 3's scale are the strongest argument so far for some workflow automation.
- [ ] `docs/reference/ENV.md` if env-vars / paths get non-trivial.
- [ ] Per-app exclusion list UI in Settings — audit candidate, not done.
- [ ] "Hotkey to toggle enabled" — second hotkey or triple-press to pause/resume; audit candidate.

## Architectural findings (cumulative across pilots)

- **Smoke-test catches what unit tests cannot.** Session 3's 2 hotfixes (E-0002 modifier-flag bleed, E-0003 Tab-as-boundary on Cmd+Tab) were both pre-existing upstream bugs that no unit test could have surfaced — they require interactive HID-level event timing with human-held modifier keys. Lesson hardened in `feedback_step_by_step_smoke_testing.md`. For any change touching CGEventTap or synthetic-event injection, schedule interactive smoke-test as a mandatory step, not a nice-to-have.

---

## Archive index

*(no chunks yet — first archive triggers if PLAN exceeds ~20k chars)*

- `docs/archive/plan-shipped-phases/` — empty.
