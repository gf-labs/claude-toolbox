"""Tests for iter_session_dirs — storage-space enumeration over ~/.claude/projects."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _projects import iter_session_dirs  # noqa: E402


def _seed(pd, *keys):
    pd.mkdir(parents=True, exist_ok=True)
    for k in keys:
        (pd / k).mkdir()
    return pd


def test_global_returns_all_dirs_including_orphans(tmp_path):
    # An orphan is simply a key-dir with no backing repo; iter_session_dirs never
    # reconstructs, so global scope (scoped_keys -> None) returns every dir.
    pd = _seed(tmp_path / "pd", "-a", "-b", "-orphan-gone-repo")
    scope = ("global", None, tmp_path)
    result = iter_session_dirs(scope=scope, projects_dir=pd)
    assert [k for k, _ in result] == ["-a", "-b", "-orphan-gone-repo"]
    assert result[0] == ("-a", pd / "-a")


def test_single_returns_only_that_key(tmp_path):
    pd = _seed(tmp_path / "pd", "-a", "-b", "-c")
    scope = ("single", "-b", tmp_path)
    result = iter_session_dirs(scope=scope, projects_dir=pd)
    assert result == [("-b", pd / "-b")]


def test_parent_returns_only_child_keys(tmp_path):
    pd = _seed(tmp_path / "pd", "-a", "-b", "-c")
    scope = ("parent", [("-a", tmp_path / "a"), ("-c", tmp_path / "c")], tmp_path)
    result = iter_session_dirs(scope=scope, projects_dir=pd)
    assert [k for k, _ in result] == ["-a", "-c"]


def test_skips_non_dir_entries(tmp_path):
    pd = _seed(tmp_path / "pd", "-a")
    (pd / "stray.txt").write_text("x", encoding="utf-8")
    scope = ("global", None, tmp_path)
    result = iter_session_dirs(scope=scope, projects_dir=pd)
    assert [k for k, _ in result] == ["-a"]


def test_missing_projects_dir_returns_empty(tmp_path):
    scope = ("global", None, tmp_path)
    result = iter_session_dirs(scope=scope, projects_dir=tmp_path / "does-not-exist")
    assert result == []


def test_result_sorted_by_key(tmp_path):
    pd = _seed(tmp_path / "pd", "-zebra", "-alpha", "-mid")
    scope = ("global", None, tmp_path)
    result = iter_session_dirs(scope=scope, projects_dir=pd)
    assert [k for k, _ in result] == ["-alpha", "-mid", "-zebra"]
