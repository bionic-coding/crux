"""Retain explicit owner evidence; serialize capture and application under the cycle lock.

The caller supplies observed intent and actual provenance. This writer validates
bindings and structure; it authenticates neither a speaker nor natural language.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re

from cycle_workflow import (PHASES, CycleError, atomic, contained, digest, encoded, event,
                            load, locked, now, plan_file_of, revise_plan, save, withdrawn_names)
from secret_scan import scan_fields, scan_text

PRESENTATION = 'crux.owner-decision-presentation.v1'
CAPTURE = 'crux.owner-decision-capture.v1'
APPLICATION = 'crux.owner-decision-application.v1'
BINDING = ('purpose', 'cycle_id', 'subject', 'subject_sha256')
REF_KEYS = {'path', 'sha256'}
MAX_BYTES = 1024 * 1024
PURPOSES = ('idr', 'adr-acceptance', 'acceptance-change')
PROPOSAL_KEYS = {'cycle_id', 'plan_revision', 'remove', 'move', 'add'}


class OwnerDecisionError(CycleError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def fail(code):
    raise OwnerDecisionError(code)


def _plain(value):
    return (isinstance(value, str) and bool(value) and not value.startswith(('/', '~'))
            and '\\' not in value and not any(ord(c) < 32 for c in value)
            and all(p not in ('', '.', '..') for p in value.split('/')))


def _reference(ref):
    if (not isinstance(ref, dict) or set(ref) != REF_KEYS or not _plain(ref.get('path'))
            or not isinstance(ref.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', ref['sha256'])):
        fail('invalid-reference')
    return ref


def _scan(value):
    try:
        unsafe = scan_fields(value) or scan_text(json.dumps(value))
    except Exception:
        fail('scanner-unavailable')
    if unsafe:
        fail('unsafe-owner-evidence')
    if len(encoded(value)) > MAX_BYTES:
        fail('owner-evidence-too-large')


def _binding(value):
    if value.get('purpose') not in PURPOSES:
        fail('invalid-purpose')
    if not _plain(value.get('subject')):
        fail('invalid-subject')
    if not isinstance(value.get('subject_sha256'), str) or not re.fullmatch('[0-9a-f]{64}', value['subject_sha256']):
        fail('invalid-subject-digest')
    if value.get('cycle_id') is not None and not isinstance(value['cycle_id'], str):
        fail('invalid-cycle')
    if value['purpose'] == 'idr' and not value.get('cycle_id'):
        fail('idr-requires-cycle')
    if value['purpose'] == 'acceptance-change' and not value.get('cycle_id'):
        fail('acceptance-change-requires-cycle')
    return {key: value[key] for key in BINDING}


def _request(value, extra, *, operation=False):
    keys = set(BINDING) | set(extra) | ({'op_id'} if operation else set())
    if not isinstance(value, dict) or set(value) != keys:
        fail('invalid-request-fields')
    _binding(value)
    if operation and (not isinstance(value['op_id'], str) or not re.fullmatch('[A-Za-z0-9._-]{8,64}', value['op_id'])):
        fail('invalid-operation-id')
    _scan(value)


def _root(value):
    identity = value['cycle_id']
    if identity is not None:
        if not re.fullmatch(r'(?:[A-Z][A-Z0-9]*-)?CYC-\d{4,}', identity):
            fail('invalid-cycle')
        return f'cycles/{identity}/owner-decisions'
    return 'adrs/owner-decisions'


def _active(cfg, value):
    if value['cycle_id'] is not None:
        doc = load(cfg.repo_root, value['cycle_id'])
        if doc['status'] != 'active':
            fail('cycle-not-active')
        if doc['type'] == 'release':
            fail('owner-decisions-unavailable-for-release')
        return doc


def _subject(cfg, value):
    path = contained(cfg.docs_root, value['subject'])
    if not path.is_file():
        fail('subject-missing')
    if value['purpose'] == 'idr':
        doc = load(cfg.repo_root, value['cycle_id'])
        target = next((d for d in doc['decisions'] if d['path'] == value['subject'] and d['kind'] == 'idr'), None)
        if target is None:
            fail('subject-owner-mismatch')
        if path.stat().st_size > MAX_BYTES or digest(path.read_bytes()) != target['sha256']:
            fail('retained-subject-changed')
    elif value['purpose'] == 'acceptance-change':
        directory = contained(cfg.docs_root, f"cycles/{value['cycle_id']}/acceptance")
        if (path.parent != directory or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.json', path.name)
                or value['subject'] != f"cycles/{value['cycle_id']}/acceptance/{path.name}"):
            fail('subject-owner-mismatch')
        if path.stat().st_size > MAX_BYTES:
            fail('subject-too-large')
        try:
            proposal = json.loads(path.read_bytes())
        except ValueError:
            fail('invalid-acceptance-proposal')
        if not isinstance(proposal, dict) or proposal.get('cycle_id') != value['cycle_id']:
            fail('subject-owner-mismatch')
    else:
        if (path.parent != cfg.docs_root / 'adrs'
                or not re.fullmatch(r'(?:[A-Z][A-Z0-9]*-)?ADR-\d{4,}-.+\.md', path.name)):
            fail('subject-owner-mismatch')
        from decision_policy import frontmatter
        front, _ = frontmatter(path.read_text())
        metadata = contained(cfg.docs_root, f'adrs/proposals/{front["id"]}.json')
        if not metadata.is_file():
            fail('new-policy-proposal-required')
        proposal = json.loads(metadata.read_text())
        if proposal.get('subject') != value['subject'] or proposal.get('cycle_id') != value['cycle_id']:
            fail('subject-owner-mismatch')
    if path.stat().st_size > MAX_BYTES:
        fail('subject-too-large')
    return path


def _schema(record):
    from council_records import _validator
    validator = _validator()
    schema = validator.load_schema(Path(__file__).parents[1] / 'schemas/owner-decision.schema.json')
    errors = []
    validator.validate(record, schema, '#', '#', errors, 'owner-decision')
    if errors:
        fail('invalid-owner-evidence')
    unsealed = {k: v for k, v in record.items() if k != 'record_sha256'}
    if record['record_sha256'] != digest(encoded(unsealed)):
        fail('owner-evidence-integrity')
    _binding(record)
    if record['format'] == CAPTURE:
        for key in ('quote', 'owner_date'):
            if not record[key].strip():
                fail('invalid-owner-evidence')
        if not record['source']['reference'].strip():
            fail('missing-provenance')
        try:
            if date.fromisoformat(record['owner_date']).isoformat() != record['owner_date']:
                fail('invalid-owner-date')
        except ValueError:
            fail('invalid-owner-date')
    return record


def _seal(value):
    value = dict(value)
    value['record_sha256'] = digest(encoded(value))
    _schema(value)
    _scan(value)
    return value


def _reader(cfg):
    def read(relative):
        path = contained(cfg.docs_root, relative)
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            fail('owner-evidence-missing-or-oversized')
        return path.read_bytes()
    return read


def _load(read, ref, kind):
    _reference(ref)
    category = {PRESENTATION: 'presentations', CAPTURE: 'captures', APPLICATION: 'applications'}[kind]
    pattern = (r'(?:cycles/(?:[A-Z][A-Z0-9]*-)?CYC-\d{4,}|adrs)/owner-decisions/'
               + category + r'/[A-Za-z0-9._-]{8,64}\.json')
    if not re.fullmatch(pattern, ref['path']):
        fail('owner-evidence-path-mismatch')
    try:
        raw = read(ref['path'])
        if len(raw) > MAX_BYTES or digest(raw) != ref['sha256']:
            fail('owner-evidence-reference-mismatch')
        record = _schema(json.loads(raw))
    except OwnerDecisionError:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        fail('owner-evidence-unreadable')
    if record['format'] != kind:
        fail('owner-evidence-format-mismatch')
    if ref['path'] != _path(record, kind):
        fail('owner-evidence-path-mismatch')
    return record


def _path(value, kind):
    category = {PRESENTATION: 'presentations', CAPTURE: 'captures', APPLICATION: 'applications'}[kind]
    ident = value['op_id'] if kind != APPLICATION else Path(value['capture']['path']).stem
    return f'{_root(value)}/{category}/{ident}.json'


def _ref(cfg, path):
    return {'path': path, 'sha256': digest(contained(cfg.docs_root, path).read_bytes())}


def _store(cfg, record):
    path = _path(record, record['format'])
    target = contained(cfg.docs_root, path)
    if target.exists():
        old = _load(_reader(cfg), _ref(cfg, path), record['format'])
        ignore = {'at', 'record_sha256'}
        if {k: v for k, v in old.items() if k not in ignore} != {k: v for k, v in record.items() if k not in ignore}:
            fail('operation-conflict')
        return _ref(cfg, path), old, True
    atomic(target, record)
    return _ref(cfg, path), record, False


def validate_capture_evidence(read, ref):
    """Validate immutable evidence without reinterpreting later captures as revocation."""
    capture = _load(read, ref, CAPTURE)
    presentation = _load(read, capture['presentation'], PRESENTATION)
    if _binding(capture) != _binding(presentation):
        fail('presentation-binding-mismatch')
    return capture


def _lineage(cfg, capture):
    rows = {}
    root = contained(cfg.docs_root, _root(capture) + '/captures')
    for path in sorted(root.glob('*.json')):
        name = path.relative_to(cfg.docs_root).as_posix()
        ref = _ref(cfg, name)
        value = validate_capture_evidence(_reader(cfg), ref)
        if _binding(value) == _binding(capture):
            rows[name] = (ref, value)
    children = {}
    for name, (_, value) in rows.items():
        previous = value['supersedes']
        if previous is not None:
            _reference(previous)
            if previous['path'] not in rows or rows[previous['path']][0] != previous:
                fail('cross-subject-or-missing-supersession')
            children.setdefault(previous['path'], []).append(name)
            if len(children[previous['path']]) > 1:
                fail('forked-owner-lineage')
        seen = set()
        cursor = name
        while cursor in rows:
            if cursor in seen:
                fail('cyclic-owner-lineage')
            seen.add(cursor)
            predecessor = rows[cursor][1]['supersedes']
            if predecessor is None:
                break
            cursor = predecessor['path']
    heads = [row for name, row in rows.items() if name not in children]
    if len(heads) != 1:
        fail('ambiguous-owner-lineage')
    return heads[0]


def _current(cfg, capture, ref):
    head, value = _lineage(cfg, capture)
    if head != ref:
        fail('superseded-owner-capture')
    if capture['disposition'] != 'approve':
        fail('owner-capture-not-approved')
    return head, value


def acknowledgment(cfg, capture):
    head, value = _lineage(cfg, capture)
    return {'current_capture': head, 'current_disposition': value['disposition'], 'lifecycle_changed': False,
            'lifecycle_route': {'adr-acceptance': 'transition-adr under separate lifecycle authorization',
                                'acceptance-change': 'a later acceptance-change capture, or a plan revision in Plan or Build'}.get(
                                    capture['purpose'], 'revise the IDR or withdraw-decision in Plan under its existing requirements')}


def resolve_capture(cfg, request):
    _request(request, {'capture'})
    capture = validate_capture_evidence(_reader(cfg), request['capture'])
    if _binding(capture) != _binding(request):
        fail('capture-binding-mismatch')
    return capture


def authorize_adr(cfg, request, subject, cycle_id, proposed_sha256):
    """Called only inside decision_policy.accept's existing mutation lock."""
    capture = resolve_capture(cfg, request)
    if _binding(capture) != {'purpose': 'adr-acceptance', 'cycle_id': cycle_id,
                             'subject': subject, 'subject_sha256': proposed_sha256}:
        fail('capture-binding-mismatch')
    _current(cfg, capture, request['capture'])
    return capture


