"""Read-only display of legacy cycle records: schema_version 1 to 3, written by the typed engine.

It reads a record and returns bounded display facts: the dashboards' row (`row`), the queue's status
(`status_of`) and a summary of the record (`facts`), release cycles of every list included. It never
resumes, writes or validates a record against the mutation schemas, and it imports no typed-engine
module, so a historical record renders after that engine is gone. The tables below are frozen copies of
the typed engine's (phases, host dispatch modes, classification kinds), because a historical record's
vocabulary no longer changes. A record whose schema_version is not 1, 2 or 3 is refused as unreadable.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import re

from cycle_store import CycleError, contained, tree

ID = re.compile(r'^(?:[A-Z][A-Z0-9]{1,9}-)?CYC-[0-9]{4,}$')
SCHEMA_VERSIONS = (1, 2, 3)
PHASES = {
    'dev': ['plan', 'build', 'test', 'review', 'reflect'],
    'iterate': ['plan', 'build', 'test', 'review', 'reflect'],
    'refactor': ['plan', 'build', 'test', 'review', 'reflect'],
    'simplify': ['plan', 'build', 'test', 'review', 'reflect'],
    'quick-fix': ['build', 'test', 'review', 'reflect'],
    'release': ['release'],
}
# A release record without release_list predates the fixed lists.
LEGACY_RELEASE = {'phases': ['plan', 'release', 'reflect'], 'limit': 2}
# The phase after Build is 'test' on a record without phase_names and 'verify' on a record that carries it.
CHECK_PHASES = ('test', 'verify')
CLOSED = {'completed', 'abandoned', 'shortcut'}
STATUSES = {'active', 'paused', *CLOSED}
TASK_STATUSES = {'pending', 'active', 'done', 'blocked', 'superseded'}


def is_legacy(doc):
    """A typed-engine record: a JSON object with no `format` field. Lightweight records carry one."""
    return isinstance(doc, dict) and 'format' not in doc


def load(text):
    """Parse one legacy record's text; refuse anything that is not a legacy record of a known schema version."""
    doc = json.loads(text)
    if not is_legacy(doc):
        raise CycleError('not a legacy cycle record')
    if doc.get('schema_version') not in SCHEMA_VERSIONS:
        raise CycleError(f"unknown legacy schema_version {clean(repr(doc.get('schema_version')), 40)}")
    return doc


