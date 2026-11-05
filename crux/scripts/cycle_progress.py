"""Read-only, bounded cycle progress projection for terminal and dashboard."""
from __future__ import annotations
import json
from pathlib import Path
import time
from bionic_config import load_config, require_schema_version
from cycle_workflow import PHASES, ID, contained, CycleError, phases_of, withdrawn_names
from cycle_timing import cycle_timing
import cycle_questions
from cycle_summary import recorded_or_live_runs, test_run_lines
import cycle_activity
from datetime import datetime, timezone

# Reader format 5 (format 4 with each cycle's classifications reduced to classification_count, an uncapped integer).
# The dashboards compare these literals against their own copies.
FORMAT_VERSION = 5
ASSIGNMENT_STATES = ['reserved', 'running']
OBSERVATIONS = ['reserved-unbound', 'running-bound']
# The reader has no host status call and reads no result file, so liveness is never more than unknown.
LIVENESS = ['unknown']
MAX_ASSIGNMENTS = 50
MAX_EXCEPTION = 300
# Retained context can grow cycle records beyond the other inputs' 2 MB bound.
MAX_CYCLE_RECORD_BYTES = 4 * 1024 * 1024


def clean(value, limit=200):
    return ''.join(c for c in str(value) if ord(c)>=32 and ord(c)!=127)[:limit]


def cycle_number(identity):
    """The numeric part of a cycle id, whatever artifact prefix precedes CYC."""
    return int(identity.rsplit('CYC-',1)[1])


def current_waits(decisions, withdrawn=()):
    """Names whose latest decision revision still lacks approval, in first-seen order.

    Earlier revisions stay in the record; only the current wait is reported. A withdrawn name
    (`cycle_workflow.withdrawn_names`) waits for nothing, so it is left out."""
    latest={}
    for d in decisions:latest[d['name']]=d
    return [clean(name) for name,d in latest.items() if name not in withdrawn and (not d.get('approval') or (d['kind']=='adr' and not d.get('accepted')))]


def _returns_handle(host, mode=None):
    """Whether a dispatch to this host in the attempt's recorded mode returns a handle.

    A null or unknown host, or a mode the adapter does not list, counts as returning one."""
    import cycle_hosts
    if host is None or cycle_hosts.adapter(host) is None:
        return True
    if mode is not None and mode not in cycle_hosts.ADAPTERS[host].modes:
        return True
    return cycle_hosts.returns_handle(host, mode)


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
                     'unresolved':a['state']=='reserved' and _returns_handle(host,a.get('mode'))})
    return rows[:MAX_ASSIGNMENTS]


def classification_count(doc):
    """How many route classifications the record holds: the rows inspect lists, uncapped.

    The view shows only this count. The question, answer, route, model, provider and cost of each
    classification stay in the record, in inspect and in the finish response."""
    return len(cycle_questions.rows(doc))


MAX_COUNCIL_NAMES=20
MAX_COUNCIL_ROUNDS=20


def councils_of(sio, cfg, doc):
    """The council rounds of each decision, derived from the attempt and record files: attempt id, outcome, reason convened.

    Returns {} when the cycle has no council directory or a file cannot be read; the view survives either."""
    import cycle_council
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
                             for r in cycle_council.council_rounds(rows,read)[-MAX_COUNCIL_ROUNDS:]]
                for name,rows in list(by.items())[:MAX_COUNCIL_NAMES]}
    except (OSError,ValueError,KeyError,CycleError):
        return {}


def council_lines(name, rounds):
    """One line per council round: `Council <name> round N · <attempt> · <outcome> · <reason>`."""
    return [f"  Council {name} round {r['round']} · {str(r['attempt'])[:8]} · {r['outcome']} · {r['reason']}" for r in rounds]


def exception_of(doc):
    done=doc.get('completion')
    text=done.get('exception') if isinstance(done,dict) else None
    return clean(text,MAX_EXCEPTION) if isinstance(text,str) and text else None


class Document(dict):
    """The cycle-progress document. It serializes as a plain dict; `queue_lines`, `run_lines`, `council_rounds` and `activity_of` ride along for `render` only.

    `run_lines` maps a cycle id to a function returning its test-run lines, and `activity_of` to a function
    returning its derived activity. The reader format has neither key, so the JSON stays as it was."""
    queue_lines=None
    run_lines=None
    council_rounds={}
    activity_of={}


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


