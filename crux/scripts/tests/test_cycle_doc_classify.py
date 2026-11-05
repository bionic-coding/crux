"""Exact release-prep binding and atomic text-free document classification records."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_doc_classify as sink_api
from crux import decisions
from cycle_workflow import create, load, mutate
import test_cycle_commit as fixture

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ('# Document\n\nIntro stays.\n\n## Upload\n\nUpload uses Bronze protocol.\n\n'
          '## Operations\n\nOperations depends on Upload and Bronze.\n\n## Notes\n\nUnrelated notes remain.\n')


class SinkBase(fixture.CommitBase):
    def setUp(self):
        super().setUp()
        for patcher in (mock.patch.object(decisions, 'classifier_status', return_value=decisions.Status(True)),
                        mock.patch('crux.decisions.transport._credential', side_effect=AssertionError('no live credentials'))):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.release_id = create(self.repo, 'release', 'Release fixture', 'Prep docs',
                                 ['README.md', 'public'], ['docs'], 'developer', 'commander', release_list='beta')['id']
        (self.repo / 'README.md').write_text(SOURCE)
        (self.repo / 'public').mkdir()
        (self.repo / 'public/README.md').write_text('prior rendition\n')
        self.git('add', '-A')
        self.git('commit', '-qm', 'release fixture')

    def diagnostic(self, **changes):
        return {'kind': sink_api.KIND, 'question_version': '1', 'section': 'section-2', 'input_sha256': 'a' * 64,
                'question_ids': ['section-2'], 'answer': 'copy', 'probabilities': {'copy': 0.9, 'regenerate': 0.1},
                'route': 'copy', 'fallback': None, 'model_role': decisions.MODEL_ROLE,
                'model': decisions.EXPECTED_SERVED_MODEL, 'configuration_reason': None, 'request_id': 'fixture-request-1',
                'served_model': decisions.EXPECTED_SERVED_MODEL, 'served_provider': 'OpenAI', 'http_status': 200,
                'attempts': 1, 'cost': {'cost': 0.01}, **changes}


class DocumentSinkTests(SinkBase):
    def test_records_in_the_exact_cycle_with_request_identity_and_provenance_but_no_state(self):
        unrelated = load(self.repo, self.cid)
        sink = sink_api.bind(self.repo, self.release_id, 'README')
        result = sink.record([self.diagnostic()])
        doc = load(self.repo, self.release_id)
        entry = doc['classifications'][0]
        self.assertEqual(result['cycle'], self.release_id)
        self.assertEqual(entry['request_id'], 'fixture-request-1')
        self.assertEqual(entry['question_ids'], ['section-2'])
        self.assertEqual(entry['question_version'], '1')
        self.assertEqual(entry['served_model'], decisions.EXPECTED_SERVED_MODEL)
        self.assertEqual(entry['answer']['choice'], 'copy')
        self.assertEqual(entry['route'], 'copy')
        self.assertIsNone(entry['fallback'])
        self.assertRegex(entry['fingerprint'], r'^[0-9a-f]{64}$')
        provenance = next(e for e in doc['history'] if e['action'] == 'public-doc-classified')
        self.assertEqual(provenance['inputs']['source']['path'], 'README.md')
        self.assertEqual(provenance['inputs']['source']['sha256'], hashlib.sha256(SOURCE.encode()).hexdigest())
        self.assertEqual(provenance['indexes'], [0])
        self.assertNotIn('Bronze protocol', json.dumps(doc))
        self.assertEqual(load(self.repo, self.cid), unrelated)
        self.assertFalse(sink.record([self.diagnostic()])['record_commit']['changed'])
        self.assertEqual(len(load(self.repo, self.release_id)['classifications']), 1)

    def test_replay_changes_no_revision_and_interruption_retry_reuses_the_answer(self):
        sink = sink_api.bind(self.repo, self.release_id, 'README')
        sink.record([self.diagnostic()])
        revision = load(self.repo, self.release_id)['revision']
        replay = sink.record([self.diagnostic()])
        self.assertTrue(replay['replayed'])
        self.assertEqual(load(self.repo, self.release_id)['revision'], revision)
        resumed = sink_api.bind(self.repo, self.release_id, 'README')
        reused = resumed.reuse('a' * 64, ['section-2'])['section-2']
        self.assertEqual(reused['outcome'].request_id, 'fixture-request-1')
        resumed.record([self.diagnostic(reused_from=reused['reused_from'], cost=None)])
        entries = load(self.repo, self.release_id)['classifications']
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1]['reused_from']['index'], 0)
        self.assertIsNone(entries[1]['cost'])

    def test_fallback_retains_the_reason_and_conservative_action(self):
        sink = sink_api.bind(self.repo, self.release_id, 'README')
        sink.record([self.diagnostic(answer=None, route='regenerate', fallback='timeout', probabilities=None)])
        doc = load(self.repo, self.release_id)
        self.assertIsNone(doc['classifications'][0]['route'])
        self.assertEqual(doc['classifications'][0]['fallback'], 'timeout')
        self.assertEqual(doc['history'][-1]['fallback_action'], 'regenerate')
        self.assertEqual(sink.reuse('a' * 64, ['section-2']), {})

    def test_newly_validated_prep_reuses_unchanged_answer_but_old_invocation_is_stale(self):
        original = sink_api.bind(self.repo, self.release_id, 'README')
        original.record([self.diagnostic()])
        mutate(self.repo, self.release_id, 'task', task_id='prep', state='active', note='newly owned prep')
        with self.assertRaises(sink_api.SinkError):
            original.record([self.diagnostic()])
        resumed = sink_api.bind(self.repo, self.release_id, 'README')
        reused = resumed.reuse('a' * 64, ['section-2'])
        self.assertEqual(reused['section-2']['outcome'].request_id, 'fixture-request-1')

    def test_unrelated_official_paused_and_finished_prep_cycles_are_rejected(self):
        with self.assertRaises(sink_api.SinkError):
            sink_api.bind(self.repo, self.cid, 'README')
        official = create(self.repo, 'release', 'Official', 'publish', ['README.md'], ['done'],
                          'developer', 'commander', release_list='official')['id']
        with self.assertRaises(sink_api.SinkError):
            sink_api.bind(self.repo, official, 'README')
        mutate(self.repo, self.release_id, 'pause', reason='fixture pause')
        with self.assertRaises(sink_api.SinkError):
            sink_api.bind(self.repo, self.release_id, 'README')
        mutate(self.repo, self.release_id, 'resume', reason='fixture resumed')
        mutate(self.repo, self.release_id, 'task', task_id='prep', state='done', note='fixture done')
        with self.assertRaises(sink_api.SinkError):
            sink_api.bind(self.repo, self.release_id, 'README')

    def test_document_or_rendition_change_refuses_the_atomic_record(self):
        for relative in ('README.md', 'public/README.md'):
            with self.subTest(path=relative):
                path = self.repo / relative
                before = path.read_bytes()
                sink = sink_api.bind(self.repo, self.release_id, 'README')
                path.write_bytes(before + b'changed\n')
                with self.assertRaises(sink_api.SinkError):
                    sink.record([self.diagnostic()])
                self.assertEqual(load(self.repo, self.release_id).get('classifications', []), [])
                path.write_bytes(before)

    def test_configuration_change_refuses_record_and_reuse(self):
        sink = sink_api.bind(self.repo, self.release_id, 'README')
        with mock.patch.object(decisions, 'classifier_basis', return_value={'changed': True}):
            with self.assertRaises(sink_api.SinkError):
                sink.record([self.diagnostic()])
            with self.assertRaises(sink_api.SinkError):
                sink.reuse('a' * 64, ['section-2'])

    def test_changed_opt_out_or_credential_presence_refuses_stale_use(self):
        sink = sink_api.bind(self.repo, self.release_id, 'README')
        sink.record([self.diagnostic()])
        with mock.patch.object(decisions, 'classifier_status', return_value=decisions.Status(False, 'credential-missing')):
            with self.assertRaises(sink_api.SinkError):
                sink.reuse('a' * 64, ['section-2'])
            disabled = sink_api.bind(self.repo, self.release_id, 'README')
            self.assertEqual(disabled.reuse('a' * 64, ['section-2']), {})
            disabled.record([self.diagnostic(answer=None, route='regenerate', fallback='unconfigured')])
        with mock.patch.object(sink_api.bionic_config, 'load_decisions_policy', return_value={'classifier': 'off'}):
            with self.assertRaises(sink_api.SinkError):
                sink.record([self.diagnostic()])
            disabled = sink_api.bind(self.repo, self.release_id, 'README')
            self.assertEqual(disabled.reuse('a' * 64, ['section-2']), {})

    def test_source_change_after_record_refuses_output_replacement(self):
        sink = sink_api.bind(self.repo, self.release_id, 'README')
        sink.record([self.diagnostic()])
        (self.repo / 'README.md').write_text(SOURCE + 'new input\n')
        callback = mock.Mock()
        with self.assertRaises(sink_api.SinkError):
            sink.write(callback)
        callback.assert_not_called()

    def test_scan_failure_refuses_a_record(self):
        sink = sink_api.bind(self.repo, self.release_id, 'README')
        with mock.patch.object(sink_api.secret_scan, 'scan_text', side_effect=RuntimeError('fixture scanner failed')):
            with self.assertRaisesRegex(sink_api.SinkError, 'scan is unavailable'):
                sink.record([self.diagnostic()])
        self.assertEqual(load(self.repo, self.release_id).get('classifications', []), [])

    def test_unknown_fields_or_secret_shape_are_refused_without_a_record(self):
        sink = sink_api.bind(self.repo, self.release_id, 'README')
        for item in (self.diagnostic(state=SOURCE), self.diagnostic(request_id='ghp_' + 'A1b2C3d4' * 5)):
            with self.assertRaises(sink_api.SinkError):
                sink.record([item])
        self.assertEqual(load(self.repo, self.release_id).get('classifications', []), [])

    def test_write_revalidates_before_replacement_and_preserves_the_retained_observation(self):
        sink = sink_api.bind(self.repo, self.release_id, 'README')
        sink.record([self.diagnostic()])
        out = self.repo / 'public/README.md'
        sink.write(lambda: out.write_text('new rendition\n'))
        self.assertEqual(out.read_text(), 'new rendition\n')
        self.assertEqual(len(load(self.repo, self.release_id)['classifications']), 1)
        with self.assertRaises(sink_api.SinkError):
            sink.write(lambda: out.write_text('stale replacement\n'))
        self.assertEqual(out.read_text(), 'new rendition\n')

    def test_failed_atomic_save_leaves_no_classification(self):
        sink = sink_api.bind(self.repo, self.release_id, 'README')
        with mock.patch.object(sink_api, 'save', side_effect=OSError('fixture write failed')):
            with self.assertRaises(sink_api.SinkError):
                sink.record([self.diagnostic()])
        self.assertEqual(load(self.repo, self.release_id).get('classifications', []), [])


@unittest.skipUnless((ROOT / 'tools/generate-public-docs.py').is_file(), 'dev repository generator is not shipped')
class BoundGeneratorWorkflowTests(SinkBase):
    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(ROOT))
        from tools.tests import test_generate_public_docs
        self.gen = test_generate_public_docs.generate_public_docs
        config = mock.patch.object(self.gen, 'get_model_config', side_effect=test_generate_public_docs.fixture_model_config)
        config.start()
        self.addCleanup(config.stop)
        digest = hashlib.sha256(SOURCE.encode()).hexdigest()
        previous = self.gen.make_fingerprint('README.md', digest, 'fixture-model', '2026-10-31')
        previous += ' ' + self.gen.basis_comment(self.gen.current_basis('readme.md', 'fixture-model')) + '\n' + SOURCE
        (self.repo / 'public/README.md').write_text(previous)
        self.git('add', '-A')
        self.git('commit', '-qm', 'document baseline')
        (self.repo / 'README.md').write_text(SOURCE.replace('Bronze protocol', 'Silver protocol'))
        self.ask_count = 0
        def answers(state, questions, **kwargs):
            self.ask_count += 1
            return {qid: decisions.Outcome('answered', choice='copy', request_id='fixture-request-1',
                    served_model=decisions.EXPECTED_SERVED_MODEL, served_provider='OpenAI') for qid in questions}
        for patcher in (mock.patch.object(self.gen, 'DEV_ROOT', self.repo),
                        mock.patch.object(self.gen, 'get_default_model', return_value='fixture-model'),
                        mock.patch.object(self.gen, 'call_model', side_effect=lambda model, prompt, **kwargs:
                            prompt.split('Start with this heading line exactly as written: ', 1)[1].split('\n', 1)[0] + '\n\nRewritten\n'),
                        mock.patch.object(decisions, 'classifier_status', return_value=decisions.Status(True)),
                        mock.patch.object(decisions, 'ask_many', side_effect=answers),
                        mock.patch('crux.decisions.transport._credential', side_effect=AssertionError('no live credentials'))):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_existing_prep_command_records_in_its_explicit_cycle_before_output(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.gen.main(['README', '--cycle', self.release_id]), 0)
        entry = load(self.repo, self.release_id)['classifications'][0]
        self.assertEqual(entry['request_id'], 'fixture-request-1')
        self.assertEqual(entry['route'], 'copy')
        self.assertEqual(self.ask_count, 1)
        self.assertIn('Rewritten', (self.repo / 'public/README.md').read_text())
        self.assertEqual(load(self.repo, self.cid).get('classifications', []), [])

    def test_standalone_command_sends_nothing_and_ambiguous_or_unrelated_cycles_refuse(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.gen.main(['README', '--cycle', self.release_id, '--cycle', self.cid]), 2)
            self.assertEqual(self.gen.main(['README', '--cycle', self.cid]), 2)
            self.assertEqual(self.gen.main(['README']), 0)
        self.assertEqual(self.ask_count, 0)
        self.assertEqual(load(self.repo, self.release_id).get('classifications', []), [])

    def test_failed_save_leaves_the_previous_public_rendition_untouched(self):
        out = self.repo / 'public/README.md'
        before = out.read_bytes()
        with mock.patch.object(sink_api, 'save', side_effect=OSError('fixture save refused')):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(self.gen.main(['README', '--cycle', self.release_id]), 1)
        self.assertEqual(out.read_bytes(), before)

    def test_bound_timeout_records_fallback_and_regenerates_the_candidate(self):
        with mock.patch.object(decisions, 'ask_many', side_effect=lambda state, questions, **kwargs: {
            qid: decisions.Outcome('timeout', attempts=2) for qid in questions}):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(self.gen.main(['README', '--cycle', self.release_id]), 0)
        doc = load(self.repo, self.release_id)
        self.assertEqual(doc['classifications'][0]['fallback'], 'timeout')
        self.assertIsNone(doc['classifications'][0]['route'])
        self.assertEqual(doc['history'][-1]['fallback_action'], 'regenerate')

    def test_interrupted_after_persistence_reuses_without_another_send_on_retry(self):
        out = self.repo / 'public/README.md'
        before = out.read_bytes()
        with mock.patch.object(self.gen, 'write_atomic', side_effect=OSError('fixture crash before replace')):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(self.gen.main(['README', '--cycle', self.release_id]), 1)
        self.assertEqual(out.read_bytes(), before)
        self.assertEqual(self.ask_count, 1)
        mutate(self.repo, self.release_id, 'task', task_id='prep', state='active', note='resumed prep ownership')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.gen.main(['README', '--cycle', self.release_id]), 0)
        self.assertEqual(self.ask_count, 1)
        entries = load(self.repo, self.release_id)['classifications']
        self.assertEqual(entries[-1]['reused_from']['index'], 0)
        self.assertEqual(entries[-1]['request_id'], 'fixture-request-1')


if __name__ == '__main__':
    unittest.main()
