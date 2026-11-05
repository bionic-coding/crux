"""Commit the cycle record: the cycle writer's own checkpoint commit.

After a phase-changing advance, a pause, a finish or an owner-exception, after every dispatch and
delivery operation (prepare-dispatch, attach-execution, deliver and mark-lost), and on the typed
`commit-record` operation, the writer commits `<docs>/cycles/<id>/` and nothing else. `queue start-next`
commits the cycle and queue together while holding the queue lock. The commit uses `git commit --only`, so source another role has staged
stays staged and out of the commit. Untracked files under the cycle directory are added first, by
exact path.

Queue writes commit the same way: `commit_queue` commits the queue and its history, with the
same deferral conditions, and `commit_paths` is the shared step both use.

`commit_record` never raises for a git condition. It reports, in the operation result:

    {"changed": bool, "commit": SHA|None, "paths": [...], "message": str|None, "deferred": REASON|None}

`deferred` names why no commit was made: ``not-a-git-repository``, ``operation-in-progress`` (merge,
rebase, cherry-pick or revert), ``index-locked``, ``full-suite-running`` or ``commit-failed``. A
deferral is not a failure: the record stays on disk and the next `commit-record` commits it. A repeat
with nothing to commit is a no-op (``changed`` false, no ``deferred``).

The full-suite lock is `<git-common-dir>/crux/full-suite.lock`, held by `tools/test-suite.py` for the
whole run. A direct `parallel_suite.py --shared-evidence` run of a registered checkout suite holds the
same lock while it executes, so this module detects it as well. A staged run and a focused run hold no
lock and are not detected.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import re
import subprocess

from cycle_workflow import contained, load, locked, tree

SUITE_LOCK = ('crux', 'full-suite.lock')
IN_PROGRESS = (('MERGE_HEAD', 'merge'), ('CHERRY_PICK_HEAD', 'cherry-pick'), ('REVERT_HEAD', 'revert'),
               ('rebase-merge', 'rebase'), ('rebase-apply', 'rebase'))
# Typed operations whose success is followed by a record commit.
# Dispatch and delivery operations commit too, so a record they dirty never waits for a later
# phase change (IDR lean-workflow-traps-and-recovery approach 1). A replay of any of them commits a
# record an interrupted run left pending, without applying the operation again.
COMMITTING = ('advance', 'finish', 'owner-exception', 'prepare-dispatch', 'attach-execution', 'deliver', 'mark-lost', 'execution-check', 'child-link', 'release-continue')
# The history actions whose commit message names the task and attempt.
ATTEMPT_ACTIONS = ('prepare-dispatch', 'attach-execution', 'deliver', 'mark-lost')
# Files a pending report lists before it says it is cut.
PENDING_SHOWN = 20
# Low-level commands whose success is followed by a record commit.
LOW_LEVEL_COMMITTING = ('advance', 'pause', 'owner-complete', 'abandon')


def git(root, *argv):
    done = subprocess.run(['git', '--no-optional-locks', '--literal-pathspecs', '-C', str(root), *argv], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def record_paths(cfg, cycle_id):
    """Ordinary cycle commits own only the cycle directory."""
    return [(cfg.docs_root / 'cycles' / cycle_id).relative_to(cfg.repo_root).as_posix()]


def queue_paths(cfg):
    """Queue writer paths, including history left pending by a deferred commit."""
    paths = []
    queue = contained(cfg.docs_root, 'queue/cycles.yaml')
    if queue.is_file() or queue.is_symlink():
        paths.append(queue.relative_to(cfg.repo_root).as_posix())
    history = contained(cfg.docs_root, 'queue/history/items')
    if history.is_dir():
        paths.extend(p.relative_to(cfg.repo_root).as_posix() for p in sorted(history.iterdir())
                     if re.fullmatch(r'Q-[0-9]{4,}\.json', p.name) and p.is_file() and not p.is_symlink())
    return paths


def pending_files(cfg, paths):
    """Changed or untracked files under `paths`, or None when this is not a git work tree."""
    code, out, _ = git(cfg.repo_root, 'status', '--porcelain', '--untracked-files=all', '--', *paths)
    if code != 0:
        return None
    return [line[3:] for line in out.splitlines() if line]


def suite_lock_state(cfg):
    """Read flock ownership and its diagnostic holder; a stale record is not a live process."""
    code,out,_=git(cfg.repo_root,'rev-parse','--path-format=absolute','--git-common-dir')
    if code!=0:return {'flock':'unavailable','holder':None,'path':None}
    path=Path(out.strip()).joinpath(*SUITE_LOCK)
    try:fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    except FileNotFoundError:return {'flock':'not-held','holder':None,'path':str(path)}
    except OSError:return {'flock':'unavailable','holder':None,'path':str(path)}
    try:
        try:fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB);state='not-held'
        except OSError:state='held'
        raw=os.pread(fd,4096,0).decode(errors='replace').strip()
        try:holder=json.loads(raw) if raw else None
        except ValueError:holder={'unparsed':raw}
        return {'flock':state,'holder':holder,'path':str(path)}
    finally:os.close(fd)


def suite_running(cfg):
    """True while a full suite holds `<git-common-dir>/crux/full-suite.lock`. Probes with a shared, non-blocking lock."""
    code, out, _ = git(cfg.repo_root, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if code != 0:
        return False
    lock = Path(out.strip()).joinpath(*SUITE_LOCK)
    try:
        fd = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    except OSError:
        return True
    finally:
        os.close(fd)
    return False


def deferral(cfg):
    """(reason, detail) when a commit must wait, else None."""
    code, out, _ = git(cfg.repo_root, 'rev-parse', '--absolute-git-dir')
    if code != 0:
        return 'not-a-git-repository', 'git cannot find a work tree here'
    git_dir = Path(out.strip())
    for name, kind in IN_PROGRESS:
        if (git_dir / name).exists():
            return 'operation-in-progress', f'a {kind} is in progress'
    if (git_dir / 'index.lock').exists():
        return 'index-locked', 'another git process holds the index lock'
    if suite_running(cfg):
        return 'full-suite-running', 'a full suite holds the full-suite lock'
    return None


def label_of(doc):
    """The event a commit message names, read from the newest history event."""
    last = doc['history'][-1]
    action = last['action']
    if action == 'advance':
        if 'from_phase' in last:
            return f"advance {last['from_phase']}->{last['to_phase']}" + (' (completed)' if doc['status'] == 'completed' else '')
        return 'advance -> ' + ('completed' if doc['status'] == 'completed' else doc['phase'])
    if action in ATTEMPT_ACTIONS and last.get('task'):
        return f"{action} {last['task']}" + (f" attempt {last['attempt']}" if last.get('attempt') else '')
    return action


def commit_paths(cfg, paths, message):
    """Commit `paths` alone with `git commit --only`, under the record commit's deferral conditions.

    `message` is a string or a callable that returns one; it is called only when there is something to commit.
    Returns the result described in the module docstring. The caller holds whatever lock guards `paths`."""
    base = {'changed': False, 'commit': None, 'paths': paths, 'message': None, 'deferred': None}
    files = pending_files(cfg, paths)
    if files is None:
        return {**base, 'deferred': 'not-a-git-repository', 'detail': 'git cannot find a work tree here'}
    if not files:
        return base
    found = deferral(cfg)
    if found:
        return {**base, 'deferred': found[0], 'detail': found[1], 'pending': files}
    text = message() if callable(message) else message
    code, _, err = git(cfg.repo_root, 'add', '--', *paths)
    if code == 0:
        code, _, err = git(cfg.repo_root, 'commit', '--only', '--no-verify', '-m', text, '--', *paths)
    if code != 0:
        return {**base, 'deferred': 'commit-failed', 'detail': err.strip()[:300], 'pending': files}
    _, head, _ = git(cfg.repo_root, 'rev-parse', 'HEAD')
    return {**base, 'changed': True, 'commit': head.strip(), 'message': text}


def commit_record(repo_root, cycle_id, label=None, include_queue=False):
    """Commit the cycle record now, under the cycle lock. Returns the result described in the module docstring."""
    with locked(repo_root) as (cfg, _):
        doc = load(repo_root, cycle_id)
        revision = doc.get('revision')
        paths = record_paths(cfg, cycle_id) + (queue_paths(cfg) if include_queue else [])
        return commit_paths(cfg, paths,
                            lambda: f"{cycle_id} record: {label or label_of(doc)}" + (f' (rev {revision})' if revision is not None else ''))


def commit_queue(cfg, label):
    """Commit the queue file alone after a queue write. The caller holds the queue lock.

    Same result and deferral conditions as `commit_record`; the message is `queue: <label>`."""
    paths = queue_paths(cfg)
    try:
        return commit_paths(cfg, paths, f'queue: {label}')
    except Exception as exc:  # the queue is already saved; the commit is the writer's follow-up
        return {'changed': False, 'commit': None, 'paths': paths, 'message': None, 'deferred': 'commit-error',
                'detail': f'{type(exc).__name__}: {exc}'[:300]}


def after_write(repo_root, cycle_id, label=None, include_queue=False):
    """`commit_record` for a writer that has just saved: any error becomes a deferral, never a failed operation."""
    try:
        result = commit_record(repo_root, cycle_id, label, include_queue=include_queue)
        # Never take the queue lock while the cycle lock is held. A joint start already
        # holds the queue lock, so only an ordinary terminal cycle triggers a sweep.
        if not include_queue and result.get('deferred') is None and load(repo_root, cycle_id)['status'] in ('completed', 'abandoned'):
            import cycle_queue
            try:
                cfg = tree(repo_root)
                if cycle_queue.read_queue(cfg)['format_version'] == 2:
                    result['queue_sweep'] = cycle_queue.archive(repo_root, only_if_items=True)
            except (cycle_queue.QueueError, OSError) as exc:
                result['queue_sweep'] = {'ok': False, 'error': str(exc)}
        return result
    except Exception as exc:  # the record is already saved; the commit is the writer's follow-up
        return {'changed': False, 'commit': None, 'paths': [], 'message': None, 'deferred': 'commit-error',
                'detail': f'{type(exc).__name__}: {exc}'[:300]}


def pending_record(repo_root, cycle_id):
    """What inspect reports: whether the record has uncommitted changes. Reads only."""
    cfg = tree(repo_root)
    files = pending_files(cfg, record_paths(cfg, cycle_id))
    if files is None:
        return {'git': False, 'pending': False, 'files': []}
    found = deferral(cfg) if files else None
    out = {'git': True, 'pending': bool(files), 'files': files[:PENDING_SHOWN], 'deferred': found[0] if found else None}
    _,git_dir,_=git(cfg.repo_root,'rev-parse','--absolute-git-dir')
    index=Path(git_dir.strip())/'index.lock'
    out['locks']={'full_suite':suite_lock_state(cfg),
                  'index':{'path':str(index),'state':'present-owner-unknown' if index.exists() else 'absent'}}
    if len(files) > PENDING_SHOWN:
        # A cut list says so and gives the count (approach 8).
        out.update(files_total=len(files), files_cut=True)
    return out
