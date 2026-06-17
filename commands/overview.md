---
description: PM-style project overview — current state, recent work, backlog priorities, active plans, and sequencing recommendation. Project-scoped: reads from the current repo. Use at the start of a session or when deciding what to work on next.
allowed-tools: Bash
model: claude-sonnet-4-6
---

## Collect context

Run all commands now before producing output.

**Scope + date:**
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py
date +%Y-%m-%d
```

**Git state:**
```bash
echo "BRANCH:" && (git branch -vv 2>/dev/null | head -3 || echo "not a git repo")
echo "UNCOMMITTED:" && (git status --short 2>/dev/null | wc -l | tr -d ' ')
echo "UNPUSHED:" && (git log @{u}.. --oneline 2>/dev/null | wc -l | tr -d ' ')
echo "LOG:" && git log --oneline -8 2>/dev/null
echo "CHANGED_FILES:" && git status --short 2>/dev/null
```

**Backlog (TaskWarrior):**
```bash
REPO=$(git rev-parse --show-toplevel 2>/dev/null | xargs basename 2>/dev/null)
DOMAIN=$(git rev-parse --show-toplevel 2>/dev/null | sed 's|.*/Repos/||' | cut -d'/' -f1)
TW_PROJECT="${DOMAIN}.${REPO}"
task rc.verbose=nothing project:${TW_PROJECT} limit:5 list 2>/dev/null || echo "(TaskWarrior unavailable)"
```

**Inventory:**
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-inventory.py 2>/dev/null || echo "(unavailable)"
```

**Active plans (this project):**
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plans.py 2>/dev/null
```

**Session log:**
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-session-log.py 2>/dev/null
```

**Project metadata (if plugin):**
```bash
python3 -c "import json; d=json.load(open('.claude-plugin/plugin.json')); print('plugin v' + d['version'])" 2>/dev/null || true
```

---

## Your role

Read all collected context and produce a PM-style overview for the current project. Be specific and direct — not a git log dump, not a backlog recitation.

Flag any discrepancies between TaskWarrior tasks, active plans, and actual git state. Trust git over planning docs when they conflict.

When building the Sequencing section: weight session log recency — if the last session log entry has an open **Resume:** or **Open threads:** line, surface that as the top "Now" item. Cross-reference the session log against backlog items to identify what's already in motion vs. cold-start work.

---

## Output format

**[repo name] — [version if plugin] — [date]**

**Current state** — one honest sentence.

**Recent work** — what shipped in the last few sessions (git log + session log). 3–5 bullets, outcomes not mechanics.

**In flight** — uncommitted changes or unpushed commits that are done but not yet landed.

**Inventory** — one line from collect-inventory.py (commands/agents/hooks/scripts counts).

**Backlog highlights** — top 3–5 pending TaskWarrior tasks, with size. Skip completed/deleted items.

**Plans** — active plans with one-line status each. Flag stale or conflicting plans.

**Sequencing**

```
Now (no dependencies):
  → [item]

Soon:
  → [item]

When [condition]:
  → [item]
```

Max 3 bullets per tier. Prioritize: (1) broken things, (2) blockers on other work, (3) high-leverage / low-effort.
