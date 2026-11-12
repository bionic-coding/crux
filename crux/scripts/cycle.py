#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml>=6.0", "httpx>=0.27,<1.0"]
# ///
"""Create, execute and inspect a cycle; no reusable book or prompt minimum."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
from cycle_workflow import CLOSED, OPEN, CycleError, shortcut_present, PHASES, DELIVERY_FIELDS, create, load, locked, contained, atomic_bytes, mutate_tracked, tree, read_retained, query_decisions, result_file
from bionic_config import BionicConfigError
import cycle_classify
import cycle_commit
import cycle_context
import cycle_prereqs


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
    o.add_argument('--release-list',dest='release_list',choices=['beta','official'],help='a release item\'s task list: beta (the default) or official')
    o.add_argument('--held',action='store_true');o.add_argument('--reason',help='why the item is held; required with --held')
    o=op('list',help='one line per open item, the authorization and what start-next would do');o.add_argument('--full',action='store_true',help='every item with its full fields, and the authorization history')
    o=op('archive',help='preview or archive terminal started items');o.add_argument('--dry-run',action='store_true');o.add_argument('--migrate',action='store_true',help='explicitly migrate a format 1 queue to format 2')
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


# The commands that take one JSON document, and the argument name each hands to the mutation.
FILE_COMMANDS={'plan':'plan','review':'report','decision':'contents','reflect':'reflection','task-add':'task','coverage':'coverage','plan-details':'details','owner-complete':'owner','shortcut':'request','reduction':'reduction'}


def cycle_arguments(c, help='cycle id, such as CYC-0001; or give it as --cycle'):
    """The cycle every per-cycle command takes: positionally or as `--cycle CYC`; `resolve_cycle` merges them."""
    c.add_argument('cycle', nargs='?', help=help)
    c.add_argument('--cycle', dest='cycle_opt', metavar='CYC', help='the cycle id, as an alternative to the positional; naming both with different values is refused')


def resolve_cycle(p, a):
    """Set `a.cycle` from the positional or `--cycle`; refuse two different values; refuse neither where one is required."""
    if not hasattr(a,'cycle_opt'): return
    option=a.cycle_opt; del a.cycle_opt
    if a.cycle is not None and option is not None and a.cycle!=option:
        raise CycleError(f'the cycle is given twice with different values: {a.cycle} and {option}')
    if a.cycle is None: a.cycle=option
    if a.cycle is None and a.command not in ('await','status'): p.error('the following arguments are required: cycle')


def read_json_arg(repo_root, value):
    """The JSON text a `--json` option names: standard input for `-`, a repository file for `@PATH`, else the value itself.

    The file must resolve, through symlinks, to a regular file inside the repository root; a relative path is read from the root."""
    if value=='-': return sys.stdin.read()
    if not value.startswith('@'): return value
    name=value[1:]
    if not name: raise CycleError('--json @PATH needs a path after the @')
    root=Path(repo_root).resolve(); path=Path(name)
    target=(path if path.is_absolute() else root/path).resolve()
    if not target.is_relative_to(root): raise CycleError(f'--json @{name} resolves to {target}, outside the repository root {root}')
    if not target.is_file(): raise CycleError(f'--json @{name}: no file at {target}')
    try: return target.read_text()
    except OSError as exc: raise CycleError(f'--json @{name}: cannot read {target}: {type(exc).__name__}') from exc


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root', default='.')
    p.add_argument('--compact', action='store_true', help='print one JSON line: the cycle position, whether the record changed, and the named task')
    sub=p.add_subparsers(dest='command', required=True)
    c=sub.add_parser('create')
    for name in ('title','goal','implementer','coordinator'):
        c.add_argument('--'+name, required=True)
    c.add_argument('--type', choices=[*PHASES, 'auto'], required=True, help='the cycle type; auto asks the classifier to size the work and refuses when it cannot')
    c.add_argument('--sizing-receipt', dest='sizing_receipt', metavar='JSON', help='the receipt a fallen-back `--type auto` printed, passed back with an explicit --type so the creating save records it')
    c.add_argument('--list', dest='release_list', choices=['beta','official'], help='the fixed task list of a release cycle; required with --type release')
    for name in ('scope','acceptance'):
        c.add_argument('--'+name, action='append', required=True)
    for name in ('owner-approval','show','validate','advance','pause','resume','plan','task','checks','coverage','completion','evidence','scrutiny','review','decision','approve-decision','return','change-type','extend','reflect','abandon','query-decisions','task-add','plan-details','owner-complete','shortcut','handoff','reconcile','reduction','assignment','defer','withdraw-decision','friction'):
        c=sub.add_parser(name); cycle_arguments(c)
        if name in ('show','validate'): c.add_argument('--full', action='store_true', help='print the whole record instead of the bounded summary')
        c.add_argument('--compact', action='store_true', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
        if name=='reconcile': c.add_argument('--apply', action='store_true', help='write only the updates the commits and repository establish')
        if name in ('pause','resume','plan','change-type','plan-details','withdraw-decision'):
            c.add_argument('--reason', required=True)
        if name in FILE_COMMANDS:
            form=c.add_mutually_exclusive_group(required=True)
            form.add_argument('--file', type=Path, metavar='PATH', help='a file holding the JSON document')
            form.add_argument('--json', dest='json_text', metavar='JSON', help="the JSON document inline as one argument; '-' reads standard input; '@PATH' reads a file inside the repository")
        if name=='shortcut':
            form.add_argument('--present', action='store_true', help='print what the closure would record, with the reflection sha256 to quote; writes and commits nothing')
        if name=='friction':
            form=c.add_mutually_exclusive_group(required=True)
            form.add_argument('--json', dest='json_text', metavar='JSON', help="{who, what, cost, category, fix} as inline JSON, '-' for standard input or '@PATH' for a file inside the repository; appends one row to the cycle's friction log and commits the record")
            form.add_argument('--file', type=Path, metavar='PATH', help='a readable regular file holding the same JSON object')
        if name=='resume': c.add_argument('--new-evidence')
        if name=='defer':
            c.add_argument('--finding', help='finding id r<N>:<advisory|cosmetic>:<index>; defer names this or --decision'); c.add_argument('--note', required=True, help='where the follow-up is recorded')
            c.add_argument('--decision', help='a withdrawn IDR name: records where its removed work is followed up, with the reason and the council attempt history')
        if name=='withdraw-decision':
            c.add_argument('--name',required=True,help='the IDR name to withdraw')
            c.add_argument('--task',dest='tasks',action='append',default=[],help='a plan task id that depends on the IDR; repeatable. The task is removed from the plan in the same write')
        if name=='task':
            c.add_argument('--task-id', required=True); c.add_argument('--state', choices=['pending','active','done','blocked','superseded'])
            c.add_argument('--superseded-by', dest='superseded_by', metavar='TASK-ID', help='with --state superseded: the plan task that replaces this one, in the same phase; a dependency on this task is then satisfied once that task is done. Requires --note')
            c.add_argument('--expect-revision', type=int, help='optional version-three guard: refuse without mutation when the cycle revision changed; inspect before retrying')
            c.add_argument('--assignee'); c.add_argument('--result-path', help='absolute, or relative to the repository root or the docs root (the docs-relative form is converted)'); c.add_argument('--note')
            c.add_argument('--commit', dest='commits', action='append', help='commit that resolves in this repository; repeatable, merged as a set')
            c.add_argument('--evidence', action='append', help='path that exists, relative to the docs root or the repository root (converted to docs-relative); repeatable, merged as a set')
            c.add_argument('--stage', choices=['implemented','integrated'])
            c.add_argument('--fix-before', dest='fix_before', metavar='TE-ID', help='fix task: the test-evidence receipt of the check that failed')
            c.add_argument('--fix-after', dest='fix_after', metavar='TE-ID', help='fix task: the receipt of the same check passing now')
            c.add_argument('--fix-observation', help='criterion fix: committed JSON after observation, relative to the docs root')
            c.add_argument('--adopt-commit', dest='adopt_commits', action='append', help='adopt an ancestor commit delivered by this cycle in an earlier pass; repeatable')
            c.add_argument('--replace-commit', nargs=2, metavar=('OLD','NEW'), help='replace a recorded commit (for example after a rebase) and keep the old id in replaced_commits; requires --note')
        if name=='checks':
            c.add_argument('--check', action='append', required=True)
            c.add_argument('--phase', choices=['build'], help='build records the complete set of Build checks; omit to record the required checks')
        if name=='assignment':
            c.add_argument('--id', required=True, help='a task id, a stream id such as stream-a, or a singleton role name such as commander')
            mode=c.add_mutually_exclusive_group(required=True)
            mode.add_argument('--state', choices=['running','finished','lost'], help='running starts the id, or resumes a finished or lost one as the next attempt, and refuses while it is running; finished after the final report returned and the execution ended; lost needs --note naming host evidence')
            mode.add_argument('--seen', action='store_true', help='record contact with a running assignment: advances last_seen and sets --agent when given')
            mode.add_argument('--resume-token', metavar='TOKEN', help='before resuming the same open host execution, rotate this current delivery token and retain the previous result; requires --note')
            c.add_argument('--role', help='required with --state running'); c.add_argument('--task'); c.add_argument('--agent', help='host execution handle')
            c.add_argument('--result-path', help='absolute, or relative to the repository root or the docs root (the docs-relative form is converted)'); c.add_argument('--note')
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
            c.add_argument('--execution-task',help='in Build, required: the pending or blocked task whose execution proof refuses execution-foreign-source or execution-source-outside-scope; the writer re-runs the proof')
        if name=='change-type':
            c.add_argument('--type',choices=PHASES,required=True); c.add_argument('--human-approval')
        if name=='extend':
            c.add_argument('--limit',type=int,required=True); c.add_argument('--human-approval',required=True)
    queue_parser(sub)
    c=sub.add_parser('owner-decision', help='retain a shown decision and explicit conversational owner evidence')
    owner=c.add_subparsers(dest='owner_action', required=True)
    for action in ('present', 'capture', 'apply'):
        form=owner.add_parser(action)
        form.add_argument('--json', dest='owner_request', required=True,
                          help='one JSON request; the caller supplies observed words, source and disposition')
    c=sub.add_parser('context-read', help='read a bounded inspect-listed context reference; read-only',
                     description='Read canonical project/plugin context or an exact recorded attempt result. '
                     'Use inspect context_read.references; this grants no arbitrary path access. '
                     'Each page is at most 16384 UTF-8 bytes; each complete object at most 1048576 bytes. '
                     'Later pages require the first page SHA-256. Exit 0 page, 1 refusal, 2 environment.')
    cycle_arguments(c)
    c.add_argument('--compact', action='store_true', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    c.add_argument('--ref', required=True, help='exact reference from inspect context_read.references')
    c.add_argument('--offset', type=int, default=0, help='UTF-8 byte offset; use next_offset from the previous page')
    c.add_argument('--limit', type=int, default=16384, help='maximum page bytes, from 4 through 16384')
    c.add_argument('--sha256', help='full object digest from the first page; required after offset zero')
    c=sub.add_parser('op', help='run one typed operation from a JSON request', description='Run one typed cycle operation: inspect, prepare-dispatch, attach-execution, deliver, mark-lost, advance, finish, owner-exception or upgrade. The request is one JSON document (crux/schemas/cycle-operation.schema.json), given inline with --json REQUEST, on standard input with --json -, from a repository file with --json @PATH, or in a file with --file PATH. Prints one JSON response. Exit 0 succeeded or replayed, 1 refused with every error and its recovery, 2 environment.')
    cycle_arguments(c); c.add_argument('--compact', action='store_true', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    form=c.add_mutually_exclusive_group(required=True)
    form.add_argument('--json', dest='request', metavar='REQUEST', help="the request as one JSON string; '-' reads standard input; '@PATH' reads a file inside the repository")
    form.add_argument('--file', dest='request_file', type=Path, metavar='PATH', help='a file holding the request')
    c=sub.add_parser('await', help='wait for a delegated result file; read-only, run it as a host background command', description='Wait until a result file exists, is non-empty and stops growing; the first file to arrive wins. Two forms: `await CYCLE --task-id ID` watches the recorded result_path of each named task; `await --path ABS` watches an exact absolute result path and reads no cycle, so it serves a dispatch with no task and bookkeeping after closure. Prints one JSON line and exits 0 on arrival or 1 on timeout (ok true, arrived false) or refusal (ok false). The path form prints cycle and task as null. It writes nothing. A file that arrived proves neither that the agent is alive nor that its work is complete: read and validate the report.')
    cycle_arguments(c, 'cycle id, positional or --cycle; required with --task-id, refused with --path'); c.add_argument('--compact', action='store_true', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    c.add_argument('--task-id', action='append', dest='task_ids', help='task whose result_path to watch; repeatable')
    c.add_argument('--path', action='append', dest='paths', help='exact absolute result path to watch, with no cycle and no task; repeatable')
    c.add_argument('--timeout', type=float, required=True, help='seconds to wait, above 0 and at most 3600')
    c.add_argument('--marker', metavar='ASSIGNMENT/ATTEMPT[#TOKEN]', help='arrive only when the last non-blank line matches this exact result marker; use the current token from inspect for a modern attempt')
    c=sub.add_parser('status', help='show cycle progress; read-only', description='Render cycle progress exactly as visualize-cycle-progress.py does. With no CYCLE it shows active cycles first, then the others by cycle number, highest first, at most 60, followed by the queue. It writes nothing. Exit 0 ok, 1 invalid or unknown cycle, 2 environment.')
    cycle_arguments(c, 'cycle id, positional or --cycle; omit it to show every cycle')
    c.add_argument('--json', action='store_true', help="print the visualizer's JSON document")
    c.add_argument('--watch', type=positive_seconds, metavar='SECONDS', help='clear the screen and redraw every SECONDS until Ctrl-C')
    c.add_argument('--activity', action='store_true', help="with --json, add each cycle's derived last activity; the default JSON is unchanged (text always shows it for an open cycle)")
    return p


def positive_seconds(value):
    seconds=float(value)
    if not seconds>0: raise argparse.ArgumentTypeError('must be above 0')
    return seconds


CLEAR='\x1b[H\x1b[2J'


def status(repo_root, cycle_id, as_json, watch, activity=False):
    """Print the cycle visualization once, or redraw it every `watch` seconds until Ctrl-C; read-only."""
    from cycle_progress import view, render, FORMAT_VERSION
    def draw():
        document=view(repo_root,cycle_id,activity=activity)
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
        print(json.dumps({'format':'crux.cycle-progress','format_version':FORMAT_VERSION,'ok':False,'error':{'code':'run-invalid'}}) if as_json else str(exc)); return 1


AWAIT_POLL=0.25; AWAIT_SETTLE=1.0; AWAIT_MAX=3600


def _arrived_size(path):
    try:
        if path.is_file() and path.stat().st_size>0: return path.stat().st_size
    except OSError: pass
    return None


def await_result(repo_root, cycle_id, task_ids, timeout, paths=None, end_marker=None):
    """Wait for the first watched result file; read-only. Returns the output line.

    The task form resolves each task's recorded result_path through the cycle. The path form
    watches exact absolute paths and reads no cycle, so cycle state never refuses it."""
    if not 0<timeout<=AWAIT_MAX: raise CycleError(f'timeout must be above 0 and at most {AWAIT_MAX} seconds')
    expected=None
    if end_marker is not None:
        import cycle_hosts
        expected=cycle_hosts.parse_marker(end_marker)
        if expected is None: raise CycleError('--marker must be ASSIGNMENT/ATTEMPT, for example build-it/1')
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
            if expected is not None:
                if cycle_hosts.marker_arrived(path,*expected): return line(tid,path,True)
                continue
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


RESUME_STEPS=[
    'Check the host handle of each running assignment before dispatching anything.',
    'When agent is null, look for a live host execution matching its role and result path.',
    'If the execution is alive, message or await it and dispatch nothing.',
    'Record an assignment lost only with host evidence that it ended without a final report: --state lost --note naming that evidence.',
    'Then resume the work under the same id with --state running.',
]

RESERVED_STEPS=[
    'A reserved attempt was prepared and may not have launched: attach its handle with the attach-execution operation, deliver its result, or mark it lost with host evidence.',
]

def with_assignments(repo,identity,out):
    """Add the open assignments, with elapsed seconds since last_seen, and the resume steps to a handoff.

    A version-3 record lists reserved as well as running attempts and adds each one's state and host;
    a version-1 or version-2 record lists running assignments with the earlier keys only."""
    from datetime import datetime, timezone
    doc=load(repo,identity); at=datetime.now(timezone.utc); running=[]
    open_states=OPEN if doc['schema_version']==3 else ('running',)
    for e in doc.get('assignments',[]):
        if e['state'] not in open_states: continue
        seen=datetime.fromisoformat(e['last_seen'])
        row={**{k:e[k] for k in ('id','role','task','agent','result_path','attempt','started_at','last_seen')},'elapsed_seconds':max(0,int((at-seen).total_seconds()))}
        if doc['schema_version']==3: row.update(state=e['state'],host=e.get('host'))
        running.append(row)
    out['assignments']=running; out['resume_steps']=RESUME_STEPS+(RESERVED_STEPS if any(r.get('state')=='reserved' for r in running) else [])
    return out

def with_fixes(repo,identity,out):
    """Add one row per fix task (task, pass, phase, finding, status) to a handoff."""
    doc=load(repo,identity)
    out['fixes']=[{'task':t['id'],'pass':t['fix']['pass'],'phase':t['phase'],'finding':t['fix']['finding'],'status':t['status']} for t in doc['plan']['tasks'] if 'fix' in t]
    return out

def action_file_form(a):
    """The `op` argv that reads the request from a file: the recovery a JSON parse refusal names."""
    return {'argv':['uv','run',str(Path(__file__).resolve()),'--repo-root',str(a.repo_root),'--compact','op',a.cycle,'--file'],
            'caller_fills':['--file'],'purpose':'write the request to a file and pass its path; a file needs no shell escaping'}


def run_op(a):
    """`cycle.py op`: parse the request, run it, print the response; exit 0, 1 or 2."""
    import cycle_ops
    dumps=lambda value: json.dumps(value,**({'separators':(',',':')} if a.compact else {'indent':2}))
    file_form=action_file_form(a)
    try:
        if a.request_file is not None and not a.request_file.is_file():
            raise OSError('not a regular file')
        text=a.request_file.read_text() if a.request_file is not None else read_json_arg(a.repo_root,a.request)
    except CycleError as exc:
        print(dumps({'ok':False,'op':None,'cycle':a.cycle,'errors':[cycle_ops.failure('request-unreadable',str(exc),field='--json',observed=a.request)]})); return 1
    except OSError as exc:
        print(dumps({'ok':False,'op':None,'cycle':a.cycle,'errors':[cycle_ops.failure('request-unreadable',f'cannot read the request: {type(exc).__name__}: {exc}; --file takes a readable regular file',field='--file',observed=str(a.request_file))]})); return 1
    try:
        request=json.loads(text)
    except ValueError as exc:
        # The usual cause is shell quoting of an inline payload; the file form needs no escaping.
        print(dumps({'ok':False,'op':None,'cycle':a.cycle,'errors':[cycle_ops.failure('invalid-request',f'the request is not JSON: {exc}. Write the request to a file and pass it with --file PATH (or --json @PATH for a file inside the repository); a file needs no shell escaping',field=None,
                                                                                         recovery=[file_form])]})); return 1
    try:
        code,response=cycle_ops.run(a.repo_root,a.cycle,request)
    except (BionicConfigError,ImportError) as exc:
        print(str(exc),file=sys.stderr); return 2
    print(dumps(response)); return code


def create_command(a):
    """`create`: an explicit type, or `auto` to size the work; a sizing receipt is recorded by the creating save."""
    common=(a.title,a.goal,a.scope,a.acceptance,a.implementer,a.coordinator)
    if a.type=='auto':
        if a.sizing_receipt is not None: raise CycleError('--sizing-receipt belongs to an explicit --type')
        if a.release_list is not None: raise CycleError('--list belongs to release cycles; type auto never sizes to release')
        # Prerequisites refuse before the sizing request and before the cycles lock; nothing is written.
        cycle_prereqs.require(tree(a.repo_root).repo_root,a.scope)
        return cycle_classify.size_work(a.repo_root,lambda kind,classification: create(a.repo_root,kind,*common,classification=classification),a.title,a.goal,a.scope,a.acceptance)
    classification=None
    if a.sizing_receipt is not None:
        classification=cycle_classify.receipt_classification(cycle_classify.validate_sizing_receipt(json.loads(a.sizing_receipt)))
    cycle_prereqs.require(tree(a.repo_root).repo_root,a.scope)
    return create(a.repo_root,a.type,*common,release_list=a.release_list,classification=classification)


def _same_file(first, second):
    return first.resolve()==second.resolve()


def _two_files(kind, item, docs_path, repo_path):
    return CycleError(f'{kind} {item} names two different files: {docs_path.resolve()} (relative to the docs root) and {repo_path.resolve()} (relative to the repository root); give an absolute path to choose one')


def _plain(item):
    path=Path(item)
    return not path.is_absolute() and '..' not in path.parts and bool(path.parts)


def normalize_evidence(cfg, item):
    """An evidence path in the docs-relative form the writer takes, from a docs-relative or repository-relative one."""
    if not _plain(item): return item
    in_docs, in_repo=cfg.docs_root/item, cfg.repo_root/item
    if in_docs.is_file() and in_repo.is_file() and not _same_file(in_docs,in_repo): raise _two_files('evidence',item,in_docs,in_repo)
    if in_docs.is_file() or not in_repo.is_file(): return item
    try: return in_repo.resolve().relative_to(cfg.docs_root.resolve()).as_posix()
    except ValueError: return item


def normalize_result_path(cfg, item):
    """A result path in the repository-relative (or absolute) form the writer takes, from a repository-relative or docs-relative one."""
    if not _plain(item): return item
    in_docs, in_repo=cfg.docs_root/item, cfg.repo_root/item
    if in_docs.exists() and in_repo.exists() and not _same_file(in_docs,in_repo): raise _two_files('result path',item,in_docs,in_repo)
    if in_repo.exists() or not in_docs.exists(): return item
    return Path(os.path.relpath(in_docs, cfg.repo_root)).as_posix()


FRICTION_KEYS=('who','what','cost','category','fix')
FRICTION_HEADER="""# {cycle} friction log

