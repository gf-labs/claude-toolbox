# Changelog

All notable changes to the `tools` plugin (`claude-toolbox`) are documented here.
This project follows [Semantic Versioning](https://semver.org).

## [Unreleased]

### Added
- `git-policy-auditor` agent + `collect-git-policy.py` + `check-manifest-tag.py` + hardened CI templates + a generic default policy: audit any repo against a git policy and emit a migration plan.

## [0.5.1] — 2026-06-17

First public release under `gf-labs`. Session-lifecycle management for Claude Code,
delivered as the `tools` plugin (commands namespaced `/tools:*`).

### Commands
Twelve session-lifecycle commands:
`aside` · `backlog` · `brief` · `cleanup` · `consolidate-tasks` · `doctor` ·
`overview` · `pin` · `recap` · `search-sessions` · `status` · `wrap`

### Internals
- **One path encoder** — `scripts/_scope.py` `project_key()` is the single source for
  the cwd → `~/.claude/projects` key encoding, collapsing the inline copies that had
  drifted across scripts; it probes disk to stay correct across older Claude Code
  encodings.
- **One slug deriver** — `scripts/_slug.py` is the single source for repo → TaskWarrior
  project slug, consumed by the collectors and the command markdown.
- **PreCompact gate** — `scripts/check-pin-ran.py` reads the session id from stdin and
  warns when a session is compacted without a pin.
- **Session naming** — `scripts/post-save.py` names the current session and any unnamed
  sessions in scope.

### Packaging
- LICENSE, README, and marketplace metadata for distribution via `gf-labs/gfl-marketplace`.
