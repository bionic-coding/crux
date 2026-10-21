"""A persistent, ordered queue of requested work that commander turns into cycles one at a time.

The queue is one YAML file, `<docs_dir>/queue/cycles.yaml`. List order is execution order.
An item holds the request (title, outcome, scope, acceptance, suggested type) and where it
stands (pending, held, starting, started). The outcome of a started item is never stored:
readers derive it from the cycle's own record, so the queue and the cycle views cannot
disagree.

Authorization is a single record of the owner's quoted instruction plus the item ids it
captured. It authorizes starting cycles only: never a push, a publish, a release, a longer
pass limit or an approval of a decision. Each started cycle keeps its own type, pass limit
and stop points.

Starting an item is a recoverable two-step write. `start_next` records an intent (state
`starting` with a random token), calls `cycle_workflow.create` with that token as origin,
then records the cycle id. A crash between the steps leaves the intent; the next call scans
the cycle records for the token and adopts the cycle, or cancels the intent when none carries it.

Lock order is the queue lock (`<docs_dir>/queue/.lock`), then the cycles lock that `create`
takes itself. Nothing takes the queue lock while holding the cycles lock. Readers take no lock.

Known limits:
- The 500-item cap counts every item, including started ones, for the queue's lifetime.
- `start_next` considers only cycles that the queue started; other cycles are not its concern.
- The lock guards overlapping invocations and crashes, not deliberate tampering.
- A CLI rewrite drops YAML comments. The owner may edit the file by hand; every read validates it.
- The writer cannot verify that an authorization instruction is the owner's own words; that
  rule rests on the commander contract.
- The queue lock file is not gitignored by downstream trees, as the cycles lock is not.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
import fcntl
import json
import re
import uuid
from pathlib import Path

from bionic_config import BionicConfigError
from cycle_workflow import CycleError, ID, PHASES, atomic_bytes, contained, create, load, now, tree, validate as validate_cycle

FORMAT = 'crux.cycle-queue'
QUEUE_ID = re.compile(r'^Q-[0-9]{4,}$')
TYPE = re.compile(r'^[a-z][a-z-]{1,30}$')
TOKEN = re.compile(r'^[0-9a-f]{32}$')
DATE = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
MAX_ITEMS = 500
MAX_TITLE = 200
MAX_TEXT = 2000
MAX_LIST = 50
UNSTARTED = ('pending', 'held')
ITEM_KEYS = ('id', 'title', 'outcome', 'suggested_type', 'scope', 'acceptance', 'depends_on', 'references', 'state', 'hold_reason', 'start_token', 'cycle', 'added_at', 'started_at')
AUTH_KEYS = ('instruction', 'kind', 'count', 'scope', 'started', 'authorized_at', 'date')
ENDED_KEYS = ('ended_at', 'ended', 'reason')
TOP_KEYS = ('format', 'format_version', 'next_number', 'items', 'authorization', 'authorization_history')


class QueueError(CycleError):
    """A refusal: the request or the queue file is invalid. Exit 1."""


class QueueEnvError(CycleError):
    """An environment problem: an unreadable or unlockable path, or PyYAML missing. Exit 2."""


class QueueStop(QueueError):
    """start-next cannot proceed; the reason, item and detail tell the owner what to decide."""

    def __init__(self, reason, item, detail):
        super().__init__(f'{reason}: {detail}')
        self.reason, self.item, self.detail = reason, item, detail


def _bad(location, message):
    raise QueueError(f'{location}: {message}')


# -- storage ------------------------------------------------------------------

def _yaml():
    try:
        import yaml
    except ImportError as exc:
        raise QueueEnvError('PyYAML is unavailable; run this script through uv run') from exc
    return yaml


def queue_file(cfg):
    return contained(cfg.docs_root, 'queue/cycles.yaml')


def empty_queue():
    return {'format': FORMAT, 'format_version': 1, 'next_number': 1, 'items': [], 'authorization': None, 'authorization_history': []}


def _ordered(doc):
    def keyed(record, keys):
        return {k: record[k] for k in keys if k in record}
    out = keyed(doc, TOP_KEYS)
    out['items'] = [keyed(i, ITEM_KEYS) for i in doc['items']]
    out['authorization'] = keyed(doc['authorization'], AUTH_KEYS) if doc['authorization'] else None
    out['authorization_history'] = [keyed(h, AUTH_KEYS + ENDED_KEYS) for h in doc['authorization_history']]
    return out


def write_queue(cfg, doc):
    """Validate, then replace the file atomically with a fixed key order."""
    check_queue(doc)
    text = _yaml().safe_dump(_ordered(doc), sort_keys=False, default_flow_style=False, allow_unicode=True, width=100)
    atomic_bytes(queue_file(cfg), text.encode())


def parse_queue(text, label='queue file'):
    """Parse and validate queue text; every failure names the file, the location and the repair."""
    yaml = _yaml()
    repair = 'correct the file or restore it from git'
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise QueueError(f'{label}: not valid YAML ({type(exc).__name__}); {repair}') from exc
    try:
        if not isinstance(doc, dict):
            _bad('/', 'the queue must be a mapping')
        check_queue(doc, schema=True)
    except QueueError as exc:
        raise QueueError(f'{label}: {exc}; {repair}') from exc
    return doc


def read_queue(cfg):
    path = queue_file(cfg)
    if not path.exists():
        return empty_queue()
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError) as exc:
        raise QueueEnvError(f'cannot read {path}: {type(exc).__name__}') from exc
    return parse_queue(text, f'{cfg.docs_dir}/queue/cycles.yaml')


@contextmanager
def locked_queue(repo):
    cfg = tree(repo)
    try:
        directory = contained(cfg.docs_root, 'queue')
        directory.mkdir(exist_ok=True)
        stream = contained(directory, '.lock').open('a')
    except OSError as exc:
        raise QueueEnvError(f'cannot prepare the queue directory: {type(exc).__name__}') from exc
    with stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX)
        except OSError as exc:
            raise QueueEnvError(f'cannot lock the queue: {type(exc).__name__}') from exc
        yield cfg


# -- validation ---------------------------------------------------------------

def _check_text(location, item):
    for key, limit in (('title', MAX_TITLE), ('outcome', MAX_TEXT)):
        if not item[key].strip() or len(item[key]) > limit:
            _bad(f'{location}/{key}', f'must be non-blank and at most {limit} characters')
    for key in ('scope', 'acceptance'):
        values = item[key]
        if not 1 <= len(values) <= MAX_LIST:
            _bad(f'{location}/{key}', f'needs 1 to {MAX_LIST} entries')
        for value in values:
            if not value.strip() or len(value) > MAX_TEXT:
                _bad(f'{location}/{key}', f'entries must be non-blank and at most {MAX_TEXT} characters')
    if any(s.startswith(':') for s in item['scope']):
        _bad(f'{location}/scope', 'a scope path cannot use git pathspec magic')
    if item['hold_reason'] is not None and len(item['hold_reason']) > MAX_TEXT:
        _bad(f'{location}/hold_reason', f'at most {MAX_TEXT} characters')
    references = item.get('references', [])
    if not isinstance(references, list) or len(references) > MAX_LIST:
        _bad(f'{location}/references', f'must be a list of at most {MAX_LIST} entries')
    for value in references:
        if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT:
            _bad(f'{location}/references', f'entries must be non-blank strings of at most {MAX_TEXT} characters')
    if len(set(references)) != len(references):
        _bad(f'{location}/references', 'must not repeat a path')


def _check_authorization(record, location):
    kind, count = record['kind'], record['count']
    if not record['instruction'].strip():
        _bad(f'{location}/instruction', 'the owner instruction must not be blank')
    if (kind == 'next' and count != 1) or (kind == 'next-n' and not (isinstance(count, int) and count >= 1)) or (kind == 'queue' and count is not None):
        _bad(f'{location}/count', f'count {count!r} does not fit kind {kind}')
    if len(set(record['scope'])) != len(record['scope']) or len(set(record['started'])) != len(record['started']):
        _bad(location, 'scope and started must not repeat an id')
    if not set(record['started']) <= set(record['scope']):
        _bad(f'{location}/started', 'started ids must be a subset of scope')


def check_queue(doc, schema=False):
    """Cross-checks beyond the schema. `schema=True` validates the schema first (read time)."""
    if schema:
        from council_records import _validator
        validator = _validator()
        schema_doc = validator.load_schema(Path(__file__).parent.parent / 'schemas/cycle-queue.schema.json')
        errors = []
        validator.validate(doc, schema_doc, '#', '#', errors, 'queue')
        if errors:
            first = errors[0]
            _bad(first['instance_path'].replace('#', '', 1) or '/', first['error'])
    items = doc['items']
    if len(items) > MAX_ITEMS:
        _bad('/items', f'holds {len(items)} items; the limit is {MAX_ITEMS}')
    index = {}
    for i, item in enumerate(items):
        location = f'/items/{i}'
        if item['id'] in index:
            _bad(f'{location}/id', f"ids must be unique; {item['id']} repeats")
        index[item['id']] = i
        if int(item['id'][2:]) >= doc['next_number']:
            _bad(f'{location}/id', f"{item['id']} is not below next_number {doc['next_number']}")
        _check_text(location, item)
        state = item['state']
        if state == 'held':
            if not item['hold_reason'] or not item['hold_reason'].strip():
                _bad(f'{location}/hold_reason', 'a held item needs a reason')
        elif item['hold_reason'] is not None:
            _bad(f'{location}/hold_reason', 'only a held item carries a reason')
        if state in UNSTARTED:
            if item['cycle'] is not None or item['start_token'] is not None or item['started_at'] is not None:
                _bad(location, f'a {state} item must not carry a cycle, start_token or started_at')
        else:
            if not item['start_token'] or not TOKEN.fullmatch(item['start_token']):
                _bad(f'{location}/start_token', f'a {state} item needs a start_token (32 hex characters)')
            if state == 'starting' and (item['cycle'] is not None or item['started_at'] is not None):
                _bad(location, 'a starting item must not carry a cycle yet')
            if state == 'started':
                if not item['cycle'] or not ID.fullmatch(item['cycle']):
                    _bad(f'{location}/cycle', f"cycle {item['cycle']!r} is not a cycle id")
                if not item['started_at']:
                    _bad(f'{location}/started_at', 'a started item needs started_at')
    cycles = [i['cycle'] for i in items if i['state'] == 'started']
    if len(set(cycles)) != len(cycles):
        _bad('/items', 'two items name the same cycle')
    for i, item in enumerate(items):
        location = f'/items/{i}/depends_on'
        if len(set(item['depends_on'])) != len(item['depends_on']):
            _bad(location, 'repeats a dependency')
        for dep in item['depends_on']:
            if dep == item['id']:
                _bad(location, f"{dep} depends on itself")
            if dep not in index:
                _bad(location, f"{item['id']} depends on {dep}, which does not exist")
    visiting, done = set(), set()

    def visit(node):
        if node in done:
            return
        if node in visiting:
            _bad('/items', f'dependencies contain a cycle through {node}')
        visiting.add(node)
        for dep in items[index[node]]['depends_on']:
            visit(dep)
        visiting.discard(node)
        done.add(node)

    for item in items:
        visit(item['id'])
    seen_unstarted = None
    starting = 0
    for i, item in enumerate(items):
        if item['id'] in index and any(index[d] > i for d in item['depends_on']):
            late = next(d for d in item['depends_on'] if index[d] > i)
            _bad(f'/items/{i}', f"dependency {late} must precede {item['id']} in list order")
        if item['state'] in UNSTARTED:
            seen_unstarted = seen_unstarted or item['id']
        else:
            if seen_unstarted:
                _bad(f'/items/{i}', f"unstarted item {seen_unstarted} precedes {item['state']} item {item['id']}")
            starting += item['state'] == 'starting'
    if starting > 1:
        _bad('/items', 'at most one item may be starting')
    if doc['authorization'] is not None:
        _check_authorization(doc['authorization'], '/authorization')
    for i, record in enumerate(doc['authorization_history']):
        _check_authorization(record, f'/authorization_history/{i}')


def _check_references(cfg, references):
    """Write-time check of an item's reference paths: shape, then that each names something inside the repository.

    Read time checks shape only (`_check_text`), so a reference deleted later never breaks the queue."""
    if len(references) > MAX_LIST:
        raise QueueError(f'references holds at most {MAX_LIST} entries')
    if len(set(references)) != len(references):
        raise QueueError('references must not repeat a path')
    for path in references:
        if not isinstance(path, str) or not path.strip() or len(path) > MAX_TEXT:
            raise QueueError(f'a reference must be a non-blank path of at most {MAX_TEXT} characters')
        if path.startswith(':'):
            raise QueueError('a reference path cannot use git pathspec magic')
        try:
            target = contained(cfg.repo_root, path)
        except CycleError as exc:
            raise QueueError(f'reference {path!r}: {exc}') from exc
        if not target.exists():
            raise QueueError(f'reference {path!r} does not exist in the repository')


def _check_fields(cfg, title, outcome, kind, scope, acceptance):
    if not isinstance(title, str) or not title.strip() or len(title) > MAX_TITLE:
        raise QueueError(f'title must be non-blank and at most {MAX_TITLE} characters')
    if not isinstance(outcome, str) or not outcome.strip() or len(outcome) > MAX_TEXT:
        raise QueueError(f'outcome must be non-blank and at most {MAX_TEXT} characters')
    if not isinstance(kind, str) or not TYPE.fullmatch(kind):
        raise QueueError('type must be a lowercase kebab token such as quick-fix')
    for label, values in (('scope', scope), ('acceptance', acceptance)):
        if not values or len(values) > MAX_LIST or any(not isinstance(v, str) or not v.strip() or len(v) > MAX_TEXT for v in values):
            raise QueueError(f'{label} needs 1 to {MAX_LIST} non-blank entries of at most {MAX_TEXT} characters')
    for path in scope:
        if path.startswith(':'):
            raise QueueError('a scope path cannot use git pathspec magic')
        contained(cfg.repo_root, path)


# -- derived status -------------------------------------------------------------

def cycle_status(repo, identity):
    """The cycle's own status, or 'missing' when its record cannot be loaded and validated."""
    try:
        return load(repo, identity)['status']
    except (CycleError, OSError, KeyError, ValueError):
        return 'missing'


