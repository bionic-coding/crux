"""Local facts for optional cycle context and evidence handoffs.

Only catalog descriptions, recorded task/evidence text and worker reports enter
classifier state. Role grants, file contents, commits and receipt validity stay
local. These helpers never dispatch, approve a decision or mutate a cycle.
"""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
import re

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SKILL_ID = re.compile(r'[a-z][a-z0-9-]*')
MAX_CANDIDATES = 16
MAX_REFERENCES = 32
_FACTS = ContextVar('cycle_classification_facts', default=None)
_ADVISORY = ContextVar('cycle_advisory_deadline', default=None)
_PROVIDER_REQUESTS = ContextVar('cycle_provider_requests', default=True)


@contextmanager
def provider_scope(allowed):
    """Provider permission belongs to the explicit operation, never repository text."""
    token = _PROVIDER_REQUESTS.set(bool(allowed))
    try:
        yield
    finally:
        _PROVIDER_REQUESTS.reset(token)


def provider_requests_allowed():
    return _PROVIDER_REQUESTS.get()


def cache_only_operation(function):
    @wraps(function)
    def scoped(*args, **kwargs):
        with provider_scope(False):
            return function(*args, **kwargs)
    return scoped


class AdvisoryUnavailable(TimeoutError):
    """Optional facts could not be completed within the operation's advisory budget."""


@contextmanager
def advisory_scope(deadline=None, *, fresh=False):
    """Share one budget, including discovery and read-only currentness, across an operation."""
    active = _ADVISORY.get()
    if active is not None and not fresh:
        yield active['deadline']
        return
    from crux import decisions
    state = {'deadline': deadline if deadline is not None else decisions.Deadline(), 'exhausted': False}
    token = _ADVISORY.set(state)
    try:
        yield state['deadline']
    finally:
        _ADVISORY.reset(token)


def advisory_deadline():
    active = _ADVISORY.get()
    return active['deadline'] if active is not None else None


def advisory_unavailable():
    active = _ADVISORY.get()
    return active is not None and active['exhausted']


def checkpoint():
    """Yield between local units of work; this cannot preempt one regex or filesystem call."""
    active = _ADVISORY.get()
    if active is not None and active['deadline'].remaining() <= 0:
        active['exhausted'] = True
        raise AdvisoryUnavailable('deadline-exhausted')


def advisory_operation(function):
    @wraps(function)
    def scoped(*args, **kwargs):
        with advisory_scope(kwargs.get('decisions_deadline')):
            return function(*args, **kwargs)
    return scoped


@contextmanager
def facts_scope(*, fresh=False):
    """Share local reads only within one immutable record snapshot, never across a provider call."""
    if not fresh and _FACTS.get() is not None:
        yield
        return
    token = _FACTS.set({})
    try:
        yield
    finally:
        _FACTS.reset(token)


def memo(key, function):
    checkpoint()
    facts = _FACTS.get()
    if facts is None:
        result = function()
        checkpoint()
        return result
    if key not in facts:
        facts[key] = function()
    checkpoint()
    return facts[key]


def available_roles():
    import models_catalog
    try:
        catalog = models_catalog.load()
    except (models_catalog.SpecViolation, OSError, ValueError):
        return set()
    return {role for role in catalog.agents if (PLUGIN_ROOT / 'agents' / (role + '.md')).is_file()}


def streams(doc):
    """Read the writer-validated structured declaration; historical prose is not a declaration."""
    return list(doc['plan'].get('streams', []))


def permitted_roles(doc, task):
    if task['phase'] == 'build':
        independent = [stream for stream in streams(doc) if stream.get('independent') is True]
        units = task.get('integrates', [])
        roles = ['developer']
        if len(independent) >= 2 or len(units) >= 2:
            roles.append('dev-lead')
    else:
        roles = {'plan': ['architect'], 'verify': ['dev-lead'], 'test': ['dev-lead'],
                 'review': ['reviewer'], 'reflect': ['historian'], 'release': ['dev-lead']}.get(task['phase'], [])
    configured = available_roles()
    return [role for role in roles if role in configured]


def role_skills(role):
    path = PLUGIN_ROOT / 'agents' / (role + '.md')
    if role not in available_roles() or path.is_symlink():
        return []
    text = path.read_text()
    header = text.split('---', 2)[1] if text.startswith('---') else ''
    match = re.search(r'^skills:\s*\[([^\]]*)\]', header, re.M)
    return [name.strip().strip('\"\'') for name in match.group(1).split(',') if SKILL_ID.fullmatch(name.strip().strip('\"\''))] if match else []


