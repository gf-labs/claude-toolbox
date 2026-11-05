# Contributing to claude-toolbox

The repo ships as the `tools` plugin. Git Flow with CI-enforced releases; the gates below
are machines, not suggestions.

## Branches and PRs

- `main` = stable releases only; `develop` = daily integration.
- Branch `feature/<name>` off `develop`; PRs into `develop` are **squash-merged**.
- `release/*` / `hotfix/*` merge into `main` via merge-commit PRs. A release bumps the
  manifest version on the release branch, tags the release-branch tip `vX.Y.Z`, then
  merges, so tag and manifest land on `main` together.

## The gates

- **test.yml** — ruff + pytest on Python 3.11. Locally:
  `python3 -m pip install -r requirements-dev.txt && ruff check . && python3 -m pytest tests/ -q`
- **release-gate.yml** — PRs into `main` need a `## [<manifest version>]` CHANGELOG
  section; pushes to `main` must match the nearest reachable tag.
- **release.yml** — on a `v*` tag, re-runs lint, tests, and the manifest↔tag check, then
  publishes a GitHub Release whose notes are that tag's CHANGELOG section (hard-fails
  when the section is missing). No build or publish step — distribution is "clone `main`".
- **check-docs.py** — README agents/hooks tables, LIBRARY.md counts, and relative links
  must match the tree. Locally: `python3 scripts/check-docs.py`
- Actions are SHA-pinned; Dependabot maintains them.

## Changes

- Every user-visible change adds a `## [Unreleased]` CHANGELOG entry.
- Scripts are **stdlib-only** Python 3.11+. New commands/agents/hooks: see
  [`README.md`](README.md#extending) for the frontmatter contracts, and add the matching
  row to [`LIBRARY.md`](LIBRARY.md) — the docs checker will hold you to it.
- Commit style: `type(scope): imperative summary` (≤ 50 chars).
- Pre-release checklist: re-verify README claims against the diff.

Licensed MIT — contributions land under the same license.
