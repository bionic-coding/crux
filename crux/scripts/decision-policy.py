#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Propose and accept ADRs under the prospective council/human policy.

`owner-decision present|capture|apply --json REQUEST` retains the owner's explicit answer to an exact ADR
acceptance. REQUEST is inline JSON, `-` for standard input, or `@PATH` for a file inside the repository.
It prints one JSON result and exits 0 when the step succeeded, 1 when it was refused (the refusal code and
its detail are in `error`), and 2 when REQUEST could not be read.
"""
import argparse
import json
from pathlib import Path
import sys
from decision_policy import propose, accept, adopt


class RequestUnreadable(Exception):
    """The `--json` value names a file or stream that cannot be read: an environment error, not a refusal."""


def read_request(repo_root, value):
    """The JSON text `--json` names: standard input for `-`, a file inside the repository for `@PATH`, else the value."""
    if value == '-':
        try:
            return sys.stdin.read()
        except OSError as exc:
            raise RequestUnreadable(f'--json -: cannot read standard input: {type(exc).__name__}') from exc
    if not value.startswith('@'):
        return value
    name = value[1:]
    if not name:
        raise RequestUnreadable('--json @PATH needs a path after the @')
    root = Path(repo_root).resolve()
    path = Path(name)
    target = (path if path.is_absolute() else root / path).resolve()
    if not target.is_relative_to(root):
        raise RequestUnreadable(f'--json @{name} resolves to {target}, outside the repository root {root}')
    if not target.is_file():
        raise RequestUnreadable(f'--json @{name}: no file at {target}')
    try:
        return target.read_text()
    except OSError as exc:
        raise RequestUnreadable(f'--json @{name}: cannot read {target}: {type(exc).__name__}') from exc


def owner_decision_command(args):
    """Run one owner-decision step and return (exit code, printable document)."""
    import owner_decision
    try:
        request = json.loads(read_request(args.repo_root, args.request))
    except RequestUnreadable as exc:
        return 2, {'ok': False, 'error': str(exc)}
    except ValueError:
        return 1, {'ok': False, 'error': {'code': 'invalid-request-json', 'expected': 'one JSON object'}}
    try:
        report = getattr(owner_decision, args.owner_action)(args.repo_root, request)
    except owner_decision.OwnerDecisionError as exc:
        return 1, {'ok': False, 'error': {'code': exc.code, **exc.detail}}
    except OSError as exc:
        return 2, {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
    except (ValueError, KeyError) as exc:
        return 1, {'ok': False, 'error': str(exc)}
    return 0, {'ok': True, **report}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('--repo-root',default='.')
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('propose');s.add_argument('--file',type=Path,required=True);s.add_argument('--origin',choices=['direct','whiteboard','inbox','cycle'],required=True);s.add_argument('--cycle',help='the lightweight cycle record a cycle-origin ADR names; it is planning, working or reviewing');s.add_argument('--creation-approval',help='retired: refuses with a retirement message');s.add_argument('--creation-subject',help='retired: refuses with a retirement message')
    s=sub.add_parser('adopt',help='write proposal metadata (origin legacy-adoption) for a HEAD-tracked legacy Proposed ADR; grants no approval');s.add_argument('--subject',required=True,help='the ADR path relative to the docs root')
    s=sub.add_parser('accept');s.add_argument('--subject',required=True);s.add_argument('--approval',required=True);s.add_argument('--human-approval')
    s=sub.add_parser('owner-decision',help="retain a shown ADR and the owner's explicit answer: present, then capture, then apply with the council approval")
    owner=s.add_subparsers(dest='owner_action',required=True)
    for action,about in (('present','record the exact ADR bytes shown to the owner and the question asked'),
                         ('capture','record the owner\'s verbatim answer, its source and date, against a presentation'),
                         ('apply','accept the ADR from a current approving capture and the council approval of the same bytes')):
        form=owner.add_parser(action,help=about)
        form.add_argument('--json',dest='request',required=True,metavar='REQUEST',help='one JSON request: inline, - for standard input, or @PATH inside the repository')
    a=p.parse_args(argv)
    if a.command=='owner-decision':
        code,document=owner_decision_command(a)
        print(json.dumps(document,indent=2));return code
    try:
        if a.command=='propose':result=propose(a.repo_root,json.loads(a.file.read_text()),origin=a.origin,cycle_id=a.cycle,creation_approval=a.creation_approval,creation_subject=a.creation_subject)
        elif a.command=='adopt':result=adopt(a.repo_root,a.subject)
        else:result=accept(a.repo_root,a.subject,a.approval,human_approval=a.human_approval)
        print(json.dumps({'ok':True,**result},indent=2));return 0
    except (ValueError,OSError,KeyError) as exc:
        print(json.dumps({'ok':False,'error':str(exc),**({'code':exc.code} if hasattr(exc,'code') else {})}));return 1

if __name__=='__main__':sys.exit(main())
