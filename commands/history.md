---
description: Cross-project Claude history — what did I work on recently?
argument-hint: [--days N] [--project repo-name]
allowed-tools: Bash
model: claude-haiku-4-5-20251001
---

## Arguments

`$ARGUMENTS`

Parse: `--days N` sets time range (default: 7). `--project name` filters to one project by matching the repo name at the end of the project path.

## Auto-collected context

**History** (prompts from the last N days, grouped):
!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-history.py $ARGUMENTS

---

## Your role

Read the auto-collected history above and render it as a clean, scannable report. Do not add analysis or commentary — just format and present what was injected. If the Python output already includes the formatted result, display it as-is.

The output should look like:

```
## History — last [N] days[  — [project filter]]

[N] prompts across [N] project(s)

### [repo-name] — [YYYY-MM-DD]
- [prompt, truncated]
- ...

### [repo-name] — [YYYY-MM-DD]
- ...
```

If no history was found: say so clearly and suggest running with fewer `--days`.
