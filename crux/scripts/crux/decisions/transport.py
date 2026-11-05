"""The shipped Decisions transport: request build, the one call, validation and error mapping.

``crux.decisions.ask`` and ``classifier_status`` delegate here. The module is adapted
from the experiment transport under ``tools/jev/``, which the plugin tree never
imports. Differences are deliberate and listed below.

Properties held here:

1. The URL derives from a pinned origin (``https://openrouter.ai``) and a pinned path
   (``/api/alpha/decisions``). The registry's gateway origin must match on scheme,
   host and port, with no userinfo, before the credential is read. A mismatch makes
   the classifier unconfigured and sends nothing.
2. No redirect is followed. ``follow_redirects=False`` is passed on the call itself,
   so an injected client cannot forward the body to a ``Location`` the gateway picks.
3. The ``provider`` object is exactly ``dict(REQUIRED_DENIALS)`` on every request. It
   never comes from the registry. The registry loader refuses an entry that weakens
   the data-collection denial or carries a key in ``REFUSED_ENTRY_KEYS``. Nothing
   here relaxes a denial.
4. The credential comes from ``crux_env``, travels only in the authorization header,
   and appears in no outcome, exception message or log line. An outcome carries no
   free text from the gateway; ids copied from a response are length- and
   character-bounded and dropped when they contain the credential.
5. The request omits ``session_id`` and ``user``.

Order of checks, each ending the call with an ``Outcome`` and no request:
role and registry entry (``unconfigured``), state size (``over-input-bound``), token
ceilings (``over-token-ceiling``), credential (``unconfigured``), secret scan
(``scan-match``, ``scan-failure``). The call follows. ``ask_many`` splits its wire
questions into requests of at most ``MAX_QUESTIONS_PER_REQUEST``; the ceilings, the
scan and the retry apply to each request.

Retry: one retry, only after ``timeout`` or ``unavailable``. Each request is bounded
by ``min(entry timeout, deadline.call_timeout())`` as a wall-clock limit on the whole
exchange, so a response that drips bytes ends at the bound. When the deadline has no
time left, a first call is not made and the outcome is ``unavailable`` with zero
attempts; a retry that finds no time left returns the first attempt's outcome.

Served model: the response ``model`` must equal ``EXPECTED_SERVED_MODEL`` or that id
followed by ``-`` and eight digits. The gateway lists the endpoint as
``openai/gpt-6-luna-decisions-20261006``, so a dated id of the pinned model is the
same model. Any other value, or no value, is ``malformed:served-model``.

Differences from the experiment: a ``refusal`` answer type is recognised; a noul or
score answer to a choice question is malformed; a data-policy or no-endpoint gateway
error maps to ``no-endpoint`` whatever its status; 401 and 403 keep their status
class; one retry replaces the experiment's none; confidence gates nothing.
"""
from __future__ import annotations

import json
import logging
import math
import re
import threading
import time
from dataclasses import dataclass, field, replace
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

import httpx

import crux_env
from crux.core import llm_caller

from . import (
    ANSWERED, CALL_TIMEOUT_SECONDS, EXPECTED_SERVED_MODEL, MAX_CONFIGURED_STATE_CHARS, MAX_QUESTIONS_PER_REQUEST, MAX_RETRIES, MAX_STATE_CHARS,
    MODEL_ROLE, REFUSED_ENTRY_KEYS, REQUIRED_DENIALS,
    STATE_PLUS_ALL_QUESTIONS_TOKENS, STATE_PLUS_LONGEST_QUESTION_TOKENS, ChoiceQuestion, Deadline, Outcome, PredicateQuestion,
    ScoreQuestion, Status,
)

_log = logging.getLogger(__name__)

PINNED_SCHEME = 'https'
PINNED_HOST = 'openrouter.ai'
DECISIONS_PATH = '/api/alpha/decisions'
CREDENTIAL_KEY = 'OPENROUTER_API_KEY'

# The role the registry maps to the classifier's model. Named here as a literal so the
# role-reader check sees this module read it; a test pins it to MODEL_ROLE.
_ROLE = 'cycle_classifier'

