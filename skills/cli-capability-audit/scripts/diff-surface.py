#!/usr/bin/env python3
"""Diff a CLI's IMPLEMENTED surface against what its help text and docs claim.

Runs `<bin> --help` ONLY. Never invokes a subcommand — in a real toolkit that
would open $EDITOR, launch fzf, or spend money on an API.

Reports both set-differences, because each catches a different bug:

  phantom      advertised/documented but NOT implemented → user follows the
               docs and hits an error
  undocumented implemented but NOT advertised            → real capability
               nobody can find

Auditing only one direction is the most common way this job gets done wrong:
checking "are all commands documented?" while never asking "does every
documented command exist?" leaves an entire class of defect invisible.

Usage:
  extract-surface.py --tool foo --top-level --names foo.sh \\
    | diff-surface.py --tool foo --bin ./bin/foo --docs README.md docs/foo.md

  diff-surface.py --tool foo --bin ./bin/foo --impl-file impl.txt --docs '**/*.md'

Every finding is printed UNVERIFIED with a ready-to-run check. Verify before
reporting — see references/failure-modes.md.

Exits 0 by default: findings are candidates, and a candidate is not a build
failure. Pass --strict to exit 1 on findings once the map is trusted enough to
gate on — that is what turns the map into a fixture rather than a doc that rots.
"""
from __future__ import annotations

import argparse
import glob
import re
import subprocess
import sys
from pathlib import Path

# Headings whose bodies are NOT command lists. Everything until the next
# heading is skipped. Without this, layout names, tool names, env vars, and
# wrapped description lines all parse as commands.
NON_COMMAND_SECTIONS = re.compile(
    r'^\s*(Layouts?|Tools?|Env|Environment|Notes?|Examples?|Templates?|'
    r'Template tokens|Options?|Flags?|Config|Configuration|See also|'
    r'Further Reading|Aliases)\s*:\s*$',
    re.IGNORECASE,
)
ANY_HEADING = re.compile(r'^\s*[A-Z][A-Za-z0-9 /&()\'-]*:\s*$')

HELP_ALIASES = {"help", "usage", "h"}

# Max leading spaces for a line to be considered a command entry rather than
# wrapped description text. Raise for help output with unusually deep nesting.
MAX_COMMAND_INDENT = 8


def advertised(tool: str, binpath: str, timeout: int = 20) -> set[str]:
    """Parse `<bin> --help`. Captures stderr too — many tools print usage there,
    and capturing only stdout yields a silently empty set, which reads as
    'nothing is documented' rather than as a bug in this script."""
    try:
        r = subprocess.run([binpath, "--help"], capture_output=True,
                           text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"warning: could not run {binpath} --help: {e}", file=sys.stderr)
        return set()
    out = (r.stdout or "") + "\n" + (r.stderr or "")

    found: set[str] = set()
    skipping = False
    for line in out.splitlines():
        if NON_COMMAND_SECTIONS.match(line):
            skipping = True
            continue
        if ANY_HEADING.match(line):
            skipping = False
            continue
        if skipping:
            continue
        # "  tool subcmd ..."  (preferred — unambiguous)
        m = re.match(rf'^\s{{1,}}{re.escape(tool)}\s+([a-z][a-z0-9-]*)', line)
        if m:
            found.add(m.group(1))
            continue
        # "  subcmd [args] <args>    description"
        #
        # Split on the FIRST run of 2+ spaces: left is the command spec, right
        # is the description. Requiring 2+ spaces immediately after the name
        # instead is wrong — it silently drops every command that takes an
        # argument (`install [pkgs...]`, `doctor <cask>...`, `init <repo-url>`),
        # which on one real CLI hid 12 of 17 commands and reported them all as
        # undocumented.
        # Command entries sit near the left margin; wrapped description text is
        # indented to the description column (typically 25-30 spaces). Without
        # this cap, a continuation line like
        #     "                    a complete DB."
        # registers `a` as a command.
        indent = len(line) - len(line.lstrip())
        if indent > MAX_COMMAND_INDENT:
            continue
        toks = line.strip().split()
        if not toks or not re.fullmatch(r'[a-z][a-z0-9-]*', toks[0]):
            continue
        # Consume argument placeholders after the name.
        i = 1
        while i < len(toks) and re.match(r'^[\[<(\-]|^\.\.\.$|^\|$', toks[i]):
            i += 1
        if i >= len(toks):
            continue
        # The description must follow. Accept either a 2+ space gutter (the
        # common layout) or a description starting with a capital/backtick after
        # a single space — `align [--suppress-all] Interactive entity resolution`
        # is a real help line, and requiring the gutter drops it.
        gutter = re.search(r'\S\s{2,}\S', line)
        if gutter or re.match(r'^[A-Z`(]', toks[i]):
            found.add(toks[0])
    # The tool's own name appears in usage lines like `areas <slug>` or
    # `workstation <layout>`; it is the program, not a subcommand.
    return found - HELP_ALIASES - {tool}


