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
from cycle_workflow import CycleError, PHASES, create, load, mutate, tree, read_retained, query_decisions
from bionic_config import BionicConfigError


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root', default='.')
    sub=p.add_subparsers(dest='command', required=True)
    c=sub.add_parser('create')
    for name in ('title','goal','implementer','coordinator'):
        c.add_argument('--'+name, required=True)
    c.add_argument('--type', choices=PHASES, required=True)
    for name in ('scope','acceptance'):
        c.add_argument('--'+name, action='append', required=True)
    for name in ('show','validate','advance','pause','resume','plan','task','checks','coverage','completion','evidence','scrutiny','review','decision','approve-decision','return','change-type','extend','release-ready','release-verified','reflect','abandon','query-decisions','task-add','plan-details'):
        c=sub.add_parser(name); c.add_argument('cycle')
        if name in ('pause','resume','plan','change-type','plan-details'):
            c.add_argument('--reason', required=True)
        if name in ('plan','review','decision','reflect','task-add','coverage','plan-details'):
            c.add_argument('--file', type=Path, required=True)
        if name=='resume': c.add_argument('--new-evidence')
        if name=='task':
            c.add_argument('--task-id', required=True); c.add_argument('--state', choices=['pending','active','done','blocked'],required=True)
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
        if name=='return':
            for field in ('improved','unresolved','next-change','justification'): c.add_argument('--'+field,required=True)
            c.add_argument('--progress',choices=['yes','no'],required=True)
        if name=='change-type':
            c.add_argument('--type',choices=PHASES,required=True); c.add_argument('--human-approval')
        if name=='extend':
            c.add_argument('--limit',type=int,required=True); c.add_argument('--human-approval',required=True)
        if name=='release-ready':
            c.add_argument('--authorization',required=True); c.add_argument('--destination',action='append',required=True); c.add_argument('--artifact',action='append',required=True)
        if name=='release-verified': c.add_argument('--verification',required=True)
    return p


def main(argv=None):
    a=parser().parse_args(argv)
    try:
        if a.command=='create':
            result=create(a.repo_root,a.type,a.title,a.goal,a.scope,a.acceptance,a.implementer,a.coordinator)
        elif a.command in ('show','validate'):
            result=load(a.repo_root,a.cycle)
        elif a.command=='query-decisions':
            result=query_decisions(a.repo_root,a.cycle)
        else:
            args=vars(a).copy()
            for k in ('repo_root','command','cycle'): args.pop(k,None)
            if 'file' in args:
                value=json.loads(args.pop('file').read_text())
                args[{'plan':'plan','review':'report','decision':'contents','reflect':'reflection','task-add':'task','coverage':'coverage','plan-details':'details'}[a.command]]=value
            for old,new in (('type','kind'),('check','checks'),('risk','risks'),('destination','destinations'),('artifact','artifacts')):
                if old in args: args[new]=args.pop(old)
            if 'progress' in args: args['progress']=args['progress']=='yes'
            result=mutate(a.repo_root,a.cycle,a.command,**args)
        print(json.dumps({'ok':True,'cycle':result},indent=2)); return 0
    except (CycleError,BionicConfigError,ValueError,OSError,KeyError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)})); return 1

if __name__=='__main__': sys.exit(main())
