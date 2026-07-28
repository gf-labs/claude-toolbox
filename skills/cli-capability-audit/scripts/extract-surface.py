#!/usr/bin/env python3
"""Extract the IMPLEMENTED command surface of a CLI tool from its source.

Static analysis only — never executes the tool. Recognizes the dispatch idioms
that actually occur in hand-rolled CLIs, not just the obvious one:

  bash    case arms            `foo)` / `foo|bar)` inside `case ... in`
  bash    if-guards            `if [[ "$cmd" == "foo" ]]`
  python  equality chains      `if cmd == "foo":` / `elif command in ("a","b")`
  python  argparse subparsers  `sub.add_parser("foo")`
  python  per-command parsers  `ArgumentParser(prog="tool foo")`
  python  click                `@cli.command("foo")` / `@cli.command()` + def foo
  go      cobra                `&cobra.Command{Use: "foo ..."`

Why more than case arms: a dispatcher that special-cases one command with an
`if` above its `case` block is common (it avoids side effects like logging), and
a case-only extractor reports that command as a phantom. That false positive is
the single most likely way this audit produces a wrong answer.

Usage:
  extract-surface.py --tool NAME FILE [FILE...]        # human-readable
  extract-surface.py --tool NAME --json FILE [FILE...] # machine-readable
  extract-surface.py --tool NAME --names FILE [...]    # bare names, one per line

Output is a CANDIDATE set. Nested subcommands (`tool agent approve`) are
reported at the depth they appear; dispatch to a sub-handler shows up as the
parent name. Verify before publishing — see references/failure-modes.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# --- bash -------------------------------------------------------------------
RE_FUNC = re.compile(r'^\s*(?:function\s+)?([A-Za-z0-9_]+)\s*\(\)')
RE_CASE_OPEN = re.compile(r'^\s*case\s+.*\bin\s*$')
RE_CASE_CLOSE = re.compile(r'^\s*esac\b')
# An arm ends in `)` and is followed by end-of-line or a command on the same line.
RE_ARM = re.compile(r'^\s*(?P<arm>[A-Za-z0-9_*|:.@%+-]+)\)\s*(?:$|[^)]|\s)')
RE_IF_EQ = re.compile(
    r'if\s+\[\[\s+"?\$\{?(?:\w+)\}?"?\s*==\s*"?([A-Za-z0-9][A-Za-z0-9_-]*)"?\s*\]\]'
)

# --- python -----------------------------------------------------------------
# Only treat an equality chain as dispatch when the variable is plausibly the
# command token. Matching any `x == "literal"` floods the result with unrelated
# string comparisons — format names, status values, severity labels. On one real
# 3.6k-line CLI the unconstrained form reported 60+ commands for a 24-command
# tool. Extend this set for a codebase that names its dispatch variable
# something else; do not remove the constraint.
DISPATCH_VARS = r'(?:cmd|command|subcmd|subcommand|verb|sub|action|op|mode)'
# The optional `\w+.` prefix matches attribute access — `args.command`,
# `ns.cmd`, `opts.subcommand`. That is the form `add_subparsers(dest="command")`
# produces, so it is the DEFAULT for argparse CLIs, not an edge case. Anchoring
# the bare name directly after `if` reported 0 commands for a tool that
# dispatches only that way, which turns every advertised command into a phantom.
_VAR = rf'(?:\w+\.)?{DISPATCH_VARS}'
RE_PY_EQ = re.compile(
    rf'^\s*(?:el)?if\s+{_VAR}\s*==\s*["\']([A-Za-z0-9][A-Za-z0-9_-]*)["\']'
)
RE_PY_IN = re.compile(rf'^\s*(?:el)?if\s+{_VAR}\s+in\s*\(([^)]*)\)')
RE_ADD_PARSER = re.compile(r'\.add_parser\(\s*["\']([A-Za-z0-9][A-Za-z0-9_-]*)["\']')
RE_PROG = re.compile(r'prog\s*=\s*["\']([^"\']+)["\']')
RE_CLICK = re.compile(r'@\w+\.command\(\s*(?:["\']([A-Za-z0-9][A-Za-z0-9_-]*)["\'])?')
RE_DEF = re.compile(r'^\s*def\s+([A-Za-z0-9_]+)\s*\(')

# --- go ---------------------------------------------------------------------
RE_COBRA = re.compile(r'Use:\s*["\']([A-Za-z0-9][A-Za-z0-9_-]*)')

# Arms that are structural, not commands.
NOISE_ARMS = {"*", "", '""', "--*", "-*"}

# `help` is a help alias sitting alongside -h/--help, not a capability. Counting
# it inflates every tool by exactly one.
HELP_ALIASES = {"help", "usage", "h"}


def _clean(arm: str) -> list[str]:
    """Split an alternation arm and drop flags / wildcards / empties."""
    out = []
    for part in arm.split("|"):
        part = part.strip().strip('"').strip("'")
        if not part or part in NOISE_ARMS:
            continue
        if part.startswith("-"):          # -h, --help, --all …
            continue
        if "*" in part or "?" in part:    # glob fallthrough
            continue
        if part in HELP_ALIASES:
            continue
        out.append(part)
    return out


def scan_bash(path: Path, tool: str) -> list[dict]:
    found: list[dict] = []
    func = "(top)"
    depth = 0
    for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        m = RE_FUNC.match(line)
        if m and "()" in line:
            func = m.group(1)

        # if-guard dispatch (must run regardless of case depth)
        for m in RE_IF_EQ.finditer(line):
            name = m.group(1)
            if name not in NOISE_ARMS and not name.startswith("-"):
                found.append(dict(name=name, idiom="bash:if-guard",
                                  scope=func, file=str(path), line=i))

        if RE_CASE_OPEN.match(line):
            depth += 1
            continue
        if RE_CASE_CLOSE.match(line):
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            continue
        m = RE_ARM.match(line)
        if m:
            for name in _clean(m.group("arm")):
                # depth is the nesting level of the case block. Arms of a case
                # nested inside another case are SUBcommands — `notebook journal
                # daily` lives at depth 2. Flattening them into the top-level
                # count turns a 2-command tool into a 13-command one.
                found.append(dict(name=name, idiom="bash:case", depth=depth,
                                  scope=func, file=str(path), line=i))
    return found


def scan_python(path: Path, tool: str) -> list[dict]:
    found: list[dict] = []
    lines = path.read_text(errors="replace").splitlines()
    for i, line in enumerate(lines, 1):
        m = RE_PY_EQ.match(line)
        if m:
            found.append(dict(name=m.group(1), idiom="python:eq-chain",
                              scope="", file=str(path), line=i))
        m = RE_PY_IN.match(line)
        if m:
            for lit in re.findall(r'["\']([A-Za-z0-9][A-Za-z0-9_-]*)["\']', m.group(1)):
                found.append(dict(name=lit, idiom="python:in-tuple",
                                  scope="", file=str(path), line=i))
        for m in RE_ADD_PARSER.finditer(line):
            found.append(dict(name=m.group(1), idiom="python:argparse",
                              scope="", file=str(path), line=i))
        for m in RE_PROG.finditer(line):
            parts = m.group(1).split()
            if len(parts) >= 2 and parts[0] == tool:
                found.append(dict(name=" ".join(parts[1:]), idiom="python:prog",
                                  scope="", file=str(path), line=i))
        m = RE_CLICK.search(line)
        if m:
            name = m.group(1)
            if not name:  # @cli.command() → next def's name
                for nxt in lines[i:i + 4]:
                    d = RE_DEF.match(nxt)
                    if d:
                        name = d.group(1).replace("_", "-")
                        break
            if name:
                found.append(dict(name=name, idiom="python:click",
                                  scope="", file=str(path), line=i))
    return found


def scan_go(path: Path, tool: str) -> list[dict]:
    return [
        dict(name=m.group(1), idiom="go:cobra", scope="", file=str(path), line=i)
        for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1)
        for m in [RE_COBRA.search(line)] if m
    ]


SCANNERS = {".sh": scan_bash, ".bash": scan_bash,
            ".py": scan_python, ".go": scan_go}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tool", required=True, help="Tool name (for prog= matching)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--names", action="store_true", help="Bare names, one per line")
    ap.add_argument("--top-level", action="store_true",
                    help="Only commands found in the FIRST file (the entry "
                         "dispatcher). Use this for the headline count — later "
                         "files hold sub-handlers whose depth cannot be "
                         "inferred statically.")
    ap.add_argument("files", nargs="+", type=Path)
    args = ap.parse_args()

    hits: list[dict] = []
    for idx, p in enumerate(args.files):
        if not p.is_file():
            continue
        scan = SCANNERS.get(p.suffix)
        if scan:
            for h in scan(p, args.tool):
                h["entry"] = (idx == 0)
                hits.append(h)

    if args.top_level:
        hits = [h for h in hits
                if h["entry"] and h.get("depth", 1) <= 1 and " " not in h["name"]]

    # Deduplicate on name, keeping first provenance.
    seen: dict[str, dict] = {}
    for h in hits:
        seen.setdefault(h["name"], h)
    ordered = sorted(seen.values(), key=lambda h: h["name"])

    if args.names:
        for h in ordered:
            print(h["name"])
    elif args.json:
        json.dump({"tool": args.tool,
                   "count": len(ordered),
                   "commands": ordered}, sys.stdout, indent=2)
        print()
    else:
        print(f"{args.tool}: {len(ordered)} candidate commands\n")
        for h in ordered:
            print(f"  {h['name']:24s} {h['idiom']:18s} "
                  f"{Path(h['file']).name}:{h['line']}"
                  + (f"  in {h['scope']}" if h["scope"] else ""))
        idioms = sorted({h["idiom"] for h in ordered})
        print(f"\n  idioms seen: {', '.join(idioms) or 'none'}")
        print("  CANDIDATES — verify before publishing (see failure-modes.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
