# claude-toolbox backlog

The open product work, curated. Tracked here; to pick one up, see
[CONTRIBUTING.md](CONTRIBUTING.md).

Each item states the problem and the proposed change, checked against the source at the
time of writing. Items marked **Proposal** sketch a direction that still needs a design
pass; items marked **Decision needed** wait on a design call, not on effort.

## Bugs

### `consolidate-tasks` writes its working manifest to a fixed `/tmp` path

**Problem.** The command stores the scanned manifest and the approved subset at
`/tmp/consolidate-manifest.json` and `/tmp/consolidate-approved.json`. Two sessions running
it at once clobber each other's manifest mid-review, and a host that restricts writes under
`/tmp` fails the command at its first step.

**Fix.** Create the files with `tempfile`, which honours `$TMPDIR`, and pass the path
between the collector and `add-tasks.py` explicitly.

### `consolidate-tasks` cannot exclude a root tracking file

**Problem.** The collector treats every root-level `BACKLOG.md`, `TODO.md`, `ROADMAP.md`,
or `INITIATIVES.md` as an inbox, and a `README.md` too when one of its headings looks like
a planning section: it extracts each bare bullet as a proposed task and, once every
approved item has been added, overwrites the whole file with a tombstone pointing at the
task store. The `exclude` list in `.tw-slugs.json` applies only to the `docs/` scan, so a
curated, published backlog such as this file has no opt-out and would be consumed by its
own tool, and a README with a "Next" section would be replaced by a one-line tombstone.

**Fix.** Honour the exclude list for root files too, or recognise a marker line in the
file; never tombstone an excluded file or a `README.md`. Add a test that runs the collector
against a repo whose root backlog is excluded and asserts no items and no tombstone.

### The MCP server is registered before its virtualenv exists

**Problem.** The `SessionStart` hook registers the bundled MCP server with Claude Code
whenever its launcher script is present, and the launcher runs the server with the
interpreter in `mcp_server/.venv`. Nothing creates that virtualenv: the README describes it
as a step for manual registration only, so a fresh install gets a registered server that
cannot start.

**Fix.** Check for the virtualenv before registering. When it is missing, either create it
and install the server's dependency, or skip registration and print the setup command; and
make the launcher fail with a clear message rather than a missing-interpreter error.

## Features

### Hook-enforce memory migration and check the size budget before appending

**Problem.** Every `## Session snapshot` block in `MEMORY.md` moves to the session log only
when `pin` runs, as a prompt step the model performs; nothing checks that it happened, and
a session that ends without a pin leaves the blocks in place. On size, Claude Code loads
only the head of `MEMORY.md` and reports an error after a write that crosses its limit,
but the plugin's own append comes first: `pin` writes its section without checking the
budget and `wrap` only warns near the cap, so an entry can land over budget and the
trimming happens after the fact.

**Fix.** Run the migration from a `SessionStart` or `PreCompact` hook, so it happens on
session events rather than on the user remembering a command, and have `pin` measure the
file against the budget before it appends, trimming or refusing the entry instead of
leaving it to the post-write error.

### Cap multi-agent fan-out mechanically

**Problem.** One `Agent` batch or `Workflow` script can dispatch dozens of subagents, each
with its own context, so a single over-scaled call can cost more than the rest of the
session before any result lands. Claude Code's own guards are a running-count throttle on
the `Agent` tool and size limits and warnings on a workflow run; none of them refuses a
launch above a budget the user set, so the only pre-launch guard is guidance the model can
skip under momentum.

**Fix.** A `PreToolUse` hook on `Agent` and `Workflow` that estimates the dispatch count
from the call (parallel `Agent` batches; `parallel` and `pipeline` fan-out in a `Workflow`
script), prints the estimate, and denies above a configurable threshold, so the user sees
the scale before launch rather than in the bill.

### Resolve the plugin root without a manual environment variable

