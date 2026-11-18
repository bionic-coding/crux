"""A persistent, ordered queue of requested work that commander turns into cycles one at a time.

The active queue is `<docs_dir>/queue/cycles.yaml`. List order is execution order.
An item holds the request (title, outcome, scope, acceptance, suggested type) and where it
stands (pending, held, starting, started). The outcome of a started item is never stored:
readers derive it from the cycle's own record, so the queue and the cycle views cannot
disagree.

Authorization is a single record of the owner's quoted instruction plus the item ids it
captured. It authorizes starting cycles, and for a release item the publish of that item's
version to its target, which `tools/release.py` reads from this record; never a push, another
publish, a longer pass limit or an approval of a decision. Each started cycle keeps its own
type, pass limit and stop points. A release item's optional `release_list` (beta, the default,
or official) names the task list of the cycle it starts.

Starting an item is a recoverable two-step write. `start_next` records an intent (state
`starting` with a random token), calls `cycle_writer.create` with that token as the record's
queue binding, then records the cycle id. A release item starts through `cycle_writer.create_release`
the same way, with the version taken from its title or the current authorization. A crash between the steps leaves the intent; the next call scans
the cycle records for the token and adopts the cycle, or cancels the intent when none carries it.

Lock order is the queue lock (`<docs_dir>/queue/.lock`), then the cycles lock that `create`
takes itself. Nothing takes the queue lock while holding the cycles lock. Readers take no lock.

Known limits:
- Format 1 counts every item toward the 500-item cap. Format 2 archives terminal
  started items under `queue/history/items/`, and the cap applies to active items.
- Migration to format 2 is explicit. Older tools cannot read format 2 safely.
- `start_next` considers only cycles that the queue started; other cycles are not its concern.
- The lock guards overlapping invocations and crashes, not deliberate tampering.
- A CLI rewrite drops YAML comments. The owner may edit the file by hand; every read validates it.
- The writer cannot verify that an authorization instruction is the owner's own words; that
  rule rests on the commander contract.
- The queue lock file is not gitignored by downstream trees, as the cycles lock is not.

Commits: every mutating operation except `start-next` commits the queue and changed history
(`commit_queue`, `git commit --only`) after it writes, still inside the queue lock,
and returns the result as `queue_commit`. The commit defers with a reason under the record
commit's conditions (a running full suite, a merge or rebase, an index lock, no repository); the
queue change is saved either way. `start-next` that starts or adopts a cycle commits the queue file
and the new cycle record together in one record commit, returned as `record_commit`, so it leaves a
clean tree (IDR lean-workflow-traps-and-recovery approach 1). A cancelled start intent commits the
queue file alone, as `queue_commit`.

Scope: `add`, `edit` and `start-next` split every scope value on commas, so `a, b` names two paths.
A stored comma-joined value stays as stored and is split when a cycle starts.

`queue list` prints one line per open item by default; `--full` resolves history too.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
import fcntl
import hashlib
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

from bionic_config import BionicConfigError
from cycle_store import CLOSED, CycleError, ID, atomic_bytes, commit_paths, contained, git, now, tree
import cycle_history

FORMAT = 'crux.cycle-queue'
QUEUE_ID = re.compile(r'^Q-[0-9]{4,}$')
TYPE = re.compile(r'^[a-z][a-z-]{1,30}$')
TOKEN = re.compile(r'^[0-9a-f]{32}$')
DATE = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
# An item's suggested type is a recorded label; `auto` names none. Only `release` selects another start.
AUTO_TYPE = 'auto'
TYPES = ('dev', 'iterate', 'refactor', 'simplify', 'quick-fix', 'release', AUTO_TYPE)
MAX_ITEMS = 500
# The active snapshot shares this finite UTF-8 budget with the progress reader.
MAX_QUEUE_BYTES = 2_000_000
# A maximal normal item can contain 150 fields of 2,000 four-byte characters.
# Keep the bound above that payload and refuse oversized exceptional metadata
# before writing or removing the active item.
MAX_HISTORY_BYTES = 2 * 1024 * 1024
MAX_TITLE = 200
MAX_TEXT = 2000
MAX_LIST = 50
UNSTARTED = ('pending', 'held')
# A release item's fixed task list; an item without the key starts a beta-list cycle.
RELEASE_LISTS = ('beta', 'official')
ITEM_KEYS = ('id', 'title', 'outcome', 'suggested_type', 'scope', 'acceptance', 'depends_on', 'references', 'release_list', 'state', 'hold_reason', 'start_token', 'cycle', 'added_at', 'started_at')
AUTH_KEYS = ('instruction', 'kind', 'count', 'scope', 'started', 'authorized_at', 'date')
ENDED_KEYS = ('ended_at', 'ended', 'reason')
TOP_KEYS = ('format', 'format_version', 'next_number', 'items', 'authorization', 'authorization_history')


# -- cycle creation -------------------------------------------------------------------
# Every item starts a crux.cycle.v1 record through the cycle writer; a release item's record carries its
# fixed step list. A legacy typed (schema_version) record is only read, through cycle_history, the
# read-only historical reader.

def create(repo, title, lead, definition, queue):
    """Create the cycle record for a queue start through the cycle writer."""
    import cycle_writer
    return cycle_writer.create(repo, title, lead, definition, queue=queue)


def create_release(repo, release_list, version, title, goal, scope, acceptance, lead, queue):
    """Create the release record for a queue start through the cycle writer."""
    import cycle_writer
    return cycle_writer.create_release(repo, release_list, version, title, goal, scope, acceptance, lead, queue=queue)


# -- queue commits ----------------------------------------------------------------

def queue_paths(cfg):
    """Queue writer paths, including history left pending by a deferred commit."""
    paths = []
    queue = contained(cfg.docs_root, 'queue/cycles.yaml')
    if queue.is_file() or queue.is_symlink():
        paths.append(queue.relative_to(cfg.repo_root).as_posix())
    history = contained(cfg.docs_root, 'queue/history/items')
    if history.is_dir():
        paths.extend(p.relative_to(cfg.repo_root).as_posix() for p in sorted(history.iterdir())
                     if re.fullmatch(r'Q-[0-9]{4,}\.json', p.name) and p.is_file() and not p.is_symlink())
    return paths


def commit_queue(cfg, label):
    """Commit the queue file alone after a queue write. The caller holds the queue lock.

    Same result and deferral conditions as the cycle record commit (`cycle_store.commit_paths`); the message is `queue: <label>`."""
    paths = queue_paths(cfg)
    try:
        return commit_paths(cfg, paths, f'queue: {label}')
    except Exception as exc:  # the queue is already saved; the commit is the writer's follow-up
        return {'changed': False, 'commit': None, 'paths': paths, 'message': None, 'deferred': 'commit-error',
                'detail': f'{type(exc).__name__}: {exc}'[:300]}


class QueueError(CycleError):
    """A refusal: the request or the queue file is invalid. Exit 1."""


class QueueEnvError(CycleError):
    """An environment problem: an unreadable or unlockable path, or PyYAML missing. Exit 2."""


class QueueStop(QueueError):
    """start-next cannot proceed; the reason, item and detail tell the owner what to decide."""

    def __init__(self, reason, item, detail, missing=None):
        super().__init__(f'{reason}: {detail}')
        self.reason, self.item, self.detail, self.missing = reason, item, detail, missing


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


def queue_bytes(doc):
    """Validate the complete serialized snapshot before mutation side effects."""
    check_queue(doc)
    text = _yaml().safe_dump(_ordered(doc), sort_keys=False, default_flow_style=False, allow_unicode=True, width=100)
    payload = text.encode('utf-8')
    if len(payload) > MAX_QUEUE_BYTES:
        raise QueueError(f'active queue exceeds the {MAX_QUEUE_BYTES}-byte limit; queue remains unchanged')
    return payload


def write_queue(cfg, doc):
    """Validate, then replace the file atomically with a fixed key order."""
    atomic_bytes(queue_file(cfg), queue_bytes(doc))


def read_queue_text(source, path):
    """Bound this queue read without widening unrelated source transport reads."""
    from admission_source_io import SourceIORefusal
    try:
        return source.read_text(path, max_bytes=MAX_QUEUE_BYTES)
    except SourceIORefusal as exc:
        raise QueueError(f'active queue unavailable within the {MAX_QUEUE_BYTES}-byte limit or guarded read refused') from exc


def parse_queue(text, label='queue file'):
    """Parse and validate queue text; every failure names the file, the location and the repair."""
    if len(text.encode('utf-8')) > MAX_QUEUE_BYTES:
        raise QueueError(f'{label}: exceeds the {MAX_QUEUE_BYTES}-byte limit')
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
        from admission_source_io import SourceIO
        source = SourceIO(cfg.repo_root)
        try:
            text = read_queue_text(source, path)
        finally:
            source.close()
    except (OSError, UnicodeDecodeError) as exc:
        raise QueueEnvError(f'cannot read {path}: {type(exc).__name__}') from exc
    doc = parse_queue(text, f'{cfg.docs_dir}/queue/cycles.yaml')
    if doc['format_version'] == 2:
        for item in doc['items']:
            resolve_item(cfg, doc, item['id'])
            for dep in item['depends_on']:
                resolve_item(cfg, doc, dep)
    return doc


def _item_digest(item):
    raw = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _check_history_binding(cfg, item, source=None):
    """A history item names a terminal cycle of either format that carries the item's id and start token."""
    try:
        path = contained(cfg.docs_root, f"cycles/{item['cycle']}/cycle.json")
        if source is None:
            if path.is_symlink() or not path.is_file():
                raise QueueError('the cycle record is missing or unsafe')
            cycle = json.loads(path.read_text(encoding='utf-8'))
        else:
            cycle = json.loads(source.read_text(path, max_bytes=4 * 1024 * 1024))
        if not isinstance(cycle, dict) or cycle.get('id') != item['cycle']:
            raise QueueError('the cycle record names another cycle')
        terminal = _record_terminal(cycle)
    except (CycleError, OSError, KeyError, ValueError, TypeError) as exc:
        raise QueueError(f"history {item['id']} has no valid cycle: {exc}") from exc
    if not terminal or _origin(cycle) != {'item': item['id'], 'token': item['start_token']}:
        raise QueueError(f"history {item['id']} has an invalid terminal cycle binding")


