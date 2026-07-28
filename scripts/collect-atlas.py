#!/usr/bin/env python3
"""Atlas dispatcher: parse $ARGUMENTS, resolve scope, run facet collectors, emit sections.

Dispatch-only — never re-derives enumeration/grouping the collectors and _projects
already do. All I/O is under __main__ so the pure functions are importable for tests.
"""
import datetime
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _atlas_render  # noqa: E402
from _projects import (  # noqa: E402
    enumerate_projects,
    global_scope,
    projects_under,
    stale_keys,
    subtree_projects,
)

SCRIPTS = Path(__file__).parent
FACETS = ('projects', 'sessions', 'memory', 'plans', 'specs', 'plugins', 'claude.md')  # closed vocabulary

# facet -> backing collector script
COLLECTOR = {
    'projects': 'collect-status.py',
    'sessions': 'collect-session-list.py',  # NOT collect-sessions.py (cleanup inventory)
    'memory': 'collect-status.py',       # a projection of the same rows
    'plans': 'collect-plans.py',
    'specs': 'collect-superpowers-docs.py',
    'plugins': 'collect-plugin-drift.py',
    'claude.md': 'collect-claude-md-map.py',
}

# Scope-aware collectors that would otherwise inherit the ambient cwd scope;
# atlas is the cross-project lens, so it forces them global.
FORCE_GLOBAL = ('collect-status.py', 'collect-claude-md-map.py', 'collect-session-list.py',
                'collect-superpowers-docs.py')

# Machine-level facets: their lines don't name projects, so scope-narrowing by
# project name would gut them — always rendered whole.
GLOBAL_FACETS = ('plugins',)


def parse_args(argv):
    """argv (no program name) -> request dict. Pure; unknown tokens accumulate in errors."""
    facets, errors = [], []
    project = None
    depth = 'auto'
    stale = False
    all_scope = False
    dir_arg = None
    dry_run = False
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == '--project':
            i += 1
            if i < len(argv):
                project = argv[i]
            else:
                errors.append('--project requires a NAME')
        elif tok == '--full':
            depth = 'full'
        elif tok == '--compact':
            depth = 'compact'
        elif tok == '--stale':
            stale = True
        elif tok == '--all':
            all_scope = True
        elif tok == '--dir':
            i += 1
            if i < len(argv):
                dir_arg = argv[i]
            else:
                errors.append('--dir requires a NAME or PATH')
        elif tok == '--dry-run':
            dry_run = True
        elif tok.startswith('--'):
            errors.append(f'unknown flag: {tok}')
        elif tok in FACETS:
            if tok not in facets:
                facets.append(tok)
        else:
            errors.append(f'unknown facet: {tok} (valid: {", ".join(FACETS)})')
        i += 1
    if not facets and not stale:
        facets = [f for f in FACETS if f not in GLOBAL_FACETS]  # default = full project picture
    return {'facets': facets, 'project': project, 'depth': depth, 'stale': stale,
            'all': all_scope, 'dir': dir_arg, 'dry_run': dry_run, 'errors': errors}


def render_request(request):
    lines = ['=== REQUEST ===',
             f'FACETS: {",".join(request["facets"]) or "(none)"}',
             f'PROJECT: {request["project"] or "(all)"}',
             f'DIR: {request["dir"] or "(none)"}',
             f'DEPTH: {request["depth"]}',
             # The nesting IS the flag-precedence rule: --project > --dir > --all > subtree.
             f'SCOPE: {"project" if request["project"] else ("dir" if request["dir"] else ("all" if request["all"] else "subtree"))}',
             f'STALE: {"yes" if request["stale"] else "no"}']
    if request['errors']:
        lines.append('ERRORS: ' + '; '.join(request['errors']))
    return '\n'.join(lines)


def _run(script):
    cmd = [sys.executable, str(SCRIPTS / script)]
    if script in FORCE_GLOBAL:
        cmd.append('--all')
    try:
        return subprocess.run(cmd, capture_output=True, text=True).stdout
    except OSError as e:
        return f'(collector {script} failed: {e})'


def resolve_project(name):
    """name -> (key, display) via exact Project.name match ('container/name' also accepted)."""
    projects = enumerate_projects(scope=global_scope())
    if '/' in name:
        cont, base = name.split('/', 1)
        matches = [p for p in projects if p.name == base and (p.container or '') == cont]
    else:
        matches = [p for p in projects if p.name == name]
    if not matches:
        known = ', '.join(sorted({p.name for p in projects})) or '(none)'
        return None, f'no project named "{name}". Known: {known}'
    if len(matches) > 1:
        quals = ', '.join(f'{m.container or "?"}/{m.name}' for m in matches)
        return None, f'"{name}" is ambiguous ({len(matches)}: {quals}) — qualify as --project <container>/<name>'
    return matches[0].key, matches[0].name


