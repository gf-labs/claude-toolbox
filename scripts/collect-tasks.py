#!/usr/bin/env python3
"""collect-tasks.py — scan one or all repos for un-migrated work items; emit JSON manifest."""

import argparse
import json
import re
import subprocess
import sys
import uuid
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path

SKIP_SECTIONS = {"done", "completed", "shipped", "archived", "history",
                 "changelog", "released", "removed", "superseded"}

PLANNING_HEADINGS = {"backlog", "todo", "planned", "up next", "active",
                     "queued", "later", "deferred", "in progress", "next"}

DISCOVER_SKIP_DIRS = {"_archive", "__unsorted__", "archive", ".git",
                      "node_modules", ".venv", "dist", "build"}

DOCS_SKIP_DIRS = {"superpowers", "standards"}

DISCOVER_MAX_DEPTH = 2

ROOT_TRACKING_FILES = ["BACKLOG.md", "TODO.md", "ROADMAP.md", "INITIATIVES.md"]

TOMBSTONE_PREFIX = "Tasks tracked in TaskWarrior"

TAG_KEYWORDS: dict[str, set[str]] = {
    "bug": {"bug", "fix", "error", "broken"},
    "command": {"command"},
    "agent": {"agent"},
    "hook": {"hook"},
    "pipeline": {"pipeline"},
    "infra": {"mcp", "server", "infra", "architecture", "kuzu", "ast"},
    "research": {"research", "review", "read", "investigate"},
}

SIZE_KEYWORDS: dict[str, set[str]] = {
    "XS": {"trivial", "typo", "rename", "one-line"},
    "S": {"small", "focused", "quick"},
    "M": {"refactor", "multi-part", "several"},
    "L": {"large", "unknown", "architecture", "overhaul"},
}

COMPLETION_MARKERS = {"~~", "**done", "**completed", "**shipped", "**removed",
                      "**superseded", "**retired", "**cancelled", "**redundant"}


def derive_slug(repo_path: Path, repos_root: Path | None = None) -> str:
    """Derive TW project slug from repo path under ~/Repos."""
    if repos_root is None:
        repos_root = Path.home() / "Repos"
    try:
        rel = repo_path.resolve().relative_to(repos_root.resolve())
        parts = list(rel.parts)
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        if len(parts) == 1:
            return parts[0]
    except ValueError:
        pass
    return repo_path.name


def is_tombstoned(file_path: Path) -> bool:
    """Return True if file contains only the tombstone line."""
    try:
        return file_path.read_text().strip().startswith(TOMBSTONE_PREFIX)
    except OSError:
        return False


def load_tw_slugs(repo_path: Path) -> dict:
    """Load .tw-slugs.json from repo root; return empty dict if absent or malformed."""
    config_path = repo_path / ".tw-slugs.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def get_exclude_patterns(tw_slugs: dict) -> list[str]:
    """Extract exclude patterns from .tw-slugs.json (under the 'exclude' key)."""
    excl = tw_slugs.get("exclude", [])
    return excl if isinstance(excl, list) else []


def match_slug(file_path: Path, repo_path: Path, tw_slugs: dict, default_slug: str) -> str:
    """Match file against .tw-slugs.json glob patterns; first match wins; else default."""
    try:
        rel = str(file_path.resolve().relative_to(repo_path.resolve()))
    except ValueError:
        return default_slug
    for pattern, slug in tw_slugs.items():
        if pattern == "exclude":
            continue
        if fnmatch(rel, pattern):
            return slug
    return default_slug


def infer_tag(description: str) -> str:
    """Infer TaskWarrior tag from description keywords."""
    lower = description.lower()
    for tag, keywords in TAG_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return tag
    return "task"


def infer_size(description: str) -> str:
    """Infer task size (XS/S/M/L) from description keywords."""
    lower = description.lower()
    for size, keywords in SIZE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return size
    return "S"


def parse_sections(text: str) -> list[dict]:
    """Split markdown text into heading-delimited sections.

    Returns list of dicts: {heading: str|None, level: int, lines: list[str]}.
    The first section (before any heading) has heading=None.
    Headings inside fenced code blocks (``` or ~~~) are ignored.
    """
    sections: list[dict] = []
    current: dict = {"heading": None, "level": 0, "lines": []}
    in_fence = False

    for line in text.splitlines():
        if re.match(r'^(`{3,}|~{3,})', line):
            in_fence = not in_fence
            current["lines"].append(line)
            continue
        if in_fence:
            current["lines"].append(line)
            continue
        m = re.match(r'^(#{1,6})\s+(.+)', line)
        if m:
            sections.append(current)
            current = {
                "heading": m.group(2).strip(),
                "level": len(m.group(1)),
                "lines": [],
            }
        else:
            current["lines"].append(line)

    sections.append(current)
    return sections


def is_skip_section(heading: str | None) -> bool:
    """Return True if section heading indicates completed/archived content."""
    if heading is None:
        return False
    lower = heading.lower()
    return any(skip in lower for skip in SKIP_SECTIONS)


