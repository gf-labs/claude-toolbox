---
description: Answer a mid-task side question, then resume
allowed-tools: Bash, Read, Glob, Grep
model: claude-sonnet-4-6
argument-hint: <question>
---

## Context

**Arguments:** `$ARGUMENTS`

The user has a side question while you are mid-task. The question is in `$ARGUMENTS`.

---

## Your role

You are in the middle of a task. Handle this side question without losing your place.

### Edge case — question reveals a problem

If answering the question reveals an issue with what you were doing (e.g., a wrong assumption, a bug in the approach, a constraint you weren't aware of), **flag it before resuming**:

> **Note before resuming:** [what the problem is and what you'll do differently]

Then resume.

### Edge case — question is a redirect

If the question is actually a request to switch tasks entirely (not a clarifying question), ask before switching:

> This looks like a task change rather than a side question. Switch to: [new task]? (yes/no)

Do not switch until confirmed.

---

## Output format

```
ASIDE: $ARGUMENTS

[Answer the question concisely. Read-only during aside — no writes unless the answer directly requires a file read to answer accurately.]

— Back to task: [one-line description of what you were doing before the aside]
```

After outputting this block, resume where you left off without restating the aside.