def resolve_dir(value, projects):
    """--dir value -> (anchor Path, error). A filesystem path (absolute/~/relative)
    when one exists, else a unique component-name match over the registered
    project paths and their ancestors."""
    p = Path(value).expanduser()
    cand = p if p.is_absolute() else Path.cwd() / p
    if cand.is_dir():
        return cand.resolve(), None
    hits = {anc for pr in projects for anc in (pr.path, *pr.path.parents) if anc.name == value}
    if len(hits) == 1:
        return hits.pop(), None
    if hits:
        opts = ', '.join(sorted(str(h) for h in hits))
        return None, f'--dir "{value}" is ambiguous ({len(hits)}: {opts}) — pass a path'
    return None, f'--dir "{value}": no such directory or project-path component'


def _keep_line(ln, names):
    """Keep header/marker lines and any row naming an in-scope project (Plan 1 substring filter)."""
    s = ln.strip()
    if not s:
        return True
    if s[0] in '#=' or ln.startswith(('GROUP', 'PROJECT', 'CONTAINER', 'KEY', 'SINGLE', 'LAST_SNAPSHOT')):
        return True
    return any(n in ln for n in names)


def emit(request):
    out = [render_request(request)]

    proj_key = proj_name = None
    if request['project']:
        proj_key, proj_name = resolve_project(request['project'])
        if proj_key is None:
            out.append('=== ERROR ===')
            out.append(proj_name)  # holds the reason
            # ERROR is terminal by design (fail-fast on a malformed request).
            return '\n'.join(out)

    # Scope resolution -> the in-scope Project list. The nesting IS the
    # flag-precedence rule: --project > --dir > --all > subtree. Collectors always
    # run global (--all); narrowing happens here, on the resolved list.
    projects_all = enumerate_projects(scope=global_scope())
    if proj_key is not None:
        scope_projects = [p for p in projects_all if p.key == proj_key]
    elif request['dir']:
        anchor, err = resolve_dir(request['dir'], projects_all)
        scope_projects = []
        if err is None:
            scope_projects = projects_under(anchor, projects_all)
            if not scope_projects:
                err = f'--dir "{request["dir"]}": no registered projects under {anchor}'
        if err:
            out.append('=== ERROR ===')
            out.append(err)
            # Same fail-fast contract as an unresolvable --project.
            return '\n'.join(out)
    elif request['all']:
        scope_projects = projects_all
    else:
        scope_projects = subtree_projects()

    keep_names = ({p.name for p in scope_projects}
                  if {p.key for p in scope_projects} != {p.key for p in projects_all}
                  else None)

    status_cache = {}
    def status_out():
        if 'v' not in status_cache:
            status_cache['v'] = _run('collect-status.py')
        return status_cache['v']

    project_facets = [f for f in request['facets'] if f not in GLOBAL_FACETS]
    global_facets = [f for f in request['facets'] if f in GLOBAL_FACETS]

    if len(project_facets) >= 2:
        # Merged mode: parse the collectors' rows and render one ATLAS section.
        parsed = {}
        if 'projects' in project_facets or 'memory' in project_facets:
            parsed['status'] = _atlas_render.parse_status(status_out())
        if 'sessions' in project_facets:
            parsed['sessions'] = _atlas_render.parse_sessions(_run(COLLECTOR['sessions']))
        if 'plans' in project_facets:
            parsed['plans'] = _atlas_render.parse_plans(_run(COLLECTOR['plans']))
        if 'specs' in project_facets:
            parsed['specs'] = _atlas_render.parse_specs(_run(COLLECTOR['specs']))
        if 'claude.md' in project_facets:
            parsed['claude_md'] = _atlas_render.parse_claude_md(_run(COLLECTOR['claude.md']))
        scope_label = ('project' if request['project']
                       else ('dir' if request['dir'] else ('all' if request['all'] else 'subtree')))
        out.append('=== ATLAS ===')
        out.append(_atlas_render.build_atlas(scope_projects, project_facets, parsed,
                                             request['depth'], datetime.date.today(),
                                             scope_label))
    else:
        # Single-facet mode: the v1 flat section, byte-identical.
        for facet in project_facets:
            out.append(f'=== {facet.upper()} ===')
            text = status_out() if facet in ('projects', 'memory') else _run(COLLECTOR[facet])
            if keep_names:
                text = '\n'.join(ln for ln in text.splitlines() if _keep_line(ln, keep_names))
            out.append(text.rstrip('\n') or '(no data)')

    for facet in global_facets:
        out.append(f'=== {facet.upper()} ===')
        out.append(_run(COLLECTOR[facet]).rstrip('\n') or '(no data)')

    if request['stale']:
        out.append('=== STALE ===')
        # STALE is machine-level hygiene — always global, never subtree-narrowed.
        orphaned, unscoped = stale_keys(active_keys={p.key for p in projects_all})
        if not orphaned and not unscoped:
            out.append('(none)')
        else:
            for k, note in orphaned:
                out.append(f'ORPHANED\t{k}\t{note}')
            for k, note in unscoped:
                out.append(f'UNSCOPED\t{k}\t{note}')

    return '\n'.join(out)


def main(argv):
    request = parse_args(argv)
    if request['dry_run']:
        print(render_request(request))
        return
    print(emit(request))


if __name__ == '__main__':
    main(sys.argv[1:])
