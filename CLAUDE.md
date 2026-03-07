# CLAUDE.md

## What this is

claude-toolbox — versioned personal Claude Code commands, scripts, and agents. Delivered as the
`tools` plugin (gfl-marketplace). Commands are namespaced `/tools:*`.

## How scripts are called

Commands call scripts via `!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/foo.py`. The env var
`CLAUDE_TOOLBOX_ROOT` must be set in `~/.claude/settings.json`. It points to this repo's
absolute path.

## How to add a new command

1. Create `commands/[name].md` with standard frontmatter
2. If it needs a script: add `scripts/collect-[name].py` or `scripts/[name].py`
3. Bump version in `.claude-plugin/plugin.json`
4. Run `/plugin install tools@gfl-marketplace` in a new session

## How to add a new agent

Create `agents/[name].md` with `name`, `description`, `tools`, `model`, and `color` frontmatter.
Plugin delivers it automatically on next install.

## Key files

| File | Role |
|------|------|
| `.claude-plugin/plugin.json` | Plugin manifest — bump version on every release |
| `hooks/hooks.json` | Plugin-registered hooks (SessionStart, PostToolUse) |
| `scripts/collect-*.py` | Data collection scripts called by commands |
| `scripts/validate-env.py` | SessionStart hook — validates CLAUDE_TOOLBOX_ROOT |
| `docs/claude-directory-reference.md` | Claude Code directory discovery reference |

## Working in this repo

`.claude/settings.json` grants `Bash(gh:*)` for GitHub operations.
