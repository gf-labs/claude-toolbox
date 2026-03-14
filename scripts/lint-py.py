#!/usr/bin/env python3
"""PostToolUse hook — lint any .py file touched by Edit or Write."""
import json
import subprocess
import sys
from pathlib import Path

try:
    event = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)

file_path = event.get('tool_input', {}).get('file_path', '')

if not file_path or not file_path.endswith('.py'):
    sys.exit(0)

path = Path(file_path)
if not path.exists():
    sys.exit(0)

issues = []

# Syntax check
result = subprocess.run(
    [sys.executable, '-m', 'py_compile', str(path)],
    capture_output=True, text=True
)
if result.returncode != 0:
    issues.append(f'SYNTAX:\n{result.stderr.strip()}')

# Ruff lint
try:
    result = subprocess.run(
        ['ruff', 'check', '--quiet', str(path)],
        capture_output=True, text=True
    )
    if result.returncode != 0 and result.stdout.strip():
        issues.append(f'RUFF:\n{result.stdout.strip()}')
except FileNotFoundError:
    pass  # ruff not installed

if issues:
    print(f'⚠ lint-py [{path.name}]')
    for issue in issues:
        print(issue)
