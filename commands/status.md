---
description: Current project state — git detail, architecture snapshot, and next steps
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

Recent commits:
  [8 lines from git log --oneline]

### Architecture
[top-level dirs, each with file count]
.claude/: [contents listed]
Config: [present/absent for each root config file]
Hooks: [event types + handler counts, or "none configured"]
MCP: [registered server names, or "none at user scope"]

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
