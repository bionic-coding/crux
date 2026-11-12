"""Route classification for the cycle engine: policy, state, orchestration and records.

The engine asks versioned Decisions questions and routes on each answer only inside a boundary that
code computes from cycle facts. This module owns everything between the triggering
operation and the stored entry. The transport (`crux.decisions`) owns the wire; the
question text lives in `cycle_questions`.

Flow of one classification (IDR decision-transport-and-routing, revision 4):

1. Code computes the permitted routes and the floor from the record (`plan_of`) and builds
   the state from the permitted record fields only (`STATE_FIELDS`).
2. The request is sent with the cycle lock released, under one `Deadline` that every call of
   the operation shares.
   Questions that share one kind and one state go in one request (`batches`): the review-routing
   predicates of one review, and the finding dispositions of one report over a shared review state that
   lists the batch's findings. A request holds at most `decisions.MAX_QUESTIONS_PER_REQUEST` questions and
   a state within the input bound; requests for unrelated states run with at most
   `decisions.REQUEST_CONCURRENCY` at once (IDR luna-classification-expansion approaches 2 and 10).
3. One locked transaction rebuilds the decision input and permitted routes. An identical
   input reuses its valid answer and names the original request. A changed input is asked
   once more, then falls back as `stale` if it changes again. Bookkeeping revisions alone
   never discard an answer.
4. The engine records the route and offers it through `inspect`. It never dispatches, marks
   an attempt lost, returns or adds a fix task on an answer. Work sizing at creation is the
   one route it applies itself.

An entry never carries state text. Its fingerprint includes rendered state, a local
digest of complete source fields, questions, options, policy and model configuration.
When the classifier is unconfigured nothing is built, sent or recorded.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import fnmatch
import hashlib
import json
from pathlib import Path
import re

from crux import decisions

import bionic_config
import cycle_questions as questions
import cycle_context as advisory
from cycle_workflow import (
    CHECK_PHASES, CLOSED, FINDING_ID, OPEN, PHASES, CycleError, dependency_satisfied, event, fix_step_problem, load, locked, now, read_retained, run_git, save, tree,
)

# `execution-arrangement` left this set in CYC-0127: every phase permits one role, so no writer asked it.
# A historical classification of that kind stays readable in the record and is never revalidated.
KINDS = ('work-sizing', 'review-routing', 'finding-disposition', 'failure-routing',
         'context-selection', 'handoff-completeness', 'review-finding-grouping', 'focused-test-ranking')
# Version 2 partial-reuse records may misstate wire membership; never reuse them.
ROUTING_POLICY_VERSION = '4'
# Fallback strings the engine adds to the transport's `decisions.FALLBACKS`. The transport's status is
# recorded verbatim for every other fallback.
ENGINE_FALLBACKS = ('insufficient-information', 'route-not-permitted', 'policy-refused', 'stale')
RETURN_PHASES = (*CHECK_PHASES, 'review')
SIZING_RECEIPT_FIELDS = ('request_id', 'question_set', 'question_version', 'model', 'served_model', 'answer', 'fallback')
# Fields a receipt may also carry; a receipt written before they existed omits them.
SIZING_RECEIPT_OPTIONAL = ('served_provider', 'cost', 'fingerprint', 'question_ids')

MAX_PATHS = 10
MAX_PATH_CHARS = 120
MAX_TITLE_CHARS = 120
MAX_FINDING_CHARS = 600
MAX_TASK_CHARS = 300
MAX_LIST = 8
MAX_SUMMARY_IDS = 5
MAX_LOG_BYTES = 400_000

# The record fields each state may read. The state builders below read nothing else.
STATE_FIELDS = {
    'work-sizing': ('title', 'goal', 'scope', 'acceptance'),
    'review-routing': ('phase', 'pass', 'scrutiny', 'risks', 'floor', 'changed_paths', 'tasks'),
    'finding-disposition': ('findings', 'review', 'phase', 'pass'),
    'failure-routing': ('trigger', 'task', 'attempt', 'attempts_in_pass', 'attempt_limit', 'check', 'summary', 'phase', 'pass', 'report', 'failed_criteria', 'handoff_unresolved'),
}
# The review facts every finding of one report shares; named here so the finding state cannot grow past them.
SHARED_REVIEW_FACTS = ('verdict', 'scrutiny', 'pass', 'counts', 'changed_paths', 'required_checks')

# Specialists the review floor may require. `paths` are lower-case fnmatch globs over changed path names;
# `risks` are review_policy risk tags (a tag equal to the specialist id also counts); `covers` names the
# escalation triggers of crux/skills/cycle/references/review.md that the specialist answers; `concern` names the
# concern a specialist reviews, and the review block keeps one specialist per concern.
SPECIALISTS = {
    'credentials-and-data-transmission': {
        'concern': 'credentials-and-data-transmission',
        'paths': ('*secret*', '*credential*', '*.env', '*crux_env*', '*crux/decisions/*', '*llm_caller*', '*openrouter*'),
        'risks': ('credentials', 'sensitive-data', 'sensitive data', 'encryption', 'data-transmission'),
        'covers': ('credentials/sensitive data/encryption',)},
    'model-routing-boundary': {
        'concern': 'model-routing-boundary',
        'paths': ('*llm_router*', '*/_config/*', '*models.yml', '*model_roles*'),
        'risks': ('model-routing', 'external-model'),
        'covers': ()},
    'recovery-and-destructive-operations': {
        'concern': 'recovery-and-destructive-operations',
        'paths': ('*migrat*', '*recover*', '*backup*', '*restore*', '*purge*', '*delete*'),
        'risks': ('destructive-operations', 'migration', 'recovery'),
        'covers': ('destructive operations/migrations/recovery',)},
    'release-distribution': {
        'concern': 'release-distribution',
        'paths': ('*release*', 'sync.sh', '*plugin.json', '*marketplace.json', 'pyproject.toml', '*package.json', '*requirements*.txt',
                  'uv.lock', '.github/workflows/*'),
        'risks': ('release', 'dependency-installation', 'distribution'),
        'covers': ('dependency installation/release distribution',)},
    'authentication-and-authorization': {
        'concern': 'authentication-and-authorization',
        'paths': ('*/auth*', 'auth*', '*_auth*', '*authn*', '*authz*', '*permission*', '*tenant*', '*login*'),
        'risks': ('authentication', 'authorization', 'tenant-isolation', 'privilege'),
        'covers': ('authentication/authorization/tenant isolation',)},
    'untrusted-input-execution': {
        'concern': 'untrusted-input-execution',
        'paths': ('*exec*', '*shell*', '*eval*', '*upload*', '*sandbox*'),
        'risks': ('untrusted-input', 'execution', 'file-operations'),
        'covers': ('untrusted input reaching execution or file operations',)},
}

# Refusal codes that trigger failure routing, and whether the subject is the request's task or its assignment.
REFUSAL_TRIGGERS = {
    'unresolved-dispatch': 'task_id',
    'attempt-limit': 'task_id',
    'delivery-conflict': 'assignment',
    'superseded-attempt': 'assignment',
    # No mutating operation refuses with this code today: it is an inspect problem, and inspect writes nothing.
    'result-path-missing': 'assignment',
}


@dataclass(frozen=True)
class Job:
    """One question to classify. Deduplication also requires an unchanged input fingerprint."""

    kind: str
    subject: str
    trigger: str | None = None


@dataclass
class Plan:
    """What code computed for one question: the shared state, the permitted routes and the policy fingerprint.

    `item` is the question's own part of a batched state, listed under `item_field` beside the other
    questions' parts; a plan without one shares `state` whole."""

    state: dict
    routes: list
    fingerprint: str | None
    item: dict | None = None
    item_field: str | None = None
    source: dict | None = None
    request_state: dict | None = None
    question_ids: tuple[str, ...] = ()          # membership of the outcome's request
    context_question_ids: tuple[str, ...] = ()  # cohort rebuilding its bound state/source digest
    question_version: str | None = None
    reused_from: dict | None = None
    policy_fingerprint: str | None = field(init=False)

    def __post_init__(self):
        self.policy_fingerprint = self.fingerprint

    def full_state(self) -> dict:
        """The state of this question asked alone."""
        return self.state if self.item_field is None else {**self.state, self.item_field: [self.item]}


# ───────────────────────────── configuration ─────────────────────────────

def classifier_state(repo_root) -> dict:
    """{configured, reason}: the repository opt-out and the transport's own check, combined."""
    if dict(decisions.REQUIRED_DENIALS) != {'data_collection': 'deny'}:
        return {'configured': False, 'reason': 'data-policy-changed'}
    try:
        policy = bionic_config.load_decisions_policy(repo_root)
    except (bionic_config.BionicConfigError, OSError):
        return {'configured': False, 'reason': 'configuration-error'}
    if policy['classifier'] == 'off':
        return {'configured': False, 'reason': 'opted-out'}
    status = decisions.classifier_status()
    return {'configured': bool(status.configured), 'reason': status.reason}


# ───────────────────────────── local input helpers ─────────────────────────────

def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def bounded(text, limit) -> str:
    return ' '.join(str(text).split())[:limit]


