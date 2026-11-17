"""Opt-in cycle pilot: one lead, milestone records, native delegation and independent review."""
from contextlib import contextmanager, nullcontext
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace
import uuid

import cycle_runtime as runtime
from cycle_workflow import CycleError, contained, now, tree

FORMAT = 'crux.cycle.vNext'
STATES = ('planning', 'working', 'reviewing', 'reviewed', 'completed', 'paused', 'abandoned')
TASK_STATES = ('pending', 'working', 'blocked', 'done')
# Records of the work under the documentation tree; a change here is never reviewed code.
BOOKKEEPING = ('cycles', 'adrs/councils', 'journal', 'log', 'queue')
SCHEMA = Path(__file__).resolve().parent.parent / 'schemas/cycle-pilot.schema.json'


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
    validate(record)
    if record['id'] != identity:
        raise CycleError('pilot record identity does not match its directory')
    return record


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
    text(plan['council']['reason'], 'plan.council.reason')
    checks = plan['verification']['checks']
    if not checks or len({c['id'] for c in checks}) != len(checks):
        raise CycleError('verification requires distinct selected checks')
    for check in checks:
        text(check['id'], 'verification check id', 128)
        text(check['rationale'], 'verification rationale')
    text(plan['verification']['gaps'], 'verification.gaps')
    tasks = {t['id']: t for t in doc['tasks']}
    if len(tasks) != len(doc['tasks']) or not tasks:
        raise CycleError('pilot requires distinct tasks')
    for task in tasks.values():
        text(task['id'], 'task id', 128)
        if not re.fullmatch('[a-z0-9][a-z0-9-]*', task['id']):
            raise CycleError('task ids use lowercase letters, digits and hyphens')
        text(task['description'], 'task description')
        text(task['owner'], 'task owner', 256)
        if task['council'] and not plan['council']['needed']:
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
    if not isinstance(spec, dict) or set(spec) - {'id', 'description', 'owner', 'depends_on', 'council', 'kind'}:
        raise CycleError('task definition has unknown fields')
    return {'id': spec['id'], 'description': spec['description'], 'owner': spec.get('owner', lead),
            'depends_on': spec.get('depends_on', []), 'council': spec.get('council', council),
            'kind': spec.get('kind', 'implementation'), 'run': 0, 'status': 'pending', 'checkout': None,
            'summary': '', 'attempts': []}


def _new_record(identity, base, title, lead, specification, queue, follows=None):
    spec = deepcopy(specification)
    tasks = spec.pop('tasks', [])
    if set(spec) - {'goal', 'scope', 'acceptance', 'verification', 'council'}:
        raise CycleError('plan definition has unknown fields')
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
    _new_record('CYC-0000', git(repo, 'rev-parse', 'HEAD'), title, lead, specification, None)


def create(repo, title, lead, specification, queue=None, follows=None):
    """Allocate in the main checkout before branching; no source or record commit is made.

    `queue` is the starting item and token when the queue writer starts this pilot. `follows` names
    an existing cycle this one is linked to, for a repair that deserves its own scope."""
    from cycle_workflow import locked
    base = git(repo, 'rev-parse', 'HEAD')
    if follows is not None and not path_of(repo, follows).is_file():
        raise CycleError(f'--follows names no cycle record: {follows}')
    _new_record('CYC-0000', base, title, lead, specification, queue, follows)
    with locked(repo) as (cfg, directory):
        identity = runtime.allocate(cfg, directory)
        doc = _new_record(identity, base, title, lead, specification, queue, follows)
        directory.joinpath(identity).mkdir()
        runtime.atomic(path_of(repo, identity), doc)
        return doc


@contextmanager
def locked_record(repo, identity, actor, expected, role='lead', before_write=None):
    """Lock, load and admit one writer. The lead writes every milestone except the review verdict.

    `role='reviewer'` admits any actor but the lead; `record_review` then binds that actor to the
    requested reviewer. `expected=None` skips the revision check for the queue binding, which is
    idempotent and runs under the queue lock."""
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
        elif actor != doc['lead']:
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
    `reconcile_claims` removes such a leftover on the next write to the same pilot. A refusal or
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
    return {selection['id']: latest.get(selection['id']) for selection in doc['plan']['verification']['checks']}


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


