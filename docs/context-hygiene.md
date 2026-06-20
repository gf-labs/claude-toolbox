# Context Hygiene — Reference Guide

A durable reference for managing Claude Code context across sessions and projects.
Run `/tools:cleanup` to act on most of this automatically.

---

## How context works

### The context window (per session)
- A single rolling buffer, ~200k tokens for Claude Sonnet 4.6
- Everything in the session lives here: messages, tool results, injected files, auto-collected bash output
- When full: older turns are **compacted** (summarized + discarded). Recent turns stay verbatim.
- Accepting compact when prompted = cleaner summary with full context still fresh. **Accept it.**
- The raw session transcript lives at `~/.claude/projects/[project-key]/[session-id].jsonl`

### What persists across sessions

| Store | Location | Loaded automatically? | You control it? |
|-------|----------|-----------------------|-----------------|
| MEMORY.md | `~/.claude/projects/[key]/memory/MEMORY.md` | Yes (auto-memory, 200-line limit) | Yes — `/tools:pin`, `/tools:cleanup` |
| session-log.md | `~/.claude/projects/[key]/memory/session-log.md` | No | Yes — written by `/tools:pin`, `/tools:wrap`, `/tools:cleanup` |
| CLAUDE.md | `[repo]/CLAUDE.md` or `~/.claude/CLAUDE.md` | Yes (every session) | Yes — edit directly |
| Plans | `~/.claude/plans/[name].md` | No (read on demand) | Yes — delete when done |
| Reference docs | `~/.claude/docs/[topic].md` | No (reference on demand) | Yes |
| Knowledge graph | `~/.claude/knowledge-graphs/[topic].md` | No (loaded by ramp) | Yes — managed by `/ramp:up` |
| Session files | `~/.claude/projects/[key]/[id].jsonl` | No (archive only) | Yes — delete freely |

### Token costs (approximate)
- 1 English paragraph (~100 words) ≈ 130 tokens
- 100-line Python file ≈ 600–1,000 tokens
- 100-line JSON/YAML ≈ 1,500–2,500 tokens
- Large bash output dump (500 lines) ≈ 3,000–8,000 tokens
- CLAUDE.md (typical) ≈ 3,000–4,000 tokens
- MEMORY.md (typical) ≈ 2,000–3,000 tokens
- **Rule of thumb:** heavy tool-use sessions exhaust a window in 30–50 turns; conversation-only can go 300+

---

## What belongs where

| Information | Right place |
|------------|-------------|
| How this project works (stable, permanent) | `CLAUDE.md` |
| Project motivation, founding context, JDs | `CLAUDE.md` `## Background` section or `~/.claude/docs/` |
| Stable patterns, preferences, architectural decisions | `MEMORY.md` (via `/tools:pin`) |
| Session history — what was done and when | `session-log.md` (via `/tools:pin` or `/tools:wrap`) |
| In-flight design for a specific feature | Plan file (delete when done) |
| Reference material you might re-inject | `~/.claude/docs/[topic].md` (global) or `docs/context/[name].md` (repo) |
| Your demonstrated Claude Code skills | Knowledge graph (`~/.claude/knowledge-graphs/`) |
| Raw session transcript | `.jsonl` file — scratch paper, delete freely |

---

## Splitting off adjacent work

When a tangential issue comes up mid-session:

1. **In the current session:** write a plan file with all relevant context:
   - What the issue is
   - Key artifacts to read (`@path/to/file`)
   - What done looks like
2. **Open a new terminal tab/pane**, `cd` to the same (or relevant) repo, run `claude`
3. In the new session: `@~/.claude/plans/[name].md` loads the handoff
4. Work proceeds independently; current session stays on topic

**Agent tool (within session):** Dispatch a subagent for self-contained tasks. It runs to completion and returns results — not a persistent parallel session. Good for "go implement X and return the result," not for ongoing parallel conversation.

**Worktrees:** For branch-isolated work, `git worktree add ../[name] -b [branch]` + new terminal in that directory. Sessions in worktrees are independent.

---

## MEMORY.md management

- **200-line truncation:** MEMORY.md is loaded at session start but truncated at 200 lines. Content after line 200 is silently dropped. The most recently appended content gets cut off first.
- **Rule:** Keep MEMORY.md under 150 lines. Archive verbose or resolved sections to topic files.
- **Structure:** Stable facts at the top (architecture, patterns, preferences), recent snapshots at the bottom.
- When a project goes dormant: extract key decisions to MEMORY.md, delete all sessions.

---

## Maintenance routine

| Frequency | Action |
|-----------|--------|
| End of each working session | `/tools:wrap` — session log + git check + plan cleanup + backlog + done marker |
| Mid-session break (session log + memory) | `/tools:pin` — status + session-log entry + optional MEMORY.md update, in one step |
| End of a feature/topic | Delete completed plan files (via `/tools:wrap` Step 3 or manually) |
| When MEMORY.md hits ~150 lines | `/tools:pin` migration — move old snapshot entries to session-log.md; archive verbose sections to topic files |
| Weekly (or when returning to a project) | `/tools:cleanup` — delete old sessions, extract context, surface memory warnings |
| When a project is dormant | Extract key decisions to MEMORY.md, delete all sessions via `/tools:cleanup` |

Run `/tools:cleanup` to handle sessions, plans review, memory size warnings, and plugin cache drift in one pass.

---

## Reference artifacts — how to store them

For any content you want available in future sessions:

```
~/.claude/docs/              # Global reference (cross-project)
  context-hygiene.md         # This file
  [topic].md

[repo]/docs/context/         # Project-specific reference
  background.md              # Project motivation, JDs, founding context
  decisions.md               # Architecture decisions
  [topic].md
```

To inject into a session: `@~/.claude/docs/[file].md` in a prompt or command.
To make always-available for a project: add `@docs/context/background.md` to CLAUDE.md.

**For URLs:** Store URL + a 2–3 line summary. URLs rot; local copies don't. For critical reference material, store a local copy.
