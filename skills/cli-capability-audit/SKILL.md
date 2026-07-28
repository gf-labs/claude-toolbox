---
name: cli-capability-audit
description: This skill should be used when the user asks to "audit my CLI docs", "build a capabilities map", "check if my help text is accurate", "find undocumented commands", "find documentation drift", "are my docs up to date", "what can this tool actually do", "refresh the help docs", or wants a verified inventory of every command a CLI repo implements. Works on hand-rolled bash, Python (argparse/click), and Go (cobra) CLIs.
version: 0.1.0
---

# CLI capability audit

Derive what a CLI **actually implements** from its dispatcher source, diff that against what
its help text and docs **claim**, fix the gaps, and publish a capability map that records
reality.

Use when docs have drifted, when a repo needs an accurate command inventory, or when
someone needs to describe a codebase accurately (a README, a summary, a resume bullet) and
the existing docs can't be trusted as the source.

## The core idea

Three sets per tool, compared **in both directions**:

| Set | Source | How |
|---|---|---|
| **Implemented** | Dispatcher source | Static parse — case arms, if-guards, dispatch chains |
| **Advertised** | `<tool> --help` | Run help only, never a subcommand |
| **Documented** | README, per-tool docs, agent context files | Text scan |

- `advertised − implemented` → **phantom**: user follows docs, hits an error
- `implemented − advertised` → **undocumented**: real capability nobody can find

Both directions matter. Checking only "are my commands documented?" misses phantom
commands entirely, and phantoms are the higher-severity class.

**Never execute subcommands to introspect.** In a real toolkit that opens `$EDITOR`,
launches `fzf`, or spends money on an API. Drift detection needs no execution — it is a set
operation over two static reads plus `--help`.

## Workflow

Announce: "Using cli-capability-audit to <purpose>."

**Resolve the script paths first.** The audit runs with the working directory set to the
repo *being audited*, while these scripts ship inside the plugin — a bare
`scripts/extract-surface.py` will not resolve. Set once, then use `$AUDIT` throughout:

```bash
AUDIT="${CLAUDE_PLUGIN_ROOT:-$CLAUDE_TOOLBOX_ROOT}/skills/cli-capability-audit/scripts"
```

`CLAUDE_PLUGIN_ROOT` is the active plugin install location. If it is unset, fall back to
`${CLAUDE_TOOLBOX_ROOT}/skills/cli-capability-audit` — the skill ships from claude-toolbox.
If neither is set, invoke the scripts by absolute path under the plugin install location.

### 1. Inventory the tools

Find dispatch entry points and their doc surfaces. In a multi-tool repo, enumerate
`bin/*` or `lib/tools/*/` and note, per tool: entry script, help text location, per-tool
docs, agent context file (`CLAUDE.md`/`AGENTS.md`).

