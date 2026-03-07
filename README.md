# claude-toolbox

Personal Claude Code global toolbox — versioned commands, agents, scripts, hooks, and docs.

## Goals

- Version-control and distribute global Claude Code commands, scripts, agents, hooks, and docs
- Extract large inline bash blocks from commands into standalone, reusable Python scripts
- Distribute via the plugin system (gfl-marketplace) — commands namespaced as `/tools:*`

## Commands

| Command | Description |
|---------|-------------|
| `/tools:audit` | Repo audit — universal checks for any codebase |
| `/tools:cleanup` | Clean up old Claude session artifacts |
| `/tools:doctor` | Claude Code environment health check |
| `/tools:history` | Cross-project Claude history |
| `/tools:snapshot` | Capture current session context into project MEMORY.md |
| `/tools:status` | Project status — git state, recent commits, BACKLOG, knowledge tree health |

## Structure

```
claude-toolbox/
├── commands/    # slash commands delivered as /tools:*
├── agents/      # subagents (e.g., explore)
├── scripts/     # Python scripts called by commands
├── hooks/       # hooks.json for plugin-registered hooks
├── mcp/         # stub for future MCP server
└── docs/        # architecture plan and references
```

## Private

This is a personal toolbox repo — not intended for general use.
