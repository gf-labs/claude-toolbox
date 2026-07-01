"""Tests for scripts/collect-git-policy.py (stdlib-only, no conftest)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect-git-policy.py"
_spec = importlib.util.spec_from_file_location("collect_git_policy", _SCRIPT)
cgp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cgp)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false",
         "-C", str(repo), *args],
        check=True, capture_output=True,
    )


def _repo(tmp_path: Path, *, version="0.5.1", tag="v0.5.1", workflow=True,
          changelog=True, dependabot=False) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / ".claude-plugin").mkdir()
    (repo / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "x", "version": version}), encoding="utf-8"
    )
    if workflow:
        (repo / ".github" / "workflows").mkdir(parents=True)
        (repo / ".github" / "workflows" / "test.yml").write_text("name: test\n", encoding="utf-8")
    if changelog:
        (repo / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    if dependabot:
        (repo / ".github").mkdir(exist_ok=True)
        (repo / ".github" / "dependabot.yml").write_text("version: 2\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    if tag:
        _git(repo, "tag", "-a", tag, "-m", tag)
    return repo


def test_is_git_repo_false_on_plain_dir(tmp_path):
    assert cgp.is_git_repo(tmp_path) is False


def test_branches_lists_main(tmp_path):
    assert "main" in cgp.branches(_repo(tmp_path))


def test_tags_lists_version_tag(tmp_path):
    assert cgp.tags(_repo(tmp_path)) == ["v0.5.1"]


def test_workflows_lists_yml(tmp_path):
    assert cgp.workflows(_repo(tmp_path)) == ["test.yml"]


def test_workflows_empty_when_absent(tmp_path):
    assert cgp.workflows(_repo(tmp_path, workflow=False)) == []


def test_has_file_changelog(tmp_path):
    repo = _repo(tmp_path)
    assert cgp.has_file(repo, "CHANGELOG.md") is True
    assert cgp.has_file(repo, ".github/dependabot.yml") is False


def test_github_slug_parses_https(tmp_path):
    repo = _repo(tmp_path)
    _git(repo, "remote", "add", "origin", "https://github.com/acme/widget.git")
    assert cgp.github_slug(repo) == "acme/widget"


def test_github_slug_none_for_non_github(tmp_path):
    repo = _repo(tmp_path)
    _git(repo, "remote", "add", "origin", "https://gitlab.com/acme/widget.git")
    assert cgp.github_slug(repo) is None


def test_render_non_git(tmp_path):
    assert "GIT: no" in cgp.render(tmp_path)


def test_render_golden(tmp_path):
    # A repo whose manifest matches its tag: the full facts report.
    report = cgp.render(_repo(tmp_path, version="0.5.1", tag="v0.5.1"))
    assert "=== REPO ===" in report
    assert "DEFAULT_BRANCH: main" in report
    assert "=== MANIFEST_TAG ===" in report
    assert "EXIT: 0" in report            # manifest 0.5.1 == tag v0.5.1
    assert "WORKFLOWS: test.yml" in report
    assert "PRESENT: yes" in report       # CHANGELOG
    assert "DEPENDABOT: no" in report