def _statuses(repo, doc):
    return {i['cycle']: cycle_status(repo, i['cycle']) for i in doc['items'] if i['state'] == 'started'}


def _label(item, statuses):
    return statuses.get(item['cycle'], item['state']) if item['state'] == 'started' else item['state']


def remaining(doc):
    auth = doc['authorization']
    if not auth:
        return []
    present = {i['id'] for i in doc['items']}
    return [q for q in auth['scope'] if q in present and q not in auth['started']]


def _unsatisfied(doc, item, statuses):
    by = {i['id']: i for i in doc['items']}
    return [by[d] for d in item['depends_on'] if not (by[d]['state'] == 'started' and statuses.get(by[d]['cycle']) == 'completed')]


def _stop(reason, item, detail):
    return ('stop', reason, item, detail)


def decide(doc, statuses):
    """The first applicable verdict for a queue with no starting item: in-progress, stop or go."""
    items = doc['items']
    for item in items:
        if item['state'] == 'started':
            status = statuses[item['cycle']]
            if status in ('active', 'paused'):
                return ('in-progress', item, status)
            if status == 'missing':
                return _stop('cycle-missing', item['id'], f"the record for {item['cycle']} cannot be loaded; restore it before the queue continues")
    head = next((i for i in items if i['state'] in UNSTARTED), None)
    if head is None:
        return _stop('queue-empty', None, 'no unstarted item remains')
    auth = doc['authorization']
    if auth is None:
        return _stop('not-authorized', head['id'], 'no active authorization; the owner must instruct the run')
    by = {i['id']: i for i in items}
    abandoned = [q for q in auth['started'] if q in by and statuses.get(by[q]['cycle']) == 'abandoned']
    if abandoned:
        return _stop('previous-abandoned', abandoned[0], f"{', '.join(abandoned)} ended abandoned; the owner re-authorizes to continue")
    if not remaining(doc):
        return _stop('authorization-exhausted', head['id'], 'every captured item has started; the owner authorizes more')
    if head['id'] not in auth['scope']:
        return _stop('outside-authorization', head['id'], f"{head['id']} was not captured by the current authorization")
    if head['state'] == 'held':
        return _stop('held', head['id'], f"{head['id']} is held: {head['hold_reason']}")
    unsatisfied = _unsatisfied(doc, head, statuses)
    if unsatisfied:
        names = ', '.join(f"{d['id']} ({_label(d, statuses)})" for d in unsatisfied)
        reason = 'dependency-abandoned' if any(_label(d, statuses) == 'abandoned' for d in unsatisfied) else 'blocked'
        return _stop(reason, head['id'], f"{head['id']} waits for {names}" + ('; the owner edits depends_on or removes the item' if reason == 'dependency-abandoned' else ''))
    if head['suggested_type'] not in PHASES:
        return _stop('type-unsupported', head['id'], f"type {head['suggested_type']} is not a cycle type; edit the item's type")
    return ('go', head)


