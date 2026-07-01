import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "collect-tasks.py"


def load_module():
    spec = importlib.util.spec_from_file_location("collect_tasks", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def m():
    return load_module()


# ── derive_slug ─────────────────────────────────────────────────────────────
# Mechanism (public) default = basename; the `domain.repo` strategy is opt-in
# policy, supplied either by explicit arg or by the CLAUDE_TOOLBOX_* env vars.

def test_derive_slug_default_is_basename(tmp_path, m, monkeypatch):
    # Even with a repos_root, the default strategy is basename — no assumption
    # that tasks should be filed under <domain>.<repo>.
    monkeypatch.delenv("CLAUDE_TOOLBOX_SLUG_STRATEGY", raising=False)
    monkeypatch.delenv("CLAUDE_TOOLBOX_REPOS_ROOT", raising=False)
    repos = tmp_path / "Repos"
    repo = repos / "business" / "toolbox"
    repo.mkdir(parents=True)
    assert m.derive_slug(repo, repos_root=repos) == "toolbox"


def test_derive_slug_env_policy(tmp_path, m, monkeypatch):
    # Policy via env: strategy + repos_root from the environment → domain.repo.
    repos = tmp_path / "Repos"
    repo = repos / "business" / "toolbox"
    repo.mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_TOOLBOX_SLUG_STRATEGY", "domain.repo")
    monkeypatch.setenv("CLAUDE_TOOLBOX_REPOS_ROOT", str(repos))
    assert m.derive_slug(repo) == "business.toolbox"


def test_derive_slug_two_levels(tmp_path, m):
    repos = tmp_path / "Repos"
    repo = repos / "business" / "toolbox"
    repo.mkdir(parents=True)
    assert m.derive_slug(repo, repos_root=repos, strategy="domain.repo") == "business.toolbox"


def test_derive_slug_three_levels_container(tmp_path, m):
    # A `_container/` between domain and repo (e.g. business/_claude-plugins/gfl-marketplace)
    # must still slug as domain.repo (basename) — matching the read-path TW_PROJECT used by
    # the commands and collect-pin.py. domain.container orphans tasks (TBX-I-9).
    repos = tmp_path / "Repos"
    repo = repos / "business" / "_claude-plugins" / "gfl-marketplace"
    repo.mkdir(parents=True)
    assert m.derive_slug(repo, repos_root=repos, strategy="domain.repo") == "business.gfl-marketplace"


def test_derive_slug_one_level(tmp_path, m):
    repos = tmp_path / "Repos"
    repo = repos / "toolbox"
    repo.mkdir(parents=True)
    assert m.derive_slug(repo, repos_root=repos, strategy="domain.repo") == "toolbox"


def test_derive_slug_outside_repos(tmp_path, m):
    repo = tmp_path / "some" / "other" / "path"
    repo.mkdir(parents=True)
    # Falls back to repo name when not under repos_root, even with the strategy on.
    assert m.derive_slug(repo, repos_root=tmp_path / "Repos", strategy="domain.repo") == "path"


# ── find_git_repos ───────────────────────────────────────────────────────────

def test_find_git_repos_descends_containers(tmp_path, m):
    # `_name/` containers must NOT consume a depth level — a plugin repo nested
    # at domain/_container/repo (depth 3) stays discoverable. Regression guard for
    # the business/_claude-plugins/ collapse.
    root = tmp_path / "Repos"
    plain = root / "learn" / "course"                       # depth 2, plain
    nested = root / "business" / "_claude-plugins" / "ramp"  # depth 3, via container
    for r in (plain, nested):
        (r / ".git").mkdir(parents=True)
    found = {p.name for p in m.find_git_repos(root)}
    assert found == {"course", "ramp"}


def test_find_git_repos_skips_dot_dirs(tmp_path, m):
    # `.name/` dormant dirs are skipped entirely (taxonomy hidden convention).
    root = tmp_path / "Repos"
    (root / ".archive" / "dead-repo" / ".git").mkdir(parents=True)
    (root / "live" / ".git").mkdir(parents=True)
    found = {p.name for p in m.find_git_repos(root)}
    assert found == {"live"}


# ── is_tombstoned ────────────────────────────────────────────────────────────

def test_is_tombstoned_true(tmp_path, m):
    f = tmp_path / "BACKLOG.md"
    f.write_text("Tasks tracked in TaskWarrior — run `task project:foo list`\n")
    assert m.is_tombstoned(f) is True


def test_is_tombstoned_false(tmp_path, m):
    f = tmp_path / "BACKLOG.md"
    f.write_text("- [ ] some task\n")
    assert m.is_tombstoned(f) is False


def test_is_tombstoned_missing(tmp_path, m):
    assert m.is_tombstoned(tmp_path / "MISSING.md") is False


# ── load_tw_slugs ─────────────────────────────────────────────────────────────

def test_load_tw_slugs_present(tmp_path, m):
    (tmp_path / ".tw-slugs.json").write_text('{"docs/dot.md": "business.toolbox.dot"}')
    assert m.load_tw_slugs(tmp_path) == {"docs/dot.md": "business.toolbox.dot"}


def test_load_tw_slugs_absent(tmp_path, m):
    assert m.load_tw_slugs(tmp_path) == {}


def test_load_tw_slugs_malformed(tmp_path, m):
    (tmp_path / ".tw-slugs.json").write_text("not json")
    assert m.load_tw_slugs(tmp_path) == {}


# ── match_slug ────────────────────────────────────────────────────────────────

def test_match_slug_exact(tmp_path, m):
    slugs = {"docs/dot.md": "business.toolbox.dot"}
    f = tmp_path / "docs" / "dot.md"
    f.parent.mkdir()
    f.touch()
    assert m.match_slug(f, tmp_path, slugs, "business.toolbox") == "business.toolbox.dot"


def test_match_slug_glob(tmp_path, m):
    slugs = {"docs/**": "business.toolbox.sub"}
    f = tmp_path / "docs" / "nested" / "file.md"
    f.parent.mkdir(parents=True)
    f.touch()
    assert m.match_slug(f, tmp_path, slugs, "business.toolbox") == "business.toolbox.sub"


def test_match_slug_no_match(tmp_path, m):
    f = tmp_path / "BACKLOG.md"
    f.touch()
    assert m.match_slug(f, tmp_path, {}, "business.toolbox") == "business.toolbox"


def test_match_slug_first_wins(tmp_path, m):
    slugs = {"docs/*.md": "first", "docs/dot.md": "second"}
    f = tmp_path / "docs" / "dot.md"
    f.parent.mkdir()
    f.touch()
    assert m.match_slug(f, tmp_path, slugs, "default") == "first"


# ── infer_tag / infer_size ────────────────────────────────────────────────────

def test_infer_tag_bug(m):
    assert m.infer_tag("fix the broken login") == "bug"


def test_infer_tag_research(m):
    assert m.infer_tag("investigate memory usage") == "research"


def test_infer_tag_default(m):
    assert m.infer_tag("add new widget") == "task"


def test_infer_size_xs(m):
    assert m.infer_size("trivial rename") == "XS"


def test_infer_size_large(m):
    assert m.infer_size("large architecture overhaul") == "L"


def test_infer_size_default(m):
    assert m.infer_size("implement new feature") == "S"


# ── parse_sections ────────────────────────────────────────────────────────────

def test_parse_sections_empty(m):
    sections = m.parse_sections("")
    assert len(sections) == 1
    assert sections[0]["heading"] is None


def test_parse_sections_with_headings(m):
    text = "intro\n## Active\n- task\n## Done\n- old\n"
    sections = m.parse_sections(text)
    assert len(sections) == 3  # preamble, Active, Done
    assert sections[0]["heading"] is None
    assert sections[1]["heading"] == "Active"
    assert sections[2]["heading"] == "Done"
    assert "- task" in sections[1]["lines"]


def test_parse_sections_level(m):
    sections = m.parse_sections("### Deep\ncontent\n")
    assert sections[1]["level"] == 3


# ── is_skip_section ───────────────────────────────────────────────────────────

def test_is_skip_section_done(m):
    assert m.is_skip_section("Done") is True


def test_is_skip_section_shipped(m):
    assert m.is_skip_section("v1.2 Shipped") is True


def test_is_skip_section_active(m):
    assert m.is_skip_section("Active") is False


def test_is_skip_section_none(m):
    assert m.is_skip_section(None) is False


# ── has_planning_heading ──────────────────────────────────────────────────────

def test_has_planning_heading_true(m):
    assert m.has_planning_heading("## Backlog\n- item\n") is True


def test_has_planning_heading_false(m):
    assert m.has_planning_heading("## Introduction\nsome text\n") is False


def test_has_planning_heading_case_insensitive(m):
    assert m.has_planning_heading("## UP NEXT\n- item\n") is True


# ── extract_items_from_lines ──────────────────────────────────────────────────

def test_extract_unchecked_checklist(m):
    assert m.extract_items_from_lines(["- [ ] do the thing"]) == ["do the thing"]


def test_extract_skips_checked(m):
    assert m.extract_items_from_lines(["- [x] already done"]) == []


def test_extract_bare_list(m):
    assert m.extract_items_from_lines(["- add feature"]) == ["add feature"]


def test_extract_skips_completion_marker(m):
    assert m.extract_items_from_lines(["- **Done** — shipped"]) == []
    assert m.extract_items_from_lines(["- **Cancelled** reason"]) == []


def test_extract_skips_strikethrough(m):
    assert m.extract_items_from_lines(["- ~~old task~~"]) == []


# ── find_tracking_files ───────────────────────────────────────────────────────

def test_find_tracking_files_root_level(tmp_path, m):
    (tmp_path / "BACKLOG.md").write_text("- [ ] task\n")
    found = m.find_tracking_files(tmp_path)
    assert tmp_path / "BACKLOG.md" in found


def test_find_tracking_files_skips_tombstoned(tmp_path, m):
    (tmp_path / "BACKLOG.md").write_text(
        "Tasks tracked in TaskWarrior — run `task project:x list`\n"
    )
    found = m.find_tracking_files(tmp_path)
    assert tmp_path / "BACKLOG.md" not in found


def test_find_tracking_files_readme_with_planning(tmp_path, m):
    (tmp_path / "README.md").write_text("## Backlog\n- [ ] task\n")
    found = m.find_tracking_files(tmp_path)
    assert tmp_path / "README.md" in found


def test_find_tracking_files_readme_without_planning(tmp_path, m):
    (tmp_path / "README.md").write_text("## Introduction\nsome text\n")
    found = m.find_tracking_files(tmp_path)
    assert tmp_path / "README.md" not in found


def test_find_tracking_files_docs_subdir(tmp_path, m):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "dot.md").write_text("## Active\n- [ ] task\n")
    found = m.find_tracking_files(tmp_path)
    assert docs / "dot.md" in found


