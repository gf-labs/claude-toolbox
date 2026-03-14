---
description: Claude Code environment health check + toolbox integrity
allowed-tools: Bash, Read, Glob, Grep
model: claude-sonnet-4-6
---

## Toolbox-specific context

**Commands**:
!ls commands/*.md 2>/dev/null || echo "none"

**Scripts**:
!ls scripts/*.py 2>/dev/null || echo "none"

**hooks.json**:
!cat hooks/hooks.json 2>/dev/null || echo "NOT FOUND"

**plugin.json**:
!cat .claude-plugin/plugin.json 2>/dev/null || echo "NOT FOUND"

**pyproject.toml**:
!test -f pyproject.toml && echo "EXISTS" || echo "MISSING"

---

@~/.claude/commands/doctor.md

---

## Toolbox-specific checks

Run after the global checks above. Prefix findings T2–T6. Same severity model.

### T2 — Scripts referenced by commands exist
From the Commands output above, grep for script references:
Use Bash: `grep -h 'scripts/[a-z_-]*\.py' commands/*.md | grep -oE 'scripts/[a-z_/-]+\.py' | sort -u`
For each referenced script path, check it exists with `test -f`.
- `[CRITICAL]` if any referenced script is missing
- `[PASSED]` if all referenced scripts exist

### T4 — hooks.json has wired hooks
Read the hooks.json output above.
- `[WARN]` if hooks.json is missing or contains no wired hook events
- `[PASSED]` if at least one hook event has entries

### T5 — plugin.json completeness
Read the plugin.json output above. Check for: `name`, `version`, `description`, `author`, `license`, `keywords`.
- `[WARN]` for each missing field
- `[PASSED]` if all fields present

### T6 — pyproject.toml with lint rules
Read the pyproject.toml output above.
- `[WARN]` if MISSING
- Use Bash to check for `select` key: `grep -c 'select' pyproject.toml 2>/dev/null || echo 0`
- `[WARN]` if present but no `select` key under `[tool.ruff.lint]`
- `[PASSED]` if exists with lint rules configured

---

## Output format

```
## Doctor — claude-toolbox — [date]

### Global checks
[same format as ~/.claude/commands/doctor.md output]

### Toolbox checks
[CRITICAL/WARN/PASSED] TN — Check name
- Finding: [specific detail]
- Fix: [exact action]
```

List issues first (CRITICAL before WARN), then PASSED at the bottom.
