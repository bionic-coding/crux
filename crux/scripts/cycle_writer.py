"""Opt-in cycle pilot: one lead, milestone records, native delegation and independent review."""
from contextlib import contextmanager, nullcontext
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from types import SimpleNamespace
import uuid

import cycle_runtime as runtime
from cycle_store import CycleError, contained, now, tree

FORMAT = 'crux.cycle.v1'
# A record written before the cutover keeps the vNext value; a write never changes a record's own format.
FORMATS = ('crux.cycle.vNext', 'crux.cycle.v1')
SCRUTINY_LEVELS = ('focused', 'standard', 'intensive')
ADR_ID = re.compile(r'ADR-[0-9]{4,}')
# An adrs entry names the identity decision_policy allocated, which carries the artifact prefix when one is configured.
ADR_ENTRY_ID = re.compile(r'(?:[A-Z][A-Z0-9]{1,9}-)?ADR-[0-9]{4,}')
STATES = ('planning', 'working', 'reviewing', 'reviewed', 'completed', 'paused', 'abandoned')
TASK_STATES = ('pending', 'working', 'blocked', 'done')
# The states a record whose plan holds only goal, scope and acceptance may take.
UNPLANNED_STATES = ('planning', 'paused', 'abandoned')
# The active states in which a cycle drafts an ADR: an agent may need a corrective decision during work or review.
DECISION_STATES = ('planning', 'working', 'reviewing')


def decision_state_route(state):
    """The route back to a state that drafts an ADR, as a refusal suffix; empty when none applies."""
    if state == 'reviewed':
        return '; a plan revision returns the cycle to planning, where it can draft the ADR'
    return ''
# Records of the work under the documentation tree; a change here is never reviewed code.
BOOKKEEPING = ('cycles', 'adrs/councils', 'journal', 'log', 'queue')
SCHEMA = Path(__file__).resolve().parent.parent / 'schemas/cycle-record.schema.json'


class LegacyRecord(CycleError):
    """A record with no format value: a legacy typed record, which no writer command touches."""


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise CycleError(f'Git observation failed: {result.stderr.strip()}')
    return result.stdout.rstrip('\n')


def text(value, field, limit=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise CycleError(f'{field} requires non-empty text of at most {limit} characters')
    return value


def strings(value, field, *, empty=False):
    if not isinstance(value, list) or (not value and not empty) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise CycleError(f'{field} requires a list of non-empty strings')
    return value


def _encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def path_of(repo, identity):
    if not isinstance(identity, str) or not re.fullmatch(r'(?:[A-Z][A-Z0-9]{1,9}-)?CYC-[0-9]{4,}', identity):
        raise CycleError('invalid cycle identity')
    return contained(tree(repo).docs_root, f'cycles/{identity}/cycle.json')


def load_pilot(repo, identity):
    path = path_of(repo, identity)
    if path.is_symlink() or not path.is_file():
        raise CycleError('pilot record must be a regular file')
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CycleError(f'cannot read pilot {identity}: {exc}') from exc
    if isinstance(record, dict) and 'format' not in record:
        raise LegacyRecord(f'{identity} is a legacy typed record (it has a schema_version and no format value); the writer never changes it. '
                           'cycle.py show and status read it')
    validate(record)
    if record['id'] != identity:
        raise CycleError('pilot record identity does not match its directory')
    return record


def plan_complete(doc):
    """Whether the plan holds verification, a council decision and at least one task.

    A queue start or a create without a plan file records only the goal, scope and acceptance; the
    cycle stays in planning until the lead records the rest with the plan command."""
    return 'verification' in doc['plan'] and 'council' in doc['plan'] and bool(doc['tasks'])


def council_needed(doc):
    return bool(doc['plan'].get('council', {}).get('needed', False))


def validate(doc):
    from council_records import _validator
    validator = _validator()
    errors = []
    validator.validate(doc, validator.load_schema(SCHEMA), '#', '#', errors, 'pilot cycle')
    if errors:
        raise CycleError(f'invalid pilot record: {errors[0]}')
    plan = doc['plan']
    for field in ('goal',):
        text(plan[field], 'plan.' + field)
    strings(plan['scope'], 'plan.scope')
    strings(plan['acceptance'], 'plan.acceptance')
    if not plan_complete(doc) and doc['state'] not in UNPLANNED_STATES:
        raise CycleError('a cycle leaves planning only with verification, council and at least one task; '
                         'the lead records them with plan IDENTITY --file FILE --reason TEXT')
    if 'council' in plan:
        text(plan['council']['reason'], 'plan.council.reason')
    if 'verification' in plan:
        checks = plan['verification']['checks']
        if not checks or len({c['id'] for c in checks}) != len(checks):
            raise CycleError('verification requires distinct selected checks')
        for check in checks:
            text(check['id'], 'verification check id', 128)
            text(check['rationale'], 'verification rationale')
        text(plan['verification']['gaps'], 'verification.gaps')
    if 'scrutiny' in plan:
        text(plan['scrutiny']['reason'], 'plan.scrutiny.reason')
    for entry in doc.get('adrs', []):
        text(entry['path'], 'adrs path', 512)
    tasks = {t['id']: t for t in doc['tasks']}
    if len(tasks) != len(doc['tasks']):
        raise CycleError('pilot requires distinct tasks')
    for task in tasks.values():
        text(task['id'], 'task id', 128)
        if not re.fullmatch('[a-z0-9][a-z0-9-]*', task['id']):
            raise CycleError('task ids use lowercase letters, digits and hyphens')
        text(task['description'], 'task description')
        text(task['owner'], 'task owner', 256)
        if task['council'] and not council_needed(doc):
            raise CycleError('a council-dependent task requires the plan to declare council needed')
        if len(set(task['depends_on'])) != len(task['depends_on']) or any(d not in tasks or d == task['id'] for d in task['depends_on']):
            raise CycleError('task dependencies must name distinct other tasks')
        seen = set()
        pending = list(task['depends_on'])
        while pending:
            ident = pending.pop()
            if ident == task['id']:
                raise CycleError('task dependencies contain a cycle')
            if ident not in seen:
                seen.add(ident)
                pending.extend(tasks[ident]['depends_on'])
        if len(set(task.get('adr_dependencies', []))) != len(task.get('adr_dependencies', [])):
            raise CycleError('adr_dependencies name distinct ADRs')
        if task['status'] != 'pending' and task['run'] < 1:
            raise CycleError('started tasks require a positive run number')
    ids = set()
    for check in doc['checks']:
        if check['id'] in ids:
            raise CycleError('check observation ids must be unique')
        for field in ('check_id', 'command', 'tested_revision', 'summary', 'reason'):
            text(check[field], 'check.' + field)
        if check['use'] == 'reused':
            prior = next((p for p in doc['checks'] if p['id'] == check.get('reused_from') and p['id'] in ids), None)
            if (prior is None or prior['check_id'] != check['check_id']
                    or prior['result'] != 'passed' or any(prior[k] != check[k] for k in ('command', 'tested_revision', 'result'))):
                raise CycleError('check reuse must preserve a prior passing observation of this plan revision')
        elif 'reused_from' in check:
            raise CycleError('executed observations carry no reuse reference')
        ids.add(check['id'])


def _task(spec, lead, council):
    if not isinstance(spec, dict) or set(spec) - {'id', 'description', 'owner', 'depends_on', 'council', 'kind', 'adr_dependencies'}:
        raise CycleError('task definition has unknown fields')
    task = {'id': spec['id'], 'description': spec['description'], 'owner': spec.get('owner', lead),
            'depends_on': spec.get('depends_on', []), 'council': spec.get('council', council),
            'kind': spec.get('kind', 'implementation'), 'run': 0, 'status': 'pending', 'checkout': None,
            'summary': '', 'attempts': []}
    if 'adr_dependencies' in spec:
        names = spec['adr_dependencies']
        if (not isinstance(names, list) or not names or len(set(map(str, names))) != len(names)
                or any(not isinstance(n, str) or not ADR_ID.fullmatch(n) for n in names)):
            raise CycleError('adr_dependencies requires distinct ADR ids such as ADR-0183')
        task['adr_dependencies'] = names
    return task


def default_scrutiny(repo):
    """The project's review scrutiny from .bionic.yml, with the reason a plan states when it names none."""
    from bionic_config import load_workflow_policy
    return {'level': load_workflow_policy(repo)['review.scrutiny'], 'reason': 'project default'}


def _new_record(identity, base, title, lead, specification, queue, follows=None, scrutiny=None):
    spec = deepcopy(specification)
    tasks = spec.pop('tasks', [])
    if set(spec) - {'goal', 'scope', 'acceptance', 'verification', 'council', 'scrutiny'}:
        raise CycleError('plan definition has unknown fields')
    if scrutiny is not None:
        spec.setdefault('scrutiny', scrutiny)
    text(title, 'title', 256)
    text(lead, 'lead', 256)
    doc = {'format': FORMAT, 'id': identity, 'revision': 1, 'state': 'planning', 'title': title, 'lead': lead,
           'base_commit': base, 'created_at': now(), 'updated_at': now(), 'plan': {'revision': 1, **spec},
           'tasks': [_task(t, lead, spec.get('council', {}).get('needed', False)) for t in tasks],
           'checks': [], 'councils': [], 'review': None, 'delivery': {'pr': None, 'ci': 'unknown', 'merge': 'unmerged', 'commit': None},
           'blockers': [], 'history': [], 'completion': None}
    if queue is not None:
        doc['queue'] = {'item': queue['item'], 'token': queue['token'], 'origin': 'start', 'started_at': now()}
    if follows is not None:
        doc['follows'] = follows  # the completed cycle whose delivered work this cycle repairs or extends
    validate(doc)
    return doc


def check_definition(repo, title, lead, specification):
    """Validate a definition without allocating, so a refused queue start burns no cycle id."""
    _new_record('CYC-0000', git(repo, 'rev-parse', 'HEAD'), title, lead, specification, None, scrutiny=default_scrutiny(repo))


def create(repo, title, lead, specification, queue=None, follows=None):
    """Allocate in the main checkout before branching; no source or record commit is made.

    `queue` is the starting item and token when the queue writer starts this pilot. `follows` names
    an existing cycle this one is linked to, for a repair that deserves its own scope."""
    from cycle_store import locked
    base = git(repo, 'rev-parse', 'HEAD')
    if follows is not None and not path_of(repo, follows).is_file():
        raise CycleError(f'--follows names no cycle record: {follows}')
    scrutiny = default_scrutiny(repo)
    _new_record('CYC-0000', base, title, lead, specification, queue, follows, scrutiny)
    with locked(repo) as (cfg, directory):
        identity = runtime.allocate(cfg, directory)
        doc = _new_record(identity, base, title, lead, specification, queue, follows, scrutiny)
        directory.joinpath(identity).mkdir()
        runtime.atomic(path_of(repo, identity), doc)
        return doc


# -- release records ---------------------------------------------------------------------
# A release record carries one task per fixed step of its list. `tools/release.py` and its ledger
# stay authoritative: the ordinary task, batch, plan, review, finish and reopen writes refuse, and
# `record_release` closes the steps once the ledger shows the target published.

RELEASE_DESCRIPTOR = 'tools/crux-release.json'
RELEASE_VERSION = re.compile(r'\d+\.\d+\.\d+')
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
        ('live-check-and-go-ahead', "Take the owner's queued go-ahead, given after the beta was tagged, as the owner's attestation that the tagged artifact was hand-tested, including any owed live check",
         "the owner's quoted go-ahead for the tagged artifact; release.py official records it as the live-check attestation when a check is owed"),
        ('official', 'Publish and tag the official release with the same go-ahead', 'release.py official published'),
        ('record', 'Copy the ledger into this cycle, with the reason when the target did not publish, and prepend its release op to the log',
         'release.py record and the commit that holds the log op'),
    ],
}
DESCRIPTOR_LIMIT = 1024 * 1024


