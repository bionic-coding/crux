"""Verify execution checkouts without replacing the immutable task/review base."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess

import cycle_hosts
import cycle_context_read as reader
from council_records import git_isolated_env
from cycle_workflow import CycleError, atomic_bytes, contained, digest, encoded, scope_name_in_scope

FORMAT = 'crux.execution-proof.v1'
# Checkpoints retain only a blob identity, never content, so owned files such as a
# long operation log may exceed the context reader's 1 MiB bound. Still bounded.
CHECKPOINT_OBJECT_BYTES = 64 * 1024 * 1024


class ExecutionError(CycleError):
    def __init__(self, code, **details):
        self.code, self.details = code, details
        super().__init__('execution checkout refused: ' + code)


def git(root, *args, allowed=(0,)):
    env = git_isolated_env()
    env.pop('OPENROUTER_API_KEY', None)
    env.update(GIT_LITERAL_PATHSPECS='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    done = subprocess.run(['git', '--no-optional-locks', '--no-pager', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=' + os.devnull,
                           '-C', str(root), *args], capture_output=True, env=env)
    if done.returncode not in allowed:
        raise ExecutionError('execution-git-unavailable')
    return done.returncode, done.stdout


def _text(root, *args):
    return git(root, *args)[1].decode('utf-8').strip()


def _ancestor(root, before, after):
    return git(root, 'merge-base', '--is-ancestor', before, after, allowed=(0, 1))[0] == 0


def _resolve(root, value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise ExecutionError('execution-invalid-base')
    if _text(root, 'rev-parse', '--verify', value + '^{commit}') != value:
        raise ExecutionError('execution-invalid-base')
    return value


def checkout(cfg, requested=None):
    """Only this repository's registered checkout roots can be inspected."""
    roots = []
    for item in git(cfg.repo_root, 'worktree', 'list', '--porcelain', '-z')[1].split(b'\0'):
        if item.startswith(b'worktree '):
            roots.append(Path(os.fsdecode(item[9:])).resolve())
    selected = Path(requested).resolve() if requested else cfg.repo_root.resolve()
    if selected not in roots:
        raise ExecutionError('execution-unregistered-checkout')
    return selected


def bookkeeping_paths(cfg, doc):
    # This is the writer's exact boundary, including a queue deletion. No other
    # documentation, journal or generic shared-evidence exclusion is admitted.
    own = (cfg.docs_root / 'cycles' / doc['id']).relative_to(cfg.repo_root).as_posix()
    queue = (cfg.docs_root / 'queue/cycles.yaml').relative_to(cfg.repo_root).as_posix()
    return own, queue


def _bookkeeping(name, boundary):
    own, queue = boundary
    return name == queue or name == own or name.startswith(own + '/')


def _paths(root, sha):
    raw = git(root, 'diff-tree', '--no-commit-id', '--root', '-r', '-m', '--no-renames',
              '--name-only', '-z', sha, '--')[1]
    return sorted(set(os.fsdecode(name) for name in raw.split(b'\0') if name))


def _queue_history_commit(cfg, sha, root, paths, boundary):
    """Recognize an archive transaction, not arbitrary files under queue/history."""
    own, queue = boundary
    prefix = queue.rsplit('/', 1)[0] + '/history/items/'
    names = [name for name in paths if name.startswith(prefix)]
    if not names or queue not in paths:
        return False
    if any(not _bookkeeping(name, boundary) and name not in names for name in paths):
        return False
    if any(not re.fullmatch(re.escape(prefix) + r'Q-[0-9]{4,}\.json', name) for name in names):
        return False
    try:
        parents = _text(root, 'rev-list', '--parents', '-n', '1', sha).split()[1:]
        if len(parents) != 1:
            return False
        import cycle_queue
        from cycle_workflow import tree
        current_cfg = tree(root)
        before_raw = git(root, 'show', parents[0] + ':' + queue)[1]
        after_raw = git(root, 'show', sha + ':' + queue)[1]
        if max(len(before_raw), len(after_raw)) > 32 * 1024 * 1024:
            return False
        before = cycle_queue.parse_queue(before_raw.decode('utf-8'))
        after = cycle_queue.parse_queue(after_raw.decode('utf-8'))
        old = {item['id']: item for item in before['items']}
        new = {item['id']: item for item in after['items']}
        for name in names:
            qid = Path(name).stem
            # Every history record is newly added together with removal of the
            # identical active item; the canonical reader validates its binding.
            if qid not in old or qid in new:
                return False
            if git(root, 'cat-file', '-e', parents[0] + ':' + name, allowed=(0, 128))[0] == 0:
                return False
            raw = git(root, 'show', sha + ':' + name)[1]
            path = current_cfg.docs_root / 'queue' / 'history' / 'items' / (qid + '.json')
            if path.is_symlink() or not path.is_file() or len(raw) > cycle_queue.MAX_HISTORY_BYTES:
                return False
            if path.read_bytes() != raw or cycle_queue._read_history(current_cfg, qid) != old[qid]:
                return False
        return True
    except (CycleError, OSError, ValueError, UnicodeError, KeyError, TypeError):
        return False


def _trailered(root, sha, task):
    values = _text(root, 'log', '-1', '--format=%(trailers:key=Cycle-Task,valueonly,separator=%x1e)', sha)
    return task in {item.strip() for item in values.split('\x1e')}


def _dirty(root, scope, boundary):
    raw = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all')[1]
    names, parts, index = [], raw.split(b'\0'), 0
    while index < len(parts):
        row = parts[index]
        index += 1
        if not row:
            continue
        changed = [os.fsdecode(row[3:])]
        if row[:1] in (b'R', b'C') or row[1:2] in (b'R', b'C'):
            changed.append(os.fsdecode(parts[index]))
            index += 1
        names.extend(name for name in changed if scope_name_in_scope(name, scope) and not _bookkeeping(name, boundary))
    return sorted(set(names))


