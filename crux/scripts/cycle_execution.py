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
                raw = reader._bounded_bytes(reader.Reference(path, root))
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


def _matches_checkpoint(cfg, root, sha, paths, checkpoint, boundary):
    pending = checkpoint.get('pending_sources') or {}
    source = [name for name in paths if not _bookkeeping(name, boundary)]
    if not source or not set(source).issubset(pending):
        return False
    parents = _text(root, 'rev-list', '--parents', '-n', '1', sha).split()[1:]
    if len(parents) != 1 or not _ancestor(root, checkpoint['execution_head'], parents[0]):
        return False
    # A checkpoint cannot skip unverified intervening source, even if its final bytes match.
    for between in _text(root, 'rev-list', checkpoint['execution_head'] + '..' + parents[0]).splitlines():
        between_paths = _paths(root, between)
        if not (all(_bookkeeping(name, boundary) for name in between_paths)
                or _queue_history_commit(cfg, between, root, between_paths, boundary)):
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
                    and _matches_checkpoint(cfg, root, sha, paths, origin['proof'], boundary)):
                return {'assignment': entry['id'], 'attempt': entry['attempt'], 'checkpoint': ref}
    expected = {'delivery_token': entry.get('delivery_token'), 'checkout': str(root)}
    if entry.get('execution_started') != expected:
        return None
    for item in reversed(checkpoints):
        if (item['proof'].get('delivery_token') == entry.get('delivery_token')
                and _matches_checkpoint(cfg, root, sha, paths, item['proof'], boundary)):
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


def _integrated_merge(cfg, doc, entry, sha, root, boundary, cache):
    """Prove a two-parent merge without admitting manual resolutions or merge drivers."""
    parents = _text(root, 'show', '-s', '--format=%P', sha).split()
    if len(parents) != 2 or not _ancestor(root, entry['base'], parents[0]):
        return None
    child = _integrated_source(cfg, doc, entry, parents[1], _paths(root, parents[1]), boundary, cache)
    if child is None:
        return None
    delivered = next(item for item in doc['assignments']
                     if item['id'] == child['assignment'] and item['attempt'] == child['attempt'])['delivery']
    if not all(_ancestor(root, commit, parents[1]) for commit in delivered['commits']):
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
    return {'main_parent': parents[0], 'child_parent': parents[1], 'tree': expected, 'child': child}


def prove(cfg, doc, entry, *, requested=None, edited_paths=(), delivery_commits=()):
    """Prove a stable observed HEAD. A racing bookkeeping commit refreshes this proof."""
    root = checkout(cfg, requested)
    base = _resolve(root, entry['base'])
    scope = list(doc['plan']['scope'])
    boundary = bookkeeping_paths(cfg, doc)
    cache = {}
    for name in edited_paths:
        if (not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts
                or not scope_name_in_scope(name, scope) or _bookkeeping(name, boundary)):
            raise ExecutionError('execution-edited-path-outside-scope')
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
            if (all(_bookkeeping(name, boundary) for name in paths)
                    or _queue_history_commit(cfg, sha, root, paths, boundary)):
                row['kind'] = 'bookkeeping'
            else:
                if not all(scope_name_in_scope(name, scope) or _bookkeeping(name, boundary) for name in paths):
                    raise ExecutionError('execution-source-outside-scope', commit=sha)
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
                else:
                    raise ExecutionError('execution-foreign-source', commit=sha, paths=paths)
            commits.append(row)
        if (head == _text(root, 'rev-parse', '--verify', 'HEAD') and dirty == _dirty(root, scope, boundary)
                and pending == _pending(root, dirty)):
            return {'format': FORMAT, 'cycle': doc['id'], 'assignment': entry['id'], 'attempt': entry['attempt'],
                    'delivery_token': entry.get('delivery_token'), 'review_base': base,
                    'execution_head': head, 'checkout': str(root), 'commits': commits,
                    'dirty_paths': dirty, 'pending_sources': pending, 'owned_paths': scope,
                    'ownership_basis': 'conservative recorded plan scope; grants no edit permission'}
    raise ExecutionError('execution-checkout-changing')


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
