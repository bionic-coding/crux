"""Record public-document classifications for one explicit release-prep cycle.

The generator supplies only typed diagnosis fields and complete input digests.
This engine adapter owns validation, the locked atomic write, currentness,
idempotency and reuse. It never infers a cycle or stores request state text.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import uuid

from crux import decisions
import cycle_commit
import cycle_questions
import bionic_config
import secret_scan
from cycle_workflow import CycleError, event, load, locked, now, save

KIND = 'public-document-relevance'
DOCUMENTS = {'README': ('README.md', 'public/README.md'), 'USER_GUIDE': ('USER_GUIDE.md', 'public/USER_GUIDE.md')}
HEX = re.compile(r'[0-9a-f]{64}')
SECTION = re.compile(r'section-[0-9]+')
FIELDS = frozenset(('kind', 'question_version', 'section', 'input_sha256', 'question_ids', 'answer', 'probabilities',
                    'route', 'fallback', 'model_role', 'model', 'configuration_reason', 'request_id', 'served_model',
                    'served_provider', 'http_status', 'attempts', 'cost', 'reused_from'))


class SinkError(RuntimeError):
    """The exact cycle/input binding cannot safely retain this classification."""


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _classifier_policy(root):
    if dict(decisions.REQUIRED_DENIALS) != {'data_collection': 'deny'}:
        return {'configured': False, 'reason': 'data-policy-changed'}
    try:
        if bionic_config.load_decisions_policy(root)['classifier'] == 'off':
            return {'configured': False, 'reason': 'opted-out'}
    except (bionic_config.BionicConfigError, OSError):
        return {'configured': False, 'reason': 'configuration-error'}
    status = decisions.classifier_status()
    return {'configured': status.configured, 'reason': status.reason}


def _context(doc):
    if (doc.get('schema_version') != 3 or doc.get('type') != 'release' or doc.get('release_list') != 'beta'
            or doc.get('status') != 'active' or doc.get('phase') != 'release'):
        raise SinkError('document relevance needs the exact active version-3 beta release cycle')
    prep = next((task for task in doc['plan']['tasks'] if task['id'] == 'prep'), None)
    if prep is None or prep['status'] not in ('pending', 'active'):
        raise SinkError('document relevance belongs to the owning release prep task before it is done')
    attempts = [{key: attempt.get(key) for key in ('id', 'attempt', 'delivery_token')}
                for attempt in doc.get('assignments', [])
                if attempt['task'] == 'prep' and attempt['state'] in ('reserved', 'running')]
    return {'pass': doc['pass'], 'phase': doc['phase'], 'task': 'prep', 'task_status': prep['status'], 'attempts': attempts}


def validate_cycle(repo_root, cycle_id):
    try:
        with locked(repo_root):
            return _context(load(repo_root, cycle_id))
    except (CycleError, OSError) as exc:
        raise SinkError('cannot bind the supplied release cycle: ' + str(exc)) from exc


def _file_digest(root, relative, optional=False):
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise SinkError('document inputs must be regular files within the owning repository')
    if optional and not path.exists():
        return None
    if not path.is_file():
        raise SinkError('document input is not a regular file: ' + relative)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DocumentSink:
    def __init__(self, root, cycle_id, document):
        if document not in DOCUMENTS:
            raise SinkError('only README and USER_GUIDE may classify document sections')
        self.root = Path(root).resolve()
        self.cycle_id, self.document = cycle_id, document
        self.invocation = uuid.uuid4().hex
        try:
            with locked(self.root):
                self.context = _context(load(self.root, cycle_id))
                self.inputs = self._inputs()
                self.basis = decisions.classifier_basis()
                self.policy = _classifier_policy(self.root)
                qset = cycle_questions.question_set(KIND)
                self.question = {'version': qset.version, 'instructions': qset.instructions,
                                 'options': cycle_questions.options(KIND, ('regenerate', 'copy'))}
        except (CycleError, OSError) as exc:
            raise SinkError('cannot bind document inputs: ' + str(exc)) from exc

    def _inputs(self):
        source, rendition = DOCUMENTS[self.document]
        return {'source': {'path': source, 'sha256': _file_digest(self.root, source)},
                'rendition': {'path': rendition, 'sha256': _file_digest(self.root, rendition, optional=True)}}

    def _current(self, doc):
        qset = cycle_questions.question_set(KIND)
        current_question = {'version': qset.version, 'instructions': qset.instructions,
                            'options': cycle_questions.options(KIND, ('regenerate', 'copy'))}
        if (_context(doc) != self.context or self._inputs() != self.inputs
                or decisions.classifier_basis() != self.basis or current_question != self.question
                or _classifier_policy(self.root) != self.policy):
            raise SinkError('release-prep context, document inputs or classifier policy changed; regenerate from current inputs')

    def _fingerprint(self, section, state_digest):
        return digest({'policy': 'release-document-relevance-1', 'cycle': self.cycle_id,
                       'document': self.document, 'inputs': self.inputs, 'state_sha256': state_digest,
                       'question': self.question, 'question_id': section, 'configuration': self.basis,
                       'classifier_policy': self.policy})

    def reuse(self, state_digest, question_ids):
        """Reuse only valid answers for identical question, full inputs, policy and configuration."""
        if not isinstance(state_digest, str) or not HEX.fullmatch(state_digest):
            raise SinkError('invalid document request digest')
        found = {}
        try:
            with locked(self.root):
                doc = load(self.root, self.cycle_id)
                self._current(doc)
                if not self.policy['configured']:
                    return {}
                for section in question_ids:
                    if not isinstance(section, str) or not SECTION.fullmatch(section):
                        raise SinkError('invalid document question id')
                    fingerprint = self._fingerprint(section, state_digest)
                    for index in range(len(doc.get('classifications', [])) - 1, -1, -1):
                        entry = doc['classifications'][index]
                        if (entry['kind'] == KIND and entry['fingerprint'] == fingerprint
                                and entry['fallback'] is None and entry['route'] in ('copy', 'regenerate')
                                and (entry.get('answer') or {}).get('choice') == entry['route']):
                            found[section] = {'outcome': decisions.Outcome('answered', choice=entry['route'],
                                probabilities=entry['answer'].get('probabilities'), request_id=entry['request_id'],
                                served_model=entry['served_model'], served_provider=entry.get('served_provider')),
                                'question_ids': entry['question_ids'],
                                'reused_from': entry.get('reused_from') or
                                    {'index': index, 'revision': entry['revision'], 'request_id': entry['request_id']}}
                            break
        except (CycleError, OSError) as exc:
            raise SinkError('cannot read document classifications: ' + str(exc)) from exc
        return found

    def _entry(self, item, doc, revision):
        if not isinstance(item, dict) or set(item) - FIELDS:
            raise SinkError('unsupported document diagnostic fields; request state is never retained')
        section, sha = item.get('section'), item.get('input_sha256')
        ids = item.get('question_ids')
        if (item.get('kind') != KIND or item.get('question_version') != self.question['version']
                or item.get('model_role') != decisions.MODEL_ROLE or item.get('model') != decisions.EXPECTED_SERVED_MODEL
                or not isinstance(section, str) or not SECTION.fullmatch(section)
                or not isinstance(sha, str) or not HEX.fullmatch(sha)
                or not isinstance(ids, list) or not ids or len(ids) > decisions.MAX_QUESTIONS_PER_REQUEST
                or any(not isinstance(qid, str) or not SECTION.fullmatch(qid) for qid in ids)
                or len(ids) != len(set(ids)) or section not in ids):
            raise SinkError('document diagnostic identity or question provenance is invalid')
        for key, pattern in (('request_id', r'[A-Za-z0-9._:-]{1,160}'),
                             ('served_model', r'[A-Za-z0-9._/:-]{1,200}'),
                             ('served_provider', r'[A-Za-z0-9 ._/()-]{1,100}')):
            value = item.get(key)
            if value is not None and (not isinstance(value, str) or not re.fullmatch(pattern, value)):
                raise SinkError('invalid document serving metadata')
        answer, route, fallback = item.get('answer'), item.get('route'), item.get('fallback')
        if route not in ('copy', 'regenerate'):
            raise SinkError('document route is not permitted')
        if fallback is None:
            if not self.policy['configured'] or answer not in ('copy', 'regenerate') or answer != route:
                raise SinkError('document answer does not establish its route')
        elif (fallback not in (*decisions.FALLBACKS, 'insufficient-information', 'malformed')
              or route != 'regenerate'):
            raise SinkError('document fallback must conservatively regenerate')
        cost = (item.get('cost') or {}).get('cost') if isinstance(item.get('cost'), dict) else None
        if cost is not None and (isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0):
            raise SinkError('invalid document classification cost')
        probabilities = item.get('probabilities')
        if probabilities is not None and (not isinstance(probabilities, dict)
                or set(probabilities) - set(self.question['options'])
                or any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                       or not 0 <= value <= 1 for value in probabilities.values())):
            raise SinkError('invalid document answer probabilities')
        fingerprint = self._fingerprint(section, sha)
        entry = {'kind': KIND, 'request_id': item.get('request_id'), 'question_set': KIND,
                 'question_version': self.question['version'], 'model': item['model'],
                 'served_model': item.get('served_model'), 'served_provider': item.get('served_provider'), 'cost': cost,
                 'answer': {'choice': answer, 'probabilities': probabilities} if answer in self.question['options'] else None,
                 'route': route if fallback is None else None, 'fallback': fallback,
                 'subject': self.document + ':' + section, 'fingerprint': fingerprint, 'question_ids': ids,
                 'trigger': 'public-docs:' + self.invocation, 'pass': doc['pass'], 'phase': doc['phase'],
                 'at': now(), 'revision': revision}
        previous = item.get('reused_from')
        if previous is not None:
            try:
                old = doc['classifications'][previous['index']]
                valid = (old['fingerprint'] == fingerprint and old['revision'] == previous['revision']
                         and old['request_id'] == previous['request_id'] == entry['request_id']
                         and old['fallback'] is None and old['route'] == route == answer)
            except (KeyError, TypeError, IndexError):
                valid = False
            if not valid:
                raise SinkError('reused document answer has no matching retained provenance')
            entry['reused_from'] = previous
        return entry

    def record(self, diagnostics):
        """Validate and append the batch atomically before any rendition replacement."""
        if not isinstance(diagnostics, list) or not diagnostics:
            raise SinkError('document diagnostics must be a nonempty list')
        try:
            if secret_scan.scan_text(json.dumps(diagnostics, allow_nan=False)):
                raise SinkError('document diagnostic secret scan refused persistence')
        except (TypeError, ValueError) as exc:
            raise SinkError('document diagnostics are not serializable') from exc
        except SinkError:
            raise
        except Exception as exc:
            raise SinkError('document diagnostic secret scan is unavailable') from exc
        try:
            with locked(self.root) as (cfg, _):
                doc = load(self.root, self.cycle_id)
                self._current(doc)
                revision = doc['revision'] + 1
                entries = [self._entry(item, doc, revision) for item in diagnostics]
                if len({entry['subject'] for entry in entries}) != len(entries):
                    raise SinkError('duplicate document question in one write')
                key = digest({'invocation': self.invocation, 'diagnostics': diagnostics})
                previous = next((e for e in doc['history'] if e['action'] == 'public-doc-classified' and e.get('key') == key), None)
                if previous is not None:
                    result = {'cycle': self.cycle_id, 'revision': doc['revision'], 'indexes': previous['indexes'], 'replayed': True}
                else:
                    indexes = list(range(len(doc.get('classifications', [])), len(doc.get('classifications', [])) + len(entries)))
                    doc.setdefault('classifications', []).extend(entries)
                    event(doc, 'public-doc-classified', key=key, invocation=self.invocation, document=self.document,
                          inputs=self.inputs, configuration_sha256=digest(self.basis), context=self.context,
                          classifier_policy=self.policy, indexes=indexes, fallback_action='regenerate')
                    save(cfg, doc)
                    result = {'cycle': self.cycle_id, 'revision': doc['revision'], 'indexes': indexes, 'replayed': False}
            result['record_commit'] = cycle_commit.after_write(self.root, self.cycle_id, 'public document classifications')
            return result
        except (CycleError, OSError) as exc:
            raise SinkError('document classifications were not saved: ' + str(exc)) from exc

    def write(self, callback):
        """Validate before replacement, never afterward. The atomic-write callback must call no cycle writer."""
        try:
            with locked(self.root):
                self._current(load(self.root, self.cycle_id))
                return callback()
        except (CycleError, OSError) as exc:
            raise SinkError('document output was not replaced: ' + str(exc)) from exc


def bind(repo_root, cycle_id, document):
    return DocumentSink(repo_root, cycle_id, document)
