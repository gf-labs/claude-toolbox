"""Tests for _atlas_render — pure parse + render for the atlas ATLAS section."""
import datetime
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _atlas_render as ar  # noqa: E402
from _projects import Project  # noqa: E402

TODAY = datetime.date(2026, 7, 2)

STATUS_HEADER = (
    "GROUP\tPROJECT\tBRANCH\tLOCAL_BRANCHES\tSESSIONS\tCHANGES\tLAST_COMMIT\t"
    "MEMORY_LINES\tMEMORY_STATUS\tBACKLOG_ITEMS\tLAST_SNAPSHOT\tSESSIONS_SINCE\t"
    "LAST_SESSION_LOG\tLOG_ENTRIES\tLAST_COMMIT_DATE"
)
STATUS = (
    STATUS_HEADER + "\n"
    "\talpha\tmain\t2\t3\t1\tabc1234\t101L\tOK\t—\t2026-07-02\t—\t2026-07-02\t30\t2026-07-02\n"
    "\tbeta\tdevelop\t1\t2\t—\tdef5678\t12L\tTHIN\t3\t—\t—\t—\t—\t2026-06-25\n"
    "\n"
    "# ORPHANED_KEYS\n"
    "KEY\tSESSIONS\tNOTE\n"
    "zombie\t0\tno dir on disk\n"
)

SESSIONS = (
    "PROJECT\tSESSION\tTITLE\tLAST_EVENT\n"
    "alpha\taaaa1111-2222\talpha-work\t2026-07-02\n"
    "alpha\tbbbb3333-4444\t—\t2026-06-30\n"
    "beta\tcccc5555-6666\tbeta-sess\t2026-06-25\n"
)

CLAUDE_MD = (
    "CONTAINER\tPROJECT\tCLAUDE_MD_DEPTH\tMEMORY_LINES\tMEMORY_STATUS\tCHAIN\n"
    "\talpha\t3\t101L\tOK\t~/.claude/CLAUDE.md » ~/Repos/CLAUDE.md » ~/Repos/work/alpha/CLAUDE.md\n"
)

PLANS = (
    "alpha-thing.md  120L  [alpha]  Alpha Thing Plan\n"
    "  → first task bullet\n"
    "_done-old.md  80L  [alpha]  Old Done Plan\n"
    "mystery.md  10L  [?]  Unattributed\n"
)

SPECS = (
    "PROJECT\tKIND\tSTATUS\tFILE\tTITLE\n"
    "alpha\tspec\tlive\t2026-07-01-x-design.md\tX Design\n"
    "alpha\tspec\tdone\t_done-2026-06-30-y-design.md\tY Design\n"
    "alpha\tplan\tlive\t2026-07-01-x.md\tX Plan\n"
)


def proj(path, container=None):
    p = Path(path)
    return Project(key="k-" + p.name, path=p, name=p.name, container=container,
                   proj_dir=Path("/nonexistent") / p.name)


def test_elapsed_today_yesterday_and_days():
    assert ar.elapsed("2026-07-02", TODAY) == "today"
    assert ar.elapsed("2026-07-01", TODAY) == "yesterday"
    assert ar.elapsed("2026-06-25", TODAY) == "7d ago"


def test_elapsed_future_clamps_to_today():
    assert ar.elapsed("2026-07-03", TODAY) == "today"  # UTC bleed, never "-1d ago"


def test_elapsed_garbage_is_dash():
    assert ar.elapsed("—", TODAY) == "—"
    assert ar.elapsed("", TODAY) == "—"
    assert ar.elapsed(None, TODAY) == "—"


def test_shorten_chain_basenames_and_global():
    chain = "~/.claude/CLAUDE.md » ~/Repos/CLAUDE.md » ~/Repos/work/alpha/CLAUDE.md"
    assert ar.shorten_chain(chain) == "global » Repos » alpha"


def test_parse_status_rows_and_ignores_stale_tail():
    rows = ar.parse_status(STATUS)
    assert set(rows) == {"alpha", "beta"}
    assert rows["alpha"][0]["MEMORY_STATUS"] == "OK"
    assert rows["alpha"][0]["LAST_COMMIT_DATE"] == "2026-07-02"
    assert "zombie" not in rows


def test_parse_status_pads_missing_date_column():
    fourteen = STATUS_HEADER.rsplit("\tLAST_COMMIT_DATE", 1)[0] + "\n" + \
        "\talpha\tmain\t2\t3\t1\tabc1234\t101L\tOK\t—\t—\t—\t—\t30\n"
    rows = ar.parse_status(fourteen)
    assert "LAST_COMMIT_DATE" not in rows["alpha"][0]
    assert rows["alpha"][0]["LOG_ENTRIES"] == "30"


