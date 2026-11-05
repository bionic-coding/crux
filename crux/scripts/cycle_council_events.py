"""Durable diagnostic call events beside a council's existing attempt ownership."""
from __future__ import annotations

import json
import os
from pathlib import Path

import council_policy as policy
import cycle_context_read as reader
from cycle_workflow import CycleError, atomic_bytes, contained, digest, encoded, tree

FORMAT = 'crux.council-call-events.v1'
EVENT = 'crux.council-call-event.v1'
SEATS = ('openai', 'anthropic', 'gemini')
PHASES = ('request', 'outcome')


def _validate(value):
    from council_records import _validator
    validator = _validator()
    schema = validator.load_schema(Path(__file__).resolve().parents[1] / 'schemas/cycle-council-call.schema.json')
    errors = []
    validator.validate(value, schema, '#', '#', errors, 'council call checkpoint')
    if errors:
        raise CycleError('invalid council call checkpoint schema')


def enable(attempt, models):
    attempt['call_checkpoints'] = {'format': FORMAT, 'models': {
        ('gemini' if seat == 'google' else seat): model for seat, model in models.items()}}


def _path(attempt_path, seat, number, phase):
    return attempt_path.parent / ('calls-' + attempt_path.stem.removeprefix('attempt-')) / f'{seat}-{number}-{phase}.json'


def _binding(attempt, relative):
    return {key: attempt.get(key) for key in ('id', 'subject', 'subject_sha256', 'cycle_id')} | {'attempt': relative}


def _safe(value, key):
    import secret_scan
    from untrusted import redact
    if isinstance(value, str):
        if secret_scan.scan_text(value, exact=[key] if key else []):
            return '[redacted unsafe council evidence]'
        return redact(value, quoted=False, limit=reader.MAX_OBJECT_BYTES)
    if isinstance(value, dict):
        return {_safe(k, key): _safe(v, key) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(v, key) for v in value]
    return value


def _available(payload):
    if payload is None:
        return None
    raw = encoded(payload)
    if len(raw) <= reader.MAX_OBJECT_BYTES // 2:
        return payload
    vote = payload.get('vote') or {}
    decision = vote.get('decision')
    return {key: payload[key] for key in ('format', 'id', 'attempt', 'subject_sha256', 'phase', 'seat', 'call_number')} | {
        'vote': {'decision': decision if decision in ('APPROVE', 'APPROVE_WITH_NITS', 'REQUEST_CHANGES', 'REJECT', 'ARCHITECTURAL', 'DEFER_TO_HUMAN') else 'unknown'},
        'evidence_unavailable': {'reason': 'diagnostic-size-bound', 'size_bytes': len(raw), 'sha256': digest(raw)}}


class Sink:
    def __init__(self, cfg, path, attempt, ownership, key):
        self.cfg, self.path, self.attempt, self.ownership, self.key = cfg, path, attempt, ownership, key
        self.relative = path.relative_to(cfg.docs_root).as_posix()
        self.failure = None

    def __call__(self, value):
        payload = None
        try:
            phase, seat, number = value['phase'], value['seat'], value['call_number']
            if self.failure and phase == 'request':
                raise CycleError('a failed checkpoint prevents further requests')
            if phase not in PHASES or seat not in SEATS or type(number) is not int or number not in (1, 2):
                raise CycleError('invalid call checkpoint identity')
            current = policy.read_json(self.cfg.repo_root, self.path.relative_to(self.cfg.repo_root).as_posix())
            if (current.get('status') != 'running' or _binding(current, self.relative) != _binding(self.attempt, self.relative)
                    or current.get('call_checkpoints') != self.attempt.get('call_checkpoints')):
                raise CycleError('call checkpoint claim is closed or changed')
            # The runner supplies its existing flock descriptor, never a replacement ownership lock.
            if os.fstat(self.ownership).st_ino != self.path.with_suffix('.lock').stat().st_ino:
                raise CycleError('call checkpoint ownership changed')
            models = self.attempt['call_checkpoints']['models']
            if value['registry_key'] != models[seat]:
                raise CycleError('call checkpoint model changed')
            payload = {'format': EVENT, **_binding(self.attempt, self.relative),
                       **{name: _safe(value[name], self.key) for name in
                          ('phase', 'seat', 'call_number', 'registry_key', 'requested_model', 'metadata', 'vote')}}
            sealed = policy.seal(payload)
            _validate(sealed)
            raw = encoded(sealed)
            if len(raw) > reader.MAX_OBJECT_BYTES or reader._scan(raw.decode()):
                raise CycleError('call checkpoint exceeds safe evidence bounds')
            path = _path(self.path, seat, number, phase)
            if path.parent.is_symlink():
                raise CycleError('call checkpoint directory is not a regular owned directory')
            if path.exists():
                raise CycleError('call checkpoint already exists; never repeat its request')
            atomic_bytes(path, raw)
        except Exception as exc:
            # This fallback is diagnostic only, and can never satisfy durable call completeness.
            self.failure = self.failure or {'phase': value.get('phase'), 'seat': value.get('seat'), 'call_number': value.get('call_number'),
                                           'cause': type(exc).__name__, 'available_outcome': _available(payload) if value.get('phase') == 'outcome' else None}
            raise CycleError('council call checkpoint unavailable') from None


