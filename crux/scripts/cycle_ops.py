"""Typed cycle operations: one request document, one locked transaction, one response.

Entry point: `run(repo_root, cycle_id, request) -> (exit_code, response)`, reached
through `cycle.py op CYCLE --json REQUEST`. The request shape is
crux/schemas/cycle-operation.schema.json.

Response on success::

    {"ok": true, "op": OP, "cycle": ID, "op_id": ID|null, "changed": bool,
     "revision": N, "replayed": bool, ...operation fields}

Response on refusal (nothing written)::

    {"ok": false, "op": OP, "cycle": ID, "errors": [
        {"code", "field", "expected", "observed", "problem", "recovery": [ACTION|ARGV]}]}

An ACTION is ``{"request": {...}, "caller_fills": [...], "purpose": str}``; `request`
validates against the operation schema once the fields `caller_fills` names are
filled. An ARGV is ``{"argv": [...], "caller_fills": [...], "purpose": str}`` for a
low-level command; `caller_fills` names the flags that need the caller's judgment.
The engine never inserts placeholder values.

Optional classifications return their outcomes and the post-write revision. Dispatch selects
a permitted role and optional context; retained deliveries assess evidence completeness and
stopless failures. Mutating Build boundaries refresh additive test suggestions. Inspect reads
stored current answers without provider calls or writes. Exact known refusal codes use code
handlers before semantic judgment. A classification grants no approval, pass or tool.

Exit codes: 0 succeeded (including an idempotent replay), 1 refused, 2 environment.

Every mutating operation runs under one hold of the cycle lock: load, journal lookup,
request validation, every argument and state check (collected), mutation, schema
validation and one atomic save that carries the operation's journal entry and its
history event. Every operation the schema names is implemented here: inspect,
prepare-dispatch, attach-execution, deliver, mark-lost, advance, finish,
owner-exception and upgrade.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import time
import uuid

import cycle_activity
import cycle_summary
import cycle_classify
import cycle_context as cycle_advisory
import cycle_questions
import cycle_commit
import cycle_hosts
import cycle_dispatch
import cycle_execution
import cycle_local_skills
from cycle_workflow import (
    ASSIGNMENT_V3_FIELDS, CHECK_PHASES, CLOSED, OPEN, PHASES, CycleError, LinkedWorktree, atomic_bytes, check_coverage, check_references, check_tests, contained, event,
    legacy, listed, load, locked, main_checkout, now, path_class, phases_of, read_retained, requirements, resolve_commit, run_git, save,
    source_fingerprint, tree, updated_task, v3_fields, dependency_satisfied,
    council_state, latest_idr, withdraw_decision, withdrawn_names, adr_dependency_problems,
)

SCHEMA = Path(__file__).resolve().parent.parent / 'schemas/cycle-operation.schema.json'
CYCLE_SCRIPT = Path(__file__).resolve().parent / 'cycle.py'
OPERATIONS = ('inspect', 'dispatch-invocation', 'execution-check', 'child-link', 'release-continue', 'advice-refresh', 'prepare-dispatch', 'attach-execution', 'deliver', 'mark-lost', 'advance', 'finish',
              'owner-exception', 'upgrade', 'commit-record', 'withdraw-decision')
VERSION = 3
# The history action an operation records when it differs from the operation's name.
EVENT_NAMES = {'upgrade': 'upgraded'}
# Each task and role accepts at most this many attempts within one pass, of any outcome.
ATTEMPT_LIMIT = 3
# Operations that write no journal entry and so carry no op_id.
UNJOURNALED = ('inspect', 'dispatch-invocation', 'commit-record')
ASSIGNMENT_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')


class Refused(Exception):
    def __init__(self, errors, **details):
        super().__init__('; '.join(e['problem'] for e in errors))
        self.errors = errors
        self.details = details


def failure(code, problem, *, field=None, expected=None, observed=None, recovery=None):
    return {'code': code, 'field': field, 'expected': expected, 'observed': observed, 'problem': problem,
            'recovery': recovery or []}


def action(request, caller_fills, purpose):
    return {'request': request, 'caller_fills': ['op_id', *caller_fills] if request['op'] not in UNJOURNALED else list(caller_fills),
            'purpose': purpose}


def lowlevel(cfg, args, purpose, caller_fills=()):
    return {'argv': ['uv', 'run', str(CYCLE_SCRIPT), '--repo-root', str(cfg.repo_root), '--compact', *args],
            'caller_fills': list(caller_fills), 'purpose': purpose}


# ───────────────────────────── request handling ─────────────────────────────

def canonical(request) -> bytes:
    return json.dumps(request, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def request_digest(request) -> str:
    return hashlib.sha256(canonical(request)).hexdigest()


def schema_errors(request):
    from council_records import _validator
    validator = _validator()
    errors = []
    validator.validate(request, validator.load_schema(SCHEMA), '#', '#', errors, 'operation')
    out = []
    for e in errors:
        name = e['instance_path'][2:] or None
        missing = re.search(r"missing required property '([^']+)'", e['error'])
        if missing:
            name = missing.group(1)
        out.append(failure('invalid-request', e['error'], field=name, expected=e['schema_path'], observed=None))
    return out


@cycle_advisory.cache_only_operation
@cycle_advisory.advisory_operation
def run(repo_root, cycle_id, request):
    """Apply one typed operation; return (exit code, response)."""
    op = request.get('op') if isinstance(request, dict) else None
    base = {'op': op, 'cycle': cycle_id}
    if not isinstance(request, dict) or op not in OPERATIONS:
        return 1, {**base, 'ok': False, 'errors': [failure('invalid-request', 'the request must be a JSON object whose op is one of ' + ', '.join(OPERATIONS),
                                                           field='op', expected=list(OPERATIONS), observed=op)]}
    try:
        if op == 'advice-refresh':
            errors = schema_errors(request)
            if errors:
                raise Refused(errors)
            from crux import decisions
            try:
                with cycle_advisory.provider_scope(True), cycle_advisory.advisory_scope(decisions.Deadline(seconds=5.0), fresh=True):
                    result = refresh_advice(repo_root, cycle_id, request)
            except (cycle_advisory.AdvisoryUnavailable, KeyboardInterrupt) as exc:
                with locked(repo_root) as (cfg, _):
                    doc = load(repo_root, cycle_id)
                    check_version(cfg, doc, op)
                    result = replay(cfg, doc, request)
                    if result is None:
                        result = commit(cfg, doc, request, {'advice': 'optional',
                            'classification_unavailable': 'cancelled' if isinstance(exc, KeyboardInterrupt) else 'deadline-exhausted'},
                            {'kinds': list(dict.fromkeys(request.get('kinds', ['review-routing', 'focused-test-ranking'])))})
            result['record_commit'] = cycle_commit.after_write(repo_root, cycle_id)
            return 0, {**base, 'ok': True, **result}
        if op == 'dispatch-invocation':
            errors = schema_errors(request)
            if errors:
                raise Refused(errors)
            with locked(repo_root) as (cfg, _):
                doc = load(repo_root, cycle_id)
                check_version(cfg, doc, op)
                result = dispatch_invocation(cfg, doc, request)
            return 0, {**base, 'ok': True, **result}
        if op == 'inspect':
            errors = schema_errors(request)
            if errors:
                raise Refused(errors)
            # From a linked worktree, inspect reads and evaluates the main checkout, never a stale copy.
            found = inspect(main_checkout(repo_root) or repo_root, cycle_id, request)
            return 0, {**base, 'ok': True, **(summarize(found) if request.get('summary') else found)}
        if op == 'commit-record':
            errors = schema_errors(request)
            if errors:
                raise Refused(errors)
            # An op_id is validated by the schema and echoed, never journaled: the commit is idempotent.
            return 0, {**base, 'ok': True, 'op_id': request.get('op_id'), **cycle_commit.commit_record(repo_root, cycle_id, 'checkpoint')}
        deadline = cycle_advisory.advisory_deadline()
        result = mutate(repo_root, cycle_id, request, decisions_deadline=deadline)
        found = {**result, **classify_success(repo_root, cycle_id, request, result, decisions_deadline=deadline)}
        # Routine hooks consume current cache only; they never own a provider wait.
        if op == 'execution-check' and request.get('record_commit') == 'defer':
            # The worker's adjacency-bound source commit goes first; it then runs commit-record.
            found['record_commit'] = deferred_record_commit(repo_root, cycle_id)
        elif op in cycle_commit.COMMITTING:
            found['record_commit'] = cycle_commit.after_write(repo_root, cycle_id)
        if op in ('deliver', 'release-continue'):
            found.update(release_finish(repo_root, cycle_id, request))
        if cycle_advisory.advisory_unavailable():
            found['advisory_unavailable'] = 'deadline-exhausted'
        return 0, {**base, 'ok': True, **found}
    except Refused as exc:
        return 1, {**base, 'ok': False, 'errors': exc.errors, **exc.details,
                   **classify_refusal(repo_root, cycle_id, request, exc.errors)}
    except LinkedWorktree as exc:
        return 1, {**base, 'ok': False, 'errors': [failure('linked-worktree', str(exc), field='repo_root', expected=str(exc.main),
                                                           observed=str(repo_root))]}
    except cycle_execution.ExecutionError as exc:
        return 1, {**base, 'ok': False, 'errors': [failure(exc.code, str(exc), observed=exc.details, recovery=[
            *([{'argv': exc.details['argv'], 'caller_fills': [], 'purpose': 'fast-forward this clean older checkout to the immutable base, then check again'}]
              if 'argv' in exc.details else []),
            *execution_recovery(repo_root, cycle_id, exc, request),
            action({'op': 'inspect'}, [], 'inspect the exact attempt; use normal isolated checkout/integration for unverified source, never reset shared work')])]}
    except cycle_dispatch.SnapshotError as exc:
        return 1, {**base, 'ok': False, 'errors': [failure(exc.code, str(exc), recovery=[
            action({'op': 'inspect'}, [], 'inspect the exact attempt; await or attach it, or use existing affirmative loss evidence before a new attempt')])]}
    except CycleError as exc:
        return 1, {**base, 'ok': False, 'errors': [failure('cycle-refused', str(exc))]}


def deferred_record_commit(repo_root, cycle_id):
    """execution-check with record_commit "defer": the proof and record stay on disk, uncommitted."""
    try:
        cfg = tree(repo_root)
        pending = cycle_commit.pending_files(cfg, cycle_commit.record_paths(cfg, cycle_id)) or []
    except (CycleError, OSError):
        pending = []
    return {'changed': False, 'commit': None, 'deferred': 'requested-adjacent-commit', 'pending': pending,
            'request': {'op': 'commit-record'},
            'note': ('make the adjacency-bound source commit now with git commit --only naming exactly the '
                     "checkpoint's edited paths, then run commit-record; this relies on the one-editor guard")}


# A refusal's recovery names one route each. Neither route depends on another task's intent.
NEW_PASS_ROUTE = ('return to a new pass: a counted return with --execution-task, legal from Build after every attempt '
                  'is delivered (the writer re-runs the proof of that task and refuses unless it refuses this way), and '
                  "from Verify or Review. The new pass's task base is HEAD at the task's first reservation in that pass, "
                  'so this commit then lies below the base. It needs no replacement task and keeps delivered work; an '
                  'unfinished fix task leaves the plan. It counts against the pass limit; at an exhausted limit the cycle '
                  'pauses for the existing resume route. Consequence: the commit lies below every new task base, so no '
                  "execution proof accounts for it, and its task's next done delivery covers only commits above that "
                  "task's new base; the return-requested event retains every abandoned range under execution_refusal")
RETURN_FILLS = ('--improved', '--unresolved', '--next-change', '--justification', '--progress')
DAMAGED_REPORT_NOTE = ('a retained delivery report that would ground this commit is damaged: restore the bytes that '
                       'match its recorded sha256 from the commit that retained it (git log -- PATH, then git show '
                       'COMMIT:PATH) and check again; otherwise take the new-pass route')
OUTSIDE_SCOPE_NOTE = ('a path outside the recorded scope cannot be committed by this attempt. Remove uncommitted bytes '
                      'at exactly these paths only when your own edit in this attempt wrote them and git status showed '
                      'the path clean before that edit; otherwise remove nothing. In both cases deliver blocked naming '
                      'the paths; the plan owner adds them to scope or another task regenerates them')
OUTSIDE_STREAM_NOTE = ("the plan owner revises this task's stream: add these paths to the stream when it stays disjoint "
                       "from every other independent stream, otherwise remove the task's stream field so it falls back "
                       'to plan-scope ownership. Before delivering blocked, remove your own uncommitted bytes at exactly '
                       'these paths, put a diff of the removed bytes in the blocked report so the re-dispatch can '
                       'reapply them, and list your commits in the blocked delivery')


def refused_task(repo_root, cycle_id, request):
    """The task a refused request names: a prepare-dispatch task_id, or an execution-check assignment's task."""
    request = request or {}
    if request.get('op') == 'prepare-dispatch' and isinstance(request.get('task_id'), str):
        return request['task_id']
    if isinstance(request.get('assignment'), str):
        try:
            entry = assignment_entry(load(repo_root, cycle_id), request['assignment'])
        except (CycleError, OSError, ValueError, KeyError, TypeError):
            entry = None
        if entry is not None:
            return entry.get('task')
    return None


def execution_recovery(repo_root, cycle_id, exc, request=None):
    """Code-specific recovery for an execution refusal; empty for other codes."""
    def low(args, purpose, fills=()):
        return {'argv': ['uv', 'run', str(CYCLE_SCRIPT), '--repo-root', str(repo_root), '--compact', *args],
                'caller_fills': list(fills), 'purpose': purpose}
    paths = exc.details.get('paths', [])
    if exc.code in ('execution-foreign-source', 'execution-source-outside-scope'):
        task = refused_task(repo_root, cycle_id, request)
        if task:
            routes = [low(['return', cycle_id, '--execution-task', task], NEW_PASS_ROUTE, RETURN_FILLS)]
        else:
            routes = [low(['return', cycle_id], NEW_PASS_ROUTE, ['--execution-task', *RETURN_FILLS])]
        for item in exc.details.get('damaged_reports', []):
            try:
                cfg = tree(repo_root)
                name = (cfg.docs_root / str(item.get('path'))).relative_to(cfg.repo_root).as_posix()
            except (CycleError, OSError, ValueError):
                name = str(item.get('path'))
            routes.append({'argv': ['git', '-C', str(repo_root), 'log', '--format=%H', '--', name],
                           'caller_fills': [], 'purpose': DAMAGED_REPORT_NOTE, 'report': item})
        return routes
    if exc.code == 'execution-edited-path-outside-scope':
        return [{'argv': None, 'caller_fills': [], 'purpose': OUTSIDE_SCOPE_NOTE, 'paths': paths}]
    if exc.code == 'execution-edited-path-outside-stream':
        return [low(['plan', cycle_id], OUTSIDE_STREAM_NOTE, ['--file', '--reason']) | {'paths': paths}]
    return []


def refresh_advice(repo_root, cycle_id, request):
    """One explicit optional refresh, batching all eligible requested question kinds."""
    from crux import decisions
    with locked(repo_root) as (cfg, _):
        doc = load(repo_root, cycle_id)
        check_version(cfg, doc, 'advice-refresh')
        if (problem := stale_cycle(doc, allow_paused=False)):
            raise Refused([problem])
        prior = next((item for item in doc['operations'] if item['op_id'] == request['op_id']), None)
        if prior:
            if prior['request_sha256'] != request_digest(request):
                raise Refused([failure('op-id-reused', 'advice refresh operation id was already used for another request')])
            return {'op_id': request['op_id'], 'replayed': True, 'changed': False, **prior['result']}
        task = task_entry(doc, request.get('task_id')) if request.get('task_id') else None
        kinds = list(dict.fromkeys(request.get('kinds', ['review-routing', 'focused-test-ranking'])))
        role = request.get('role')
        if 'context-selection' in kinds and task is None:
            raise Refused([failure('unknown-task', 'task context advice requires a recorded task_id')])
        if 'context-selection' in kinds and role not in cycle_advisory.available_roles():
            raise Refused([failure('role-selection-required', 'context advice requires an explicit configured role')])
        jobs = []
        if task is not None:
            if 'context-selection' in kinds:
                choices = cycle_advisory.candidates(doc, task, role)
                jobs += [cycle_classify.Job('context-selection', f'{task["id"]}:skill-{i}', 'role:' + role)
                         for i in range(len(choices))]
        if 'focused-test-ranking' in kinds and doc['phase'] == 'build':
            jobs += [cycle_classify.Job('focused-test-ranking', f'candidate-{i}')
                     for i in range(len(cycle_advisory.focused_candidates(cfg, doc)))]
        if 'review-routing' in kinds and doc['phase'] == 'review':
            floor = cycle_classify.review_floor(cfg, doc)
            jobs += [cycle_classify.Job('review-routing', cycle_classify.REVIEW_SUBJECT + ident)
                     for ident in cycle_classify.SPECIALISTS if ident not in floor['specialists']]
        if 'review-finding-grouping' in kinds:
            jobs += cycle_classify.grouping_jobs(cfg, doc)
        if 'finding-disposition' in kinds and doc['reviews']:
            report = read_retained(cfg, doc['reviews'][-1])
            jobs += [cycle_classify.Job('finding-disposition', f'r{len(doc["reviews"])}:{category}:{i}')
                     for category in ('blocking', 'advisory', 'cosmetic') for i in range(len(report[category]))]
        assignment = assignment_entry(doc, request.get('assignment')) if request.get('assignment') else None
        if 'handoff-completeness' in kinds:
            if assignment is None or not assignment.get('delivery'):
                raise Refused([failure('unknown-assignment', 'handoff refresh requires a retained assignment delivery')])
            target = task_entry(doc, assignment['task'])
            jobs += [cycle_classify.Job('handoff-completeness', f'{assignment["id"]}/{assignment["attempt"]}/evidence-{i}')
                     for i in range(len(target['expected_evidence']))]
        if 'failure-routing' in kinds:
            if assignment and (assignment.get('delivery') or {}).get('outcome') in ('failed', 'blocked'):
                jobs.append(cycle_classify.Job('failure-routing', assignment['task'],
                                               f'delivery:{assignment["id"]}/{assignment["attempt"]}'))
            elif request.get('evidence_id'):
                failed = cycle_classify.receipt_record(repo_root, request['evidence_id'])
                if failed.get('status') != 'failed':
                    raise Refused([failure('failure-evidence-required', 'failure advice needs a recorded failed check')])
                jobs.append(cycle_classify.Job('failure-routing', failed['declaration']['check_id'],
                                               'check:' + request['evidence_id']))
            else:
                raise Refused([failure('failure-evidence-required', 'failure advice needs a failed retained assignment or receipt')])
    # Explicit refresh has one short transport/local deadline. The transport's
    # existing scans, privacy policy, fresh locked validation and independent
    # question fallbacks remain the same as other admitted classifier calls.
    found = cycle_classify.safely(cycle_classify.classify, repo_root, cycle_id, jobs,
                                  decisions_deadline=cycle_advisory.advisory_deadline())
    with locked(repo_root) as (cfg, _):
        doc = load(repo_root, cycle_id)
        return commit(cfg, doc, request, {'classifications': found.get('classifications', []),
                      'advice': 'optional', 'classification_unavailable': found.get('classification_unavailable')},
                      {'kinds': kinds})


