"""Project-local skills in cycle dispatch, and the forge-log `used` entries their reports earn.

This module holds the only host-to-root map the cycle engine uses (IDR
local-skill-dispatch-and-use approach 1). Dispatch reads the roots of the attempt's
recorded host, lists each root under fail-closed guards (approach 2), refuses a local
skill that shadows a plugin skill or declares a tool grant (approaches 3 and 4), and
admits a local skill through the predicate plugin eligibility uses (approach 5). A
local candidate changes only the prompt text of an invocation.

The record commit of a completed cycle is the one writer of `used` entries
(approaches 8 and 9). `Flush` writes only when that commit follows at once and no
active or paused cycle holds an open attempt, writes no root whose result would fail
the commit rule, and restores every written root the commit step does not land.
`committable` is the commit rule: a forge log joins a commit only when its working
bytes equal its HEAD bytes plus one contiguous block of entries the engine rederives
from completed cycles' retained reports. Nothing here copies report text into a log.
"""
from __future__ import annotations

import contextlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import subprocess

import cycle_context
import cycle_context_read as reader
from cycle_workflow import CLOSED

# Approach 1: the one root map. OpenCode reads two roots; the first holds precedence.
ROOTS = {
    'claude-code': ('.claude/skills',),
    'codex': ('.agents/skills',),
    'opencode': ('.opencode/skills', '.opencode/skill'),
    'omp': ('.omp/skills',),
}
ALL_ROOTS = tuple(dict.fromkeys(root for roots in ROOTS.values() for root in roots))
MAX_DIRECTORIES = 64
MAX_CANDIDATES = 8
MAX_REPORT_LINES = 16
MAX_FILE_BYTES = reader.MAX_OBJECT_BYTES
SKILL_ID = re.compile(r'[a-z0-9][a-z0-9-]*')
TERM = re.compile(r'[a-z0-9 -]{4,60}')
MAX_TERMS = 8
GRANT_KEYS = ('allowed-tools', 'tools')
REPORT_PREFIX = b'Local-Skill-Used: '
REPORT_LINE = re.compile(r'Local-Skill-Used: ([a-z0-9][a-z0-9-]*) (ok|partial)[ \t]*')
LOG_NAME = 'forge-log.md'
TEMP_PREFIX = '.forge-log-'
TEMP_NAME = re.compile(r'\.forge-log-.*\.tmp')
CYCLE_ID = re.compile(r'(?:[A-Z][A-Z0-9]{1,9}-)?CYC-[0-9]{4,}')
USED_HEADER = re.compile(r'## \[[^\]]*\] used \| ([a-z0-9][a-z0-9-]*)')
ENTRY_HEADER = re.compile(r'## \[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2})\] used \| ([a-z0-9][a-z0-9-]*)')
BODY_KEY = re.compile(r'(\S+) (\S+)/([0-9]+) ')
# forge-skill's locked preamble (crux/skills/forge-skill/SKILL.md, Forge-Log Contract).
# A new log is this preamble followed by one empty line.
PREAMBLE = (b'# Forge log\n\n_Written by forge-skill. Entries newest-first. Events: authored | revised | used | '
            b'evaluated | fallback | escalated | pruned. forge-skill is the sole writer of the lifecycle events '
            b'(authored, revised, pruned); the usage events (used, evaluated, fallback, escalated) are written by '
            b'the session that used the forged skill, in forge-skill\'s locked format._\n')
NEW_LOG = PREAMBLE + b'\n'
# The closed list of reasons a report line records no entry.
IGNORED_REASONS = ('plugin-skill', 'unknown-local-skill', 'no-host', 'no-time', 'over-cap', 'report-changed',
                   'cycle-not-completed', 'no-report-header', 'report-oversized')
OPEN = ('reserved', 'running')
OPEN_RECOVERY = ('resume the cycle and close the attempt (deliver it or mark it lost), or abandon the cycle; '
                 'repair a cycle listed in unreadable_records so its record loads')


