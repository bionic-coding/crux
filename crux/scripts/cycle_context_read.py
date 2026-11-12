"""Read code-owned cycle context without granting arbitrary filesystem access.

The same total bound applies to future retained dispatch snapshots. Pagination
hashes and scans the complete bounded object before returning any UTF-8 text.
Neither listing nor reading writes files, executes project code or selects files from homes.
"""
from __future__ import annotations

from dataclasses import dataclass
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from secret_scan import check_secret_location, scan_text


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
MAX_OBJECT_BYTES = 1024 * 1024
# The live operation log is the one family of objects read under a larger bound: a legacy
# or stray <docs_dir>/log.md, a staged stray under <docs_dir>/log/ and each monthly detail
# file there. Every other object keeps MAX_OBJECT_BYTES. Paging and scans are unchanged.
LOG_OBJECT_BYTES = 8 * 1024 * 1024
MAX_PAGE_BYTES = 16 * 1024
MIN_PAGE_BYTES = 4  # One UTF-8 scalar always fits.
TEXT_SUFFIXES = frozenset({'.md', '.json', '.yaml', '.yml', '.txt', '.tmpl'})
PROJECT_CONTEXT = ('AGENTS.md', 'crux-cycles.md', 'crux-cycle-plan.md',
                   'crux-review-updates.md', 'crux-testing-updates.md')
ARCH_CONTEXT = ('index.md', 'overview.md', 'data-model.md', 'api-surface.md',
                'module-graph.md', 'decision-index.md', '_meta/manifest.json', '_meta/coverage.json')
FORBIDDEN_PARTS = frozenset({'.git', '.aws', '.ssh', '.gnupg', '.azure', '.kube',
                             '.crux', '.bionic', 'secrets', 'secret-store', 'credentials',
                             'keychains', '.npmrc', '.pypirc', '.netrc', '.git-credentials',
                             '.gitcookies', '.docker', '.dockercfg', 'keyrings', '.password-store'})
FORBIDDEN_NAMES = frozenset({'credentials.json', 'credentials.yml', 'credentials.yaml',
                             'secrets.json', 'secrets.yml', 'secrets.yaml', 'id_rsa',
                             'id_ed25519', 'id_ecdsa', 'auth.json', '.credentials.json',
                             'token.json', 'tokens.json', 'credentials.toml', 'secrets.toml'})


def _scan(text):
    """Keep scanner infrastructure failures inside the bounded reader's refusal contract."""
    try:
        return scan_text(text)
    except Exception:
        raise ReadRefused('scanner-unavailable') from None


@dataclass(frozen=True)
class Reference:
    path: Path
    root: Path
    sha256: str | None = None


def _plain(name: str) -> bool:
    return (isinstance(name, str) and bool(name) and '\\' not in name and '\x00' not in name
            and not any(ord(c) < 32 for c in name) and not name.startswith(('~', '/'))
            and all(p not in ('', '.', '..') for p in name.split('/')))


def _forbidden(path: Path) -> bool:
    # Do not consult HOME, CRUX_HOME or any credential store to decide this.
    parts = [p.casefold() for p in path.parts]
    return (any(p in FORBIDDEN_PARTS for p in parts)
            or any(p == '.env' or p.startswith('.env.') or p.endswith('.env') or p == '.envrc'
                   for p in parts)
            or path.name.casefold() in FORBIDDEN_NAMES
            or path.suffix.casefold() in {'.key', '.pem', '.p12', '.pfx', '.keychain', '.keychain-db'})


def _files(root: Path):
    """List text context below a code-selected root, without traversing links."""
    if any(p.is_symlink() for p in (root, *root.parents)):
        return
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and not _forbidden(Path(directory) / d)
                         and not (Path(directory) / d).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            if not name.startswith('.') and path.suffix in TEXT_SUFFIXES and not _forbidden(path):
                yield path