def _descriptor_bytes(path):
    """The descriptor's bytes from one bounded read; a symlink or a file over 1 MiB is refused."""
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, 'rb') as stream:
        raw = stream.read(DESCRIPTOR_LIMIT + 1)
    if len(raw) > DESCRIPTOR_LIMIT:
        raise ValueError('descriptor too large')
    return raw


def release_descriptor(cfg):
    """Read project release data only; the writer never runs repository commands."""
    path = contained(cfg.repo_root, RELEASE_DESCRIPTOR)
    if not path.exists():
        return None
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError('descriptor is not a regular file')
        raw = _descriptor_bytes(path)
        value = json.loads(raw)
        required = {'format', 'prep_scope', 'commands', 'targets'}
        if (not isinstance(value, dict) or not required <= set(value) <= required | {'official_scope'}
                or value['format'] != 1 or not isinstance(value['commands'], dict)
                or not isinstance(value['targets'], dict) or set(value['targets']) != {'beta', 'official'}
                or any(not isinstance(repo, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo)
                       for repo in value['targets'].values())):
            raise ValueError('invalid descriptor fields')
        # The official list's mandatory scope is optional; when present it is validated like prep_scope.
        for key in ('prep_scope', 'official_scope'):
            if key not in value:
                continue
            if not isinstance(value[key], list) or not value[key]:
                raise ValueError('invalid descriptor fields')
            for name in value[key]:
                if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in Path(name).parts:
                    raise ValueError('invalid prep path')
                contained(cfg.repo_root, name)
            if len(set(value[key])) != len(value[key]):
                raise ValueError('duplicate prep path')
        for kind, steps in value['commands'].items():
            if kind not in ('beta', 'official') or not isinstance(steps, dict):
                raise ValueError('invalid release list')
            for step, commands in steps.items():
                if (not isinstance(step, str) or not isinstance(commands, list) or not commands
                        or any(not isinstance(command, list) or not command
                               or any(not isinstance(arg, str) or not arg or '\x00' in arg for arg in command)
                               for command in commands)):
                    raise ValueError('invalid command descriptor')
        return {'path': RELEASE_DESCRIPTOR, 'sha256': hashlib.sha256(raw).hexdigest(), **value}
    except (ValueError, OSError) as exc:
        raise CycleError('release descriptor is unavailable or invalid: ' + type(exc).__name__) from None


def scope_name_in_scope(name, patterns):
    """True when a repo-relative name lies in the scope under the walk's glob semantics.

    A name is in scope when it, or a directory above it, matches a pattern with `PurePosixPath.full_match`
    (recursive `**`). The walk's `.git` and `__pycache__` exclusions apply."""
    path = PurePosixPath(name)
    if '.git' in path.parts or '__pycache__' in path.parts:
        return False
    candidates = [path, *path.parents][:-1]
    return any(c.full_match(pattern) for pattern in patterns for c in candidates)


def release_scope(cfg, scope, release_list, *, capture=False):
    """Complete the scope on capture, or refuse a frozen scope that omits mandatory paths before allocation."""
    descriptor = release_descriptor(cfg)
    # The beta list requires prep_scope; the official list requires official_scope when the descriptor
    # carries it. A descriptor without official_scope leaves the official scope as given.
    key = {'beta': 'prep_scope', 'official': 'official_scope'}.get(release_list)
    if descriptor is None or key not in descriptor:
        return list(scope)
    missing = [name for name in descriptor[key] if not scope_name_in_scope(name, scope)]
    if missing and not capture:
        label = 'release prep scope' if release_list == 'beta' else 'official release scope'
        raise CycleError(label + ' omits mandatory paths: ' + ', '.join(missing)
                         + '; correct the unstarted queue item before authorization/start')
    return list(dict.fromkeys([*scope, *missing]))


def _release_specification(cfg, release_list, version, goal, scope, acceptance, lead):
    if release_list not in RELEASE_LISTS:
        raise CycleError('a release record requires release list beta or official')
    if not isinstance(version, str) or not RELEASE_VERSION.fullmatch(version):
        raise CycleError('a release record requires a version of the form X.Y.Z')
    scope = release_scope(cfg, strings(scope, 'scope'), release_list)
    steps = RELEASE_LISTS[release_list]
    return {'goal': goal, 'scope': scope, 'acceptance': acceptance,
            'verification': {'checks': [{'id': 'release-ledger', 'rationale': (
                'tools/release.py records every step in its ledger, and the release verify step is the only suite step; '
                'the ledger, not a separate check observation, is the evidence of a release')}],
                'gaps': 'none: the ledger holds the artifact, authorization, verification, smoke and tag evidence'},
            'council': {'needed': False, 'reason': 'a release runs a fixed step list with no plan council'},
            'tasks': [{'id': step, 'description': description, 'owner': lead, 'depends_on': [steps[i - 1][0]] if i else [],
                       'council': False, 'kind': 'implementation'} for i, (step, description, _) in enumerate(steps)]}


def create_release(repo, release_list, version, title, goal, scope, acceptance, lead, queue=None):
    """Allocate a release record: kind release, one task per fixed step of its list, in order.

    Everything is validated before allocation, so a refusal burns no cycle id. The record has no plan
    council and no review; `tools/release.py` records its steps through `record_release`."""
    from cycle_store import locked
    cfg = tree(repo)
    specification = _release_specification(cfg, release_list, version, goal, scope, acceptance, lead)
    base = git(repo, 'rev-parse', 'HEAD')

    def build(identity):
        doc = _new_record(identity, base, title, lead, specification, queue)
        doc.update(kind='release', release={'list': release_list, 'version': version}, state='working')
        validate(doc)
        return doc
    build('CYC-0000')
    with locked(repo) as (cfg, directory):
        identity = runtime.allocate(cfg, directory)
        doc = build(identity)
        directory.joinpath(identity).mkdir()
        runtime.atomic(path_of(repo, identity), doc)
        return doc


def record_release(repo, identity, commit, evidence, summary=None):
    """Close a release record once the ledger shows the target published: (record, changed).

    One locked write by the decision-writer role. A completed record returns unchanged, so a replay
    writes nothing. Every unfinished step task is marked done with one attempt that says release.py
    record closed it. A record that is not a release, a legacy record and an abandoned record refuse."""
    text(commit, 'release commit', 512)
    text(evidence, 'release evidence', 1024)
    with locked_record(repo, identity, None, None, role='writer') as doc:
        if doc.get('kind') != 'release':
            raise CycleError(f'{identity} is not a release record')
        if doc['state'] == 'abandoned':
            raise CycleError(f'{identity} is abandoned and no longer takes a release record')
        if doc['state'] == 'completed':
            return doc, False
        at = now()
        closed = 'closed by release.py record because the ledger shows the target published'
        for task in doc['tasks']:
            if task['status'] == 'done':
                continue
            task['run'] = task['run'] or 1
            task['status'], task['checkout'] = 'done', None
            task['summary'] = f'{closed}; commit {commit}; evidence {evidence}' if task['id'] == 'record' else closed
            task['attempts'].append({'run': task['run'], 'owner': task['owner'], 'checkout': None, 'started_at': at,
                                     'ended_at': at, 'outcome': 'done', 'summary': closed})
        if summary is not None:
            text(summary, 'release summary')
        doc['completion'] = {'completed_at': at, 'commit': commit, 'evidence': evidence,
                             'summary': summary or f"{doc['release']['list']} release {doc['release']['version']} recorded by release.py record"}
        doc['state'] = 'completed'
        doc.pop('resume_state', None)
        doc['blockers'] = []
    return load_pilot(repo, identity), True


@contextmanager
def locked_record(repo, identity, actor, expected, role='lead', before_write=None):
    """Lock, load and admit one writer. The lead writes every milestone except the review verdict.

    `role='reviewer'` admits any actor but the lead; `record_review` then binds that actor to the
    requested reviewer. `role='writer'` admits the decision writer, which names no lead actor.
    `expected=None` skips the revision check for the queue binding, which is idempotent and runs
    under the queue lock."""
    path = path_of(repo, identity)
    lock = path.parent / '.pilot.lock'
    if not path.is_file() or lock.is_symlink():
        raise CycleError('pilot record or lock unavailable')
    with lock.open('a+') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        doc = load_pilot(repo, identity)
        if role == 'reviewer':
            if actor == doc['lead']:
                raise CycleError('the lead requests review and never records its verdict; the requested reviewer submits its own report as --actor')
        elif role != 'writer' and actor != doc['lead']:
            raise CycleError('only the recorded lead changes this pilot')
        if expected is not None and (type(expected) is not int or expected != doc['revision']):
            raise CycleError(f'stale revision: expected {expected}, current {doc["revision"]}; inspect before retrying')
        original = _encoded(doc)
        yield doc
        if _encoded(doc) != original:
            doc['revision'] += 1
            doc['updated_at'] = now()
            validate(doc)
            if before_write:
                before_write()
            runtime.atomic(path, doc)


