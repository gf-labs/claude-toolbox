# Failure modes

Every item here was observed on a real audit, not imagined. They share one property:
**they make the docs look worse than they are.** An auditor that over-reports is worse than
no auditor — it burns trust on the first run and gets ignored on the second.

Read this before trusting any output.

---

## The dangerous class: silent wrong answers

These produce a *plausible* result rather than an error, so nothing signals that the run is
invalid.

### BSD `grep -E` has no `\s`

On macOS, `grep -E "^\s+foo"` matches nothing — silently. Every command then reads as
"absent from help," which is indistinguishable from a genuine wall of findings.

Use POSIX classes: `grep -E "^[[:space:]]+foo"`.

Symptom to watch for: **every single check fails.** Real drift is patchy. A 100% failure
rate is a broken checker, not a broken codebase.

### `$` inside a double-quoted shell regex

`grep -qE "^[[:space:]]+${c}([[:space:]]|$)"` — the `$)` is consumed by the shell, not
passed to grep. Escape it (`\$`) or use single quotes with a different interpolation
strategy.

Same symptom: uniform, total failure.

### Usage printed to stderr

Many tools write help to stderr. Capturing only stdout yields an empty advertised set, so
**every implemented command reports as undocumented.**

Always capture both: `subprocess.run(..., capture_output=True)` then concatenate
`stdout + stderr`.

### A repo can contain a working copy of a tool it no longer owns

The worst observed silent wrong answer was not a parser bug. A tool had been **extracted
to its own repo**, but a complete duplicate — dispatcher, handlers, help text, all of it —
remained behind and still dispatched. Every consistency check passed (the code exists, the
help matches, the docs match), and the audit counted 25 commands of another product's
surface as this repo's capability: 8 tools / 82 commands instead of the true 7 / 57.

Dispatch presence is not ownership. A consistency audit is structurally blind to this;
only a **canonicity check** catches it. Before counting any tool:

1. **Where does the PATH binary resolve?** `readlink -f "$(which tool)"` — if it lands
   outside this repo, the tool lives elsewhere.
2. **Does a sibling repo own it?** Scan adjacent repos for the same tool name; compare
   file mtimes/log dates to see which copy is ahead.
3. **Are there extraction pointers?** A `docs/<tool>.md` stub saying "moved to X" for one
   graduated tool implies others may have left *without* leaving a pointer — absence of a
   pointer is not evidence of residency.
4. **Ask the user.** "Has anything been extracted or graduated from this repo?" costs one
   question; in the observed case the user had said so unprompted and the fact was lost.

If a residual duplicate is found, it is a **finding in itself** (stale copy diverging from
canonical; edits landing in the dead copy), not a tool to document.

### Word-splitting through a shell function

Passing `"tool cmd"` pairs through a `for` loop into a function that re-splits `$1 $2`
silently mangled arguments in one observed run — the same call worked when invoked
directly and failed inside the loop. Prefer `printf '%s\n' ... | while read -r a b`, and
**always spot-check one known-good case** (a command you can see in the help with your own
eyes). If that case reports as missing, the harness is broken, not the docs.

---

## Over-reporting: parser noise

### Dispatch is not only `case`

A dispatcher may special-case a command with an `if` guard *above* its `case` block —
commonly to skip logging setup:

```bash
if [[ "$cmd" == "logs" ]]; then ... ; return $?; fi
case "$cmd" in ...
```

A case-only extractor reports `logs` as a phantom. It is real. Observed in 2 of 8 tools in
one repo.

### Not every CLI uses `add_subparsers`

One 3,600-line Python CLI dispatched via a bare `if cmd == "x":` chain — no subparsers, no
`cmd_*` naming convention. Each subcommand built its own `ArgumentParser(prog="tool sub")`.

### Unconstrained equality matching floods the result

Matching any `x == "literal"` in Python picked up format names (`json`, `jsonl`), severity
labels (`error`), sensitivity levels (`confidential`, `restricted`), and durations (`5h`,
`7d`) — reporting **60+ commands for a 24-command tool**.