def _pending(root, names):
    """Retain object identities only; never retain edited file contents or invoke filters."""
    if not names:
        return {}
    indexed = {}
    for row in git(root, 'ls-files', '--stage', '-z', '--', *names)[1].split(b'\0'):
        if not row:
            continue
        metadata, name = row.split(b'\t', 1)
        mode, oid, stage = metadata.decode('ascii').split()
        if stage != '0':
            raise ExecutionError('execution-unmerged-index')
        indexed[os.fsdecode(name)] = {'mode': mode, 'oid': oid}
    out = {}
    for name in names:
        path = root / name
        if reader._forbidden(path) or reader.check_secret_location(path):
            raise ExecutionError('execution-checkpoint-path-refused')
        try:
            before = path.lstat()
        except FileNotFoundError:
            working = None
        else:
            if not stat.S_ISREG(before.st_mode):
                raise ExecutionError('execution-checkpoint-not-regular')
            try:
                raw = reader._bounded_bytes(reader.Reference(path, root), limit=CHECKPOINT_OBJECT_BYTES)
            except reader.ReadRefused:
                raise ExecutionError('execution-checkpoint-unavailable') from None
            if reader._identity(before) != reader._identity(path.lstat()):
                raise ExecutionError('execution-checkout-changing')
            # Git bases in this contract are SHA-1 commits. No clean filter or textconv runs.
            oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            working = {'mode': '100755' if before.st_mode & 0o111 else '100644', 'oid': oid}
        out[name] = {'index': indexed.get(name), 'working': working}
    return out


def _checkpoints(cfg, doc, entry, root, cache):
    key = (entry['id'], entry['attempt'], str(root))
    if key in cache:
        return cache[key]
    rows = []
    for operation in doc.get('operations', []):
        result = operation.get('result', {})
        metadata = result.get('execution') or {}
        if (operation['op'] != 'execution-check' or result.get('assignment') != entry['id']
                or result.get('attempt') != entry['attempt'] or metadata.get('checkout') != str(root)
                or metadata.get('review_base') != entry['base']):
            continue
        ref = metadata['proof']
        if ref['path'] != f'cycles/{doc["id"]}/execution/{ref["sha256"]}.json':
            raise ExecutionError('execution-checkpoint-unavailable')
        try:
            raw = reader._bounded_bytes(reader.Reference(contained(cfg.docs_root, ref['path']), cfg.repo_root))
            proof = json.loads(raw)
        except (reader.ReadRefused, ValueError, OSError):
            raise ExecutionError('execution-checkpoint-unavailable') from None
        if (digest(raw) != ref['sha256'] or not isinstance(proof, dict) or proof.get('format') != FORMAT
                or proof.get('cycle') != doc['id'] or proof.get('assignment') != entry['id']
                or proof.get('attempt') != entry['attempt'] or proof.get('checkout') != str(root)
                or proof.get('review_base') != entry['base'] or proof.get('execution_head') != metadata.get('execution_head')):
            raise ExecutionError('execution-checkpoint-unavailable')
        rows.append({'ref': ref, 'proof': proof})
    # A pause seal can admit an already checkpointed own commit before its
    # normal post-commit check. Its digest-bound execution artifact remains in
    # the assignment's execution history after the rotated check consumes the
    # resume seal; preserve that admission without trusting a trailer alone.
    referenced = {item['ref']['sha256'] for item in rows}
    for metadata in [*entry.get('execution_history', []), entry.get('execution') or {}]:
        ref = metadata.get('proof') or {}
        sha = ref.get('sha256')
        if not sha or sha in referenced or ref.get('path') != f'cycles/{doc["id"]}/execution/{sha}.json':
            continue
        try:
            raw = reader._bounded_bytes(reader.Reference(contained(cfg.docs_root, ref['path']), cfg.repo_root))
            proof = json.loads(raw)
        except (reader.ReadRefused, ValueError, OSError):
            raise ExecutionError('execution-checkpoint-unavailable') from None
        if not isinstance(proof, dict) or not proof.get('seal_host') or not proof.get('seal_agent'):
            continue
        if (digest(raw) != sha or proof.get('format') != FORMAT or proof.get('cycle') != doc['id']
                or proof.get('assignment') != entry['id'] or proof.get('attempt') != entry['attempt']
                or proof.get('checkout') != str(root) or proof.get('review_base') != entry['base']
                or proof.get('execution_head') != metadata.get('execution_head')
                or proof['seal_host'] != entry.get('host') or proof['seal_agent'] != entry.get('agent')):
            raise ExecutionError('execution-checkpoint-unavailable')
        rows.append({'ref': ref, 'proof': proof})
        referenced.add(sha)
    cache[key] = rows
    return rows


def _matches_checkpoint(cfg, root, sha, paths, checkpoint, boundary, scope):
    pending = checkpoint.get('pending_sources') or {}
    source = [name for name in paths if not _bookkeeping(name, boundary)]
    if not source or not set(source).issubset(pending):
        return False
    parents = _text(root, 'rev-list', '--parents', '-n', '1', sha).split()[1:]
    if len(parents) != 1 or not _ancestor(root, checkpoint['execution_head'], parents[0]):
        return False
    # A checkpoint cannot skip unverified intervening source, even if its final bytes match.
    for between in _text(root, 'rev-list', checkpoint['execution_head'] + '..' + parents[0]).splitlines():
        if not _is_bookkeeping_commit(cfg, root, between, _paths(root, between), boundary, scope):
            return False
    committed = {}
    for row in git(root, 'ls-tree', '-z', sha, '--', *source)[1].split(b'\0'):
        if row:
            metadata, name = row.split(b'\t', 1)
            mode, kind, oid = metadata.decode('ascii').split()
            if kind != 'blob':
                return False
            committed[os.fsdecode(name)] = {'mode': mode, 'oid': oid}
    return all(committed.get(name) in (pending[name]['index'], pending[name]['working']) for name in source)