@contextmanager
def claims_transaction(repo):
    """Checkout claims for one record write, held under the runtime lock for the whole write.

    Yields the claims mapping and a flush. Every task of the write reads and changes the same
    mapping, so two tasks of one batch cannot claim one checkout.

    Two files are written, and the record is the commit point. The writes are ordered so that a
    process killed at any moment leaves at most a claim the record does not back, never a working
    assignment without its claim:
      1. before the record: the claims as they stood, plus every claim this write adds or replaces;
      2. the record;
      3. after the record: the final claims, which drop the claims this write releases.
    `reconcile_claims` removes such a leftover on the next claiming write to the same pilot: task,
    batch, resume, recover, finish or abandon. Other writes leave it in place. A refusal or
    failure restores the claims exactly as they stood, which is certain because the lock was held."""
    with runtime.locked(repo) as state:
        snapshot = deepcopy(state['claims'])
        flushed = []

        def flush():
            before_record = {**snapshot, **state['claims']}
            if before_record != snapshot:
                runtime.flush(repo, {**state, 'claims': before_record})
                flushed.append(True)
        try:
            yield state['claims'], flush
        except BaseException:
            state['claims'].clear()
            state['claims'].update(snapshot)
            if flushed:
                runtime.flush(repo, state)
            raise
        if flushed or state['claims'] != snapshot:
            runtime.flush(repo, state)


def reconcile_claims(doc, claims):
    """Bring this pilot's claims back in line with its record after an interrupted write.

    Only a claim that carries this pilot's identity is ever removed, and only when the record holds
    no working assignment with the same task, owner, run and checkout. Because the record is the
    commit point, such a claim can only be what an interrupted write of this pilot left. Another
    owner's claim is never touched, and nothing is inferred from time. Returns what it did."""
    notes = []
    working = {t['checkout']: t for t in doc['tasks'] if t['status'] == 'working' and t['kind'] == 'implementation' and t.get('checkout')}
    for checkout, claim in list(claims.items()):
        if claim.get('cycle') != doc['id']:
            continue
        task = working.get(checkout)
        if task and (claim.get('task'), claim.get('owner'), claim.get('run')) == (task['id'], task['owner'], task['run']):
            continue
        del claims[checkout]
        notes.append(f"removed the claim on {checkout} for task {claim.get('task')} run {claim.get('run')}: "
                     'the record holds no matching working assignment, so an interrupted write left it')
    for checkout, task in working.items():
        claim = claims.get(checkout)
        if claim is None:
            claims[checkout] = {'cycle': doc['id'], 'task': task['id'], 'owner': task['owner'], 'run': task['run'], 'checkout': checkout}
            notes.append(f"restored the claim on {checkout} for working task {task['id']} run {task['run']}")
        elif claim.get('cycle') != doc['id']:
            notes.append(f"task {task['id']} is recorded working in {checkout}, which {claim.get('cycle')}/{claim.get('task')} holds; "
                         'that claim is left alone, so reassign the task to another checkout')
    return notes


def _bookkeeping(repo, path):
    cfg = tree(repo)
    relative = cfg.docs_root.relative_to(cfg.repo_root).as_posix()
    return any(path.startswith(f'{relative}/{name}/') for name in BOOKKEEPING)


def _clean_code(repo):
    rows = iter(git(repo, 'status', '--porcelain=v1', '-z', '--untracked-files=all').split('\0'))
    for row in rows:
        if not row:
            continue
        paths = [row[3:]]
        if 'R' in row[:2] or 'C' in row[:2]:
            paths.append(next(rows, ''))
        if any(not path or not _bookkeeping(repo, path) for path in paths):
            return False
    return True


def selected_checks(doc):
    latest = {}
    for check in doc['checks']:
        if check['plan_revision'] == doc['plan']['revision']:
            latest[check['check_id']] = check
    return {selection['id']: latest.get(selection['id']) for selection in doc['plan'].get('verification', {}).get('checks', [])}


def checks_pass(doc):
    return all(result is not None and result['result'] == 'passed' for result in selected_checks(doc).values())


def review_recorded(doc):
    """The recorded facts of an approving review, without a Git observation."""
    review = doc.get('review')
    if (not review or review['verdict'] != 'approve' or review['plan_revision'] != doc['plan']['revision']
            or review['blocking'] or not checks_pass(doc)
            or any(t['status'] != 'done' for t in doc['tasks'] if t['kind'] == 'implementation')):
        return False
    if review['at'] < last_reopen(doc):
        return False  # a reopened cycle needs a review of its repair
    if 'task_runs' in review and review['task_runs'] != _task_runs(doc):
        return False  # an implementation task was added or run again after the approval
    definitions = {ident: result['command'] for ident, result in selected_checks(doc).items() if result}
    return review['check_definitions'] == definitions


def code_changes(repo, since, until='HEAD'):
    """Paths outside bookkeeping that differ between commits `since` and `until`, without rename detection."""
    changed = [p for p in git(repo, 'diff', '--no-renames', '--name-only', '-z', since, until).split('\0') if p]
    return [path for path in changed if not _bookkeeping(repo, path)]


def _task_runs(doc):
    return {t['id']: t['run'] for t in doc['tasks'] if t['kind'] == 'implementation'}


def last_reopen(doc):
    """The time of the newest reopen, or '' when the cycle was never reopened."""
    return max((entry['at'] for entry in doc.get('history') or [] if entry.get('kind') == 'reopen'), default='')


def _commit(repo, name):
    """The commit an id names, or None. The name is one argument-vector entry."""
    result = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet', name + '^{commit}'],
                            capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None


def reviewed_paths(repo, doc):
    """The code paths the reviewed range changed: cycle base to reviewed head, bookkeeping excluded,
    without rename detection, so a rename names both its old path and its new one."""
    return code_changes(repo, doc['base_commit'], doc['review']['head_commit'])


def reviewed_path_changes(repo, doc):
    """The reviewed-path rule that review admission and `applicability` share.

    Returns the reviewed paths whose content in this checkout differs from their content at the
    reviewed head, committed or not. Other paths do not count: commits elsewhere on a shared branch
    are other work. Bookkeeping never counts. The comparison is by content, so it is a
    path-preservation boundary: it does not detect a later change that touches only new paths."""
    paths = reviewed_paths(repo, doc)
    if not paths:
        return []
    return [p for p in git(repo, 'diff', '--no-renames', '--name-only', '-z', doc['review']['head_commit'], '--',
                           *(':(literal)' + path for path in paths)).split('\0') if p]


STALE_PATHS = 'reviewed paths changed after the reviewed head: '


def applicability(repo, doc):
    """Whether the recorded approving review still covers this cycle's final change: (bool, reason).

    The finish gate and every status view read this one function. The review applies while every
    reviewed path holds, in this checkout, the content it had at the reviewed head; see
    `reviewed_path_changes`, the rule review admission applies too. A queue binding plays no part."""
    if not review_recorded(doc):
        return False, 'no approving review of this plan revision is recorded with passing selected checks and finished implementation tasks'
    head = doc['review']['head_commit']
    try:
        if _commit(repo, head) is None:
            return False, f'the reviewed head {head[:12]} is not in this repository'
        changed = reviewed_path_changes(repo, doc)
        if changed:
            return False, STALE_PATHS + ', '.join(changed[:5])
        return True, 'the reviewed paths hold the reviewed content'
    except CycleError as exc:
        return False, str(exc)


def review_current(repo, doc):
    """True when the recorded approving review applies to the cycle's final change."""
    return applicability(repo, doc)[0]


def status_facts(repo, doc):
    """The facts every status view reports, kept apart: the recorded review, whether it applies to
    the final change, whether the cycle completed, and the delivery facts, which completion never implies."""
    review, done = doc.get('review'), doc['state'] == 'completed'
    if done:
        applicable, reason = None, 'completed; the recorded review is historical and later commits are other work'
    elif not review:
        applicable, reason = None, 'no review recorded'
    else:
        applicable, reason = applicability(repo, doc)
    return {'status': queue_status(doc),
            'review': {'verdict': review['verdict'], 'reviewer': review['reviewer'], 'head_commit': review['head_commit'],
                       'plan_revision': review['plan_revision']} if review else None,
            'review_applicable': applicable, 'applicability': reason, 'completed': done,
            'reopened': sum(entry.get('kind') == 'reopen' for entry in doc.get('history') or []), 'delivery': doc['delivery']}


def queue_status(doc):
    """The status a queue reader shows for this pilot, from the record alone.

    `reviewed` means an approving review is recorded and the cycle awaits its finish operation.
    `completed` means the cycle finished. Neither says anything about a PR, CI, a merge or a release."""
    if doc['state'] in ('abandoned', 'paused', 'completed'):
        return doc['state']
    if doc['state'] == 'reviewed' and review_recorded(doc):
        return 'reviewed'
    return 'active'


def ever_completed(doc):
    """True for a completed pilot and for one reopened after completing; its queue item stays archivable."""
    return doc['state'] == 'completed' or bool(last_reopen(doc))


def reviewed_range_contained(repo, doc):
    """True when the reviewed head descends from the cycle base and HEAD contains it."""
    review = doc['review']
    for older, newer in ((doc['base_commit'], review['head_commit']), (review['head_commit'], 'HEAD')):
        if subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', older, newer], capture_output=True).returncode:
            return False
    return True


def bind_queue(repo, identity, actor, binding):
    """Record the queue item this pilot completed. Called by the queue writer under the queue lock.

    A repeat for the same item returns the stored binding and writes nothing."""
    with locked_record(repo, identity, actor, None) as doc:
        existing = doc.get('queue')
        if existing:
            if existing['item'] != binding['item']:
                raise CycleError(f"{identity} is already bound to {existing['item']}")
            return existing
        doc['queue'] = binding
        return binding


