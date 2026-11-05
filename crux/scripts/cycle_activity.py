"""The last activity of a cycle and of each of its open attempts, derived read-only.

`activity(repo_root, doc, now)` is the one entry point. It reads data the record and git
already hold and writes nothing: no heartbeat, no record field, no agent step.

Sources, each an event `{'source', 'at_s', 'age_s', 'detail'}`:
- `record-write`: the record's `updated_at`.
- `last-seen`: an open attempt's `last_seen`.
- `commit`: a commit made after the attempt started whose `Cycle-Task` trailer names the
  attempt's task (any ref, so a commit on a worktree branch counts).
- `result-file`: the modification time of the attempt's result file, when written after it started.
- `worktree-change`: the newest modification time among the uncommitted changes of a linked
  worktree created after the attempt started.

An attempt's last activity is its newest event; the cycle's is the newest of its record write and
every open attempt's. A cycle with no open attempt is `idle`. Activity age is not liveness and is
never loss evidence: liveness stays `unknown`.

Cost is bounded. Git runs only when an attempt is open: one `git log` (at most COMMIT_LIMIT commits
since the earliest open attempt started), one `git worktree list`, and one `git status` per linked
worktree created after that start (at most WORKTREE_LIMIT, each read to at most CHANGE_LIMIT
entries). A failed or missing git yields no git events; it never raises.

A worktree change belongs to one attempt: the open attempt that started last before the worktree was
created, since a dispatch reserves its attempt just before the host creates the worktree. Known limit:
nothing records which attempt made a worktree, so when several attempts are reserved before their
worktrees are created (parallel dispatch in one turn), every such worktree goes to the last of them.
"""
from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

OPEN_STATES = ('reserved', 'running')
SOURCES = ('record-write', 'last-seen', 'commit', 'result-file', 'worktree-change')
COMMIT_LIMIT = 500
WORKTREE_LIMIT = 20
CHANGE_LIMIT = 200
GIT_TIMEOUT = 10
DETAIL_LIMIT = 120