def _history_path(cfg, qid):
    if not isinstance(qid, str) or not QUEUE_ID.fullmatch(qid):
        raise QueueError(f'{qid!r} is not a queue item id')
    return contained(cfg.docs_root, f'queue/history/items/{qid}.json')


def _read_history(cfg, qid, source=None):
    path = _history_path(cfg, qid)
    try:
        if source is not None:
            if source.kind(path) != 'file':
                raise QueueError(f'history {qid} is missing or unsafe')
            record = json.loads(source.read_text(path, max_bytes=MAX_HISTORY_BYTES))
        else:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_HISTORY_BYTES:
                raise QueueError(f'history {qid} is missing, unsafe or too large')
            record = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise QueueError(f'cannot read history {qid}: {type(exc).__name__}') from exc
    if not isinstance(record, dict) or set(record) != {'format', 'item', 'source_sha256', 'order', 'provenance'}:
        raise QueueError(f'history {qid} has invalid fields')
    item = record['item']
    if record['format'] != 'crux.cycle-queue-history.v1' or not isinstance(item, dict) or item.get('id') != qid:
        raise QueueError(f'history {qid} has invalid identity')
    if item.get('state') != 'started' or record['source_sha256'] != _item_digest(item):
        raise QueueError(f'history {qid} has invalid item or digest')
    cycle_id = item.get('cycle')
    if (not isinstance(cycle_id, str) or not ID.fullmatch(cycle_id)
            or record['order'] != int(cycle_id.rsplit('CYC-', 1)[1])
            or record['provenance'] != {'cycle': cycle_id, 'start_token': item.get('start_token')}):
        raise QueueError(f'history {qid} has invalid provenance')
    sample = empty_queue()
    sample.update(format_version=2, next_number=int(qid[2:]) + 1, items=[item])
    check_queue(sample, schema=True)
    _check_history_binding(cfg, item, source=source)
    return item