# ───────────────────────────── listing (approaches 2 to 5) ─────────────────────────────

def plugin_ids() -> frozenset:
    raw = json.loads((cycle_context.PLUGIN_ROOT / 'catalog/skills.json').read_text())
    return frozenset(item.get('id') for item in raw if isinstance(item, dict) and isinstance(item.get('id'), str))


def root_problem(repo_root: Path, root: str) -> str | None:
    """None when the root and every directory between the repository root and it is a real directory.

    `absent` when a component does not exist; a symlink anywhere on the way refuses."""
    path = Path(repo_root)
    parts = Path(root).parts
    for index, part in enumerate(parts):
        path = path / part
        if path.is_symlink():
            return 'symlink-root' if index == len(parts) - 1 else 'symlink-ancestor'
        if not path.exists():
            return 'absent'
        if not path.is_dir():
            return 'root-not-directory'
    return None


def read_regular(path: Path, limit: int | None = MAX_FILE_BYTES) -> tuple[bytes | None, str | None]:
    """Read a regular file without following a final symlink; (bytes, None) or (None, reason).

    O_NONBLOCK keeps a FIFO from blocking the open; fstat then refuses it as not a regular file.
    `limit=None` reads with no size cap, as the cycle engine's own record loader does."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None, 'missing'
    except OSError:
        return None, 'symlink-or-unreadable'
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return None, 'not-regular-file'
        if limit is not None and info.st_size > limit:
            return None, 'oversized'
        chunks, total = [], 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if limit is not None and total > limit:
                return None, 'oversized'
        return b''.join(chunks), None
    finally:
        os.close(fd)


def _frontmatter(raw: bytes):
    import yaml
    try:
        text = raw.decode('utf-8')
    except UnicodeError:
        return None
    if not text.startswith('---'):
        return None
    pieces = text.split('---', 2)
    if len(pieces) < 3:
        return None
    try:
        header = yaml.safe_load(pieces[1])
    except Exception:  # YAMLError, and RecursionError from deeply nested collections: a refusal never fails a dispatch
        return None
    return header if isinstance(header, dict) else None


def _terms(header):
    metadata = header.get('metadata')
    value = metadata.get('domain_terms') if isinstance(metadata, dict) else None
    if value is None:
        return (), False
    if not isinstance(value, str):
        return (), True
    terms = tuple(term.strip() for term in value.split('|'))
    if not 1 <= len(terms) <= MAX_TERMS or not all(TERM.fullmatch(term) for term in terms):
        return (), True
    return terms, False


def _skill(repo_root: Path, root: str, name: str, plugin: frozenset):
    """(skill, refusals) for one directory entry of a guarded root."""
    if not SKILL_ID.fullmatch(name):
        return None, 'invalid-id'
    if name in plugin:
        return None, 'shadows-plugin-skill'
    root_path = Path(repo_root) / root
    directory = root_path / name
    if directory.is_symlink():
        return None, 'symlink-skill-directory'
    path = directory / 'SKILL.md'
    if path.is_symlink():
        return None, 'symlink-skill-file'
    if not path.exists():
        return None, 'missing-skill-file'
    resolved = path.resolve()
    if not resolved.is_relative_to(root_path.resolve()) or not resolved.is_relative_to(Path(repo_root).resolve()):
        return None, 'escapes-root'
    if reader._forbidden(path.relative_to(repo_root)):
        return None, 'credential-path'
    raw, problem = read_regular(path)
    if raw is None:
        return None, {'missing': 'missing-skill-file', 'symlink-or-unreadable': 'symlink-skill-file'}.get(problem, problem)
    header = _frontmatter(raw)
    if header is None:
        return None, 'invalid-frontmatter'
    if header.get('name') != name:
        return None, 'name-mismatch'
    metadata = header.get('metadata')
    if any(key in header for key in GRANT_KEYS) or (isinstance(metadata, dict) and any(key in metadata for key in GRANT_KEYS)):
        return None, 'declares-tool-grant'
    terms, invalid = _terms(header)
    return {'id': name, 'root': root, 'terms': terms, 'invalid_terms': invalid}, None


def listing(repo_root: Path, host: str, plugin: frozenset | None = None) -> dict:
    """Every local skill of the host's roots that passes approaches 2 to 4, and every refusal.

    A refusal omits that skill and records `{id, root, reason}`; it never fails a dispatch.
    `invalid-domain-terms` is recorded beside a skill that stays listed with no terms."""
    plugin = plugin_ids() if plugin is None else plugin
    skills, refused, seen = [], [], set()
    for root in ROOTS.get(host, ()):
        problem = root_problem(repo_root, root)
        if problem == 'absent':
            continue
        if problem:
            refused.append({'id': None, 'root': root, 'reason': problem})
            continue
        root_path = Path(repo_root) / root
        try:
            names = sorted(entry.name for entry in os.scandir(root_path)
                           if entry.is_symlink() or entry.is_dir(follow_symlinks=False))
        except OSError:
            refused.append({'id': None, 'root': root, 'reason': 'root-unreadable'})
            continue
        if len(names) > MAX_DIRECTORIES:
            refused.append({'id': None, 'root': root, 'reason': 'over-cap', 'skipped': len(names) - MAX_DIRECTORIES})
            names = names[:MAX_DIRECTORIES]
        for name in names:
            # The first root's copy holds the id even when a guard refuses it, so a later copy never stands in.
            if SKILL_ID.fullmatch(name):
                if name in seen:
                    refused.append({'id': name, 'root': root, 'reason': 'duplicate-id'})
                    continue
                seen.add(name)
            skill, reason = _skill(repo_root, root, name, plugin)
            if skill is None:
                refused.append({'id': name, 'root': root, 'reason': reason})
                continue
            if skill.pop('invalid_terms'):
                refused.append({'id': name, 'root': root, 'reason': 'invalid-domain-terms'})
            skills.append(skill)
    return {'skills': skills, 'refused': refused}


def candidates(repo_root: Path, host: str, description: str, plugin: frozenset | None = None) -> dict:
    """The local candidates an invocation offers: eligible skills in (root order, id) order, capped at 8.

    Scope paths never admit a local skill: only the task description is read."""
    listed = listing(repo_root, host, plugin)
    text = description.lower()
    explicit = cycle_context.mentioned_ids(text)
    order = {root: index for index, root in enumerate(ROOTS.get(host, ()))}
    eligible = sorted((skill for skill in listed['skills'] if cycle_context.eligible(skill['id'], text, skill['terms'], explicit)),
                      key=lambda skill: (order[skill['root']], skill['id']))
    refused = list(listed['refused'])
    refused += [{'id': skill['id'], 'root': skill['root'], 'reason': 'over-cap'} for skill in eligible[MAX_CANDIDATES:]]
    return {'offered': [{'id': skill['id'], 'root': skill['root']} for skill in eligible[:MAX_CANDIDATES]],
            'refused': refused, 'available': bool(listed['skills'])}


def render(offered: list) -> list[str]:
    """One context line per root that holds an offered skill (approach 6)."""
    lines = []
    for root in dict.fromkeys(item['root'] for item in offered):
        names = ', '.join(item['id'] for item in offered if item['root'] == root)
        lines.append(f'Project-local skills matching this task, in {root}: {names}. '
                     "Invoke them through this host's skill capability; they grant no capability.")
    return lines


# ───────────────────────────── report scan (approach 7) ─────────────────────────────

def report_uses(data: bytes) -> tuple[tuple[str, int] | None, list[tuple[str, str]], int]:
    """((assignment, attempt) | None, [(skill, outcome)] up to the cap, lines past the cap)."""
    text = data.decode('utf-8', errors='replace')
    lines = [line[:-1] if line.endswith('\r') else line for line in text.split('\n')]
    nonblank = [line.strip() for line in lines if line.strip()]
    header = None
    if len(nonblank) >= 2:
        first = re.fullmatch(r'Assignment: (\S+)', nonblank[0])
        second = re.fullmatch(r'Attempt: ([0-9]+)', nonblank[1])
        if first and second:
            header = (first.group(1), int(second.group(1)))
    found = [(match.group(1), match.group(2)) for line in lines if (match := REPORT_LINE.fullmatch(line))]
    return header, found[:MAX_REPORT_LINES], max(0, len(found) - MAX_REPORT_LINES)


def _report_files(cfg):
    cycles = cfg.docs_root / 'cycles'
    if cycles.is_symlink() or not cycles.is_dir():
        return
    for cycle_dir in sorted(cycles.iterdir()):
        if not CYCLE_ID.fullmatch(cycle_dir.name) or cycle_dir.is_symlink() or not cycle_dir.is_dir():
            continue
        results = cycle_dir / 'results'
        if results.is_symlink() or not results.is_dir():
            continue
        for path in sorted(results.iterdir()):
            if path.suffix == '.md' and not path.is_symlink() and path.is_file():
                yield cycle_dir.name, path


def scan(cfg, plugin: frozenset) -> tuple[dict, list]:
    """Pending uses keyed (skill, cycle, assignment, attempt), and ignored lines with their reasons.

    A byte scan finds candidate reports; a plugin skill id is skipped without reading its record."""
    import hashlib
    uses, ignored = {}, []
    for cycle_id, path in _report_files(cfg):
        data, problem = read_regular(path)
        rel = path.relative_to(cfg.docs_root).as_posix()
        if problem == 'oversized':
            ignored.append({'report': rel, 'id': None, 'reason': 'report-oversized'})
            continue
        if data is None or REPORT_PREFIX not in data:
            continue
        header, found, past = report_uses(data)
        if header is None:
            if found:
                ignored.append({'report': rel, 'id': None, 'reason': 'no-report-header'})
            continue
        if past:
            ignored.append({'report': rel, 'id': None, 'reason': 'over-cap', 'skipped': past})
        sha = hashlib.sha256(data).hexdigest()
        for skill, outcome in found:
            if skill in plugin:
                ignored.append({'report': rel, 'id': skill, 'reason': 'plugin-skill'})
                continue
            key = (skill, cycle_id, header[0], header[1])
            prior = uses.get(key)
            # One use per (cycle, assignment, attempt, skill); conflicting outcomes record partial.
            outcome = outcome if prior is None or prior['outcome'] == outcome else 'partial'
            uses[key] = {'report': rel, 'sha256': sha, 'outcome': outcome}
    return uses, ignored


def _load_record(cfg, cycle_id):
    """(record, None), or (None, 'missing' | 'unreadable' | 'invalid'). No size cap: the engine's loader has none."""
    data, problem = read_regular(cfg.docs_root / 'cycles' / cycle_id / 'cycle.json', limit=None)
    if data is None:
        return None, 'missing' if problem == 'missing' else 'unreadable'
    try:
        doc = json.loads(data)
    except (ValueError, RecursionError):
        # Deeply nested JSON exhausts the parser's recursion limit; that record is unreadable, so it defers.
        return None, 'invalid'
    if (not isinstance(doc, dict) or not isinstance(doc.get('status'), str)
            or not isinstance(doc.get('assignments', []), list)
            or not all(isinstance(entry, dict) for entry in doc.get('assignments', []))):
        return None, 'invalid'
    return doc, None


