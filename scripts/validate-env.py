#!/usr/bin/env python3
"""SessionStart hook — validates CLAUDE_TOOLBOX_ROOT is set and points to a real dir."""
import os
import sys
from pathlib import Path

root = os.environ.get('CLAUDE_TOOLBOX_ROOT', '')

if not root:
    print('⚠ CLAUDE_TOOLBOX_ROOT is not set — /tools:* commands may not work correctly.', file=sys.stderr)
    sys.exit(1)

if not Path(root).is_dir():
    print(f'⚠ CLAUDE_TOOLBOX_ROOT={root!r} does not exist — /tools:* commands may not work correctly.', file=sys.stderr)
    sys.exit(1)
