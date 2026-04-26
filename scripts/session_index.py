from __future__ import annotations

import json
import os
from pathlib import Path

DATA_ROOT = Path.home() / '.claude' / 'data' / 'tools'


def _registry_path(project_key: str) -> Path:
    return DATA_ROOT / project_key / 'sessions-meta.json'


def read_registry(project_key: str) -> dict:
    path = _registry_path(project_key)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def write_registry(project_key: str, data: dict) -> None:
    path = _registry_path(project_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)


def get_status(project_key: str, uuid: str) -> str | None:
    return read_registry(project_key).get(uuid, {}).get('status')


def set_status(project_key: str, uuid: str, status: str, **kwargs) -> None:
    registry = read_registry(project_key)
    entry = registry.get(uuid, {})
    entry['status'] = status
    entry.update(kwargs)
    registry[uuid] = entry
    write_registry(project_key, registry)