**Problem.** Commands call their scripts through `${CLAUDE_TOOLBOX_ROOT}`, which the user
must set by hand in `~/.claude/settings.json` after a marketplace install, and the
`SessionStart` validator exits non-zero every session until they do. Parts of the plugin
already resolve themselves: the hooks use Claude Code's `${CLAUDE_PLUGIN_ROOT}`, one
bundled skill falls back through `${CLAUDE_PLUGIN_ROOT:-$CLAUDE_TOOLBOX_ROOT}`, the other
documents the same fallback in prose, and the MCP setup hook falls back to its own path.
The command files still need the manual step, as do the skill bash blocks that call the
shared scripts directly.

**Fix.** First prove, on a real marketplace install, that Claude Code substitutes
`${CLAUDE_PLUGIN_ROOT}` inside command bodies and that the fallback form survives the
substitution: the variable is not in the shell environment, so an unrecognised form would
always take the fallback. Then give the command bash blocks that fallback so the scripts
need no change, centralize it in a shared include once the include mechanism is proven to
resolve from the marketplace cache, and soften the validator to warn-only.

### `/tools:memory-hygiene`: an on-demand audit of a project's memory pair

**Problem.** `MEMORY.md` and `session-log.md` accrete across sessions with nothing that
audits the pair: facts duplicated between them or across the topic files `MEMORY.md`
indexes, durable facts with no date stamp, topic files the index no longer references and
references to files that no longer exist, snapshot sections not yet migrated, and size
against the thresholds the plugin already warns at.

**Fix.** A report-only command with an opt-in `--fix` that checks dedup, staleness (oldest
undated first), dangling references and orphans, and size budget. Distinct from the
migration hook above, which is automatic on session events; this is the hygiene pass a
maintainer runs on purpose.

### Roll up and clean every `CLAUDE.md` in the load chain

**Problem.** Claude Code loads `CLAUDE.md` files recursively up the directory tree, so rules
stack across the global, parent-directory, and repo levels. The atlas `claude.md` facet
already maps which files a project inherits and stops there by design: nothing renders what
is actually resident at a cwd, or finds rules duplicated or contradicting across levels.

**Fix.** A skill that renders the consolidated view resident at a directory, then, on
opt-in, dedups overlapping rules, flags stale or contradictory directives, and proposes
where each rule belongs (global, parent directory, or repo). Report-only by default. It
must never move a private directive into a public repo, and must respect the user's
directory layout.

### Unified search across memory, tasks, and plans

**Problem.** `/tools:search-sessions` searches transcripts, and nothing searches the other
stores the plugin reads: project memory files, the TaskWarrior backlog, and plan files. The
README roadmap promises unified search from one command.

**Fix.** One search command across every store above with a per-store filter, extending the
session search and keeping its table shape: one row per hit with where it lives, its age,
and a line of context.

### `/tools:decide`: an append-only decision log

**Problem.** Design specs, which the atlas `specs` facet already indexes per repo, record
the *what*. Nothing records the *why*: the alternatives weighed, the rationale, and the
condition that would reopen the decision. Those live in session logs, where they are hard
to find again.

**Fix.** An append-only capture command (decision · alternatives · rationale · revisit-if)
with a query layer, indexed by the atlas `specs` facet next to the design specs and plans
it already lists, and able to backfill decisions from those existing specs. `wrap` gets an
optional decision-capture step at close-out, and `pin` can surface decisions made but not
yet recorded.

### `tools:archaeologist`: a read-only "when and why did we do X" agent

**Problem.** Answering "when and why did we decide X" means reading across session logs,
memory, and raw transcripts by hand, often across projects.

**Fix.** A read-only agent that synthesizes over the session log, the decision log above,
memory, and raw session transcripts across all projects. The natural reader for that
decision log; an agent because the work is open-ended search and synthesis.

### A portfolio rollup across the backlog and design artifacts

**Problem.** `/tools:overview` is a sequencing brief for one session: a handful of top
tasks, the plan map, recent commits, and Now/Soon/When tiers. It never reads the repo's own
specs and plans, and has no view of the whole backlog by lifecycle, open decisions, or
accumulated debt.

**Decision needed.** Extend `overview` or add a separate `rollup`. Either way the shape is
a new collector that gathers:

