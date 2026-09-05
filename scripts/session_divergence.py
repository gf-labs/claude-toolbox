"""Read-only three-store session-name divergence check.

A session's display name lives in three places on disk:

  1. the session JSONL ``custom-title`` — ``~/.claude/projects/<key>/<sid>.jsonl``
     (the only store claude-toolbox writes)
  2. the peer roster ``name`` — ``~/.claude/sessions/<pid>.json`` (the address
     ``SendMessage``/``ListAgents`` resolve; duplicates are ambiguous)
  3. the job ``name`` — ``~/.claude/jobs/<jobId>/state.json``

A ``/rename`` propagates across a compact-chain group and touches these stores at
slightly different moments, so they drift apart. This module *reports* the
divergence and never writes stores 2 and 3 — they are Claude Code's own live
state, rewritten by running processes, so a racing write could corrupt them. The
full evidence chain is in ``docs/session-rename-propagation.md``.

Joins are keyed on session id. The pure ``find_divergences`` takes already-read,
normalized inputs so it is testable without touching ``~/.claude``.
"""
from __future__ import annotations

import json
from pathlib import Path

import session_naming


def collect_titles(proj_dirs: list[Path]) -> dict[str, str]:
    """Map session id → ``custom-title`` across the given project dirs.

    Keys are JSONL stems (the session id). Sessions with no title are omitted,
    so a missing key means "no title store," which the join reads as absent.
    Reuses ``session_naming.read_title`` (last custom-title wins, corrupt lines
    tolerated). Nonexistent dirs are skipped.
    """
    titles: dict[str, str] = {}
    for d in proj_dirs:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.jsonl")):
            title = session_naming.read_title(f)
            if title:
                titles[f.stem] = title
    return titles


