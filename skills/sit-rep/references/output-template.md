# Sit-Rep Output Template

Canonical structure for the project sit-rep. Each section below specifies its purpose, what to include, what to exclude, and an example row drawn from an example search-index sit-rep produced 2026-06-08.

The document opens with an H1 header naming the scope and date:

```markdown
# Sit-rep — <scope> · YYYY-MM-DD
```

If a topic filter is active, declare it on the line immediately below:

```markdown
**Re-scoped to <topic>** (note any adjacent areas included and why).
```

---

## Section 1: Velocity (orders of magnitude)

**Purpose:** Anchor the reader in scale before narrative. Five to ten numbers that surprise.

**Include:** Commit count + line delta over the window, hot files, peak day, key dataset sizes (events, docs, corpus tokens), money spent on paid runs, percent of target reached.

**Exclude:** Round-number metrics that anyone could guess. "We have a CI pipeline" is not an order of magnitude; "tier-2 sweep processed 1.2M tokens" is.

**Example:**

```markdown
| Metric | Value |
|---|---|
| Search-scoped commits | **113** of 125 total (90%) |
| Lines net | **+35,314 / −1,620** |
| Hot file | `cli.py` — touched in **34** commits |
| Findings docs created this week | **5** under `docs/tools/search/findings/` |
| Events in `events.db` | **84K+** |
| Tier-2 sweep corpus | **1.2M tokens** |
| Index arc surface | **612 ready docs** at v2 dual-score threshold |
| Index arc spend | **$42.00** combined dry-run |
| North-star achievement | **153%** (target 400, hit 612) |
```

Close with one sentence framing the scale ("This is the work of a small team's quarter, compressed.").

---

## Section 2: Where we've been

**Purpose:** Show the arc, not the diff. The reader should see how shape changed over the window.

**Include:** Dated milestones; for each, a one-line "order-of-magnitude marker" in the right column (cost cut, event yield, lines shipped, % achieved).

**Exclude:** Routine commit messages. A milestone is something the project would lose value if you removed.

**Example:**

```markdown
| Date | Milestone | Order of magnitude |
|---|---|---|
| 2026-05-25 → 5/30 | V1 engine scaffold: ingest + FTS5 + dedup + ranking V1 + scheduler + embeddings | ~50 commits in 6 days |
| 2026-05-30 | **V1 shipped** | Foundational |
| 2026-06-01 | **TICKET-204 batch tuning** — 47% cost cut, 2–3× event yield | Cost halved |
| 2026-06-05 | **Multi-method index arc closed dry-run at 612 / 153%** | North-star reached |
| 2026-06-06 | **/tmp wipe loses $42 / 2hr arc** → policy locked | Painful corrective |
```

After the table, name the bend in the curve in one sentence:

> "The bend in the curve: mid-arc we shifted from *building extraction* to *validating extraction quality* — the v2 dual-score model and the dry-run-only policy both flow from recognizing that 'the ranker says new' is insufficient signal for promotion."

---

## Section 3: Where we are right now

**Purpose:** Three crisp buckets so the reader can locate every in-progress thread.

**Sub-buckets (always in this order):**

### Closed
Bullet list of substantive completions in the window. Each bullet names the artifact, not the commit.

### In flight
Pending TaskWarrior items, plus any work that is staged but not landed. Note Sonnet/cost implications.

### Gated (with explicit triggers)
Work that is correct but waiting. Name the trigger explicitly. If double-blocked, list both blockers.

**Example:**

```markdown
### Gated (correctly)
**Write-back of 503 net-new ready docs → `_staging.db` → `catalog.toml`** is gated on:
1. [[indexing-dry-run-only]] — explicit user go-ahead required
2. /tmp artifact loss — verdicts cost ~$42 to re-derive against durable storage

**Decision trigger:** downstream-consumer demand (serving-layer rollout, export job, dashboard).
```

End the section with one **Repo state** line: branch + ahead/behind + dirty count + scope of dirty work.

---

## Section 4: Where we're going

**Purpose:** Three time horizons so the reader sees both committable next-steps and conditional future work.

**Sub-headers (always in this order):**

### Next 1–2 weeks
Committable work — items that can land without further user decision. Note Sonnet spend / no-spend.

### Gated on signal
Items that won't move until an external condition changes. Name the condition.

### Deferred with explicit triggers
Table format: Item · Trigger. Re-trigger conditions must be measurable, not aspirational.

**Example deferral table:**