def read(repo, relative, *, attempt=None):
    cfg = tree(repo)
    path = contained(cfg.docs_root, relative)
    attempt = attempt or policy.read_json(repo, path.relative_to(cfg.repo_root).as_posix())
    marker = attempt.get('call_checkpoints')
    if marker is None:
        return {'required': False, 'complete': False, 'events': [], 'calls': [], 'limit': 'historical-no-call-checkpoints'}
    if marker.get('format') != FORMAT or not isinstance(marker.get('models'), dict):
        raise CycleError('invalid council checkpoint binding')
    events, calls = [], []
    for seat in SEATS:
        for number in (1, 2):
            pair = {}
            for phase in PHASES:
                event_path = _path(path, seat, number, phase)
                if not event_path.exists() and not event_path.is_symlink():
                    continue
                try:
                    raw = reader._bounded_bytes(reader.Reference(event_path, cfg.repo_root))
                    if reader._scan(raw.decode()):
                        raise CycleError('unsafe council checkpoint')
                    value = json.loads(raw)
                    policy.verify_seal(value)
                    _validate(value)
                except (reader.ReadRefused, ValueError, OSError):
                    raise CycleError('unavailable council checkpoint') from None
                if (value.get('format') != EVENT or any(value.get(k) != v for k, v in _binding(attempt, relative).items())
                        or value.get('phase') != phase or value.get('seat') != seat or value.get('call_number') != number
                        or value.get('registry_key') != marker['models'].get(seat)):
                    raise CycleError('council checkpoint belongs to another call or subject')
                ref = {'path': event_path.relative_to(cfg.docs_root).as_posix(), 'sha256': digest(raw)}
                events.append(ref)
                pair[phase] = (ref, value)
            if not pair:
                continue
            if 'request' not in pair:
                raise CycleError('council outcome has no durable request checkpoint')
            call = {'seat': seat, 'call_number': number, 'request': pair['request'][0],
                    'status': 'known' if 'outcome' in pair else 'unknown'}
            if 'outcome' in pair:
                call.update(outcome=pair['outcome'][0], metadata=pair['outcome'][1]['metadata'], vote=pair['outcome'][1]['vote'])
            calls.append(call)
        seat_calls = [call for call in calls if call['seat'] == seat]
        if seat_calls and seat_calls[0]['call_number'] != 1:
            raise CycleError('council retry has no first call checkpoint')
        if len(seat_calls) == 2 and seat_calls[0]['status'] != 'known':
            raise CycleError('council retry bypassed its prior outcome checkpoint')
    complete = (set(marker['models']) == set(SEATS) and {c['seat'] for c in calls} == set(SEATS)
                and all(c['status'] == 'known' for c in calls) and not attempt.get('checkpoint_failure'))
    return {'required': True, 'complete': complete, 'events': events, 'calls': calls}


def finish(cfg, path, attempt, record, sink=None):
    if not attempt.get('call_checkpoints'):
        return []
    evidence = read(cfg.repo_root, path.relative_to(cfg.docs_root).as_posix(), attempt=attempt)
    if sink is not None and sink.failure:
        record['checkpoint_failure'] = sink.failure
        attempt['checkpoint_failure'] = sink.failure
    if record.get('checkpoint_failure'):
        evidence['complete'] = False
    # A fabricated/mock aggregate cannot skip the required request/outcome protocol.
    for seat in record.get('seats', []):
        name = 'gemini' if seat.get('provider') == 'google' else seat.get('provider')
        outcomes = [call for call in evidence['calls'] if call['seat'] == name and call['status'] == 'known']
        vote = outcomes[-1].get('vote') if outcomes else None
        if not vote or any(vote.get(key) != _safe(seat.get(key), sink.key if sink else None) for key in ('decision', 'findings')):
            evidence['complete'] = False
    record['call_evidence'] = evidence
    if not evidence['complete'] and record.get('outcome') != 'could-not-run':
        record.update(outcome='could-not-run', reason='call-checkpoint-unavailable')
    return [contained(cfg.docs_root, ref['path']) for ref in evidence['events']]


def validate_current(repo, record, *, record_path):
    """New approval/application requires current artifacts; sealed historical standing is separate."""
    claimed = record.get('call_evidence') or {}
    if not claimed.get('required'):
        return
    cfg = tree(repo)
    relative = record.get('attempt')
    if not isinstance(relative, str):
        raise CycleError('council checkpoint attempt binding is missing')
    path = contained(cfg.docs_root, relative)
    attempt = policy.read_json(repo, path.relative_to(cfg.repo_root).as_posix())
    if (not attempt.get('call_checkpoints') or attempt.get('status') != 'finished'
            or attempt.get('record') != record_path
            or any(attempt.get(key) != record.get(key) for key in ('purpose', 'subject', 'subject_sha256', 'cycle_id'))
            or (record.get('format') == policy.RECORD and any(attempt.get(key) != record.get(key) for key in ('id', 'logical_id', 'policy')))):
        raise CycleError('council checkpoint attempt identity is stale or incomplete')
    current = read(repo, relative, attempt=attempt)
    if not current['complete'] or current != claimed:
        raise CycleError('required council checkpoint references are missing or changed')


def historical(repo, rows):
    from cycle_council import council_directory, logical_directory
    cfg = tree(repo)
    out = []
    for row in rows:
        if not row.get('call_checkpoints'):
            continue
        directory = (logical_directory(cfg, row['logical_id'], row.get('cycle_id')) if row.get('logical_id')
                     else council_directory(cfg, row.get('cycle_id')))
        relative = (directory / ('attempt-' + row['id'] + '.json')).relative_to(cfg.docs_root).as_posix()
        out.append({'kind': 'historical-partial-evidence', 'attempt': relative, 'subject_sha256': row['subject_sha256'],
                    'evidence': read(repo, relative, attempt=row), 'checkpoint_failure': row.get('checkpoint_failure')})
    return out