def release_finish(repo_root, cycle_id, request):
    """Finish a listed release cycle once a delivery leaves every step done (IDR lean-workflow-traps-and-recovery approach 2).

    Runs after the delivery is saved and committed, so a refused finish leaves the delivery recorded and
    committed; the refusal is reported under `finish` and inspect keeps offering finish. A replay of the
    delivery reaches here too, so a crash between the delivery and its finish is completed by the replay
    without repeating the delivery. The finish op_id derives from the delivery's, so a repeat of a
    finished one replays. Returns {} when the cycle is not a release cycle ready to finish."""
    try:
        doc = load(repo_root, cycle_id)
    except CycleError:
        return {}
    if (doc.get('schema_version') != VERSION or not listed(doc) or doc['status'] != 'active'
            or any(t['status'] != 'done' for t in doc['plan']['tasks'])
            or any(e['state'] in OPEN for e in doc.get('assignments', []))):
        return {}
    finish_request = {'op': 'finish', 'op_id': 'release-finish-' + hashlib.sha256(request['op_id'].encode()).hexdigest()[:24],
                      'expect_revision': doc['revision']}
    try:
        finished = mutate(repo_root, cycle_id, finish_request)
    except Refused as exc:
        return {'finish': {'ok': False, 'request': finish_request, 'errors': exc.errors}}
    except CycleError as exc:
        return {'finish': {'ok': False, 'request': finish_request, 'errors': [failure('cycle-refused', str(exc))]}}
    finished['record_commit'] = cycle_commit.after_write(repo_root, cycle_id)
    return {'finish': {'ok': True, **finished}}


def classification_fields(target, report):
    """Accumulate independent hook diagnostics without discarding an earlier question's fallback."""
    fields = cycle_classify.response_fields(report)
    target.setdefault('classifications', []).extend(fields.pop('classifications', []))
    target.update(fields)
    return target


def classify_success(repo_root, cycle_id, request, result, *, decisions_deadline=None):
    """Assess retained delivery and refresh suggestions outside the mutation lock, within one deadline.

    Replays and no-ops ask nothing. A named stop suppresses delivery interpretation; only the caller
    applies the stop. Completeness offers recovery and never establishes correctness or approval.
    """
    if (not cycle_advisory.provider_requests_allowed()
            or not result.get('changed') or result.get('replayed')):
        return {}
    found = {}
    if request['op'] == 'advance' and result.get('phase') == 'review':
        classification_fields(found, cycle_classify.safely(cycle_classify.entered_review, repo_root, cycle_id,
                                                          decisions_deadline=decisions_deadline))
    if request['op'] == 'deliver' and not request.get('stop'):
        classification_fields(found, cycle_classify.safely(cycle_classify.handoff, repo_root, cycle_id, result['task'],
                                                          result['assignment'], result['attempt'], decisions_deadline=decisions_deadline))
        with locked(repo_root) as (cfg, _):
            view=handoff_view(cfg,load(repo_root,cycle_id),result['assignment'],result['attempt'])
        needs_failure=result.get('outcome') in ('failed','blocked') or bool(view['unresolved'])
        if result.get('outcome') in ('failed', 'blocked'):
            classification_fields(found, cycle_classify.safely(cycle_classify.failed_delivery, repo_root, cycle_id, result['task'],
                                                              result['assignment'], result['attempt'], decisions_deadline=decisions_deadline))
        elif view['unresolved']:
            classification_fields(found, cycle_classify.safely(cycle_classify.unresolved_handoff, repo_root, cycle_id, result['task'],
                                                              result['assignment'], result['attempt'], decisions_deadline=decisions_deadline))
        classification_fields(found, cycle_classify.safely(cycle_classify.focused_tests, repo_root, cycle_id,
                                                          decisions_deadline=decisions_deadline))
        with locked(repo_root) as (cfg, _):
            doc = load(repo_root, cycle_id)
            found['handoff'] = handoff_view(cfg, doc, result['assignment'], result['attempt'])
            if needs_failure:
                offers = [offer for offer in cycle_classify.offered_actions(cfg, doc, None)
                          if offer.get('classification', {}).get('subject') in (result['task'], result['assignment'])]
                found['failure_recovery'] = failure_actions(cfg, doc, offers)
                if not found['failure_recovery'] and found['handoff'].get('assessment'):
                    found['failure_recovery']=[found['handoff']['assessment']]
            found['revision'] = doc['revision']
    return {key: value for key, value in found.items() if value != []}


REFUSAL_HANDLERS = {
    'unresolved-dispatch': 'inspect-open-attempt',
    'attempt-limit': 'counted-return-or-stop',
    'delivery-conflict': 'new-delivery-attempt',
    'superseded-attempt': 'inspect-current-attempt',
    'result-path-missing': 'inspect-current-attempt',
    'stale-revision': 'refresh-state',
    'op-id-reused': 'resubmit-new-operation',
}


def classify_refusal(repo_root, cycle_id, request, errors):
    """Exact code recoveries precede semantic judgment. A handler authorizes no action."""
    if not isinstance(request, dict):
        return {}
    handlers = [{'code': e['code'], 'handler': REFUSAL_HANDLERS[e['code']],
                 'actions': deepcopy(e.get('recovery') or [action({'op': 'inspect'}, [], 'inspect the current attempt')])}
                for e in errors if e.get('code') in REFUSAL_HANDLERS]
    remaining = [e for e in errors if e.get('code') not in REFUSAL_HANDLERS]
    result = {'recovery_handlers': handlers} if handlers else {}
    if any(e.get('code') in cycle_classify.REFUSAL_TRIGGERS for e in remaining):
        result.update(cycle_classify.response_fields(cycle_classify.safely(
            cycle_classify.refused_operation, repo_root, cycle_id, request, remaining)))
    return result


def mutation_basis(cfg, doc):
    """Ignore classifier bookkeeping only. Every semantic writer event and HEAD remain part of the fence."""
    snapshot = {key: value for key, value in doc.items() if key not in ('classifications', 'revision', 'updated_at', 'history')}
    snapshot['history'] = [{key: value for key, value in entry.items() if key != 'revision'}
                           for entry in doc['history'] if entry['action'] != 'classified']
    return request_digest({'record': snapshot, 'head': git_head(cfg)})


def selection_mutation(repo_root, cycle_id, request, prior, deadline):
    """Preflight the original request, ask outside the lock, then apply current pure readers.

    The original request is also the journal identity. A role recommendation never rewrites it.
    A classifier save advances revision but changes no semantic fact in the guarded snapshot.
    """
    from test_evidence import call_scope
    op = request['op']
    if not cycle_advisory.provider_requests_allowed():
        with locked(repo_root) as (cfg, _), call_scope():
            doc = load(repo_root, cycle_id)
            if (found := replay(cfg, doc, request)) is not None:
                return found
            if (errors := schema_errors(request)):
                raise Refused(errors)
            check_version(cfg, doc, op)
            if op == 'prepare-dispatch':
                dispatch_validation(cfg, doc, request, request.get('role'))
                role = cycle_classify.arrangement_result(cfg, doc, request['task_id'], role=request.get('role'))['role']
                if role is None:
                    raise Refused([failure('role-selection-required', 'choose the permitted role explicitly; optional advice is not required',
                                          recovery=[action(resubmission(request), ['role'], 'choose the accountable role')])])
                result, fields = prepare_dispatch(cfg, doc, request, resolved_role=role,
                                                  context=optional_context(cfg, doc, request['task_id'], role))
            else:
                result, fields = advance(cfg, doc, request, prior)
            return commit(cfg, doc, request, result, fields)
    with locked(repo_root) as (cfg, _), call_scope():
        doc = load(repo_root, cycle_id)
        if (replayed := replay(cfg, doc, request)) is not None:
            return replayed
        if (errors := schema_errors(request)):
            raise Refused(errors)
        check_version(cfg, doc, op)
        if op == 'prepare-dispatch':
            dispatch_validation(cfg, doc, request, request.get('role'))
            role = cycle_classify.arrangement_result(cfg, doc, request['task_id'], role=request.get('role'))['role']
            if role:
                dispatch_validation(cfg, doc, request, role)
        else:
            if doc['phase'] != 'build':
                result, fields = advance(cfg, doc, request, prior)
                return commit(cfg, doc, request, result, fields)
            # Build ranking alone needs a two-part transaction. Other advances keep their single validation.
            advance(cfg, deepcopy(doc), request, prior)
        basis, original_revision = mutation_basis(cfg, doc), doc['revision']
    diagnostics = {}
    if op == 'prepare-dispatch':
        report = cycle_classify.safely(cycle_classify.arrangement, repo_root, cycle_id, request['task_id'],
                                       role=request.get('role'), decisions_deadline=deadline)
        classification_fields(diagnostics, report)
        role = report.get('role')
        if role:
            classification_fields(diagnostics, cycle_classify.safely(cycle_classify.context_bundles, repo_root, cycle_id,
                                                                     request['task_id'], role, decisions_deadline=deadline))
    classification_fields(diagnostics, cycle_classify.safely(cycle_classify.focused_tests, repo_root, cycle_id,
                                                             decisions_deadline=deadline))
    try:
        with locked(repo_root) as (cfg, _), call_scope():
            doc = load(repo_root, cycle_id)
            if (replayed := replay(cfg, doc, request)) is not None:
                return replayed
            if mutation_basis(cfg, doc) != basis:
                if op == 'advance' and request['expect_revision'] != doc['revision']:
                    raise Refused([stale_revision(doc, request, 'advancing')])
                raise Refused([failure('dispatch-context-changed' if op == 'prepare-dispatch' else 'operation-context-changed',
                                       'the record or HEAD changed during optional classification; inspect before retrying',
                                       recovery=[action({'op': 'inspect'}, [], 'inspect the current state before retrying')])])
            if op == 'prepare-dispatch':
                selection = cycle_classify.arrangement_result(cfg, doc, request['task_id'], role=request.get('role'))
                role = selection['role']
                if role is None:
                    raise Refused([failure('role-selection-required', 'no current permitted role selection; the responsible agent must choose',
                                           field='role', expected=selection['permitted_roles'],
                                           recovery=[action(resubmission(request), ['role'], 'choose an explicit configured role without changing its grants')])])
                context = optional_context(cfg, doc, request['task_id'], role)
                result, fields = prepare_dispatch(cfg, doc, request, resolved_role=role, context=context)
            else:
                result, fields = advance(cfg, doc, request, prior, guard_revision=original_revision)
            # The journal must carry the caller's original payload, including its original revision.
            result = commit(cfg, doc, request, result, fields)
            diagnostics.pop('revision', None)
            return {**result, **{key: value for key, value in diagnostics.items() if value != []}}
    except Refused as exc:
        exc.details.update({key: value for key, value in diagnostics.items() if value != []})
        raise


def mutate(repo_root, cycle_id, request, *, decisions_deadline=None):
    op = request['op']
    from test_evidence import call_scope
    # A lookup that reads the shared evidence store runs before the cycle lock is taken, in its own
    # call scope. The locked half opens a fresh scope, so it validates what it attaches against the
    # state it holds the lock on.
    prior = PRELOOKUP[op](repo_root, cycle_id) if op in PRELOOKUP else None
    if op in ('prepare-dispatch', 'advance'):
        return selection_mutation(repo_root, cycle_id, request, prior, decisions_deadline)
    with locked(repo_root) as (cfg, _), call_scope():
        doc = load(repo_root, cycle_id)
        replayed = replay(cfg, doc, request)
        if replayed is not None:
            return replayed
        errors = schema_errors(request)
        if errors:
            raise Refused(errors)
        check_version(cfg, doc, op)
        handler = HANDLERS.get(op)
        if handler is None:
            raise Refused([failure('operation-unavailable', f'{op} is not available in this build of the cycle engine',
                                   field='op', observed=op)])
        result, fields = handler(cfg, doc, request, **({'prior': prior} if op in PRELOOKUP else {}))
        if not result.pop('changed', True):
            return {'op_id': request['op_id'], 'changed': False, 'revision': doc['revision'], 'replayed': False, **result}
        return commit(cfg, doc, request, result, fields)


def check_version(cfg, doc, op):
    version = doc['schema_version']
    if version == 1:
        raise Refused([failure('unsupported-version', 'typed operations need a version-3 record; a version-1 record keeps the low-level commands',
                               field='schema_version', expected=VERSION, observed=version)])
    if version == 2 and op != 'upgrade':
        raise Refused([failure('needs-upgrade', 'typed operations need a version-3 record; upgrade this cycle first',
                               field='schema_version', expected=VERSION, observed=version,
                               recovery=[action({'op': 'upgrade'}, [], 'upgrade the record to version 3, retaining its version-2 bytes')])])


def commit(cfg, doc, request, result, fields):
    """One atomic save: the change, its history event and its journal entry.

    `save` increments the revision and stamps it on the event, so the journal and the
    result carry the revision that save produces."""
    revision = doc['revision'] + 1
    event(doc, EVENT_NAMES.get(request['op'], request['op']), op_id=request['op_id'], **fields)
    result = {**result, 'revision': revision}
    doc['operations'].append({'op_id': request['op_id'], 'op': request['op'], 'request_sha256': request_digest(request),
                              'at': now(), 'revision': revision, 'result': journal_result(result)})
    save(cfg, doc)
    after = AFTER_SAVE.get(request['op'])
    if after:
        # An after-save step may add response fields; the journal and a replay never carry them.
        result = {**result, **(after(cfg, doc) or {})}
    return {'op_id': request['op_id'], 'changed': True, 'replayed': False, **result}


JOURNAL_KEYS = ('revision', 'assignment', 'attempt', 'task', 'result_path', 'base', 'delivery_token', 'invocation_snapshot', 'execution', 'execution_observation', 'handle', 'retained', 'sha256',
                'outcome', 'status', 'completion', 'phase', 'reused', 'next_assignment', 'next_attempt', 'next_delivery_token', 'stopped', 'step_result',
                'advice', 'classification_unavailable', 'evidence_size')


def journal_result(result):
    """The compact result kept in the journal: ids, paths and revision; never request text."""
    out = {key: result[key] for key in JOURNAL_KEYS if key in result}
    if 'execution' in out:
        out['execution'] = {key: out['execution'][key] for key in ('review_base', 'execution_head', 'checkout', 'proof')}
    return out


def replay(cfg, doc, request):
    """The journaled outcome for a repeated op_id, or None when the op_id is new."""
    op_id = request.get('op_id')
    entry = next((e for e in doc.get('operations', []) if e['op_id'] == op_id), None) if isinstance(op_id, str) else None
    if entry is None:
        return None
    observed = request_digest(request)
    if entry['request_sha256'] != observed:
        raise Refused([failure('op-id-reused', f'op_id {op_id} was used for a different request',
                               field='op_id', expected=entry['request_sha256'], observed=observed,
                               recovery=[action({k: v for k, v in request.items() if k != 'op_id'}, [],
                                                'submit this request under a new op_id')])])
    result = dict(entry['result'])
    out = {'op_id': op_id, 'changed': False, 'replayed': True, **result}
    if request['op'] in ('deliver', 'release-continue'):
        replay_delivery(cfg, doc, request, result)
        if request['op'] == 'release-continue' and result.get('next_assignment'):
            current = assignment_entry(doc, result['next_assignment'])
            if doc['status'] != 'active':
                out['continuation_unavailable'] = 'cycle-not-active'
            elif (current and current.get('delivery_token') != result.get('next_delivery_token')):
                out['continuation_unavailable'] = 'delivery-token-rotated; inspect the exact current attempt'
            elif current and current['attempt'] == result['next_attempt'] and current['state'] == 'running':
                try:
                    if current.get('host') != request['host'] or current.get('agent') != request['handle']:
                        raise Refused([failure('release-continuation-mismatch', 'the native execution binding changed')])
                    out['continuation'] = continuation_delta(cfg, doc, current)
                except (Refused, CycleError, cycle_dispatch.SnapshotError, OSError):
                    out['continuation_unavailable'] = 'release-continuation-stale; inspect the current attempt and use normal recovery'
    if request['op'] == 'execution-check':
        entry, proof, _ = execution_check_proof(cfg, doc, request)
        proof = stable_execution_proof(cfg, doc, entry, proof)
        if cycle_execution.digest(cycle_execution.encoded(proof)) != result['execution']['proof']['sha256']:
            raise Refused([failure('execution-proof-stale', 'checkout or attempt binding changed after this recorded check; refresh under a new operation id',
                                  recovery=[action(resubmission(request), [], 'check the current HEAD without replacing the immutable base')])])
    if request['op'] == 'prepare-dispatch':
        current = assignment_entry(doc, result['assignment'])
        attempt_open = (doc['status'] == 'active' and current is not None and current['attempt'] == result['attempt']
                        and current['state'] == 'reserved')
        out['attempt_state'] = current['state'] if current and current['attempt'] == result['attempt'] else 'superseded'
        out['cycle_status'] = doc['status']
        if attempt_open:
            if result.get('delivery_token') != current.get('delivery_token'):
                out['invocation_unavailable'] = 'delivery-token-rotated; retrieve the current exact attempt through inspect'
            elif current.get('invocation_snapshot'):
                recovered = dispatch_invocation(cfg, doc, {'assignment': current['id'], 'attempt': current['attempt']})
                ensure_directory(Path(result['result_path']).parent)
                out.update(recovered)
            else:
                out['invocation_unavailable'] = 'historical-no-snapshot; original caller/context bytes unavailable, never reconstructed'
    return out


def replay_delivery(cfg, doc, request, result):
    source = Path(result['result_path']) if result.get('result_path') else None
    try:
        data = source.read_bytes() if source and source.is_file() and not source.is_symlink() else None
    except OSError:
        data = None
    if data is None:
        data = contained(cfg.docs_root, result['retained']).read_bytes()
        source_label = 'the retained copy'
    else:
        source_label = 'the result file'
    observed = hashlib.sha256(data).hexdigest()
    if observed != result['sha256']:
        raise Refused([failure('delivery-conflict', f'{source_label} changed since this delivery was recorded',
                               field='result', expected=result['sha256'], observed=observed)])