def record_adr(repo, identity, entry):
    """Record one ADR the cycle proposed: {adr, path, sha256}, the digest taken at proposal time.

    Called by the decision writer under the record lock, so it names no lead actor. The cycle must be
    planning, working or reviewing. An identical repeat writes nothing; a different entry for a recorded ADR
    refuses. Nothing compares the digest later."""
    if (not isinstance(entry, dict) or set(entry) != {'adr', 'path', 'sha256'} or not isinstance(entry['adr'], str)
            or not ADR_ENTRY_ID.fullmatch(entry['adr']) or not isinstance(entry['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', entry['sha256'])):
        raise CycleError('an ADR entry requires adr (such as ADR-0183), path and a 64-character sha256')
    text(entry['path'], 'adrs path', 512)
    contained(tree(repo).docs_root, entry['path'])
    with locked_record(repo, identity, None, None, role='writer') as doc:
        if doc['state'] not in DECISION_STATES:
            raise CycleError('an ADR is recorded while the cycle is planning, working or reviewing; it is ' + doc['state']
                             + decision_state_route(doc['state']))
        existing = next((e for e in doc.get('adrs', []) if e['adr'] == entry['adr']), None)
        if existing:
            if existing != entry:
                raise CycleError(f"{entry['adr']} is already recorded with different content for {identity}")
            return existing
        doc.setdefault('adrs', []).append(dict(entry))
        return entry


def council_current(doc):
    return (not council_needed(doc) or any(c['plan_revision'] == doc['plan']['revision']
            and c['outcome'] == 'approved' for c in doc['councils']))


def blockers(doc):
    result = list(doc['blockers'])
    if not plan_complete(doc):
        result.append('plan incomplete: the lead records verification, council and tasks with plan IDENTITY --file FILE --reason TEXT')
    result += [f"{t['id']}: {t['summary']}" for t in doc['tasks'] if t['status'] == 'blocked']
    if not council_current(doc):
        result.append('council required for dependent tasks; no approved result for this plan revision')
    return list(dict.fromkeys(result))


def summarize(repo, doc):
    facts = status_facts(repo, doc)
    return {'format': doc['format'], 'id': doc['id'], 'revision': doc['revision'], 'title': doc['title'],
            'state': doc['state'], 'scrutiny': doc['plan'].get('scrutiny') or default_scrutiny(repo),
            'lead': doc['lead'], 'plan_revision': doc['plan']['revision'], 'tasks': [
                {k: t[k] for k in ('id', 'description', 'owner', 'run', 'status', 'summary', 'checkout')} for t in doc['tasks']],
            'completed': sum(t['status'] == 'done' for t in doc['tasks']), 'total': len(doc['tasks']),
            'blockers': blockers(doc), 'checks': [
                {'check_id': ident, 'result': result['result'] if result else 'missing'} for ident, result in selected_checks(doc).items()],
            'review': facts['review'], 'review_applicable': facts['review_applicable'],
            'applicability': facts['applicability'], 'finished': facts['completed'],
            'reopened': facts['reopened'], 'delivery': facts['delivery']}


def _claim(repo, doc, task, checkout, owner, run, claims):
    checkout = str(runtime.checkout_root(checkout))
    if runtime.common_directory(checkout) != runtime.common_directory(repo):
        raise CycleError('task checkout must belong to this Git repository')
    claim = claims.get(checkout)
    if claim and (claim.get('cycle'), claim.get('task')) != (doc['id'], task['id']):
        raise CycleError(f"checkout is owned by {claim}; use a distinct worktree, or when the holder's write was interrupted, "
                         f"run `cycle.py recover {claim.get('cycle')}` to remove a claim its record does not back")
    legacy = runtime.legacy_holders(repo, tree(repo).docs_root, checkout)
    if legacy:
        raise CycleError('checkout has legacy editing assignments: ' + ', '.join(legacy))
    claims[checkout] = {'cycle': doc['id'], 'task': task['id'], 'owner': owner, 'run': run, 'checkout': checkout}
    return checkout


def _release(doc, task, claims):
    claim = claims.get(task['checkout']) if task.get('checkout') else None
    if claim and all(claim.get(k) == v for k, v in {'cycle': doc['id'], 'task': task['id'], 'owner': task['owner'], 'run': task['run']}.items()):
        del claims[task['checkout']]


def _startable(doc, task):
    if any(t['id'] in task['depends_on'] and t['status'] != 'done' for t in doc['tasks']):
        raise CycleError('task dependencies are unfinished')
    if task['council'] and not council_current(doc):
        raise CycleError('council-required task is blocked until this exact plan revision is approved')


def _adr_status(repo, entry):
    """The status an ADR file states, or 'unknown' when the file or its frontmatter cannot be read."""
    import yaml
    from adr_frontmatter import frontmatter_block
    try:
        block = frontmatter_block(contained(tree(repo).docs_root, entry['path']).read_text())
        front = yaml.safe_load(block) if block is not None else None
        return str(front.get('status') or 'unknown') if isinstance(front, dict) else 'unknown'
    except (OSError, ValueError, CycleError, yaml.YAMLError):
        return 'unknown'


def _outside_adr_entry(repo, task, name):
    """The entry for an ADR this cycle did not record: found under adrs/ by its id, and its acceptance receipt
    validated against the file when its acceptance_format requires one. An acceptance_format the writer does not
    know refuses. Nothing is written to the record."""
    import yaml
    from adr_frontmatter import frontmatter_block
    cfg = tree(repo)
    unknown = (f"adr-dependency-unrecorded: task {task['id']} names {name}, which this cycle has not recorded "
               'and no ADR file under adrs/ carries')
    matches = sorted((cfg.docs_root / 'adrs').glob(f'{name}-*.md')) if ADR_ENTRY_ID.fullmatch(name) else []
    if len(matches) != 1:
        raise CycleError(unknown)
    entry = {'adr': name, 'path': matches[0].relative_to(cfg.docs_root).as_posix()}
    try:
        front = yaml.safe_load(frontmatter_block(contained(cfg.docs_root, entry['path']).read_text()) or '')
    except (OSError, ValueError, CycleError, yaml.YAMLError):
        front = None
    if not isinstance(front, dict) or front.get('id') != name:
        raise CycleError(unknown)
    # No format is a legacy ADR, read by its status alone; the summaries projection refuses any other value too.
    if front.get('acceptance_format') not in (None, 'crux.adr-acceptance.v1'):
        raise CycleError(f"adr-dependency-acceptance-format-unknown: task {task['id']} names {name}, whose "
                         f"acceptance_format {str(front.get('acceptance_format'))[:80]!r} the writer does not know; "
                         'only crux.adr-acceptance.v1 or no acceptance_format is read')
    if front.get('status') == 'Accepted' and front.get('acceptance_format') == 'crux.adr-acceptance.v1':
        from decision_policy import validate_acceptance
        try:
            validate_acceptance(cfg, {'path': entry['path']})
        except (CycleError, OSError, ValueError, KeyError, TypeError) as error:
            raise CycleError(f"adr-dependency-acceptance-invalid: task {task['id']} names {name}, "
                             f'whose acceptance record does not validate: {error}')
    return entry


def _adr_dependencies_met(repo, doc, task):
    """Refuse while an ADR a task names is not Accepted.

    An ADR this cycle proposed is read through its recorded entry. Any other ADR is found under adrs/ by
    its id, and an Accepted status needs a valid acceptance receipt where its acceptance_format requires one;
    an unknown acceptance_format refuses."""
    recorded = {entry['adr']: entry for entry in doc.get('adrs', [])}
    for name in task.get('adr_dependencies', []):
        entry = recorded[name] if name in recorded else _outside_adr_entry(repo, task, name)
        status = _adr_status(repo, entry)
        if status != 'Accepted':
            raise CycleError(f"adr-dependency-awaiting-acceptance: task {task['id']} names {name}, whose status is {status}, not Accepted")


def task_update(repo, doc, args, claims):
    """Record an assignment or a result against `claims`, the mapping of a claims transaction."""
    text(args.owner, 'task owner', 256)
    if args.status not in TASK_STATES[1:]:
        raise CycleError('invalid task milestone')
    if type(args.run) is not int:
        raise CycleError('task run requires an integer')
    task = next((t for t in doc['tasks'] if t['id'] == args.task), None)
    if task is None:
        raise CycleError('unknown task; revise the plan task list explicitly')
    summary = getattr(args, 'summary', None)
    if args.status == 'working':
        if doc['state'] in ('paused', 'abandoned'):
            raise CycleError('resume before assigning work')
        if args.run != task['run'] + 1:
            raise CycleError('a new assignment increments the task run by one')
        if task['status'] == 'working' and not summary:
            raise CycleError('reassigning unfinished work requires a summary of its observed state')
        _startable(doc, task)
        _adr_dependencies_met(repo, doc, task)
        checkout = getattr(args, 'checkout', None) or str(Path(repo).resolve())
        if task['kind'] == 'implementation':
            checkout = _claim(repo, doc, task, checkout, args.owner, args.run, claims)
        else:
            checkout = None
        if task['checkout'] and task['checkout'] != checkout:
            _release(doc, task, claims)
        if task['attempts'] and task['attempts'][-1]['outcome'] is None:
            task['attempts'][-1].update(outcome='interrupted', summary=summary or 'lead reassigned work', ended_at=now())
        task.update(owner=args.owner, run=args.run, status='working', checkout=checkout, summary=summary or '')
        task['attempts'].append({'run': args.run, 'owner': args.owner, 'checkout': checkout, 'started_at': now(),
                                 'ended_at': None, 'outcome': None, 'summary': ''})
    else:
        text(summary, 'task outcome summary')
        named = f"this result names run {args.run} owned by {args.owner}"
        if task['status'] == 'working':
            if args.run != task['run'] or args.owner != task['owner']:
                raise CycleError(f"late or mismatched result: task {task['id']} is working at run {task['run']} owned by {task['owner']}; {named}")
            if args.status == 'done':
                _adr_dependencies_met(repo, doc, task)
            task.update(status=args.status, summary=summary)
            task['attempts'][-1].update(outcome=args.status, summary=summary, ended_at=now())
            if args.status == 'done' and task['kind'] == 'implementation':
                _record_commit(repo, task['attempts'][-1])
            _release(doc, task, claims)
        elif (task['status'], task['run'], task['owner'], task['summary']) == (args.status, args.run, args.owner, summary):
            return  # an identical repeat of a recorded result changes nothing
        elif args.run <= task['run']:
            raise CycleError(f"late or mismatched result: task {task['id']} is {task['status']} at run {task['run']} owned by {task['owner']}; {named}, which was superseded or already recorded")
        elif task['status'] == 'done':
            raise CycleError(f"invalid transition: task {task['id']} is already done at run {task['run']}; revise the plan to add new work")
        elif args.run != task['run'] + 1:
            raise CycleError(f"invalid transition: a result for {task['status']} task {task['id']} names run {task['run'] + 1}, the next run; {named}")
        else:
            # Direct completion: a pending or blocked task records its result in one write. It starts a run, as an
            # assignment does, so a paused cycle refuses it; a running task's own result is still accepted.
            if doc['state'] == 'paused':
                raise CycleError('resume before recording a new run; a paused cycle accepts only the result of a running task')
            _startable(doc, task)
            if args.status == 'done':
                _adr_dependencies_met(repo, doc, task)
            # A claim an interrupted write left for this cycle and task is certainly this task's own.
            for checkout, claim in list(claims.items()):
                if (claim.get('cycle'), claim.get('task')) == (doc['id'], task['id']):
                    del claims[checkout]
            moment = now()
            attempt = {'run': args.run, 'owner': args.owner, 'checkout': None, 'started_at': moment,
                       'ended_at': moment, 'outcome': args.status, 'summary': summary}
            linked = getattr(args, 'checkout', None)
            if (args.status == 'done' and task['kind'] == 'implementation' and linked
                    and Path(linked).resolve() != Path(repo).resolve()):
                # Work finished in a linked worktree is bound to that worktree and its commit, as at working to done.
                attempt['checkout'] = _linked_checkout(repo, linked)
                _record_commit(repo, attempt)
                task['checkout'] = attempt['checkout']
            task.update(owner=args.owner, run=args.run, status=args.status, summary=summary)
            task['attempts'].append(attempt)
    if doc['state'] == 'planning':
        doc['state'] = 'working'


def apply_batch(repo, doc, value, claims):
    """Apply task updates, then check observations, as one write.

    The entries change the in-memory record and the transaction's claims. One refused entry
    raises, so the record is not written and the claims are restored."""
    if not isinstance(value, dict) or set(value) - {'tasks', 'checks'}:
        raise CycleError('batch accepts only tasks and checks')
    tasks, checks = value.get('tasks', []), value.get('checks', [])
    if not isinstance(tasks, list) or not isinstance(checks, list) or not (tasks or checks):
        raise CycleError('batch requires a list of tasks, a list of checks, or both')
    for index, entry in enumerate(tasks):
        if (not isinstance(entry, dict) or set(entry) - {'task', 'owner', 'run', 'status', 'checkout', 'summary'}
                or not {'task', 'owner', 'run', 'status'} <= set(entry)):
            raise CycleError(f'batch task {index} requires task, owner, run and status, with optional checkout and summary')
        try:
            task_update(repo, doc, SimpleNamespace(**{'checkout': None, 'summary': None, **entry}), claims)
        except CycleError as exc:
            raise CycleError(f"batch task {index} ({entry['task']}): {exc}") from exc
    for index, observation in enumerate(checks):
        try:
            record_check(doc, observation)
        except CycleError as exc:
            raise CycleError(f'batch check {index}: {exc}') from exc


def record_check(doc, observation):
    allowed = {'check_id', 'executed_command', 'tested_revision', 'result', 'summary', 'reason', 'reuse'}
    if not isinstance(observation, dict) or set(observation) - allowed:
        raise CycleError('local observation has unknown fields; use the compact local-check shape')
    entry = {key: text(observation.get(key), 'check.' + key) for key in ('check_id', 'summary', 'reason')}
    entry['plan_revision'] = doc['plan']['revision']
    if observation.get('reuse'):
        previous = next((c for c in doc['checks'] if c['id'] == observation['reuse']), None)
        latest = [c for c in doc['checks'] if c['check_id'] == entry['check_id']]
        if (previous is None or previous['check_id'] != entry['check_id'] or previous['result'] != 'passed'
                or not latest or latest[-1]['result'] != 'passed'):
            raise CycleError('reuse requires a prior passing result with no later failed result')
        if any(observation.get(k) is not None for k in ('executed_command', 'tested_revision', 'result')):
            raise CycleError('reuse retains the original command, revision and result')
        entry.update({key: previous[key] for key in ('command', 'tested_revision', 'result')}, use='reused', reused_from=previous['id'])
    else:
        if observation.get('result') not in ('passed', 'failed'):
            raise CycleError('check requires a passed or failed observed result')
        entry.update(command=text(observation.get('executed_command'), 'check.command'),
                     tested_revision=text(observation.get('tested_revision'), 'check.tested_revision'),
                     result=observation['result'], use='executed')
    if doc['checks'] and all(doc['checks'][-1].get(k) == value for k, value in entry.items()):
        return
    doc['checks'].append({'id': 'LC-' + uuid.uuid4().hex, 'at': now(), **entry})


def request_review(repo, doc, reviewer):
    """The lead asks one named, independent reviewer to assess the committed code at HEAD."""
    if doc['state'] == 'paused':
        raise CycleError('resume before review')
    if not plan_complete(doc):
        raise CycleError('review needs a complete plan: record verification, council and tasks with plan first')
    text(reviewer, 'reviewer', 256)
    if reviewer in _implementers(doc):
        raise CycleError('reviewer must be independent of the lead and implementation owners')
    if not _clean_code(repo):
        raise CycleError('commit source edits before requesting review; uncommitted source cannot be bound to a reviewed range')
    _work_integrated(repo, doc)
    doc['review_request'] = {'reviewer': reviewer, 'plan_revision': doc['plan']['revision'],
                             'head_commit': git(repo, 'rev-parse', 'HEAD'), 'at': now()}
    doc['state'] = 'reviewing'


COMMIT_ID = re.compile(r'[0-9a-f]{40}(?:[0-9a-f]{24})?')


def _own_worktree(checkout, subject):
    """Git's worktree root for `checkout` when it is `checkout` itself, or None when it is no directory or no Git checkout.

    Git reads HEAD from the nearest enclosing worktree. A worktree nested inside another checkout whose `.git` link
    file is missing therefore reports the enclosing checkout's HEAD, so a directory Git resolves to another root
    refuses. `subject` opens the refusal."""
    path = Path(checkout)
    if not path.is_dir():
        return None
    try:
        root = runtime.checkout_root(path)
    except runtime.RuntimeRefusal:
        return None
    if root != path.resolve():
        raise CycleError(f'{subject} is not a Git worktree root: Git resolves it to the enclosing worktree {root}, whose HEAD '
                         f'is not this checkout\'s. When it is a linked worktree that lost its .git link, restore the link with '
                         f'`git worktree repair {path}` from the main checkout; otherwise name the worktree root')
    return root


def _linked_checkout(repo, checkout):
    """The worktree root a direct completion names, refused when it belongs to another repository."""
    root = _own_worktree(checkout, f'task result: {checkout}')
    if root is not None and runtime.common_directory(root) != runtime.common_directory(repo):
        raise CycleError('task checkout must belong to this Git repository')
    return str(root if root is not None else Path(checkout).resolve())


def _record_commit(repo, attempt):
    """Bind a done attempt that ran in another checkout to that checkout's HEAD commit.

    Review-start judges the recorded commit after the worktree is gone. A checkout whose HEAD cannot
    be read refuses the result, so removing a worktree before recording its result cannot unbind the work.
    A directory Git does not identify as its own worktree root refuses too, so an enclosing HEAD is never bound."""
    checkout = attempt.get('checkout')
    if not checkout or Path(checkout).resolve() == Path(repo).resolve():
        return
    root = _own_worktree(checkout, f'task result: {checkout}')
    result = subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', '--quiet', 'HEAD^{commit}'],
                            capture_output=True, text=True) if root is not None else None
    head = result.stdout.strip() if result is not None and result.returncode == 0 else ''
    if not COMMIT_ID.fullmatch(head):
        raise CycleError(f'task result: the attempt ran in {checkout}, whose HEAD commit cannot be read; record the result '
                         'before removing that worktree, or reassign the task to a checkout that holds the work')
    attempt['commit'] = head