def candidates(doc, task, role):
    return memo(('skills', doc['id'], doc['revision'], task['id'], role), lambda: _candidates(doc, task, role))


def _candidates(doc, task, role):
    """Offer catalog candidates without preloading their bodies into the classifier."""
    raw = json.loads((PLUGIN_ROOT / 'catalog/skills.json').read_text())
    declared = set(role_skills(role))
    # Repository scope names explain ownership, not the work's domain. In particular
    # "bionic/adrs" must not preload backfill or migration skills into a UI task.
    text = task['description'].lower()
    explicit = set(re.findall(r'(?<![a-z0-9-])([a-z][a-z0-9]+(?:-[a-z0-9]+)+)(?![a-z0-9-])', text))
    domains = {
        'call-llm': ('external model', 'model gateway', 'openrouter', 'classifier', 'decisions api'),
        'council': ('council',),
        'check-drift': ('drift', 'regenerated output', 'generated output'),
        'prose-review': ('prose review', 'writing rules'),
        'log-work': ('journal', 'reflection'),
        'query-docs': ('knowledge retrieval', 'documentation query'),
        'backfill-signoff': ('backfill signoff', 'backfill sign-off'),
        'cleanup-campsite': ('cleanup campsite', 'cleanup-campsite'),
    }
    relevant = []
    for item in raw:
        checkpoint()
        ident = item.get('id', '')
        if not SKILL_ID.fullmatch(ident):
            continue
        if ident in declared or ident == 'cycle' or ident in explicit or any(term in text for term in domains.get(ident, ())):
            relevant.append({'id': ident, 'description': item.get('description', '')})
    relevant.sort(key=lambda item: (item['id'] != 'cycle', item['id'] not in declared, item['id']))
    return relevant[:MAX_CANDIDATES]


def skill_bundle(ident):
    if not isinstance(ident, str) or not SKILL_ID.fullmatch(ident):
        raise ValueError('invalid skill id')
    root = (PLUGIN_ROOT / 'skills').resolve()
    directory = root / ident
    path = directory / 'SKILL.md'
    if directory.is_symlink() or path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError('canonical skill body is unavailable')
    return {'id': ident, 'directory': str(directory.resolve()), 'body': path.read_text()}


def sections(report):
    """Preserve complete report sections locally before state builders apply their bounds."""
    out, title, lines = [], 'Report', []
    for line in report.splitlines():
        checkpoint()
        if re.match(r'^#{1,6}\s+', line):
            if lines:
                out.append({'heading': title, 'text': '\n'.join(lines)})
            title, lines = re.sub(r'^#{1,6}\s+', '', line), []
        else:
            lines.append(line)
    if lines or not out:
        out.append({'heading': title, 'text': '\n'.join(lines)})
    return out


def references(report):
    """Extract citations as data; a model cannot add a filesystem locator."""
    report = '\n'.join(line for line in report.splitlines()
                       if not re.match(r'^(?:Assignment|Attempt|Result-End):', line))
    found = []
    patterns = (
        ('receipt', r'\b(TE-[0-9a-f]{32})\b'),
        ('commit', r'\b(?:commit:|commit\s+)([0-9a-f]{7,64})\b|`([0-9a-f]{7,40})`'),
        ('path', r'(?<![\w/])(?:path:)?((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+(?::[0-9]+(?:-[0-9]+)?)?)'),
        ('path', r'\bpath:([A-Za-z0-9_.-]+(?:\.[A-Za-z0-9]+)(?::[0-9]+(?:-[0-9]+)?)?)'),
    )
    for kind, pattern in patterns:
        checkpoint()
        for match in re.finditer(pattern, report):
            checkpoint()
            value = next(value for value in match.groups() if value is not None)
            if (kind, value) not in found:
                found.append((kind, value))
    return [{'id': f'ref-{index}', 'kind': kind, 'value': value} for index, (kind, value) in enumerate(found)]


