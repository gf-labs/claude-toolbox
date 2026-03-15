#!/usr/bin/env python3
"""
Auto-register the claude-toolbox MCP server via `claude mcp add -s user`.

Runs on SessionStart — idempotent, skips silently if already registered.
Uses CLAUDE_TOOLBOX_ROOT to resolve the venv python and server path.
Writes to ~/.claude.json (user scope), available across all projects.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_TOOLBOX_ROOT", Path(__file__).parent.parent))
SERVER_SCRIPT = PLUGIN_ROOT / "mcp_server" / "server.py"
VENV_PYTHON = PLUGIN_ROOT / "mcp_server" / ".venv" / "bin" / "python3"
CLAUDE_JSON = Path.home() / ".claude.json"
SERVER_NAME = "claude-toolbox"


def already_registered() -> bool:
    """Check ~/.claude.json directly — faster than `claude mcp list`."""
    if not CLAUDE_JSON.exists():
        return False
    try:
        data = json.loads(CLAUDE_JSON.read_text(encoding="utf-8"))
        return SERVER_NAME in data.get("mcpServers", {})
    except (json.JSONDecodeError, OSError):
        return False


def main() -> None:
    if already_registered():
        return

    claude = shutil.which("claude")
    if not claude:
        print("[claude-toolbox] 'claude' not found in PATH — skipping MCP setup")
        return

    python_cmd = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"

    try:
        subprocess.run(
            [claude, "mcp", "add", "-s", "user",
             SERVER_NAME, python_cmd, str(SERVER_SCRIPT)],
            check=True, timeout=15,
            capture_output=True,
        )
        print(f"[claude-toolbox] registered MCP server '{SERVER_NAME}' (user scope) → restart Claude Code to activate")
    except subprocess.CalledProcessError as e:
        print(f"[claude-toolbox] failed to register MCP server: {e.stderr.decode().strip()}")


if __name__ == "__main__":
    main()