# -- views ------------------------------------------------------------------------

def _authorization_view(doc):
    auth = doc['authorization']
    if auth is None:
        return None
    return {**{k: auth[k] for k in AUTH_KEYS}, 'remaining': remaining(doc)}


def _item_view(doc, item, position, statuses):
    by = {i['id']: i for i in doc['items']}
    auth = doc['authorization']
    return {
        'position': position, 'id': item['id'], 'title': item['title'], 'outcome': item['outcome'], 'type': item['suggested_type'],
        'scope': item['scope'], 'acceptance': item['acceptance'], 'references': item.get('references', []), 'state': item['state'], 'hold_reason': item['hold_reason'],
        'cycle': item['cycle'], 'cycle_status': statuses.get(item['cycle']) if item['state'] == 'started' else None,
        'in_scope': bool(auth and item['id'] in auth['scope']),
        'dependencies': [{'id': d, 'state': by[d]['state'], 'cycle_status': statuses.get(by[d]['cycle']) if by[d]['state'] == 'started' else None,
                          'satisfied': by[d]['state'] == 'started' and statuses.get(by[d]['cycle']) == 'completed'} for d in item['depends_on']],
    }


def _next_view(doc, statuses):
    starting = next((i for i in doc['items'] if i['state'] == 'starting'), None)
    if starting:
        return {'item': starting['id'], 'startable': False, 'stop': 'starting', 'detail': 'an interrupted start is pending; run start-next to recover it'}
    verdict = decide(doc, statuses)
    if verdict[0] == 'go':
        return {'item': verdict[1]['id'], 'startable': True, 'stop': None, 'detail': None}
    if verdict[0] == 'in-progress':
        return {'item': verdict[1]['id'], 'startable': False, 'stop': 'in-progress', 'detail': f"{verdict[1]['cycle']} is {verdict[2]}"}
    return {'item': verdict[2], 'startable': False, 'stop': verdict[1], 'detail': verdict[3]}


