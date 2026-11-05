"""Schema-backed, single-undertaking cycles. Historical promptbook readers are unchanged."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import posixpath
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import uuid

from bionic_config import load_config, load_workflow_policy, require_schema_version

PHASES = {
    'dev': ['plan', 'build', 'test', 'review', 'reflect'],
    'iterate': ['plan', 'build', 'test', 'review', 'reflect'],
    'refactor': ['plan', 'build', 'test', 'review', 'reflect'],
    'simplify': ['plan', 'build', 'test', 'review', 'reflect'],
    'quick-fix': ['build', 'test', 'review', 'reflect'],
    'release': ['release'],
}
# pass_limit 1 for a release cycle only satisfies the schema's integer; no action opens a second pass.
LIMITS = {'dev': 7, 'iterate': 2, 'refactor': 7, 'simplify': 3, 'quick-fix': 1, 'release': 1}
# A release record without release_list predates the fixed lists; this table serves validation and display.
LEGACY_RELEASE = {'phases': ['plan', 'release', 'reflect'], 'limit': 2}
# Each task: (id, description, expected_evidence). Every task is in phase release and depends on its predecessor.
RELEASE_LISTS = {
    'beta': [
        ('prep', 'Prepare the release: bump the versions, promote the changelog, regenerate the public docs, and commit them',
         'the commit that carries the prepared release'),
        ('prepare', 'Bind this cycle to the beta target and check the prep', 'release.py prepare recorded in the ledger'),
        ('verify', 'Run release.py verify: freeze the artifact and run the release gates', 'release.py verify passed'),
        ('beta-and-smoke', "Publish the untagged beta under the owner's quoted authorization, then install it in isolation",
         'release.py beta published and release.py smoke passed'),
        ('tag', 'Tag the beta and create its release once verify and smoke passed on the authorized artifact', 'release.py tag recorded the tag'),
        ('record', 'Copy the ledger into this cycle and prepend its release op to the log', 'release.py record and the commit that holds the log op'),
    ],
    'official': [
        ('live-check-and-go-ahead', "Collect the owner's quoted go-ahead and any owed live-check result for the tagged artifact",
         "the owner's quote and release.py smoke --live-check when owed"),
        ('official', 'Publish and tag the official release with the same go-ahead', 'release.py official published'),
        ('record', 'Copy the ledger into this cycle, with the reason when the target did not publish, and prepend its release op to the log',
         'release.py record and the commit that holds the log op'),
    ],
}
# `create` seeds this Plan-phase task so the first `inspect` offers prepare-dispatch for the plan writer.
SEEDED_PLAN_TASK = {'id': 'plan', 'phase': 'plan', 'status': 'pending',
                    'description': 'Write the plan, and the IDR where the work needs one, and record them in this cycle',
                    'expected_evidence': ['the recorded plan, and the IDR when one is required']}
ID = re.compile(r'^(?:[A-Z][A-Z0-9]{1,9}-)?CYC-[0-9]{4,}$')
CLOSED = {'completed', 'abandoned'}
# Attempt states that hold a task on a version-3 record.
OPEN = ('reserved', 'running')
# The assignment fields a version-3 record adds; low-level entries carry them as null.
ASSIGNMENT_V3_FIELDS = ('host', 'base', 'delivery')


def v3_fields():
    """The top-level fields a version-3 record adds; create and upgrade start from these.

    `revision` starts at 0 because the first save increments it to 1."""
    return {'revision': 0, 'operations': [], 'results_dir': None}


class CycleError(ValueError):
    pass


def listed(doc):
    """A release cycle created under a fixed list."""
    return doc['type'] == 'release' and bool(doc.get('release_list'))


def legacy(doc):
    """A release record from before the fixed lists: historical, closable only."""
    return doc['type'] == 'release' and not doc.get('release_list')


# The phase after Build is 'test' on a record without phase_names and 'verify' on a record that carries it.
CHECK_PHASES = ('test', 'verify')


def own_phase(doc, value):
    """Map either name of the phase after Build to the record's own name; any other value is returned unchanged.

    A record whose sequence holds neither name (a release record) maps nothing."""
    own = [name for name in phases_of(doc) if name in CHECK_PHASES]
    return own[0] if own and value in CHECK_PHASES else value


def phase_title(doc):
    """The record's own title for the phase after Build, for engine messages."""
    return 'Test' if CHECK_PHASES[0] in phases_of(doc) else 'Verify'


def phases_of(doc):
    """The type's phase sequence in the record's own vocabulary; phase_names does not apply to a release record."""
    if legacy(doc):
        return LEGACY_RELEASE['phases']
    sequence = PHASES[doc['type']]
    if doc['type'] != 'release' and doc.get('phase_names') == 'verify':
        return [CHECK_PHASES[1] if name == CHECK_PHASES[0] else name for name in sequence]
    return sequence


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode()


def contained(root: Path, relative: str | Path) -> Path:
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise CycleError('path must be relative and contain no parent segments')
    target = root / path
    if not target.resolve().is_relative_to(root.resolve()):
        raise CycleError('path escapes its owning tree')
    # No symlink writes or retained subjects, including symlinks pointing inward.
    if any(parent.is_symlink() for parent in (target, *target.parents) if parent != root.parent):
        raise CycleError('symlink paths are refused')
    return target


def atomic(path: Path, value):
    atomic_bytes(path, encoded(value))


def atomic_bytes(path: Path, data: bytes):
    """Write through a temp file, fsync, then os.replace, so a reader sees a whole file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.cycle-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def tree(repo):
    cfg = load_config(repo, require_tree=True)
    require_schema_version(cfg.docs_root)
    return cfg


class LinkedWorktree(CycleError):
    """A mutating command ran in a linked worktree; `main` is the main checkout's project root."""
    def __init__(self, main):
        super().__init__(f'linked-worktree: cycle records are written only from the main checkout; rerun with --repo-root {main}')
        self.main = main


def main_checkout(repo):
    """The main checkout's project root when `repo` lies in a linked worktree; None otherwise.

    The main checkout is the parent of the common git directory; the project root keeps its
    offset below the worktree's top level. None outside git, or when git cannot answer."""
    repo = Path(repo).resolve()
    try:
        done = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--path-format=absolute', '--git-dir', '--git-common-dir', '--show-toplevel'],
                              capture_output=True, text=True)
    except OSError:
        return None
    lines = done.stdout.split('\n')
    if done.returncode or len(lines) < 3 or not all(lines[:3]):
        return None
    git_dir, common, top = (Path(line).resolve() for line in lines[:3])
    if git_dir == common or common.name != '.git':
        return None
    return common.parent / repo.relative_to(top)


def require_main_checkout(repo):
    """The shared guard every mutating command calls: refuse a linked worktree, naming the main checkout."""
    main = main_checkout(repo)
    if main is not None:
        raise LinkedWorktree(main)


@contextmanager
def locked(repo):
    require_main_checkout(repo)
    cfg = tree(repo)
    directory = contained(cfg.docs_root, 'cycles')
    directory.mkdir(exist_ok=True)
    lock = contained(directory, '.lock')
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield cfg, directory


def validate_arrangement(plan):
    """Only explicit literal, disjoint ownership can establish independent stream facts."""
    streams = plan.get('streams', [])
    if len({stream['id'] for stream in streams}) != len(streams):
        raise CycleError('stream ids must be unique')
    independent = []
    for stream in streams:
        paths = stream['paths']
        if len(paths) != len(set(paths)):
            raise CycleError('stream paths must be unique')
        for path in paths:
            if (path != path.strip() or any(char in path for char in '*?[]{}\\:')
                    or any(part in ('', '.', '..') for part in path.split('/'))):
                raise CycleError('stream paths must be literal repository-relative file or directory paths')
        if stream['independent']:
            for prior in independent:
                if any(a == b or a.startswith(b + '/') or b.startswith(a + '/') for a in paths for b in prior):
                    raise CycleError('independent stream paths must be disjoint')
            independent.append(paths)
    tasks = {task['id']: task for task in plan['tasks']}
    for task in tasks.values():
        units = task.get('integrates', [])
        if not units:
            continue
        if (task['phase'] != 'build' or len(units) != len(set(units))
                or any(unit not in tasks or unit == task['id'] or tasks[unit]['phase'] != 'build'
                       or unit not in task['depends_on'] for unit in units)):
            raise CycleError('integrates must name distinct existing Build tasks in this Build task\'s dependencies')


def validate(doc):
    from council_records import _validator
    validator = _validator()
    schema = validator.load_schema(Path(__file__).parent.parent / 'schemas/cycle.schema.json')
    errors = []
    validator.validate(doc, schema, '#', '#', errors, 'cycle')
    if errors:
        raise CycleError(f'invalid cycle: {errors[0]}')
    if doc['schema_version'] == 2 and not {'coverage', 'completion'}.issubset(doc):
        raise CycleError('version-two cycle requires coverage and completion fields')
    if len(doc['implementers']) != len(set(doc['implementers'])) or len(doc['required_checks']) != len(set(doc['required_checks'])):
        raise CycleError('implementers and required checks must be unique')
    if len(doc.get('build_checks', [])) != len(set(doc.get('build_checks', []))):
        raise CycleError('build checks must be unique')
    for classification in doc.get('classifications', []):
        for field in ('question_ids','context_question_ids'):
            ids = classification.get(field, [])
            if len(ids) != len(set(ids)):
                raise CycleError(f'classification {field} must be unique')
    if doc['phase'] not in phases_of(doc):
        raise CycleError('phase is incompatible with cycle type')
    if doc['pass'] > doc['pass_limit']:
        raise CycleError('pass exceeds approved limit')
    if any(scope.startswith(':') for scope in doc['plan']['scope']):
        raise CycleError('scope cannot use git pathspec magic')
    task_ids = [task['id'] for task in doc['plan']['tasks']]
    if len(task_ids) != len(set(task_ids)):
        raise CycleError('task ids must be unique')
    validate_arrangement(doc['plan'])
    assignment_ids = [entry['id'] for entry in doc.get('assignments', [])]
    if len(assignment_ids) != len(set(assignment_ids)):
        raise CycleError('assignment ids must be unique')
    for task in doc['plan']['tasks']:
        if task['phase'] not in phases_of(doc) or any(dep not in task_ids or dep == task['id'] for dep in task['depends_on']):
            raise CycleError('task phase or dependency is invalid')
    graph = {t['id']: t['depends_on'] for t in doc['plan']['tasks']}
    def visit(node, visiting):
        if node in visiting:
            raise CycleError('task dependencies contain a cycle')
        for dependency in graph[node]:
            visit(dependency, visiting | {node})
    for node in graph:
        visit(node, set())
    if listed(doc):
        fixed = RELEASE_LISTS[doc['release_list']]
        expected = [(tid, 'release', [fixed[i - 1][0]] if i else []) for i, (tid, _, _) in enumerate(fixed)]
        if [(t['id'], t['phase'], t['depends_on']) for t in doc['plan']['tasks']] != expected:
            raise CycleError(f"a {doc['release_list']} release cycle carries exactly its fixed task list, in order, each depending on its predecessor")
    return doc


def load(repo, identity):
    if not ID.fullmatch(identity):
        raise CycleError('invalid cycle identity')
    cfg = tree(repo)
    path = contained(cfg.docs_root, f'cycles/{identity}/cycle.json')
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CycleError(f'cannot load cycle {identity}: {type(exc).__name__}') from exc
    validate(doc)
    if doc['id'] != identity:
        raise CycleError('cycle identity differs from its directory')
    return doc


def revision_boundary(doc):
    """Index of the first history event that belongs to the version-3 record: after the last `upgraded` event, else 0."""
    marks = [i for i, e in enumerate(doc['history']) if e.get('action') == 'upgraded']
    return marks[-1] if marks else 0


def stamp_revision(doc):
    """Version 3: increment `revision` and stamp it on every version-3 event that has none yet.

    Events from before an upgrade stay revisionless; the `upgraded` event carries the revision its save produced."""
    if doc.get('schema_version') != 3:
        return
    doc['revision'] = doc.get('revision', 0) + 1
    for entry in doc['history'][revision_boundary(doc):]:
        entry.setdefault('revision', doc['revision'])


def save(cfg, doc):
    """Validate and write atomically. On a version-3 record every save increments `revision` first."""
    stamp_revision(doc)
    validate(doc)
    atomic(contained(cfg.docs_root, f"cycles/{doc['id']}/cycle.json"), doc)


def event(doc, action, **fields):
    doc['history'].append({'at': now(), 'action': action, 'pass': doc['pass'], 'phase': doc['phase'], 'status': doc['status'], **fields})
    doc['updated_at'] = now()


