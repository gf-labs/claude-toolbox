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
TaskWarrior project slug lives in _slug.derive_slug (imported by collect-tasks).
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


def write_title(path: Path, name: str, *, force: bool = False) -> bool:
    """Append a custom-title record naming the session (sessionId = file stem).

    Idempotent: if the session's current effective title already equals ``name``,
    this is a no-op and returns ``False`` (unless ``force`` is given). This is what
    stops title write-amplification — repeated naming with an unchanged value no
    longer appends a redundant record. Returns ``True`` when a record was written.
    """
    if not force and read_title(path) == name:
        return False
    record = json.dumps({'type': 'custom-title', 'customTitle': name, 'sessionId': path.stem})
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write(record + '\n')
    return True


# A stale-fork marker is the base title plus a `~MM-DD` suffix (the date the fork
# went stale), optionally disambiguated with a short session-id: `name~06-27` or
# `name~06-27-1a2b`.
STALE_SUFFIX_RE = re.compile(r'~\d{2}-\d{2}(?:-[0-9a-f]{4})?$')


def base_title(title: str) -> str:
    """Strip a `~MM-DD[-sid]` stale-fork suffix to recover the canonical base title."""
    return STALE_SUFFIX_RE.sub('', title)


def scan_title_and_ts(path: Path) -> tuple[str, str]:
    """Single-pass read returning ``(effective_title, last_event_timestamp)``.

    The effective title is the *last* ``custom-title`` record; the timestamp is the
    last ISO ``timestamp`` seen on any event line. One scan instead of two — these
    session files can be tens of MB.
    """
    title = ''
    ts = ''
    try:
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
            if 'custom-title' in line and '"type"' in line:
                try:
                    obj = json.loads(line)
                    if obj.get('type') == 'custom-title':
                        title = obj.get('customTitle', '')
                        continue
                except json.JSONDecodeError:
                    pass
            if '"timestamp"' in line:
                try:
                    obj = json.loads(line)
                    t = obj.get('timestamp')
                    if t:
                        ts = t
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return title, ts


def plan_fork_relabels(proj_dir: Path) -> list[dict]:
    """Return relabel actions that disambiguate same-named session forks.

    Within a project, named sessions sharing a *base* title are forks of one
    logical session — Claude Code's /resume picker shows them identically and
    renames them as a group (compact-chain). Per-file titles, however, are read
    independently, so writing distinct titles to the files disambiguates them.

    The newest session by last-event timestamp (NOT file mtime — any write,
    including a relabel, perturbs mtime) keeps the clean base title; older forks
    get a ``base~MM-DD`` marker. Only entries whose current title differs from the
    proposed one are returned, so this is idempotent across runs.

    Each action: ``{path, sid, current, proposed, last_event, reason}``.
    """
    from collections import defaultdict

    sessions = []
    for f in proj_dir.glob('*.jsonl'):
        title, ts = scan_title_and_ts(f)
        if not title:
            continue  # unnamed sessions are post-save's job, not the relabeler's
        sessions.append({'path': f, 'sid': f.stem, 'title': title,
                         'base': base_title(title), 'ts': ts})

    groups: dict[str, list] = defaultdict(list)
    for s in sessions:
        groups[s['base']].append(s)

    actions = []
    for base, members in groups.items():
        if len(members) < 2:
            continue  # no collision → nothing to disambiguate
        members.sort(key=lambda s: s['ts'], reverse=True)  # newest last-event first
        live, stale = members[0], members[1:]

        if live['title'] != base:
            actions.append({'path': live['path'], 'sid': live['sid'][:8],
                            'current': live['title'], 'proposed': base,
                            'last_event': live['ts'][:10],
                            'reason': 'live fork (newest activity) → clean name'})

        used = {base}
        for s in stale:
            date = s['ts'][:10] if s['ts'] else ''
            mmdd = date[5:] if date else 'old'
            proposed = f'{base}~{mmdd}'
            if proposed in used:  # two stale forks same date → add a sid tiebreaker
                proposed = f'{base}~{mmdd}-{s["sid"][:4]}'
            used.add(proposed)
            if s['title'] != proposed:
                actions.append({'path': s['path'], 'sid': s['sid'][:8],
                                'current': s['title'], 'proposed': proposed,
                                'last_event': date or 'unknown',
                                'reason': f'stale fork (last active {date or "unknown"})'})
    return actions