def _work_integrated(repo, doc):
    """Refuse review-start while finished work recorded in another checkout is missing from this HEAD.

    Review admission takes the request head as the cycle's change, so work done in a linked worktree
    must be integrated first. A done attempt that recorded its commit is judged by that commit whether
    or not the worktree still exists: a commit this repository no longer holds, or one HEAD does not
    contain, refuses. While the worktree exists its live HEAD must also be contained, as before, and a
    directory Git does not identify as its own worktree root refuses. A record with no captured commit
    skips a checkout that no longer exists or is no Git checkout."""
    here = Path(repo).resolve()
    for task in doc['tasks']:
        if task['kind'] != 'implementation':
            continue
        done = [a for a in task['attempts'] if a.get('outcome') == 'done' and a.get('checkout')]
        if not done or Path(done[-1]['checkout']).resolve() == here:
            continue
        checkout = Path(done[-1]['checkout'])
        if 'commit' in done[-1]:
            recorded = done[-1]['commit']
            label = recorded[:12] if isinstance(recorded, str) else 'unreadable'
            if not isinstance(recorded, str) or not COMMIT_ID.fullmatch(recorded) or _commit(repo, recorded) is None:
                raise CycleError(f"review-start: task {task['id']} finished in {checkout} at commit {label}, which this repository "
                                 'no longer holds; restore and integrate that work, or revise the plan when it is abandoned'
                                 + _copied_route(doc, task, None))
            if not _is_ancestor(repo, recorded, 'HEAD'):
                raise CycleError(f"review-start: task {task['id']} finished in {checkout} at commit {label}, which this checkout "
                                 'does not contain; integrate it first, or revise the plan when its work is abandoned'
                                 + _copied_route(doc, task, label))
        root = _own_worktree(checkout, f"review-start: task {task['id']} ran in {checkout}, which")
        result = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True) if root is not None else None
        if result is None or result.returncode or not result.stdout.strip():
            continue
        head = result.stdout.strip()
        if not _is_ancestor(repo, head, 'HEAD'):
            raise CycleError(f"review-start: task {task['id']} ran in {checkout}, whose HEAD {head[:12]} this checkout does not contain; "
                             'integrate it first, or remove that worktree when its work is abandoned'
                             + _copied_route(doc, task, head[:12]))


