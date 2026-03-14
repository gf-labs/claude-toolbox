# claude-toolbox — Backlog

## In Progress
(nothing)

## Up Next

(nothing)

## Backlog

### Evaluate everything-claude-code for toolbox ideas
- **Size:** S
- Review https://github.com/affaan-m/everything-claude-code and identify patterns, commands, or utilities worth incorporating into this toolbox
- Look for: prompt patterns, hook ideas, workflow automations, command designs not yet covered here

### Auto-collected context blocks (`!cmd`) don't expand `settings.json` env vars
- **Size:** S
- Commands using `${CLAUDE_TOOLBOX_ROOT}` in `!` blocks receive raw templates instead of executed output — the `!` executor doesn't expand env vars defined in `settings.json["env"]`
- Affects: `cleanup` (and any future command using `${CLAUDE_TOOLBOX_ROOT}` in `!` context blocks); `status` retired, reducing scope
- `audit` works because it uses only plain shell commands with no env var references
- Fix options: (a) use `$HOME/Repos/gfl/claude-toolbox` literals instead of the var, (b) wrap in a shell that sources the env, or (c) rely on `CLAUDE_TOOLBOX_ROOT` being set in the shell environment rather than settings.json
- Workaround: LLM runs Bash tool calls manually — output is still correct but not hands-free


### Standalone gfl-marketplace repo with URL sources
- **Size:** S
- Repo already exists at `~/Repos/_archive/gfl-marketplace`
- Remaining work: switch to URL sources pointing at standalone repos (no symlinks required):
  ```json
  { "name": "ramp",  "source": { "source": "url", "url": "https://github.com/gf-labs/ramp.git" } },
  { "name": "tools", "source": { "source": "url", "url": "https://github.com/gf-labs/claude-toolbox.git" } }
  ```
- Update `settings.json` `extraKnownMarketplaces.gfl-marketplace.source.path` to point at the archive repo
- Remove `ramp/toolbox` symlink + revert marketplace.json in ramp
- Enables clean distribution: each plugin repo is independent

### Re-evaluate `brief` model after status merge
- **Size:** XS
- `brief` was Haiku when it was a lightweight orient command; it now absorbs all of `status` (recent commits, activity history, toolbox health) — may warrant Sonnet for correctness on the richer output
- Decision point: run brief a few times and check if Haiku handles the expanded format well; upgrade to Sonnet if output quality suffers

### mcp/server.py — toolbox MCP server
- **Size:** M
- Currently a stub. Potential: expose session search + cleanup ops as MCP tools