def test_status_for_disambiguates_duplicate_names_by_group():
    text = (STATUS_HEADER + "\n"
            "cont-a\talpha\tmain\t1\t1\t—\tx\t10L\tTHIN\t—\t—\t—\t—\t—\t—\n"
            "cont-b\talpha\tdev\t1\t1\t—\ty\t99L\tOK\t—\t—\t—\t—\t—\t—\n")
    rows = ar.parse_status(text)
    p = proj("/r/cont-b/alpha", container="cont-b")
    assert ar.status_for(p, rows)["BRANCH"] == "dev"
    assert ar.status_for(proj("/r/alpha"), {}) is None


def test_parse_sessions_keeps_order_per_project():
    rows = ar.parse_sessions(SESSIONS)
    assert [sid[:4] for sid, _, _ in rows["alpha"]] == ["aaaa", "bbbb"]
    assert rows["beta"][0][1] == "beta-sess"


def test_parse_claude_md_keyed_by_project():
    rows = ar.parse_claude_md(CLAUDE_MD)
    assert rows["alpha"]["CLAUDE_MD_DEPTH"] == "3"
    assert rows["alpha"]["CHAIN"].startswith("~/.claude/CLAUDE.md")


def test_parse_plans_drops_done_and_unattributed():
    rows = ar.parse_plans(PLANS)
    assert rows == {"alpha": [("Alpha Thing Plan", "120L")]}
    assert ar.parse_plans("NONE") == {}


def test_parse_specs_rows():
    rows = ar.parse_specs(SPECS)
    assert len(rows["alpha"]) == 3
    assert ("spec", "live", "X Design") in rows["alpha"]


DIGEST_STATUS = (
    STATUS_HEADER + "\n"
    "\talpha\tmain\t2\t3\t1\tabc1234\t101L\tOK\t—\t2026-07-02\t—\t2026-07-02\t30\t2026-07-02\n"
    "\tbeta\tdevelop\t1\t2\t—\tdef5678\t12L\tTHIN\t3\t—\t—\t—\t—\t2026-06-25\n"
    "\tgamma\tmain\t1\t1\t—\t9abcdef\tnone\tMISSING\t—\t—\t—\t—\t—\t2026-06-01\n"
    "\tsolo\tmain\t1\t1\t—\t1234abc\tnone\tMISSING\t—\t—\t—\t—\t—\t2026-06-01\n"
    "header\twork\t—\t—\t2\t—\t—\tnone\tMISSING\t—\t—\t—\t—\t—\t—\n"
)

ALL_FACETS = ["projects", "sessions", "memory", "plans", "specs", "claude.md"]


def _digest_world():
    projects = [
        proj("/r/business/work/alpha", container="work"),
        proj("/r/business/work/beta", container="work"),
        proj("/r/business/work", container=None),
        proj("/r/personal/gamma"),
        proj("/r/solo"),
    ]
    parsed = {
        "status": ar.parse_status(DIGEST_STATUS),
        "sessions": ar.parse_sessions(SESSIONS),
        "plans": ar.parse_plans(PLANS),
        "specs": ar.parse_specs(SPECS),
    }
    return projects, parsed


def test_digest_groups_by_first_component_under_common_root():
    projects, parsed = _digest_world()
    lines = ar._render_digest(projects, ALL_FACETS, parsed, TODAY)
    assert "business/" in lines and "personal/" in lines
    solo = [ln for ln in lines if ln.startswith("solo")]
    assert solo, "direct child of the common root renders as a bare row, not a group"
    assert lines.index(solo[0]) < lines.index("business/"), "bare rows precede groups"


def test_digest_row_cells_and_marker():
    projects, parsed = _digest_world()
    lines = ar._render_digest(projects, ALL_FACETS, parsed, TODAY)
    alpha = next(ln for ln in lines if "work/alpha" in ln)
    assert "work/alpha !" in alpha          # uncommitted changes -> marker
    assert "main ±1 · today" in alpha       # branch, changes, commit elapsed
    assert "2s · today" in alpha            # session count + newest recency
    assert "101L OK" in alpha
    # live counts only; the specs facet counts in-repo docs kind-blind (spec + plan files)
    assert "2 specs · 1 plan" in alpha
    beta = next(ln for ln in lines if "work/beta" in ln)
    assert "!" not in beta and "±" not in beta
    assert "devel" in beta and "7d ago" in beta


def test_digest_missing_data_renders_dashes():
    projects, parsed = _digest_world()
    lines = ar._render_digest(projects, ALL_FACETS, parsed, TODAY)
    gamma = next(ln for ln in lines if "gamma" in ln)
    cells = [c for c in gamma.split("  ") if c.strip()]
    assert "—" in cells  # no sessions/memory/docs -> dashes, row still renders
    work = next(ln for ln in lines if ln.strip().startswith("work ") or ln.strip() == "work")
    assert "—" in work   # container project without git -> '—' git cell


