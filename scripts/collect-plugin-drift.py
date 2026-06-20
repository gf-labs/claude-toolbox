#!/usr/bin/env python3
"""Plugin cache drift — cached commands vs. source repo."""
import json
from pathlib import Path

settings_path = Path.home() / '.claude' / 'settings.json'
cache_base = Path.home() / '.claude' / 'plugins' / 'cache'

try:
    settings = json.loads(settings_path.read_text(encoding='utf-8'))
except (OSError, ValueError):
    print('SETTINGS_UNREADABLE')
    raise SystemExit(1)

marketplaces = settings.get('extraKnownMarketplaces', {})
enabled = settings.get('enabledPlugins', {})

if not enabled:
    print('NO_PLUGINS_ENABLED (hint: --plugin-dir sessions clear enabledPlugins)')
    raise SystemExit(0)

for plugin_at_market in [k for k, v in enabled.items() if v]:
    parts = plugin_at_market.split('@', 1)
    if len(parts) != 2:
        continue
    plugin_name, market_name = parts
    market_entry = marketplaces.get(market_name)
    if not market_entry:
        print(f'{plugin_at_market}: marketplace source path unknown')
        continue
    source_dir = market_entry.get('source', {}).get('path') if isinstance(market_entry, dict) else None
    if not source_dir:
        print(f'{plugin_at_market}: marketplace source path not resolvable')
        continue
    # Resolve per-plugin source directory from marketplace plugins list
    plugin_source_dir = Path(source_dir)  # default: marketplace root (covers source "./")
    marketplace_json = Path(source_dir) / '.claude-plugin' / 'marketplace.json'
    if marketplace_json.exists():
        try:
            mdata = json.loads(marketplace_json.read_text(encoding='utf-8'))
            for p in mdata.get('plugins', []):
                if p.get('name') == plugin_name:
                    rel = p.get('source', './')
                    plugin_source_dir = (Path(source_dir) / rel).resolve()
                    break
        except Exception:
            pass  # fall back to marketplace root
    source_commands = set(
        f.stem for f in (plugin_source_dir / 'commands').glob('*.md')
    ) if (plugin_source_dir / 'commands').exists() else set()
    cache_plugin = cache_base / market_name / plugin_name
    cached_versions = sorted(cache_plugin.iterdir()) if cache_plugin.exists() else []
    if not cached_versions:
        print(f'{plugin_at_market}: NO CACHE FOUND')
        continue
    latest = cached_versions[-1]
    cached_commands = set(
        f.stem for f in (latest / 'commands').glob('*.md')
    ) if (latest / 'commands').exists() else set()
    stale = cached_commands - source_commands
    missing = source_commands - cached_commands
    if stale or missing:
        print(f'{plugin_at_market} (cache: {latest.name}):')
        for c in sorted(stale):
            print(f'  STALE  {c} — in cache but not in source')
        for c in sorted(missing):
            print(f'  MISSING {c} — in source but not in cache')
        print(f'  Fix: /plugin marketplace add {plugin_source_dir} then /plugin install {plugin_at_market}')
    else:
        print(f'{plugin_at_market}: cache in sync ({len(cached_commands)} commands)')
