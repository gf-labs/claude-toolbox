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



### Re-evaluate `brief` model after status merge
- **Size:** XS
- `brief` was Haiku when it was a lightweight orient command; it now absorbs all of `status` (recent commits, activity history, toolbox health) — may warrant Sonnet for correctness on the richer output
- Decision point: run brief a few times and check if Haiku handles the expanded format well; upgrade to Sonnet if output quality suffers

### mcp/server.py — toolbox MCP server
- **Size:** M
- Currently a stub. Potential: expose session search + cleanup ops as MCP tools
- **On ice** — needs a concrete use case before building; low priority until one emerges
