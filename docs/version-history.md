# claude-toolbox — Version History

Milestones compiled from git log. Patch-level fixes and doc-only commits omitted.
Curated through v0.5.x; see `git log` for newer patch-level detail.

---

## v0.5.x — 2026-04 → 2026-06
**Lifecycle redesign, orientation taxonomy, sit-rep, public-release hardening**
- Session-tracking redesign — `collect-pin.py` single-pass collector; `post-save.py` canonical session-naming; `/tools:summarize` and `/tools:snapshot` retired (folded into `/tools:pin`)
- Orientation command taxonomy — `brief` (cold start), `status` (warm pulse), `recap` (time-windowed), `overview` (planning)
- `sit-rep` skill — narrative situation report (velocity, pivots, learnings, risks) with bundled scripts + references
- TaskWarrior migration — `BACKLOG.md` retired; `/tools:backlog` + `/tools:consolidate-tasks` + `collect-inventory.py`
- MCP server — `search_sessions`, `list_plans`, `get_session_log`; `setup-mcp.py` auto-registration
- README overhaul to GFL family standard; public-release hardening pass (accuracy, privacy, install correctness)

## v0.4.24 — 2026-04-05
**Commands: /aside, brief extension support, pin skip check**
- `/tools:aside` — aside/tangent handler command
- `tools:brief` extension model: base command + `.claude/status.md` project extension
- `tools:pin` skip check — no-op if nothing new since last pin

## v0.4.10 — 2026-03-14
**Session summary in /tools:pin Step 1**
- Pin command now shows session activity summary inline (not just branch/backlog state)

## v0.4.7 — 2026-03-14
**Command consolidation**
- `audit` merged into `doctor`; `env` and `rename-sessions` retired
- Cleaner command surface

## v0.4.6 — 2026-03-14
**Rename logic standardization**
- Single rename script, uniform output across brief/pin/wrap

## v0.4.5 — 2026-03-14
**Session auto-rename during lifecycle**
- Auto-renames unnamed sessions during brief/pin/wrap

## v0.4.4 — 2026-03-14
**Session rename from context**
- `rename-sessions` command + `name-session --path` flag

## v0.4.3 — 2026-03-14
**User-invocable session summarizer**
- `/tools:summarize` command *(later retired in v0.5.x — folded into `/tools:pin`)*

## v0.4.2 — 2026-03-14
**Doctor command**
- `/tools:doctor` — global env base + toolbox integrity checks

## v0.4.1 — 2026-03-14
**Global base commands + agents**
- Review and summarize agents added

## v0.4.0 — 2026-03-14
**Linting infrastructure**
- `pyproject.toml`, lint-py hook, `Bash(python3 -m ruff)` permission

## v0.3.8 — 2026-03-14
**Hooks infrastructure + plan-map**
- Hooks: SessionStart, PostToolUse
- `.project-map` plans cache

## v0.3.7 / v0.3.6 / v0.3.5 — 2026-03-14
**brief consolidation; per-command model config**

## v0.3.4 — 2026-03-09
**Session auto-naming + orphaned/unscoped key display split**

## v0.3.3 — 2026-03-09
**brief enrichment**
- Session excerpts, plan previews, memory status, ramp integration

## v0.3.2 — 2026-03-09
**Plan tracking in .project-map**
- Plans section: creation/reference session tracking

## v0.3.1 — 2026-03-09
**Orphaned plugin cache detection**

## v0.2.9 — 2026-03-08
**Session lifecycle**
- `/tools:wrap` end-of-session command
- `session-log.md` — persistent session history
- `/tools:pin` consolidation of summarize + snapshot
- Scope-aware commands via `_scope.py`

## v0.1 — 2026-03-07
**Initial repo scaffold**
- Migrated 6 global commands from `~/.claude/commands/`
- Plugin delivery via `--plugin-dir`
- `docs/`, `scripts/`, `agents/`, `hooks/` structure
