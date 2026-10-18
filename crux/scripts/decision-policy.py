#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Propose and accept ADRs under the prospective council/human policy."""
import argparse
import json
from pathlib import Path
import sys
from decision_policy import propose, accept


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo-root',default='.')
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('propose');s.add_argument('--file',type=Path,required=True);s.add_argument('--origin',choices=['direct','whiteboard','inbox','cycle'],required=True);s.add_argument('--cycle');s.add_argument('--creation-approval');s.add_argument('--creation-subject')
    s=sub.add_parser('accept');s.add_argument('--subject',required=True);s.add_argument('--approval',required=True);s.add_argument('--human-approval')
    a=p.parse_args(argv)
    try:
        if a.command=='propose':result=propose(a.repo_root,json.loads(a.file.read_text()),origin=a.origin,cycle_id=a.cycle,creation_approval=a.creation_approval,creation_subject=a.creation_subject)
        else:result=accept(a.repo_root,a.subject,a.approval,human_approval=a.human_approval)
        print(json.dumps({'ok':True,**result},indent=2));return 0
    except (ValueError,OSError,KeyError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)}));return 1

if __name__=='__main__':sys.exit(main())
