"""Guard that the git-policy CI templates keep their hardening invariants.

Asserted with regex (stdlib only — the suite has no YAML dependency): every
`uses:` is pinned to a 40-char commit SHA, no action floats on a tag/branch,
and each workflow declares a top-level `permissions:` block.
"""
from __future__ import annotations

import re
from pathlib import Path

WF_DIR = Path(__file__).resolve().parents[1] / "templates" / "git-policy" / "workflows"
WORKFLOWS = sorted(WF_DIR.glob("*.yml"))

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