def resolve_reference(cfg, reference, delivery):
    """Return currency facts without returning referenced file or receipt contents."""
    from cycle_workflow import contained, run_git
    kind, value = reference['kind'], reference['value']
    checkpoint()
    try:
        if kind == 'path':
            match = re.fullmatch(r'(.+?)(?::([0-9]+)(?:-([0-9]+))?)?', value)
            relative, first, last = match.groups()
            path = contained(cfg.repo_root, relative)
            if path.is_symlink() or not path.is_file():
                return {'valid': False, 'reason': 'path-missing-or-not-regular'}
            data = path.read_bytes()
            if first and not 1 <= int(first) <= int(last or first) <= len(data.splitlines()):
                return {'valid': False, 'reason': 'line-range-outside-file'}
            return {'valid': True, 'sha256': hashlib.sha256(data).hexdigest()}
        if kind == 'commit':
            code, sha = run_git(cfg, 'rev-parse', '--verify', value + '^{commit}')
            if code:
                return {'valid': False, 'reason': 'commit-missing'}
            sha = sha.strip()
            on_head, _ = run_git(cfg, 'merge-base', '--is-ancestor', sha, 'HEAD')
            return {'valid': on_head == 0 or sha in delivery.get('commits', []), 'sha256': sha,
                    'reason': None if on_head == 0 or sha in delivery.get('commits', []) else 'commit-outside-delivery'}
        if kind == 'receipt':
            from test_evidence import validate_evidence
            result = validate_evidence(cfg.repo_root, value)
            return {'valid': result.get('status') == 'passed', 'reason': None if result.get('status') == 'passed' else 'receipt-not-passing'}
    except AdvisoryUnavailable:
        raise
    except Exception as exc:
        return {'valid': False, 'reason': type(exc).__name__}
    return {'valid': False, 'reason': 'unknown-reference-kind'}


def retained_report(cfg, entry):
    from cycle_workflow import CycleError, contained, digest
    delivery = entry.get('delivery') or {}
    path = contained(cfg.docs_root, delivery.get('path', ''))
    if path.is_symlink() or not path.is_file():
        raise CycleError('handoff needs the retained regular report')
    data = path.read_bytes()
    if digest(data) != delivery.get('sha256'):
        raise CycleError('retained report digest changed')
    return data.decode('utf-8')


def report_routes(report):
    """Patterns establish handler prerequisites; they never supply authorization or a finding verdict."""
    patterns = {
        'stale-state-refresh': r'\b(?:stale[- ]revision|revision mismatch|fingerprint mismatch|expect_revision)\b',
        'request-repair': r'\b(?:invalid[- ]json|json parse|unmatched quote|syntax error|invalid-request)\b',
        'environment-investigation': r'\b(?:ModuleNotFoundError|ImportError|PermissionError|command not found|No such file or directory)\b',
    }
    return [route for route, pattern in patterns.items() if re.search(pattern, report, re.I)]


def failed_criteria(cfg, doc, refs):
    """Offer only failed, committed criterion observations the report actually cites."""
    from cycle_workflow import contained, criterion_observation
    found = []
    for ref in refs[:MAX_REFERENCES]:
        checkpoint()
        if ref['kind'] != 'path':
            continue
        relative = re.sub(r':[0-9]+(?:-[0-9]+)?$', '', ref['value'])
        try:
            path = contained(cfg.repo_root, relative)
            if path.suffix != '.json':
                continue
            record = json.loads(path.read_text())
            index = record.get('criterion')
            document_path = path.relative_to(cfg.docs_root).as_posix()
            receipt, _ = criterion_observation(cfg, doc, index, document_path, before=True)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if not any(item['index'] == index for item in found):
            found.append({'index': index, 'observation': receipt['path']})
    return found


def handoff_data(cfg, doc, assignment, attempt):
    return memo(('handoff', doc['id'], doc['revision'], assignment, attempt),
                lambda: _handoff_data(cfg, doc, assignment, attempt))


def _handoff_data(cfg, doc, assignment, attempt):
    from cycle_workflow import CycleError
    entry = next((item for item in doc.get('assignments', []) if item['id'] == assignment and item['attempt'] == attempt), None)
    if entry is None or not entry.get('delivery'):
        return None
    task = next((item for item in doc['plan']['tasks'] if item['id'] == entry['task']), None)
    if task is None:
        raise CycleError('handoff task is missing')
    report = retained_report(cfg, entry)
    refs = references(report)
    checked = {ref['id']: resolve_reference(cfg, ref, entry['delivery']) for ref in refs}
    return {'entry': entry, 'task': task, 'report': report, 'sections': sections(report),
            'references': refs, 'checked': checked}


def context_limit(name='context_keep', default=3):
    from crux import decisions
    basis = decisions.classifier_basis() or {}
    return basis.get(name, default)


def focused_candidates(cfg, doc):
    return memo(('focused', doc['id'], doc['revision']), lambda: _focused_candidates(cfg, doc))


def focused_facts(cfg, doc):
    """Bind scoped current source locally, including work not yet recorded as a delivery."""
    return memo(('focused-source', doc['id'], doc['revision']), lambda: _focused_facts(cfg, doc))


def focused_facts_current(cfg, doc):
    """Fence cached discovery with a fresh source identity before publishing a selection."""
    return focused_facts(cfg, doc) == _focused_facts(cfg, doc)