- the full backlog categorized in-flight / designed / ideated / debt, with a stale tail;
- spec and plan status parsed from their headers (approved, plan-ready, executed),
  extending the atlas `specs` facet, which today reports live versus done from the
  filename;
- open decisions and discussions, from the decision log and exploratory docs;
- a debt rollup: dependency bumps waiting, lint warnings, uncommitted docs.

### Rethink the orientation surface

**Problem.** `brief`, `status`, `recap`, `overview`, and `sit-rep` are fixed-template
reports assembled from one shared pool of collectors. They overlap enough that it is
unclear which to run, and a fixed template often misfits the moment; what the user wants
is synthesis steered in conversation, not a choice between reports.

**Proposal.** Split the shared context layer from a steerable lens layer, add two readers
the pool lacks (the live transcript as narrative, and specs/plans/memory as intent), and
make it a user setting whether orientation is pushed at session start or pulled on request.
Pick the mechanism per component (command, skill, hook, or MCP tool) rather than defaulting
to a command. The atlas collectors already provide the shared substrate; the lens layer and
the two readers remain.

### Atlas: filter and sort the digest by session recency

**Problem.** The digest line shows each project's session count and the age of its newest
session, but the table cannot be filtered or sorted by that age, so finding which projects
had live work this week still means reading every row.

**Decision needed.** An `--active Nd` filter that keeps only projects with a session inside
the window, a recency sort, or both. A short design pass picks one.

### Atlas: a named-session table with size and context columns

**Problem.** No view outside the cleanup and search flows merges every named session with
its size, recency, and context columns, grouped by where it lives on disk. The atlas
sessions facet lists each session's id, title, and last-event date per project and nothing
more.

**Fix.** An atlas `--tree` or extended `--full` mode, reusing its scope and orphan
resolution, that scans transcripts for the latest custom title and emits one merged table
sorted by size: top-level directory, repo, title, line count, context size at the last turn
and the window that size implies, history size, model, last active, message and tool-call
counts, compactions. Design constraints:

- file a session under the directory where most of its events occurred, not its first
  cwd, since sessions change directory mid-run;
- read each transcript's own cwd field rather than decoding the project key, which is
  lossy and produces false orphans;
- dedupe resume-duplicated records before reporting size, since one transcript can be
  many times its unique length;
- flag duplicate titles only within a project key, the scope `--resume` resolves.

### Compaction-resilient context recovery

**Problem.** The `PreCompact` hook refuses to compact until a `pin` has run, so a session
log entry exists before context is lost, and the orientation commands read the log on
demand; nothing re-injects it automatically after compaction, so recovery depends on the
user remembering to ask. The entry is also narrative, so hard-won repo state (landed SHAs,
held or unpushed work, gotchas, corrections) has no fixed place in it. And the gate is
registered without a matcher, so it blocks automatic compaction too: an unpinned session
that reaches the context limit fails its request instead of compacting.

**Fix.** Make the pin entry carry a compressed dev-state ledger as part of its ritual,
inject the latest entry on a `SessionStart` with a compaction source, deploy a subagent to
roll the file up when it is too large to inject whole, and scope the gate to manual
compaction or have it write the checkpoint itself when compaction is automatic.

### `consolidate-tasks`: a pluggable issue-source adapter

**Problem.** The collector's issue source is hard-wired to `gh issue list`, so a repo
tracked anywhere but GitHub contributes no issues to the consolidation.

**Fix.** An adapter interface with GitHub as the default and other trackers opt-in, kept
generic for the public plugin.

## Git-policy tooling

The plugin ships a read-only `git-policy-auditor` agent, a `stamp-git-policy.py` transform
that renders the policy's CI files into a target repo, and a `git-guard` hook that denies
the irreversible git operations on the model's own Bash calls. These extend that surface.

### A worktree-aware feature-branch command

**Problem.** The policy says new work starts on a `feature/*` branch off `develop`, never on
`develop` or `main` directly, and the guard cannot enforce it: branching is reversible, so
the rule lives in prose and depends on remembering it.

**Fix.** A command that creates a policy-correct feature branch off an up-to-date
`develop`, with optional worktree isolation for work that must not disturb the current
checkout.

