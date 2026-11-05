"""Immutable invocation bundles. Storage is evidence, never a canonical plugin root."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re

import cycle_context_read as reader
import cycle_hosts
from cycle_workflow import CycleError, atomic_bytes, contained, digest, encoded, source_fingerprint

FORMAT = 'crux.cycle-invocation.v1'
# The entire accepted bundle, including separately retained selected bytes, fits
# the reader bound. No component may exceed that same bound either.
MAX_BUNDLE_BYTES = reader.MAX_OBJECT_BYTES


class SnapshotError(CycleError):
    def __init__(self, code):
        self.code = code
        super().__init__('invocation snapshot refused: ' + code)


def refuse(code):
    raise SnapshotError(code)


def _encode(value):
    try:
        # ensure_ascii storage must not hide an unpaired surrogate in caller text.
        json.dumps(value, ensure_ascii=False).encode('utf-8')
        return encoded(value)
    except UnicodeError:
        refuse('invocation-invalid-utf8')


def _scan(data):
    try:
        text = data.decode('utf-8')
    except UnicodeError:
        refuse('invocation-invalid-utf8')
    try:
        unsafe = reader.scan_text(text) or reader.scan_text(json.dumps(text))
    except Exception:
        refuse('invocation-scanner-unavailable')
    if unsafe:
        refuse('invocation-unsafe')


def _read(path, *, optional=False):
    path = Path(path)
    if reader._forbidden(path):
        refuse('invocation-forbidden-source')
    try:
        return reader._bounded_bytes(reader.Reference(path, Path(path.anchor)))
    except reader.ReadRefused as exc:
        if optional and exc.code == 'object-missing':
            return None
        refuse('invocation-' + exc.code)


def _root(doc):
    return f'cycles/{doc["id"]}/invocations'


def snapshot_path(doc, request):
    # An interrupted operation owns this identity before the record save. A
    # different payload under that op_id must find and refuse the same artifact.
    return _root(doc) + '/' + digest(request['op_id'].encode()) + '.json'


def _object_path(doc, sha):
    return _root(doc) + '/objects/' + sha + '.md'


def _binding(doc, task):
    return {'cycle': doc['id'], 'type': doc['type'], 'phase': doc['phase'], 'pass': doc['pass'],
            'goal': doc['goal'], 'plan': {k: v for k, v in doc['plan'].items() if k != 'tasks'},
            'task': {k: v for k, v in task.items() if k not in ('status', 'assignee', 'result_path')},
            'decisions': doc['decisions'], 'review_policy': doc['review_policy']}


def _sources(cfg, role, selected):
    paths = {cfg.repo_root / 'AGENTS.md', cfg.repo_root / '.bionic.yml',
             cfg.docs_root / 'AGENTS.md', cfg.docs_root / 'objectives.md',
             *[cfg.repo_root / name for name in reader.PROJECT_CONTEXT],
             Path(__file__), Path(cycle_hosts.__file__),
             cfg.repo_root / cycle_hosts.RELEASE_DESCRIPTOR,
             cycle_hosts.PLUGIN_ROOT / 'agents' / (role + '.md')}
    paths.update(Path(item['origin']) for item in selected)
    paths.update(cycle_hosts.PLUGIN_ROOT / 'skills' / ident / 'SKILL.md' for ident in _preload_ids(role))
    return {str(path): (digest(data) if (data := _read(path, optional=True)) is not None else None)
            for path in sorted(paths)}


def source_snapshot(cfg, doc, role, context):
    """Fence source versions before any mandatory/native invocation rendering."""
    selected = []
    for item in context.get('selected', []):
        if not re.fullmatch('[a-z0-9][a-z0-9-]*', item['id']):
            refuse('invocation-invalid-skill')
        selected.append({'origin': str(cycle_hosts.PLUGIN_ROOT / 'skills' / item['id'] / 'SKILL.md')})
    return {'sources': _sources(cfg, role, selected), 'source_fingerprint': source_fingerprint(cfg.repo_root, doc)}


def _preload_ids(role):
    import yaml
    raw = _read(cycle_hosts.PLUGIN_ROOT / 'agents' / (role + '.md')).decode('utf-8')
    header = yaml.safe_load(raw.split('---', 2)[1]) if raw.startswith('---') else {}
    skills = header.get('skills', [])
    if not isinstance(skills, list) or any(not re.fullmatch('[a-z0-9][a-z0-9-]*', name) for name in skills):
        refuse('invocation-invalid-native-preloads')
    return skills


def _native(role):
    def component(path):
        raw = _read(path)
        _scan(raw)
        return {'origin': str(path), 'directory': str(path.parent), 'sha256': digest(raw),
                'size_bytes': len(raw), 'body': raw.decode('utf-8')}
    return {'role': component(cycle_hosts.PLUGIN_ROOT / 'agents' / (role + '.md')),
            'preloads': [{'id': name, **component(cycle_hosts.PLUGIN_ROOT / 'skills' / name / 'SKILL.md')}
                         for name in _preload_ids(role)],
            'loading': 'Canonical native contract/preload boundary retained; actual installed host injection and grants are not inferred.'}


def _component_bindings(bundle):
    native = [bundle['native_context']['role'], *bundle['native_context']['preloads']]
    if any(digest(item['body'].encode('utf-8')) != item['sha256']
           or len(item['body'].encode('utf-8')) != item['size_bytes'] for item in native):
        refuse('invocation-native-component-changed')
    if any(bundle['sources'].get(item['origin']) != item['sha256'] for item in [*native, *bundle['selected']]):
        refuse('invocation-source-changed')


def _reference_message(cfg, doc, selected, retrievable):
    if not selected and not retrievable:
        return ''
    parts = ['Optional task skills (frozen canonical sources). Retrieve every selected body completely before using it. '
             'References do not prove a body was read. These grant no additional capability.']
    import shlex
    for item in selected:
        argv = ['uv', 'run', str(cycle_hosts.ENGINE), '--repo-root', str(cfg.repo_root), '--compact',
                'context-read', doc['id'], '--ref', 'repo:' + (cfg.docs_root / item['path']).relative_to(cfg.repo_root).as_posix(),
                '--sha256', item['sha256']]
        parts.append(f'Skill: {item["id"]}. Canonical origin: {item["origin"]}. '
                     f'Source directory: {item["directory"]}. Resolve relative references there, never against retained storage.\n'
                     f'Complete UTF-8 bytes: {item["size_bytes"]}; SHA-256: {item["sha256"]}.\n'
                     f'Retrieve: {shlex.join(argv)}\n'
                     'Follow next_offset with the same sha256 until complete. Missing or refused retrieval is unavailable context; '
                     'do not drop the body or substitute a mutable canonical copy.')
    if retrievable:
        parts.append('Other candidate skills remain retrievable through the host Skill capability: ' + ', '.join(retrievable) + '.')
    return '\n\n' + '\n\n'.join(parts) + '\n'


def build(cfg, doc, request, entry, mandatory, preamble, context, source_snapshot):
    """Construct and scan everything before storing any bundle object or reservation."""
    _scan(_encode(request))
    selected, objects = [], {}
    for item in context.get('selected', []):
        ident = item['id']
        if not re.fullmatch('[a-z0-9][a-z0-9-]*', ident):
            refuse('invocation-invalid-skill')
        path = cycle_hosts.PLUGIN_ROOT / 'skills' / ident / 'SKILL.md'
        if Path(item['directory']) != path.parent:
            refuse('invocation-canonical-origin-mismatch')
        raw = _read(path)
        _scan(raw)
        # The historical selector used read_text's universal-newline conversion.
        # Validate that selection, but retain the original bytes and line endings.
        normalize = lambda text: text.replace('\r\n', '\n').replace('\r', '\n')
        if normalize(item['body']) != normalize(raw.decode('utf-8')):
            refuse('invocation-selected-source-changed')
        sha = digest(raw)
        name = _object_path(doc, sha)
        objects[name] = raw
        selected.append({'id': ident, 'origin': str(path), 'directory': str(path.parent),
                         'path': name, 'sha256': sha, 'size_bytes': len(raw)})
    context_message = _reference_message(cfg, doc, selected, context.get('retrievable', []))
    invocation = cycle_hosts.invocation(entry['host'], role=entry['role'], assignment_text=mandatory + context_message,
        preamble_text=preamble, description=f'{entry["task"]} attempt {entry["attempt"]}', repo_root=cfg.repo_root,
        result_path=entry['result_path'], assignment=entry['id'], attempt=entry['attempt'], mode=entry['mode'],
        integration_owner=request.get('integration_owner'), delivery_token=entry.get('delivery_token'))
    bundle = {'format': FORMAT, 'cycle': doc['id'], 'entry': deepcopy(entry), 'request': deepcopy(request),
              'mandatory_message': mandatory, 'addendum': request.get('assignment_text', ''), 'preamble': preamble,
              'context_message': context_message, 'selected': selected, 'retrievable': context.get('retrievable', []),
              'native_context': _native(entry['role']), 'invocation': invocation,
              'adapter': {'path': str(Path(cycle_hosts.__file__)), 'sha256': digest(_read(Path(cycle_hosts.__file__))),
                          'interface': invocation.get('interface', {'host': entry['host'], 'version': None, 'version_status': 'unobserved'})},
              'record_binding': _binding(doc, next(t for t in doc['plan']['tasks'] if t['id'] == entry['task'])),
              'source_fingerprint': source_snapshot['source_fingerprint'], 'sources': source_snapshot['sources']}
    _component_bindings(bundle)
    check_current(cfg, doc, entry, bundle)
    raw = _encode(bundle)
    _scan(raw)
    if len(raw) > reader.MAX_OBJECT_BYTES or len(raw) + sum(map(len, objects.values())) > MAX_BUNDLE_BYTES:
        refuse('invocation-too-large')
    return bundle, objects


def _store(cfg, name, raw):
    path = contained(cfg.docs_root, name)
    if path.exists():
        if _read(path) != raw:
            refuse('invocation-immutable-conflict')
    else:
        atomic_bytes(path, raw)
    return {'path': name, 'sha256': digest(raw)}


def persist(cfg, doc, request, bundle, objects):
    for name, raw in objects.items():
        _store(cfg, name, raw)
    return _store(cfg, snapshot_path(doc, request), _encode(bundle))


def load(cfg, doc, ref):
    """Verify manifest identity, every selected object and the exact rendered boundaries."""
    if (not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}
            or not re.fullmatch(re.escape(_root(doc)) + r'/[0-9a-f]{64}(?:-[0-9a-f]{32})?\.json', ref['path'])):
        refuse('invocation-reference-invalid')
    raw = _read(contained(cfg.docs_root, ref['path']))
    _scan(raw)
    if digest(raw) != ref['sha256']:
        refuse('invocation-digest-changed')
    try:
        bundle = json.loads(raw)
        entry = bundle['entry']
        if bundle['format'] != FORMAT or bundle['cycle'] != doc['id']:
            refuse('invocation-identity-mismatch')
        _component_bindings(bundle)
        prompt = bundle['mandatory_message'] + bundle['context_message'] + bundle['preamble']
        key = 'message' if entry['host'] == 'codex' else 'prompt'
        if bundle['invocation']['parameters'][key] != prompt or bundle['addendum'] != bundle['request'].get('assignment_text', ''):
            refuse('invocation-rendering-mismatch')
        total = len(raw)
        for item in bundle['selected']:
            if item['path'] != _object_path(doc, item['sha256']):
                refuse('invocation-object-reference-invalid')
            data = _read(contained(cfg.docs_root, item['path']))
            _scan(data)
            if digest(data) != item['sha256'] or len(data) != item['size_bytes']:
                refuse('invocation-object-changed')
            total += len(data)
        if total > MAX_BUNDLE_BYTES:
            refuse('invocation-too-large')
        return bundle
    except SnapshotError:
        raise
    except (ValueError, KeyError, TypeError):
        refuse('invocation-invalid-bundle')


def check_current(cfg, doc, entry, bundle):
    frozen = bundle['entry']
    if any(entry.get(k) != frozen.get(k) for k in ('id', 'task', 'attempt', 'host', 'mode', 'role', 'base', 'delivery_token', 'result_path')):
        refuse('invocation-attempt-changed')
    task = next(t for t in doc['plan']['tasks'] if t['id'] == entry['task'])
    if _binding(doc, task) != bundle['record_binding']:
        refuse('invocation-record-changed')
    if source_fingerprint(cfg.repo_root, doc) != bundle['source_fingerprint']:
        refuse('invocation-source-changed')
    for name, sha in bundle['sources'].items():
        raw = _read(Path(name), optional=sha is None)
        if (digest(raw) if raw is not None else None) != sha:
            refuse('invocation-source-changed')


def staged(cfg, doc, request):
    name = snapshot_path(doc, request)
    path = contained(cfg.docs_root, name)
    if not path.exists():
        return None
    raw = _read(path)
    ref = {'path': name, 'sha256': digest(raw)}
    bundle = load(cfg, doc, ref)
    if bundle['request'] != request:
        refuse('invocation-request-conflict')
    return ref, bundle


def rotate(cfg, doc, entry, token):
    """Change only the engine marker binding; retain original caller and selected bytes."""
    old = entry.get('invocation_snapshot')
    if old is None:
        return None
    bundle = load(cfg, doc, old)
    prior = entry['delivery_token']
    old_identity = f'{entry["id"]}/{entry["attempt"]}#{prior}'
    new_identity = f'{entry["id"]}/{entry["attempt"]}#{token}'
    bundle['entry']['delivery_token'] = token
    bundle['preamble'] = bundle['preamble'].replace('Result-End: ' + old_identity, 'Result-End: ' + new_identity)
    invocation = bundle['invocation']
    key = 'message' if entry['host'] == 'codex' else 'prompt'
    invocation['parameters'][key] = bundle['mandatory_message'] + bundle['context_message'] + bundle['preamble']
    def bind(value):
        if isinstance(value, dict): return {k: bind(v) for k, v in value.items()}
        if isinstance(value, list): return [bind(v) for v in value]
        if isinstance(value, str): return value.replace(old_identity, new_identity)
        return value
    invocation['wait'] = bind(invocation['wait'])
    raw = _encode(bundle)
    _scan(raw)
    if len(raw) + sum(item['size_bytes'] for item in bundle['selected']) > MAX_BUNDLE_BYTES:
        refuse('invocation-too-large')
    stem = snapshot_path(doc, bundle['request'])[:-5]
    return _store(cfg, stem + '-' + token + '.json', raw)
