#!/usr/bin/env python3
"""add-tasks.py — execute an approved consolidate-tasks manifest against TaskWarrior."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TOMBSTONE_TEMPLATE = "Tasks tracked in TaskWarrior — run `task project:{slug} list`\n"

_SOURCE_MAP = {"markdown": "backlog", "code": "code", "github": "github"}


def task_add(item: dict) -> tuple[bool, str]:
    """Run `task add` for one item. Returns (success, task_id_or_error_message)."""
    cmd = [
        "task", "add",
        item["description"],
        f"project:{item['inferred_slug']}",
        f"+{item['inferred_tag']}",
        f"size:{item['inferred_size']}",
        f"source:{_SOURCE_MAP.get(item['source_type'], item['source_type'])}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return False, result.stderr.strip()
    m = re.search(r"Created task (\d+)", result.stdout)
    return True, m.group(1) if m else "?"


def task_annotate(task_id: str, note: str) -> None:
    """Annotate a task; silently ignore failures (annotation is best-effort)."""
    subprocess.run(
        ["task", "annotate", task_id, note],
        capture_output=True,
    )


def tombstone_file(file_path: Path, slug: str) -> None:
    file_path.write_text(TOMBSTONE_TEMPLATE.format(slug=slug))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to approved manifest JSON")
    args = parser.parse_args()

    try:
        manifest = json.loads(Path(args.manifest).read_text())
    except FileNotFoundError:
        print(f"ERROR: manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: manifest is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    manifest_path = Path(args.manifest)
    created_ids: list[str] = []
    executed = 0
    skipped = 0
    flagged = 0
    errors: list[str] = []
    tombstoned: list[str] = []
    unchanged: list[str] = []

    for repo in manifest["repos"]:
        repo_path = Path(repo["path"])
        default_slug = repo["slug"]

        # Track per-file: which items had errors
        file_added: dict[str, bool] = {}   # source_file → all adds succeeded
        file_slug: dict[str, str] = {}     # source_file → slug (for tombstone line)
        file_has_unadded: set[str] = set() # source_file → has any skipped/flagged items

        for item in repo["items"]:
            status = item.get("status", "proposed")

            if status == "executed":
                executed += 1
                continue
            if status == "skip":
                skipped += 1
                src = item.get("source_file")
                if src:
                    file_has_unadded.add(src)
                continue
            if status == "flag":
                flagged += 1
                src = item.get("source_file")
                if src:
                    file_has_unadded.add(src)
                continue
            if status != "approved":
                continue

            ok, result = task_add(item)

            src = item.get("source_file")
            if not ok:
                errors.append(f"{item['description'][:60]}: {result}")
                if src:
                    file_added[src] = False
                continue

            task_id = result
            created_ids.append(task_id)
            item["status"] = "executed"  # mark for idempotency on re-run

            if src:
                if src not in file_added:
                    file_added[src] = True
                    file_slug[src] = item["inferred_slug"]
                # A failure on a later item from the same file marks it False
                # (handled above via file_added[src] = False on failure)

            # Annotate
            if item["source_type"] == "code" and item.get("line"):
                task_annotate(task_id, f"{src}:{item['line']}")
            elif item["source_type"] == "github" and item.get("github_url"):
                task_annotate(task_id, item["github_url"])

        # Tombstone files where all approved items succeeded
        for rel in repo.get("tombstone_candidates", []):
            abs_path = repo_path / rel
            if not abs_path.exists():
                unchanged.append(f"{rel} (file not found)")
                continue
            if rel in file_has_unadded:
                unchanged.append(f"{rel} (skipped/flagged items — not tombstoned)")
                continue
            if file_added.get(rel) is False:
                unchanged.append(f"{rel} (add errors — not tombstoned)")
                continue
            if file_added.get(rel) is None:
                unchanged.append(f"{rel} (no items added — not tombstoned)")
                continue
            slug = file_slug.get(rel, default_slug)
            tombstone_file(abs_path, slug)
            tombstoned.append(rel)

    # Persist executed status so re-runs skip already-added items
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # Report
    if executed:
        print(f"Already executed: {executed} (skipped — re-run idempotency)")
    print(f"Created:    {len(created_ids)} tasks"
          f" (IDs: {', '.join(created_ids) if created_ids else 'none'})")
    print(f"Skipped:    {skipped}")
    print(f"Flagged:    {flagged} (not added)")
    print(f"Errors:     {len(errors)}")
    if tombstoned:
        print(f"Tombstoned: {', '.join(tombstoned)}")
    if unchanged:
        print(f"Unchanged:  {', '.join(unchanged)}")
    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    main()