def create(repo, kind, title, goal, scope, acceptance, implementer, coordinator, origin=None, release_list=None, classification=None):
    """Create a cycle. `origin`, when given, is recorded as a `queue` key on the created event.

    `classification`, when given, is called with the new record and returns the work-sizing entry the
    creating save writes; the entry's revision is 1 because the creating save is the first.

    A release cycle requires `release_list` (beta or official) and carries that list's fixed tasks."""
    if kind not in PHASES or not all((title.strip(), goal.strip(), scope, acceptance, implementer.strip(), coordinator.strip())):
        raise CycleError('type, title, goal, scope, acceptance, implementer and coordinator are required')
    if kind == 'release' and release_list not in RELEASE_LISTS:
        raise CycleError('a release cycle requires --list beta or --list official')
    if kind != 'release' and release_list is not None:
        raise CycleError('--list belongs to release cycles')
    with locked(repo) as (cfg, directory):
        for name in scope:
            contained(cfg.repo_root, name)
        if kind == 'release':
            from cycle_hosts import release_scope
            release_scope(cfg, scope, release_list)
        used = [int(match.group(1)) for path in directory.iterdir()
                if (match := re.search(r'CYC-([0-9]+)$', path.name))]
        identity = f"{cfg.artifact_prefix + '-' if cfg.artifact_prefix else ''}CYC-{max(used, default=0) + 1:04d}"
        policy = load_workflow_policy(repo)
        doc = {
            'schema_version': 3, 'id': identity, 'title': title, 'type': kind, 'goal': goal,
            'status': 'active', 'phase': PHASES[kind][0], 'pass': 1, 'pass_limit': LIMITS[kind],
            'created_at': now(), 'updated_at': now(), 'implementers': [implementer], 'coordinator': coordinator,
            'plan': {'revision': 1, 'scope': scope, 'constraints': [], 'acceptance': acceptance, 'verification': [], 'tasks': []},
            'review_policy': {'scrutiny': policy['review.scrutiny'], 'rationale': 'repository default', 'risks': []},
            'required_checks': [], 'evidence': [], 'decisions': [], 'reviews': [], 'history': [],
            'reflection': None, 'blocker': None, 'extensions': [], 'release': None,
            'coverage': None, 'completion': None, 'phase_names': 'verify', **v3_fields(),
        }
        if PHASES[kind][0] == 'plan':
            doc['plan']['tasks'].append(dict(SEEDED_PLAN_TASK, depends_on=[], expected_evidence=list(SEEDED_PLAN_TASK['expected_evidence'])))
        if kind == 'release':
            doc['release_list'] = release_list
            previous = None
            for tid, description, evidence in RELEASE_LISTS[release_list]:
                doc['plan']['tasks'].append({'id': tid, 'phase': 'release', 'description': description, 'depends_on': [previous] if previous else [],
                                             'status': 'pending', 'expected_evidence': [evidence]})
                previous = tid
        if classification is not None:
            doc['classifications'] = [classification(doc)]
        event(doc, 'created', **({'queue': dict(origin)} if origin else {}))
        # Allocate the directory before writing; an interrupted allocation is never reused.
        contained(directory, identity).mkdir()
        save(cfg, doc)
        return doc


def _scope_walk(repo, cfg, doc, patterns=None):
    """Walk the scope with Python glob semantics (`**` is recursive).

    Return `[(pattern, matched, relative file names)]`, one entry per pattern. Excludes the cycle's own
    directory, the cycles lock, `.git` and `__pycache__`.
    """
    out = []
    own_cycle = cfg.docs_root / 'cycles' / doc['id']
    for pattern in (doc['plan']['scope'] if patterns is None else patterns):
        contained(repo, pattern)
        matches = sorted(repo.glob(pattern))
        names = []
        for match in matches:
            for path in sorted(match.rglob('*')) if match.is_dir() else [match]:
                relative = path.relative_to(repo).as_posix()
                if path.is_relative_to(own_cycle) or path == cfg.docs_root / 'cycles/.lock':
                    continue
                if '.git' in path.relative_to(repo).parts or '__pycache__' in path.parts:
                    continue
                if path.is_file():
                    contained(repo, relative)
                    names.append(relative)
        out.append((pattern, bool(matches), names))
    return out


def scope_name_in_scope(name, patterns):
    """True when a repo-relative name lies in the scope under the walk's glob semantics.

    A name is in scope when it, or a directory above it, matches a pattern with `PurePosixPath.full_match`
    (recursive `**`). The walk's `.git` and `__pycache__` exclusions apply. The cycle directory and lock
    are excluded by the callers' pathspecs, as in the walk.
    """
    path = PurePosixPath(name)
    if '.git' in path.parts or '__pycache__' in path.parts:
        return False
    candidates = [path, *path.parents][:-1]
    return any(c.full_match(pattern) for pattern in patterns for c in candidates)


def scope_files(repo, cfg, doc, patterns=None):
    """The one predicate that lists scope files: the glob walk minus untracked git-ignored files.

    Returns `[(pattern, surviving names)]`, or None when git cannot classify the files (no git,
    not inside a work tree, or an unclassifiable path). The fingerprint and the completion check both read it.
    """
    from test_evidence import _ignored_names
    walked = _scope_walk(repo, cfg, doc, patterns)
    ignored = _ignored_names(repo, sorted({name for _, _, names in walked for name in names}))
    if ignored is None:
        return None
    return [(pattern, [n for n in names if n not in ignored]) for pattern, _, names in walked]


def _scope_rows_v1(repo, cfg, doc):
    rows = {}
    own_cycle = cfg.docs_root / 'cycles' / doc['id']
    for pattern in doc['plan']['scope']:
        contained(repo, pattern)
        matches = sorted(repo.glob(pattern))
        for match in matches:
            for path in sorted(match.rglob('*')) if match.is_dir() else [match]:
                relative = path.relative_to(repo).as_posix()
                if path.is_relative_to(own_cycle) or path == cfg.docs_root / 'cycles/.lock':
                    continue
                if '.git' in path.relative_to(repo).parts or '__pycache__' in path.parts:
                    continue
                if path.is_file():
                    contained(repo, relative)
                    rows[relative] = digest(path.read_bytes())
        if not matches:
            rows[pattern] = None
    return rows


def _bookkeeping_entries(repo):
    """The shared evidence exclusion list, read once for one fingerprint."""
    from suite_evidence import runtime_exclusions
    from test_evidence import EvidenceError
    try:
        return runtime_exclusions(repo)
    except EvidenceError as exc:
        raise CycleError(f'cannot read the bookkeeping exclusions: {exc}') from exc


def _bookkeeping_excluded(repo, name, entries=None):
    """True when a repo-relative name is append-only bookkeeping under the shared evidence exclusion list.

    The list is `suite_evidence.runtime_exclusions`: the docs-relative journal, log, inbox, queue and
    cycle records plus the files `.bionic.yml` names under `evidence.bookkeeping_paths`. An entry
    excludes itself and everything below it. A caller testing many names passes the list it read once.
    """
    if entries is None:
        entries = _bookkeeping_entries(repo)
    path = PurePosixPath(name)
    targets = {PurePosixPath(entry) for entry in entries}
    return path in targets or not targets.isdisjoint(path.parents)


def _scope_rows_v2(repo, cfg, doc, bookkeeping=False):
    listed = scope_files(repo, cfg, doc)
    if listed is None:
        return None
    rows = {}
    entries = None
    for pattern, names in listed:
        if bookkeeping and names:
            # Read on first use, as each per-name call read it before.
            entries = _bookkeeping_entries(repo) if entries is None else entries
            names = [n for n in names if not _bookkeeping_excluded(repo, n, entries)]
        for name in names:
            rows[name] = digest((repo / name).read_bytes())
        if not names:
            rows[pattern] = None
    return rows


def source_fingerprint(repo, doc, version=3):
    """Fingerprint declared review scope: file names, bytes and deletions.

    Version 3 is version 2 without append-only bookkeeping: files the shared evidence
    exclusion list names (`suite_evidence.runtime_exclusions`) leave the rows, so an
    append to the log or a configured bookkeeping file keeps a review bound while a
    source change does not. Version 2 lists files through `scope_files`, so untracked
    git-ignored files are outside it, and hashes `{'fingerprint_version': 2, 'rows': rows}`.
    Version 1 walks the working tree, ignored files included. Versions 1 and 2 are
    kept so records made under them still bind.
    """
    repo = Path(repo).resolve()
    cfg = tree(repo)
    if version == 1:
        return digest(encoded(_scope_rows_v1(repo, cfg, doc)))
    rows = _scope_rows_v2(repo, cfg, doc, bookkeeping=version == 3)
    if rows is None:
        return digest(encoded(_scope_rows_v1(repo, cfg, doc)))
    return digest(encoded({'fingerprint_version': version, 'rows': rows}))


def fingerprint_binds(repo, doc, stored):
    """A stored fingerprint binds when it equals the version 3, 2 or 1 value of the current source.

    A version 1 match needs every file, ignored ones included, to be as hashed,
    so it is never looser than the original rule.
    """
    return any(stored == source_fingerprint(repo, doc, version=v) for v in (3, 2, 1))


def retained(cfg, identity, category, value):
    name = f"cycles/{identity}/{category}/{uuid.uuid4().hex}.json"
    path = contained(cfg.docs_root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(encoded(value))
    return {'path': name, 'sha256': digest(path.read_bytes())}


def read_retained(cfg, ref):
    path = contained(cfg.docs_root, ref['path'])
    data = path.read_bytes()
    if digest(data) != ref['sha256']:
        raise CycleError('retained evidence changed')
    return json.loads(data)


def withdrawn_names(doc):
    """The IDR names this cycle withdrew. A name in this set accepts no revision, approval or council attempt.

    Each entry of `doc['withdrawals']` carries `name`, `reason`, `tasks`, `at` and `plan_revision`, and a `deferral` once `defer --decision` ran."""
    return {w['name'] for w in doc.get('withdrawals', [])}


def replaced_name(cfg, doc, name):
    """The withdrawn name an IDR name replaces: `contents.replaces` of its latest revision, or None."""
    ref = next((d for d in reversed(doc['decisions']) if d['kind'] == 'idr' and d['name'] == name), None)
    return read_retained(cfg, ref)['contents'].get('replaces') if ref else None


def approvals(cfg, doc, kind):
    approved = []
    withdrawn = withdrawn_names(doc)
    for decision in doc['decisions']:
        if decision['kind'] != kind or decision['name'] in withdrawn:
            continue
        subject = read_retained(cfg, decision)
        if not decision.get('approval'):
            continue
        from cycle_council import validate_approval
        validate_approval(cfg.repo_root, decision['approval'], purpose=kind, subject=decision['path'])
        approved.append(subject)
    return approved


SELECTION_KEYS = ('assessed', 'proposals', 'selected')
PROPOSAL_KEYS = {'id', 'removes', 'retained_behavior', 'objectives', 'decision_clauses', 'expected_savings', 'verification', 'paths'}
OWNER_ONLY = 'owner selection is required outside a scope authorized in advance'


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _texts(value):
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value)


def selected_proposals(contents):
    """The proposals a simplify selection IDR selects, or a refusal naming the first shape fault."""
    if not _text(contents.get('assessed')):
        raise CycleError('the simplify selection needs a non-empty assessed statement')
    proposals = contents.get('proposals')
    if not isinstance(proposals, list) or not proposals:
        raise CycleError('the simplify selection needs a non-empty list of proposals')
    by_id = {}
    for proposal in proposals:
        if not isinstance(proposal, dict) or set(proposal) != PROPOSAL_KEYS:
            raise CycleError('each simplify proposal carries exactly: ' + ', '.join(sorted(PROPOSAL_KEYS)))
        if not _text(proposal['id']) or proposal['id'] in by_id:
            raise CycleError('simplify proposal ids are non-empty and unique')
        for key in ('removes', 'retained_behavior', 'expected_savings', 'verification'):
            if not _text(proposal[key]):
                raise CycleError(f"proposal {proposal['id']} needs a non-empty {key}")
        for key in ('objectives', 'decision_clauses', 'paths'):
            if not _texts(proposal[key]):
                raise CycleError(f"proposal {proposal['id']} needs a non-empty list of {key}")
        clauses = proposal['decision_clauses']
        if any(c.strip().startswith('none') for c in clauses) and (len(clauses) != 1 or not re.fullmatch(r'none:\s*\S.*', clauses[0].strip())):
            raise CycleError(f"proposal {proposal['id']}: 'none' must be the only decision clause and give a reason as 'none: <reason>'")
        by_id[proposal['id']] = proposal
    selected = contents.get('selected')
    if not _texts(selected) or len(set(selected)) != len(selected) or not set(selected) <= set(by_id):
        raise CycleError('selected must be a non-empty list of distinct proposal ids drawn from the proposals')
    return [by_id[pid] for pid in selected]


def scope_covers(entry, path):
    """Whether a scope entry names the path: equal, or a directory the path lies under."""
    entry, path = posixpath.normpath(entry), posixpath.normpath(path)
    return path == entry or path.startswith(entry.rstrip('/') + '/')


def within_scope(cfg, path, scope):
    try:
        target = contained(cfg.repo_root, path)
    except CycleError as exc:
        raise CycleError(f'proposal path {path}: {exc}') from exc
    return covered_path(cfg.repo_root, target, scope) or any(scope_covers(entry, path) for entry in scope)


def queue_item_scope(cfg, doc):
    """The frozen scope of the queue item that started this cycle, or None without a queue origin."""
    origin = next((h.get('queue') for h in doc['history'][:1] if h.get('action') == 'created'), None)
    if not isinstance(origin, dict) or not origin.get('item'):
        return None
    import cycle_queue  # imported here: cycle_queue imports this module
    try:
        queue = cycle_queue.read_queue(cfg)
        items = [cycle_queue.resolve_item(cfg, queue, origin['item'])]
    except (CycleError, OSError, ValueError):
        return None
    item = next((i for i in items if i.get('id') == origin['item'] and i.get('cycle') == doc['id']), None)
    return list(item['scope']) if item else None


def check_selection(cfg, doc):
    """Simplify: one current IDR revision carries a valid selection that its approval authorizes."""
    current = {}
    for decision in doc['decisions']:
        if decision['kind'] == 'idr' and decision['name'] not in withdrawn_names(doc):
            current[decision['name']] = decision
    carriers = []
    for decision in current.values():
        record = read_retained(cfg, decision)
        if any(key in record['contents'] for key in SELECTION_KEYS):
            carriers.append((decision, record))
    if len(carriers) != 1:
        raise CycleError('a simplify cycle needs exactly one current IDR revision carrying the selection (assessed, proposals, selected); found ' + str(len(carriers)))
    decision, record = carriers[0]
    chosen = selected_proposals(record['contents'])
    for proposal in chosen:
        for path in proposal['paths']:
            if not within_scope(cfg, path, doc['plan']['scope']):
                raise CycleError(f"selected proposal {proposal['id']} changes {path}, which lies outside the plan scope")
    approval = json.loads(contained(cfg.docs_root, decision['approval']).read_text())
    if isinstance(approval, dict) and approval.get('format') == 'crux.owner-approval':
        return
    if isinstance(approval, dict) and approval.get('format') == 'crux.owner-decision-capture.v1':
        from cycle_council import validate_approval
        validate_approval(cfg.repo_root, decision['approval'], purpose='idr', subject=decision['path'])
        return
    scope = queue_item_scope(cfg, doc)
    if scope is None or not all(any(scope_covers(item, entry) for item in scope) for entry in doc['plan']['scope']):
        raise CycleError(f'the selection has a council approval only; {OWNER_ONLY}')


