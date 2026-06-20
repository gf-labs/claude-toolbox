#!/usr/bin/env bash
#
# collect-velocity.sh — velocity collector for the sit-rep skill
#
# Args:
#   $1 (optional) — topic filter. Space-separated words are treated as OR
#                   (e.g. "search index ranking"). Empty = full project.
#   $2 (optional) — window in days. Default: 14
#
# Output (to stdout):
#   - Total commit count over the window
#   - Topic-scoped commit count + percentage (if topic given)
#   - Cadence by day (commits per day)
#   - Top 10 hot files
#   - Total lines added/removed
#   - Topic-scoped lines (rough; via path keyword match)
#   - Top 3 peak commit days
#
# Exit codes:
#   0  — success
#   1  — not in a git repository
#   2  — invalid args

set -euo pipefail

TOPIC="${1:-}"
DAYS="${2:-14}"

if ! [[ "$DAYS" =~ ^[0-9]+$ ]]; then
  echo "ERROR: window-days must be an integer (got: $DAYS)" >&2
  exit 2
fi

SINCE="${DAYS} days ago"

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$ROOT" ]; then
  echo "ERROR: not in a git repository" >&2
  exit 1
fi
cd "$ROOT"

echo "=== Window: last $DAYS days (since $(git log --since="$SINCE" --reverse --pretty=format:'%ad' --date=short 2>/dev/null | head -1 || echo 'n/a')) ==="
echo ""

# --- Total commit count ---
TOTAL=$(git log --since="$SINCE" --oneline 2>/dev/null | wc -l | tr -d ' ')
echo "TOTAL_COMMITS: $TOTAL"

# --- Topic-scoped commit count ---
if [ -n "$TOPIC" ]; then
  # Build a regex alternation: "search index ranking" → "search\|index\|ranking"
  PATTERN=$(printf '%s\n' $TOPIC | paste -sd'|' - | sed 's/|/\\|/g')
  SCOPED=$(git log --since="$SINCE" --oneline --grep="$PATTERN" --regexp-ignore-case 2>/dev/null | wc -l | tr -d ' ')
  if [ "$TOTAL" -gt 0 ]; then
    PCT=$(awk -v s="$SCOPED" -v t="$TOTAL" 'BEGIN { printf "%.0f", (s/t)*100 }')
  else
    PCT=0
  fi
  echo "SCOPED_COMMITS [$TOPIC]: $SCOPED / $TOTAL (${PCT}%)"
fi
echo ""

# --- Cadence by day ---
echo "=== Cadence (commits per day) ==="
git log --since="$SINCE" --pretty=format:"%ad" --date=short 2>/dev/null \
  | sort \
  | uniq -c \
  | sort -k2
echo ""

# --- Top 10 hot files (total scope) ---
echo "=== Top 10 hot files (total scope) ==="
git log --since="$SINCE" --name-only --pretty=format: 2>/dev/null \
  | grep -v '^$' \
  | sort \
  | uniq -c \
  | sort -rn \
  | head -10
echo ""

# --- Total lines added/removed ---
echo "=== Lines added/removed (total scope) ==="
git log --since="$SINCE" --shortstat --pretty=format: 2>/dev/null \
  | grep -E "files? changed" \
  | awk '{ adds += $4; dels += $6; n += 1 } END { print "+" adds " -" dels " (across " n " commits with file changes)" }'
echo ""

# --- Topic-scoped lines (rough; via path keyword match) ---
if [ -n "$TOPIC" ]; then
  echo "=== Lines added/removed (topic-scoped, by path keyword match) ==="
  for word in $TOPIC; do
    # Glob-match paths containing the word
    SUMMARY=$(git log --since="$SINCE" --shortstat --pretty=format: -- "*${word}*" 2>/dev/null \
      | grep -E "files? changed" \
      | awk -v w="$word" '{ adds += $4; dels += $6; n += 1 } END {
          if (n > 0) {
            print "[" w "] +" adds " -" dels " (across " n " commits with file changes)"
          } else {
            print "[" w "] (no commits touched paths matching *" w "*)"
          }
        }')
    echo "$SUMMARY"
  done
  echo ""
fi

# --- Top 3 peak days ---
echo "=== Peak commit days (top 3) ==="
git log --since="$SINCE" --pretty=format:"%ad" --date=short 2>/dev/null \
  | sort \
  | uniq -c \
  | sort -rn \
  | head -3
echo ""

# --- Ticket references (durable identifiers for cost/quality experiments) ---
# Section 2 milestones should cite TICKET-NNN rather than paraphrase.
TICKET_REFS=$(git log --since="$SINCE" --pretty=format:"%cs %s" 2>/dev/null \
  | grep -E 'TICKET-[0-9]+' || true)
if [ -n "$TICKET_REFS" ]; then
  echo "=== Ticket references in window ==="
  echo "$TICKET_REFS" | head -25
  echo ""
  echo "Unique tickets:"
  echo "$TICKET_REFS" | grep -oE 'TICKET-[0-9]+' | sort -u
fi