def resolve_item(cfg, doc, qid, source=None):
    """Resolve an item from an already captured active snapshot, then immutable history."""
    if not isinstance(qid, str) or not QUEUE_ID.fullmatch(qid):
        raise QueueError(f'{qid!r} is not a queue item id')
    active = next((item for item in doc['items'] if item['id'] == qid), None)
    pending = getattr(doc, 'pending_history', {}).get(qid)
    if active is None and pending is not None:
        return pending
    if doc['format_version'] == 1:
        if active is None:
            raise QueueError(f'no queue item {qid}')
        return active
    path = _history_path(cfg, qid)
    exists = source.kind(path) is not None if source is not None else path.exists() or path.is_symlink()
    if exists:
        archived = _read_history(cfg, qid, source=source)
        if int(qid[2:]) >= doc['next_number']:
            raise QueueError(f'history {qid} is not below next_number {doc["next_number"]}')
        if active is not None and active != archived:
            raise QueueError(f'conflicting active and history copies of {qid}')
        return active if active is not None else archived
    if active is None:
        raise QueueError(f'no queue item or history for {qid}')
    return active


def _with_history(cfg, doc, ids=(), full=False, source=None):
    if doc['format_version'] == 1:
        return doc
    wanted = set(ids)
    wanted.update(dep for item in doc['items'] for dep in item['depends_on'])
    if doc['authorization']:
        wanted.update(doc['authorization']['started'])
    if full:
        directory = contained(cfg.docs_root, 'queue/history/items')
        if directory.exists():
            if directory.is_symlink() or not directory.is_dir():
                raise QueueError('queue history directory is unsafe')
            for path in directory.iterdir():
                if path.suffix != '.json' or not QUEUE_ID.fullmatch(path.stem):
                    raise QueueError(f'invalid history entry {path.name}')
                wanted.add(path.stem)
    active = {item['id'] for item in doc['items']}
    archived = []
    while wanted:
        qid = wanted.pop()
        if any(item['id'] == qid for item in archived):
            continue
        item = resolve_item(cfg, doc, qid, source=source)
        if qid not in active:
            archived.append(item)
            wanted.update(dep for dep in item['depends_on'] if dep not in active)
    started = archived + [item for item in doc['items'] if item['state'] == 'started']
    started.sort(key=lambda item: int(item['cycle'].rsplit('CYC-', 1)[1]))
    return {**doc, 'items': started + [item for item in doc['items'] if item['state'] != 'started']}


def _archive_items(repo, cfg, doc, dry_run=False, only_ids=None):
    """Validate candidates, persist immutable history, then remove them from the snapshot."""
    def committed(item):
        path = (cfg.docs_root / 'cycles' / item['cycle'] / 'cycle.json').relative_to(cfg.repo_root).as_posix()
        code, out, _ = git(cfg.repo_root, 'status', '--porcelain', '--untracked-files=all', '--', path)
        # Non-git repositories remain supported; a dirty tracked cycle must commit first.
        return code != 0 or not out.strip()

    selected = [item for item in doc['items'] if item['state'] == 'started'
                and (only_ids is None or item['id'] in only_ids)
                and cycle_status(repo, item['cycle']) in CLOSED and committed(item)]
    records = []
    for item in selected:
        _check_history_binding(cfg, item)
        path = _history_path(cfg, item['id'])
        if path.exists() or path.is_symlink():
            if _read_history(cfg, item['id']) != item:
                raise QueueError(f"conflicting active and history copies of {item['id']}")
        record = {'format': 'crux.cycle-queue-history.v1', 'item': item,
                  'source_sha256': _item_digest(item), 'order': int(item['cycle'].rsplit('CYC-', 1)[1]),
                  'provenance': {'cycle': item['cycle'], 'start_token': item['start_token']}}
        payload = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
        if len(payload) > MAX_HISTORY_BYTES:
            raise QueueError(f"history {item['id']} exceeds the {MAX_HISTORY_BYTES}-byte limit; item remains active")
        records.append((path, record, payload))
    if dry_run:
        return [item['id'] for item in selected]
    projected = deepcopy(doc)
    projected['format_version'] = 2
    projected['items'] = [item for item in doc['items'] if item['id'] not in {row['id'] for row in selected}]
    queue_bytes(projected)
    for path, record, payload in records:
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.queue-history-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if _read_history(cfg, record['item']['id']) != record['item']:
                    raise QueueError(f"conflicting active and history copies of {record['item']['id']}")
        finally:
            os.unlink(temporary)
    ids = {item['id'] for item in selected}
    doc['items'] = [item for item in doc['items'] if item['id'] not in ids]
    return [item['id'] for item in selected]


def archive(repo, dry_run=False, migrate=False, only_if_items=False):
    """Preview or commit the explicit format migration and terminal-item sweep."""
    with locked_queue(repo) as cfg:
        doc = read_queue(cfg)
        if doc['format_version'] == 1 and not (migrate or dry_run):
            raise QueueError('format 1 needs explicit --migrate before archival')
        work = deepcopy(doc)
        items = _archive_items(repo, cfg, work, dry_run=dry_run)
        if dry_run:
            return {'ok': True, 'items': items, 'format_version': doc['format_version'], 'dry_run': True}
        if only_if_items and not items:
            return {'ok': True, 'items': [], 'format_version': doc['format_version']}
        work['format_version'] = 2
        write_queue(cfg, work)
        return {'ok': True, 'items': items, 'format_version': 2,
                'queue_commit': commit_queue(cfg, 'archive terminal items')}


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
    if 'release_list' in item:
        if item['release_list'] not in RELEASE_LISTS:
            _bad(f'{location}/release_list', f"must be one of {', '.join(RELEASE_LISTS)}")
        if item['suggested_type'] != 'release':
            _bad(f'{location}/release_list', 'belongs to a release item only')


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
            if dep not in index and doc['format_version'] == 1:
                _bad(location, f"{item['id']} depends on {dep}, which does not exist")
    visiting, done = set(), set()

    def visit(node):
        if node in done:
            return
        if node in visiting:
            _bad('/items', f'dependencies contain a cycle through {node}')
        visiting.add(node)
        for dep in items[index[node]]['depends_on']:
            if dep in index:
                visit(dep)
        visiting.discard(node)
        done.add(node)

    for item in items:
        visit(item['id'])
    seen_unstarted = None
    starting = 0
    for i, item in enumerate(items):
        if item['id'] in index and any(d in index and index[d] > i for d in item['depends_on']):
            late = next(d for d in item['depends_on'] if d in index and index[d] > i)
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


