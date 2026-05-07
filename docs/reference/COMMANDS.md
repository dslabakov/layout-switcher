# Build & Deploy Commands

> Last updated: 2026-05-07 (bootstrap)

---

## First-time local setup

```bash
cd /Users/slabakov/dev/Layoutswitcher
bash setup.sh
```

`setup.sh` does:
- Create `.venv/` if missing.
- Install `requirements.txt` into `.venv/`.
- Build EN wordlist via `scripts/build_wordlist.py` (output goes to `~/.config/layout-switcher/`).
- Copy `config.example.yaml` → `~/.config/layout-switcher/config.yaml` (only if not already present).

**Note:** `install.sh` is the end-user one-liner that clones to `~/layout-switcher` and then runs `setup.sh`. For local dev work in this repo, skip `install.sh` and call `setup.sh` directly.

---

## Run in foreground (smoke test, dev)

```bash
cd /Users/slabakov/dev/Layoutswitcher
source .venv/bin/activate
python3 -m src.main
```

**Required permission:** macOS Accessibility for the running terminal AND for the python interpreter (System Settings → Privacy & Security → Accessibility). On first run macOS will prompt; grant to terminal binary path. If the event tap doesn't activate, check the prompt + retry.

Stop with `Ctrl-C` (clean shutdown of CGEventTap).

---

## Run via launchd (production / always-on)

### Install LaunchAgent

```bash
# After source changes — re-substitute placeholders + reload.
PLIST_TEMPLATE=/Users/slabakov/dev/Layoutswitcher/com.layout-switcher.plist
PLIST_INSTALLED=$HOME/Library/LaunchAgents/com.layout-switcher.plist
LOG_DIR=$HOME/Library/Logs/layout-switcher
mkdir -p "$LOG_DIR"

VENV_PYTHON=/Users/slabakov/dev/Layoutswitcher/.venv/bin/python3
SRC_MAIN=/Users/slabakov/dev/Layoutswitcher/src/main.py

sed -e "s|__VENV_PYTHON__|$VENV_PYTHON|g" \
    -e "s|__SRC_MAIN__|$SRC_MAIN|g" \
    -e "s|__LOG_DIR__|$LOG_DIR|g" \
    "$PLIST_TEMPLATE" > "$PLIST_INSTALLED"
```

### Bootstrap / reload / unload

```bash
# Bootstrap (modern launchd command — preferred over deprecated `load`)
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.layout-switcher.plist

# Force restart immediately (skip the StartInterval / KeepAlive cooldown)
launchctl kickstart gui/$(id -u)/com.layout-switcher

# List
launchctl list | grep com.layout-switcher

# Tail logs
tail -f ~/Library/Logs/layout-switcher/stderr.log
tail -f ~/Library/Logs/layout-switcher/stdout.log

# Unload
launchctl bootout gui/$(id -u)/com.layout-switcher

# Uninstall completely
rm ~/Library/LaunchAgents/com.layout-switcher.plist
```

---

## Tests

```bash
cd /Users/slabakov/dev/Layoutswitcher
source .venv/bin/activate
pytest                       # full suite
pytest tests/test_layout_mapper.py        # single file
pytest tests/test_layout_mapper.py::test_specific_thing -v   # single test, verbose
```

CI is not configured yet. Local tests only. Always pass before merging.

---

## Build EN wordlist (regenerate)

```bash
source .venv/bin/activate
python3 scripts/build_wordlist.py
```

Reads macOS system dictionary + appends tech terms. Writes to `~/.config/layout-switcher/wordlist.txt` (or wherever the script's default output path resolves to — verify against the script).

Re-run if:
- macOS dictionary updated.
- Want to add domain-specific tech terms (script likely has a constant list to extend).

---

## Git workflow

### Daily

```bash
git status
git fetch origin upstream
git log --oneline origin/main..HEAD          # what's local-only
git log --oneline HEAD..upstream/main        # what's new upstream
```

### Sync from upstream

See `docs/reference/UPSTREAM-SYNC.md` for full procedure. Summary:

```bash
git fetch upstream
git checkout -b upstream-merge/$(date +%Y-%m-%d)
git merge upstream/main
# resolve conflicts; run pytest; commit
git push origin HEAD
gh pr create --base main --title "upstream-merge: $(date +%Y-%m-%d)" --body "Sync from moiz2306/layout-switcher"
# orchestrator review → merge
```

### Branch from main for feature work

```bash
git checkout main && git pull origin main
git checkout -b feature/<short-name>
# ... agent does work ...
git push -u origin feature/<short-name>
gh pr create --base main --fill
```

---

## Useful one-liners

```bash
# List py files + line counts (good for STRUCTURE refresh)
find src -name "*.py" -exec wc -l {} +

# Find TODO / FIXME / XXX comments without reading source bodies (orchestrator-allowed via grep)
grep -rE 'TODO|FIXME|XXX' src/ scripts/ --include="*.py" | head -20

# Verify .venv has correct python
.venv/bin/python3 --version
.venv/bin/python3 -c 'import pyobjc, pymorphy3, yaml; print("deps OK")'

# Quick diff of any local divergence from upstream
git fetch upstream
git diff upstream/main..HEAD -- src/   # only src changes
git diff --stat upstream/main..HEAD     # summary across files

# Test launchd plist substitution dry-run (without installing)
sed -e "s|__VENV_PYTHON__|/path|g" -e "s|__SRC_MAIN__|/path|g" -e "s|__LOG_DIR__|/path|g" com.layout-switcher.plist
```