REDUCTION_AREAS = ('production', 'tests', 'instructions', 'execution')
AREA_KEYS = {'change', 'before', 'after', 'evidence'}


def reduction_areas(value):
    """Validate a reduction file: exactly the four areas, each with a closed change and its evidence."""
    if not isinstance(value, dict) or set(value) != {'areas'}:
        raise CycleError('a reduction file holds exactly one key: areas')
    areas = value['areas']
    if not isinstance(areas, dict) or set(areas) != set(REDUCTION_AREAS):
        raise CycleError('reduction areas are exactly: ' + ', '.join(REDUCTION_AREAS))
    for name in REDUCTION_AREAS:
        area = areas[name]
        if not isinstance(area, dict) or set(area) != AREA_KEYS:
            raise CycleError(f'reduction area {name} carries exactly: ' + ', '.join(sorted(AREA_KEYS)))
        if area['change'] not in ('decrease', 'unchanged', 'increase'):
            raise CycleError(f'reduction area {name}: change is decrease, unchanged or increase')
        if not _text(area['before']) or not _text(area['after']) or not _texts(area['evidence']):
            raise CycleError(f'reduction area {name} needs non-empty before, after and a non-empty evidence list')
    return deepcopy(areas)


def check_reduction(cfg, doc):
    """Simplify gate: a current reduction record with no increase in any area and a decrease in at least one."""
    record = doc.get('reduction')
    if not record:
        raise CycleError(f'a simplify cycle needs a reduction record for this pass; record one with the reduction command in the {phase_title(doc)} phase')
    if record['pass'] != doc['pass'] or not fingerprint_binds(cfg.repo_root, doc, record['input_sha256']):
        raise CycleError(f'the reduction record is stale (another pass, or the source changed since it was recorded); record it again in the {phase_title(doc)} phase')
    areas = record['areas']
    increased = [name for name in REDUCTION_AREAS if areas[name]['change'] == 'increase']
    if increased:
        raise CycleError('the reduction record shows an increase in ' + ', '.join(increased) + '; a simplify cycle allows none, so report the increase and propose it as different work (a queue item or an owner report), then remove it from this cycle')
    if not any(areas[name]['change'] == 'decrease' for name in REDUCTION_AREAS):
        raise CycleError('the reduction record shows no area with a decrease; a simplify cycle must reduce at least one area')


def check_withdrawals(doc):
    """A withdrawn name's listed task in the current plan refuses leaving the phase, so a crash or a later plan revision cannot revive it."""
    in_plan = {t['id'] for t in doc['plan']['tasks']}
    for row in doc.get('withdrawals', []):
        restored = sorted(set(row['tasks']) & in_plan)
        if restored:
            raise CycleError(f"IDR {row['name']} was withdrawn, and its task {', '.join(restored)} is in the plan again; remove it with a plan revision")


def check_decisions(cfg, doc):
    check_withdrawals(doc)
    withdrawn = withdrawn_names(doc)
    required = doc['type'] in ('dev', 'simplify') or any(d['kind'] == 'idr' and d['name'] not in withdrawn for d in doc['decisions'])
    if required and not approvals(cfg, doc, 'idr'):
        raise CycleError('council or owner approval of an exact IDR revision is required before dependent work')
    for decision in doc['decisions']:
        if decision['kind'] == 'adr':
            if not decision.get('accepted'):
                raise CycleError('an ADR dependency is awaiting acceptance')
            from decision_policy import validate_acceptance
            validate_acceptance(cfg, decision)
    # Every retained IDR revision marked current requires its own approval.
    current = {}
    for decision in doc['decisions']:
        if decision['kind'] == 'idr' and decision['name'] not in withdrawn:
            current[decision['name']] = decision
    for decision in current.values():
        if not decision.get('approval'):
            raise CycleError('the current IDR revision is not approved')
        from cycle_council import validate_approval
        validate_approval(cfg.repo_root, decision['approval'], purpose='idr', subject=decision['path'])
    if doc['type'] == 'simplify':
        check_selection(cfg, doc)


def check_coverage(doc):
    """Require an explicit account of affected behavior, not a blanket suite."""
    if doc['schema_version'] == 1:
        return
    coverage = doc.get('coverage')
    if not isinstance(coverage, dict) or set(coverage) != {'affected', 'checks', 'not_selected'}:
        raise CycleError('declare related-test coverage before advancing testing')
    if not coverage['affected'] or not all(isinstance(v, str) and v.strip() for v in coverage['affected']):
        raise CycleError('coverage must identify affected behavior and integration points')
    checks = coverage['checks']
    if not isinstance(checks, list) or not all(isinstance(c, dict) and set(c) == {'check_id', 'rationale'} and all(isinstance(v, str) and v.strip() for v in c.values()) for c in checks):
        raise CycleError('coverage checks require check_id and coverage rationale')
    selected = [c['check_id'] for c in checks]
    if len(selected) != len(set(selected)) or set(selected) != set(doc['required_checks']):
        raise CycleError('coverage selected checks must match required checks exactly')
    if not isinstance(coverage['not_selected'], str) or not coverage['not_selected'].strip():
        raise CycleError('coverage must explain checks not selected (or state none)')


def completion_paths(cfg, doc, scope=None):
    # The record cannot contain the SHA of its own final commit. All other scope
    # must be committed; the conductor commits final cycle bookkeeping afterward.
    own = (cfg.docs_root / 'cycles' / doc['id']).relative_to(cfg.repo_root).as_posix()
    lock = (cfg.docs_root / 'cycles/.lock').relative_to(cfg.repo_root).as_posix()
    return [*(doc['plan']['scope'] if scope is None else scope), f':(exclude){own}/**', f':(exclude){lock}']


def check_completion(cfg, doc):
    if doc['schema_version'] == 1:
        return
    record = doc.get('completion')
    if not record:
        raise CycleError('record completion commits or an explicit user-request exception')
    if not fingerprint_binds(cfg.repo_root, doc, record['input_sha256']):
        raise CycleError('completion inputs changed; commit changes and record completion again')
    if not isinstance(record.get('remaining'), str) or not record['remaining'].strip():
        raise CycleError('completion must explain remaining uncommitted work (or state none)')
    commits, exception = record.get('commits'), record.get('exception')
    if bool(commits) == bool(exception):
        raise CycleError('completion needs commits or an explicit user-request exception, exclusively')
    if exception:
        if not isinstance(exception, str) or not exception.strip():
            raise CycleError('exception must quote the actual user instruction and its context')
        return
    def git(*args):
        try:
            result = subprocess.run(['git', '-C', str(cfg.repo_root), *args], capture_output=True, text=True)
        except OSError as exc:
            raise CycleError('git is required to check completion') from exc
        if result.returncode:
            raise CycleError('completion commit must exist in this repository and be an ancestor of HEAD')
        return result.stdout.strip()
    for sha in commits:
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', sha):
            raise CycleError('completion requires full commit SHAs')
        git('rev-parse', '--verify', sha + '^{commit}')
        git('merge-base', '--is-ancestor', sha, 'HEAD')
    # Check committed and staged/unstaged changes, as well as new scoped files. Git pathspecs give `**`
    # two `*` semantics, so each diff keeps only the cycle exclusions and the scope is matched here with
    # the same glob semantics the shared predicate walks. Tracked paths always count, including deleted
    # ones; git ignores only untracked files, so ignore rules never hide a diff entry. `--no-renames` lists
    # both ends of a move, so an in-scope source moved out of scope still counts.
    paths = ['.', *completion_paths(cfg, doc, [])]
    def in_scope(output):
        return [n for n in output.split('\0') if n and scope_name_in_scope(n, doc['plan']['scope'])]
    changed = in_scope(git('diff', '--relative', '--no-renames', '--name-only', '-z', commits[-1], '--', *paths))
    staged = in_scope(git('diff', '--relative', '--no-renames', '--cached', '--name-only', '-z', 'HEAD', '--', *paths))
    unstaged = in_scope(git('diff', '--relative', '--no-renames', '--name-only', '-z', '--', *paths))
    # Untracked in-scope files: the shared predicate's files minus tracked ones. A project root
    # below the top level works because git classifies from any directory inside a work tree.
    listed = scope_files(cfg.repo_root, cfg, doc)
    if listed is None:
        raise CycleError('could not classify the scope files with git')
    tracked = set(git('ls-files', '-z', '--cached').split('\0'))
    untracked = [name for _, names in listed for name in names if name not in tracked]
    if changed or staged or unstaged or untracked:
        raise CycleError('uncommitted or later scope changes are missing from the completion commit')


# An unmet list names at most this many items, then says it is cut and gives the count.
UNMET_SHOWN = 20


def unmet_message(problems):
    """One message naming every unmet item with its reason; a cut list says so and gives the count."""
    shown = '; '.join(problems[:UNMET_SHOWN])
    if len(problems) > UNMET_SHOWN:
        shown += f'; and {len(problems) - UNMET_SHOWN} more ({len(problems)} in all; the list is cut)'
    return shown


def check_current_evidence(cfg, doc, checks):
    """Every check in ``checks`` has a current-pass evidence ref that still validates.

    The refusal names every check that fails, each with its reason, not only the first
    (IDR lean-workflow-traps-and-recovery approach 8)."""
    from test_evidence import validate_evidence
    problems = []
    for check in checks:
        matching = [ref for ref in doc['evidence'] if ref['check_id'] == check and ref['pass'] == doc['pass']]
        if not matching:
            problems.append(f'missing passing evidence for {check}')
            continue
        try:
            validate_evidence(cfg.repo_root, matching[-1]['evidence_id'], check_id=check)
        except ValueError as exc:
            problems.append(f'invalid evidence for {check}: {exc}')
    if problems:
        raise CycleError(unmet_message(problems))


def whole_state_checks(cfg):
    """The registered checks that prove a whole code state in a plugin-authoring checkout, else ``[]``.

    These are the full checkout suites and the tier check: every registered ``checkout:`` id except the
    release-tier suites. A release-tier receipt never satisfies Build exit or completion (IDR test-tiers A4).
    """
    from authoring_scope import is_authoring_checkout
    if not is_authoring_checkout(cfg.repo_root, __file__):
        return []
    from suite_evidence import full_checkout_ids, registered_declarations
    return full_checkout_ids(registered_declarations(cfg.repo_root))


def check_tests(cfg, doc):
    check_coverage(doc)
    if not doc['required_checks']:
        raise CycleError('declare at least one required check (focused verification is sufficient)')
    missing = [check for check in whole_state_checks(cfg) if check not in doc['required_checks']]
    if missing:
        raise CycleError('required checks must include the full checkout suites and the tier check; missing: '
                         + ', '.join(missing))
    check_current_evidence(cfg, doc, doc['required_checks'])


def check_build(cfg, doc):
    """Build exit: each declared Build check passes; a plugin-authoring checkout also declares the full checkout suites and the tier check."""
    declared = doc.get('build_checks', [])
    missing = [check for check in whole_state_checks(cfg) if check not in declared]
    if missing:
        raise CycleError('Build checks must include the registered checkout suites; missing: ' + ', '.join(missing))
    check_current_evidence(cfg, doc, declared)


BASIS_VERSION = 4

# Version 3 classifies every task field. A field in neither set fails loudly,
# so a future task field forces a decision rather than silently entering or
# leaving the basis.
TASK_BASIS_FIELDS = ('id', 'phase', 'description', 'expected_evidence', 'integrates')
TASK_BOOKKEEPING_FIELDS = ('depends_on', 'status', 'assignee', 'result_path', 'commits', 'evidence', 'stage', 'note', 'replaced_commits', 'fix', 'adopted_commits')


def review_basis_digest(doc, version):
    """Digest what an independent reviewer approved.

    Version 1 hashes the whole plan. Version 2 omits plan tasks of phases after
    the Review phase (Reflect today), so reflection bookkeeping added
    after approval keeps the binding. Task status, reflection, completion,
    history, blocker and status are never part of the basis.

    Version 3 keeps the version-2 phase cutoff and projects each task to
    `TASK_BASIS_FIELDS`, so delivery bookkeeping (`TASK_BOOKKEEPING_FIELDS`)
    keeps an approval bound. It also drops the plan's revision counter; the
    fields the counter counts are hashed directly. Versions 1 and 2 compute as
    they did when recorded.

    Version 4 keeps version 3 and replaces the current-pass evidence list with
    a map from each required check id to the `declaration_sha256` of its latest
    current-pass ref (a legacy ref without the field contributes its
    evidence_id). A refresh of the same declaration keeps an approval bound; a
    changed command, inputs or exclusions does not. Live evidence validity is
    checked at every gate by `check_tests`, not by the basis.
    """
    plan = deepcopy(doc['plan'])
    if version in (2, 3, 4):
        sequence = phases_of(doc)
        cutoff = sequence.index('review')
        plan['tasks'] = [task for task in plan['tasks'] if sequence.index(task['phase']) <= cutoff]
    elif version != 1:
        raise CycleError('unknown review basis version')
    if version in (3, 4):
        plan.pop('revision', None)
        projected = []
        for task in plan['tasks']:
            unclassified = sorted(set(task) - set(TASK_BASIS_FIELDS) - set(TASK_BOOKKEEPING_FIELDS))
            if unclassified:
                raise CycleError('unclassified task field in review basis: ' + ', '.join(unclassified))
            projected.append({key: task[key] for key in TASK_BASIS_FIELDS if key in task})
        plan['tasks'] = projected
    else:
        for task in plan['tasks']:
            task.pop('status', None)
    current = [ref for ref in doc['evidence'] if ref['pass'] == doc['pass']]
    if version == 4:
        latest = {}
        for ref in current:
            latest[ref['check_id']] = ref.get('declaration_sha256') or ref['evidence_id']
        evidence = {check: latest[check] for check in sorted(set(doc['required_checks'])) if check in latest}
    else:
        evidence = current
    basis = {'plan': plan, 'required_checks': doc['required_checks'], 'review_policy': doc['review_policy'], 'evidence': evidence}
    if doc['schema_version'] >= 2:
        basis['coverage'] = doc['coverage']
    if version in (3, 4) and doc['type'] == 'simplify':
        # A reduction changed after approval invalidates the review. Other types hash as they always did.
        basis['reduction'] = doc.get('reduction')
    return digest(encoded(basis))


