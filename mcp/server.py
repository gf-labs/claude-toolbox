#!/usr/bin/env python3
"""
claude-toolbox MCP server

Exposes session data from ~/.claude/ as queryable tools — usable from any
Claude context, not just the current project session.

Quick setup:
  pip install mcp

Configure in .mcp.json (project-local) or ~/.claude/.mcp.json (global):
  {
    "mcpServers": {
      "claude-toolbox": {
        "command": "python3",
        "args": ["/absolute/path/to/claude-toolbox/mcp/server.py"]
      }
    }
  }
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise SystemExit(
        "mcp package not found.\n"
        "Install with: pip install mcp\n"
        "Or: uv add mcp"
    )

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECTS_DIR = Path.home() / ".claude" / "projects"
PLANS_DIR = Path.home() / ".claude" / "plans"

mcp = FastMCP("claude-toolbox")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _session_metadata(jsonl_path: Path) -> dict:
    """Extract title, first user message, and last prompt from a session JSONL."""
    title = ""
    first_user = ""
    last_prompt = ""
    try:
        for line in jsonl_path.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            t = obj.get("type", "")
            if t == "custom-title":
                title = obj.get("customTitle", "")
            if t == "last-prompt" and not last_prompt:
                last_prompt = obj.get("lastPrompt", "")[:120]
            if t == "user" and not first_user:
                msg = obj.get("message", {})
                content = msg.get("content", "") if isinstance(msg, dict) else ""
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            first_user = c.get("text", "")[:120]
                            break
                elif isinstance(content, str):
                    first_user = content[:120]
    except Exception:
        pass
    return {"title": title, "first_user": first_user, "last_prompt": last_prompt}


def _project_display(key: str) -> str:
    """Convert a project key like -Users-foo-Repos-bar to 'bar'."""
    parts = [p for p in key.split("-") if p]
    return parts[-1] if parts else key


def _read_session_log(proj_key: str, n_entries: int = 20) -> str:
    """Return the last n_entries from a project's session-log.md, or empty string."""
    log = PROJECTS_DIR / proj_key / "memory" / "session-log.md"
    if not log.exists():
        return ""
    text = log.read_text(errors="replace")
    blocks = re.split(r"^(## .+)$", text, flags=re.MULTILINE)
    # blocks alternates: [pre-header, header1, body1, header2, body2, ...]
    sections = []
    i = 1
    while i + 1 < len(blocks):
        sections.append(blocks[i] + "\n" + blocks[i + 1])
        i += 2
    return "\n\n".join(sections[-n_entries:])


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def search_sessions(query: str, days: int = 90) -> str:
    """
    Search session history by keyword across all projects.

    Searches session title, first user message, and last prompt. Returns
    matching sessions sorted by recency, limited to the given age window.

    Args:
        query: Keyword or phrase to search for (case-insensitive)
        days:  How far back to search in days (default: 90)
    """
    if not PROJECTS_DIR.exists():
        return json.dumps([])

    cutoff = time.time() - days * 86400
    pattern = query.lower()
    results = []

    for proj in sorted(PROJECTS_DIR.iterdir()):
        if not proj.is_dir():
            continue
        for f in sorted(proj.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                stat = f.stat()
            except Exception:
                continue
            if stat.st_mtime < cutoff:
                continue

            meta = _session_metadata(f)
            searchable = (
                meta["title"] + " " + meta["first_user"] + " " + meta["last_prompt"]
            ).lower()
            if pattern not in searchable:
                continue

            age_days = int((time.time() - stat.st_mtime) / 86400)
            size_k = stat.st_size // 1024
            results.append({
                "session_id": f.stem[:8],
                "title": meta["title"] or meta["first_user"][:60] or "(untitled)",
                "project": _project_display(proj.name),
                "age_days": age_days,
                "size_k": size_k,
            })

    results.sort(key=lambda r: r["age_days"])
    return json.dumps(results, indent=2)


@mcp.tool()
def list_plans() -> str:
    """
    List all active plans with title, project attribution, and line count.

    Reads ~/.claude/plans/*.md and cross-references .project-map for project
    attribution. Returns a JSON array of plan objects.
    """
    if not PLANS_DIR.exists():
        return json.dumps([])

    plan_files = sorted(PLANS_DIR.glob("*.md"))
    if not plan_files:
        return json.dumps([])

    # Load project attribution from ## Plans section of .project-map
    plan_map: dict[str, str] = {}
    cache = PLANS_DIR / ".project-map"
    if cache.exists():
        in_plans = False
        current_plan = ""
        for line in cache.read_text().splitlines():
            if line.strip() == "## Plans":
                in_plans = True
                continue
            if in_plans and line.startswith("## ") and line.strip() != "## Plans":
                break
            if not in_plans:
                continue
            if line.startswith("### "):
                current_plan = line[4:].strip()
            elif current_plan and line.startswith("- Created: "):
                created = line[11:].strip()
                if "(" in created and created.endswith(")"):
                    plan_map[current_plan] = created[created.rfind("(") + 1 : -1]

    results = []
    for f in plan_files:
        try:
            text = f.read_text(errors="replace")
            lines = text.splitlines()
            title = ""
            past_frontmatter = False
            for line in lines:
                if line.strip() == "---":
                    past_frontmatter = not past_frontmatter
                    continue
                if not title and line.startswith("# "):
                    title = line[2:].strip()
                    break
            results.append({
                "filename": f.name,
                "title": title or f.stem,
                "project": plan_map.get(f.name, "unknown"),
                "line_count": len(lines),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d"),
            })
        except Exception:
            continue

    return json.dumps(results, indent=2)


@mcp.tool()
def get_session_log(project: str = "") -> str:
    """
    Read session log entries for a project.

    Finds the matching project by name and returns the last 20 session log
    entries from its session-log.md. If project is empty, returns logs for
    all projects with a non-empty session log.

    Args:
        project: Project name (e.g. 'claude-toolbox', 'ramp'). Leave empty
                 to list available projects.
    """
    if not PROJECTS_DIR.exists():
        return "No projects directory found."

    # Build project-name → key mapping
    proj_map: dict[str, str] = {}
    for d in PROJECTS_DIR.iterdir():
        if d.is_dir():
            name = _project_display(d.name)
            proj_map[name] = d.name

    if not project:
        available = [
            name for name, key in sorted(proj_map.items())
            if (PROJECTS_DIR / key / "memory" / "session-log.md").exists()
        ]
        if not available:
            return "No session logs found."
        return "Available projects:\n" + "\n".join(f"  - {p}" for p in available)

    # Find best match (exact, then prefix, then substring)
    key = proj_map.get(project)
    if not key:
        candidates = [k for n, k in proj_map.items() if project.lower() in n.lower()]
        if not candidates:
            available = sorted(proj_map.keys())
            return f"Project '{project}' not found. Available: {', '.join(available)}"
        key = candidates[0]

    log_text = _read_session_log(key)
    if not log_text:
        return f"No session log found for project '{project}'."

    project_name = _project_display(key)
    return f"# {project_name} — session log (last 20 entries)\n\n{log_text}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