def _record(cfg, cycle_id, cache):
    if cycle_id not in cache:
        cache[cycle_id] = _load_record(cfg, cycle_id)[0]
    return cache[cycle_id]


def _attempt(doc, assignment, attempt):
    """The attempt entry, current or replaced by a later attempt (kept in its history event)."""
    entries = [*doc.get('assignments', []), *(event['previous'] for event in doc.get('history', [])
                                                if isinstance(event.get('previous'), dict))]
    for entry in entries:
        if entry.get('id') == assignment and entry.get('attempt') == attempt and isinstance(entry.get('delivery'), dict):
            return entry
    return None


def _utc_minute(value):
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        return None
    return moment.astimezone(timezone.utc)


def derive(cfg, key, use, plugin, records, listings):
    """(root, sort key, entry bytes) for a rederivable use, or the reason it records nothing."""
    skill, cycle_id, assignment, attempt = key
    doc = _record(cfg, cycle_id, records)
    if doc is None or doc.get('status') != 'completed':
        return 'cycle-not-completed'
    entry = _attempt(doc, assignment, attempt)
    if entry is None or entry['delivery'].get('path') != use['report'] or entry['delivery'].get('sha256') != use['sha256']:
        return 'report-changed'
    host = entry.get('host')
    if host not in ROOTS:
        return 'no-host'
    moment = _utc_minute(entry.get('ended_at'))
    if moment is None:
        return 'no-time'
    if host not in listings:
        listings[host] = listing(cfg.repo_root, host, plugin)
    root = next((item['root'] for item in listings[host]['skills'] if item['id'] == skill), None)
    if root is None:
        return 'unknown-local-skill'
    text = (f'## [{moment.strftime("%Y-%m-%d %H:%M")}] used | {skill}\n'
            f'{cycle_id} {assignment}/{attempt} {entry.get("role")} report; {use["outcome"]}\n\n')
    return root, (moment.isoformat(), cycle_id, assignment, attempt, skill), text.encode('utf-8')


