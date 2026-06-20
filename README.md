<p align="center">
  <!-- LOGO: drop a hosted banner/glyph here later, e.g. <img src="docs/assets/toolbox.png" width="120"> -->
</p>

<h1 align="center">claude-toolbox</h1>

<p align="center"><em>Session lifecycle management for Claude Code — orient, checkpoint, close out, and never lose the thread between sessions.</em></p>

<p align="center">
  <a href="https://github.com/gf-labs/claude-toolbox"><img src="https://img.shields.io/badge/version-0.5.1-3b82f6?style=flat-square" alt="version"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-22c55e?style=flat-square" alt="license"></a>
  <img src="https://img.shields.io/badge/Claude_Code-plugin-d97757?style=flat-square&logo=anthropic&logoColor=white" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/MCP-server-6366f1?style=flat-square" alt="MCP server">
</p>

<p align="center">Built by <a href="https://github.com/berniegreen">Bernie Green</a> · <a href="https://github.com/gf-labs">Greenfield Labs</a></p>

> **Repo, plugin, and namespace.** The repository is `claude-toolbox`. It ships as the **`tools`** plugin through the [GFL marketplace](https://github.com/gf-labs/gfl-marketplace), and its commands are namespaced **`/tools:*`**. One artifact, three names — that's normal for a Claude Code plugin, and worth knowing before you read on.

---

## Why this exists

Claude Code's greatest strength is also its sharpest edge: the **session**. Everything happens inside a single rolling context window — messages, file reads, tool output — and when that window fills, the reasoning that got you there is compacted away. Decisions evaporate between sessions. After a few days off, you reopen a repo with no idea where you left it.

`claude-toolbox` is the system I built to keep the thread. It manages the full session lifecycle — **orient** at the start, **checkpoint** in the middle, **close out** cleanly at the end, and **archive** what matters — so understanding compounds across sessions instead of resetting with each one.

The conceptual backbone lives in [`docs/context-hygiene.md`](docs/context-hygiene.md): how the context window works, what persists where, and what each command automates.

## What you get

- **Never lose the thread.** Orientation commands rebuild your mental model in seconds — scaled to how long you've been away, from a 30-second pulse to a full cold-start brief.
- **Checkpoint without ceremony.** `/tools:pin` captures status, writes a session-log entry, and updates durable memory in one step — run it before you `/compact`.
- **Close out cleanly.** `/tools:wrap` runs the end-of-session ritual: session log, git check, plan cleanup, backlog review, memory health.
- **Keep context lean.** A `PreCompact` hook refuses to compact until you've checkpointed; `/tools:cleanup` extracts context from old sessions *before* deleting them.
- **Query your own history.** Full-text search across every session — from any project — via a command or a local MCP server.

---

## Session lifecycle

The commands map onto the natural arc of a working session. You rarely need all of them at once; reach for the one that matches where you are.

```
[ start of session ]
  /tools:brief        orient — branch, in-progress, last snapshot, plans, recent activity
  /tools:overview     plan  — current state + backlog priorities + a sequencing recommendation

[ during the session ]
  work…
  /tools:status       quick pulse — git detail, last session note, in-progress backlog
  /tools:pin          break checkpoint — status + session log + optional MEMORY.md  (run before /compact)
  /tools:aside        answer a side question in a fixed format, then resume
  /tools:backlog      capture a task to TaskWarrior without breaking flow

[ end of session ]
  /ramp:wrap          harvest the knowledge graph   (if the ramp plugin is installed)
  /tools:wrap         close-out ritual:
                        session log → git check → plan cleanup → backlog review
                        → memory health → optional "mark session done"

[ periodic housekeeping ]
  /tools:cleanup          extract context from old sessions, then delete them
  /tools:search-sessions  full-text search across session history
  /tools:sit-rep          narrative situation report — velocity, pivots, learnings, risks
  /tools:doctor           environment + project health check
```

---

## Commands

Twelve commands plus one skill, grouped by when you reach for them. Cheap, high-frequency commands run on Haiku; reasoning-heavy ones run on Sonnet.

### Orientation — *"where am I?"*

Four commands answer different re-entry questions. Pick by how long you've been away and what you need.

| Command | When | Question it answers |
|---------|------|---------------------|
| `/tools:brief`    | Cold start / long absence (days or weeks) | "Get me back up to speed" |
| `/tools:status`   | Mid-stream, still warm | "Where am I right now?" |
| `/tools:recap`    | After stepping away briefly (hours or a day) | "What did I do recently?" |
| `/tools:overview` | Planning / deciding what's next | "What should I work on next?" |

> See [`docs/design-log.md`](docs/design-log.md) § *Orientation Command Taxonomy* for the full differentiation table — the reasoning behind splitting one "status" command into four.

### In-session — capture & checkpoint

| Command | Description |
|---------|-------------|
| `/tools:pin`               | Break checkpoint — status display, session-log entry, optional MEMORY.md update |
| `/tools:aside`             | Answer a mid-task side question in a fixed format, then return to the task |
| `/tools:backlog`           | Add a task to TaskWarrior for this project (`[item] [+tag] [size:S]`) |
| `/tools:consolidate-tasks` | Sweep work items — markdown trackers, code `TODO`/`FIXME`, GitHub issues — into TaskWarrior, with dedup and tombstoning |
| `/tools:sit-rep`           | Narrative situation report across weeks of work — velocity, milestones, pivots, learnings, risks *(ships as a skill)* |

### Close-out & maintenance

| Command | Description |
|---------|-------------|
| `/tools:wrap`            | End-of-session housekeeping — session log, git check, plan cleanup, backlog review, done marker |
| `/tools:cleanup`         | Clean up old session artifacts — preview, extract context, then delete |
| `/tools:doctor`          | Claude Code environment + project health check (scope-aware) |
| `/tools:search-sessions` | Full-text search across session history by keyword and age |

---

## Where state lives

`claude-toolbox` reads from and writes to the stores Claude Code already uses. Nothing is hidden in a database — every store is a plain file you can open, edit, and version.

| Store | Location | Auto-loaded? | Written by |
|-------|----------|--------------|------------|
| `MEMORY.md`      | `~/.claude/projects/[key]/memory/MEMORY.md`      | Yes — auto-memory, 200-line budget | `/tools:pin` |
| `session-log.md` | `~/.claude/projects/[key]/memory/session-log.md` | No | `/tools:pin`, `/tools:wrap`, `/tools:cleanup` |
| `CLAUDE.md`      | `[repo]/CLAUDE.md` or `~/.claude/CLAUDE.md`      | Yes — every session | Manual |
| Plans            | `~/.claude/plans/[name].md`                      | No — read on demand | Manual / agents |
| Session files    | `~/.claude/projects/[key]/[id].jsonl`            | No — archive only | Claude Code |

---

## Agents

Agents are subprocesses Claude can spawn during a task. They run in a separate context and return a single result — ideal for read-heavy subtasks that would otherwise flood your main window.

| Agent | Model | Description |
|-------|-------|-------------|
| `explore`   | Haiku  | Fast codebase explorer — finds files, searches code, answers structure questions |
| `plan`      | Sonnet | Implementation planner — reads the codebase, returns a phase-by-phase plan |
| `review`    | Haiku  | Structured code review — diff analysis, readability, correctness, security |
| `summarize` | Haiku  | Session summarizer — given a JSONL path, returns a concise account of what happened |

> All four are **read-only** — none has `Write` or `Edit`, so they can't touch your working tree. Most use `Glob, Grep, Read, Bash`; `summarize` is narrower (`Read, Bash`). They explore and report, nothing more.

---

## Hooks

Hooks are commands Claude Code fires automatically on lifecycle events. The plugin registers them via [`hooks/hooks.json`](hooks/hooks.json); they apply to every session that loads the plugin.

| Event | Matcher | Script | What it does |
|-------|---------|--------|--------------|
| `SessionStart` | — | `validate-env.py`     | Checks `CLAUDE_TOOLBOX_ROOT` is set and valid |
| `SessionStart` | — | `setup-mcp.py`        | Auto-registers the MCP server at user scope (idempotent) |
| `PostToolUse`  | `Write`        | `collect-plan-map.py` | Refreshes the plan-to-project map after file creates |
| `PostToolUse`  | `Edit \| Write` | `lint-py.py`          | Syntax-checks any Python file that was just edited |
| `PreCompact`   | — | `check-pin-ran.py`    | **Blocks** compaction unless `/tools:pin` ran this session (so context is never summarized away uncheckpointed) |

---

## MCP server

`claude-toolbox` exposes a local [MCP](https://modelcontextprotocol.io) server so any Claude context — not just the current project — can query your session data.

| Tool | Description |
|------|-------------|
| `search_sessions` | Full-text search across session history by keyword and age |
| `list_plans`      | List all active plans with project attribution |
| `get_session_log` | Read session-log entries for a project |

The `setup-mcp.py` SessionStart hook registers it for you. To register manually, first create the server's virtualenv — it depends on the `mcp` package, and the system `python3` won't resolve it:

```bash
python3 -m venv mcp_server/.venv
mcp_server/.venv/bin/pip install mcp
```

Then point a config entry at the venv's python (or use `mcp_server/start.sh`, which resolves it for you):

```json
{
  "mcpServers": {
    "claude-toolbox": {
      "command": "/path/to/claude-toolbox/mcp_server/.venv/bin/python3",
      "args": ["/path/to/claude-toolbox/mcp_server/server.py"]
    }
  }
}
```

---

## Getting started

### Requirements

- **Claude Code** (latest)
- **Python 3.11+** — commands and hooks are stdlib-only; no third-party dependencies
- **[TaskWarrior](https://taskwarrior.org)** *(optional)* — only `/tools:backlog` and `/tools:consolidate-tasks` use it

### Install

The commands call helper scripts through the `CLAUDE_TOOLBOX_ROOT` environment variable, so
whichever install path you pick, you also set that one env var to the repo's location.

**Option A — GFL marketplace (recommended):**

```
/plugin marketplace add gf-labs/gfl-marketplace
/plugin install tools@gfl-marketplace
```

Then clone the repo somewhere and point `CLAUDE_TOOLBOX_ROOT` at it in `~/.claude/settings.json`
so the command scripts resolve:

```json
{ "env": { "CLAUDE_TOOLBOX_ROOT": "/abs/path/to/claude-toolbox" } }
```

**Option B — local dev (run straight from a clone):**

```bash
git clone https://github.com/gf-labs/claude-toolbox ~/path/to/claude-toolbox
```

Set the same env var in `~/.claude/settings.json`, then launch Claude Code with `--plugin-dir`
pointed at the **repo root** (the directory that contains `.claude-plugin/`, not `.claude-plugin/` itself):

```bash
claude --plugin-dir /abs/path/to/claude-toolbox
```

Restart the session. A SessionStart hook validates your setup; commands are now available as `/tools:*`.

### First run

```
/tools:doctor     # confirm the environment is healthy
/tools:brief      # orient — even on a fresh repo this shows you what it sees
```

<!-- DEMO GIF: /tools:brief on a returning repo, ~15s asciinema -->

---

## Repo structure

```
claude-toolbox/
├── commands/    # slash commands, delivered as /tools:*
├── agents/      # read-only subagents (explore, plan, review, summarize)
├── skills/      # multi-step skills (sit-rep)
├── scripts/     # Python collectors called by commands and hooks (stdlib only)
├── hooks/       # hooks.json — plugin-registered lifecycle hooks
├── mcp_server/  # local MCP server (search_sessions, list_plans, get_session_log)
├── docs/        # context-hygiene reference, design log, directory reference
└── tests/       # pytest coverage for the collectors
```

---

## Built with Claude Code

`claude-toolbox` is itself a tour of Claude Code's extension model — there is no application runtime, only configuration and stdlib Python. If you're learning what a plugin can do, this repo is a worked example of every major surface:

- **Slash commands** — 12 commands using `$ARGUMENTS`, `` !`bash` `` output injection, and per-command `model` selection (Haiku for cheap/fast, Sonnet for reasoning)
- **Subagents** — 4 custom read-only agents in `agents/` for context-isolated work
- **Skills** — `sit-rep`, a multi-step synthesis skill with bundled scripts and references
- **Hooks** — 5 hooks across `SessionStart`, `PostToolUse`, and `PreCompact`, including a `PreCompact` gate that blocks compaction (exit 2) until you've checkpointed with `/tools:pin`
- **MCP server** — a local stdio server exposing three session-query tools
- **Plugin packaging** — a versioned `plugin.json` manifest, distributed through a marketplace catalog
- **Settings hierarchy** — global / project / local `settings.json`, env vars, and permission scoping

---

## Extending

| Add a… | Steps |
|--------|-------|
| **Command** | Create `commands/[name].md` with frontmatter (`description`, `allowed-tools`, optional `model`, `argument-hint`). Bump the version, restart. |
| **Script**  | Add `scripts/[name].py` (stdlib only). Call it from a command with `!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/[name].py`. |
| **Agent**   | Create `agents/[name].md` with frontmatter (`name`, `description`, `tools`, `model`, `color`). Bump the version, restart. |
| **Hook**    | Add an entry to `hooks/hooks.json` under the event key (`SessionStart`, `PostToolUse`, `PreCompact`, `Stop`, …). Bump the version, restart. |

Bump the version in [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) on every release. See [`CLAUDE.md`](CLAUDE.md) for repo conventions and gotchas.

---

## Roadmap

- **Unified search** across sessions, plans, memory, and backlog from one command
- **Tighter ramp integration** — a single knowledge-and-session harvest at wrap time
- **Submission to the official Anthropic plugin marketplace** once stabilized

---

## License

[MIT](./LICENSE) © 2026 Greenfield Labs
