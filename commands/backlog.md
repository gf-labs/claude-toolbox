---
description: Add a task to TaskWarrior for this project
argument-hint: [item description] [+tag] [size:S]
allowed-tools: Bash
model: claude-sonnet-4-6
---

## Arguments

`$ARGUMENTS`

If arguments provided: use them as the item description (with optional tags and size).
If no arguments: derive a task from this session's recent context (open threads, incomplete work, things mentioned as "later" or "TODO").

---

## Your role

Add a new task to TaskWarrior for the current project.

**Step 1 — Determine project slug:**
```bash
echo "SLUG: $(python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_slug.py)"
```
If not in a git repo: ask the user for the project slug (format: `domain.reponame`).

**Step 2 — Check for existing similar task:**
```bash
task project:[slug] list
```
If a closely matching task exists, say so and stop.

**Step 3 — Draft task add + annotation:**

From `$ARGUMENTS`, extract:
- **Short title** (required, ≤ 70 chars): a scannable lede — the verb + object, no qualifiers, no bench specs, no env-var lists, no parentheticals
- **Details** (when present): everything else from the input — benchmarks to run, env vars to set, rationale, things to skip, gated-on conditions, links. Becomes an annotation
- **Type tag** (infer from description): `+command`, `+agent`, `+hook`, `+pipeline`, `+infra`, `+research`
- **Size** (default `size:S`): `size:XS|S|M|L|XL`
- **Priority** (omit unless clearly blocking): `priority:H|M|L`
- **Special status**: `wait:someday` for truly indefinite deferrals; `+blocked` for gated items

If the user's input is one short sentence with no rationale, just use it as the title — no annotation needed. Default behavior is to *split* longer input into title + annotation, not stuff everything into the title.

Draft commands:
```bash
task add "[short title]" project:[slug] +[type] size:[S] source:manual
# only if details present:
task annotate [ID] "[details]"
```

Show the draft to the user. If the split between title and details is ambiguous, confirm before executing.

**Step 4 — Execute:**
Run `task add` first, capture the new task ID from output (e.g. `Created task 563.`), then run `task annotate [ID] ...` if details were drafted.

For `+blocked` items, add a gated-on annotation (in addition to the details annotation, if any):
```bash
task annotate [ID] "gated on: [condition]"
```

**Step 5 — Confirm:** "Added task [N]: [description]"
