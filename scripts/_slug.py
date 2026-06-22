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

Importable: ``from _slug import derive_slug``.
Runnable:   ``python3 _slug.py [path]`` prints the slug for the path (default:
the git toplevel of the cwd); prints nothing if no path can be resolved.
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


def _git_toplevel() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else _git_toplevel()
    if arg:
        print(derive_slug(arg))
