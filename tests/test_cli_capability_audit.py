"""Tests for the cli-capability-audit skill's bundled scripts (stdlib-only).

Both scripts are regex-driven parsers, and their characteristic failure is a
pattern that looks correct and silently under-matches — producing a plausible
wrong answer rather than an error. The regression cases below are the ones that
actually shipped broken; keep them.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

_SKILL = (Path(__file__).resolve().parents[1]
          / "skills" / "cli-capability-audit" / "scripts")
_EXTRACT = _SKILL / "extract-surface.py"
_DIFF = _SKILL / "diff-surface.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


extract = _load("extract_surface", _EXTRACT)
diff = _load("diff_surface", _DIFF)


def _names(hits: list[dict]) -> set[str]:
    return {h["name"] for h in hits}


# --- extract: bash ------------------------------------------------------------

BASH = """\
#!/bin/bash
main() {
  local cmd="$1"
  # Special-cased above the dispatcher to skip logging setup.
  if [[ "$cmd" == "logs" ]]; then show_logs; return $?; fi
  case "$cmd" in
    build)   do_build ;;
    ship|deploy) do_ship ;;
    notebook)
      case "$2" in
        journal) do_journal ;;
        daily)   do_daily ;;
      esac
      ;;
    help|-h|--help) usage ;;
    *) usage; return 1 ;;
  esac
}
"""


def test_bash_case_arms_and_alternation(tmp_path):
    p = tmp_path / "tool.sh"
    p.write_text(BASH)
    found = _names(extract.scan_bash(p, "tool"))
    assert {"build", "ship", "deploy", "notebook"} <= found


def test_bash_if_guard_dispatch_is_not_a_phantom(tmp_path):
    """A command special-cased with `if` above the `case` is real."""
    p = tmp_path / "tool.sh"
    p.write_text(BASH)
    assert "logs" in _names(extract.scan_bash(p, "tool"))


def test_bash_nested_case_arms_are_deeper_than_top_level(tmp_path):
    p = tmp_path / "tool.sh"
    p.write_text(BASH)
    depths = {h["name"]: h.get("depth") for h in extract.scan_bash(p, "tool")
              if h["idiom"] == "bash:case"}
    assert depths["build"] == 1
    assert depths["journal"] == 2 and depths["daily"] == 2


def test_bash_drops_help_aliases_flags_and_globs(tmp_path):
    p = tmp_path / "tool.sh"
    p.write_text(BASH)
    found = _names(extract.scan_bash(p, "tool"))
    assert not found & {"help", "h", "-h", "--help", "*", ""}


# --- extract: python ----------------------------------------------------------

def test_python_attribute_dispatch_var_is_matched(tmp_path):
    """Regression: `args.command == "x"` is what add_subparsers(dest=...) yields.

    Anchoring the bare name straight after `if` reported ZERO commands for a CLI
    that dispatches only this way — which turns every advertised command into a
    phantom, the worst silent wrong answer this tool can produce.
    """
    p = tmp_path / "cli.py"
    p.write_text(
        'def main(args):\n'
        '    if args.command == "alpha":\n'
        '        pass\n'
        '    elif args.cmd == "beta":\n'
        '        pass\n'
        '    elif opts.subcommand == "gamma":\n'
        '        pass\n'
    )
    assert _names(extract.scan_python(p, "cli")) == {"alpha", "beta", "gamma"}


def test_python_bare_dispatch_var_still_matched(tmp_path):
    p = tmp_path / "cli.py"
    p.write_text('if cmd == "alpha":\n    pass\nelif verb == "beta":\n    pass\n')
    assert _names(extract.scan_python(p, "cli")) == {"alpha", "beta"}


def test_python_unrelated_equality_is_not_a_command(tmp_path):
    """Unconstrained matching reported 60+ commands for a 24-command tool."""
    p = tmp_path / "cli.py"
    p.write_text(
        'if fmt == "json":\n    pass\n'
        'elif severity == "error":\n    pass\n'
        'elif args.output_format == "jsonl":\n    pass\n'
    )
    assert _names(extract.scan_python(p, "cli")) == set()


def test_python_in_tuple_and_argparse_and_click(tmp_path):
    p = tmp_path / "cli.py"
    p.write_text(
        'if args.command in ("pull", "push"):\n    pass\n'
        'sub.add_parser("build")\n'
        '@cli.command("ship")\n'
        'def ship_it():\n    pass\n'
        '@cli.command()\n'
        'def tear_down():\n    pass\n'
    )
    assert _names(extract.scan_python(p, "cli")) == {
        "pull", "push", "build", "ship", "tear-down"}


def test_python_prog_records_nested_verb(tmp_path):
    p = tmp_path / "cli.py"
    p.write_text('ArgumentParser(prog="tool agent approve")\n')
    assert _names(extract.scan_python(p, "tool")) == {"agent approve"}


def test_go_cobra(tmp_path):
    p = tmp_path / "main.go"
    p.write_text('cmd := &cobra.Command{Use: "serve [flags]", Short: "x"}\n')
    assert _names(extract.scan_go(p, "tool")) == {"serve"}


# --- extract: CLI -------------------------------------------------------------

def _run_extract(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(_EXTRACT), *args],
                          capture_output=True, text=True)


def test_extract_top_level_excludes_nested_and_non_entry_files(tmp_path):
    entry = tmp_path / "tool.sh"
    entry.write_text(BASH)
    handler = tmp_path / "sub.py"
    handler.write_text('if cmd == "inner":\n    pass\n')

    r = _run_extract("--tool", "tool", "--top-level", "--names",
                     str(entry), str(handler))
    assert r.returncode == 0, r.stderr
    got = set(r.stdout.split())
    assert {"build", "ship", "deploy", "notebook", "logs"} == got
    assert "journal" not in got   # depth 2
    assert "inner" not in got     # not the entry dispatcher


def test_extract_names_are_deduplicated_and_sorted(tmp_path):
    p = tmp_path / "tool.sh"
    p.write_text('case "$1" in\n  build) a ;;\n  build) b ;;\n  alpha) c ;;\nesac\n')
    r = _run_extract("--tool", "tool", "--names", str(p))
    assert r.stdout.split() == ["alpha", "build"]


# --- diff: doc mention parsing ------------------------------------------------

def test_doc_mention_matches_markdown_scaffolding():
    """Regression: bullets, table cells, and headings were all silently missed.

    The old single-run prefix class matched only a bare or bare-backticked line,
    so the docs half of the audit was very nearly a no-op — and it failed closed,
    which reads as 'clean'.
    """
    pat = diff.doc_mention_re("dot")
    for line in [
        "- `dot install` — install packages",
        "* `dot install`",
        "| `dot install` | installs |",
        "### `dot install`",
        "  > `dot install`",
        "`dot install`",
        "dot install",
    ]:
        assert pat.findall(line) == ["install"], line


def test_doc_mention_ignores_mid_sentence_and_other_tools():
    pat = diff.doc_mention_re("dot")
    assert pat.findall("Then run `dot install` afterwards.") == []
    assert pat.findall("- `brew install` — not our tool") == []


def test_documented_reports_empty_files_explicitly(tmp_path):
    """An empty result must be distinguishable from 'no --docs passed'."""
    silent = tmp_path / "SILENT.md"
    silent.write_text("Nothing relevant here.\n")
    loud = tmp_path / "LOUD.md"
    loud.write_text("- `dot install` — yes\n- `dot help` — alias, excluded\n")

    got = diff.documented("dot", [str(tmp_path / "*.md")])
    assert got[str(silent)] == set()
    assert got[str(loud)] == {"install"}


# --- diff: help parsing -------------------------------------------------------

def _fake_bin(tmp_path: Path, body: str, name: str = "demo") -> str:
    p = tmp_path / name
    p.write_text("#!/bin/bash\ncat <<'EOF'\n" + body + "\nEOF\n")
    p.chmod(0o755)
    return str(p)


def test_advertised_keeps_commands_that_take_arguments(tmp_path):
    """A required 2-space gutter hid 12 of 17 commands on a real CLI."""
    b = _fake_bin(tmp_path, "\n".join([
        "usage: demo <cmd>",
        "Commands:",
        "  install [pkgs...]   Install packages",
        "  doctor <cask>...    Fix quarantine",
        "  align [--all] Interactive resolution",
    ]))
    assert diff.advertised("demo", b) == {"install", "doctor", "align"}


def test_advertised_reads_stderr_and_skips_non_command_sections(tmp_path):
    p = tmp_path / "demo"
    p.write_text("#!/bin/bash\ncat >&2 <<'EOF'\n" + "\n".join([
        "Commands:",
        "  build [target]   Build it",
        "Layouts:",
        "  wide             Not a command",
        "Env:",
        "  DEMO_HOME        Not a command",
    ]) + "\nEOF\n")
    p.chmod(0o755)
    assert diff.advertised("demo", str(p)) == {"build"}


def test_advertised_drops_the_tool_name_and_help_aliases(tmp_path):
    b = _fake_bin(tmp_path, "\n".join([
        "  demo <slug>      Open a slug",
        "  demo build       Build it",
        "  help             Show help",
    ]))
    assert diff.advertised("demo", b) == {"build"}


# --- diff: CLI + exit codes ---------------------------------------------------

def _run_diff(impl: str, tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    f = tmp_path / "impl.txt"
    f.write_text(impl)
    return subprocess.run(
        [sys.executable, str(_DIFF), "--impl-file", str(f), *args],
        capture_output=True, text=True, cwd=str(tmp_path))


def test_diff_reports_both_directions(tmp_path):
    b = _fake_bin(tmp_path, "\n".join([
        "Commands:",
        "  build [target]   Build it",
        "  ghost            Never implemented",
    ]))
    r = _run_diff("build\nhidden\n", tmp_path, "--tool", "demo", "--bin", b)
    assert "PHANTOM (1)" in r.stdout and "ghost" in r.stdout
    assert "UNDOCUMENTED (1)" in r.stdout and "hidden" in r.stdout


def test_diff_exits_zero_by_default_and_one_under_strict(tmp_path):
    doc = tmp_path / "README.md"
    doc.write_text("- `demo ghost` — does not exist\n")
    base = ("--tool", "demo", "--docs", str(doc))

    lenient = _run_diff("build\n", tmp_path, *base)
    assert lenient.returncode == 0
    assert "1 candidate finding(s)" in lenient.stdout

    strict = _run_diff("build\n", tmp_path, *base, "--strict")
    assert strict.returncode == 1


def test_diff_warns_when_implemented_set_is_empty(tmp_path):
    """A total failure is a broken harness, not catastrophic drift."""
    b = _fake_bin(tmp_path, "Commands:\n  build [x]   Build it\n")
    r = _run_diff("", tmp_path, "--tool", "demo", "--bin", b)
    assert "implemented set is EMPTY" in r.stdout
    assert "treat this whole run as invalid" in r.stdout
    assert r.returncode == 0

    strict = _run_diff("", tmp_path, "--tool", "demo", "--bin", b, "--strict")
    assert strict.returncode == 1


def test_diff_warns_when_help_and_impl_do_not_overlap(tmp_path):
    b = _fake_bin(tmp_path, "Commands:\n  build [x]   Build it\n")
    r = _run_diff("something-else\n", tmp_path, "--tool", "demo", "--bin", b)
    assert "0 overlap" in r.stdout


def test_diff_docs_section_shown_even_when_nothing_matches(tmp_path):
    doc = tmp_path / "README.md"
    doc.write_text("No command mentions at all.\n")
    r = _run_diff("build\n", tmp_path, "--tool", "demo", "--docs", str(doc))
    assert "## vs docs" in r.stdout
    assert "(0 mentioned)" in r.stdout
    assert r.returncode == 0