def _active_source(cfg, doc, entry, sha, root, paths, boundary, cache):
    if not _trailered(root, sha, entry['task']):
        return None
    checkpoints = _checkpoints(cfg, doc, entry, root, cache)
    # An admitted commit stays admitted across same-execution token rotation. Its original
    # checkpoint must precede the admission and retain that admission's exact token binding.
    for index, admitted in enumerate(checkpoints):
        for row in admitted['proof'].get('commits', []):
            if row['sha'] != sha or row.get('kind') != 'same-attempt-commit':
                continue
            ref = row.get('provenance', {}).get('checkpoint')
            origin = next((item for item in checkpoints[:index] if item['ref'] == ref), None)
            if (origin and origin['proof'].get('delivery_token') == admitted['proof'].get('delivery_token')
                    and _ancestor(root, sha, admitted['proof']['execution_head'])
                    and _matches_checkpoint(cfg, root, sha, paths, origin['proof'], boundary, doc['plan']['scope'])):
                return {'assignment': entry['id'], 'attempt': entry['attempt'], 'checkpoint': ref}
    expected = {'delivery_token': entry.get('delivery_token'), 'checkout': str(root)}
    if entry.get('execution_started') != expected:
        return None
    for item in reversed(checkpoints):
        if (item['proof'].get('delivery_token') == entry.get('delivery_token')
                and _matches_checkpoint(cfg, root, sha, paths, item['proof'], boundary, doc['plan']['scope'])):
            return {'assignment': entry['id'], 'attempt': entry['attempt'], 'checkpoint': item['ref']}
    return None


def _retained_source(cfg, doc, entry, sha, root, paths, boundary, cache):
    entries = list(doc.get('assignments', [])) + [h['previous'] for h in doc['history'] if isinstance(h.get('previous'), dict)]
    for prior in entries:
        if prior.get('task') != entry['task'] or prior.get('base') != entry['base']:
            continue
        terminal = 'mark-lost' if prior.get('state') == 'lost' else 'deliver'
        if (prior.get('state') in ('lost', 'finished')
                and any(h['action'] == terminal and h.get('assignment') == prior['id']
                        and h.get('attempt') == prior['attempt'] for h in doc['history'])):
            provenance = _active_source(cfg, doc, prior, sha, root, paths, boundary, cache)
            if provenance:
                return provenance
        delivery = prior.get('delivery') or {}
        if (prior.get('task') != entry['task'] or prior.get('base') != entry['base']
                or prior.get('state') != 'finished' or not delivery.get('commits')
                or not any(sha == tip or _ancestor(root, sha, tip) for tip in delivery['commits'])):
            continue
        if not any(h['action'] == 'deliver' and h.get('assignment') == prior['id']
                   and h.get('attempt') == prior['attempt'] for h in doc['history']):
            continue
        path = contained(cfg.docs_root, delivery['path'])
        try:
            raw = reader._bounded_bytes(reader.Reference(path, cfg.repo_root))
        except reader.ReadRefused:
            raise ExecutionError('execution-resume-proof-unreadable') from None
        if digest(raw) != delivery['sha256']:
            raise ExecutionError('execution-resume-proof-changed')
        if cycle_hosts.result_problem(raw.decode('utf-8'), prior['id'], prior['attempt'], prior.get('delivery_token')):
            raise ExecutionError('execution-resume-proof-invalid')
        if _trailered(root, sha, entry['task']):
            return {'assignment': prior['id'], 'attempt': prior['attempt'],
                    'result': {'path': delivery['path'], 'sha256': delivery['sha256']}}
    return None


def _integrated_source(cfg, doc, entry, sha, paths, boundary, cache):
    """Admit only exact, delivered, checkpoint-proven declared child commits."""
    parent = next((task for task in doc['plan']['tasks'] if task['id'] == entry.get('task')), None)
    if not parent:
        return None
    children = set(parent.get('integrates', ())) & set(parent.get('depends_on', ()))
    children.discard(entry.get('task'))
    for child in doc.get('assignments', []):
        delivery = child.get('delivery') or {}
        child_task = next((task for task in doc['plan']['tasks'] if task['id'] == child.get('task')), None)
        if (child.get('task') not in children or child.get('state') != 'finished'
                or not child_task or child_task['status'] != 'done' or sha not in child_task.get('commits', [])
                or delivery.get('outcome') != 'done' or sha not in delivery.get('commits', [])):
            continue
        if not any(event.get('action') == 'deliver' and event.get('assignment') == child['id']
                   and event.get('attempt') == child['attempt'] for event in doc['history']):
            continue
        try:
            raw = reader._bounded_bytes(reader.Reference(contained(cfg.docs_root, delivery['path']), cfg.repo_root))
            if digest(raw) != delivery['sha256'] or cycle_hosts.result_problem(
                    raw.decode('utf-8'), child['id'], child['attempt'], child.get('delivery_token')):
                raise ExecutionError('execution-resume-proof-invalid')
            child_checkout = (child.get('execution') or {}).get('checkout')
            if not isinstance(child_checkout, str) or not child_checkout:
                raise ExecutionError('execution-resume-proof-unavailable')
            child_root = checkout(cfg, child_checkout)
        except (reader.ReadRefused, OSError, UnicodeError, KeyError, TypeError):
            raise ExecutionError('execution-resume-proof-unreadable') from None
        provenance = _active_source(cfg, doc, child, sha, child_root, paths, boundary, cache)
        if provenance:
            return {'task': child['task'], 'assignment': child['id'], 'attempt': child['attempt'],
                    'checkpoint': provenance['checkpoint'],
                    'result': {'path': delivery['path'], 'sha256': delivery['sha256']}}
    return None


