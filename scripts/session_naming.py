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

# A git commit echo is "[<branch> <hash>] <subject>" for any branch, not just
# main/master (git-flow commits land on feature/*). _BRANCH_PREFIX strips the
# bracket in derive_name; _COMMIT_ECHO spots the echo line in a tool result.
_BRANCH_PREFIX = re.compile(r'^\[[^\]]+\]\s*')
_COMMIT_ECHO = re.compile(r'^\[\S+ [0-9a-f]{7,40}\] +\S')
_CC_PREFIX = re.compile(
    r'^(feat|fix|chore|docs|refactor|test|style|perf|ci|build)[!]?(\([^)]+\))?:\s*'
)
_VERSION_SUFFIX = re.compile(r'\s*\(v[\d.]+\)\s*$')
_SLASH_COMMAND = re.compile(r'^/\S+\s*')

# A session can open with harness preamble instead of a typed message: the
# scaffolding a slash command emits, the local-command caveat and its stdout, a
# system reminder, or the summary that opens a continued session. Naming a
# session after any of these produces junk (gfl-marketplace once had two named
# "local-command-caveat-caveat-messages"), so extract_context skips them and
# uses the first message the user actually wrote.
_PREAMBLE_PREFIXES = (
    '<local-command-caveat>', '<command-name>', '<command-message>',
    '<command-args>', '<local-command-stdout>', '<system-reminder>',
)
_CONTINUATION_PREFIX = 'This session is being continued'


