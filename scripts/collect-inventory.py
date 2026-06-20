#!/usr/bin/env python3
"""Derive project surface inventory from disk. Never stored; always re-derived.

Output: Commands: N · Agents: N · Hooks: N · Scripts: N
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _count_hook_commands(obj: object) -> int:
    """Recursively count entries with type='command' in hooks.json."""
    if isinstance(obj, dict):
        if obj.get("type") == "command":
            return 1  # command dicts are leaf nodes — do not recurse into their values
        return sum(_count_hook_commands(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(_count_hook_commands(item) for item in obj)
    return 0


def main() -> None:
    commands = len(list(ROOT.glob("commands/*.md")))
    agents = len(list(ROOT.glob("agents/*.md")))
    scripts = len(list(ROOT.glob("scripts/*.py")))

    hooks_path = ROOT / "hooks" / "hooks.json"
    hooks = _count_hook_commands(json.loads(hooks_path.read_text(encoding='utf-8'))) if hooks_path.exists() else 0

    print(f"Commands: {commands} \u00b7 Agents: {agents} \u00b7 Hooks: {hooks} \u00b7 Scripts: {scripts}")


if __name__ == "__main__":
    main()