```markdown
| Item | Trigger |
|---|---|
| Phase 2A live probe (full enrichment) | Phase 2C succeeds + cost envelope confirmed |
| Phase 3 v3 (related/depends_on edges via LLM) | Parent inference proves out at scale |
| Self-hosted embeddings | bge-small-en-v1.5 hits quality ceiling |
| Full re-index pass (~6,200 docs, ~$310) | Write-back happens AND re-index coverage gap independently flagged downstream |
```

---

## Section 5: Pivots & deviations

**Purpose:** Show course corrections. Distinguish smart ones from costly ones.

**Sub-tables (always all three, even if a row is missing):**

### Healthy pivots
| Pivot | Trigger | Outcome |

### Costly corrections (painful, but corrective)
| Deviation | Cost | Rule locked |

The "Rule locked" column is critical — it shows the deviation produced a durable rule, not just a one-off fix.

### Non-pivots that turned out right
Bullets describing what was *held* despite pressure to change. These are the underappreciated wins.

**Example costly-correction row:**

```markdown
| Overnight Sonnet arc to `/tmp` | **$42 + 2hr arc lost** to macOS reboot wipe | [[long-runs-write-durable]] — runs >$5/100calls MUST write to `~/data/` or `~/Repos/<project>/.runs/`; NEVER `/tmp` |
```

---

## Section 6: Learnings

**Purpose:** Distill durable patterns. One sentence each. Evidence in parens.

**Two lists:**

### Keep (patterns proven repeatedly)
Each item: one sentence describing the pattern + one phrase of evidence.

### Killed (anti-patterns retired)
Same format; describe what was tried and why it was retired.

**Example "Keep" item:**

> Script→library lifting — when 2nd instance of in-script pattern appears, lift to library. Expose mechanism, keep policy in caller. (TICKET-246 left `output_dir` to caller per docstring guidance)

**Example "Killed" item:**

> Trusting the `[index build] WARN: 5h quota at X%` line — per-session-scope, not account-aggregate. Replaced by Settings → Usage as ground truth (`[[quota-warn-unreliable]]`)

---

## Section 7: Risk register

**Purpose:** Make the reader see the boring-but-real risks without panic-mode framing.

**Table format:** Risk · Likelihood · Impact · Mitigation status

**Rules:**
- 5–8 rows max
- Include the obvious-in-hindsight risks (unpushed branch, dirty tree spanning multiple arcs, library untested in production)
- "Mitigation status" must be honest: "tracked", "documented but not started", "policy locked", "awaiting downstream signal"

**Example row:**

```markdown
| TICKET-246 library hardening untested in real production traffic | Until next paid run | Edge cases the 8 unit tests miss | First real-traffic test will be the next index arc; `paused`/`rate_limited` summary keys give observability |
```

---

## Section 8: The shape of the next inflection

**Purpose:** A short narrative close — 2–4 sentences. Name the gate that gates the gate.

**What to include:**
- One-sentence summary of the work pattern over the window (e.g. "Two weeks of build → validate → lock policy has produced X")
- The **next inflection** — what changes the shape of the work going forward
- The **gate** — the single question that, if answered, unlocks downstream choices

**What to avoid:**
- Restating Sections 1–7
- Generic "the team is doing great" closes
- Action items that belong in Section 4

**Example close:**

> Two weeks of build → validate → lock policy has produced a clean dry-run frontier and a hardened library substrate. The next inflection is **wait for downstream pull, or seed it**. The 503 ready docs are correct work that has nowhere to land productively yet. Two paths: be patient and let consumers materialize on their own cadence, or stand up a minimum serving-layer POC to give write-back a target. The choice is downstream of how much you trust the dry-run counts to age well — which is downstream of TICKET-250's field-mapping schema review. **TICKET-250 is the gate that gates the gate.**

End with one sentence reading the overall health:

> "The work is healthy. Velocity is sustained, course corrections produced durable rules, and the gates are clearly named."

---

## Section-omission rules

A section may be omitted if it has nothing substantive. Heuristics:

- **Skip Section 5 (Pivots)** only if the window genuinely contained no course corrections. Most windows ≥7 days have at least one.
- **Skip Section 6 (Learnings)** only if no ramp snapshots or anti-pattern signatures landed in `MEMORY.md` during the window.
- **Skip Section 7 (Risks)** only if the repo is in a known-quiescent state (recently shipped, nothing in flight).
- **Never skip Sections 1, 2, 3, 8.** Velocity, history, present, and inflection are the core narrative spine.

When omitting, do so silently — do not write "Section 5: (none)". Just skip the header.