This log records each point where the cycle procedure, its instructions, the host or the tooling
cost time or rounds that a better tool or instruction would have saved. Each entry names what
happened with the command or step, its cost, a category (engine, instructions, host or tooling) and
a proposed fix. Entries are appended as the cycle runs; the Reflect phase reads them.

| Id | Who | What happened (command or step) | Cost | Category | Proposed fix |
|---|---|---|---|---|---|
"""


def friction_command(a):
    """`friction`: append one row to the cycle's friction log under the cycle lock, then commit the record. Returns the JSON output."""
    if getattr(a,'file',None) is not None:
        if not a.file.is_file(): raise CycleError(f'--file {a.file}: not a readable regular file')
        text=a.file.read_text()
    else:
        text=read_json_arg(a.repo_root,a.json_text)
    try: request=json.loads(text)
    except ValueError as exc: raise CycleError(f'the friction request is not JSON: {exc}; write it to a file and pass --file PATH') from exc
    if not isinstance(request,dict): raise CycleError('the friction request must be a JSON object')
    unknown=sorted(set(request)-set(FRICTION_KEYS)); missing=[k for k in FRICTION_KEYS if not (isinstance(request.get(k),str) and request[k].strip())]
    if unknown: raise CycleError('unknown friction keys: '+', '.join(unknown))
    if missing: raise CycleError('friction needs non-empty string values for: '+', '.join(missing))
    cells=[re.sub(r'\s*[\r\n]+\s*',' ',request[k].strip()).replace('|','\\|') for k in FRICTION_KEYS]
    doc=load(a.repo_root,a.cycle)
    with locked(a.repo_root) as (cfg,_):
        path=contained(cfg.docs_root,f"cycles/{doc['id']}/evidence/friction.md")
        text=path.read_text() if path.is_file() else FRICTION_HEADER.format(cycle=doc['id'])
        numbers=[int(m.group(1)) for m in re.finditer(r'^\|\s*F(\d+)\s*\|',text,re.M)]
        ident=f'F{max(numbers,default=0)+1}'
        if not text.endswith('\n'): text+='\n'
        atomic_bytes(path,(text+f"| {ident} | "+' | '.join(cells)+' |\n').encode())
        relative=path.relative_to(cfg.repo_root).as_posix()
    return {'ok':True,'cycle':doc['id'],'id':ident,'path':relative,'record_commit':cycle_commit.after_write(a.repo_root,doc['id'],'friction')}


