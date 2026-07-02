"""Tests for scripts/stamp-git-policy.py (stdlib-only, no conftest)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stamp-git-policy.py"
_spec = importlib.util.spec_from_file_location("stamp_git_policy", _SCRIPT)
sgp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sgp)


# --- derivations --------------------------------------------------------------

def test_toolbox_version_matches_own_manifest():
    manifest = _SCRIPT.parents[1] / ".claude-plugin" / "plugin.json"
    expected = json.loads(manifest.read_text(encoding="utf-8"))["version"]
    assert sgp.toolbox_version() == expected


def test_derive_python_default(tmp_path):
    assert sgp.derive_python(tmp_path) == "3.12"


def test_derive_python_from_requires_python(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nrequires-python = ">=3.11"\n', encoding="utf-8")
    assert sgp.derive_python(tmp_path) == "3.11"


def test_has_ruff_config_variants(tmp_path):
    assert sgp.has_ruff_config(tmp_path) is False
    (tmp_path / "ruff.toml").write_text("line-length = 100\n", encoding="utf-8")
    assert sgp.has_ruff_config(tmp_path) is True


def test_has_ruff_config_pyproject_section(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.ruff]\nline-length = 100\n', encoding="utf-8")
    assert sgp.has_ruff_config(tmp_path) is True


def test_derive_install_requirements_dev_wins(tmp_path):
    (tmp_path / "requirements-dev.txt").write_text("pytest\n", encoding="utf-8")
    assert sgp.derive_install(tmp_path, keep_lint=True) == \
        "python3 -m pip install -r requirements-dev.txt"


def test_derive_install_dev_extra_requires_version(tmp_path):
    # [dev] extra WITH [project].version -> editable install
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "1.0.0"\n'
        '[project.optional-dependencies]\ndev = ["pytest"]\n', encoding="utf-8")
    assert sgp.derive_install(tmp_path, keep_lint=False) == \
        "python3 -m pip install -e '.[dev]'"


def test_derive_install_versionless_pyproject_falls_back(tmp_path):
    # the claude-toolbox lesson: no [project].version -> not pip-installable
    (tmp_path / "pyproject.toml").write_text(
        '[project.optional-dependencies]\ndev = ["pytest"]\n', encoding="utf-8")
    assert sgp.derive_install(tmp_path, keep_lint=False) == \
        "python3 -m pip install 'pytest>=8'"


def test_derive_install_fallback_adds_ruff_when_linting(tmp_path):
    assert sgp.derive_install(tmp_path, keep_lint=True) == \
        "python3 -m pip install 'pytest>=8' 'ruff>=0.6'"


def test_derive_test_none_without_tests_dir(tmp_path):
    assert sgp.derive_test(tmp_path) is None
    (tmp_path / "tests").mkdir()
    assert sgp.derive_test(tmp_path) == "python3 -m pytest tests/ -q"


# --- renders --------------------------------------------------------------

_TPL = Path(__file__).resolve().parents[1] / "templates" / "git-policy"


def _test_yml() -> str:
    return (_TPL / "workflows" / "test.yml").read_text(encoding="utf-8")


def _release_yml() -> str:
    return (_TPL / "workflows" / "release.yml").read_text(encoding="utf-8")


def test_render_test_yml_stamps_all_seams():
    out = sgp.render_test_yml(
        _test_yml(), python="3.11",
        install="python3 -m pip install -r requirements-dev.txt",
        test="python3 -m pytest tests/ -q", lint="ruff check .")
    assert out.count('python-version: "3.11"') == 2
    assert 'python-version: "3.12"' not in out
    assert "run: python3 -m pip install -r requirements-dev.txt" in out
    assert "-e '.[dev]'" not in out
    assert "- name: Lint\n        run: ruff check .\n" in out


def test_render_test_yml_removes_lint_block():
    out = sgp.render_test_yml(
        _test_yml(), python="3.12",
        install="python3 -m pip install 'pytest>=8'",
        test="python3 -m pytest tests/ -q", lint=None)
    assert "- name: Lint" not in out
    assert "        run: ruff check .\n" not in out


def test_render_test_yml_custom_lint_command():
    out = sgp.render_test_yml(
        _test_yml(), python="3.12",
        install="python3 -m pip install 'pytest>=8' 'ruff>=0.6'",
        test="python3 -m pytest tests/ -q", lint="ruff check src/")
    assert "        run: ruff check src/\n" in out
    assert "        run: ruff check .\n" not in out


def test_render_release_yml_stamps_python():
    out = sgp.render_release_yml(_release_yml(), python="3.11")
    assert out.count('python-version: "3.11"') == 1
    assert ".github/scripts/check-manifest-tag.py" in out  # verbatim, untouched


def test_replace_line_raises_on_anchor_drift():
    import pytest
    with pytest.raises(ValueError):
        sgp._replace_line("no anchors here", "MISSING", "X", 1)


def test_vendored_checker_header_after_shebang():
    src = "#!/usr/bin/env python3\n\"\"\"doc.\"\"\"\nx = 1\n"
    out = sgp.vendored_checker(src, "0.6.0")
    lines = out.splitlines()
    assert lines[0] == "#!/usr/bin/env python3"
    assert lines[1] == "# vendored from claude-toolbox v0.6.0 — re-stamp to update"
    assert lines[2] == '"""doc."""'


# --- plan / CLI -----------------------------------------------------------

def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false",
         "-C", str(repo), *args],
        check=True, capture_output=True,
    )


def _target(tmp_path: Path, *, changelog=False) -> Path:
    """Minimal stampable target: git repo + plugin manifest + tests dir."""
    repo = tmp_path / "t"
    repo.mkdir(parents=True)  # callers may pass a not-yet-created subdir of tmp_path
    _git(repo, "init", "-q", "-b", "main")
    (repo / ".claude-plugin").mkdir()
    (repo / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "t", "version": "1.0.0"}), encoding="utf-8")
    (repo / "tests").mkdir()
    if changelog:
        (repo / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    return repo


def test_render_all_seeds_changelog_only_when_missing(tmp_path):
    kw = dict(python="3.12", install="python3 -m pip install 'pytest>=8'",
              test="python3 -m pytest tests/ -q", lint=None)
    assert "CHANGELOG.md" in sgp.render_all(_target(tmp_path), **kw)
    assert "CHANGELOG.md" not in sgp.render_all(
        _target(tmp_path / "b", changelog=True), **kw)


def test_build_plan_drops_noops(tmp_path):
    repo = _target(tmp_path)
    rendered = {"a.txt": "same\n", "b.txt": "new\n"}
    (repo / "a.txt").write_text("same\n", encoding="utf-8")
    plan = sgp.build_plan(repo, rendered)
    assert [rel for rel, _, _ in plan] == ["b.txt"]
    rel, old, new = plan[0]
    assert old is None and new == b"new\n"


def test_unified_diff_new_file_against_devnull():
    out = sgp.unified_diff("x/y.txt", None, b"hello\n")
    assert out.startswith("--- /dev/null")
    assert "+hello" in out


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(_SCRIPT), *args],
                          capture_output=True, text=True)


def test_cli_exit2_on_non_repo(tmp_path):
    r = _run_cli("--repo", str(tmp_path))
    assert r.returncode == 2
    assert "not a git repository" in r.stderr


def test_cli_exit2_without_manifest(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    r = _run_cli("--repo", str(repo))
    assert r.returncode == 2
    assert "version manifest" in r.stderr


def test_cli_accepts_versioned_pyproject_manifest(tmp_path):
    # Widened gate: any manifest the vendored checker reads, not just plugin.json.
    repo = tmp_path / "p"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "p"\nversion = "1.0.0"\n', encoding="utf-8")
    (repo / "tests").mkdir()
    r = _run_cli("--repo", str(repo))
    assert r.returncode == 0
    assert "+++ b/.github/workflows/test.yml" in r.stdout


def test_cli_accepts_package_json_manifest(tmp_path):
    repo = tmp_path / "n"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "package.json").write_text(
        json.dumps({"name": "n", "version": "1.0.0"}), encoding="utf-8")
    (repo / "tests").mkdir()  # a non-pytest repo would pass --test; gate is what's under test
    r = _run_cli("--repo", str(repo))
    assert r.returncode == 0


def test_cli_exit2_without_tests_dir_names_flag(tmp_path):
    repo = _target(tmp_path)
    (repo / "tests").rmdir()
    r = _run_cli("--repo", str(repo))
    assert r.returncode == 2
    assert "--test" in r.stderr


def test_cli_exit2_on_malformed_pyproject(tmp_path):
    # tomllib.TOMLDecodeError must land as a clean exit 2, never a traceback.
    repo = _target(tmp_path)
    (repo / "pyproject.toml").write_text("not [valid toml\n", encoding="utf-8")
    r = _run_cli("--repo", str(repo))
    assert r.returncode == 2
    assert "error:" in r.stderr
    assert "Traceback" not in r.stderr


def test_cli_dry_run_default_writes_nothing(tmp_path):
    repo = _target(tmp_path)
    r = _run_cli("--repo", str(repo))
    assert r.returncode == 0
    assert "--write" in r.stdout            # points at the apply flag
    assert "+++ b/.github/workflows/test.yml" in r.stdout
    assert not (repo / ".github").exists()  # nothing written


def test_cli_write_lays_files_down(tmp_path):
    repo = _target(tmp_path)
    r = _run_cli("--repo", str(repo), "--write")
    assert r.returncode == 0
    for rel in (".github/workflows/test.yml", ".github/workflows/release.yml",
                ".github/dependabot.yml", ".github/scripts/check-manifest-tag.py",
                "CHANGELOG.md"):
        assert (repo / rel).is_file(), rel


# --- golden end-to-end ------------------------------------------------------

def test_golden_bare_target_full_test_yml(tmp_path):
    """Bare target: manifest + tests only — no pyproject/requirements/ruff.
    (NB: NOT ramp's shape — ramp has requirements-dev.txt; see Verification.)
    Exact-bytes assertion: fallback install, no lint step, default python."""
    repo = _target(tmp_path)
    assert _run_cli("--repo", str(repo), "--write").returncode == 0
    tpl = (Path(__file__).resolve().parents[1]
           / "templates" / "git-policy" / "workflows" / "test.yml")
    expected = tpl.read_text(encoding="utf-8").replace(
        "        run: python3 -m pip install -e '.[dev]'",
        "        run: python3 -m pip install 'pytest>=8'",
    ).replace("      - name: Lint\n        run: ruff check .\n", "")
    got = (repo / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    assert got == expected


def test_golden_requirements_dev_target(tmp_path):
    repo = _target(tmp_path)
    (repo / "requirements-dev.txt").write_text("pytest\nruff\n", encoding="utf-8")
    (repo / "ruff.toml").write_text("line-length = 100\n", encoding="utf-8")
    assert _run_cli("--repo", str(repo), "--write").returncode == 0
    got = (repo / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    assert "        run: python3 -m pip install -r requirements-dev.txt" in got
    assert "      - name: Lint\n        run: ruff check .\n" in got


def test_golden_pyproject_dev_extra_target(tmp_path):
    repo = _target(tmp_path)
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "t"\nversion = "1.0.0"\nrequires-python = ">=3.11"\n'
        '[project.optional-dependencies]\ndev = ["pytest", "ruff"]\n'
        '[tool.ruff]\nline-length = 100\n', encoding="utf-8")
    assert _run_cli("--repo", str(repo), "--write").returncode == 0
    got = (repo / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    assert got.count('python-version: "3.11"') == 2
    assert "        run: python3 -m pip install -e '.[dev]'" in got
    assert "      - name: Lint" in got
    rel = (repo / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert rel.count('python-version: "3.11"') == 1


def test_golden_vendored_checker_is_source_plus_header(tmp_path):
    repo = _target(tmp_path)
    assert _run_cli("--repo", str(repo), "--write").returncode == 0
    src = (Path(__file__).resolve().parents[1]
           / "scripts" / "check-manifest-tag.py").read_text(encoding="utf-8")
    got = (repo / ".github" / "scripts" / "check-manifest-tag.py").read_text(encoding="utf-8")
    lines = got.splitlines(keepends=True)
    assert lines[1].startswith("# vendored from claude-toolbox v")
    assert lines[0] + "".join(lines[2:]) == src  # byte-identical minus header


def test_golden_changelog_never_overwritten(tmp_path):
    repo = _target(tmp_path, changelog=True)
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n## [1.0.0]\n- real history\n",
                                       encoding="utf-8")
    assert _run_cli("--repo", str(repo), "--write").returncode == 0
    assert "real history" in (repo / "CHANGELOG.md").read_text(encoding="utf-8")


def test_second_run_is_empty_and_idempotent(tmp_path):
    repo = _target(tmp_path)
    assert _run_cli("--repo", str(repo), "--write").returncode == 0
    r = _run_cli("--repo", str(repo))
    assert r.returncode == 0
    assert "Nothing to do" in r.stdout
    assert "+++" not in r.stdout
