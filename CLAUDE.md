# CLAUDE.md

## What this is

claude-toolbox — versioned personal Claude Code commands, scripts, and agents. Delivered as
the `tools` plugin (gfl-marketplace). Commands are namespaced `/tools:*`.

## Where things are documented

- What each command, skill, agent, MCP tool, hook, and load-bearing script does —
  [`LIBRARY.md`](LIBRARY.md)
- How to add a command, script, agent, or hook, with the frontmatter each one needs —
  [`README.md`](README.md#extending)
- Branches, PRs, CI gates, and the release sequence — [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Repo layout, the state stores this plugin reads and writes, install and first run —
  [`README.md`](README.md)
- Slug derivation (`_slug.py`): strategies, the two entry points, and the silent-failure
  mode — [`docs/slug-derivation.md`](docs/slug-derivation.md)
- Claude Code directory discovery —
  [`docs/claude-directory-reference.md`](docs/claude-directory-reference.md)

## Environment wiring

Commands call scripts via `!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/foo.py`, so
`CLAUDE_TOOLBOX_ROOT` must be set in `~/.claude/settings.json` to this repo's absolute path.
`scripts/validate-env.py` is the SessionStart hook that checks it.

The `git-policy-auditor` agent reads its policy path from `CLAUDE_TOOLBOX_GIT_POLICY` (same
`env` block); unset falls back to `templates/git-policy/default-policy.md`.

## Gotchas — do not relearn these

- **`${CLAUDE_PLUGIN_ROOT}` is plugin-scoped.** Claude Code documents it as substituted
  in a plugin's own `hooks/hooks.json`, `.mcp.json`, and command/skill/agent bodies —
  never in global `~/.claude/settings.json` hooks (use a plain env var there, e.g.
  `RAMP_ROOT`) and never in the Bash tool's environment. The command-body substitution
  is unproven here on a marketplace install, so command bash lines use
  `CLAUDE_TOOLBOX_ROOT`.
- **`/compact` cannot be invoked programmatically** — it is a CLI built-in; no skill or hook
  can trigger it.
- **Use `shutil.which()`, not `command -v`** — macOS shell builtins have no standalone
  binary, so a `command -v` check in a script lies.
- **Scripts are stdlib-only Python 3.11+.** No third-party imports, ever — the plugin ships
  with no install step.
- **Pass a session cwd to `derive_scope_slug`, never `derive_slug`.** The wrong one
  returns a plausible slug that matches zero tasks instead of erroring.
- **Doc-only fixes still ride a release** — github.com renders `main`, and `main` only moves
  through the release PR.
- **After renaming or adding a plan**, refresh `.project-map` so it resolves in `/tools:*`
  output: `python3 $CLAUDE_TOOLBOX_ROOT/scripts/collect-plan-map.py > /dev/null`.
  (The plan-file *naming* convention is a personal workflow and lives in the global
  `~/.claude/CLAUDE.md`, not in this published repo.)

## Working here

`.claude/settings.json` grants `Bash(gh:*)` for GitHub operations.

Distributed tier: start new work on a `feature/*` branch off `develop`, never directly on
`develop` or `main`. The `git-guard` PreToolUse hook (`scripts/git-guard.py`) enforces the
irreversible subset of that rule automatically — it denies those destructive commands when
Claude runs them via the Bash tool, except a forced branch delete (`branch -D`), which raises
a permission prompt instead. It does **not** fire on the user's own `!git` commands,
which remain the unguarded escape hatch. The habits above (branch off `develop`, ask first)
stay prose because they are interpretive; the hook guards only the deterministic cases.