def clipping(source, sent, path='') -> dict:
    """Paths and original lengths of every string or list the state builder clipped."""
    found = {}
    if isinstance(source, (str, list)) and isinstance(sent, type(source)) and len(source) > len(sent):
        found[path] = {'clipped': True, 'original_length': len(source)}
    if isinstance(source, dict) and isinstance(sent, dict):
        for key in sent.keys() & source.keys():
            found.update(clipping(source[key], sent[key], f'{path}.{key}' if path else key))
    elif isinstance(source, list) and isinstance(sent, list):
        for index, (original, value) in enumerate(zip(source, sent)):
            found.update(clipping(original, value, f'{path}[{index}]'))
    return found


def sourced(plan, source, item_source=None):
    """Keep complete source fields local; only clipping metadata joins the request."""
    marks = clipping(source, plan.state)
    if marks:
        plan.state['clipped'] = marks
    plan.source = source
    if plan.item is not None:
        marks = clipping(item_source, plan.item)
        if marks:
            plan.item['clipped'] = marks
        plan.source = {'shared': source, 'item': item_source}
    return plan


def task_entry(doc, ident):
    return next((t for t in doc['plan']['tasks'] if t['id'] == ident), None)


def assignment_entry(doc, ident):
    return next((a for a in doc.get('assignments', []) if a['id'] == ident), None)


def task_assignments(doc, task_id):
    return [(a['id'], a['attempt'], a['state'], (a.get('delivery') or {}).get('outcome')) for a in doc.get('assignments', []) if a['task'] == task_id]


def path_bound(paths, *, clip=True) -> dict:
    return {'count': len(paths), 'first': [bounded(p, MAX_PATH_CHARS) for p in paths[:MAX_PATHS]] if clip else list(paths)}


# ───────────────────────────── facts: paths, floor, findings ─────────────────────────────

def changed_paths(cfg, doc) -> list:
    """Path names touched by the commits the tasks record; the plan scope when no commit is recorded."""
    seen = set()
    for sha in dict.fromkeys(c for t in doc['plan']['tasks'] for c in t.get('commits', [])):
        code, out = run_git(cfg, 'diff-tree', '--no-commit-id', '--name-only', '-r', '--root', '-z', sha)
        if code == 0:
            seen.update(name for name in out.split('\0') if name)
    return sorted(seen or doc['plan']['scope'])


def review_floor(cfg, doc) -> dict:
    """The specialists review requires, from changed paths, risk tags and cycle facts, whatever the cycle type."""
    paths = changed_paths(cfg, doc)
    risks = {r.strip().lower() for r in doc['review_policy']['risks']}
    sources = {}
    for ident, spec in SPECIALISTS.items():
        hits = []
        for path in paths:
            if any(fnmatch.fnmatchcase(path.lower(), glob) for glob in spec['paths']):
                hits.append('path:' + bounded(path, MAX_PATH_CHARS))
                if len(hits) == 3:
                    break
        hits += ['risk:' + tag for tag in sorted(risks & {ident, *spec['risks']})]
        if hits:
            sources[ident] = hits
    return {'specialists': list(sources), 'sources': sources, 'scrutiny': doc['review_policy']['scrutiny'], 'paths': paths}


def finding_fields(item, *, clip=True):
    """(title, text) of one recorded finding, each length-bounded; a string is its own title and text."""
    if isinstance(item, str):
        return (bounded(item.split('\n', 1)[0], MAX_TITLE_CHARS), bounded(item, MAX_FINDING_CHARS)) if clip else (item.split('\n', 1)[0], item)
    if isinstance(item, dict):
        title = next((item[k] for k in ('title', 'summary', 'path') if isinstance(item.get(k), str) and item[k].strip()), '')
        parts = []
        for key in ('consequence', 'evidence', 'text', 'detail', 'description'):
            value = item.get(key)
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, list):
                parts += [v for v in value if isinstance(v, str)]
        return (bounded(title, MAX_TITLE_CHARS), bounded(' '.join(parts), MAX_FINDING_CHARS)) if clip else (title, ' '.join(parts))
    return '', ''


def finding_at(cfg, doc, finding_id):
    """(report, number, category, index, item) for a finding of a report in this pass, else None."""
    match = FINDING_ID.fullmatch(finding_id)
    if not match:
        return None
    number, category, index = int(match.group(1)), match.group(2), int(match.group(3))
    if not 1 <= number <= len(doc['reviews']):
        return None
    report = read_retained(cfg, doc['reviews'][number - 1])
    if report['pass'] != doc['pass'] or index >= len(report[category]):
        return None
    return report, number, category, index, report[category][index]


def review_facts(cfg, doc, report, *, clip=True) -> dict:
    """The facts every finding of one report shares (`SHARED_REVIEW_FACTS`)."""
    return {'verdict': report['verdict'], 'scrutiny': report.get('scrutiny', doc['review_policy']['scrutiny']), 'pass': report['pass'],
            'counts': {k: len(report[k]) for k in ('blocking', 'advisory', 'cosmetic')},
            'changed_paths': path_bound(changed_paths(cfg, doc), clip=clip),
            'required_checks': [bounded(c, MAX_PATH_CHARS) for c in doc['required_checks'][:MAX_LIST]] if clip else list(doc['required_checks'])}


def receipt_record(repo_root, evidence_id):
    from test_evidence import _read, storage
    return _read(storage(repo_root) / (evidence_id + '.json'))


def failure_summary(check_id, returncode, log_text, *, clip=True) -> dict:
    """Extract a failure summary by code: check id, exit status, failing test ids, exception type, first message line.

    Captured output, tracebacks and diffs are never copied; every field is length-bounded."""
    text = log_text or ''
    ids = []
    for pattern in (r'^(?:FAIL|ERROR): (\S+) \(([\w.]+)\)', r'^(?:FAILED|ERROR) (\S+::\S+)'):
        for found in re.finditer(pattern, text, re.M):
            name = found.group(2) if found.lastindex == 2 else found.group(1)
            if name not in ids:
                ids.append(name)
    exc = None
    for found in re.finditer(r'^([A-Za-z_][\w.]*(?:Error|Exception|Failure|Exit)):[ \t]*(.*)$', text, re.M):
        exc = found
    render = bounded if clip else lambda value, limit: value
    return {'check_id': render(check_id, MAX_PATH_CHARS), 'exit_status': returncode if isinstance(returncode, int) else None,
            'failing_tests': [render(i, MAX_PATH_CHARS) for i in (ids[:MAX_SUMMARY_IDS] if clip else ids)],
            'exception_type': render(exc.group(1), 80) if exc else None,
            'message': render(exc.group(2), 160) if exc else None}


def check_summary(repo_root, evidence_id, *, clip=True) -> dict:
    """The failure summary of a failing receipt; an unreadable receipt or log yields a summary of what is known."""
    try:
        record = receipt_record(repo_root, evidence_id)
    except Exception:
        return failure_summary('unknown', None, '')
    log, original_bytes = '', 0
    try:
        from test_evidence import _log_bytes, storage
        data = _log_bytes(storage(repo_root), record)
        if isinstance(data, bytes):
            original_bytes = len(data)
            log = (data[:MAX_LOG_BYTES] if clip else data).decode('utf-8', errors='replace')
    except Exception:
        log = ''
    summary = failure_summary(record['declaration']['check_id'], record.get('returncode'), log, clip=clip)
    if clip and original_bytes > MAX_LOG_BYTES:
        summary['clipped'] = {'log_bytes': {'clipped': True, 'original_length': original_bytes}}
    return summary


# ───────────────────────────── plans: state, routes, fingerprints ─────────────────────────────

REVIEW_SUBJECT = 'review:'


def concern(ident) -> str:
    return SPECIALISTS[ident].get('concern', ident)


def plan_review(cfg, doc, job):
    """One predicate per specialist not on the floor (subject `review:<id>`): add it, or keep the floor."""
    if doc['status'] != 'active' or doc['phase'] != 'review' or not job.subject.startswith(REVIEW_SUBJECT):
        return None
    ident = job.subject[len(REVIEW_SUBJECT):]
    if ident not in SPECIALISTS:
        return None
    floor = review_floor(cfg, doc)
    if ident in floor['specialists']:
        return None
    routes = [f'add:{ident}', 'floor-only']
    tasks = [t for t in doc['plan']['tasks'] if t['phase'] == 'review']
    state = {'phase': doc['phase'], 'pass': doc['pass'], 'scrutiny': doc['review_policy']['scrutiny'],
             'risks': [bounded(r, MAX_TITLE_CHARS) for r in doc['review_policy']['risks'][:MAX_LIST]],
             'floor': floor['specialists'], 'changed_paths': path_bound(floor['paths']),
             'tasks': [{'id': bounded(t['id'], MAX_PATH_CHARS), 'description': bounded(t['description'], MAX_TASK_CHARS)} for t in tasks[:MAX_LIST]]}
    facts = {'phase': doc['phase'], 'pass': doc['pass'], 'reviews': len(doc['reviews']),
             'tasks': [(t['id'], t['status'], task_assignments(doc, t['id'])) for t in tasks]}
    source = {**state, 'risks': list(doc['review_policy']['risks']), 'changed_paths': path_bound(floor['paths'], clip=False),
              'tasks': [{'id': t['id'], 'description': t['description']} for t in tasks]}
    return sourced(Plan(state, routes, digest(facts)), source)


