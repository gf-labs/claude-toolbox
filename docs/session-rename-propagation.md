# Session Rename Propagation and the Fork Election

*Investigated 2026-09-04. Status: fix applied 2026-09-04 — `isMeta` gate in
`scan_session` + two regression tests (fail unpatched → pass); suite 429, ruff clean.*

A `/rename` in one Claude Code session silently retitles **other** sessions in the
same compact-chain. claude-toolbox's fork relabeler then resolves the resulting
collision **backwards**, because the propagated write always lands last. Net effect:
renaming a session hands its name to a different session, repeatedly, and no amount
of renaming escapes it.

This document records the evidence, the root cause, the one-line fix, and the
approaches that were tested and rejected.

---

## Symptom

Two sessions in `~/.claude/projects/-Users-berniegreen-Repos-projects-job-search/`:

| session | size | role |
|---|---|---|
| `c6ec6058-3a21-40ab-8b8f-d999d8a42586` | 30.7 MB | the real work, live in a zellij pane |
| `b15da7c4-b356-44a5-9f59-64390e57d749` | 1.0 MB | leftover, no process, idle since 15:30 |

Every attempt to name the big one `job-search-main` (then `js-main`) ended with the
big one carrying a `~09-04` stale marker and the 1 MB leftover holding the clean name.

This matters because `workstation` seeds resume by title (`--resume <name>`), so a
title flip turns into a seed pointing at a session that no longer answers to that
name. `workstation` is not a cause — it is what makes the breakage visible.

---

## Root cause: Claude Code renames a *group*

`~/.claude/history.jsonl` records which session each slash command was typed in.
Cross-referencing it against the `custom-title` records in each session file:

| when (ET) | `/rename` typed in | what the *other* file did |
|---|---|---|
| 14:50:33 | b15da7c4 → `job-search-prep` | nothing |
| 15:04:55 | b15da7c4 → `job-search-prep` | c6ec6058 retitled, same second |
| 15:50:25 | c6ec6058 → `job-search-main` | b15da7c4 retitled, **+55 ms** |
| 17:12:54 | c6ec6058 → `js-main` | b15da7c4 retitled, **+61 ms** |

Three of four renames wrote a title into a session the user was not in and did not
rename. The writes are Claude Code's own (compact JSON, versus the spaced
`json.dump` output claude-toolbox produces), and Claude Code additionally injects a
turn into the other conversation reading *"The user named this session …"*.

`relabel-forks.py`'s own docstring already names this behavior: the `/resume` picker
*"shows two identical rows and renames them as a **group** (the compact-chain)."*

### Where the grouping shows up on disk

**Corrected 2026-09-04, second pass.** An earlier version of this document said
*"there is no shared identifier on disk — the grouping lives inside Claude Code."*
That is false, and it was reached by looking only at the session JSONLs. Those carry
no fork link, but Claude Code's **job state** does.

`~/.claude/jobs/c6ec6058/state.json`:

```
sessionId        c6ec6058-3a21-40ab-8b8f-d999d8a42586
resumeSessionId  b15da7c4-b356-44a5-9f59-64390e57d749
linkScanPath     …/b15da7c4-b356-44a5-9f59-64390e57d749.jsonl
nameSource       user
```

An explicit link between exactly the two sessions that rename together. The
background process's own command line spells out the same lineage:

```
claude --session-id c6ec6058-… --fork-session --resume …/da35b7bc-….jsonl
```

This is a real opening: a group-aware relabeler could read `resumeSessionId` rather
than inferring forks from shared base titles. **Untested** against the four-row
propagation table above — a candidate mechanism, not a confirmed one.

`nameSource` is uniformly `user`, *including* on the session whose name arrived by
propagation, so it cannot distinguish a real rename from a propagated one.

### What the grouping is *not*

- **Not a fork link inside the session JSONL** — no `parentSessionId`, `forkedFrom`,
  or equivalent in the conversation files themselves. The link lives one level out,
  in job state.
