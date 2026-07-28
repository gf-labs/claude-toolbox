#!/usr/bin/env python3
"""Stamp git-policy CI files into a target repo's working tree.

Deterministic adoption transform: the git-policy-auditor DESCRIBES the fix;
this computes it. Derives per-repo values from the target (each overridable),
renders templates/git-policy/, and prints a unified diff (default) or writes
the files (--write). Never stages, commits, or branches — the human reviews
`git diff` in the target and commits. stdlib-only.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_TEMPLATES = _HERE.parent / "templates" / "git-policy"
_CHECKER_SRC = _HERE / "check-manifest-tag.py"
_TOOLBOX_MANIFEST = _HERE.parent / ".claude-plugin" / "plugin.json"

# Anchor strings guarded by tests/test_git_policy_templates.py — keep in sync.
_PY_LINE = '          python-version: "3.12"'
_INSTALL_LINE = "        run: python3 -m pip install -e '.[dev]'"
_TEST_LINE = "        run: python3 -m pytest tests/ -q"
_LINT_BLOCK = "      - name: Lint\n        run: ruff check .\n"
_LINT_RUN_LINE = "        run: ruff check .\n"

_REQUIRES_PY = re.compile(r'requires-python\s*=\s*"[^"0-9]*(\d+\.\d+)')

# Ownership markers. A generated file carries _STAMP_MARKER; the vendored
# checker carries its own long-standing _VENDOR_MARKER. Either means "the stamp
# wrote this, so the stamp may replace it" — anything else is hand-authored and
# is skipped unless --force.
_STAMP_MARKER = "# stamped by claude-toolbox git-policy"
_VENDOR_MARKER = "# vendored from claude-toolbox"


def toolbox_version() -> str:
    return json.loads(_TOOLBOX_MANIFEST.read_text(encoding="utf-8"))["version"]


def derive_python(repo: Path) -> str:
    pyproject = repo / "pyproject.toml"
    if pyproject.is_file():
        m = _REQUIRES_PY.search(pyproject.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return "3.12"


def has_ruff_config(repo: Path) -> bool:
    if (repo / "ruff.toml").is_file() or (repo / ".ruff.toml").is_file():
        return True
    pyproject = repo / "pyproject.toml"
    return pyproject.is_file() and "[tool.ruff" in pyproject.read_text(encoding="utf-8")


def derive_install(repo: Path, keep_lint: bool) -> str:
    if (repo / "requirements-dev.txt").is_file():
        return "python3 -m pip install -r requirements-dev.txt"
    pyproject = repo / "pyproject.toml"
    if pyproject.is_file():
        import tomllib  # stdlib >=3.11; lazy per check-manifest-tag.py's pattern
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        project = data.get("project", {})
        if "version" in project and "dev" in project.get("optional-dependencies", {}):
            # A version-less pyproject is not pip-installable (the lesson from
            # claude-toolbox's own first red CI run) — hence the version check.
            return "python3 -m pip install -e '.[dev]'"
    base = "python3 -m pip install 'pytest>=8'"
    return (base + " 'ruff>=0.6'") if keep_lint else base


def derive_test(repo: Path) -> str | None:
    if (repo / "tests").is_dir():
        return "python3 -m pytest tests/ -q"
    return None


def _replace_line(text: str, old: str, new: str, count: int) -> str:
    """Replace an anchored seam; raise if the template drifted from the anchors."""
    found = text.count(old)
    if found != count:
        raise ValueError(f"anchor {old!r}: expected {count} occurrence(s), found {found}")
    return text.replace(old, new)


def render_test_yml(text: str, *, python: str, install: str, test: str,
                    lint: str | None) -> str:
    text = _replace_line(text, _PY_LINE, f'          python-version: "{python}"', 2)
    text = _replace_line(text, _INSTALL_LINE, f"        run: {install}", 1)
    text = _replace_line(text, _TEST_LINE, f"        run: {test}", 1)
    if lint is None:
        text = _replace_line(text, _LINT_BLOCK, "", 1)
    elif lint != "ruff check .":
        text = _replace_line(text, _LINT_RUN_LINE, f"        run: {lint}\n", 1)
    return text


def render_release_yml(text: str, *, python: str, install: str, test: str,
                       lint: str | None) -> str:
    """Same seams as test.yml — release.yml re-runs the gate on the tag.

    test.yml never fires on tags, so a tag pushed onto a broken tree would cut a
    release; stamping the install/test/lint lines here keeps the two gates on
    the same bar instead of leaving release.yml on the template's defaults.
    """
    text = _replace_line(text, _PY_LINE, f'          python-version: "{python}"', 1)
    text = _replace_line(text, _INSTALL_LINE, f"        run: {install}", 1)
    text = _replace_line(text, _TEST_LINE, f"        run: {test}", 1)
    if lint is None:
        text = _replace_line(text, _LINT_BLOCK, "", 1)
    elif lint != "ruff check .":
        text = _replace_line(text, _LINT_RUN_LINE, f"        run: {lint}\n", 1)
    return text


def stamped_header(version: str) -> str:
    """Provenance banner marking a file as stamp-OWNED, so re-stamping may replace it.

    Ownership is opt-out by deletion: a file without this header (hand-authored,
    or adopted by removing the banner) is skipped rather than overwritten. That
    is what stops `--write` from silently destroying repo-specific CI — ramp,
    for instance, needs a 3.8/3.13 matrix and a separate `lint` job that the
    single-job template does not express, and whose exact job names its branch
    protection requires by name.
    """
    return (f"{_STAMP_MARKER} v{version} — re-stamp to update.\n"
            "# Edits to this file are overwritten by the next `--write`. To take\n"
            "# repo-specific ownership, delete these three header lines: the\n"
            "# stamper then skips the file instead of replacing it.\n")


def is_stamp_owned(old: bytes | None) -> bool:
    """True when the stamp may write this path: absent, or previously stamped."""
    if old is None:
        return True
    text = old.decode("utf-8", "replace")
    return _STAMP_MARKER in text or _VENDOR_MARKER in text


def vendored_checker(src: str, version: str) -> str:
    """Byte-identical checker plus a provenance header after the shebang."""
    lines = src.splitlines(keepends=True)
    header = f"# vendored from claude-toolbox v{version} — re-stamp to update\n"
    return lines[0] + header + "".join(lines[1:])


def render_all(repo: Path, *, python: str, install: str, test: str,
               lint: str | None) -> dict[str, str]:
    """relpath -> rendered content for every file the stamp owns."""
    version = toolbox_version()
    header = stamped_header(version)
    out = {
        ".github/workflows/test.yml": header + render_test_yml(
            (_TEMPLATES / "workflows" / "test.yml").read_text(encoding="utf-8"),
            python=python, install=install, test=test, lint=lint),
        ".github/workflows/release.yml": header + render_release_yml(
            (_TEMPLATES / "workflows" / "release.yml").read_text(encoding="utf-8"),
            python=python, install=install, test=test, lint=lint),
        ".github/dependabot.yml": header +
            (_TEMPLATES / "dependabot.yml").read_text(encoding="utf-8"),
        # Carries _VENDOR_MARKER instead — its own provenance header predates
        # the stamp banner and is asserted byte-for-byte by the golden tests.
        ".github/scripts/check-manifest-tag.py": vendored_checker(
            _CHECKER_SRC.read_text(encoding="utf-8"), version),
    }
    # A CHANGELOG is living content, not a generated artifact: seed-only-if-missing.
    if not (repo / "CHANGELOG.md").is_file():
        out["CHANGELOG.md"] = (_TEMPLATES / "CHANGELOG-seed.md").read_text(encoding="utf-8")
    return out


def build_plan(repo: Path, rendered: dict[str, str]) -> list[tuple[str, bytes | None, bytes]]:
    """[(relpath, old_bytes | None, new_bytes)], identical-bytes entries dropped."""
    plan = []
    for rel, content in sorted(rendered.items()):
        new = content.encode("utf-8")
        existing = repo / rel
        old = existing.read_bytes() if existing.is_file() else None
        if old != new:
            plan.append((rel, old, new))
    return plan


def unified_diff(rel: str, old: bytes | None, new: bytes) -> str:
    old_lines = old.decode("utf-8").splitlines(keepends=True) if old is not None else []
    return "".join(difflib.unified_diff(
        old_lines, new.decode("utf-8").splitlines(keepends=True),
        fromfile="/dev/null" if old is None else f"a/{rel}",
        tofile=f"b/{rel}",
    ))


def target_manifest(repo: Path) -> str | None:
    """Relpath of the version manifest the vendored checker will read, or None.

    Delegates to check-manifest-tag.py's own read_manifest_version() (loaded via
    importlib — the checker is hyphenated) so the stamp's entry gate and the
    stamped CI gate can never disagree about what counts as a manifest. The
    stamped CI enforces manifest<->tag sync, so a target without a readable
    version is unstampable.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_manifest_tag", _CHECKER_SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        _version, rel = mod.read_manifest_version(repo)
        return rel
    except (FileNotFoundError, KeyError, ModuleNotFoundError, ValueError):
        # no manifest / versionless manifest / no tomllib (<3.11) / malformed
        # pyproject or plugin.json (TOMLDecodeError and JSONDecodeError both
        # subclass ValueError) — all mean "nothing the CI gate could read".
        return None