def plan_finding(cfg, doc, job):
    if doc['status'] != 'active' or doc['phase'] != 'review':
        return None
    found = finding_at(cfg, doc, job.subject)
    if found is None:
        return None
    report, number, category, index, item = found
    title, text = finding_fields(item)
    blocking = category == 'blocking'
    routes = []
    if number == len(doc['reviews']) and fix_step_problem(doc, cfg) is None:
        routes.append('fix-step')
    if blocking:
        routes.append('return')
    else:
        routes += ['follow-up', 'agent-assessment']
    state = {'review': review_facts(cfg, doc, report), 'phase': doc['phase'], 'pass': doc['pass']}
    item = {'id': job.subject, 'category': category, 'title': title, 'text': text}
    fixes = [t['id'] for t in doc['plan']['tasks'] if 'fix' in t and t['phase'] == doc['phase'] and t['fix']['pass'] == doc['pass']]
    facts = {'pass': doc['pass'], 'phase': doc['phase'], 'latest': number == len(doc['reviews']), 'fixes': fixes,
             'deferred': any(d['finding'] == job.subject and d['pass'] == doc['pass'] for d in doc.get('deferrals', []))}
    original_title, original_text = finding_fields(found[-1], clip=False)
    original_item = {'id': job.subject, 'category': category, 'title': original_title, 'text': original_text}
    plan = sourced(Plan(state, routes, digest(facts), item, 'findings'),
                   {**state, 'review': review_facts(cfg, doc, report, clip=False)}, original_item)
    plan.source['recorded_item'] = found[-1]
    return plan


def attempt_count(doc, task_id, roles):
    import cycle_ops
    roles = roles or [None]
    return max(len(cycle_ops.reservations(doc, task_id, role)) for role in roles)


def plan_failure(cfg, doc, job, repo_root=None):
    import cycle_ops
    if doc['status'] != 'active':
        return None
    kind, _, detail = (job.trigger or '').partition(':')
    in_return = doc['phase'] in RETURN_PHASES and doc['pass'] < doc['pass_limit']
    if kind == 'check':
        routes = (['return'] if in_return else []) + ['agent-assessment']
        refs = sorted((r['evidence_id'], r['use']) for r in doc['evidence'] if r['check_id'] == job.subject and r['pass'] == doc['pass'])
        state = {'trigger': {'kind': 'check-failed'}, 'check': bounded(job.subject, MAX_PATH_CHARS),
                 'summary': check_summary(repo_root, detail) if repo_root is not None else None, 'phase': doc['phase'], 'pass': doc['pass']}
        source = {**state, 'check': job.subject}
        # The complete receipt log digest invalidates clipped message text without sending captured output.
        if repo_root is not None:
            source['summary'] = check_summary(repo_root, detail, clip=False)
            try:
                source['receipt_output_sha256'] = receipt_record(repo_root, detail).get('output_sha256')
            except Exception:
                source['receipt_output_sha256'] = None
        return sourced(Plan(state, routes, digest({'pass': doc['pass'], 'phase': doc['phase'], 'refs': refs})), source)
    if kind in ('delivery', 'handoff'):
        assignment_id, _, attempt = detail.rpartition('/')
        entry = assignment_entry(doc, assignment_id)
        task = task_entry(doc, job.subject)
        if entry is None or str(entry['attempt']) != attempt or entry['task'] != job.subject or not entry.get('delivery'):
            return None
    elif kind == 'refusal' and REFUSAL_TRIGGERS.get(detail) == 'assignment':
        entry = assignment_entry(doc, job.subject)
        task = task_entry(doc, entry['task']) if entry else None
    elif kind == 'refusal' and detail in REFUSAL_TRIGGERS:
        task = task_entry(doc, job.subject)
        entry = next((a for a in reversed(doc.get('assignments', [])) if a['task'] == job.subject), None)
    else:
        return None
    if task is None:
        return None
    if entry and (entry.get('delivery') or {}).get('stop'):
        return None
    unresolved = None
    if kind == 'handoff':
        if task.get('assignee', entry['id']) != entry['id']:
            return None
        prefix = f"{entry['id']}/{entry['attempt']}/evidence-"
        unresolved = sorted(subject for subject, answer in selected_entries(cfg, doc, 'handoff-completeness').items()
                            if subject.startswith(prefix) and answer['route'] == 'unresolved')
        if not unresolved:
            return None
    held = next((a for a in doc.get('assignments', []) if a['task'] == task['id'] and a['state'] in OPEN), None)
    live = entry if entry is not None and entry['state'] in OPEN else held
    live = live if live is not None and live.get('host') in _hosts() else None
    roles = [entry['role']] if entry else sorted({a['role'] for a in doc.get('assignments', []) if a['task'] == task['id']})
    used = attempt_count(doc, task['id'], roles)
    routes = []
    redispatch = (task['phase'] == doc['phase'] and task['status'] in ('pending', 'blocked') and held is None
                  and all(dependency_satisfied(doc, d) for d in task['depends_on']) and used < cycle_ops.ATTEMPT_LIMIT)
    if redispatch and detail not in ('attempt-limit', 'superseded-attempt', 'result-path-missing', 'unresolved-dispatch'):
        routes.append('re-dispatch')
    if live is not None and detail in ('unresolved-dispatch', 'superseded-attempt', 'result-path-missing'):
        routes.append('mark-lost')
    if in_return:
        routes.append('return')
    import cycle_context as context
    data = context.handoff_data(cfg, doc, entry['id'], entry['attempt']) if entry and entry.get('delivery') else None
    report = data['report'] if data else ''
    additional = context.report_routes(report)
    routes += [route for route in additional if route != 'environment-investigation' or used < cycle_ops.ATTEMPT_LIMIT]
    if doc['phase'] == 'build' and used < cycle_ops.ATTEMPT_LIMIT and held is None:
        routes.append('owning-developer')
    if data and used < cycle_ops.ATTEMPT_LIMIT and held is None:
        handoff = handoff_result(cfg, doc, entry['id'], entry['attempt'])
        if handoff['omissions']:
            routes.append('missing-evidence-request')
    criteria = context.failed_criteria(cfg, doc, data['references']) if data else []
    if criteria and doc['phase'] in RETURN_PHASES and fix_step_problem(doc, cfg) is None:
        routes.append('acceptance-fix')
    routes.append('agent-assessment')
    state = {'trigger': {'kind': 'handoff-unresolved' if kind == 'handoff' else 'delivery-failed' if kind == 'delivery' else 'refusal', 'code': detail if kind == 'refusal' else None},
             'task': {'id': bounded(task['id'], MAX_PATH_CHARS), 'description': bounded(task['description'], MAX_TASK_CHARS), 'status': task['status']},
             'attempt': ({'id': bounded(entry['id'], MAX_PATH_CHARS), 'attempt': entry['attempt'], 'role': entry['role'], 'state': entry['state'],
                          'outcome': (entry.get('delivery') or {}).get('outcome')} if entry else None),
             'attempts_in_pass': used, 'attempt_limit': cycle_ops.ATTEMPT_LIMIT, 'phase': doc['phase'], 'pass': doc['pass'],
             'report': bounded(report, 8000), 'failed_criteria': criteria}
    facts = {'pass': doc['pass'], 'phase': doc['phase'], 'task': task['status'], 'attempts': task_assignments(doc, task['id']), 'used': used}
    if unresolved is not None:
        state['handoff_unresolved'] = list(unresolved)
        facts.update(unresolved=unresolved, assignee=task.get('assignee'), delivery=entry['delivery']['sha256'])
    source = {**state, 'task': {'id': task['id'], 'description': task['description'], 'status': task['status']},
              'attempt': {**state['attempt'], 'id': entry['id']} if entry else None, 'report': report}
    return sourced(Plan(state, routes, digest(facts)), source)


def _hosts():
    import cycle_hosts
    return cycle_hosts.ADAPTERS


def plan_of(cfg, doc, job, repo_root=None):
    """The plan for a job on this record, or None when the subject is no longer open for the classification."""
    advisory.checkpoint()
    if job.kind == 'review-routing':
        return plan_review(cfg, doc, job)
    if job.kind == 'finding-disposition':
        return plan_finding(cfg, doc, job)
    if job.kind == 'failure-routing':
        return plan_failure(cfg, doc, job, repo_root or cfg.repo_root)
    if job.kind in KINDS:
        from cycle_context import plan_new
        return plan_new(cfg, doc, job, repo_root)
    return None


# ───────────────────────────── records ─────────────────────────────

def same_job(entry, doc, job) -> bool:
    return (entry['kind'], entry['subject'], entry.get('trigger'), entry['pass']) == (job.kind, job.subject, job.trigger, doc['pass'])


def duplicate(doc, job, plan=None) -> bool:
    """Only an identical input already recorded at this revision is an idempotent replay."""
    return any(same_job(e, doc, job) and e.get('question_ids') and plan is not None
               and e['fingerprint'] == plan.fingerprint and e['revision'] == doc['revision']
               for e in doc.get('classifications', []))


