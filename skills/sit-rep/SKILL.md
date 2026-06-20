---
name: sit-rep
description: This skill should be used when the user asks for a "sit-rep", "situation report", "comprehensive overview of the project", "paint a picture of where we've been and where we're going", "show me orders of magnitude", or any narrative synthesis of project state covering velocity, milestones, pivots, learnings, and risks. Defaults to the current git repository; accepts an optional topic filter (e.g. "search", "billing") to scope output to a single sub-arc.
version: 0.1.0
---

# Project Sit-Rep

Produce a comprehensive situation report on the current project: where it has been, where it is, where it is going, what changed course, what was learned, what could trip the next phase.

A sit-rep is not a status check. Use `/tools:overview` for point-in-time status, `/tools:pin` for break checkpoints, or `/tools:recap` for one-session summaries. The sit-rep is for **narrative synthesis across 2+ weeks of work** when the reader needs to see the shape of the arc, not the current task.

## When to use

Trigger phrases include:
- "give me a sit-rep on this project"
- "paint a picture of where we've been and where we're going"
- "comprehensive overview of <project>"
- "look for all key orders of magnitude"
- "how have we stayed on track / pivoted / deviated"
- "what are the learnings, good and bad"

Skip this skill for: simple status questions, single-session recaps, point-in-time queries ("what's blocked right now").

## Scope and arguments

**Default scope is the current git repository.** Resolve via `${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py`; treat its output as authoritative.

**Environment-variable fallbacks.** The skill references two distinct roots:

