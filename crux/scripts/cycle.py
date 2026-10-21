#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Create, execute and inspect a cycle; no reusable book or prompt minimum."""
import argparse
import json
from pathlib import Path
import sys
import threading
import time
from cycle_workflow import CycleError, PHASES, DELIVERY_FIELDS, create, load, mutate_tracked, tree, read_retained, query_decisions, result_file
from bionic_config import BionicConfigError


def queue_parser(sub):
    """The `queue` group: every input is a flag, so one shell form reaches every operation."""
    q=sub.add_parser('queue',help='the persistent cycle queue',description='Capture and order work once, then start authorized items as cycles one at a time. Exit 0 succeeded, 1 refused or stopped, 2 environment.')
    ops=q.add_subparsers(dest='queue_op',required=True)
    def op(name,item=False,**kw):
        o=ops.add_parser(name,**kw)
        o.add_argument('--compact',action='store_true',default=argparse.SUPPRESS,help=argparse.SUPPRESS)
        if item: o.add_argument('item',help='queue item id, such as Q-0001')
        return o
    o=op('add')
    o.add_argument('--title',required=True);o.add_argument('--outcome',required=True);o.add_argument('--type',dest='item_type',required=True,help='suggested cycle type; checked when the item starts')
    o.add_argument('--scope',action='append',required=True);o.add_argument('--acceptance',action='append',required=True)
    o.add_argument('--depends-on',dest='depends_on',action='append',help='item id that must complete first; repeatable')
    o.add_argument('--position',type=int,help='1-based position in the full list; default is the end')
    o.add_argument('--reference',dest='references',action='append',help='repository path to a supporting document, such as a brief; repeatable')
    o.add_argument('--held',action='store_true');o.add_argument('--reason',help='why the item is held; required with --held')
    op('list',help='every item with derived cycle status, the authorization and what start-next would do')
    op('show',item=True)
    o=op('edit',item=True)
    o.add_argument('--title');o.add_argument('--outcome');o.add_argument('--type',dest='item_type')
    o.add_argument('--scope',action='append',help='repeatable; replaces the scope');o.add_argument('--acceptance',action='append',help='repeatable; replaces the acceptance')
    o.add_argument('--depends-on',dest='depends_on',action='append',help='repeatable; replaces the dependencies');o.add_argument('--no-depends',action='store_true')
    o.add_argument('--reference',dest='references',action='append',help='repeatable; replaces the references');o.add_argument('--no-references',action='store_true')
    o=op('move',item=True);o.add_argument('--position',type=int,required=True)
    o=op('hold',item=True);o.add_argument('--reason',required=True)
    op('unhold',item=True);op('remove',item=True)
    o=op('authorize',help="record the owner's quoted instruction and capture the items it covers")
    o.add_argument('--kind',choices=['next','next-n','queue'],required=True);o.add_argument('--count',type=int)
    o.add_argument('--instruction',required=True,help="the owner's own message, verbatim");o.add_argument('--date',required=True,help='YYYY-MM-DD of the owner message')
    o=op('revoke',help='end the active authorization; use it for an owner pause');o.add_argument('--reason',required=True)
    o=op('start-next',help='start the head item as a cycle, or report the open cycle or the stop reason')
    o.add_argument('--implementer',default='dev-lead');o.add_argument('--coordinator',default='dev-lead')


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root', default='.')
    p.add_argument('--compact', action='store_true', help='print one JSON line: the cycle position, whether the record changed, and the named task')
    sub=p.add_subparsers(dest='command', required=True)
    c=sub.add_parser('create')
    for name in ('title','goal','implementer','coordinator'):
        c.add_argument('--'+name, required=True)
    c.add_argument('--type', choices=PHASES, required=True)
    c.add_argument('--list', dest='release_list', choices=['beta','official'], help='the fixed task list of a release cycle; required with --type release')
    for name in ('scope','acceptance'):
        c.add_argument('--'+name, action='append', required=True)
    for name in ('owner-approval','show','validate','advance','pause','resume','plan','task','checks','coverage','completion','evidence','scrutiny','review','decision','approve-decision','return','change-type','extend','reflect','abandon','query-decisions','task-add','plan-details','owner-complete','handoff','reconcile','reduction'):
        c=sub.add_parser(name); c.add_argument('cycle')
        if name in ('show','validate'): c.add_argument('--full', action='store_true', help='print the whole record instead of the bounded summary')
        c.add_argument('--compact', action='store_true', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
        if name=='reconcile': c.add_argument('--apply', action='store_true', help='write only the updates the commits and repository establish')
        if name in ('pause','resume','plan','change-type','plan-details'):
            c.add_argument('--reason', required=True)
        if name in ('plan','review','decision','reflect','task-add','coverage','plan-details','owner-complete','reduction'):
            c.add_argument('--file', type=Path, required=True)
        if name=='resume': c.add_argument('--new-evidence')
        if name=='task':
            c.add_argument('--task-id', required=True); c.add_argument('--state', choices=['pending','active','done','blocked'])
            c.add_argument('--assignee'); c.add_argument('--result-path', help='absolute, or relative to the repository root (not the docs root)'); c.add_argument('--note')
            c.add_argument('--commit', dest='commits', action='append', help='commit that resolves in this repository; repeatable, merged as a set')
            c.add_argument('--evidence', action='append', help='docs-relative path that exists; repeatable, merged as a set')
            c.add_argument('--stage', choices=['implemented','integrated'])
            c.add_argument('--replace-commit', nargs=2, metavar=('OLD','NEW'), help='replace a recorded commit (for example after a rebase) and keep the old id in replaced_commits; requires --note')
        if name=='checks': c.add_argument('--check', action='append', required=True)
        if name=='completion':
            group=c.add_mutually_exclusive_group(required=True)
            group.add_argument('--commit', dest='commits', action='append')
            group.add_argument('--exception', help='Actual user instruction requesting uncommitted delivery, with context')
            c.add_argument('--remaining', required=True)
        if name=='evidence':
            c.add_argument('--check-id',required=True); c.add_argument('--evidence-id',required=True); c.add_argument('--use',choices=['executed','reused','waited'],required=True)
        if name=='scrutiny':
            c.add_argument('--scrutiny',choices=['focused','standard','intensive'],required=True); c.add_argument('--rationale',required=True); c.add_argument('--risk',action='append',default=[])
        if name=='decision':
            c.add_argument('--kind',choices=['idr','adr'],required=True); c.add_argument('--name',required=True); c.add_argument('--creation-approval'); c.add_argument('--creation-subject')
        if name=='approve-decision':
            c.add_argument('--subject',required=True); c.add_argument('--approval',required=True)
        if name=='owner-approval':
            c.add_argument('--subject',required=True); c.add_argument('--quote',required=True)
            c.add_argument('--conversation',required=True); c.add_argument('--date')
            c.add_argument('--approve',action='store_true',help='also run approve-decision on the new record')
            c.add_argument('--print-command',action='store_true',help='print the owner command; write nothing')
        if name=='return':
            for field in ('improved','unresolved','next-change','justification'): c.add_argument('--'+field,required=True)
            c.add_argument('--progress',choices=['yes','no'],required=True)
        if name=='change-type':
            c.add_argument('--type',choices=PHASES,required=True); c.add_argument('--human-approval')
        if name=='extend':
            c.add_argument('--limit',type=int,required=True); c.add_argument('--human-approval',required=True)
    queue_parser(sub)
    c=sub.add_parser('await', help='wait for a delegated result file; read-only, run it as a host background command', description='Wait until a result file exists, is non-empty and stops growing; the first file to arrive wins. Two forms: `await CYCLE --task-id ID` watches the recorded result_path of each named task; `await --path ABS` watches an exact absolute result path and reads no cycle, so it serves a dispatch with no task and bookkeeping after closure. Prints one JSON line and exits 0 on arrival or 1 on timeout (ok true, arrived false) or refusal (ok false). The path form prints cycle and task as null. It writes nothing. A file that arrived proves neither that the agent is alive nor that its work is complete: read and validate the report.')
    c.add_argument('cycle', nargs='?', help='cycle id; required with --task-id, refused with --path'); c.add_argument('--compact', action='store_true', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    c.add_argument('--task-id', action='append', dest='task_ids', help='task whose result_path to watch; repeatable')
    c.add_argument('--path', action='append', dest='paths', help='exact absolute result path to watch, with no cycle and no task; repeatable')
    c.add_argument('--timeout', type=float, required=True, help='seconds to wait, above 0 and at most 3600')
    c=sub.add_parser('status', help='show cycle progress; read-only', description='Render cycle progress exactly as visualize-cycle-progress.py does. With no CYCLE it shows active cycles first, then the others by cycle number, highest first, at most 20, followed by the queue. It writes nothing. Exit 0 ok, 1 invalid or unknown cycle, 2 environment.')
    c.add_argument('cycle', nargs='?', help='cycle id; omit it to show every cycle')
    c.add_argument('--json', action='store_true', help="print the visualizer's JSON document")
    c.add_argument('--watch', type=positive_seconds, metavar='SECONDS', help='clear the screen and redraw every SECONDS until Ctrl-C')
    return p


def positive_seconds(value):
    seconds=float(value)
    if not seconds>0: raise argparse.ArgumentTypeError('must be above 0')
    return seconds


CLEAR='\x1b[H\x1b[2J'


def status(repo_root, cycle_id, as_json, watch):
    """Print the cycle visualization once, or redraw it every `watch` seconds until Ctrl-C; read-only."""
    from cycle_progress import view, render
    def draw():
        document=view(repo_root,cycle_id)
        return json.dumps(document) if as_json else render(document)
    try:
        if watch is None: print(draw()); return 0
        while True:
            print(CLEAR+draw(), flush=True); time.sleep(watch)
    except KeyboardInterrupt:
        return 0
    except (BionicConfigError,ImportError) as exc:
        print(str(exc), file=sys.stderr); return 2
    except (CycleError,ValueError,OSError,KeyError) as exc:
        print(json.dumps({'format':'crux.cycle-progress','format_version':2,'ok':False,'error':{'code':'run-invalid'}}) if as_json else str(exc)); return 1


AWAIT_POLL=0.25; AWAIT_SETTLE=1.0; AWAIT_MAX=3600


def _arrived_size(path):
    try:
        if path.is_file() and path.stat().st_size>0: return path.stat().st_size
    except OSError: pass
    return None


def await_result(repo_root, cycle_id, task_ids, timeout, paths=None):
    """Wait for the first watched result file; read-only. Returns the output line.

    The task form resolves each task's recorded result_path through the cycle. The path form
    watches exact absolute paths and reads no cycle, so cycle state never refuses it."""
    if not 0<timeout<=AWAIT_MAX: raise CycleError(f'timeout must be above 0 and at most {AWAIT_MAX} seconds')
    if paths:
        if cycle_id or task_ids: raise CycleError('await takes either CYCLE --task-id ID or --path ABS, not both')
        if not all(Path(p).is_absolute() for p in paths): raise CycleError('--path must be an exact absolute result path')
        cycle_ref=None; watched=[(None,Path(p)) for p in paths]
    else:
        if not cycle_id or not task_ids: raise CycleError('await needs CYCLE with --task-id ID, or --path ABS')
        doc=load(repo_root,cycle_id); cfg=tree(repo_root); cycle_ref=doc['id']
        tasks={t['id']:t for t in doc['plan']['tasks']}; watched=[]
        for tid in task_ids:
            if tid not in tasks: raise CycleError(f'unknown task {tid}')
            if not tasks[tid].get('result_path'): raise CycleError(f'task {tid} has no recorded result_path')
            watched.append((tid,result_file(cfg,tasks[tid]['result_path'])))
    # Event.wait is a stdlib timed wait; no sleep call, and one interval at most 1 s.
    pause=threading.Event().wait
    start=time.monotonic(); deadline=start+timeout
    def line(task,path,arrived): return {'ok':True,'cycle':cycle_ref,'arrived':arrived,'task':task,'result_path':str(path) if path else None,'waited_seconds':round(time.monotonic()-start,2)}
    while True:
        for tid,path in watched:
            size=_arrived_size(path)
            if size is not None:
                pause(AWAIT_SETTLE)
                if _arrived_size(path)==size: return line(tid,path,True)
        remaining=deadline-time.monotonic()
        if remaining<=0: return line(None,None,False)
        pause(min(AWAIT_POLL,remaining))


def compact_line(doc, changed, task_id=None):
    line={'ok':True,'cycle':doc['id'],'phase':doc['phase'],'pass':doc['pass'],'status':doc['status'],'updated_at':doc['updated_at'],'changed':changed}
    if task_id:
        task=next(t for t in doc['plan']['tasks'] if t['id']==task_id)
        line['task']={'id':task['id'],'state':task['status'],**{k:task[k] for k in DELIVERY_FIELDS if k in task}}
    return line


def main(argv=None):
    a=parser().parse_args(argv)
    try:
        changed=True; task_id=None
        if a.command=='create':
            result=create(a.repo_root,a.type,a.title,a.goal,a.scope,a.acceptance,a.implementer,a.coordinator,release_list=a.release_list)
        elif a.command in ('show','validate'):
            result=load(a.repo_root,a.cycle); changed=False
            if not (a.full or a.compact):
                from cycle_summary import summarize, render
                cfg=tree(a.repo_root)
                print('{\n  "ok": true,\n  "summary": '+render(summarize(result,lambda ref: read_retained(cfg,ref))).replace('\n','\n  ')+'\n}'); return 0
        elif a.command=='status':
            return status(a.repo_root,a.cycle,a.json,a.watch)
        elif a.command=='await':
            report=await_result(a.repo_root,a.cycle,a.task_ids,a.timeout,a.paths)
            print(json.dumps(report,separators=(',',':'))); return 0 if report['arrived'] else 1
        elif a.command=='queue':
            import cycle_queue
            code,payload=cycle_queue.run(a)
            print(json.dumps(payload,**({'separators':(',',':')} if a.compact else {'indent':2}))); return code
        elif a.command=='handoff':
            from cycle_reconcile import handoff
            print(json.dumps(handoff(a.repo_root,a.cycle),**({'separators':(',',':')} if a.compact else {'indent':2}))); return 0
        elif a.command=='reconcile':
            from cycle_reconcile import reconcile
            report=reconcile(a.repo_root,a.cycle,a.apply)
            print(json.dumps(report,**({'separators':(',',':')} if a.compact else {'indent':2}))); return 0 if report['ok'] else 1
        elif a.command=='owner-approval':
            from owner_approval import write_owner_approval, printable_command
            if a.print_command:
                print(json.dumps({'ok':True,'command':printable_command(a.repo_root,a.cycle,a.subject,a.quote,a.conversation,a.date)},indent=2)); return 0
            path=write_owner_approval(a.repo_root,a.cycle,a.subject,a.quote,a.conversation,a.date)
            if not a.approve:
                print(json.dumps({'ok':True,'approval':path},indent=2)); return 0
            result,changed=mutate_tracked(a.repo_root,a.cycle,'approve-decision',subject=a.subject,approval=path)
        elif a.command=='query-decisions':
            result=query_decisions(a.repo_root,a.cycle)
        else:
            args=vars(a).copy()
            for k in ('repo_root','command','cycle','compact'): args.pop(k,None)
            task_id=args.get('task_id')
            if 'file' in args:
                value=json.loads(args.pop('file').read_text())
                args[{'plan':'plan','review':'report','decision':'contents','reflect':'reflection','task-add':'task','coverage':'coverage','plan-details':'details','owner-complete':'owner','reduction':'reduction'}[a.command]]=value
            for old,new in (('type','kind'),('check','checks'),('risk','risks')):
                if old in args: args[new]=args.pop(old)
            if 'progress' in args: args['progress']=args['progress']=='yes'
            result,changed=mutate_tracked(a.repo_root,a.cycle,a.command,**args)
        if a.compact: print(json.dumps(compact_line(result,changed,task_id),separators=(',',':'))); return 0
        print(json.dumps({'ok':True,'cycle':result},indent=2)); return 0
    except (CycleError,BionicConfigError,ValueError,OSError,KeyError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},**({'separators':(',',':')} if getattr(a,'compact',False) else {}))); return 1

if __name__=='__main__': sys.exit(main())
