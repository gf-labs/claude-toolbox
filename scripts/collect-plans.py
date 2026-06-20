#!/usr/bin/env python3
"""Plans inventory with project association (reads ## Plans section of .project-map)."""
from pathlib import Path

plans_dir = Path.home() / '.claude' / 'plans'

if not plans_dir.exists() or not list(plans_dir.glob('*.md')):
    print('NONE')
else:
    # Load project map from ## Plans section (read-only — no scanning)
    plan_map = {}
    cache = plans_dir / '.project-map'
    if cache.exists():
        in_plans = False
        current = None
        for line in cache.read_text(encoding='utf-8').splitlines():
            if line.strip() == '## Plans':
                in_plans = True
                continue
            if in_plans and line.startswith('## ') and line.strip() != '## Plans':
                break
            if not in_plans:
                continue
            if line.startswith('### '):
                current = line[4:].strip()
            elif current and line.startswith('- Created: '):
                created = line[11:].strip()
                # Extract project name from "date · sid (project-name)"
                if '(' in created and created.endswith(')'):
                    plan_map[current] = created[created.rfind('(') + 1:-1]

    for f in sorted(plans_dir.glob('*.md')):
        text = f.read_text(encoding='utf-8')
        file_lines = text.splitlines()
        line_count = len(file_lines)
        title = ''
        first_bullet = ''
        past_frontmatter = False
        for line in file_lines:
            if line.strip() == '---':
                past_frontmatter = not past_frontmatter
                continue
            if not title and line.startswith('# '):
                title = line[2:].strip()
            if title and not first_bullet and line.startswith('- '):
                first_bullet = line[2:].strip()[:80]
            if title and first_bullet:
                break
        project = plan_map.get(f.name, '?')
        print(f'{f.name}  {line_count}L  [{project}]  {title[:50]}')
        if first_bullet:
            print(f'  → {first_bullet}')