- `CLAUDE_TOOLBOX_ROOT` — the claude-toolbox repo (provides `_scope.py`, `collect-plans.py`). If unset, default to `~/Repos/claude-toolbox`, or shell out to `git rev-parse --show-toplevel` from within the repo.
- `CLAUDE_PLUGIN_ROOT` — the active plugin install location (provides this skill's bundled `scripts/collect-velocity.sh`). If unset, fall back to `${CLAUDE_TOOLBOX_ROOT}/skills/sit-rep` since the skill ships from claude-toolbox.

**Optional first positional argument: topic filter.** When set, exclude commits, files, milestones, pivots, and learnings unrelated to that topic. Multi-word filters are space-separated and treated as an OR (e.g. `search index ranking` includes commits matching any of those terms).

Examples:
- `(no arg)` — full project scope
- `search` — only the search-index arc
- `billing api` — billing + api (treated as one combined arc)

**Discovering the right filter:** If the working directory holds multiple parallel arcs (more than one tool family or product line under active development) and the user did not specify a filter, ask once via `AskUserQuestion` before producing output. Do not guess. If the session name encodes a sub-tool scope (see memory `[[session-scope-naming]]`), surface it as the recommended default.

## Collect context

Run the commands below in parallel before drafting output. Store results mentally; do not paste raw output into the report.

**Scope + date:**
```bash
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/_scope.py
date +%Y-%m-%d
```

**Velocity (call the bundled script):**
```bash
# Args: $1=topic filter (optional), $2=window in days (default 14)
bash "${CLAUDE_PLUGIN_ROOT}/skills/sit-rep/scripts/collect-velocity.sh" "$TOPIC" 14
```

If `CLAUDE_PLUGIN_ROOT` is unset, invoke the script via its absolute path under the plugin install location.

**Backlog (TaskWarrior):**
```bash
REPO=$(git rev-parse --show-toplevel | xargs basename)
DOMAIN=$(git rev-parse --show-toplevel | sed 's|.*/Repos/||' | cut -d'/' -f1)
TW_PROJECT="${DOMAIN}.${REPO}"
task rc.verbose=nothing project:${TW_PROJECT} status:pending list 2>/dev/null
task rc.verbose=nothing project:${TW_PROJECT} status:completed end.after:today-21d list 2>/dev/null

# When a topic filter is set, ALSO list TW items whose description mentions the topic.
# These are the items that should populate Section 3 (In flight) and Section 4 (Next 1–2 weeks)
# for a topic-scoped sit-rep — without this filter, topic-relevant TW items get drowned in
# repo-wide noise. Cite TW IDs (#142, #143) verbatim; they are durable identifiers.
if [ -n "$TOPIC" ]; then
  for t in $TOPIC; do
    task rc.verbose=nothing project:${TW_PROJECT} status:pending /${t}/ list 2>/dev/null
  done
fi
```

**Branch + repo state:**
```bash
git branch -vv | grep '^\*'
git status --short | wc -l | tr -d ' '
git log --oneline -25
```

**Roadmap + active plans:**
```bash
ROADMAP="$(git rev-parse --show-toplevel)/docs/architecture/roadmap.md"
[ -f "$ROADMAP" ] && cat "$ROADMAP" || echo "ROADMAP_MISSING"
python3 ${CLAUDE_TOOLBOX_ROOT}/scripts/collect-plans.py 2>/dev/null
```

**Findings + review docs in window:**
```bash
ROOT=$(git rev-parse --show-toplevel)
find "$ROOT/docs" -type f \( -name "*findings*" -o -path "*/findings/*" -o -name "*review*" \) -newermt "14 days ago" 2>/dev/null

# When a topic filter is set, ALSO ls the topic's findings dir directly. The mtime filter above
# routinely misses docs that were last touched outside the window but carry the headline numbers
# (north-star %, $ spend, ready-doc counts). Read each file that names a closed arc and lift the
# top-of-file numbers verbatim into Section 1. These docs are the canonical source for the
# arc's magnitude — MEMORY.md citations of the same numbers are usually stale.
if [ -n "$TOPIC" ]; then
  for t in $TOPIC; do
    ls -la "$ROOT/docs/tools/$t/findings/" 2>/dev/null
  done
fi
```

**Canonical-DB / corpus magnitudes (re-derive, never cite from memory):**
```bash
# If the topic has a SQLite store (or any persistent data store), query it directly for live
# counts. MEMORY.md citations like "84K events" drift across sessions — see
# [[counts-drift-rederive]]. Always cite the number the DB returns NOW.
#
# This step is topic-aware: the agent should identify the canonical DBs for the topic before
# running and replace the examples below. For a search-index store:
for db in ~/data/search/events.db ~/.config/index/events.db ~/.config/index/_staging.db; do
  [ -f "$db" ] && { ls -lh "$db"; echo "  tables:"; sqlite3 "$db" ".tables" 2>/dev/null | head -5; }
done
# Then run topic-appropriate COUNT(*) queries against the tables you found. File size on disk
# is itself an order-of-magnitude anchor (Section 1 row: "events.db = 1.3 GB").
```

**Ticket references in the window:**
```bash
# Commit messages frequently cite TICKET-NNN — durable identifiers for cost/quality experiments,
# library-hardening arcs, and prompt A/B harnesses. Extract them so Section 2 milestones can
# cite the ID rather than paraphrase ("TICKET-204 batch tuning — 47% cost cut").
git log --since="14 days ago" --pretty="%cs %s" 2>/dev/null \
  | grep -E 'TICKET-[0-9]+' | head -25
git log --since="14 days ago" --pretty="%cs %s" 2>/dev/null \
  | grep -oE 'TICKET-[0-9]+' | sort -u

# Also grep docs + topic source dirs — tickets often appear in findings, planning, or architecture
# docs but never in a commit message (e.g. an experiment ID that produced a finding without a
# code commit). Catches IDs that the git-log grep alone would miss. Scope is intentionally
# broad: docs/architecture/, docs/tools/<topic>/, and lib/tools/<topic>/ all commonly hold them.
ROOT=$(git rev-parse --show-toplevel)
SCAN_DIRS=("$ROOT/docs/architecture")
if [ -n "$TOPIC" ]; then
  for t in $TOPIC; do
    SCAN_DIRS+=("$ROOT/docs/tools/$t" "$ROOT/lib/tools/$t")
  done
fi
grep -rhoE 'TICKET-[0-9]+' "${SCAN_DIRS[@]}" 2>/dev/null | sort -u
```

**Memory + session log (read directly via Read tool):**
- `~/.claude/projects/<project-key>/memory/MEMORY.md` — durable rules, anti-pattern signatures, ramp snapshots
- `~/.claude/projects/<project-key>/memory/session-log.md` — narrative arc, pivots, what didn't work

The project key is the absolute path of the repo's git root with `/` replaced by `-`.

Worked example: `/Users/you/Repos/example/project` → `-Users-you-Repos-example-project` → `~/.claude/projects/-Users-you-Repos-example-project/memory/MEMORY.md`.

Derive in one line: `KEY=$(git rev-parse --show-toplevel | tr '/' '-')`. For large session logs, read the last ~500 lines.

## Produce the sit-rep

Output a single markdown document with the eight sections below, in order. Omit any section that has nothing substantive to fill. Match each section to its purpose — these are content prompts, not headers to fill mechanically.

For the canonical section structure with example rows, see **`references/output-template.md`**.

For heuristics on surfacing orders of magnitude, pivots, learnings, and risks from `MEMORY.md` + `session-log.md` + findings docs, see **`references/signal-extraction.md`**.

### 1. Velocity (orders of magnitude)
A short table of 5–10 numbers that anchor the work. Commits, lines, hot files, corpus sizes, dollars spent, percent completion vs target. Pick numbers that *surprise* — "12 commits" is not surprising; "12 commits in one day, peak of 26 on date X" is.

### 2. Where we've been
Chronological milestone table. Each row: date · milestone · order-of-magnitude marker. Bound to the topic filter. Name the bend in the curve — when did the work change shape?

### 3. Where we are right now
Three sub-buckets: **Closed** · **In flight** · **Gated** (with explicit triggers). Plus a one-line **Repo state** (branch, ahead/behind, dirty count, what the dirty work spans).

### 4. Where we're going
Three horizons: **Next 1–2 weeks** (committable now) · **Gated on signal** (paused, with trigger named) · **Deferred with explicit triggers** (table format).

### 5. Pivots & deviations
Three sub-tables:
- **Healthy pivots** — Pivot · Trigger · Outcome
- **Costly corrections** — Deviation · Cost · Rule locked
- **Non-pivots that turned out right** — what was held despite pressure to change

### 6. Learnings
Two lists: **Keep** (patterns proven repeatedly) and **Killed** (anti-patterns retired). Each item is one sentence plus one phrase of evidence.

### 7. Risk register
Table: Risk · Likelihood · Impact · Mitigation status. 5–8 rows max. Include boring-but-real risks (unpushed branch, dirty tree spanning multiple arcs, untested-in-prod libraries).

### 8. The shape of the next inflection
2–4 sentences narrative close. Name the gate that gates the gate — the question that, if answered, unlocks the rest.

**Picking the right gate (judgment heuristic):** This section fails when an interesting but orthogonal blocker gets named instead of the actual load-bearing one. Trace forward from each candidate gate: "if this resolved tomorrow, what gets unblocked?" The correct gate is the one whose resolution unblocks the **largest downstream consumer**, not the one that surfaced most recently. A cost-log bug that blocks a future quality experiment is **not** the right gate when 503 ready docs are sitting behind a policy decision that blocks the entire write-back arc. Today-fresh discoveries belong in Section 7 (Risks) unless they sit on the consumer-unblocking critical path.

**Tie-breaker — when two candidates unblock the same consumer:** If two gates both forward-trace to the same downstream destination, they sit on the same dependency chain at different depths. Pick the one **earlier** in the chain — the upstream gate of the gate. A serving-layer rollout and a field-mapping schema review may both ultimately unblock write-back-to-`catalog.toml`; but the schema review gates the write-back posture that the serving layer would consume, so the schema review is the true gate. Naming the downstream-terminal candidate misses the fact that you can't sensibly stand it up until the upstream decision lands.

## Constraints

- **Default scope is the current git repository.** Do not aggregate across multiple repos unless explicitly asked.
- **Honor the topic filter strictly.** If the filter is "search", exclude commits, milestones, and pivots that are purely about other arcs. When in doubt, include and annotate why it relates.
- **Re-derive numerical anchors from canonical artifacts.** Never sum cited counts from `MEMORY.md` — counts drift across sessions (see `[[counts-drift-rederive]]`). Always go to git log / DB / source file for the actual number.
- **Quote dates verbatim.** Don't say "last week" — say "2026-06-05". Memory and session logs are time-anchored; preserve that.
- **Cite policy locks as `[[memory-slug]]` references.** If a rule was locked into memory, mark which memory file holds it so the reader can trace it.
- **Lead with surprise.** Section 1's numbers and Section 5's pivots should make the reader recognize patterns they had not yet named.
- **Do not commit anything.** This is a read-only report. Saving it to a file is optional and only if asked.

## Additional Resources

### Reference Files
- **`references/output-template.md`** — canonical 8-section structure with example rows drawn from an example search-index sit-rep
- **`references/signal-extraction.md`** — heuristics for surfacing orders of magnitude, pivots, learnings, and risks from `MEMORY.md` + `session-log.md` + findings docs

### Scripts
- **`scripts/collect-velocity.sh`** — parameterizable velocity collector. Args: `$1` topic filter (optional, space-separated for OR), `$2` window in days (default 14). Emits commit cadence, hot files, line counts, scoped commit percentage, peak day
