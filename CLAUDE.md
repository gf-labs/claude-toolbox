# CLAUDE.md

## What this is

claude-toolbox — versioned personal Claude Code commands, scripts, and agents. Delivered as the
`tools` plugin (gfl-marketplace). Commands are namespaced `/tools:*`.

## How scripts are called

Commands call scripts via `!python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/foo.py`. The env var
`CLAUDE_TOOLBOX_ROOT` must be set in `~/.claude/settings.json`. It points to this repo's
absolute path.

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
| `hooks/hooks.json` | Plugin-registered hooks (SessionStart, PostToolUse) |
| `scripts/collect-*.py` | Data collection scripts called by commands |
| `scripts/validate-env.py` | SessionStart hook — validates CLAUDE_TOOLBOX_ROOT |
| `scripts/_scope.py` | Scope detection — returns `single`, `parent`, or `global` mode |
| `scripts/post-save.py` | Names current session + renames unnamed sessions in scope |
| `docs/claude-directory-reference.md` | Claude Code directory discovery reference |

## Gotchas

- **`${CLAUDE_PLUGIN_ROOT}` is reserved** — only resolves inside a plugin's own `hooks/hooks.json`. Use a plain env var (e.g. `RAMP_ROOT`) in global `~/.claude/settings.json` hooks.
- **`/compact` cannot be programmatically invoked** — it's a CLI built-in; skills and hooks cannot trigger it.
- **`shutil.which()` not `command -v`** — macOS shell builtins have no standalone binary; use Python's `shutil.which()` to check tool availability in scripts.
- **Session scope key**: `~/.claude/projects/` uses path-based keys (slashes → hyphens). `_scope.py` handles derivation.

## Plan file naming

When a plan file is written to `~/.claude/plans/`, if the filename is a random slug
(pattern: three common words joined by hyphens, e.g. `buzzing-jumping-taco.md`), rename it
to a descriptive kebab-case slug derived from the plan's `# ` title before calling ExitPlanMode.

Steps:
1. Read the plan file to find its `# Title` header.
2. Determine the current project name:
   `Bash: git rev-parse --show-toplevel 2>/dev/null | xargs basename 2>/dev/null || echo ""`
   If the command returns a non-empty value, use it as the prefix (e.g. `claude-toolbox`).
   If empty (not in a git repo), omit the prefix.
3. Convert title to kebab-case: lowercase, spaces→hyphens, strip punctuation, max 6 words.
4. Final filename: `[project]-[title-slug].md` (or just `[title-slug].md` if no project).
5. `Bash: mv ~/.claude/plans/old-name.md ~/.claude/plans/new-name.md`
5b. Record the rename so `.project-map` can resolve JSONL references to the old name:
   `Bash: python3 -c "from pathlib import Path; open(Path.home()/'.claude'/'plans'/'.renames','a').write('old-name.md\tnew-name.md\n')"`
   (Replace `old-name.md` and `new-name.md` with the actual filenames.)
6. Reference the new path going forward.
7. Update `.project-map` so the new plan is tracked immediately:
   `Bash: python3 $CLAUDE_TOOLBOX_ROOT/scripts/collect-plan-map.py > /dev/null`

## Working in this repo

`.claude/settings.json` grants `Bash(gh:*)` for GitHub operations.
