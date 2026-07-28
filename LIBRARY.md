# claude-toolbox — Library

The complete surface of the `tools` plugin. Everything user-facing is namespaced `tools:`
(e.g. `/tools:status`, agent `tools:review`). This file is the map; each command/skill file
carries its own detailed prompt.

**Four user-facing surfaces:** commands · skills · agents · MCP tools.
**Two infrastructure layers:** hooks (auto-fire) · scripts (called by the above).

---

## Commands

Single-file prompt templates in `commands/*.md`, invoked explicitly as `/tools:<name>`.

### 🧭 Orientation — read-only "where am I?"
Point-in-time situational awareness. None of these write anything. Pick by how cold you are.

| Command | Use when | Model |
|---------|----------|-------|
| `/tools:brief` | Cold start / returning after days–weeks; scales depth to absence | haiku |
| `/tools:status` | Warm mid-session pulse — git detail, last note, in-progress backlog | haiku |
| `/tools:recap` | Stepped away hours/days — commits, notes, files in a time window | haiku |
| `/tools:overview` | Planning — PM-style state + backlog priorities + plans + sequencing | sonnet |

> The narrative-synthesis sibling of this group is the **`/tools:sit-rep`** *skill* (see Skills) —
> use it for the multi-week arc, not the point-in-time snapshot.

### 🗺️ Inventory — cross-project map
The map around you — current project + nested children by default, `--dir` to anchor anywhere, `--all` for the whole machine (Orientation is single-project; this is cross-project).

| Command | Use when | Model |
|---------|----------|-------|
| `/tools:atlas` | Cross-project map, adaptive render — ≤4 projects in scope → detail cards, more → aligned digest grouped by domain; default: current project + children, every facet except plugins; facets projects · sessions · memory · plans · specs · plugins · claude.md; `--dir NAME\|PATH` = the subtree under any directory; `--all` = every project; `--project NAME` inspects any project from anywhere; `--full`/`--compact` force cards/digest; `--stale` lists orphaned/unscoped keys | haiku |

### 🔖 Checkpoints & close-out — the only commands that write session memory
These append to `session-log.md` / `MEMORY.md`.

| Command | Use when |
|---------|----------|
| `/tools:pin` | Mid-session checkpoint before a break/compact — status, session log, optional MEMORY.md; `--yes-all` runs it non-interactively (`--save` persists, `--ask` overrides) |
| `/tools:wrap` | End-of-session close-out — session log, git check, plan cleanup, backlog review, done marker |

### ⏸️ In-flight
| Command | Use when |
|---------|----------|
| `/tools:aside` | A side question interrupts the main task — answer it, then resume cleanly |

### ✅ Task & backlog
| Command | Use when |
|---------|----------|
| `/tools:backlog` | Add a single task to TaskWarrior for this project |
| `/tools:consolidate-tasks` | Scan repo (or all repos via `--discover`) → dedup → bulk-create tasks → tombstone source |

### 🩺 Maintenance & history
| Command | Use when |
|---------|----------|
| `/tools:doctor` | Claude Code environment + project health check (`--dry-run` to report only) |
| `/tools:cleanup` | Prune old session artifacts — extract context first, then delete |
| `/tools:search-sessions` | Keyword-search session history → matching sessions with title + prompts |

---

## Skills

Bundled `skills/<name>/SKILL.md` + reference docs + scripts. Can **auto-trigger** on natural
language (not just explicit invocation), and use progressive disclosure for their references.

| Skill | Use when |
|-------|----------|
| `/tools:sit-rep` | Narrative synthesis across 2+ weeks of work — velocity, milestones, pivots, learnings, risks. The *arc*, not the current task. Bundles `output-template.md`, `signal-extraction.md`, `collect-velocity.sh`. |
| `/tools:cli-capability-audit` | A CLI's docs have drifted from what it implements, or a repo needs a verified command inventory. Derives the implemented surface from dispatcher source, diffs it against `--help` and the docs **in both directions** (phantom vs undocumented), and publishes a capability map. Bundles `extract-surface.py`, `diff-surface.py`, `failure-modes.md`, `capability-map-template.md`. |

---

## Agents

