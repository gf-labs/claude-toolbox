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

**Invocation mode**:
```bash
echo "${ARGUMENTS:-}"
```

---

**Scope**:
```bash
python3 -c "
import os, subprocess
from pathlib import Path
cwd = Path(os.getcwd())
cwd_key = str(cwd).replace('/', '-')
projects_dir = Path.home() / '.claude' / 'projects'
if (projects_dir / cwd_key).exists():
    print(f'SINGLE {cwd.name} ({cwd_key})')
else:
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
        git_key = git_root.replace('/', '-')
        if (projects_dir / git_key).exists():
            print(f'SINGLE {Path(git_root).name} ({git_key})')
        else:
            print('GLOBAL')
    except Exception:
        print('GLOBAL')
" 2>/dev/null || echo "GLOBAL"
```

**Global settings**:
```bash
cat ~/.claude/settings.json 2>/dev/null || echo "NOT FOUND"
```

**Project settings**:
```bash
cat .claude/settings.json 2>/dev/null || echo "NOT FOUND"
```

**Project MCP config**:
```bash
cat .mcp.json 2>/dev/null || echo "NOT FOUND"
```

**Global commands**:
```bash
ls ~/.claude/commands/ 2>/dev/null || echo "EMPTY"
```

**Global agents**:
```bash
ls ~/.claude/agents/ 2>/dev/null || echo "NONE"
```

**Current repo**:
```bash
basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "(not a git repo)"
```

---

## Your role

You are a Claude Code environment health checker. Read all context collected above and run the checks below. Use only what was collected — do not read additional files.

---

## Claude environment checks

### Check 1 — Global settings validity
Read the global settings JSON above.
- `[CRITICAL]` if `~/.claude/settings.json` is NOT FOUND
- `[CRITICAL]` if the JSON is malformed (not parseable)
- `[WARN]` if neither `permissions` nor `hooks` keys are present (likely an empty or stub config)
- `[PASSED]` otherwise — note the top-level keys present

### Check 2 — Hook script integrity
Extract every `command:` value from both settings files (global + project). For hook commands that reference a script path (e.g., `python3 /path/to/script.py`):
- Resolve the script path (strip `python3`, `bash`, etc. to get the file path)
- `[CRITICAL]` if the referenced script file does not exist at the resolved path
- Skip commands that are pure shell builtins or don't reference a file path
- `[PASSED]` if all referenced scripts exist (or no script-based hooks are configured)

To check if a path exists, use the `Bash` tool: `test -f /path/to/script && echo EXISTS || echo MISSING`

### Check 3 — Project settings validity
Behavior depends on scope (from the Scope output above):

- **Single mode**: Read `.claude/settings.json` in CWD (injected above).
  - `[INFO]` if NOT FOUND — no project settings, global only (may be intentional)
  - `[CRITICAL]` if present but malformed JSON
  - `[WARN]` if present and has hooks but they reference missing scripts (covered by Check 2)
  - `[PASSED]` if valid JSON or not present

- **Parent mode**: For each child path listed in the scope output, check `[child]/.claude/settings.json`.
  Use `Bash` to read each: `cat [child]/.claude/settings.json 2>/dev/null || echo NOT FOUND`
  Show results as a summary table row per project (see Output format below).

- **Global mode**: `[INFO]` — no project detected from CWD, skipping project-specific check 3.

### Check 4 — MCP config validity
Behavior depends on scope (from the Scope output above):

- **Single mode**: Read `.mcp.json` in CWD (injected above).
  - `[INFO]` if NOT FOUND — no MCP servers configured for this project
  - `[CRITICAL]` if present but malformed JSON
  - For each server in `mcpServers`: extract the `command` path (first element if array, or the command string). Check if it exists.
    - `[CRITICAL]` if the MCP command binary/interpreter path does not exist
    - `[WARN]` if the `args` script path does not exist
  - `[PASSED]` if valid and all paths resolve