CHARS_PER_TOKEN = 4          # the experiment's estimate: chars / 4, rounded up
MAX_RESPONSE_BYTES = 1_000_000
MAX_ID_CHARS = 128
QUESTION_ID_MAX_CHARS = 128

_SERVED_DATED = re.compile(r'-\d{8}$')
_SAFE_ID = re.compile(r'^[A-Za-z0-9._:/-]+$')
_NO_ENDPOINT = re.compile(
    r'data[\s-]*polic(?:y|ies)|zero[\s-]*data[\s-]*retention|no\s+endpoints?\s+found|no\s+(?:matching\s+)?endpoints?',
    re.IGNORECASE)


class UnusableEntry(Exception):
    """The role or its registry entry cannot support a classification. ``reason`` is the status code."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class OverCeiling(Exception):
    """The request estimate is over a token ceiling. Carries numbers only."""


@dataclass(frozen=True)
class ClassifierEntry:
    api_string: str
    url: str
    auth_header: str
    auth_prefix: str
    timeout_seconds: float
    input_bounds: Mapping[str, int] = field(default_factory=dict)
    model_key: str = ''
    context_keep: int = 3
    focused_test_keep: int = 3


# --- configuration -----------------------------------------------------------------------------

def pinned_url(base_url: str) -> str:
    """The Decisions URL for a gateway base URL, or ``UnusableEntry`` when the origin is not the pinned one."""
    try:
        parts = urlsplit(base_url)
        host = (parts.hostname or '').lower()
        port = parts.port
    except (ValueError, AttributeError):
        raise UnusableEntry('registry-entry-invalid') from None
    if '@' in parts.netloc or parts.scheme != PINNED_SCHEME or host != PINNED_HOST or port is not None:
        raise UnusableEntry('registry-entry-invalid')
    return urlunsplit((PINNED_SCHEME, PINNED_HOST, DECISIONS_PATH, '', ''))


def load_classifier_entry() -> ClassifierEntry:
    """Load the ``cycle_classifier`` entry and refuse one that weakens a denial.

    Raises ``UnusableEntry('role-missing')`` when the role is absent or empty, and
    ``UnusableEntry('registry-entry-invalid')`` for every other defect: an unknown
    model, a type other than ``decisions``, ``data_collection`` other than ``deny``,
    any key in ``REFUSED_ENTRY_KEYS`` (``zdr``), a model id other than ``EXPECTED_SERVED_MODEL``, a bad
    timeout, or an origin other than the pinned one. It never reads the credential.
    """
    try:
        config = llm_caller.load_router_config()
        roles = config.get('model_roles') if isinstance(config, dict) else None
        value = roles.get(_ROLE) if isinstance(roles, dict) else None
    except (OSError, ValueError):
        raise UnusableEntry('registry-entry-invalid') from None
    if not value:
        raise UnusableEntry('role-missing')
    if not isinstance(value, str):
        raise UnusableEntry('registry-entry-invalid')
    try:
        # Currentness must not inherit the shared role resolver's warm cache.
        key = value
        cfg = llm_caller.get_model_config(key)
        raw = config['models'][key]
    except (ValueError, TypeError, KeyError, OSError):
        raise UnusableEntry('registry-entry-invalid') from None
    timeout = raw.get('timeout_seconds', CALL_TIMEOUT_SECONDS)
    bounds = raw.get('input_bounds', {})
    keeps = [raw.get(name, 3) for name in ('context_keep', 'focused_test_keep')]
    if (cfg.model_type != 'decisions'
            or cfg.data_collection != REQUIRED_DENIALS['data_collection']
            or any(key in raw for key in REFUSED_ENTRY_KEYS)
            or cfg.api_string != EXPECTED_SERVED_MODEL
            or isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or timeout <= 0
            or not isinstance(bounds, dict)
            or any(type(count) is not int or not 0 <= count <= 8 for count in keeps)
            or any(not isinstance(kind, str) or not kind.strip()
                   or isinstance(bound, bool) or not isinstance(bound, int)
                   or not 1 <= bound <= MAX_CONFIGURED_STATE_CHARS
                   for kind, bound in bounds.items())):
        raise UnusableEntry('registry-entry-invalid')
    return ClassifierEntry(cfg.api_string, pinned_url(cfg.base_url), cfg.auth_header, cfg.auth_prefix,
                           float(timeout), dict(bounds), key, *keeps)


def _input_bound(entry: ClassifierEntry, kinds: tuple[str, ...]) -> int:
    if not isinstance(kinds, (tuple, list)) or any(not isinstance(kind, str) or not kind.strip() for kind in kinds):
        raise TypeError('kinds must be a sequence of non-empty classification names')
    return min((entry.input_bounds.get(kind, MAX_STATE_CHARS) for kind in kinds), default=MAX_STATE_CHARS)


def input_bound(kinds: tuple[str, ...] = ()) -> int:
    """Select named central policy; callers cannot supply a larger numeric cap."""
    try:
        entry = load_classifier_entry()
    except UnusableEntry:
        entry = ClassifierEntry('', '', '', '', CALL_TIMEOUT_SECONDS)
    return _input_bound(entry, kinds)


def classifier_basis() -> dict[str, Any] | None:
    """The request policy, without credentials or unrelated registry metadata."""
    try:
        entry = load_classifier_entry()
    except UnusableEntry:
        return None
    return {'model': entry.api_string, 'model_key': entry.model_key, 'endpoint': entry.url,
            'timeout_seconds': entry.timeout_seconds, 'auth_header': entry.auth_header, 'auth_prefix': entry.auth_prefix,
            'input_bounds': dict(entry.input_bounds), 'default_bound': MAX_STATE_CHARS,
            'context_keep': entry.context_keep, 'focused_test_keep': entry.focused_test_keep,
            'denials': dict(REQUIRED_DENIALS), 'refused_entry_keys': sorted(REFUSED_ENTRY_KEYS),
            'question_limit': MAX_QUESTIONS_PER_REQUEST,
            'token_limits': [STATE_PLUS_LONGEST_QUESTION_TOKENS, STATE_PLUS_ALL_QUESTIONS_TOKENS]}


def _credential() -> str | None:
    try:
        value = crux_env.get(CREDENTIAL_KEY)
    except Exception:
        return None
    return value if isinstance(value, str) and value else None


def classifier_status() -> Status:
    """Whether the classifier can send. Never raises and never returns the credential."""
    try:
        load_classifier_entry()
    except UnusableEntry as exc:
        return Status(False, exc.reason)
    except Exception:
        return Status(False, 'registry-entry-invalid')
    if _credential() is None:
        return Status(False, 'credential-missing')
    return Status(True, None)


# --- request build -----------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def render_state(state: Mapping[str, Any]) -> str:
    try:
        return json.dumps(state, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        raise TypeError('state is not JSON-serializable') from None


def wire_question(question: ChoiceQuestion) -> dict[str, Any]:
    if not isinstance(question, ChoiceQuestion):
        raise TypeError('question must be a ChoiceQuestion')
    options = question.options
    if (not isinstance(question.instructions, str) or not question.instructions.strip()
            or not isinstance(options, Mapping) or not options
            or not all(isinstance(k, str) and k and isinstance(v, str) for k, v in options.items())):
        raise TypeError('a ChoiceQuestion needs instructions and a non-empty map of option id to description')
    return {'type': 'choice', 'instructions': question.instructions, 'criteria': dict(options)}


def check_ceilings(rendered_state: str, wire_questions: Mapping[str, Any]) -> None:
    """Refuse an estimate over the token ceilings. Raises ``OverCeiling`` naming numbers only."""
    state_tokens = estimate_tokens(rendered_state)
    sizes = [estimate_tokens(json.dumps(q, ensure_ascii=False, sort_keys=True)) for q in wire_questions.values()]
    if state_tokens + max(sizes) > STATE_PLUS_LONGEST_QUESTION_TOKENS:
        raise OverCeiling(f'{state_tokens + max(sizes)} estimated tokens for state plus the longest question')
    if state_tokens + sum(sizes) > STATE_PLUS_ALL_QUESTIONS_TOKENS:
        raise OverCeiling(f'{state_tokens + sum(sizes)} estimated tokens for state plus all questions')


def _scan(texts: list[str], credential: str) -> str | None:
    """``None`` when the scan passes, else ``scan-match`` or ``scan-failure``. Fails closed."""
    try:
        import secret_scan
        for text in texts:
            if secret_scan.scan_text(text, exact=[credential]):
                return 'scan-match'
    except Exception:
        return 'scan-failure'
    return None


# --- the call ----------------------------------------------------------------------------------

@dataclass(frozen=True)
class _Reply:
    kind: str                  # 'response' | 'timeout' | 'unavailable'
    status_code: int | None = None
    body: bytes = b''


class _Overrun(Exception):
    pass


class _TooLarge(Exception):
    pass


def _exchange(client: Any, url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> _Reply:
    """One request bounded in wall-clock time. A worker thread does the exchange; the caller waits `timeout`."""
    box: list[_Reply] = []

    def work() -> None:
        http = client if client is not None else httpx.Client()
        end = time.monotonic() + timeout
        try:
            with http.stream('POST', url, headers=headers, json=payload, timeout=httpx.Timeout(timeout),
                             follow_redirects=False) as response:
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    if time.monotonic() > end:
                        raise _Overrun()
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        raise _TooLarge()
                    chunks.append(chunk)
                box.append(_Reply('response', response.status_code, b''.join(chunks)))
        except (_Overrun, httpx.TimeoutException):
            box.append(_Reply('timeout'))
        except _TooLarge:
            box.append(_Reply('response', 200, b''))          # an unreadable body: malformed
        except Exception:
            box.append(_Reply('unavailable'))
        finally:
            if client is None:
                http.close()

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive() or not box:
        return _Reply('timeout')
    return box[0]


def names_no_endpoint(message: str) -> bool:
    """Whether a gateway error message names the data policy, zero data retention or a missing endpoint."""
    return bool(isinstance(message, str) and _NO_ENDPOINT.search(message))


def _error_message(body: bytes) -> str:
    text = body[:4096].decode('utf-8', errors='replace')
    try:
        data = json.loads(text)
    except ValueError:
        return text
    error = data.get('error') if isinstance(data, Mapping) else None
    if isinstance(error, Mapping) and isinstance(error.get('message'), str):
        return error['message']
    if isinstance(error, str):
        return error
    return ''


def _served_ok(served: Any) -> bool:
    if not isinstance(served, str):
        return False
    if served == EXPECTED_SERVED_MODEL:
        return True
    return served.startswith(EXPECTED_SERVED_MODEL) and bool(_SERVED_DATED.fullmatch(served[len(EXPECTED_SERVED_MODEL):]))


def _clean_id(value: Any, credential: str) -> str | None:
    """A response id kept for the record: bounded, plain characters, never containing the credential."""
    if (isinstance(value, str) and 0 < len(value) <= MAX_ID_CHARS and _SAFE_ID.fullmatch(value)
            and credential not in value):
        return value
    return None


def _clean_provider(value: Any, credential: str) -> str | None:
    """The serving provider a response names: 1-200 printable ASCII characters, never containing the credential."""
    if (isinstance(value, str) and 0 < len(value) <= 200 and all(' ' <= ch <= '~' for ch in value)
            and credential not in value):
        return value
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and 0.0 <= number <= 1.0 else None


def _usage(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    usage: dict[str, Any] = {}
    for name in ('input_tokens', 'output_tokens'):
        value = raw.get(name)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            usage[name] = value
    cost = raw.get('cost')
    if isinstance(cost, (int, float)) and not isinstance(cost, bool) and math.isfinite(cost) and cost >= 0:
        usage['cost'] = float(cost)
    return usage or None


def _answer_outcome(base: Outcome, answer: Any, question: ChoiceQuestion, usage: Mapping[str, Any] | None) -> Outcome:
    """Validate one answer against its own question. Another question's answer never affects this one."""
    if not isinstance(answer, Mapping):
        return base
    kind = answer.get('type')
    if kind == 'refusal':
        return replace(base, status='refusal')
    if kind != 'choice':                       # a noul, score or unknown type is malformed
        return base
    choice = answer.get('choice')
    if not isinstance(choice, str) or choice not in question.options:
        return base
    probabilities = None
    raw_probabilities = answer.get('probabilities')
    if raw_probabilities is not None:
        if not isinstance(raw_probabilities, Mapping) or not set(raw_probabilities) <= set(question.options):
            return base
        probabilities = {}
        for name, value in raw_probabilities.items():
            number = _number(value)
            if number is None:
                return base
            probabilities[name] = number            # a sum other than 1 is recorded, not refused
    confidence = None
    if answer.get('confidence') is not None:
        confidence = _number(answer['confidence'])
        if confidence is None:
            return base
    return replace(base, status=ANSWERED, choice=choice, probabilities=probabilities, confidence=confidence, usage=usage)


