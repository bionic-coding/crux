"""Schema-backed, single-undertaking cycles. Historical promptbook readers are unchanged."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid

from bionic_config import load_config, load_workflow_policy, require_schema_version

PHASES = {
    'dev': ['plan', 'build', 'test', 'review', 'reflect'],
    'iterate': ['plan', 'build', 'test', 'review', 'reflect'],
    'refactor': ['plan', 'build', 'test', 'review', 'reflect'],
    'quick-fix': ['build', 'test', 'review', 'reflect'],
    'release': ['plan', 'release', 'reflect'],
}
LIMITS = {'dev': 7, 'iterate': 2, 'refactor': 7, 'quick-fix': 1, 'release': 2}
ID = re.compile(r'^(?:[A-Z][A-Z0-9]{1,9}-)?CYC-[0-9]{4,}$')
CLOSED = {'completed', 'abandoned'}


class CycleError(ValueError):
    pass


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
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.cycle-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded(value))
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


@contextmanager
def locked(repo):
    cfg = tree(repo)
    directory = contained(cfg.docs_root, 'cycles')
    directory.mkdir(exist_ok=True)
    lock = contained(directory, '.lock')
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield cfg, directory


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
    if doc['phase'] not in PHASES[doc['type']]:
        raise CycleError('phase is incompatible with cycle type')
    if doc['pass'] > doc['pass_limit']:
        raise CycleError('pass exceeds approved limit')
    if any(scope.startswith(':') for scope in doc['plan']['scope']):
        raise CycleError('scope cannot use git pathspec magic')
    task_ids = [task['id'] for task in doc['plan']['tasks']]
    if len(task_ids) != len(set(task_ids)):
        raise CycleError('task ids must be unique')
    for task in doc['plan']['tasks']:
        if task['phase'] not in PHASES[doc['type']] or any(dep not in task_ids or dep == task['id'] for dep in task['depends_on']):
            raise CycleError('task phase or dependency is invalid')
    graph = {t['id']: t['depends_on'] for t in doc['plan']['tasks']}
    def visit(node, visiting):
        if node in visiting:
            raise CycleError('task dependencies contain a cycle')
        for dependency in graph[node]:
            visit(dependency, visiting | {node})
    for node in graph:
        visit(node, set())
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


def save(cfg, doc):
    validate(doc)
    atomic(contained(cfg.docs_root, f"cycles/{doc['id']}/cycle.json"), doc)


def event(doc, action, **fields):
    doc['history'].append({'at': now(), 'action': action, 'pass': doc['pass'], 'phase': doc['phase'], **fields})
    doc['updated_at'] = now()


def create(repo, kind, title, goal, scope, acceptance, implementer, coordinator):
    if kind not in PHASES or not all((title.strip(), goal.strip(), scope, acceptance, implementer.strip(), coordinator.strip())):
        raise CycleError('type, title, goal, scope, acceptance, implementer and coordinator are required')
    with locked(repo) as (cfg, directory):
        for name in scope:
            contained(cfg.repo_root, name)
        used = [int(match.group(1)) for path in directory.iterdir()
                if (match := re.search(r'CYC-([0-9]+)$', path.name))]
        identity = f"{cfg.artifact_prefix + '-' if cfg.artifact_prefix else ''}CYC-{max(used, default=0) + 1:04d}"
        policy = load_workflow_policy(repo)
        doc = {
            'schema_version': 2, 'id': identity, 'title': title, 'type': kind, 'goal': goal,
            'status': 'active', 'phase': PHASES[kind][0], 'pass': 1, 'pass_limit': LIMITS[kind],
            'created_at': now(), 'updated_at': now(), 'implementers': [implementer], 'coordinator': coordinator,
            'plan': {'revision': 1, 'scope': scope, 'constraints': [], 'acceptance': acceptance, 'verification': [], 'tasks': []},
            'review_policy': {'scrutiny': policy['review.scrutiny'], 'rationale': 'repository default', 'risks': []},
            'required_checks': [], 'evidence': [], 'decisions': [], 'reviews': [], 'history': [],
            'reflection': None, 'blocker': None, 'extensions': [], 'release': None,
            'coverage': None, 'completion': None,
        }
        event(doc, 'created')
        # Allocate the directory before writing; an interrupted allocation is never reused.
        contained(directory, identity).mkdir()
        save(cfg, doc)
        return doc


def source_fingerprint(repo, doc):
    """Fingerprint declared review scope, actual dirty bytes, names and deletions."""
    repo = Path(repo).resolve()
    rows = {}
    cfg = tree(repo)
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
    return digest(encoded(rows))


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


def approvals(cfg, doc, kind):
    approved = []
    for decision in doc['decisions']:
        if decision['kind'] != kind:
            continue
        subject = read_retained(cfg, decision)
        if not decision.get('approval'):
            continue
        from cycle_council import validate_approval
        validate_approval(cfg.repo_root, decision['approval'], purpose=kind, subject=decision['path'])
        approved.append(subject)
    return approved


def check_decisions(cfg, doc):
    required = doc['type'] == 'dev' or any(d['kind'] == 'idr' for d in doc['decisions'])
    if required and not approvals(cfg, doc, 'idr'):
        raise CycleError('council approval of an exact IDR revision is required before dependent work')
    for decision in doc['decisions']:
        if decision['kind'] == 'adr':
            if not decision.get('accepted'):
                raise CycleError('an ADR dependency is awaiting acceptance')
            from decision_policy import validate_acceptance
            validate_acceptance(cfg, decision)
    # Every retained IDR revision marked current requires its own approval.
    current = {}
    for decision in doc['decisions']:
        if decision['kind'] == 'idr':
            current[decision['name']] = decision
    for decision in current.values():
        if not decision.get('approval'):
            raise CycleError('the current IDR revision is not approved')
        from cycle_council import validate_approval
        validate_approval(cfg.repo_root, decision['approval'], purpose='idr', subject=decision['path'])


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


def completion_paths(cfg, doc):
    # The record cannot contain the SHA of its own final commit. All other scope
    # must be committed; the conductor commits final cycle bookkeeping afterward.
    own = (cfg.docs_root / 'cycles' / doc['id']).relative_to(cfg.repo_root).as_posix()
    lock = (cfg.docs_root / 'cycles/.lock').relative_to(cfg.repo_root).as_posix()
    return [*doc['plan']['scope'], f':(exclude){own}/**', f':(exclude){lock}']


def check_completion(cfg, doc):
    if doc['schema_version'] == 1:
        return
    record = doc.get('completion')
    if not record:
        raise CycleError('record completion commits or an explicit user-request exception')
    if record['input_sha256'] != source_fingerprint(cfg.repo_root, doc):
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
        result = subprocess.run(['git', '-C', str(cfg.repo_root), *args], capture_output=True, text=True)
        if result.returncode:
            raise CycleError('completion commit must exist in this repository and be an ancestor of HEAD')
        return result.stdout.strip()
    for sha in commits:
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', sha):
            raise CycleError('completion requires full commit SHAs')
        git('rev-parse', '--verify', sha + '^{commit}')
        git('merge-base', '--is-ancestor', sha, 'HEAD')
    # Check committed and staged/unstaged changes, as well as new scoped files.
    # git pathspecs handle declared globs; user scope cannot add exclusion magic.
    paths = completion_paths(cfg, doc)
    changed = git('diff', '--name-only', commits[-1], '--', *paths)
    staged = git('diff', '--cached', '--name-only', 'HEAD', '--', *paths)
    unstaged = git('diff', '--name-only', '--', *paths)
    untracked = '\n'.join(path for path in git('ls-files', '--others', '--', *paths).splitlines() if '__pycache__' not in Path(path).parts)
    if changed or staged or unstaged or untracked:
        raise CycleError('uncommitted or later scope changes are missing from the completion commit')


def check_tests(cfg, doc):
    check_coverage(doc)
    if not doc['required_checks']:
        raise CycleError('declare at least one required check (focused verification is sufficient)')
    from test_evidence import validate_evidence
    for check in doc['required_checks']:
        matching = [ref for ref in doc['evidence'] if ref['check_id'] == check and ref['pass'] == doc['pass']]
        if not matching:
            raise CycleError(f'missing passing evidence for {check}')
        try:
            validate_evidence(cfg.repo_root, matching[-1]['evidence_id'], check_id=check)
        except ValueError as exc:
            raise CycleError(f'invalid evidence for {check}: {exc}') from exc


BASIS_VERSION = 2


def review_bearing_phase(kind):
    """The phase whose gate binds a review: Release when the type has one, else Review."""
    return 'release' if 'release' in PHASES[kind] else 'review'


def review_basis_digest(doc, version):
    """Digest what an independent reviewer approved.

    Version 1 hashes the whole plan. Version 2 omits plan tasks of phases after
    the review-bearing phase (Reflect today), so reflection bookkeeping added
    after approval keeps the binding. Task status, reflection, completion,
    history, blocker and status are never part of the basis.
    """
    plan = deepcopy(doc['plan'])
    if version == 2:
        sequence = PHASES[doc['type']]
        cutoff = sequence.index(review_bearing_phase(doc['type']))
        plan['tasks'] = [task for task in plan['tasks'] if sequence.index(task['phase']) <= cutoff]
    elif version != 1:
        raise CycleError('unknown review basis version')
    for task in plan['tasks']:
        task.pop('status', None)
    basis = {'plan': plan, 'required_checks': doc['required_checks'], 'review_policy': doc['review_policy'], 'evidence': [ref for ref in doc['evidence'] if ref['pass'] == doc['pass']]}
    if doc['schema_version'] >= 2:
        basis['coverage'] = doc['coverage']
    return digest(encoded(basis))


def review_basis_v1(doc):
    """The original whole-plan basis, kept to bind reports recorded before versioning."""
    return review_basis_digest(doc, 1)


def review_basis(doc):
    """The current basis (version 2), recorded in new reports."""
    return review_basis_digest(doc, BASIS_VERSION)


def basis_binds(report, v1, v2):
    """Whether a stored report's basis matches the current record.

    A versioned report binds only to its own version. An unversioned (legacy)
    report binds to the version-1 or the version-2 digest. An unknown version
    never binds.
    """
    stored = report.get('basis_sha256')
    version = report.get('basis_version')
    if version is None:
        return stored in (v1, v2)
    if type(version) is int and version in (1, 2):
        return stored == (v1 if version == 1 else v2)
    return False


def check_review(cfg, doc):
    fingerprint = source_fingerprint(cfg.repo_root, doc)
    v1, v2 = review_basis_v1(doc), review_basis(doc)
    for ref in reversed(doc['reviews']):
        report = read_retained(cfg, ref)
        if report['pass'] != doc['pass'] or report['input_sha256'] != fingerprint or not basis_binds(report, v1, v2):
            continue
        if report['reviewer'] in doc['implementers']:
            continue
        if report['verdict'] == 'approve' and not report['blocking']:
            return report
        raise CycleError('blocking review findings require returning through the cycle')
    raise CycleError('a passing independent review of the current scope is required')


def mutate(repo, identity, action, **args):
    with locked(repo) as (cfg, directory):
        doc = load(repo, identity)
        if doc['status'] in CLOSED:
            raise CycleError('closed cycles cannot restart or mutate')
        if doc['status'] == 'paused' and action not in {'resume', 'extend', 'abandon', 'reflect', 'change-type'}:
            raise CycleError('cycle is paused; resolve its blocker and resume first')
        if action == 'plan':
            if doc['phase'] != 'plan':
                raise CycleError('plan revisions require the Plan phase')
            plan = deepcopy(args['plan'])
            plan['revision'] = doc['plan']['revision'] + 1
            event(doc, 'plan-revised', previous=deepcopy(doc['plan']), reason=args['reason'])
            doc['plan'] = plan
        elif action == 'plan-details':
            if doc['type'] != 'quick-fix':
                raise CycleError('plan-details is for quick-fix; other types revise the plan in the Plan phase')
            if doc['phase'] not in {'build', 'test'}:
                raise CycleError('plan-details requires the Build or Test phase')
            details = args['details']
            if not isinstance(details, dict) or not details or set(details) - {'constraints', 'verification'}:
                raise CycleError('plan details must be a non-empty object with only constraints and verification')
            for key, value in details.items():
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
            task = next((t for t in doc['plan']['tasks'] if t['id'] == args['task_id']), None)
            if not task:
                raise CycleError('unknown task')
            if args['state'] == 'done' and any(t['status'] != 'done' for t in doc['plan']['tasks'] if t['id'] in task['depends_on']):
                raise CycleError('task dependencies are incomplete')
            task['status'] = args['state']
            event(doc, 'task-updated', task=task['id'], state=args['state'])
        elif action == 'task-add':
            task = deepcopy(args['task'])
            sequence = PHASES[doc['type']]
            if doc['type'] == 'quick-fix':
                # Quick-fix has no Plan phase: record expected evidence for the current or any later phase.
                if task['phase'] not in sequence or sequence.index(task['phase']) < sequence.index(doc['phase']):
                    raise CycleError('quick-fix adds tasks for the current or a later phase')
            elif task['phase'] != doc['phase'] and doc['phase'] != 'plan':
                raise CycleError('add tasks for the current phase or revise the plan')
            doc['plan']['tasks'].append(task)
        elif action == 'checks':
            doc['required_checks'] = args['checks']
        elif action == 'coverage':
            doc['coverage'] = deepcopy(args['coverage'])
            check_coverage(doc)
        elif action == 'completion':
            doc['completion'] = {key: args.get(key) for key in ('commits', 'exception', 'remaining')}
            doc['completion']['input_sha256'] = source_fingerprint(cfg.repo_root, doc)
            check_completion(cfg, doc)
        elif action == 'evidence':
            from test_evidence import validate_evidence
            validate_evidence(cfg.repo_root, args['evidence_id'], check_id=args['check_id'])
            doc['evidence'].append({'check_id': args['check_id'], 'evidence_id': args['evidence_id'], 'pass': doc['pass'], 'use': args['use']})
        elif action == 'scrutiny':
            if args['scrutiny'] not in ('focused', 'standard', 'intensive'):
                raise CycleError('invalid scrutiny level')
            doc['review_policy'] = {key: args[key] for key in ('scrutiny', 'rationale', 'risks')}
        elif action == 'review':
            if doc['phase'] not in {'review', 'release'}:
                raise CycleError('independent review belongs to Review or Release')
            for previous in doc['reviews']:
                prior = read_retained(cfg, previous)
                if prior['pass'] == doc['pass'] and (prior['verdict'] == 'changes-required' or prior['blocking']):
                    raise CycleError('blocking review findings require a counted return before another review')
            report = deepcopy(args['report'])
            needed = {'reviewer', 'scope', 'evidence', 'blocking', 'advisory', 'cosmetic', 'verdict', 'rationale'}
            if set(report) != needed or not report['reviewer'].strip() or report['reviewer'] in doc['implementers']:
                raise CycleError('review must identify an independent reviewer and all report fields')
            if not report['scope'] or set(report['scope']) != set(doc['plan']['scope']) or not report['evidence'] or not report['rationale'].strip():
                raise CycleError('review scope must cover the declared scope and identify evidence and rationale')
            check_tests(cfg, doc)
            if report['verdict'] not in {'approve', 'changes-required'} or not all(isinstance(report[k], list) for k in ('scope', 'evidence', 'blocking', 'advisory', 'cosmetic')):
                raise CycleError('invalid review report')
            for finding in report['blocking']:
                if not isinstance(finding, dict) or not all(finding.get(k) for k in ('path', 'consequence', 'evidence')):
                    raise CycleError('blocking findings require path, consequence, and evidence')
            report.update({'pass': doc['pass'], 'scrutiny': doc['review_policy']['scrutiny'], 'input_sha256': source_fingerprint(cfg.repo_root, doc), 'basis_version': BASIS_VERSION, 'basis_sha256': review_basis(doc), 'at': now()})
            doc['reviews'].append(retained(cfg, identity, 'reviews', report))
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
            from cycle_council import validate_approval
            validate_approval(cfg.repo_root, args['approval'], purpose=target['kind'], subject=target['path'])
            target['approval'] = args['approval']
            if target['kind'] == 'adr':
                raise CycleError('use decision-policy accept for ADR acceptance')
        elif action == 'pause':
            if not args['reason'].strip():
                raise CycleError('pause requires a blocker')
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
                doc['phase'] = 'build' if doc['type'] == 'quick-fix' else 'plan'
                for task in doc['plan']['tasks']:
                    task['status'] = 'pending'
                doc['plan']['revision'] += 1
            doc['status'] = 'active'
            doc['blocker'] = None
        elif action == 'extend':
            if not args['human_approval'].strip() or args['limit'] <= doc['pass_limit']:
                raise CycleError('raising a limit requires explicit human approval and a higher limit')
            doc['extensions'].append({'at': now(), 'from': doc['pass_limit'], 'to': args['limit'], 'human_approval': args['human_approval']})
            doc['pass_limit'] = args['limit']
        elif action == 'return':
            if doc['phase'] not in {'test', 'review', 'release'}:
                raise CycleError('only testing, review, or release findings return a cycle')
            assessment = {k: args[k] for k in ('improved', 'unresolved', 'next_change', 'justification')}
            if not all(isinstance(v, str) and v.strip() for v in assessment.values()):
                raise CycleError('return requires progress, remaining work, next change, and justification')
            event(doc, 'return-requested', assessment=assessment, plan=deepcopy(doc['plan']), release=deepcopy(doc['release']))
            if not args['progress'] or doc['pass'] >= doc['pass_limit']:
                doc['status'] = 'paused'
                doc['blocker'] = {'reason': 'progress-stalled' if not args['progress'] else 'pass-limit', 'evidence': [assessment], 'next_step': 'reassess stalled work or request explicit approval for additional passes'}
            else:
                doc['pass'] += 1
                doc['phase'] = 'build' if doc['type'] == 'quick-fix' else 'plan'
                for task in doc['plan']['tasks']:
                    task['status'] = 'pending'
                doc['plan']['revision'] += 1
        elif action == 'change-type':
            kind = args['kind']
            if kind not in PHASES or not args['reason'].strip():
                raise CycleError('valid type and reason required')
            if kind == doc['type']:
                raise CycleError('type is unchanged')
            if doc['phase'] in {'test', 'review', 'release', 'reflect'} and (not doc['blocker'] or doc['blocker']['reason'] not in {'pass-limit', 'progress-stalled'}):
                raise CycleError('record a counted return before changing type after testing or review, including paused work')
            if doc['blocker'] and doc['blocker']['reason'] == 'pass-limit' and not args.get('human_approval'):
                raise CycleError('changing type cannot bypass an exhausted limit without human approval')
            old = doc['type']
            if doc['pass'] >= doc['pass_limit'] and doc['phase'] in {'test', 'review', 'release'} and not args.get('human_approval'):
                raise CycleError('changing type after the final attempt requires explicit human approval')
            limit = max(LIMITS[kind], doc['pass'])
            if doc['extensions']:
                limit = max(limit, doc['pass_limit'])
            doc['type'], doc['pass_limit'], doc['phase'] = kind, limit, PHASES[kind][0]
            event(doc, 'type-changed', previous_type=old, reason=args['reason'], previous_plan=deepcopy(doc['plan']), human_approval=args.get('human_approval'))
            doc['plan']['tasks'] = []
        elif action == 'release-ready':
            if doc['type'] != 'release' or doc['phase'] != 'release':
                raise CycleError('release preparation requires the Release phase')
            check_decisions(cfg, doc)
            check_tests(cfg, doc)
            check_review(cfg, doc)
            if not args['authorization'].strip() or not args['destinations'] or not args['artifacts']:
                raise CycleError('publication requires exact destinations, artifacts, and authorization')
            artifacts = []
            from test_evidence import validate_evidence
            test_records = [validate_evidence(cfg.repo_root, ref['evidence_id'], check_id=ref['check_id']) for ref in doc['evidence'] if ref['pass'] == doc['pass']]
            for name in args['artifacts']:
                path = contained(cfg.repo_root, name)
                if not covered_path(cfg.repo_root, path, doc['plan']['scope']):
                    raise CycleError('release artifact lies outside the reviewed scope')
                if not any(row['snapshot']['inputs'].get(path.relative_to(cfg.repo_root).as_posix(), {}).get('sha256') == digest(path.read_bytes()) for row in test_records):
                    raise CycleError('release artifact lacks matching packaging or installation evidence')
                artifacts.append({'path': name, 'sha256': digest(path.read_bytes())})
            doc['release'] = {'authorization': args['authorization'], 'destinations': args['destinations'], 'artifacts': artifacts, 'input_sha256': source_fingerprint(cfg.repo_root, doc), 'verification': None}
        elif action == 'release-verified':
            if not doc['release'] or not args['verification'].strip():
                raise CycleError('publication readiness and verification required')
            if any(digest(contained(cfg.repo_root, a['path']).read_bytes()) != a['sha256'] for a in doc['release']['artifacts']):
                raise CycleError('release artifacts changed after approval')
            if doc['release']['input_sha256'] != source_fingerprint(cfg.repo_root, doc):
                raise CycleError('release inputs changed after approval')
            doc['release']['verification'] = args['verification']
        elif action == 'reflect':
            if doc['phase'] != 'reflect' and doc['status'] != 'paused':
                raise CycleError('reflection belongs to Reflect or abandonment')
            if not all(args['reflection'].get(k) for k in ('outcome', 'lessons', 'remaining')):
                raise CycleError('reflection requires outcome, lessons, and remaining work (use none when empty)')
            doc['reflection'] = args['reflection']
        elif action == 'abandon':
            if not doc['reflection']:
                raise CycleError('abandonment requires reflection')
            doc['status'] = 'abandoned'
        elif action == 'advance':
            check_decisions(cfg, doc)
            phase = doc['phase']
            if any(t['status'] != 'done' for t in doc['plan']['tasks'] if t['phase'] == phase):
                raise CycleError('current phase has unfinished tasks')
            if phase == 'plan':
                plan = doc['plan']
                if not plan['verification'] or not plan['tasks'] or not set(PHASES[doc['type']]).issubset({t['phase'] for t in plan['tasks']}):
                    raise CycleError('the plan must describe verification and tasks across every phase')
                if doc['type'] == 'refactor' and not plan.get('preserved_behavior'):
                    raise CycleError('refactor must identify preserved behavior and intended improvement')
                if doc['type'] == 'refactor' and not plan.get('improvement'):
                    raise CycleError('refactor requires intended improvement')
            if phase == 'test':
                check_tests(cfg, doc)
            if phase == 'review':
                check_tests(cfg, doc)
                check_review(cfg, doc)
            if phase == 'release':
                if not doc['release'] or not doc['release']['verification']:
                    raise CycleError('release requires reviewed publication and verification')
                check_tests(cfg, doc)
                check_review(cfg, doc)
            if phase == 'reflect':
                if any(task['status'] != 'done' for task in doc['plan']['tasks']):
                    raise CycleError('completion requires every planned task to be done')
                check_tests(cfg, doc)
                check_review(cfg, doc)
                if not doc['reflection']:
                    raise CycleError('reflection is required before completion')
                check_completion(cfg, doc)
                doc['status'] = 'completed'
            else:
                doc['phase'] = PHASES[doc['type']][PHASES[doc['type']].index(phase) + 1]
        else:
            raise CycleError('unknown cycle action')
        event(doc, action, **({'reason': args['reason']} if 'reason' in args else {}))
        save(cfg, doc)
        return doc


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
                reviews.append({'report':report['path'],'input_sha256':value['input_sha256'],'pass':value['pass'],'matches_current_source':value['input_sha256']==current,'matches_current':value==current_review})
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