def test_find_tracking_files_symlink_dedup(tmp_path, m):
    """find_tracking_files does not return the same file twice via symlink."""
    repo = tmp_path / "repo"
    repo.mkdir()
    backlog = repo / "BACKLOG.md"
    backlog.write_text("- item\n")
    docs = repo / "docs"
    docs.mkdir()
    link = docs / "BACKLOG.md"
    link.symlink_to(backlog)
    candidates = m.find_tracking_files(repo)
    resolved = [c.resolve() for c in candidates]
    assert len(resolved) == len(set(str(p) for p in resolved)), "Duplicate file found via symlink"


# ── collect_markdown_items ────────────────────────────────────────────────────

def test_collect_markdown_items_extracts(tmp_path, m):
    f = tmp_path / "BACKLOG.md"
    f.write_text("## Active\n- [ ] do a thing\n## Done\n- [ ] old thing\n")
    items = m.collect_markdown_items(f, tmp_path, {}, "test.repo")
    descriptions = [i["description"] for i in items]
    assert "do a thing" in descriptions
    assert "old thing" not in descriptions  # Done section skipped


def test_collect_markdown_items_slug_routing(tmp_path, m):
    docs = tmp_path / "docs"
    docs.mkdir()
    f = docs / "dot.md"
    f.write_text("## Active\n- [ ] configure dot\n")
    items = m.collect_markdown_items(
        f, tmp_path, {"docs/dot.md": "business.toolbox.dot"}, "business.toolbox"
    )
    assert items[0]["inferred_slug"] == "business.toolbox.dot"


