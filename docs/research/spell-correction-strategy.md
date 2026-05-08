# Spell-correction & Swift-port — strategy & research findings

> Captured 2026-05-08, session 5. **Discussion-only session — no source changes.**
> Status: **deferred**. User explicitly said «пока ничего не хочу делать». This file is reference for future revisit.

---

## Context

User asked: «is on-the-fly spell-correction (typo fixing as you type, separate from layout switching) feasible to add to Layoutswitcher? How hard, LLM or not?»

Discussion broadened to:
- existing solutions in the system-wide-spell-correction niche (Reddit / GitHub / HN research)
- multilingual support
- map of feature possibilities for open-source distribution
- reconsidering the 2026-05-07 Python-vs-Swift decision in distribution context
- two-track strategy: prototype on Python, port to Swift after spec stabilizes

---

## Findings

### 1. Spell-correction fits the current pipeline trivially

The existing daemon already implements: CGEventTap → `WordBuffer` accumulator → boundary trigger → validity check → if invalid, `AutoCorrector.correct()` does backspace+retype. **Replacing «invalid → convert layout» with «invalid → find nearest correct spelling» is the same pipeline, different engine in the middle.**

INV-003 (`_can_correct_next_word` flag) is a feature, not an obstacle: spell-correction inherits the same desync protection for free.

**MVP estimate:** 4-8 hours (one new module `spell_corrector.py`, one engine call, reused `AutoCorrector.correct()`, config flag).
**Production-quality** (false-positive triage, per-app exclusion, code-aware mode) — weeks of edge-case work.

---

### 2. Existing solutions in the niche

Researched via background fork agent (Reddit, GitHub, HN). Categorized:

| Project | Type | License | Approach | Notes |
|---|---|---|---|---|
| **Charm** | Commercial native macOS | $9.99 one-time | CGEventTap → boundary spell-check → AX inject | **Closest analog.** On-device, 200ms, all apps. https://www.theodorehq.com/charm |
| **Caramba Switcher** | Commercial App Store | Subscription | Layout + spell + Double-Capital + per-app | Author of original Punto Switcher. RU/EN. |
| **Espanso** | Open Rust | GPL | Fixed-dictionary substitutions | NOT fuzzy. Community ~8000 EN typos pack. Misses novel typos. https://github.com/espanso/espanso |
| **KeySwitcher** | Open Swift | — | Layout + AI typo polish | Polish via right-Option hotkey, not on boundary. https://github.com/graninilya/keyswitcher |
| **LanguageTool** | Open Java | LGPL | Local server + native helper | Mail/Notes/Slack/Word — not system-wide. Heavy startup. |
| **Grammarly** | Commercial | Subscription | Cloud LLM | Not fully system-wide. |
| **macOS built-in** | First-party | — | NSSpellChecker per-app | Only in NSTextView-based apps; widely disabled by users due to false positives. |

**Open-source niche gap:** Python daemon for system-wide spell correction on macOS does not exist. FOSS unified tool (layout + adaptive spell, RU+EN, privacy-first) does not exist. **Layoutswitcher is positioned to fill this gap if extended.**

---

### 3. Recommended engine: `NSSpellChecker` via pyobjc

Why it beats alternatives for our case:

- `pyobjc-framework-Cocoa` is already in `requirements.txt` — **zero new dependencies**.
- Auto-detects language per-word (RU/EN/mixed) via `correctionForWordRange:in:String:language:None:inSpellDocumentWithTag:`.
- Returns single concrete candidate or `None` — built-in confidence gate.
- Uses user's personal dictionary from System Settings.
- Microsecond latency, fully offline.

API sketch:

```python
from AppKit import NSSpellChecker

checker = NSSpellChecker.sharedSpellChecker()
candidate = checker.correctionForWordRange_inString_language_inSpellDocumentWithTag_(
    (0, len(word)), word, None, 0   # None = auto-detect language
)
if candidate and candidate != word:
    auto_corrector.correct(word, candidate)
```

Alternatives considered and why not (for MVP):

| Engine | Why not |
|---|---|
| **SymSpell** | Fastest but no contextual understanding, must self-host wordlists |
| **Hunspell** | Best EN accuracy but no Russian morphology context |
| **JamSpell** | Has bigram context, but requires ~200MB pre-trained model files |
| **LanguageTool** | Heavy Java server, startup overhead unacceptable |
| **Cloud LLM** | Latency incompatible with inline boundary trigger |

---

### 4. Multilingual support — free with `NSSpellChecker`

Works out of the box for any language with macOS dictionary installed (System Settings → Keyboard → Text Input → Edit). Includes: EN (US/UK/AU), RU, DE, FR, IT, ES, PT, NL, PL, CS, SE, DK, NO, FI, TR, EL, HE, AR, KO, JA, ZH (Simp/Trad), UK, HU, RO, VI, TH, ...