def list_view(repo):
    cfg = tree(repo)
    doc = read_queue(cfg)
    statuses = _statuses(repo, doc)
    return {'ok': True, 'items': [_item_view(doc, i, n, statuses) for n, i in enumerate(doc['items'], 1)],
            'authorization': _authorization_view(doc), 'next': _next_view(doc, statuses)}


def _find(doc, qid):
    if not isinstance(qid, str) or not QUEUE_ID.fullmatch(qid):
        raise QueueError(f'{qid!r} is not a queue item id (Q-0001 form)')
    for item in doc['items']:
        if item['id'] == qid:
            return item
    raise QueueError(f'no queue item {qid}')


def show(repo, qid):
    cfg = tree(repo)
    doc = read_queue(cfg)
    item = _find(doc, qid)
    return {'ok': True, 'item': _item_view(doc, item, doc['items'].index(item) + 1, _statuses(repo, doc))}


# -- mutating operations --------------------------------------------------------------

def _mutate(repo, change):
    """Run `change(cfg, doc)` on a copy under the queue lock, then validate and write."""
    with locked_queue(repo) as cfg:
        doc = read_queue(cfg)
        work = deepcopy(doc)
        result = change(cfg, work)
        write_queue(cfg, work)
        return result


def _unstarted(item, action):
    if item['state'] not in UNSTARTED:
        raise QueueError(f"{item['id']} is {item['state']}; {action} applies only to pending or held items")


