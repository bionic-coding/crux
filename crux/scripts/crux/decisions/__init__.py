"""The shipped Decisions transport for cycle classification.

This package is the contract between the transport and the cycle engine. The cycle
engine (``cycle_classify``) imports only the names in ``__all__``. It never builds a
request, reads the credential or touches the wire itself.

Contract (CYC-0090, IDR decision-transport-and-routing revision 5):

- ``REQUIRED_DENIALS`` is the one central, named denial set. The transport writes
  exactly these values into every request's ``provider`` object, whatever the
  registry entry says, and the registry loader refuses an entry that weakens one.
  No switch relaxes a denial.
- ``REFUSED_ENTRY_KEYS`` names the provider preferences the route never sends. The
  registry loader and model validation refuse an entry that carries one, so the
  registry cannot reintroduce a preference the route cannot satisfy.
- ``classifier_status()`` reports whether the classifier can send: the
  ``cycle_classifier`` role is present and non-empty, its registry entry loads with
  the denials intact, and the gateway credential exists. It never raises for an
  unconfigured classifier and never returns the credential. The repository opt-out
  (``.bionic.yml`` ``decisions: {classifier: off}``) is read by the caller, not here.
- ``ask()`` asks one choice question about one state, under a shared ``Deadline``.
  It retries once, only after a timeout or unavailability, and returns an
  ``Outcome``; it raises only on a programming error (a bad argument type). Every
  failure is an ``Outcome`` whose ``status`` is not ``answered``.
- ``ask_many()`` asks several choice questions, keyed by id, about one state in one
  request, and returns an ``Outcome`` per id (CYC-0099, IDR luna-classification-expansion
  approach 1). Each answer is validated by its id on its own, so a malformed or refused
  answer falls back for that question only. A request-level timeout or unavailability is
  retried once, asking only the questions without a valid answer. ``ask()`` is
  ``ask_many()`` with one question. The request's usage is reported on the first
  answered outcome only, so summing outcomes counts one request's cost once.
- Question types (approach 1): ``ChoiceQuestion`` for exclusive categories,
  ``PredicateQuestion`` for an independent yes/no property and ``ScoreQuestion`` for an
  ordering of candidates. The route's native ``noul`` and ``score`` types are unobserved
  until a live check records them, and a ``noul`` answer is a probability that would need
  a threshold, so both are always sent as choice questions: a predicate as one yes/no
  choice, and a score as one yes/no choice per candidate, with code keeping the yes
  answers up to ``keep`` in candidate order. A score is answered only when every
  candidate's choice is.
- ``MAX_QUESTIONS_PER_REQUEST`` bounds one request (approach 2): ``ask_many`` splits the
  wire questions into requests of at most that many, each with its own single retry.
  ``REQUEST_CONCURRENCY`` bounds how many requests a caller runs at once for unrelated
  states. A per-request limit observed lower than the maximum is written here.

Nothing in this package imports from ``tools/jev``.

Named input bounds live in the configured model entry's ``input_bounds`` mapping.
``ask_many(kinds=(...))`` uses the smallest named bound, defaults to 4,000 and
refuses invalid configuration above 12,000. Callers never provide a numeric cap.
``classifier_basis()`` identifies model, endpoint and request policy without
reading a credential; the engine uses it to invalidate local answer reuse.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import time
from types import MappingProxyType
from typing import Any, Callable, Mapping

# The one central denial set. An owner-directed change to the denials edits these two
# constants and their tests, and nothing structural. The data-collection denial is sent
# on every request; the zero-data-retention preference is not sent, because the route's
# one endpoint does not offer zero data retention.
REQUIRED_DENIALS: Mapping[str, Any] = MappingProxyType({'data_collection': 'deny'})
REFUSED_ENTRY_KEYS: frozenset[str] = frozenset({'zdr'})

MODEL_ROLE = 'cycle_classifier'
EXPECTED_SERVED_MODEL = 'openai/gpt-6-luna-decisions'
CALL_TIMEOUT_SECONDS = 20.0
OPERATION_DEADLINE_SECONDS = 60.0
MAX_RETRIES = 1
MAX_STATE_CHARS = 4_000
MAX_CONFIGURED_STATE_CHARS = 12_000
STATE_PLUS_LONGEST_QUESTION_TOKENS = 32_000
STATE_PLUS_ALL_QUESTIONS_TOKENS = 64_000
INSUFFICIENT_INFORMATION = 'insufficient-information'
# The central batching configuration (IDR luna-classification-expansion approach 2).
MAX_QUESTIONS_PER_REQUEST = 8
REQUEST_CONCURRENCY = 3

# Outcome statuses. `answered` carries a choice; every other status is a fallback, and
# the status string is the value recorded in a classification entry's `fallback`.
ANSWERED = 'answered'
FALLBACKS = (
    'refusal',               # the answer's type is `refusal`; no retry
    'malformed',             # schema deviation, unknown answer type, noul answer, unrecognised 4xx; no retry
    'malformed:served-model',  # served model differs from EXPECTED_SERVED_MODEL; no retry
    'malformed:http-401',    # 401; no retry
    'malformed:http-403',    # 403; no retry
    'no-endpoint',           # gateway message names the data policy, zero data retention or no matching endpoint; no retry
    'timeout',               # after the one retry
    'unavailable',           # 5xx, 429 or connection failure after the one retry; or the deadline left no time, with no call
    'unconfigured',          # role missing or empty, registry entry unusable, or credential missing; no request built
    'over-input-bound',      # rendered state over MAX_STATE_CHARS; no request built
    'over-token-ceiling',    # estimate over a token ceiling; no request built
    'scan-match',            # the secret scan matched; nothing sent
    'scan-failure',          # the scanner failed to import or raised; nothing sent
)


@dataclass
class Deadline:
    """The per-operation deadline that every classification call in one operation shares."""

    seconds: float = OPERATION_DEADLINE_SECONDS
    clock: Callable[[], float] = time.monotonic
    started: float | None = None

    def __post_init__(self):
        if self.started is None:
            self.started = self.clock()

    def remaining(self) -> float:
        return max(0.0, self.seconds - (self.clock() - self.started))

    def call_timeout(self) -> float:
        """The lesser of the per-call timeout and the time left."""
        return min(CALL_TIMEOUT_SECONDS, self.remaining())


@dataclass(frozen=True)
class ChoiceQuestion:
    """One choice question. `options` maps each option id to its description, in order."""

    instructions: str
    options: Mapping[str, str]


@dataclass(frozen=True)
class PredicateQuestion:
    """One independent yes/no property. Sent as a choice of `yes`, `no` and any `extra` options, in that order."""

    instructions: str
    yes: str
    no: str
    extra: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True)
class ScoreQuestion:
    """An ordering of candidates, used only to pick at most `keep` of them.

    Sent as one yes/no choice per candidate; the outcome's `selected` holds the yes candidates in
    candidate order, at most `keep`."""

    instructions: str
    candidates: Mapping[str, str]
    keep: int


@dataclass(frozen=True)
class Outcome:
    """The result of `ask`. Exactly one of `choice` (status `answered`) and a fallback status."""

    status: str
    choice: str | None = None
    probabilities: Mapping[str, float] | None = None
    confidence: float | None = None
    request_id: str | None = None     # null when no request was sent
    served_model: str | None = None   # null when unobserved
    served_provider: str | None = None  # the serving provider the response names; null when unobserved
    http_status: int | None = None
    attempts: int = 0                 # requests actually sent: 0, 1 or 2
    usage: Mapping[str, Any] | None = None
    selected: tuple[str, ...] | None = None   # a score question's kept candidates; None for other types

    @property
    def answered(self) -> bool:
        return self.status == ANSWERED


@dataclass(frozen=True)
class Status:
    configured: bool
    reason: str | None = None   # a short code such as `role-missing`, `credential-missing`, `registry-entry-invalid`


def classifier_status() -> Status:
    from .transport import classifier_status as impl
    return impl()


def ask_many(state: Mapping[str, Any], questions: Mapping[str, Any], *, deadline: Deadline,
             client: Any = None, kinds: tuple[str, ...] = ()) -> dict[str, Outcome]:
    from .transport import ask_many as impl
    return impl(state, questions, deadline=deadline, client=client, kinds=kinds)


def input_bound(kinds: tuple[str, ...] = ()) -> int:
    """The smallest centrally configured bound of the named kinds, defaulting to 4,000."""
    from .transport import input_bound as impl
    return impl(kinds)


def classifier_basis() -> dict[str, Any] | None:
    """Credential-free model, endpoint and request-policy identity for local reuse checks."""
    from .transport import classifier_basis as impl
    return impl()


def ask(state: Mapping[str, Any], question_id: str, question: ChoiceQuestion, *, deadline: Deadline,
        client: Any = None) -> Outcome:
    from .transport import ask as impl
    return impl(state, question_id, question, deadline=deadline, client=client)


__all__ = [
    'ANSWERED', 'CALL_TIMEOUT_SECONDS', 'ChoiceQuestion', 'Deadline', 'EXPECTED_SERVED_MODEL', 'FALLBACKS',
    'INSUFFICIENT_INFORMATION', 'MAX_CONFIGURED_STATE_CHARS', 'MAX_QUESTIONS_PER_REQUEST', 'MAX_RETRIES', 'MAX_STATE_CHARS', 'MODEL_ROLE',
    'OPERATION_DEADLINE_SECONDS', 'Outcome', 'PredicateQuestion', 'REFUSED_ENTRY_KEYS', 'REQUEST_CONCURRENCY', 'ScoreQuestion', 'REQUIRED_DENIALS', 'STATE_PLUS_ALL_QUESTIONS_TOKENS', 'STATE_PLUS_LONGEST_QUESTION_TOKENS', 'Status', 'ask', 'ask_many',
    'classifier_basis', 'classifier_status', 'input_bound',
]
