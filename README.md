# claude-toolbox

Personal Claude Code global toolbox — versioned commands, agents, scripts, hooks, and MCP server.

Built by [Bernie Green](https://github.com/berniegreen) / Greenfield Labs

---

## Why this exists

Claude Code's session model creates a context hygiene problem: context accumulates, decisions
get lost between sessions, and there's no structured way to carry understanding forward.
claude-toolbox is the system I built to solve this — a plugin managing the full session
lifecycle from orientation to archival.

## Goals

- Version-control and distribute global Claude Code commands, scripts, agents, hooks, and docs
- Extract large inline bash blocks from commands into standalone, reusable Python scripts
- Distribute via the plugin system (gfl-marketplace) — commands namespaced as `/tools:*`

---

## Session lifecycle

```
[start of session]
  /tools:brief        — orient: branch, in-progress, last snapshot, plans, recent activity

[during session]
  work...
  /tools:pin          — break checkpoint: status + session log + optional MEMORY.md update
  /tools:backlog      — add a new item to BACKLOG.md mid-session

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

[periodic]
  /tools:cleanup           — delete old sessions, extract context to session-log.md + MEMORY.md
  /tools:search-sessions   — search session history by keyword
```

### Storage

| Store | Location | Loaded automatically? | Written by |
|-------|----------|-----------------------|------------|
| `MEMORY.md` | `~/.claude/projects/[key]/memory/MEMORY.md` | Yes (auto-memory, 200-line limit) | `/tools:pin` |
| `session-log.md` | `~/.claude/projects/[key]/memory/session-log.md` | No | `/tools:pin`, `/tools:wrap`, `/tools:cleanup` |
| `CLAUDE.md` | `[repo]/CLAUDE.md` or `~/.claude/CLAUDE.md` | Yes (every session) | Manual |
| Plans | `~/.claude/plans/[name].md` | No | Manual / agents |
| Session files | `~/.claude/projects/[key]/[id].jsonl` | No | Claude Code |

---

## Commands

### Orientation

Four commands answer different re-entry questions. Pick by how long you've been away and what you need:

| Command | When | Question answered |
|---------|------|-------------------|
| `/tools:brief`   | Cold start / long absence (days or weeks) | "Get me back up to speed" |
| `/tools:status`  | Mid-stream, still warm | "Where am I right now?" |
| `/tools:recap`   | After stepping away briefly (hours or a day) | "What did I do recently?" |
| `/tools:overview`| Planning / deciding what to work on next | "What should I work on next?" |

See [docs/design-log.md — Orientation Command Taxonomy](#) for the full differentiation table.

| Command | Description |
|---------|-------------|
| `/tools:brief`   | Cold-start orientation — absence-scaled depth (session log, backlog, plans, architecture, recent activity); `/tools:brief [session-id]` to summarize a past session |
| `/tools:status`  | Warm mid-session check — git diff detail with hunk headers, last session log entry, In Progress backlog |
| `/tools:recap`   | Time-windowed "where was I?" — git commits, files touched, session notes in window; `--days N` or `--hours N` |
| `/tools:overview`| PM-style project overview — recent work, in-flight, backlog priorities, active plans, 3-tier sequencing |

### Session lifecycle

| Command | Description |
|---------|-------------|
| `/tools:pin`            | Break checkpoint — status display, session log, optional MEMORY.md update |
| `/tools:wrap`           | End-of-session housekeeping — git check, plan cleanup, backlog review, done marker |
| `/tools:aside`          | Answer a mid-task side question in a fixed format, then resume |
| `/tools:backlog`        | Add an item to BACKLOG.md from within Claude |
| `/tools:doctor`         | Claude Code environment + project health check (scope-aware) |
| `/tools:cleanup`        | Clean up old Claude session artifacts — preview, extract context, then delete |
| `/tools:search-sessions`| Full-text search across session history by keyword and age |

### AI ingestion pipeline

| Command | Description |
|---------|-------------|
| `/tools:ingest`         | Ingest documents, PDFs, notes into the pipeline (Phase A, ≤20 files / ≤50k chars) |
| `/tools:codex`          | Run preserve → codex → integrate sequence for code artifact extraction |
| `/tools:pipeline`       | Full pipeline status snapshot — sources, index, synthesis, Tier 2 coverage, next steps |
| `/tools:thread-pipeline`| *(deprecated — use `/tools:pipeline`)* Thread extraction pipeline status |

---

## AI ingestion pipeline

The pipeline transforms AI chat exports (Claude, ChatGPT, Gemini) into durable project
documentation across multiple repos. It runs as a series of phases orchestrated by
`scripts/run-pipeline.py`.

```
conversations.json  (claude / chatgpt / gemini)
        ↓
[Phase 1]  extract-threads.py
           scan  → INDEX.md  (thread inventory)
           index → per-project .md thread files
        ↓
[Phase 2F] run-pipeline.py synthesize
           Haiku per-thread analysis; clusters, flags unclear threads
        ↓
[Phase 2G] run-pipeline.py synthesize --integrate
           Sonnet cross-thread synthesis; convergence loop into project docs
        ↓
[Phase 3]  run-pipeline.py preserve / codex
           Code artifact extraction → code-reference.md rollup → codex staging files
        ↓
[Phase 4]  run-pipeline.py integrate
           Merge staged docs into destination repos (example-project, gfl, home, etc.)
        ↓
Output: durable docs in each project repo
```

The central fact store is an immutable append-only `events.jsonl` in
`$AI_INGESTION_ROOT/timeline/`, with a derived staleness layer
(`staleness.json`: current / superseded / review-needed) computed separately.

For large batch runs, bypass the commands and call the orchestrator directly:

```bash
python3 scripts/run-pipeline.py index --project example-project --auto
python3 scripts/run-pipeline.py synthesize --project example-project
python3 scripts/run-pipeline.py integrate --project example-project
```

Full operational guide: `docs/pipeline-runbook.md`

---

## Agents

Agents are subprocesses invoked by Claude during a task. They run in isolation and return
a single structured result. Use them for read-heavy subtasks that would otherwise consume
main context.

| Agent | Model | Isolation | Description |
|-------|-------|-----------|-------------|
| `plan` | Sonnet | worktree | Implementation planner — reads codebase, returns a phase-by-phase plan. No writes. |
| `review` | Haiku | worktree | Structured code review — diff analysis, readability, correctness, security. Read-only. |
| `explore` | Haiku | — | Fast codebase explorer — finds files, searches code, answers structure questions. |
| `summarize` | Haiku | — | Session summarizer — given a JSONL path, returns a concise summary of what happened. |

Worktree isolation means the agent operates on a temporary copy of the repo; it cannot
affect the working tree even if it writes files.

---

## Hooks

Hooks are shell commands that fire automatically on Claude Code lifecycle events. The plugin
registers hooks via `hooks/hooks.json`; they apply to every session that loads the plugin.

| Event | Matcher | Script | What it does |
|-------|---------|--------|--------------|
| `SessionStart` | — | `validate-env.py` | Checks `CLAUDE_TOOLBOX_ROOT` is set and valid |
| `SessionStart` | — | `setup-mcp.py` | Auto-registers MCP server at user scope (idempotent) |
| `PostToolUse` | `Write` | `collect-plan-map.py` | Refreshes plan-to-project map after file creates |
| `PostToolUse` | `Edit\|Write` | `lint-py.py` | Syntax-checks any Python file that was just edited |
| `PreCompact` | — | `check-pin-ran.py` | Blocks context compaction unless `/tools:pin` was run this session |

---

## MCP server

claude-toolbox exposes a local MCP server with three tools for querying session data from
any Claude context — not just the current project.

| Tool | Description |
|------|-------------|
| `search_sessions` | Full-text search across session history by keyword and age |
| `list_plans` | List all active plans with project attribution |
| `get_session_log` | Read session log entries for a project |

Setup (one-time):

```bash
python3 -m venv <path-to-claude-toolbox>/mcp_server/.venv
<path-to-claude-toolbox>/mcp_server/.venv/bin/pip install mcp
```

Add to `.mcp.json` to enable:

```json
{
  "mcpServers": {
    "claude-toolbox": {
      "command": "<path-to-claude-toolbox>/mcp_server/.venv/bin/python3",
      "args": ["<path-to-claude-toolbox>/mcp_server/server.py"]
    }
  }
}
```

---

## Structure

```
claude-toolbox/
├── commands/    # slash commands delivered as /tools:*
├── agents/      # subagents (plan, review, explore, summarize)
├── scripts/     # Python scripts called by commands and hooks
├── hooks/       # hooks.json — plugin-registered lifecycle hooks
├── mcp_server/  # MCP server (search_sessions, list_plans, get_session_log)
└── docs/        # architecture, pipeline runbook, design logs
```

---

## Install

1. Add `CLAUDE_TOOLBOX_ROOT` to your `~/.claude/settings.json`:
   ```json
   { "env": { "CLAUDE_TOOLBOX_ROOT": "/path/to/claude-toolbox" } }
   ```
2. Add this repo as a plugin source using `--plugin-dir`:
   ```json
   { "pluginDirs": ["/path/to/claude-toolbox/.claude-plugin"] }
   ```
3. Restart the session — commands are available as `/tools:*`.

## Extending

**New command**: create `commands/[name].md` with frontmatter (`description`, `allowed-tools`, optional `model`). Bump version in `.claude-plugin/plugin.json`, then restart.

**New script**: add `scripts/[name].py` (stdlib only — no third-party deps). Reference it from a command via `python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/[name].py`.

**New agent**: create `agents/[name].md` with frontmatter (`name`, `description`, `tools`, `model`, `color`). Bump version and restart.

**New hook**: add an entry to `hooks/hooks.json` under the appropriate event key (`SessionStart`, `PostToolUse`, `PreCompact`, `Stop`, etc.). Bump version and restart.