# ───────────────────────────── the forge log and its commit rule (approach 9) ─────────────────────────────

def presence(data: bytes) -> set:
    """Presence keys (skill, cycle, assignment, attempt) of the `used` entries a log holds."""
    lines = data.decode('utf-8', errors='replace').split('\n')
    found = set()
    for index, line in enumerate(lines[:-1]):
        header = USED_HEADER.fullmatch(line.rstrip('\r'))
        body = BODY_KEY.match(lines[index + 1]) if header else None
        if body:
            found.add((header.group(1), body.group(1), body.group(2), int(body.group(3))))
    return found


def _entry_start(data: bytes) -> int | None:
    if data.startswith(b'## ['):
        return 0
    index = data.find(b'\n## [')
    return None if index < 0 else index + 1


def insert(base: bytes, block: bytes) -> bytes:
    """Insert one block before the first entry, or after the bytes when the log holds none.

    A log with no entry and no trailing LF receives exactly one LF before the block."""
    index = _entry_start(base)
    if index is None:
        return base + (b'\n' if base and not base.endswith(b'\n') else b'') + block
    return base[:index] + block + base[index:]


def inserted_block(working: bytes, head: bytes | None) -> bytes | None:
    """The bytes inserted into the base, or None when `working` is not the base plus one inserted block."""
    base = head if head is not None else NEW_LOG
    index = _entry_start(base)
    prefix, suffix = (base, b'') if index is None else (base[:index], base[index:])
    if len(working) < len(base) or not working.startswith(prefix) or not working.endswith(suffix):
        return None
    middle = working[len(prefix):len(working) - len(suffix)]
    if index is None and base and not base.endswith(b'\n') and middle:
        if not middle.startswith(b'\n'):
            return None
        middle = middle[1:]
    return middle