**Then check canonicity — dispatch presence is not ownership.** A repo can contain a
complete, working copy of a tool that has been extracted to its own repo. For each tool:
where does its PATH binary resolve (`readlink -f "$(which tool)"`)? Does a sibling repo
own it? Ask the user: "has anything been extracted or graduated from this repo?" A tool
whose canonical home is elsewhere is **excluded from the counts** and its residual copy
reported as a finding. See `references/failure-modes.md` § *A repo can contain a working
copy of a tool it no longer owns* — this produced the largest silent wrong answer observed
(counting 25 of another product's commands as local capability).

Report the doc-surface matrix — which tools have which files. Missing files are findings.

### 2. Extract the implemented surface

```bash
"$AUDIT"/extract-surface.py --tool NAME --top-level --names ENTRY.sh [SUBHANDLER.py ...]
```

The **first file is the entry dispatcher** and is authoritative for top-level commands;
later files hold sub-handlers whose depth cannot be inferred statically. Drop
`--top-level` to see nested verbs too.

Run without `--names` to see each command's idiom and `file:line` provenance — useful when
a result looks wrong.

### 3. Diff against help and docs

```bash
"$AUDIT"/extract-surface.py --tool NAME --top-level --names ENTRY.sh \
  | "$AUDIT"/diff-surface.py --tool NAME --bin ./bin/NAME --docs README.md 'docs/**/*.md'
```

`diff-surface.py` exits 0 even with findings — they are candidates, not failures. Once the
map is trusted and wired into CI, add `--strict` to exit 1 on findings.

**Heed the `!!` harness warnings.** An empty implemented set, an empty advertised set, or
zero overlap between them means the extractor or the help parser is broken — not that the
docs are catastrophic. Stop and spot-check before reading the findings.

**Keep `--top-level` on both sides.** Diffing a top-level implemented set against an
all-depth advertised set manufactures findings in bulk that are pure artifacts of the
mismatch. Audit nested verbs separately, per parent command.

Output is **candidates, all unverified**.

### 4. Verify every finding by hand

Do not skip this. **The scripts have produced false positives on every codebase they have
been run against.**

1. **Spot-check the harness first** — pick a command visible in the help with your own eyes
   and confirm the checker reports it present. If every check fails, the harness is broken,
   not the docs.
2. Confirm each phantom: run `<tool> <cmd>` (it should error) or grep the dispatcher.
3. Confirm each undocumented command has a real handler, not a dead arm.

Read **`references/failure-modes.md`** before trusting output — it lists the traps that
produce plausible wrong answers, including one (`grep -E` and `\s` on BSD/macOS) that fails
silently and looks exactly like a wall of genuine findings.

### 5. Make the judgment calls explicitly

A script cannot decide these. Record each choice in the map so the count is reproducible:
stub commands, fallthrough arms (`tool <slug>`), aliases, nested verbs, roadmap entries.
See `references/failure-modes.md` § *Judgment calls*.

### 6. Write the capability map

Publish `docs/capabilities.md` (or `CAPABILITIES.md` at root for a single-tool repo) from
the **implemented** set — reality, not aspiration. Follow
**`references/capability-map-template.md`**.

The map becomes the expected-state file the audit checks against, so it stops being a doc
that rots quietly and starts being a fixture with a checker pointed at it.

### 7. Fix the docs

In severity order:

1. **Phantoms** — remove from help/docs, or implement. Help that promises a command that
   errors is the only case where docs actively mislead.
2. **Undocumented commands** — add to help text.
3. **Project-level references** — the headline README/context file.
4. **Missing context files** — write them for tools that lack one.
5. **Unbuilt-tool docs** — banner them (`> **Status: NOT IMPLEMENTED — design only.**`) so
   aspiration reads as aspiration. Leave forward-looking vision docs alone; give them a
   pointer to the map instead of rewriting them.

Prefer **folding into existing doc surfaces** over creating new ones. The disease is
hand-maintained docs that drift; adding a parallel layer makes it worse. One new rollup is
the right budget.

### 8. Re-run and prove it

Re-run steps 2–3 and show the audit returns clean. Update the map's drift section to state
the current number first, then what was resolved. **A fix that isn't re-measured isn't a
fix.**

## Scope discipline

Fix **tool docs** — help text, per-tool docs, context files, the map. Do **not** rewrite
vision or design documents that deliberately describe unbuilt things; they are a different
genre and rewriting them is the user's call. Give them a one-line pointer to the map and
move on.

Verify claims before writing them. When documenting behavior, read the implementation —
exact enum strings, real flag names, actual thresholds. Prose written from memory is how
the drift started.

## Additional resources

### Reference files
- **`references/failure-modes.md`** — traps that produce plausible wrong answers; the
  verification protocol; the judgment-call table. **Read before trusting output.**
- **`references/capability-map-template.md`** — canonical map structure and counting rules.

### Scripts
Both live at `${CLAUDE_PLUGIN_ROOT}/skills/cli-capability-audit/scripts/` — see the path
resolution at the top of § Workflow.

- **`extract-surface.py`** — implemented surface from source. Handles bash `case`
  arms and `if`-guards, Python equality chains (bare and attribute-style, `args.command`) /
  argparse / click, Go cobra. Tracks nesting depth and idiom provenance. `--top-level`,
  `--names`, `--json`.
- **`diff-surface.py`** — three-way diff. Runs `--help` only (captures stderr too),
  section-bounds the parse, reports both set-differences with a ready-to-run verify command
  per finding. Warns loudly when the sets suggest a broken harness. `--strict` exits 1 on
  findings.

Both are covered by `tests/test_cli_capability_audit.py` in claude-toolbox.