- **Not a bridge mirror** — `b0801a38` shares `bridgeSessionId`
  `cse_01CcWH6h4Kz9G2Z9FwUvj4vz` with `c6ec6058` in job state and did **not** rename
  with the group. (An earlier version claimed each session has its *own*
  `bridgeSessionId`; that was read off the JSONLs and is too strong. The conclusion
  holds — a shared bridge id does not imply a shared rename — but that supporting
  claim does not.)
- **Not cwd-wide** — `cab6adf9` (`job-search-scratch`) sits in the same directory,
  is also bridged, and has exactly **one** title across its whole history. It is the
  control case.

**Best-fitting explanation (inferred, not proven):** the two became a group at 14:53
when they briefly shared the literal title `job-search-main`, and the grouping stuck.
That fits all four rows — the 14:50:33 rename did not propagate because their titles
still differed, and the two later ones propagated even though the titles differed
*again* by then (`…~09-04` vs clean). If correct, **a `~MM-DD` suffix does not
ungroup them**, contrary to what `relabel-forks.py`'s docstring assumes.

---

## Why the workaround makes it worse

`session_naming.plan_fork_relabels` exists to work around exactly the above: within a
project, sessions sharing a base title are forks; the newest by last-event timestamp
keeps the clean name, the rest get `base~MM-DD`.

The propagated rename is written to the *other* file **after** the one you typed in —
by 55 ms, then 61 ms. So immediately after any rename, the tiebreak crowns the session
you did not rename. It is not flaky; it is reliably backwards.

Measured at 17:13, before any corrective action:

```
b15da7c4   last event  21:12:54.306Z   <- wins under current logic
c6ec6058   last event  21:12:54.245Z
```

Neither component alone would loop. Without the group rename there is no collision.
Without the relabeler you would have two identically-titled sessions — untidy but
stable.

---

## The mechanism: an injected turn with a timestamp

The propagation writes a batch of records into the receiving file. Enumerating every
record written into `b15da7c4` after its last genuine turn (15:30:54):

| record type | carries `timestamp`? |
|---|---|
| `custom-title`, `agent-name`, `ai-title` | no |
| `mode`, `permission-mode`, `atis-latch` | no |
| `file-history-snapshot`, `last-prompt` | no |
| `bridge-session` | no |
| **`user` (the rename echo)** | **yes** |

Exactly one timestamped record, and it is synthetic:

```json
{
  "type": "user",
  "isMeta": true,
  "sessionKind": "bg",
  "message": {
    "content": "<system-reminder>\nThe user named this session \"js-main\". This may indicate the session's focus or intent.\n</system-reminder>"
  },
  "timestamp": "..."
}
```

That single fake turn is the entire defect on our side. `b15da7c4` accumulated **11**
of them and had been winning ties on echoes alone since 15:30.

```
b15da7c4   last ANY event   17:12:54.306
           last REAL event  15:30:54.894    <- almost 2 hours earlier
c6ec6058   last ANY event   17:21:56.792
           last REAL event  17:21:56.792
```

---

## The fix

An injected turn is not human activity and must not advance the activity clock.
One added condition in `session_naming.scan_session`:

```python
                    if t:
                        saw_event = True
                        if obj.get('sessionKind') != 'bg':
                            saw_non_bg = True
                        if not obj.get('isMeta'):     # injected turn, not human activity
                            ts = t
```

`saw_event` and `saw_non_bg` semantics are unchanged — only the activity clock moves.

**Regression tests** (added 2026-09-04, beside
`test_plan_fork_relabels_promotes_live_to_clean_name` in `tests/test_session_naming.py`;
both watched failing before the patch — the election test's unpatched failure output
proposes demoting the *live* fork, the real-world flip verbatim):

- `test_scan_session_meta_records_do_not_advance_activity_clock` — the clock skips an
  `isMeta: true` echo but still advances on `isMeta: false` (slash commands) and on
  plain turns (no key).
- `test_plan_fork_relabels_meta_echo_does_not_steal_clean_name` — an echo in the stale
  fork newer than the live fork's last real turn; the stale fork is demoted by its own
  real-activity date.