def applicability(repo, doc):
    """Whether the recorded approving review still covers this cycle's final change: (bool, reason).

    The finish gate and every status view read this one function. The review applies while every
    reviewed path holds, in this checkout, the content it had at the reviewed head. Committed and
    uncommitted changes to those paths both count. Other paths do not: commits elsewhere on a
    shared branch are other work. Bookkeeping never counts, and a queue binding plays no part.
    The comparison is by content, so it is a path-preservation boundary: it does not detect a
    later change of the same cycle that touches only new paths."""
    if not review_recorded(doc):
        return False, 'no approving review of this plan revision is recorded with passing selected checks and finished implementation tasks'
    head = doc['review']['head_commit']
    try:
        if _commit(repo, head) is None:
            return False, f'the reviewed head {head[:12]} is not in this repository'
        paths = reviewed_paths(repo, doc)
        changed = [p for p in git(repo, 'diff', '--no-renames', '--name-only', '-z', head, '--',
                                  *(':(literal)' + path for path in paths)).split('\0') if p] if paths else []
        if changed:
            return False, 'reviewed paths changed after the reviewed head: ' + ', '.join(changed[:5])
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


def council_current(doc):
    return (not doc['plan']['council']['needed'] or any(c['plan_revision'] == doc['plan']['revision']
            and c['outcome'] == 'approved' for c in doc['councils']))


def blockers(doc):
    result = list(doc['blockers'])
    result += [f"{t['id']}: {t['summary']}" for t in doc['tasks'] if t['status'] == 'blocked']
    if not council_current(doc):
        result.append('council required for dependent tasks; no approved result for this plan revision')
    return list(dict.fromkeys(result))


