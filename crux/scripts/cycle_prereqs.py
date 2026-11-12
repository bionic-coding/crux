"""Environment prerequisites a cycle needs before any work starts.

`cycle.py create` and `queue start-next` call `check` before they write anything. It returns every
missing prerequisite, each with a `code`, an `observed` value and a `fix`, plus `notes` on probes that
found nothing to check. The callers refuse with code `environment-prerequisite` when one is missing.

Three probes, each one subprocess bounded at `TIMEOUT` seconds; a timeout counts as missing:

- Git and an author and committer identity, in every root, because the cycle writer commits its
  records. `git var GIT_AUTHOR_IDENT` and `git var GIT_COMMITTER_IDENT` run in the repository.
  A missing `git` binary is reported with an install fix, not the `git config` fix.
- Each Python minor in the repository's own `pyproject.toml` `[tool.crux] python-versions`
  resolves through `uv python find <minor>`, which downloads nothing. No declared list means no
  check; there is no fallback list. A missing `uv` is reported once, with its own fix.
- `node --version` succeeds when a scope entry equals, contains or lies inside the parent directory
  of a git-tracked test-tiers root whose manifest pattern names TypeScript files. Scope entries are
  resolved through `cycle_workflow.scope_paths`, the helper `create` uses, so `./crux-mods` and
  `crux-mods` match the same root. A repository that is not a git work tree, or a manifest that
  cannot be read, finds no roots: the result notes why and refuses nothing.

Known limit: root discovery runs `git ls-files` through `test_tiers`, whose own timeout is 60 seconds.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import tomllib

import test_tiers

TIMEOUT = 10
CODE = 'environment-prerequisite'
TYPESCRIPT_SUFFIXES = ('.ts', '.tsx', '.mts', '.cts')
IDENTITY_FIX = ("configure a git identity: git config --global user.name 'Your Name' and "
                "git config --global user.email you@example.com (or set them in this repository without --global)")
GIT_FIX = 'install git so `git` is on PATH'
UV_FIX = 'install uv (https://docs.astral.sh/uv/) so `uv` is on PATH'
NODE_FIX = 'install Node.js so `node` is on PATH'


class EnvironmentPrerequisite(Exception):
    """A cycle cannot start: `missing` lists each absent prerequisite with its fix."""

    def __init__(self, missing, notes=()):
        self.missing, self.notes = list(missing), list(notes)
        super().__init__('environment prerequisites missing: '
                         + '; '.join(f"{m['code']} ({m['observed']}): {m['fix']}" for m in self.missing))

    def payload(self):
        return {'ok': False, 'code': CODE, 'error': str(self), 'missing': self.missing,
                **({'notes': self.notes} if self.notes else {})}


def run_probe(argv, cwd):
    """`(returncode, output)` of one probe; raises FileNotFoundError when the binary is absent."""
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f'timed out after {TIMEOUT} seconds'
    return done.returncode, (done.stderr.strip() or done.stdout.strip())


def _last_line(text):
    lines = [line for line in (text or '').splitlines() if line.strip()]
    return lines[-1].strip() if lines else ''


def _probe(runner, argv, cwd):
    """`(ok, observed)`, or `(None, observed)` when the binary is absent."""
    command = ' '.join(argv)
    try:
        code, output = runner(argv, cwd)
    except FileNotFoundError:
        return None, f'{argv[0]}: not found on PATH'
    except OSError as exc:
        return False, f'{command}: {type(exc).__name__}: {exc}'
    if code is None:
        return False, f'{command}: {output}'
    if code != 0:
        return False, f'{command} exited {code}: {_last_line(output)}'.rstrip(': ')
    return True, command


def _identity(repo, runner):
    missing = []
    for code, variable in (('git-author-identity', 'GIT_AUTHOR_IDENT'), ('git-committer-identity', 'GIT_COMMITTER_IDENT')):
        ok, observed = _probe(runner, ['git', 'var', variable], repo)
        if ok is None:
            return [{'code': 'git-missing', 'observed': observed, 'fix': GIT_FIX}]
        if not ok:
            missing.append({'code': code, 'observed': observed, 'fix': IDENTITY_FIX})
    return missing


def declared_minors(repo):
    """The minors `pyproject.toml` declares under `[tool.crux] python-versions`, or `(None, note)`."""
    path = Path(repo) / 'pyproject.toml'
    if not path.is_file():
        return None, None
    try:
        data = tomllib.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return None, f'python minors not checked: cannot read {path.name}: {type(exc).__name__}'
    found = data.get('tool', {}).get('crux', {}).get('python-versions')
    if not found:
        return None, None
    if not isinstance(found, list) or not all(isinstance(m, str) and m.strip() for m in found):
        return None, 'python minors not checked: [tool.crux] python-versions is not a list of strings'
    return [m.strip() for m in found], None


def _minors(repo, runner, notes):
    minors, note = declared_minors(repo)
    if note:
        notes.append(note)
    missing = []
    for minor in minors or ():
        ok, observed = _probe(runner, ['uv', 'python', 'find', minor], repo)
        if ok is None:
            return [{'code': 'uv-missing', 'observed': observed, 'fix': UV_FIX}]
        if not ok:
            missing.append({'code': 'python-minor', 'observed': observed,
                            'fix': f'install Python {minor}: uv python install {minor}'})
    return missing


def typescript_roots(repo, notes):
    """Git-tracked test-tiers roots whose manifest pattern names TypeScript files."""
    try:
        roots, _ = test_tiers.discover_manifests(repo, mode='git')
    except test_tiers.ManifestError as exc:
        notes.append(f'node not checked: no test-tiers roots found ({exc}); a repository that is not a git work tree has none')
        return []
    found = []
    for root in roots:
        try:
            data, _ = test_tiers.read_json(test_tiers.manifest_path(root))
        except test_tiers.ManifestError as exc:
            notes.append(f'node not checked for {root}: {exc}')
            continue
        pattern = data.get('pattern') if isinstance(data, dict) else None
        if isinstance(pattern, str) and pattern.endswith(TYPESCRIPT_SUFFIXES):
            found.append(root.resolve())
    return found


def _in_scope(entries, root):
    parent = root.parent
    return any(e == parent or parent.is_relative_to(e) or e.is_relative_to(parent) for e in entries)


def _node(repo, scope, runner, notes):
    import cycle_workflow
    entries = [path.resolve() for path in cycle_workflow.scope_paths(repo, scope or ())]
    if not entries:
        return []
    roots = [root for root in typescript_roots(repo, notes) if _in_scope(entries, root)]
    if not roots:
        return []
    ok, observed = _probe(runner, ['node', '--version'], repo)
    if ok:
        return []
    return [{'code': 'node-missing', 'observed': observed, 'fix': NODE_FIX}]


def check(repo, scope, runner=run_probe):
    """`{'missing': [...], 'notes': [...]}` for the repository root `repo` and the cycle's `scope` entries."""
    repo = Path(repo).resolve()
    notes = []
    missing = _identity(repo, runner) + _minors(repo, runner, notes) + _node(repo, scope, runner, notes)
    return {'missing': missing, 'notes': notes}


def require(repo, scope, runner=run_probe):
    """Raise `EnvironmentPrerequisite` when `check` finds a missing prerequisite."""
    result = check(repo, scope, runner)
    if result['missing']:
        raise EnvironmentPrerequisite(result['missing'], result['notes'])
    return result