Two corpus facts firm the gate up beyond the table above (checked 2026-09-04): genuine
human turns carry no `isMeta` key at all — on timestamped records the field occurs only
as `user`+`isMeta: true` (injected) or `system`+`isMeta: false` — and no session file is
all-`isMeta` (0 of 48), so the gate cannot leave a clock empty. The change deliberately
flows through `scan_title_and_ts` into the atlas sessions facet: "last activity" means
last *real* activity there too.

---

## Rejected alternatives

**`sessionKind == 'bg'` — actively wrong.** It looks like the principled filter and is
not: it appears on nearly every record, real conversation turns included.

```
b15da7c4:  253 of 260 timestamped records are sessionKind:'bg'
c6ec6058: 6746 of 6797 timestamped records are sessionKind:'bg'
```

Filtering on it selects 15:17:07 instead of 15:30:54 — it discards genuine activity.
Note this is *not* the same as `scan_session`'s existing `is_bg` flag, which requires
**every** record to be bg and is correct as written. Leave that alone.

**Matching the reminder text** (`'The user named this session' in content`) — produces
an identical result on real data (15:30:54.894), but depends on Anthropic's wording.
`isMeta` is structural and survives a rewrite.

**Switching workstation seeds to `--resume <uuid>`** — trades one bug for a worse one.
Titles follow a compact chain across forks; uuids do not. A uuid-pinned seed would
silently resume the pre-compact fork, which is harder to notice than a title flip.

---

## Verification performed

| check | result |
|---|---|
| Is the echo the only timestamped record the propagation writes? | Yes — table above |
| Would the fix have prevented the 2026-09-04 flip? | Yes. At 17:13: current logic crowns b15da7c4; patched crowns c6ec6058 |
| Patched election against live data | Proposes exactly `b15da7c4 → js-main~09-04` |
| Idempotent? | Yes — re-planning after applying yields no actions |
| Do slash commands still count as activity? | Yes. `/rename` and `/compact` are `isMeta: False`; `away_summary` likewise |
| Baseline suite | `tests/test_session_naming.py` + `tests/test_relabel_forks.py` — 49 passed |

**One behavior change beyond the echo:** `isMeta: true` also marks the pin skill's own
`## Collect context` injection, so a `/tools:pin` body does not itself register as
activity. The assistant turns that follow it do, so no session goes dark from this.

---

## Scope

This repairs the **election**, not the propagation. Claude Code will still rename the
group; the relabeler will resolve it correctly and immediately instead of crowning the
wrong file. The group rename cannot be prevented from this side.

The underlying defect is upstream — `/rename` writes titles into sessions the user is
not in, with nothing in the UI showing the group exists or which sessions are in it.
Worth reporting to Anthropic.

It also repairs only **one of three** name stores — see below.

---

## Three name stores, and we write one

*Found 2026-09-04, second pass, from a peer roster showing two sessions both
addressable as `js-main`.*