def load_record(repo, identity):
    """Read the legacy record of `identity` from the repository's tree: a regular file, parsed and checked."""
    if not isinstance(identity, str) or not ID.fullmatch(identity):
        raise CycleError('invalid cycle identity')
    path = contained(tree(repo).docs_root, f'cycles/{identity}/cycle.json')
    if path.is_symlink() or not path.is_file():
        raise CycleError('the cycle record is missing or not a regular file')
    try:
        doc = load(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise CycleError(f'cannot read {identity}: {exc}') from exc
    check(doc, identity)
    return doc


def check(doc, folder=None):
    """Refuse a legacy record whose display fields a reader cannot interpret; return it unchanged.

    This is the reader's bound, not the typed engine's schema: identity, type, phase, pass, status and
    the schema version. `folder` is the record's directory name, which must equal its id."""
    if doc.get('schema_version') not in SCHEMA_VERSIONS:raise CycleError('unknown legacy schema_version')
    if not isinstance(doc.get('id'),str) or not ID.fullmatch(doc['id']) or (folder is not None and doc['id']!=folder):raise CycleError('invalid cycle identity')
    if doc.get('type') not in PHASES or doc.get('phase') not in phases_of(doc):raise CycleError('invalid cycle')
    if type(doc.get('pass')) is not int or type(doc.get('pass_limit')) is not int or not 1<=doc['pass']<=doc['pass_limit']<=1_000_000:raise CycleError('invalid cycle pass')
    if doc.get('status') not in STATUSES:raise CycleError('invalid cycle status')
    return doc


def status_of(doc):
    """The status a queue reader shows for a parsed legacy record, after `check`."""
    if not is_legacy(doc):
        raise CycleError('not a legacy cycle record')
    return check(doc)['status']


def phases_of(doc):
    """The type's phase sequence in the record's own vocabulary; phase_names does not apply to a release record."""
    if doc['type'] == 'release' and not doc.get('release_list'):
        return LEGACY_RELEASE['phases']
    sequence = PHASES[doc['type']]
    if doc['type'] != 'release' and doc.get('phase_names') == 'verify':
        return [CHECK_PHASES[1] if name == CHECK_PHASES[0] else name for name in sequence]
    return sequence


def withdrawn_names(doc):
    """The IDR names this cycle withdrew."""
    return {w['name'] for w in doc.get('withdrawals', [])}


def clean(value, limit=200):
    return ''.join(c for c in str(value) if ord(c)>=32 and ord(c)!=127)[:limit]


def current_waits(decisions, withdrawn=()):
    """Names whose latest decision revision still lacks approval, in first-seen order.

    Earlier revisions stay in the record; only the current wait is reported. A withdrawn name
    (`withdrawn_names`) waits for nothing, so it is left out."""
    latest={}
    for d in decisions:latest[d['name']]=d
    return [clean(name) for name,d in latest.items() if name not in withdrawn and (not d.get('approval') or (d['kind']=='adr' and not d.get('accepted')))]


MAX_EXCEPTION = 300


def exception_of(doc):
    done=doc.get('completion')
    text=done.get('exception') if isinstance(done,dict) else None
    return clean(text,MAX_EXCEPTION) if isinstance(text,str) and text else None


def recorded_runs(doc):
    """A closed cycle's recorded `test_runs`, or None. An open cycle's live tally is not history."""
    done = doc.get('completion')
    return done.get('test_runs') if isinstance(done, dict) else None


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


# Elapsed and paused time of a cycle, computed from its history alone; the rules are in cycle_timing.py's docstring.
KNOWN = {'active', 'paused'} | CLOSED
_SELF = {'pause': 'paused', 'resume': 'active', 'owner-complete': 'completed', 'abandon': 'abandoned', 'shortcut': 'shortcut'}


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


def epoch(stamp):
    return None if stamp is None else int(datetime.fromisoformat(stamp).timestamp())


def times(doc, moment):
    """Elapsed-time fields, computed from history alone at the reader's now."""
    t=cycle_timing(doc,moment)
    started,ended=epoch(t['started_at']),epoch(t['ended_at'])
    open_segment=t['segments'][-1] if ended is None and t['segments'] else None
    per={}
    for s in t['segments']:
        row=per.setdefault(s['phase'],[0.0,0.0]);row[0]+=s['active_seconds'];row[1]+=s['paused_seconds']
    order=phases_of(doc)
    phase_times=[{'phase':p,'active_s':int(per[p][0]),'paused_s':int(per[p][1])} for p in order if p in per]
    return {'started_s':started,'ended_s':ended,'paused_s':min(int(t['paused_seconds']),int(t['elapsed_seconds'])),'open_started_s':epoch(open_segment['started_at']) if open_segment else None,'basis':t['basis'],'phase_times':phase_times}


# -- open attempts ----------------------------------------------------------------------------------
# Reader format constants the dashboards compare against their own copies.
ASSIGNMENT_STATES = ['reserved', 'running']
OBSERVATIONS = ['reserved-unbound', 'running-bound']
# The reader has no host status call and reads no result file, so liveness is never more than unknown.
LIVENESS = ['unknown']
MAX_ASSIGNMENTS = 50
# Frozen from the typed engine's host adapters: each host's default dispatch mode, its modes, and the
# modes whose dispatch returns a handle. A reservation in a handle mode that never bound one is an
# unresolved dispatch.
HOST_MODES = {
    'claude-code': ('blocking', ('background', 'blocking'), frozenset({'background'})),
    'codex': ('spawn', ('spawn',), frozenset({'spawn'})),
    'opencode': ('foreground', ('background', 'foreground'), frozenset({'background'})),
    'omp': ('blocking', ('background', 'blocking'), frozenset({'background'})),
}


def returns_handle(host, mode=None):
    """Whether a dispatch to `host` in `mode` returns a handle. A null or unknown host, or a mode the
    host does not list, counts as returning one."""
    if host not in HOST_MODES:
        return True
    default, modes, handles = HOST_MODES[host]
    if mode is not None and mode not in modes:
        return True
    return (mode or default) in handles


def edits_main_checkout(entry):
    """Whether a recorded attempt edits the main checkout. Frozen from the typed engine's isolation rule: only a
    developer on claude-code works in a worktree; every other role and host, and an unknown or null host, edits the main checkout."""
    return not (entry.get('host') == 'claude-code' and entry.get('role') == 'developer')


def _text_or_none(value, limit=200):
    return clean(value, limit) if isinstance(value, str) else None


def open_assignments(doc):
    """The record's open attempts (reserved or running) in record order. Liveness stays unknown."""
    rows=[]
    for a in doc.get('assignments',[]):
        if a['state'] not in ASSIGNMENT_STATES:continue
        host=a.get('host')
        rows.append({'id':clean(a['id']),'task':_text_or_none(a.get('task')),'role':clean(a['role']),'host':_text_or_none(host),'attempt':a['attempt'],
                     'state':a['state'],'observation':OBSERVATIONS[ASSIGNMENT_STATES.index(a['state'])],'liveness':LIVENESS[0],
                     'unresolved':a['state']=='reserved' and returns_handle(host,a.get('mode'))})
    return rows[:MAX_ASSIGNMENTS]


# -- classifications and council rounds -------------------------------------------------------------
# Frozen from the typed engine's question sets: the classification kinds a record's rows count.
QUESTION_KINDS = frozenset({'context-selection', 'failure-routing', 'finding-disposition', 'focused-test-ranking',
                            'handoff-completeness', 'public-document-relevance', 'review-finding-grouping',
                            'review-routing', 'work-sizing'})


def classification_count(doc):
    """How many route classifications the record holds: every entry that is an object of a known kind, uncapped.

    The view shows only this count; the question, answer, route, model, provider and cost stay in the record."""
    entries = doc.get('classifications')
    if not isinstance(entries, list):
        return 0
    return sum(isinstance(e, dict) and e.get('kind') in QUESTION_KINDS for e in entries)


def council_rounds(rows, read_record):
    """Each council round of a decision: attempt id, outcome and the reason it was convened.

    `rows` are attempt records; `read_record(docs_relative_path)` returns a council record. The reason is the
    attempt's own progress text, `initial` when it recorded none, and `delta revision` when a delta was reviewed.
    'architect-settled' is an outcome: the architect agreement resolved a dissent the seats left."""
    out=[]
    for row in sorted(rows,key=lambda r:(r.get('started_at',''),r.get('id',''))):
        progress=row.get('progress') if isinstance(row.get('progress'),str) and row['progress'].strip() else None
        reason='delta revision'+(f': {progress}' if progress else '') if row.get('delta') else progress or 'initial'
        outcome=row.get('status','running')
        if row.get('record'):
            try:record=read_record(row['record'])
            except (OSError,ValueError,CycleError):record=None
            if isinstance(record,dict):
                outcome=record.get('outcome',outcome)
                seats=record.get('seats') or []
                dissent=any(s.get('decision') not in ('APPROVE','APPROVE_WITH_NITS') or any(f.get('kind')!='nit' for f in s.get('findings',[])) for s in seats)
                if outcome=='approved' and dissent and (record.get('architect') or {}).get('agrees') is True:outcome='architect-settled'
        out.append({'attempt':row.get('id'),'round':row.get('round'),'outcome':outcome,'reason':reason})
    return out


# -- summary facts ------------------------------------------------------------------------------------
MAX_FACT_ITEMS = 50


def facts(doc, read_record=None):
    """Bounded display facts of one checked legacy record: identity, type, status, phase, pass and limit,
    task counts, the latest review verdict, completion, recorded test evidence, the tasks' evidence paths
    and, for a release cycle, its list, destinations, verification and retained ledger path. `read_record(docs_relative_path)` reads the latest review report; without it, or when the
    report cannot be read, the verdict is None and the report path is still given."""
    check(doc)
    counts = {}
    for task in doc['plan']['tasks']:
        counts[task['status']] = counts.get(task['status'], 0) + 1
    reviews = [r for r in doc.get('reviews') or [] if isinstance(r, dict) and isinstance(r.get('path'), str)]
    review = None
    if reviews:
        verdict = None
        if read_record is not None:
            try:
                report = read_record(reviews[-1]['path'])
                verdict = clean(report.get('verdict'), 40) if isinstance(report, dict) and isinstance(report.get('verdict'), str) else None
            except (OSError, ValueError, CycleError):
                verdict = None
        review = {'path': clean(reviews[-1]['path'], 300), 'verdict': verdict, 'count': len(reviews)}
    done = doc.get('completion')
    completion = None
    if isinstance(done, dict):
        commits = done.get('commits') if isinstance(done.get('commits'), list) else []
        completion = {'commits': [clean(c, 64) for c in commits[:MAX_FACT_ITEMS]], 'exception': exception_of(doc),
                      'remaining': _text_or_none(done.get('remaining'), 300)}
    evidence = [{'check_id': clean(e.get('check_id'), 200), 'evidence_id': clean(e.get('evidence_id'), 80), 'pass': e.get('pass'), 'use': _text_or_none(e.get('use'), 40)}
                for e in (doc.get('evidence') or [])[:MAX_FACT_ITEMS] if isinstance(e, dict)]
    paths = []
    for task in doc['plan']['tasks']:
        for path in task.get('evidence') or []:
            if isinstance(path, str) and clean(path, 300) not in paths:
                paths.append(clean(path, 300))
    release = None
    if doc['type'] == 'release':
        held = doc.get('release') if isinstance(doc.get('release'), dict) else {}
        ledger = held.get('ledger') if isinstance(held.get('ledger'), dict) else {}
        release = {'list': doc.get('release_list'), 'destinations': [clean(d, 200) for d in (held.get('destinations') or [])[:MAX_FACT_ITEMS]],
                   'verification': _text_or_none(held.get('verification'), 300), 'retained': _text_or_none(ledger.get('retained'), 300)}
    return {'id': doc['id'], 'title': clean(doc['title']), 'type': doc['type'], 'schema_version': doc['schema_version'],
            'status': doc['status'], 'phase': doc['phase'], 'phases': phases_of(doc), 'pass': doc['pass'], 'pass_limit': doc['pass_limit'],
            'tasks': counts, 'review': review, 'completion': completion, 'evidence': evidence, 'evidence_paths': paths[:MAX_FACT_ITEMS], 'release': release,
            'reflection': clean(doc['reflection']['outcome'], 300) if isinstance(doc.get('reflection'), dict) and doc['reflection'].get('outcome') else None}


def row(doc, folder, modified_s, moment):
    """The dashboards' cycle object for one legacy record, and its superseded tasks for the text view.

    `folder` is the record's directory name."""
    check(doc, folder)
    tasks=[];superseded=[]
    for task in doc['plan']['tasks'][:500]:
        if task['status'] not in TASK_STATUSES or task['phase'] not in phases_of(doc):raise CycleError('invalid task')
        if task['status']=='superseded':
            # The dashboards accept a closed status set, so a superseded task rides beside the cycle object for the text view.
            superseded.append({'id':clean(task['id']),'phase':task['phase'],'description':clean(task['description']),'superseded_by':clean(str(task.get('superseded_by')))})
            continue
        tasks.append({'id':clean(task['id']),'phase':task['phase'],'description':clean(task['description']),'status':task['status']})
    history=[{'pass':e['pass'],'phase':e['phase'],'reason':clean(e['assessment']['unresolved'])} for e in doc['history'] if e['action']=='return-requested'][-20:]
    waits=current_waits(doc['decisions'],withdrawn_names(doc))
    cycle={'id':doc['id'],'title':clean(doc['title']),'type':doc['type'],'status':doc['status'],'phase':doc['phase'],'pass':doc['pass'],'pass_limit':doc['pass_limit'],'phases':phases_of(doc),'tasks':tasks,'returns':history,'waits':waits[:20],'blocker':clean(doc['blocker']['reason']) if doc['blocker'] else None,'reflection':clean(doc['reflection']['outcome']) if doc['reflection'] else None,'modified_s':modified_s,'schema_version':doc.get('schema_version'),'revision':doc.get('revision') if doc.get('schema_version')==3 else None,'assignments':open_assignments(doc),'classification_count':classification_count(doc),'exception':exception_of(doc),**times(doc,moment)}
    return cycle, superseded
