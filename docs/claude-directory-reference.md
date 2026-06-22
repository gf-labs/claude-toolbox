# Claude Code Directory Reference

A reference for where Claude Code discovers and loads different artifact types, and how the `tools` plugin delivers them.

## Discovery table

| Directory / File | Plugin-delivered | Global | Project | Notes |
|-----------------|-----------------|--------|---------|-------|
| `commands/` | ✓ namespaced `/tools:*` | `~/.claude/commands/` | `.claude/commands/` | Auto-discovered by plugin system |
| `agents/` | ✓ | `~/.claude/agents/` | `.claude/agents/` | Auto-discovered; `Agent(subagent_type=name)` |
| `skills/` | ✓ | `~/.claude/skills/` | `.claude/skills/` | Auto-discovered; multi-step skills with bundled scripts/references (e.g. `skills/sit-rep/`) |
| `scripts/` | ✓ via `CLAUDE_TOOLBOX_ROOT` | `~/.claude/scripts/` | `.claude/scripts/` | Not auto-discovered; called via `!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/foo.py` |
| `docs/` | ✓ via reference | `~/.claude/docs/` | `.claude/docs/` | Not auto-discovered; `@`-included or linked in CLAUDE.md |
| `hooks/hooks.json` | ✓ auto-registered | via `settings.json` | via `.claude/settings.json` | Auto-registered on `/plugin install` |
| `mcp_server/server.py` | ✓ | via `~/.claude.json` | via `.mcp.json` | Must be manually registered (or auto-registered by `setup-mcp.py`) |
| `settings.json` | ✗ | personal (dotfiles) | personal | Not plugin-managed |
| `CLAUDE.md` | ✗ | personal (dotfiles) | personal | Not plugin-managed |

## Notes

**Commands vs skills**: Most user slash commands live in `commands/` (served as `/tools:*`, e.g. `/tools:cleanup`). Multi-step skills that bundle their own scripts and reference files live in `skills/` (e.g. `skills/sit-rep/`). Both are plugin-delivered and auto-discovered; the difference is structure (a single command file vs. a skill directory), not location.

**Scripts path**: Commands call scripts via `!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/foo.py`. The `CLAUDE_TOOLBOX_ROOT` env var is set in `~/.claude/settings.json` and expands in shell-executed bash injections. This is stable across plugin version upgrades (points to the live repo, same pattern as `CLAUDE_PLUGIN_ROOT` in ramp).

**Scope model**: Claude Code does not walk up the directory tree — a `.claude/` at a parent level is treated as the project scope for sessions launched there. Global scope (`~/.claude/`) is always available.

**Plugin delivery**: The plugin system copies files to `~/.claude/plugins/cache/[marketplace]/[plugin]/[version]/` on install. Commands in `commands/` are auto-served with the plugin namespace. Hooks in `hooks/hooks.json` are auto-registered.
