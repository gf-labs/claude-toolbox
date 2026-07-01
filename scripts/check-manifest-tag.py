#!/usr/bin/env python3
"""Assert a repo's manifest version matches its latest release tag.

Shares the genre of gfl-marketplace's validate-marketplace.py (a stdlib CI gate
that exits non-zero) applied to the manifest<->tag sync rule in git-policy.md.
Dual-use: the facts collector runs it during audit, and release.yml vendors it
as a CI gate. stdlib-only.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

# Stable release tags only: vMAJOR.MINOR.PATCH (pre-release tags are excluded
# from "latest stable" — they never satisfy the manifest<->tag sync rule).
SEMVER_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def read_manifest_version(repo: Path) -> tuple[str, str]:
    """Return (version, manifest_relpath) for the first manifest found.

    Search order: .claude-plugin/plugin.json, pyproject.toml, package.json.
    Raises FileNotFoundError if none exist, KeyError if one exists without a
    version, ModuleNotFoundError if a pyproject needs tomllib on Python <3.11.
    """
    plugin = repo / ".claude-plugin" / "plugin.json"
    if plugin.is_file():
        return json.loads(plugin.read_text(encoding="utf-8"))["version"], ".claude-plugin/plugin.json"

    pyproject = repo / "pyproject.toml"
    if pyproject.is_file():
        import tomllib  # stdlib >=3.11; lazy so the json paths work on any 3.x
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        if "version" in data.get("project", {}):
            return data["project"]["version"], "pyproject.toml"
        if "version" in data.get("tool", {}).get("poetry", {}):
            return data["tool"]["poetry"]["version"], "pyproject.toml"
        raise KeyError("pyproject.toml has no project.version or tool.poetry.version")

    pkg = repo / "package.json"
    if pkg.is_file():
        return json.loads(pkg.read_text(encoding="utf-8"))["version"], "package.json"

    raise FileNotFoundError(
        "no manifest found (.claude-plugin/plugin.json, pyproject.toml, package.json)"
    )


def latest_stable_tag(tags: list[str]) -> str | None:
    """Return the highest stable vX.Y.Z tag by SemVer precedence, or None."""
    parsed = []
    for t in tags:
        m = SEMVER_TAG.match(t.strip())
        if m:
            parsed.append((tuple(int(g) for g in m.groups()), t.strip()))
    if not parsed:
        return None
    parsed.sort()
    return parsed[-1][1]


def git_tags(repo: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "tag", "--list", "v*"],
        capture_output=True, text=True, check=True,
    )
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Assert manifest version == latest release tag.")
    ap.add_argument("--repo", default=".", help="repo directory (default: cwd)")
    ap.add_argument("--tag", help="compare against this exact tag instead of the latest")
    args = ap.parse_args(argv)
    repo = Path(args.repo).resolve()

    try:
        version, manifest = read_manifest_version(repo)
    except (FileNotFoundError, KeyError, ModuleNotFoundError) as e:
        # missing manifest, versionless manifest, or tomllib absent (<3.11)
        print(f"INDETERMINATE: {e}")
        return 2

    if args.tag:
        tag_ver = args.tag[1:] if args.tag.startswith("v") else args.tag
        if tag_ver == version:
            print(f"OK: {manifest} version {version} == tag {args.tag}")
            return 0
        print(f"DRIFT: {manifest} version {version} != tag {args.tag}")
        return 1

    try:
        tags = git_tags(repo)
    except subprocess.CalledProcessError as e:
        print(f"INDETERMINATE: not a git repo or git failed ({e})")
        return 2
    tag = latest_stable_tag(tags)
    if tag is None:
        print(f"DRIFT: {manifest} version {version}, latest stable tag: (none)")
        return 1
    if tag[1:] == version:
        print(f"OK: {manifest} version {version} == latest tag {tag}")
        return 0
    print(f"DRIFT: {manifest} version {version} != latest tag {tag}")
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