Subagents in `agents/*.md` — dispatched by the model (or via the Agent tool), not typed as
slash commands. All read-only except where noted.

| Agent | Role |
|-------|------|
| `tools:explore` | Fast codebase explorer — finds files, searches code, answers structure questions |
| `tools:plan` | Implementation planner — reads codebase, returns a phase-by-phase plan (no writes) |
| `tools:review` | Structured code review — diff analysis, readability, correctness, security (read-only) |
| `tools:summarize` | Session summarizer — given a JSONL session path, returns a concise summary |
| `tools:git-policy-auditor` | Read-only audit of a repo against a git policy (or the bundled default) — emits a compliance report + migration plan |

---

## MCP server

Server `claude-toolbox` (`mcp_server/server.py`) — exposes session data as tools queryable from
**any** Claude context, not just this project. Registered at user scope on SessionStart.

| Tool | Returns |
|------|---------|
| `search_sessions` | Keyword search across **all** projects (default: no age cap) |
| `list_plans` | All active plans with title, project attribution, line count |
| `get_session_log` | A project's session-log entries (last 20) |

---

## Hooks

Auto-fire handlers registered in `hooks/hooks.json`.

| Event | Handler | Purpose |
|-------|---------|---------|
| PreToolUse (Bash) | `git-guard.py` | Denies local irreversible git ops (`reset --hard`, `clean -f*`, `branch -D`, `checkout`/`restore` discards) on Claude's calls. Fail-open; user `!git` bypasses |
| SessionStart | `validate-env.py` | Verifies `CLAUDE_TOOLBOX_ROOT` is set |
| SessionStart | `setup-mcp.py` | Idempotently registers the MCP server (`claude mcp add -s user`) |
| PostToolUse | `collect-plan-map.py` | Refreshes `.project-map` plan index |
| PostToolUse | `lint-py.py` | Lints touched Python |
| PreCompact | `check-pin-ran.py` | Warns if you didn't `/tools:pin` before compacting |

---

## Scripts (infrastructure)

~40 files in `scripts/` — called by the commands/hooks above, not invoked directly. The
load-bearing ones:

| Script(s) | Role |
|-----------|------|
| `_scope.py` | Scope detection + project-key encoding — **single source of truth** |
| `_projects.py` | L2 project enumeration over `_scope` — repo-space (`enumerate_projects`, powers atlas) *and* storage-space (`iter_session_dirs`, session-key folders incl. orphans; powers cleanup · search-sessions · brief) |
| `_session.py` | Current-session JSONL resolution — env-var-first (`CLAUDE_CODE_SESSION_ID`), heuristic fallback; **single source of truth** for "which session is live" |
| `_slug.py` | Repo path → TaskWarrior project slug — **single source of truth** |
| `collect-*.py` (≈19) | Data collectors feeding the commands (pin, summarize, tasks, drift, history, memory…); `collect-session-list.py` = the atlas sessions facet (distinct from `collect-sessions.py`, the cleanup inventory) |
| `collect-git-policy.py` | Deterministic git-policy facts (branches, tags, workflows, dependabot/CHANGELOG, manifest↔tag) for `tools:git-policy-auditor` to render |
| `check-manifest-tag.py` | Assert a repo's manifest version equals its latest release tag — collector/audit + CI gate (stdlib, exit 0/1/2) |
| `stamp-git-policy.py` | Stamp git-policy CI files into a target repo — derives per-repo values, dry-run diff by default, `--write` to apply; never touches git |
| `post-save.py`, `session_naming.py`, `relabel-forks.py`, `name-session.py`, `rename-unnamed.py` | Session naming + fork disambiguation |
| `update-project-map.py`, `collect-plan-map.py` | Keep `.project-map` current |
| `session_index.py`, `mark-session-done.py`, `add-tasks.py`, `lint-py.py`, `setup-mcp.py`, `validate-env.py` | Supporting utilities + hook bodies |

---

## At a glance

**13 commands · 2 skills · 5 agents · 3 MCP tools · 6 hook handlers · ~40 scripts** — all
user-facing surfaces namespaced `tools:`. Plugin manifest: `.claude-plugin/plugin.json`.
