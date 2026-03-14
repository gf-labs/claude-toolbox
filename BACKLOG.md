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

### Auto-collected context blocks (`!cmd`) don't expand `settings.json` env vars
- **Size:** S
- Commands using `${CLAUDE_TOOLBOX_ROOT}` in `!` blocks receive raw templates instead of executed output — the `!` executor doesn't expand env vars defined in `settings.json["env"]`
- Affects: `cleanup` (and any future command using `${CLAUDE_TOOLBOX_ROOT}` in `!` context blocks); `status` and `audit` retired, reducing scope
- `doctor` project health checks use plain shell commands and are unaffected
- Fix options: (a) use `$HOME/Repos/gfl/claude-toolbox` literals instead of the var, (b) wrap in a shell that sources the env, or (c) rely on `CLAUDE_TOOLBOX_ROOT` being set in the shell environment rather than settings.json
- Workaround: LLM runs Bash tool calls manually — output is still correct but not hands-free



### Re-evaluate `brief` model after status merge
- **Size:** XS
- `brief` was Haiku when it was a lightweight orient command; it now absorbs all of `status` (recent commits, activity history, toolbox health) — may warrant Sonnet for correctness on the richer output
- Decision point: run brief a few times and check if Haiku handles the expanded format well; upgrade to Sonnet if output quality suffers

### mcp/server.py — toolbox MCP server
- **Size:** M
- Currently a stub. Potential: expose session search + cleanup ops as MCP tools
- **On ice** — needs a concrete use case before building; low priority until one emerges