def review_basis_v1(doc):
    """The original whole-plan basis, kept to bind reports recorded before versioning."""
    return review_basis_digest(doc, 1)


def review_basis_v2(doc):
    """The version-2 basis, kept to bind reports recorded under it."""
    return review_basis_digest(doc, 2)


def review_basis(doc):
    """The current basis (version 4), recorded in new reports."""
    return review_basis_digest(doc, BASIS_VERSION)


def basis_binds(report, v1, v2, v3=None, v4=None):
    """Whether a stored report's basis matches the current record.

    A versioned report binds only to its own version. An unversioned (legacy)
    report binds to the version-1 or the version-2 digest, as it did before
    version 3 existed. An unknown version never binds.
    """
    stored = report.get('basis_sha256')
    version = report.get('basis_version')
    if version is None:
        return stored in (v1, v2)
    if type(version) is int and version in (1, 2, 3, 4):
        expected = {1: v1, 2: v2, 3: v3, 4: v4}[version]
        return expected is not None and stored == expected
    return False


def check_review(cfg, doc):
    v1, v2, v3, v4 = review_basis_v1(doc), review_basis_v2(doc), review_basis_digest(doc, 3), review_basis(doc)
    for ref in reversed(doc['reviews']):
        report = read_retained(cfg, ref)
        if report['pass'] != doc['pass'] or not fingerprint_binds(cfg.repo_root, doc, report['input_sha256']) or not basis_binds(report, v1, v2, v3, v4):
            continue
        if report['reviewer'] in doc['implementers']:
            continue
        if report['verdict'] == 'approve' and not report['blocking']:
            return report
        raise CycleError('blocking review findings require returning through the cycle')
    raise CycleError('a passing independent review of the current scope is required')


def requirements(cfg, doc, target, first=False):
    """Unmet requirements for `target`: `next` (leave the current phase) or `completion` (close the cycle).

    Each item is {requirement, problem}. The checks run in the order the low-level advance
    always ran them, so the first item is the error it raises; with `first` the evaluation
    stops there, so a later check never runs. The low-level advance, the typed advance,
    finish and inspect all read this one function."""
    items = []

    def need(name, check):
        if first and items:
            return
        try:
            check()
        except CycleError as exc:
            items.append({'requirement': name, 'problem': str(exc)})

    def tasks_done(phase=None, message='current phase has unfinished tasks'):
        def check():
            open_tasks = [f"{t['id']} ({t['status']})" for t in doc['plan']['tasks'] if t['status'] != 'done' and (phase is None or t['phase'] == phase)]
            if open_tasks:
                raise CycleError(f'{message}: {unmet_message(open_tasks)}')
        return check

    if listed(doc):
        need('tasks', tasks_done())
        need('completion', lambda: check_completion(cfg, doc))
        return items
    phase = 'reflect' if target == 'completion' else doc['phase']
    need('decisions', lambda: check_decisions(cfg, doc))
    need('phase-tasks', tasks_done(phase))
    if phase == 'plan':
        def plan_check():
            plan = doc['plan']
            if not plan['verification'] or not plan['tasks'] or not set(phases_of(doc)).issubset({t['phase'] for t in plan['tasks']}):
                raise CycleError('the plan must describe verification and tasks across every phase')
            if doc['type'] == 'refactor' and not plan.get('preserved_behavior'):
                raise CycleError('refactor must identify preserved behavior and intended improvement')
            if doc['type'] == 'refactor' and not plan.get('improvement'):
                raise CycleError('refactor requires intended improvement')
        need('plan', plan_check)
    elif phase == 'build':
        need('build-checks', lambda: check_build(cfg, doc))
    elif phase in CHECK_PHASES:
        need('tests', lambda: check_tests(cfg, doc))
        if doc['type'] == 'simplify':
            need('reduction', lambda: check_reduction(cfg, doc))
    elif phase == 'review':
        need('tests', lambda: check_tests(cfg, doc))
        need('review', lambda: check_review(cfg, doc))
    elif phase == 'reflect':
        need('tasks', tasks_done(message='completion requires every planned task to be done'))
        need('tests', lambda: check_tests(cfg, doc))
        if doc['type'] == 'simplify':
            need('reduction', lambda: check_reduction(cfg, doc))
        need('review', lambda: check_review(cfg, doc))
        def reflection():
            if not doc['reflection']:
                raise CycleError('reflection is required before completion')
        need('reflection', reflection)
        need('completion', lambda: check_completion(cfg, doc))
    return items


def first_unmet(cfg, doc, target='next'):
    """Raise the first unmet requirement's message, as the low-level advance always has."""
    unmet = requirements(cfg, doc, target, first=True)
    if unmet:
        raise CycleError(unmet[0]['problem'])



DELIVERY_FIELDS = ('assignee', 'result_path', 'commits', 'evidence', 'stage', 'note', 'replaced_commits', 'fix', 'adopted_commits')
STAGES = ('implemented', 'integrated')


def run_git(cfg, *argv):
    done = subprocess.run(['git', '-C', str(cfg.repo_root), *argv], capture_output=True, text=True)
    return done.returncode, done.stdout


def resolve_commit(cfg, name):
    """Full 40-hex id of an existing commit, or a refusal."""
    if not re.fullmatch(r'[0-9a-fA-F]{7,64}', str(name)):
        raise CycleError(f'commit {name} is not a hexadecimal commit id')
    code, out = run_git(cfg, 'rev-parse', '--verify', '--quiet', f'{name}^{{commit}}')
    full = out.strip()
    if code != 0 or not re.fullmatch(r'[0-9a-f]{40}', full):
        raise CycleError(f'commit {name} does not resolve to a commit in this repository')
    return full


def on_head(cfg, sha):
    return run_git(cfg, 'merge-base', '--is-ancestor', sha, 'HEAD')[0] == 0


def result_file(cfg, value):
    """A recorded result path: absolute, or relative to the repository root (not the docs root)."""
    path = Path(value)
    return path if path.is_absolute() else cfg.repo_root / path


def delivery_holds(cfg, task):
    """Whether a task's recorded delivery still stands: integrated commits on HEAD, evidence files present.

    The two checks are independent. Any git or filesystem error counts as not holding,
    so revalidation never refuses a command.
    """
    try:
        if task.get('stage') == 'integrated' and not all(on_head(cfg, c) for c in task.get('commits', [])):
            return False
    except (OSError, ValueError):
        return False
    for item in task.get('evidence', []):
        try:
            if not contained(cfg.docs_root, item).is_file():
                return False
        except (CycleError, OSError, ValueError):
            return False
    return True


def reopen(task):
    """An affected task loses its status and stage and keeps every other recorded field."""
    task['status'] = 'pending'
    task.pop('stage', None)


def start_pass(cfg, doc):
    """Reset tasks for a new pass: Plan and Build tasks whose delivery still holds stay; others reset.

    A done fix task stays done and is never reopened. An unfinished fix task leaves the plan, and
    nothing depends on it afterwards; the `return-requested` event already holds the prior plan."""
    kept, dropped = [], set()
    for task in doc['plan']['tasks']:
        if 'fix' in task:
            if task['status'] == 'done':
                kept.append(task)
            else:
                dropped.add(task['id'])
            continue
        if task['phase'] not in {'plan', 'build'} or not delivery_holds(cfg, task):
            reopen(task)
        kept.append(task)
    for task in kept:
        task['depends_on'] = [d for d in task['depends_on'] if d not in dropped]
    doc['plan']['tasks'] = kept
    doc['plan']['revision'] += 1


REPLAN_FIELDS = ('phase', 'description', 'expected_evidence', 'depends_on', 'integrates')


def check_plan_file(plan, doc=None):
    """A plan file sets plan content only; delivery belongs to the `task` command.

    While `doc` is in Plan, a Plan-phase task may also carry `"status": "done"`."""
    in_plan = doc is not None and doc['phase'] == 'plan'
    for task in plan.get('tasks', []):
        if not isinstance(task, dict):
            continue
        status = task.get('status', 'pending')
        settable = status == 'done' and in_plan and task.get('phase') == 'plan'
        found = ([f"status {status}"] if status != 'pending' and not settable else []) + [k for k in DELIVERY_FIELDS if k in task]
        if found:
            raise CycleError(f"plan task {task.get('id')} carries {', '.join(found)}; a plan file sets plan content only, so record state and delivery with the `task` command")


def replan(cfg, previous, plan):
    """Merge a plan file over the recorded plan: an unaffected paired task keeps its status and delivery."""
    recorded = {t['id']: t for t in previous['tasks']}
    merged = []
    for task in plan['tasks']:
        old = recorded.get(task['id'])
        if old is None:
            merged.append(task)
            continue
        new = deepcopy(task)
        marked = task.get('status') == 'done'
        new['status'] = 'done' if marked else old['status']
        for key in DELIVERY_FIELDS:
            if key in old:
                new[key] = deepcopy(old[key])
        if not marked and (any(old.get(k) != task.get(k) for k in REPLAN_FIELDS) or not delivery_holds(cfg, new)):
            reopen(new)
        merged.append(new)
    plan['tasks'] = merged


def replace_commit(cfg, task, new, pair, note):
    """Replace OLD with NEW in place in `new` and append the replacement; a repeat is a no-op."""
    old, name = pair
    if not (note or '').strip():
        raise CycleError('--replace-commit requires --note')
    target = resolve_commit(cfg, name)
    prefix = str(old).lower()
    if not re.fullmatch(r'[0-9a-f]{7,40}', prefix):
        raise CycleError(f'commit {old} is not a hexadecimal commit id')
    commits, history = list(task.get('commits', [])), task.get('replaced_commits', [])
    if target in commits and any(h['from'].startswith(prefix) and h['to'] == target for h in history):
        return
    matches = [c for c in commits if c.startswith(prefix)]
    if not matches:
        raise CycleError(f'commit {old} is not recorded on this task')
    if len(matches) > 1:
        raise CycleError(f'commit prefix {old} matches more than one recorded commit')
    if target in commits:
        raise CycleError(f'commit {name} is already recorded on this task')
    new['commits'] = [target if c == matches[0] else c for c in commits]
    new['replaced_commits'] = [*history, {'from': matches[0], 'to': target, 'at': now(), 'note': note.strip()}]


FIX_KEYS = {'finding', 'eligibility'}
FIX_PHASES = (*CHECK_PHASES, 'review')


def fix_receipt(cfg, evidence_id):
    """The stored test-evidence record for an id, or a refusal."""
    from test_evidence import EvidenceError, _read, storage
    if not isinstance(evidence_id, str) or not re.fullmatch(r'TE-[0-9a-f]{32}', evidence_id):
        raise CycleError('invalid evidence ID: a fix names test-evidence receipts such as TE-<32 hex>')
    try:
        return _read(storage(cfg.repo_root) / (evidence_id + '.json'))
    except EvidenceError as exc:
        raise CycleError(f'evidence {evidence_id} cannot be read: {exc}') from exc


def fix_before_receipt(cfg, evidence_id):
    record = fix_receipt(cfg, evidence_id)
    if record.get('status') != 'failed':
        raise CycleError(f"--fix-before must name a receipt that recorded a failure; {evidence_id} has status {record.get('status')}")
    return record


def fix_after_receipt(cfg, evidence_id, check_id):
    """The receipt is the current valid passing result for ``check_id`` (the check that failed before)."""
    from test_evidence import EvidenceError, validate_evidence
    try:
        return validate_evidence(cfg.repo_root, evidence_id, check_id=check_id)
    except EvidenceError as exc:
        raise CycleError(f'--fix-after {evidence_id} does not answer the failed check {check_id}: {exc}') from exc


def set_fix_receipts(cfg, new, args):
    """Record --fix-before and --fix-after on a fix task; finding and eligibility are never touched."""
    before, after = args.get('fix_before'), args.get('fix_after')
    if not (before or after):
        return
    if 'fix' not in new:
        raise CycleError(f"task {new['id']} is not a fix task; --fix-before and --fix-after belong to a task added with a fix")
    fix = dict(new['fix'])
    if before:
        fix['before'] = fix_before_receipt(cfg, before)['id']
    check = fix_receipt(cfg, fix['before'])['declaration']['check_id'] if fix.get('before') else None
    if after:
        if check is None:
            raise CycleError('record --fix-before, the receipt of the failure, before --fix-after')
        fix['after'] = fix_after_receipt(cfg, after, check)['id']
    elif fix.get('after') and before:
        fix_after_receipt(cfg, fix['after'], check)
    new['fix'] = fix


