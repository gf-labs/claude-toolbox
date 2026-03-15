---
description: Claude Code environment + project health check
allowed-tools: Bash, Read, Glob, Grep, Edit
model: claude-sonnet-4-6
---

## Collect context

Run each command below now before proceeding. Store results mentally.

**Today's date, repo, CLAUDE.md**:
```bash
echo "DATE:" && date +%Y-%m-%d
echo "REPO:" && (basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "(not a git repo)")
echo "CLAUDE_MD:" && (test -f CLAUDE.md && echo "present" || echo "MISSING")
```

**Commands and scripts**:
```bash
echo "COMMANDS:" && (ls commands/*.md 2>/dev/null || echo "none")
echo "SCRIPTS:" && (ls scripts/*.py 2>/dev/null || echo "none")
```

**hooks.json**:
```bash
cat hooks/hooks.json 2>/dev/null || echo "NOT FOUND"
```

**plugin.json**:
```bash
cat .claude-plugin/plugin.json 2>/dev/null || echo "NOT FOUND"
```

**pyproject.toml**:
```bash
test -f pyproject.toml && echo "EXISTS" || echo "MISSING"
```

**JSON validity**:
```bash
python3 -c "
import json, glob
files = []
for pattern in ['*.json', '.claude/*.json', '.claude-plugin/*.json', 'hooks/*.json']:
    files.extend(glob.glob(pattern))
files = sorted(set(files))
if not files:
    print('no JSON files found')
else:
    for f in files:
        try:
            json.load(open(f))
            print('OK: ' + f)
        except Exception as e:
            print('ERROR: ' + f + ': ' + str(e))
" 2>/dev/null || echo "python3 not available"
```

**Python syntax**:
```bash
python3 -c "
import py_compile
from pathlib import Path
files = [str(f) for f in Path('.').rglob('*.py')
         if not any(p in f.parts for p in ['.git', '.venv', '__pycache__', 'node_modules'])]
if not files:
    print('no Python files found')
else:
    for f in sorted(files):
        try:
            py_compile.compile(f, doraise=True)
            print('OK: ' + f)
        except py_compile.PyCompileError as e:
            print('ERROR: ' + f + ': ' + str(e))
" 2>/dev/null || echo "python3 not available"
```

**.gitignore**:
```bash
cat .gitignore 2>/dev/null || echo "not found"
```

---

@~/.claude/commands/doctor.md

---

## Project health checks

Run after the Claude environment checks above. Prefix findings P1–P8. Same severity model ([CRITICAL] / [WARN] / [INFO] / [PASSED]).

### P1 — CLAUDE.md present
Read the CLAUDE.md output above.
- `[WARN]` if MISSING — Claude sessions run without project instructions
- `[PASSED]` if present

### P2 — JSON validity
Interpret the JSON validity output above.
- `[CRITICAL]` if any file shows `ERROR:` — malformed JSON breaks hooks and plugin loading silently
- `[PASSED]` if all files show `OK:` or no JSON files found

### P3 — Python syntax
Interpret the Python syntax output above.
- `[CRITICAL]` if any file shows `ERROR:` — syntax errors cause hooks to fail silently on every tool use
- `[PASSED]` if all files show `OK:` or no Python files found

### P4 — .gitignore completeness
Read the .gitignore above. Check entries relevant to what's present in this repo:
- `.venv/` or `venv/` — `[WARN]` if Python files exist but neither is in .gitignore
- `__pycache__/` — `[WARN]` if Python files exist but missing
- `*.pyc` — `[WARN]` if Python files exist but missing
- `.env` — `[INFO]` if not present (commonly needed but not always)
- `.mcp.json` — `[WARN]` if `.mcp.json.example` exists but `.mcp.json` is not ignored
`[PASSED]` if all relevant entries are present.

### P5 — Scripts referenced by commands exist
From the Commands output above, extract all script references:
```bash
grep -h 'scripts/[a-z_-]*\.py' commands/*.md | grep -oE 'scripts/[a-z_/-]+\.py' | sort -u
```
For each referenced script path, check it exists with `test -f`.
- `[CRITICAL]` if any referenced script is missing
- `[PASSED]` if all referenced scripts exist

### P6 — hooks.json has wired hooks
Read the hooks.json output above.
- `[WARN]` if hooks.json is missing or contains no wired hook events
- `[PASSED]` if at least one hook event has entries

### P7 — plugin.json completeness
Read the plugin.json output above. Check for: `name`, `version`, `description`, `author`, `license`, `keywords`.
- `[WARN]` for each missing field
- `[PASSED]` if all fields present

### P8 — pyproject.toml with lint rules
Read the pyproject.toml output above.
- `[WARN]` if MISSING
- Use Bash to check for `select` key: `grep -c 'select' pyproject.toml 2>/dev/null || echo 0`
- `[WARN]` if present but no `select` key under `[tool.ruff.lint]`
- `[PASSED]` if exists with lint rules configured

---

## Output format

```
## Doctor — [repo] — [date]

### Claude Environment
[output from global doctor checks 1–7]

### Project Health
[CRITICAL/WARN/INFO/PASSED] PN — Check name
- Finding: [specific detail]
- Fix: [exact action]
```

List issues first (CRITICAL before WARN), then PASSED/INFO at the bottom.

---

## After the report

Ask: "Fix issues automatically? Reply `fix all`, `fix [check]` (e.g. `fix P2 P4`), or `skip`."

Auto-fixable: P4 (.gitignore additions).
Manual: P1 (create CLAUDE.md), P2 (fix JSON), P3 (fix Python).

If fixing: use Edit for targeted changes. Report each as `[fixed] path — what changed`.
