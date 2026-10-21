#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27", "pyyaml>=6.0"]
# ///
# Replaying a publication reaches httpx through the summaries survey reader.
# Declare it here so the installed CLI also works outside the project venv.
"""Write and verify committed replay receipts for prospective migration publications.

`write` replays one committed publication with every receipt lookup disabled and, only on
success, writes `<docs_dir>/adrs/migrations/receipts/<publication-id>.json`. It commits
nothing. `verify` replays each receipt in its scope the same way, with lookups disabled,
and reports a receipt that is invalid, orphaned, untrusted, mismatched or absent from the
replay's result. Neither command ever records a refusal.

Exit codes: 0 clean, 1 refusal or findings (JSON on stdout), 2 environment or usage error.
"""
import argparse
import json
import os
from pathlib import Path
import sys

import adr_migration as m
import migration_receipts as receipts
from council_records import git
from cycle_workflow import CycleError, atomic_bytes, contained, encoded


class UsageError(Exception):
    """A malformed command line or an unusable anchor: exit 2, never a silent narrowing."""


def _row(repo, publication):
    """The committed prospective inventory row for a repository-relative publication path."""
    import adr_migration_publication as publications
    wanted = Path(publication).as_posix()
    for row in publications.inventory(repo):
        if row['path'] == wanted:
            return row
    raise CycleError('publication is not a committed prospective publication: ' + wanted)


def replay(repo, row):
    """Run the full admission with every receipt ignored; return the receipt it proves."""
    import adr_migration_publication as publications
    identity = json.loads(row['content'])['id']
    with receipts.disabled(), receipts.recording() as ran:
        publications.publication_facts(repo, row)
    if identity not in ran:
        raise CycleError('the parent reader did not run for ' + identity)
    return receipts.build(ran[identity])


def write(repo, publication):
    repo = Path(repo).resolve()
    row = _row(repo, publication)
    expected = replay(repo, row)
    relative = receipts.receipt_path(repo, expected['publication']['id'])
    target = contained(repo, relative)
    raw = encoded(expected)
    if os.path.lexists(target):
        if m.read(repo, relative) != raw:
            raise CycleError('a receipt with other bytes exists; delete it in a reviewed commit and rerun write')
        return {'status': 'unchanged', 'changed': False, 'path': relative, 'publication': expected['publication']['id']}
    atomic_bytes(target, raw)
    return {'status': 'written', 'changed': True, 'path': relative, 'publication': expected['publication']['id']}


def _object(repo, revision, relative):
    """Git object id of a path at a revision, or None when the path is absent."""
    found = git(repo, 'rev-parse', '--verify', '--quiet', revision + ':' + relative)
    return found.stdout.decode().strip() if found.returncode == 0 else None


def _anchor(repo, since):
    """Refuse an anchor that is not a full commit of this object store and an ancestor of HEAD."""
    try:
        m.full_commit(repo, since)
        m.ancestor(repo, since, m._git(repo, 'rev-parse', 'HEAD').decode().strip())
    except CycleError as error:
        raise UsageError('--since must name a full commit that is an ancestor of HEAD: ' + str(error)) from None
    return since


def _names(repo):
    """Receipt file names committed at HEAD or present in the working tree."""
    directory = receipts.receipts_directory(repo)
    names = set()
    listed = git(repo, 'ls-tree', '--name-only', 'HEAD', '--', directory + '/')
    if listed.returncode == 0:
        names.update(Path(line).name for line in listed.stdout.decode().splitlines() if line)
    folder = Path(repo) / directory
    if os.path.lexists(folder):
        # `contained` refuses a symlink at the directory or at any ancestor up to the root.
        contained(Path(repo).resolve(), directory)
        if not folder.is_dir():
            raise CycleError('receipts directory is not a regular directory: ' + directory)
        names.update(entry.name for entry in folder.iterdir())
    return sorted(names), directory


def verify(repo, since=None):
    repo = Path(repo).resolve()
    if since is not None:
        since = _anchor(repo, since)
    names, directory = _names(repo)
    import adr_migration_publication as publications
    rows = {json.loads(row['content'])['id']: row for row in publications.inventory(repo)}
    findings, checked = [], []

    def found(name, error):
        findings.append({'receipt': directory + '/' + name, 'error': error})

    for name in names:
        relative = directory + '/' + name
        current = _object(repo, 'HEAD', relative)
        if since is not None and current is not None and current == _object(repo, since, relative) \
                and not git(repo, 'status', '--porcelain', '--', relative).stdout.strip():
            continue  # byte-identical to the anchor and unmodified in the working tree
        checked.append(name)
        publication_id = name.removesuffix('.json')
        if not name.endswith('.json') or not m.SLUG.fullmatch(publication_id):
            found(name, 'unexpected entry in the receipts directory')
            continue
        try:
            raw, receipt = receipts.read_receipt(repo, relative) or (None, None)
        except CycleError as error:
            found(name, str(error))
            continue
        if receipt is None:
            found(name, 'receipt is committed at HEAD but missing from the working tree')
            continue
        row = rows.get(publication_id)
        if row is None or receipt['publication']['id'] != publication_id:
            found(name, 'orphan receipt: no committed prospective publication has this id')
            continue
        try:
            standing = receipts.trust(repo, relative, receipt)
        except CycleError as error:
            found(name, str(error))
            continue
        if standing != 'trusted':
            found(name, 'receipt is uncommitted or was edited after its introducing commit')
            continue
        try:
            expected = replay(repo, row)
        except CycleError as error:
            found(name, 'replay refused: ' + str(error))
            continue
        if expected != receipt:
            differing = sorted(key for key in expected if expected[key] != receipt.get(key))
            found(name, receipts.MISMATCH + ': ' + ', '.join(differing))
        elif encoded(expected) != raw:
            found(name, 'receipt bytes are not the canonical encoding')
    return {'status': 'findings' if findings else 'clean', 'checked': checked, 'findings': findings,
            'scope': 'all' if since is None else 'since ' + since}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['write', 'verify'])
    parser.add_argument('--repo-root', default='.')
    parser.add_argument('--publication', help='write: repository-relative path of a committed *.publication.json')
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument('--since', metavar='COMMIT', help='verify: receipts added or changed since this full commit')
    scope.add_argument('--all', action='store_true', help='verify: every receipt')
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_:
        return 2 if exit_.code else 0
    try:
        if args.command == 'write':
            if not args.publication or args.since or args.all:
                raise UsageError('write requires --publication and takes no verify scope')
            result = write(args.repo_root, args.publication)
        else:
            if args.publication or not (args.since or args.all):
                raise UsageError('verify requires exactly one of --since COMMIT or --all')
            result = verify(args.repo_root, args.since)
    except UsageError as error:
        print(str(error), file=sys.stderr)
        return 2
    except CycleError as error:
        print(json.dumps({'status': 'refused', 'error': str(error)}, sort_keys=True, indent=2))
        return 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'receipt tooling unavailable: {type(error).__name__}: {error}', file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 1 if result['status'] == 'findings' else 0


if __name__ == '__main__':
    sys.exit(main())