# ───────────────────────────── shared requirements ─────────────────────────────

def completion_candidate(cfg, doc, *, lessons=None, remaining=None, tip=None):
    """The record finish would save, and the errors that stop it.

    Returns (candidate, errors). errors carry finish's refusal codes: open-attempts,
    no-commits, commits-not-linear, tip-invalid. Without lessons and remaining the
    candidate keeps an existing reflection, or carries an evaluation-only one that is
    never written."""
    errors = []
    held = [e for e in doc.get('assignments', []) if e['state'] in OPEN]
    if held:
        errors.append(failure('open-attempts', 'finish needs every attempt delivered or marked lost; open: '
                              + ', '.join(f"{e['id']}/{e['attempt']} ({e['state']})" for e in held),
                              field='assignments', expected='no reserved or running attempt',
                              observed=[f"{e['id']}/{e['attempt']}" for e in held]))
    collected = list(dict.fromkeys(c for t in doc['plan']['tasks'] for c in t.get('commits', [])))
    ordered = None
    if not collected:
        errors.append(failure('no-commits', 'no task records a commit, so ordinary completion has nothing to bind',
                              field='plan.tasks.commits', expected='at least one recorded commit', observed=[],
                              recovery=[action({'op': 'owner-exception'}, ['quote', 'conversation', 'date'],
                                               "close the cycle on the owner's own instruction, with its requirements recorded unmet")]))
    else:
        ancestors = ancestry(cfg, collected)
        if ancestors is None:
            ancestors = {c: {o for o in collected if o != c and is_ancestor(cfg, o, c)} for c in collected}
        tips = [c for c in collected if len(ancestors[c]) == len(collected) - 1]
        chosen = None
        if tip is not None:
            try:
                full = resolve_commit(cfg, tip)
            except CycleError as exc:
                full = None
                errors.append(failure('tip-invalid', str(exc), field='tip', expected='a commit that descends from every recorded commit', observed=tip))
            if full and all(o == full or is_ancestor(cfg, o, full) for o in collected):
                chosen = full
            elif full:
                errors.append(failure('tip-invalid', 'the given tip does not descend from every recorded commit',
                                      field='tip', expected='a commit that descends from every recorded commit', observed=tip))
        elif tips:
            chosen = tips[0]
        else:
            heads = [c for c in collected if not any(c in ancestors[o] for o in collected if o != c)]
            head = git_head(cfg)
            fill = []
            request = {'op': 'finish', 'expect_revision': doc['revision']}
            fills_in = [] if listed(doc) else ['lessons', 'remaining']
            if head and all(is_ancestor(cfg, c, head) for c in collected):
                request['tip'] = head
            else:
                fill = ['tip']
            errors.append(failure('commits-not-linear', 'no recorded commit descends from all the others; heads: ' + ', '.join(h[:12] for h in heads),
                                  field='tip', expected='one commit that descends from every recorded commit', observed=heads,
                                  recovery=[action(request, [*fills_in, *fill], 'finish at a tip that contains every recorded commit')]))
        if chosen:
            ordered = sorted((c for c in collected if c != chosen), key=lambda c: len(ancestors[c])) + [chosen]
    candidate = deepcopy(doc)
    if listed(doc):
        pass  # a release cycle needs no reflection
    elif lessons is not None:
        candidate['reflection'] = {'outcome': outcome_text(cfg, doc), 'lessons': list(lessons), 'remaining': list(remaining)}
    elif not candidate['reflection']:
        candidate['reflection'] = {'outcome': outcome_text(cfg, doc), 'lessons': ['(supplied by finish)'], 'remaining': ['(supplied by finish)']}
    if ordered:
        candidate['completion'] = {'commits': ordered, 'exception': None,
                                   'remaining': '; '.join(remaining) if remaining else ('none' if listed(doc) else 'supplied by finish'),
                                   'input_sha256': source_fingerprint(cfg.repo_root, candidate)}
    return candidate, errors


def outcome_text(cfg, doc):
    """Routine completion prose generated from recorded facts."""
    delivered = [t['id'] for t in doc['plan']['tasks'] if t['status'] == 'done']
    review = 'none recorded'
    if doc['reviews']:
        try:
            report = read_retained(cfg, doc['reviews'][-1])
            review = f"{report['verdict']} by {report['reviewer']} (pass {report['pass']})"
        except (CycleError, OSError, ValueError, KeyError):
            review = 'unreadable'
    return (f"Delivered tasks: {', '.join(delivered) or 'none'}. "
            f"Acceptance criteria: {'; '.join(doc['plan']['acceptance'])}. Latest review: {review}.")


# ───────────────────────────── git helpers ─────────────────────────────

def git_head(cfg):
    code, out = run_git(cfg, 'rev-parse', '--verify', '--quiet', 'HEAD')
    return out.strip() if code == 0 and out.strip() else None


def is_ancestor(cfg, older, newer):
    return run_git(cfg, 'merge-base', '--is-ancestor', older, newer)[0] == 0


def ancestry(cfg, commits):
    """{c: the other `commits` that are ancestors of c}, from one rev-list walk instead of a merge-base per pair.

    None when git cannot list the commits or a commit is not named by its full id; the caller then
    asks merge-base pair by pair, as before."""
    code, out = run_git(cfg, 'rev-list', '--parents', *commits, '--')
    if code:
        return None
    parents = {}
    for line in out.splitlines():
        sha, *above = line.split()
        parents[sha] = above
    if any(c not in parents for c in commits):
        return None
    wanted = set(commits)
    found = {}
    for commit in commits:
        seen, stack = set(), list(parents[commit])
        while stack:
            sha = stack.pop()
            if sha not in seen:
                seen.add(sha)
                stack.extend(parents.get(sha, ()))
        found[commit] = (seen & wanted) - {commit}
    return found


def trailer_commits(cfg, base, task_id):
    """Commits on HEAD since `base` whose `Cycle-Task:` trailer names the task, oldest first."""
    code, out = run_git(cfg, 'log', '--reverse', '--format=%H%x1f%(trailers:key=Cycle-Task,valueonly,separator=%x1e)%x1d', f'{base}..HEAD')
    if code:
        return []
    found = []
    for record in out.split('\x1d'):
        record = record.strip()
        if not record:
            continue
        sha, _, values = record.partition('\x1f')
        if task_id in {v.strip() for v in values.split('\x1e')}:
            found.append(sha.strip())
    return found


def carries_trailer(cfg, sha, task_id):
    code, out = run_git(cfg, 'log', '-1', '--format=%(trailers:key=Cycle-Task,valueonly,separator=%x1e)', sha)
    return code == 0 and task_id in {v.strip() for v in out.split('\x1e')}


# ───────────────────────────── shared lookups ─────────────────────────────

def assignment_entry(doc, ident):
    return next((e for e in doc.get('assignments', []) if e['id'] == ident), None)


def task_entry(doc, ident):
    return next((t for t in doc['plan']['tasks'] if t['id'] == ident), None)


def reservations(doc, task_id=None, role=None):
    """Typed reservations of the current pass, from history."""
    return [e for e in doc['history'] if e['action'] == 'prepare-dispatch' and e['pass'] == doc['pass']
            and (task_id is None or e.get('task') == task_id) and (role is None or e.get('role') == role)]


def task_base(cfg, doc, task_id):
    """HEAD at the task's first typed reservation in this pass; HEAD now when there is none."""
    earlier = reservations(doc, task_id)
    return earlier[0]['base'] if earlier else git_head(cfg)


def objectives_path(cfg):
    return str(cfg.docs_root / 'objectives.md')


def ensure_directory(path: Path):
    """Recreate a recorded result directory with mode 0700; refuse a symlink or a non-directory."""
    if path.is_symlink():
        raise Refused([failure('result-path-symlink', f'{path} is a symlink', field='result_path', observed=str(path))])
    if path.exists() and not path.is_dir():
        raise Refused([failure('result-path-not-directory', f'{path} exists and is not a directory', field='result_path', observed=str(path))])
    if not path.exists():
        path.mkdir(mode=0o700, parents=True)


def optional_context(cfg, doc, task_id, role):
    """An unavailable optional reader selects no bodies; it cannot remove the mandatory assignment."""
    try:
        return cycle_classify.context_result(cfg, doc, task_id, role)
    except Exception as exc:
        return {'selected': [], 'retrievable': [], 'error': type(exc).__name__}


def build_invocation(cfg, doc, request, entry, context=None):
    """The invocation for a reserved attempt. Its preamble names the engine that wrote the reservation
    and where the role runs on this host (IDR lean-workflow-traps-and-recovery approaches 12 and 13)."""
    context = context if context is not None else optional_context(cfg, doc, entry['task'], entry['role'])
    source_snapshot = cycle_dispatch.source_snapshot(cfg, doc, entry['role'], context)
    # Local candidates of the attempt's host change only the prompt text (IDR local-skill-dispatch-and-use approaches 1 to 7).
    local = cycle_local_skills.candidates(cfg.repo_root, entry['host'], task_entry(doc, entry['task'])['description'])
    base = entry['base']
    owner = request.get('integration_owner')
    preamble = cycle_hosts.preamble(cycle=doc['id'], task=entry['task'], assignment=entry['id'], attempt=entry['attempt'],
                                    objectives=objectives_path(cfg), result_path=entry['result_path'], base=base,
                                    task_commits=trailer_commits(cfg, base, entry['task']) if base else [],
                                    engine=str(CYCLE_SCRIPT), isolated=cycle_hosts.isolation(entry['host'], entry['role'], owner),
                                    delivery_token=entry.get('delivery_token'), role=entry['role'],
                                    local_skill_report=local['available'])
    text = cycle_hosts.assignment(role=entry['role'], host=entry['host'], objectives=objectives_path(cfg),
                                  repo_root=cfg.repo_root, docs_root=cfg.docs_root, cycle=doc,
                                  task=task_entry(doc, entry['task']), addendum=request.get('assignment_text', ''),
                                  integration_owner=owner)
    capabilities = cycle_hosts.capability_status(entry['role'], request.get('capabilities'),
                                                continuation=bool(entry.get('release_continuation')))
    text += '\nRequired native capabilities (unknown is not observed support):\n' + json.dumps(capabilities, sort_keys=True) + '\n'
    if entry.get('release_continuation'):
        text += ('\nFixed release continuation is enabled for this same native execution only. '
                 'After each actual step result, retain the exact marked report and submit release-continue. '
                 'The returned continuation is a context delta, never a new spawn. '
                 'This transport grants only release-continue and execution-check; native grants remain binding. '
                 'No command is executed by the engine. Frozen release limits/command descriptors:\n'
                 + json.dumps(entry['release_continuation'], sort_keys=True) + '\n')
    return cycle_dispatch.build(cfg, doc, request, entry, text, preamble, context, source_snapshot, local)


def dispatch_invocation(cfg, doc, request):
    """Return frozen executable parameters only for this eligible reserved attempt."""
    entry, errors = attempt_errors(doc, request, ('reserved', 'running', 'finished', 'lost'))
    if errors:
        raise Refused(errors)
    out = {'assignment': entry['id'], 'attempt': entry['attempt'], 'attempt_state': entry['state'],
           'invocation_snapshot': entry.get('invocation_snapshot')}
    if not entry.get('invocation_snapshot'):
        return {**out, 'invocation_unavailable': 'historical-no-snapshot; original caller/context bytes unavailable, never reconstructed'}
    bundle = cycle_dispatch.load(cfg, doc, entry['invocation_snapshot'])
    if entry['state'] != 'reserved':
        return {**out, 'invocation_unavailable': 'attempt-already-dispatched-or-closed; read retained context without dispatching again'}
    task = task_entry(doc, entry['task'])
    errors = [problem] if (problem := stale_cycle(doc, allow_paused=False)) else []
    if (task is None or task['phase'] != doc['phase'] or task['status'] != 'active'
            or task['assignee'] != entry['id'] or any(not dependency_satisfied(doc, dep) for dep in task['depends_on'])):
        errors.append(failure('invocation-task-ineligible', 'the recorded task no longer permits this reserved invocation',
                              recovery=[action({'op': 'inspect'}, [], 'inspect current eligibility and the exact attempt recovery')]))
    if errors:
        raise Refused(errors)
    cycle_dispatch.check_current(cfg, doc, entry, bundle)
    return {**out, 'invocation': deepcopy(bundle['invocation'])}


def stale_cycle(doc, allow_paused):
    if doc['status'] in CLOSED:
        return failure('cycle-closed', f"cycle {doc['id']} is {doc['status']}", field='status', expected='active', observed=doc['status'])
    if doc['status'] == 'paused' and not allow_paused:
        return failure('cycle-paused', 'the cycle is paused; resume it first', field='status', expected='active', observed='paused')
    return None


# ───────────────────────────── the main checkout's one editor ─────────────────────────────
# IDR one-editor-per-checkout revision 3, approaches 1 to 3: at most one editing attempt holds the main checkout.

EDITING_ROLES = ('developer', 'dev-lead')


def editing_task(task):
    """A Build-phase task or a fix task. A release step is in phase release, so it is never an editing task."""
    return task is not None and (task['phase'] == 'build' or 'fix' in task)


def targets_main_checkout(entry):
    """Whether an attempt edits the main checkout: its recorded host gives it no worktree, or no adapter knows the host."""
    host = entry.get('host')
    if not host or cycle_hosts.adapter(host) is None:
        return True
    return not cycle_hosts.isolation(host, entry['role'])['worktree']


def open_editors(doc, *, task_id=None):
    """The open set: every reserved or running editing attempt that targets the main checkout.

    The one reader for prepare-dispatch and the low-level `assignment --state running` path. It leaves out the
    attempts of the task being reserved: an open attempt of that task already refuses on its own."""
    found = []
    for entry in doc.get('assignments', []):
        if entry['state'] not in OPEN or entry['role'] not in EDITING_ROLES or not entry.get('task') or entry['task'] == task_id:
            continue
        if editing_task(task_entry(doc, entry['task'])) and targets_main_checkout(entry):
            found.append(entry)
    return found


def checkout_refusal(held, role):
    """checkout-has-open-editing-attempt, naming each open attempt with its recoveries."""
    observed = [{'assignment': e['id'], 'attempt': e['attempt'], 'task': e['task'], 'role': e['role']} for e in held]
    recovery = [action({'op': 'inspect'}, [], 'inspect each open attempt and await its result')]
    for entry in held:
        recovery.extend(attempt_routes(entry))
    names = ', '.join(f"{e['role']} attempt {e['id']}/{e['attempt']} on task {e['task']}" for e in held)
    found = failure('checkout-has-open-editing-attempt',
                    f'the main checkout is held by {names}; wait for it to deliver or be marked lost with host evidence. '
                    'Only an invocation that isolates in its own worktree is admitted beside it',
                    field='task_id', expected='no open editing attempt on the main checkout', observed=observed, recovery=recovery)
    if role == 'dev-lead':
        found['note'] = ('Only the open dev-lead may dispatch this unit, as a developer, and only on a host with per-call isolation; '
                         'the commander dispatches no developer.')
    return found


def holds_unit_reservation(doc, task):
    """A Build or fix task a developer reserved in this pass is a unit: only its coordinating dev-lead redispatches it."""
    return editing_task(task) and bool(reservations(doc, task['id'], 'developer'))


def redispatch_role(doc, task, role):
    """The role an inspect handler offers for a task: dev-lead for an editing task, none for a unit, else the given role.

    Never a developer: inspect offers the commander no developer dispatch, so a developer-reserved task of any
    phase stays an agent offer for its coordinating dev-lead."""
    if not editing_task(task):
        return None if role == 'developer' else role
    return None if holds_unit_reservation(doc, task) else 'dev-lead'


# ───────────────────────────── operations ─────────────────────────────

def dispatch_failures(cfg, doc, task, roles):
    """Why a prepare-dispatch for this task would refuse on the task's own facts; empty when it would not.

    The one eligibility function: prepare-dispatch calls it with the request's role and inspect calls it with
    every role that already holds a reservation, so inspect never offers a dispatch the writer refuses.
    """
    errors = []
    if task['phase'] != doc['phase']:
        errors.append(failure('task-not-current-phase', f"task {task['id']} belongs to {task['phase']}; the cycle is in {doc['phase']}",
                              field='task_id', expected=doc['phase'], observed=task['phase']))
    if task['status'] not in ('pending', 'blocked'):
        errors.append(failure('task-not-eligible', f"task {task['id']} is {task['status']}", field='task_id',
                              expected=['pending', 'blocked'], observed=task['status']))
    waiting = [d for d in task['depends_on'] if not dependency_satisfied(doc, d)]
    if waiting:
        errors.append(failure('dependencies-incomplete', 'dependencies are not done: ' + ', '.join(waiting), field='task_id', observed=waiting))
    holder = next((e for e in doc.get('assignments', []) if e['task'] == task['id'] and e['state'] in OPEN), None)
    if holder:
        errors.append(failure('unresolved-dispatch', f"attempt {holder['id']}/{holder['attempt']} ({holder['state']}) holds task {task['id']}",
                              field='task_id', expected='no reserved or running attempt', observed=f"{holder['id']}/{holder['attempt']}",
                              recovery=[action({'op': 'inspect'}, [], 'inspect the open attempt and follow the recovery it returns'),
                                        *attempt_routes(holder)]))
    for problem in adr_dependency_problems(cfg, doc, task):
        errors.append(failure(problem['code'], problem['problem'], field='adr_dependencies',
                              expected='an accepted ADR decision recorded in this cycle',
                              observed={'name': problem['name'], 'status': problem['status']},
                              recovery=[action({'op': 'inspect'}, [], 'inspect the cycle decisions; the task waits for the ADR acceptance')]))
    # The dev-lead half of the checkout guard. A dev-lead never isolates, so it needs no host; a request that names no
    # role selects the dev-lead for a Build or fix task.
    if editing_task(task) and (not roles or 'dev-lead' in roles):
        if holds_unit_reservation(doc, task):
            errors.append(failure('unit-task-needs-coordinator',
                                  f"task {task['id']} holds a developer reservation in pass {doc['pass']}, so it is a unit; "
                                  'only its coordinating dev-lead redispatches it, as a developer',
                                  field='role', expected='developer, dispatched by the coordinating dev-lead', observed='dev-lead',
                                  recovery=[action({'op': 'inspect'}, [], 'inspect the coordinating task and dispatch it instead')]))
        if (held := open_editors(doc, task_id=task['id'])):
            errors.append(checkout_refusal(held, 'dev-lead'))
    for role in roles:
        if len(reservations(doc, task['id'], role)) >= ATTEMPT_LIMIT:
            errors.append(failure('attempt-limit', f'task {task["id"]} has had {ATTEMPT_LIMIT} {role} attempts in pass {doc["pass"]}',
                                  field='task_id', expected=f'fewer than {ATTEMPT_LIMIT} attempts per task and role in a pass',
                                  observed=len(reservations(doc, task['id'], role)),
                                  recovery=attempt_limit_recovery(cfg, doc)))
            break
    return errors