def split_scope(values):
    """Every scope value split on commas into stripped, non-empty entries; None stays None."""
    if values is None:
        return None
    return [piece.strip() for value in values for piece in (value.split(',') if isinstance(value, str) else [value])
            if not isinstance(piece, str) or piece.strip()]


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

def _legacy_status(repo, identity):
    try:
        return cycle_history.load_record(repo, identity)['status']
    except (CycleError, OSError, KeyError, ValueError, TypeError):
        return 'missing'


def cycle_status(repo, identity):
    """The cycle's own status, or 'missing' when its record cannot be loaded and validated.

    A pilot record answers `reviewed` once its approving review is recorded and `completed` once it
    finished. Neither status says anything about a PR, CI, a merge or a release."""
    status = _legacy_status(repo, identity)
    if status != 'missing':
        return status
    try:
        import cycle_writer
        return cycle_writer.queue_status(cycle_writer.load_pilot(repo, identity))
    except (CycleError, OSError, KeyError, ValueError, TypeError):
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
            # A reviewed pilot awaits only its finish operation; it holds the queue until then,
            # so the next item's commits cannot change its reviewed paths first.
            if status in ('active', 'paused', 'reviewed'):
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
        shortcut = [d['id'] for d in unsatisfied if _label(d, statuses) == 'shortcut']
        text = f"{head['id']} waits for {names}"
        if reason == 'dependency-abandoned':
            text += '; the owner edits depends_on or removes the item'
        elif shortcut:
            text += f"; {', '.join(shortcut)} closed as a shortcut with gaps, so the owner edits depends_on or removes the item"
        return _stop(reason, head['id'], text)
    if head['suggested_type'] not in TYPES:
        return _stop('type-unsupported', head['id'], f"type {head['suggested_type']} is not a cycle type; edit the item's type")
    return ('go', head)


# -- views ------------------------------------------------------------------------

def _authorization_view(doc):
    auth = doc['authorization']
    if auth is None:
        return None
    return {**{k: auth[k] for k in AUTH_KEYS}, 'remaining': remaining(doc)}


def _pilot_facts(repo, doc):
    """For each started item whose cycle is a pilot: the recorded review, whether it still covers the
    final change, completion and the delivery facts, from the writer's own status function."""
    import cycle_writer
    facts = {}
    for item in doc['items']:
        if item['state'] == 'started':
            try:
                found = cycle_writer.status_facts(repo, cycle_writer.load_pilot(repo, item['cycle']))
            except (CycleError, OSError, KeyError, ValueError, TypeError):
                continue  # a typed cycle, or a record `cycle_status` already reports as missing
            facts[item['cycle']] = {key: found[key] for key in ('review', 'review_applicable', 'applicability', 'completed', 'reopened', 'delivery')}
    return facts


def _history_facts(repo, doc):
    """For each started item whose cycle is a typed (legacy) record: the historical reader's bounded facts."""
    found = {}
    cfg = None
    for item in doc['items']:
        if item['state'] != 'started':
            continue
        try:
            record = cycle_history.load_record(repo, item['cycle'])
            cfg = cfg or tree(repo)
            found[item['cycle']] = cycle_history.facts(record, lambda rel: json.loads(contained(cfg.docs_root, rel).read_text(encoding='utf-8')))
        except (CycleError, OSError, KeyError, ValueError, TypeError):
            continue  # a pilot cycle, or a record `cycle_status` already reports as missing
    return found


def _position(doc, item):
    """An unstarted item's 1-based place among the unstarted items, in queue order; None once it has started."""
    unstarted = [i['id'] for i in doc['items'] if i['state'] in UNSTARTED]
    return unstarted.index(item['id']) + 1 if item['id'] in unstarted else None


