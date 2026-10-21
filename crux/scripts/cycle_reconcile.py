"""Continuation handoff and evidence-only reconciliation of a cycle record.

Link rule: a commit belongs to a cycle when its subject begins with the cycle id
(for example `CYC-0014 U1: ...`) or it carries a `Cycle: <ID>` trailer line.
A commit links to a task through a `Cycle-Task: <task-id>` trailer line.
Reconcile proposes only what those commits and the repository establish. A commit
establishes implementation, so only build-phase tasks take proposals; a commit linked
to a test, review, release or reflect task is reported unresolved. It never records
tested or reviewed, never records review or evidence, never advances a phase, never
completes a cycle and never reads elapsed time. A missing result file is a
discrepancy only for a done task; an open task's result file is still expected.
"""
from __future__ import annotations

import re

from cycle_workflow import CLOSED, CycleError, load, mutate_tracked, on_head, resolve_commit, result_file, run_git, tree

ANY_CYCLE = re.compile(r'^((?:[A-Z][A-Z0-9]{1,9}-)?CYC-[0-9]{4,})(?![0-9A-Za-z-])')
TASK_TRAILER = re.compile(r'^Cycle-Task:[ \t]*(\S+)[ \t]*$', re.M)
CYCLE_TRAILER = re.compile(r'^Cycle:[ \t]*(\S+)[ \t]*$', re.M)


def handoff(repo, identity):
    """Read-only continuation summary of one cycle."""
    doc = load(repo, identity)
    tasks = doc['plan']['tasks']
    active = [t for t in tasks if t['status'] == 'active']
    pending = [t for t in tasks if t['status'] in ('pending', 'blocked')]
    out = {
        'cycle': doc['id'], 'title': doc['title'], 'type': doc['type'], 'phase': doc['phase'],
        'pass': doc['pass'], 'pass_limit': doc['pass_limit'], 'status': doc['status'],
        'blocker': doc['blocker'],
        'active': [{'id': t['id'], **{k: t[k] for k in ('assignee', 'result_path') if k in t}} for t in active],
        'delivered': [{'id': t['id'], **{k: t[k] for k in ('stage', 'commits') if k in t}} for t in tasks if t.get('stage') or t.get('commits')],
        'pending': [{'id': t['id'], 'phase': t['phase'], 'status': t['status']} for t in pending],
    }
    if doc['status'] in CLOSED:
        out['next_action'] = f"Cycle {doc['status']}; nothing remains to do"
    elif doc['status'] == 'paused':
        blocker = doc['blocker'] or {}
        out['next_action'] = f"Cycle paused: {blocker.get('reason', 'unknown blocker')}; {blocker.get('next_step', 'resolve the blocker, then resume')}"
    elif active:
        files = [t['result_path'] for t in active if t.get('result_path')]
        suffix = f" (result files {', '.join(files)})" if files else ''
        out['next_action'] = f"Collect results for active tasks {', '.join(t['id'] for t in active)}{suffix} and record delivery"
    else:
        unfinished = [t['id'] for t in pending if t['phase'] == doc['phase']]
        if unfinished:
            out['next_action'] = f"Start {doc['phase']} tasks {', '.join(unfinished)}"
        else:
            out['next_action'] = f"All {doc['phase']} tasks done; run advance"
    return out


def linked_commits(cfg, identity):
    """Map task id -> {'commits': [...], 'ambiguous': reason|None} from trailers across all refs."""
    code, out = run_git(cfg, 'log', '--all', '--format=%H%x1f%B%x1e')
    if code != 0:
        raise CycleError('cannot read commit history')
    links: dict[str, dict] = {}
    for record in out.split('\x1e'):
        if not record.strip():
            continue
        sha, _, body = record.strip().partition('\x1f')
        tasks = list(dict.fromkeys(TASK_TRAILER.findall(body)))
        if not tasks:
            continue
        subject = body.strip().splitlines()[0] if body.strip() else ''
        named = set(CYCLE_TRAILER.findall(body))
        if (match := ANY_CYCLE.match(subject)):
            named.add(match.group(1))
        if identity not in named:
            continue
        reason = None
        if len(named) > 1:
            reason = f'ambiguous: commit {sha[:12]} names more than one cycle'
        elif len(tasks) > 1:
            reason = f'ambiguous: commit {sha[:12]} names more than one task'
        for task in tasks:
            entry = links.setdefault(task, {'commits': [], 'ambiguous': None})
            entry['commits'].append(sha)
            entry['ambiguous'] = entry['ambiguous'] or reason
    return links


def worktrees(cfg):
    code, out = run_git(cfg, 'worktree', 'list', '--porcelain')
    found, current = [], {}
    for line in out.splitlines() + ['']:
        if not line:
            if current:
                found.append(current)
            current = {}
        elif ' ' in line:
            key, value = line.split(' ', 1)
            current[key] = value
    return found