def reusable(doc, job, plan):
    for index in range(len(doc.get('classifications', [])) - 1, -1, -1):
        entry = doc['classifications'][index]
        if (same_job(entry, doc, job) and entry.get('question_ids') and entry['fingerprint'] == plan.fingerprint
                and entry.get('fallback') is None and entry.get('route') in plan.routes
                and isinstance(entry.get('answer'), dict) and entry['answer'].get('choice') == entry['route']):
            return index, entry
    return None


def bind_batch(batch, basis):
    """Bind each answer to the actual shared state and complete local source fields."""
    state = batch_state(batch)
    ids = tuple(question_id(item[0]) for item in batch)
    sources = digest(sorted({digest(item[1].source or item[1].full_state()) for item in batch}))
    for job, plan, _ in batch:
        qset = questions.question_set(job.kind)
        plan.question_ids = ids
        plan.context_question_ids = ids
        plan.question_version = qset.version
        plan.request_state = state
        plan.fingerprint = digest({'set': job.kind, 'version': qset.version,
                                   'instructions': qset.instructions, 'question_id': question_id(job),
                                   'state': json.dumps(state, ensure_ascii=False, sort_keys=True, allow_nan=False), 'source_digest': sources,
                                   'options': list(questions.options(job.kind, plan.routes).items()),
                                   'policy': [ROUTING_POLICY_VERSION, plan.policy_fingerprint], 'configuration': basis})


def prepare_inputs(items, basis):
    for batch in batches(items):
        advisory.checkpoint()
        bind_batch(batch, basis)
    advisory.checkpoint()


def current_input(cfg, doc, job, plan, basis, repo_root=None, cache=None):
    """Reconstruct the original batch against current facts; nothing is read from stored source text."""
    advisory.checkpoint()
    context_ids = plan.context_question_ids or plan.question_ids
    key = (job.kind, job.trigger, context_ids, job.subject if question_id(job) == job.kind else None)
    if cache is not None and key in cache:
        return cache[key].get(job)
    context = []
    for ident in context_ids or (question_id(job),):
        advisory.checkpoint()
        if ident == question_id(job):
            other = job
        elif ident.startswith('subject-') and job.kind in ('context-selection', 'handoff-completeness', 'review-finding-grouping', 'focused-test-ranking'):
            from cycle_context import peer_jobs
            other = next((peer for peer in peer_jobs(cfg, doc, job) if question_id(peer) == ident), None)
            if other is None:
                continue
        else:
            other = Job(job.kind, ident, job.trigger)
        fresh = plan_of(cfg, doc, other, repo_root)
        advisory.checkpoint()
        if fresh is not None:
            context.append([other, fresh, None])
    if not context:
        return None
    bind_batch(context, basis)
    found = {item[0]: item[1] for item in context}
    if cache is not None:
        cache[key] = found
    return found.get(job)


def answer_of(outcome):
    if outcome.status != decisions.ANSWERED:
        return None
    return {'choice': outcome.choice, 'probabilities': dict(outcome.probabilities) if outcome.probabilities is not None else None}


def billing_of(outcome):
    """The serving provider and cost the gateway response reported; null for each one it did not report."""
    return {'served_provider': outcome.served_provider, 'cost': (outcome.usage or {}).get('cost')}


def make_entry(job, outcome, route, fallback, plan, doc, revision):
    entry = {'kind': job.kind, 'request_id': outcome.request_id, 'question_set': job.kind,
            'question_version': plan.question_version, 'model': decisions.EXPECTED_SERVED_MODEL,
            'served_model': outcome.served_model, **billing_of(outcome), 'answer': answer_of(outcome), 'route': route, 'fallback': fallback,
            'subject': job.subject, 'fingerprint': plan.fingerprint, 'question_ids': list(plan.question_ids),
            'trigger': job.trigger, 'pass': doc['pass'], 'phase': doc['phase'],
            'at': now(), 'revision': revision, 'routing_policy_version': ROUTING_POLICY_VERSION}
    if plan.reused_from is not None:
        entry['reused_from'] = plan.reused_from
    if plan.context_question_ids and plan.context_question_ids != plan.question_ids:
        entry['context_question_ids'] = list(plan.context_question_ids)
    return entry


def decide(outcome, plan, plan_now, stale):
    """(route, fallback) for an outcome: the transport status or an engine fallback, else the permitted route."""
    if outcome.status != decisions.ANSWERED:
        return None, outcome.status
    if outcome.choice == decisions.INSUFFICIENT_INFORMATION:
        return None, 'insufficient-information'
    if stale:
        return None, 'stale'
    if outcome.choice not in plan.routes:
        return None, 'route-not-permitted'
    if plan_now is None or outcome.choice not in plan_now.routes:
        return None, 'policy-refused'
    return outcome.choice, None


def question_of(job, plan):
    qset = questions.question_set(job.kind)
    return decisions.ChoiceQuestion(instructions=qset.instructions, options=questions.options(job.kind, plan.routes))


def question_id(job) -> str:
    """The id a question goes under: its subject where one request holds several of its kind, else its kind."""
    if job.kind in ('review-routing', 'finding-disposition', 'context-selection', 'handoff-completeness', 'review-finding-grouping', 'focused-test-ranking'):
        return job.subject if len(job.subject) <= 128 and '#' not in job.subject else 'subject-' + digest(job.subject)
    return job.kind


def ask_one(job, plan, deadline):
    if not plan.question_ids:
        bind_batch([[job, plan, None]], decisions.classifier_basis())
    plan.question_ids = (question_id(job),)
    return decisions.ask_many(batch_state([[job, plan, None]]), {question_id(job): question_of(job, plan)}, deadline=deadline, kinds=(job.kind,))[question_id(job)]


def state_size(state) -> int:
    """The rendered length the transport bounds, rendered as the transport renders it."""
    return len(json.dumps(state, ensure_ascii=False, sort_keys=True, allow_nan=False))


def batch_state(batch) -> dict:
    plan = batch[0][1]
    if plan.request_state is not None:
        return plan.request_state
    if plan.item_field is None:
        return plan.state
    return {**plan.state, plan.item_field: [item[1].item for item in batch]}


def batches(items) -> list:
    """Group [job, plan, outcome] items into requests.

    Items share a request only when their kind, shared state and item field are equal and their question ids
    differ. A request holds at most `decisions.MAX_QUESTIONS_PER_REQUEST` questions and, when it lists items,
    stays within its centrally configured kind bound; an item that does not fit starts the next request. Order is kept."""
    groups = {}
    for item in items:
        advisory.checkpoint()
        job, plan = item[0], item[1]
        groups.setdefault((job.kind, digest(plan.request_state if plan.request_state is not None else plan.state), plan.item_field), []).append(item)
    out = []
    for group in groups.values():
        batch = []
        for item in group:
            advisory.checkpoint()
            trial = batch + [item]
            ids = [question_id(i[0]) for i in trial]
            if batch and (len(trial) > decisions.MAX_QUESTIONS_PER_REQUEST or len(set(ids)) < len(ids)
                          or state_size(batch_state(trial)) > decisions.input_bound(tuple(i[0].kind for i in trial))):
                out.append(batch)
                batch = [item]
            else:
                batch = trial
        out.append(batch)
    return out


def ask_batches(items, deadline) -> None:
    """Ask every item's question, one request per batch, at most `decisions.REQUEST_CONCURRENCY` at once."""
    def run(batch):
        if deadline.remaining() <= 0:
            for item in batch:
                item[2] = decisions.Outcome(status='unavailable')
            return
        ids = tuple(question_id(item[0]) for item in batch)
        for item in batch:
            item[1].question_ids = ids
        found = decisions.ask_many(batch_state(batch), {question_id(i[0]): question_of(i[0], i[1]) for i in batch},
                                   deadline=deadline, kinds=tuple(dict.fromkeys(i[0].kind for i in batch)))
        for item in batch:
            item[2] = found[question_id(item[0])]
    requests = batches(items)
    if not requests:
        return
    if len(requests) == 1:
        run(requests[0])
        return
    with ThreadPoolExecutor(max_workers=min(decisions.REQUEST_CONCURRENCY, len(requests))) as pool:
        list(pool.map(run, requests))


def outcome_report(job, plan, outcome, route, fallback, revision, recorded=True):
    out = {'kind': job.kind, 'subject': job.subject, 'trigger': job.trigger, 'route': route, 'fallback': fallback, 'recorded': recorded,
           'request_id': outcome.request_id, 'revision': revision}
    if plan.reused_from is not None:
        out['reused_from'] = plan.reused_from
    if fallback is not None:
        qset = questions.question_set(job.kind)
        out['question'] = {'set': job.kind, 'version': qset.version, 'instructions': qset.instructions,
                           'options': questions.options(job.kind, plan.routes)}
        out['evidence'] = plan.full_state()
        out['outcome'] = {'status': outcome.status, 'choice': outcome.choice, 'served_model': outcome.served_model,
                          'http_status': outcome.http_status, 'attempts': outcome.attempts}
    return out


@advisory.advisory_operation
def classify(repo_root, cycle_id, jobs, *, decisions_deadline=None) -> dict:
    try:
        return _classify(repo_root, cycle_id, jobs, decisions_deadline=advisory.advisory_deadline())
    except advisory.AdvisoryUnavailable:
        return {'classifications': [{'kind': job.kind, 'subject': job.subject, 'trigger': job.trigger,
                                    'route': None, 'fallback': 'unavailable', 'recorded': False} for job in jobs],
                'classification_unavailable': 'deadline-exhausted'}