def attempt_limit_recovery(cfg, doc):
    """A counted return requires Verify/Review and a remaining pass; no handler grants one."""
    routes = []
    if doc['phase'] in (*CHECK_PHASES, 'review') and doc['pass'] < doc['pass_limit'] and not listed(doc):
        routes.append(lowlevel(cfg, ['return', doc['id']], 'start a new pass through a counted return',
                               ['--improved', '--unresolved', '--next-change', '--justification', '--progress']))
    routes.append(lowlevel(cfg, ['pause', doc['id']], 'pause the cycle as an escalation stop', ['--reason']))
    return routes


def dispatch_validation(cfg, doc, request, role):
    """Check dispatch facts without allocating a result directory, reserving or classifying."""
    errors = []
    if (problem := stale_cycle(doc, allow_paused=False)):
        errors.append(problem)
    task = task_entry(doc, request['task_id'])
    host = request['host']
    if task is None:
        errors.append(failure('unknown-task', f"task {request['task_id']} is not in the plan", field='task_id', observed=request['task_id'],
                              expected=[t['id'] for t in doc['plan']['tasks']]))
    else:
        errors.extend(dispatch_failures(cfg, doc, task, [role] if role else []))
    mode = request.get('mode')
    if cycle_hosts.adapter(host) is None:
        errors.append(failure('unknown-host', f'no adapter for host {host}', field='host', expected=sorted(cycle_hosts.ADAPTERS), observed=host))
    elif (role == 'developer' and editing_task(task) and not cycle_hosts.isolation(host, role)['worktree']
            and (held := open_editors(doc, task_id=task['id']))):
        # The developer half of the checkout guard: it needs the host, because only a host with per-call isolation
        # gives a developer its own worktree.
        errors.append(checkout_refusal(held, role))
    elif mode is not None and mode not in cycle_hosts.modes(host):
        errors.append(failure('unknown-mode', f'the {host} adapter offers no dispatch mode {mode}', field='mode',
                              expected=list(cycle_hosts.modes(host)), observed=mode))
    if role is not None:
        try:
            cycle_hosts.role_boundary(role)
        except (OSError, ValueError) as exc:
            errors.append(failure('role-contract-unavailable', str(exc), field='role', expected='a readable canonical role boundary', observed=role))
        try:
            capabilities = cycle_hosts.capability_status(role, request.get('capabilities'),
                                                        continuation=bool(request.get('release_continuation')))
            if capabilities['missing']:
                errors.append(failure('role-capability-unavailable', 'known host capability gap: ' + ', '.join(capabilities['missing']),
                                      field='capabilities', observed=capabilities))
        except ValueError as exc:
            errors.append(failure('capability-evidence-invalid', str(exc), field='capabilities'))
    explicit = request.get('result_path')
    if explicit is not None:
        path = Path(explicit)
        if not path.is_absolute():
            errors.append(failure('result-path-not-absolute', 'result_path must be absolute', field='result_path', expected='an absolute path', observed=explicit))
        elif path.is_symlink():
            errors.append(failure('result-path-symlink', 'result_path is a symlink', field='result_path', observed=explicit))
        elif path.is_dir():
            errors.append(failure('result-path-is-directory', 'result_path names a directory; give the result file path', field='result_path', observed=explicit))
    ident = request.get('assignment')
    entry = assignment_entry(doc, ident) if ident else None
    if entry is not None and task is not None and entry['task'] != task['id']:
        errors.append(failure('assignment-task-mismatch', f"assignment {ident} belongs to task {entry['task']}", field='assignment',
                              expected=task['id'], observed=entry['task']))
    base = task_base(cfg, doc, task['id']) if task else None
    if task is not None and base is None:
        errors.append(failure('no-head', 'the repository has no HEAD commit to record as the task base', field=None))
    if errors:
        raise Refused(errors)
    return task, entry, base


def prepare_dispatch(cfg, doc, request, *, resolved_role=None, context=None, continuation=None):
    role = resolved_role or request.get('role')
    task, entry, base = dispatch_validation(cfg, doc, request, role)
    initial_spec = continuation if continuation is not None else cycle_hosts.continuation_spec(cfg, doc, request, role)
    host, mode, ident = request['host'], request.get('mode'), request.get('assignment')
    staged = cycle_dispatch.staged(cfg, doc, request)
    if staged:
        snapshot, bundle = staged
        fresh = deepcopy(bundle['entry'])
        cycle_dispatch.check_current(cfg, doc, fresh, bundle)
        ident, attempt = fresh['id'], fresh['attempt']
        existing = assignment_entry(doc, ident)
        retry = existing is not None and (existing['state'] == 'lost' or
                (existing['state'] == 'finished' and (existing.get('delivery') or {}).get('outcome') in ('failed', 'blocked')))
        if existing is not None and (not retry or attempt != existing['attempt'] + 1):
            raise cycle_dispatch.SnapshotError('invocation-staged-attempt-conflict')
        fresh['invocation_snapshot'] = snapshot
        execution, _ = cycle_execution.retain(cfg, doc, fresh, cycle_execution.prove(cfg, doc, fresh))
        fields = {'task': task['id'], 'assignment': ident, 'attempt': attempt, 'role': fresh['role'],
                  'host': fresh['host'], 'mode': fresh['mode'], 'base': fresh['base'], 'invocation_snapshot': snapshot}
        if existing is not None:
            fields['previous'] = deepcopy(existing)
            existing.clear(); existing.update(fresh)
        else:
            doc.setdefault('assignments', []).append(fresh)
        task.update(status='active', assignee=ident, result_path=fresh['result_path'])
        ensure_directory(Path(fresh['result_path']).parent)
        return {'assignment': ident, 'attempt': attempt, 'task': task['id'], 'result_path': fresh['result_path'],
                'base': fresh['base'], 'delivery_token': fresh['delivery_token'], 'invocation_snapshot': snapshot,
                'execution': execution, 'invocation': deepcopy(bundle['invocation']),
                'local_skills': cycle_dispatch.local_skills(bundle)}, fields
    explicit = request.get('result_path')
    # Choose the assignment and attempt.
    retry = entry is not None and (entry['state'] == 'lost' or (entry['state'] == 'finished' and (entry.get('delivery') or {}).get('outcome') in ('failed', 'blocked')))
    if entry is not None and not retry:
        entry, ident = None, None  # the current attempt finished done: a new assignment
    if ident is None or (entry is None and assignment_entry(doc, ident)):
        ident = fresh_id(doc, task['id'])
    attempt = entry['attempt'] + 1 if entry else 1
    if explicit is None:
        directory = results_directory(doc)
        result_path = str(directory / f'{ident}-attempt-{attempt}.md')
    else:
        result_path = explicit
    at = now()
    fresh = {'id': ident, 'role': role, 'task': task['id'], 'agent': None, 'result_path': result_path, 'state': 'reserved',
             'attempt': attempt, 'started_at': at, 'last_seen': at, 'ended_at': None, 'note': None,
             'host': host, 'mode': cycle_hosts.mode_of(host, mode).name, 'base': base, 'delivery': None,
             'delivery_token': uuid.uuid4().hex}
    spec = initial_spec
    if spec is not None:
        fresh['release_continuation'] = deepcopy(spec)
    bundle, objects = build_invocation(cfg, doc, request, fresh, context)
    execution = cycle_execution.prove(cfg, doc, fresh)
    snapshot = cycle_dispatch.persist(cfg, doc, request, bundle, objects)
    cycle_dispatch.check_current(cfg, doc, fresh, bundle)
    execution, _ = cycle_execution.retain(cfg, doc, fresh, execution)
    fresh['invocation_snapshot'] = snapshot
    fields = {'task': task['id'], 'assignment': ident, 'attempt': attempt, 'role': role, 'host': host, 'mode': fresh['mode'], 'base': base}
    fields['invocation_snapshot'] = snapshot
    if entry:
        fields['previous'] = deepcopy(entry)
        entry.clear(); entry.update(fresh)
    else:
        doc.setdefault('assignments', []).append(fresh)
        entry = fresh
    task['status'] = 'active'
    task['assignee'] = ident
    task['result_path'] = result_path
    result = {'assignment': ident, 'attempt': attempt, 'task': task['id'], 'result_path': result_path, 'base': base,
              'delivery_token': fresh['delivery_token'],
              'invocation_snapshot': snapshot, 'execution': execution, 'invocation': bundle['invocation'],
              'optional_context': {'selected': [item['id'] for item in (context or {}).get('selected', [])],
                                   'retrievable': (context or {}).get('retrievable', [])},
              'local_skills': cycle_dispatch.local_skills(bundle)}
    result['capability_status'] = cycle_hosts.capability_status(role, request.get('capabilities'), continuation=spec is not None)
    return result, fields


def fresh_id(doc, task_id):
    used = {e['id'] for e in doc.get('assignments', [])}
    if task_id not in used and ASSIGNMENT_ID.fullmatch(task_id):
        return task_id
    stem = re.sub(r'[^A-Za-z0-9._-]', '-', task_id)[:56] or 'task'
    n = 2
    while f'{stem}-{n}' in used:
        n += 1
    return f'{stem}-{n}'


def results_directory(doc):
    """The cycle's engine-allocated result directory; a vanished one is replaced by a new allocation."""
    recorded = doc.get('results_dir')
    if recorded and Path(recorded).is_dir() and not Path(recorded).is_symlink():
        return Path(recorded)
    # Bind new directories canonically: macOS may spell its temporary directory
    # through /var, which the reader's no-follow policy deliberately refuses.
    created = Path(tempfile.mkdtemp(prefix=f"crux-results-{doc['id']}-")).resolve()
    doc['results_dir'] = str(created)
    return created


def attempt_errors(doc, request, states):
    """Errors for a request that names an assignment attempt; empty when the attempt is current and in `states`."""
    entry = assignment_entry(doc, request['assignment'])
    if entry is None:
        return entry, [failure('unknown-assignment', f"no assignment {request['assignment']}", field='assignment', observed=request['assignment'])]
    if request['attempt'] != entry['attempt']:
        return entry, [failure('superseded-attempt', f"attempt {request['attempt']} is not current; the current attempt is {entry['attempt']}",
                               field='attempt', expected=entry['attempt'], observed=request['attempt'],
                               recovery=[action({'op': 'inspect'}, [], 'inspect the current attempt')])]
    if entry['state'] not in states:
        return entry, [failure('attempt-not-open', f"attempt {entry['id']}/{entry['attempt']} is {entry['state']}",
                               field='attempt', expected=list(states), observed=entry['state'])]
    return entry, []


def attach_execution(cfg, doc, request):
    errors = []
    if (problem := stale_cycle(doc, allow_paused=True)):
        errors.append(problem)
    entry, found = attempt_errors(doc, request, OPEN)
    errors += found
    if not found and entry['state'] == 'running':
        if entry['agent'] == request['handle']:
            if errors:
                raise Refused(errors)
            return {'changed': False, 'assignment': entry['id'], 'attempt': entry['attempt'], 'handle': entry['agent']}, {}
        errors.append(failure('handle-conflict', f"attempt {entry['id']}/{entry['attempt']} is bound to another handle",
                              field='handle', expected=entry['agent'], observed=request['handle']))
    if errors:
        raise Refused(errors)
    entry.update({'state': 'running', 'agent': request['handle'], 'last_seen': now()})
    result = {'assignment': entry['id'], 'attempt': entry['attempt'], 'task': entry['task'], 'handle': entry['agent']}
    result.update(observe_execution(cfg, doc, entry))
    return result, {'task': entry['task'], 'assignment': entry['id'], 'attempt': entry['attempt'], 'handle': entry['agent']}


def observe_execution(cfg, doc, entry, *, delivery_commits=()):
    """Observation cannot erase a real host handle or change delivery semantics."""
    try:
        proof = cycle_execution.prove(cfg, doc, entry, requested=(entry.get('execution') or {}).get('checkout'),
                                      delivery_commits=delivery_commits)
        execution, _ = cycle_execution.retain(cfg, doc, entry, proof)
        return {'execution': execution}
    except cycle_execution.ExecutionError as exc:
        code, details = exc.code, exc.details
    except Exception as exc:
        # Optional proof infrastructure must not discard an already observed host or delivery fact.
        code, details = 'execution-proof-unavailable', {'cause': type(exc).__name__}
    return {'execution_observation': {'ok': False, 'code': code, 'details': details,
                                     'note': 'No current checkout proof; use execution-check or normal isolated integration. Host/delivery facts remain recorded.'}}


def execution_check_proof(cfg, doc, request):
    """Fresh checks and replays share the current attempt and clean-start guards."""
    if (problem := stale_cycle(doc, allow_paused=False)):
        raise Refused([problem])
    entry, errors = attempt_errors(doc, request, OPEN)
    if errors:
        raise Refused(errors)
    edited = request.get('edited_paths', [])
    started = entry.get('execution_started')
    try:
        root = cycle_execution.checkout(cfg, request.get('checkout'))
        expected = {'delivery_token': entry.get('delivery_token'), 'checkout': str(root)}
        if started != expected:
            sealed = cycle_execution.resume_start(cfg, doc, entry, root) if entry.get('resume_seal') else None
            if sealed is not None:
                if edited and set(edited) != set(sealed):
                    raise cycle_execution.ExecutionError('execution-resume-paths-changed')
                edited = sealed
            elif edited:
                raise cycle_execution.ExecutionError('execution-clean-start-required')
        proof = cycle_execution.prove(cfg, doc, entry, requested=str(root), edited_paths=edited)
    except cycle_execution.ExecutionError:
        raise
    except Exception as exc:
        raise cycle_execution.ExecutionError('execution-proof-unavailable', cause=type(exc).__name__) from None
    return entry, proof, expected


def execution_check(cfg, doc, request):
    entry, proof, expected = execution_check_proof(cfg, doc, request)
    observed_head = proof['execution_head']
    proof = stable_execution_proof(cfg, doc, entry, proof)
    try:
        execution, changed = cycle_execution.retain(cfg, doc, entry, proof)
    except cycle_execution.ExecutionError:
        raise
    except Exception as exc:
        raise cycle_execution.ExecutionError('execution-proof-unavailable', cause=type(exc).__name__) from None
    if entry.get('execution_started') != expected:
        entry['execution_started'] = expected
        changed = True
    if entry.pop('resume_seal', None) is not None:
        changed = True
    result = {'changed': changed, 'assignment': entry['id'], 'attempt': entry['attempt'], 'task': entry['task'], 'execution': execution,
              'execution_observation': {'current_head': observed_head, 'retained_proof_reused': observed_head != proof['execution_head']}}
    return result, {'assignment': entry['id'], 'attempt': entry['attempt'], 'task': entry['task'],
                    'review_base': entry['base'], 'execution_head': execution['execution_head'], 'proof': execution['proof']}


def stable_execution_proof(cfg, doc, entry, fresh):
    """Reuse an exact sealed proof after its own verified writer checkpoint.

    Otherwise self-committing a proof would change HEAD and cause the next identical
    check to commit yet another proof forever. Fresh prove() already checked current
    ancestry, dirty bytes, index identities and each intervening commit.
    """
    previous = entry.get('execution') or {}
    ref = previous.get('proof') or {}
    if ref.get('path') != f'cycles/{doc["id"]}/execution/{ref.get("sha256")}.json':
        return fresh
    try:
        import cycle_context_read as reader
        raw = reader._bounded_bytes(reader.Reference(contained(cfg.docs_root, ref['path']), cfg.repo_root))
        old = json.loads(raw)
    except (reader.ReadRefused, OSError, ValueError):
        return fresh
    if hashlib.sha256(raw).hexdigest() != ref.get('sha256'):
        return fresh
    if (not isinstance(old, dict) or any(old.get(key) != value for key, value in fresh.items()
            if key not in ('execution_head', 'commits')) or set(old) != set(fresh)):
        return fresh
    before, after = old.get('commits', []), fresh['commits']
    if (len(before) <= len(after) and after[:len(before)] == before
            and all(execution_checkpoint_commit(cfg, doc, entry, row, ref)
                    for row in after[len(before):])
            and cycle_execution._ancestor(Path(fresh['checkout']), old['execution_head'], fresh['execution_head'])):
        return old
    return fresh


def execution_checkpoint_commit(cfg, doc, entry, row, ref):
    """Normalize the proof writer's own checkpoint, never arbitrary bookkeeping.

    The committed journal binds this exact proof to the same execution. Commit
    messages confer nothing. Queue writes, notes and other record operations
    still require a fresh proof and invalidate a replay of an older check.
    """
    record = (cfg.docs_root / 'cycles' / doc['id'] / 'cycle.json').relative_to(cfg.repo_root).as_posix()
    proof = (cfg.docs_root / ref['path']).relative_to(cfg.repo_root).as_posix()
    if row.get('kind') != 'bookkeeping' or not row.get('paths') or set(row['paths']) - {record, proof}:
        return False
    try:
        code, raw = cycle_execution.git(Path((entry.get('execution') or {})['checkout']),
                                        'show', row['sha'] + ':' + record, allowed=(0, 128))
        if code or len(raw) > 16 * 1024 * 1024:
            return False
        committed = json.loads(raw)
        operation = committed['operations'][-1]
        result = operation['result']
        return (operation['op'] == 'execution-check' and result.get('assignment') == entry['id']
                and result.get('attempt') == entry['attempt'] and result.get('execution', {}).get('proof') == ref)
    except (KeyError, IndexError, TypeError, ValueError, cycle_execution.ExecutionError):
        return False


