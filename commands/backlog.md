---
description: Add an item to BACKLOG.md from within Claude
argument-hint: [item description]
allowed-tools: Bash, Read, Edit, Write
---

## Arguments

`$ARGUMENTS`

If arguments provided: use them as the item title/description.
If no arguments: derive an item from this session's recent context (open threads, incomplete work, things mentioned as "later" or "TODO").

---

## Your role

Add a new backlog item to the project's BACKLOG.md.

**Step 1 — Find target BACKLOG.md:**
```bash
git rev-parse --show-toplevel 2>/dev/null || echo ""
```
- If in a git repo: target is `[repo-root]/BACKLOG.md`
- If not in a git repo: target is `$CLAUDE_TOOLBOX_ROOT/BACKLOG.md`

**Step 2 — Read the BACKLOG.md** to understand the format and existing items. Check whether a similar item already exists — if so, say so and stop.

**Step 3 — Compose the item:**

Format:
```
### [title]
- **Size:** [XS / S / M / L]
- [one-line description of what to do and why]
```

- Title: concise imperative phrase (e.g. "Fix X", "Add Y", "Refactor Z")
- Size: XS = trivial change, S = a focused session, M = multi-session, L = large/unknown
- Body: one line is usually enough; add bullets only if there are distinct sub-steps

**Step 4 — Append to the `## Backlog` section** using the Edit tool (match the last item in the section, append after it). If no `## Backlog` section exists, append one at the end of the file.

**Step 5 — Confirm:** "Added to BACKLOG.md: [title]"