def _copied_route(doc, task, commit):
    """The refusal's route for work a squash merge or cherry-pick integrated under new commit IDs.

    The ancestry check cannot see copied work, so the lead verifies the content and records the
    task's completion in the review checkout at the next run; review-start then judges that attempt."""
    verify = (f'`git diff {commit} HEAD` on the task\'s paths shows only later work' if commit
              else "the task's paths at HEAD hold the change")
    run = task['run'] + 1
    return (f'. When a squash merge or cherry-pick already integrated it, verify that HEAD holds the change ({verify}), '
            f"reassign the task in this checkout at the next run with `task {doc['id']} --task {task['id']} --owner OWNER "
            f'--run {run} --status working`, and record completion there with `--run {run} --status done`')


def _implementers(doc):
    implementers = {doc['lead'], *(t['owner'] for t in doc['tasks'] if t['kind'] == 'implementation')}
    implementers.update(a['owner'] for t in doc['tasks'] if t['kind'] == 'implementation' for a in t['attempts'])
    return implementers


def _is_ancestor(repo, older, newer):
    return subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', older, newer], capture_output=True).returncode == 0


def _admissible_head(repo, doc, request, report):
    """Refuse a reviewed head that lacks the cycle's change or whose reviewed paths changed after it.

    The cycle's change is the code committed when review was requested: review-start refuses
    uncommitted source, so the request head holds it. The reviewed head must descend from the request
    head or hold the same code. Later commits then refuse the report only when they change a reviewed
    path, the rule `applicability` applies at finish. When implementation work was recorded after the
    request, or the request names no head this repository holds, the request head need not hold the
    change, so any later code change refuses the report, as before this rule."""
    head, floor = report['head_commit'], request.get('head_commit')
    started = request['at']
    late = any((attempt.get('started_at') or '') >= started or (attempt.get('ended_at') or '') >= started
               for task in doc['tasks'] if task['kind'] == 'implementation' for attempt in task['attempts'])
    if late or not isinstance(floor, str) or _commit(repo, floor) is None:
        changed = code_changes(repo, head)
        if changed:
            cause = 'implementation work was recorded after review was requested' if late else 'the review request names no head in this repository'
            raise CycleError(f'stale review: {cause} and code changed after the reviewed head: ' + ', '.join(changed[:5]))
        return
    if not _is_ancestor(repo, floor, head) and code_changes(repo, head, floor):
        if not _is_ancestor(repo, floor, 'HEAD'):
            raise CycleError(f'the commit review was requested at ({floor[:12]}) is no longer in the history of HEAD; '
                             'run review-start again to bind the rewritten work')
        raise CycleError(f'review must name a head that holds the code committed when review was requested ({floor[:12]}); '
                         'name that head or a later one')
    changed = reviewed_path_changes(repo, {**doc, 'review': report})
    if changed:
        raise CycleError('stale review: ' + STALE_PATHS + ', '.join(changed[:5]))


def record_review(repo, doc, report, actor):
    if doc['state'] in ('paused', 'abandoned'):
        raise CycleError('review requires an active pilot')
    required = {'reviewer', 'plan_revision', 'base_commit', 'head_commit', 'verdict', 'blocking', 'acceptance', 'test_selection', 'summary'}
    if not isinstance(report, dict) or not required <= set(report) or set(report) - required - {'advisory', 'lessons', 'remaining'}:
        raise CycleError('review report has missing or unknown fields')
    text(report['reviewer'], 'reviewer', 256)
    if report['reviewer'] in _implementers(doc):
        raise CycleError('reviewer must be independent of the lead and implementation owners')
    if report['reviewer'] != actor:
        raise CycleError('the reviewer submits its own report: --actor must equal the report reviewer')
    if report['plan_revision'] != doc['plan']['revision']:
        raise CycleError('stale review: the report names a superseded plan revision')
    request = doc.get('review_request')
    if doc['state'] != 'reviewing' or not request or request['plan_revision'] != doc['plan']['revision']:
        raise CycleError('no review is requested for this plan revision; the lead runs review-start --reviewer first')
    if request['reviewer'] != actor:
        raise CycleError(f"review was requested from {request['reviewer']}; another reviewer needs a new review-start")
    if report['base_commit'] != doc['base_commit']:
        raise CycleError('review must name the original cycle base')
    head = git(repo, 'rev-parse', text(report['head_commit'], 'head_commit', 64) + '^{commit}')
    report = {**report, 'head_commit': head}
    if not reviewed_range_contained(repo, {**doc, 'review': report}):
        raise CycleError('review must name a head that descends from the cycle base and that HEAD contains')
    _admissible_head(repo, doc, request, report)
    if not _clean_code(repo):
        raise CycleError('commit source edits before final review; uncommitted source cannot be bound to the reviewed range')
    text(report['test_selection'], 'independent test selection assessment')
    text(report['summary'], 'completion summary')
    if report['verdict'] not in ('approve', 'changes-required') or not isinstance(report['blocking'], list):
        raise CycleError('review requires a verdict and blocking findings list')
    acceptance = report['acceptance']
    if (not isinstance(acceptance, list) or sorted(a.get('criterion') for a in acceptance if isinstance(a, dict)) != list(range(len(doc['plan']['acceptance'])))
            or any(type(a.get('met')) is not bool or not isinstance(a.get('evidence'), str) or not a['evidence'].strip() for a in acceptance)):
        raise CycleError('review must assess every acceptance criterion with an observed result and evidence')
    if report['verdict'] == 'approve':
        if report['blocking'] or any(not a['met'] for a in acceptance) or not checks_pass(doc):
            raise CycleError('approval requires met acceptance, no blocking findings and passing selected checks')
        if any(t['status'] != 'done' for t in doc['tasks'] if t['kind'] == 'implementation'):
            raise CycleError('implementation tasks remain unfinished')
        if not council_current(doc):
            raise CycleError('required council conclusion is unresolved')
    if doc['review']:
        doc['history'].append({'kind': 'review', 'review': doc['review']})
    doc['review'] = {**report, 'at': now(), 'requested_at': request['at'], 'submitted_by': actor, 'task_runs': _task_runs(doc),
                     'check_definitions': {ident: result['command'] for ident, result in selected_checks(doc).items() if result}}
    del doc['review_request']
    if report['verdict'] == 'approve':
        doc['state'] = 'reviewed'
        doc['completion'] = {'summary': report['summary'], 'lessons': report.get('lessons', []), 'remaining': report.get('remaining', []), 'at': now()}
    else:
        doc['state'] = 'working'
        # Each blocking finding becomes a task, and the review keeps the task ids in finding order, so a
        # plan revision can name the finding by its id (see plan_boundary).
        doc['review']['finding_tasks'] = []
        for index, finding in enumerate(report['blocking']):
            description = finding if isinstance(finding, str) else json.dumps(finding, sort_keys=True)
            ident = f'review-{len(doc["history"])}-{index + 1}'
            doc['tasks'].append(_task({'id': ident, 'description': description, 'council': False}, doc['lead'], False))
            doc['review']['finding_tasks'].append(ident)


DELIVERY_FACTS = ('pr', 'ci', 'merge', 'commit', 'published')


def record_delivery(doc, value):
    """Record observed PR, CI, merge and publication facts. They are independent of completion:
    they never complete a cycle, never reopen one, and completion never implies any of them."""
    if not isinstance(value, dict) or not value or set(value) - set(DELIVERY_FACTS):
        raise CycleError('delivery accepts only pr, ci, merge, commit and published facts')
    for key in ('pr', 'commit', 'published'):
        if value.get(key) is not None:
            text(value[key], 'delivery.' + key, 512)
    if value.get('ci', 'unknown') not in ('unknown', 'pending', 'passed', 'failed') or value.get('merge', 'unmerged') not in ('unmerged', 'merged'):
        raise CycleError('delivery.ci is unknown, pending, passed or failed; delivery.merge is unmerged or merged')
    doc['delivery'].update(value)


def finish(repo, doc, summary):
    """Complete the cycle. It needs finished work, passing selected checks and an approving
    independent review that applies to the final change; it needs no PR, CI, merge or branch."""
    if doc['state'] == 'completed':
        return  # a repeated finish changes nothing
    if doc['state'] in ('paused', 'abandoned'):
        raise CycleError('finish requires an active pilot')
    review = doc.get('review')
    unfinished = [t['id'] for t in doc['tasks'] if t['kind'] == 'implementation' and t['status'] != 'done']
    if unfinished:
        raise CycleError('finish requires every implementation task done; unfinished: ' + ', '.join(unfinished))
    failing = [ident for ident, result in selected_checks(doc).items() if result is None or result['result'] != 'passed']
    if failing:
        raise CycleError('finish requires every selected check to pass; missing or failed: ' + ', '.join(failing))
    if not review:
        raise CycleError('finish requires an independent review; none is recorded')
    if review['verdict'] != 'approve' or review['blocking']:
        raise CycleError('finish requires an approving review with no blocking finding')
    if review['plan_revision'] != doc['plan']['revision']:
        raise CycleError('obsolete review: it approved a superseded plan revision')
    if review['at'] < last_reopen(doc):
        raise CycleError('obsolete review: it predates the reopening; the repair needs its own review')
    if 'task_runs' in review and review['task_runs'] != _task_runs(doc):
        raise CycleError('obsolete review: an implementation task was added or run again after the approval')
    if any(not entry['met'] for entry in review['acceptance']):
        raise CycleError('finish requires every acceptance criterion met; the owner changes a criterion through a plan revision')
    if not council_current(doc):
        raise CycleError('required council conclusion is unresolved')
    applicable, reason = applicability(repo, doc)
    if not applicable:
        raise CycleError(f'obsolete review: {reason}')
    if doc['state'] != 'reviewed':
        raise CycleError('finish follows a recorded approving review; the cycle is ' + doc['state'])
    completion = dict(doc['completion'] or {})
    if summary:
        completion['summary'] = text(summary, 'completion summary')
    doc['completion'] = {**completion, 'completed_at': now(), 'review_head': review['head_commit'], 'reviewer': review['reviewer']}
    doc['state'] = 'completed'


