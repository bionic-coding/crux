"""Committed replay receipts for prospective migration publications.

A prospective publication is admitted on every authority read. Admission runs the
parent commit's own approval reader in a clean clone of that parent. The run reads
only immutable inputs: a full parent commit, the approval path and the reader code
fixed at that commit. A receipt is a committed file that attests the run succeeded,
bound by hash to those inputs. A read that finds a trusted receipt with every
binding equal skips the reader run and nothing else. Every other admission check,
including the clean clone, the installed-support checks and the current reader's own
validation of the approval, still runs on every read that reaches the baseline step.

What a receipt is and is not:

* It records a success. The schema admits the result `approved` only; no refusal is
  ever written or remembered.
* It is not approval evidence. It records no approval, owner instruction or council
  verdict, cannot create or alter one, and deleting it changes no verdict wherever
  the old reader still runs in the reading environment. A trusted-receipt read does
  not observe an environment-only failure of the old reader (an interpreter or
  library that no longer runs it). That is the documented practice change: such a
  failure now surfaces when a receipt is written or verified.
* It is trusted only when it is committed, unedited since its introducing commit, and
  introduced strictly after its publication commit. Activation therefore never writes
  one. A receipt that is new, uncommitted or edited in the tree being read is
  untrusted: the read replays, and the parent reader's refusal refuses.
* Any binding mismatch, any trust-rule failure (introduced at or before the
  publication commit) and any invalid receipt file refuses with a distinct
  `CycleError`. `authority_view` maps every `CycleError` to the existing code
  `migration-authority-input-invalid`. No existing message is reworded.

Bound inputs: the publication (id, path, sha256, introducing commit), the parent
commit, the approval and package bindings, and the reader. `reader.path` is a fixed
identifier, never a filesystem path. The execution environment (interpreter,
libraries, ambient variables) is deliberately unbound. `published_objectives` is an
in-process context variable, and `_revision_environment()` carries no objectives or
owner-exception state. Objectives and the owner exception therefore reach the parent
reader only through the parent tree, which the full parent commit binds, and through
the hash-bound approval and package bytes.

For an `installed-support` reader, the imports of the installed reader that lie
outside `INSTALLED_INVENTORY`, including this module, are unbound in the same way as
the environment. Future installed-support records do not pin this module.

Scope. A receipts scope is entered by `publication_facts`. When none is active it
loads, lazily and pinned to the repository being read (the outermost tree), the
receipt of each publication it is asked about, and it closes when that
`publication_facts` returns. A nested `publication_facts` inside a clone view reuses
the active scope, keyed by the full publication identity. Trust is evaluated against
the outermost repository, never against a clone. Nothing is stored beyond the scope.
"""
from contextlib import contextmanager
from copy import deepcopy
import contextvars
import os
from pathlib import Path
import json

import adr_migration as m
from cycle_workflow import CycleError, digest, encoded, tree

FORMAT = 'crux.migration-replay-receipt.v1'
SCHEMA = 'migration-replay-receipt.schema.json'
MAX_BYTES = 65536
MISMATCH = 'migration replay receipt does not match publication inputs'
INVALID = 'migration replay receipt is invalid'
READER_PATHS = {'parent-tree': 'crux/scripts/adr-migration.py',
                'installed-support': 'scripts/adr-migration.py'}
# Receipt fields that must equal what the reading process computed.
BOUND = ('publication', 'parent', 'approval', 'package', 'reader')

_SCOPE = contextvars.ContextVar('migration_receipts_scope', default=None)
_DISABLED = contextvars.ContextVar('migration_receipts_disabled', default=False)
_RECORDER = contextvars.ContextVar('migration_receipts_recorder', default=None)


def receipts_directory(repo):
    """Repository-relative directory that holds every receipt."""
    root = Path(repo).resolve()
    return (tree(root).docs_root / 'adrs/migrations/receipts').relative_to(root).as_posix()


def receipt_path(repo, publication_id):
    return receipts_directory(repo) + '/' + m.slug(publication_id) + '.json'


def reader_binding(source, script_bytes, support=None):
    """The reader field for the script a replay executes."""
    if source not in READER_PATHS:
        raise CycleError(INVALID)
    return {'source': source, 'path': READER_PATHS[source], 'sha256': digest(script_bytes),
            'support_sha256': digest(encoded(support)) if source == 'installed-support' else None}