def references(cfg, doc) -> dict[str, Reference]:
    """Canonical context and exact recorded result identities; caller text adds no grant."""
    repo = cfg.repo_root
    plugin = PLUGIN_ROOT
    refs: dict[str, Reference] = {}

    def add(prefix, root, name, digest=None):
        if _plain(name):
            path = root / name
            if not _forbidden(path) and not _scan(str(path)):
                refs[prefix + name] = Reference(path, root, digest)

    for name in PROJECT_CONTEXT:
        add('repo:', repo, name)
    for name in ('AGENTS.md', 'objectives.md'):
        add('repo:', repo, (cfg.docs_root / name).relative_to(repo).as_posix())
    for name in ARCH_CONTEXT:
        add('repo:', repo, (cfg.docs_root / 'arch' / name).relative_to(repo).as_posix())
    # All artifacts under this named cycle are code-owned cycle context. This
    # also covers the immutable invocation snapshots added by the next unit.
    cycle_root = cfg.docs_root / 'cycles' / doc['id']
    add('repo:', repo, (cycle_root / 'cycle.json').relative_to(repo).as_posix())
    for path in _files(cycle_root):
        object_match = re.fullmatch(r'invocations/objects/([0-9a-f]{64})\.md', path.relative_to(cycle_root).as_posix())
        add('repo:', repo, path.relative_to(repo).as_posix(), object_match.group(1) if object_match else None)
    # Code writes queue references into this exact goal block. Ordinary prose,
    # scope paths and arbitrary strings in a report do not authorize reads.
    heading = '\n\nReferences (read before planning; read-only, not scope):\n'
    if heading in doc.get('goal', ''):
        for line in doc['goal'].split(heading, 1)[1].splitlines():
            if line.startswith('- '):
                add('repo:', repo, line[2:])
    for decision in doc.get('decisions', []):
        for key in ('path', 'approval'):
            name = decision.get(key)
            if name and _plain(name):
                add('repo:', repo, (cfg.docs_root / name).relative_to(repo).as_posix(),
                    decision.get('sha256') if key == 'path' else None)
    for path in _files(plugin / 'agents'):
        if path.parent == plugin / 'agents' and path.suffix == '.md':
            add('plugin:', plugin, path.relative_to(plugin).as_posix())
    # Keep canonical singleton references even when a required file is missing.
    for role in ('architect', 'brainstormer', 'commander', 'dev-lead', 'developer',
                 'historian', 'librarian', 'night-gardener', 'reviewer', 'wayfinder'):
        add('plugin:', plugin, f'agents/{role}.md')
    skills = plugin / 'skills'
    if not skills.is_symlink() and skills.is_dir():
        for directory in sorted(skills.iterdir()):
            if directory.is_symlink() or not directory.is_dir():
                continue
            add('plugin:', plugin, f'skills/{directory.name}/SKILL.md')
            for path in _files(directory / 'references'):
                add('plugin:', plugin, path.relative_to(plugin).as_posix())
    for path in _files(plugin / 'schemas'):
        if path.parent == plugin / 'schemas' and path.suffix == '.json':
            add('plugin:', plugin, path.relative_to(plugin).as_posix())
    for entry in doc.get('assignments', []):
        identity = f'{entry["id"]}/{entry["attempt"]}'
        execution = entry.get('execution')
        if execution and _plain(execution['proof']['path']):
            ref = execution['proof']
            refs['execution:' + identity] = Reference(cfg.docs_root / ref['path'], repo, ref['sha256'])
        snapshot = entry.get('invocation_snapshot')
        if snapshot and _plain(snapshot['path']):
            refs['invocation:' + identity] = Reference(cfg.docs_root / snapshot['path'], repo, snapshot['sha256'])
        for previous in entry.get('invocation_history', []):
            if _plain(previous['path']):
                refs['invocation-history:' + identity + '/' + previous['sha256']] = Reference(
                    cfg.docs_root / previous['path'], repo, previous['sha256'])
        name = entry.get('result_path')
        if name:
            path = Path(name)
            path = path if path.is_absolute() else repo / path
            # An external path is permitted only by this exact recorded attempt.
            refs['result:' + identity] = Reference(path, Path(path.anchor))
        delivery = entry.get('delivery')
        if delivery and _plain(delivery['path']):
            refs['retained-result:' + identity] = Reference(cfg.docs_root / delivery['path'], repo, delivery['sha256'])
    return refs


