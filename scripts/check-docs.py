#!/usr/bin/env python3
"""Docs-consistency gate: README agents/hooks tables, LIBRARY.md counts, links.

Checks (mechanical only):
  1. README "## Agents" rows ↔ agents/*.md (both directions).
  2. README "## Hooks" script names == hooks/hooks.json command basenames (set equality),
     and every referenced script exists in scripts/.
  3. LIBRARY.md's bold summary line — commands/skills/agents/hook-handlers/scripts counts
     — matches the filesystem. The MCP-tools count is NOT checked: mcp_server/server.py
     has no static marker worth coupling a regex to; it is re-verified at release per
     CONTRIBUTING's checklist.
  4. Relative links in README.md resolve.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def section(text, heading):
    m = re.search(r"^" + re.escape(heading) + r"\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def hook_commands(repo):
    data = json.loads((repo / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    names = []
    for entries in data.get("hooks", {}).values():
        for entry in entries:
            for h in entry.get("hooks", []):
                if h.get("type") == "command":
                    script = h["command"].split()[1] if len(h["command"].split()) > 1 else h["command"]
                    names.append(Path(script).name)
    return names


def check_agents(repo, readme, problems):
    rows = set(re.findall(r"^\|\s*`([a-z-]+)`", section(readme, "## Agents"), re.M))
    files = {p.stem for p in (repo / "agents").glob("*.md")}
    for name in sorted(files - rows):
        problems.append(f"agent file with no README row: agents/{name}.md")
    for name in sorted(rows - files):
        problems.append(f"README agent row with no file: {name}")


def check_hooks(repo, readme, problems):
    handlers = hook_commands(repo)
    table_scripts = set(re.findall(r"`([a-z\-]+\.py)`", section(readme, "## Hooks")))
    for name in sorted(set(handlers) - table_scripts):
        problems.append(f"hook handler with no README Hooks row: {name}")
    for name in sorted(table_scripts - set(handlers)):
        problems.append(f"README Hooks row with no hooks.json handler: {name}")
    for name in set(handlers):
        if not (repo / "scripts" / name).exists():
            problems.append(f"hooks.json references a missing script: scripts/{name}")


def check_library_counts(repo, problems):
    lib = (repo / "LIBRARY.md").read_text(encoding="utf-8")
    m = re.search(r"\*\*(\d+) commands · (\d+) skills · (\d+) agents · (\d+) MCP tools"
                  r" · (\d+) hook handlers · (\d+) scripts\*\*", lib)
    if not m:
        problems.append("LIBRARY.md summary line not found / format changed")
        return
    actual = {
        "commands": len(list((repo / "commands").glob("*.md"))),
        "skills": len(list((repo / "skills").glob("*/SKILL.md"))),
        "agents": len(list((repo / "agents").glob("*.md"))),
        "hook handlers": len(hook_commands(repo)),
        "scripts": len(list((repo / "scripts").glob("*.py"))),
    }
    claimed = {
        "commands": int(m.group(1)), "skills": int(m.group(2)), "agents": int(m.group(3)),
        "hook handlers": int(m.group(5)), "scripts": int(m.group(6)),
    }
    for key, want in actual.items():
        if claimed[key] != want:
            problems.append(f"LIBRARY.md says {claimed[key]} {key}; the tree has {want}")


def check_links(repo, problems):
    text = (repo / "README.md").read_text(encoding="utf-8")
    for target in re.findall(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)", text):
        path = target.split("#")[0]
        if path and not (repo / path).exists():
            problems.append(f"README.md links to a missing path: {target}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".")
    repo = Path(ap.parse_args().repo).resolve()
    readme = (repo / "README.md").read_text(encoding="utf-8")

    problems = []
    check_agents(repo, readme, problems)
    check_hooks(repo, readme, problems)
    check_library_counts(repo, problems)
    check_links(repo, problems)

    if problems:
        print(f"check-docs: {len(problems)} problem(s)")
        for p in problems:
            print("  - " + p)
        return 1
    print("check-docs: OK (agents, hooks, LIBRARY counts, links)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
