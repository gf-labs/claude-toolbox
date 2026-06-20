# Signal Extraction Heuristics

How to surface orders of magnitude, pivots, learnings, and risks from the three primary sources: `MEMORY.md`, `session-log.md`, and findings/review docs under `docs/`.

These are heuristics, not rules. When a heuristic conflicts with the actual artifact, trust the artifact.

---

## Source: MEMORY.md

Located at `~/.claude/projects/<project-key>/memory/MEMORY.md`. Auto-loaded into context but truncated when the file exceeds the index budget (the system reminder warns when this happens — e.g. "MEMORY.md is 1416 lines and 214.4KB. Only part of it was loaded"). Always `Read` the full file directly when producing a sit-rep; do not rely on the auto-loaded preview.

### What lives here

- **Durable user/feedback/project/reference entries** — index lines pointing to topic files
- **Ramp snapshots** — dated knowledge-graph notes (`## ramp snapshot — YYYY-MM-DD`)
- **Session snapshots** — dated stable-pattern blocks awaiting migration to session-log

### What to extract

**For Section 1 (orders of magnitude):**
- Dollar amounts in ramp snapshots and session-log entries (e.g. "overnight $42 arc")
- Token counts mentioned as totals ("1.2M tokens", "84K events")
- Percentages vs targets ("153% of north-star", "47% cost cut")

**For Section 5 (pivots):**
- Memory entries with names starting `feedback_` describe rules locked from past corrections. Each is a healthy pivot or costly correction. Follow the `[[slug]]` reference to read the full entry.
- "Rule locked" column in the sit-rep should cite the `[[slug]]`.

**For Section 6 (learnings):**
- Ramp snapshots' bullet lists name patterns demonstrated and durable
- Memory entries starting `feedback_` after the corrective verb ("don't", "stop", "avoid") describe what was killed; those starting `feedback_` after positive verbs ("prefer", "use", "lean") describe what to keep

### Heuristics

- A memory file with a "Re-surfaced" or "Anti-pattern signature to watch for" section indicates the rule was sharpened across multiple instances — that is a stable, high-confidence pattern. Lead with it.
- A memory file's date in its body (vs filename) shows when the rule was first locked; older rules with no updates are stable, recently-updated rules are still in flux.
- A `[[name]]` reference to a slug that doesn't yet exist is a marker the user thought was worth writing later — call it out as an open thread if relevant.

---

## Source: session-log.md

Located at `~/.claude/projects/<project-key>/memory/session-log.md`. Append-only narrative log.

### What lives here

- Dated session entries with header `## YYYY-MM-DD · <8-char session id>` (or `(migrated)` for retroactively-imported MEMORY snapshots)
- Per-entry sections: `**Files changed:**`, `**Git:**`, bullets of key actions, `**What didn't work:**`, `**Resume:**`, `**Open threads:**`

### What to extract

**For Section 2 (chronological):**
- Use session-log entries as a milestone source. The header date + the most-recent commit cited in `**Git:**` triangulate the milestone date.
- Bullets naming "shipped X" or "closed Y arc" are milestone candidates.

**For Section 5 (pivots — healthy):**
- `**Resume:**` lines that changed direction between consecutive entries indicate a pivot. Compare the previous entry's `**Resume:**` to the next entry's opening bullets.
- Bullets containing phrases like "user pushback", "redirect", "stop and re-derive", "reframed" name the trigger for a pivot.

**For Section 5 (pivots — costly):**
- `**What didn't work:**` sections are gold — each names a deviation and (often) its cost.
- Entries with cost figures in their bullets (e.g. "$42 + 2hr lost") are costly-correction candidates.

**For Section 7 (risks):**
- `**Open threads:**` sections name what was unresolved as of that entry. Cross-reference forward — if an open thread never reappears resolved, it is still a risk.
- `**Resume:**` lines that reference "untested in production" or "single-machine" risks are direct risk-register candidates.

### Heuristics

- Read the **last ~500 lines** for a 14-day window. Older entries are useful for "where we've been" but rarely change the present picture.
- Session-log entries with `(migrated)` suffix were originally Session snapshots in MEMORY.md — treat them as MEMORY-quality (stable patterns) rather than narrative.
- A session ID appearing across multiple consecutive entries (e.g. `3bfe8b4a` four entries in a row) marks a long-running session. The patterns demonstrated across that range are higher-confidence than single-session ones.

---

## Source: Findings + review docs

Located under `docs/tools/<tool>/findings/`, `docs/tools/<tool>/review-*.md`, or `docs/architecture/`. Created when an arc closes or a multi-agent review lands.

### What lives here