def main(argv: list[str]) -> int:
    import argparse
    import subprocess
    ap = argparse.ArgumentParser(
        description="Stamp git-policy CI files into a target repo (dry-run by default).")
    ap.add_argument("--repo", required=True, help="path to the target repo")
    ap.add_argument("--write", action="store_true",
                    help="write files into the target working tree (default: diff only)")
    ap.add_argument("--force", action="store_true",
                    help="also overwrite hand-authored files (those without the stamp "
                         "header); discards repo-specific CI customization")
    ap.add_argument("--python", help="override the derived python version")
    ap.add_argument("--install", help="override the derived install command")
    ap.add_argument("--test", help="override the derived test command")
    ap.add_argument("--lint", help="override the lint command (default: derived from ruff config)")
    args = ap.parse_args(argv)
    repo = Path(args.repo).resolve()

    probe = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True)
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        print(f"error: {repo} is not a git repository", file=sys.stderr)
        return 2
    if target_manifest(repo) is None:
        print(f"error: {repo} has no readable version manifest "
              "(.claude-plugin/plugin.json, versioned pyproject.toml, or package.json) — "
              "the stamped CI enforces manifest<->tag sync and needs one",
              file=sys.stderr)
        return 2

    try:
        lint = args.lint or ("ruff check ." if has_ruff_config(repo) else None)
        test = args.test or derive_test(repo)
        if test is None:
            print("error: no tests/ directory in the target — pass --test CMD "
                  "(a repo without tests must not get a silently-green CI gate)",
                  file=sys.stderr)
            return 2
        python = args.python or derive_python(repo)
        install = args.install or derive_install(repo, keep_lint=lint is not None)
        rendered = render_all(repo, python=python, install=install, test=test, lint=lint)
    except ValueError as e:
        # Anchor drift (_replace_line's ValueError) or a malformed target
        # pyproject (tomllib.TOMLDecodeError subclasses ValueError): structural
        # either way — exit 2, never a traceback / exit 1.
        print(f"error: {e}", file=sys.stderr)
        return 2

    plan = build_plan(repo, rendered)
    if not plan:
        print("Nothing to do — target already matches the stamped output.")
        return 0

    # Split before doing anything: a hand-authored file (no stamp header) is
    # skipped, not silently replaced. --force opts back into overwriting.
    if args.force:
        writable, skipped = plan, []
    else:
        writable = [entry for entry in plan if is_stamp_owned(entry[1])]
        skipped = [rel for rel, old, _new in plan if not is_stamp_owned(old)]

    if args.write:
        for rel, _old, new in writable:
            dest = repo / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(new)
        if writable:
            print(f"Wrote {len(writable)} file(s) into {repo}.")
            print(f"Review with `git -C {repo} diff` (+ untracked) and commit.")
        else:
            print("Wrote nothing — every changed file is hand-authored (see below).")
    else:
        for rel, old, new in writable:
            sys.stdout.write(unified_diff(rel, old, new))
        if writable:
            print(f"\nWould write {len(writable)} file(s). Re-run with --write to apply.")
        else:
            print("\nNothing writable — every changed file is hand-authored (see below).")

    if skipped:
        print(f"\nSkipped {len(skipped)} hand-authored file(s) — no "
              f"'{_STAMP_MARKER}' header, so the stamp does not own them:")
        for rel in skipped:
            print(f"  {rel}")
        print("Re-run with --force to overwrite them. That DISCARDS repo-specific\n"
              "CI: a customized test.yml may define jobs (e.g. a version matrix, or\n"
              "a separate `lint` job) whose names branch protection requires — "
              "replacing it can block every PR.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