def criterion_observation(cfg, doc, index, path, *, before=False):
    """Read a committed observation; retain its digest so later edits cannot rewrite the measurement."""
    if type(index) is not int or not 0 <= index < len(doc['plan']['acceptance']):
        raise CycleError('criterion observation index is outside the acceptance criteria (indices start at zero)')
    if not _text(path):
        raise CycleError('criterion observation names a non-empty documentation-relative file path')
    source = contained(cfg.docs_root, path)
    rel = source.relative_to(cfg.repo_root).as_posix()
    if path_class(source, cfg.docs_root) is not None:
        raise CycleError('criterion observation must be a regular file within the documentation tree')
    data = source.read_bytes()
    try:
        code, committed = run_git(cfg, 'show', f'HEAD:{rel}')
    except UnicodeError as exc:
        raise CycleError('criterion observation must contain UTF-8 JSON') from exc
    if code or committed.encode() != data:
        raise CycleError('criterion observation must match a committed file on HEAD')
    try:
        record = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise CycleError('criterion observation must contain JSON') from exc
    if (not isinstance(record, dict) or set(record) != {'criterion', 'value', 'met', 'commit'}
            or type(record['criterion']) is not int or record['criterion'] != index
            or not _text(record['value']) or type(record['met']) is not bool):
        raise CycleError('criterion observation carries criterion (the same index), value, met and commit')
    sha = resolve_commit(cfg, record['commit'])
    if not on_head(cfg, sha):
        raise CycleError('criterion observation measured commit must be an ancestor of HEAD')
    if before and record['met']:
        raise CycleError('a before observation must record the criterion unmet')
    return {'path': source.relative_to(cfg.docs_root).as_posix(), 'sha256': digest(data)}, {**record, 'commit': sha}


def set_fix_observation(cfg, doc, new, args):
    path = args.get('fix_observation')
    if not path:
        return
    if 'criterion' not in new.get('fix', {}):
        raise CycleError('--fix-observation belongs to a criterion fix')
    criterion = new['fix']['criterion']
    ref, _ = criterion_observation(cfg, doc, criterion['index'], path)
    criterion['after'] = ref


def check_fix_done(cfg, new, doc=None):
    """A fix task is done only with a commit, a failed check that now passes, and for Review an approving fix-diff review."""
    fix = new['fix']
    if not new.get('commits'):
        raise CycleError('a fix task needs at least one commit before it is done')
    if 'criterion' in fix:
        criterion = fix['criterion']
        if not criterion.get('after'):
            raise CycleError('a criterion fix needs an after observation through --fix-observation')
        # read_retained verifies the digest before reparsing and checking committed provenance.
        try:
            read_retained(cfg, criterion['before'])
            read_retained(cfg, criterion['after'])
        except CycleError as exc:
            raise CycleError('criterion observation digest changed') from exc
        criterion_observation(cfg, doc, criterion['index'], criterion['before']['path'], before=True)
        _, after = criterion_observation(cfg, doc, criterion['index'], criterion['after']['path'])
        if not after['met']:
            raise CycleError('the after observation must record the criterion met')
        if any(run_git(cfg, 'merge-base', '--is-ancestor', sha, after['commit'])[0] for sha in new['commits']):
            raise CycleError('the after observation must measure the fix commit or a descendant of every fix commit')
        check_current_evidence(cfg, doc, list(dict.fromkeys([*doc.get('build_checks', []), *doc['required_checks']])))
    else:
        if not fix.get('before'):
            raise CycleError('a fix task needs --fix-before: the receipt of the check that failed')
        if not fix.get('after'):
            raise CycleError('a fix task needs --fix-after: the receipt of the same check passing now')
        check = fix_before_receipt(cfg, fix['before'])['declaration']['check_id']
        fix_after_receipt(cfg, fix['after'], check)
    if new['phase'] == 'review':
        if not fix.get('review'):
            raise CycleError('a Review-phase fix needs a recorded fix-diff review before it is done: record a review whose report names this task as fix_task')
        report = read_retained(cfg, fix['review'])
        if report['verdict'] != 'approve' or report['blocking']:
            raise CycleError('the fix-diff review is not approving and non-blocking; a blocking finding returns through the cycle')


def fix_phase_problem(doc):
    """The refusal text when the cycle's phase takes no fix task, else None."""
    return None if doc['phase'] in FIX_PHASES else f"a fix task is added in {phase_title(doc)} or Review only"


def fix_slot_problem(doc, cfg):
    """The refusal text when this phase and pass have no room for a fix task, else None."""
    if any('fix' in other and other['phase'] == doc['phase'] and other['fix']['pass'] == doc['pass'] for other in doc['plan']['tasks']):
        return 'one fix task per phase per pass: a second fix returns through the cycle'
    if doc['phase'] == 'review':
        current = [read_retained(cfg, ref) for ref in doc['reviews']]
        current = [report for report in current if report['pass'] == doc['pass']]
        latest = current[-1] if current else None
        if not latest or not (latest['verdict'] == 'changes-required' or latest['blocking']) or not latest['blocking']:
            return 'a Review-phase fix needs the latest review of this pass to be blocking, with at least one blocking finding; otherwise return through the cycle'
    return None


def check_fix_findings(doc, cfg, findings):
    """Validate the optional `fix.findings`: distinct blocking ids of the latest review, Review phase only."""
    if doc['phase'] != 'review':
        raise CycleError(f'fix.findings names blocking findings of the latest review; a {phase_title(doc)} fix takes none')
    if not isinstance(findings, list) or not findings or len(set(findings)) != len(findings):
        raise CycleError('fix.findings is a non-empty list of distinct finding ids such as r1:blocking:0')
    latest = read_retained(cfg, doc['reviews'][-1])
    for finding in findings:
        match = FINDING_ID.fullmatch(finding) if isinstance(finding, str) else None
        if not match or match.group(2) != 'blocking':
            raise CycleError('fix.findings holds blocking finding ids such as r1:blocking:0')
        if int(match.group(1)) != len(doc['reviews']) or int(match.group(3)) >= len(latest['blocking']):
            raise CycleError(f'fix.findings {finding} is not a blocking finding of the latest review')


def fix_step_problem(doc, cfg):
    """Why a fix task cannot be added now, from the cycle's facts alone; None when it can.

    check_fix_add applies these same two checks, so a classified fix-step meets the eligibility the writer enforces."""
    return fix_phase_problem(doc) or fix_slot_problem(doc, cfg)


def check_fix_add(doc, cfg, task):
    """Accept a task carrying `fix` only for a small fix in the phase after Build (Verify, or Test on an older record) or Review; the writer sets `pass`."""
    fix = task['fix']
    if (problem := fix_phase_problem(doc)):
        raise CycleError(problem)
    if task['phase'] != doc['phase']:
        raise CycleError('a fix task belongs to the current phase')
    if not isinstance(fix, dict) or not FIX_KEYS <= set(fix) <= FIX_KEYS | {'findings', 'criterion'}:
        raise CycleError('a fix carries finding and eligibility and, in Review, optionally findings; the writer sets pass, and before, after and review come from the task and review commands')
    if not all(_text(fix[key]) for key in FIX_KEYS):
        raise CycleError('a fix needs a non-empty finding and eligibility reason')
    if task.get('status', 'pending') != 'pending' or any(key in task for key in DELIVERY_FIELDS if key != 'fix'):
        raise CycleError('a fix task is added pending with no delivery fields; record delivery with the `task` command')
    if (problem := fix_slot_problem(doc, cfg)):
        raise CycleError(problem)
    if 'findings' in fix:
        check_fix_findings(doc, cfg, fix['findings'])
    task['fix'] = {'finding': fix['finding'], 'eligibility': fix['eligibility'], 'pass': doc['pass'], **({'findings': list(fix['findings'])} if 'findings' in fix else {})}
    if 'criterion' in fix:
        criterion = fix['criterion']
        if not isinstance(criterion, dict) or set(criterion) != {'index', 'observation'}:
            raise CycleError('fix.criterion names index and observation (a committed failed observation)')
        ref, _ = criterion_observation(cfg, doc, criterion['index'], criterion['observation'], before=True)
        task['fix']['criterion'] = {'index': criterion['index'], 'before': ref}


FINDING_ID = re.compile(r'^r([0-9]+):(blocking|advisory|cosmetic):([0-9]+)$')


def record_deferral(cfg, doc, finding, note):
    """The deferral entry for a recorded, non-blocking finding of this pass; refuses anything else."""
    match = FINDING_ID.fullmatch(finding) if isinstance(finding, str) else None
    if not match:
        raise CycleError('a finding id looks like r<N>:<blocking|advisory|cosmetic>:<index>, for example r1:advisory:0')
    number, category, index = int(match.group(1)), match.group(2), int(match.group(3))
    if category == 'blocking':
        raise CycleError('a blocking finding is fixed or returned; it is never deferred')
    if not 1 <= number <= len(doc['reviews']):
        raise CycleError(f'no review report {number} on this record')
    report = read_retained(cfg, doc['reviews'][number - 1])
    if report['pass'] != doc['pass'] or index >= len(report[category]):
        raise CycleError(f'finding {finding} is not a finding of a review report in this pass')
    if any(d['finding'] == finding and d['pass'] == doc['pass'] for d in doc.get('deferrals', [])):
        raise CycleError(f'finding {finding} is already deferred')
    if not isinstance(note, str) or not note.strip():
        raise CycleError('a deferral needs a note that names where the follow-up is recorded')
    return {'finding': finding, 'note': note.strip(), 'pass': doc['pass'], 'phase': doc['phase'], 'at': now()}


def latest_idr(doc, name):
    """The latest retained revision of an IDR name, or None."""
    return next((d for d in reversed(doc['decisions']) if d['kind'] == 'idr' and d['name'] == name), None)


def replacement_chain(cfg, doc, name):
    """The name, then each withdrawn name it replaces in turn."""
    chain = []
    while name and name not in chain:
        chain.append(name)
        name = replaced_name(cfg, doc, name)
    return chain


def council_state(cfg, doc, name):
    """The council attempts that count against an IDR name and the limit the council writer applies; read-only.

    The count follows the replacement chain, so a replacement continues the attempts of the record it replaces. The
    limit comes from `council_policy.resolve`, the call `cycle_council.begin_mode` makes, and is never a constant here.
    Raises CycleError when the attempt files or the policy cannot be read."""
    import council_policy as policy
    import cycle_council
    rows = cycle_council.idr_history(cfg, doc, name)
    frozen = rows[-1].get('policy') if rows else None
    if rows and frozen is None:
        frozen = {'mode': 'strict', 'settings': policy.normalized({}), 'legacy_limit': 3}
    elif frozen and any(row.get('format') == 'crux.cycle-council-attempt' for row in rows):
        frozen = dict(frozen, legacy_limit=3)
    limit = policy.resolve(cfg.repo_root, 'idr', previous=frozen, logical_id=f"idr:{doc['id']}:{name}")['max_attempts']
    return {'attempts': rows, 'limit': limit}


def attempt_history(cfg, doc, name):
    """The recorded council attempts of an IDR name as the defer entry keeps them; empty when none can be read."""
    try:
        rows = council_state(cfg, doc, name)['attempts']
    except (CycleError, OSError, ValueError):
        return []
    return [{'round': row.get('round'), 'id': row.get('id'), 'status': row.get('status'), 'record': row.get('record'),
             'progress': row.get('progress')} for row in rows]


def check_replaces(cfg, doc, name, contents):
    """A withdrawn name takes no revision; `replaces` names a withdrawn record and stays the same across revisions."""
    if name in withdrawn_names(doc):
        raise CycleError(f'IDR {name} was withdrawn and accepts no further revision; a narrowed record needs a new name that replaces it')
    previous = replaced_name(cfg, doc, name)
    if latest_idr(doc, name):
        if contents.get('replaces') != previous:
            raise CycleError(f'a revision of {name} keeps the replaces of the revision before it: {previous!r}')
        return
    if 'replaces' not in contents:
        return
    target = contents['replaces']
    if not _text(target):
        raise CycleError('replaces is the text name of the withdrawn IDR it replaces')
    if target not in withdrawn_names(doc) or target == name:
        raise CycleError(f'replaces names {target!r}, which is not an IDR withdrawn in this cycle')


def withdraw_decision(cfg, doc, name, reason, tasks):
    """Mark an IDR name withdrawn and remove its dependent tasks from the plan, in the record the caller saves.

    The caller writes the record once, so the mark and the removal land together. The plan-revised event keeps
    the removed tasks (in `previous`) and the reason. Only the Plan phase withdraws."""
    if doc['phase'] != 'plan':
        raise CycleError('a decision is withdrawn in the Plan phase; later phases keep their approved records')
    if not _text(reason):
        raise CycleError('withdrawal needs a reason')
    if not isinstance(name, str) or latest_idr(doc, name) is None:
        raise CycleError(f'{name!r} is not a retained IDR of this cycle')
    if name in withdrawn_names(doc):
        raise CycleError(f'IDR {name} is already withdrawn')
    if not isinstance(tasks, list) or not all(isinstance(t, str) for t in tasks) or len(set(tasks)) != len(tasks):
        raise CycleError('withdrawal lists the dependent plan task ids, each once')
    by_id = {t['id']: t for t in doc['plan']['tasks']}
    for task_id in tasks:
        if task_id not in by_id:
            raise CycleError(f'unknown task {task_id}: list only tasks that are in the plan')
        if by_id[task_id]['status'] != 'pending' or task_holder(doc, task_id):
            raise CycleError(f'task {task_id} has started, so it is not removed with a withdrawal')
    for task in doc['plan']['tasks']:
        blocked = sorted(set(task['depends_on']) & set(tasks))
        if task['id'] not in tasks and blocked:
            raise CycleError(f"task {task['id']} depends on {', '.join(blocked)}; list it too, or revise the plan first")
    previous = deepcopy(doc['plan'])
    doc['plan']['tasks'] = [t for t in doc['plan']['tasks'] if t['id'] not in tasks]
    doc['plan']['revision'] = previous['revision'] + 1
    event(doc, 'plan-revised', previous=previous, reason=reason, withdrawn=name, removed_tasks=list(tasks))
    doc.setdefault('withdrawals', []).append({'name': name, 'reason': reason.strip(), 'tasks': list(tasks), 'at': now(),
                                              'plan_revision': doc['plan']['revision']})