def reopen(doc, reason, owner_instruction, definitions):
    """Reopen a completed cycle for a related repair, on the owner's recorded instruction.

    The earlier completion, checks and review stay in the record. Repair tasks are added, and the
    cycle completes again only after those tasks, their checks and a review newer than this reopening."""
    if doc['state'] != 'completed':
        raise CycleError('only a completed pilot reopens; the cycle is ' + doc['state'])
    text(reason, 'reopen reason')
    text(owner_instruction, "the owner's actual instruction to reopen")
    if not isinstance(definitions, list) or not definitions:
        raise CycleError('reopening requires at least one repair task')
    known = {t['id'] for t in doc['tasks']}
    tasks = []
    for definition in definitions:
        task = _task({**definition, 'council': False} if isinstance(definition, dict) else definition, doc['lead'], False)
        if task['id'] in known or task['kind'] != 'implementation':
            raise CycleError('a repair task needs a new id and is implementation work')
        known.add(task['id'])
        tasks.append(task)
    doc['history'].append({'kind': 'reopen', 'reason': reason, 'owner_instruction': owner_instruction,
                           'completion': doc['completion'], 'review': doc['review'], 'at': now()})
    doc['tasks'].extend(tasks)
    doc['state'] = 'working'


def council_subject(repo, doc):
    cfg = tree(repo)
    relative = f'adrs/councils/consultations/pilot-{doc["id"]}-plan-{doc["plan"]["revision"]}.json'
    path = contained(cfg.docs_root, relative)
    subject = {'format': 'crux.pilot-plan', 'cycle': doc['id'], 'plan': doc['plan'], 'tasks': [
        {key: task[key] for key in ('id', 'description', 'owner', 'depends_on', 'council', 'kind', 'adr_dependencies') if key in task}
        for task in doc['tasks']]}
    raw = _encoded(subject)
    if path.exists():
        frozen = json.loads(path.read_text())
        if frozen.get('plan') != doc['plan'] or frozen.get('cycle') != doc['id'] or frozen.get('format') != 'crux.pilot-plan':
            raise CycleError('frozen plan subject differs; preserve it and allocate a material plan revision')
    if not path.exists():
        runtime.atomic(path, subject)
    return relative


OWNER_ROUTE = "the owner's recorded words through plan --owner-approval"


def _finding_texts(finding):
    """The text a finding carries: the string itself, or every string value inside a structured finding."""
    if isinstance(finding, str):
        return [finding]
    if isinstance(finding, dict):
        return [part for value in finding.values() for part in _finding_texts(value)]
    if isinstance(finding, list):
        return [part for value in finding for part in _finding_texts(value)]
    return []


def names_path(finding, path):
    """Whether a finding names `path`: the exact path occurs in its text, bounded on both sides by a character
    that cannot continue a path. A longer path, a prefix of one or a path below a directory never names it;
    a full stop that ends a sentence still bounds it."""
    pattern = re.compile(r'(?<![A-Za-z0-9_./-])' + re.escape(path) + r'(?![A-Za-z0-9_/-])(?!\.[A-Za-z0-9_/-])')
    return any(pattern.search(part) for part in _finding_texts(finding))


def _recorded_finding(doc, ident):
    """The review and the blocking finding that a recorded review of this cycle stored under task id `ident`."""
    reviews = [entry['review'] for entry in doc['history'] if isinstance(entry.get('review'), dict)]
    reviews += [doc['review']] if doc.get('review') else []
    for review in reviews:
        ids, blocking = review.get('finding_tasks'), review.get('blocking')
        if (review.get('verdict') == 'changes-required' and isinstance(ids, list) and isinstance(blocking, list)
                and ident in ids and ids.index(ident) < len(blocking)):
            return review, blocking[ids.index(ident)]
    return None, None


def plan_boundary(doc, proposed, args):
    """Decide whether a plan revision may change scope or acceptance; return the scope extension to record.

    The owner's words admit any change. Without them, a revision admits a scope difference only when it names a
    blocking finding that the cycle's requested reviewer recorded for this cycle (--finding, the task id the
    finding became) and a criterion of the current plan (--criterion, zero-based); every added path appears in
    that finding, no scope entry is removed or reordered and acceptance is unchanged. Whether the criterion
    requires the fix is the next review's judgement, not the writer's."""
    owner = args.owner_approval
    finding, criterion = getattr(args, 'finding', None), getattr(args, 'criterion', None)
    old_scope, scope = doc['plan']['scope'], proposed.get('scope')
    acceptance_changed = proposed.get('acceptance') != doc['plan']['acceptance']
    if finding is None and criterion is None:
        if scope != old_scope or acceptance_changed:
            if not isinstance(owner, str) or not owner.strip() or len(owner) > 4000:
                raise CycleError(f'a scope or acceptance change needs {OWNER_ROUTE}; a scope addition may instead name '
                                 'a blocking review finding with --finding and the criterion it serves with --criterion')
        return None
    if owner is not None:
        raise CycleError("name either the owner's words (--owner-approval) or a review finding (--finding and --criterion), not both")
    if finding is None or criterion is None:
        raise CycleError('--finding and --criterion are given together: the blocking finding and the acceptance criterion it serves')
    if acceptance_changed:
        raise CycleError(f'a review finding changes no acceptance criterion; an acceptance change needs {OWNER_ROUTE}')
    if not isinstance(scope, list) or scope[:len(old_scope)] != old_scope:
        raise CycleError('a review finding only adds scope paths after the recorded ones; the revision removes or reorders '
                         f'a scope entry, which needs {OWNER_ROUTE}')
    added = scope[len(old_scope):]
    if not added:
        raise CycleError('the revision adds no path to scope; --finding admits only a scope addition')
    if any(not isinstance(path, str) or not path.strip() for path in added) or len(set(scope)) != len(scope):
        raise CycleError('each added scope path is a distinct non-empty string not already in scope')
    acceptance = doc['plan']['acceptance']
    if type(criterion) is not int or not 0 <= criterion < len(acceptance):
        raise CycleError(f'--criterion names a zero-based acceptance criterion of the current plan, 0 to {len(acceptance) - 1}')
    text(finding, 'finding', 256)
    review, body = _recorded_finding(doc, finding)
    if review is None:
        raise CycleError(f'{finding} is no blocking finding of a review recorded for this cycle; a lead note, task or '
                         f'check observation is no finding, and a scope addition without one needs {OWNER_ROUTE}')
    reviewer = review.get('reviewer')
    if not review.get('requested_at') or review.get('submitted_by') != reviewer or reviewer in _implementers(doc):
        raise CycleError(f"{finding} was not recorded by the cycle's requested independent reviewer; a scope addition "
                         f'without one needs {OWNER_ROUTE}')
    missing = [path for path in added if not names_path(body, path)]
    if missing:
        raise CycleError(f'finding {finding} does not name {", ".join(missing)}; add only the paths the finding names, '
                         f'or use {OWNER_ROUTE}')
    return {'finding': finding, 'reviewer': reviewer, 'review_at': review.get('at'),
            'text': body if isinstance(body, str) else json.dumps(body, sort_keys=True),
            'criterion': criterion, 'criterion_text': acceptance[criterion], 'paths': added}


def mutate(repo, identity, actor, expected, action, args):
    # A write that can change checkout claims holds the runtime lock around the record write.
    claiming = action in ('task', 'batch', 'resume', 'recover', 'finish', 'abandon')
    transaction = claims_transaction(repo) if claiming else nullcontext((None, None))
    with transaction as (claims, flush), \
            locked_record(repo, identity, actor, expected, role='reviewer' if action == 'review' else 'lead', before_write=flush) as doc:
        if claiming:
            # First settle what an interrupted earlier write of this pilot may have left.
            args.recovered = reconcile_claims(doc, claims)
        if action == 'recover':
            return {'recovered': args.recovered, 'revision': doc['revision']}
        if doc.get('kind') == 'release' and action in ('task', 'batch', 'plan', 'review-start', 'review', 'finish', 'reopen'):
            raise CycleError(f"{identity} is a release record: release.py's record functions advance it and its ledger stays authoritative; the ordinary {action} write is refused")
        if doc['state'] == 'abandoned':
            raise CycleError('abandoned pilots do not restart')
        if doc['state'] == 'completed' and action not in ('delivery', 'finish', 'reopen'):
            raise CycleError('a completed pilot takes delivery facts only; reopen it on the owner\'s instruction, or create a linked cycle with --follows')
        if action == 'task':
            task_update(repo, doc, args, claims)
        elif action == 'check':
            record_check(doc, args.value)
        elif action == 'batch':
            apply_batch(repo, doc, args.value, claims)
        elif action == 'plan':
            proposed = deepcopy(args.value)
            definitions = proposed.pop('tasks', None)
            proposed.pop('revision', None)
            # Goal, scope and acceptance a revision omits stay as recorded, so a cycle started without a
            # plan file is planned by naming only verification, council and tasks.
            for key in ('goal', 'scope', 'acceptance'):
                proposed.setdefault(key, doc['plan'][key])
            extension = plan_boundary(doc, proposed, args)
            entry = {'kind': 'plan', 'plan': doc['plan'], 'reason': text(args.reason, 'plan change reason'),
                     'owner_approval': args.owner_approval, 'at': now()}
            if extension:
                entry['scope_extension'] = extension
            # A revision supersedes an open review request: the request moves into this history entry, so the
            # record keeps it and no reader takes the cycle for one still in review.
            withdrawn = doc.pop('review_request', None)
            if withdrawn:
                entry['review_request'] = withdrawn
            doc['history'].append(entry)
            proposed.setdefault('scrutiny', default_scrutiny(repo))
            doc['plan'] = {'revision': doc['plan']['revision'] + 1, **proposed}
            if definitions is not None:
                old = {t['id']: t for t in doc['tasks']}
                for definition in definitions:
                    _task(definition, doc['lead'], council_needed(doc))
                    previous = old.get(definition['id'])
                    if previous and previous['status'] == 'working' and any(previous.get(k) != v for k, v in definition.items()):
                        raise CycleError('reconcile a working task before changing its definition or owner')
                if any(t['status'] == 'working' and t['id'] not in {d['id'] for d in definitions} for t in old.values()):
                    raise CycleError('cannot remove a working task; reconcile it first')
                if any(t['run'] > 0 and t['id'] not in {d['id'] for d in definitions} for t in old.values()):
                    raise CycleError('retain started tasks and their author/outcome history')
                if any(t['id'] in old and old[t['id']]['run'] > 0 and t.get('kind', old[t['id']]['kind']) != old[t['id']]['kind'] for t in definitions):
                    raise CycleError('retain the kind of started tasks to preserve implementation author history')
                doc['tasks'] = [{**old[t['id']], **t} if t['id'] in old else _task(t, doc['lead'], council_needed(doc)) for t in definitions]
            # A revised plan returns the cycle to planning. A paused cycle stays paused with its blocker, and only
            # resume returns it, to planning; owner words and finding scope additions are recorded while paused.
            if doc['state'] == 'paused':
                doc['resume_state'] = 'planning'
            else:
                doc.pop('resume_state', None)  # an earlier writer could leave one behind on an unpaused cycle
                doc['state'] = 'planning'
        elif action == 'review-start':
            request_review(repo, doc, args.reviewer)
        elif action == 'review':
            record_review(repo, doc, args.value, actor)
        elif action == 'delivery':
            record_delivery(doc, args.value)
        elif action == 'finish':
            finish(repo, doc, getattr(args, 'summary', None))
        elif action == 'reopen':
            reopen(doc, args.reason, args.owner_instruction, args.value)
        elif action == 'pause':
            text(args.reason, 'pause reason')
            if doc['state'] != 'paused':
                doc['resume_state'] = doc['state']
            doc['state'] = 'paused'
            doc['blockers'] = [args.reason]
        elif action == 'resume':
            if doc['state'] != 'paused':
                raise CycleError('pilot is not paused')
            text(args.reconcile, 'resume reconciliation of Git status, diff and host state')
            text(args.reason, 'resume reason')
            for task in doc['tasks']:
                if task['status'] == 'working' and task['kind'] == 'implementation':
                    _claim(repo, doc, task, task['checkout'], task['owner'], task['run'], claims)
            doc['history'].append({'kind': 'resume', 'reason': args.reason, 'reconcile': args.reconcile, 'at': now()})
            doc['state'] = doc.pop('resume_state', 'working')
            doc['blockers'] = []
        elif action == 'abandon':
            text(args.reason, 'abandon reason')
            for task in doc['tasks']:
                if task['status'] == 'working':
                    raise CycleError('reconcile working tasks before abandonment; their checkout claims are retained')
            doc['state'] = 'abandoned'
            doc['completion'] = {'summary': args.reason, 'remaining': [t['id'] for t in doc['tasks'] if t['status'] != 'done'], 'at': now()}
        elif action == 'council-subject':
            relative = council_subject(repo, doc)
            return {'subject': relative, 'identity': 'pilot:' + doc['id'] + ':plan', 'purpose': 'consultation',
                    'next': 'Run cycle-council.py --purpose consultation --subject SUBJECT --identity IDENTITY --question QUESTION_FILE with the returned values and a question file; retain the approved result and lead response.'}
        elif action == 'council':
            import cycle_council
            subject = council_subject(repo, doc)
            text(args.response, 'lead response to substantive council findings')
            cycle_council.validate_approval(repo, args.record, purpose='consultation', subject=subject)
            doc['councils'].append({'plan_revision': doc['plan']['revision'], 'subject': subject, 'record': args.record,
                                    'outcome': 'approved', 'response': args.response, 'at': now()})
        else:
            raise CycleError('unknown pilot milestone')
    return load_pilot(repo, identity)