def committable(working: bytes, head: bytes | None, derived: dict) -> tuple[bool, list]:
    """The commit rule: (passes, inserted presence keys).

    `derived` maps a presence key to the exact entry bytes the engine rederives for it."""
    middle = inserted_block(working, head)
    if middle is None:
        return False, []
    base_keys = presence(head if head is not None else NEW_LOG)
    keys, rest = [], middle
    while rest:
        # Each inserted entry is exactly a header line, one body line and one empty line.
        first = rest.find(b'\n')
        second = rest.find(b'\n', first + 1) if first >= 0 else -1
        if second < 0 or rest[second + 1:second + 2] != b'\n':
            return False, []
        entry = rest[:second + 2]
        header = ENTRY_HEADER.fullmatch(rest[:first].decode('utf-8', errors='replace'))
        body = BODY_KEY.match(rest[first + 1:second].decode('utf-8', errors='replace'))
        if not header or not body:
            return False, []
        key = (header.group(2), body.group(1), body.group(2), int(body.group(3)))
        if key in keys or key in base_keys or derived.get(key) != entry:
            return False, []
        keys.append(key)
        rest = rest[len(entry):]
    return True, keys


def head_blob(cfg, relative: str) -> bytes | None:
    done = subprocess.run(['git', '--no-optional-locks', '-C', str(cfg.repo_root), 'cat-file', 'blob', 'HEAD:' + relative],
                          capture_output=True)
    return done.stdout if done.returncode == 0 else None


