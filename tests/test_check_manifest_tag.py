"""Tests for scripts/check-manifest-tag.py.

Pure helpers are unit-tested by importing the hyphenated script by path
(stdlib-only suite, no conftest). CLI behavior is covered in the integration
tests added in Task 2.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-manifest-tag.py"
_spec = importlib.util.spec_from_file_location("check_manifest_tag", _SCRIPT)
cmt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cmt)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_reads_plugin_json_first(tmp_path):
    # plugin.json wins even when other manifests are present (precedence).
    _write(tmp_path / ".claude-plugin" / "plugin.json", {"name": "x", "version": "0.5.1"})
    _write(tmp_path / "package.json", {"name": "x", "version": "9.9.9"})
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "8.8.8"\n', encoding="utf-8"
    )
    assert cmt.read_manifest_version(tmp_path) == ("0.5.1", ".claude-plugin/plugin.json")


def test_reads_pyproject_project_version(tmp_path):
    import pytest
    pytest.importorskip("tomllib")  # stdlib >=3.11; skip cleanly on older Python
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "1.2.3"\n', encoding="utf-8"
    )
    assert cmt.read_manifest_version(tmp_path) == ("1.2.3", "pyproject.toml")


def test_reads_package_json(tmp_path):
    _write(tmp_path / "package.json", {"name": "x", "version": "2.0.0"})
    assert cmt.read_manifest_version(tmp_path) == ("2.0.0", "package.json")


def test_missing_manifest_raises(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        cmt.read_manifest_version(tmp_path)


def test_latest_stable_tag_picks_semver_max(tmp_path):
    tags = ["v0.9.0", "v1.2.0", "v1.10.0", "v1.2.0-beta.1", "not-a-tag"]
    assert cmt.latest_stable_tag(tags) == "v1.10.0"


def test_latest_stable_tag_none_when_empty(tmp_path):
    assert cmt.latest_stable_tag(["v1.0.0-rc.1", "garbage"]) is None


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false",
         "-C", str(repo), *args],
        check=True, capture_output=True,
    )


def _init_repo(repo: Path, version: str | None, tag: str | None = None) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    if version is not None:
        _write(repo / ".claude-plugin" / "plugin.json", {"name": "x", "version": version})
    else:
        (repo / "README.md").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    if tag:
        _git(repo, "tag", "-a", tag, "-m", tag)


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args], capture_output=True, text=True
    )


def test_cli_ok_when_manifest_matches_latest_tag(tmp_path):
    repo = tmp_path / "r"
    _init_repo(repo, "1.2.0", "v1.2.0")
    result = _run("--repo", str(repo))
    assert result.returncode == 0, result.stdout
    assert "OK" in result.stdout


def test_cli_drift_when_tag_differs(tmp_path):
    repo = tmp_path / "r"
    _init_repo(repo, "1.2.0", "v1.1.0")  # the common case: manifest ahead of tag
    result = _run("--repo", str(repo))
    assert result.returncode == 1
    assert "DRIFT" in result.stdout and "v1.1.0" in result.stdout


def test_cli_drift_when_no_tags(tmp_path):
    repo = tmp_path / "r"
    _init_repo(repo, "1.2.0")
    result = _run("--repo", str(repo))
    assert result.returncode == 1
    assert "DRIFT" in result.stdout and "(none)" in result.stdout


def test_cli_indeterminate_when_no_manifest(tmp_path):
    repo = tmp_path / "r"
    _init_repo(repo, None)
    result = _run("--repo", str(repo))
    assert result.returncode == 2
    assert "INDETERMINATE" in result.stdout


def test_cli_indeterminate_when_versionless_manifest(tmp_path):
    # KeyError (no "version") -> exit 2, before any git call.
    _write(tmp_path / ".claude-plugin" / "plugin.json", {"name": "x"})
    result = _run("--repo", str(tmp_path))
    assert result.returncode == 2
    assert "INDETERMINATE" in result.stdout


def test_cli_indeterminate_when_not_a_git_repo(tmp_path):
    # Manifest present but not a git repo -> git tag fails -> exit 2, not a crash.
    _write(tmp_path / ".claude-plugin" / "plugin.json", {"name": "x", "version": "1.0.0"})
    result = _run("--repo", str(tmp_path))
    assert result.returncode == 2
    assert "INDETERMINATE" in result.stdout


def test_cli_tag_mode_matches_given_tag(tmp_path):
    repo = tmp_path / "r"
    _init_repo(repo, "1.2.0")  # no real tag needed in --tag mode
    assert _run("--repo", str(repo), "--tag", "v1.2.0").returncode == 0
    assert _run("--repo", str(repo), "--tag", "v9.9.9").returncode == 1


# --- --nearest mode (reachability-aware; used by release-gate.yml on main) ---


def _bump_manifest(repo: Path, version: str, message: str) -> None:
    _write(repo / ".claude-plugin" / "plugin.json", {"name": "x", "version": version})
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", message)


def test_nearest_ok_when_tag_is_reachable(tmp_path):
    repo = tmp_path / "r"
    _init_repo(repo, "1.2.0", "v1.2.0")
    result = _run("--repo", str(repo), "--nearest")
    assert result.returncode == 0, result.stdout
    assert "OK" in result.stdout and "reachable" in result.stdout


def test_nearest_drift_when_never_tagged(tmp_path):
    repo = tmp_path / "r"
    _init_repo(repo, "1.2.0")
    result = _run("--repo", str(repo), "--nearest")
    assert result.returncode == 1
    assert "(none)" in result.stdout and "annotated-tag" in result.stdout


def test_nearest_detects_orphaned_tag_after_squash(tmp_path):
    """The case the default mode cannot see.

    Simulates a squash-merge: the release commit is tagged on a side branch,
    main gets an equivalent commit that is not a descendant of it. The tag still
    exists in the repo, so the reachability-BLIND default mode passes — while
    --nearest fails and names the squash.
    """
    repo = tmp_path / "r"
    _init_repo(repo, "1.0.0", "v1.0.0")
    _git(repo, "checkout", "-q", "-b", "release/1.1.0")
    _bump_manifest(repo, "1.1.0", "release 1.1.0")
    _git(repo, "tag", "-a", "v1.1.0", "-m", "v1.1.0")  # tag the release tip
    _git(repo, "checkout", "-q", "main")
    _bump_manifest(repo, "1.1.0", "squashed release 1.1.0")  # equivalent, not a descendant

    blind = _run("--repo", str(repo))  # default mode: highest tag anywhere
    assert blind.returncode == 0, "precondition: the blind check passes on an orphaned tag"

    result = _run("--repo", str(repo), "--nearest")
    assert result.returncode == 1
    assert "not reachable" in result.stdout.lower()
    assert "squash" in result.stdout.lower()


def test_nearest_indeterminate_when_not_a_git_repo(tmp_path):
    _write(tmp_path / ".claude-plugin" / "plugin.json", {"name": "x", "version": "1.0.0"})
    result = _run("--repo", str(tmp_path), "--nearest")
    assert result.returncode == 2
    assert "INDETERMINATE" in result.stdout
