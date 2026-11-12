"""A bounded summary of a cycle record for routine `cycle.py show` and `validate` output.

The full record grows with every task and history event. The summary keeps the fields a
coordinator reads between steps and truncates every free-text field, so the output fits one
tool response; `--full` prints the whole record.
"""
import json
import os
import subprocess
from pathlib import Path

import cycle_questions
from cycle_timing import active_window

CLASSIFICATION_COUNT = 20
TITLE_LIMIT = 120
BLOCKER_LIMIT = 200
DESCRIPTION_LIMIT = 100
HISTORY_COUNT = 5
SHORT_COMMIT = 12


def clip(value, limit):
    """Truncate a string to at most `limit` characters, ending in an ellipsis when cut."""
    if not isinstance(value, str):
        return value
    return value if len(value) <= limit else value[:limit - 3] + '...'


def summarize(doc, review_verdict=None):
    """Return the bounded summary of a loaded cycle record.

    A version-3 record adds `schema_version`, `revision` and `attempts` (the reserved and running
    attempt counts); every other record keeps the earlier keys only.

    `review_verdict` optionally maps a record's retained review reference to its report
    (a dict with `verdict`); the record itself holds only references.
    """
    blocker = doc.get('blocker')
    if blocker:
        blocker = {'reason': clip(blocker.get('reason'), BLOCKER_LIMIT), 'next_step': clip(blocker.get('next_step'), BLOCKER_LIMIT)}
    tasks = [{
        'id': t['id'], 'phase': t.get('phase'), 'status': t.get('status'), 'stage': t.get('stage'), 'assignee': t.get('assignee'),
        'commits': [c[:SHORT_COMMIT] for c in t.get('commits', [])],
        'description': clip(t.get('description'), DESCRIPTION_LIMIT),
    } for t in doc['plan']['tasks']]
    latest = None
    if doc.get('reviews'):
        latest = {'count': len(doc['reviews'])}
        if review_verdict:
            try:
                report = review_verdict(doc['reviews'][-1])
                latest.update({'verdict': report.get('verdict'), 'pass': report.get('pass')})
            except Exception:
                latest['verdict'] = None
    summary = {
        'id': doc['id'], 'type': doc['type'], 'title': clip(doc['title'], TITLE_LIMIT), 'status': doc['status'], 'phase': doc['phase'],
        'pass': doc['pass'], 'pass_limit': doc['pass_limit'], 'plan_revision': doc['plan'].get('revision'),
        'blocker': blocker, 'tasks': tasks, 'required_checks': [clip(c, DESCRIPTION_LIMIT) for c in doc.get('required_checks', [])],
        'evidence_count': sum(1 for e in doc.get('evidence', []) if e.get('pass') == doc['pass']),
        'latest_review': latest, 'decision_count': len(doc.get('decisions', [])),
        'recent_history': [{'action': h.get('action'), 'at': h.get('at')} for h in doc.get('history', [])[-HISTORY_COUNT:]],
    }
    if doc.get('schema_version') == 3:
        # Version 1 and 2 summaries keep their keys exactly; a version-3 record adds these four.
        states = [a['state'] for a in doc.get('assignments', [])]
        summary['schema_version'] = 3
        summary['revision'] = doc.get('revision')
        summary['attempts'] = {'reserved': states.count('reserved'), 'running': states.count('running')}
        # The route classifications with their question, answer, provider and cost; the latest last.
        summary['classifications'] = cycle_questions.rows(doc)[-CLASSIFICATION_COUNT:]
    return summary


def render(summary):
    """Print form: top-level keys on their own lines, each task and history row on one line."""
    import json
    rows = []
    for key, value in summary.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            body = ',\n'.join('    ' + json.dumps(v, separators=(', ', ': ')) for v in value)
            rows.append(f'  {json.dumps(key)}: [\n{body}\n  ]')
        else:
            rows.append(f'  {json.dumps(key)}: {json.dumps(value)}')
    return '{\n' + ',\n'.join(rows) + '\n}'


# Receipt reasons that name the lookup state a run started from, not a retry of a failure.
NON_RETRY_REASONS = {'missing', 'inputs-changed', 'expired'}


