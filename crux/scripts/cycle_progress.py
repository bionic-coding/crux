"""Read-only, bounded cycle progress projection for terminal and dashboard."""
from __future__ import annotations
import json
from pathlib import Path
import time
from bionic_config import load_config, require_schema_version
from cycle_workflow import PHASES, ID, contained, CycleError, phases_of
from cycle_timing import cycle_timing
from datetime import datetime, timezone


def clean(value, limit=200):
    return ''.join(c for c in str(value) if ord(c)>=32 and ord(c)!=127)[:limit]


def cycle_number(identity):
    """The numeric part of a cycle id, whatever artifact prefix precedes CYC."""
    return int(identity.rsplit('CYC-',1)[1])


def current_waits(decisions):
    """Names whose latest decision revision still lacks approval, in first-seen order.

    Earlier revisions stay in the record; only the current wait is reported."""
    latest={}
    for d in decisions:latest[d['name']]=d
    return [clean(name) for name,d in latest.items() if not d.get('approval') or (d['kind']=='adr' and not d.get('accepted'))]


class Document(dict):
    """The cycle-progress document. It serializes as a plain dict; `queue_lines` rides along for `render` only."""
    queue_lines=None


def queue_lines(sio, cfg, statuses):
    """Text lines for the queued requests, or None when there is no queue file.

    One error line stands in for an invalid queue or missing PyYAML, so the cycle view survives."""
    try:
        path=contained(cfg.docs_root,'queue/cycles.yaml')
        kind=sio.kind(path)
        if kind is None:return None
        if kind!='file':raise CycleError('the queue path is not a file')
        import cycle_queue
        doc=cycle_queue.parse_queue(sio.read_text(path),f'{cfg.docs_dir}/queue/cycles.yaml')
    except (ValueError,OSError,KeyError,ImportError) as exc:
        return ['Queued requests unavailable: '+clean(exc if not isinstance(exc,ImportError) else 'PyYAML is not installed',300)]
    lines=['Queued requests']
    auth=doc['authorization']
    scope=set(auth['scope']) if auth else set()
    by={i['id']:i for i in doc['items']}
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


def view(repo, identity=None, now=None):
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
    cycles=[]
    for path in paths:
        contained(cfg.docs_root,path.relative_to(cfg.docs_root))
        doc=json.loads(sio.read_text(path))
        if not ID.fullmatch(doc['id']) or doc['id']!=path.parent.name or doc['type'] not in PHASES or doc['phase'] not in phases_of(doc):raise CycleError('invalid cycle')
        if type(doc['pass']) is not int or type(doc['pass_limit']) is not int or not 1<=doc['pass']<=doc['pass_limit']<=1_000_000:raise CycleError('invalid cycle pass')
        if doc['status'] not in {'active','paused','completed','abandoned'}:raise CycleError('invalid cycle status')
        tasks=[]
        for task in doc['plan']['tasks'][:500]:
            if task['status'] not in {'pending','active','done','blocked'} or task['phase'] not in phases_of(doc):raise CycleError('invalid task')
            tasks.append({'id':clean(task['id']),'phase':task['phase'],'description':clean(task['description']),'status':task['status']})
        history=[{'pass':e['pass'],'phase':e['phase'],'reason':clean(e['assessment']['unresolved'])} for e in doc['history'] if e['action']=='return-requested'][-20:]
        waits=current_waits(doc['decisions'])
        cycles.append({'id':doc['id'],'title':clean(doc['title']),'type':doc['type'],'status':doc['status'],'phase':doc['phase'],'pass':doc['pass'],'pass_limit':doc['pass_limit'],'phases':phases_of(doc),'tasks':tasks,'returns':history,'waits':waits[:20],'blocker':clean(doc['blocker']['reason']) if doc['blocker'] else None,'reflection':clean(doc['reflection']['outcome']) if doc['reflection'] else None,'modified_s':int(sio.metadata(path)['st_mtime_ns']//1_000_000_000),**times(doc,moment)})
    # Active cycles first, then every other cycle; each group by cycle number, highest first.
    cycles.sort(key=lambda c:(c['status']!='active',-cycle_number(c['id'])))
    document=Document({'format':'crux.cycle-progress','format_version':2,'ok':True,'docs_dir':cfg.docs_dir,'now_s':now_s,'cycles':cycles[:20]})
    # Text-only: the queue never enters the JSON document, whose key set a dashboard parses exactly.
    document.queue_lines=None if identity else queue_lines(sio,cfg,{c['id']:c['status'] for c in cycles})
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


def render(document):
    lines=[]
    for c in document['cycles']:
        # A listed release cycle has one phase and no pass limit to show.
        position=f"{c['phase'].title()} · {c['status']}" if c['type']=='release' and c['phases']==['release'] else f"Pass {c['pass']} of {c['pass_limit']} · {c['phase'].title()} · {c['status']}"
        lines.extend([f"{c['id']} {c['title']} [{c['type']}]",position, ' → '.join(p.title() for p in c['phases'])])
        end=c['ended_s'] if c['ended_s'] is not None else document['now_s']
        lines.append(f"  Elapsed {duration(end-c['started_s'])}"+(f" · paused {duration(c['paused_s'])}" if c['paused_s'] else '')+(' (derived)' if c['basis']=='derived' else ''))
        lines.extend(f"  {t['status']:7} {t['phase']:7} {t['description']}" for t in c['tasks'])
        lines.extend(f"  Return after pass {r['pass']} ({r['phase']}): {r['reason']}" for r in c['returns'])
        if c['waits']:lines.append('  Awaiting approval: '+', '.join(c['waits']))
        if c['blocker']:lines.append('  Paused: '+c['blocker'])
        if c['reflection']:lines.append('  Outcome: '+c['reflection'])
    lines.extend(getattr(document,'queue_lines',None) or [])
    return '\n'.join(lines) or 'No cycles.'