def view(repo, identity=None, now=None, activity=False):
    """The cycle-progress document.

    The JSON is the dashboards' document, whose objects they accept by exact key set, so it is unchanged
    by default. `activity=True` adds each cycle's derived `activity` (cycle_activity.activity), for a
    caller that asks for it. `render` draws an open cycle's activity either way, deriving it on demand."""
    from admission_source_io import SourceIO
    sio=SourceIO(Path(repo),max_bytes=2_000_000)
    try:
        return _view(sio,identity,now,activity)
    finally:
        sio.close()


def _view(sio, identity=None, now=None, activity=False):
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
    cycles=[];rounds={}
    docs=[]
    for path in paths:
        contained(cfg.docs_root,path.relative_to(cfg.docs_root))
        doc=json.loads(sio.read_text(path,max_bytes=MAX_CYCLE_RECORD_BYTES))
        docs.append(doc)
        if not ID.fullmatch(doc['id']) or doc['id']!=path.parent.name or doc['type'] not in PHASES or doc['phase'] not in phases_of(doc):raise CycleError('invalid cycle')
        if type(doc['pass']) is not int or type(doc['pass_limit']) is not int or not 1<=doc['pass']<=doc['pass_limit']<=1_000_000:raise CycleError('invalid cycle pass')
        if doc['status'] not in {'active','paused','completed','abandoned'}:raise CycleError('invalid cycle status')
        tasks=[]
        for task in doc['plan']['tasks'][:500]:
            if task['status'] not in {'pending','active','done','blocked'} or task['phase'] not in phases_of(doc):raise CycleError('invalid task')
            tasks.append({'id':clean(task['id']),'phase':task['phase'],'description':clean(task['description']),'status':task['status']})
        history=[{'pass':e['pass'],'phase':e['phase'],'reason':clean(e['assessment']['unresolved'])} for e in doc['history'] if e['action']=='return-requested'][-20:]
        waits=current_waits(doc['decisions'],withdrawn_names(doc))
        cycles.append({'id':doc['id'],'title':clean(doc['title']),'type':doc['type'],'status':doc['status'],'phase':doc['phase'],'pass':doc['pass'],'pass_limit':doc['pass_limit'],'phases':phases_of(doc),'tasks':tasks,'returns':history,'waits':waits[:20],'blocker':clean(doc['blocker']['reason']) if doc['blocker'] else None,'reflection':clean(doc['reflection']['outcome']) if doc['reflection'] else None,'modified_s':int(sio.metadata(path)['st_mtime_ns']//1_000_000_000),'schema_version':doc.get('schema_version'),'revision':doc.get('revision') if doc.get('schema_version')==3 else None,'assignments':open_assignments(doc),'classification_count':classification_count(doc),'exception':exception_of(doc),**times(doc,moment)})
        # Council rounds ride beside the cycle objects for `render`, not inside them: the dashboards accept a closed key set.
        rounds[doc['id']]=councils_of(sio,cfg,doc)
        if activity:cycles[-1]['activity']=cycle_activity.activity(sio.root,doc,now_s)
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
        try:return test_run_lines(recorded_or_live_runs(root,d,now_s))
        except (ValueError,KeyError,TypeError,OSError):return []
    document.run_lines={d['id']:(lambda d=d:runs_of(d)) for d in docs}
    document.council_rounds=rounds
    # Text status derives activity on demand, only for the open cycles it draws.
    document.activity_of={d['id']:(lambda d=d:cycle_activity.activity(root,d,now_s)) for d in docs}
    return document


def _epoch(stamp):
    return None if stamp is None else int(datetime.fromisoformat(stamp).timestamp())


def times(doc, moment):
    """Elapsed-time fields, computed from history alone at the reader's now."""
    t=cycle_timing(doc,moment)
    started,ended=_epoch(t['started_at']),_epoch(t['ended_at'])
    open_segment=t['segments'][-1] if ended is None and t['segments'] else None
    per={}
    for s in t['segments']:
        row=per.setdefault(s['phase'],[0.0,0.0]);row[0]+=s['active_seconds'];row[1]+=s['paused_seconds']
    order=phases_of(doc)
    phase_times=[{'phase':p,'active_s':int(per[p][0]),'paused_s':int(per[p][1])} for p in order if p in per]
    return {'started_s':started,'ended_s':ended,'paused_s':min(int(t['paused_seconds']),int(t['elapsed_seconds'])),'open_started_s':_epoch(open_segment['started_at']) if open_segment else None,'basis':t['basis'],'phase_times':phase_times}


def duration(seconds):
    minutes=max(0,int(seconds))//60
    return f'{minutes}m' if minutes<60 else f'{minutes//60}h{minutes%60:02d}m'


def _assignment_line(a, last=None, indent='    '):
    head=f"{indent}Attempt {a['attempt']} · {a['id']}"+(f" · task {a['task']}" if a['task'] else '')+f" · {a['role']} · {a['state']}"
    line=head+(', unresolved dispatch' if a['unresolved'] else '')+' · liveness '+a['liveness']
    return line+(' · last activity '+clean(cycle_activity.describe(last)) if last else '')


def _task_lines(c, show_attempts):
    """The labelled Tasks section, each open attempt nested under its task; attempts with no listed task follow under Attempts."""
    attempts=c.get('assignments',[]) if show_attempts else []
    lasts={(r['id'],r['attempt']):r['last'] for r in (c.get('activity') or {}).get('attempts',[])}
    def line(a):return _assignment_line(a,lasts.get((a['id'],a['attempt'])),'      ')
    ids={t['id'] for t in c['tasks']}
    lines=['  Tasks'] if c['tasks'] else []
    for t in c['tasks']:
        lines.append(f"  {t['status']:7} {t['phase']:7} {t['description']}")
        lines.extend(line(a) for a in attempts if a['task']==t['id'])
    orphans=[a for a in attempts if a['task'] not in ids]
    if orphans:lines.append('  Attempts')
    lines.extend(_assignment_line(a,lasts.get((a['id'],a['attempt']))) for a in orphans)
    return lines


def render(document):
    lines=[]
    for c in document['cycles']:
        # A listed release cycle has one phase and no pass limit to show.
        position=f"{c['phase'].title()} · {c['status']}" if c['type']=='release' and c['phases']==['release'] else f"Pass {c['pass']} of {c['pass_limit']} · {c['phase'].title()} · {c['status']}"
        if c.get('revision') is not None:position+=f" · revision {c['revision']}"
        lines.extend([f"{c['id']} {c['title']} [{c['type']}]",position, ' → '.join(p.title() for p in c['phases'])])
        end=c['ended_s'] if c['ended_s'] is not None else document['now_s']
        lines.append(f"  Elapsed {duration(end-c['started_s'])}"+(f" · paused {duration(c['paused_s'])}" if c['paused_s'] else '')+(' (derived)' if c['basis']=='derived' else ''))
        live=c['status'] in ('active','paused')
        if live and 'activity' not in c:
            derive=(getattr(document,'activity_of',None) or {}).get(c['id'])
            if derive:c={**c,'activity':derive()}
        if live and c.get('activity'):lines.append('  Activity: '+clean(cycle_activity.summary_line(c['activity'])))
        runs=(getattr(document,'run_lines',None) or {}).get(c['id'])
        if runs:lines.extend(runs())
        lines.extend(_task_lines(c,live))
        lines.extend(f"  Return after pass {r['pass']} ({r['phase']}): {r['reason']}" for r in c['returns'])
        if c.get('classification_count'):lines.append(f"  Classifications: {c['classification_count']}")
        councils=getattr(document,'council_rounds',{}).get(c['id'],{})
        if councils:lines.append('  Councils')
        for name,rows in councils.items():lines.extend(council_lines(name,rows))
        if c.get('exception'):lines.append('  Owner exception: '+c['exception'])
        if c['waits']:lines.append('  Awaiting approval: '+', '.join(c['waits']))
        if c['blocker']:lines.append('  Paused: '+c['blocker'])
        if c['reflection']:lines.append('  Outcome: '+c['reflection'])
    lines.extend(getattr(document,'queue_lines',None) or [])
    return '\n'.join(lines) or 'No cycles.'
