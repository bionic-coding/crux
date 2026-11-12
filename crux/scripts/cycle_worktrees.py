"""Remove a finishing cycle's own merged, clean agent worktrees; list every other linked worktree.

`cleanup(repo_root, task_ids)` is the one entry point; `finish` calls it after the record is saved.
It removes a linked worktree only when all of these hold:

- its path lies under `<repo_root>/.claude/worktrees/`;
- it has a branch (a detached worktree has no branch to delete) and is not locked;
- its branch tip carries a `Cycle-Task:` trailer naming one of `task_ids`;
- its branch tip is an ancestor of HEAD;
- its tree is clean, untracked files included.

Removal is `git worktree remove <path>` and then `git branch -d <branch>`, never `--force` or `-D`, so
git refuses anything the checks above missed. Every other linked worktree is returned under `kept` with
the first reason it failed, and is left in place. A git failure keeps the worktree; nothing raises.

Cleanup runs after finish saves its completed state. Open attempts of any remaining active or
paused cycle protect a worktree by its tip's task trailer or their recorded result_path. This is
recorded ownership, never an inference from elapsed time, pid or a worktree's creation time.
"""
from __future__ import annotations

from pathlib import Path
import json
import subprocess

AGENT_DIR = Path('.claude') / 'worktrees'
GIT_TIMEOUT = 30


