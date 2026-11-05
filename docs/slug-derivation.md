# Slug derivation — repo path → TaskWarrior project slug

`scripts/_slug.py` is the single source of truth for mapping a path to a TaskWarrior
project slug. `collect-pin.py`, `collect-tasks.py`, and the `/tools:*` command markdown all
go through it (the markdown invokes it as
`python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_slug.py`).

## Mechanism and policy

- **Default (mechanism): `slug = repo basename`** — no assumption about where repos live.
- **Opt-in (policy), via `~/.claude/settings.json` `env`:**
  - `CLAUDE_TOOLBOX_REPOS_ROOT` — the anchor directory repos live under; also the
    `--discover` default.
  - `CLAUDE_TOOLBOX_SLUG_STRATEGY` — `basename` (default) or `domain.repo`
    (`<first-component-under-root>.<basename>`, skipping any `_container/` in between).

This split keeps the published plugin generic: a personal dotfiles config sets the env to
restore a `~/Repos/<domain>/<repo>` → `domain.repo` convention. `--discover` walks
`_name/` containers without spending a depth level and skips `.name/` dormant dirs.

## Two entry points — pick by what you hold

`derive_slug` maps a **repo**. `derive_scope_slug` maps a **scope**, which is whatever a
Claude Code project is rooted at and is not always a repo (a monorepo may root its
sessions at `lib/tools/<tool>/`). A scope below the repo root slugs as
`<repo basename>.<scope basename>` — `mono.cli`, `mono.api` — using the repo's basename
and never its full slug, so a sub-scope reads the same under either strategy. At the repo
root the two functions are identical.

## The failure mode this exists to prevent

Handing a sub-repo path to `derive_slug` **fails silently**. Under `domain.repo` it pairs
the domain with a non-repo basename (`~/Repos/work/mono/lib/tools/cli` → `work.cli`,
which matches zero tasks), and an empty backlog reads as "nothing queued" rather than as
a lookup miss. That was live in `collect-pin.py` until the scope-slug fix landed.

A caller holding a session cwd wants `derive_scope_slug`. The `_slug.py` CLI takes the
scope reading, so the `/tools:*` markdown is correct even when invoked from inside a
subdirectory.
