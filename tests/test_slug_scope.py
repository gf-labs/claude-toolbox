"""Tests for _slug.derive_scope_slug — the scope (not repo) → TW slug mapping.

`derive_slug` maps a REPO. Nothing enforced that, and pin's 'single' mode hands
it the session cwd, which for this toolbox's own sessions is `lib/tools/<tool>/`
— below the repo root. Under the `domain.repo` strategy that pairs the DOMAIN
with a non-repo basename and emits a slug matching zero tasks:

    ~/Repos/business/toolbox/lib/tools/workstation
      derive_slug       -> business.workstation   (0 tasks — nothing errors)
      derive_scope_slug -> toolbox.workstation    (the real project)

The failure is silent by construction, which is the whole reason it survived:
an empty backlog reads as "nothing queued", not as a lookup miss. These tests
pin the sub-repo rule and, just as importantly, that repo-root scopes still go
through `derive_slug` untouched.
"""
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _slug  # noqa: E402


def _repo(path: Path) -> Path:
    """A real git repo — derive_scope_slug resolves the root via git."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    return path


# ── the sub-repo rule ───────────────────────────────────────────────────────

def test_scope_below_repo_uses_repo_basename_and_scope_basename(tmp_path):
    # The reported bug, exactly: business.workstation -> toolbox.workstation.
    repos = tmp_path / "Repos"
    repo = _repo(repos / "business" / "toolbox")
    scope = repo / "lib" / "tools" / "workstation"
    scope.mkdir(parents=True)
    assert _slug.derive_scope_slug(
        scope, repo, repos_root=repos, strategy="domain.repo"
    ) == "toolbox.workstation"


def test_sub_scope_drops_the_domain(tmp_path):
    # NOT business.toolbox.workstation — the convention in use is <repo>.<tool>
    # (toolbox.workstation, toolbox.dot). Only the repo-root half varies by
    # strategy, so a sub-scope must read the same under either one.
    repos = tmp_path / "Repos"
    repo = _repo(repos / "business" / "toolbox")
    scope = repo / "lib" / "tools" / "dot"
    scope.mkdir(parents=True)
    for strategy in ("domain.repo", "basename"):
        assert _slug.derive_scope_slug(
            scope, repo, repos_root=repos, strategy=strategy
        ) == "toolbox.dot", strategy


def test_depth_below_repo_is_irrelevant(tmp_path):
    # Only the two basenames matter; the intervening path is not encoded.
    repos = tmp_path / "Repos"
    repo = _repo(repos / "business" / "toolbox")
    shallow = repo / "areas"
    deep = repo / "a" / "b" / "c" / "d" / "areas"
    shallow.mkdir(parents=True)
    deep.mkdir(parents=True)
    for scope in (shallow, deep):
        assert _slug.derive_scope_slug(
            scope, repo, repos_root=repos, strategy="domain.repo"
        ) == "toolbox.areas"


# ── repo-root scopes are unchanged ──────────────────────────────────────────

def test_repo_root_scope_falls_through_to_derive_slug(tmp_path):
    repos = tmp_path / "Repos"
    repo = _repo(repos / "business" / "toolbox")
    assert _slug.derive_scope_slug(
        repo, repo, repos_root=repos, strategy="domain.repo"
    ) == "business.toolbox"
    assert _slug.derive_scope_slug(
        repo, repo, repos_root=repos, strategy="basename"
    ) == "toolbox"


def test_repo_root_inside_a_container_still_skips_it(tmp_path):
    # The container rule belongs to derive_slug and must survive the delegation:
    # business/_claude-plugins/claude-toolbox -> business.claude-toolbox.
    repos = tmp_path / "Repos"
    repo = _repo(repos / "business" / "_claude-plugins" / "claude-toolbox")
    assert _slug.derive_scope_slug(
        repo, repo, repos_root=repos, strategy="domain.repo"
    ) == "business.claude-toolbox"


# ── degradation ─────────────────────────────────────────────────────────────

def test_no_repo_root_falls_back_to_derive_slug(tmp_path):
    # Not in a repo at all: behave exactly as before this function existed.
    repos = tmp_path / "Repos"
    loose = repos / "business" / "loose"
    loose.mkdir(parents=True)
    assert _slug.derive_scope_slug(
        loose, None, repos_root=repos, strategy="domain.repo"
    ) == "business.loose"


def test_scope_outside_the_given_repo_trusts_the_scope(tmp_path):
    # A caller can hand us a repo_root the scope is not under (stale cwd, a
    # nested checkout). Trust the scope rather than inventing <that repo>.<us>.
    repos = tmp_path / "Repos"
    repo = _repo(repos / "business" / "toolbox")
    other = repos / "personal" / "elsewhere"
    other.mkdir(parents=True)
    assert _slug.derive_scope_slug(
        other, repo, repos_root=repos, strategy="domain.repo"
    ) == "personal.elsewhere"


def test_repo_root_is_resolved_from_the_scope_when_omitted(tmp_path):
    # collect-pin passes the root it already has; other callers should not have
    # to. Omitted, it comes from `git rev-parse` run IN the scope dir.
    repos = tmp_path / "Repos"
    repo = _repo(repos / "business" / "toolbox")
    scope = repo / "lib" / "tools" / "notebook"
    scope.mkdir(parents=True)
    assert _slug.derive_scope_slug(
        scope, repos_root=repos, strategy="domain.repo"
    ) == "toolbox.notebook"


def test_derive_slug_itself_is_untouched(tmp_path):
    # The repo→slug contract keeps its old behavior, including the wrong answer
    # for a sub-repo path. That is not a bug in derive_slug — it is why callers
    # with a scope must use derive_scope_slug.
    repos = tmp_path / "Repos"
    repo = repos / "business" / "toolbox"
    scope = repo / "lib" / "tools" / "workstation"
    scope.mkdir(parents=True)
    assert _slug.derive_slug(
        scope, repos_root=repos, strategy="domain.repo"
    ) == "business.workstation"
