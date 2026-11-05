"""Council call checkpoints preserve partial evidence without conferring approval."""
import asyncio
import json
from pathlib import Path
import sys
import subprocess
import time
import unittest
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_council as council
import test_cycle_council as fixtures
from crux.council.async_council import AsyncCouncil, AsyncCouncilConfig, validate_gate_assignment
from crux.core.llm_caller import get_model_config


class CallCheckpointTests(unittest.TestCase):
    setUp = fixtures.ModeAwareCouncilTests.setUp

    def convene(self, transport, **extra):
        with patch('crux_env.get', return_value='fixture-gateway-key'), \
                patch('crux.council.async_council.get', return_value='fixture-gateway-key'), \
                patch.dict('os.environ', {'OPENROUTER_API_KEY': 'fixture-gateway-key'}):
            return council.convene(self.root, 'consultation', 'adrs/subject.txt', 'Judge the fixture.',
                                   identity='events-fixture', transport=transport, **extra)

    def transport(self):
        models = {cfg.api_string: cfg for cfg in (get_model_config(m) for m in validate_gate_assignment().values())}
        seen = []
        def reply(request):
            payload = json.loads(request.content)
            seen.append(payload)
            cfg = models[payload['model']]
            vote = {'decision': 'APPROVE', 'confidence': .9, 'reasoning': 'Fixture evidence.', 'findings': []}
            return httpx.Response(200, json={'model': cfg.api_string, 'provider': next(iter(cfg.accepted_served_providers)),
                                          'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(vote)}}]})
        return httpx.MockTransport(reply), seen

    def test_gateway_runner_always_retains_bound_request_and_outcome_events(self):
        transport, seen = self.transport()
        with patch('crux_env.get', return_value='fixture-gateway-key'), \
                patch('crux.council.async_council.get', return_value='fixture-gateway-key'), \
                patch.dict('os.environ', {'OPENROUTER_API_KEY': 'fixture-gateway-key'}):
            output = council.convene(self.root, 'consultation', 'adrs/subject.txt', 'Judge the fixture.',
                                     identity='events-fixture', transport=transport)
        attempt = json.loads((self.docs / output['attempt']).read_text())
        self.assertIn('call_checkpoints', attempt)
        import cycle_council_events as events
        evidence = events.read(self.root, output['attempt'])
        self.assertEqual(len(seen), 3)
        self.assertEqual(len(evidence['events']), 6)
        self.assertTrue(all(call['status'] == 'known' for call in evidence['calls']))
        self.assertTrue(evidence['complete'])
        record = json.loads((self.docs / output['record']).read_text())
        self.assertEqual(record['call_evidence'], evidence)
        self.assertNotIn('fixture-gateway-key', json.dumps(evidence))

    def test_library_request_checkpoint_failure_prevents_transport(self):
        transport, seen = self.transport()
        def fail(event):
            raise OSError('private checkpoint failure fixture')
        config = AsyncCouncilConfig(gate=True, council_kind='implementation', transport=transport, on_call_event=fail)
        with patch('crux.council.async_council.get', return_value='fixture-gateway-key'), \
                patch.dict('os.environ', {'OPENROUTER_API_KEY': 'fixture-gateway-key'}):
            with self.assertRaisesRegex(Exception, 'checkpoint'):
                asyncio.run(AsyncCouncil(config).deliberate('Fixture proposal.'))
        self.assertEqual(seen, [])

    def test_recovery_view_exposes_exact_commands_without_mutation_or_provider(self):
        _, path, attempt, _ = council.begin_mode(self.root, 'consultation', 'adrs/subject.txt', 'Judge.', identity='view-fixture')
        relative = path.relative_to(self.docs).as_posix()
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file() and '.git' not in p.parts}
        with patch.object(council, 'convene', side_effect=AssertionError('inspect must not convene')):
            view = council.recovery_view(self.root, relative)
        self.assertEqual(view['subject_sha256'], attempt['subject_sha256'])
        for kind in ('probe', 'await', 'recover'):
            action = next(a for a in view['actions'] if a['kind'] == kind)
            self.assertEqual(action['argv'][-2:], ['--' + kind, relative])
            self.assertTrue(action['prerequisites'])
        after = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file() and '.git' not in p.parts}
        self.assertEqual(before, after)

    def test_request_atomic_failure_stops_calls_and_preserves_counted_diagnosis(self):
        import cycle_council_events as events
        transport, seen = self.transport()
        with patch.object(events, 'atomic_bytes', side_effect=OSError('private storage fixture detail')):
            output = self.convene(transport)
        row = json.loads((self.docs / output['attempt']).read_text())
        record = json.loads((self.docs / output['record']).read_text())
        self.assertEqual(seen, [])
        self.assertEqual((row['round'], row['status'], output['outcome']), (1, 'finished', 'could-not-run'))
        self.assertEqual(record['checkpoint_failure']['phase'], 'request')
        self.assertFalse(record['call_evidence']['complete'])
        self.assertNotIn('private storage', json.dumps(record))
        self.assertEqual(council.recover(self.root, output['attempt'])['id'], row['id'])

    def test_outcome_atomic_failure_retains_available_negative_without_retry_or_approval(self):
        import cycle_council_events as events
        from crux.core.llm_caller import get_model_config
        models = {get_model_config(m).api_string: get_model_config(m) for m in validate_gate_assignment().values()}
        seen = []
        def reply(request):
            payload = json.loads(request.content); seen.append(payload['model'])
            cfg = models[payload['model']]
            vote = {'decision': 'REQUEST_CHANGES', 'confidence': .9, 'reasoning': 'Known fixture negative.',
                    'findings': [{'id': 'F1', 'kind': 'blocking', 'dimension': 'Correctness',
                                  'safety_adjacent': False, 'text': 'Known fixture negative.'}]}
            return httpx.Response(200, json={'model': cfg.api_string, 'provider': next(iter(cfg.accepted_served_providers)),
                                          'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(vote)}}]})
        atomic = events.atomic_bytes
        def fail_outcome(path, data):
            if path.name.endswith('-outcome.json'):
                raise OSError('private outcome fixture detail')
            return atomic(path, data)
        with patch.object(events, 'atomic_bytes', side_effect=fail_outcome):
            output = self.convene(httpx.MockTransport(reply))
        record = json.loads((self.docs / output['record']).read_text())
        self.assertEqual(output['outcome'], 'could-not-run')
        self.assertEqual(record['checkpoint_failure']['phase'], 'outcome')
        self.assertEqual(record['checkpoint_failure']['available_outcome']['vote']['decision'], 'REQUEST_CHANGES')
        self.assertFalse(record['call_evidence']['complete'])
        self.assertTrue(all(seen.count(model) == 1 for model in set(seen)))
        self.assertNotIn('private outcome', json.dumps(record))
        import council_policy as policy
        self.assertEqual(policy.evaluate({**record, 'architect': {'agrees': True, 'subject_sha256': record['subject_sha256'],
                                                                'rationale': 'Fixture agreement', 'dissent': []}}), 'could-not-run')

    def test_complete_looking_aggregate_cannot_bypass_required_event_protocol(self):
        from dataclasses import asdict
        from unittest.mock import AsyncMock
        from crux.core.data_classes import CouncilVote, CouncilDeliberation
        votes = [CouncilVote(model=seat + '/fixture', provider=seat, decision='APPROVE', confidence=.9,
                             reasoning='Fixture approval.') for seat in ('openai', 'anthropic', 'google')]
        result = CouncilDeliberation(votes=votes, consensus='UNANIMOUS_APPROVE', consensus_confidence=.9,
                                     key_agreements=[], key_disagreements=[], final_recommendation={})
        transport, _ = self.transport()
        with patch('crux.council.async_council.AsyncCouncil') as fake:
            fake.return_value.deliberate = AsyncMock(return_value=result)
            output = self.convene(transport)
        self.assertEqual(output['outcome'], 'could-not-run')
        record = json.loads((self.docs / output['record']).read_text())
        self.assertEqual(record['seats'], [asdict(vote) for vote in votes])
        import council_policy as policy
        agreement = {'agrees': True, 'subject_sha256': record['subject_sha256'], 'rationale': 'Fixture approval.', 'dissent': []}
        self.assertEqual(policy.disposition(self.root, output['record'], agreement)['outcome'], 'could-not-run')

    def test_killed_process_preserves_known_negative_and_unknown_call_without_requests_on_recovery(self):
        scripts = str(Path(council.__file__).parent)
        code = '''import asyncio,json,sys
from pathlib import Path
from unittest.mock import patch
import httpx
sys.path.insert(0,sys.argv[1])
import cycle_council as council
from crux.council.async_council import validate_gate_assignment
from crux.core.llm_caller import get_model_config
root=Path(sys.argv[2]); cfgs=[get_model_config(m) for m in validate_gate_assignment().values()]
models={c.api_string:c for c in cfgs}; first=cfgs[0].api_string
async def reply(request):
 data=json.loads(request.content); cfg=models[data['model']]
 if data['model']!=first:
  (root/'inflight').touch()
  await asyncio.Event().wait()
 vote={'decision':'REQUEST_CHANGES','confidence':.9,'reasoning':'Durable negative fixture.',
       'findings':[{'id':'F1','kind':'blocking','dimension':'Correctness','safety_adjacent':False,'text':'Durable negative fixture.'}]}
 return httpx.Response(200,json={'model':cfg.api_string,'provider':next(iter(cfg.accepted_served_providers)),
  'choices':[{'finish_reason':'stop','message':{'content':json.dumps(vote)}}]})
with patch('crux_env.get',return_value='fixture-gateway-key'),patch('crux.council.async_council.get',return_value='fixture-gateway-key'),patch.dict('os.environ',{'OPENROUTER_API_KEY':'fixture-gateway-key'}):
 council.convene(root,'consultation','adrs/subject.txt','Judge fixture.',identity='events-fixture',transport=httpx.MockTransport(reply))
'''
        process = subprocess.Popen([sys.executable, '-c', code, scripts, str(self.root)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
        self.addCleanup(cleanup)
        deadline = time.monotonic() + 20
        path = None
        while time.monotonic() < deadline:
            rows = list(self.docs.rglob('attempt-*.json'))
            outcomes = list(self.docs.rglob('openai-1-outcome.json'))
            if rows and outcomes and (self.root / 'inflight').exists():
                path = rows[0]
                break
            if process.poll() is not None:
                self.fail(process.communicate()[1].decode())
            time.sleep(.01)
        self.assertIsNotNone(path, 'fixture did not reach its durable-negative/in-flight boundary')
        relative = path.relative_to(self.docs).as_posix()
        self.assertEqual(council.probe_attempt(self.root, relative)['flock'], 'held')
        process.kill(); process.communicate(timeout=10)
        self.assertLess(process.returncode, 0)
        with patch.object(council, 'convene', side_effect=AssertionError('recovery must not make requests')):
            recovered = council.recover(self.root, relative)
        self.assertEqual((recovered['status'], recovered['round']), ('interrupted', 1))
        evidence = recovered['call_evidence']
        known = [call for call in evidence['calls'] if call['status'] == 'known']
        self.assertEqual([call['vote']['decision'] for call in known], ['REQUEST_CHANGES'])
        self.assertTrue(any(call['status'] == 'unknown' for call in evidence['calls']))
        before = path.read_bytes()
        self.assertEqual(council.recover(self.root, relative)['id'], recovered['id'])
        self.assertEqual(path.read_bytes(), before)
        transport, seen = self.transport()
        second = self.convene(transport, progress='Recovered the terminated fixture; review its retained negative.')
        row = json.loads((self.docs / second['attempt']).read_text())
        self.assertEqual(row['round'], 2)
        prompt = next(message['content'] for message in seen[0]['messages'] if message['role'] == 'user')
        payload, _ = json.JSONDecoder().raw_decode(prompt[prompt.index('{'):])
        partial = next(item for item in payload['prior_reviews'] if item.get('kind') == 'historical-partial-evidence')
        self.assertEqual(partial['attempt'], relative)
        self.assertIn('Durable negative fixture.', json.dumps(partial))
        fresh = json.loads((self.docs / second['record']).read_text())
        self.assertTrue(all(vote['decision'] == 'APPROVE' for vote in fresh['seats']))
        self.assertEqual(row['history'][0]['id'], recovered['id'])

    def test_architect_action_binds_result_and_disappears_when_subject_changes(self):
        transport, _ = self.transport()
        output = self.convene(transport)
        view = council.recovery_view(self.root, output['attempt'])
        action = next(action for action in view['actions'] if action['kind'] == 'architect')
        self.assertEqual(action['argv'][-4:], ['--architect', 'PATH', '--record', output['record']])
        self.assertEqual(view['result_ref']['path'], output['record'])
        (self.docs / 'adrs/subject.txt').write_text('A changed proposal.')
        stale = council.recovery_view(self.root, output['attempt'])
        self.assertFalse(stale['subject_current'])
        self.assertNotIn('architect', [action['kind'] for action in stale['actions']])

    def test_sealed_but_stale_call_identity_cannot_be_reused(self):
        import cycle_council_events as events
        import council_policy as policy
        from cycle_workflow import CycleError, encoded
        transport, _ = self.transport()
        output = self.convene(transport)
        ref = events.read(self.root, output['attempt'])['events'][0]
        path = self.docs / ref['path']; raw = path.read_bytes()
        for field, value in (('id', 'f' * 32), ('subject_sha256', '0' * 64), ('registry_key', 'another-model'), ('call_number', True)):
            with self.subTest(field=field):
                changed = json.loads(raw); changed[field] = value
                path.write_bytes(encoded(policy.seal(changed)))
                before = path.read_bytes()
                with self.assertRaises(CycleError):
                    events.read(self.root, output['attempt'])
                self.assertEqual(path.read_bytes(), before)
        path.write_bytes(raw)

    def test_event_contents_exclude_raw_prompt_and_redact_credentials_in_vote(self):
        import cycle_council_events as events
        models = {get_model_config(m).api_string: get_model_config(m) for m in validate_gate_assignment().values()}
        def reply(request):
            cfg = models[json.loads(request.content)['model']]
            vote = {'decision': 'REQUEST_CHANGES', 'confidence': .9, 'reasoning': 'fixture-gateway-key',
                    'findings': [{'id': 'F1', 'kind': 'blocking', 'dimension': 'Correctness',
                                  'safety_adjacent': True, 'text': 'fixture-gateway-key'}]}
            return httpx.Response(200, json={'model': cfg.api_string, 'provider': next(iter(cfg.accepted_served_providers)),
                                          'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(vote)}}]})
        output = self.convene(httpx.MockTransport(reply))
        evidence = events.read(self.root, output['attempt'])
        self.assertEqual(output['outcome'], 'could-not-run')
        for ref in evidence['events']:
            raw = (self.docs / ref['path']).read_text()
            self.assertNotIn('fixture-gateway-key', raw)
            self.assertNotIn('Judge the fixture.', raw)
        self.assertTrue(any(call.get('vote', {}).get('decision') == 'REQUEST_CHANGES' for call in evidence['calls']))

    def test_review_regression_multiline_finding_does_not_erase_complete_calls(self):
        models = {get_model_config(m).api_string: get_model_config(m) for m in validate_gate_assignment().values()}
        text = 'First fixture line.\nSecond fixture line.\tTab.'
        def reply(request):
            cfg = models[json.loads(request.content)['model']]
            vote = {'decision': 'APPROVE_WITH_NITS', 'confidence': .9, 'reasoning': 'Fixture evidence.',
                    'findings': [{'id': 'N1', 'kind': 'nit', 'dimension': 'Clarity', 'safety_adjacent': False, 'text': text}]}
            return httpx.Response(200, json={'model': cfg.api_string, 'provider': next(iter(cfg.accepted_served_providers)),
                                          'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(vote)}}]})
        output = self.convene(httpx.MockTransport(reply))
        record = json.loads((self.docs / output['record']).read_text())
        self.assertEqual(output['outcome'], 'awaiting-architect')
        self.assertTrue(record['call_evidence']['complete'])
        self.assertEqual(record['seats'][0]['findings'][0]['text'], text)

    def test_review_regression_legacy_convening_retains_prior_partial_findings(self):
        import cycle_council_events as events
        case = fixtures.CouncilTests('test_configured_gate_approval_exact_bytes')
        case.setUp(); self.addCleanup(case.doCleanups)
        models = {get_model_config(m).api_string: get_model_config(m) for m in validate_gate_assignment().values()}
        first_model = get_model_config(validate_gate_assignment()['openai_top']).api_string
        phase, seen = [1], []
        def reply(request):
            data = json.loads(request.content); seen.append(data); cfg = models[data['model']]
            negative = phase[0] == 1 and data['model'] == first_model
            vote = {'decision': 'REQUEST_CHANGES' if negative else 'APPROVE', 'confidence': .9,
                    'reasoning': 'Retained legacy negative.' if negative else 'Fresh fixture approval.',
                    'findings': [{'id': 'F1', 'kind': 'blocking', 'dimension': 'Correctness', 'safety_adjacent': False,
                                  'text': 'Retained legacy negative.'}] if negative else []}
            return httpx.Response(200, json={'model': cfg.api_string, 'provider': next(iter(cfg.accepted_served_providers)),
                                          'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(vote)}}]})
        atomic = events.atomic_bytes
        def fail(path, data):
            if path.name == 'anthropic-1-outcome.json':
                raise OSError('offline legacy checkpoint fixture')
            return atomic(path, data)
        with patch('crux_env.get', return_value='fixture-gateway-key'), \
                patch('crux.council.async_council.get', return_value='fixture-gateway-key'), \
                patch.dict('os.environ', {'OPENROUTER_API_KEY': 'fixture-gateway-key'}):
            with patch.object(events, 'atomic_bytes', side_effect=fail):
                first = council.convene(case.root, 'idr', case.subject, 'Judge fixture.', cycle_id=case.doc['id'],
                                        transport=httpx.MockTransport(reply))
            self.assertEqual(first['outcome'], 'could-not-run')
            phase[0] = 2; seen.clear()
            second = council.convene(case.root, 'idr', case.subject, 'Judge the fixture again.', cycle_id=case.doc['id'],
                                     progress='Recovered the fixture and retained its negative.', transport=httpx.MockTransport(reply))
        prompt = next(message['content'] for message in seen[0]['messages'] if message['role'] == 'user')
        payload, _ = json.JSONDecoder().raw_decode(prompt[prompt.index('{'):])
        self.assertIn('Retained legacy negative.', json.dumps(payload['prior_reviews']))
        self.assertTrue(all(item['kind'] == 'historical-partial-evidence' for item in payload['prior_reviews']))
        record = json.loads((case.cfg.docs_root / second['record']).read_text())
        self.assertEqual(second['outcome'], 'approved')
        self.assertTrue(all(vote['decision'] == 'APPROVE' for vote in record['seats']))
        self.assertEqual(json.loads((case.cfg.docs_root / second['attempt']).read_text())['round'], 2)

    def approved(self):
        import council_policy as policy
        transport, _ = self.transport()
        output = self.convene(transport)
        record = json.loads((self.docs / output['record']).read_text())
        agreement = {'agrees': True, 'subject_sha256': record['subject_sha256'], 'rationale': 'Fixture agreement.', 'dissent': []}
        return output, record, agreement

    def remove_outcome(self, record):
        ref = next(ref for ref in record['call_evidence']['events'] if ref['path'].endswith('-outcome.json'))
        (self.docs / ref['path']).unlink()

    def test_review_regression_missing_event_prevents_new_architect_approval(self):
        import council_policy as policy
        from cycle_workflow import CycleError
        output, record, agreement = self.approved()
        self.remove_outcome(record)
        path = self.docs / output['record']; before = path.read_bytes()
        with self.assertRaisesRegex(CycleError, 'checkpoint'):
            policy.disposition(self.root, output['record'], agreement)
        self.assertEqual(path.read_bytes(), before)

    def test_review_regression_new_application_checks_refs_but_sealed_history_stays_valid(self):
        import council_policy as policy
        from cycle_workflow import CycleError
        output, _, agreement = self.approved()
        policy.disposition(self.root, output['record'], agreement)
        approved = council.validate_approval(self.root, output['record'], purpose='consultation', subject='adrs/subject.txt')
        self.remove_outcome(approved)
        with self.assertRaisesRegex(CycleError, 'checkpoint'):
            council.validate_approval(self.root, output['record'], purpose='consultation', subject='adrs/subject.txt')
        self.assertEqual(council.validate_record(approved, purpose='consultation', subject='adrs/subject.txt',
                                                subject_sha256=approved['subject_sha256'])['outcome'], 'approved')

    def test_review_regression_applied_adr_standing_survives_later_event_loss(self):
        import decision_policy as dp
        import council_policy as policy
        from cycle_workflow import digest, tree
        (self.docs / 'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        proposal = dp.propose(self.root, {'title': 'Fixture evidence', 'body': '# Decision\nKeep fixture evidence.\n',
            'governs': [{'domain': 'evidence', 'scope': 'tree', 'rule': 'Keep fixture evidence.', 'handle': 'keep-fixture-evidence'}]}, origin='direct')['path']
        output, _ = fixtures.ModeAwareCouncilTests.call(self, purpose='adr', subject=proposal)
        record = json.loads((self.docs / output['record']).read_text())
        policy.disposition(self.root, output['record'], {'agrees': True, 'subject_sha256': digest((self.docs / proposal).read_bytes()),
                                                       'rationale': 'Fixture agreement.', 'dissent': []})
        accepted = dp.accept(self.root, proposal, output['record'], human_approval='Offline fixture owner accepts the exact ADR.')
        self.assertEqual(accepted['standing'], 'binding')
        self.remove_outcome(record)
        before = (self.docs / proposal).read_bytes()
        dp.validate_acceptance(tree(self.root), {'path': proposal})
        self.assertEqual(dp.accept(self.root, proposal, output['record'], human_approval='Offline fixture owner accepts the exact ADR.')['standing'], 'binding')
        self.assertEqual((self.docs / proposal).read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