def blocking_cycles(cfg) -> tuple[list[str], list[str]]:
    """(cycles that defer a flush, the subset whose record cannot be read).

    A cycle defers when its status is not closed and it holds a reserved or running attempt, or when its
    record exists but cannot be read or has the wrong shape: an unread record may hold an open attempt.
    A cycle directory with no record defers nothing."""
    cycles = cfg.docs_root / 'cycles'
    found, unreadable = [], []
    if cycles.is_symlink() or not cycles.is_dir():
        return found, unreadable
    for cycle_dir in sorted(cycles.iterdir()):
        if not CYCLE_ID.fullmatch(cycle_dir.name) or cycle_dir.is_symlink() or not cycle_dir.is_dir():
            continue
        doc, problem = _load_record(cfg, cycle_dir.name)
        if problem == 'missing':
            continue
        if problem:
            found.append(cycle_dir.name)
            unreadable.append(cycle_dir.name)
        elif doc['status'] not in CLOSED and any(entry.get('state') in OPEN for entry in doc.get('assignments', [])):
            found.append(cycle_dir.name)
    return found, unreadable


def open_attempt_cycles(cfg) -> list[str]:
    """Every cycle that defers a flush (see `blocking_cycles`)."""
    return blocking_cycles(cfg)[0]


def _temporaries(cfg, root):
    path = Path(cfg.repo_root) / root
    if root_problem(cfg.repo_root, root):
        return []
    return sorted(entry for entry in path.iterdir() if TEMP_NAME.fullmatch(entry.name)
                  and not entry.is_symlink() and entry.is_file())


