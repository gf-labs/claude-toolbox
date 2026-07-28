# Changelog

All notable changes to the `tools` plugin (`claude-toolbox`) are documented here.
This project follows [Semantic Versioning](https://semver.org).

## [0.7.0] — 2026-07-28

### Added
- `/tools:atlas` — cross-project atlas with an adaptive render: ≤4 in-scope projects
  get detail cards, more collapse to one aligned digest line each, grouped by domain.
  Facets projects · sessions · memory · plans · specs · plugins · claude.md; `--dir
  NAME|PATH` anchors the lens at any subtree, `--all` spans every project, `--project
  NAME` inspects one from anywhere, `--full`/`--compact` force cards/digest, `--stale`
  lists orphaned/unscoped keys. Built on a new `_projects.py` enumeration layer.
- `/tools:pin` non-interactive flow — `--yes-all` runs the pin without prompts
  (`--save` persists proposed node upgrades + the MEMORY snapshot, `--ask` overrides),
  and `--yas` is shorthand for `--yes-all --save`. Config-driven via `YES_ALL`.
- `scripts/stamp-git-policy.py` — deterministic git-policy adoption transform: derives
  per-repo CI values, renders the `templates/git-policy/` files, and dry-run-diffs
  (default) or writes (`--write`) them into a target repo. Closes the audit's
  "apply-manual" gap; the `test.yml` template gains an explicit Lint step.

### Changed
- Project enumeration single-sourced onto `_projects.py` (`enumerate_projects` for
  repo-space, `iter_session_dirs` for storage-space) — the hand-rolled enumeration
  across collectors is gone; storage enumeration is namespace-split for orphan safety.
- Current-session resolution now reads the `CLAUDE_CODE_SESSION_ID` environment
  variable instead of inferring the live session from transcript mtimes — the
  freshest-file heuristic misidentified the session whenever two were open at once.
- Repo is ruff-clean with a CI lint gate on `test.yml`; `release.yml` now runs the
  same lint+test bar before cutting a Release, and hard-fails when the pushed tag
  has no matching `CHANGELOG.md` section (previously it shipped placeholder notes).
- git-policy docs clarified: the manifest↔tag sync compares **versions, not commits**.

### Fixed
- Background jobs never claim fork titles in session naming.
- `_scope._reconstruct` correctly inverts the lossy project-key encoding.

## [0.6.0] — 2026-07-01

### Added
- `git-guard.py` — a fail-open `PreToolUse` (Bash) hook that denies only local, irreversible git operations (`reset --hard`, `clean -f*`, `branch -D`, and `checkout`/`restore` discards) when Claude runs them via the Bash tool. It never fires on the user's `!git` commands, which remain the unguarded escape hatch. Pairs with a new **Git workflow** prose rule in `CLAUDE.md` (branch off `develop`, ask-first) — interpretive habits stay prose, deterministic damage-prevention is the hook. This is the plugin's first `PreToolUse` matcher and the layer-3 (client-side, pre-emptive) complement to the CI/CD and branch-protection layers.

## [0.5.2] — 2026-06-30

### Added
- `git-policy-auditor` agent + `collect-git-policy.py` + `check-manifest-tag.py` + hardened CI templates + a generic default policy: audit any repo against a git policy and emit a migration plan.
- Session fork disambiguation — `scripts/relabel-forks.py` and `session_naming.py` helpers relabel same-named forks (auto-compact continuations) so the `/resume` picker stays unambiguous; `post-save.py` self-heals current-scope forks on every pin/wrap.
- `LIBRARY.md` — a full-surface map of the plugin (commands · skill · agents · MCP tools · hooks · scripts), linked from the README.

### Fixed
- `/tools:status` — describe the inline bang-backtick syntax in prose instead of showing it literally, which the renderer would execute at render time (caused a `command not found` crash).

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
