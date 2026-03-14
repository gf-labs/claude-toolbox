---
description: Toolbox self-audit — checks scripts, commands, hooks, and plugin manifest
allowed-tools: Bash, Read, Glob
---

## Auto-collected context

**Repo root**:
!git rev-parse --show-toplevel 2>/dev/null || echo "(not a git repo)"

**Commands**:
!ls commands/*.md 2>/dev/null || echo "none"

**Scripts**:
!ls scripts/*.py 2>/dev/null || echo "none"

**hooks.json**:
!cat hooks/hooks.json 2>/dev/null || echo "NOT FOUND"

**plugin.json**:
!cat .claude-plugin/plugin.json 2>/dev/null || echo "NOT FOUND"

**BACKLOG.md** (first 10 lines):
!head -10 BACKLOG.md 2>/dev/null || echo "not found"

---

## Your role

Toolbox-specific auditor. Use only the auto-collected context above plus targeted Bash/Read/Glob calls for individual checks. Do not read files beyond what's needed per check.

---

## Checks

### T1 — Script shebangs
For each `.py` file in `scripts/`, verify the first line is `#!/usr/bin/env python3`.
Use Read tool to check the first line of each script.
- `[WARN]` for any script missing the shebang
- `[PASSED]` if all scripts have correct shebangs

### T2 — Scripts referenced by commands exist
For each `commands/*.md`, grep for `python3 .*scripts/` patterns to find script references.
Use Bash: `grep -h 'scripts/[a-z_-]*\.py' commands/*.md | grep -oE 'scripts/[a-z_/-]+\.py' | sort -u`
For each referenced script path, check it exists.
- `[CRITICAL]` if any referenced script is missing
- `[PASSED]` if all referenced scripts exist

### T3 — BACKLOG.md not a placeholder
Read the BACKLOG.md output above.
- `[WARN]` if the file is not found
- `[WARN]` if `## In Progress` and `## Up Next` both contain only `(nothing)` or are empty — stale placeholder
- `[PASSED]` otherwise

### T4 — hooks.json non-empty
Read the hooks.json output above.
- `[WARN]` if hooks.json is `{"hooks": {}}` or otherwise has no wired hooks
- `[PASSED]` if at least one hook event has entries

### T5 — plugin.json completeness
Read the plugin.json output above. Check for presence of all required fields:
`name`, `version`, `description`, `author`, `license`, `keywords`, `category`
- `[WARN]` for each missing field
- `[PASSED]` if all fields present
- `[INFO]` if `category` is absent (optional but recommended)

---

## Output format

```
## Toolbox Audit — [repo] — [date]

### [N] issue(s) found

**[SEVERITY] TN — Check name**
- Finding: [specific detail]
- Fix: [exact action]

[PASSED] TN — Check name — ok
```

List issues first (CRITICAL before WARN), then PASSED/INFO at the bottom.

After the report, say: "Run `/tools:audit` for universal repo checks (JSON validity, Python syntax, .gitignore)."