# Kinds whose admission rested on a checkpoint, a validated delivery report or a
# delivered range. A current-delivery row rests on ancestry alone and grounds nothing.
ADMITTING_KINDS = ('same-attempt-commit', 'same-task-resume', 'integrated-task-source', 'cycle-task-source')
# The evidence-only child-tip walk follows at most this many bookkeeping commits.
EVIDENCE_WALK_LIMIT = 32


def _parents(root, sha):
    return _text(root, 'rev-list', '--parents', '-n', '1', sha).split()[1:]


def _other_cycle_record(cfg, root, sha, paths, boundary, scope):
    """The other cycles whose record commit C is, or None: the basis `other-cycle-record`.

    The whole commit is judged. (i) C has at most one parent. (ii) Every path lies in this
    cycle's own boundary or under `<docs>/cycles/<ID>/` for another valid cycle id. (iii) At
    least one path lies under such a directory. (iv) C's tree holds each such cycle.json.
    (v) No path lies in this cycle's plan scope. (vi) Each such cycle.json at C's first
    parent is absent or parses with a status outside CLOSED; an unreadable one fails.
    It admits by paths and tree content, never by subject, trailer or author.
    """
    from cycle_workflow import CLOSED, ID
    if scope is None or not paths:
        return None
    prefix = (cfg.docs_root / 'cycles').relative_to(cfg.repo_root).as_posix() + '/'
    own = boundary[0].rsplit('/', 1)[-1]
    cycles = set()
    for name in paths:
        if scope_name_in_scope(name, scope):
            return None
        if _bookkeeping(name, boundary):
            continue
        ident = name[len(prefix):].split('/', 1)[0] if name.startswith(prefix) else ''
        if not ident or '/' not in name[len(prefix):] or ident == own or not ID.match(ident):
            return None
        cycles.add(ident)
    if not cycles:
        return None
    parents = _parents(root, sha)
    if len(parents) > 1:
        return None
    for ident in sorted(cycles):
        record = f'{prefix}{ident}/cycle.json'
        if git(root, 'cat-file', '-e', f'{sha}:{record}', allowed=(0, 128))[0] != 0:
            return None
        if not parents:
            continue
        code, raw = git(root, 'show', f'{parents[0]}:{record}', allowed=(0, 128))
        if code != 0:
            if git(root, 'cat-file', '-e', f'{parents[0]}:{record}', allowed=(0, 128))[0] == 0:
                return None  # present but unreadable
            continue  # absent at the parent, as for a record queue start-next creates
        try:
            status = json.loads(raw.decode('utf-8')).get('status')
        except (ValueError, UnicodeError, AttributeError):
            return None
        if not isinstance(status, str) or status in CLOSED:
            return None
    return sorted(cycles)


def _is_bookkeeping_commit(cfg, root, sha, paths, boundary, scope):
    return bool(all(_bookkeeping(name, boundary) for name in paths)
                or _queue_history_commit(cfg, sha, root, paths, boundary)
                or _other_cycle_record(cfg, root, sha, paths, boundary, scope))


def _child_tip(cfg, root, sha, boundary, scope):
    """Resolve a merge's second parent past an evidence-only child tip.

    Walk first parents while each commit is bookkeeping-only, at most
    EVIDENCE_WALK_LIMIT commits. Returns (commit, paths) of the first commit that
    is not bookkeeping, or None when the walk exceeds the bound or ends.
    """
    current, walked = sha, 0
    while True:
        paths = _paths(root, current)
        if not _is_bookkeeping_commit(cfg, root, current, paths, boundary, scope):
            return current, paths
        walked += 1
        parents = _parents(root, current)
        if walked > EVIDENCE_WALK_LIMIT or not parents:
            return None
        current = parents[0]


def _merge_proof(cfg, root, entry, sha, boundary, admit, scope):
    """Prove a two-parent merge without admitting manual resolutions or merge drivers.

    `admit(commit, paths)` returns (provenance, delivered commits) for the resolved
    second parent, or None.
    """
    parents = _text(root, 'show', '-s', '--format=%P', sha).split()
    if len(parents) != 2 or not _ancestor(root, entry['base'], parents[0]):
        return None
    resolved = _child_tip(cfg, root, parents[1], boundary, scope)
    if resolved is None:
        return None
    admitted = admit(*resolved)
    if admitted is None:
        return None
    child, delivered = admitted
    if not all(_ancestor(root, commit, parents[1]) for commit in delivered):
        return None  # A historical earlier child commit is not the delivered unit's tip.
    # merge-tree may invoke locally configured custom merge drivers. This proof
    # deliberately supports only builtin deterministic merging, never repository
    # commands or resolutions supplied by the worker.
    code, drivers = git(root, 'config', '--get-regexp', r'^merge\..*\.driver$', allowed=(0, 1))
    if code == 0 and drivers.strip():
        return None
    code, merged = git(root, '-c', 'core.attributesFile=' + os.devnull, '-c', 'merge.renormalize=false',
                       'merge-tree', '--write-tree', '--no-messages', *parents, allowed=(0, 1, 128, 129))
    if code:
        return None
    expected = merged.decode('ascii').strip()
    if not re.fullmatch(r'[0-9a-f]{40}', expected) or expected != _text(root, 'rev-parse', sha + '^{tree}'):
        return None
    found = {'main_parent': parents[0], 'child_parent': parents[1], 'tree': expected, 'child': child}
    if resolved[0] != parents[1]:
        found['child_source'] = resolved[0]
    return found


