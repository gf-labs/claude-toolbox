"""Guard the git-policy CI templates: hardening invariants + release-notes logic.

Hardening (regex, stdlib only — the suite has no YAML dependency): every
`uses:` is pinned to a 40-char commit SHA, no action floats on a tag/branch,
and each workflow declares a top-level `permissions:` block.

Release notes: `release.yml` embeds the CHANGELOG-section extractor as an inline
heredoc. These tests pull that code out verbatim and run it against fixture
changelogs, so the fiddliest net-new CD artifact is behaviour-tested, not just
shape-checked.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

WF_DIR = Path(__file__).resolve().parents[1] / "templates" / "git-policy" / "workflows"
WORKFLOWS = sorted(WF_DIR.glob("*.yml"))
RELEASE_YML = WF_DIR / "release.yml"

USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)", re.M)
SHA_PINNED = re.compile(r"@[0-9a-f]{40}$")
FLOATING = re.compile(r"@(?:v?\d+(?:\.\d+)*|master|main|latest)$")


def test_workflow_templates_exist():
    assert WORKFLOWS, "expected at least one workflow template under templates/git-policy/workflows/"


def test_every_uses_is_sha_pinned():
    for wf in WORKFLOWS:
        for ref in USES.findall(wf.read_text(encoding="utf-8")):
            assert SHA_PINNED.search(ref), f"{wf.name}: {ref!r} is not SHA-pinned"
            assert not FLOATING.search(ref), f"{wf.name}: {ref!r} floats on a tag/branch"


def test_each_workflow_declares_permissions():
    for wf in WORKFLOWS:
        assert re.search(r"(?m)^permissions:", wf.read_text(encoding="utf-8")), \
            f"{wf.name}: no top-level permissions block"


# --- release.yml CHANGELOG-notes extraction (behaviour, not shape) ------------

def _extract_changelog_code() -> str:
    """Pull the CHANGELOG-notes extraction heredoc out of release.yml verbatim."""
    lines = RELEASE_YML.read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if "<<'PY'" in line]
    assert starts, "release.yml no longer contains the <<'PY' heredoc"
    start = starts[0]
    ends = [i for i in range(start + 1, len(lines)) if lines[i].strip() == "PY"]
    assert ends, "release.yml heredoc is not terminated by a PY line"
    return textwrap.dedent("\n".join(lines[start + 1:ends[0]]))


def _extract(changelog: str, tag: str) -> subprocess.CompletedProcess:
    """Run the extracted logic against a CHANGELOG fixture; return the result."""
    code = _extract_changelog_code()
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
        return subprocess.run([sys.executable, "-c", code, tag],
                              cwd=d, capture_output=True, text=True)


def _run_extract(changelog: str, tag: str) -> str:
    """stdout of a run that is expected to succeed."""
    r = _extract(changelog, tag)
    assert r.returncode == 0, r.stderr
    return r.stdout


_SAMPLE = """\
# Changelog

## [Unreleased]

### Added
- unreleased thing

## [1.2.0] — 2026-06-30

### Added
- the feature

## [1.1.0] — 2026-06-01

- older stuff
"""


def test_extract_pulls_the_matching_section_only():
    out = _run_extract(_SAMPLE, "v1.2.0")
    assert out.startswith("## [1.2.0]")
    assert "the feature" in out
    # Must stop at the next section boundary — no bleed into 1.1.0 or Unreleased.
    assert "older stuff" not in out
    assert "unreleased thing" not in out


def test_extract_strips_leading_v():
    assert _run_extract(_SAMPLE, "1.2.0").startswith("## [1.2.0]")


def test_extract_matches_unbracketed_heading():
    cl = "# Changelog\n\n## 2.0.0\n\n- bare heading\n"
    out = _run_extract(cl, "v2.0.0")
    assert out.startswith("## 2.0.0")
    assert "bare heading" in out


def test_extract_hard_fails_when_version_absent():
    """No matching section is a broken release, not a formatting nicety.

    This previously fell back to the literal string "Release 9.9.9" and shipped
    it as the entire Release body — e.g. when the changes were still parked
    under [Unreleased] at tag time. The failure was silent: green workflow,
    published Release, empty notes. It must fail loudly instead, before the
    Release is created.
    """
    r = _extract(_SAMPLE, "v9.9.9")
    assert r.returncode != 0
    assert "Release 9.9.9" not in r.stdout          # no placeholder body emitted
    assert "::error::" in r.stderr                  # annotated in the GH log
    assert "## [9.9.9]" in r.stderr                 # names the fix


# --- stamp seams: scripts/stamp-git-policy.py rewrites exactly these lines ----
# If one of these fails after a template edit, update the stamp's anchors too.

TEST_YML = WF_DIR / "test.yml"


def test_stamp_anchors_in_test_yml():
    text = TEST_YML.read_text(encoding="utf-8")
    assert text.count('          python-version: "3.12"') == 2
    assert text.count("        run: python3 -m pip install -e '.[dev]'") == 1
    assert text.count("        run: python3 -m pytest tests/ -q") == 1
    assert text.count("      - name: Lint\n        run: ruff check .\n") == 1


def test_stamp_anchors_in_release_yml():
    # release.yml re-runs the gate on the tag, so it carries the same
    # install/test/lint seams as test.yml — each exactly once.
    text = RELEASE_YML.read_text(encoding="utf-8")
    assert text.count('          python-version: "3.12"') == 1
    assert text.count("        run: python3 -m pip install -e '.[dev]'") == 1
    assert text.count("        run: python3 -m pytest tests/ -q") == 1
    assert text.count("      - name: Lint\n        run: ruff check .\n") == 1


def test_release_yml_hard_fails_on_missing_changelog_section():
    """The placeholder-notes fallback must stay gone.

    `("## " + note) if note else f"Release {ver}"` silently published a Release
    whose entire body was "Release X.Y.Z" when the CHANGELOG had no matching
    section — a broken release that looked successful.
    """
    text = RELEASE_YML.read_text(encoding="utf-8")
    assert 'f"Release {ver}"' not in text
    assert "::error::No CHANGELOG.md section for" in text


def test_workflows_gate_prs_into_develop():
    """Integration PRs must be gated, not just the ones into main."""
    text = TEST_YML.read_text(encoding="utf-8")
    assert "branches: [main, develop]" in text


def test_templates_use_vendored_checker_path():
    # Stamped repos always vendor to .github/scripts/ — the templates must
    # already say so verbatim (no checker-path replacement exists in the stamp).
    for wf in WORKFLOWS:
        text = wf.read_text(encoding="utf-8")
        if "check-manifest-tag" in text:
            assert ".github/scripts/check-manifest-tag.py" in text
