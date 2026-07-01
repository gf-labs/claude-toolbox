#!/usr/bin/env python3
"""Gather deterministic git-policy facts for a repo as a structured report.

The git-policy-auditor agent RENDERS these facts against the (prose) policy's
tier requirements — it does not re-gather them by hand. Keeping the mechanical
inspection here (not in the agent prompt) makes it testable and keeps the agent
focused on judgment. stdlib-only.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

_CHECKER = Path(__file__).resolve().parent / "check-manifest-tag.py"


def _git(repo: Path, *args: str) -> tuple[int, str]:
    p = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    return p.returncode, p.stdout.strip()


def is_git_repo(repo: Path) -> bool:
    code, out = _git(repo, "rev-parse", "--is-inside-work-tree")
    return code == 0 and out == "true"


def branches(repo: Path) -> list[str]:
    code, out = _git(repo, "branch", "-a", "--format=%(refname:short)")
    return [b for b in out.splitlines() if b.strip()] if code == 0 else []


def default_branch(repo: Path) -> str:
    code, out = _git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if code == 0 and out:
        return out.rsplit("/", 1)[-1]
    code, out = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return out if (code == 0 and out and out != "HEAD") else "main"


def tags(repo: Path) -> list[str]:
    code, out = _git(repo, "tag", "--list", "v*")
    return [t for t in out.splitlines() if t.strip()] if code == 0 else []


def workflows(repo: Path) -> list[str]:
    wf = repo / ".github" / "workflows"
    if not wf.is_dir():
        return []
    return sorted(
        p.name for p in wf.iterdir()
        if p.is_file() and p.suffix in (".yml", ".yaml")
    )


def has_file(repo: Path, relpath: str) -> bool:
    return (repo / relpath).is_file()


def github_slug(repo: Path) -> str | None:
    """owner/repo if origin is a GitHub remote, else None."""
    code, out = _git(repo, "remote", "get-url", "origin")
    if code != 0 or "github.com" not in out:
        return None
    tail = out.split("github.com", 1)[1].lstrip(":/")
    if tail.endswith(".git"):
        tail = tail[:-4]
    return tail or None


def manifest_tag(repo: Path) -> tuple[str, int]:
    """(verdict_line, exit_code) from check-manifest-tag.py in default mode."""
    p = subprocess.run(
        ["python3", str(_CHECKER), "--repo", str(repo)],
        capture_output=True, text=True,
    )
    return (p.stdout.strip() or "(no output)"), p.returncode


def render(repo: Path) -> str:
    if not is_git_repo(repo):
        return "\n".join(["=== REPO ===", f"PATH: {repo}", "GIT: no (not a git work tree)"])
    slug = github_slug(repo)
    verdict, code = manifest_tag(repo)
    return "\n".join([
        "=== REPO ===",
        f"PATH: {repo}",
        f"DEFAULT_BRANCH: {default_branch(repo)}",
        f"GITHUB_REMOTE: {slug or '(none — branch-protection checks are N/A)'}",
        "=== BRANCHES ===",
        "\n".join(branches(repo)) or "(none)",
        "=== TAGS ===",
        "\n".join(tags(repo)) or "(none)",
        "=== MANIFEST_TAG ===",
        f"VERDICT: {verdict}",
        f"EXIT: {code}  (0 match / 1 drift / 2 indeterminate)",
        "=== CI ===",
        "WORKFLOWS: " + (", ".join(workflows(repo)) or "(none)"),
        f"DEPENDABOT: {'yes' if has_file(repo, '.github/dependabot.yml') else 'no'}",
        "=== CHANGELOG ===",
        f"PRESENT: {'yes' if has_file(repo, 'CHANGELOG.md') else 'no'}",
    ])


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Gather git-policy facts for a repo.")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args(argv)
    print(render(Path(args.repo).resolve()))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