def _integrated_merge(cfg, doc, entry, sha, root, boundary, cache):
    """Prove a merge of a declared child, resolving an evidence-only child tip."""
    def admit(tip, paths):
        child = _integrated_source(cfg, doc, entry, tip, paths, boundary, cache)
        if child is None:
            return None
        delivered = next(item for item in doc['assignments']
                         if item['id'] == child['assignment'] and item['attempt'] == child['attempt'])['delivery']
        return child, delivered['commits']
    return _merge_proof(cfg, root, entry, sha, boundary, admit, doc['plan']['scope'])


def _task_of(doc, ident):
    return next((task for task in doc['plan']['tasks'] if task['id'] == ident), None)


def _stream_of(doc, task):
    """The declared stream a task names; None for a task with no stream."""
    name = (task or {}).get('stream')
    if not name:
        return None
    return next((stream for stream in doc['plan'].get('streams', []) if stream['id'] == name), None)


def _done_deliveries(doc, task_id):
    """Finished assignments of a task that delivered done, each with its deliver event."""
    entries = list(doc.get('assignments', [])) + [h['previous'] for h in doc['history'] if isinstance(h.get('previous'), dict)]
    seen = set()
    for prior in entries:
        key = (prior.get('id'), prior.get('attempt'))
        delivery = prior.get('delivery') or {}
        if (prior.get('task') != task_id or key in seen or prior.get('state') != 'finished'
                or delivery.get('outcome') != 'done'):
            continue
        if not any(h['action'] == 'deliver' and h.get('assignment') == prior['id']
                   and h.get('attempt') == prior['attempt'] for h in doc['history']):
            continue
        seen.add(key)
        yield prior


def _retained_proofs(cfg, doc, prior, cache):
    """Every digest-checked proof an assignment retains; a damaged proof grounds nothing."""
    key = ('retained-proofs', prior['id'], prior['attempt'])
    if key in cache:
        return cache[key]
    found = []
    for metadata in [prior.get('execution') or {}, *prior.get('execution_history', [])]:
        ref = (metadata or {}).get('proof') or {}
        sha = ref.get('sha256')
        if not isinstance(sha, str) or ref.get('path') != f'cycles/{doc["id"]}/execution/{sha}.json':
            continue
        try:
            raw = reader._bounded_bytes(reader.Reference(contained(cfg.docs_root, ref['path']), cfg.repo_root))
            proof = json.loads(raw)
        except (reader.ReadRefused, ValueError, OSError, CycleError):
            continue
        if (digest(raw) != sha or not isinstance(proof, dict) or proof.get('format') != FORMAT
                or proof.get('cycle') != doc['id'] or proof.get('assignment') != prior['id']
                or proof.get('attempt') != prior['attempt']):
            continue
        found.append((ref, proof))
    cache[key] = found
    return found


def _report_damage(cfg, prior):
    """None when the retained delivery report matches its digest and marker; else the problem."""
    delivery = prior['delivery']
    try:
        raw = reader._bounded_bytes(reader.Reference(contained(cfg.docs_root, delivery['path']), cfg.repo_root))
        if digest(raw) != delivery['sha256']:
            return 'changed'
        if cycle_hosts.result_problem(raw.decode('utf-8'), prior['id'], prior['attempt'], prior.get('delivery_token')):
            return 'invalid'
    except (reader.ReadRefused, OSError, UnicodeError, KeyError, TypeError, CycleError):
        return 'unreadable'
    return None


def _cycle_task_source(cfg, doc, entry, sha, root, paths, boundary, cache, damaged):
    """Admit a one-parent commit through another done task's validated delivery.

    Ground (a): a retained digest-checked proof of that delivery lists the commit
    with an admitting kind. Ground (b): the commit carries the task's trailer, lies
    inside the delivered range and above that assignment's base. Either ground also
    needs the delivery report to validate; a damaged report grounds nothing and is
    named in `damaged` for the refusal.
    """
    if len(_parents(root, sha)) > 1:
        return None
    source = [name for name in paths if not _bookkeeping(name, boundary)]
    for task in doc['plan']['tasks']:
        if task['id'] == entry.get('task') or task['status'] != 'done':
            continue
        stream = _stream_of(doc, task)
        if stream and not all(scope_name_in_scope(name, stream['paths']) for name in source):
            continue
        for prior in _done_deliveries(doc, task['id']):
            ground = None
            for ref, proof in _retained_proofs(cfg, doc, prior, cache):
                if any(isinstance(row, dict) and row.get('sha') == sha and row.get('kind') in ADMITTING_KINDS
                       for row in proof.get('commits', [])):
                    ground = {'ground': 'retained-proof', 'proof': ref}
                    break
            if ground is None:
                delivery, base = prior['delivery'], prior.get('base')
                if (isinstance(base, str) and _trailered(root, sha, task['id'])
                        and any(sha == tip or _ancestor(root, sha, tip) for tip in delivery.get('commits', []))
                        and not _ancestor(root, sha, base)):
                    ground = {'ground': 'validated-delivery'}
            if ground is None:
                continue
            delivery = prior['delivery']
            problem = _report_damage(cfg, prior)
            if problem:
                damaged.append({'task': task['id'], 'assignment': prior['id'], 'attempt': prior['attempt'],
                                'path': delivery.get('path'), 'sha256': delivery.get('sha256'), 'problem': problem})
                continue
            return {'task': task['id'], 'assignment': prior['id'], 'attempt': prior['attempt'], **ground,
                    'result': {'path': delivery['path'], 'sha256': delivery['sha256']}}
    return None