- **Findings docs** — retrospective for a closed arc, often with cost summary, methodology lock-in, and patch-shape spec for follow-on work
- **Review docs** — convergent findings from multi-agent reviews, usually with proposed track amendments
- **Closer preambles** — `> **CLOSED YYYY-MM-DD in <commit>.**` blocks added to findings docs when a follow-on TaskWarrior item ships

### What to extract

**For Section 1 (orders of magnitude):**
- Findings docs usually open with the headline numbers ("612 ready docs / 153% / $42.00 combined"). Quote them directly.

**For Section 2 (chronological):**
- The arc's closure date (from the doc's `_YYYY-MM-DD.md` filename or its opening date line) is a milestone.

**For Section 4 (deferred with triggers):**
- Findings docs often have "Deferred specs" or "Full re-index" sections naming items with explicit re-trigger conditions. Lift these directly into the deferral table; do not paraphrase.

**For Section 5 (costly corrections):**
- "Library hardening opportunities" or "What we'd do differently" sections in findings docs catalog deviations that produced rules.

### Heuristics

- A findings doc with a `CLOSED` preamble at the top of a section is the canonical answer to "did the follow-on ship?" Trust it over MEMORY or session-log for ship status.
- Multi-agent reviews (4-agent / 3-agent) produce **convergent findings** (3+ agents agreed) — these are the highest-signal claims in the repo. Surface them in Section 5 or Section 7 as appropriate.
- Findings docs created within the window are themselves an order-of-magnitude marker (Section 1: "N findings docs created this week").

---

## Source: Git log

The git log is canonical for **what shipped**, not **why it shipped**. Use it to verify but not to source narrative.

### What to extract

**For Section 1 (orders of magnitude):**
- Commit count over the window (total + topic-filtered)
- Lines added/removed (use `--shortstat` summed via awk)
- Hot files (top N by modification frequency)
- Peak commit day

**For Section 2 (chronological):**
- Use `git log --oneline --since='YYYY-MM-DD'` for verification, not generation. Milestones come from session-log + findings; git log confirms the date.

### Heuristics

- A commit message starting with `add(`, `ship(`, or `update(` is a feature landing. `fix(` and `refactor(` are usually maintenance, not milestones.
- A commit message containing a TaskWarrior ID (e.g. `#246`) is auditable against the TW list — verify the corresponding item is completed.
- Topic-filtered commit count divided by total is a useful "what fraction of effort went into X" anchor. Cite both ("113 of 125 total — 90%").

---

## Source: TaskWarrior

`task project:<domain>.<repo> list` is canonical for **what's pending and recently completed**. Use it for Section 3 (In flight) and Section 4 (Next 1–2 weeks).

### What to extract

- Pending TW items: each is a Section 3 "In flight" candidate
- Recently-completed TW items in window (`end.after:today-14d`): each may be a Section 2 milestone
- TW item descriptions often encode cost ("~10 min pure DB op", "no Sonnet cost"): preserve these in Section 4

### Heuristics

- A pending TW item with a description naming a cost ("~10 min", "$0 cost") is a high-leverage next step — surface it in Section 4 (Next 1–2 weeks) by default.
- A completed TW item that doesn't appear in the git log under a clear commit usually shipped under a different branch or as documentation — note this if it changes the velocity picture.

---

## When sources disagree

- **MEMORY says X exists, but `grep` finds nothing:** Trust the current state. Note the memory as stale; recommend updating it.
- **Session-log says shipped but git log doesn't show it:** Look for a topic-branch or unpushed commit. If genuinely missing, flag as a discrepancy in Section 7 (Risk register).
- **Findings doc says CLOSED but no commit hash:** The closure may be policy-level (deferred-by-removal) rather than code-level. Check the doc's CLOSED line for context.
- **TW item says completed but no matching commit:** Common for pure-documentation or pure-investigation tasks. Acceptable; do not flag.

---

## Source: canonical SQLite / corpus stores

When the topic has a persistent data store (events.db, _staging.db, shards.db, catalog.toml-derived sqlite), it is the **only** trustworthy source for "how big is X right now."

### Heuristics

- **Never cite "84K events" / "612 ready docs" / "$42.00 spend" from MEMORY.md.** Those numbers were correct when written, but counts drift. Re-derive with a live `COUNT(*)` (or read the live findings doc, which itself was written against the live DB at closure time).
- **File size on disk** is itself a Section 1 anchor — `ls -lh ~/data/search/events.db` → "events.db = 1.3 GB" surprises the reader more than the row count alone.
- **Cost-log files** (e.g. `cost-log.jsonl`) — count rows for total paid-call magnitude; do not infer model split from memory, query the file.
- When the canonical store is missing or empty but a memory entry references a number, surface this as a discrepancy in Section 7 (Risks).