def _reference_view(cfg, doc):
    """Inspect's supported references and commands; listing reads no object content."""
    rows = []
    for name, ref in sorted(references(cfg, doc).items()):
        if _forbidden(ref.path) or _scan(str(ref.path)) or check_secret_location(ref.path):
            continue
        rows.append({'ref': name, 'source_path': str(ref.path),
                     'argv': ['uv', 'run', str(PLUGIN_ROOT / 'scripts/cycle.py'), '--repo-root', str(cfg.repo_root),
                              'context-read', doc['id'], '--ref', name]})
    return {'max_object_bytes': MAX_OBJECT_BYTES, 'max_log_object_bytes': LOG_OBJECT_BYTES,
            'max_page_bytes': MAX_PAGE_BYTES,
            'pagination': 'Use next_offset with the first page sha256; offset and limit count UTF-8 bytes.',
            'references': rows}


def reference_view(cfg, doc):
    """Report unavailable scanning without returning a partial reference roster or changing inspect state."""
    try:
        return _reference_view(cfg, doc)
    except ReadRefused as exc:
        return {'ok': False, 'error': {'code': exc.code}, 'references': [],
                'max_object_bytes': MAX_OBJECT_BYTES, 'max_page_bytes': MAX_PAGE_BYTES}


class ReadRefused(Exception):
    def __init__(self, code, **metadata):
        self.code = code
        self.metadata = metadata


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _bounded_bytes(ref: Reference, *, limit: int = MAX_OBJECT_BYTES) -> bytes:
    """Open every component relative to a no-follow directory descriptor.

    Compare descriptor and path identities before/after reading. Nonblocking open
    and fstat refuse a raced special file without waiting on its writer. `limit`
    defaults to the context bound; identity-only callers may pass a larger one.
    """
    path, root = ref.path, ref.root
    if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(root):
        raise ReadRefused('unsafe-path')
    if (not all(hasattr(os, flag) for flag in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK'))
            or os.open not in os.supports_dir_fd or os.stat not in os.supports_dir_fd
            or os.stat not in os.supports_follow_symlinks):
        raise ReadRefused('read-capability-unavailable')
    descriptors = []
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        # Roots themselves may contain links, so start at the filesystem root.
        directory = os.open(path.anchor, directory_flags)
        descriptors.append(directory)
        parts = path.parts[1:]
        for part in parts[:-1]:
            directory = os.open(part, directory_flags, dir_fd=directory)
            descriptors.append(directory)
        before_path = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
        if stat.S_ISLNK(before_path.st_mode):
            raise ReadRefused('unsafe-path')
        if not stat.S_ISREG(before_path.st_mode):
            raise ReadRefused('not-regular')
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        descriptors.append(descriptor)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or _identity(before) != _identity(before_path):
            raise ReadRefused('object-changed')
        if before.st_size > limit:
            raise ReadRefused('object-too-large', size_bytes=before.st_size, sha256=None)
        chunks = []
        size = 0
        while size <= limit:
            data = os.read(descriptor, min(65536, limit + 1 - size))
            if not data:
                break
            chunks.append(data)
            size += len(data)
        after = os.fstat(descriptor)
        after_path = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
        # Compare the opened leaf with its directory entry after the read.
        if (_identity(before) != _identity(after) or _identity(before) != _identity(after_path)
                or size != before.st_size):
            raise ReadRefused('object-changed')
        if size > limit:
            raise ReadRefused('object-too-large', size_bytes=size, sha256=None)
        # All components remain the directories we opened, even if renamed.
        current = Path(path.anchor)
        for info_fd, part in zip(descriptors[1:-1], parts[:-1]):
            current = current / part
            info = os.stat(current, follow_symlinks=False)
            held = os.fstat(info_fd)
            if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != (held.st_dev, held.st_ino):
                raise ReadRefused('object-changed')
        return b''.join(chunks)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            raise ReadRefused('object-missing') from None
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise ReadRefused('unsafe-path') from None
        raise ReadRefused('object-unreadable') from None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _object_limit(cfg, path: Path) -> int:
    """Return LOG_OBJECT_BYTES for a legacy or stray log.md, a detail file and a staged legacy or stray file."""
    from cycle_workflow import CycleError, contained
    import operation_log as ol
    try:
        log = contained(cfg.docs_root, ol.LEGACY_NAME)
        log_dir = contained(cfg.docs_root, ol.LOG_DIR)
    except CycleError:
        return MAX_OBJECT_BYTES
    if path == log:
        return LOG_OBJECT_BYTES
    if path.parent == log_dir and (ol.DETAIL_NAME.match(path.name)
                                   or ol.STAGED_LEGACY_NAME.match(path.name)
                                   or ol.STAGED_STRAY_NAME.match(path.name)):
        return LOG_OBJECT_BYTES
    return MAX_OBJECT_BYTES


def read_context(cfg, doc, reference, *, offset=0, limit=MAX_PAGE_BYTES, sha256=None):
    """Return one bounded page or a refusal containing no partial file content."""
    metadata = {'ok': False, 'cycle': doc['id']}
    try:
        if not isinstance(reference, str) or ':' not in reference or not _plain(reference.split(':', 1)[1]):
            # Unknown bare names are not interpreted as filesystem paths.
            raise ReadRefused('invalid-reference' if ':' in str(reference) else 'unknown-reference')
        selected = references(cfg, doc).get(reference)
        if selected is None:
            raise ReadRefused('unknown-reference')
        if _forbidden(selected.path) or _scan(str(selected.path)) or check_secret_location(selected.path):
            raise ReadRefused('forbidden-path')
        metadata.update(ref=reference, source_path=str(selected.path))
        if type(offset) is not int or offset < 0:
            raise ReadRefused('invalid-offset')
        if type(limit) is not int or not MIN_PAGE_BYTES <= limit <= MAX_PAGE_BYTES:
            raise ReadRefused('invalid-limit')
        if sha256 is not None and not re.fullmatch('[0-9a-f]{64}', sha256):
            raise ReadRefused('invalid-digest')
        if offset and sha256 is None:
            raise ReadRefused('digest-required')
        data = _bounded_bytes(selected, limit=_object_limit(cfg, selected.path))
        digest = hashlib.sha256(data).hexdigest()
        metadata.update(size_bytes=len(data), sha256=digest)
        if selected.sha256 is not None and selected.sha256 != digest:
            raise ReadRefused('bound-digest-changed')
        if sha256 is not None and sha256 != digest:
            raise ReadRefused('digest-changed')
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            raise ReadRefused('invalid-utf8') from None
        if _scan(text) or _scan(json.dumps(text)):
            raise ReadRefused('secret-detected')
        if offset > len(data) or (offset < len(data) and data[offset] & 0xc0 == 0x80):
            raise ReadRefused('invalid-offset')
        end = min(offset + limit, len(data))
        while end < len(data) and data[end] & 0xc0 == 0x80:
            end -= 1
        return {**metadata, 'ok': True, 'offset': offset, 'limit': limit, 'end_offset': end,
                'next_offset': end if end < len(data) else None, 'complete': end == len(data),
                'text': data[offset:end].decode('utf-8')}
    except ReadRefused as exc:
        return {**metadata, **exc.metadata, 'error': {'code': exc.code}}