Constrain to dispatch-shaped variable names (`cmd`, `command`, `verb`, `sub`, `action`, …).

### Requiring a 2-space gutter drops every command that takes an argument

Parsing `^\s{2,}(\w+)\s{2,}\S` looks reasonable and silently misses:

```
  install [pkgs...]              Install packages from manifest
  doctor <cask>...               Fix Gatekeeper quarantine
  init <repo-url>                Set the dot-configs pointer
```

Each has a **single** space after the command name. On one real CLI this hid **12 of 17
commands** and reported every one as undocumented — a 71% false-positive rate that looked
like a catastrophic documentation failure.

Consume argument placeholders (`[...]`, `<...>`, `--flag`, `...`, `|`) after the name
before looking for the description.

### The tool's own name is not a subcommand

Usage lines like `areas <slug>`, `workstation <layout>`, `notebook <path>` put the program
name in command position. Subtract the tool name from the advertised set.

### Depth must match on both sides of the diff

Comparing a **top-level** implemented set against an **all-depth** advertised set (or vice
versa) generates phantoms and undocumented entries in bulk that are purely artifacts of the
mismatch. Nested verbs (`tool agent approve`) appear in help as indented sub-entries; if the
implemented side excludes them, they read as phantom.

Diff top-level against top-level. Audit nested verbs separately, per parent command.

### Help text has sections that are not command lists

`Layouts:`, `Tools:`, `Env:`, `Examples:`, `Notes:` — their bodies parse as commands.
Wrapped description lines are worse, yielding entries like `a`, `complete`, `backticked`,
`accepts`. Skip from a non-command heading until the next heading.

### Nested `case` blocks are subcommands

`notebook journal daily` lives in a `case` nested inside the dispatcher's `case`. Counting
arms without tracking nesting depth turned a **2-command tool into 13**.

Only depth-1 arms are top-level.

### `help` is not a capability

`help` sits alongside `-h|--help` in the same arm. Counting it inflates every tool by
exactly one.

---

## Under-reporting: the direction you forget

**Run both set-differences.** The natural question is "are all my commands documented?"
(`implemented − documented`). The one that gets skipped is "does every documented command
exist?" (`documented − implemented`).

On one audit, checking only the first direction missed that a tool's entire overview
documented **four commands that were never built** — a doc describing a completely
different tool than the one that shipped. It surfaced by accident, while reading the file
for an unrelated edit.

Phantom commands are the higher-severity class: a missing doc entry means a user can't
find a feature; a phantom entry means a user follows the documentation and hits an error.

---

## Judgment calls a script cannot make

Stop automating here and decide deliberately. Record the decision in the map so the count
is reproducible.

| Situation | The question | Reasonable default |
|---|---|---|
| **Stub commands** | Dispatches, but the handler prints "deferred" and returns 0 | Count it, flag it inline. Omitting misrepresents the dispatcher; counting silently inflates capability |
| **Fallthrough arms** | `tool <slug>`, `tool <layout>` — one arm, N real values | One command, not N. Counting six layouts as six commands padded a total from 82 to 88 |
| **Aliases** | `toolbox journal` → `notebook journal` | Judgment. The script sees a dispatch arm; whether an alias is a capability is a human call |
| **Nested verbs** | `tool agent approve` | Count separately from top-level. Folding them in took one repo from 82 to ~123, which reads as inflation |
| **Roadmap entries** | Documented with a version marker, never built | Not implemented. A version marker is not an implementation |

---

## Verification protocol

Non-negotiable before any finding is reported:

1. **Spot-check the harness first.** Pick one command you can see in the help with your own
   eyes and confirm the checker reports it as present. If it doesn't, stop — everything
   downstream is invalid.
2. **Confirm each phantom** by actually running `<tool> <cmd>` (safe: it should error) or by
   grepping the dispatcher for the arm.
3. **Confirm each undocumented command is real**, not a dead arm — find its handler.
4. **Re-run the full audit after fixing** and show it returns clean. A fix that isn't
   re-measured isn't a fix.