def child_link(cfg, doc, request):
    """Attach a delivered bounded child without reopening its active integration task."""
    if (problem := stale_cycle(doc, allow_paused=False)):
        raise Refused([problem])
    parent, errors = attempt_errors(doc, request, ('running',))
    if errors:
        raise Refused(errors)
    task = task_entry(doc, parent['task'])
    child = task_entry(doc, request['child_task'])
    if (parent['role'] != 'dev-lead' or not parent.get('agent') or task['phase'] != 'build'
            or task['status'] != 'active' or child is None or child['phase'] != 'build'
            or child['id'] == task['id'] or child['status'] != 'done'):
        raise Refused([failure('child-integration-ineligible', 'link needs an attached active Build dev-lead and a delivered completed Build child')])
    entries = [entry for entry in doc['assignments'] if entry['task'] == child['id']
               and entry['state'] == 'finished' and (entry.get('delivery') or {}).get('outcome') == 'done']
    if not entries or not child.get('commits'):
        raise Refused([failure('child-integration-unproven', 'child needs its retained successful delivery and committed source')])
    def depends_on(ident, wanted, seen=None):
        seen = set() if seen is None else seen
        if ident in seen:
            return False
        seen.add(ident)
        current = task_entry(doc, ident)
        return wanted in current['depends_on'] or any(depends_on(item, wanted, seen) for item in current['depends_on'])
    if depends_on(child['id'], task['id']):
        raise Refused([failure('dependency-cycle', 'child integration would create a dependency cycle')])
    # Existing completed Build prerequisites supply the already-declared integration
    # base. No status, source scope, marker, review base or host identity changes.
    units = [ident for ident in task['depends_on'] if task_entry(doc, ident)['phase'] == 'build'
             and task_entry(doc, ident)['status'] == 'done']
    integrated = list(dict.fromkeys([*task.get('integrates', []), *units, child['id']]))
    task['depends_on'] = list(dict.fromkeys([*task['depends_on'], child['id']]))
    # A declared integration names at least two completed Build units. A lead's first child,
    # with no completed Build prerequisite, joins as a dependency only; the next link, which
    # then counts it among the completed prerequisites, declares the integration.
    if len(integrated) >= 2:
        task['integrates'] = integrated
    return {'assignment': parent['id'], 'attempt': parent['attempt'], 'task': task['id'],
            'child_task': child['id'], 'integrates': task.get('integrates', [])}, {'task': task['id'], 'child_task': child['id']}


def continuation_delta(cfg, doc, entry):
    """A frozen next-task message for an existing execution, never a spawn offer."""
    bundle = cycle_dispatch.load(cfg, doc, entry['invocation_snapshot'])
    cycle_dispatch.check_current(cfg, doc, entry, bundle)
    if bundle['entry'].get('release_continuation') != entry.get('release_continuation'):
        raise Refused([failure('release-continuation-stale', 'the frozen continuation limits changed')])
    continuation_bindings(cfg, doc, entry)
    spec = entry['release_continuation']
    _, ledger = read_continuation_ledger(cfg, spec, allow_missing=spec['artifact'] is None and entry['task'] == 'prepare')
    logical_steps = {'beta-and-smoke': ['beta', 'smoke'], 'live-check-and-go-ahead': ['smoke']}.get(entry['task'], [entry['task']])
    if any(ledger.get('steps', {}).get(step, {}).get('state') in ('failed', 'interrupted') for step in logical_steps):
        raise Refused([failure('release-step-not-passed', 'the current release command failed or was interrupted; use normal recovery')])
    if spec['artifact'] is not None:
        artifact = ledger.get('artifact')
        identity = {key: artifact.get(key) for key in ('stage_sha256', 'git_tree')} if isinstance(artifact, dict) else None
        publish_step = 'beta-and-smoke' if spec['list'] == 'beta' else 'official'
        published = ledger.get('steps', {}).get('beta' if spec['list'] == 'beta' else 'official') or {}
        if published.get('state') in ('failed', 'interrupted'):
            raise Refused([failure('release-step-not-passed', 'publication failed or was interrupted; use normal recovery')])
        publish_started = (published.get('state', 'pending') != 'pending' or bool(published.get('attempts'))
                           or bool(ledger.get('targets', {}).get(spec['list']))
                           or bool(ledger.get('authorizations', {}).get(spec['list'])))
        # The official command creates its cycle binding. Only a successor with
        # no recorded publication attempt or facts may retain an unbound value.
        unbound_official = spec['list'] == 'official' and entry['task'] == 'official' and not publish_started
        allowed_cycles = (doc['id'], None) if unbound_official else (doc['id'],)
        if (identity != spec['artifact'] or ledger.get('version') != spec['version']
                or ledger.get('cycles', {}).get(spec['list']) not in allowed_cycles):
            raise Refused([failure('release-artifact-changed', 'the pinned release artifact or target changed')])
        if (spec['steps'].index(entry['task']) > spec['steps'].index(publish_step)
                or entry['task'] == publish_step and publish_started):
            continuation_authorization(ledger, spec, identity)
    parameters = bundle['invocation']['parameters']
    return {'action': 'continue-in-same-host', 'assignment': entry['id'], 'attempt': entry['attempt'],
            'task': entry['task'], 'handle': entry['agent'], 'host': entry['host'],
            'delivery_token': entry['delivery_token'], 'result_path': entry['result_path'],
            'base': entry['base'], 'invocation_snapshot': entry['invocation_snapshot'],
            'message': parameters.get('message', parameters.get('prompt')),
            'commands': entry['release_continuation']['commands'][entry['task']]}


