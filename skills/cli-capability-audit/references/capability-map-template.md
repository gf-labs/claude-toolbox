# Capability map — output template

The canonical shape for `docs/capabilities.md` (single-tool repos may name it
`CAPABILITIES.md` at root). Adapt section depth to the repo; keep the order.

The map's job is to be **the one file that records reality**. Every other doc is a view.

---

## Header

State provenance up front so a reader knows whether to trust it:

```markdown
# <Project> capabilities

Project-wide capability map: every command the project actually implements, one row each.

**This file records reality, not intent.** Every entry was derived from dispatcher
source — case arms, if-guards, and dispatch chains — not from help text or prose.
Where the two disagree, the drift is recorded in § Drift status rather than silently
reconciled.

- **Derived:** YYYY-MM-DD, from `<branch or tag>`
- **Scope:** N tools · **M top-level commands** · ~K nested subcommands
- **Re-derive:** see § How this was derived
```

## At a glance

One row per tool. Include the canonical data store — it answers "what does this own?"
faster than prose.

```markdown
| Tool | Cmds | Purpose | Canonical store |
|---|---:|---|---|
| `foo` | 31 | One line, no marketing | `foo.toml` → `foo.db` |
```

## Cross-cutting capabilities

What the shared library provides to every tool. This is often the most undersold part of a
codebase: it's the reason a new tool costs a dispatcher instead of a runtime.

```markdown
| Capability | Module | Surface |
|---|---|---|
| Flag parsing | `flags.sh` | `--dry-run` `--verbose` `--profile` |
```

Also record **partial cross-cutting adoption** — "6 of 8 tools implement the log shim; 2
document it" is exactly the kind of inconsistency a per-tool view can never surface.

## Per-tool sections

One `##` per tool, command tables grouped by function. Split read-only from
mutating/expensive when that distinction is load-bearing — for an LLM reading the map to
decide what it may run unprompted, this is the single most useful grouping.

Mark stubs inline where they appear:

```markdown
> `taxonomy` dispatches but is a **stub** — prints a deferral notice and returns 0.
> Counted because it dispatches; it does no work.
```

## Designed, not built

Docs for unbuilt things, excluded from the counts. Without this section a reader cannot
tell design from reality, and the count silently inflates.

```markdown
| Doc | Status |
|---|---|
| `docs/tools/foo/` | Unbuilt — design only |
```

## Drift status

After a fix pass, state the current number first, then what was resolved. A map that only
lists problems goes stale the moment they're fixed.

```markdown
**Current state: 0 commands missing from `--help`, 0 phantom commands in tool docs.**
Verified YYYY-MM-DD by re-running the derivation below.

### Resolved in the YYYY-MM-DD pass
| Category | Count | What it was |
|---|---:|---|

### Known, not fixed
- ...
```

Keep "Known, not fixed" honest. Items that are deliberately left alone belong here with the
reason, not omitted.

## How this was derived

Method, plus the failure modes encountered. This is what makes a re-run trustworthy rather
than a fresh guess.

```markdown
Three sets per tool, compared pairwise. No command was executed.

1. **Implemented** — dispatcher case arms, if-guards, and dispatch chains
2. **Advertised** — commands named in each tool's usage text
3. **Documented** — commands named in per-tool and project-level docs

`advertised − implemented` = phantom. `implemented − advertised` = undocumented.

**Every finding was hand-verified.** The automated pass produced false positives on its
first runs; the failure modes are worth knowing before trusting a re-run: <list them>
```

---

## Counting rules

State these in the map itself. Without them the headline number isn't reproducible, and a
future re-run will "find" a change that is really a definitional difference.

- Bare fallthrough forms (`tool <slug>`) are **one** command, not N
- Nested verbs counted **separately** from the top-level total (`82 top-level · 41 nested`)
- Stubs **counted**, flagged inline
- Aliases: state the choice explicitly either way
- Dispatcher itself: if it has its own commands, it's a tool — say so, since it changes the
  tool count (`7 peer tools` vs `8 tools with a command surface` are both defensible)