def defer_withdrawal(cfg, doc, name, note):
    """Record where the work removed by a withdrawal is followed up; keeps the reason and the council attempt history."""
    row = next((w for w in doc.get('withdrawals', []) if w['name'] == name), None)
    if row is None:
        raise CycleError(f'IDR {name} is not withdrawn; withdraw it before deferring its work')
    if 'deferral' in row:
        raise CycleError(f'the work of IDR {name} is already deferred')
    if not _text(note):
        raise CycleError('a deferral needs a note that names where the follow-up is recorded')
    row['deferral'] = {'note': note.strip(), 'at': now(), 'reason': row['reason'], 'tasks': list(row['tasks']),
                       'attempts': attempt_history(cfg, doc, name)}


def updated_task(cfg, doc, task, args):
    """The task as it would be after this update; the caller compares it with the stored task."""
    new = deepcopy(task)
    fields = {k: args.get(k) for k in ('state', 'assignee', 'result_path', 'stage', 'note')}
    commits, evidence = args.get('commits') or [], args.get('evidence') or []
    pair = args.get('replace_commit')
    if not any(fields.values()) and not commits and not evidence and not pair and not args.get('fix_before') and not args.get('fix_after') and not args.get('fix_observation') and not args.get('adopt_commits'):
        raise CycleError('task update names no state or delivery field')
    state = fields['state']
    if state == 'done' and any(t['status'] != 'done' for t in doc['plan']['tasks'] if t['id'] in task['depends_on']):
        raise CycleError('task dependencies are incomplete')
    if pair:
        # With a replacement the note describes it and does not overwrite the task note.
        replace_commit(cfg, task, new, pair, fields['note'])
        fields['note'] = None
    if state:
        new['status'] = state
    for key in ('assignee', 'result_path', 'note'):
        if fields[key]:
            if not str(fields[key]).strip():
                raise CycleError(f'{key} must not be empty')
            new[key] = fields[key]
    full = [resolve_commit(cfg, c) for c in commits]
    if full:
        new['commits'] = list(dict.fromkeys([*new.get('commits', []), *full]))
    if args.get('adopt_commits'):
        rows = list(new.get('adopted_commits', []))
        for name in args['adopt_commits']:
            sha = resolve_commit(cfg, name)
            provenance = adoption_source(cfg, doc, sha)
            if provenance not in rows:
                rows.append(provenance)
            new['commits'] = list(dict.fromkeys([*new.get('commits', []), sha]))
        new['adopted_commits'] = rows
    if evidence:
        merged = list(task.get('evidence', []))
        seen = {posixpath.normpath(e) for e in merged}
        for item in evidence:
            if not contained(cfg.docs_root, item).is_file():
                raise CycleError(f'evidence {item} does not exist under the docs root')
            # './e.md' and 'e.md' name one file: store and compare the normalized form.
            item = posixpath.normpath(str(item))
            if item not in seen:
                merged.append(item)
                seen.add(item)
        new['evidence'] = merged
    result = new.get('result_path')
    if new['status'] == 'done' and result and not Path(result).is_absolute():
        # reconcile reads the same base; a docs-relative path would read as missing.
        if not result_file(cfg, result).exists() and (cfg.docs_root / result).exists():
            raise CycleError(f'result path {result} is relative to the docs root; '
                             'give it absolute or relative to the repository root')
    stage = fields['stage']
    if stage:
        if stage not in STAGES:
            raise CycleError('stage must be implemented or integrated')
        if task.get('stage') and STAGES.index(stage) < STAGES.index(task['stage']):
            # A late duplicate report (implemented after integrated) is already satisfied
            # when it names only recorded commits; a new commit at a lower stage is refused.
            if any(c not in task.get('commits', []) for c in full):
                raise CycleError('stage cannot move backward')
        else:
            new['stage'] = stage
    if new.get('stage') and not new.get('commits'):
        raise CycleError('a stage requires at least one recorded commit')
    if new.get('stage') == 'integrated':
        behind = [c[:12] for c in new['commits'] if not on_head(cfg, c)]
        if behind:
            raise CycleError('integrated requires every commit to be an ancestor of HEAD; not on HEAD: ' + ', '.join(behind))
    if 'criterion' in new.get('fix', {}) and (args.get('fix_before') or args.get('fix_after')):
        raise CycleError('a criterion fix uses observations rather than --fix-before and --fix-after receipts')
    set_fix_receipts(cfg, new, args)
    set_fix_observation(cfg, doc, new, args)
    if 'fix' in new and new['status'] == 'done' and task['status'] != 'done':
        check_fix_done(cfg, new, doc)
    return new


def adoption_source(cfg, doc, sha):
    """The exact earlier recorded delivery of an ancestor commit with the source task's trailer."""
    if not on_head(cfg, sha):
        raise CycleError('an adopted commit must be an ancestor of the main checkout HEAD')
    from cycle_ops import carries_trailer
    entries = list(doc.get('assignments', []))
    entries += [h['previous'] for h in doc['history'] if isinstance(h.get('previous'), dict) and 'delivery' in h['previous']]
    candidates = []
    for entry in entries:
        delivery = entry.get('delivery') or {}
        if entry.get('state') != 'finished' or delivery.get('outcome') != 'done' or sha not in delivery.get('commits', []):
            continue
        for h in doc['history']:
            if h['action'] == 'deliver' and h.get('assignment') == entry['id'] and h.get('attempt') == entry['attempt']:
                candidates.append({'sha': sha, 'source_task': entry['task'], 'pass': h['pass'], 'attempt': entry['attempt']})
    # Low-level task delivery has no host attempt; retain null rather than inventing one.
    for h in doc['history']:
        if h['action'] == 'task-updated' and h.get('state') == 'done' and sha in h.get('commits', []):
            candidates.append({'sha': sha, 'source_task': h['task'], 'pass': h['pass'], 'attempt': None})
    candidates = [row for row in candidates if carries_trailer(cfg, sha, row['source_task'])]
    if not candidates:
        raise CycleError('an adopted commit needs a Cycle-Task trailer matching a task of this cycle and its recorded delivery')
    prior = next((row for row in candidates if row['pass'] < doc['pass']), None)
    if prior is None:
        raise CycleError('an adopted commit must have been delivered in an earlier pass')
    return prior


def rotate_delivery_tokens(cfg, doc, assignment=None):
    """Resume invalidates modern open markers and retains the previous result without rewriting history."""
    for entry in doc.get('assignments', []):
        if assignment is not None and entry['id'] != assignment:
            continue
        token = entry.get('delivery_token')
        if entry['state'] not in OPEN or (not token and assignment is None):
            continue  # Records written before delivery tokens keep their original marker contract.
        if doc['status'] == 'active':
            # A host hand-back rotates without a cycle pause. If proof is unavailable,
            # rotation remains possible but dirty recovery stays on the old safe path.
            from cycle_execution import seal_pending
            try:
                seal_pending(cfg, doc, entry)
            except (CycleError, OSError):
                entry.pop('resume_seal', None)
        new_token = uuid.uuid4().hex
        from cycle_dispatch import rotate
        snapshot = rotate(cfg, doc, entry, new_token)
        source = result_file(cfg, entry['result_path'])
        retained = f"cycles/{doc['id']}/evidence/resumed-results/{entry['id']}-{entry['attempt']}-{token or 'legacy'}.md"
        target = contained(cfg.docs_root, retained)
        if source.is_symlink() or (source.exists() and not source.is_file()):
            raise CycleError('resume requires the previous result path to be a regular file or absent')
        if source.is_file():
            data = source.read_bytes()
            if target.exists() and target.read_bytes() != data:
                raise CycleError('a retained previous result already exists with different bytes')
            atomic_bytes(target, data)
            source.unlink()
        if target.is_file():
            ref = {'path': retained, 'sha256': digest(target.read_bytes())}
            entry.setdefault('previous_results', []).append(ref)
        if snapshot is not None:
            entry.setdefault('invocation_history', []).append(entry['invocation_snapshot'])
            entry['invocation_snapshot'] = snapshot
        entry['delivery_token'] = new_token


# A singleton role runs once per cycle, so its assignment id is its role name.
SINGLETON_ROLES = ('commander',)


def holder_routes(entry):
    """The routes that release a task held by an open attempt."""
    if entry.get('host'):
        return (f"Deliver its result with the typed deliver operation (assignment {entry['id']}, attempt {entry['attempt']}), "
                "or mark it lost with affirmative host evidence; dispatch nothing")
    return 'Message or await that agent, or record it lost with host evidence; dispatch nothing'


def task_holder(doc, task_id):
    """The open attempt holding a task on a version-3 record, or None."""
    if doc['schema_version'] != 3:
        return None
    return next((e for e in doc.get('assignments', []) if e['task'] == task_id and e['state'] in OPEN), None)


def describe_live(entry):
    holder = f"agent {entry['agent']}" if entry['agent'] else f"result path {entry['result_path']}"
    return f"role {entry['role']}, {holder}, started_at {entry['started_at']}, last_seen {entry['last_seen']}"


def record_assignment(cfg, doc, args):
    """Apply one assignment change; return (event fields, changed).

    `--state running` starts an id or resumes a finished or lost one as attempt N+1.
    A start is never idempotent: it refuses while the id is running, even as an
    identical replay, so a retried start can never read as permission to dispatch.
    `--seen` always advances last_seen. An identical `finished` or `lost` repeat
    writes nothing. Liveness is never inferred from time: only `--state lost`
    with a note naming host evidence ends an entry nobody finished."""
    ident, state, seen = args.get('id'), args.get('state'), args.get('seen')
    resume_token = args.get('resume_token')
    if not ident or not ident.strip():
        raise CycleError('assignment requires --id')
    if sum(bool(value) for value in (state, seen, resume_token)) != 1:
        raise CycleError('assignment takes exactly one of --state, --seen or --resume-token')
    entries = doc.setdefault('assignments', [])
    entry = next((e for e in entries if e['id'] == ident), None)
    note = args.get('note')
    if resume_token:
        if not entry or entry['state'] not in OPEN or not entry.get('host'):
            raise CycleError('--resume-token requires an open typed attempt; use prepare-dispatch for new work')
        if not _text(note):
            raise CycleError('--resume-token requires --note naming the host resumption')
        expected = entry.get('delivery_token') or 'legacy'
        if resume_token != expected:
            raise CycleError('the delivery token changed; inspect the current attempt before resuming it')
        if doc['status'] != 'active':
            raise CycleError('resume the paused cycle before resuming a host execution')
        rotate_delivery_tokens(cfg, doc, ident)
        entry['last_seen'] = now()
        return {'assignment': ident, 'attempt': entry['attempt'], 'resumed': True,
                'previous_token': expected, 'delivery_token': entry['delivery_token'], 'note': note}, True
    if state == 'running':
        role = args.get('role')
        if not role or not role.strip():
            raise CycleError('assignment --state running requires --role')
        if role in SINGLETON_ROLES and ident != role:
            raise CycleError(f'{role} is a singleton role; record its assignment under the id {role}')
        task = args.get('task')
        if task is not None and task not in {t['id'] for t in doc['plan']['tasks']}:
            raise CycleError(f'unknown task {task}')
        if entry and entry['state'] in OPEN:
            raise CycleError(f"assignment {ident} is already {entry['state']}: {describe_live(entry)}. Message or await that agent, or record it lost with host evidence; dispatch nothing")
        holding = OPEN if doc['schema_version'] == 3 else ('running',)
        holder = next((e for e in entries if task is not None and e['task'] == task and e['state'] in holding and e['id'] != ident), None)
        if holder:
            raise CycleError(f"task {task} is held by {holder['state']} assignment {holder['id']}: {describe_live(holder)}. {holder_routes(holder)}")
        at = now()
        fresh = {'id': ident, 'role': role, 'task': task, 'agent': args.get('agent'), 'result_path': args.get('result_path'),
                 'state': 'running', 'attempt': entry['attempt'] + 1 if entry else 1, 'started_at': at, 'last_seen': at, 'ended_at': None, 'note': note}
        if doc['schema_version'] == 3:
            fresh.update({key: None for key in ASSIGNMENT_V3_FIELDS})
        extra = {'assignment': ident, 'state': 'running', 'attempt': fresh['attempt']}
        if entry:
            extra['previous'] = deepcopy(entry)
            entry.clear(); entry.update(fresh)
        else:
            entries.append(fresh)
        return extra, True
    if not entry:
        raise CycleError(f'unknown assignment {ident}; start it with --state running')
    if seen:
        if entry['state'] != 'running':
            raise CycleError(f"assignment {ident} is {entry['state']}; --seen records contact with a running assignment only")
        entry['last_seen'] = now()
        if args.get('agent') is not None:
            entry['agent'] = args['agent']
        if note is not None:
            entry['note'] = note
        return {'assignment': ident, 'seen': entry['last_seen']}, True
    if state == 'lost' and not (note and note.strip()):
        raise CycleError('assignment --state lost requires --note naming the host evidence that the execution ended without a final report')
    if entry['state'] == state and (note is None or note == entry['note']):
        return {}, False
    if state == 'finished' and entry.get('host'):
        # A typed attempt ends through deliver, which checks the marker, retains the result and checks the range.
        raise CycleError(f"assignment {ident} attempt {entry['attempt']} was reserved by prepare-dispatch; record its result with the typed deliver operation, or mark it lost with host evidence")
    # A version-3 reservation is the current attempt and may be recorded lost; finished needs a running entry.
    ending = ('running', 'reserved') if state == 'lost' and doc['schema_version'] == 3 else ('running',)
    if entry['state'] not in ending:
        raise CycleError(f"assignment {ident} is {entry['state']}; only a {' or '.join(ending)} assignment can be recorded {state}")
    at = now()
    entry.update({'state': state, 'ended_at': at, 'last_seen': at})
    if note is not None:
        entry['note'] = note
    return {'assignment': ident, 'state': state, 'attempt': entry['attempt']}, True