def _view_of(doc, item):
    return {'ok': True, 'item': _item_view(doc, item, doc['items'].index(item) + 1, {})}


def add(repo, title, outcome, kind, scope, acceptance, depends_on=None, position=None, held=False, reason=None, references=None):
    if held and not (reason and reason.strip()):
        raise QueueError('--held needs --reason')
    if reason and not held:
        raise QueueError('--reason applies only with --held')

    def change(cfg, doc):
        _check_fields(cfg, title, outcome, kind, scope, acceptance)
        _check_references(cfg, references or [])
        if len(doc['items']) >= MAX_ITEMS:
            raise QueueError(f'the queue holds {MAX_ITEMS} items, the limit; started items count')
        at = len(doc['items']) + 1 if position is None else position
        if not 1 <= at <= len(doc['items']) + 1:
            raise QueueError(f"position must be 1 to {len(doc['items']) + 1}")
        item = {'id': f"Q-{doc['next_number']:04d}", 'title': title, 'outcome': outcome, 'suggested_type': kind, 'scope': list(scope),
                'acceptance': list(acceptance), 'depends_on': list(depends_on or []), 'state': 'held' if held else 'pending',
                'hold_reason': reason if held else None, 'start_token': None, 'cycle': None, 'added_at': now(), 'started_at': None}
        if references:
            item['references'] = list(references)
        doc['next_number'] += 1
        doc['items'].insert(at - 1, item)
        return _view_of(doc, item)

    return _mutate(repo, change)