def _classify(repo_root, cycle_id, jobs, *, decisions_deadline=None) -> dict:
    """Ask and record the classifications `jobs` name; return {classifier, classifications, revision?}.

    Never asks on a version-1 or version-2 record or a closed cycle; never builds a request when the classifier
    is unconfigured. The request is sent with the lock released; the entries are written in one transaction."""
    report = {'classifications': []}
    if not advisory.provider_requests_allowed():
        # Current cached answers are read and revalidated by arrangement_result,
        # context_result, handoff_result and selected_entries. A cache miss is not
        # an execution and must not append a fictional unavailable outcome.
        return {**report, 'advice': 'cache-only'}
    advisory.checkpoint()
    doc = load(repo_root, cycle_id)
    if doc['schema_version'] != 3 or doc['status'] != 'active' or not jobs:
        return report
    cfg = tree(repo_root)
    state = classifier_state(repo_root)
    report['classifier'] = state
    if not state['configured']:
        report['classifications'] = [{'kind': j.kind, 'subject': j.subject, 'trigger': j.trigger, 'route': None, 'fallback': 'opted-out' if state['reason'] == 'opted-out' else 'unconfigured',
                                      'recorded': False} for j in jobs if plan_of(cfg, doc, j, repo_root) is not None]
        return report
    from cycle_context import facts_scope
    with facts_scope():
        pending = []
        for job in jobs:
            advisory.checkpoint()
            plan = plan_of(cfg, doc, job, repo_root)
            advisory.checkpoint()
            if plan is not None and plan.routes:
                pending.append([job, plan, None])
    if not pending:
        return report
    prepare_inputs(pending, decisions.classifier_basis())
    wanted = []
    for item in pending:
        job, plan, _ = item
        if duplicate(doc, job, plan):
            report['classifications'].append({'kind': job.kind, 'subject': job.subject, 'trigger': job.trigger,
                                              'skipped': 'already-classified', 'recorded': False})
            continue
        hit = reusable(doc, job, plan)
        if hit is not None:
            index, entry = hit
            plan.reused_from = entry.get('reused_from') or {'index': index, 'revision': entry['revision'], 'request_id': entry['request_id']}
            plan.question_ids = tuple(entry['question_ids'])
            plan.context_question_ids = tuple(entry.get('context_question_ids') or entry['question_ids'])
            item[2] = decisions.Outcome(status=decisions.ANSWERED, choice=entry['answer']['choice'],
                                       probabilities=entry['answer'].get('probabilities'), request_id=entry['request_id'],
                                       served_model=entry.get('served_model'), served_provider=entry.get('served_provider'))
        wanted.append(item)
    pending = wanted
    if not pending:
        return report
    deadline = decisions_deadline
    ask_batches([item for item in pending if item[2] is None], deadline)
    reasked = False
    while True:
        with locked(repo_root) as (cfg, _):
            doc = load(repo_root, cycle_id)
            state_now = classifier_state(repo_root)
            if not state_now['configured']:
                report['classifier'] = state_now
                report['classifications'] += [{'kind': j.kind, 'subject': j.subject, 'trigger': j.trigger,
                                               'route': None, 'fallback': 'unconfigured', 'recorded': False} for j, _, _ in pending]
                return report
            basis = decisions.classifier_basis()
            live = []
            context_cache = {}
            validation_unavailable = False
            changed_source_jobs = set()
            try:
                with facts_scope(fresh=True):
                    fresh_plans = [current_input(cfg, doc, item[0], item[1], basis, repo_root, context_cache) for item in pending]
                    if any(item[0].kind == 'focused-test-ranking' for item in pending) and not advisory.focused_facts_current(cfg, doc):
                        changed_source_jobs = {item[0] for item in pending if item[0].kind == 'focused-test-ranking'}
                        fresh_plans = [None if item[0] in changed_source_jobs else plan for item, plan in zip(pending, fresh_plans)]
                    advisory.checkpoint()
            except advisory.AdvisoryUnavailable:
                # Keep known provider diagnostics, but no route can survive incomplete currentness.
                validation_unavailable = True
                fresh_plans = [None] * len(pending)
                report['classification_unavailable'] = 'deadline-exhausted'
            for item, fresh in zip(pending, fresh_plans):
                if duplicate(doc, item[0], fresh):
                    report['classifications'].append({'kind': item[0].kind, 'subject': item[0].subject, 'trigger': item[0].trigger,
                                                      'skipped': 'already-classified', 'recorded': False})
                else:
                    live.append((item, fresh))
            if not live:
                return report
            retry = [(item, fresh) for item, fresh in live if fresh is not None and item[1].fingerprint != fresh.fingerprint
                     and item[2].status == decisions.ANSWERED and item[2].choice != decisions.INSUFFICIENT_INFORMATION]
            if not (retry and not reasked):
                revision = doc['revision'] + 1
                entries = []
                for (job, plan, outcome), plan_now in live:
                    stale = plan_now is not None and plan.fingerprint != plan_now.fingerprint
                    route, fallback = ((None, 'unavailable') if validation_unavailable else
                                       (None, 'stale') if job in changed_source_jobs else decide(outcome, plan, plan_now, stale))
                    entries.append((job, plan, outcome, route, fallback,
                                    make_entry(job, outcome, route, fallback, plan, doc, revision)))
                doc.setdefault('classifications', []).extend(e[-1] for e in entries)
                event(doc, 'classified', kinds=sorted({e[0].kind for e in entries}), count=len(entries))
                save(cfg, doc)
                report['classifications'] += [outcome_report(j, p, o, r, f, doc['revision']) for j, p, o, r, f, _ in entries]
                report['revision'] = doc['revision']
                return report
            # Only changed decision inputs are asked again. Bookkeeping revisions keep their answers.
            pending = [item for item, _ in live]
            asking = []
            for item, fresh in retry:
                fresh.request_state = None
                fresh.question_ids = ()
                fresh.context_question_ids = ()
                item[1], item[2] = fresh, None
                asking.append(item)
            prepare_inputs(asking, basis)
        reasked = True
        ask_batches(asking, deadline)


def response_fields(found) -> dict:
    """The fields a classification report adds to an operation's response: outcomes, classifier state, the post-write revision."""
    out = {key: found[key] for key in ('classifications', 'classifier', 'classification_error', 'classification_unavailable') if found.get(key)}
    if 'revision' in found:
        out['revision'] = found['revision']
    return out


def safely(function, *args, **kwargs) -> dict:
    """Run a classification hook; a bug in it never turns a committed operation into a crash."""
    try:
        return function(*args, **kwargs)
    except advisory.AdvisoryUnavailable:
        return {'classification_unavailable': 'deadline-exhausted'}
    except Exception as exc:  # noqa: BLE001 - the triggering operation already committed
        return {'classification_error': type(exc).__name__}


# ───────────────────────────── triggers ─────────────────────────────

@advisory.advisory_operation
def selected_entries(cfg, doc, kind):
    """Read current answers only; never ask or install a stale selection."""
    from cycle_context import facts_scope
    cache = {}
    with facts_scope():
        entries = {entry['subject']: entry for entry in current_entries(doc)
                   if entry['kind'] == kind and valid_plan(cfg, doc, entry, cache=cache) is not None}
        if kind == 'focused-test-ranking' and entries and not advisory.focused_facts_current(cfg, doc):
            return {}
        advisory.checkpoint()
        return entries


def arrangement_result(cfg, doc, task_id, *, role=None):
    """Revalidate a role selection against the record held by the caller's lock."""
    from cycle_context import available_roles, permitted_roles
    task = task_entry(doc, task_id)
    if role is not None:
        if role not in available_roles():
            raise CycleError('explicit role is not configured')
        return {'role': role, 'permitted_roles': [role], 'explicit': True}
    # Every phase permits at most one role, so an omitted role selects it and no question is asked.
    roles = permitted_roles(doc, task) if task is not None and task['phase'] == doc['phase'] else []
    return {'role': roles[0] if len(roles) == 1 else None, 'permitted_roles': roles}


@advisory.advisory_operation
def arrangement(repo_root, cycle_id, task_id, *, role=None, decisions_deadline=None):
    """The role a dispatch selects; each role retains its configured tools and model."""
    return arrangement_result(tree(repo_root), load(repo_root, cycle_id), task_id, role=role)


@advisory.advisory_operation
def context_bundles(repo_root, cycle_id, task_id, role, *, decisions_deadline=None):
    try:
        with advisory.facts_scope():
            return _context_bundles(repo_root, cycle_id, task_id, role, decisions_deadline=advisory.advisory_deadline())
    except advisory.AdvisoryUnavailable:
        return {'classifications': [], 'selected': [], 'retrievable': [], 'classification_unavailable': 'deadline-exhausted'}


def _context_bundles(repo_root, cycle_id, task_id, role, *, decisions_deadline=None):
    """Select optional canonical bodies instead of preloading every role skill."""
    import cycle_context as context
    doc = load(repo_root, cycle_id)
    task = task_entry(doc, task_id)
    choices = context.candidates(doc, task, role) if task is not None and role in context.available_roles() else []
    jobs = [Job('context-selection', f'{task_id}:skill-{index}', 'role:' + role) for index in range(len(choices))]
    found = classify(repo_root, cycle_id, jobs, decisions_deadline=decisions_deadline)
    with advisory.facts_scope(fresh=True):
        return {**found, **context_result(tree(repo_root), load(repo_root, cycle_id), task_id, role)}