A session's name lives in three places. claude-toolbox **writes** the first and only
the first. (**Corrected 2026-09-04, third pass:** an earlier version claimed *no
reference* to `.claude/sessions` or `.claude/jobs` anywhere in `scripts/` or `hooks/`.
False — `scripts/_session.py` *reads* the roster as Tier 2 of `current_session_jsonl`,
matching on `cwd` and ranking by `startedAt`. The claim came from grepping for the
literal path; the code builds it as `home / '.claude' / 'sessions'`, which a literal
grep misses. Nothing anywhere touches `.claude/jobs`, and nothing writes either store,
so the write-side claim stands. Useful consequence: a divergence check can lift
`_session.py`'s roster loop, malformed-JSON and non-dict guards included.) Measured for
`b15da7c4` immediately after a successful `relabel-forks.py --apply`, all three
disagreed:

| store | value | written |
|---|---|---|
| session JSONL `custom-title` | `js-main~09-04` | 18:10 — our relabel |
| `~/.claude/sessions/<pid>.json` → `name` | `js-main` | 17:12:54.296 — the propagation |
| `~/.claude/jobs/<jobId>/state.json` → `name` | `job-search-prep` | 14:50 — the original rename |

So a relabel repairs the `/resume` picker and leaves the **peer roster** duplicated.
The repair reads as successful while the ambiguity it was meant to remove is still on
screen.

It is the same defect, not a second one. `nameSince` on the two colliding peers:

```
c6ec6058 (typed in)     17:12:54.238
b15da7c4 (propagated)   17:12:54.296     Δ 58 ms
```

Same order, same 55–61 ms band as the `custom-title` writes. One `/rename`, two peers
named.

**Why this surface is worse than the picker.** Roster names are *addresses* —
`SendMessage({to: "js-main"})` against two matching rows has to fall back to the
bracketed ref. A duplicate in the picker is confusing; a duplicate here is ambiguous.

**Do not start by writing the other two stores.** They are Claude Code's own live
state, rewritten by running processes; a racing write can be clobbered or corrupt
state. That is a materially different risk from appending a `custom-title` record to a
JSONL. Report divergence first.

One more thing the roster surfaces: a background job in `state: done`, `tempo: idle`
keeps holding a name. `pid 8315` has been resident since Aug 21 (`startedAt`) but has
answered to `js-main` only since the 17:12:54.296 propagation (`nameSince`) — two
different fields an earlier version of this section conflated. Done, idle, resident,
and holding an address the bug handed it.

---

## Follow-ups worth considering

1. **Sticky winner.** Persist the elected sid per base title in the existing registry
   (`~/.claude/data/tools/<project_key>/sessions-meta.json`, via `session_index.py`).
   Re-elect only when the incumbent has had no real activity for N days. The
   `plan_fork_relabels` docstring already records two prior rounds of ping-pong
   fighting; stickiness ends the class rather than this instance.
2. **Near-tie guard.** If the top two timestamps are within ~5 seconds, that is not a
   meaningful activity difference — fall back to a stable key (real-turn count, or
   whoever currently holds the clean name). Insurance if `isMeta` ever stops matching.
3. **Make relabels loud.** Have `post-save.py` warn when it relabels a session that is
   currently running in a pane — the only case that breaks a `ws --resume`. Today it
   relabels silently and the damage surfaces days later as a stale seed.

---

## Diagnostic recipe

When a session title moves on its own:

```bash
PROJECT_KEY=-Users-berniegreen-Repos-projects-job-search   # adjust

# 1. What is each session actually called, and how big is it?
python3 - "$PROJECT_KEY" <<'PY'
import os, sys
from pathlib import Path
sys.path.insert(0, os.path.join(os.environ["CLAUDE_TOOLBOX_ROOT"], "scripts"))
import session_naming as sn
d = Path.home()/".claude/projects"/sys.argv[1]
for f in sorted(d.glob("*.jsonl")):
    t, ts, bg = sn.scan_session(f)
    if t:
        print(f"{f.stem[:8]}  {f.stat().st_size/1e6:7.1f} MB  {t:<24} {ts}  bg={bg}")
PY

# 2. Who actually typed a rename, and where? (Claude Code's own record)
python3 - <<'PY'
import json, datetime
from pathlib import Path
for line in open(Path.home()/".claude/history.jsonl", errors="replace"):
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if str(r.get("display", "")).startswith(("/rename", "/compact")):
        when = datetime.datetime.fromtimestamp(r["timestamp"]/1000)
        print(when.strftime("%m-%d %H:%M:%S"), r["sessionId"][:8], r["display"])
PY

# 3. What would the relabeler do right now? (dry-run is the default)
python3 $CLAUDE_TOOLBOX_ROOT/scripts/relabel-forks.py --path ~/.claude/projects/<project-key>
```

A title that changed with **no** matching `/rename` in `history.jsonl` for that session
id is a propagated rename, not something you did.

### Recovering a session that lost its name

Do **not** `/rename` your way out — each rename re-ties the election with the copy
landing last.

1. Send one real message in the session you want to keep the clean name. That puts it
   genuinely ahead instead of milliseconds behind.
2. `relabel-forks.py --path <project-key-dir> --apply`.

Those writes are file-level and do not propagate — that is the whole point of the script.