COMMANDS = ('create', 'show', 'plan', 'task', 'check', 'batch', 'review-start', 'review', 'delivery', 'finish', 'reopen', 'recover',
            'pause', 'resume', 'abandon', 'council-subject', 'council')


def add_commands(operations):
    """Register the writer commands on any subparsers object: top level and under `pilot` take the same arguments."""
    create_parser = operations.add_parser('create')
    create_parser.add_argument('--title', required=True)
    create_parser.add_argument('--lead', required=True)
    create_parser.add_argument('--plan', help='JSON plan definition; without it, --goal, --scope and --acceptance start the cycle in planning')
    create_parser.add_argument('--goal', help='without --plan: the goal')
    create_parser.add_argument('--scope', action='append', help='without --plan: one scope path; repeatable')
    create_parser.add_argument('--acceptance', action='append', help='without --plan: one acceptance criterion; repeatable')
    create_parser.add_argument('--follows', help='an existing cycle this one is linked to, such as the completed cycle it repairs')
    create_parser.add_argument('--release-list', choices=sorted(RELEASE_LISTS), help='create a release record with this fixed step list; needs --version')
    create_parser.add_argument('--version', help='with --release-list: the release version, X.Y.Z')
    show = operations.add_parser('show')
    show.add_argument('identity')
    show.add_argument('--full', action='store_true')
    for name in ('plan', 'task', 'check', 'batch', 'review-start', 'review', 'delivery', 'finish', 'reopen', 'recover', 'pause', 'resume', 'abandon', 'council-subject', 'council'):
        command = operations.add_parser(name)
        command.add_argument('identity')
        command.add_argument('--actor', required=True)
        command.add_argument('--expect-revision', type=int, required=True)
        if name in ('plan', 'check', 'batch', 'review', 'delivery', 'reopen'):
            command.add_argument('--file', required=True)
        if name == 'plan':
            command.add_argument('--reason', required=True)
            command.add_argument('--owner-approval', help="the owner's own words approving a scope or acceptance change")
            command.add_argument('--finding', help='without owner words: the task id of the blocking review finding that names each added scope path')
            command.add_argument('--criterion', type=int, help='with --finding: the zero-based acceptance criterion of the current plan the fix serves')
        if name == 'task':
            command.add_argument('--task', required=True)
            command.add_argument('--owner', required=True)
            command.add_argument('--run', type=int, required=True)
            command.add_argument('--status', choices=TASK_STATES[1:], required=True)
            command.add_argument('--checkout')
            command.add_argument('--summary')
        if name == 'finish':
            command.add_argument('--summary', help='a concise completion summary; the review summary stands when omitted')
        if name == 'reopen':
            command.add_argument('--reason', required=True)
            command.add_argument('--owner-instruction', required=True, help="the owner's own words authorizing the reopening")
        if name == 'review-start':
            command.add_argument('--reviewer', required=True, help='the independent reviewer asked to submit the verdict')
        if name in ('pause', 'resume', 'abandon'):
            command.add_argument('--reason', required=True)
        if name == 'resume':
            command.add_argument('--reconcile', required=True)
        if name == 'council':
            command.add_argument('--record', required=True)
            command.add_argument('--response', required=True)


def add_parser(subparsers):
    """The `pilot` alias: the same commands one level down, printing the payload under `pilot`."""
    pilot = subparsers.add_parser('pilot', help='alias of the top-level writer commands: pilot SUB is SUB')
    add_commands(pilot.add_subparsers(dest='pilot_action', required=True))


LEGACY_NOTE = ('{identity} is a legacy typed-engine record: it is read-only through cycle.py show and status, '
               'and nothing changed.')


def _is_legacy(repo, identity):
    """Whether `identity` names a record with no `format` field, a typed-engine record the writer never reads or writes."""
    import cycle_history
    if not isinstance(identity, str) or not cycle_history.ID.fullmatch(identity):
        return False
    path = contained(tree(repo).docs_root, f'cycles/{identity}/cycle.json')
    if path.is_symlink() or not path.is_file():
        return False
    try:
        return cycle_history.is_legacy(json.loads(path.read_text(encoding='utf-8')))
    except (OSError, ValueError):
        return False


def show_legacy(repo, identity, full):
    """Render a legacy record through the read-only history reader: bounded facts, or the raw record with `--full`."""
    import cycle_history
    doc = cycle_history.load_record(repo, identity)
    cfg = tree(repo)
    return doc if full else cycle_history.facts(doc, lambda rel: json.loads(contained(cfg.docs_root, rel).read_text(encoding='utf-8')))


def _create_definition(args):
    """The definition `create` writes: the --plan file, or the goal, scope and acceptance flags alone."""
    flags = [name for name in ('goal', 'scope', 'acceptance') if getattr(args, name, None)]
    if args.plan:
        if flags:
            raise CycleError('--plan holds the whole definition; drop ' + ', '.join('--' + name for name in flags))
        return json.loads(Path(args.plan).read_text())
    if len(flags) != 3:
        raise CycleError('create needs --plan FILE, or --goal, --scope and --acceptance to start the cycle in planning')
    return {'goal': args.goal, 'scope': list(args.scope), 'acceptance': list(args.acceptance)}


def cli(args):
    """Run one writer command from parsed arguments; the `pilot` route prints under `pilot`, the top-level route under `cycle`."""
    repo = Path(args.repo_root).resolve()
    pilot_route = hasattr(args, 'pilot_action')
    key = 'pilot' if pilot_route else 'cycle'
    try:
        action = args.pilot_action if pilot_route else args.command
        if action != 'create' and _is_legacy(repo, args.identity):
            if action == 'show':
                print(json.dumps({'ok': True, 'legacy': True, 'cycle': show_legacy(repo, args.identity, args.full)}))
                return 0
            raise CycleError(LEGACY_NOTE.format(identity=args.identity))
        if action == 'create':
            if getattr(args, 'version', None) and not getattr(args, 'release_list', None):
                raise CycleError('--version belongs to a release record: pass --release-list beta or official')
            if getattr(args, 'release_list', None):
                if args.plan or args.follows or not args.version:
                    raise CycleError('a release record takes --version with --goal, --scope and --acceptance, and no --plan or --follows')
                definition = _create_definition(args)
                doc = create_release(repo, args.release_list, args.version, args.title, definition['goal'], definition['scope'],
                                     definition['acceptance'], args.lead)
            else:
                doc = create(repo, args.title, args.lead, _create_definition(args), follows=args.follows)
        elif action == 'show':
            doc = load_pilot(repo, args.identity)
        else:
            if hasattr(args, 'file'):
                args.value = json.loads(Path(args.file).read_text())
            doc = mutate(repo, args.identity, args.actor, args.expect_revision, action, args)
            if action in ('council-subject', 'recover'):
                print(json.dumps({'ok': True, **doc}))
                return 0
        result = doc if getattr(args, 'full', False) else summarize(repo, doc)
        payload = {'ok': True, key: result}
        if getattr(args, 'recovered', None):
            payload['recovered'] = args.recovered
        if action == 'delivery' and args.value.get('ci') == 'failed':
            payload['offer'] = ('CI failure recorded; the cycle state is unchanged. Offer the owner the choice: reopen this cycle for the '
                                'related repair (reopen, with the owner\'s instruction), or create a linked cycle (create --follows '
                                + doc['id'] + ') when the repair deserves its own scope.')
        print(json.dumps(payload))
        return 0
    except (CycleError, runtime.RuntimeRefusal, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 1
