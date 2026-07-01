#!/usr/bin/env python3
"""PreToolUse hook: deny local, irreversible git ops on Claude's Bash calls.

Guards Claude only — PreToolUse never fires on the user's ``!git`` commands, so
the user always keeps an unguarded path. Fail-open on any parse error: a rail
that crashed closed would block all of Claude's git on a single bug.

Deny set (see docs/superpowers/specs/2026-07-01-git-guard-hook-design.md):
  reset --hard · clean -f* · branch -D · checkout discard · restore discard
Everything else, including push (any form), is allowed.
"""
import json
import shlex
import sys

_SPLIT_OPS = ("&&", "||", ";", "|")


def _git_segments(command):
    """Return token lists for each ``git`` segment of a (possibly compound) command.

    Non-git segments and segments that fail shlex parsing are skipped (fail-open).
    """
    # Normalize shell separators to a single sentinel, then split.
    normalized = command
    for op in _SPLIT_OPS:
        normalized = normalized.replace(op, "\x00")
    segments = []
    for raw in normalized.split("\x00"):
        raw = raw.strip()
        if not raw:
            continue
        try:
            tokens = shlex.split(raw)
        except ValueError:
            continue  # unbalanced quotes -> fail-open
        if tokens and tokens[0] == "git":
            segments.append(tokens)
    return segments


def _subcommand_and_args(tokens):
    """Strip 'git' and any global options (incl. ``-C <path>``); return (subcmd, args)."""
    i = 1  # skip 'git'
    while i < len(tokens):
        tok = tokens[i]
        if tok == "-C" or tok == "--git-dir" or tok == "--work-tree":
            i += 2  # option takes a value
            continue
        if tok.startswith("-"):
            i += 1  # other global option, no value we care about
            continue
        break
    if i >= len(tokens):
        return None, []
    return tokens[i], tokens[i + 1:]


def _classify_tokens(tokens):
    sub, args = _subcommand_and_args(tokens)
    if sub is None:
        return None

    if sub == "reset":
        if "--hard" in args:
            return ("reset-hard", "git reset --hard wipes uncommitted local work irreversibly.")
        return None

    if sub == "clean":
        for a in args:
            if a == "--force":
                return ("clean-force", "git clean --force deletes untracked files irreversibly.")
            if a.startswith("-") and not a.startswith("--") and "f" in a:
                return ("clean-force", "git clean -f deletes untracked files irreversibly.")
        return None

    if sub == "branch":
        if "-D" in args:
            return ("branch-delete-force", "git branch -D drops an unmerged branch tip.")
        has_delete = "-d" in args or "--delete" in args
        has_force = "-f" in args or "--force" in args
        if has_delete and has_force:
            return ("branch-delete-force", "git branch --delete --force drops an unmerged branch tip.")
        return None

    if sub == "checkout":
        # Deny only on explicit discard signals. A bare operand is ambiguous
        # (branch name vs pathspec) — and branch names commonly contain '/'
        # (feature/x) — so per the spec we allow-when-ambiguous and never infer
        # a discard from a slash. The discard forms carry -f/--force, '--', or '.'.
        if "-f" in args or "--force" in args or "--" in args or "." in args:
            return ("checkout-discard", "git checkout discards uncommitted changes to tracked files irreversibly.")
        return None

    if sub == "restore":
        for a in args:
            if a.startswith("-"):
                continue
            # any non-option operand is a pathspec for restore
            return ("restore-discard", "git restore discards uncommitted changes to tracked files irreversibly.")
        if "." in args:
            return ("restore-discard", "git restore . discards uncommitted changes to tracked files irreversibly.")
        return None

    return None


def classify(command):
    """Pure verdict. Never raises — returns allow on any surprise (fail-open)."""
    try:
        for tokens in _git_segments(command or ""):
            hit = _classify_tokens(tokens)
            if hit:
                rule, reason = hit
                return {"action": "deny", "rule": rule, "reason": reason}
    except Exception:
        return {"action": "allow"}
    return {"action": "allow"}


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)  # malformed stdin -> fail-open

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command", "")
    verdict = classify(command)
    if verdict["action"] != "deny":
        sys.exit(0)

    reason = f"{verdict['reason']} Run it via !git if you mean it."
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
