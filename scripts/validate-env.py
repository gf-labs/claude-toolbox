#!/usr/bin/env python3
"""SessionStart hook — validates CLAUDE_TOOLBOX_ROOT and RAMP_ROOT are set and real."""
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

ramp_root = os.environ.get('RAMP_ROOT', '')
if not ramp_root:
    print('⚠ RAMP_ROOT is not set — /ramp:* hooks may fail.', file=sys.stderr)
elif not Path(ramp_root).is_dir():
    print(f'⚠ RAMP_ROOT={ramp_root!r} does not exist — /ramp:* hooks may fail.', file=sys.stderr)

# Ensure data-policy.json is in place for tools plugin
_plugin_root = Path(__file__).parent.parent
_policy_src = _plugin_root / 'data-policy.json'
_policy_dst = Path.home() / '.claude' / 'data' / 'tools' / 'data-policy.json'
if _policy_src.exists() and not _policy_dst.exists():
    _policy_dst.parent.mkdir(parents=True, exist_ok=True)
    import shutil as _shutil
    _shutil.copy2(_policy_src, _policy_dst)