def present(repo, request):
    _request(request, {'question'}, operation=True)
    if not isinstance(request['question'], str) or not request['question'].strip():
        fail('question-required')
    with locked(repo) as (cfg, _):
        value = _seal({'format': PRESENTATION, **request, 'at': now()})
        if contained(cfg.docs_root, _path(value, PRESENTATION)).exists():
            ref, record, replayed = _store(cfg, value)
            return {'presentation': ref, 'record': record, 'replayed': replayed}
        _active(cfg, request)
        path = _subject(cfg, request)
        if digest(path.read_bytes()) != request['subject_sha256']:
            fail('stale-presented-subject')
        ref, record, replayed = _store(cfg, value)
        return {'presentation': ref, 'record': record, 'replayed': replayed}


def capture(repo, request):
    _request(request, {'presentation', 'disposition', 'quote', 'source', 'owner_date', 'supersedes'}, operation=True)
    with locked(repo) as (cfg, _):
        shown = _load(_reader(cfg), request['presentation'], PRESENTATION)
        if _binding(shown) != _binding(request):
            fail('presentation-binding-mismatch')
        value = _seal({'format': CAPTURE, **request, 'at': now()})
        path = _path(value, CAPTURE)
        if contained(cfg.docs_root, path).exists():
            ref, record, replayed = _store(cfg, value)
        else:
            _active(cfg, request)
            root = contained(cfg.docs_root, _root(value) + '/captures')
            prior = []
            for candidate in root.glob('*.json'):
                candidate_ref = _ref(cfg, candidate.relative_to(cfg.docs_root).as_posix())
                old = validate_capture_evidence(_reader(cfg), candidate_ref)
                if _binding(old) == _binding(value):
                    prior.append(old)
            if prior:
                head, _ = _lineage(cfg, value)
                if request['supersedes'] != head:
                    fail('forked-or-stale-owner-supersession')
            elif request['supersedes'] is not None:
                fail('cross-subject-or-missing-supersession')
            ref, record, replayed = _store(cfg, value)
        head, _ = _lineage(cfg, record)
        return {'capture': ref, 'record': record, 'replayed': replayed, 'current': head == ref}