def _item_view(doc, item, statuses, facts=None, history=None, text=True):
    """One item's view. `text=False` leaves out the outcome, scope, acceptance and references,
    the text an archived item keeps in its immutable history entry for `queue show`."""
    by = {i['id']: i for i in doc['items']}
    auth = doc['authorization']
    detail = {'outcome': item['outcome'], 'scope': item['scope'], 'acceptance': item['acceptance'],
              'references': item.get('references', [])} if text else {}
    return {
        **({'pilot': facts[item['cycle']]} if facts and item['cycle'] in facts else {}),
        **({'history': history[item['cycle']]} if history and item['cycle'] in history else {}),
        'position': _position(doc, item), 'id': item['id'], 'title': item['title'], 'type': item['suggested_type'], **detail,
        'release_list': item.get('release_list', 'beta') if item['suggested_type'] == 'release' else None, 'state': item['state'], 'hold_reason': item['hold_reason'],
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


# Reviewed work awaits its finish operation, so it is open: only a terminal status closes an item.
OPEN_CYCLE = ('active', 'paused', 'missing', 'reviewed')


def _is_open(item, statuses):
    return item['state'] != 'started' or statuses.get(item['cycle']) in OPEN_CYCLE


def _line(doc, item, statuses):
    auth = doc['authorization']
    if item['state'] == 'started':
        parts = [f"{item['id']} {item['cycle']} {statuses.get(item['cycle'])}" + (' (awaiting finish)' if statuses.get(item['cycle']) == 'reviewed' else '')]
    else:
        parts = [f"{item['id']} {item['state']}"]
    parts.append(f"{item['suggested_type']}: {item['title']}")
    if item['state'] == 'held':
        parts.append(f"hold: {item['hold_reason']}")
    waiting = [d['id'] for d in _unsatisfied(doc, item, statuses)] if item['state'] != 'started' else []
    if waiting:
        parts.append('waits on ' + ', '.join(waiting))
    if auth and item['id'] in auth['scope'] and item['id'] not in auth['started']:
        parts.append('authorized')
    return ' | '.join(parts)


def _authorization_line(doc):
    auth = doc['authorization']
    if auth is None:
        return None
    count = f" {auth['count']}" if auth['count'] is not None else ''
    return f"{auth['kind']}{count}, {auth['date']}, remaining: {', '.join(remaining(doc)) or 'none'}"


def list_view(repo, full=False):
    cfg = tree(repo)
    doc = read_queue(cfg)
    view_doc = _with_history(cfg, doc, full=full)
    statuses = _statuses(repo, view_doc)
    if full:
        # The rows leave per-item history facts, and an archived item's text, to `queue show`.
        facts, active = _pilot_facts(repo, view_doc), {i['id'] for i in doc['items']}
        return {'ok': True, 'items': [{**_item_view(view_doc, i, statuses, facts, text=i['id'] in active), 'archived': i['id'] not in active}
                                      for i in view_doc['items']],
                'authorization': _authorization_view(view_doc), 'authorization_history': doc['authorization_history'], 'next': _next_view(view_doc, statuses)}
    shown = [i for i in doc['items'] if _is_open(i, statuses)]
    return {'ok': True, 'items': [_line(view_doc, i, statuses) for i in shown], 'closed': len(doc['items']) - len(shown),
            'authorization': _authorization_line(view_doc), 'next': _next_view(view_doc, statuses),
            'full': 'run `queue list --full` for every item and the authorization history'}


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
    view_doc = _with_history(cfg, doc, ids=[qid])
    item = _find(view_doc, qid)
    return {'ok': True, 'item': _item_view(view_doc, item, _statuses(repo, view_doc), _pilot_facts(repo, view_doc),
                                           _history_facts(repo, view_doc))}


# -- mutating operations --------------------------------------------------------------

class _PendingQueue(dict):
    """A private mutation snapshot with prevalidated, not-yet-written history."""


def _mutate(repo, change, label):
    """Run `change(cfg, doc)` on a copy under the queue lock, then validate, write and commit the queue file.

    `label` names the act in the commit message: a string, or a callable of the result."""
    with locked_queue(repo) as cfg:
        doc = read_queue(cfg)
        work = _PendingQueue(deepcopy(doc))
        selected = _archive_items(repo, cfg, doc, dry_run=True) if doc['format_version'] == 2 else []
        work.pending_history = {item['id']: item for item in work['items'] if item['id'] in selected}
        if selected:
            work['items'] = [item for item in work['items'] if item['id'] not in work.pending_history]
        result = change(cfg, work)
        check_queue(work, schema=True)
        _with_history(cfg, work)
        queue_bytes(work)
        if selected:
            archived = _archive_items(repo, cfg, deepcopy(doc), only_ids=set(selected))
            if archived != selected:
                raise QueueError('archive candidates changed while preparing the mutation; retry')
        write_queue(cfg, work)
        result['queue_commit'] = commit_queue(cfg, label(result) if callable(label) else label)
        return result


def _unstarted(item, action):
    if item['state'] not in UNSTARTED:
        raise QueueError(f"{item['id']} is {item['state']}; {action} applies only to pending or held items")


def _view_of(doc, item):
    return {'ok': True, 'item': _item_view(doc, item, {})}


def add(repo, title, outcome, kind, scope, acceptance, depends_on=None, position=None, held=False, reason=None, references=None, release_list=None):
    if held and not (reason and reason.strip()):
        raise QueueError('--held needs --reason')
    if reason and not held:
        raise QueueError('--reason applies only with --held')
    if release_list is not None and release_list not in RELEASE_LISTS:
        raise QueueError(f"--release-list must be one of {', '.join(RELEASE_LISTS)}")
    if release_list is not None and kind != 'release':
        raise QueueError('--release-list belongs to a release item: pass --type release')

    scope = split_scope(scope)

    def change(cfg, doc):
        captured_scope = scope
        if kind == 'release':
            import cycle_writer
            captured_scope = cycle_writer.release_scope(cfg, scope, release_list or 'beta', capture=True)
        _check_fields(cfg, title, outcome, kind, captured_scope, acceptance)
        _check_references(cfg, references or [])
        if len(doc['items']) >= MAX_ITEMS:
            raise QueueError(f'the queue holds {MAX_ITEMS} items, the limit; started items count')
        at = len(doc['items']) + 1 if position is None else position
        if not 1 <= at <= len(doc['items']) + 1:
            raise QueueError(f"position must be 1 to {len(doc['items']) + 1}")
        item = {'id': f"Q-{doc['next_number']:04d}", 'title': title, 'outcome': outcome, 'suggested_type': kind, 'scope': list(captured_scope),
                'acceptance': list(acceptance), 'depends_on': list(depends_on or []), 'state': 'held' if held else 'pending',
                'hold_reason': reason if held else None, 'start_token': None, 'cycle': None, 'added_at': now(), 'started_at': None}
        if doc['format_version'] == 2 and (_history_path(cfg, item['id']).exists() or _history_path(cfg, item['id']).is_symlink()):
            raise QueueError(f"allocated id {item['id']} collides with history; restore next_number")
        if references:
            item['references'] = list(references)
        if release_list is not None:
            item['release_list'] = release_list
        doc['next_number'] += 1
        doc['items'].insert(at - 1, item)
        return _view_of(_with_history(cfg, doc), item)

    return _mutate(repo, change, lambda r: f"add {r['item']['id']}")


def edit(repo, qid, title=None, outcome=None, kind=None, scope=None, acceptance=None, depends_on=None, no_depends=False, references=None, no_references=False):
    if no_references and references:
        raise QueueError('--no-references and --reference exclude each other')
    if no_depends and depends_on:
        raise QueueError('--no-depends and --depends-on exclude each other')
    if all(v is None for v in (title, outcome, kind, scope, acceptance, depends_on, references)) and not no_depends and not no_references:
        raise QueueError('nothing to change; pass at least one field')
    scope = split_scope(scope)

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
        if 'release_list' in item and item['suggested_type'] != 'release':
            raise QueueError(f"{qid} carries release_list {item['release_list']}, which belongs to a release item; keep --type release")
        if references is not None:
            _check_references(cfg, item['references'])
        return _view_of(_with_history(cfg, doc), item)

    return _mutate(repo, change, f'edit {qid}')


def move(repo, qid, position):
    def change(cfg, doc):
        item = _find(doc, qid)
        _unstarted(item, 'move')
        if not 1 <= position <= len(doc['items']):
            raise QueueError(f"position must be 1 to {len(doc['items'])}")
        doc['items'].remove(item)
        doc['items'].insert(position - 1, item)
        return _view_of(_with_history(cfg, doc), item)

    return _mutate(repo, change, f'move {qid} to {position}')


def hold(repo, qid, reason):
    def change(cfg, doc):
        item = _find(doc, qid)
        _unstarted(item, 'hold')
        if item['state'] == 'held':
            raise QueueError(f'{qid} is already held')
        if not reason or not reason.strip():
            raise QueueError('hold needs a non-blank reason')
        item['state'], item['hold_reason'] = 'held', reason
        return _view_of(_with_history(cfg, doc), item)

    return _mutate(repo, change, f'hold {qid}')


def unhold(repo, qid):
    def change(cfg, doc):
        item = _find(doc, qid)
        if item['state'] != 'held':
            raise QueueError(f'{qid} is {item["state"]}, not held')
        item['state'], item['hold_reason'] = 'pending', None
        return _view_of(_with_history(cfg, doc), item)

    return _mutate(repo, change, f'unhold {qid}')


def remove(repo, qid):
    def change(cfg, doc):
        item = _find(doc, qid)
        _unstarted(item, 'remove')
        dependents = [i['id'] for i in doc['items'] if qid in i['depends_on']]
        if dependents:
            raise QueueError(f"{', '.join(dependents)} depend on {qid}; edit or remove them first")
        doc['items'].remove(item)
        return {'ok': True, 'removed': qid}

    return _mutate(repo, change, f'remove {qid}')


def _assessment(item, value):
    """The lead's statement of how the reviewed pilot met the queued outcome and each criterion."""
    if not isinstance(value, dict) or set(value) != {'outcome', 'acceptance'}:
        raise QueueError('assessment requires exactly outcome and acceptance')
    rows = value['acceptance']
    if not isinstance(value['outcome'], str) or not value['outcome'].strip() or len(value['outcome']) > MAX_TEXT:
        raise QueueError(f'assessment outcome requires evidence text of at most {MAX_TEXT} characters')
    if (not isinstance(rows, list) or any(not isinstance(r, dict) or set(r) != {'criterion', 'evidence'} for r in rows)
            or [r['criterion'] for r in rows] != list(range(len(item['acceptance'])))
            or any(not isinstance(r['evidence'], str) or not r['evidence'].strip() or len(r['evidence']) > MAX_TEXT for r in rows)):
        raise QueueError(f"assessment acceptance requires one entry with evidence for each of {item['id']}'s {len(item['acceptance'])} criteria, in order")
    return {'outcome': value['outcome'], 'acceptance': [{'criterion': r['criterion'], 'evidence': r['evidence']} for r in rows]}


def _reconciled_view(qid, record, repeated):
    import cycle_writer
    delivery = record['delivery']
    return {'ok': True, 'reconciled': qid, 'cycle': record['id'], 'disposition': cycle_writer.queue_status(record),
            'completed': record['state'] == 'completed', 'merged': delivery['merge'] == 'merged', 'ci': delivery['ci'],
            'repeated': repeated}


def reconcile(repo, qid, pilot_id, actor, assessment):
    """Associate a pending item with the reviewed pilot that completed it.

    The pilot keeps its own identity and the item becomes started under it; the authorization and
    every other item are left as they are. The pilot record is bound first, so an interrupted call
    is finished by repeating it, and a repeat of a finished call writes and commits nothing."""
    import cycle_writer
    cfg = tree(repo)
    record = cycle_writer.load_pilot(repo, pilot_id)
    queue = read_queue(cfg)
    current = next((i for i in queue['items'] if i['id'] == qid), None)
    if current is None and queue['format_version'] == 2 and _history_path(cfg, qid).is_file():
        current = resolve_item(cfg, queue, qid)  # an archived item: a repeat still answers from history
    bound = record.get('queue')
    if (current and bound and current['state'] == 'started' and current['cycle'] == pilot_id
            and (bound['item'], bound['token']) == (qid, current['start_token'])):
        return _reconciled_view(qid, record, True)

    def change(cfg, doc):
        item = _find(doc, qid)
        if item['state'] != 'pending':
            raise QueueError(f"{qid} is {item['state']}; reconcile applies only to a pending item")
        record = cycle_writer.load_pilot(repo, pilot_id)
        status = cycle_writer.queue_status(record)
        if status not in ('reviewed', 'completed'):
            raise QueueError(f'{pilot_id} is {status}; reconcile needs its recorded approving review')
        if not re.search(rf'(?<![A-Z0-9-]){re.escape(qid)}(?![0-9])', record['title'] + '\n' + record['plan']['goal']):
            raise QueueError(f'{pilot_id} names no {qid} in its title or goal; it is not recorded as work on this item')
        if not cycle_writer.reviewed_range_contained(repo, record):
            raise QueueError(f"{pilot_id}'s reviewed head is not contained in HEAD")
        digest = _item_digest(item)
        binding = cycle_writer.bind_queue(repo, pilot_id, actor, {
            'item': qid, 'token': uuid.uuid4().hex, 'origin': 'reconcile', 'item_sha256': digest, 'review_head': record['review']['head_commit'],
            'assessment': _assessment(item, assessment), 'reconciled_at': now()})
        if binding['item_sha256'] != digest:
            raise QueueError(f'{qid} changed after {pilot_id} was bound to it; inspect both before repeating')
        item.update(state='started', cycle=pilot_id, start_token=binding['token'], started_at=binding['reconciled_at'])
        auth = doc['authorization']
        if auth and qid in auth['scope'] and qid not in auth['started']:
            auth['started'].append(qid)  # as a legacy start records it, so remaining() keeps its meaning
        doc['items'].remove(item)
        doc['items'].insert(sum(i['state'] not in UNSTARTED for i in doc['items']), item)
        return _reconciled_view(qid, cycle_writer.load_pilot(repo, pilot_id), False)

    return _mutate(repo, change, f'reconcile {qid} with {pilot_id}')


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

    return _mutate(repo, change, f'authorize {kind}' + (f' {count}' if kind == 'next-n' else ''))


def revoke(repo, reason):
    if not reason or not reason.strip():
        raise QueueError('revoke needs a non-blank reason')

    def change(cfg, doc):
        if not doc['authorization']:
            raise QueueError('no active authorization to revoke')
        _end_authorization(doc, 'revoked', reason)
        return {'ok': True, 'revoked': True}

    return _mutate(repo, change, 'revoke')


# -- start-next -------------------------------------------------------------------------

WRITER_FORMATS = ('crux.cycle.vNext', 'crux.cycle.v1')


def _origin(parsed):
    """The queue item and start token a parsed cycle record of either format carries, or None. No validation."""
    if parsed.get('format') in WRITER_FORMATS:
        bound = parsed.get('queue')
        return {'item': bound.get('item'), 'token': bound.get('token')} if isinstance(bound, dict) else None
    history = parsed.get('history')
    first = history[0] if isinstance(history, list) and history and isinstance(history[0], dict) else None
    return first.get('queue') if first and first.get('action') == 'created' else None


def _record_status(parsed):
    """Validate a parsed cycle record of either format and return the status a queue reader shows.

    A typed (legacy) record is checked by the read-only historical reader, not the typed engine's schema."""
    if parsed.get('format') in WRITER_FORMATS:
        import cycle_writer
        cycle_writer.validate(parsed)
        return cycle_writer.queue_status(parsed)
    return cycle_history.status_of(parsed)


def _record_terminal(parsed):
    """Validate a parsed cycle record and say whether its queue item is archivable. A pilot that
    completed stays archivable after an owner-authorized reopening, so reopening undoes no archival."""
    status = _record_status(parsed)
    if parsed.get('format') in WRITER_FORMATS:
        import cycle_writer
        return status == 'abandoned' or cycle_writer.ever_completed(parsed)
    return status in CLOSED


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
        if _origin(parsed) == wanted:
            matches.append((folder, parsed))
    if len(matches) > 1:
        raise QueueError(f"{item['id']} matches {len(matches)} cycles: {', '.join(f.name for f, _ in matches)}; resolve them by hand")
    if not matches:
        return None
    folder, parsed = matches[0]
    try:
        _record_status(parsed)
    except (CycleError, KeyError, TypeError) as exc:
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


def _commit_writer_start(cfg, cycle_id, item_id):
    """Commit the queue file and the new cycle record together. Never raises; the writes are already saved."""
    record = contained(cfg.docs_root, f'cycles/{cycle_id}/cycle.json').relative_to(cfg.repo_root).as_posix()
    paths = queue_paths(cfg) + [record]
    try:
        return commit_paths(cfg, paths, f'queue: start {item_id} as {cycle_id}')
    except Exception as exc:
        return {'changed': False, 'commit': None, 'paths': paths, 'message': None, 'deferred': 'commit-error',
                'detail': f'{type(exc).__name__}: {exc}'[:300]}


def _started(repo, cfg, outcome, item, found):
    writer = found.get('format') in WRITER_FORMATS
    return {'ok': True, 'outcome': outcome, 'item': item['id'], 'cycle': found['id'], 'status': _record_status(found),
            'format': found['format'] if writer else 'legacy', 'record_commit': _commit_writer_start(cfg, found['id'], item['id'])}


PLAN_KEYS = ('verification', 'council', 'tasks', 'scrutiny')


def definition_for(item, plan=None):
    """The writer definition for a queue item: the item supplies goal, scope and acceptance.

    An optional lead plan adds any of verification, council, tasks and scrutiny. Without one the
    cycle starts in planning, and the lead records the rest with the writer's plan command."""
    if plan is not None and (not isinstance(plan, dict) or set(plan) - set(PLAN_KEYS)):
        raise QueueError('a start plan holds only ' + ', '.join(PLAN_KEYS) + '; the queue item supplies goal, scope and acceptance')
    return {'goal': _goal(item), 'scope': split_scope(item['scope']), 'acceptance': list(item['acceptance']), **(plan or {})}


RELEASE_VERSION = re.compile(r'(?<![0-9.])([0-9]+\.[0-9]+\.[0-9]+)(?!\.?[0-9])')


def _release_version(doc, item):
    """The version a release item publishes: the first X.Y.Z in its title, else in the current authorization."""
    for source in (item['title'], (doc.get('authorization') or {}).get('instruction') or ''):
        found = RELEASE_VERSION.search(source)
        if found:
            return found.group(1)
    raise QueueError(f"{item['id']} is a release item and names no version: put the version, such as 1.2.3, in the item title "
                     "(queue edit --title) before it starts")


def _start_release(repo, cfg, doc, head, lead):
    """A release item's record through the cycle writer: the same intent, create, adopt and commit as any start."""
    import cycle_writer
    version, release_list = _release_version(doc, head), head.get('release_list', 'beta')
    # This item already carries the owner's frozen authority. Refuse an omission before the
    # intent, token and history writes; never widen it here.
    cycle_writer.release_scope(cfg, split_scope(head['scope']), release_list)
    if doc['format_version'] == 2:
        _archive_items(repo, cfg, doc)
    head['state'], head['start_token'] = 'starting', uuid.uuid4().hex
    write_queue(cfg, doc)
    try:
        created = create_release(repo, release_list, version, f"{head['id']}: {head['title']}", _goal(head), split_scope(head['scope']),
                                 list(head['acceptance']), lead, {'item': head['id'], 'token': head['start_token']})
    except Exception as exc:
        return _failed_start(repo, cfg, doc, head, exc)
    _adopt(doc, head, created)
    write_queue(cfg, doc)
    return _started(repo, cfg, 'started', head, created)


def _failed_start(repo, cfg, doc, head, exc):
    """After a create that raised: adopt the record it may have written, or cancel the intent and refuse."""
    found = adoption_scan(cfg, head)
    if found:
        _adopt(doc, head, found)
        write_queue(cfg, doc)
        return _started(repo, cfg, 'adopted', head, found)
    _cancel_intent(head)
    write_queue(cfg, doc)
    commit_queue(cfg, f"cancel start {head['id']}")
    raise QueueError(f"the cycle for {head['id']} was not created: {exc}") from exc


def start_next(repo, implementer='dev-lead', coordinator='dev-lead', lead=None, plan=None):
    """Start the head item when every rule allows it; otherwise return the open cycle or raise a QueueStop.

    A non-release item starts a crux.cycle.v1 record through the cycle writer, led by `lead` (the
    implementer when none is named). `plan` is an optional definition of verification, council, tasks
    and scrutiny; without it the cycle starts in planning. The item's suggested type is a recorded
    label: no classifier sizes it. A release item starts a release record with its fixed step list and
    takes no plan."""
    with locked_queue(repo) as cfg:
        doc = read_queue(cfg)
        starting = next((i for i in doc['items'] if i['state'] == 'starting'), None)
        if starting:
            found = adoption_scan(cfg, starting)
            if found:
                _adopt(doc, starting, found)
                write_queue(cfg, doc)
                return _started(repo, cfg, 'adopted', starting, found)
            _cancel_intent(starting)
            write_queue(cfg, doc)
            commit_queue(cfg, f"cancel start {starting['id']}")
        view_doc = _with_history(cfg, doc)
        verdict = decide(view_doc, _statuses(repo, view_doc))
        if verdict[0] == 'in-progress':
            return {'ok': True, 'outcome': 'in-progress', 'item': verdict[1]['id'], 'cycle': verdict[1]['cycle'], 'status': verdict[2]}
        if verdict[0] == 'stop':
            raise QueueStop(verdict[1], verdict[2], verdict[3])
        head = verdict[1]
        # Reserve room for the largest filesystem-supported cycle name and its
        # adoption fields before any archive, intent or new cycle is written.
        preview = deepcopy(doc)
        if doc['format_version'] == 2:
            archived = set(_archive_items(repo, cfg, doc, dry_run=True))
            preview['items'] = [item for item in preview['items'] if item['id'] not in archived]
        future = _find(preview, head['id'])
        future['start_token'] = '0' * 32
        _adopt(preview, future, {'id': 'XXXXXXXXXX-CYC-' + '9' * 240})
        queue_bytes(preview)
        if head['suggested_type'] == 'release':
            if plan is not None:
                raise QueueError(f"{head['id']} is a release item; its fixed step list takes no start plan")
            return _start_release(repo, cfg, doc, head, lead or implementer)
        import cycle_writer
        title, owner = f"{head['id']}: {head['title']}", lead or implementer
        definition = definition_for(head, plan)
        # Validate before the intent is written, so a refused definition leaves the item pending and burns no id.
        cycle_writer.check_definition(repo, title, owner, definition)
        if doc['format_version'] == 2:
            _archive_items(repo, cfg, doc)
        head['state'], head['start_token'] = 'starting', uuid.uuid4().hex
        write_queue(cfg, doc)
        try:
            created = create(repo, title, owner, definition, {'item': head['id'], 'token': head['start_token']})
        except Exception as exc:
            return _failed_start(repo, cfg, doc, head, exc)
        _adopt(doc, head, created)
        write_queue(cfg, doc)
        return _started(repo, cfg, 'started', head, created)


# -- command line ----------------------------------------------------------------------------

def dispatch(a):
    repo, op = a.repo_root, a.queue_op
    if op == 'add':
        return add(repo, a.title, a.outcome, a.item_type, a.scope, a.acceptance, a.depends_on, a.position, a.held, a.reason, a.references,
                   a.release_list)
    if op == 'list':
        return list_view(repo, getattr(a, 'full', False))
    if op == 'archive':
        return archive(repo, a.dry_run, a.migrate)
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
    if op == 'reconcile':
        return reconcile(repo, a.item, a.pilot, a.actor, json.loads(Path(a.file).read_text(encoding='utf-8')))
    if op == 'authorize':
        return authorize(repo, a.kind, a.instruction, a.date, a.count)
    if op == 'revoke':
        return revoke(repo, a.reason)
    if op == 'start-next':
        # `--pilot` is an accepted no-op: every non-release start is the writer's start.
        plan = json.loads(Path(a.plan).read_text(encoding='utf-8')) if getattr(a, 'plan', None) else None
        return start_next(repo, a.implementer, a.coordinator, getattr(a, 'lead', None), plan)
    raise QueueError(f'unknown queue operation {op}')


def run(a):
    """Run a parsed `queue` command; return (exit code, payload). 1 refuses or stops, 2 is the environment."""
    try:
        return 0, dispatch(a)
    except QueueStop as stop:
        return 1, {'ok': False, 'stop': {'reason': stop.reason, 'item': stop.item, 'detail': stop.detail,
                                         **({'missing': stop.missing} if stop.missing else {})}}
    except (QueueEnvError, BionicConfigError, OSError) as exc:
        return 2, {'ok': False, 'error': str(exc)}
    except (CycleError, ValueError, KeyError) as exc:
        return 1, {'ok': False, 'error': str(exc)}
