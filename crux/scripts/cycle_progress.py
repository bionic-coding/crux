"""Read-only, bounded cycle progress projection for terminal and dashboard.

Lightweight records render through cycle_writer and legacy records through cycle_history; no typed-engine
module loads. A legacy record shows what its own bytes and its council files hold: its open attempts with
unknown liveness, its classification count, its council rounds and, once closed, its recorded test runs.
No activity or live test tally is derived for a legacy record. One unreadable record in a listing is shown
as unreadable and the other cycles render."""
from __future__ import annotations
import json
from pathlib import Path
import time
from bionic_config import load_config, require_schema_version
from cycle_store import contained, CycleError
import cycle_history
from cycle_history import ID, clean, current_waits, exception_of, test_run_lines, times  # noqa: F401  (current_waits, exception_of, times: re-exported)
from cycle_history import ASSIGNMENT_STATES, LIVENESS, MAX_ASSIGNMENTS, OBSERVATIONS, classification_count, open_assignments  # noqa: F401  (re-exported)
from datetime import datetime, timezone

# Reader format 5 (format 4 with each cycle's classifications reduced to classification_count, an uncapped integer).
# The dashboards compare these literals against their own copies.
FORMAT_VERSION = 5
# Retained context can grow cycle records beyond the other inputs' 2 MB bound.
MAX_CYCLE_RECORD_BYTES = 4 * 1024 * 1024


def cycle_number(identity):
    """The numeric part of a cycle id, whatever artifact prefix precedes CYC."""
    return int(identity.rsplit('CYC-',1)[1])


MAX_COUNCIL_NAMES=20
MAX_COUNCIL_ROUNDS=20


def councils_of(sio, cfg, doc):
    """The council rounds of each decision, derived from the attempt and record files: attempt id, outcome, reason convened.

    Returns {} when the cycle has no council directory or a file cannot be read; the view survives either."""
    base=cfg.docs_root/'cycles'/doc['id']/'councils'/'decisions'
    prefix=f"idr:{doc['id']}:"
    try:
        if sio.kind(base)!='directory':return {}
        folders=[f for f in sio.glob(base,'*') if sio.kind(f)=='directory']
        by={}
        for folder in folders:
            for path in sio.glob(folder,'attempt-*.json'):
                row=json.loads(sio.read_text(path))
                logical=row.get('logical_id') if isinstance(row,dict) else None
                if isinstance(logical,str) and logical.startswith(prefix):by.setdefault(logical[len(prefix):],[]).append(row)
        def read(rel):return json.loads(sio.read_text(contained(cfg.docs_root,rel)))
        return {clean(name):[{k:(clean(v,300) if isinstance(v,str) else v) for k,v in r.items()}
                             for r in cycle_history.council_rounds(rows,read)[-MAX_COUNCIL_ROUNDS:]]
                for name,rows in list(by.items())[:MAX_COUNCIL_NAMES]}
    except (OSError,ValueError,KeyError,CycleError):
        return {}


def council_lines(name, rounds):
    """One line per council round: `Council <name> round N · <attempt> · <outcome> · <reason>`."""
    return [f"  Council {name} round {r['round']} · {str(r['attempt'])[:8]} · {r['outcome']} · {r['reason']}" for r in rounds]


class Document(dict):
    """The cycle-progress document. It serializes as a plain dict; `queue_lines`, `run_lines`, `council_rounds` and `superseded_tasks` ride along for `render` only.

    `run_lines` maps a cycle id to a function returning its test-run lines. The reader format has no such
    key, so the JSON stays as it was."""
    queue_lines=None
    run_lines=None
    council_rounds={}
    superseded_tasks={}


def read_queue_doc(sio, cfg):
    """The parsed queue document, or None when there is no queue file. Raises on an invalid queue."""
    path=contained(cfg.docs_root,'queue/cycles.yaml')
    kind=sio.kind(path)
    if kind is None:return None
    if kind!='file':raise CycleError('the queue path is not a file')
    import cycle_queue
    doc=cycle_queue.parse_queue(cycle_queue.read_queue_text(sio,path),f'{cfg.docs_dir}/queue/cycles.yaml')
    if doc['format_version']==2:
        for item in doc['items']:
            cycle_queue.resolve_item(cfg,doc,item['id'],source=sio)
            for dep in item['depends_on']:
                cycle_queue.resolve_item(cfg,doc,dep,source=sio)
    return doc


def _queue_error(exc):
    return clean(exc if not isinstance(exc,ImportError) else 'PyYAML is not installed',300)