def _store(repo_root):
    """The durable receipt directory for this checkout, or None. It only reads and creates nothing."""
    override = os.environ.get('CRUX_TEST_EVIDENCE_STORE')
    if override:
        path = Path(override)
    else:
        try:
            found = subprocess.run(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'], cwd=repo_root, capture_output=True, text=True)
        except OSError:
            return None
        if found.returncode:
            return None
        path = Path(found.stdout.strip()) / 'crux' / 'test-evidence'
    return path if path.is_dir() else None


def _receipts(store, since=None, ids=()):
    """({id: receipt fields}, unreadable count). A file that cannot be read is counted, never dropped silently.

    With `since`, only a receipt written at or after `since` (by file modification time), or one named in
    `ids`, is parsed. A receipt is written after its run starts, so every receipt whose run started at or
    after `since` is still read; the rest are skipped without parsing."""
    found, unreadable = {}, 0
    wanted = {f'{i}.json' for i in ids if isinstance(i, str)}
    for path in sorted(store.glob('TE-*.json')):
        if since is not None and path.name not in wanted:
            try:
                if path.stat().st_mtime < since:
                    continue
            except OSError:
                pass
        try:
            record = json.loads(path.read_text())
            found[record['id']] = {'id': record['id'], 'check_id': record['declaration']['check_id'], 'started_at': float(record['started_at']),
                                   'seconds': float(record['seconds']), 'status': record['status'], 'reason': record.get('reason')}
        except (OSError, ValueError, KeyError, TypeError):
            unreadable += 1
    return found, unreadable


def is_retry(receipt):
    """Whether the run started with a retry reason. An interrupted run stores its interruption in that field, so it counts as none."""
    return receipt['status'] != 'interrupted' and isinstance(receipt['reason'], str) and receipt['reason'] not in NON_RETRY_REASONS


def test_runs(repo_root, doc, now):
    """The cycle's test runs from the durable receipt store, or None when the checkout has no store.

    Executed: receipts whose run started inside the cycle's window (creation to its close, or to `now`
    while it is open), each once, passed, failed and interrupted alike. Reused: receipts the record
    attaches that started outside the window; they add no minutes. `minutes` is the sum of the executed
    receipts' wall seconds. `executions` is the total; `with_retry_reason` is the subtotal of runs started
    with --retry-reason. A run killed before it wrote a receipt is not counted. Only receipts written
    inside the window or attached by the record are parsed, and `unreadable` counts among those."""
    store = _store(repo_root)
    if store is None:
        return None
    begin, end = active_window(doc, now)
    receipts, unreadable = _receipts(store, begin, [ref.get('evidence_id') for ref in doc.get('evidence', [])])
    executed = sorted((r for r in receipts.values() if begin <= r['started_at'] <= end), key=lambda r: (r['started_at'], r['id']))
    inside = {r['id'] for r in executed}
    by_check = {}
    for r in executed:
        row = by_check.setdefault(r['check_id'], {'receipts': [], 'with_retry_reason': 0, 'seconds': 0.0})
        row['receipts'].append(r['id'])
        row['with_retry_reason'] += is_retry(r)
        row['seconds'] += r['seconds']
    reused = {}
    for ref in doc.get('evidence', []):
        eid = ref.get('evidence_id')
        if eid in receipts and eid not in inside and eid not in reused.setdefault(ref['check_id'], []):
            reused[ref['check_id']].append(eid)
    return {'executions': len(executed), 'with_retry_reason': sum(is_retry(r) for r in executed),
            'minutes': round(sum(r['seconds'] for r in executed) / 60, 1),
            'executed': [{'check_id': check, 'runs': len(row['receipts']), 'receipts': row['receipts'],
                          'with_retry_reason': row['with_retry_reason'], 'minutes': round(row['seconds'] / 60, 1)}
                         for check, row in sorted(by_check.items())],
            'reused': [{'check_id': check, 'receipts': ids} for check, ids in sorted(reused.items()) if ids],
            'unreadable': unreadable}


def recorded_or_live_runs(repo_root, doc, now):
    """What inspect and `cycle status` show: a closed cycle's recorded `test_runs`, else the live tally of an open one."""
    if doc.get('status') in ('completed', 'abandoned', 'shortcut'):
        done = doc.get('completion')
        return done.get('test_runs') if isinstance(done, dict) else None
    return test_runs(repo_root, doc, now)


def test_run_lines(runs):
    """Text lines for a `test_runs` value, shared by inspect and `cycle status`. Empty without one."""
    if not runs:
        return []
    lines = [f"  Test runs: {runs['executions']} executed ({runs['with_retry_reason']} with a retry reason), "
             f"{sum(len(row['receipts']) for row in runs['reused'])} reused, {runs['minutes']} test minutes"]
    lines += [f"    executed {row['check_id']}: {row['runs']} run(s), {row['minutes']} min, receipts {', '.join(row['receipts'])}" for row in runs['executed']]
    lines += [f"    reused {row['check_id']}: {', '.join(row['receipts'])}" for row in runs['reused']]
    if runs['unreadable']:
        lines.append(f"    {runs['unreadable']} receipt(s) unreadable and not counted")
    return lines
