import re
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "collect-inventory.py"
PATTERN = re.compile(r"Commands: \d+ · Agents: \d+ · Hooks: \d+ · Scripts: \d+")


def test_output_format():
    result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, f"Script exited {result.returncode}: {result.stderr}"
    assert PATTERN.fullmatch(result.stdout.strip()), (
        f"Unexpected format: {result.stdout.strip()!r}\n"
        f"Expected: 'Commands: N · Agents: N · Hooks: N · Scripts: N'"
    )


def test_counts_nonzero():
    result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    line = result.stdout.strip()
    counts = [int(n) for n in re.findall(r": (\d+)", line)]
    assert len(counts) == 4, f"Expected 4 counts, got {len(counts)} in: {line!r}"
    assert all(n > 0 for n in counts), f"Expected all counts > 0, got: {line!r}"
