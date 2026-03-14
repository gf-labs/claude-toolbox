---
description: Rename sessions based on their content — proposes names from commits and first messages
argument-hint: [pattern | --unnamed] [--force]
allowed-tools: Bash, Read
---

## Arguments

`$ARGUMENTS`

Parse from arguments:
- **pattern** — substring to match against session title/first-message/last-prompt (same as search-sessions)
- `--unnamed` — target only sessions with no custom-title (mutually exclusive with pattern)
- `--force` — allow renaming sessions that already have a custom-title
- **(none)** — same as `--unnamed` (default: find unnamed sessions in scope)

---

## Step 1 — Find target sessions

```bash
python3 -c "
import json, os, sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.environ.get('CLAUDE_TOOLBOX_ROOT', '') + '/scripts')
try:
    from _scope import get_scope
    _m, _d, _ = get_scope()
    _allowed = {_d} if _m == 'single' else ({k for k, _ in _d} if _m == 'parent' else None)
except Exception:
    _allowed = None

raw = 'ARGUMENTS_PLACEHOLDER'
args = raw.split()
force = '--force' in args
unnamed_only = '--unnamed' in args or not any(a for a in args if not a.startswith('--'))
pattern = ' '.join(a for a in args if not a.startswith('--')).lower().strip()

projects_dir = Path.home() / '.claude' / 'projects'
results = []

for proj in sorted(projects_dir.iterdir()):
    if not proj.is_dir(): continue
    if _allowed is not None and proj.name not in _allowed: continue
    for f in sorted(proj.glob('*.jsonl'), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            custom_title = ''
            first_user = ''
            last_prompt = ''
            commits = []
            for line in f.read_text(errors='replace').splitlines():
                if not line.strip(): continue
                obj = json.loads(line)
                t = obj.get('type', '')
                if t == 'custom-title':
                    custom_title = obj.get('customTitle', '')
                if t == 'last-prompt' and not last_prompt:
                    last_prompt = obj.get('lastPrompt', '')[:100]
                if t == 'user' and not first_user:
                    msg = obj.get('message', {})
                    content = msg.get('content', '')
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get('type') == 'text':
                                first_user = c.get('text', '')[:120]; break
                    elif isinstance(content, str):
                        first_user = content[:120]
                if t == 'assistant':
                    for block in obj.get('message', {}).get('content', []):
                        if isinstance(block, dict) and block.get('type') == 'tool_result':
                            for inner in block.get('content', []):
                                if isinstance(inner, dict) and inner.get('type') == 'text':
                                    txt = inner.get('text', '')
                                    if 'git commit' in txt.lower() or txt.startswith('[main') or txt.startswith('[master'):
                                        lines = txt.strip().splitlines()
                                        if lines:
                                            commits.append(lines[0][:80])

            if unnamed_only and custom_title and not force:
                continue
            if pattern and pattern not in (custom_title + ' ' + first_user + ' ' + last_prompt).lower():
                continue
            if custom_title and not force and not unnamed_only:
                continue

            age_days = int((datetime.now().timestamp() - f.stat().st_mtime) / 86400)
            proj_name = proj.name.split('-')[-1] if '-' in proj.name else proj.name
            print(f'SESSION|{f}|{f.stem[:8]}|{proj_name}|{age_days}d|{custom_title}|{(commits[0] if commits else first_user)[:80]}')
        except Exception:
            pass
"
```

Replace `ARGUMENTS_PLACEHOLDER` with the raw `$ARGUMENTS` string.

If no sessions found: say "No unnamed sessions found in scope." and stop.

---

## Step 2 — Propose names

For each SESSION line, derive a proposed name:

**Source priority** (use first available):
1. The commit message in the last field — strip `[main ...] `, strip leading `feat:` / `fix:` / `chore:` / `docs:` prefixes, strip trailing `(vX.Y.Z)` version suffixes
2. The first user message — take the first 5–7 significant words

**Format rules:**
- kebab-case, max 5 words
- Lowercase, spaces → hyphens, strip punctuation
- No dates, no generic words: `session`, `work`, `update`, `changes`, `misc`
- Examples: `plan-map-refactor`, `brief-enhancements`, `lint-hook-setup`

If the session already has a custom-title (shown in field 6) and `--force` was passed, keep the proposed name but note the override.

---

## Step 3 — Display review table

```
### Rename proposals — [N] session(s)

| Session | Project | Age | Current name | Proposed name | Source |
|---------|---------|-----|--------------|---------------|--------|
| 4794c719 | claude-toolbox | 3d | (none) | lint-hook-setup | commit |
| a5734a17 | ramp | 12d | (none) | knowledge-graph-refactor | commit |
| 9d302b76 | claude-toolbox | 28d | old-name | brief-enhancements | message |
```

Mark the Source column: `commit` if derived from a git commit, `message` if from the first user message.

Ask: "Apply these renames? Reply `yes` to apply all, `edit` to modify individual names, or `skip`."

---

## Step 4 — Apply renames

**If `yes`:** apply all proposed renames:
```bash
python3 $CLAUDE_TOOLBOX_ROOT/scripts/name-session.py "PROPOSED_NAME" --path /full/path/to/session.jsonl --force
```
Repeat for each session. Report: "Renamed [N] session(s)."

**If `edit`:** show each proposed rename one at a time:
```
Session 4794c719 → "lint-hook-setup"
Accept? Reply the name to use, `skip` to leave unchanged, or `yes` to accept.
```
Apply confirmed renames with the same command above.

**If `skip`:** say "No renames applied." and stop.

---

## Constraints

- Never rename the current active session (most recent JSONL by mtime in the current project) — skip it silently
- Always use `--force` flag with `name-session.py` since we're intentionally overriding
- Do not fabricate names — derive only from actual content in the session