def _application_record(cfg, capture_ref, capture, applied_at):
    value = _seal({'format': APPLICATION, **_binding(capture), 'capture': capture_ref, 'applied_at': applied_at})
    return _store(cfg, value)[0]


def _apply_idr(cfg, request):
    capture = resolve_capture(cfg, request)
    if capture['disposition'] != 'approve':
        fail('owner-capture-not-approved')
    doc = load(cfg.repo_root, capture['cycle_id'])
    target = next((d for d in doc['decisions'] if d['path'] == capture['subject'] and d['kind'] == 'idr'), None)
    if target is None:
        fail('subject-owner-mismatch')
    previous = next((e for e in doc['history'] if e['action'] == 'owner-decision-applied'
                     and e.get('capture') == request['capture']), None)
    if previous is not None:
        application = _application_record(cfg, request['capture'], capture, previous['at'])
        return {'applied': True, 'already_applied': True, 'application': application, **acknowledgment(cfg, capture)}
    _active(cfg, capture)
    _current(cfg, capture, request['capture'])
    path = _subject(cfg, capture)
    if digest(path.read_bytes()) != capture['subject_sha256']:
        fail('stale-presented-subject')
    if target['name'] in withdrawn_names(doc):
        fail('decision-withdrawn')
    if next(d for d in reversed(doc['decisions']) if d['name'] == target['name'])['path'] != capture['subject']:
        fail('stale-decision-revision')
    target['approval'] = request['capture']['path']
    event(doc, 'owner-decision-applied', capture=request['capture'], subject=capture['subject'])
    save(cfg, doc)
    application = _application_record(cfg, request['capture'], capture, doc['history'][-1]['at'])
    return {'applied': True, 'already_applied': False, 'application': application, **acknowledgment(cfg, capture)}


