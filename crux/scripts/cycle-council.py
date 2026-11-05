#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "httpx>=0.27"]
# ///
"""Convene configured council seats for one exact cycle or standalone ADR subject."""
import argparse
import json
import sys
from pathlib import Path
from cycle_council import PURPOSES, convene, recover, launch_detached, notify_runner, await_attempt, probe_attempt
from bionic_config import BionicConfigError


def positive_int(value):
    try:
        parsed=int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('must be a positive integer') from exc
    if parsed<=0:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return parsed


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',default='.')
    p.add_argument('--cycle'); p.add_argument('--purpose',choices=PURPOSES)
    p.add_argument('--subject'); p.add_argument('--question',type=Path)
    p.add_argument('--progress'); p.add_argument('--human-approval'); p.add_argument('--recover')
    p.add_argument('--probe',help='docs-relative attempt: report its flock and holder without writing')
    p.add_argument('--await',dest='await_path',help='docs-relative attempt: await its outcome within a window')
    p.add_argument('--timeout',type=float,default=1800)
    p.add_argument('--foreground',action='store_true',help='run synchronously for diagnostics; default convening is detached')
    p.add_argument('--_runner-fd',type=int,help=argparse.SUPPRESS)
    p.add_argument('--_launch-id',help=argparse.SUPPRESS)
    p.add_argument('--identity',help='stable consultation or ADR-creation identity')
    p.add_argument('--extension',type=positive_int,help='owner-recorded higher attempt limit')
    p.add_argument('--initialize-council',choices=('lite','standard','strict'))
    p.add_argument('--selection',help='explicit setup choice provenance')
    p.add_argument('--record-policy',help='new council policy instruction slug')
    p.add_argument('--owner-instruction',help='repository-relative owner conversation JSON')
    p.add_argument('--policy-action',default='select-council-mode',choices=('select-council-mode','extend-council-limit'))
    p.add_argument('--architect',type=Path,metavar='PATH',help='PATH to a JSON file holding the exact-revision architect agreement and typed dissent')
    p.add_argument('--record',help='docs-relative council result for architect disposition')
    p.add_argument('--prepare-pass',choices=('challenge','final'))
    p.add_argument('--native-attempt',help='docs-relative prepared native attempt')
    p.add_argument('--harness',choices=('codex','claude','opencode'))
    p.add_argument('--author-context',help='actual host proposal-author context')
    p.add_argument('--response',type=Path,help='architect response before final native pass')
    p.add_argument('--ingest-result',type=Path,help='unmodified host tool request/result/final envelope JSON')
    p.add_argument('--request',help='docs-relative sealed native request')
    p.add_argument('--readiness',type=Path,help='committed U1 source/test/review bindings for disposition purpose')
    p.add_argument('--max-tokens',type=positive_int,default=None,
                   help='first-attempt output token budget for every seat. Omitted: each seat derives its budget from its registry output limit (half the limit, at least 32000, at most the limit) and a truncated reply retries once at the seat limit. Given: refused above the smallest selected seat limit')
    a=p.parse_args(argv)
    runner_fd=a._runner_fd
    try:
        if a.initialize_council:
            from council_policy import initialize
            result=initialize(a.repo_root,a.initialize_council,selection=a.selection)
        elif a.record_policy:
            from council_policy import record_policy
            result=record_policy(a.repo_root,a.record_policy,a.owner_instruction,action=a.policy_action,
                                 logical_id=a.identity,limit=a.extension)
        elif a.architect:
            from council_policy import disposition
            result=disposition(a.repo_root,a.record,json.loads(a.architect.read_text()))
        elif a.prepare_pass:
            from council_native import prepare
            result=prepare(a.repo_root,a.purpose,a.subject,a.question.read_text() if a.question else '',
                phase=a.prepare_pass,attempt_path=a.native_attempt,harness=a.harness,author_context=a.author_context,
                response=a.response.read_text() if a.response else None,cycle_id=a.cycle,identity=a.identity,
                progress=a.progress,extension=a.extension,readiness=json.loads(a.readiness.read_text()) if a.readiness else None)
        elif a.ingest_result:
            from council_native import ingest
            result=ingest(a.repo_root,a.request,json.loads(a.ingest_result.read_text()))
        elif a.recover: result=recover(a.repo_root,a.recover)
        elif a.probe:result=probe_attempt(a.repo_root,a.probe)
        elif a.await_path:result=await_attempt(a.repo_root,a.await_path,a.timeout)
        else:
            if not all((a.purpose,a.subject,a.question)): p.error('--purpose, --subject and --question are required')
            if not a.foreground and runner_fd is None:
                result=launch_detached(a.repo_root,list(argv if argv is not None else sys.argv[1:]),
                                      purpose=a.purpose,subject=a.subject,cycle_id=a.cycle,identity=a.identity)
                print(json.dumps(result,indent=2));return 0 if result.get('outcome')=='running' else 1
            options={'readiness':json.loads(a.readiness.read_text())} if a.readiness else {}
            if a.identity is not None:options['identity']=a.identity
            if a.extension is not None:options['extension']=a.extension
            if runner_fd is not None:
                def on_claim(path,attempt):
                    nonlocal runner_fd
                    fd=runner_fd;runner_fd=None
                    notify_runner(fd,{'phase':'claimed','attempt':path,'id':attempt['id']})
                options.update(on_claim=on_claim,attempt_id=a._launch_id)
            result=convene(a.repo_root,a.purpose,a.subject,a.question.read_text(),cycle_id=a.cycle,progress=a.progress,human_approval=a.human_approval,max_tokens=a.max_tokens,**options)
        if runner_fd is not None:
            notify_runner(runner_fd,{'phase':'finished','result':result});runner_fd=None
        print(json.dumps(result,indent=2)); return 0 if result.get('outcome') in (None,'approved','running') else 1
    except (ValueError,OSError,BionicConfigError) as exc:
        result={'ok':False,'error':str(exc)}
        if runner_fd is not None:notify_runner(runner_fd,{'phase':'finished','result':result})
        print(json.dumps(result));return 1

if __name__=='__main__':sys.exit(main())