def _epoch(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None


def _event(source, at, now, detail=None):
    return {'source': source, 'at_s': int(at), 'age_s': max(0, int(now - at)),
            'detail': None if detail is None else str(detail)[:DETAIL_LIMIT]}


def _newest(events):
    events = [e for e in events if e is not None]
    return max(events, key=lambda e: e['at_s']) if events else None


def _git(repo_root, *argv):
    try:
        done = subprocess.run(['git', *argv], cwd=repo_root, capture_output=True, text=True, timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def trailer_commits(repo_root, since):
    """[(sha, commit time, [Cycle-Task values])] for commits on any ref since `since`, newest first."""
    out = _git(repo_root, 'log', '--all', f'--since=@{int(since)}', f'--max-count={COMMIT_LIMIT}',
               '--format=%H%x1f%ct%x1f%(trailers:key=Cycle-Task,valueonly,separator=%x1d)%x1e')
    rows = []
    for chunk in (out or '').split('\x1e'):
        parts = chunk.strip('\n').split('\x1f')
        if len(parts) != 3 or not parts[1].isdigit():
            continue
        rows.append((parts[0], int(parts[1]), [t.strip() for t in parts[2].split('\x1d') if t.strip()]))
    return rows


def _admin_dir(worktree):
    """The worktree's administrative directory under the common git dir, from its `.git` file."""
    try:
        text = (worktree / '.git').read_text(encoding='utf-8').strip()
    except OSError:
        return None
    if not text.startswith('gitdir:'):
        return None
    path = Path(text[len('gitdir:'):].strip())
    return path if path.is_absolute() else worktree / path


def _created(worktree):
    """When a linked worktree was created: its admin `commondir` file, written once by `git worktree add`."""
    admin = _admin_dir(worktree)
    for name in ('commondir', 'gitdir'):
        try:
            return (admin / name).stat().st_mtime if admin else None
        except OSError:
            continue
    return None


def linked_worktrees(repo_root):
    """[(path, created)] for every linked worktree (the main one excluded) whose creation time is readable."""
    out = _git(repo_root, 'worktree', 'list', '--porcelain')
    paths = [Path(line[len('worktree '):]) for line in (out or '').splitlines() if line.startswith('worktree ')]
    rows = []
    for path in paths[1:]:
        created = _created(path)
        if created is not None:
            rows.append((path, created))
    return rows


def last_change(worktree):
    """The newest modification time among a worktree's uncommitted changes, or None when it is clean."""
    out = _git(worktree, 'status', '--porcelain=v1', '-z', '--untracked-files=normal')
    if not out:
        return None
    newest = None
    entries = out.split('\0')
    skip = False
    for n, entry in enumerate(entries):
        if n >= CHANGE_LIMIT:
            break
        if skip:
            skip = False
            continue
        if len(entry) < 4:
            continue
        # A rename or copy entry is followed by its source path, which carries no change time of its own.
        skip = entry[0] in 'RC'
        try:
            mtime = os.lstat(worktree / entry[3:]).st_mtime
        except OSError:
            continue
        newest = mtime if newest is None else max(newest, mtime)
    return newest


def activity(repo_root, doc, now=None):
    """The cycle's activity: {'state', 'last', 'attempts'}.

    `state` is 'idle' with no open attempt and 'attempts-open' otherwise. `last` is the newest event.
    `attempts` lists each open attempt in record order as {'id', 'task', 'attempt', 'last'}."""
    now = time.time() if now is None else now
    record = _epoch(doc.get('updated_at'))
    record_event = _event('record-write', record, now) if record is not None else None
    open_rows = [a for a in doc.get('assignments', []) if isinstance(a, dict) and a.get('state') in OPEN_STATES]
    starts = [s for s in (_epoch(a.get('started_at')) for a in open_rows) if s is not None]
    commits, worktrees = [], []
    if starts:
        earliest = min(starts)
        commits = trailer_commits(repo_root, earliest)
        candidates = sorted((w for w in linked_worktrees(repo_root) if w[1] >= earliest), key=lambda w: -w[1])[:WORKTREE_LIMIT]
        worktrees = [(path, created, last_change(path)) for path, created in candidates]
    # Each worktree belongs to the open attempt that started last before it was created.
    owner = {}
    for n, (path, created, changed) in enumerate(worktrees):
        before = [(s, i) for i, s in enumerate(_epoch(a.get('started_at')) for a in open_rows) if s is not None and s <= created]
        if before and changed is not None:
            owner.setdefault(max(before)[1], []).append(_event('worktree-change', changed, now, path.name))
    attempts = []
    for index, a in enumerate(open_rows):
        start = _epoch(a.get('started_at'))
        seen = _epoch(a.get('last_seen'))
        events = [_event('last-seen', seen, now) if seen is not None else None]
        if start is not None:
            task = a.get('task')
            events += [_event('commit', ct, now, sha[:12]) for sha, ct, tasks in commits if task and task in tasks and ct >= start][:1]
            result = a.get('result_path')
            if isinstance(result, str) and result:
                try:
                    mtime = Path(result).stat().st_mtime
                    if mtime >= start:
                        events.append(_event('result-file', mtime, now, Path(result).name))
                except OSError:
                    pass
            events += owner.get(index, [])
        attempts.append({'id': a.get('id'), 'task': a.get('task'), 'attempt': a.get('attempt'), 'last': _newest(events)})
    last = _newest([record_event, *(r['last'] for r in attempts)])
    return {'state': 'attempts-open' if open_rows else 'idle', 'last': last, 'attempts': attempts}


def age(seconds):
    """A short age: 45s, 12m, 3h05m, 2d04h."""
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f'{seconds}s'
    minutes = seconds // 60
    if minutes < 60:
        return f'{minutes}m'
    hours = minutes // 60
    if hours < 48:
        return f'{hours}h{minutes % 60:02d}m'
    return f'{hours // 24}d{hours % 24:02d}h'


def describe(event):
    """`12m ago (commit 1a2b3c4d5e6f)`, or `no activity recorded`."""
    if not event:
        return 'no activity recorded'
    detail = f" {event['detail']}" if event.get('detail') else ''
    return f"{age(event['age_s'])} ago ({event['source']}{detail})"


def summary_line(result):
    """The cycle's one-line activity text: `idle for 3h00m (record-write)` or `last activity 2m ago (commit ...)`."""
    last = result['last']
    if result['state'] == 'idle':
        return f"idle for {age(last['age_s'])} ({last['source']})" if last else 'idle, no activity recorded'
    return 'last activity ' + describe(last)
