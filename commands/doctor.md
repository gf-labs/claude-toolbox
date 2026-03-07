---
description: Claude Code environment health check — settings, hooks, MCP, toolbox
allowed-tools: Bash, Read, Glob, Grep
---

## Auto-collected context

**Global settings**:
!cat ~/.claude/settings.json 2>/dev/null || echo "NOT FOUND"

**Project settings**:
!cat .claude/settings.json 2>/dev/null || echo "NOT FOUND"

**Project MCP config**:
!cat .mcp.json 2>/dev/null || echo "NOT FOUND"

**Global commands**:
!ls ~/.claude/commands/ 2>/dev/null || echo "EMPTY"

**Global agents**:
!ls ~/.claude/agents/ 2>/dev/null || echo "NONE"

**Current repo**:
!basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "(not a git repo)"

---

## Your role

You are a Claude Code environment health checker. Read all auto-collected context above and run the checks below. Use only what was injected — do not read additional files.

---

## Checks

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
Read the project settings JSON above (`.claude/settings.json`).
- `[INFO]` if NOT FOUND — no project settings, global only (may be intentional)
- `[CRITICAL]` if present but malformed JSON
- `[WARN]` if present and has hooks but they reference missing scripts (covered by Check 2)
- `[PASSED]` if valid JSON or not present

### Check 4 — MCP config validity
Read the project MCP config above (`.mcp.json`).
- `[INFO]` if NOT FOUND — no MCP servers configured for this project
- `[CRITICAL]` if present but malformed JSON
- For each server in `mcpServers`: extract the `command` path (first element if array, or the command string). Check if it exists.
  - `[CRITICAL]` if the MCP command binary/interpreter path does not exist
  - `[WARN]` if the `args` script path does not exist
- `[PASSED]` if valid and all paths resolve

### Check 5 — Toolbox environment
Using the `Bash` tool, run the following checks:
- `[WARN]` if `CLAUDE_TOOLBOX_ROOT` env var is not set: `printenv CLAUDE_TOOLBOX_ROOT`
- `[WARN]` if `$CLAUDE_TOOLBOX_ROOT` does not point to a directory that exists
- `[INFO]` if `~/.claude/docs/` does not exist — no reference docs dir
- `[PASSED]` if `CLAUDE_TOOLBOX_ROOT` is set, the path exists, and docs dir is present

### Check 6 — Global command toolbox
Read the global commands and agents lists above.
- List all files found in `~/.claude/commands/` (this file itself counts)
- `[INFO]` if `~/.claude/agents/` does not exist — no global agents defined
- No pass/fail — informational inventory only

---

## Output format

```
## Doctor — [date] — [repo name or "~"]

### [N] issue(s) found

**[SEVERITY] Check N — Name**
- Finding: [specific, what's wrong]
- Fix: [exact action]

[PASSED] Check N — Name — [one-line summary]
[INFO] Check N — Name — [one-line note]
```

List all issues first (CRITICAL before WARN), then PASSED/INFO at the bottom.

---

## After the report

End with this footer (always, regardless of findings):

---
*To add project-specific checks: create `.claude/commands/doctor.md` in your repo.
Open it with:*

```
Run `/tools:doctor` first for environment health. Project-specific checks below:
```

*Then add your checks as additional numbered sections.*