def _git(cwd, *argv):
    """(returncode, stdout, stderr); returncode None when git could not run."""
    try:
        done = subprocess.run(['git', *argv], cwd=cwd, capture_output=True, text=True, timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, '', str(exc)
    return done.returncode, done.stdout, done.stderr


def linked(repo_root):
    """Every linked worktree, the main one excluded: [{'path', 'head', 'branch', 'locked'}]."""
    code, out, _ = _git(repo_root, 'worktree', 'list', '--porcelain')
    if code != 0:
        return []
    rows, row = [], None
    for line in out.splitlines() + ['']:
        if line.startswith('worktree '):
            row = {'path': line[len('worktree '):], 'head': None, 'branch': None, 'locked': False}
        elif row is None:
            continue
        elif line.startswith('HEAD '):
            row['head'] = line[len('HEAD '):]
        elif line.startswith('branch '):
            row['branch'] = line[len('branch '):]
        elif line == 'locked' or line.startswith('locked '):
            row['locked'] = True
        elif line == '':
            rows.append(row)
            row = None
    return rows[1:]


def _trailers(repo_root, commit):
    code, out, _ = _git(repo_root, 'log', '-1', '--format=%(trailers:key=Cycle-Task,valueonly,separator=%x1d)', commit)
    return [t.strip() for t in out.strip().split('\x1d') if t.strip()] if code == 0 else []


def _inside(path, directory):
    try:
        resolved = Path(path).resolve()
        return resolved != directory and resolved.is_relative_to(directory)
    except (OSError, ValueError):
        return False


def open_owners(repo_root):
    """Recorded attempts of unfinished cycles, plus any records whose ownership could not be read."""
    from cycle_workflow import tree
    from bionic_config import BionicConfigError
    owners,problems=[],[]
    try:cfg=tree(repo_root)
    except (OSError,ValueError,BionicConfigError) as exc:return [],[f'ownership unavailable: {type(exc).__name__} reading project configuration']
    root=cfg.docs_root.resolve()
    for path in sorted((root/'cycles').glob('*/cycle.json')):
        label=path.relative_to(root).as_posix()
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('ownership record is a symlink or outside the tree')
            doc=json.loads(path.read_text())
            if not isinstance(doc,dict):raise ValueError('ownership record is not an object')
            if doc.get('status') in {'completed','abandoned','shortcut'}:continue
            if doc.get('status') not in {'active','paused'} or not isinstance(doc.get('assignments',[]),list):
                raise ValueError('ownership state is unknown')
            for entry in doc.get('assignments',[]):
                if not isinstance(entry,dict):raise ValueError('attempt ownership is not an object')
                if entry.get('state') not in {'reserved','running','finished','lost'}:raise ValueError('attempt state is unknown')
                if entry['state'] in {'reserved','running'}:
                    owners.append({'cycle':doc.get('id',path.parent.name),'assignment':entry.get('id','unknown'),
                                   'task':entry.get('task'),'result_path':entry.get('result_path')})
        except (OSError,ValueError,RuntimeError) as exc:
            problems.append(f'ownership unavailable: {label} ({type(exc).__name__})')
    return owners,problems


def ownership_reason(repo_root,row,tip_tasks,owners,problems):
    if problems:return '; '.join(problems)
    worktree=Path(row['path']).resolve()
    for owner in owners:
        label=f"open attempt {owner['cycle']}/{owner['assignment']}"
        if owner['task'] and owner['task'] in tip_tasks:
            return f"held by {label}: branch tip names its task {owner['task']}"
        result=owner['result_path']
        if isinstance(result,str) and result:
            try:
                path=Path(result)
                path=(path if path.is_absolute() else Path(repo_root)/path).resolve()
                if path==worktree or path.is_relative_to(worktree):
                    return f'held by {label}: recorded result_path {result} lies in this worktree'
            except (OSError,RuntimeError,ValueError):
                return f'ownership unavailable: {label} has an unreadable result_path'
    return None


def verdict(repo_root, row, task_ids, agent_dir, owners=(), ownership_problems=()):
    """(task, None) when the worktree is the cycle's to remove, else (None, the reason it is kept)."""
    if not _inside(row['path'], agent_dir):
        return None, f'not under {AGENT_DIR.as_posix()}'
    if not row['branch'] or not row['head']:
        return None, 'detached: no branch'
    if row['locked']:
        return None, 'locked'
    tip_tasks=_trailers(repo_root,row['head'])
    if reason:=ownership_reason(repo_root,row,tip_tasks,owners,ownership_problems):
        return None,reason
    named = [t for t in tip_tasks if t in task_ids]
    if not named:
        return None, "branch tip carries no Cycle-Task trailer naming this cycle's tasks"
    code, _, _ = _git(repo_root, 'merge-base', '--is-ancestor', row['head'], 'HEAD')
    if code != 0:
        return None, 'not merged: branch tip is not an ancestor of HEAD'
    code, out, _ = _git(row['path'], 'status', '--porcelain=v1', '--untracked-files=all')
    if code != 0:
        return None, 'unreadable: git status failed'
    if out.strip():
        return None, 'dirty: uncommitted or untracked changes'
    return named[0], None


def cleanup(repo_root, task_ids):
    """{'removed': [{'path', 'branch', 'task'}], 'kept': [{'path', 'branch', 'reason'}]}."""
    repo_root = Path(repo_root)
    agent_dir = (repo_root / AGENT_DIR).resolve()
    task_ids = set(task_ids)
    removed, kept = [], []
    rows=linked(repo_root)
    owners,problems=open_owners(repo_root) if rows else ([],[])
    for row in rows:
        branch = row['branch'][len('refs/heads/'):] if (row['branch'] or '').startswith('refs/heads/') else row['branch']
        task, reason = verdict(repo_root, row, task_ids, agent_dir, owners, problems)
        if reason is None:
            code, _, err = _git(repo_root, 'worktree', 'remove', row['path'])
            if code != 0:
                reason = 'git worktree remove refused: ' + (err.strip().splitlines() or ['no message'])[-1]
        if reason is not None:
            kept.append({'path': row['path'], 'branch': branch, 'reason': reason})
            continue
        entry = {'path': row['path'], 'branch': branch, 'task': task}
        code, _, err = _git(repo_root, 'branch', '-d', branch)
        if code != 0:
            entry['branch_kept'] = 'git branch -d refused: ' + (err.strip().splitlines() or ['no message'])[-1]
        removed.append(entry)
    return {'removed': removed, 'kept': kept}