# The actions a release cycle accepts; every other action refuses. `assignment` is record bookkeeping:
# it adds no step, phase or gate, and lets a release dispatch keep duplicate-dispatch protection.
LISTED_ACTIONS = {'task', 'completion', 'pause', 'resume', 'abandon', 'owner-complete', 'advance', 'assignment'}
LEGACY_ACTIONS = {'pause', 'reflect', 'abandon'}


def mutate(repo, identity, action, **args):
    return mutate_tracked(repo, identity, action, **args)[0]


def mutate_tracked(repo, identity, action, **args):
    """Apply an action under the lock; return (record, changed). A no-op task update writes nothing."""
    with locked(repo) as (cfg, directory):
        doc = load(repo, identity)
        extra = {}
        # One recording survives closure: an assignment's `finished`, so a final hand-back that arrives
        # after the cycle closed is still recorded. Starts, contact and `lost` stay refused.
        late_finish = action == 'assignment' and args.get('state') == 'finished' and not args.get('seen')
        if doc['status'] in CLOSED and not late_finish:
            raise CycleError('closed cycles cannot restart or mutate')
        if listed(doc) and action not in LISTED_ACTIONS:
            raise CycleError(f'{action} is not available on a release cycle: it runs one fixed task list (ADR-0163)')
        if legacy(doc) and action not in LEGACY_ACTIONS:
            raise CycleError(f'{action} is not available on a historical release cycle; it can only be paused, reflected on and abandoned')
        # A paused cycle still records that an agent reported in or ended; it starts nothing.
        ending = action == 'assignment' and args.get('state') != 'running'
        if doc['status'] == 'paused' and not ending and action not in {'resume', 'extend', 'abandon', 'reflect', 'change-type', 'owner-complete'}:
            raise CycleError('cycle is paused; resolve its blocker and resume first')
        if action == 'plan':
            if 'plan' not in phases_of(doc) or doc['phase'] not in {'plan', 'build'}:
                raise CycleError('plan revisions require the Plan or Build phase')
            plan = deepcopy(args['plan'])
            check_plan_file(plan, doc)
            for planned in plan.get('tasks', []):
                if isinstance(planned, dict) and 'phase' in planned:
                    planned['phase'] = own_phase(doc, planned['phase'])
            marked = {t['id'] for t in plan.get('tasks', []) if isinstance(t, dict) and t.get('status') == 'done'}
            replan(cfg, doc['plan'], plan)
            by_id = {t['id']: t for t in plan['tasks'] if isinstance(t, dict) and 'id' in t}
            for planned in (by_id[i] for i in marked if i in by_id):
                late = [d for d in planned.get('depends_on', []) if d in by_id and by_id[d]['status'] != 'done']
                if late:
                    raise CycleError(f"plan task {planned['id']} is done but its dependencies are not: {', '.join(late)}")
            # A recorded plan task that any attempt names stays, as recorded, so the attempt keeps its task.
            kept = next((t for t in doc['plan']['tasks'] if t['id'] == 'plan'), None)
            if 'plan' not in by_id and kept is not None and any(e.get('task') == 'plan' for e in doc.get('assignments', [])):
                plan['tasks'].insert(0, kept)
            plan['revision'] = doc['plan']['revision'] + 1
            event(doc, 'plan-revised', previous=deepcopy(doc['plan']), reason=args['reason'])
            doc['plan'] = plan
        elif action == 'plan-details':
            if doc['type'] != 'quick-fix':
                raise CycleError('plan-details is for quick-fix; other types revise the plan in the Plan or Build phase')
            if doc['phase'] not in {'build', *CHECK_PHASES}:
                raise CycleError(f"plan-details requires the Build or {phase_title(doc)} phase")
            details = args['details']
            if not isinstance(details, dict) or not details or set(details) - {'constraints', 'verification', 'streams'}:
                raise CycleError('plan details must be a non-empty object with only constraints, verification and streams')
            for key, value in details.items():
                if key == 'streams':
                    continue  # The canonical schema and validate_arrangement validate the resulting plan at save.
                if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
                    raise CycleError(f'{key} must be a non-empty list of non-empty strings')
            if not args['reason'].strip():
                raise CycleError('plan-details requires a reason')
            plan = deepcopy(doc['plan'])
            plan.update(deepcopy(details))
            plan['revision'] = doc['plan']['revision'] + 1
            event(doc, 'plan-revised', previous=deepcopy(doc['plan']), reason=args['reason'])
            doc['plan'] = plan
        elif action == 'task':
            expected = args.get('expect_revision')
            if expected is not None:
                if type(expected) is not int or expected < 1 or doc['schema_version'] != 3:
                    raise CycleError('task --expect-revision requires a positive version-three revision')
                if expected != doc['revision']:
                    raise CycleError(f'stale-revision: task expected revision {expected}, observed {doc["revision"]}; inspect before retrying')
            task = next((t for t in doc['plan']['tasks'] if t['id'] == args['task_id']), None)
            if not task:
                raise CycleError('unknown task')
            updated = updated_task(cfg, doc, task, args)
            if updated == task:
                return doc, False
            holder = task_holder(doc, task['id'])
            if holder and updated['status'] != task['status']:
                raise CycleError(f"task {task['id']} is held by {holder['state']} assignment {holder['id']}: {describe_live(holder)}. {holder_routes(holder)}")
            rerun = listed(doc) and task['status'] != 'pending' and updated['status'] == 'pending'
            task.clear()
            task.update(updated)
            if rerun:
                # A rerun resumes at this step: every later task of the fixed list waits again.
                later = doc['plan']['tasks'][[t['id'] for t in doc['plan']['tasks']].index(task['id']) + 1:]
                for other in later:
                    reopen(other)
            extra = {key: updated[key] for key in DELIVERY_FIELDS if key in updated}
            event(doc, 'task-updated', task=task['id'], state=task['status'], **extra)
            save(cfg, doc)
            return doc, True
        elif action == 'assignment':
            extra, changed = record_assignment(cfg, doc, args)
            if not changed:
                return doc, False
        elif action == 'task-add':
            task = deepcopy(args['task'])
            if 'phase' in task:
                task['phase'] = own_phase(doc, task['phase'])
            if 'fix' in task:
                check_fix_add(doc, cfg, task)
            sequence = phases_of(doc)
            if doc['type'] == 'quick-fix':
                # Quick-fix has no Plan phase: record expected evidence for the current or any later phase.
                if task['phase'] not in sequence or sequence.index(task['phase']) < sequence.index(doc['phase']):
                    raise CycleError('quick-fix adds tasks for the current or a later phase')
            elif task['phase'] != doc['phase'] and doc['phase'] != 'plan':
                raise CycleError('add tasks for the current phase or revise the plan')
            doc['plan']['tasks'].append(task)
            if 'fix' in task:
                extra = {'task': task['id'], 'fix': deepcopy(task['fix'])}
        elif action == 'withdraw-decision':
            if doc['schema_version'] != 3:
                raise CycleError('withdraw-decision needs a version-3 record')
            withdraw_decision(cfg, doc, args['name'], args['reason'], args['tasks'])
            extra = {'name': args['name'], 'tasks': list(args['tasks'])}
        elif action == 'defer' and args.get('decision') is not None:
            if doc['schema_version'] != 3:
                raise CycleError('defer needs a version-3 record')
            if args.get('finding') is not None:
                raise CycleError('defer names a finding or a withdrawn decision, not both')
            if doc['phase'] not in {'plan', 'build'}:
                raise CycleError('the work of a withdrawn decision is deferred in the Plan or Build phase')
            defer_withdrawal(cfg, doc, args['decision'], args['note'])
            extra = {'decision': args['decision']}
        elif action == 'defer':
            if doc['schema_version'] != 3:
                raise CycleError('defer needs a version-3 record')
            if args.get('finding') is None:
                raise CycleError('defer names a finding or a withdrawn decision (--finding or --decision)')
            if doc['phase'] != 'review':
                raise CycleError('a finding is deferred in Review, where its report was recorded')
            deferral = record_deferral(cfg, doc, args['finding'], args['note'])
            doc.setdefault('deferrals', []).append(deferral)
            extra = {'finding': deferral['finding']}
        elif action == 'checks' and args.get('phase') == 'build':
            if doc['phase'] != 'build':
                raise CycleError('Build checks are recorded in the Build phase')
            if len(args['checks']) != len(set(args['checks'])):
                raise CycleError('Build checks must be unique')
            doc['build_checks'] = args['checks']
        elif action == 'checks':
            doc['required_checks'] = args['checks']
        elif action == 'coverage':
            doc['coverage'] = deepcopy(args['coverage'])
            check_coverage(doc)
        elif action == 'completion':
            doc['completion'] = {key: args.get(key) for key in ('commits', 'exception', 'remaining')}
            doc['completion']['input_sha256'] = source_fingerprint(cfg.repo_root, doc)
            check_completion(cfg, doc)
        elif action == 'reduction':
            if doc['type'] != 'simplify':
                raise CycleError('the reduction record belongs to simplify cycles')
            if doc['phase'] not in CHECK_PHASES:
                raise CycleError(f"the reduction record is recorded in the {phase_title(doc)} phase")
            areas = reduction_areas(args['reduction'])
            doc['reduction'] = {'pass': doc['pass'], 'at': now(), 'input_sha256': source_fingerprint(cfg.repo_root, doc), 'areas': areas}
            extra = {'input_sha256': doc['reduction']['input_sha256'], 'changes': {name: areas[name]['change'] for name in REDUCTION_AREAS}}
        elif action == 'evidence':
            from test_evidence import digest as evidence_digest, normalize, validate_evidence
            record = validate_evidence(cfg.repo_root, args['evidence_id'], check_id=args['check_id'])
            doc['evidence'].append({'check_id': args['check_id'], 'evidence_id': args['evidence_id'], 'pass': doc['pass'], 'use': args['use'], 'declaration_sha256': evidence_digest(normalize(record['declaration']))})
        elif action == 'scrutiny':
            if args['scrutiny'] not in ('focused', 'standard', 'intensive'):
                raise CycleError('invalid scrutiny level')
            doc['review_policy'] = {key: args[key] for key in ('scrutiny', 'rationale', 'risks')}
        elif action == 'review':
            if doc['phase'] != 'review':
                raise CycleError('independent review belongs to Review')
            report = deepcopy(args['report'])
            if report.get('scope') is None:
                report['scope'] = list(doc['plan']['scope'])
            fix_task = None
            if 'fix_task' in report:
                fix_task = next((t for t in doc['plan']['tasks'] if t['id'] == report['fix_task'] and 'fix' in t and t['phase'] == 'review' and t['fix']['pass'] == doc['pass']), None) if _text(report['fix_task']) else None
                if not fix_task:
                    raise CycleError("fix_task must name this pass's review-phase fix task")
                if not fix_task.get('commits'):
                    raise CycleError('the fix task needs a recorded commit before its diff is reviewed')
            for previous in doc['reviews']:
                prior = read_retained(cfg, previous)
                if prior['pass'] == doc['pass'] and (prior['verdict'] == 'changes-required' or prior['blocking']):
                    # The one blocking report the fix answers does not bar its fix-diff review; a blocking fix-diff review does.
                    if fix_task and not prior.get('fix_task'):
                        continue
                    raise CycleError('blocking review findings require a counted return before another review')
            if fix_task and fix_task['fix'].get('review'):
                raise CycleError('the fix task already has its fix-diff review')
            needed = {'reviewer', 'scope', 'evidence', 'blocking', 'advisory', 'cosmetic', 'verdict', 'rationale'}
            if set(report) - {'fix_task'} != needed or not report['reviewer'].strip() or report['reviewer'] in doc['implementers']:
                raise CycleError('review must identify an independent reviewer and all report fields')
            if fix_task and report['reviewer'] == fix_task.get('assignee'):
                raise CycleError('the fix-diff reviewer cannot be the fix assignee')
            if not report['scope'] or set(report['scope']) != set(doc['plan']['scope']) or not report['evidence'] or not report['rationale'].strip():
                raise CycleError('review scope must equal the declared scope exactly, and the review must identify evidence and rationale')
            check_tests(cfg, doc)
            if report['verdict'] not in {'approve', 'changes-required'} or not all(isinstance(report[k], list) for k in ('scope', 'evidence', 'blocking', 'advisory', 'cosmetic')):
                raise CycleError('invalid review report')
            for finding in report['blocking']:
                if not isinstance(finding, dict) or not all(finding.get(k) for k in ('path', 'consequence', 'evidence')):
                    raise CycleError('blocking findings require path, consequence, and evidence')
            report.update({'pass': doc['pass'], 'scrutiny': doc['review_policy']['scrutiny'], 'input_sha256': source_fingerprint(cfg.repo_root, doc), 'basis_version': BASIS_VERSION, 'basis_sha256': review_basis(doc), 'at': now()})
            doc['reviews'].append(retained(cfg, identity, 'reviews', report))
            if fix_task:
                fix_task['fix']['review'] = dict(doc['reviews'][-1])
        elif action == 'decision':
            if doc['phase'] not in {'plan', 'build'}:
                raise CycleError('new implementation reasoning requires planning before dependent work')
            if doc['type'] == 'quick-fix':
                raise CycleError('material decisions require changing quick-fix to another type')
            if args['kind'] not in {'idr', 'adr'}:
                raise CycleError('decision must be idr or adr')
            contents = deepcopy(args['contents'])
            if args['kind'] == 'idr':
                for key in ('alternatives', 'approach', 'assumptions', 'constraints', 'intended_evidence'):
                    if not contents.get(key):
                        raise CycleError(f'IDR requires {key}')
                check_replaces(cfg, doc, args['name'], contents)
            else:
                raise CycleError('create ADRs through decision-policy propose --origin cycle')
                if not args.get('creation_approval') or not args.get('creation_subject'):
                    raise CycleError('cycle ADR creation requires prior council justification')
                from cycle_council import validate_approval
                validate_approval(cfg.repo_root, args['creation_approval'], purpose='adr-creation', subject=args['creation_subject'])
            name = args['name']
            record = {'cycle_id': identity, 'kind': args['kind'], 'name': name, 'revision': 1 + sum(d['name'] == name for d in doc['decisions']), 'contents': contents, 'at': now()}
            ref = retained(cfg, identity, 'decisions', record)
            doc['decisions'].append({**ref, 'kind': args['kind'], 'name': name, 'approval': None, 'accepted': False})
        elif action == 'approve-decision':
            target = next((d for d in doc['decisions'] if d['path'] == args['subject']), None)
            if not target:
                raise CycleError('subject is not a retained cycle decision')
            if target['name'] in withdrawn_names(doc):
                raise CycleError(f"IDR {target['name']} was withdrawn and takes no approval")
            approval_data = json.loads(contained(cfg.docs_root, args['approval']).read_text())
            if isinstance(approval_data, dict) and approval_data.get('format') == 'crux.owner-decision-capture.v1':
                raise CycleError('use owner-decision apply for conversational evidence')
            from cycle_council import validate_approval
            validate_approval(cfg.repo_root, args['approval'], purpose=target['kind'], subject=target['path'])
            target['approval'] = args['approval']
            if target['kind'] == 'adr':
                raise CycleError('use decision-policy accept for ADR acceptance')
        elif action == 'pause':
            if not args['reason'].strip():
                raise CycleError('pause requires a blocker')
            from cycle_execution import seal_pending
            for entry in doc.get('assignments', []):
                try:
                    seal_pending(cfg, doc, entry)
                except (CycleError, OSError):
                    # Pausing still works when sealing is unavailable; no dirty
                    # continuation is granted without its complete proof.
                    entry.pop('resume_seal', None)
            doc['status'] = 'paused'
            doc['blocker'] = {'reason': args['reason'], 'evidence': args.get('evidence', []), 'next_step': args.get('next_step', 'resolve blocker')}
        elif action == 'resume':
            if doc['status'] != 'paused' or not args['reason'].strip():
                raise CycleError('resume requires a paused cycle and resolution')
            blocker = doc['blocker'] or {}
            if blocker.get('reason') in {'pass-limit', 'progress-stalled'}:
                if doc['pass'] >= doc['pass_limit']:
                    raise CycleError('approve an additional pass before resuming this return')
                if blocker['reason'] == 'progress-stalled' and not args.get('new_evidence'):
                    raise CycleError('stalled progress requires new evidence before resuming')
                doc['pass'] += 1
                doc['phase'] = 'build'
                start_pass(cfg, doc)
            rotate_delivery_tokens(cfg, doc)
            doc['status'] = 'active'
            doc['blocker'] = None
        elif action == 'extend':
            if not args['human_approval'].strip() or args['limit'] <= doc['pass_limit']:
                raise CycleError('raising a limit requires explicit human approval and a higher limit')
            doc['extensions'].append({'at': now(), 'from': doc['pass_limit'], 'to': args['limit'], 'human_approval': args['human_approval']})
            doc['pass_limit'] = args['limit']
        elif action == 'return':
            if doc['phase'] not in {*CHECK_PHASES, 'review'}:
                raise CycleError('only testing or review findings return a cycle')
            assessment = {k: args[k] for k in ('improved', 'unresolved', 'next_change', 'justification')}
            if not all(isinstance(v, str) and v.strip() for v in assessment.values()):
                raise CycleError('return requires progress, remaining work, next change, and justification')
            event(doc, 'return-requested', assessment=assessment, plan=deepcopy(doc['plan']))
            if not args['progress'] or doc['pass'] >= doc['pass_limit']:
                doc['status'] = 'paused'
                doc['blocker'] = {'reason': 'progress-stalled' if not args['progress'] else 'pass-limit', 'evidence': [assessment], 'next_step': 'reassess stalled work or request explicit approval for additional passes'}
            else:
                doc['pass'] += 1
                doc['phase'] = 'build'
                start_pass(cfg, doc)
        elif action == 'change-type':
            kind = args['kind']
            if kind not in PHASES or kind == 'release' or not args['reason'].strip():
                raise CycleError('valid type and reason required; a release cycle is created with its list, never changed into')
            if kind == doc['type']:
                raise CycleError('type is unchanged')
            if doc['type'] == 'simplify' and not args.get('human_approval'):
                raise CycleError('changing a simplify cycle to another type requires explicit human approval, so it never silently becomes another type')
            if doc['phase'] in {*CHECK_PHASES, 'review', 'reflect'} and (not doc['blocker'] or doc['blocker']['reason'] not in {'pass-limit', 'progress-stalled'}):
                raise CycleError('record a counted return before changing type after testing or review, including paused work')
            if doc['blocker'] and doc['blocker']['reason'] == 'pass-limit' and not args.get('human_approval'):
                raise CycleError('changing type cannot bypass an exhausted limit without human approval')
            old = doc['type']
            if doc['pass'] >= doc['pass_limit'] and doc['phase'] in {*CHECK_PHASES, 'review'} and not args.get('human_approval'):
                raise CycleError('changing type after the final attempt requires explicit human approval')
            limit = max(LIMITS[kind], doc['pass'])
            if doc['extensions']:
                limit = max(limit, doc['pass_limit'])
            doc['type'], doc['pass_limit'], doc['phase'] = kind, limit, PHASES[kind][0]
            event(doc, 'type-changed', previous_type=old, reason=args['reason'], previous_plan=deepcopy(doc['plan']), human_approval=args.get('human_approval'))
            doc['plan']['tasks'] = []
            if PHASES[kind][0] == 'plan':
                doc['plan']['tasks'].append(dict(SEEDED_PLAN_TASK, depends_on=[], expected_evidence=list(SEEDED_PLAN_TASK['expected_evidence'])))
        elif action == 'reflect':
            if doc['phase'] != 'reflect' and doc['status'] != 'paused':
                raise CycleError('reflection belongs to Reflect or abandonment')
            if not args['reflection'].get('outcome'):
                raise CycleError('reflection requires outcome, lessons, and remaining work (use none when empty)')
            for field in ('lessons', 'remaining'):
                items = args['reflection'].get(field)
                if not (isinstance(items, list) and items and all(isinstance(i, str) and i.strip() for i in items)):
                    raise CycleError(f'reflection {field} must be a non-empty list of non-empty strings (use ["none"] when there is nothing)')
            doc['reflection'] = args['reflection']
        elif action == 'owner-complete':
            # The owner closes a cycle whose gates cannot be satisfied. Nothing
            # recorded is rewritten: blocker, evidence, reviews, release and
            # reflection stay as they are. The history event carries the
            # owner's verbatim words and fingerprints of the cited authority.
            extra = {'owner': owner_authorization(cfg, args['owner'])}
            doc['status'] = 'completed'
        elif action == 'abandon':
            if not doc['reflection'] and not listed(doc):
                raise CycleError('abandonment requires reflection')
            doc['status'] = 'abandoned'
        elif action == 'advance':
            # One policy: the requirements the typed operations read, first unmet item raised.
            first_unmet(cfg, doc)
            if listed(doc) or doc['phase'] == 'reflect':
                doc['status'] = 'completed'
            else:
                doc['phase'] = phases_of(doc)[phases_of(doc).index(doc['phase']) + 1]
        else:
            raise CycleError('unknown cycle action')
        event(doc, action, **({'reason': args['reason']} if 'reason' in args else {}), **extra)
        save(cfg, doc)
        return doc, True