def read_continuation_ledger(cfg, spec, *, allow_missing=False):
    """Read canonical release bytes without executing a repository command."""
    import cycle_context_read as reader
    code, common = run_git(cfg, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if code:
        raise Refused([failure('release-ledger-unavailable', 'the canonical release evidence store is unavailable')])
    root = Path(common.strip())
    path = contained(root, 'crux/releases/' + spec['version'] + '/ledger.json')
    try:
        raw = reader._bounded_bytes(reader.Reference(path, root))
        ledger = json.loads(raw)
    except reader.ReadRefused as exc:
        if allow_missing and exc.code == 'object-missing':
            return None, {}
        raise Refused([failure('release-ledger-unavailable', 'read the completed release command result before continuing')]) from None
    except (OSError, ValueError):
        raise Refused([failure('release-ledger-unavailable', 'read the completed release command result before continuing')]) from None
    if not isinstance(ledger, dict):
        raise Refused([failure('release-ledger-unavailable', 'the canonical release ledger is invalid')])
    return raw, ledger


def continuation_authorization(ledger, spec, identity):
    authorization = ledger.get('authorizations', {}).get(spec['list']) or {}
    target = ledger.get('targets', {}).get(spec['list']) or {}
    if (not isinstance(authorization.get('quote'), str) or not authorization['quote'].strip()
            or authorization.get('repo') != spec['target'] or authorization.get('artifact') != identity
            or target.get('repo') != spec['target'] or target.get('tree') != identity['git_tree']):
        raise Refused([failure('release-authorization-unverified', 'the published target lacks its exact artifact-bound owner authorization')])


def continuation_bindings(cfg, doc, entry):
    spec = entry.get('release_continuation')
    if (not spec or entry['role'] != 'dev-lead' or spec['list'] != doc.get('release_list')
            or spec['steps'] != [task['id'] for task in doc['plan']['tasks']]):
        raise Refused([failure('release-continuation-mismatch', 'continuation needs the current fixed list and native role')])
    descriptor = cycle_hosts.release_descriptor(cfg)
    role_sha = hashlib.sha256((cycle_hosts.PLUGIN_ROOT / 'agents' / 'dev-lead.md').read_bytes()).hexdigest()
    if (descriptor is None or descriptor['sha256'] != spec['descriptor']['sha256']
            or descriptor['targets'][spec['list']] != spec['target'] or role_sha != spec['role_sha256']):
        raise Refused([failure('release-continuation-stale', 'the frozen release descriptor or native grant changed; use normal recovery')])


def continuation_ledger(cfg, doc, entry, observation):
    """Read the release writer's canonical ledger and bind a successful logical step."""
    spec, step = entry['release_continuation'], entry['task']
    if step == 'prep':
        return
    raw, ledger = read_continuation_ledger(cfg, spec)
    if hashlib.sha256(raw).hexdigest() != observation.get('ledger_sha256'):
        raise Refused([failure('release-ledger-stale', 'the observed release ledger changed; inspect the actual step result')])
    if ledger.get('version') != spec['version'] or ledger.get('cycles', {}).get(spec['list']) not in (
            doc['id'], *([None] if step == 'live-check-and-go-ahead' else [])):
        raise Refused([failure('release-target-mismatch', 'ledger version/cycle does not match the frozen release target')])
    names = {'beta-and-smoke': ['beta', 'smoke'], 'live-check-and-go-ahead': ['smoke']}.get(step, [step])
    if any(ledger.get('steps', {}).get(name, {}).get('state') != 'passed' for name in names):
        raise Refused([failure('release-step-not-passed', 'the release writer has not recorded this logical step as passed')])
    artifact = ledger.get('artifact')
    if step not in ('prepare',) and (not isinstance(artifact, dict)
            or not artifact.get('stage_sha256') or not artifact.get('git_tree')):
        raise Refused([failure('release-artifact-unverified', 'the release artifact has not been frozen')])
    identity = ({key: artifact[key] for key in ('stage_sha256', 'git_tree')} if isinstance(artifact, dict) else None)
    if spec['artifact'] is not None and identity != spec['artifact']:
        raise Refused([failure('release-artifact-changed', 'the frozen artifact changed; normal recovery and new owner words are required')])
    if identity is not None:
        spec['artifact'] = identity
    if step in ('beta-and-smoke', 'tag', 'official', 'record'):
        continuation_authorization(ledger, spec, identity)


def release_continue(cfg, doc, request):
    """Deliver one fixed step and reserve its successor on the same observed host."""
    if (problem := stale_cycle(doc, allow_paused=False)):
        raise Refused([problem])
    entry, errors = attempt_errors(doc, request, ('running',))
    if errors:
        raise Refused(errors)
    spec = entry.get('release_continuation')
    if (not listed(doc) or entry['role'] != 'dev-lead' or not spec
            or request['delivery_token'] != entry.get('delivery_token')
            or request['handle'] != entry.get('agent') or request['host'] != entry.get('host')
            or request['target'] != doc['release_list'] or spec['list'] != doc['release_list']
            or spec['steps'] != [task['id'] for task in doc['plan']['tasks']]):
        raise Refused([failure('release-continuation-mismatch', 'continuation needs the current frozen list, token, target and same native handle')])
    continuation_bindings(cfg, doc, entry)
    observed = request['step_result']
    if observed['step'] != entry['task']:
        raise Refused([failure('release-step-mismatch', 'the observed command result belongs to another logical step')])
    if request['outcome'] == 'done' and observed['exit_code'] != 0:
        raise Refused([failure('release-step-not-passed', 'a nonzero command result cannot deliver a successful step')])
    if request['outcome'] == 'done' and not request.get('stop'):
        if entry['task'] == 'prep' and not request.get('commits'):
            raise Refused([failure('release-prep-uncommitted', 'prep continuation needs its committed prepared source')])
        continuation_ledger(cfg, doc, entry, observed)
    delivery_request = {'op': 'deliver', 'op_id': request['op_id'],
                        **{key: request[key] for key in ('assignment', 'attempt', 'outcome', 'commits', 'evidence', 'stop') if key in request}}
    result, fields = deliver(cfg, doc, delivery_request)
    result['step_result'] = deepcopy(observed)
    event(doc, 'release-step-delivered', task=entry['task'], assignment=entry['id'], attempt=entry['attempt'],
          command_exit=observed['exit_code'], outcome=request['outcome'])
    if request['outcome'] != 'done' or request.get('stop'):
        return {**result, 'stopped': True}, fields
    index = spec['steps'].index(entry['task'])
    if index + 1 == len(spec['steps']):
        return {**result, 'stopped': False}, fields
    successor = spec['steps'][index + 1]
    next_request = {'op': 'prepare-dispatch', 'op_id': 'continue-next-' + request_digest(request)[:24],
                    'task_id': successor, 'role': 'dev-lead', 'host': entry['host'], 'mode': entry['mode'],
                    'integration_owner': spec['owner'], 'capabilities': spec['capabilities'],
                    'release_continuation': {'version': spec['version']}}
    prepared, _ = prepare_dispatch(cfg, doc, next_request, resolved_role='dev-lead', context={}, continuation=spec)
    following = assignment_entry(doc, prepared['assignment'])
    following.update(state='running', agent=entry['agent'], last_seen=now())
    result.update(next_assignment=following['id'], next_attempt=following['attempt'], next_delivery_token=following['delivery_token'],
                  continuation=continuation_delta(cfg, doc, following), stopped=False)
    return result, {**fields, 'next_task': successor, 'handle': entry['agent']}


def deliver(cfg, doc, request):
    errors = []
    entry = assignment_entry(doc, request['assignment'])
    commits_in, evidence_in = request.get('commits', []), request.get('evidence', [])
    # Repeat equivalence first: an identical delivery of the current attempt is a no-op.
    if entry and request['attempt'] == entry['attempt'] and entry['state'] == 'finished' and entry.get('delivery'):
        return delivery_repeat(cfg, doc, request, entry)
    if (problem := stale_cycle(doc, allow_paused=True)):
        errors.append(problem)
    entry, found = attempt_errors(doc, request, OPEN)
    errors += found
    task = task_entry(doc, entry['task']) if entry and not found else None
    data = None
    if entry and not found:
        source = Path(entry['result_path'])
        if not source.is_absolute():
            source = cfg.repo_root / source
        if source.is_symlink():
            errors.append(failure('result-is-symlink', f'{source} is a symlink; the result must be a regular file', field='result', observed=str(source)))
        elif not source.exists():
            errors.append(failure('result-missing', f'no result at {source}', field='result', expected='a regular file', observed=str(source),
                                  recovery=[action({'op': 'inspect'}, [], 'inspect the attempt; a missing file is no evidence it failed')]))
        elif source.is_dir():
            errors.append(failure('result-is-directory', f'{source} is a directory', field='result', expected='a regular file', observed=str(source)))
        elif not source.is_file():
            errors.append(failure('result-not-regular', f'{source} is not a regular file', field='result', observed=str(source)))
        else:
            try:
                data = source.read_bytes()
            except OSError as exc:
                errors.append(failure('result-unreadable', f'{source} cannot be read: {type(exc).__name__}', field='result', observed=str(source)))
        if data is not None:
            problem = cycle_hosts.result_problem(data.decode('utf-8', errors='replace'), entry['id'], entry['attempt'], entry.get('delivery_token'))
            if problem:
                errors.append(failure(problem[0], problem[1], field='result', observed=str(source)))
    full = []
    for name in commits_in:
        try:
            full.append(resolve_commit(cfg, name))
        except CycleError as exc:
            errors.append(failure('commit-unresolved', str(exc), field='commits', observed=name))
    full = list(dict.fromkeys(full))
    if entry and not found and entry.get('base'):
        for sha in full:
            if not is_ancestor(cfg, entry['base'], sha) and not adopted_for_delivery(cfg, doc, task, sha):
                errors.append(failure('commit-not-from-base', f'commit {sha[:12]} does not descend from the task base {entry["base"][:12]}',
                                      field='commits', expected=entry['base'], observed=sha,
                                      recovery=[action(resubmission(request), [], 'rebase the commit onto the task base, then deliver the rebased commit'),
                                                attempt_routes(entry)[1]]))
        if request['outcome'] == 'done':
            # Only a done delivery closes the task, so only it must cover the task's trailer-tagged commits.
            for sha in trailer_commits(cfg, entry['base'], entry['task']):
                if not any(sha == c or is_ancestor(cfg, sha, c) for c in full):
                    errors.append(failure('undelivered-task-commit', f'commit {sha[:12]} carries Cycle-Task: {entry["task"]} but lies outside the delivered range',
                                          field='commits', expected='every trailer-tagged task commit since the base', observed=sha))
    evidence = []
    for item in evidence_in:
        root = cfg.repo_root.resolve()
        path = Path(item)
        cls = ('outside-repository', 'is not a repository-relative path') if path.is_absolute() or '..' in path.parts else path_class(root / path, root)
        if cls is None and not (root / path).resolve().is_relative_to(cfg.docs_root.resolve()):
            cls = ('outside-docs', 'lies outside the docs tree, where task evidence is recorded')
        if cls:
            errors.append(failure(f'evidence-{cls[0]}', f'evidence {item} {cls[1]}', field='evidence', expected='a regular file inside the docs tree', observed=item,
                                  recovery=[action(resubmission(request), [],
                                                   'deliver reads evidence from the main checkout only; evidence produced on an unintegrated branch '
                                                   'must be integrated there before deliver, then submit this delivery again')]))
        else:
            evidence.append((root / path).resolve().relative_to(cfg.docs_root.resolve()).as_posix())
    outcome = request['outcome']
    updated = None
    if outcome == 'done' and task is not None:
        # Validate the task update before any write, and report its failure with the other input errors.
        # An unresolved commit is already an error; the check still runs on the commits that resolved.
        try:
            updated = updated_task(cfg, doc, task, {'state': 'done', 'commits': full, 'evidence': evidence,
                                                    'stage': request.get('stage'), 'note': request.get('note')})
        except CycleError as exc:
            errors.append(failure('task-refused', str(exc), field='outcome', observed=outcome))
    if errors:
        raise Refused(errors)
    execution_observation = observe_execution(cfg, doc, entry, delivery_commits=full)
    # Retain the result once; a retry before the save overwrites the same copy.
    retained = f"cycles/{doc['id']}/results/{entry['id']}-attempt-{entry['attempt']}.md"
    atomic_bytes(contained(cfg.docs_root, retained), data)
    sha = hashlib.sha256(data).hexdigest()
    delivery = {'path': retained, 'sha256': sha, 'outcome': outcome, 'commits': full, 'evidence': evidence,
                'stage': request.get('stage'), 'note': request.get('note')}
    if request.get('stop'):
        # The stop a blocked delivery names stays in the record, so inspect can tell a stop from a failure.
        delivery['stop'] = request['stop']
    if outcome == 'done':
        task.clear(); task.update(updated)
    else:
        task['status'] = 'blocked' if outcome == 'blocked' else 'pending'
    at = now()
    entry.update({'state': 'finished', 'ended_at': at, 'last_seen': at, 'delivery': delivery})
    untrailered = [c for c in full if not carries_trailer(cfg, c, entry['task'])]
    result = {'assignment': entry['id'], 'attempt': entry['attempt'], 'task': task['id'], 'outcome': outcome,
              'retained': retained, 'sha256': sha, 'result_path': entry['result_path'], 'status': task['status'],
              'untrailered_commits': untrailered}
    result.update(execution_observation)
    return result, {'task': task['id'], 'assignment': entry['id'], 'attempt': entry['attempt'], 'outcome': outcome, 'sha256': sha}


def adopted_for_delivery(cfg, doc, task, sha):
    """Only an explicitly recorded adoption waives the task-base comparison for that exact commit."""
    from cycle_workflow import adoption_source
    recorded = next((row for row in (task or {}).get('adopted_commits', []) if row['sha'] == sha), None)
    if recorded is None:
        return False
    try:
        return adoption_source(cfg, doc, sha) == recorded
    except CycleError:
        return False


def delivery_repeat(cfg, doc, request, entry):
    recorded = entry['delivery']
    try:
        source = Path(entry['result_path'])
        data = source.read_bytes() if source.is_file() and not source.is_symlink() else contained(cfg.docs_root, recorded['path']).read_bytes()
    except (OSError, CycleError):
        data = b''
    commits = []
    for name in request.get('commits', []):
        try:
            commits.append(resolve_commit(cfg, name))
        except CycleError:
            commits.append(name)
    proposed = {'outcome': request['outcome'], 'commits': list(dict.fromkeys(commits)),
                'evidence': [str(Path(e)) for e in request.get('evidence', [])], 'stage': request.get('stage'),
                'note': request.get('note'), 'stop': request.get('stop'), 'sha256': hashlib.sha256(data).hexdigest()}
    root = cfg.repo_root.resolve()
    proposed['evidence'] = [((root / e).resolve().relative_to(cfg.docs_root.resolve()).as_posix()
                             if (root / e).resolve().is_relative_to(cfg.docs_root.resolve()) else e) for e in proposed['evidence']]
    differing = [k for k, v in proposed.items() if recorded.get(k) != v]
    if not differing:
        return {'changed': False, 'assignment': entry['id'], 'attempt': entry['attempt'], 'task': entry['task'],
                'outcome': recorded['outcome'], 'retained': recorded['path'], 'sha256': recorded['sha256']}, {}
    raise Refused([failure('delivery-conflict', 'this attempt is already delivered; deliveries are immutable. Differs: ' + ', '.join(differing),
                           field=differing[0], expected={k: recorded.get(k) for k in differing}, observed={k: proposed[k] for k in differing},
                           recovery=conflict_recovery(cfg, doc, entry))])


def conflict_recovery(cfg, doc, entry, role=None):
    task = task_entry(doc, entry['task'])
    dispatch = action({'op': 'prepare-dispatch', 'task_id': task['id'], 'role': role or entry['role'], 'host': entry['host']},
                      [], 'dispatch a new assignment for the changed work')
    if task['status'] in ('pending', 'blocked'):
        return [dispatch]
    reopen = lowlevel(cfg, ['task', doc['id'], '--task-id', task['id'], '--state', 'pending'], 'reopen the done task')
    if task['phase'] == doc['phase']:
        return [reopen, dispatch]
    if doc['phase'] in (*CHECK_PHASES, 'review') and doc['pass'] < doc['pass_limit'] and not listed(doc):
        return [lowlevel(cfg, ['return', doc['id']], 'return to Build in a new pass',
                         ['--improved', '--unresolved', '--next-change', '--justification', '--progress']), reopen, dispatch]
    return [lowlevel(cfg, ['pause', doc['id']], 'pause: the current phase or pass limit allows no return', ['--reason']),
            action({'op': 'owner-exception'}, ['quote', 'conversation', 'date'], "close on the owner's own instruction")]


def stale_revision(doc, request, purpose):
    """The stale-revision refusal; its one recovery is inspect, never a request carrying the new revision."""
    newer = [e['action'] for e in doc['history'] if e.get('revision', 0) > request['expect_revision']]
    return failure('stale-revision', f"the record moved to revision {doc['revision']}; newer actions: {', '.join(newer) or 'none'}",
                   field='expect_revision', expected=doc['revision'], observed=request['expect_revision'],
                   recovery=[action({'op': 'inspect'}, [], f'inspect the current state before {purpose}')])


def resubmission(request):
    """The request again, for a new op_id; the caller_fills of the action that carries it are empty."""
    return {key: value for key, value in request.items() if key != 'op_id'}


def attempt_routes(entry):
    """The two typed routes that release a task held by an open attempt: deliver and mark-lost."""
    ident = {'assignment': entry['id'], 'attempt': entry['attempt']}
    return [action({'op': 'deliver', **ident}, ['outcome'], 'record the result when it has arrived; add commits, evidence, stage and note as the report states'),
            action({'op': 'mark-lost', **ident}, ['evidence', 'note'],
                   'record the attempt lost only with affirmative host evidence that the execution ended or never started '
                   f'(kinds: {", ".join(cycle_hosts.EVIDENCE_KINDS)}); elapsed time and wait or status errors are never evidence')]


def result_file(cfg, entry):
    path = Path(entry['result_path']) if entry.get('result_path') else None
    return cfg.repo_root / path if path and not path.is_absolute() else path


def result_complete(cfg, entry):
    """Whether a regular, complete result is at the attempt's recorded path."""
    path = result_file(cfg, entry)
    if not path or path.is_symlink() or not path.is_file():
        return False
    try:
        return cycle_hosts.result_problem(path.read_text(errors='replace'), entry['id'], entry['attempt'], entry.get('delivery_token')) is None
    except OSError:
        return False


def mark_lost(cfg, doc, request):
    """Record an undelivered attempt lost on affirmative host evidence; the task returns to pending.

    An attempt that is already lost answers with a no-write success that names its state."""
    errors = []
    if (problem := stale_cycle(doc, allow_paused=True)):
        errors.append(problem)
    entry, found = attempt_errors(doc, request, (*OPEN, 'lost'))
    if entry and not found and entry['state'] == 'lost':
        if errors:
            raise Refused(errors)
        return {'changed': False, 'assignment': entry['id'], 'attempt': entry['attempt'], 'task': entry['task'],
                'attempt_state': 'lost', 'ended_at': entry['ended_at'], 'note': entry['note']}, {}
    errors += found
    if entry and not found:
        evidence = request['evidence']
        if not entry.get('host'):
            errors.append(failure('attempt-without-host', f"attempt {entry['id']}/{entry['attempt']} has no recorded host, so the engine cannot judge the evidence",
                                  field='assignment', observed=entry['id'],
                                  recovery=[lowlevel(cfg, ['assignment', doc['id'], '--id', entry['id'], '--state', 'lost'],
                                                     'record the low-level attempt lost, quoting the host evidence', ['--note'])]))
        elif cycle_hosts.adapter(entry['host']) is None:
            errors.append(failure('unknown-host', f"no adapter for host {entry['host']}", field='assignment', observed=entry['host']))
        elif (refusal := cycle_hosts.loss_evidence(entry['host'], mode=entry.get('mode'), state=entry['state'], kind=evidence['kind'], detail=evidence['detail'],
                                                     result_complete=result_complete(cfg, entry))):
            code, problem = refusal
            recovery = (attempt_routes(entry)[:1] if code == 'result-arrived'
                        else [action({'op': 'inspect'}, [], 'inspect the attempt; elapsed time and errors do not show it ended')])
            errors.append(failure(code, problem, field='evidence', expected=list(cycle_hosts.EVIDENCE_KINDS), observed=evidence, recovery=recovery))
    if errors:
        raise Refused(errors)
    at = now()
    task = task_entry(doc, entry['task'])
    entry.update({'state': 'lost', 'ended_at': at, 'last_seen': at, 'note': request['note']})
    task['status'] = 'pending'
    result = {'assignment': entry['id'], 'attempt': entry['attempt'], 'task': task['id'], 'status': 'pending'}
    return result, {'task': task['id'], 'assignment': entry['id'], 'attempt': entry['attempt'],
                    'evidence_kind': request['evidence']['kind'], 'evidence_detail': request['evidence']['detail']}


def finish(cfg, doc, request):
    errors = []
    if (problem := stale_cycle(doc, allow_paused=False)):
        errors.append(problem)
    release = listed(doc)
    if not release and doc['phase'] != 'reflect':
        errors.append(failure('wrong-phase', f"finish runs in Reflect; the cycle is in {doc['phase']}", field=None, expected='reflect', observed=doc['phase']))
    if request['expect_revision'] != doc['revision']:
        errors.append(stale_revision(doc, request, 'finishing'))
    if not release:
        # Only a release cycle closes without a reflection; any other cycle needs the lessons and what remains.
        for name in ('lessons', 'remaining'):
            if name not in request:
                errors.append(failure('reflection-missing', f'finish needs {name} from the delegator; a release cycle needs neither',
                                      field=name, expected='a non-empty list of strings', observed=None,
                                      recovery=[action({'op': 'finish', 'expect_revision': doc['revision']}, ['lessons', 'remaining'],
                                                       'finish with the lessons and what remains')]))
    candidate, found = completion_candidate(cfg, doc, lessons=request.get('lessons'), remaining=request.get('remaining'), tip=request.get('tip'))
    errors += found
    if not found and (release or doc['phase'] == 'reflect'):
        for item in requirements(cfg, candidate, 'completion'):
            errors.append(failure('requirement-unmet', item['problem'], field=item['requirement'],
                                  recovery=[action({'op': 'inspect'}, [], 'inspect the unmet requirements and the actions that meet them')]))
    if errors:
        raise Refused(errors)
    if not release:
        doc['reflection'] = candidate['reflection']
    doc['completion'] = candidate['completion']
    runs = cycle_summary.test_runs(cfg.repo_root, doc, time.time())
    if runs is not None:
        doc['completion']['test_runs'] = runs
    doc['status'] = 'completed'
    tip = doc['completion']['commits'][-1]
    completion = {'tip': tip, 'commits': doc['completion']['commits'],
                  'classifications': cycle_questions.rows(doc), 'test_runs': runs}
    result = {'status': 'completed', 'completion': completion}
    if not release:
        # ADR-0168: the reflection of a cycle other than a listed release cycle reports its evidence's committed size.
        result['evidence_size'] = evidence_size(cfg, doc, git_head(cfg) or tip)
    return result, {'tip': tip}


EVIDENCE_SIZE_MEASURE = 'sum of blob sizes from git ls-tree -r -l at the completion HEAD over {path}'


def evidence_size(cfg, doc, commit):
    """The committed size of the cycle directory at `commit`: {bytes, files, measure}.

    `finish` passes the checkout HEAD at completion, which includes the record commits made after the
    last task commit. The measure is the sum of blob sizes `git ls-tree -r -l` reports at that commit over
    `<docs_dir>/cycles/<id>/`. Bytes the finish itself writes are not yet committed and are not counted."""
    relative = (cfg.docs_root / 'cycles' / doc['id']).relative_to(cfg.repo_root).as_posix() + '/'
    code, out = run_git(cfg, 'ls-tree', '-r', '-l', '--full-tree', commit, '--', relative)
    total = files = 0
    if code == 0:
        for line in out.splitlines():
            meta, _, _path = line.partition('\t')
            fields = meta.split()
            if len(fields) == 4 and fields[1] == 'blob' and fields[3].isdigit():
                total += int(fields[3])
                files += 1
    return {'bytes': total, 'files': files, 'measure': EVIDENCE_SIZE_MEASURE.format(path=relative)}


# ───────────────────────────── advance and evidence reuse ─────────────────────────────

def phase_checks(doc):
    """The check ids the current phase requires."""
    if doc['phase'] == 'build':
        return list(doc.get('build_checks', []))
    if doc['phase'] in (*CHECK_PHASES, 'review', 'reflect'):
        return list(doc['required_checks'])
    return []


def missing_checks(cfg, doc):
    """Required checks with no current-pass evidence ref, or whose latest ref no longer validates."""
    from test_evidence import validate_evidence
    missing = []
    for check in phase_checks(doc):
        refs = [r for r in doc['evidence'] if r['check_id'] == check and r['pass'] == doc['pass']]
        if not refs:
            missing.append(check)
            continue
        try:
            validate_evidence(cfg.repo_root, refs[-1]['evidence_id'], check_id=check)
        except ValueError:
            missing.append(check)
    return missing


def check_declaration(cfg, check):
    """The declaration a lookup for `check` uses: the registered one, else the newest receipt's own.

    The store cannot be searched by check id without a declaration, so an unregistered check
    reuses the declaration its newest version-2 receipt recorded."""
    from test_evidence import receipts_for, registered_declaration, storage
    try:
        registered = registered_declaration(cfg.repo_root, check)
    except Exception:
        registered = None
    if registered is not None:
        return registered
    # Only this check's receipts are parsed; the scoped read finds the same ones a whole-store read finds.
    receipts = [r for r in receipts_for(storage(cfg.repo_root), {check}) if r['schema_version'] == 2]
    receipts.sort(key=lambda r: (r['finished_at'], r['started_at']), reverse=True)
    return receipts[0]['declaration'] if receipts else None


def reusable_receipts(cfg, doc):
    """{check_id: {check_id, evidence_id}} for each missing check that has a passing receipt on the current inputs."""
    from test_evidence import lookup
    found = {}
    for check in missing_checks(cfg, doc):
        try:
            declaration = check_declaration(cfg, check)
            # A finder: advance validates each chosen receipt again under the lock with a full lookup.
            result = lookup(cfg.repo_root, declaration, matching_only=True) if declaration else None
        except ValueError:
            continue
        if result and result['state'] == 'passed':
            found[check] = {'check_id': check, 'evidence_id': result['record']['id']}
    return found


def attach_reusable(cfg, doc, chosen):
    """Attach each chosen receipt to `doc` as a reused ref, exactly as the low-level evidence action records one.

    Returns the checks attached. A receipt that no longer validates raises evidence-changed."""
    from test_evidence import digest as evidence_digest, normalize, validate_evidence
    attached = []
    for check in missing_checks(cfg, doc):
        item = (chosen or {}).get(check)
        if item is None:
            continue
        try:
            record = validate_evidence(cfg.repo_root, item['evidence_id'], check_id=check)
        except ValueError as exc:
            raise Refused([failure('evidence-changed', f'the receipt found for {check} no longer validates: {exc}', field=check,
                                   expected=item['evidence_id'], observed=str(exc),
                                   recovery=[action({'op': 'inspect'}, [], 'inspect the current evidence and the actions that meet it')])])
        doc['evidence'].append({'check_id': check, 'evidence_id': item['evidence_id'], 'pass': doc['pass'], 'use': 'reused',
                                'declaration_sha256': evidence_digest(normalize(record['declaration']))})
        attached.append(check)
    return attached


def advance_lookup(repo_root, cycle_id):
    """The receipts a typed advance may attach, found before the cycle lock is taken, in one evidence read."""
    from test_evidence import call_scope
    try:
        doc, cfg = load(repo_root, cycle_id), tree(repo_root)
        if doc['schema_version'] != VERSION or doc['status'] != 'active':
            return {}
        with call_scope():
            return reusable_receipts(cfg, doc)
    except (CycleError, OSError, ValueError):
        return {}


def review_requests_changes(cfg, doc):
    """The latest current-pass review asks for changes."""
    if doc['phase'] != 'review':
        return False
    for ref in reversed(doc['reviews']):
        try:
            report = read_retained(cfg, ref)
        except (CycleError, OSError, ValueError):
            continue
        if report['pass'] == doc['pass']:
            return report['verdict'] != 'approve' or bool(report['blocking'])
    return False


def return_routes(cfg, doc):
    """The low-level return, and pause once the pass limit is spent."""
    routes = [lowlevel(cfg, ['return', doc['id']], 'record the counted return to Build in a new pass',
                       ['--improved', '--unresolved', '--next-change', '--justification', '--progress'])]
    if doc['pass'] >= doc['pass_limit']:
        routes.append(lowlevel(cfg, ['pause', doc['id']], 'pause the cycle: the pass limit is spent', ['--reason']))
    return routes


def declaration_routes(cfg, doc, name):
    """The low-level commands that record what an unmet Verify (Test on records created before the rename) or Review requirement still lacks.

    The caller authors the declaration or report; these routes name only where it goes."""
    if doc['phase'] not in (*CHECK_PHASES, 'review', 'reflect'):
        return []
    if name == 'tests':
        if not doc['required_checks']:
            return [lowlevel(cfg, ['checks', doc['id']], 'declare the required checks; repeat --check for the complete set', ['--check'])]
        try:
            check_coverage(doc)
        except CycleError:
            return [lowlevel(cfg, ['coverage', doc['id']], 'declare the coverage: the affected behavior, one rationale per required check and what is not selected; pass the JSON with --json or --file',
                             ['--json'])]
    elif name == 'reduction' and doc['type'] == 'simplify' and doc['phase'] in CHECK_PHASES:
        return [lowlevel(cfg, ['reduction', doc['id']], 'record the reduction: one change (decrease, unchanged or increase) with before, after and evidence for each of the four areas; pass the JSON with --json or --file',
                         ['--json'])]
    elif name == 'review' and doc['phase'] == 'review' and not review_requests_changes(cfg, doc):
        try:
            check_tests(cfg, doc)
        except CycleError:
            return []
        return [lowlevel(cfg, ['review', doc['id']], "record the independent reviewer's report; pass the JSON with --json or --file", ['--json'])]
    return []


def requirement_error(cfg, doc, item):
    """One refusal per unmet requirement, with a recovery that targets that requirement."""
    name = item['requirement']
    recovery = []
    if name in ('build-checks', 'tests'):
        recovery += declaration_routes(cfg, doc, name)
        for check in missing_checks(cfg, doc):
            recovery.append(lowlevel(cfg, ['evidence', doc['id'], '--check-id', check],
                                     f'run {check}, then attach its passing receipt', ['--evidence-id', '--use']))
    elif name == 'reduction':
        recovery = declaration_routes(cfg, doc, name)
    elif name == 'review' and review_requests_changes(cfg, doc):
        recovery = return_routes(cfg, doc)
    elif name == 'review':
        recovery = declaration_routes(cfg, doc, name)
    elif name == 'completion' and listed(doc):
        recovery = [action({'op': 'finish', 'expect_revision': doc['revision']}, [], 'complete the release cycle')]
    if not recovery:
        recovery = [action({'op': 'inspect'}, [], 'inspect the unmet requirements and the actions that meet them')]
    return failure('requirement-unmet', item['problem'], field=name, recovery=recovery)


def advance(cfg, doc, request, prior=None, *, guard_revision=None):
    errors = []
    if (problem := stale_cycle(doc, allow_paused=False)):
        errors.append(problem)
    if request['expect_revision'] != (doc['revision'] if guard_revision is None else guard_revision):
        errors.append(stale_revision(doc, request, 'advancing'))
    if errors:
        raise Refused(errors)
    if doc['phase'] == 'reflect' and not listed(doc):
        raise Refused([failure('finish-required', 'Reflect ends through finish, which computes the completion record',
                               field='phase', expected='finish', observed='advance',
                               recovery=[action({'op': 'finish', 'expect_revision': doc['revision']}, ['lessons', 'remaining'],
                                                'close the cycle with its recorded commits')])])
    candidate = deepcopy(doc)
    attached = attach_reusable(cfg, candidate, prior)
    unmet = requirements(cfg, candidate, 'next')
    if unmet:
        raise Refused([requirement_error(cfg, candidate, item) for item in unmet])
    doc['evidence'] = candidate['evidence']
    before = doc['phase']
    if listed(doc):
        doc['status'] = 'completed'
    else:
        doc['phase'] = phases_of(doc)[phases_of(doc).index(doc['phase']) + 1]
    result = {'status': doc['status'], 'phase': doc['phase'], 'reused': attached}
    return result, {'from_phase': before, 'to_phase': doc['phase'], 'reused': attached}


def finish_cleanup(cfg, doc):
    """Remove the recorded attempt files in the engine-allocated directory, then the directory if empty."""
    directory = doc.get('results_dir')
    if not directory:
        return
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        return
    for entry in doc.get('assignments', []):
        path = Path(entry['result_path'] or '')
        if entry.get('host') and path.parent == root and path.is_file() and not path.is_symlink():
            try:
                path.unlink()
            except OSError:
                pass
    try:
        root.rmdir()
    except OSError:
        pass


# ───────────────────────────── records: owner-exception and upgrade ─────────────────────────────

def exception_unmet(cfg, doc):
    """The unmet completion list as inspect computes it, including the completion_candidate errors."""
    if listed(doc):
        return requirements(cfg, doc, 'completion')
    candidate, blocking = completion_candidate(cfg, doc)
    return [{'requirement': e['code'], 'problem': e['problem']} for e in blocking] + (
        requirements(cfg, candidate, 'completion') if not blocking else [])


def owner_exception(cfg, doc, request):
    """The exceptional close on the owner's own words.

    It records the quote and conversation verbatim in the history event's `owner` field (the
    shape owner-complete writes), the unmet completion list and every reserved or running
    attempt. It never marks a requirement satisfied and never touches an attempt."""
    if (problem := stale_cycle(doc, allow_paused=True)):
        raise Refused([problem])
    if legacy(doc):
        raise Refused([failure('legacy-release', 'a historical release cycle can only be paused, reflected on and abandoned',
                               field='type', observed='release')])
    refs, problems = check_references(cfg, request.get('references', []))
    if problems:
        without = {k: v for k, v in request.items() if k not in ('op_id', 'references')}
        errors = []
        for item in problems:
            error = failure(item['code'], item['problem'], field='references', expected='repository-relative regular files',
                            observed=item['name'], recovery=[action(without, [], 'close the cycle with the same words and no references')])
            error['candidates'] = item['candidates']
            errors.append(error)
        raise Refused(errors)
    unmet = exception_unmet(cfg, doc)
    open_attempts = [{'id': e['id'], 'attempt': e['attempt'], 'task': e['task'], 'state': e['state'], 'result_path': e['result_path']}
                     for e in doc.get('assignments', []) if e['state'] in OPEN]
    owner = {'origin': 'owner-conversation', 'quote': request['quote'], 'conversation': request['conversation'],
             'date': request['date'], 'authority': refs}
    doc['status'] = 'completed'
    return ({'status': 'completed', 'unmet': unmet, 'open_attempts': open_attempts},
            {'owner': owner, 'unmet': unmet, 'open_attempts': open_attempts})


def upgrade(cfg, doc, request):
    """Version 2 to version 3 on an active or paused cycle with no running assignment.

    The previous record bytes go to upgrade/v2-cycle.json before the save; a retry after a crash
    rewrites identical bytes, and a different file already there is refused rather than replaced."""
    if doc['schema_version'] == 3:
        raise Refused([failure('already-upgraded', 'the record is already version 3', field='schema_version', expected=2, observed=3)])
    if (problem := stale_cycle(doc, allow_paused=True)):
        raise Refused([problem])
    running = [e for e in doc.get('assignments', []) if e['state'] in OPEN]
    if running:
        recovery = []
        for e in running:
            where = ['assignment', doc['id'], '--id', e['id']]
            recovery.append(lowlevel(cfg, [*where, '--state', 'finished'],
                                     f"mark {e['id']} finished, only after the agent's final report or a host completion signal"))
            recovery.append(lowlevel(cfg, [*where, '--state', 'lost', '--note'],
                                     f"mark {e['id']} lost, only on the same affirmative evidence mark-lost needs (the host reported the agent terminated)",
                                     caller_fills=['--note']))
        raise Refused([failure('assignments-running', 'upgrade needs every assignment finished or lost; running: '
                               + ', '.join(f"{e['id']}/{e['attempt']}" for e in running), field='assignments',
                               expected='no running assignment', observed=[f"{e['id']}/{e['attempt']}" for e in running], recovery=recovery)])
    source = contained(cfg.docs_root, f"cycles/{doc['id']}/cycle.json")
    previous = source.read_bytes()
    relative = f"cycles/{doc['id']}/upgrade/v2-cycle.json"
    backup = contained(cfg.docs_root, relative)
    if backup.exists() and backup.read_bytes() != previous:
        raise Refused([failure('upgrade-backup-conflict', f'{relative} already holds different bytes; the upgrade does not replace it',
                               field='backup', expected=hashlib.sha256(previous).hexdigest(), observed=relative)])
    if not backup.exists():
        atomic_bytes(backup, previous)
    doc['schema_version'] = 3
    doc.update(v3_fields())
    for entry in doc.get('assignments', []):
        for key in ASSIGNMENT_V3_FIELDS:
            entry[key] = None
    return {'status': doc['status'], 'backup': relative}, {'previous_sha256': hashlib.sha256(previous).hexdigest()}


def withdraw_decision_op(cfg, doc, request):
    """Withdraw an IDR name in Plan: one record write marks it and removes its dependent tasks (see withdraw_decision)."""
    if (problem := stale_cycle(doc, allow_paused=False)):
        raise Refused([problem])
    if legacy(doc) or listed(doc):
        raise Refused([failure('cycle-refused', 'a release cycle has no decisions to withdraw', field='type', observed=doc['type'])])
    try:
        withdraw_decision(cfg, doc, request['name'], request['reason'], request['tasks'])
    except CycleError as exc:
        raise Refused([failure('cycle-refused', str(exc))]) from exc
    return ({'phase': doc['phase']}, {'name': request['name'], 'reason': request['reason'], 'tasks': list(request['tasks'])})


HANDLERS = {'prepare-dispatch': prepare_dispatch, 'execution-check': execution_check, 'child-link': child_link, 'release-continue': release_continue, 'attach-execution': attach_execution, 'deliver': deliver, 'mark-lost': mark_lost,
            'advance': advance, 'finish': finish, 'owner-exception': owner_exception, 'upgrade': upgrade,
            'withdraw-decision': withdraw_decision_op}
PRELOOKUP = {'advance': advance_lookup}
def finish_after_save(cfg, doc):
    """Remove the attempt files, then this cycle's merged, clean agent worktrees; report the worktrees."""
    import cycle_worktrees
    finish_cleanup(cfg, doc)
    tasks = {t['id'] for t in doc['plan']['tasks']} | {e['task'] for e in doc.get('assignments', [])}
    return {'worktrees': cycle_worktrees.cleanup(cfg.repo_root, tasks)}


AFTER_SAVE = {'finish': finish_after_save}


# ───────────────────────────── inspect ─────────────────────────────

def scope_leftovers(cfg, doc):
    """Paths in the plan scope that git reports as changed or untracked in the main checkout."""
    code, out = run_git(cfg, 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--', *doc['plan']['scope'])
    if code:
        return []
    found, parts = [], out.split('\0')
    skip = False
    for part in parts:
        if skip:
            skip = False
        elif len(part) > 3:
            found.append(part[3:])
            skip = part[0] in 'RC' or part[1] in 'RC'
    return found


def observation(cfg, doc, entry):
    """One derived observation per attempt; nothing is stored."""
    state = entry['state']
    out = {'id': entry['id'], 'task': entry['task'], 'role': entry['role'], 'host': entry.get('host'), 'mode': entry.get('mode'), 'attempt': entry['attempt'],
           'state': state, 'handle': entry['agent'], 'result_path': entry['result_path']}
    if entry.get('execution'):
        out['execution'] = deepcopy(entry['execution'])
        out['execution_currency'] = 'observed execution_head only; refresh through execution-check before work when HEAD changes'
    if state in OPEN:
        out['execution_check'] = action({'op': 'execution-check', 'assignment': entry['id'], 'attempt': entry['attempt']}, [],
                                        'verify the actual registered checkout before editing; unchanged proof is reused without a record commit')
    out['original_context'] = ({'snapshot': deepcopy(entry['invocation_snapshot']),
                                'retrieve': action({'op': 'dispatch-invocation', 'assignment': entry['id'], 'attempt': entry['attempt']}, [],
                                                   'retrieve this frozen invocation; executable parameters require current reserved eligibility')}
                               if entry.get('invocation_snapshot') else
                               {'unavailable': 'historical-no-snapshot; original invocation bytes were not retained'})
    if entry.get('invocation_history'):
        out['invocation_history'] = deepcopy(entry['invocation_history'])
    if entry.get('delivery_token'):
        out['delivery_token'] = entry['delivery_token']
        if state in OPEN and doc['status'] == 'active':
            out['resume'] = lowlevel(cfg, ['assignment', doc['id'], '--id', entry['id'], '--resume-token', entry['delivery_token']],
                                     'rotate delivery identity before resuming this same host execution; this starts no new execution', ['--note'])
    if entry.get('previous_results'):
        out['previous_results'] = deepcopy(entry['previous_results'])
    if state == 'finished':
        out['observation'] = 'delivered' if entry.get('delivery') else 'finished'
        return out
    if state == 'lost':
        out['observation'] = 'lost'
        if entry.get('host') and entry['task'] in {t['id'] for t in doc['plan']['tasks']} and any(
                e['assignment'] == entry['id'] and e['attempt'] == entry['attempt'] for e in reservations(doc, entry['task'])):
            # The next attempt can commit these under the task trailer or set them aside.
            out['leftovers'] = scope_leftovers(cfg, doc)
        return out
    out['observation'] = 'reserved-unbound' if state == 'reserved' else 'running-bound'
    path = result_file(cfg, entry)
    if result_complete(cfg, entry):
        out['observation'] = 'result-arrived'
    typed = entry.get('host') in cycle_hosts.ADAPTERS
    if typed:
        out['recovery'] = cycle_hosts.recovery_order(entry['host'], mode=entry.get('mode'), observation=out['observation'])
    if out['observation'] != 'result-arrived':
        if typed and path:
            # Windows are uncapped: inspect offers the next one and the caller starts it.
            out['wait'] = cycle_hosts.wait_descriptor(entry['host'], mode=entry.get('mode'), repo_root=cfg.repo_root,
                                                      result_path=str(path), assignment=entry['id'], attempt=entry['attempt'],
                                                      delivery_token=entry.get('delivery_token'))
            if entry['host'] == 'codex':
                out['wait']['binding']['handle'] = entry['agent']
        # No host in this build offers the engine a status call, so liveness is unknown.
        out['liveness'] = cycle_hosts.liveness(entry['host'], mode=entry.get('mode'), state=state) if typed else 'unknown'
        if path and not path.parent.is_dir():
            out['problem'] = 'result-path-missing'
    return out


def activity_of(cfg, doc, observed):
    """The cycle's last activity, and each open attempt's as `last_activity` on its observation.

    Derived read-only by cycle_activity from the record write, attempt last_seen, Cycle-Task commits,
    result files and linked-worktree changes. It is not liveness and never loss evidence: `liveness`
    keeps its own value."""
    found = cycle_activity.activity(cfg.repo_root, doc)
    by_attempt = {(a['id'], a['attempt']): a['last'] for a in found['attempts']}
    for entry in observed:
        if entry['state'] in OPEN:
            entry['last_activity'] = by_attempt.get((entry['id'], entry['attempt']))
    return {'state': found['state'], 'last': found['last'], 'text': cycle_activity.summary_line(found)}


def orphan_results(cfg, doc):
    """Retained result files that no recorded delivery names, as inspect problems."""
    directory = cfg.docs_root / 'cycles' / doc['id'] / 'results'
    if not directory.is_dir() or directory.is_symlink():
        return []
    named = {e['delivery']['path'] for e in doc.get('assignments', []) if e.get('delivery')}
    found = []
    for path in sorted(directory.iterdir()):
        relative = f"cycles/{doc['id']}/results/{path.name}"
        if path.is_file() and relative not in named:
            found.append({'code': 'orphan-retained-result', 'path': relative,
                          'problem': 'a retained result copy has no recorded delivery; it is kept, and a later deliver of the same attempt overwrites it'})
    return found


def nit_gaps(cfg, doc, decision):
    """Nit ids in the council record that approves a revision with no architect disposition for them.

    Reads `seats[].findings` of kind nit and `architect.nits[]`; an owner approval or a record with no nits has none."""
    if not decision.get('approval'):
        return []
    record = json.loads(contained(cfg.docs_root, decision['approval']).read_text())
    if not isinstance(record, dict) or record.get('format') not in ('crux.cycle-council', 'crux.cycle-council.v2'):
        return []
    from council_policy import nit_ids
    nits = nit_ids(record)
    disposed = {n['id'] for n in (record.get('architect') or {}).get('nits', []) if isinstance(n, dict) and n.get('disposition')}
    return [n for n in nits if n not in disposed]


def decision_findings(cfg, doc):
    """Problems and offered actions that concern withdrawn and exhausted IDRs, for a version-3 record.

    Reports a withdrawal with no defer entry, a new IDR that does not say what it replaces, a record at its council
    attempt limit, a withdrawn record with no attempts left where the type needs an approved IDR, and approved revisions
    whose nits have no recorded disposition. No route here asks the owner for anything."""
    problems, actions = [], []
    withdrawn = withdrawn_names(doc)
    cid = doc['id']
    for row in doc.get('withdrawals', []):
        if row['tasks'] and 'deferral' not in row:
            problems.append({'code': 'withdrawal-not-deferred', 'name': row['name'], 'tasks': row['tasks'],
                             'problem': f"IDR {row['name']} was withdrawn and its tasks were removed from the plan, but no queue entry records where that work continues"})
            actions.append(defer_route(cfg, doc, row))
    if doc.get('withdrawals'):
        first_at = min(w['at'] for w in doc['withdrawals'])
        seen = set()
        for ref in doc['decisions']:
            if ref['kind'] != 'idr' or ref['name'] in withdrawn or ref['name'] in seen:
                continue
            seen.add(ref['name'])
            record = read_retained(cfg, ref)
            if record['at'] > first_at and 'replaces' not in record['contents']:
                problems.append({'code': 'replaces-missing', 'name': ref['name'], 'withdrawn': sorted(withdrawn),
                                 'problem': f"IDR {ref['name']} was recorded after a withdrawal and does not say which withdrawn record it replaces; add replaces to its contents, so its attempts continue that record's count"})
    if doc['status'] == 'active' and doc['phase'] == 'plan':
        for name in dict.fromkeys(d['name'] for d in doc['decisions'] if d['kind'] == 'idr' and d['name'] not in withdrawn):
            if latest_idr(doc, name).get('approval'):
                continue
            try:
                state = council_state(cfg, doc, name)
            except (CycleError, OSError, ValueError):
                continue
            if len(state['attempts']) >= state['limit']:
                problems.append({'code': 'council-attempts-exhausted', 'name': name, 'attempts': len(state['attempts']), 'limit': state['limit'],
                                 'problem': f'IDR {name} has used its {state["limit"]} council attempts; withdraw it and its dependent tasks, then narrow the scope under a new name that replaces it'})
                actions.append(action({'op': 'withdraw-decision', 'name': name}, ['reason', 'tasks'],
                                      f'withdraw IDR {name}: list the plan tasks that depend on it and the reason'))
    needs_idr = doc['type'] in ('dev', 'simplify')
    for row in doc.get('withdrawals', []) if needs_idr else []:
        try:
            state = council_state(cfg, doc, row['name'])
            if len(state['attempts']) < state['limit'] or any(d['kind'] == 'idr' and d['name'] not in withdrawn and d.get('approval') for d in doc['decisions']):
                continue
        except (CycleError, OSError, ValueError):
            continue
        problems.append({'code': 'withdrawn-no-attempts-left', 'name': row['name'],
                         'problem': f"IDR {row['name']} is withdrawn with no council attempts left, and a {doc['type']} cycle needs an approved IDR; defer the remaining scope and abandon" +
                                    (', or change the type to iterate' if doc['type'] == 'dev' else '')})
        if 'deferral' not in row:
            actions.append(defer_route(cfg, doc, row))
        if doc['type'] == 'dev':
            actions.append(lowlevel(cfg, ['change-type', cid, '--type', 'iterate'], 'change the cycle to iterate, which needs no approval, when the remaining scope needs no material decision', ['--reason']))
        if doc['status'] == 'active':
            actions.append(lowlevel(cfg, ['pause', cid], 'pause the cycle before abandoning the deferred scope', ['--reason']))
        elif not doc['reflection']:
            actions.append(lowlevel(cfg, ['reflect', cid], 'record the reflection that abandonment requires', ['--json']))
        else:
            actions.append(lowlevel(cfg, ['abandon', cid], 'abandon the cycle: its scope is deferred and its decision was withdrawn', []))
    current = {}
    for ref in doc['decisions']:
        if ref['kind'] == 'idr' and ref['name'] not in withdrawn:
            current[ref['name']] = ref
    for name, ref in current.items():
        try:
            gaps = nit_gaps(cfg, doc, ref)
        except (OSError, ValueError, KeyError):
            continue
        if gaps:
            problems.append({'code': 'nit-dispositions-missing', 'name': name, 'approval': ref['approval'], 'nits': gaps,
                             'problem': f"the council record that approves IDR {name} lists nits with no architect disposition ({', '.join(gaps)}); the architect records each nit as apply-in-build or declined"})
    return problems, actions


def council_rounds_of(cfg, doc):
    """The council rounds of each IDR name that has attempts: attempt id, outcome and the reason it was convened."""
    import cycle_council
    out = {}
    for name in dict.fromkeys(d['name'] for d in doc['decisions'] if d['kind'] == 'idr'):
        try:
            rows = cycle_council.idr_history(cfg, doc, name, allow_open=True)
        except (CycleError, OSError, ValueError):
            continue
        if rows:
            rounds = cycle_council.council_rounds(rows, lambda rel: json.loads(contained(cfg.docs_root, rel).read_text()))
            for summary, row in zip(rounds, sorted(rows, key=lambda r: (r.get('started_at', ''), r.get('id', '')))):
                directory = (cycle_council.logical_directory(cfg, row['logical_id'], row.get('cycle_id')) if row.get('logical_id')
                             else cycle_council.council_directory(cfg, row.get('cycle_id')))
                relative = (directory / ('attempt-' + row['id'] + '.json')).relative_to(cfg.docs_root).as_posix()
                try:
                    summary['recovery'] = cycle_council.recovery_view(cfg.repo_root, relative)
                except (CycleError, OSError, ValueError):
                    summary['recovery_unavailable'] = True
            out[name] = rounds
    return out


def defer_route(cfg, doc, row):
    return lowlevel(cfg, ['defer', doc['id'], '--decision', row['name'], '--note'],
                    f"record the queue entry for the work removed with IDR {row['name']}; the entry keeps the reason and the council attempt history", ['--note'])


SUMMARY_FIELDS = ('revision', 'status', 'phase', 'pass', 'pass_limit', 'activity', 'unmet', 'actions', 'problems', 'record', 'focused_suggestions', 'advisory_unavailable')
SUMMARY_ATTEMPT = ('id', 'task', 'role', 'attempt', 'state', 'observation', 'liveness', 'last_activity', 'problem', 'recovery')
SUMMARY_ACTION = ('request', 'argv', 'caller_fills', 'purpose', 'agent', 'handler', 'classification',
                  'retained_report', 'assessment', 'criterion_options', 'recovery', 'omissions', 'unresolved')


def summarize(found):
    """The opt-in short form of inspect: position, unmet requirements, next actions, open attempts and record state.

    Every value is the full output's, trimmed: an action keeps its request or argv and the fields
    the caller fills, and an attempt its identity, state and recovery order."""
    out = {name: found[name] for name in SUMMARY_FIELDS if name in found}
    out['actions'] = [{k: a[k] for k in SUMMARY_ACTION if k in a} for a in found.get('actions', [])]
    out['open_attempts'] = [{k: e[k] for k in SUMMARY_ATTEMPT if k in e} for e in found.get('assignments', [])
                            if e.get('state') in OPEN]
    out['summary'] = True
    return out


def execution_return_offers(cfg, doc):
    """The counted return inspect offers after a range refusal journaled at delivery; it runs no proof.

    Offered only while no assignment of the cycle is reserved or running, for a pending or blocked
    task of the current phase whose latest assignment was reserved in the current pass and whose
    deliver event journaled an execution_observation with one of the two range codes. The writer's
    own probe decides at the return.
    """
    if listed(doc) or doc['phase'] not in ('build', *CHECK_PHASES, 'review'):
        return []
    if any(e['state'] in OPEN for e in doc.get('assignments', [])):
        return []
    offers = []
    for task in doc['plan']['tasks']:
        if task['phase'] != doc['phase'] or task['status'] not in ('pending', 'blocked'):
            continue
        entries = [e for e in doc.get('assignments', []) if e['task'] == task['id']]
        if not entries or entries[-1]['state'] != 'finished':
            continue
        entry = entries[-1]
        if not any(r['assignment'] == entry['id'] and r['attempt'] == entry['attempt'] for r in reservations(doc, task['id'])):
            continue  # a previous pass's delivery draws no offer
        observed = [((item.get('result') or {}).get('execution_observation') or {}).get('code')
                    for item in doc.get('operations', []) if item.get('op') == 'deliver'
                    and (item.get('result') or {}).get('assignment') == entry['id']
                    and (item.get('result') or {}).get('attempt') == entry['attempt']]
        if any(code in cycle_execution.RANGE_CODES for code in observed):
            offers.append(lowlevel(cfg, ['return', doc['id'], '--execution-task', task['id']],
                                   f"return to a new pass over the execution refusal task {task['id']} met; " + NEW_PASS_ROUTE,
                                   RETURN_FILLS))
    return offers


def blocked_pauses(cfg, doc):
    """The pause, offered beside any classified route, for each blocked task whose blocked delivery named no stop.

    A stopless blocked delivery triggers failure routing, but the block may still need an owner pause, so
    the pause stays available (IDR lean-workflow-traps-and-recovery approach 3). A delivery that named a stop
    gets the pause from the caller as before; the engine never pauses on its own."""
    out = []
    for task in doc['plan']['tasks']:
        if task['status'] != 'blocked' or task['phase'] != doc['phase']:
            continue
        latest = next((e for e in reversed(doc.get('assignments', [])) if e['task'] == task['id'] and e.get('delivery')), None)
        delivery = (latest or {}).get('delivery') or {}
        if delivery.get('outcome') == 'blocked' and not delivery.get('stop'):
            out.append(lowlevel(cfg, ['pause', doc['id']], f"pause the cycle if the block on task {task['id']} needs an owner decision or a wait; "
                                                           'otherwise follow the classified route or redispatch', ['--reason']))
    return out


def handoff_view(cfg, doc, assignment, attempt):
    """Completeness offers recovery, never a correctness gate or an automatic task mutation."""
    try:
        summary = cycle_classify.handoff_result(cfg, doc, assignment, attempt)
    except Exception as exc:
        return {'items': [], 'omissions': [], 'unresolved': [], 'reference_failures': [],
                'route': 'agent-assessment', 'recovery': [], 'error': type(exc).__name__}
    summary['recovery'] = []
    entry = assignment_entry(doc, assignment)
    task = task_entry(doc, entry['task']) if entry else None
    if (summary['unresolved'] and doc['status']=='active' and doc['schema_version']==VERSION
            and entry is not None and entry['attempt']==attempt and entry.get('delivery') and not entry['delivery'].get('stop')
            and task is not None and task.get('assignee',assignment)==assignment):
        summary['assessment']={'agent':True,'handler':'agent-assessment','caller_fills':[],
                               'purpose':f'assess unresolved expected evidence for {task["id"]}; preserve its recorded delivery and ordinary writer boundaries',
                               'unresolved':list(summary['unresolved']),
                               'retained_report':{key:entry['delivery'][key] for key in ('path','sha256')}}
    if (summary['route'] != 'missing-evidence-request' or doc['status'] != 'active' or doc['schema_version'] != VERSION
            or entry is None or entry['attempt'] != attempt or not entry.get('delivery') or entry['delivery'].get('stop')
            or task is None or task['phase'] != doc['phase']):
        if summary['omissions'] or summary['unresolved']:
            summary['route'] = 'agent-assessment'
        return summary
    role = redispatch_role(doc, task, entry['role'])
    if role is None:
        summary['route'] = 'agent-assessment'
        return summary
    candidate = deepcopy(doc)
    pending = task_entry(candidate, task['id'])
    try:
        if pending['status'] == 'done':
            pending.update(updated_task(cfg, candidate, pending, {'state': 'pending'}))
        dispatch_validation(cfg, candidate, {'task_id': task['id'], 'host': entry['host']}, role)
    except (Refused, CycleError):
        summary['route'] = 'agent-assessment'
        return summary
    summary['recovery'] = conflict_recovery(cfg, doc, entry, role)
    if task['status'] == 'done':
        summary['recovery'][0]['argv'].extend(['--expect-revision', str(doc['revision'])])
    return summary


def failure_actions(cfg, doc, offers):
    """Materialize bounded handlers only when code has the facts; retain missing judgment explicitly."""
    out = []
    for offer in offers:
        route = offer.get('handler')
        if route is None:
            out.append(offer)
            continue
        subject = offer['classification']['subject']
        task = task_entry(doc, subject)
        entry = assignment_entry(doc, subject)
        if task is None and entry:
            task = task_entry(doc, entry['task'])
        if task is not None:
            entry = next((value for value in reversed(doc.get('assignments', []))
                          if value['task'] == task['id'] and value.get('delivery')), entry)
        delivery = (entry or {}).get('delivery') or {}
        retained = {key: delivery[key] for key in ('path', 'sha256') if key in delivery}
        resolved = None
        if route == 'missing-evidence-request' and entry:
            view = handoff_view(cfg, doc, entry['id'], entry['attempt'])
            if view['recovery']:
                resolved = {**view['recovery'][0], 'recovery': view['recovery']}
        elif (route in ('owning-developer', 'environment-investigation') and task is not None and task['phase'] == 'build'
              and redispatch_role(doc, task, 'dev-lead') is not None):
            # The commander redispatches an editing task as a dev-lead; a unit task stays an agent offer for its coordinator.
            role = 'dev-lead'
            host = (entry or {}).get('host')
            request = {'op': 'prepare-dispatch', 'task_id': task['id'], 'role': role, 'host': host,
                       'assignment_text': f'Handle {route} within this task. Read the retained report at '
                                          f'{cfg.docs_root / delivery["path"]}; preserve its evidence and the recorded constraints.'} if retained else None
            if request is not None:
                try:
                    cycle_classify.arrangement_result(cfg, doc, task['id'], role=role)
                    dispatch_validation(cfg, doc, request, role)
                except (Refused, CycleError):
                    pass
                else:
                    resolved = action(request, [], f'follow the {route} handler within the existing task and allowance')
        elif route == 'acceptance-fix' and entry and task is not None:
            import cycle_context
            try:
                data = cycle_context.handoff_data(cfg, doc, entry['id'], entry['attempt'])
                criteria = cycle_context.failed_criteria(cfg, doc, data['references']) if data else []
                if criteria and doc['phase'] in (*CHECK_PHASES, 'review') and cycle_classify.fix_step_problem(doc, cfg) is None:
                    resolved = lowlevel(cfg, ['task-add', doc['id']], 'author the bounded acceptance-fix task as JSON; '
                                        'include its smallness argument and one of the validated criterion observations', ['--file'])
                    resolved['criterion_options'] = criteria
            except (CycleError, OSError, ValueError):
                pass
        if resolved is not None:
            out.append({**resolved, 'handler': route, 'classification': offer['classification'], 'retained_report': retained})
        else:
            # A report cannot supply an original request payload, a fix rationale or any new authorization.
            out.append({**offer, 'agent': True, 'retained_report': retained,
                        'assessment': 'use the retained evidence to supply missing authoring fields; revalidate the ordinary writer before acting'})
    return out


@cycle_advisory.advisory_operation
def inspect(repo_root, cycle_id, request):
    """The state `inspect` reports, plus whether the record has uncommitted changes and the commit-record action that clears them.

    One call scope holds the evidence reads, so each receipt and input is read once per inspect."""
    from test_evidence import call_scope
    with call_scope():
        out = inspect_state(repo_root, cycle_id, request)
    out['record'] = cycle_commit.pending_record(repo_root, cycle_id)
    if out['record']['pending']:
        out['actions'] = [*out.get('actions', []), action({'op': 'commit-record'}, [], 'commit the cycle record, which has uncommitted changes')]
    elif (out.get('status') == 'completed' and not out['record'].get('forge_log_open_attempts')
          and any(row['state'] in ('committable', 'missing') for row in out['record'].get('forge_logs', []))):
        # The record commit of a completed cycle writes and commits rederivable forge-log entries.
        out['actions'] = [*out.get('actions', []), action({'op': 'commit-record'}, [], 'commit the forge-log used entries this completed cycle rederives')]
    if cycle_advisory.advisory_unavailable():
        out['advisory_unavailable'] = 'deadline-exhausted'
    return out


def inspect_state(repo_root, cycle_id, request):
    doc = load(repo_root, cycle_id)
    cfg = tree(repo_root)
    version = doc['schema_version']
    out = {'revision': doc.get('revision'), 'schema_version': version, 'status': doc['status'], 'phase': doc['phase'],
           'pass': doc['pass'], 'pass_limit': doc['pass_limit'], 'head': git_head(cfg),
           'classifier': cycle_classify.classifier_state(repo_root), 'classifications': cycle_questions.rows(doc)}
    superseded = [{'task': t['id'], 'superseded_by': t['superseded_by']} for t in doc['plan']['tasks'] if t['status'] == 'superseded']
    if superseded:
        out['superseded'] = superseded
    from cycle_context_read import reference_view
    out['context_read'] = reference_view(cfg, doc)
    current_lost = [e for e in doc.get('assignments', []) if e['state'] == 'lost' and e.get('host')
                    and any(r['assignment'] == e['id'] and r['attempt'] == e['attempt'] for r in reservations(doc, e['task']))]
    out['assignments'] = [observation(cfg, doc, e) for e in doc.get('assignments', [])
                          if e['state'] in OPEN or e.get('delivery') is not None or e in current_lost]
    out['focused_suggestions'] = []
    if version == VERSION and doc['status'] == 'active':
        try:
            out['focused_suggestions'] = cycle_classify.focused_suggestions(cfg, doc)
        except Exception as exc:
            out['focused_suggestions_error'] = type(exc).__name__
        for entry in out['assignments']:
            source = assignment_entry(doc, entry['id'])
            if source.get('delivery') is not None and any(r['assignment'] == entry['id'] and r['attempt'] == entry['attempt']
                                                        for r in reservations(doc, entry['task'])):
                entry['handoff'] = handoff_view(cfg, doc, entry['id'], entry['attempt'])
    out['activity'] = activity_of(cfg, doc, out['assignments'])
    out['problems'] = orphan_results(cfg, doc)
    out['test_runs'] = cycle_summary.recorded_or_live_runs(cfg.repo_root, doc, time.time())
    if doc['status'] in CLOSED:
        out.update(unmet={'next': [], 'completion': []}, actions=[])
        return out
    out['unmet'] = {'next': requirements(cfg, doc, 'next')}
    actions = []
    if version == 2:
        out['unmet']['completion'] = requirements(cfg, doc, 'completion')
        out['actions'] = [action({'op': 'upgrade'}, [], 'upgrade the record to version 3 before typed operations')]
        return out
    if version == 1:
        out['unmet']['completion'] = requirements(cfg, doc, 'completion')
        out['actions'] = []
        return out
    candidate, blocking = completion_candidate(cfg, doc)
    out['unmet']['completion'] = [{'requirement': e['code'], 'problem': e['problem']} for e in blocking] + (
        requirements(cfg, candidate, 'completion') if not blocking else [])
    host = request.get('host')
    active = doc['status'] == 'active'
    review = cycle_classify.review_block(cfg, doc) if active else None
    if review is not None:
        out['review'] = review
    for entry in out['assignments']:
        recovery = (entry.get('handoff') or {}).get('recovery', [])
        if recovery:
            # The remaining steps are an ordered sequence in handoff.recovery, not legal alternatives yet.
            first = {**recovery[0], 'handler': 'missing-evidence-request',
                     'omissions': entry['handoff']['omissions'],
                     'purpose': f'request the missing evidence for {entry["task"]}: ' + recovery[0]['purpose']}
            actions.append(first)
        if entry['observation'] == 'result-arrived':
            actions.append(action({'op': 'deliver', 'assignment': entry['id'], 'attempt': entry['attempt']}, ['outcome'],
                                  'record the arrived result; add commits, evidence, stage and note as the report states'))
        elif entry['observation'] == 'reserved-unbound' and entry['host'] in cycle_hosts.ADAPTERS and cycle_hosts.returns_handle(entry['host'], entry.get('mode')):
            actions.append(action({'op': 'attach-execution', 'assignment': entry['id'], 'attempt': entry['attempt']}, ['handle'],
                                  'bind the handle the host returned when the agent was dispatched'))
        if entry.get('problem') == 'result-path-missing':
            actions.append(attempt_routes(entry)[1])
    if active:
        held = {e['task'] for e in doc.get('assignments', []) if e['state'] in OPEN}
        for task in doc['plan']['tasks']:
            if task['phase'] != doc['phase']:
                continue
            # The offer applies prepare-dispatch's own eligibility, attempt limit included. A Build or fix task is offered
            # to its reader, the commander, as a dev-lead dispatch only (IDR one-editor-per-checkout approach 3); any
            # other task is evaluated for every role that reserved it.
            editing = editing_task(task)
            roles = ['dev-lead'] if editing else sorted({e['role'] for e in reservations(doc, task['id'])})
            refusals = dispatch_failures(cfg, doc, task, roles)
            if refusals and all(e['code'] == 'attempt-limit' for e in refusals) and task['status'] in ('pending', 'blocked'):
                actions.extend(refusals[0]['recovery'])
            elif not refusals:
                request_doc = {'op': 'prepare-dispatch', 'task_id': task['id'], **({'role': 'dev-lead'} if editing else {})}
                fills = []
                if host in cycle_hosts.ADAPTERS:
                    request_doc['host'] = host
                else:
                    fills.append('host')
                found = action(request_doc, fills, f"dispatch task {task['id']}")
                if task['phase'] == 'review' and review is not None:
                    cycle_classify.name_specialists(found, review)
                actions.append(found)
        actions += blocked_pauses(cfg, doc)
        actions += execution_return_offers(cfg, doc)
        reusable = reusable_receipts(cfg, doc)
        out['reusable_evidence'] = [reusable[check] for check in missing_checks(cfg, doc) if check in reusable]
        if listed(doc):
            if not out['unmet']['completion']:
                actions.append(action({'op': 'finish', 'expect_revision': doc['revision']}, [], 'complete the release cycle'))
        elif doc['phase'] == 'reflect':
            if not out['unmet']['completion']:
                actions.append(action({'op': 'finish', 'expect_revision': doc['revision']}, ['lessons', 'remaining'],
                                      'close the cycle with its recorded commits'))
            else:
                for item in blocking:
                    actions += [a for a in item['recovery'] if 'request' in a and a['request']['op'] == 'finish']
        for item in out['unmet']['next']:
            for route in declaration_routes(cfg, doc, item['requirement']):
                if route not in actions:
                    actions.append(route)
        if review_requests_changes(cfg, doc):
            actions += return_routes(cfg, doc)
        elif not held and (listed(doc) or doc['phase'] != 'reflect'):
            # Typed advance when nothing is unmet, or when attaching the reusable receipts meets every item.
            candidate = deepcopy(doc)
            for check in missing_checks(cfg, candidate):
                if check in reusable:
                    try:
                        attach_reusable(cfg, candidate, {check: reusable[check]})
                    except Refused:
                        pass
            if not requirements(cfg, candidate, 'next'):
                actions.append(action({'op': 'advance', 'expect_revision': doc['revision']}, [], 'leave the current phase'))
    found, offered = decision_findings(cfg, doc)
    out['councils'] = council_rounds_of(cfg, doc)
    out['problems'] += found
    actions += offered
    if active:
        classified=failure_actions(cfg,doc,cycle_classify.offered_actions(cfg,doc,host,repo_root))
        assessments=[]
        for entry in out['assignments']:
            assessment=(entry.get('handoff') or {}).get('assessment')
            if assessment and not any(offer.get('classification',{}).get('kind')=='failure-routing'
                                      and offer['classification']['subject'] in (entry['task'],entry['id']) for offer in classified):
                assessments.append(assessment)
        out['actions']=classified+assessments+actions
    else:
        out['actions']=actions
    return out
