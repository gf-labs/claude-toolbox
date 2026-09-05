import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _run(script, home, cwd, *args):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          env=env, capture_output=True, text=True, cwd=str(cwd))


def _register(home, *repos):
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True, exist_ok=True)
    for r in repos:
        r.mkdir(parents=True, exist_ok=True)
        (projects / str(r).replace("/", "-")).mkdir(exist_ok=True)
    return projects


def _session(proj, stem, content, mtime):
    f = proj / f"{stem}.jsonl"
    f.write_text(json.dumps({"type": "user", "message": {"content": content}}) + "\n",
                 encoding="utf-8")
    os.utime(f, (mtime, mtime))
    return f


def test_post_save_global_names_unnamed_across_projects(tmp_path):
    # Two registered projects, cwd is neither -> global scope. Each has an older
    # unnamed session (rename candidate) plus a newer "current" session.
    home = tmp_path / "home"
    alpha = tmp_path / "work" / "alpha"
    beta = tmp_path / "work" / "beta"
    projects = _register(home, alpha, beta)
    for repo in (alpha, beta):
        pd = projects / str(repo).replace("/", "-")
        _session(pd, "old-aaaa", f"implement the {repo.name} widget", mtime=1000)
        _session(pd, "new-bbbb", "current work", mtime=2000)
    outside = tmp_path / "nowhere"
    outside.mkdir()

    result = _run("post-save.py", home, outside)
    assert result.returncode == 0, result.stderr
    # Global mode: the most-recent-per-project is named as "current"; both projects
    # touched. Assert a Named line appears and no crash (exact name depends on scope
    # order — pin the stable substring, not the ordering).
    assert "Named:" in result.stdout or "Renamed:" in result.stdout, result.stdout


# --------------------------------------------------------------------------
# junk-title re-derivation (the #661 title mis-latch fix)
# --------------------------------------------------------------------------

def _titled_session(proj, stem, content, title, mtime):
    f = proj / f"{stem}.jsonl"
    f.write_text(
        json.dumps({"type": "user", "message": {"content": content}}) + "\n"
        + json.dumps({"type": "custom-title", "customTitle": title, "sessionId": stem}) + "\n",
        encoding="utf-8")
    os.utime(f, (mtime, mtime))
    return f


def _titled_session_with_commit(proj, stem, content, title, commit_subject, mtime,
                                branch="feature/x", sha="abc1234f"):
    # like _titled_session but with a git commit echo between the user message
    # and the title, so extract_context derives the name from the commit
    f = proj / f"{stem}.jsonl"
    f.write_text(
        json.dumps({"type": "user", "message": {"content": content}}) + "\n"
        + json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_result", "content": [
                {"type": "text", "text": f"[{branch} {sha}] {commit_subject}"}]}]}}) + "\n"
        + json.dumps({"type": "custom-title", "customTitle": title, "sessionId": stem}) + "\n",
        encoding="utf-8")
    os.utime(f, (mtime, mtime))
    return f


def _titles(f):
    out = []
    for ln in f.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        obj = json.loads(ln)
        if obj.get("type") == "custom-title":
            out.append(obj["customTitle"])
    return out


def _run_current(script, home, cwd, sid, *args):
    env = {**os.environ, "HOME": str(home), "CLAUDE_CODE_SESSION_ID": sid}
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          env=env, capture_output=True, text=True, cwd=str(cwd))


def test_post_save_rederives_junk_titled_current_session(tmp_path):
    # a real work session whose title latched onto junk ("*-scratch-*") is
    # re-derived from its most recent commit on the next pin — the #661 fix.
    # A junk title heals only from a commit (a trustworthy work artifact).
    home = tmp_path / "home"
    repo = tmp_path / "work" / "proj"
    projects = _register(home, repo)
    pd = projects / str(repo).replace("/", "-")
    f = _titled_session_with_commit(pd, "sess-aaaa", "implement the parser widget",
                                    "old-scratch-9", "add the parser widget", 2000)
    outside = tmp_path / "nowhere"
    outside.mkdir()

    result = _run_current("post-save.py", home, outside, "sess-aaaa")
    assert result.returncode == 0, result.stderr
    titles = _titles(f)
    assert titles[0] == "old-scratch-9"          # original kept as history
    assert titles[-1] == "add-parser-widget"     # re-derived from the commit


def test_post_save_leaves_junk_title_with_no_commit_untouched(tmp_path):
    # Option A: a junk title heals ONLY from a commit. With a usable first-user
    # message but NO commit, the junk title is left as-is — never re-derived into
    # another weak slug (the junk->junk defect). /rename is the durable fix.
    home = tmp_path / "home"
    repo = tmp_path / "work" / "proj"
    projects = _register(home, repo)
    pd = projects / str(repo).replace("/", "-")
    f = _titled_session(pd, "sess-dddd", "implement the parser widget", "old-scratch-9", 2000)
    outside = tmp_path / "nowhere"
    outside.mkdir()

    result = _run_current("post-save.py", home, outside, "sess-dddd")
    assert result.returncode == 0, result.stderr
    assert _titles(f) == ["old-scratch-9"]       # unchanged despite a usable first-user msg


def test_post_save_leaves_real_titled_session_untouched(tmp_path):
    # a legitimate title must never be re-derived over
    home = tmp_path / "home"
    repo = tmp_path / "work" / "proj"
    projects = _register(home, repo)
    pd = projects / str(repo).replace("/", "-")
    f = _titled_session(pd, "sess-bbbb", "implement the parser widget", "parser-refactor", 2000)
    outside = tmp_path / "nowhere"
    outside.mkdir()

    result = _run_current("post-save.py", home, outside, "sess-bbbb")
    assert result.returncode == 0, result.stderr
    assert _titles(f) == ["parser-refactor"]         # unchanged
    assert "NONE" in result.stdout


def test_post_save_keeps_junk_title_when_no_name_derivable(tmp_path):
    # junk title but only harness preamble as content -> nothing to derive ->
    # the junk title is left as-is, never blanked
    home = tmp_path / "home"
    repo = tmp_path / "work" / "proj"
    projects = _register(home, repo)
    pd = projects / str(repo).replace("/", "-")
    f = _titled_session(pd, "sess-cccc", "<command-name>/tools:pin</command-name>",
                        "x-scratch-1", 2000)
    outside = tmp_path / "nowhere"
    outside.mkdir()

    result = _run_current("post-save.py", home, outside, "sess-cccc")
    assert result.returncode == 0, result.stderr
    assert _titles(f) == ["x-scratch-1"]             # unchanged, not blanked


def test_post_save_rederives_junk_titled_non_current_session(tmp_path):
    # the "other sessions" loop heals a latched junk title too, not just current
    home = tmp_path / "home"
    repo = tmp_path / "work" / "proj"
    projects = _register(home, repo)
    pd = projects / str(repo).replace("/", "-")
    _titled_session(pd, "curr-zzzz", "current work here", "steady-progress", 3000)  # current, good title
    old = _titled_session_with_commit(pd, "old-aaaa", "wire up the collector",
                                      "tmp-scratch-4", "wire up the collector", 1000)
    outside = tmp_path / "nowhere"
    outside.mkdir()

    result = _run_current("post-save.py", home, outside, "curr-zzzz")
    assert result.returncode == 0, result.stderr
    assert _titles(old)[-1] == "wire-up-collector"   # non-current junk healed from commit
