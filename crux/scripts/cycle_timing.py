"""Elapsed and paused time of a cycle, computed from its history alone.

A pure function of a cycle document and an explicit `now`: it reads no clock and
stores nothing, so no copy of the result can drift from the history it came from.

Rules:
- The timeline never runs backwards. Each history entry's effective time is the
  later of its own timestamp and the previous effective time; `now` is clamped to
  at least the last effective time. Active and paused seconds therefore add up to
  `elapsed_seconds`.
- The time between two entries belongs to the state the earlier entry left. It is
  paused when that state is `paused` and active otherwise.
- An entry carries the resulting `status` when the writer recorded it. Without
  one, `pause`, `resume`, `owner-complete` and `abandon` name their own result. A
  `return` leaves the cycle paused only when `resume` is the next entry (after any
  `extend`), or when it is the last entry of a cycle whose status is paused; a
  resume is legal only on a paused cycle, so that proves the wait. Such an
  inference labels the timing `derived`; a record read entirely from entries it
  names is `recorded`.
- Completion or abandonment closes every segment and wait at that entry, so a
  closed cycle's values do not change with `now`.
- A segment is a run of time under one (pass, phase) pair; it changes each time
  that pair changes.
"""
from __future__ import annotations

from datetime import datetime, timezone

CLOSED = {'completed', 'abandoned'}
KNOWN = {'active', 'paused'} | CLOSED
_SELF = {'pause': 'paused', 'resume': 'active', 'owner-complete': 'completed', 'abandon': 'abandoned'}


def _parse(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _now(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromtimestamp(value, timezone.utc)


def _iso(moment):
    return moment.astimezone(timezone.utc).isoformat()


def _resolve(history, i, previous, doc_status):
    """Return (status after entry i, whether it was inferred)."""
    entry = history[i]
    last = i == len(history) - 1
    recorded = entry.get('status')
    if recorded in KNOWN:
        return recorded, False
    action = entry.get('action')
    if action in _SELF:
        status, inferred = _SELF[action], False
    elif action == 'return':
        j = i + 1
        while j < len(history) and history[j].get('action') == 'extend':
            j += 1
        paused = (j < len(history) and history[j].get('action') == 'resume') or (j >= len(history) and doc_status == 'paused')
        status, inferred = ('paused' if paused else 'active'), True
    else:
        status, inferred = previous, False
    if last and doc_status in CLOSED and status not in CLOSED:
        return doc_status, True
    if last and doc_status == 'paused' and status == 'active':
        return 'paused', True
    return status, inferred


def cycle_timing(doc, now):
    """Timing of `doc` at `now` (an aware datetime or epoch seconds)."""
    history = [e for e in doc.get('history') or [] if isinstance(e, dict)]
    first = _parse(history[0].get('at')) if history else None
    started = _parse(doc.get('created_at')) or first or _now(now)
    # Effective times: nondecreasing, never before the start.
    effective, floor = [], started
    for entry in history:
        stamp = _parse(entry.get('at'))
        floor = max(floor, stamp) if stamp else floor
        effective.append(floor)
    # State after each entry, stopping at the entry that closed the cycle.
    states, derived, ended = [], False, None
    status = 'active'
    for i in range(len(history)):
        status, inferred = _resolve(history, i, status, doc.get('status'))
        derived = derived or inferred
        states.append(status)
        if status in CLOSED:
            ended = i
            break
    used = len(states)
    end = effective[ended] if ended is not None else max(_now(now), effective[-1] if effective else started)
    # Intervals: (start, end, state, key). The span before the first entry is active.
    intervals = []
    if history:
        key0 = (history[0].get('pass'), history[0].get('phase'))
        intervals.append((started, effective[0], 'active', key0))
        for i in range(used):
            stop = effective[i + 1] if i + 1 < used else end
            if ended is not None and i == ended:
                break
            intervals.append((effective[i], stop, states[i], (history[i].get('pass'), history[i].get('phase'))))
    else:
        intervals.append((started, end, 'active', (doc.get('pass'), doc.get('phase'))))
    segments = []
    for begin, stop, state, key in intervals:
        seconds = (stop - begin).total_seconds()
        if not segments or segments[-1]['key'] != key:
            segments.append({'key': key, 'started': begin, 'ended': stop, 'active': 0.0, 'paused': 0.0})
        segment = segments[-1]
        segment['ended'] = stop
        segment['paused' if state == 'paused' else 'active'] += seconds
    open_cycle = ended is None
    out = [{'pass': s['key'][0], 'phase': s['key'][1], 'started_at': _iso(s['started']),
            'ended_at': None if open_cycle and s is segments[-1] else _iso(s['ended']),
            'active_seconds': s['active'], 'paused_seconds': s['paused']} for s in segments]
    return {
        'started_at': _iso(started),
        'ended_at': _iso(effective[ended]) if ended is not None else None,
        'elapsed_seconds': (end - started).total_seconds(),
        'paused_seconds': sum(s['paused'] for s in segments),
        'basis': 'derived' if derived else 'recorded',
        'segments': out,
    }