### A commit-message guard hook

**Problem.** The commit style (`type(scope): imperative summary`, with a short subject) is
checked by nobody until review.

**Fix.** A `PreToolUse` hook that validates the message of a `git commit` the model is about
to run against the style, denying with the rule that failed. Same shape and fail-open
posture as `git-guard`.

### `git-policy-init`: one command to adopt the policy

**Problem.** Adopting the policy in a fresh repo is a chain of steps run by hand: audit,
stamp the CI files, create `develop`, configure branch protection. The stamp transform
deliberately never branches or commits, so the chain has no driver.

**Fix.** A command that orchestrates audit → stamp → `develop` creation → branch-protection
setup, stopping for review at each irreversible step.

### Extend the `git-guard` deny-set

**Problem.** The guard denies `reset --hard`, forced `clean`, forced branch deletion, and
`checkout` or `restore` discards, and allows everything else by design. Irreversible
operations still outside it: expiring the reflog, forced worktree removal, and `stash drop`
or `stash clear`.

**Fix.** Add them to the classifier with the same fail-open, allow-when-ambiguous posture,
each with a test that shows the plain form still passes.

## Maintenance

### Dependabot for the Python toolchain

**Problem.** Dependabot tracks only the GitHub Actions pins; the `pytest` and `ruff` pins in
`requirements-dev.txt` are bumped by hand, so a new series is noticed only when someone
looks.

**Fix.** Add a `pip` ecosystem to `.github/dependabot.yml` targeting `develop`, the same way
the Actions ecosystem does.

### Promote the release gate to a required check

**Problem.** The `release-gate` workflow (the CHANGELOG section on pull requests into
`main`; the manifest against the nearest reachable tag on push) has not yet shipped to
`main`, so its job has never reported there, and marking it required waits on a first real
run.

**Fix.** After the next release lands on `main`, verify the gate's first run passed and add
its job to the required checks.

### Decouple the environment validator from the ramp plugin

**Problem.** `validate-env.py` runs on every `SessionStart` and warns when `RAMP_ROOT` is
unset, a variable that belongs to the sibling `ramp` plugin, so a `tools`-only install sees
a spurious warning every session. `pin` and `wrap` likewise invoke `/ramp:pin` and
`/ramp:wrap` unconditionally and skip silently when ramp is absent. The README roadmap
wants tighter integration, a single knowledge-and-session harvest at wrap time, which
needs a reliable presence check rather than an unconditional call.

**Fix.** Drop the `RAMP_ROOT` check from this plugin's validator, detect once whether ramp
is installed and branch on that in `pin` and `wrap`, and design the single harvest on top
of that detection.

### Make the `sit-rep` skill's data sources configurable

**Problem.** The skill ships one maintainer's layout as its working example: fixed probe
paths for an events database and a per-tool findings directory, a commit-message grep for
one ticket prefix, cross-references to memory notes that do not ship with the plugin, and
an output template whose worked examples are another project's history. On any other
repository those sections come back empty, and the template reads as someone else's status
report.

**Fix.** Read the probe paths and the ticket pattern from a small configuration block with
documented defaults, replace the template's examples with neutral placeholders, and drop
the memory cross-references.

### Document the TaskWarrior setup the task commands require

**Problem.** The task commands assume a TaskWarrior configured with `size` and `source`
user-defined attributes. When they are missing, `consolidate-tasks` stops and points at a
design spec that is not in this repository, and no public page explains the setup.

**Fix.** A short setup page with the `.taskrc` lines and what each attribute is for, linked
from the README and from the command's own error message.

### A local pre-commit layer mirroring the CI gate

**Problem.** The only blocking gate is CI on pull requests and on pushes that touch code:
`ruff`, `pytest`, and `check-docs`; the plugin's own lint hook is advisory and fires only on
files the model edits. A contributor learns about a lint or docs failure after pushing.

**Fix.** A `.pre-commit-config.yaml` running the same checks locally, with the pins read
from `requirements-dev.txt` so the two never drift. Optional and additive; CI stays the gate
of record.
