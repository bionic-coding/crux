#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml>=6.0", "httpx>=0.27,<1.0"]
# ///
"""Create, run and inspect a cycle: one lead, milestone records, native delegation and independent review."""
import argparse
import json
from pathlib import Path
import sys
import time
from bionic_config import BionicConfigError
from cycle_store import CycleError


def cycle_arguments(c, help='cycle id, such as CYC-0001; or give it as --cycle'):
    """The cycle `status` takes: positionally or as `--cycle CYC`; `resolve_cycle` merges them."""
    c.add_argument('cycle', nargs='?', help=help)
    c.add_argument('--cycle', dest='cycle_opt', metavar='CYC', help='the cycle id, as an alternative to the positional; naming both with different values is refused')


def resolve_cycle(p, a):
    """Set `a.cycle` from the positional or `--cycle`; refuse two different values."""
    if not hasattr(a,'cycle_opt'): return
    option=a.cycle_opt; del a.cycle_opt
    if a.cycle is not None and option is not None and a.cycle!=option:
        raise CycleError(f'the cycle is given twice with different values: {a.cycle} and {option}')
    if a.cycle is None: a.cycle=option


def add_status_parser(sub):
    c=sub.add_parser('status', help='show cycle progress; read-only', description='Render cycle progress exactly as visualize-cycle-progress.py does. With no CYCLE it shows active cycles first, then the others by cycle number, highest first, at most 60, followed by the queue. It writes nothing. Exit 0 ok, 1 invalid or unknown cycle, 2 environment.')
    cycle_arguments(c, 'cycle id, positional or --cycle; omit it to show every cycle')
    c.add_argument('--json', action='store_true', help="print the visualizer's JSON document")
    c.add_argument('--watch', type=positive_seconds, metavar='SECONDS', help='clear the screen and redraw every SECONDS until Ctrl-C')


def positive_seconds(value):
    seconds=float(value)
    if not seconds>0: raise argparse.ArgumentTypeError('must be above 0')
    return seconds


CLEAR='\x1b[H\x1b[2J'


def status(repo_root, cycle_id, as_json, watch):
    """Print the cycle visualization once, or redraw it every `watch` seconds until Ctrl-C; read-only."""
    from cycle_progress import view, render, FORMAT_VERSION
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
        print(json.dumps({'format':'crux.cycle-progress','format_version':FORMAT_VERSION,'ok':False,'error':{'code':'run-invalid'}}) if as_json else str(exc)); return 1


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
    o=op('list',help='one line per open item, the authorization and what start-next would do');o.add_argument('--full',action='store_true',help='one row per item and the authorization history; an archived row omits its outcome, scope, acceptance and references, which queue show gives')
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
    o=op('reconcile',item=True,help='associate a pending item with the reviewed pilot cycle that completed it; a repeat changes nothing')
    o.add_argument('--pilot',required=True,help='the pilot cycle id');o.add_argument('--actor',required=True,help="the pilot's recorded lead")
    o.add_argument('--file',required=True,help='JSON assessment: outcome evidence and one evidence entry per queue acceptance criterion')
    o=op('authorize',help="record the owner's quoted instruction and capture the items it covers")
    o.add_argument('--kind',choices=['next','next-n','queue'],required=True);o.add_argument('--count',type=int)
    o.add_argument('--instruction',required=True,help="the owner's own message, verbatim");o.add_argument('--date',required=True,help='YYYY-MM-DD of the owner message')
    o=op('revoke',help='end the active authorization; use it for an owner pause');o.add_argument('--reason',required=True)
    o=op('start-next',help='start the head item as a cycle, or report the open cycle or the stop reason')
    o.add_argument('--implementer',default='dev-lead',help='the lead when --lead is omitted');o.add_argument('--coordinator',default='dev-lead',help='a release item\'s test coordinator')
    o.add_argument('--pilot',action='store_true',help='accepted and ignored: every start is the writer\'s start')
    o.add_argument('--lead',help='the cycle lead; default the implementer')
    o.add_argument('--plan',help='optional JSON holding any of verification, council, tasks and scrutiny; the item supplies goal, scope and acceptance, and without it the cycle starts in planning')


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


