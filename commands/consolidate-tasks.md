---
description: Consolidate all work items from this repo (or all repos with --discover) into TaskWarrior — section-aware scanning, sub-slug routing, dedup, bulk task creation, tombstoning.
argument-hint: [--discover [PATH]]
allowed-tools: Bash, Read, Write, Edit
model: claude-sonnet-4-6
---

## Your role

Orchestrate the consolidate-tasks pipeline. Work through the steps below interactively — pause for user confirmation where noted.

---

## Step 0 — Preflight + collect

**Verify TaskWarrior is available:**
```bash
task --version 2>/dev/null || { echo "TASK_MISSING"; exit 1; }
task udas 2>/dev/null | grep -cE "^(size|source)" | grep -q "^2$" || echo "MISSING_UDAS"
```
- If `TASK_MISSING`: stop — "TaskWarrior not found. Install it (`brew install task`) and add `size` and `source` UDAs to `~/.taskrc` before running this skill."
- If `MISSING_UDAS`: stop — "Required UDAs (size, source) not found in ~/.taskrc. See the claude-toolbox TaskWarrior design spec."

**Run collection:**
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-tasks.py $ARGUMENTS > /tmp/consolidate-manifest.json
echo "EXIT:$?"
```

If exit code nonzero, read `/tmp/consolidate-manifest.json` for the error message, print it, and stop.

Read `/tmp/consolidate-manifest.json`. Sum across all repos and print:
```
N repos · M tracking files · K code comments · J GitHub issues
```
Where:
- repos = number of entries in `repos[]`
- tracking files = count of distinct `source_file` values where `source_type == "markdown"`
- code comments = count of items where `source_type == "code"`
- GitHub issues = count of items where `source_type == "github"`

If all item counts are zero across all repos: print "No items found to migrate." and stop.

---

## Step 1 — Confirm slugs

For each repo in the manifest:
- Print: `[repo-name] → [slug]`
- If `tw_slugs_present: true`, show the sub-slug mappings from the items (group by inferred_slug per source_file)
- If `files_with_no_slug_mapping` is non-empty, flag each: `⚠ [file] — no sub-slug mapping (will default to [slug])`

Ask: "Confirm these slugs, or provide overrides:"

Wait for confirmation. If overrides provided, apply them to all matching items in `/tmp/consolidate-manifest.json` using the Edit tool.

---

## Step 2 — Dedup + judgment

For each unique `inferred_slug` value in the manifest, run:
```bash
task rc.verbose=nothing project:[SLUG] all 2>/dev/null
```

Then scan the manifest items and:
- Set `status: skip` for items whose description is ≥80% similar to any existing task description
- Set `status: flag` for items whose description explicitly references a different repo name that is not represented in the manifest
- Note any `files_with_no_slug_mapping` items for user review in Step 3

Apply changes by writing the updated manifest back to `/tmp/consolidate-manifest.json`.

---

## Step 3 — Present migration plan

Present grouped output. In discover mode (manifest `mode == "discover"`): group by repo first.
In repo mode: skip the per-repo grouping header.

```
## Migration plan

Coverage: N total · M proposed · K skipped · F flagged
→ Does this coverage look right? All N items should be accounted for.

### [repo-slug] — N items              ← omit header in repo mode

#### Markdown items — N
1. [description] → +[tag] size:[S]  ([source_file] § [section])
2. [description] → +[tag] size:[M]

#### Code comments — N
3. [description] → +bug size:XS  [source_file:line]

#### GitHub issues — N
4. #12 Issue title → +[tag] size:[S]

### Skipped — N
- [description] (reason: similar to existing task / already tracked)

### Flagged — N
- [description] (references: [other-repo])
```

Ask: "Confirm this plan? Reply:
- `yes` — execute all proposed items
- `skip N` or `skip N,M` — skip specific items by number
- A revised version of the plan — paste corrected list
- `no` — cancel"

Wait for user confirmation.

---

## Step 4 — Write approved manifest

Apply the user's decisions to `/tmp/consolidate-manifest.json`:
- Set `status: skip` for any items the user chose to skip
- Keep `status: approved` for all confirmed items (change `status: proposed` → `status: approved`)
- Set `status: flag` for any items the user chose to flag

Write the result to `/tmp/consolidate-approved.json`.

---

## Step 5 — Execute

```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/add-tasks.py --manifest /tmp/consolidate-approved.json
```

---

## Step 6 — Report

Render the output from `add-tasks.py` as the final summary.

If flagged items exist, ask: "How would you like to handle each flagged item?
- Add to this project with a cross-ref annotation
- Skip
- Defer to that project's own consolidation run"
