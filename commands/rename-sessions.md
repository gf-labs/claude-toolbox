---
description: Rename sessions based on their content — proposes names from commits and first messages
argument-hint: [pattern | --unnamed] [--force]
allowed-tools: Bash
---

## Arguments

`$ARGUMENTS`

Parse from arguments:
- **pattern** — substring to match against session title and first message
- `--unnamed` — target only sessions with no custom-title (default if no pattern given)
- `--force` — allow renaming sessions that already have a custom-title
- **(none)** — same as `--unnamed`

---

## Step 1 — Propose names (dry run)

```bash
python3 $CLAUDE_TOOLBOX_ROOT/scripts/rename-unnamed.py --dry-run PATTERN_FLAGS
```

Build `PATTERN_FLAGS` from `$ARGUMENTS`:
- If a non-`--` word is present: `--pattern "that-word" [--force if given]`
- If `--force` only: `--force`
- If nothing or `--unnamed`: no extra flags

If output is `NONE`: say "No unnamed sessions found in scope." and stop.

---

## Step 2 — Display review table

Parse each `PROPOSAL: path|id8|current_title|proposed_name` line.

```
### Rename proposals — [N] session(s)

| Session | Age | Current name | Proposed name | Source |
|---------|-----|--------------|---------------|--------|
| 4794c719 | 3d  | (none)       | lint-hook-setup | commit |
| a5734a17 | 12d | (none)       | knowledge-graph-refactor | commit |
```

- **Age**: compute from file mtime (the path is available from the PROPOSAL line)
- **Source**: `commit` if proposed_name came from a commit (proposed_name differs from a slug of first message); otherwise `message`
- **Current name**: show `(none)` if empty

Ask: "Apply these renames? Reply `yes` to apply all, `edit` to modify individual names, or `skip`."

---

## Step 3 — Apply

**If `yes`:**
```bash
python3 $CLAUDE_TOOLBOX_ROOT/scripts/rename-unnamed.py PATTERN_FLAGS
```
(Same flags as Step 1, without `--dry-run`.) Report: "Renamed [N] session(s)."

**If `edit`:** show each one at a time:
```
Session 4794c719 → "lint-hook-setup"
Accept? Reply the name to use, `skip` to leave unchanged, or `yes` to accept.
```
For each accepted/edited name, apply directly:
```bash
python3 $CLAUDE_TOOLBOX_ROOT/scripts/name-session.py "NAME" --path /full/path/to/session.jsonl --force
```

**If `skip`:** say "No renames applied." and stop.

---

## Constraints

- The path in each PROPOSAL line is the full absolute path — pass it directly to `name-session.py`
- Never rename the current active session; it is excluded by `rename-unnamed.py` by default
