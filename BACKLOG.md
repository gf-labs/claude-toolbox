# claude-toolbox — Backlog

## In Progress
(nothing)

## Up Next

(nothing)

## Backlog

### Evaluate community Claude Code resources for toolbox ideas
- **Size:** S
- Review the following and identify patterns, commands, or utilities worth incorporating:
  - https://github.com/affaan-m/everything-claude-code
  - https://github.com/shanraisshan/claude-code-best-practice
- Look for: prompt patterns, hook ideas, workflow automations, command designs not yet covered here

### Commit `CLAUDE_TOOLBOX_ROOT` export to dotfiles
- **Size:** XS
- `shellenv/exports` was updated with `export CLAUDE_TOOLBOX_ROOT="$HOME/Repos/gfl/claude-toolbox"` to fix `!cmd` context injection in brief/pin/wrap — needs to be committed in the dotfiles repo



### Upgrade `brief` model to Sonnet if parent-mode quality degrades
- **Size:** XS
- Evaluated 2026-03-14: keeping Haiku — task is template rendering (no reasoning), well-specified format; Haiku handles it well
- Watch for: parent mode with full multi-repo table after `!cmd` fix takes effect (dotfiles commit pending); if output is malformed or missing sections, upgrade `model:` in commands/brief.md to `claude-sonnet-4-6`

### mcp/server.py — toolbox MCP server
- **Size:** M
- Currently a stub. Potential: expose session search + cleanup ops as MCP tools
- **On ice** — needs a concrete use case before building; low priority until one emerges