def summarize(repo, doc):
    facts = status_facts(repo, doc)
    return {'format': FORMAT, 'id': doc['id'], 'revision': doc['revision'], 'title': doc['title'],
            'state': doc['state'],
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
        raise CycleError(f'checkout is owned by {claim}; use a distinct worktree or reconcile its owner')
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
            task.update(status=args.status, summary=summary)
            task['attempts'][-1].update(outcome=args.status, summary=summary, ended_at=now())
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
            # Direct completion: a pending or blocked task records its result in one write.
            _startable(doc, task)
            # A claim an interrupted write left for this cycle and task is certainly this task's own.
            for checkout, claim in list(claims.items()):
                if (claim.get('cycle'), claim.get('task')) == (doc['id'], task['id']):
                    del claims[checkout]
            moment = now()
            task.update(owner=args.owner, run=args.run, status=args.status, summary=summary)
            task['attempts'].append({'run': args.run, 'owner': args.owner, 'checkout': None, 'started_at': moment,
                                     'ended_at': moment, 'outcome': args.status, 'summary': summary})
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
    text(reviewer, 'reviewer', 256)
    if reviewer in _implementers(doc):
        raise CycleError('reviewer must be independent of the lead and implementation owners')
    if not _clean_code(repo):
        raise CycleError('commit source edits before requesting review; uncommitted source cannot be bound to a reviewed range')
    doc['review_request'] = {'reviewer': reviewer, 'plan_revision': doc['plan']['revision'],
                             'head_commit': git(repo, 'rev-parse', 'HEAD'), 'at': now()}
    doc['state'] = 'reviewing'


def _implementers(doc):
    implementers = {doc['lead'], *(t['owner'] for t in doc['tasks'] if t['kind'] == 'implementation')}
    implementers.update(a['owner'] for t in doc['tasks'] if t['kind'] == 'implementation' for a in t['attempts'])
    return implementers


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
    changed = code_changes(repo, head)
    if changed:
        raise CycleError('stale review: code changed after the reviewed head: ' + ', '.join(changed[:5]))
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
        for index, finding in enumerate(report['blocking']):
            description = finding if isinstance(finding, str) else json.dumps(finding, sort_keys=True)
            doc['tasks'].append(_task({'id': f'review-{len(doc["history"])}-{index + 1}', 'description': description,
                                       'council': False}, doc['lead'], False))


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
        {key: task[key] for key in ('id', 'description', 'owner', 'depends_on', 'council', 'kind')} for task in doc['tasks']]}
    raw = _encoded(subject)
    if path.exists():
        frozen = json.loads(path.read_text())
        if frozen.get('plan') != doc['plan'] or frozen.get('cycle') != doc['id'] or frozen.get('format') != 'crux.pilot-plan':
            raise CycleError('frozen plan subject differs; preserve it and allocate a material plan revision')
    if not path.exists():
        runtime.atomic(path, subject)
    return relative


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
            if any(proposed.get(k) != doc['plan'].get(k) for k in ('scope', 'acceptance')):
                text(args.owner_approval, 'owner approval of scope or acceptance changes')
            doc['history'].append({'kind': 'plan', 'plan': doc['plan'], 'reason': text(args.reason, 'plan change reason'),
                                   'owner_approval': args.owner_approval, 'at': now()})
            doc['plan'] = {'revision': doc['plan']['revision'] + 1, **proposed}
            if definitions is not None:
                old = {t['id']: t for t in doc['tasks']}
                for definition in definitions:
                    _task(definition, doc['lead'], doc['plan']['council']['needed'])
                    previous = old.get(definition['id'])
                    if previous and previous['status'] == 'working' and any(previous.get(k) != v for k, v in definition.items()):
                        raise CycleError('reconcile a working task before changing its definition or owner')
                if any(t['status'] == 'working' and t['id'] not in {d['id'] for d in definitions} for t in old.values()):
                    raise CycleError('cannot remove a working task; reconcile it first')
                if any(t['run'] > 0 and t['id'] not in {d['id'] for d in definitions} for t in old.values()):
                    raise CycleError('retain started tasks and their author/outcome history')
                if any(t['id'] in old and old[t['id']]['run'] > 0 and t.get('kind', old[t['id']]['kind']) != old[t['id']]['kind'] for t in definitions):
                    raise CycleError('retain the kind of started tasks to preserve implementation author history')
                doc['tasks'] = [{**old[t['id']], **t} if t['id'] in old else _task(t, doc['lead'], doc['plan']['council']['needed']) for t in definitions]
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


def add_parser(subparsers):
    pilot = subparsers.add_parser('pilot', help='explicit opt-in smaller-cycle pilot; preserves legacy and release workflows')
    operations = pilot.add_subparsers(dest='pilot_action', required=True)
    create_parser = operations.add_parser('create')
    create_parser.add_argument('--title', required=True)
    create_parser.add_argument('--lead', required=True)
    create_parser.add_argument('--plan', required=True)
    create_parser.add_argument('--follows', help='an existing cycle this one is linked to, such as the completed cycle it repairs')
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
            command.add_argument('--owner-approval')
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


def cli(args):
    repo = Path(args.repo_root).resolve()
    try:
        action = args.pilot_action
        if action == 'create':
            doc = create(repo, args.title, args.lead, json.loads(Path(args.plan).read_text()), follows=args.follows)
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
        payload = {'ok': True, 'pilot': result}
        if getattr(args, 'recovered', None):
            payload['recovered'] = args.recovered
        if action == 'delivery' and args.value.get('ci') == 'failed':
            payload['offer'] = ('CI failure recorded; the cycle state is unchanged. Offer the owner the choice: reopen this cycle for the '
                                'related repair (pilot reopen, with the owner\'s instruction), or create a linked cycle (pilot create --follows '
                                + doc['id'] + ') when the repair deserves its own scope.')
        print(json.dumps(payload))
        return 0
    except (CycleError, runtime.RuntimeRefusal, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 1