---

## Composing the picture

Once signals are extracted, the sit-rep is mostly a sorting exercise:

1. **Numbers → Section 1.** Pick the 5–10 most surprising. Re-derive from live DBs + git, never from memory citations.
2. **Dated events → Section 2.** Sort chronologically; note the bend. Cite TICKET-NNN references verbatim when present.
3. **Completed/pending/blocked → Section 3.** Three buckets. Topic-scoped TW IDs are durable; cite them.
4. **Pending + gated + deferred → Section 4.** Three horizons. Deferral triggers must be measurable.
5. **`feedback_` memory + session-log `**What didn't work:**` → Section 5.** Three sub-tables.
6. **Ramp snapshots + anti-pattern signatures → Section 6.** Two lists.
7. **Open threads + unresolved `**Resume:**` references + obvious-in-hindsight risks → Section 7.** One table. **Today-fresh discoveries belong here** unless they sit on the consumer-unblocking critical path (Section 8).
8. **Synthesis → Section 8.** Name the gate that gates the gate.

If a signal does not fit any of the eight sections cleanly, it probably belongs in Section 7 as a risk or Section 3 as an open thread — those are the catch-alls.

---

## Picking the Section 8 gate (the hardest judgment)

Section 8 fails when an interesting-but-orthogonal blocker is named instead of the load-bearing one. The most common failure mode is naming a today-fresh discovery (a bug, a cost-log gap, a missing audit) because it's top-of-mind, when the actual gate is a policy decision that's been sitting for days.

### The forward-trace test

For each candidate gate, ask: **"If this resolved tomorrow, what gets unblocked?"** Then trace **two hops out**:

- Hop 1: what work item moves to ready?
- Hop 2: what downstream consumer (a tool, a serving layer, a dashboard) starts deriving value?

The right gate is the one whose forward-trace reaches the **largest downstream consumer**. If a candidate's forward-trace terminates at "we'd have signal for a future experiment," that's a Section 7 risk, not a Section 8 gate.

### Disqualifying patterns

A candidate is probably the wrong gate if:

- It surfaced for the first time today (recency bias — would not have been the gate yesterday)
- Its forward-trace hits "interesting follow-on work" but not "consumer value"
- The user has not mentioned it as blocking anything they care about
- Resolving it shrinks a risk but doesn't unlock pending work

A candidate is probably the right gate if:

- The user has named it as a decision they're sitting on
- A ready-but-gated artifact (proposals, docs, drafts) is waiting on its resolution
- Multiple downstream items in Section 4 reference it (directly or transitively)
- Memory contains a recent `feedback_` entry sharpening the policy around it

### Tie-breaker: same chain, different depths

When two candidates both forward-trace to the same downstream consumer, they sit on the same dependency chain at different depths. The correct gate is the one **earlier** in the chain — the upstream gate of the gate.

This is the second-most-common failure mode. You name a candidate that *does* unblock the downstream consumer, but it itself can't be tackled until an earlier decision lands. The reader sees the candidate and asks "what would I do tomorrow about this?" — and the honest answer is "I'd first need to decide X, where X is the actual gate."

Heuristic: if you can sensibly say "we can't stand up Candidate A until we decide Candidate B," then **B is the gate**, even if A is closer to the consumer.

### Worked examples

**Example 1 — orthogonal blocker vs consumer-unblocking gate (2026-06-08 search sit-rep):**

- **Candidate A:** Fix `cost-log.docs_indexed=0` field-population bug (discovered today). Forward-trace: → enables $/doc comparison → enables Haiku-vs-Sonnet bake-off → bake-off informs future model choice. Terminates at "future experiment."
- **Candidate B:** Resolve field-mapping schema review. Forward-trace: → unblocks index write-back policy → unblocks 503 ready docs → unblocks `catalog.toml` writes → unblocks serving-layer/export/dashboard consumers. Terminates at "actual downstream consumer."

**B is the gate.** A is a Section 7 risk row.

**Example 2 — same chain, different depths (same sit-rep, second iteration):**

- **Candidate B:** Field-mapping schema review. Forward-trace: → write-back posture decided → serving-layer rollout productive → consumers integrate.
- **Candidate C:** Serving-layer POC (`~/data/search/serve.yaml`). Forward-trace: → serving layer exists → write-back has a target → consumers integrate.

Both terminate at the same consumer (serving-layer-mediated integrations). But **B is earlier in the chain** — you can't sensibly stand up the serving layer until you've decided what posture write-back takes. Naming C as the gate buries the actual decision (B) under an implementation step that can't begin until B resolves.

**B is the gate.** C is the work that fires once B lands.
