"""Small shared Git-runtime reservations for cycle identifiers and checkout editors."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

WRITER_FORMATS = ('crux.cycle.vNext', 'crux.cycle.v1')


class RuntimeRefusal(ValueError):
    pass


def common_directory(repo):
    result = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--git-common-dir'], capture_output=True, text=True)
    if result.returncode:
        return None
    path = Path(result.stdout.strip())
    return (path if path.is_absolute() else Path(repo) / path).resolve()


def checkout_root(path):
    result = subprocess.run(['git', '-C', str(path), 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeRefusal('checkout must be a Git working tree')
    return Path(result.stdout.strip()).resolve()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(value, output, sort_keys=True, indent=2)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(repo, wrap_body=True):
    common = common_directory(repo)
    if common is None:
        raise RuntimeRefusal('pilot work requires a Git checkout')
    directory = common / 'crux' / 'pilot'
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / 'runtime.lock'
    if lock.is_symlink():
        raise RuntimeRefusal('runtime lock must be a regular file')
    with lock.open('a+') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        path = directory / 'runtime.json'
        try:
            if path.is_symlink():
                raise RuntimeRefusal('runtime state must be a regular file')
            state = json.loads(path.read_text()) if path.exists() else {'counters': {}, 'claims': {}}
            if not isinstance(state, dict) or set(state) != {'counters', 'claims'} or any(not isinstance(state[k], dict) for k in state):
                raise RuntimeRefusal('runtime state is invalid; inspect it without deleting ownership')
            before = json.dumps(state, sort_keys=True)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeRefusal(f'runtime state unavailable: {exc}') from exc
        if wrap_body:
            # A pilot's own record writes run in the body, and their failures are refusals.
            try:
                yield state
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeRefusal(f'runtime state unavailable: {exc}') from exc
        else:
            # A legacy operation's own errors propagate unchanged, so its crash recovery sees them.
            yield state
        if json.dumps(state, sort_keys=True) != before:
            try:
                atomic(path, state)
            except OSError as exc:
                raise RuntimeRefusal(f'runtime state unavailable: {exc}') from exc


def flush(repo, state):
    """Save `state` now. The caller holds `locked(repo)` and may flush again to restore a snapshot."""
    try:
        atomic(common_directory(repo) / 'crux' / 'pilot' / 'runtime.json', state)
    except OSError as exc:
        raise RuntimeRefusal(f'runtime state unavailable: {exc}') from exc


def allocate(cfg, directory):
    """Use the existing directory census, with a common-Git reservation across worktrees."""
    used = [int(match.group(1)) for path in Path(directory).iterdir()
            if (match := re.search(r'CYC-([0-9]+)$', path.name))]
    floor = max(used, default=0)
    if common_directory(cfg.repo_root) is None:
        number = floor + 1
    else:
        with locked(cfg.repo_root) as state:
            prefix = cfg.artifact_prefix or ''
            reserved = state['counters'].get(prefix, 0)
            if type(reserved) is not int or reserved < 0:
                raise RuntimeRefusal('cycle allocation counter is invalid')
            number = max(floor, reserved) + 1
            state['counters'][prefix] = number
    return f"{cfg.artifact_prefix + '-' if cfg.artifact_prefix else ''}CYC-{number:04d}"


def claim_of(repo, checkout):
    """Inspect a local reservation without changing it or inferring liveness."""
    common = common_directory(repo)
    if common is None:
        return None
    path = common / 'crux' / 'pilot' / 'runtime.json'
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text())
        claims = state['claims']
        if not isinstance(claims, dict):
            raise ValueError('claims is not a mapping')
        return claims.get(str(checkout_root(checkout)))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeRefusal('checkout ownership is unreadable; preserve it and diagnose before editing') from exc


@contextmanager
def admission(repo, enabled=True):
    """Serialize legacy reservation/save with pilot claims, after the legacy cycle lock."""
    try:
        if enabled and common_directory(repo) is not None:
            with locked(repo, wrap_body=False):
                yield
        else:
            yield
    except RuntimeRefusal as exc:
        from cycle_store import CycleError
        raise CycleError(str(exc)) from exc


def require_unclaimed(repo, checkout):
    claim = claim_of(repo, checkout)
    if claim:
        raise RuntimeRefusal(f'checkout held by pilot {claim.get("cycle", "unknown")}/{claim.get("task", "unknown")}; reconcile its owner before editing')


def legacy_holders(repo, docs_root, checkout):
    """Admission-only scan of current legacy editing assignments; historical records are skipped."""
    from cycle_history import edits_main_checkout
    from cycle_store import main_checkout, tree
    repo = main_checkout(repo) or Path(repo)
    docs_root = tree(repo).docs_root
    wanted = checkout_root(checkout)
    found = []
    for path in Path(docs_root).glob('cycles/*/cycle.json'):
        try:
            doc = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            raise RuntimeRefusal(f'cannot establish checkout ownership from {path}') from exc
        if doc.get('format') in WRITER_FORMATS or doc.get('status') not in ('active', 'paused'):
            continue
        tasks = {t['id']: t for t in doc.get('plan', {}).get('tasks', [])}
        for assignment in doc.get('assignments', []):
            task = tasks.get(assignment.get('task'), {})
            if (assignment.get('state') in ('reserved', 'running') and assignment.get('role') in ('developer', 'dev-lead')
                    and (task.get('phase') == 'build' or 'fix' in task)):
                if edits_main_checkout(assignment):
                    owned = checkout_root(repo)
                else:
                    execution = assignment.get('execution') or {}
                    owned_path = execution.get('checkout') if isinstance(execution, dict) else None
                    if not owned_path:
                        # No registered checkout means an isolated host may still be creating it.
                        raise RuntimeRefusal(f'legacy checkout ownership unresolved: {doc["id"]}/{assignment["id"]}')
                    owned = checkout_root(owned_path)
                if owned == wanted:
                    found.append(f"{doc['id']}/{assignment['id']}")
    return found