def _root_fd(repo_root, root: str) -> int:
    """A descriptor of `root`, opened one component at a time from the repository root without following a link.

    A root or ancestor swapped to a symlink after the guarded read fails here instead of redirecting a write."""
    fd = os.open(repo_root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in Path(root).parts:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
    except BaseException:
        os.close(fd)
        raise
    return fd


def _unlink(repo_root, relative: str):
    directory = _root_fd(repo_root, PurePosixPath(relative).parent.as_posix())
    try:
        os.unlink(PurePosixPath(relative).name, dir_fd=directory)
    finally:
        os.close(directory)


def _write(repo_root, relative: str, data: bytes):
    """Write through `.forge-log-<random>.tmp` in the log's directory, then rename it over the log.

    Every step resolves names against one directory descriptor opened by `_root_fd`."""
    name = PurePosixPath(relative).name
    temporary = f'{TEMP_PREFIX}{secrets.token_hex(8)}.tmp'
    directory = _root_fd(repo_root, PurePosixPath(relative).parent.as_posix())
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                info = os.stat(name, dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                info = None
            if info is not None and not stat.S_ISREG(info.st_mode):
                raise OSError('forge log is not a regular file')
            os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=directory)
            raise
    finally:
        os.close(directory)


class State:
    """One reading of every root's forge log against the uses the engine rederives."""

    def __init__(self, cfg, plugin=None):
        self.cfg = cfg
        self.plugin = plugin_ids() if plugin is None else plugin
        uses, self.ignored = scan(cfg, self.plugin)
        self.roots = {}
        heads, workings, problems = {}, {}, {}
        for root in ALL_ROOTS:
            relative = f'{root}/{LOG_NAME}'
            problem = root_problem(cfg.repo_root, root)
            path = Path(cfg.repo_root) / relative
            if problem is None and (path.is_symlink() or (path.exists() and not path.is_file())):
                problem = 'forge-log-not-regular'
            working = None
            if problem is None:
                working, failure = read_regular(path)
                if failure not in (None, 'missing'):
                    problem = 'forge-log-' + failure
            heads[root], workings[root], problems[root] = head_blob(cfg, relative), working, problem
        in_head = set().union(*(presence(head) for head in heads.values() if head is not None))
        self.head_present = len(in_head & set(uses))
        records, listings = {}, {}
        # Each rederived entry is keyed by the root that holds its skill: the same bytes in another root are foreign.
        self.derived, self.entries = {root: {} for root in ALL_ROOTS}, {root: [] for root in ALL_ROOTS}
        for key, use in sorted(uses.items()):
            if key in in_head:
                continue
            found = derive(cfg, key, use, self.plugin, records, listings)
            if isinstance(found, str):
                self.ignored.append({'report': use['report'], 'id': key[0], 'reason': found})
                continue
            root, order, entry = found
            self.derived[root][key] = entry
            self.entries[root].append((order, key, entry))
        for root in ALL_ROOTS:
            self.roots[root] = {'path': f'{root}/{LOG_NAME}', 'head': heads[root], 'working': workings[root],
                                'problem': problems[root], 'present': presence(workings[root] or b'') | in_head}

    def missing(self, root):
        info = self.roots[root]
        return sorted((item for item in self.entries[root] if item[1] not in info['present']), reverse=True)

    def check(self, root, working, head):
        return committable(working, head, self.derived[root])


def pending(cfg) -> dict:
    """What inspect reports: `forge_logs` rows and the cycles whose open attempts defer a flush. Reads only."""
    state = State(cfg)
    rows = []
    for root, info in state.roots.items():
        for temporary in _temporaries(cfg, root):
            rows.append({'path': temporary.relative_to(cfg.repo_root).as_posix(), 'state': 'stale-temporary', 'cycles': []})
        if info['problem'] not in (None, 'absent'):
            rows.append({'path': info['path'], 'state': 'foreign', 'cycles': [], 'reason': info['problem'],
                         'resolver': 'main session'})
            continue
        working, head = info['working'], info['head']
        if working is not None and working != head:
            passes, keys = state.check(root, working, head)
            if passes:
                rows.append({'path': info['path'], 'state': 'committable', 'cycles': sorted({key[1] for key in keys})})
            else:
                rows.append({'path': info['path'], 'state': 'foreign', 'cycles': [], 'resolver': 'main session'})
        missing = state.missing(root)
        if missing:
            rows.append({'path': info['path'], 'state': 'missing', 'cycles': sorted({item[1][1] for item in missing})})
    if not rows:
        return {'forge_logs': rows, 'open_attempts': []}
    cycles, unreadable = blocking_cycles(cfg)
    return {'forge_logs': rows, 'open_attempts': cycles, **({'unreadable_records': unreadable} if unreadable else {})}


class Flush:
    """Approach 8: the flush inside the record commit of a completed cycle, under the cycle writer lock."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.written = {}   # relative path -> (prior bytes or None, written bytes)
        self.checked = {}   # relative path -> bytes validated for the commit
        self.report = {'appended': [], 'present': 0, 'ignored': [], 'committed': [], 'uncommitted': [],
                       'deferred': None, 'error': None}

    @property
    def paths(self):
        return list(self.checked)

    def _error(self, root, problem):
        self.report['error'] = [*(self.report['error'] or []), {'root': root, 'problem': problem,
                                                                 'recovery': 'commit-record on any completed cycle'}]

    def prepare(self, deferred):
        """Write each root's missing entries, only when the commit follows at once and the rule passes."""
        if deferred:
            self.report['deferred'] = deferred
            return
        cycles, unreadable = blocking_cycles(self.cfg)
        if cycles:
            self.report.update(deferred='open-attempts', open_attempts=cycles, recovery=OPEN_RECOVERY)
            if unreadable:
                self.report['unreadable_records'] = unreadable
            return
        root = None
        try:
            for root in ALL_ROOTS:
                for temporary in _temporaries(self.cfg, root):
                    temporary.unlink()
            state = State(self.cfg)
            self.report['ignored'] = state.ignored
            self.report['present'] = state.head_present
            for root, info in state.roots.items():
                missing = state.missing(root)
                self.report['present'] += len(state.entries[root]) - len(missing)
                if info['problem'] == 'absent':
                    continue  # no root holds no skill, so no use names it
                if info['problem']:
                    self.report['uncommitted'].append({'path': info['path'], 'reason': info['problem']})
                    continue
                working, head = info['working'], info['head']
                if working is None and head is not None:
                    self.report['uncommitted'].append({'path': info['path'], 'reason': 'absent-working-log'})
                    continue
                if working is not None and working != head and not state.check(root, working, head)[0]:
                    self.report['uncommitted'].append({'path': info['path'], 'reason': 'foreign'})
                    continue
                current = working
                if missing:
                    new = insert(working if working is not None else NEW_LOG, b''.join(item[2] for item in missing))
                    if not state.check(root, new, head)[0]:
                        self.report['uncommitted'].append({'path': info['path'], 'reason': 'foreign'})
                        continue
                    # `_write` renames last, so a write that raises left the log as it was: nothing to restore.
                    _write(self.cfg.repo_root, info['path'], new)
                    self.written[info['path']] = (working, new)
                    self.report['appended'] += [{'path': info['path'], 'id': item[1][0], 'cycle': item[1][1],
                                                 'assignment': item[1][2], 'attempt': item[1][3]} for item in missing]
                    current = new
                if current is not None and current != head:
                    self.checked[info['path']] = current
        except Exception as exc:
            self._error(root, f'{type(exc).__name__}: {exc}'[:300])
            self.restore()
            self.checked = {}

    def restore(self, landed=()):
        """Return every written root the commit step did not land to its pre-flush bytes or absence.

        A root whose bytes changed since the flush wrote them is left alone and reported."""
        for relative, (prior, written) in list(self.written.items()):
            if relative in landed:
                continue
            path = Path(self.cfg.repo_root) / relative
            try:
                current, _ = read_regular(path)
                if current != written:
                    self._error(relative, 'restore-skipped: the bytes changed after the flush wrote them')
                    continue
                if prior is None:
                    _unlink(self.cfg.repo_root, relative)
                else:
                    _write(self.cfg.repo_root, relative, prior)
                del self.written[relative]
            except Exception as exc:
                self._error(relative, f'restore-failed: {type(exc).__name__}: {exc}'[:300])

    def finish(self, result):
        """Compare each staged log with the landed blob, restore what did not land, and return the report."""
        landed = []
        if result.get('changed'):
            for relative, checked in self.checked.items():
                blob = head_blob(self.cfg, relative)
                if blob == checked:
                    landed.append(relative)
                    self.report['committed'].append(relative)
                elif blob is not None and relative in result.get('paths', []):
                    landed.append(relative)
                    self._error(relative, 'committed-bytes-differ: the main session resolves the forge log')
        for relative in self.checked:
            if relative not in landed:
                self.report['uncommitted'].append({'path': relative, 'reason': result.get('deferred') or 'not-landed'})
        self.restore(landed)
        return self.report