def queue_view(sio, cfg, statuses):
    """The JSON queue value: None without a queue file, else {ok, items, authorization} or {ok:false, error}."""
    try:
        doc=read_queue_doc(sio,cfg)
        if doc is None:return None
        import cycle_queue
        # Every unstarted item is available to the renderer. Keep the two latest started rows.
        rows=doc['items']
        unstarted=[n for n,i in enumerate(rows) if i['state']!='started']
        started=[n for n,i in enumerate(rows) if i['state']=='started'][-2:]
        keep=sorted(unstarted+started)
        items=[{'id':i['id'],'title':clean(i['title']),'state':i['state'],'suggested_type':clean(i['suggested_type'],40),'cycle':i['cycle'],
                'cycle_status':statuses.get(i['cycle'],'missing') if i['state']=='started' else None} for i in (rows[n] for n in keep)]
        auth=doc['authorization']
        return {'ok':True,'items':items,'authorization':{'kind':auth['kind'],'remaining':cycle_queue.remaining(doc)} if auth else None}
    except (ValueError,OSError,KeyError,ImportError) as exc:
        return {'ok':False,'error':_queue_error(exc)}


def queue_lines(sio, cfg, statuses):
    """Text lines for the queued requests, or None when there is no queue file.

    One error line stands in for an invalid queue or missing PyYAML, so the cycle view survives."""
    try:
        doc=read_queue_doc(sio,cfg)
        if doc is None:return None
        import cycle_queue
    except (ValueError,OSError,KeyError,ImportError) as exc:
        return ['Queued requests unavailable: '+_queue_error(exc)]
    lines=['Queued requests']
    auth=doc['authorization']
    scope=set(auth['scope']) if auth else set()
    resolved=cycle_queue._with_history(cfg,doc,source=sio)
    by={i['id']:i for i in resolved['items']}
    def label(item):return statuses.get(item['cycle'],'missing') if item['state']=='started' else item['state']
    for n,item in enumerate(doc['items'],1):
        row=f"  {n}. {item['id']} {label(item)} {clean(item['title'])}"
        if item['depends_on']:row+=' after '+', '.join(f"{d} ({label(by[d])})" for d in item['depends_on'])
        if item['cycle']:row+=f" → {item['cycle']}"
        if item['id'] in scope:row+=' [authorized]'
        lines.append(row)
    if not doc['items']:lines.append('  none')
    if auth:
        left=cycle_queue.remaining(doc)
        lines.append(f"  Authorization: {auth['kind']}, remaining "+(', '.join(left) if left else 'none'))
    else:lines.append('  Authorization: none')
    return lines


WRITER_FORMATS = ('crux.cycle.vNext', 'crux.cycle.v1')
PILOT_PHASES = ['planning', 'working', 'reviewing', 'reviewed', 'completed']
# The closed sets the dashboards' validator accepts for a pilot row and for a started queue item.
# tools/tests/test_crux_mods_parity.py holds them equal to crux-mods/hooks/lib/view.ts.
PILOT_STATUSES = ['active', 'paused', 'reviewed', 'completed', 'abandoned']
QUEUE_CYCLE_STATUSES = ['active', 'paused', 'reviewed', 'completed', 'abandoned', 'shortcut', 'missing']


def unreadable_pilot(identity, exc, modified_s, fmt=None):
    """A row for a record of either format the reader cannot interpret, in the dashboards' closed vocabulary.

    The title and the blocker say that the record is unreadable and why. `paused` is the status
    that asks for attention; nothing else about the cycle is claimed. The row carries the pilot
    vocabulary because the dashboards accept it for any record whose format is unknown."""
    reason = clean(str(exc) or type(exc).__name__, 300)
    return {'id': identity, 'title': 'Unreadable cycle record', 'type': 'pilot', 'status': 'paused',
            'phase': 'planning', 'pass': 1, 'pass_limit': 1, 'phases': PILOT_PHASES[:], 'tasks': [], 'returns': [], 'waits': [],
            'blocker': clean(f'This record cannot be read: {reason}. The other cycles are shown.', 1000), 'reflection': None,
            'modified_s': modified_s, 'schema_version': fmt if fmt in WRITER_FORMATS else WRITER_FORMATS[0], 'revision': None, 'assignments': [],
            'classification_count': 0, 'exception': None, 'started_s': modified_s, 'ended_s': None, 'paused_s': 0,
            'open_started_s': modified_s, 'basis': 'derived', 'phase_times': []}