def build(facts):
    """The receipt for one successful replay. Deterministic: no clock, path or environment."""
    return {'format': FORMAT, **deepcopy({k: facts[k] for k in BOUND}), 'result': 'approved'}


def parse(raw):
    """Decode and schema-validate receipt bytes. Raises the invalid-receipt error."""
    try:
        value = json.loads(raw)
        validator = m._validator()
        schema = validator.load_schema(Path(__file__).resolve().parent.parent / 'schemas' / SCHEMA)
        errors = []
        validator.validate(value, schema, '#', '#', errors, 'migration-replay-receipt')
    except (ValueError, OSError, UnicodeError, KeyError, TypeError):
        raise CycleError(INVALID) from None
    if errors or not isinstance(value, dict) or value.get('format') != FORMAT:
        raise CycleError(INVALID)
    return value


def read_receipt(repo, relative):
    """Read one receipt file. None when absent. Refuses a symlink, a non-regular or oversized file."""
    if not os.path.lexists(Path(repo) / relative):
        return None
    try:
        raw = m.read(repo, relative)
        if len(raw) > MAX_BYTES:
            raise CycleError(INVALID)
    except (CycleError, OSError):
        raise CycleError(INVALID) from None
    return raw, parse(raw)


def trust(repo, relative, receipt):
    """'trusted', or 'untrusted' for a receipt that is uncommitted or edited since its introduction.

    A receipt that is committed and unedited but not introduced strictly after its
    publication commit fails the trust rule and refuses.
    """
    try:
        introduced = m.introduction(repo, relative)
    except CycleError:
        return 'untrusted'
    published = receipt['publication']['publication_commit']
    try:
        m.ancestor(repo, published, introduced)
    except CycleError:
        raise CycleError(MISMATCH) from None
    if introduced == published:
        raise CycleError(MISMATCH)
    return 'trusted'


class _Scope:
    def __init__(self, repo):
        self.repo = Path(repo).resolve()
        self.entries = {}

    def entry(self, publication_id):
        if publication_id not in self.entries:
            self.entries[publication_id] = self._load(publication_id)
        return self.entries[publication_id]

    def _load(self, publication_id):
        relative = receipt_path(self.repo, publication_id)
        try:
            found = read_receipt(self.repo, relative)
        except CycleError:
            return {'error': True}
        if found is None:
            return None
        return {'error': False, 'path': relative, 'receipt': found[1], 'trust': None}


@contextmanager
def scope(repo):
    """Open the receipts scope for the outermost repository being read; nested calls reuse it."""
    if _SCOPE.get() is not None:
        yield
        return
    token = _SCOPE.set(_Scope(repo))
    try:
        yield
    finally:
        _SCOPE.reset(token)


@contextmanager
def disabled():
    """Ignore every receipt for the whole operation (writer and verification replay)."""
    token = _DISABLED.set(True)
    try:
        yield
    finally:
        _DISABLED.reset(token)


@contextmanager
def recording():
    """Collect the facts of each replay that ran, keyed by publication id."""
    box = {}
    token = _RECORDER.set(box)
    try:
        yield box
    finally:
        _RECORDER.reset(token)


def consult(facts):
    """True when a trusted receipt with every binding equal lets the caller skip the reader run.

    False means replay: no receipt, no active scope, or an untrusted receipt whose
    bindings are all equal. A binding mismatch, a trust-rule failure and an invalid
    receipt file raise `CycleError`.
    """
    active = _SCOPE.get()
    if active is None or _DISABLED.get():
        return False
    entry = active.entry(facts['publication']['id'])
    if entry is None:
        return False
    if entry['error']:
        raise CycleError(INVALID)
    receipt = entry['receipt']
    if any(receipt[key] != facts[key] for key in BOUND):
        raise CycleError(MISMATCH)
    if entry['trust'] is None:
        # The outermost repository decides, once; a failure is raised every time.
        entry['trust'] = trust(active.repo, entry['path'], receipt)
    return entry['trust'] == 'trusted'


def replayed(facts):
    """Report that the parent reader ran and accepted these inputs."""
    box = _RECORDER.get()
    if box is not None:
        box[facts['publication']['id']] = deepcopy(facts)