def read_roster(sessions_dir: Path) -> list[dict]:
    """Read the peer roster from ``~/.claude/sessions/<pid>.json``.

    Returns one normalized dict per entry that carries a ``sessionId``::

        {"sid", "name", "pid", "cwd", "started_at", "name_since"}

    Malformed JSON, non-dict payloads, and unreadable files are skipped — the
    guard pattern lifted from ``_session.current_session_jsonl`` (this reads a
    directory of live Claude Code state that a running process may be rewriting).
    A missing directory yields an empty list.
    """
    entries: list[dict] = []
    if not sessions_dir.exists():
        return entries
    for sf in sorted(sessions_dir.glob("*.json")):
        try:
            obj = json.loads(sf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        sid = obj.get("sessionId")
        if not sid:
            continue
        entries.append({
            "sid": sid,
            "name": obj.get("name"),
            "pid": sf.stem,
            "cwd": obj.get("cwd"),
            "started_at": obj.get("startedAt"),
            "name_since": obj.get("nameSince"),
        })
    return entries


def read_jobs(jobs_dir: Path) -> list[dict]:
    """Read job state from ``~/.claude/jobs/<jobId>/state.json``.

    Returns one normalized dict per readable ``state.json``::

        {"sid", "name", "state", "tempo", "job_id"}

    A job directory with no ``state.json``, a malformed or non-dict payload, and
    stray non-directory entries (macOS ``.DS_Store``) are skipped. A missing
    directory yields an empty list. ``sid`` may be ``None`` — a done job holding
    a name is worth surfacing even when it carries no session id to join on.
    """
    entries: list[dict] = []
    if not jobs_dir.exists():
        return entries
    for job_dir in sorted(jobs_dir.iterdir()):
        try:
            obj = json.loads((job_dir / "state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        entries.append({
            "sid": obj.get("sessionId"),
            "name": obj.get("name"),
            "state": obj.get("state"),
            "tempo": obj.get("tempo"),
            "job_id": job_dir.name,
        })
    return entries


def find_divergences(titles: dict[str, str],
                     roster: list[dict],
                     jobs: list[dict]) -> dict[str, list]:
    """Report where a session's three stored names disagree.

    ``titles`` maps session id → ``custom-title``. ``roster`` and ``jobs`` are
    lists of normalized dicts carrying at least ``sid`` and ``name``.

    Returns a findings dict grouped by class::

        {"store_disagreement": [...], "duplicate_roster_names": [...],
         "stale_holders": [...]}
    """
    roster_by_sid = {r["sid"]: r for r in roster}
    jobs_by_sid = {j["sid"]: j for j in jobs}
    all_sids = set(titles) | set(roster_by_sid) | set(jobs_by_sid)

    store_disagreement = []
    for sid in sorted(all_sids):
        title = titles.get(sid)
        roster_name = roster_by_sid.get(sid, {}).get("name")
        job_name = jobs_by_sid.get(sid, {}).get("name")
        present = [n for n in (title, roster_name, job_name) if n is not None]
        if len(set(present)) > 1:
            store_disagreement.append({
                "sid": sid,
                "title": title,
                "roster_name": roster_name,
                "job_name": job_name,
            })

    # A roster name is an address; two distinct sessions holding one name is an
    # ambiguity SendMessage cannot resolve. Group by name, keep names carried by
    # two or more distinct session ids. (The reverse — one session under two
    # roster pids with different names — is not reported: this keys on name, and
    # the store-disagreement join keeps one roster entry per sid.)
    sids_by_name: dict[str, set] = {}
    for r in roster:
        name = r.get("name")
        if name is None:
            continue
        sids_by_name.setdefault(name, set()).add(r["sid"])
    duplicate_roster_names = [
        {"name": name, "sids": sorted(sids)}
        for name, sids in sorted(sids_by_name.items())
        if len(sids) > 1
    ]

    # A completed job that still carries a name is squatting on an address a
    # running session may want. State, not process liveness, is the signal here.
    stale_holders = [
        {"sid": j.get("sid"), "name": j.get("name"), "state": j.get("state"),
         "tempo": j.get("tempo"), "job_id": j.get("job_id")}
        for j in jobs
        if j.get("state") == "done" and j.get("name")
    ]

    return {
        "store_disagreement": store_disagreement,
        "duplicate_roster_names": duplicate_roster_names,
        "stale_holders": stale_holders,
    }


def format_report(findings: dict[str, list]) -> str:
    """Render findings as a human-readable, grouped report.

    A short line per finding under a per-class header, or a single clean line
    when nothing diverges. Purely presentational — it never re-derives findings.
    """
    disagree = findings["store_disagreement"]
    dups = findings["duplicate_roster_names"]
    stale = findings["stale_holders"]
    total = len(disagree) + len(dups) + len(stale)
    if total == 0:
        return "No name divergence found."

    lines = [f"Session name divergence — {total} finding(s)"]

    if disagree:
        lines.append(f"\nStore disagreement ({len(disagree)}) — one session, conflicting names:")
        for f in disagree:
            lines.append(
                f"  {f['sid']}  title={f['title']!r}  "
                f"roster={f['roster_name']!r}  job={f['job_name']!r}")

    if dups:
        lines.append(f"\nDuplicate roster addresses ({len(dups)}) — one name, many sessions:")
        for f in dups:
            lines.append(f"  {f['name']!r}  ←  {', '.join(f['sids'])}")

    if stale:
        lines.append(f"\nStale name holders ({len(stale)}) — a done job still holding a name:")
        for f in stale:
            lines.append(
                f"  {f['sid']}  {f['name']!r}  "
                f"(job {f['job_id']}, state={f['state']}, tempo={f['tempo']})")

    return "\n".join(lines)


def scan(sessions_dir: Path, jobs_dir: Path, proj_dirs: list[Path]) -> dict[str, list]:
    """Read the three stores from disk and return the divergence findings.

    The read-only orchestrator behind the CLI: reads the global roster and job
    stores plus per-project titles, then joins them. Never writes anything.
    """
    return find_divergences(
        collect_titles(proj_dirs),
        read_roster(sessions_dir),
        read_jobs(jobs_dir),
    )