def _proposal(raw):
    """The acceptance-change proposal shape: exact current criteria to remove or move, and new ones to add."""
    try:
        value = json.loads(raw)
    except ValueError:
        fail('invalid-acceptance-proposal')
    def texts(items):
        return isinstance(items, list) and all(isinstance(i, str) and i.strip() for i in items)
    if (not isinstance(value, dict) or set(value) != PROPOSAL_KEYS or type(value['plan_revision']) is not int
            or not texts(value['remove']) or not texts(value['add']) or not isinstance(value['move'], list)
            or not all(isinstance(m, dict) and set(m) == {'criterion', 'queue_item'} and isinstance(m['criterion'], str)
                       and m['criterion'].strip() and isinstance(m['queue_item'], str) for m in value['move'])
            or not (value['remove'] or value['move'] or value['add'])):
        fail('invalid-acceptance-proposal')
    return value


def _changed_acceptance(cfg, doc, proposal):
    """The new acceptance list, or a refusal code naming the failed check."""
    if 'plan' not in PHASES[doc['type']] or doc['phase'] not in ('plan', 'build'):
        fail('acceptance-change-phase')
    if proposal['plan_revision'] != doc['plan']['revision']:
        fail('acceptance-change-stale-plan')
    current = doc['plan']['acceptance']
    removed = list(proposal['remove'])
    moved = [m['criterion'] for m in proposal['move']]
    named = removed + moved
    if len(set(named)) != len(named):
        fail('acceptance-change-criterion-conflict')
    for criterion in named:
        if current.count(criterion) != 1:
            fail('acceptance-change-criterion-not-unique')
    kept = [c for c in current if c not in named]
    added = list(proposal['add'])
    if len(set(added)) != len(added) or any(a in kept for a in added):
        fail('acceptance-change-duplicate-add')
    if proposal['move']:
        import cycle_queue
        try:
            queue = cycle_queue.read_queue(cfg)
        except CycleError:
            fail('acceptance-change-queue-unreadable')
        for row in proposal['move']:
            try:
                item = cycle_queue.resolve_item(cfg, queue, row['queue_item'])
            except CycleError:
                fail('acceptance-change-destination-missing')
            if item['state'] not in ('pending', 'held'):
                fail('acceptance-change-destination-started')
            if row['criterion'] not in item['acceptance']:
                fail('acceptance-change-destination-lacks-criterion')
    if named:
        lowest = min(current.index(c) for c in named)
        for task in doc['plan']['tasks']:
            criterion = task.get('fix', {}).get('criterion')
            if isinstance(criterion, dict) and criterion.get('index', -1) >= lowest:
                fail('acceptance-change-criterion-fix-shift')
    return kept + added


