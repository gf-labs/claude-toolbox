# Design Log

Living record of open questions, key decisions, and architectural learnings.
Add entries as they arise — don't wait for a formal session.

---

## Orientation Command Taxonomy

*Decided 2026-04-21*

Four commands answer re-entry questions. Differentiated by absence duration, mental context loaded, and intent:

| | `brief` | `status` | `recap` | `overview` |
|---|---|---|---|---|
| **When** | Cold start / long absence | Mid-stream, still warm | After stepping away briefly | Planning / prioritization |
| **Question** | "Get me back up to speed" | "Where am I right now?" | "What did I do recently?" | "What should I work on next?" |
| **Session log** | Last 3–5 entries (scales to absence) | Last entry only | All entries in window | No |
| **Backlog** | In Progress + Up Next | In Progress only | No | Highlights (top 3–5) |
| **Plans** | All active | No | No | All active + sequencing |
| **Architecture snapshot** | Yes (scales to absence) | No | No | No |
| **Git state** | Summary | Detailed (diff stat + hunk headers) | Commits in window | In-flight summary |
| **Recent activity** | Yes (collect-history.py) | No | Files touched in window | Recent work (last few sessions) |
| **Next step** | Suggested | Immediate | "Pick up here" (one line) | Full sequencing (3 tiers) |
| **Model** | Haiku | Haiku | Haiku | Sonnet |
| **Writes?** | No | No | No | No |

**Depth scaling (brief only):** ABSENCE_DAYS drives output depth automatically — no flag needed.
- < 2 days: last 1 session log entry, skip architecture + MEMORY.md
- 2–7 days: last 3 entries, brief architecture snapshot
- 7+ days or unknown: last 5 entries, full architecture, full MEMORY.md

**recap time window:** `--days N` (default 1) or `--hours N` for sub-day windows.

**Architectural distinction:** `brief` always includes project-state (backlog, plans, architecture); `recap` never does. The time window is `recap`'s only lens — it cannot substitute for `brief`.

**overview freshness:** cross-references last session log Resume/Open threads field when building the sequencing section — surfaces in-motion work at top of Now tier.