def _cycle_task_merge(cfg, doc, entry, sha, root, boundary, cache, damaged):
    """Admit a conflict-free merge of another done task's delivered work, by any role."""
    def admit(tip, paths):
        child = _cycle_task_source(cfg, doc, entry, tip, root, paths, boundary, cache, damaged)
        if child is None:
            return None
        delivered = next(prior for prior in _done_deliveries(doc, child['task'])
                         if prior['id'] == child['assignment'] and prior['attempt'] == child['attempt'])
        return child, delivered['delivery']['commits']
    return _merge_proof(cfg, root, entry, sha, boundary, admit, doc['plan']['scope'])


def _foreign_fact(doc, entry, sha, root, paths, boundary):
    """The checked fact a foreign-source refusal may add; never a route."""
    if len(_parents(root, sha)) != 1:
        return None
    values = _text(root, 'log', '-1', '--format=%(trailers:key=Cycle-Task,valueonly,separator=%x1e)', sha)
    named = {item.strip() for item in values.split('\x1e') if item.strip()}
    if entry.get('task') in named:
        return None
    tasks = [task for task in doc['plan']['tasks'] if task['id'] in named]
    if len(tasks) != 1 or len(named) != 1:
        return None
    task = tasks[0]
    if task['status'] == 'done':
        return None
    bases = [event.get('base') for event in doc['history'] if event.get('action') == 'prepare-dispatch'
             and event.get('pass') == doc['pass'] and event.get('task') == task['id'] and isinstance(event.get('base'), str)]
    if not any(not _ancestor(root, sha, base) for base in bases):
        return None
    stream = _stream_of(doc, task)
    if stream and not all(scope_name_in_scope(name, stream['paths']) for name in paths if not _bookkeeping(name, boundary)):
        return None
    return {'task': task['id'], 'commit': sha,
            'fact': (f'delivering task {task["id"]} done in this pass admits commit {sha} as cycle-task-source '
                     f'ground (b), because a done delivery must cover every commit carrying the trailer '
                     f'Cycle-Task: {task["id"]} above that task\'s base')}


def _trailers(root, sha):
    values = _text(root, 'log', '-1', '--format=%(trailers:key=Cycle-Task,valueonly,separator=%x1e)', sha)
    return sorted({item.strip() for item in values.split('\x1e') if item.strip()})


def prove(cfg, doc, entry, *, requested=None, edited_paths=(), delivery_commits=(), collect=False):
    """Prove a stable observed HEAD. A racing bookkeeping commit refreshes this proof.

    The default mode raises at the first commit no admission accepts. The keyword-only
    `collect` mode, used only by the return writer's probe, classifies the whole range:
    a per-commit refusal becomes a row carrying `refused` (its code) and `details`, every
    row carries its Cycle-Task `trailers`, and the walk continues to HEAD. Whole-range
    refusals (edited paths, dirty plan-scope paths, a behind or unrelated base) still raise.
    """
    root = checkout(cfg, requested)
    base = _resolve(root, entry['base'])
    scope = list(doc['plan']['scope'])
    boundary = bookkeeping_paths(cfg, doc)
    stream = _stream_of(doc, _task_of(doc, entry.get('task')))
    cache = {}
    outside = [name for name in edited_paths
               if (not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts
                   or not scope_name_in_scope(name, scope) or _bookkeeping(name, boundary))]
    if outside:
        raise ExecutionError('execution-edited-path-outside-scope', paths=[str(name) for name in outside])
    if stream:
        beyond = [name for name in edited_paths if not scope_name_in_scope(name, stream['paths'])]
        if beyond:
            raise ExecutionError('execution-edited-path-outside-stream', paths=beyond, stream=stream['id'],
                                 task=entry.get('task'))
    for _ in range(3):
        head = _text(root, 'rev-parse', '--verify', 'HEAD')
        dirty = _dirty(root, scope, boundary)
        if set(dirty) - set(edited_paths):
            raise ExecutionError('execution-dirty-owned-paths', paths=dirty)
        pending = _pending(root, dirty)
        if head != base and not _ancestor(root, base, head):
            if _ancestor(root, head, base):
                raise ExecutionError('execution-behind-base', checkout=str(root), base=base,
                                     argv=['git', '-C', str(root), 'merge', '--ff-only', base])
            raise ExecutionError('execution-unrelated-base', base=base, head=head)
        commits = []
        for sha in _text(root, 'rev-list', '--reverse', '--topo-order', base + '..' + head).splitlines():
            paths = _paths(root, sha)
            row = {'sha': sha, 'paths': paths}
            if collect:
                row['trailers'] = _trailers(root, sha)
                try:
                    _classify(cfg, doc, entry, sha, root, paths, boundary, scope, stream, cache, delivery_commits, row)
                except ExecutionError as exc:
                    row.update(refused=exc.code, details=exc.details)
            else:
                _classify(cfg, doc, entry, sha, root, paths, boundary, scope, stream, cache, delivery_commits, row)
            commits.append(row)
        if (head == _text(root, 'rev-parse', '--verify', 'HEAD') and dirty == _dirty(root, scope, boundary)
                and pending == _pending(root, dirty)):
            owned, basis = scope, 'conservative recorded plan scope; grants no edit permission'
            if stream:
                owned = list(stream['paths'])
                basis = f'declared stream {stream["id"]} within the recorded plan scope; grants no edit permission'
            return {'format': FORMAT, 'cycle': doc['id'], 'assignment': entry['id'], 'attempt': entry['attempt'],
                    'delivery_token': entry.get('delivery_token'), 'review_base': base,
                    'execution_head': head, 'checkout': str(root), 'commits': commits,
                    'dirty_paths': dirty, 'pending_sources': pending, 'owned_paths': owned,
                    'ownership_basis': basis}
    raise ExecutionError('execution-checkout-changing')