- **Parent mode**: For each child path, check `[child]/.mcp.json`.
  Use `Bash` to read each: `cat [child]/.mcp.json 2>/dev/null || echo NOT FOUND`
  Show results as a summary table row per project (see Output format below).

- **Global mode**: `[INFO]` — no project detected from CWD, skipping project-specific check 4.

### Check 5 — Toolbox environment
Using the `Bash` tool, run the following checks:
- `[WARN]` if `CLAUDE_TOOLBOX_ROOT` env var is not set: `printenv CLAUDE_TOOLBOX_ROOT`
- `[WARN]` if `$CLAUDE_TOOLBOX_ROOT` does not point to a directory that exists
- `[INFO]` if `~/.claude/docs/` does not exist — no reference docs dir
- `[PASSED]` if `CLAUDE_TOOLBOX_ROOT` is set, the path exists, and docs dir is present

### Check 6 — Global command toolbox
Read the global commands and agents lists above.
- List all files found in `~/.claude/commands/` (should be EMPTY — all commands delivered via plugins)
- `[WARN]` if any files are present — global commands should be migrated to plugin commands
- `[INFO]` if `~/.claude/agents/` does not exist — no global agents defined

### Check 7 — Plugin cache vs active plugins
Using the `Bash` tool, run:
```bash
python3 -c "
import json
from pathlib import Path
cache_dir = Path.home() / '.claude' / 'plugins' / 'cache'
settings_file = Path.home() / '.claude' / 'settings.json'
installed_file = Path.home() / '.claude' / 'plugins' / 'installed_plugins.json'

cache_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file()) // (1024*1024) if cache_dir.exists() else 0
cache_dirs = [d.name for d in cache_dir.iterdir() if d.is_dir()] if cache_dir.exists() else []

settings = json.loads(settings_file.read_text()) if settings_file.exists() else {}
enabled = settings.get('enabledPlugins', {})

installed = {}
if installed_file.exists():
    installed = json.loads(installed_file.read_text()).get('plugins', {})

print(f'CACHE_SIZE_MB={cache_size}')
print(f'CACHE_DIRS={cache_dirs}')
print(f'ENABLED_PLUGINS={list(enabled.keys())}')
print(f'INSTALLED_PLUGINS={list(installed.keys())}')
"
```
- `[WARN]` if cache is non-empty AND both `enabledPlugins` and `installed_plugins` are empty — orphaned cache, safe to delete
- `[INFO]` if cache is non-empty and plugins are active — cache is in use, report size
- `[PASSED]` if cache is empty or plugins are active and cache matches

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

**Project extension**:
```bash
cat .claude/doctor.md 2>/dev/null || echo "(no project extension)"
```

---

## Project-specific checks (if extension loaded)

If `.claude/doctor.md` content was injected above (not "(no project extension)"):
run the checks described in that content. Prefix findings with their declared codes.
Mark auto-fixable checks with ★.

---

## Output format

```
## Doctor — [repo] — [date]

### Claude Environment
[CRITICAL/WARN/INFO/PASSED] Check N — Name
- Finding: [specific detail]
- Fix: [exact action]

### Project Health
[CRITICAL/WARN/INFO/PASSED] PN — Check name
- Finding: [specific detail]
- Fix: [exact action]

### Project-specific checks   ← omit section if no extension loaded
[CRITICAL/WARN/INFO/PASSED] XN — Check name
- Finding: [specific detail]
- Fix: [exact action]
```

List issues first (CRITICAL before WARN), then PASSED/INFO at the bottom within each section.

---

## After the report

If the invocation mode output contains `--dry-run`: end the report here with no fix prompt.
End with: "Run `/tools:doctor` to apply auto-fixes."

Otherwise, ask: "Fix issues automatically? Reply `fix all`, `fix [check]` (e.g. `fix P2 P4`), or `skip`."

Auto-fixable: P4 (.gitignore additions). Project-specific auto-fixable checks are marked ★ in the extension.
Manual: P1 (create CLAUDE.md), P2 (fix JSON), P3 (fix Python).

If fixing: use Edit for targeted changes. Report each as `[fixed] path — what changed`.
