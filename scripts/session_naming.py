"""Session display-name helpers — derive, read, and write session titles.

A *session name* is the human-readable title stored as a ``custom-title``
record in a session JSONL. It is derived from the most recent git commit
subject seen in the session, falling back to the first user message.

Shared by post-save.py, rename-unnamed.py, name-session.py,
mark-session-done.py, migrate-sessions-meta.py, and collect-sessions.py.
This logic was previously copy-pasted across those scripts; extracting it
here removes the duplication and — because the originals lived inside
scripts that run get_scope() at import time — makes it testable.

Scope note: this module owns *session display names* only. The unrelated
TaskWarrior project slug (``domain.repo``) lives in collect-tasks.derive_slug.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# Words too generic to make a useful session name.
SKIP_WORDS = frozenset({
    'session', 'work', 'update', 'changes', 'misc', 'the', 'a', 'an',
    'to', 'and', 'for', 'in', 'of', 'is', 'it', 'this', 'that', 'with',
    'some', 'my', 'your', 'we', 'i',
})

_BRANCH_PREFIX = re.compile(r'^\[(?:main|master)[^\]]*\]\s*')
_CC_PREFIX = re.compile(
    r'^(feat|fix|chore|docs|refactor|test|style|perf|ci|build)[!]?(\([^)]+\))?:\s*'
)
_VERSION_SUFFIX = re.compile(r'\s*\(v[\d.]+\)\s*$')
_SLASH_COMMAND = re.compile(r'^/\S+\s*')


def slug(text: str) -> str:
    """Slugify free text into at most five hyphen-joined keywords."""
    words = re.sub(r'[^a-z0-9\s]', ' ', text.lower()).split()
    words = [w for w in words if w not in SKIP_WORDS and len(w) > 1][:5]
    return '-'.join(words)


def derive_name(commit: str, first_user: str) -> str:
    """Derive a session name from a commit subject, falling back to first user message."""
    if commit:
        m = _BRANCH_PREFIX.match(commit)
        source = commit[m.end():] if m else commit
        source = _CC_PREFIX.sub('', source)
        source = _VERSION_SUFFIX.sub('', source).strip()
        name = slug(source)
        if name:
            return name
    if first_user:
        source = _SLASH_COMMAND.sub('', first_user).strip()
        return slug(source)
    return ''


def extract_context(path: Path) -> tuple[str, str]:
    """Return ``(last_commit_subject, first_user_msg)`` from a session JSONL.

    Scans the first 40 lines for the first user message and the last 600
    lines for the most recent git commit subject — a ``[main ...]`` or
    ``[master ...]`` line emitted inside a commit tool result.
    """
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()

    first_user = ''
    for line in lines[:40]:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if obj.get('type') == 'user':
                content = obj.get('message', {}).get('content', '')
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get('type') == 'text':
                            first_user = c.get('text', '')[:150]
                            break
                elif isinstance(content, str):
                    first_user = content[:150]
                if first_user:
                    break
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

    commit = ''
    for line in reversed(lines[-600:]):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if obj.get('type') == 'assistant':
                for block in obj.get('message', {}).get('content', []):
                    if not isinstance(block, dict):
                        continue
                    if block.get('type') == 'tool_result':
                        for inner in block.get('content', []):
                            if isinstance(inner, dict) and inner.get('type') == 'text':
                                for ln in inner.get('text', '').splitlines():
                                    if ln.startswith('[main') or ln.startswith('[master'):
                                        commit = ln
                                        break
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
        if commit:
            break

    return commit, first_user


def read_title(path: Path) -> str:
    """Return the most recent custom-title for a session JSONL ('' if none/unreadable)."""
    title = ''
    try:
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
            try:
                obj = json.loads(line)
                if obj.get('type') == 'custom-title':
                    title = obj.get('customTitle', '')
            except (json.JSONDecodeError, AttributeError):
                pass
    except OSError:
        pass
    return title


def write_title(path: Path, name: str) -> None:
    """Append a custom-title record naming the session (sessionId = file stem)."""
    record = json.dumps({'type': 'custom-title', 'customTitle': name, 'sessionId': path.stem})
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write(record + '\n')
