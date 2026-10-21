"""A bounded summary of a cycle record for routine `cycle.py show` and `validate` output.

The full record grows with every task and history event. The summary keeps the fields a
coordinator reads between steps and truncates every free-text field, so the output fits one
tool response; `--full` prints the whole record.
"""

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
    return {
        'id': doc['id'], 'type': doc['type'], 'title': clip(doc['title'], TITLE_LIMIT), 'status': doc['status'], 'phase': doc['phase'],
        'pass': doc['pass'], 'pass_limit': doc['pass_limit'], 'plan_revision': doc['plan'].get('revision'),
        'blocker': blocker, 'tasks': tasks, 'required_checks': [clip(c, DESCRIPTION_LIMIT) for c in doc.get('required_checks', [])],
        'evidence_count': sum(1 for e in doc.get('evidence', []) if e.get('pass') == doc['pass']),
        'latest_review': latest, 'decision_count': len(doc.get('decisions', [])),
        'recent_history': [{'action': h.get('action'), 'at': h.get('at')} for h in doc.get('history', [])[-HISTORY_COUNT:]],
    }


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
