# claude-toolbox

Personal Claude Code global toolbox — versioned commands, agents, scripts, hooks, and docs.

## Goals

- Version-control and distribute global Claude Code commands, scripts, agents, hooks, and docs
- Extract large inline bash blocks from commands into standalone, reusable Python scripts
- Distribute via the plugin system (gfl-marketplace) — commands namespaced as `/tools:*`

## Commands

| Command | Description |
|---------|-------------|
| `/tools:audit`  | Repo audit — universal checks for any codebase |
| `/tools:brief`  | Start-of-session orientation — branch, backlog, snapshot health, plans |
| `/tools:cleanup`| Clean up old Claude session artifacts — extract context, then delete |
| `/tools:done`   | Mark current session for deletion |
| `/tools:env`    | Claude Code environment health check — settings, hooks, MCP, toolbox |
| `/tools:pin`    | Break checkpoint — status display, session log, optional MEMORY.md update |
| `/tools:status` | Project status — git state, BACKLOG, snapshot and session-log health, recent activity |
| `/tools:wrap`   | End-of-session housekeeping — git check, plan cleanup, backlog review, done marker |

## Session lifecycle

```
[start of session]
  /tools:brief        — orient: branch, in-progress, last snapshot, plans

[during session]
  work...
  /tools:pin          — break checkpoint: status + session log + optional MEMORY.md update

[end of session]
  /ramp:wrap          — knowledge graph harvest (if ramp installed)
  /tools:wrap         — full close-out ritual:
    Step 0: ramp check
    Step 1: session log   → skip if /tools:pin already run
    Step 2: git check     → surface uncommitted changes + unpushed commits
    Step 3: plan cleanup  → list plans, offer to mark done
    Step 4: backlog       → mark completed items done
    Step 5: memory health → warn if MEMORY.md approaching 200-line limit
    Step 6: done?         → optionally mark session for deletion

[on demand]
  /tools:status       — read-only project health at any point in the session
  /tools:done         — mark session for deletion without running wrap

[periodic]
  /tools:cleanup      — delete old sessions, extract context to session-log.md + MEMORY.md
```

### Storage

| Store | Location | Loaded automatically? | Written by |
|-------|----------|-----------------------|------------|
| `MEMORY.md` | `~/.claude/projects/[key]/memory/MEMORY.md` | Yes (auto-memory, 200-line limit) | `/tools:snapshot` |
| `session-log.md` | `~/.claude/projects/[key]/memory/session-log.md` | No | `/tools:summarize`, `/tools:wrap`, `/tools:cleanup` |
| `CLAUDE.md` | `[repo]/CLAUDE.md` or `~/.claude/CLAUDE.md` | Yes (every session) | Manual |
| Plans | `~/.claude/plans/[name].md` | No | Manual / agents |
| Session files | `~/.claude/projects/[key]/[id].jsonl` | No | Claude Code |

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