def test_collect_markdown_items_fields(tmp_path, m):
    f = tmp_path / "BACKLOG.md"
    f.write_text("## Active\n- [ ] fix broken thing\n")
    items = m.collect_markdown_items(f, tmp_path, {}, "test.repo")
    assert len(items) == 1
    item = items[0]
    assert item["source_type"] == "markdown"
    assert item["status"] == "proposed"
    assert item["inferred_tag"] == "bug"  # "fix" + "broken" → bug
    assert "id" in item  # uuid present


def test_collect_markdown_items_outside_repo_extracts(tmp_path, m):
    """collect_markdown_items handles files outside repo_path without crashing."""
    other = tmp_path / "other"
    other.mkdir()
    f = other / "BACKLOG.md"
    f.write_text("## Active\n- [ ] task\n")
    items = m.collect_markdown_items(f, tmp_path, {}, "test.repo")
    assert len(items) == 1  # still extracts items


# ── get_exclude_patterns + find_tracking_files exclude ───────────────────────

def test_get_exclude_patterns_returns_list(m):
    assert m.get_exclude_patterns({"exclude": ["docs/foo.md"]}) == ["docs/foo.md"]


def test_get_exclude_patterns_missing_key(m):
    assert m.get_exclude_patterns({}) == []


def test_get_exclude_patterns_non_list(m):
    assert m.get_exclude_patterns({"exclude": "bad"}) == []


def test_find_tracking_files_respects_exclude(tmp_path, m):
    """Docs files matching 'exclude' patterns in .tw-slugs.json are not returned."""
    docs = tmp_path / "docs"
    docs.mkdir()
    included = docs / "backlog.md"
    excluded = docs / "handoff-notes.md"
    included.write_text("## Active\n- [ ] real task\n")
    excluded.write_text("## Active\n- [ ] false positive\n")
    # Write .tw-slugs.json with an exclude pattern
    (tmp_path / ".tw-slugs.json").write_text(
        '{"exclude": ["docs/handoff-*.md"]}'
    )

    found = m.find_tracking_files(tmp_path)
    paths = [f.name for f in found]
    assert "backlog.md" in paths
    assert "handoff-notes.md" not in paths


