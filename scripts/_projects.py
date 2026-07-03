#!/usr/bin/env python3
"""L2 project enumeration: typed Project objects over _scope + the scope idioms as pure helpers.

Sits on _scope (no cycle). Pure/injectable so it is pytest-coverable. Absorbs the
enumeration/scope idioms copy-pasted across the command surface; the all-projects
walk itself lives in _scope.all_projects (get_scope's global branch delegates to it),
which this module wraps into typed objects.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _scope import _reconstruct, all_projects, get_scope, project_key  # noqa: E402


@dataclass
class Project:
    key: str             # ~/.claude/projects dir name
    path: Path           # filesystem path (cwd side)
    name: str            # path.name
    container: str | None  # containing project's name via PATH-PREFIX containment; None if top-level
    proj_dir: Path       # ~/.claude/projects/<key>


def _default_projects_dir(projects_dir):
    return Path(projects_dir) if projects_dir is not None else (Path.home() / '.claude' / 'projects')


def enumerate_projects(scope=None, projects_dir=None):
    """In-scope projects as typed Project objects.

    scope defaults to get_scope(); single -> [the one], parent/global -> the list.
    Thin typed wrapper over get_scope — does NOT re-walk. container is the name of
    the nearest ENUMERATED project whose path strictly prefixes this one (so a
    non-project intermediate dir never becomes a parent).
    """
    mode, data, cwd = scope if scope is not None else get_scope()
    pd = _default_projects_dir(projects_dir)
    if mode == 'single':
        pairs = [(data, cwd)]
    else:  # parent or global — both carry list[(key, path)]
        pairs = list(data or [])

    all_paths = {str(p) for _, p in pairs}
    projects = []
    for key, path in pairs:
        parent = max(
            (ps for ps in all_paths if str(path).startswith(ps + '/') and ps != str(path)),
            key=len,
            default=None,
        )
        container = Path(parent).name if parent else None
        projects.append(Project(key=key, path=path, name=path.name,
                                 container=container, proj_dir=pd / key))
    return projects


def global_scope():
    """A forced-global scope tuple: every project on the machine, regardless of cwd.

    For cross-project lenses (atlas) that must NOT inherit the caller's ambient scope —
    get_scope() from inside a project returns 'single', which would hide every other
    project from the lens.
    """
    return ('global', all_projects(), Path.cwd())


def projects_under(root, projects=None):
    """Projects at-or-under root — a plain directory, registered or not.

    The anchored lens behind atlas --dir: no snapping to an enclosing registered
    project; the caller names the anchor.
    """
    root = Path(root)
    if projects is None:
        projects = enumerate_projects(scope=global_scope())
    return [p for p in projects if p.path == root or root in p.path.parents]


def subtree_projects(cwd=None):
    """Projects at-or-under the innermost registered project containing cwd.

    The default atlas lens: the current project plus anything nested inside it.
    Falls back to ALL projects when cwd is outside every registered project
    (nothing to anchor the subtree to).
    """
    here = Path(cwd) if cwd is not None else Path.cwd()
    projects = enumerate_projects(scope=global_scope())
    anchors = [p.path for p in projects if p.path == here or p.path in here.parents]
    if not anchors:
        return projects
    root = max(anchors, key=lambda a: len(str(a)))
    return projects_under(root, projects)


def scoped_keys(scope=None):
    """The _allowed filter: {key} | {child keys} | None(=all/global-unfiltered)."""
    mode, data, _ = scope if scope is not None else get_scope()
    if mode == 'single':
        return {data}
    if mode == 'parent':
        return {k for k, _ in data}
    return None  # global -> unfiltered (preserves the None-means-all idiom)


def current_key(scope=None, git_root=None, projects_dir=None):
    """Collapse scope to one project key. Caller injects git_root (owns the git call)."""
    mode, data, _ = scope if scope is not None else get_scope()
    if mode == 'single':
        return data
    if git_root is None:
        return None
    return project_key(git_root, _default_projects_dir(projects_dir))


def group(projects):
    """container -> [Project]; top-level projects group under the None key."""
    out = {}
    for p in projects:
        out.setdefault(p.container, []).append(p)
    return out


def stale_keys(projects_dir=None, active_keys=None):
    """(orphaned, unscoped) as (key, reason) tuples. Always global; relative to active_keys.

    Lifts collect-status.py:152-169: 'no dir on disk' / 'duplicate (no leading dash)'
    / 'home dir — unscoped sessions'.
    """
    pd = _default_projects_dir(projects_dir)
    active = set(active_keys or set())
    all_keys = [p.name for p in sorted(pd.iterdir()) if p.is_dir()]
    with_dash = {k for k in all_keys if k.startswith('-')}
    orphaned, unscoped = [], []
    for key in all_keys:
        if key in active:
            continue
        if not key.startswith('-') and ('-' + key) in with_dash:
            orphaned.append((key, 'duplicate (no leading dash)'))
            continue
        candidates = list(_reconstruct(key, None))
        if not candidates:
            orphaned.append((key, 'no dir on disk'))
            continue
        if candidates[0] == Path.home():
            unscoped.append((key, 'home dir — unscoped sessions'))
    return orphaned, unscoped
