---
description: Repo audit — universal checks for any codebase (JSON, Python, .gitignore, settings, hooks)
allowed-tools: Read, Glob, Grep, Bash, Edit
---

## Auto-collected context

**Today's date**: !`date +%Y-%m-%d`

**Repo**: !`basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "(not a git repo)"`

**CLAUDE.md**: !`test -f CLAUDE.md && echo "present" || echo "MISSING"`

**JSON files (repo root + .claude/)**: !`find . -maxdepth 2 \( -path './.git' -prune -o -path './.venv' -prune \) -o -name '*.json' -print 2>/dev/null | sort | grep -v "\.git\|\.venv\|node_modules\|__pycache__"`

**JSON validity**:
!`python3 -c "
import json, sys
from pathlib import Path
import glob

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
" 2>/dev/null || echo "python3 not available"`

**Python files**:
!`find . -name '*.py' -not -path './.git/*' -not -path './.venv/*' -not -path './__pycache__/*' -not -path './node_modules/*' 2>/dev/null | sort || echo "none"`

**Python syntax**:
!`python3 -c "
import py_compile, glob, sys
from pathlib import Path

files = []
for f in Path('.').rglob('*.py'):
    parts = f.parts
    if any(p in parts for p in ['.git', '.venv', '__pycache__', 'node_modules']):
        continue
    files.append(str(f))

if not files:
    print('no Python files found')
else:
    for f in sorted(files):
        try:
            py_compile.compile(f, doraise=True)
            print('OK: ' + f)
        except py_compile.PyCompileError as e:
            print('ERROR: ' + f + ': ' + str(e))
" 2>/dev/null || echo "python3 not available"`

**.gitignore**: !`cat .gitignore 2>/dev/null || echo "not found"`

**.claude/settings.json**: !`cat .claude/settings.json 2>/dev/null || echo "not found"`

---

## Your role

You are a repo consistency auditor running universal checks. Use only the auto-collected context above — do not read additional files. Be precise and cite specific filenames.

---

## Universal checks

### U1 — CLAUDE.md present

- `[WARN]` if MISSING — Claude sessions run without project instructions
- `[PASSED]` if present

### U2 — JSON validity

Interpret the JSON validity output.

- `[CRITICAL]` if any file shows `ERROR:` — malformed JSON breaks hooks and plugin loading silently
- `[PASSED]` if all files show `OK:` or no JSON files exist

### U3 — Python syntax

Interpret the Python syntax output.

- `[CRITICAL]` if any file shows `ERROR:` — syntax errors cause hooks to fail silently on every tool use
- `[PASSED]` if all files show `OK:` or no Python files exist

### U4 — .gitignore completeness

Read the .gitignore above. Check for entries that are relevant to this repo based on what's present:

- `.venv/` or `venv/` — `[WARN]` if Python files exist but neither is in .gitignore
- `__pycache__/` — `[WARN]` if Python files exist but missing
- `*.pyc` — `[WARN]` if Python files exist but missing
- `.env` — `[INFO]` if not present (commonly needed but not always)
- `.mcp.json` — `[WARN]` if `.mcp.json.example` exists but `.mcp.json` is not ignored (contains absolute paths)

`[PASSED]` if all relevant entries are present.

### U5 — Hook script integrity

Read `.claude/settings.json`. For every `command:` value that references a script path (e.g., `python3 /some/path/script.py`):

- Extract the script file path
- `[CRITICAL]` if the file does not exist at that path

Use Bash `test -f /path` to verify. Skip commands that are pure shell builtins.
`[INFO]` if no project settings file found.

---

## Output format

```
## Audit Results — [repo] — [date]

### [N] issue(s) found

**[SEVERITY] UN — Check name**
- Finding: [specific, file/line where possible]
- Fix: [exact action]

[PASSED] UN — Check name — ok
[INFO] UN — Check name — note
```

List issues first (CRITICAL before WARN), then PASSED/INFO at the bottom.

---

## After the report

Ask: "Fix issues automatically? Reply `fix all`, `fix [check]` (e.g. `fix U2 U4`), or `skip`."

Auto-fixable: U4 (.gitignore additions).
Manual: U1 (create CLAUDE.md), U2 (fix JSON), U3 (fix Python), U5 (fix hook paths).

If fixing: use Edit for targeted changes. Report each as `[fixed] path — what changed`.
