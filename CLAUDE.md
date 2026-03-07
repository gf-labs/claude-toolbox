# claude-toolbox

Versioned personal Claude Code global toolbox — commands, agents, scripts, hooks, and docs.

## Purpose

This repo version-controls all global Claude Code tooling that previously lived unversioned in `~/.claude/`. It is separate from `ramp` (a portfolio product). Settings, keybindings, and CLAUDE.md remain in dotfiles.

## Plugin namespace: `tools`

Commands are delivered via the plugin system (gfl-marketplace) and accessible as `/tools:*`:
- `/tools:audit`
- `/tools:cleanup`
- `/tools:doctor`
- `/tools:history`
- `/tools:snapshot`
- `/tools:status`

## Env var requirement

Commands call scripts via `!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/foo.py`. This env var must be set in `~/.claude/settings.json`:

```json
"CLAUDE_TOOLBOX_ROOT": "/Users/you/Repos/claude-toolbox"
```

This is added in Phase 3 of the architecture plan.

## Architecture plan

`docs/claude-toolbox-architecture.md` — full 10-phase migration plan with structure decisions, scripts extraction table, and backlog additions.

## Working in this repo

The `.claude/settings.json` grants `cp` permission (needed for Phase 4 file copying) and `gh` permission (for GitHub operations).