def test_collect_markdown_items_outside_repo_absolute_fallback(tmp_path, m):
    """collect_markdown_items falls back to absolute path if file is outside repo_path."""
    repo = tmp_path / "repo"
    repo.mkdir()
    external = tmp_path / "external.md"
    external.write_text("- some task\n")
    items = m.collect_markdown_items(external, repo, {}, "test.slug")
    assert len(items) == 1
    assert items[0]["source_file"] == str(external)


# ── fenced code block safety ──────────────────────────────────────────────────

def test_has_planning_heading_ignores_code_block(m):
    """# TODO inside a fenced block must not trigger planning-heading detection."""
    text = "## Introduction\n```\n# TODO: fix this\n```\n"
    assert m.has_planning_heading(text) is False


def test_has_planning_heading_detects_outside_fence(m):
    """## Backlog outside a fenced block is still detected."""
    text = "```\n# not a heading\n```\n## Backlog\n- item\n"
    assert m.has_planning_heading(text) is True


def test_parse_sections_ignores_hash_in_code_block(m):
    """# comment inside a fenced block must not create a new section."""
    text = "## Active\n```bash\n# install deps\n```\n- real task\n"
    sections = m.parse_sections(text)
    # Should be: preamble + Active (with the code block and task line)
    assert len(sections) == 2
    assert sections[1]["heading"] == "Active"
    # The # line must be inside the Active section, not a new section
    headings = [s["heading"] for s in sections]
    assert "install deps" not in headings


def test_parse_sections_tilde_fence(m):
    """~~~ fenced blocks are also respected."""
    text = "## Active\n~~~\n# not a heading\n~~~\n- task\n"
    sections = m.parse_sections(text)
    assert len(sections) == 2


# ── nested subsection skip ────────────────────────────────────────────────────

def test_collect_markdown_nested_subsection_skipped(tmp_path, m):
    """Subsections nested under a skip heading must not be extracted."""
    f = tmp_path / "BACKLOG.md"
    f.write_text(
        "## Active\n- [ ] keep me\n"
        "## Shipped\n### Phase 1\n- [ ] old work\n"
        "## Next\n- [ ] also keep me\n"
    )
    items = m.collect_markdown_items(f, tmp_path, {}, "test.repo")
    descriptions = [i["description"] for i in items]
    assert "keep me" in descriptions
    assert "also keep me" in descriptions
    assert "old work" not in descriptions


def test_collect_markdown_skip_clears_at_sibling(tmp_path, m):
    """A sibling heading after a skip heading re-enables extraction."""
    f = tmp_path / "BACKLOG.md"
    f.write_text(
        "## Done\n- [ ] skip this\n"
        "## Active\n- [ ] keep this\n"
    )
    items = m.collect_markdown_items(f, tmp_path, {}, "test.repo")
    descriptions = [i["description"] for i in items]
    assert "keep this" in descriptions
    assert "skip this" not in descriptions


# ── checkboxes_only (docs/ vs root-level) ────────────────────────────────────

def test_extract_bare_ignored_when_checkboxes_only(m):
    lines = ["- bare bullet", "- [ ] checkbox item"]
    assert m.extract_items_from_lines(lines, checkboxes_only=True) == ["checkbox item"]


def test_extract_bare_included_when_not_checkboxes_only(m):
    lines = ["- bare bullet", "- [ ] checkbox item"]
    result = m.extract_items_from_lines(lines, checkboxes_only=False)
    assert "bare bullet" in result
    assert "checkbox item" in result


def test_docs_file_uses_checkboxes_only(tmp_path, m):
    """Files under docs/ extract only checkbox items, not bare bullets."""
    docs = tmp_path / "docs"
    docs.mkdir()
    f = docs / "planning.md"
    f.write_text("## Active\n- bare prose item\n- [ ] real task\n")
    items = m.collect_markdown_items(f, tmp_path, {}, "test.repo")
    descriptions = [i["description"] for i in items]
    assert "real task" in descriptions
    assert "bare prose item" not in descriptions


def test_root_file_includes_bare_bullets(tmp_path, m):
    """Root-level BACKLOG.md includes bare bullet items."""
    f = tmp_path / "BACKLOG.md"
    f.write_text("## Active\n- bare task\n- [ ] checkbox task\n")
    items = m.collect_markdown_items(f, tmp_path, {}, "test.repo")
    descriptions = [i["description"] for i in items]
    assert "bare task" in descriptions
    assert "checkbox task" in descriptions