def _is_preamble(text: str) -> bool:
    """True when a first-message candidate is harness preamble, not authored."""
    t = text.lstrip()
    return t.startswith(_PREAMBLE_PREFIXES) or t.startswith(_CONTINUATION_PREFIX)


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

    Scans the first 40 lines for the first user-authored message — skipping
    harness preamble (command scaffolding, the local-command caveat/stdout,
    system reminders, ``isMeta`` records, and the summary that opens a
    continued session) — and the last 600 lines for the most recent git commit
    subject: a ``[<branch> <hash>] <subject>`` echo emitted inside a commit
    tool result, for any branch (git-flow commits land on feature/*), not just
    main/master. The echo must carry a subject, so a bare ``[develop <sha>]``
    git-log listing line is ignored.
    """
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()

    first_user = ''
    for line in lines[:40]:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if obj.get('type') != 'user' or obj.get('isMeta'):
                continue  # isMeta records are harness preamble, not authored
            content = obj.get('message', {}).get('content', '')
            text = ''
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get('type') == 'text':
                        text = c.get('text', '')
                        break
            elif isinstance(content, str):
                text = content
            if not text or _is_preamble(text):
                continue
            first_user = text[:150]
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
                                    if _COMMIT_ECHO.match(ln):
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


# Titles that read as auto-derived junk rather than a real session name: a
# throwaway ``*-scratch-*`` name, or — before extract_context learned to skip it
# — a slug of harness preamble (the local-command caveat, its stdout, a system
# reminder). post-save may re-derive over one of these; it must never overwrite a
# real name, so the marker list stays deliberately narrow (distinctive phrases,
# not generic words like "command").
_JUNK_TITLE_MARKERS = (
    'scratch',
    'local-command-caveat',
    'local-command-stdout',
    'caveat-messages',
    'system-reminder',
)


def is_junk_title(title: str) -> bool:
    """True when ``title`` looks auto-derived from junk, not real content.

    Matched case-insensitively as a substring of the slug, so a ``~MM-DD``
    stale-fork suffix can't hide a marker. An empty title is *not* junk — that
    means unnamed, which callers handle separately. The session registry's
    ``keep`` status is the escape hatch for an intentional name that happens to
    match a marker.
    """
    return any(marker in title.lower() for marker in _JUNK_TITLE_MARKERS)


def scan_session(path: Path) -> tuple[str, str, bool]:
    """Single-pass read returning ``(effective_title, last_event_timestamp, is_bg)``.

    The effective title is the *last* ``custom-title`` record; the timestamp is
    the last ISO ``timestamp`` on a non-injected event line. One scan instead of
    two — these session files can be tens of MB.

    ``isMeta: true`` records never advance the timestamp. They are synthetic
    turns — skill bodies, command caveats, the post-compact continue prompt, and
    the rename echo Claude Code writes into *other* sessions of a compact-chain
    group. That echo lands milliseconds after the rename you typed, in a file
    you are not in, so counting it as activity made ``plan_fork_relabels`` crown
    the wrong fork (2026-09-04: a 1 MB leftover out-ranked the live 30 MB
    session on echoes alone). Genuine human turns carry no ``isMeta`` key at
    all. The gate applies to every caller on purpose: via ``scan_title_and_ts``
    it also makes the atlas sessions facet's "last activity" mean last *real*
    activity.

    ``is_bg`` is True when *every* event record carries ``sessionKind: 'bg'`` — the
    file belongs to a background job, not an interactive session. Presence of some
    bg records is not enough: an interactive session's file can accumulate bg-kind
    events mid-stream, so only an all-bg file counts.
    """
    title = ''
    ts = ''
    saw_event = False
    saw_non_bg = False
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
                        saw_event = True
                        if obj.get('sessionKind') != 'bg':
                            saw_non_bg = True
                        if not obj.get('isMeta'):  # injected turn — not activity
                            ts = t
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return title, ts, saw_event and not saw_non_bg


def scan_title_and_ts(path: Path) -> tuple[str, str]:
    """``scan_session`` without the bg flag — kept for existing callers."""
    title, ts, _ = scan_session(path)
    return title, ts


def plan_fork_relabels(proj_dir: Path) -> list[dict]:
    """Return relabel actions that disambiguate same-named session forks.

    Within a project, named sessions sharing a *base* title are forks of one
    logical session — Claude Code's /resume picker shows them identically and
    renames them as a group (compact-chain). Per-file titles, however, are read
    independently, so writing distinct titles to the files disambiguates them.

    The newest session by last-event timestamp (NOT file mtime — any write,
    including a relabel, perturbs mtime) keeps the clean base title; older forks
    get a ``base~MM-DD`` marker, or ``base~MM-DD-sid`` when two or more stale
    forks share a date. Only entries whose current title differs from the
    proposed one are returned, so this is idempotent across runs.

    Every proposed name is a pure function of (base, that session's own date,
    that session's own sid) — never of a session's *position* among its peers.
    That is what makes it stable: relative ``ts`` order between two stale forks
    changes whenever either is touched, so any name derived from that order
    ping-pongs on every run.

    Each action: ``{path, sid, current, proposed, last_event, reason}``.
    """
    from collections import defaultdict

    sessions = []
    for f in proj_dir.glob('*.jsonl'):
        title, ts, is_bg = scan_session(f)
        if not title:
            continue  # unnamed sessions are post-save's job, not the relabeler's
        sessions.append({'path': f, 'sid': f.stem, 'title': title,
                         'base': base_title(title), 'ts': ts, 'bg': is_bg})

    groups: dict[str, list] = defaultdict(list)
    for s in sessions:
        groups[s['base']].append(s)

    actions = []
    for base, members in groups.items():
        if len(members) < 2:
            continue  # no collision → nothing to disambiguate
        # Background-job sessions inherit the parent's title and always have
        # fresh events — they must never claim the clean name (2026-07-02
        # regression: a bg job demoted the real session to a stale marker).
        interactive = [s for s in members if not s['bg']]
        if not interactive:
            continue  # nothing to protect — leave bg-only groups alone
        members.sort(key=lambda s: (not s['bg'], s['ts']), reverse=True)
        live = max(interactive, key=lambda s: s['ts'])
        stale = [s for s in members if s is not live]

        if live['title'] != base:
            actions.append({'path': live['path'], 'sid': live['sid'][:8],
                            'current': live['title'], 'proposed': base,
                            'last_event': live['ts'][:10],
                            'reason': 'live fork (newest activity) → clean name'})

        # Same-date stale forks: EVERY member of a colliding date gets the sid
        # suffix, not just the ones after the first. Giving the bare `~MM-DD` to
        # "whichever sorted first" made the suffix depend on `ts` ordering
        # *between two stale forks* — an ordering that flips whenever either one
        # is touched, swapping their names back and forth on every run for no
        # reason. Nothing above the group had changed; only their order had.
        # A whole date group is symmetric, so there is no ordering left to flip.
        by_date: dict[str, list] = defaultdict(list)
        for s in stale:
            by_date[s['ts'][:10] if s['ts'] else ''].append(s)

        for s in stale:
            date = s['ts'][:10] if s['ts'] else ''
            mmdd = date[5:] if date else 'old'
            proposed = f'{base}~{mmdd}'
            if len(by_date[date]) > 1:
                proposed = f'{base}~{mmdd}-{s["sid"][:4]}'
            if s['title'] != proposed:
                actions.append({'path': s['path'], 'sid': s['sid'][:8],
                                'current': s['title'], 'proposed': proposed,
                                'last_event': date or 'unknown',
                                'reason': f'stale fork (last active {date or "unknown"})'})
    return actions