Auto-detection (`language=None`) handles mixed-language text per-word, e.g., «Слушай, нужно push-нуть в master, или ты forgot?» — каждое слово проверяется на своём языке без эвристик с нашей стороны.

What doesn't work:

- **CJK / Thai** — no spaces between words. Our `WordBuffer` is fundamentally boundary-based; CJK needs morphological segmentation, not feasible on CGEventTap. **Different product.**
- **RTL (Arabic, Hebrew)** — pipeline-logically works, but `correct()` via backspace+retype in RTL contexts may behave unpredictably (cursor direction, backspace direction). Needs live testing per app.
- **Languages without macOS dictionary** — NSSpellChecker silently returns `None`, no degradation; feature simply doesn't work for that language.

---

### 5. Feature roadmap (open-source distribution lens)

If we extend toward a community product, here's the addressable feature surface:

**Group 1 — text corrections (same boundary pipeline):**
- Spell correction (NSSpellChecker)
- Punctuation: `..` → `…`, `--` → `—`, smart quotes
- Capitalization after `.`, `?`, `!`
- Double-Capital fix (`HEllo` → `Hello`)
- Ё-фикация / де-ёфикация (RU)

**Group 2 — layout extensions:**
- 3rd/4th language (UK, DE, FR if user adds keyboard layouts)
- Auto-detection of intended layout — switch system layout to match started word (vs. retyping)
- Per-app behavior — off in IDE/terminal, on in Slack/Mail

**Group 3 — UX layer:**
- Undo history (multi-step rollback via hotkey)
- Suggestions popup for low-confidence corrections (vs. auto-replace)
- Custom dictionary UI (menu bar)
- Per-app exclusion list (already in PLAN.md backlog)
- Statistics — corrections/day, undo rate
- Pause-to-confirm mode for low-trust users

**Group 4 — LLM layer (separate from boundary, on pause >500ms):**
- Grammar correction (whole sentence)
- Style/tone rewriting via hotkey (select paragraph → formal/casual)
- Translation
- Local LLM (llama.cpp, MLX on M-chips) for privacy-first positioning

