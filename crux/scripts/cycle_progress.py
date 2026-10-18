"""Read-only, bounded cycle progress projection for terminal and dashboard."""
from __future__ import annotations
import json
from pathlib import Path
import time
from bionic_config import load_config, require_schema_version
from cycle_workflow import PHASES, ID, contained, CycleError


def clean(value, limit=200):
    return ''.join(c for c in str(value) if ord(c)>=32 and ord(c)!=127)[:limit]


def view(repo, identity=None):
    from admission_source_io import SourceIO
    sio=SourceIO(Path(repo),max_bytes=2_000_000)
    try:
        return _view(sio,identity)
    finally:
        sio.close()


def _view(sio, identity=None):
    cfg=load_config(sio.root,require_tree=True,_source_io=sio)
    import yaml
    manifest=yaml.safe_load(sio.read_text(cfg.docs_root/'manifest.yml'))
    if manifest.get('schema_version')!='5' or sio.kind(cfg.docs_root/'.migrating') is not None:
        raise CycleError('tree schema requires recovery')
    directory=contained(cfg.docs_root,'cycles')
    if identity and not ID.fullmatch(identity):raise CycleError('invalid cycle identity')
    paths=[contained(directory,f'{identity}/cycle.json')] if identity else [folder/'cycle.json' for folder in sio.glob(directory,'*') if sio.kind(folder)=='directory' and sio.kind(folder/'cycle.json')=='file']
    if len(paths)>200:raise CycleError('too many cycles for dashboard; use an explicit cycle')
    cycles=[]
    for path in paths:
        contained(cfg.docs_root,path.relative_to(cfg.docs_root))
        doc=json.loads(sio.read_text(path))
        if not ID.fullmatch(doc['id']) or doc['id']!=path.parent.name or doc['type'] not in PHASES or doc['phase'] not in PHASES[doc['type']]:raise CycleError('invalid cycle')
        if type(doc['pass']) is not int or type(doc['pass_limit']) is not int or not 1<=doc['pass']<=doc['pass_limit']<=1_000_000:raise CycleError('invalid cycle pass')
        if doc['status'] not in {'active','paused','completed','abandoned'}:raise CycleError('invalid cycle status')
        tasks=[]
        for task in doc['plan']['tasks'][:500]:
            if task['status'] not in {'pending','active','done','blocked'} or task['phase'] not in PHASES[doc['type']]:raise CycleError('invalid task')
            tasks.append({'id':clean(task['id']),'phase':task['phase'],'description':clean(task['description']),'status':task['status']})
        history=[{'pass':e['pass'],'phase':e['phase'],'reason':clean(e['assessment']['unresolved'])} for e in doc['history'] if e['action']=='return-requested'][-20:]
        waits=[clean(d['name']) for d in doc['decisions'] if not d.get('approval') or (d['kind']=='adr' and not d.get('accepted'))]
        cycles.append({'id':doc['id'],'title':clean(doc['title']),'type':doc['type'],'status':doc['status'],'phase':doc['phase'],'pass':doc['pass'],'pass_limit':doc['pass_limit'],'phases':PHASES[doc['type']],'tasks':tasks,'returns':history,'waits':waits[:20],'blocker':clean(doc['blocker']['reason']) if doc['blocker'] else None,'reflection':clean(doc['reflection']['outcome']) if doc['reflection'] else None,'modified_s':int(sio.metadata(path)['st_mtime_ns']//1_000_000_000)})
    cycles.sort(key=lambda c:c['modified_s'],reverse=True)
    # Show active work before recent closed work; keep both discoverable.
    cycles.sort(key=lambda c:c['status'] in {'completed','abandoned'})
    return {'format':'crux.cycle-progress','format_version':1,'ok':True,'docs_dir':cfg.docs_dir,'now_s':int(time.time()),'cycles':cycles[:20]}


def render(document):
    lines=[]
    for c in document['cycles']:
        lines.extend([f"{c['id']} {c['title']} [{c['type']}]",f"Pass {c['pass']} of {c['pass_limit']} · {c['phase'].title()} · {c['status']}", ' → '.join(p.title() for p in c['phases'])])
        lines.extend(f"  {t['status']:7} {t['phase']:7} {t['description']}" for t in c['tasks'])
        lines.extend(f"  Return after pass {r['pass']} ({r['phase']}): {r['reason']}" for r in c['returns'])
        if c['waits']:lines.append('  Awaiting approval: '+', '.join(c['waits']))
        if c['blocker']:lines.append('  Paused: '+c['blocker'])
        if c['reflection']:lines.append('  Outcome: '+c['reflection'])
    return '\n'.join(lines) or 'No cycles.'
