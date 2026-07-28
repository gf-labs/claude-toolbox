#!/usr/bin/env python3
"""Resolve the live foreground session's JSONL for a project.

Single source of truth for "which *.jsonl in ~/.claude/projects/<key>/ is the
current session." Prefers the authoritative CLAUDE_CODE_SESSION_ID the harness
exports; falls back to each caller's prior heuristic (startedAt when a cwd is
available, then newest-mtime) so behavior is unchanged when the env var is
absent (older CLI).
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def current_session_jsonl(proj_meta_dir, *, project_cwd=None, env=None, home=None):
    """Return the current session's JSONL Path in ``proj_meta_dir``, or None.

    proj_meta_dir : Path to ~/.claude/projects/<key>/ (where *.jsonl live).
    project_cwd   : the repo cwd, enabling the sessions/*.json startedAt
                    fallback; omit for callers that only hold the meta dir
                    (their fallback stays pure mtime).
    env, home     : injected for tests; default os.environ / Path.home().
    """
    env = os.environ if env is None else env
    home = Path.home() if home is None else home

    # Tier 1 — authoritative: the harness names the current session directly.
    sid = env.get('CLAUDE_CODE_SESSION_ID')
    if sid:
        cand = proj_meta_dir / f'{sid}.jsonl'
        if cand.exists():
            return cand

    jsonls = list(proj_meta_dir.glob('*.jsonl'))
    if not jsonls:
        return None

    # Tier 2 — startedAt heuristic (only when the caller supplies its cwd).
    if project_cwd is not None:
        sessions_dir = home / '.claude' / 'sessions'
        best, best_started = None, -1
        if sessions_dir.exists():
            for sf in sessions_dir.iterdir():
                try:
                    obj = json.loads(sf.read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    continue
                if not isinstance(obj, dict):
                    continue
                if obj.get('cwd') == str(project_cwd) and obj.get('sessionId'):
                    cand = proj_meta_dir / (obj['sessionId'] + '.jsonl')
                    started = obj.get('startedAt', 0)
                    if cand.exists() and started > best_started:
                        best, best_started = cand, started
        if best is not None:
            return best

    # Tier 3 — most-recently-modified JSONL.
    return max(jsonls, key=lambda f: f.stat().st_mtime)