**Group 5 — integrations:**
- Text expansion à la Espanso (`@em` → email)
- Code-aware mode (camelCase/snake_case/URL/path → don't touch)
- Personal learning from declined corrections
- Plugin architecture for community language/rule packs

---

### 6. Common pitfalls (research-derived)

**Top user complaint about all autocorrect tools: false positives.** macOS built-in is widely disabled for this reason. Threshold: only act on a single unambiguous candidate; otherwise stay silent.

**Double-correction:** if app has its own NSSpellChecker (NSTextView), our daemon adds conflict. **App-exclusion list mandatory.**

**Names, URLs, code:** `git push`, camelCase, paths must be ignored. Without this, false positives on technical text are unbearable.

**Mixed-language:** must auto-switch validation language. NSSpellChecker handles this; other engines don't.

**Case preservation:** `RECIEVE` → `RECEIVE`, not `receive`.

**Privacy:** cloud LLM autocorrect has obvious objections. Local-only is a marketable USP against Grammarly et al.

---

### 7. Swift-port re-evaluated (correction to 2026-05-07 DECISIONS)

The 2026-05-07 entry rejected Swift rewrite citing:
- (a) weeks of work
- (b) loss of `pymorphy3` (no Russian morphology equivalent on Swift)
- (c) `NaturalLanguage.framework` «qualitatively weaker for our needs»

That was correct **for personal-use context** — environmental fix existed, port not justified.

**For community-distribution context, the calculus shifts:**

1. **`pymorphy3` loss is not a blocker if spell-correction is the new core.** NSSpellChecker has its own Russian system dictionary, doesn't need pymorphy3. Pymorphy3 is only needed by current layout-detection logic. If spell-correction becomes primary, pymorphy3 becomes legacy for one narrow case — its loss is a **cost, not a blocker**.

2. **Native Swift gives real distribution advantages:**
   - `.app` bundle, signable, notarizable → brew cask, direct download, no «follow these tccutil instructions»
   - Cold start ~50ms vs Python ~300-500ms
   - No INV-001/INV-002 baggage (TCC attribution to CLI binary, arm64-vs-Rosetta hassles disappear)
   - Charm and Caramba succeed precisely because native; community expects `.dmg`, not `pip install + chmod + plist + tccutil reset`

3. **Cost remains weeks of work** — not «extremely hard», not «won't work». A one-time investment.

**Bottom line correction (from session 5):**

| Context | Optimal |
|---|---|
| Personal use (current) | Python — features iterate cheaply, port doesn't pay back |
| Community distribution | Swift — Python-daemon with Accessibility-on-CLI-binary is an adoption barrier most users won't cross |

**`pymorphy3` portability nuance.** It's not just code — it's library + OpenCorpora dictionary (compiled DAWG, several MB) + heuristic model. Algorithmically all transferable to Swift, but **weeks of work** + lifetime maintenance burden. Alternatives: use `NaturalLanguage.framework` (~70-80% coverage of pymorphy3's job, fails on long/rare/compound words), or run pymorphy3 as a Python subprocess from Swift (defeats most of the distribution gain). For spell-correction via NSSpellChecker, pymorphy3 isn't needed — so the dilemma only matters if Swift-port keeps layout-detection in current form.

---

### 8. Strategic plan: two-track development

User-articulated approach (correct & adopted):

**Track 1 — Python prototype for spec accumulation:**
1. Add spell-correction layer to current Python daemon (NSSpellChecker, MVP-sized).
2. Use it daily; accumulate real-world findings:
   - Which apps need exclusion?
   - Which false-positive patterns recur?
   - Confidence threshold sweet spot?
   - Code/URL/name detection rules?
   - Per-app overrides?
3. Iterate features cheaply on Python.
4. Capture each finding in this file or a `docs/swift-port-spec.md` (whichever stays leaner).

**Track 2 — Swift port when spec stabilizes:**
- Trigger: feature set stops churning, daily-use is bug-free, ready for distribution.
- Estimated several weeks but mostly mechanical translation (spec is known).
- Native `.app` bundle, signed, notarized, no Accessibility-on-CLI-binary footgun.

**Track 3 — Open-source publication:**
- Defer to Swift version. Premature publication of Python daemon = support burden on TCC/arm64 setup issues, distracts from feature iteration.

#### Why two-track beats «Swift now»:

- **Spec is unknown.** Writing Swift now = architecturally clean codebase that misbehaves in production where you didn't predict.
- **Cost-of-change is much lower in Python during exploration.** Add a feature → reload daemon → test in 5 seconds. Swift has rebuild + relink + relaunch + permissions cycle.
- **`pymorphy3` retirement matures naturally.** As spell-correction takes over, layout-detection's pymorphy3 dependency becomes more isolated — easier to either drop or re-implement on Swift port.

#### Mental discipline during Track 1:

For every new feature ask: **«is this spec for Swift or is this Python-specific?»**
- Spec (survives port): per-app exclusion list, confidence thresholds, code-aware regex rules, undo UX.
- Python-specific (gets thrown away): GIL workarounds, queue-ownership pattern (Swift has GCD), pyobjc binding shapes.

Avoids attachment to disposable code.

---

### 9. What to measure when comparing versions

When Swift port arrives, compare with Python on:

| Metric | Python target | Swift target |
|---|---|---|
| Latency on boundary | ~5-30ms | < 5ms |
| Cold start | ~300-500ms | ~50ms |
| Memory footprint | ~80-150MB (interpreter + pymorphy3 dict) | ~20-30MB |
| False-positive rate | engine-dependent (pymorphy3+wordlist) | engine-dependent (NaturalLanguage+NSSpellChecker) |
| **Subjective UX** | — | **most important, hardest to benchmark** |

---

## Deferred decisions

- Whether to add spell-correction to Python daemon at all (user paused; pick up when next bug or motivation arises).
- Whether to actually port to Swift (depends on Track-1 spec accumulation + appetite for distribution).
- Whether to publish open-source (depends on Track-2 + acceptance of maintainer-presence cost).

## Pointers

- Original 2026-05-07 Swift-vs-Python decision: `docs/reference/DECISIONS.md` § «2026-05-07 — Stay on Python...»
- Layout detection logic that pymorphy3 currently powers: `src/auto_corrector.py` (orchestrator: don't read directly; agents can).
- NSSpellChecker pyobjc API: `from AppKit import NSSpellChecker` (already in requirements via `pyobjc-framework-Cocoa`).
- Charm reference implementation (closest analog, closed-source): https://www.theodorehq.com/charm
- Espanso (typo dictionary precedent for FOSS distribution model): https://github.com/espanso/espanso
- Caramba Switcher (closed-source incumbent for RU+EN): https://apps.apple.com/us/app/caramba-switcher-autocorrect/id1565826179

---

## How to revisit

When motivation returns:

1. **Re-read this file.**
2. Decide: prototype spell-correction now (Track 1 start), or wait for fresh bug/feature trigger.
3. If starting Track 1: spec a Sonnet agent with «add `spell_corrector.py` using NSSpellChecker, hook into boundary trigger after layout-check, reuse `AutoCorrector.correct()`, off by default behind config flag, ~MVP-sized PR».
4. Update this file with what worked, what surprised, what needs spec changes.
5. When Track 1 has stabilized for ~1-2 months of daily use → consider Track 2 (Swift port).