# The typed cycle commands that no longer exist, each with the writer command that replaces it. None loads a module.
NO_SUCH_STEP='the workflow has no such step; the lead plans, works, requests an independent review and finishes'
RETIRED={
    'owner-approval': 'record the owner approval of a scope or acceptance change with plan --owner-approval',
    'validate': 'show IDENTITY prints the record; check records a check observation',
    'advance': 'task moves work, review-start requests the review and finish completes the cycle; no phase advances',
    'checks': 'check IDENTITY --file records one check observation; plan --file holds the selected checks',
    'coverage': 'plan --file holds the selected checks and their gaps; check records each observation',
    'completion': 'finish completes the cycle once the agreed work, checks and independent review are complete; delivery records PR, CI and merge facts',
    'evidence': 'check IDENTITY --file records an observed check with its command, revision and result',
    'local-check': 'check IDENTITY --file records one check observation',
    'scrutiny': 'plan --file carries the scrutiny level and its reason',
    'decision': 'decision-policy.py propose and accept record an ADR decision; council-subject and council attach a plan council',
    'approve-decision': 'council IDENTITY --record RECORD --response TEXT attaches an approved plan council; decision-policy.py propose and accept record an ADR decision',
    'return': 'review records the verdict; task --status working restarts a task and plan --file changes the plan',
    'change-type': NO_SUCH_STEP,
    'extend': NO_SUCH_STEP,
    'reflect': NO_SUCH_STEP,
    'query-decisions': 'show IDENTITY prints the record',
    'task-add': 'plan IDENTITY --file FILE --reason TEXT replaces the plan and its tasks',
    'plan-details': 'plan IDENTITY --file FILE --reason TEXT replaces the plan and its tasks',
    'owner-complete': 'finish completes the cycle; reopen restores a completed cycle on the owner\'s instruction',
    'shortcut': 'create a one-task plan with create, then complete it with finish',
    'handoff': 'show IDENTITY --full prints the record; status IDENTITY renders its progress',
    'reconcile': 'recover IDENTITY settles the checkout claims an interrupted write left',
    'reduction': 'record the reduction in the plan with plan --file or in the review report with review --file',
    'assignment': 'task IDENTITY --task ID --owner OWNER --run N --status working records who works a task',
    'defer': 'record a deferred finding in the review report with review --file, or start a linked cycle with create --follows',
    'withdraw-decision': 'plan --file replaces the plan and its tasks; council attaches a new plan council',
    'friction': 'record friction in the review report or the cycle\'s evidence files; the workflow keeps no friction log',
    'owner-decision': 'decision-policy.py owner-decision present, capture and apply record an owner decision on an ADR acceptance; council-subject and council attach a plan council; plan --owner-approval records an owner approval of a scope or acceptance change',
    'context-read': 'read the context file directly with the host\'s file reader; the workflow has no context bundles',
    'op': 'use the writer commands: create, plan, task, check, review-start, review, finish, delivery, reopen, pause, resume, abandon, recover',
    'await': 'native host waiting: wait on the delegated agent with the host\'s own wait; the workflow has no await command',
}
LEGACY_NOTE=('{identity} is a legacy typed-engine record: it is read-only through cycle.py show and status, '
             'and nothing changed.')


def command_token(argv):
    """The command named in `argv`, read past the global options only; None when there is none."""
    rest=iter(argv)
    for token in rest:
        if token=='--repo-root': next(rest,None)
        elif token.startswith('--repo-root=') or token=='--compact': continue
        else: return token
    return None


def repo_root_of(argv):
    rest=iter(argv)
    for token in rest:
        if token=='--repo-root': return next(rest,'.')
        if token.startswith('--repo-root='): return token.split('=',1)[1]
    return '.'


def named_legacy_record(argv):
    """The id of the first cycle in `argv` whose record is a legacy typed-engine record, or None; reads one file at most per id."""
    import cycle_history
    from cycle_store import contained, tree
    root=repo_root_of(argv)
    for token in argv:
        identity=token.split('=',1)[1] if token.startswith('--cycle=') else token
        if not cycle_history.ID.fullmatch(identity): continue
        try:
            path=contained(tree(root).docs_root,f'cycles/{identity}/cycle.json')
            if not path.is_symlink() and path.is_file() and cycle_history.is_legacy(json.loads(path.read_text(encoding='utf-8'))): return identity
        except (CycleError,BionicConfigError,OSError,ValueError): continue
    return None


def retire(name, argv):
    """Print the `command-retired` refusal for a former typed command, naming its replacement; exit 1, nothing written."""
    replacement=RETIRED[name]
    message=f'cycle.py {name} is retired: {replacement}.'
    legacy=named_legacy_record(argv)
    if legacy: message+=' '+LEGACY_NOTE.format(identity=legacy)
    print(json.dumps({'ok':False,'error':{'code':'command-retired','command':name,'replacement':replacement,'message':message}},**({'separators':(',',':')} if '--compact' in argv else {})))
    return 1


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root', default='.')
    p.add_argument('--compact', action='store_true', help='print one JSON line for queue operations')
    sub=p.add_subparsers(dest='command', required=True)
    import cycle_writer
    cycle_writer.add_commands(sub)
    cycle_writer.add_parser(sub)
    queue_parser(sub)
    add_status_parser(sub)
    return p


def main(argv=None):
    argv=sys.argv[1:] if argv is None else list(argv)
    name=command_token(argv)
    if name in RETIRED: return retire(name,argv)
    pr=parser(); a=pr.parse_args(argv)
    dumps=lambda value: json.dumps(value,**({'separators':(',',':')} if a.compact else {'indent':2}))
    try:
        resolve_cycle(pr,a)
        if a.command=='status':
            return status(a.repo_root,a.cycle,a.json,a.watch)
        if a.command=='queue':
            import cycle_queue
            if a.queue_op == 'add' and a.item_type == 'release':
                import cycle_writer
                from cycle_store import tree
                a.scope = cycle_writer.release_scope(tree(a.repo_root), cycle_queue.split_scope(a.scope),
                                                    a.release_list or 'beta', capture=True)
            code,payload=cycle_queue.run(a)
            print(dumps(payload)); return code
        from cycle_writer import cli
        return cli(a)
    except (CycleError,BionicConfigError,ValueError,OSError,KeyError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},**({'separators':(',',':')} if a.compact else {}))); return 1

if __name__=='__main__': sys.exit(main())