@advisory.advisory_operation
def context_result(cfg, doc, task_id, role):
    with advisory.facts_scope():
        return _context_result(cfg, doc, task_id, role)


def _context_result(cfg, doc, task_id, role):
    """Recompute optional bodies from the current candidate order under the caller's lock."""
    import cycle_context as context
    task = task_entry(doc, task_id)
    choices = context.candidates(doc, task, role) if task is not None and role in context.available_roles() else []
    entries = selected_entries(cfg, doc, 'context-selection')
    selected = []
    for index, item in enumerate(choices):
        advisory.checkpoint()
        entry = entries.get(f'{task_id}:skill-{index}')
        if entry and entry.get('trigger') == 'role:' + role and entry['route'] == 'include' and len(selected) < context.context_limit():
            try:
                selected.append(context.skill_bundle(item['id']))
            except (ValueError, OSError):
                pass
    advisory.checkpoint()
    return {'selected': selected, 'retrievable': [item['id'] for item in choices if item['id'] not in {s['id'] for s in selected}]}


@advisory.advisory_operation
def handoff_result(cfg, doc, assignment, attempt):
    with advisory.facts_scope():
        return _handoff_result(cfg, doc, assignment, attempt)


def _handoff_result(cfg, doc, assignment, attempt):
    """Inspect retained answers and code-resolved references without a provider call."""
    import cycle_context as context
    import cycle_ops
    if not any(entry['kind'] == 'handoff-completeness' for entry in current_entries(doc)):
        return {'items': [], 'omissions': [], 'unresolved': [], 'reference_failures': [],
                'route': None, 'advice': 'not-refreshed'}
    data = context.handoff_data(cfg, doc, assignment, attempt)
    if data is None:
        return {'items': [], 'omissions': [], 'unresolved': [], 'reference_failures': [], 'route': 'agent-assessment'}
    entries = selected_entries(cfg, doc, 'handoff-completeness')
    raw = {entry['subject']: entry for entry in current_entries(doc) if entry['kind'] == 'handoff-completeness'}
    items, omissions, unresolved, failures = [], [], [], []
    for index, expected in enumerate(data['task']['expected_evidence']):
        advisory.checkpoint()
        ident = f'{assignment}/{attempt}/evidence-{index}'
        entry = entries.get(ident)
        claimed = (raw.get(ident, {}).get('answer') or {}).get('choice', '')
        route = entry['route'] if entry else 'unresolved'
        item = {'id': ident, 'expected': expected, 'status': route}
        if claimed.startswith('answered:'):
            ref = claimed.removeprefix('answered:')
            valid = data['checked'].get(ref, {'valid': False, 'reason': 'reference-not-recorded'})
            if not valid['valid']:
                item['status'] = 'unsupported'
                failures.append({'id': ident, 'reference': ref, 'reason': valid.get('reason')})
            elif entry:
                item.update(status='answered', reference=next(value for value in data['references'] if value['id'] == ref))
        if item['status'] in ('unsupported', 'absent'):
            omissions.append(ident)
        elif item['status'] == 'unresolved':
            unresolved.append(ident)
        items.append(item)
    used = attempt_count(doc, data['task']['id'], [data['entry']['role']])
    opened = any(a['task'] == data['task']['id'] and a['state'] in OPEN for a in doc.get('assignments', []))
    route = ('missing-evidence-request' if omissions and used < cycle_ops.ATTEMPT_LIMIT and not opened and data['task']['phase'] == doc['phase'] else
             'agent-assessment' if omissions or unresolved else None)
    advisory.checkpoint()
    return {'items': items, 'omissions': omissions, 'unresolved': unresolved, 'reference_failures': failures, 'route': route}


@advisory.advisory_operation
def handoff(repo_root, cycle_id, task_id, assignment, attempt, *, decisions_deadline=None):
    """Replace rereading a retained handoff separately for every evidence item."""
    from cycle_context import handoff_data
    cfg, doc = tree(repo_root), load(repo_root, cycle_id)
    data = handoff_data(cfg, doc, assignment, attempt)
    if data is None or data['task']['id'] != task_id:
        raise CycleError('handoff requires the matching retained task delivery')
    jobs = [Job('handoff-completeness', f'{assignment}/{attempt}/evidence-{index}')
            for index in range(len(data['task']['expected_evidence']))]
    found = classify(repo_root, cycle_id, jobs, decisions_deadline=decisions_deadline)
    return {**found, **handoff_result(cfg, load(repo_root, cycle_id), assignment, attempt)}


def grouping_jobs(cfg, doc):
    from cycle_context import streams
    if doc['phase'] != 'review' or not doc['reviews'] or not streams(doc):
        return []
    number = len(doc['reviews'])
    report = read_retained(cfg, doc['reviews'][-1])
    return [Job('review-finding-grouping', f'r{number}:{category}:{index}/{part}')
            for category in ('blocking', 'advisory', 'cosmetic') for index in range(len(report[category])) for part in ('owner', 'cause')]


@advisory.advisory_operation
def finding_groups(repo_root, cycle_id, *, decisions_deadline=None):
    try:
        return _finding_groups(repo_root, cycle_id, decisions_deadline=advisory.advisory_deadline())
    except advisory.AdvisoryUnavailable:
        return {'classifications': [], 'owners': {}, 'shared_causes': {}, 'classification_unavailable': 'deadline-exhausted'}


def _finding_groups(repo_root, cycle_id, *, decisions_deadline=None):
    """Offer owner and shared-cause hypotheses while retaining every finding identity."""
    cfg, doc = tree(repo_root), load(repo_root, cycle_id)
    found = classify(repo_root, cycle_id, grouping_jobs(cfg, doc), decisions_deadline=decisions_deadline)
    entries = selected_entries(cfg, load(repo_root, cycle_id), 'review-finding-grouping')
    owners, causes = {}, {}
    for subject, entry in entries.items():
        ident, _, part = subject.rpartition('/')
        if part == 'owner':
            owners[ident] = entry['route'].removeprefix('stream:')
        else:
            causes[ident] = entry['route']
    advisory.checkpoint()
    return {**found, 'owners': owners, 'shared_causes': causes}


def repair_group(repo_root, cycle_id, finding_ids):
    """Check the ordinary allowance; a hypothesis cannot waive any finding identity."""
    from cycle_workflow import check_fix_findings
    cfg, doc = tree(repo_root), load(repo_root, cycle_id)
    try:
        check_fix_findings(doc, cfg, finding_ids)
        problem = fix_step_problem(doc, cfg)
    except CycleError as exc:
        problem = str(exc)
    return {'eligible': problem is None, 'findings': list(finding_ids), 'problem': problem,
            'requires': 'normal task-add eligibility, diff verification and evidence for every finding'}


@advisory.advisory_operation
def focused_suggestions(cfg, doc):
    with advisory.facts_scope():
        return _focused_suggestions(cfg, doc)


def _focused_suggestions(cfg, doc):
    """Read additive suggestions; authoritative required check selection stays untouched."""
    import cycle_context as context
    if doc['phase'] != 'build' or not any(entry['kind'] == 'focused-test-ranking' and entry.get('route') == 'include' for entry in current_entries(doc)):
        return []
    choices = context.focused_candidates(cfg, doc)
    entries = selected_entries(cfg, doc, 'focused-test-ranking')
    suggested = [item for index, item in enumerate(choices) if entries.get(f'candidate-{index}', {}).get('route') == 'include'][:context.context_limit('focused_test_keep')]
    advisory.checkpoint()
    return suggested


@advisory.advisory_operation
def focused_tests(repo_root, cycle_id, *, decisions_deadline=None):
    try:
        with advisory.facts_scope():
            return _focused_tests(repo_root, cycle_id, decisions_deadline=advisory.advisory_deadline())
    except advisory.AdvisoryUnavailable:
        return {'classifications': [], 'suggested_checks': [], 'classification_unavailable': 'deadline-exhausted'}


def _focused_tests(repo_root, cycle_id, *, decisions_deadline=None):
    import cycle_context as context
    cfg, doc = tree(repo_root), load(repo_root, cycle_id)
    choices = context.focused_candidates(cfg, doc) if doc['phase'] == 'build' else []
    jobs = [Job('focused-test-ranking', f'candidate-{index}') for index in range(len(choices))]
    found = classify(repo_root, cycle_id, jobs, decisions_deadline=decisions_deadline)
    with advisory.facts_scope(fresh=True):
        return {**found, 'suggested_checks': focused_suggestions(cfg, load(repo_root, cycle_id))}


def entered_review(repo_root, cycle_id, *, decisions_deadline=None) -> dict:
    """Review routing for a cycle that has just entered Review: one predicate per specialist not on the floor."""
    doc = load(repo_root, cycle_id)
    if doc['phase'] != 'review' or doc['schema_version'] != 3 or doc['status'] != 'active':
        return {}
    floor = review_floor(tree(repo_root), doc)
    jobs = [Job('review-routing', REVIEW_SUBJECT + ident) for ident in SPECIALISTS if ident not in floor['specialists']]
    return classify(repo_root, cycle_id, jobs, decisions_deadline=decisions_deadline) if jobs else {}