def _apply_acceptance(cfg, request):
    capture = resolve_capture(cfg, request)
    if capture['disposition'] != 'approve':
        fail('owner-capture-not-approved')
    doc = load(cfg.repo_root, capture['cycle_id'])
    ref = request['capture']
    # A replay acknowledges the plan revision written in the same save, before any check that it changed.
    previous = next((e for e in doc['history'] if e['action'] == 'plan-revised'
                     and ref['path'] in str(e.get('reason', '')) and ref['sha256'] in str(e.get('reason', ''))), None)
    if previous is not None:
        application = _application_record(cfg, ref, capture, previous['at'])
        return {'applied': True, 'already_applied': True, 'application': application, **acknowledgment(cfg, capture)}
    _active(cfg, capture)
    _current(cfg, capture, ref)
    path = _subject(cfg, capture)
    raw = path.read_bytes()
    if digest(raw) != capture['subject_sha256']:
        fail('stale-presented-subject')
    acceptance = _changed_acceptance(cfg, doc, _proposal(raw))
    plan = plan_file_of(doc)
    plan['acceptance'] = acceptance
    reason = (f"owner acceptance-change capture {ref['path']} sha256 {ref['sha256']} "
              f"applied to {capture['subject']}")
    revise_plan(cfg, doc, plan, reason)
    event(doc, 'plan', reason=reason)
    event(doc, 'owner-decision-applied', capture=ref, subject=capture['subject'])
    save(cfg, doc)
    # The application time is the plan-revised event's, so a replay writes the identical application record.
    revised = next(e for e in reversed(doc['history']) if e['action'] == 'plan-revised' and e.get('reason') == reason)
    application = _application_record(cfg, ref, capture, revised['at'])
    return {'applied': True, 'already_applied': False, 'application': application, **acknowledgment(cfg, capture)}


def validate_applied_idr(cfg, path, *, purpose, subject, subject_sha256, cycle_id):
    ref = _ref(cfg, path)
    capture = validate_capture_evidence(_reader(cfg), ref)
    if (purpose != 'idr' or _binding(capture) != {'purpose': 'idr', 'cycle_id': cycle_id,
                                                'subject': subject, 'subject_sha256': subject_sha256}
            or capture['disposition'] != 'approve'):
        fail('capture-binding-mismatch')
    application = _path({'capture': ref, **_binding(capture)}, APPLICATION)
    record = _load(_reader(cfg), _ref(cfg, application), APPLICATION)
    doc = load(cfg.repo_root, cycle_id)
    if record['capture'] != ref or not any(e['action'] == 'owner-decision-applied' and e.get('capture') == ref for e in doc['history']):
        fail('owner-capture-not-applied')
    return capture


def apply(repo, request):
    if not isinstance(request, dict):
        fail('invalid-request-fields')
    if request.get('purpose') == 'idr':
        with locked(repo) as (cfg, _):
            return _apply_idr(cfg, request)
    if request.get('purpose') == 'acceptance-change':
        with locked(repo) as (cfg, _):
            return _apply_acceptance(cfg, request)
    _request(request, {'capture', 'approval'})
    owner_request = {k: v for k, v in request.items() if k != 'approval'}
    from decision_policy import accept
    result = accept(repo, request['subject'], request['approval'], owner_decision=owner_request)
    return result['owner_decision_state']


def validate_reapproval(read, previous, current):
    """Require retained same-proposal descent from an interrupted approval."""
    original=validate_capture_evidence(read,previous)
    captured=validate_capture_evidence(read,current)
    if previous==current or _binding(original)!=_binding(captured) or captured['disposition']!='approve':
        fail('invalid-acceptance-reapproval')
    seen=set()
    while captured['supersedes']!=previous:
        predecessor=captured['supersedes']
        if predecessor is None or predecessor['path'] in seen:
            fail('unrelated-acceptance-reapproval')
        seen.add(predecessor['path'])
        captured=validate_capture_evidence(read,predecessor)
        if _binding(captured)!=_binding(original):
            fail('cross-subject-acceptance-reapproval')


def adr_result(cfg, receipt, request, *, already_applied):
    capture = resolve_capture(cfg, request)
    from decision_policy import receipt_identity
    return {**receipt, 'owner_decision_state': {
        'applied': True, 'already_applied': already_applied,
        'application': _ref(cfg, receipt_identity(receipt)),
        **acknowledgment(cfg, capture)}}
