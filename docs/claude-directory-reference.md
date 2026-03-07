# Claude Code Directory Reference

A reference for where Claude Code discovers and loads different artifact types, and how the `tools` plugin delivers them.

## Discovery table

| Directory / File | Plugin-delivered | Global | Project | Notes |
|-----------------|-----------------|--------|---------|-------|
| `commands/` | ✓ namespaced `/tools:*` | `~/.claude/commands/` | `.claude/commands/` | Auto-discovered by plugin system |
| `agents/` | ✓ | `~/.claude/agents/` | `.claude/agents/` | Auto-discovered; `Agent(subagent_type=name)` |
| `scripts/` | ✓ via `CLAUDE_TOOLBOX_ROOT` | `~/.claude/scripts/` | `.claude/scripts/` | Not auto-discovered; called via `!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/foo.py` |
| `docs/` | ✓ via reference | `~/.claude/docs/` | `.claude/docs/` | Not auto-discovered; `@`-included or linked in CLAUDE.md |
| `hooks/hooks.json` | ✓ auto-registered | via `settings.json` | via `.claude/settings.json` | Auto-registered on `/plugin install` |
| `mcp/server.py` | ✓ | via `~/.mcp.json` | via `.mcp.json` | Must be manually registered |
| `settings.json` | ✗ | personal (dotfiles) | personal | Not plugin-managed |
| `CLAUDE.md` | ✗ | personal (dotfiles) | personal | Not plugin-managed |

## Notes

**Commands vs skills**: No separate `skills/` directory. Both user slash commands (`/tools:cleanup`) and Claude-invoked skills use the same `commands/` files. Different invocation path, same source.

**Scripts path**: Commands call scripts via `!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/foo.py`. The `CLAUDE_TOOLBOX_ROOT` env var is set in `~/.claude/settings.json` and expands in shell-executed bash injections. This is stable across plugin version upgrades (points to the live repo, same pattern as `CLAUDE_PLUGIN_ROOT` in ramp).

**Scope model**: Claude Code does not walk up the directory tree — a `.claude/` at a parent level is treated as the project scope for sessions launched there. Global scope (`~/.claude/`) is always available.

**Plugin delivery**: The plugin system copies files to `~/.claude/plugins/cache/[marketplace]/[plugin]/[version]/` on install. Commands in `commands/` are auto-served with the plugin namespace. Hooks in `hooks/hooks.json` are auto-registered.
