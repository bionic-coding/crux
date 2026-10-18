#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27", "pyyaml>=6.0"]
# ///
# Publication preparation reaches httpx through the summaries survey reader.
# Declare it here so the installed CLI also works outside the project venv.
"""Prepare non-authoritative ADR migrations; validate exact approvals and candidates."""
import argparse
import json
from pathlib import Path
import sys
import adr_migration as migration


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['queue-create','queue-show','queue-resume','queue-page','evidence','publication-stage','package','bundle','approval','approve','candidate','candidate-show','readiness','policy','queue-stop','queue-clear-stop','installed-support','accept-package','package-acceptance'])
    parser.add_argument('--repo-root', default='.')
    parser.add_argument('--path'); parser.add_argument('--id'); parser.add_argument('--input', type=Path)
    parser.add_argument('--package'); parser.add_argument('--council'); parser.add_argument('--approval')
    parser.add_argument('--readiness', type=Path); parser.add_argument('--owner', type=Path)
    parser.add_argument('--owner-exception',help='exact scoped initial-migration provenance; changes no default policy')
    parser.add_argument('--policy',choices=sorted(migration.POLICIES))
    parser.add_argument('--size',type=int,default=5);parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--scope',type=Path,help='reviewed initial transition path list; later publications cannot widen scope')
    parser.add_argument('--pending', action='store_true', help='validate a receipt before its commit; grants no authority')
    args = parser.parse_args(argv)
    try:
        with migration.owner_exception_scope(args.repo_root,args.owner_exception):
            def require(*names):
                if any(getattr(args,n) is None for n in names):raise ValueError('missing required argument: '+', '.join(names))
            def data(path):return json.loads(path.read_text())
            if args.command=='queue-page':
                require('path');result=migration.queue_page(args.repo_root,args.path,size=args.size,offset=args.offset)
            elif args.command=='evidence':
                require('path');result=migration.render_evidence(args.repo_root,args.path)
            elif args.command=='publication-stage':
                require('path','input')
                from adr_migration_publication import stage_transaction
                supplied=data(args.input)
                changes={p:migration.read(args.repo_root,source) if source is not None else None for p,source in supplied.items()}
                result=stage_transaction(args.repo_root,args.path,changes,initial_scope=data(args.scope) if args.scope else None)
            elif args.command=='queue-create':
                require('id','input'); result=migration.create_queue(args.repo_root,args.id,data(args.input)['items'],owner_stops=data(args.input).get('owner_stops'))
            elif args.command=='queue-stop':
                require('path','input'); result=migration.queue_stop(args.repo_root,args.path,data(args.input))
            elif args.command=='queue-clear-stop':
                require('path','id','owner'); result=migration.clear_queue_stop(args.repo_root,args.path,args.id,data(args.owner))
            elif args.command=='installed-support':
                result=migration.installed_support()
            elif args.command in ('queue-show','queue-resume'):
                require('path'); result=(migration.load_queue if args.command=='queue-show' else migration.resume_queue)(args.repo_root,args.path)
            elif args.command in ('package','bundle'):
                require('path'); result=(migration.candidate_facts if args.command=='package' else migration.review_bundle)(args.repo_root,args.path)
            elif args.command=='policy':
                require('id','policy','owner'); result=migration.record_policy(args.repo_root,args.id,args.policy,data(args.owner))
            elif args.command=='accept-package':
                require('package','council'); result=migration.accept_package(args.repo_root,args.package,args.council,owner=data(args.owner) if args.owner else None)
            elif args.command=='package-acceptance':
                require('package'); result=migration.validate_package_acceptance(args.repo_root,args.package,committed=not args.pending)
            elif args.command=='approval':
                require('path'); result=migration.validate_approval(args.repo_root,args.path,committed=not args.pending)
            elif args.command=='approve':
                require('id','package','council','readiness'); result=migration.record_approval(args.repo_root,args.id,args.package,args.council,data(args.readiness),owner=data(args.owner) if args.owner else None)
            elif args.command=='candidate':
                require('id','package','approval'); result=migration.write_candidate(args.repo_root,args.id,args.package,args.approval)
            elif args.command=='candidate-show':
                require('path'); result=migration.validate_candidate(args.repo_root,args.path)
            elif args.command=='readiness':
                require('readiness'); result=migration.validate_readiness(args.repo_root,data(args.readiness))
            print(json.dumps(result,indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)}));return 1

if __name__=='__main__':sys.exit(main())