def edit(repo, qid, title=None, outcome=None, kind=None, scope=None, acceptance=None, depends_on=None, no_depends=False, references=None, no_references=False):
    if no_references and references:
        raise QueueError('--no-references and --reference exclude each other')
    if no_depends and depends_on:
        raise QueueError('--no-depends and --depends-on exclude each other')
    if all(v is None for v in (title, outcome, kind, scope, acceptance, depends_on, references)) and not no_depends and not no_references:
        raise QueueError('nothing to change; pass at least one field')

    def change(cfg, doc):
        item = _find(doc, qid)
        _unstarted(item, 'edit')
        for key, value in (('title', title), ('outcome', outcome), ('suggested_type', kind), ('scope', scope and list(scope)), ('acceptance', acceptance and list(acceptance))):
            if value is not None:
                item[key] = value
        if no_depends:
            item['depends_on'] = []
        elif depends_on is not None:
            item['depends_on'] = list(depends_on)
        if no_references:
            item.pop('references', None)
        elif references is not None:
            item['references'] = list(references)
        _check_fields(cfg, item['title'], item['outcome'], item['suggested_type'], item['scope'], item['acceptance'])
        if references is not None:
            _check_references(cfg, item['references'])
        return _view_of(doc, item)

    return _mutate(repo, change)


def move(repo, qid, position):
    def change(cfg, doc):
        item = _find(doc, qid)
        _unstarted(item, 'move')
        if not 1 <= position <= len(doc['items']):
            raise QueueError(f"position must be 1 to {len(doc['items'])}")
        doc['items'].remove(item)
        doc['items'].insert(position - 1, item)
        return _view_of(doc, item)

    return _mutate(repo, change)


def hold(repo, qid, reason):
    def change(cfg, doc):
        item = _find(doc, qid)
        _unstarted(item, 'hold')
        if item['state'] == 'held':
            raise QueueError(f'{qid} is already held')
        if not reason or not reason.strip():
            raise QueueError('hold needs a non-blank reason')
        item['state'], item['hold_reason'] = 'held', reason
        return _view_of(doc, item)

    return _mutate(repo, change)


def unhold(repo, qid):
    def change(cfg, doc):
        item = _find(doc, qid)
        if item['state'] != 'held':
            raise QueueError(f'{qid} is {item["state"]}, not held')
        item['state'], item['hold_reason'] = 'pending', None
        return _view_of(doc, item)

    return _mutate(repo, change)


def remove(repo, qid):
    def change(cfg, doc):
        item = _find(doc, qid)
        _unstarted(item, 'remove')
        dependents = [i['id'] for i in doc['items'] if qid in i['depends_on']]
        if dependents:
            raise QueueError(f"{', '.join(dependents)} depend on {qid}; edit or remove them first")
        doc['items'].remove(item)
        return {'ok': True, 'removed': qid}

    return _mutate(repo, change)