def doc_mention_re(tool: str) -> re.Pattern:
    """Line-leading `<tool> <cmd>` mention, through any markdown scaffolding.

    The leading class is a REPEATABLE run of whitespace and markdown markers, not
    a single run followed by whitespace. Markdown interleaves them — `- ` then a
    backtick, `| ` then a backtick, `### ` then a backtick — so the single-run
    form matched only a bare or bare-backticked line and silently missed every
    bullet, table cell, and heading:

        MISS  - `dot install` — install packages
        MISS  | `dot install` | ... |
        MISS  ### `dot install`
        HIT   `dot install`

    That is the dominant idiom in real docs, so the docs direction was very
    nearly a no-op — and it fails closed, which reads as "clean" rather than as
    a bug here.
    """
    return re.compile(rf'^[\s`*_\-|>#+]*{re.escape(tool)}\s+([a-z][a-z0-9-]*)', re.M)


def documented(tool: str, doc_paths: list[str]) -> dict[str, set[str]]:
    """Map each doc file → command names it mentions as `<tool> <cmd>`.

    Every matched file gets an entry, even an empty one. Omitting empty results
    makes "this file mentions no commands" indistinguishable from "no --docs was
    passed" — the exact ambiguity that hid the bug above.
    """
    pat = doc_mention_re(tool)
    result: dict[str, set[str]] = {}
    for pattern in doc_paths:
        for f in sorted(glob.glob(pattern, recursive=True)):
            p = Path(f)
            if not p.is_file():
                continue
            result[f] = set(pat.findall(p.read_text(errors="replace"))) - HELP_ALIASES
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tool", required=True)
    ap.add_argument("--bin", help="Executable for --help introspection")
    ap.add_argument("--impl-file", type=Path,
                    help="File of implemented names, one per line (default: stdin)")
    ap.add_argument("--docs", nargs="*", default=[],
                    help="Doc paths or globs (use quotes for globs)")
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 when there are findings (for CI gating). "
                         "Default exits 0 — findings are unverified candidates, "
                         "not failures.")
    args = ap.parse_args()

    if args.impl_file:
        raw = args.impl_file.read_text()
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
    else:
        ap.error("provide --impl-file or pipe names on stdin")
    impl = {ln.strip() for ln in raw.splitlines() if ln.strip()} - HELP_ALIASES

    print(f"# {args.tool} — surface audit")
    print(f"implemented: {len(impl)}\n")

    findings = 0
    suspect = False
    if not impl:
        suspect = True
        print("!! implemented set is EMPTY — the extractor found no commands.\n"
              "   Every advertised command below will report as a phantom. Check\n"
              "   the extractor against the dispatcher before believing any of it.\n")

    if args.bin:
        adv = advertised(args.tool, args.bin)
        # Real drift is patchy. A total mismatch in either direction means the
        # harness is broken, not the docs (failure-modes.md § silent wrong
        # answers) — say so, rather than emitting a plausible wall of findings.
        if adv and not adv & impl:
            suspect = True
            print(f"!! NOTHING in `{args.tool} --help` matches the implemented set "
                  "(0 overlap).\n   That is a broken harness, not documentation "
                  "drift. Spot-check one\n   command you can see in the help "
                  "yourself before reading on.\n")
        elif not adv:
            suspect = True
            print(f"!! `{args.tool} --help` yielded NO commands — help may print "
                  "somewhere\n   this parser does not read, or the section "
                  "heuristics dropped it all.\n")
        print(f"## vs `{args.tool} --help`  (advertised: {len(adv)})")
        for label, s, why in (
            ("PHANTOM", adv - impl, "advertised but not implemented"),
            ("UNDOCUMENTED", impl - adv, "implemented but absent from --help"),
        ):
            if s:
                findings += len(s)
                print(f"  {label} ({len(s)}) — {why}")
                for c in sorted(s):
                    print(f"    {c:24s} verify: {args.bin} --help | "
                          f"grep -nE '^[[:space:]]+({args.tool} )?{c}([[:space:]]|$)'")
            else:
                print(f"  {label}: none")
        print()

    if args.docs:
        docs = documented(args.tool, args.docs)
        print("## vs docs")
        if not docs:
            print("  (no files matched — check the --docs glob is quoted)")
        for f, names in sorted(docs.items()):
            ph, miss = sorted(names - impl), sorted(impl - names)
            flag = "  <-- PHANTOM" if ph else ""
            print(f"  {f}  ({len(names)} mentioned){flag}")
            if ph:
                findings += len(ph)
                print(f"    phantom:      {' '.join(ph)}")
            if miss:
                print(f"    not mentioned: {' '.join(miss)}")
        print()

    print(f"{findings} candidate finding(s) — ALL UNVERIFIED.")
    print("Confirm each one by hand before reporting. This script has produced")
    print("false positives on every codebase it has been run against.")
    if suspect:
        print("\nA harness warning fired above — treat this whole run as invalid "
              "until\nyou have spot-checked it.")
    return 1 if (args.strict and (findings or suspect)) else 0


if __name__ == "__main__":
    sys.exit(main())
