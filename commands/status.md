---
description: Warm mid-session check — git detail, last session note, and in-progress backlog. Use when you still have mental context loaded and want a quick pulse. Not for cold starts (use /tools:brief) or planning (use /tools:overview).
allowed-tools: Bash
model: claude-haiku-4-5-20251001
---

## Collect context

Run each command below now before producing output. Store results mentally.

**Today's date and repo**:
```bash
echo "DATE:" && date +%Y-%m-%d
echo "REPO:" && (basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "(not a git repo)")
```

**Git branch and remote sync**:
```bash
git status -b --short 2>/dev/null | head -3 || echo "not a git repo"
```

**Staged changes**:
```bash
git diff --stat --cached HEAD 2>/dev/null || echo "none staged"
```

**Unstaged changes**:
```bash
git diff --stat 2>/dev/null || echo "none"
```

**Untracked files**:
```bash
git ls-files --others --exclude-standard 2>/dev/null | head -10 || echo "none"
```

**Recent commits**:
```bash
git log --oneline -8 2>/dev/null || echo "no commits"
```

**Top-level directory listing**:
```bash
python3 -c "
from pathlib import Path
skip = {'.git', '.venv', 'venv', '__pycache__', 'node_modules'}
cwd = Path('.')
entries = sorted(cwd.iterdir(), key=lambda p: (p.is_file(), p.name))
for e in entries:
    if e.name.startswith('.') or e.name in skip:
        continue
    if e.is_dir():
        count = sum(1 for _ in e.rglob('*') if _.is_file())
        print(f'{e.name}/  ({count} files)')
    else:
        print(e.name)
" 2>/dev/null || ls -1
```

**.claude/ inventory**:
```bash
ls -1 .claude/ 2>/dev/null || echo "none"
```

**Root config files**:
```bash
for f in CLAUDE.md .gitignore pyproject.toml package.json Makefile; do
  test -f "$f" && echo "present: $f" || echo "absent:  $f"
done
```

**Hooks configured**:
```bash
python3 -c "
import json
from pathlib import Path
found = False
for src in ['hooks/hooks.json', '.claude/settings.json']:
    p = Path(src)
    if not p.exists():
        continue
    try:
        d = json.loads(p.read_text())
        hooks = d.get('hooks', {})
        for event, entries in hooks.items():
            count = sum(len(e.get('hooks', [])) for e in entries)
            if count:
                print(f'{event}: {count} handler(s)  [{src}]')
                found = True
    except Exception:
        pass
if not found:
    print('none configured')
" 2>/dev/null || echo "none configured"
```

**MCP servers (user scope)**:
```bash
python3 -c "
import json, os
from pathlib import Path
cfg = Path.home() / '.claude.json'
if not cfg.exists():
    print('~/.claude.json not found')
else:
    d = json.loads(cfg.read_text())
    servers = d.get('mcpServers', {})
    print('user scope: ' + ', '.join(servers.keys()) if servers else 'none at user scope')
" 2>/dev/null || echo "none"
```

**This session's log entries**:
```bash
python3 -c "
import os, re, sys, subprocess
from pathlib import Path
sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts')
from _scope import get_scope

# Get current session ID from collect-summarize.py
result = subprocess.run(['python3', os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts/collect-summarize.py'],
                        capture_output=True, text=True)
session_id = ''
for line in result.stdout.splitlines():
    if line.startswith('SESSION:'):
        session_id = line.split(':', 1)[1].strip()[:8]
        break

mode, data, cwd = get_scope()
projects_dir = Path.home() / '.claude' / 'projects'
if mode == 'single':
    key = data
else:
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
        key = git_root.replace('/', '-')
    except Exception:
        print('(could not determine project)')
        sys.exit(0)
log = projects_dir / key / 'memory' / 'session-log.md'
if not log.exists():
    print('(no session log)')
    sys.exit(0)
text = log.read_text()
blocks = re.split(r'(?=^## \d{4}-\d{2}-\d{2})', text, flags=re.MULTILINE)
if session_id:
    matched = [b for b in blocks if session_id in b]
    if matched:
        print('\n'.join(matched)[:1200])
    else:
        print('(no log entries yet this session)')
else:
    print('(could not determine session ID)')
" 2>/dev/null || echo "(unavailable)"
```

**In Progress / Up Next (TaskWarrior)**:
```bash
REPO=$(git rev-parse --show-toplevel 2>/dev/null | xargs basename 2>/dev/null)
DOMAIN=$(git rev-parse --show-toplevel 2>/dev/null | sed 's|.*/Repos/||' | cut -d'/' -f1)
TW_PROJECT="${DOMAIN}.${REPO}"
echo "IN_PROGRESS:" && (task rc.verbose=nothing project:${TW_PROJECT} +ACTIVE list 2>/dev/null || echo "(none)")
echo "UP_NEXT:" && (task rc.verbose=nothing project:${TW_PROJECT} limit:3 list 2>/dev/null || echo "(none)")
```

**Current session**:
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-summarize.py
```

**Git diff hunk headers** (what changed inside files):
```bash
git diff HEAD --unified=0 2>/dev/null | grep '^@@' | head -20 || echo "no diff"
```

**Project extension**:
```bash
cat .claude/status.md 2>/dev/null || echo "(no project extension)"
```

---

## Your role

Read all auto-collected context above and produce a **project status report**. Read-only snapshot — no writes, no questions, one screenful.

---

## Output format

```
## Status — [repo] — [date]

### Git state
Branch: [branch] [ahead N / behind N / up to date / no remote]
Staged:   [file: +N -N, ...] or "nothing staged"
Unstaged: [file: +N -N, ...] or "clean"
Untracked: [N files] or "none"
Hunks: [@@-header lines showing which regions changed, or "none"]

Recent commits:
  [8 lines from git log --oneline]

### Architecture
[top-level dirs, each with file count]
.claude/: [contents listed]
Config: [present/absent for each root config file]
Hooks: [event types + handler counts, or "none configured"]
MCP: [registered server names, or "none at user scope"]

### In Progress
[first task from IN_PROGRESS, or "(nothing in progress)"]

Up Next: [top tasks from UP_NEXT, one per line indented, or "(none)"]

### This session
Session: [SESSION first 8 chars from collect-summarize.py] — [TITLE if set, else "(untitled)"]
Files changed: [FILES_TOUCHED list, one per line indented, or "none"]

### This session log
[entries from session-log.md matching current session ID — key bullets only; "(no log entries yet this session)" if none]

### [Extension sections]      ← inserted here if .claude/status.md was injected; omit if no extension

### Next steps
- [inferred from git state + extension-provided bullets]
(max 4–6 bullets, most important first)
```

**Next steps inference rules:**
- Staged files exist → "Ready to commit: [N] files ([names])"
- Unstaged modifications → "Unstaged changes in [N] files — stage or stash before commit"
- Untracked files > 0 → "Untracked files: consider adding or .gitignoring"
- Behind remote → "Behind remote — run git pull"
- Extension provides additional next-step bullets → append them

---

## Project-specific sections (if extension loaded)

If `.claude/status.md` content was injected above (not "(no project extension)"):
render the sections described in that content, inserting them between Architecture and Next steps.
Append any next-step bullets specified by the extension to the Next steps section.

---

## Constraints

- No writes of any kind
- No questions
- Haiku only — keep it fast
- Output fits in one screenful