def _end_authorization(doc, how, reason):
    record = doc['authorization']
    doc['authorization_history'].append({**record, 'ended_at': now(), 'ended': how, 'reason': reason})
    doc['authorization'] = None


def authorize(repo, kind, instruction, date, count=None):
    if kind not in ('next', 'next-n', 'queue'):
        raise QueueError('kind must be next, next-n or queue')
    if kind == 'next-n' and (not isinstance(count, int) or count < 1):
        raise QueueError('next-n needs --count of at least 1')
    if kind != 'next-n' and count is not None:
        raise QueueError('--count applies only to next-n')
    if not instruction or not instruction.strip():
        raise QueueError("the owner's instruction must be quoted verbatim and not blank")
    if not DATE.fullmatch(date or ''):
        raise QueueError('date must be YYYY-MM-DD')
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError as exc:
        raise QueueError('date is not a calendar date') from exc

    def change(cfg, doc):
        unstarted = [i['id'] for i in doc['items'] if i['state'] in ('pending', 'held', 'starting')]
        captured = unstarted[:1] if kind == 'next' else unstarted[:count] if kind == 'next-n' else unstarted
        if not captured:
            raise QueueError('no unstarted item to capture; add one first')
        if doc['authorization']:
            _end_authorization(doc, 'superseded', 'replaced by a new authorization')
        doc['authorization'] = {'instruction': instruction, 'kind': kind, 'count': 1 if kind == 'next' else count if kind == 'next-n' else None,
                                'scope': captured, 'started': [], 'authorized_at': now(), 'date': date}
        return {'ok': True, 'authorization': _authorization_view(doc)}

    return _mutate(repo, change)


def revoke(repo, reason):
    if not reason or not reason.strip():
        raise QueueError('revoke needs a non-blank reason')

    def change(cfg, doc):
        if not doc['authorization']:
            raise QueueError('no active authorization to revoke')
        _end_authorization(doc, 'revoked', reason)
        return {'ok': True, 'revoked': True}

    return _mutate(repo, change)


# -- start-next -------------------------------------------------------------------------

def adoption_scan(cfg, item):
    """Find the cycle created for an item's start token, or None when no cycle carries it.

    A directory without cycle.json is a burned id and is skipped. A cycle.json that cannot
    be read or parsed refuses the scan, so an unreadable adopted cycle cannot cause a duplicate."""
    directory = contained(cfg.docs_root, 'cycles')
    if not directory.is_dir():
        return None
    wanted = {'item': item['id'], 'token': item['start_token']}
    matches = []
    for folder in sorted(directory.iterdir()):
        if not folder.is_dir():
            continue
        record = folder / 'cycle.json'
        if not record.exists() and not record.is_symlink():
            continue
        try:
            parsed = json.loads(record.read_text())
        except (OSError, ValueError) as exc:
            raise QueueError(f'cannot read {folder.name}/cycle.json ({type(exc).__name__}); the start of {item["id"]} stays pending recovery') from exc
        if not isinstance(parsed, dict):
            raise QueueError(f'cannot read {folder.name}/cycle.json (not a JSON object); the start of {item["id"]} stays pending recovery')
        history = parsed.get('history')
        first = history[0] if isinstance(history, list) and history and isinstance(history[0], dict) else None
        if first and first.get('action') == 'created' and first.get('queue') == wanted:
            matches.append((folder, parsed))
    if len(matches) > 1:
        raise QueueError(f"{item['id']} matches {len(matches)} cycles: {', '.join(f.name for f, _ in matches)}; resolve them by hand")
    if not matches:
        return None
    folder, parsed = matches[0]
    try:
        validate_cycle(parsed)
    except CycleError as exc:
        raise QueueError(f'{folder.name}/cycle.json carries the start token of {item["id"]} but is invalid: {exc}') from exc
    if parsed['id'] != folder.name:
        raise QueueError(f'{folder.name}/cycle.json names a different cycle id')
    return parsed


def _adopt(doc, item, cycle_doc):
    item['state'], item['cycle'], item['started_at'] = 'started', cycle_doc['id'], now()
    auth = doc['authorization']
    if auth and item['id'] in auth['scope'] and item['id'] not in auth['started']:
        auth['started'].append(item['id'])


