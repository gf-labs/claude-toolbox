# CLAUDE.md

## What this is

claude-toolbox — versioned personal Claude Code commands, scripts, and agents. Delivered as the
`tools` plugin (gfl-marketplace). Commands are namespaced `/tools:*`.

## How scripts are called

Commands call scripts via `!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/foo.py`. The env var
`CLAUDE_TOOLBOX_ROOT` must be set in `~/.claude/settings.json`. It points to this repo's
absolute path.

The `git-policy-auditor` agent reads the policy path from `CLAUDE_TOOLBOX_GIT_POLICY` (set in
`~/.claude/settings.json` `env`); unset falls back to `templates/git-policy/default-policy.md`.

## TaskWarrior project slug (`scripts/_slug.py`)

`scripts/_slug.py` is the single source of truth for mapping a repo path → TaskWarrior
project slug. `collect-pin.py`, `collect-tasks.py`, and the `/tools:*` command markdown all
go through it (the markdown invokes it as `python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_slug.py`).

- **Default (mechanism): `slug = repo basename`** — no assumption about where repos live.
- **Opt-in (policy), via `~/.claude/settings.json` `env`:**
  - `CLAUDE_TOOLBOX_REPOS_ROOT` — anchor dir repos live under (also the `--discover` default).
  - `CLAUDE_TOOLBOX_SLUG_STRATEGY` — `basename` (default) or `domain.repo` (`<first-component-under-root>.<basename>`, skipping any `_container/` in between).

This keeps the published plugin generic; a personal config (e.g. dot-configs) sets the env
to restore the `~/Repos/<domain>/<repo>` → `domain.repo` convention. `--discover` walks
`_name/` containers without spending a depth level and skips `.name/` dormant dirs.

## How to add a new command

1. Create `commands/[name].md` with standard frontmatter
2. If it needs a script: add `scripts/collect-[name].py` or `scripts/[name].py`
3. Bump version in `.claude-plugin/plugin.json`
4. Changes take effect automatically on next session start (plugin loads via `--plugin-dir`)

## Command frontmatter fields

| Field | Required | Notes |
|-------|----------|-------|
| `description` | Yes | Shown in `/skills` list |
| `allowed-tools` | Yes | e.g. `Bash, Read, Write, Edit` |
| `model` | No | Defaults to session model; use `claude-haiku-4-5-20251001` for fast/cheap commands |
| `argument-hint` | No | Hint shown in autocomplete, e.g. `[--dry-run]` |

Use `$ARGUMENTS` in the command body to pass user-provided args to scripts.

## How to add a new agent

Create `agents/[name].md` with `name`, `description`, `tools`, `model`, and `color` frontmatter.
Plugin delivers it automatically on next install.

## Key files

| File | Role |
|------|------|
| `.claude-plugin/plugin.json` | Plugin manifest — bump version on every release |
| `hooks/hooks.json` | Plugin-registered hooks (SessionStart, PostToolUse, PreCompact) |
| `scripts/collect-*.py` | Data collection scripts called by commands |
| `scripts/validate-env.py` | SessionStart hook — validates CLAUDE_TOOLBOX_ROOT |
| `scripts/_scope.py` | Scope detection — returns `single`, `parent`, or `global` mode |
| `scripts/post-save.py` | Names current session + renames unnamed sessions in scope |
| `docs/claude-directory-reference.md` | Claude Code directory discovery reference |
| `agents/git-policy-auditor.md` | Read-only agent auditing a repo against the git policy at `$CLAUDE_TOOLBOX_GIT_POLICY` (unset → bundled default) |

## Gotchas

- **`${CLAUDE_PLUGIN_ROOT}` is reserved** — only resolves inside a plugin's own `hooks/hooks.json`. Use a plain env var (e.g. `RAMP_ROOT`) in global `~/.claude/settings.json` hooks.
- **`/compact` cannot be programmatically invoked** — it's a CLI built-in; skills and hooks cannot trigger it.
- **`shutil.which()` not `command -v`** — macOS shell builtins have no standalone binary; use Python's `shutil.which()` to check tool availability in scripts.
- **Session scope key**: `~/.claude/projects/` uses path-based keys (slashes → hyphens). `_scope.py` handles derivation.

## Plan file tracking

`scripts/collect-plan-map.py` refreshes `.project-map` so renamed or newly-added plans in
`~/.claude/plans/` resolve in `/tools:*` output:
`python3 $CLAUDE_TOOLBOX_ROOT/scripts/collect-plan-map.py > /dev/null`

(The plan-file *naming* convention — renaming random three-word slugs to a title-derived
kebab-case name — is a personal workflow and lives in the global `~/.claude/CLAUDE.md`, not in
this published repo.)

## Working in this repo

`.claude/settings.json` grants `Bash(gh:*)` for GitHub operations.