def has_planning_heading(text: str) -> bool:
    """Return True if text contains at least one heading matching a planning keyword.

    Ignores headings inside fenced code blocks (``` or ~~~).
    """
    in_fence = False
    for line in text.splitlines():
        if re.match(r'^(`{3,}|~{3,})', line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r'^#{1,6}\s+(.+)', line)
        if m and any(ph in m.group(1).strip().lower() for ph in PLANNING_HEADINGS):
            return True
    return False


def extract_items_from_lines(lines: list[str], checkboxes_only: bool = False) -> list[str]:
    """Extract unchecked checklist items and (optionally) non-completion bare list items.

    checkboxes_only=True: only `- [ ]` items are extracted (bare bullets ignored).
    Used for docs/ files where bare bullets are typically prose, not tasks.
    """
    items = []
    for line in lines:
        s = line.strip()
        # Unchecked checklist: - [ ] text
        m = re.match(r'^-\s+\[\s+\]\s+(.+)', s)
        if m:
            items.append(m.group(1).strip())
            continue
        # Checked checklist: skip
        if re.match(r'^-\s+\[x\]', s, re.IGNORECASE):
            continue
        if checkboxes_only:
            continue
        # Bare list item: - text (skip if completion marker)
        m = re.match(r'^-\s+(.+)', s)
        if m:
            text = m.group(1).strip()
            lower = text.lower()
            if not any(lower.startswith(marker) for marker in COMPLETION_MARKERS):
                items.append(text)
    return items


def find_tracking_files(repo_path: Path) -> list[Path]:
    """Return all candidate tracking files in a repo (non-tombstoned)."""
    candidates: list[Path] = []

    # Root-level standard files
    for name in ROOT_TRACKING_FILES:
        f = repo_path / name
        if f.exists() and not is_tombstoned(f):
            candidates.append(f)

    # README.md if it contains a planning heading
    readme = repo_path / "README.md"
    if readme.exists() and readme not in candidates and not is_tombstoned(readme):
        try:
            if has_planning_heading(readme.read_text()):
                candidates.append(readme)
        except OSError:
            pass

    # Recursive docs/ scan
    exclude_patterns = get_exclude_patterns(load_tw_slugs(repo_path))
    docs_dir = repo_path / "docs"
    if docs_dir.is_dir():
        resolved_candidates = {c.resolve() for c in candidates}
        for f in sorted(docs_dir.rglob("*.md")):
            try:
                rel_parts = f.relative_to(docs_dir).parts[:-1]
            except ValueError:
                rel_parts = ()
            if any(part in DOCS_SKIP_DIRS for part in rel_parts):
                continue
            try:
                rel_str = str(f.relative_to(repo_path))
            except ValueError:
                rel_str = str(f)
            if any(fnmatch(rel_str, pat) for pat in exclude_patterns):
                continue
            if f.resolve() in resolved_candidates or is_tombstoned(f):
                continue
            try:
                if has_planning_heading(f.read_text()):
                    candidates.append(f)
                    resolved_candidates.add(f.resolve())
            except OSError:
                pass

    return candidates


def collect_markdown_items(
    file_path: Path,
    repo_path: Path,
    tw_slugs: dict,
    default_slug: str,
) -> list[dict]:
    """Extract all proposed items from a single tracking file."""
    try:
        text = file_path.read_text()
    except OSError:
        return []

    slug = match_slug(file_path, repo_path, tw_slugs, default_slug)
    try:
        source_rel = str(file_path.relative_to(repo_path))
    except ValueError:
        source_rel = str(file_path)
    # docs/ files use checkboxes_only — bare bullets are typically prose, not tasks
    checkboxes_only = source_rel.startswith("docs/")
    items = []

    skip_level: int | None = None  # level of the active skip heading, or None
    for section in parse_sections(text):
        level = section["level"]
        heading = section["heading"]
        # Clear skip when we move to a sibling or ancestor heading
        if heading is not None and skip_level is not None and level <= skip_level:
            skip_level = None
        # Enter skip mode when we hit a skip-marked heading
        if is_skip_section(heading):
            skip_level = level
        if skip_level is not None:
            continue
        for description in extract_items_from_lines(section["lines"], checkboxes_only):
            items.append({
                "id": str(uuid.uuid4()),
                "description": description,
                "source_file": source_rel,
                "source_type": "markdown",
                "line": None,
                "section": section["heading"],
                "inferred_slug": slug,
                "inferred_tag": infer_tag(description),
                "inferred_size": infer_size(description),
                "github_url": None,
                "status": "proposed",
            })

    return items


