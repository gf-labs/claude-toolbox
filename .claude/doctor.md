## Toolbox-specific context

**Script shebangs**:
```bash
for f in scripts/*.py; do echo "=== $f ==="; head -1 "$f"; done 2>/dev/null || echo "none"
```

**BACKLOG.md** (first 10 lines):
```bash
head -10 BACKLOG.md 2>/dev/null || echo "not found"
```

---

## Toolbox-specific checks

Run these checks. Prefix findings T1, T3. Same severity model ([CRITICAL] / [WARN] / [INFO] / [PASSED]).

### T1 — Script shebangs

Interpret the script shebangs output above. Verify the first line of each `.py` file in `scripts/` is `#!/usr/bin/env python3`.
- `[WARN]` for any script missing the shebang
- `[PASSED]` if all scripts have correct shebangs

### T3 — BACKLOG.md not a placeholder

Read the BACKLOG.md output above.
- `[WARN]` if the file is not found
- `[WARN]` if `## In Progress` and `## Up Next` both contain only `(nothing)` or are empty — stale placeholder
- `[PASSED]` otherwise