@cycle_context.cache_only_operation
def main(argv=None):
    pr=parser(); a=pr.parse_args(argv)
    extra={}
    try:
        resolve_cycle(pr,a)
        changed=True; task_id=None
        if a.command=='owner-decision':
            import owner_decision
            try:
                request=json.loads(read_json_arg(a.repo_root,a.owner_request))
                report=getattr(owner_decision,a.owner_action)(a.repo_root,request)
            except owner_decision.OwnerDecisionError as exc:
                print(json.dumps({'ok':False,'error':{'code':exc.code}})); return 1
            if request.get('cycle_id'):
                report['record_commit']=cycle_commit.after_write(a.repo_root,request['cycle_id'],'owner-decision '+a.owner_action)
            print(json.dumps({'ok':True,**report},indent=2)); return 0
        if a.command=='friction':
            print(json.dumps(friction_command(a),**({'separators':(',',':')} if a.compact else {'indent':2}))); return 0
        if a.command=='create':
            result=create_command(a)
        elif a.command in ('show','validate'):
            result=load(a.repo_root,a.cycle); changed=False
            if not (a.full or a.compact):
                from cycle_summary import summarize, render
                cfg=tree(a.repo_root)
                print('{\n  "ok": true,\n  "summary": '+render(summarize(result,lambda ref: read_retained(cfg,ref))).replace('\n','\n  ')+'\n}'); return 0
        elif a.command=='status':
            return status(a.repo_root,a.cycle,a.json,a.watch,a.activity)
        elif a.command=='context-read':
            from cycle_context_read import read_context
            report=read_context(tree(a.repo_root),load(a.repo_root,a.cycle),a.ref,
                                offset=a.offset,limit=a.limit,sha256=a.sha256)
            print(json.dumps(report,**({'separators':(',',':')} if a.compact else {'indent':2})))
            return 0 if report['ok'] else 1
        elif a.command=='await':
            report=await_result(a.repo_root,a.cycle,a.task_ids,a.timeout,a.paths,a.marker)
            print(json.dumps(report,separators=(',',':'))); return 0 if report['arrived'] else 1
        elif a.command=='op':
            return run_op(a)
        elif a.command=='queue':
            import cycle_queue
            if a.queue_op == 'add' and a.item_type == 'release':
                import cycle_hosts
                a.scope = cycle_hosts.release_scope(tree(a.repo_root), cycle_queue.split_scope(a.scope),
                                                    a.release_list or 'beta', capture=True)
            code,payload=cycle_queue.run(a)
            print(json.dumps(payload,**({'separators':(',',':')} if a.compact else {'indent':2}))); return code
        elif a.command=='handoff':
            from cycle_reconcile import handoff
            print(json.dumps(with_fixes(a.repo_root,a.cycle,with_assignments(a.repo_root,a.cycle,handoff(a.repo_root,a.cycle))),**({'separators':(',',':')} if a.compact else {'indent':2}))); return 0
        elif a.command=='reconcile':
            from cycle_reconcile import reconcile
            report=reconcile(a.repo_root,a.cycle,a.apply)
            print(json.dumps(report,**({'separators':(',',':')} if a.compact else {'indent':2}))); return 0 if report['ok'] else 1
        elif a.command=='owner-approval':
            from owner_approval import write_owner_approval, printable_command
            if a.print_command:
                print(json.dumps({'ok':True,'command':printable_command(a.repo_root,a.cycle,a.subject,a.quote,a.conversation,a.date)},indent=2)); return 0
            cycle_status=load(a.repo_root,a.cycle)['status']
            if cycle_status in CLOSED: raise CycleError('closed cycles cannot restart or mutate')
            if cycle_status=='paused': raise CycleError('cycle is paused; resolve its blocker and resume first')
            path=write_owner_approval(a.repo_root,a.cycle,a.subject,a.quote,a.conversation,a.date)
            if not a.approve:
                print(json.dumps({'ok':True,'approval':path},indent=2)); return 0
            result,changed=mutate_tracked(a.repo_root,a.cycle,'approve-decision',subject=a.subject,approval=path)
        elif a.command=='shortcut' and a.present:
            print(json.dumps({'ok':True,'present':shortcut_present(a.repo_root,a.cycle)},**({'separators':(',',':')} if a.compact else {'indent':2}))); return 0
        elif a.command=='query-decisions':
            result=query_decisions(a.repo_root,a.cycle)
        else:
            args=vars(a).copy()
            for k in ('repo_root','command','cycle','compact','present'): args.pop(k,None)
            task_id=args.get('task_id')
            if 'file' in args:
                path,text=args.pop('file'),args.pop('json_text')
                args[FILE_COMMANDS[a.command]]=json.loads(path.read_text() if path is not None else read_json_arg(a.repo_root,text))
            for old,new in (('type','kind'),('check','checks'),('risk','risks')):
                if old in args: args[new]=args.pop(old)
            if 'progress' in args: args['progress']=args['progress']=='yes'
            if a.command in ('task','assignment') and (args.get('result_path') or args.get('evidence')):
                cfg=tree(a.repo_root)
                if args.get('result_path'): args['result_path']=normalize_result_path(cfg,args['result_path'])
                if args.get('evidence'): args['evidence']=[normalize_evidence(cfg,e) for e in args['evidence']]
            before=load(a.repo_root,a.cycle)['phase'] if a.command=='advance' else None
            try:
                result,changed=mutate_tracked(a.repo_root,a.cycle,a.command,**args)
            except (CycleError,ValueError):
                if a.command=='evidence': extra.update(cycle_classify.response_fields(cycle_classify.safely(cycle_classify.failed_check,a.repo_root,a.cycle,args['evidence_id'])))
                raise
            if changed and a.command=='advance' and before!='review' and result['phase']=='review':
                extra.update(cycle_classify.response_fields(cycle_classify.safely(cycle_classify.entered_review,a.repo_root,a.cycle)))
            elif changed and a.command=='review':
                extra.update(cycle_classify.response_fields(cycle_classify.safely(cycle_classify.recorded_review,a.repo_root,a.cycle)))
            if changed and a.command in cycle_commit.LOW_LEVEL_COMMITTING: extra['record_commit']=cycle_commit.after_write(a.repo_root,a.cycle)
            if 'revision' in extra: result=load(a.repo_root,a.cycle)
        if a.compact: print(json.dumps({**compact_line(result,changed,task_id),**extra},separators=(',',':'))); return 0
        print(json.dumps({'ok':True,'cycle':result,**extra},indent=2)); return 0
    except cycle_prereqs.EnvironmentPrerequisite as exc:
        print(json.dumps(exc.payload(),**({'separators':(',',':')} if getattr(a,'compact',False) else {}))); return 1
    except cycle_classify.SizingFallback as exc:
        print(json.dumps({'ok':False,'error':str(exc),'sizing_receipt':exc.receipt,'question':exc.question,'evidence':exc.evidence},**({'separators':(',',':')} if getattr(a,'compact',False) else {}))); return 1
    except (CycleError,BionicConfigError,ValueError,OSError,KeyError) as exc:
        print(json.dumps({'ok':False,'error':str(exc),**extra},**({'separators':(',',':')} if getattr(a,'compact',False) else {}))); return 1

if __name__=='__main__': sys.exit(main())