def failed_delivery(repo_root, cycle_id, task_id, assignment, attempt, *, decisions_deadline=None) -> dict:
    return classify(repo_root, cycle_id, [Job('failure-routing', task_id, f'delivery:{assignment}/{attempt}')], decisions_deadline=decisions_deadline)


def unresolved_handoff(repo_root, cycle_id, task_id, assignment, attempt, *, decisions_deadline=None) -> dict:
    """Assess current unresolved evidence without relabeling the retained delivery outcome."""
    return classify(repo_root, cycle_id, [Job('failure-routing', task_id, f'handoff:{assignment}/{attempt}')], decisions_deadline=decisions_deadline)


def refused_operation(repo_root, cycle_id, request, errors) -> dict:
    """Failure routing for refusals whose code has more than one plausible recovery; other codes trigger nothing."""
    jobs = []
    for error in errors:
        field = REFUSAL_TRIGGERS.get(error.get('code'))
        subject = request.get(field) if field else None
        if isinstance(subject, str) and subject:
            job = Job('failure-routing', subject, f"refusal:{error['code']}")
            if job not in jobs:
                jobs.append(job)
    return classify(repo_root, cycle_id, jobs[:1]) if jobs else {}


def recorded_review(repo_root, cycle_id, *, decisions_deadline=None) -> dict:
    """One finding-disposition question per finding of the newest report, asked in bounded batches over one shared
    review state and written in one transaction."""
    doc = load(repo_root, cycle_id)
    if doc['schema_version'] != 3 or not doc['reviews']:
        return {}
    number = len(doc['reviews'])
    report = read_retained(tree(repo_root), doc['reviews'][-1])
    jobs = [Job('finding-disposition', f'r{number}:{category}:{index}')
            for category in ('blocking', 'advisory', 'cosmetic') for index in range(len(report[category]))]
    jobs += grouping_jobs(tree(repo_root), doc)
    return classify(repo_root, cycle_id, jobs, decisions_deadline=decisions_deadline)


def failed_check(repo_root, cycle_id, evidence_id) -> dict:
    """Failure routing for a receipt the engine observed failing, keyed on its receipt id."""
    record = receipt_record(repo_root, evidence_id)
    if record.get('status') != 'failed':
        return {}
    return classify(repo_root, cycle_id, [Job('failure-routing', record['declaration']['check_id'], f'check:{evidence_id}')])


# ───────────────────────────── work sizing ─────────────────────────────

class SizingFallback(CycleError):
    """Work sizing fell back; creation is refused and `receipt` carries the entry's diagnostic fields."""

    def __init__(self, fallback, receipt, question, evidence):
        super().__init__(f'work sizing fell back ({fallback}); create with an explicit --type and pass --sizing-receipt')
        self.receipt, self.question, self.evidence = receipt, question, evidence


def sizing_types():
    return [kind for kind in PHASES if kind != 'release']


def sizing_entry(job_subject, outcome, route, fallback, doc, receipt=None, trigger=None, plan=None):
    """The creating save retains the proposed work's input identity; legacy receipts keep their original fields."""
    base = {'kind': 'work-sizing', 'route': route, 'fallback': fallback, 'subject': job_subject,
            'fingerprint': plan.fingerprint if plan is not None else None, 'trigger': trigger,
            'pass': 1, 'phase': doc['phase'], 'at': now(), 'revision': 1}
    if plan is not None:
        base['question_ids'] = list(plan.question_ids)
    if receipt is not None:
        return {**base, **{k: receipt[k] for k in SIZING_RECEIPT_FIELDS}, **{k: receipt[k] for k in SIZING_RECEIPT_OPTIONAL if k in receipt}}
    return {**base, 'request_id': outcome.request_id, 'question_set': 'work-sizing',
            'question_version': questions.question_set('work-sizing').version, 'model': decisions.EXPECTED_SERVED_MODEL,
            'served_model': outcome.served_model, **billing_of(outcome), 'answer': answer_of(outcome)}


def sizing_evidence(title, goal, scope, acceptance):
    """The work-sizing state: the proposed cycle's title, goal, scope paths and acceptance criteria, each bounded."""
    state = {'title': bounded(title, MAX_TITLE_CHARS), 'goal': bounded(goal, MAX_FINDING_CHARS),
             'scope': [bounded(s, MAX_PATH_CHARS) for s in scope[:MAX_LIST]],
             'acceptance': [bounded(a, MAX_TASK_CHARS) for a in acceptance[:MAX_LIST]]}
    marks = clipping({'title': title, 'goal': goal, 'scope': scope, 'acceptance': acceptance}, state)
    if marks:
        state['clipped'] = marks
    return state


def sizing_plan(title, goal, scope, acceptance):
    return sourced(Plan(sizing_evidence(title, goal, scope, acceptance), sizing_types(), None),
                   {'title': title, 'goal': goal, 'scope': scope, 'acceptance': acceptance})


@dataclass
class QueueSizing:
    """What `queue start-next` does with a work-sizing answer: the type to create with, the entry to write, or a stop."""
    kind: str | None = None
    classification: object = None
    stop: tuple | None = None  # (reason, detail)


def queue_sizing(repo_root, item_type, title, goal, scope, acceptance) -> QueueSizing:
    """Classify a queue item's work when the classifier is configured, as `queue start-next` does.

    An item that names a cycle type keeps it: the answer is recorded as advisory and never applied.
    An item whose type is `auto` names none: a permitted answer selects the type, and a fallback stops the
    queue because no cycle exists to carry the entry. A release item is never sized. With the classifier
    unconfigured an item that names a type is created as before, and an `auto` item stops."""
    selecting = item_type == 'auto'
    if not selecting:
        return QueueSizing()
    state = classifier_state(repo_root)
    if not state['configured']:
        if selecting:
            return QueueSizing(stop=('classifier-unconfigured', f"type auto needs the classifier, which is unconfigured ({state['reason']}); edit the item's type"))
        return QueueSizing()
    types = sizing_types()
    job = Job('work-sizing', 'new', questions.SELECTING_TRIGGER if selecting else questions.ADVISORY_TRIGGER)
    plan = sizing_plan(title, goal, scope, acceptance)
    try:
        outcome = ask_one(job, plan, decisions.Deadline())
    except Exception as exc:  # the transport reports its own failures as outcomes; this guards an unexpected raise
        if selecting:
            return QueueSizing(stop=('sizing-fallback', f'work sizing could not run ({type(exc).__name__}); edit the item\'s type'))
        return QueueSizing()
    route, fallback = decide(outcome, plan, plan, False)
    if selecting and route is None:
        return QueueSizing(stop=('sizing-fallback', f"work sizing fell back ({fallback}, request {outcome.request_id}); edit the item's type"))
    entry = lambda doc: sizing_entry(doc['id'], outcome, route, fallback, doc, trigger=job.trigger, plan=plan)
    return QueueSizing(kind=route if selecting else None, classification=entry)


def size_work(repo_root, create_with, title, goal, scope, acceptance):
    """Classify the proposed work and create the cycle with the permitted type the answer names.

    `create_with(kind, classification)` performs the creation. An unconfigured classifier refuses with no receipt.
    A fallback refuses creation and raises SizingFallback carrying the receipt."""
    state = classifier_state(repo_root)
    if not state['configured']:
        raise CycleError(f"type auto needs the classifier, which is unconfigured ({state['reason']}); create with an explicit --type")
    types = sizing_types()
    evidence = sizing_evidence(title, goal, scope, acceptance)
    job = Job('work-sizing', 'new')
    plan = sizing_plan(title, goal, scope, acceptance)
    outcome = ask_one(job, plan, decisions.Deadline())
    route, fallback = decide(outcome, plan, plan, False)
    if route is not None:
        return create_with(route, lambda doc: sizing_entry(doc['id'], outcome, route, None, doc, plan=plan))
    qset = questions.question_set('work-sizing')
    receipt = {'request_id': outcome.request_id, 'question_set': 'work-sizing', 'question_version': qset.version,
               'model': decisions.EXPECTED_SERVED_MODEL, 'served_model': outcome.served_model, **billing_of(outcome), 'answer': answer_of(outcome), 'fallback': fallback,
               'fingerprint': plan.fingerprint, 'question_ids': list(plan.question_ids)}
    question = {'set': 'work-sizing', 'version': qset.version, 'instructions': qset.instructions, 'options': questions.options('work-sizing', types)}
    raise SizingFallback(fallback, receipt, question, evidence)


def validate_sizing_receipt(receipt):
    """Validate a receipt against the named subset of the classification-entry schema, or raise CycleError.

    request_id and served_model may be null; any other deviation is refused."""
    from council_records import _validator
    validator = _validator()
    schema = validator.load_schema(Path(__file__).parent.parent / 'schemas/cycle.schema.json')
    entry = schema['properties']['classifications']['items']
    subset = {'type': 'object', 'additionalProperties': False, 'required': list(SIZING_RECEIPT_FIELDS),
              'properties': {name: entry['properties'][name] for name in SIZING_RECEIPT_FIELDS + SIZING_RECEIPT_OPTIONAL}}
    errors = []
    validator.validate(receipt, subset, '#', '#', errors, 'sizing-receipt')
    if errors:
        raise CycleError(f"invalid sizing receipt: {errors[0]['error']}")
    if receipt['question_set'] != 'work-sizing' or not receipt['fallback']:
        raise CycleError('invalid sizing receipt: it must be a work-sizing fallback receipt')
    return receipt


