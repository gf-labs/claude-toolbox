#!/usr/bin/env python3
"""Persist the /tools:pin --yes-all preference into ~/.claude/settings.json.

Sets env.CLAUDE_TOOLBOX_PIN_YES_ALL = "1", preserving all other settings and
key order. Idempotent. Reads HOME from the environment (via Path.home()), so it
is testable with a fake home. Called by pin.md when --save is passed.
"""
import json
import sys
from pathlib import Path

KEY = 'CLAUDE_TOOLBOX_PIN_YES_ALL'
VALUE = '1'


def main() -> int:
    settings = Path.home() / '.claude' / 'settings.json'
    if settings.exists():
        try:
            data = json.loads(settings.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            print(f'ERROR: {settings} is not valid JSON ({e}); not modifying.', file=sys.stderr)
            return 1
    else:
        settings.parent.mkdir(parents=True, exist_ok=True)
        data = {}

    env = data.setdefault('env', {})
    if not isinstance(env, dict):
        print(f'ERROR: "env" in {settings} is not an object; not modifying.', file=sys.stderr)
        return 1

    env[KEY] = VALUE
    settings.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print(f'Saved: {KEY}={VALUE} (takes effect next session start).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