def _focused_facts(cfg, doc):
    from cycle_classify import changed_paths
    from cycle_workflow import _bookkeeping_entries, _bookkeeping_excluded, scope_name_in_scope, run_git, source_fingerprint
    recorded = any(task.get('commits') for task in doc['plan']['tasks'])
    paths = set(changed_paths(cfg, doc)) if recorded else set()
    for args in (('diff', '--relative', '--no-renames', '--name-only', '-z', 'HEAD'),
                 ('ls-files', '--others', '--exclude-standard', '-z')):
        checkpoint()
        code, output = run_git(cfg, *args)
        if code:
            raise ValueError('cannot establish current focused-test source paths')
        paths.update(name for name in output.split('\0') if name)
    bookkeeping = _bookkeeping_entries(cfg.repo_root)
    selected = []
    for name in sorted(paths):
        checkpoint()
        if scope_name_in_scope(name, doc['plan']['scope']) and not _bookkeeping_excluded(cfg.repo_root, name, bookkeeping):
            selected.append(name)
    paths = selected
    if not paths:
        paths = [name for name in doc['plan']['scope'] if not _bookkeeping_excluded(cfg.repo_root, name, bookkeeping)]
    checkpoint()
    identity = source_fingerprint(cfg.repo_root, doc)
    checkpoint()
    return {'paths': paths, 'source_identity': identity}


def _focused_candidates(cfg, doc):
    import importlib.util
    path = PLUGIN_ROOT / 'scripts/related-tests.py'
    spec = importlib.util.spec_from_file_location('_crux_related_candidate_reader', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, 'extra_candidates'):
        return []
    return module.extra_candidates(cfg.repo_root, focused_facts(cfg, doc)['paths'], checkpoint=checkpoint)


def peer_jobs(cfg, doc, job):
    """Reconstruct hashed wire IDs from code-owned subjects, without storing report text."""
    import cycle_classify as c
    if job.kind == 'context-selection':
        match = re.fullmatch(r'(.+):skill-([0-9]+)', job.subject)
        task = c.task_entry(doc, match.group(1)) if match else None
        role = (job.trigger or '').removeprefix('role:')
        return [c.Job(job.kind, f'{task["id"]}:skill-{index}', job.trigger)
                for index in range(len(candidates(doc, task, role)))] if task else []
    if job.kind == 'handoff-completeness':
        match = re.fullmatch(r'(.+)/([0-9]+)/evidence-([0-9]+)', job.subject)
        data = handoff_data(cfg, doc, match.group(1), int(match.group(2))) if match else None
        return [c.Job(job.kind, f'{match.group(1)}/{match.group(2)}/evidence-{index}')
                for index in range(len(data['task']['expected_evidence']))] if data else []
    if job.kind == 'review-finding-grouping':
        return c.grouping_jobs(cfg, doc)
    if job.kind == 'focused-test-ranking':
        return [c.Job(job.kind, f'candidate-{index}') for index in range(len(focused_candidates(cfg, doc)))]
    return []