def stopped_state(doc):
    """The state an abandoned record stopped in, so the dashboards mark that step.

    The writer records no state on abandonment, so the record's own facts decide, in the order the
    writer leaves them: the state a paused cycle paused from; an open review request (reviewing); an
    approving review no later plan revision or reopening followed (reviewed); any started task
    (working); else planning. A plan revision after tasks started reads working, although the writer
    had returned the cycle to planning."""
    if doc.get('resume_state') in PILOT_PHASES:
        return doc['resume_state']
    if doc.get('review_request'):
        return 'reviewing'
    review = doc.get('review') or {}
    later = [entry.get('at', '') for entry in doc.get('history') or [] if entry.get('kind') in ('plan', 'reopen')]
    if review.get('verdict') == 'approve' and all(at < review.get('at', '') for at in later):
        return 'reviewed'
    return 'working' if any(task.get('run', 0) > 0 for task in doc['tasks']) else 'planning'


def pilot_view(doc, repo, modified_s):
    """Adapt the explicit pilot format without inventing passes or merge completion.

    Pass fields are compatibility placeholders; renderers suppress them for type pilot.
    Timing is creation-to-observation wall time, not inferred active work time.
    """
    if not ID.fullmatch(doc.get('id', '')) or doc.get('state') not in {*PILOT_PHASES, 'paused', 'abandoned'}:
        raise CycleError('invalid pilot cycle')
    if type(doc.get('revision')) is not int or doc['revision'] < 1:
        raise CycleError('invalid pilot revision')
    state = doc['state']
    phase = doc.get('resume_state', 'working') if state == 'paused' else stopped_state(doc) if state == 'abandoned' else state
    if phase not in PILOT_PHASES:
        raise CycleError('invalid pilot phase')
    from cycle_writer import blockers
    blocker = '; '.join(clean(b) for b in blockers(doc))
    # One source for the review, applicability and delivery facts: the writer's own status function.
    from cycle_writer import status_facts
    facts = status_facts(repo, doc)
    status = state if state in {'paused', 'abandoned', 'reviewed', 'completed'} else 'active'
    assert status in PILOT_STATUSES
    if state == 'reviewed' and facts['review_applicable'] is False:
        blocker = '; '.join(filter(None, [blocker, 'Recorded review no longer covers the final change (' + facts['applicability'] + '); independent delta review needed']))
    tasks = []
    for task in doc['tasks'][:500]:
        if task['status'] not in {'pending', 'working', 'blocked', 'done'}:
            raise CycleError('invalid pilot task')
        description = f"{task['description']} [{task['owner']} run {task['run']}]"
        tasks.append({'id': clean(task['id']), 'phase': 'reviewing' if task.get('kind') == 'review' else 'working',
                      'description': clean(description), 'status': 'active' if task['status'] == 'working' else task['status']})
    delivery = doc['delivery']
    if delivery['ci'] not in {'unknown', 'pending', 'passed', 'failed'} or delivery['merge'] not in {'unmerged', 'merged'}:
        raise CycleError('invalid pilot delivery')
    delivery_text = f"Delivery, recorded separately: PR: {delivery.get('pr') or 'none'}; CI: {delivery['ci']}; merge: {delivery['merge']}"
    if delivery.get('published'):
        delivery_text += f"; published: {delivery['published']}"
    if state == 'completed':
        delivery_text = 'Completed. ' + delivery_text
    elif state == 'reviewed':
        delivery_text = ('Reviewed; awaiting finish. ' if facts['review_applicable'] else 'Reviewed; the review no longer covers the final change. ') + delivery_text
    if facts['reopened']:
        delivery_text = f"Reopened {facts['reopened']} time(s). " + delivery_text
    created = _epoch(doc['created_at'])
    ended = _epoch(doc['updated_at']) if state in {'abandoned', 'completed'} else None
    return {'id': doc['id'], 'title': clean(doc['title']), 'type': 'pilot', 'status': status,
            'phase': phase, 'pass': 1, 'pass_limit': 1, 'phases': PILOT_PHASES[:],
            'tasks': tasks, 'returns': [], 'waits': [], 'blocker': clean(blocker, 1000) or None,
            'reflection': clean(delivery_text, 1000), 'modified_s': modified_s,
            'schema_version': doc['format'], 'revision': doc['revision'], 'assignments': [],
            'classification_count': 0, 'exception': None, 'started_s': created, 'ended_s': ended,
            'paused_s': 0, 'open_started_s': None if ended is not None else created,
            'basis': 'derived', 'phase_times': []}