def _classify(cfg, doc, entry, sha, root, paths, boundary, scope, stream, cache, delivery_commits, row):
    """Label one commit of the proven range, or raise its per-commit refusal."""
    if all(_bookkeeping(name, boundary) for name in paths) or _queue_history_commit(cfg, sha, root, paths, boundary):
        row['kind'] = 'bookkeeping'
        return
    if (cycles := _other_cycle_record(cfg, root, sha, paths, boundary, scope)):
        row.update(kind='bookkeeping', basis='other-cycle-record', cycles=cycles)
        return
    if not all(scope_name_in_scope(name, scope) or _bookkeeping(name, boundary) for name in paths):
        raise ExecutionError('execution-source-outside-scope', commit=sha)
    damaged = []
    provenance = _retained_source(cfg, doc, entry, sha, root, paths, boundary, cache)
    if provenance:
        row.update(kind='same-task-resume', provenance=provenance)
    elif (provenance := _active_source(cfg, doc, entry, sha, root, paths, boundary, cache)):
        row.update(kind='same-attempt-commit', provenance=provenance)
    elif (provenance := _integrated_source(cfg, doc, entry, sha, paths, boundary, cache)):
        row.update(kind='integrated-task-source', provenance=provenance)
    elif (provenance := _integrated_merge(cfg, doc, entry, sha, root, boundary, cache)):
        row.update(kind='integrated-task-merge', provenance=provenance)
    elif any(sha == tip or _ancestor(root, sha, tip) for tip in delivery_commits):
        # Existing delivery validation supplies this exact current result.
        # This observation changes no delivery ancestry/trailer policy.
        row.update(kind='current-delivery', trailered=_trailered(root, sha, entry['task']))
    elif (provenance := _cycle_task_source(cfg, doc, entry, sha, root, paths, boundary, cache, damaged)):
        row.update(kind='cycle-task-source', provenance=provenance)
    elif (provenance := _cycle_task_merge(cfg, doc, entry, sha, root, boundary, cache, damaged)):
        row.update(kind='cycle-task-merge', provenance=provenance)
    else:
        details = {'commit': sha, 'paths': paths}
        if damaged:
            details['damaged_reports'] = list({item['path']: item for item in damaged}.values())
        if (fact := _foreign_fact(doc, entry, sha, root, paths, boundary)):
            details['fact'] = fact
        raise ExecutionError('execution-foreign-source', **details)
    if stream and row['kind'] in ('same-task-resume', 'same-attempt-commit'):
        # The stream test reads only the attempt's own work, never another task's admitted work.
        beyond = [name for name in paths if not _bookkeeping(name, boundary)
                  and not scope_name_in_scope(name, stream['paths'])]
        if beyond:
            raise ExecutionError('execution-edited-path-outside-stream', paths=beyond, stream=stream['id'],
                                 task=entry.get('task'), commit=sha)


def seal_pending(cfg, doc, entry):
    """Seal one attached execution's pending identities before its token changes.

    A conservative plan scope cannot assign dirty files between concurrent workers.
    In that case no resume seal is issued; normal checkout recovery still applies.
    """
    token, agent, host = entry.get('delivery_token'), entry.get('agent'), entry.get('host')
    started = entry.get('execution_started') or {}
    if (entry.get('state') != 'running' or not token or not agent or not host
            or started.get('delivery_token') != token or not started.get('checkout')):
        return None
    competing = any(other is not entry and other.get('state') in ('running', 'reserved')
                    and other.get('role') in ('developer', 'dev-lead')
                    for other in doc.get('assignments', []))
    if competing:
        return None
    root = checkout(cfg, started['checkout'])
    scope = list(doc['plan']['scope'])
    boundary = bookkeeping_paths(cfg, doc)
    dirty = _dirty(root, scope, boundary)
    if not dirty:
        entry.pop('resume_seal', None)
        return None
    proof = prove(cfg, doc, entry, requested=str(root), edited_paths=dirty)
    proof.update(seal_host=host, seal_agent=agent)
    execution, _ = retain(cfg, doc, entry, proof)
    entry['resume_seal'] = {'host': host, 'agent': agent, 'checkout': str(root),
                            'review_base': entry['base'], 'previous_token': token,
                            'proof': execution['proof']}
    return entry['resume_seal']


def resume_start(cfg, doc, entry, root):
    """Return exactly sealed dirty paths for the same bound, rotated execution."""
    seal = entry.get('resume_seal')
    if not seal:
        return None
    root = checkout(cfg, str(root))
    expected = {'host': entry.get('host'), 'agent': entry.get('agent'), 'checkout': str(root),
                'review_base': entry.get('base')}
    if (not seal.get('agent') or not seal.get('host')
            or any(seal.get(key) != value for key, value in expected.items())
            or entry.get('execution_started') != {'delivery_token': seal.get('previous_token'), 'checkout': str(root)}
            or not entry.get('delivery_token') or entry['delivery_token'] == seal.get('previous_token')):
        raise ExecutionError('execution-resume-identity-changed')
    ref = seal.get('proof') or {}
    if ref.get('path') != f'cycles/{doc["id"]}/execution/{ref.get("sha256")}.json':
        raise ExecutionError('execution-checkpoint-unavailable')
    try:
        raw = reader._bounded_bytes(reader.Reference(contained(cfg.docs_root, ref['path']), cfg.repo_root))
        proof = json.loads(raw)
    except (reader.ReadRefused, ValueError, OSError):
        raise ExecutionError('execution-checkpoint-unavailable') from None
    if (digest(raw) != ref.get('sha256') or not isinstance(proof, dict)
            or proof.get('format') != FORMAT or proof.get('cycle') != doc['id']
            or proof.get('assignment') != entry['id'] or proof.get('attempt') != entry['attempt']
            or proof.get('delivery_token') != seal.get('previous_token')
            or proof.get('seal_host') != seal['host'] or proof.get('seal_agent') != seal['agent']
            or proof.get('checkout') != str(root) or proof.get('review_base') != entry['base']):
        raise ExecutionError('execution-checkpoint-unavailable')
    paths = proof.get('dirty_paths')
    pending = proof.get('pending_sources')
    if (not isinstance(paths, list) or not paths or not isinstance(pending, dict)
            or set(paths) != set(pending)):
        raise ExecutionError('execution-checkpoint-unavailable')
    head = _text(root, 'rev-parse', '--verify', 'HEAD')
    if not _ancestor(root, proof.get('execution_head'), head):
        raise ExecutionError('execution-resume-ancestry-changed')
    boundary = bookkeeping_paths(cfg, doc)
    if (_dirty(root, doc['plan']['scope'], boundary) != paths or _pending(root, paths) != pending):
        raise ExecutionError('execution-resume-pending-changed')
    # Re-prove the complete range and identities; a matching file list alone is insufficient.
    current = prove(cfg, doc, entry, requested=str(root), edited_paths=paths)
    if current['pending_sources'] != pending:
        raise ExecutionError('execution-resume-pending-changed')
    return paths