def plan_new(cfg, doc, job, repo_root=None):
    """Build each newly admitted question from local facts and recorded fields."""
    import cycle_classify as c
    if doc['status'] != 'active':
        return None
    if job.kind == 'execution-arrangement':
        task = c.task_entry(doc, job.subject)
        if task is None or task['phase'] != doc['phase']:
            return None
        roles = permitted_roles(doc, task)
        if len(roles) < 2:
            return None
        source = {'task': {'id': task['id'], 'description': task['description'], 'depends_on': task['depends_on']},
                  'phase': doc['phase'], 'cycle_type': doc['type'], 'streams': streams(doc),
                  'integrates': task.get('integrates', []), 'permitted_roles': roles}
        state = {**source, 'task': {**source['task'], 'description': c.bounded(task['description'], c.MAX_TASK_CHARS)}}
        return c.sourced(c.Plan(state, roles, c.digest({'phase': doc['phase'], 'task_status': task['status']})), source)
    if job.kind == 'context-selection':
        match = re.fullmatch(r'(.+):skill-([0-9]+)', job.subject)
        role = (job.trigger or '').removeprefix('role:')
        if not match or role not in available_roles():
            return None
        task = c.task_entry(doc, match.group(1))
        if task is None or task['phase'] != doc['phase']:
            return None
        choices = candidates(doc, task, role)
        index = int(match.group(2))
        if index >= len(choices):
            return None
        source = {'task': {'id': task['id'], 'description': task['description']},
                  'role': role, 'phase': doc['phase'], 'cycle_type': doc['type']}
        state = {**source, 'task': {**source['task'], 'description': c.bounded(task['description'], c.MAX_TASK_CHARS)}}
        item_source = {'id': job.subject, 'skill': choices[index]['id'], 'description': choices[index]['description']}
        item = {**item_source, 'description': c.bounded(item_source['description'], 400)}
        return c.sourced(c.Plan(state, ['include', 'omit'], c.digest({'role': role, 'candidates': choices}), item, 'candidates'), source, item_source)
    if job.kind == 'handoff-completeness':
        match = re.fullmatch(r'(.+)/([0-9]+)/evidence-([0-9]+)', job.subject)
        if not match:
            return None
        data = handoff_data(cfg, doc, match.group(1), int(match.group(2)))
        if data is None:
            return None
        index = int(match.group(3))
        expected = data['task']['expected_evidence']
        if index >= len(expected):
            return None
        full_sections = data['sections']
        count = max(1, min(8, len(full_sections)))
        report_sections = [{'heading': c.bounded(part['heading'], 120), 'text': c.bounded(part['text'], 8000 // count)}
                           for part in full_sections[:8]]
        refs = data['references'][:MAX_REFERENCES]
        source = {'task': data['task']['id'], 'sections': full_sections, 'references': data['references']}
        state = {'task': data['task']['id'], 'sections': report_sections, 'references': refs}
        item_source = {'id': job.subject, 'expected': expected[index]}
        item = {**item_source, 'expected': c.bounded(expected[index], 400)}
        routes = ['answered:' + ref['id'] for ref in refs if data['checked'][ref['id']]['valid']]
        routes += ['unsupported', 'unresolved', 'absent']
        policy = {'assignment': data['entry']['id'], 'attempt': data['entry']['attempt'],
                  'delivery': data['entry']['delivery']['sha256'], 'reference_facts': data['checked']}
        return c.sourced(c.Plan(state, routes, c.digest(policy), item, 'items'), source, item_source)
    if job.kind == 'review-finding-grouping':
        match = re.fullmatch(r'(r[0-9]+:(?:blocking|advisory|cosmetic):[0-9]+)/(owner|cause)', job.subject)
        declared = streams(doc)
        if not match or not declared or doc['phase'] != 'review':
            return None
        found = c.finding_at(cfg, doc, match.group(1))
        if found is None:
            return None
        report, number, category, _, item = found
        if number != len(doc['reviews']):
            return None
        all_findings = [{'id': f'r{number}:{group}:{index}', 'title': c.finding_fields(value, clip=False)[0]}
                        for group in ('blocking', 'advisory', 'cosmetic') for index, value in enumerate(report[group])]
        repairs = [task['id'] for task in doc['plan']['tasks'] if task.get('fix')]
        routes = (['stream:' + stream['id'] for stream in declared] if match.group(2) == 'owner'
                  else ['independent', *['finding:' + value['id'] for value in all_findings if value['id'] != match.group(1)],
                        *['repair:' + ident for ident in repairs]])
        source = {'findings': all_findings, 'streams': declared, 'repairs': repairs, 'phase': doc['phase'], 'pass': doc['pass']}
        state = {**source, 'findings': [{**value, 'title': c.bounded(value['title'], 120)} for value in all_findings]}
        original = {'id': job.subject, 'finding': match.group(1), 'category': category,
                    'title': c.finding_fields(item, clip=False)[0]}
        bounded = {**original, 'title': c.bounded(original['title'], 120)}
        return c.sourced(c.Plan(state, routes, c.digest({'review': number, 'repairs': repairs}), bounded, 'questions'), source, original)
    if job.kind == 'focused-test-ranking' and doc['phase'] == 'build':
        found = re.fullmatch(r'candidate-([0-9]+)', job.subject)
        choices = focused_candidates(cfg, doc)
        if not found or int(found.group(1)) >= len(choices):
            return None
        choice = choices[int(found.group(1))]
        original = {'id': job.subject, 'check_id': choice['id'], 'path': choice['path'], 'reason': choice['reason']}
        item = {**original, 'path': c.bounded(original['path'], 120), 'reason': c.bounded(original['reason'], 300)}
        facts = focused_facts(cfg, doc)
        state = {'changed_paths': c.path_bound(facts['paths']), 'phase': doc['phase']}
        source = {'changed_paths': c.path_bound(facts['paths'], clip=False), 'phase': doc['phase'], 'source_identity': facts['source_identity']}
        return c.sourced(c.Plan(state, ['include', 'omit'], c.digest(choices), item, 'candidates'), source, original)
    return None
