#!/usr/bin/env python3
"""PostModelInvocation hook — append per-invocation cost estimate to ~/.claude/metrics/costs.jsonl."""
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

RATES = {  # per 1M tokens, USD
    'claude-sonnet-4-6': {'input': 3.00, 'output': 15.00},
    'claude-haiku-4-5': {'input': 0.80, 'output': 4.00},
    'claude-opus-4-6': {'input': 15.00, 'output': 75.00},
}
DEFAULT_RATE = {'input': 3.00, 'output': 15.00}

try:
    event = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)

usage = event.get('usage', {})
inp = usage.get('input_tokens', 0)
out = usage.get('output_tokens', 0)
model = event.get('model', '')
session_id = event.get('session_id', '')

rate = RATES.get(model, DEFAULT_RATE)
cost = (inp * rate['input'] + out * rate['output']) / 1_000_000

out_dir = Path.home() / '.claude' / 'metrics'
out_dir.mkdir(parents=True, exist_ok=True)
row = json.dumps({
    'ts': datetime.now(UTC).isoformat(),
    'session_id': session_id,
    'model': model,
    'input_tokens': inp,
    'output_tokens': out,
    'cost_usd': round(cost, 6),
})
try:
    (out_dir / 'costs.jsonl').open('a').write(row + '\n')
except Exception as e:
    print(f'warning: cost-tracker could not write: {e}', file=sys.stderr)