def reconcile(repo, identity, apply=False):
    cfg = tree(repo)
    doc = load(repo, identity)
    links = linked_commits(cfg, identity)
    trees = worktrees(cfg)
    by_id = {t['id']: t for t in doc['plan']['tasks']}
    discrepancies, proposed, unresolved = [], [], []
    changes: dict[str, dict] = {}
    candidates: set[str] = set()

    def unresolve(task, reason):
        unresolved.append({'task': task, 'reason': reason})

    for task_id in sorted(set(links) - set(by_id)):
        unresolve(task_id, 'commit trailer names a task that is not in the plan')
    for task in doc['plan']['tasks']:
        tid = task['id']
        recorded = task.get('commits', [])
        link = links.get(tid, {'commits': [], 'ambiguous': None})
        dangling = [c for c in recorded if run_git(cfg, 'cat-file', '-e', f'{c}^{{commit}}')[0] != 0]
        if dangling:
            discrepancies.append({'task': tid, 'kind': 'recorded-commit-missing', 'commits': dangling})
            unresolve(tid, 'recorded commit ' + ', '.join(c[:12] for c in dangling) + ' does not resolve' + ('; task is marked done' if task['status'] == 'done' else ''))
        result = task.get('result_path')
        if result and task['status'] == 'done':
            if not result_file(cfg, result).exists():
                discrepancies.append({'task': tid, 'kind': 'result-path-missing', 'result_path': result})
                unresolve(tid, f'recorded result path {result} is missing')
        if link['ambiguous']:
            discrepancies.append({'task': tid, 'kind': 'ambiguous-link', 'commits': link['commits']})
            unresolve(tid, link['ambiguous'])
            continue
        valid = [c for c in recorded if c not in dangling]
        replaced = {r['from'] for r in task.get('replaced_commits', [])}
        new = [c for c in link['commits'] if c not in recorded and c not in replaced]
        if new:
            discrepancies.append({'task': tid, 'kind': 'linked-commit-not-recorded', 'commits': new})
        if task['phase'] != 'build':
            if new:
                unresolve(tid, f"{task['phase']} task: a commit does not establish {task['phase']} completion; record it with its evidence through cycle.py task")
            continue
        combined = list(dict.fromkeys([*valid, *new]))
        if not combined:
            continue
        change: dict = {}
        if new:
            change['commits'] = new
        if not task.get('stage'):
            change['stage'] = 'implemented'
            if recorded:
                discrepancies.append({'task': tid, 'kind': 'commits-without-stage'})
        carried = [c for c in combined if not on_head(cfg, c)]
        if not carried and not dangling:
            if task.get('stage') != 'integrated':
                change['stage'] = 'integrated'
                if task.get('stage') == 'implemented':
                    discrepancies.append({'task': tid, 'kind': 'commits-on-head-stage-not-integrated'})
        else:
            for sha in carried:
                holders = [w.get('worktree', '?') for w in trees if w.get('HEAD') and run_git(cfg, 'merge-base', '--is-ancestor', sha, w['HEAD'])[0] == 0]
                where = f" (carried by worktree {', '.join(holders)})" if holders else ''
                discrepancies.append({'task': tid, 'kind': 'commit-not-on-head', 'commit': sha, 'worktrees': holders})
                unresolve(tid, f'commit {sha[:12]} is not on HEAD{where}; merge it before stage integrated')
            if task.get('stage') == 'integrated':
                unresolve(tid, 'task is integrated but a linked commit is not on HEAD; not changed')
                continue
        if task['status'] in ('pending', 'active') and (new or valid):
            candidates.add(tid)
        elif task['status'] == 'blocked' and (new or valid):
            unresolve(tid, 'state left as blocked; linked commits exist')
        changes[tid] = change
    done = {t['id'] for t in doc['plan']['tasks'] if t['status'] == 'done'}
    order: list[str] = []
    settled = False
    while not settled:
        settled = True
        for tid in sorted(candidates):
            if all(d in done for d in by_id[tid]['depends_on']):
                changes[tid]['state'] = 'done'
                done.add(tid); candidates.discard(tid); order.append(tid); settled = False
    for tid in sorted(candidates):
        blocked = [d for d in by_id[tid]['depends_on'] if d not in done]
        unresolve(tid, f"state left as {by_id[tid]['status']}; dependencies not done: " + ', '.join(blocked))
    # Proposals that complete no task come first in plan order; completions follow in
    # the order the dependency fixpoint settled them, so --apply never writes a task
    # before a dependency it needs.
    sequence = [t['id'] for t in doc['plan']['tasks'] if t['id'] not in order] + order
    for tid in sequence:
        change = changes.get(tid)
        if change:
            proposed.append({'task': tid, 'set': {k: change[k] for k in ('state', 'stage', 'commits') if k in change}})
    result = {'ok': True, 'cycle': identity, 'discrepancies': discrepancies, 'proposed': proposed,
              'applied': [], 'unresolved': unresolved}
    if apply and proposed:
        if doc['status'] != 'active':
            raise CycleError(f"cycle is {doc['status']}; resume it before reconcile --apply")
        applied, remaining = [], list(proposed)
        while remaining:
            item, update = remaining[0], remaining[0]['set']
            try:
                _, changed = mutate_tracked(repo, identity, 'task', task_id=item['task'], state=update.get('state'),
                                            stage=update.get('stage'), commits=update.get('commits'))
            except CycleError as exc:
                # Report what was already written before the refusal; nothing is retried.
                result.update(ok=False, error=f"task {item['task']}: {exc}", applied=applied, proposed=remaining)
                return result
            remaining.pop(0)
            if changed:
                applied.append(item)
        result.update(applied=applied, proposed=[p for p in proposed if p not in applied])
    return result