def collect_code_comments(repo_path: Path, default_slug: str) -> list[dict]:
    """Scan for TODO/FIXME/HACK/XXX using rg. Returns empty list if rg unavailable."""
    try:
        result = subprocess.run(
            [
                "rg", "TODO|FIXME|HACK|XXX", "--line-number",
                "--glob", "!.git", "--glob", "!node_modules",
                "--glob", "!*.lock", "--glob", "!*.min.js", "--glob", "!*.min.css",
                "--glob", "!*.md",
            ],
            capture_output=True, text=True, cwd=repo_path,
        )
    except FileNotFoundError:
        return []

    if result.returncode == 2:
        return []

    items = []
    for line in result.stdout.splitlines():
        m = re.match(r'^([^:]+):(\d+):(.+)', line)
        if not m:
            continue
        file_rel, lineno, content = m.group(1), int(m.group(2)), m.group(3).strip()
        comment_m = re.search(r'(?:TODO|FIXME|HACK|XXX)[:\s]+(.+)', content, re.IGNORECASE)
        description = comment_m.group(1).strip() if comment_m else content
        is_fixme = "FIXME" in content.upper()
        items.append({
            "id": str(uuid.uuid4()),
            "description": description,
            "source_file": file_rel,
            "source_type": "code",
            "line": lineno,
            "section": None,
            "inferred_slug": default_slug,
            "inferred_tag": "bug" if is_fixme else "task",
            "inferred_size": "XS",
            "github_url": None,
            "status": "proposed",
        })
    return items


def collect_github_issues(repo_path: Path, default_slug: str) -> list[dict]:
    """Fetch open GitHub issues via gh. Returns empty list if gh unavailable."""
    try:
        result = subprocess.run(
            ["gh", "issue", "list", "--state", "open", "--json", "number,title,labels"],
            capture_output=True, text=True, cwd=repo_path,
        )
        if result.returncode != 0:
            return []
        issues = json.loads(result.stdout)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    return [
        {
            "id": str(uuid.uuid4()),
            "description": issue["title"],
            "source_file": None,
            "source_type": "github",
            "line": None,
            "section": None,
            "inferred_slug": default_slug,
            "inferred_tag": infer_tag(issue["title"]),
            "inferred_size": infer_size(issue["title"]),
            "github_url": f"#{issue['number']}",
            "status": "proposed",
        }
        for issue in issues
    ]


def find_git_repos(root: Path) -> list[Path]:
    """Walk root up to DISCOVER_MAX_DEPTH, returning dirs containing .git."""
    repos: list[Path] = []

    def walk(path: Path, depth: int) -> None:
        if (path / ".git").exists():
            repos.append(path)
            return  # don't recurse into sub-repos
        if depth <= 0:
            return
        try:
            for child in sorted(path.iterdir()):
                if child.is_dir() and child.name not in DISCOVER_SKIP_DIRS:
                    walk(child, depth - 1)
        except PermissionError:
            pass

    walk(root, DISCOVER_MAX_DEPTH)
    return repos


def collect_repo(repo_path: Path) -> dict:
    """Collect all items from a single repo; return manifest repo entry."""
    default_slug = derive_slug(repo_path)
    tw_slugs = load_tw_slugs(repo_path)
    tracking_files = find_tracking_files(repo_path)

    items: list[dict] = []
    tombstone_candidates: list[str] = []
    files_with_no_slug_mapping: list[str] = []

    for f in tracking_files:
        try:
            rel = str(f.relative_to(repo_path))
        except ValueError:
            rel = str(f)
        # Flag docs/ files with no sub-slug entry when .tw-slugs.json exists
        if tw_slugs and rel.startswith("docs/"):
            if not any(fnmatch(rel, pat) for pat in tw_slugs if pat != "exclude"):
                files_with_no_slug_mapping.append(rel)

        file_items = collect_markdown_items(f, repo_path, tw_slugs, default_slug)
        if file_items:
            items.extend(file_items)
            tombstone_candidates.append(rel)

    items.extend(collect_code_comments(repo_path, default_slug))
    items.extend(collect_github_issues(repo_path, default_slug))

    return {
        "path": str(repo_path),
        "slug": default_slug,
        "tw_slugs_present": bool(tw_slugs),
        "items": items,
        "tombstone_candidates": tombstone_candidates,
        "files_with_no_slug_mapping": files_with_no_slug_mapping,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--discover", nargs="?",
        const=str(Path.home() / "Repos"),
        metavar="PATH",
        help="Walk all git repos under PATH (default: ~/Repos)",
    )
    args = parser.parse_args()

    if args.discover:
        root = Path(args.discover).expanduser().resolve()
        if not root.is_dir():
            print(f"ERROR: {root} is not a directory", file=sys.stderr)
            sys.exit(1)
        repos = find_git_repos(root)
        mode = "discover"
    else:
        cwd = Path.cwd().resolve()
        if not (cwd / ".git").exists():
            print(
                f"ERROR: {cwd} is not a git repo. Use --discover to walk a directory.",
                file=sys.stderr,
            )
            sys.exit(1)
        repos = [cwd]
        mode = "repo"

    manifest = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "repos": [collect_repo(r) for r in repos],
    }
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