def receipt_classification(receipt):
    """The `classification` callable for `create`: the receipt written as the fallback entry in the creating save."""
    return lambda doc: sizing_entry(doc['id'], None, None, receipt['fallback'], doc, receipt)


# ───────────────────────────── inspect: classifier, floor and offered routes ─────────────────────────────

def current_entries(doc):
    """The latest route entry of the current pass for each (kind, subject)."""
    latest = {}
    for entry in doc.get('classifications', []):
        if (entry['pass'] == doc['pass'] and entry['kind'] != 'work-sizing'
                and entry.get('routing_policy_version') == ROUTING_POLICY_VERSION):
            latest[(entry['kind'], entry['subject'])] = entry
    return list(latest.values())


def job_of(entry):
    return Job(entry['kind'], entry['subject'], entry.get('trigger'))


@advisory.advisory_operation
def valid_plan(cfg, doc, entry, repo_root=None, *, cache=None):
    with advisory.facts_scope():
        return _valid_plan(cfg, doc, entry, repo_root, cache=cache)


def _valid_plan(cfg, doc, entry, repo_root=None, *, cache=None):
    """The current plan when the stored entry may still be offered, else None (the entry is history).

    It is offered only while its fingerprint matches, its question-set version and route id exist in current code,
    and current policy permits its route. An unknown id or version never raises."""
    advisory.checkpoint()
    route = entry.get('route')
    if not route or doc['status'] != 'active' or entry['pass'] != doc['pass']:
        return None
    cache = cache if cache is not None else {}
    if '__configuration__' not in cache:
        cache['__configuration__'] = (classifier_state(repo_root or cfg.repo_root), decisions.classifier_basis())
    status, basis = cache['__configuration__']
    if not status['configured']:
        return None
    if entry['kind'] not in questions.QUESTION_SETS or questions.question_set(entry['kind']).version != entry['question_version']:
        return None
    if entry['question_set'] != entry['kind']:
        return None
    if not questions.route_exists(entry['kind'], route):
        return None
    try:
        if 'question_ids' in entry:
            original = Plan({}, [], None, question_ids=tuple(entry['question_ids']),
                            context_question_ids=tuple(entry.get('context_question_ids') or entry['question_ids']))
            plan = current_input(cfg, doc, job_of(entry), original, basis, repo_root or cfg.repo_root, cache)
        else:
            # Older fingerprints bound policy facts only; keep their reader interpretation, never reuse them.
            plan = plan_of(cfg, doc, job_of(entry), repo_root or cfg.repo_root)
    except advisory.AdvisoryUnavailable:
        raise
    except (CycleError, OSError, ValueError, KeyError):
        return None
    advisory.checkpoint()
    if plan is None or plan.fingerprint != entry['fingerprint'] or route not in plan.routes:
        return None
    return plan


@advisory.advisory_operation
def review_block(cfg, doc) -> dict | None:
    """The review floor and the specialist set a reviewer is assigned; listed in Review whatever the classifier did."""
    if doc['phase'] != 'review' or doc['status'] in CLOSED:
        return None
    floor = review_floor(cfg, doc)
    chosen = set()
    cache = {}
    try:
        with advisory.facts_scope():
            for entry in current_entries(doc):
                if entry['kind'] == 'review-routing' and (entry.get('route') or '').startswith('add:') and valid_plan(cfg, doc, entry, cache=cache):
                    chosen.add(entry['route'][4:])
            advisory.checkpoint()
    except advisory.AdvisoryUnavailable:
        chosen.clear()
    # Specialists are only ever added: the floor stays whole, and an added specialist whose concern the floor or an
    # earlier added specialist already reviews is a duplicate and is dropped.
    concerns = {concern(ident) for ident in floor['specialists']}
    added = []
    for ident in SPECIALISTS:
        if ident in chosen and ident not in floor['specialists'] and concern(ident) not in concerns:
            added.append(ident)
            concerns.add(concern(ident))
    return {'floor': floor['specialists'], 'sources': floor['sources'], 'scrutiny': floor['scrutiny'], 'added': added,
            'specialists': floor['specialists'] + added, 'changed_paths': path_bound(floor['paths'])}


def name_specialists(found, review):
    """Add the review block's specialists to a Review-phase prepare-dispatch action, as inspect's own offer does."""
    found['specialists'] = review['specialists']
    found['purpose'] += '; name these specialists in the reviewer assignment: ' + (', '.join(review['specialists']) or 'none required')
    return found


def route_action(cfg, doc, entry, host):
    """The next action for a stored route, complete except the fields `caller_fills` names."""
    import cycle_ops as ops
    route, subject, kind = entry['route'], entry['subject'], entry['kind']
    tag = {'kind': kind, 'route': route, 'subject': subject, 'request_id': entry['request_id']}
    if route in ('agent', 'agent-assessment'):
        return {'agent': True, 'classification': tag, 'caller_fills': [],
                'purpose': f'the classifier routed {subject} to the responsible agent: assess it and act with the deterministic actions'}
    if kind != 'failure-routing' and route not in ('return', 'fix-step', 'follow-up'):
        return None
    if route == 'stale-state-refresh':
        return {**ops.action({'op': 'inspect', 'host': host} if host else {'op': 'inspect'}, [], 'refresh the stale state before following its current action'), 'classification': tag}
    if route in ('request-repair', 'environment-investigation', 'missing-evidence-request', 'owning-developer', 'acceptance-fix'):
        # These are bounded handler offers, not a tool grant or an unconditional dispatch.
        # The host hook resolves the legal reopen/dispatch/fix sequence against its locked snapshot.
        return {'agent': True, 'classification': tag, 'handler': route, 'caller_fills': [],
                'purpose': questions.description(kind, route), 'preserves': ['authorization', 'attempt-limit', 'pass-limit', 'failing-gate']}
    if route == 'return':
        found = ops.lowlevel(cfg, ['return', doc['id']], f'record the counted return to Build for {subject}',
                             ['--improved', '--unresolved', '--next-change', '--justification', '--progress'])
        return {**found, 'classification': tag}
    if route == 'fix-step':
        found = ops.lowlevel(cfg, ['task-add', doc['id'], '--json'], f'add the fix task for finding {subject}; its fix names the finding and why it is small',
                             ['--json'])
        return {**found, 'classification': tag, 'finding': subject}
    if route == 'follow-up':
        found = ops.lowlevel(cfg, ['defer', doc['id'], '--finding', subject, '--note'],
                             f'record finding {subject} as deferred follow-up; the note names where the follow-up is recorded', ['--note'])
        return {**found, 'classification': tag}
    if route == 'mark-lost':
        entry_a = assignment_entry(doc, subject) or next((a for a in reversed(doc.get('assignments', [])) if a['task'] == subject and a['state'] in OPEN), None)
        if entry_a is None:
            held = [a for a in doc.get('assignments', []) if a['state'] in OPEN]
            entry_a = held[0] if held else None
        if entry_a is None:
            return None
        found = ops.attempt_routes(entry_a)[1]
        found['purpose'] = 'conditional on affirmative host evidence: ' + found['purpose']
        return {**found, 'classification': tag}
    if route == 're-dispatch':
        task_id = subject
        entry_a = assignment_entry(doc, subject)
        if entry_a is not None:
            task_id = entry_a['task']
        else:
            entry_a = next((a for a in reversed(doc.get('assignments', [])) if a['task'] == task_id), None)
        request, fills = {'op': 'prepare-dispatch', 'task_id': task_id}, []
        role = entry_a['role'] if entry_a else None
        use_host = (entry_a or {}).get('host') or host
        for name, value in (('role', role), ('host', use_host if use_host in _hosts() else None)):
            if value:
                request[name] = value
            else:
                fills.append(name)
        found = ops.action(request, fills, f'dispatch task {task_id} again as a new attempt within the attempt limit')
        task = ops.task_entry(doc, task_id)
        review = review_block(cfg, doc) if task is not None and task['phase'] == 'review' else None
        if review is not None:
            name_specialists(found, review)
        return {**found, 'classification': tag}
    return None


@advisory.advisory_operation
def offered_actions(cfg, doc, host, repo_root=None) -> list:
    try:
        with advisory.facts_scope():
            return _offered_actions(cfg, doc, host, repo_root)
    except advisory.AdvisoryUnavailable:
        return []


def _offered_actions(cfg, doc, host, repo_root=None) -> list:
    """Stored routes inspect offers first, one per subject, each only while it passes the offer conditions."""
    out = []
    cache = {}
    for entry in current_entries(doc):
        if entry['kind'] in ('review-routing',) or valid_plan(cfg, doc, entry, repo_root, cache=cache) is None:
            continue
        found = route_action(cfg, doc, entry, host)
        if found is not None:
            out.append(found)
    advisory.checkpoint()
    return out
