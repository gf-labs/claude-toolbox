#!/usr/bin/env python3
"""Single source of truth for the repo-path → TaskWarrior project slug mapping.

Used by collect-pin.py, collect-tasks.py, and the /tools:* command markdown
(invoked as a CLI: `python3 _slug.py [path]`).

Mechanism (public default): the slug is the repo's basename. A freshly-installed
toolbox files every repo's tasks under ``<reponame>`` and assumes nothing about
where repos live on disk.

Policy (opt-in, set by a personal config — e.g. dot-configs' settings.json):

  CLAUDE_TOOLBOX_REPOS_ROOT     anchor directory repos live under (e.g. ~/Repos)
  CLAUDE_TOOLBOX_SLUG_STRATEGY  "basename" (default) | "domain.repo"

With ``strategy=domain.repo`` and a ``repos_root``, the slug is
``<first-component>.<basename>``: the first path component under ``repos_root``
is the domain, the basename is the repo, and any container dirs between them
(e.g. ``business/_claude-plugins/ramp`` → ``business.ramp``) are skipped, so
tasks are not orphaned under the container. A repo outside ``repos_root`` falls
back to its basename.

``derive_slug`` maps a **repo**. A Claude Code *scope* is not always a repo —
projects can be rooted at a subdirectory — so sub-repo scopes go through
``derive_scope_slug``, which adds one rule on top: a scope inside a repo slugs
as ``<repo basename>.<scope basename>``.

Importable: ``from _slug import derive_slug, derive_scope_slug``.
Runnable:   ``python3 _slug.py [path]`` prints the slug for the path (default:
the cwd); prints nothing if no path can be resolved. The CLI takes the scope
reading, so it answers correctly from inside a subdirectory.
"""
import os
import subprocess
import sys
from pathlib import Path


def _env_repos_root() -> Path | None:
    val = os.environ.get("CLAUDE_TOOLBOX_REPOS_ROOT")
    return Path(val).expanduser() if val else None


def derive_slug(repo_path, repos_root: Path | None = None,
                strategy: str | None = None) -> str:
    """Map a repo path to a TaskWarrior project slug. See module docstring.

    Explicit ``repos_root`` / ``strategy`` arguments override the environment;
    when omitted they are read from the env vars (mechanism default: basename).
    """
    repo_path = Path(repo_path)
    if strategy is None:
        strategy = os.environ.get("CLAUDE_TOOLBOX_SLUG_STRATEGY", "basename")
    if repos_root is None:
        repos_root = _env_repos_root()

    if strategy == "domain.repo" and repos_root is not None:
        try:
            parts = repo_path.resolve().relative_to(repos_root.resolve()).parts
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[-1]}"
            if len(parts) == 1:
                return parts[0]
        except ValueError:
            pass
    return repo_path.name


def _git_toplevel(cwd=None) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL, text=True, cwd=cwd,
        ).strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def derive_scope_slug(scope_dir, repo_root=None, repos_root: Path | None = None,
                      strategy: str | None = None) -> str:
    """Map a *scope* directory to a slug. ``derive_slug`` plus the sub-repo rule.

    A scope is whatever a Claude Code project is rooted at, which is not always
    a repo — this toolbox's own sessions root at ``lib/tools/<tool>/``. Handing
    such a path to ``derive_slug`` yields a slug that matches nothing, silently:
    under ``domain.repo`` it pairs the DOMAIN with a non-repo basename, so
    ``~/Repos/business/toolbox/lib/tools/workstation`` slugs ``business.``
    ``workstation`` while the tasks live under ``toolbox.workstation``. Nothing
    errors; the backlog just reads empty.

    Rules:
      scope is the repo root, or is in no repo -> ``derive_slug`` unchanged
      scope is inside a repo                   -> ``<repo basename>.<scope basename>``

    The sub-scope form uses the repo's **basename**, never its full slug: the
    convention in use is ``toolbox.workstation`` / ``toolbox.dot``, not
    ``business.toolbox.workstation``. Only the repo-root half varies by
    strategy, so a sub-scope reads the same under either one.

    ``repo_root`` is accepted so a caller that already resolved it (collect-pin
    runs ``git rev-parse`` for other reasons) does not pay for a second
    subprocess; omitted, it is resolved from ``scope_dir``.
    """
    scope = Path(scope_dir)
    if repo_root is None:
        repo_root = _git_toplevel(scope if scope.is_dir() else None)
    if repo_root is None:
        return derive_slug(scope, repos_root, strategy)
    repo_root = Path(repo_root)
    try:
        rel = scope.resolve().relative_to(repo_root.resolve())
    except (ValueError, OSError):
        # Scope is not under the repo we were handed — trust the scope, not it.
        return derive_slug(scope, repos_root, strategy)
    if not rel.parts:
        return derive_slug(repo_root, repos_root, strategy)
    return f"{repo_root.name}.{scope.name}"


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    if arg:
        print(derive_scope_slug(arg))