def retain(cfg, doc, entry, proof):
    raw = encoded(proof)
    try:
        unsafe = reader._scan(raw.decode())
    except reader.ReadRefused:
        raise ExecutionError('execution-scanner-unavailable') from None
    if unsafe or len(raw) > reader.MAX_OBJECT_BYTES:
        raise ExecutionError('execution-proof-unsafe-or-too-large')
    sha = digest(raw)
    name = f'cycles/{doc["id"]}/execution/{sha}.json'
    path = contained(cfg.docs_root, name)
    if path.exists():
        if path.read_bytes() != raw:
            raise ExecutionError('execution-proof-conflict')
    else:
        atomic_bytes(path, raw)
    current = {'review_base': proof['review_base'], 'execution_head': proof['execution_head'], 'checkout': proof['checkout'],
               'proof': {'path': name, 'sha256': sha}}
    previous = entry.get('execution')
    if previous and previous != current:
        entry.setdefault('execution_history', []).append(previous)
    entry['execution'] = current
    return {**proof, 'proof': current['proof']}, previous != current


# A return from Build is accepted only over a range that refuses with one of these codes.
RANGE_CODES = ('execution-foreign-source', 'execution-source-outside-scope')


def _next_attempt_entry(cfg, doc, task_id):
    """The entry fields the task's next prepare-dispatch would prove, reserving nothing.

    Base: HEAD at the task's first reservation in this pass, else HEAD now.
    """
    earlier = [event for event in doc['history'] if event.get('action') == 'prepare-dispatch'
               and event.get('pass') == doc['pass'] and event.get('task') == task_id]
    base = earlier[0]['base'] if earlier else _text(cfg.repo_root, 'rev-parse', '--verify', 'HEAD')
    latest = [entry for entry in doc.get('assignments', []) if entry.get('task') == task_id]
    if latest:
        previous = latest[-1]
        return {'id': previous['id'], 'task': task_id, 'attempt': previous['attempt'] + 1, 'base': base,
                'delivery_token': None}
    return {'id': task_id, 'task': task_id, 'attempt': 1, 'base': base, 'delivery_token': None}


def _probe_range(cfg, doc, task_id):
    entry = _next_attempt_entry(cfg, doc, task_id)
    found = {'task': task_id, 'base': entry['base']}
    try:
        proof = prove(cfg, doc, entry, collect=True)
    except ExecutionError as exc:
        found.update(refused=exc.code, details=exc.details)
        return found
    rows = []
    for row in proof['commits']:
        kept = {'sha': row['sha'], 'paths': row['paths'], 'trailers': row.get('trailers', [])}
        if 'refused' in row:
            kept.update(refused=row['refused'], details=row.get('details', {}))
        else:
            kept['kind'] = row['kind']
            for key in ('basis', 'cycles'):
                if key in row:
                    kept[key] = row[key]
        rows.append(kept)
    found['rows'] = rows
    return found


def return_probe(cfg, doc, task_id):
    """The return writer's own probe: (execution_refusal, refusal problem or None).

    Only the named task's range gates the return. Every other task that is not done and
    had an assignment reserved in the current pass is probed for the record, because the
    new pass reopens or keeps blocked each such task and its next reservation takes HEAD.
    A done task is not probed: the return moves no done task's base, and its delivered
    range was observed at its delivery, whose deliver event journals any refusal in its
    execution_observation.
    """
    named = _probe_range(cfg, doc, task_id)
    ranges = [named]
    reserved = []
    for event in doc['history']:
        if (event.get('action') == 'prepare-dispatch' and event.get('pass') == doc['pass']
                and event.get('task') not in reserved and event.get('task') != task_id):
            reserved.append(event.get('task'))
    for other in reserved:
        task = _task_of(doc, other)
        if task is None or task['status'] == 'done':
            continue
        try:
            ranges.append(_probe_range(cfg, doc, other))
        except Exception as exc:  # A record probe never fails the return.
            ranges.append({'task': other, 'refused': 'execution-proof-unavailable', 'details': {'cause': type(exc).__name__}})
    head = _text(cfg.repo_root, 'rev-parse', '--verify', 'HEAD')
    refusal = {'task': task_id, 'head': head, 'ranges': ranges}
    if 'refused' in named:
        return refusal, {'code': named['refused'], 'details': named.get('details', {})}
    codes = sorted({row['refused'] for row in named['rows'] if 'refused' in row})
    if not codes:
        return refusal, {'code': 'no-refused-row'}
    other = [code for code in codes if code not in RANGE_CODES]
    if other:
        return refusal, {'code': other[0], 'codes': codes}
    return refusal, None
