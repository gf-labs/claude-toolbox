# BACKLOG

Items to be populated from Phase 10 of the architecture plan (`docs/claude-toolbox-architecture.md`).

## Commands

- **`done` command** — built in Phase 1 session 2. Marks current session for deletion by appending a `custom-title` record with "delete-me" suffix. Picked up by `/cleanup delete-me`. Note: cleanup.md was also patched to read the *last* `custom-title` entry (not first) so renamed sessions are matched correctly.