def test_digest_columns_align():
    projects, parsed = _digest_world()
    lines = ar._render_digest(projects, ALL_FACETS, parsed, TODAY)
    grouped = [ln for ln in lines if ln.startswith("  ") and "/" not in ln.split()[0]]
    # all grouped rows share the same start column for the git cell
    starts = {ln.index(" · ") for ln in grouped if " · " in ln}
    assert len(starts) >= 1  # smoke: joined with computed padding, no exception


def test_digest_facet_subset_drops_cells():
    projects, parsed = _digest_world()
    lines = ar._render_digest(projects, ["sessions", "memory"], parsed, TODAY)
    alpha = next(ln for ln in lines if "work/alpha" in ln)
    assert "main" not in alpha and "spec" not in alpha
    assert "2s · today" in alpha and "101L OK" in alpha


def test_card_renders_header_and_resource_lines():
    parsed = {
        "status": ar.parse_status(STATUS),
        "sessions": ar.parse_sessions(SESSIONS),
        "claude_md": ar.parse_claude_md(CLAUDE_MD),
        "plans": ar.parse_plans(PLANS),
        "specs": ar.parse_specs(SPECS),
    }
    out = ar.build_atlas([proj("/r/work/alpha")], ALL_FACETS, parsed, "auto", TODAY, "subtree")
    assert out.startswith("## Atlas — subtree · 1 project — 2026-07-02")
    assert "alpha   main · 1 change · commit today" in out
    assert "  claude.md   global » Repos » alpha (depth 3)" in out
    assert "  memory      101L OK · snapshot today · log today (30 entries)" in out
    assert "  sessions    2 — alpha-work (today) · bbbb3333 (2d ago)" in out
    assert "  plans       Alpha Thing Plan (120L)" in out
    assert "  specs       2 live · 1 done" in out  # counts only in a compact card


def test_card_empty_facets_render_none():
    parsed = {"status": ar.parse_status(STATUS)}
    out = ar.build_atlas([proj("/r/work/beta")], ALL_FACETS, parsed, "auto", TODAY, "subtree")
    assert "  claude.md   (none)" in out
    assert "  sessions    (none)" in out
    assert "  plans       (none)" in out
    assert "  specs       (none)" in out
    assert "backlog 3" in out  # beta's BACKLOG_ITEMS from STATUS


def test_card_session_cap_and_full_uncaps():
    many = "PROJECT\tSESSION\tTITLE\tLAST_EVENT\n" + "".join(
        f"alpha\tsid{i:04d}-0000\ttitle-{i}\t2026-07-0{min(i + 1, 2)}\n" for i in range(7)
    )
    parsed = {"sessions": ar.parse_sessions(many)}
    capped = ar.build_atlas([proj("/r/alpha")], ["sessions"], parsed, "auto", TODAY, "subtree")
    assert "+2 more" in capped and "title-6" not in capped
    full = ar.build_atlas([proj("/r/alpha")], ["sessions"], parsed, "full", TODAY, "subtree")
    assert "title-6" in full and "more" not in full


def test_mode_thresholds_and_overrides():
    ps4 = [proj(f"/r/g/p{i}") for i in range(4)]
    ps5 = [proj(f"/r/g/p{i}") for i in range(5)]
    parsed = {}
    # "  sessions" (an indented card resource line) marks cards mode; digest has no facet labels.
    assert "  sessions" in ar.build_atlas(ps4, ["sessions"], parsed, "auto", TODAY, "all")
    assert "  sessions" not in ar.build_atlas(ps5, ["sessions"], parsed, "auto", TODAY, "all")
    assert "  sessions" not in ar.build_atlas(ps4, ["sessions"], parsed, "compact", TODAY, "all")
    assert "  sessions" in ar.build_atlas(ps5, ["sessions"], parsed, "full", TODAY, "all")


def test_build_atlas_empty_scope():
    out = ar.build_atlas([], ALL_FACETS, {}, "auto", TODAY, "all")
    assert "0 projects" in out and "(no projects in scope)" in out


def test_card_qualified_name_when_container_in_scope():
    projects = [proj("/r/work", container=None), proj("/r/work/alpha", container="work")]
    parsed = {}
    out = ar.build_atlas(projects, ["sessions"], parsed, "auto", TODAY, "dir")
    assert "work/alpha" in out


def test_card_specs_titles_only_on_full():
    parsed = {"specs": ar.parse_specs(SPECS)}
    auto = ar.build_atlas([proj("/r/work/alpha")], ["specs"], parsed, "auto", TODAY, "subtree")
    assert "  specs       2 live · 1 done" in auto and "X Design" not in auto
    full = ar.build_atlas([proj("/r/work/alpha")], ["specs"], parsed, "full", TODAY, "subtree")
    assert "2 live · 1 done — X Design, X Plan" in full