def _cancel_intent(item):
    item['state'], item['start_token'] = 'pending', None


def _goal(item):
    """The cycle goal: the outcome, then any references as a read-only block. References never enter scope."""
    references = item.get('references', [])
    if not references:
        return item['outcome']
    lines = '\n'.join(f'- {path}' for path in references)
    return f"{item['outcome']}\n\nReferences (read before planning; read-only, not scope):\n{lines}"


def start_next(repo, implementer='dev-lead', coordinator='dev-lead'):
    """Start the head item when every rule allows it; otherwise return the open cycle or raise a QueueStop."""
    with locked_queue(repo) as cfg:
        doc = read_queue(cfg)
        starting = next((i for i in doc['items'] if i['state'] == 'starting'), None)
        if starting:
            found = adoption_scan(cfg, starting)
            if found:
                _adopt(doc, starting, found)
                write_queue(cfg, doc)
                return {'ok': True, 'outcome': 'adopted', 'item': starting['id'], 'cycle': found['id'], 'status': found['status']}
            _cancel_intent(starting)
            write_queue(cfg, doc)
        verdict = decide(doc, _statuses(repo, doc))
        if verdict[0] == 'in-progress':
            return {'ok': True, 'outcome': 'in-progress', 'item': verdict[1]['id'], 'cycle': verdict[1]['cycle'], 'status': verdict[2]}
        if verdict[0] == 'stop':
            raise QueueStop(verdict[1], verdict[2], verdict[3])
        head = verdict[1]
        head['state'], head['start_token'] = 'starting', uuid.uuid4().hex
        write_queue(cfg, doc)
        try:
            created = create(repo, head['suggested_type'], head['title'], _goal(head), list(head['scope']), list(head['acceptance']),
                             implementer, coordinator, origin={'item': head['id'], 'token': head['start_token']},
                             release_list='beta' if head['suggested_type'] == 'release' else None)
        except Exception as exc:
            found = adoption_scan(cfg, head)
            if found:
                _adopt(doc, head, found)
                write_queue(cfg, doc)
                return {'ok': True, 'outcome': 'adopted', 'item': head['id'], 'cycle': found['id'], 'status': found['status']}
            _cancel_intent(head)
            write_queue(cfg, doc)
            raise QueueError(f"the cycle for {head['id']} was not created: {exc}") from exc
        _adopt(doc, head, created)
        write_queue(cfg, doc)
        return {'ok': True, 'outcome': 'started', 'item': head['id'], 'cycle': created['id'], 'status': created['status']}


# -- command line ----------------------------------------------------------------------------

def dispatch(a):
    repo, op = a.repo_root, a.queue_op
    if op == 'add':
        return add(repo, a.title, a.outcome, a.item_type, a.scope, a.acceptance, a.depends_on, a.position, a.held, a.reason, a.references)
    if op == 'list':
        return list_view(repo)
    if op == 'show':
        return show(repo, a.item)
    if op == 'edit':
        return edit(repo, a.item, a.title, a.outcome, a.item_type, a.scope, a.acceptance, a.depends_on, a.no_depends, a.references, a.no_references)
    if op == 'move':
        return move(repo, a.item, a.position)
    if op == 'hold':
        return hold(repo, a.item, a.reason)
    if op == 'unhold':
        return unhold(repo, a.item)
    if op == 'remove':
        return remove(repo, a.item)
    if op == 'authorize':
        return authorize(repo, a.kind, a.instruction, a.date, a.count)
    if op == 'revoke':
        return revoke(repo, a.reason)
    if op == 'start-next':
        return start_next(repo, a.implementer, a.coordinator)
    raise QueueError(f'unknown queue operation {op}')


def run(a):
    """Run a parsed `queue` command; return (exit code, payload). 1 refuses or stops, 2 is the environment."""
    try:
        return 0, dispatch(a)
    except QueueStop as stop:
        return 1, {'ok': False, 'stop': {'reason': stop.reason, 'item': stop.item, 'detail': stop.detail}}
    except (QueueEnvError, BionicConfigError, OSError) as exc:
        return 2, {'ok': False, 'error': str(exc)}
    except (CycleError, ValueError, KeyError) as exc:
        return 1, {'ok': False, 'error': str(exc)}