def _interpret_many(reply: _Reply, questions: Mapping[str, ChoiceQuestion], credential: str) -> dict[str, Outcome]:
    """Map one reply onto an Outcome per question id. `attempts` is filled by the caller.

    A transport-level failure (status, body, served model, an answers object naming an id that was not asked)
    applies to every question. Otherwise each answer is validated by its id on its own: a missing or malformed
    answer falls back for that question only. The request's usage is reported once, on the first answered
    question in request order, so a sum over the outcomes counts the request's cost once."""
    status_code = reply.status_code
    base = Outcome(status='malformed', http_status=status_code)

    def every(outcome: Outcome) -> dict[str, Outcome]:
        return {qid: outcome for qid in questions}

    if status_code is None or not 200 <= status_code <= 299:
        if names_no_endpoint(_error_message(reply.body)):
            return every(replace(base, status='no-endpoint'))
        if status_code in (401, 403):
            return every(replace(base, status=f'malformed:http-{status_code}'))
        if status_code == 429 or (status_code is not None and 500 <= status_code <= 599):
            return every(replace(base, status='unavailable'))
        return every(base)
    try:
        data = json.loads(reply.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return every(base)
    if not isinstance(data, Mapping):
        return every(base)
    served = data.get('model')
    request_id = _clean_id(data.get('id'), credential)
    served_clean = _clean_id(served, credential)
    base = replace(base, request_id=request_id, served_model=served_clean, served_provider=_clean_provider(data.get('provider'), credential))
    if not _served_ok(served):
        return every(replace(base, status='malformed:served-model'))
    answers = data.get('answers')
    if not isinstance(answers, Mapping) or not set(answers) <= set(questions):
        return every(base)
    usage = _usage(data.get('usage'))
    out: dict[str, Outcome] = {}
    for qid, question in questions.items():
        out[qid] = _answer_outcome(base, answers.get(qid), question, usage)
        if out[qid].status == ANSWERED:
            usage = None
    return out


def _interpret(reply: _Reply, question_id: str, question: ChoiceQuestion, credential: str) -> Outcome:
    """Map one reply onto the Outcome of a single question. `attempts` is filled by the caller."""
    return _interpret_many(reply, {question_id: question}, credential)[question_id]


def _finish(outcome: Outcome) -> Outcome:
    _log.debug('decisions outcome status=%s http_status=%s attempts=%d', outcome.status, outcome.http_status,
               outcome.attempts)
    return outcome


SCORE_YES_SUFFIX = ' Answer yes when the candidate the yes option describes is one to select, and no otherwise.'
SCORE_NO_TEXT = 'Do not select this candidate.'
_SUB_SEPARATOR = '#'


def _expand(questions: Mapping[str, Any]) -> tuple[dict[str, ChoiceQuestion], dict[str, list[str]]]:
    """The wire choice questions for the asked questions, and each asked id's wire ids in order.

    A choice question goes as itself. A predicate goes as one choice of yes, no and its extra options. A score
    goes as one yes/no choice per candidate, keyed ``<id>#<n>``. Raises ``TypeError`` on a bad question."""
    wire: dict[str, ChoiceQuestion] = {}
    owners: dict[str, list[str]] = {}
    for qid, question in questions.items():
        if not isinstance(qid, str) or not qid.strip() or len(qid) > QUESTION_ID_MAX_CHARS or _SUB_SEPARATOR in qid:
            raise TypeError('question_id must be a non-empty string of at most 128 characters without #')
        if isinstance(question, ChoiceQuestion):
            wire[qid] = question
            owners[qid] = [qid]
        elif isinstance(question, PredicateQuestion):
            extra = dict(question.extra) if isinstance(question.extra, Mapping) else None
            if (extra is None or not isinstance(question.yes, str) or not isinstance(question.no, str)
                    or {'yes', 'no'} & set(extra)):
                raise TypeError('a PredicateQuestion needs yes and no texts and extra options other than yes and no')
            wire[qid] = ChoiceQuestion(question.instructions, {'yes': question.yes, 'no': question.no, **extra})
            owners[qid] = [qid]
        elif isinstance(question, ScoreQuestion):
            candidates = question.candidates
            if (not isinstance(candidates, Mapping) or not candidates or isinstance(question.keep, bool)
                    or not isinstance(question.keep, int) or question.keep < 1
                    or not isinstance(question.instructions, str) or not question.instructions.strip()):
                raise TypeError('a ScoreQuestion needs instructions, candidates and a positive keep count')
            ids = []
            for n, (name, text) in enumerate(candidates.items()):
                sub = f'{qid}{_SUB_SEPARATOR}{n}'
                if len(sub) > QUESTION_ID_MAX_CHARS or not isinstance(name, str) or not name or not isinstance(text, str):
                    raise TypeError('a ScoreQuestion candidate needs an id and a description, and its wire id at most 128 characters')
                wire[sub] = ChoiceQuestion(question.instructions + SCORE_YES_SUFFIX, {'yes': text, 'no': SCORE_NO_TEXT})
                ids.append(sub)
            owners[qid] = ids
        else:
            raise TypeError('a question must be a ChoiceQuestion, PredicateQuestion or ScoreQuestion')
    return wire, owners


def _sum_usage(outcomes: list[Outcome]) -> dict[str, Any] | None:
    total: dict[str, Any] = {}
    for outcome in outcomes:
        for name, value in (outcome.usage or {}).items():
            total[name] = total.get(name, 0) + value
    return total or None


def _collapse(question: Any, subs: list[Outcome]) -> Outcome:
    """The outcome of one asked question from its wire outcomes."""
    if not isinstance(question, ScoreQuestion):
        return subs[0]
    usage = _sum_usage(subs)
    failed = next((o for o in subs if o.status != ANSWERED), None)
    if failed is not None:
        return replace(failed, usage=usage, choice=None, probabilities=None, confidence=None)
    names = list(question.candidates)
    kept = tuple(name for name, o in zip(names, subs) if o.choice == 'yes')[:question.keep]
    first = subs[0]
    return replace(first, usage=usage, choice=None, probabilities=None, confidence=None, selected=kept,
                   attempts=max(o.attempts for o in subs))


def _chunks(ids: list[str], size: int) -> list[list[str]]:
    return [ids[i:i + size] for i in range(0, len(ids), size)]


def ask_many(state: Mapping[str, Any], questions: Mapping[str, Any], *, deadline: Deadline,
             client: Any = None, kinds: tuple[str, ...] = ()) -> dict[str, Outcome]:
    """Ask several questions about one state; return an Outcome per asked question id.

    Raises ``TypeError`` on a bad argument. The wire questions go in requests of at most
    ``MAX_QUESTIONS_PER_REQUEST``. A pre-send check (configuration, credential) applies to every request; the input
    bound, token ceilings and secret scan apply to each request. A request-level timeout or unavailability is
    retried once, asking only the questions of that request that have no valid answer; any other outcome is final."""
    if not isinstance(state, Mapping):
        raise TypeError('state must be a mapping')
    if not isinstance(questions, Mapping) or not questions:
        raise TypeError('questions must be a non-empty mapping of question id to question')
    wire_questions, owners = _expand(questions)
    wire = {qid: wire_question(question) for qid, question in wire_questions.items()}
    rendered = render_state(state)

    def done(by_wire: Mapping[str, Outcome]) -> dict[str, Outcome]:
        return {qid: _finish(_collapse(questions[qid], [by_wire[w] for w in owners[qid]])) for qid in questions}

    def every(outcome: Outcome) -> dict[str, Outcome]:
        return done({w: outcome for w in wire})

    try:
        entry = load_classifier_entry()
    except Exception:
        return every(Outcome(status='unconfigured'))
    if len(rendered) > _input_bound(entry, kinds):
        return every(Outcome(status='over-input-bound'))
    results: dict[str, Outcome] = {}
    chunks = []
    for chunk in _chunks(list(wire), MAX_QUESTIONS_PER_REQUEST):
        try:
            check_ceilings(rendered, {w: wire[w] for w in chunk})
        except OverCeiling:
            results.update({w: Outcome(status='over-token-ceiling') for w in chunk})
            continue
        chunks.append(chunk)
    if not chunks:
        return done(results)
    credential = _credential()
    if credential is None:
        return every(Outcome(status='unconfigured')) if not results else done(
            {**results, **{w: Outcome(status='unconfigured') for chunk in chunks for w in chunk}})
    headers = {entry.auth_header: f'{entry.auth_prefix}{credential}', 'Content-Type': 'application/json'}
    for chunk in chunks:
        results.update(_request(state, rendered, {w: wire[w] for w in chunk}, {w: wire_questions[w] for w in chunk},
                                entry, headers, credential, deadline, client))
    return done(results)


def _request(state: Mapping[str, Any], rendered: str, wire: Mapping[str, Any], questions: Mapping[str, ChoiceQuestion],
             entry: ClassifierEntry, headers: dict[str, str], credential: str, deadline: Deadline,
             client: Any) -> dict[str, Outcome]:
    """One request of at most MAX_QUESTIONS_PER_REQUEST wire questions, with its own secret scan and single retry."""
    failed = _scan([rendered, json.dumps(wire, ensure_ascii=False, sort_keys=True)], credential)
    if failed:
        return {qid: Outcome(status=failed) for qid in wire}
    results: dict[str, Outcome] = {}
    pending = dict(questions)
    attempts = 0
    for _ in range(MAX_RETRIES + 1):
        timeout = min(entry.timeout_seconds, deadline.call_timeout())
        if timeout <= 0:
            for qid in pending:
                results.setdefault(qid, Outcome(status='unavailable', attempts=attempts))
            break
        attempts += 1
        payload = {
            'model': entry.api_string,
            'state': dict(state),
            'questions': {qid: wire[qid] for qid in pending},
            'provider': dict(REQUIRED_DENIALS),     # never from the registry
        }
        reply = _exchange(client, entry.url, headers, payload, timeout)
        if reply.kind == 'response':
            outcomes = _interpret_many(reply, pending, credential)
        else:
            outcomes = {qid: Outcome(status=reply.kind) for qid in pending}
        retry = {}
        for qid, outcome in outcomes.items():
            results[qid] = replace(outcome, attempts=attempts)
            if outcome.status in ('timeout', 'unavailable'):
                retry[qid] = pending[qid]
        if not retry:
            break
        pending = retry
    return results


def ask(state: Mapping[str, Any], question_id: str, question: ChoiceQuestion, *, deadline: Deadline,
        client: Any = None) -> Outcome:
    """Ask one choice question about one state. Raises ``TypeError`` on a bad argument; otherwise returns an Outcome."""
    if not isinstance(question_id, str) or not question_id.strip() or len(question_id) > QUESTION_ID_MAX_CHARS:
        raise TypeError('question_id must be a non-empty string of at most 128 characters')
    return ask_many(state, {question_id: question}, deadline=deadline, client=client)[question_id]