def view(repo, identity=None, now=None):
    """The cycle-progress document.

    The JSON is the dashboards' document, whose objects they accept by exact key set. The reader derives
    no activity for a legacy cycle, because that needs the typed engine's attempt and worktree inspection."""
    from admission_source_io import SourceIO
    sio=SourceIO(Path(repo),max_bytes=2_000_000)
    try:
        return _view(sio,identity,now)
    finally:
        sio.close()


def _view(sio, identity=None, now=None):
    cfg=load_config(sio.root,require_tree=True,_source_io=sio)
    import yaml
    manifest=yaml.safe_load(sio.read_text(cfg.docs_root/'manifest.yml'))
    if manifest.get('schema_version')!='5' or sio.kind(cfg.docs_root/'.migrating') is not None:
        raise CycleError('tree schema requires recovery')
    directory=contained(cfg.docs_root,'cycles')
    if identity and not ID.fullmatch(identity):raise CycleError('invalid cycle identity')
    paths=[contained(directory,f'{identity}/cycle.json')] if identity else [folder/'cycle.json' for folder in sio.glob(directory,'*') if sio.kind(folder)=='directory' and sio.kind(folder/'cycle.json')=='file']
    if len(paths)>200:raise CycleError('too many cycles for dashboard; use an explicit cycle')
    now_s=int(time.time() if now is None else now)
    moment=datetime.fromtimestamp(now_s,timezone.utc)
    cycles=[];rounds={};superseded={}
    docs=[]
    for path in paths:
        contained(cfg.docs_root,path.relative_to(cfg.docs_root))
        text=sio.read_text(path,max_bytes=MAX_CYCLE_RECORD_BYTES)
        modified=int(sio.metadata(path)['st_mtime_ns']//1_000_000_000)
        try:
            doc=json.loads(text)
        except ValueError as exc:
            # Truncated or invalid JSON: an explicit request fails; a listing shows the record as unreadable.
            if identity or not ID.fullmatch(path.parent.name):raise
            cycles.append(unreadable_pilot(path.parent.name, exc, modified))
            continue
        if isinstance(doc,dict) and doc.get('format') in WRITER_FORMATS:
            try:
                if doc.get('id') != path.parent.name:
                    raise CycleError('invalid pilot cycle identity')
                cycles.append(pilot_view(doc, sio.root, modified))
            except (CycleError,KeyError,TypeError,ValueError,AttributeError) as exc:
                # One unreadable pilot record must not blank the dashboard. An explicit request for
                # that record still fails; a listing shows the others and names this one.
                if identity or not ID.fullmatch(path.parent.name):raise
                cycles.append(unreadable_pilot(path.parent.name, exc, modified, doc.get('format') if isinstance(doc, dict) else None))
            continue
        # A legacy record renders through the read-only historical reader.
        try:
            if not cycle_history.is_legacy(doc):raise CycleError('not a cycle record of a known format')
            row,stale=cycle_history.row(doc,path.parent.name,modified,moment)
        except (CycleError,KeyError,TypeError,ValueError,AttributeError,IndexError) as exc:
            # An unknown schema_version or an uninterpretable record: as for a pilot record, a listing names it and continues.
            if identity or not ID.fullmatch(path.parent.name):raise
            cycles.append(unreadable_pilot(path.parent.name, exc, modified))
            continue
        docs.append(doc)
        cycles.append(row)
        # The dashboards accept a closed status set, so a superseded task rides beside the cycle object for `render`.
        if stale:superseded[doc['id']]=stale
        # Council rounds ride beside the cycle objects for `render`, not inside them: the dashboards accept a closed key set.
        rounds[doc['id']]=councils_of(sio,cfg,doc)
    # Active cycles first, then every other cycle; each group by cycle number, highest first.
    cycles.sort(key=lambda c:(c['status']!='active',-cycle_number(c['id'])))
    document=Document({'format':'crux.cycle-progress','format_version':FORMAT_VERSION,'ok':True,'docs_dir':cfg.docs_dir,'now_s':now_s,'cycles':cycles[:60]})
    # The queue rides in the JSON as `queue` (null without a queue file or with an explicit identity)
    # and as text lines for `render`.
    statuses={c['id']:c['status'] for c in cycles}
    document['queue']=None if identity else queue_view(sio,cfg,statuses)
    document.queue_lines=None if identity else queue_lines(sio,cfg,statuses)
    root=sio.root
    def runs_of(d):
        try:return test_run_lines(_runs(root,d,now_s))
        except (ValueError,KeyError,TypeError,OSError):return []
    document.run_lines={d['id']:(lambda d=d:runs_of(d)) for d in docs}
    document.council_rounds=rounds
    document.superseded_tasks=superseded
    return document


def _runs(root, doc, now_s):
    """A closed record's recorded tally from its own bytes. An open legacy record shows none: its live
    tally needs the typed engine's receipt scan."""
    if doc.get('status') in cycle_history.CLOSED:
        return cycle_history.recorded_runs(doc)
    return None


_epoch = cycle_history.epoch


def duration(seconds):
    minutes=max(0,int(seconds))//60
    return f'{minutes}m' if minutes<60 else f'{minutes//60}h{minutes%60:02d}m'


def _assignment_line(a, indent='    '):
    head=f"{indent}Attempt {a['attempt']} · {a['id']}"+(f" · task {a['task']}" if a['task'] else '')+f" · {a['role']} · {a['state']}"
    return head+(', unresolved dispatch' if a['unresolved'] else '')+' · liveness '+a['liveness']


def _task_lines(c, show_attempts):
    """The labelled Tasks section, each open attempt nested under its task; attempts with no listed task follow under Attempts."""
    attempts=c.get('assignments',[]) if show_attempts else []
    def line(a):return _assignment_line(a,'      ')
    ids={t['id'] for t in c['tasks']}
    lines=['  Tasks'] if c['tasks'] else []
    for t in c['tasks']:
        lines.append(f"  {t['status']:7} {t['phase']:7} {t['description']}")
        lines.extend(line(a) for a in attempts if a['task']==t['id'])
    orphans=[a for a in attempts if a['task'] not in ids]
    if orphans:lines.append('  Attempts')
    lines.extend(_assignment_line(a) for a in orphans)
    return lines


def render(document):
    lines=[]
    for c in document['cycles']:
        # A listed release cycle has one phase and no pass limit to show.
        position=f"{c['phase'].title()} · {c['status']}" if c['type']=='pilot' or (c['type']=='release' and c['phases']==['release']) else f"Pass {c['pass']} of {c['pass_limit']} · {c['phase'].title()} · {c['status']}"
        if c.get('revision') is not None:position+=f" · revision {c['revision']}"
        if c['type']=='pilot':
            # A current record has no type and no phase chain; `pilot` is only the dashboards' row vocabulary.
            lines.extend([f"{c['id']} {c['title']}",position])
        else:
            lines.extend([f"{c['id']} {c['title']} [{c['type']}]",position, ' → '.join(p.title() for p in c['phases'])])
        end=c['ended_s'] if c['ended_s'] is not None else document['now_s']
        lines.append(f"  Elapsed {duration(end-c['started_s'])}"+(f" · paused {duration(c['paused_s'])}" if c['paused_s'] else '')+(' (derived)' if c['basis']=='derived' else ''))
        live=c['status'] in ('active','paused')
        runs=(getattr(document,'run_lines',None) or {}).get(c['id'])
        if runs:lines.extend(runs())
        if c['type'] == 'pilot':
            lines.append(f"  Tasks {sum(t['status'] == 'done' for t in c['tasks'])}/{len(c['tasks'])} done")
        lines.extend(_task_lines(c,live))
        lines.extend(f"  superseded {t['phase']:7} {t['description']} (superseded by {t['superseded_by']})" for t in (getattr(document,'superseded_tasks',None) or {}).get(c['id'],[]))
        lines.extend(f"  Return after pass {r['pass']} ({r['phase']}): {r['reason']}" for r in c['returns'])
        if c.get('classification_count'):lines.append(f"  Classifications: {c['classification_count']}")
        councils=getattr(document,'council_rounds',{}).get(c['id'],{})
        if councils:lines.append('  Councils')
        for name,rows in councils.items():lines.extend(council_lines(name,rows))
        if c.get('exception'):lines.append('  Owner exception: '+c['exception'])
        if c['waits']:lines.append('  Awaiting approval: '+', '.join(c['waits']))
        if c['blocker']:lines.append(('  Blocked: ' if c['type']=='pilot' else '  Paused: ')+c['blocker'])
        if c['reflection']:lines.append('  Outcome: '+c['reflection'])
    lines.extend(getattr(document,'queue_lines',None) or [])
    return '\n'.join(lines) or 'No cycles.'