OWNER_COMPLETION_FIELDS = {'origin', 'quote', 'date', 'conversation', 'authority'}
OWNER_REQUIRED_FIELDS = OWNER_COMPLETION_FIELDS - {'authority'}
# How many files under a directory reference a refusal lists as candidate repair values.
CANDIDATE_LIMIT = 20


def path_class(full: Path, root: Path):
    """None for a readable regular file under `root`, reached through no symlink; otherwise (code suffix, problem)."""
    try:
        relative = full.relative_to(root)
    except ValueError:
        return 'outside-repository', 'is outside the repository'
    probe = root
    for part in relative.parts:
        probe = probe / part
        if probe.is_symlink():
            return 'symlink', 'passes through a symlink'
    if not full.exists():
        return 'missing', 'does not exist'
    if full.is_dir():
        return 'is-directory', 'is a directory, not a file'
    if not full.is_file():
        return 'not-regular', 'is not a regular file'
    if not os.access(full, os.R_OK):
        return 'unreadable', 'is not readable'
    return None


def directory_candidates(root: Path, directory: Path, limit=CANDIDATE_LIMIT):
    """Up to `limit` regular files under a directory, repository-relative and sorted, as repair candidates."""
    found = []
    for path in sorted(directory.rglob('*')):
        if len(found) >= limit:
            break
        if path.is_file() and not any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root) and p != root):
            found.append(path.relative_to(root).as_posix())
    return found


def check_references(cfg, names):
    """Validate owner references: repository-relative regular files.

    Returns (refs, problems). refs are {path, sha256}; each problem is {code, name, problem, candidates},
    with code `reference-<class>`. A directory lists up to twenty files under it as candidates.
    Owner-complete and the typed owner-exception share this validator."""
    root = cfg.repo_root.resolve()
    refs, problems = [], []
    for name in names:
        if not isinstance(name, str) or not name.strip():
            problems.append({'code': 'reference-invalid', 'name': name, 'problem': 'a reference is a non-empty repository-relative path', 'candidates': []})
            continue
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or not path.parts:
            problems.append({'code': 'reference-outside-repository', 'name': name,
                             'problem': f'reference {name}: path must be relative and contain no parent segments', 'candidates': []})
            continue
        full = root / path
        found = path_class(full, root)
        if found is None:
            refs.append({'path': name, 'sha256': digest(full.read_bytes())})
            continue
        code, text = found
        candidates = directory_candidates(root, full) if code == 'is-directory' else []
        problem = f'reference {name} {text}'
        if code == 'missing':
            problem = f'authority file does not exist: {name}'
        if candidates:
            problem += '; name one of its files instead, or omit the reference: ' + ', '.join(candidates)
        problems.append({'code': f'reference-{code}', 'name': name, 'problem': problem, 'candidates': candidates})
    return refs, problems


def owner_authorization(cfg, owner):
    """Validate an owner's completion authorization; never synthesized without a quote.

    `authority` is optional: an owner instruction needs no cited file, and an agent must
    not invent one. Each given reference must be a regular file; a directory is refused
    `reference-is-directory` with the files under it as candidates."""
    if not isinstance(owner, dict) or not OWNER_REQUIRED_FIELDS <= set(owner) <= OWNER_COMPLETION_FIELDS:
        raise CycleError('owner authorization must carry exactly: ' + ', '.join(sorted(OWNER_REQUIRED_FIELDS)) + ', and optionally authority')
    if owner['origin'] != 'owner-conversation':
        raise CycleError('owner authorization requires origin owner-conversation')
    for key in ('quote', 'conversation'):
        if not isinstance(owner[key], str) or not owner[key].strip():
            raise CycleError(f'owner authorization requires a non-empty verbatim {key}')
    if not isinstance(owner['date'], str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', owner['date']):
        raise CycleError('owner authorization date must be YYYY-MM-DD')
    names = owner.get('authority', [])
    if not isinstance(names, list):
        raise CycleError('authority is a list of repository-relative file paths')
    if not all(isinstance(name, str) for name in names):
        raise CycleError('authority entries are repository-relative paths')
    refs, problems = check_references(cfg, names)
    if problems:
        raise CycleError('; '.join(f"{p['code']}: {p['problem']}" for p in problems))
    return {**deepcopy(owner), 'authority': refs}


def query_decisions(repo, identity):
    """Separate approved intent, reviewed delivery evidence, and current source."""
    cfg=tree(repo);doc=load(repo,identity)
    current=source_fingerprint(cfg.repo_root,doc)
    current_review=None
    try:
        check_tests(cfg,doc)
        current_review=check_review(cfg,doc)
    except (CycleError,OSError,ValueError):
        pass
    rows=[]
    for ref in doc['decisions']:
        if ref['kind']!='idr':continue
        record=read_retained(cfg,ref)
        approved=False
        if ref.get('approval'):
            try:
                from cycle_council import validate_approval
                validate_approval(repo,ref['approval'],purpose='idr',subject=ref['path'])
                approved=True
            except (CycleError,OSError,ValueError):pass
        reviews=[]
        for report in doc['reviews']:
            value=read_retained(cfg,report)
            if value['verdict']=='approve' and not value['blocking'] and value['reviewer'] not in doc['implementers']:
                reviews.append({'report':report['path'],'input_sha256':value['input_sha256'],'pass':value['pass'],'matches_current_source':fingerprint_binds(cfg.repo_root,doc,value['input_sha256']),'matches_current':value==current_review})
        rows.append({'decision':ref['path'],'name':ref['name'],'revision':record['revision'],'intent':record['contents'],
                     'council_approved':approved,'approval':ref.get('approval'),
                     'delivery':{'cycle_status':doc['status'],'reviewed_evidence':reviews,'test_evidence':doc['evidence']},
                     'current_source':{'scope':doc['plan']['scope'],'sha256':current,'implementation_claim':'Review and tests establish their declared coverage; intent alone proves no implementation.'}})
    return {'cycle_id':identity,'decisions':rows}


def covered_path(root, path, patterns):
    for pattern in patterns:
        contained(root,pattern)
        for match in root.glob(pattern):
            if match == path or (match.is_dir() and path.is_relative_to(match)):
                return True
    return False
