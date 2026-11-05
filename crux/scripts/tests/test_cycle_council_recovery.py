"""Council ownership covers claims and persistence; process death permits counted recovery."""
import contextlib
import fcntl
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_council as council
import cycle_commit
import council_policy as policy
from cycle_workflow import CycleError, atomic, tree
import test_cycle_council as fixtures
from test_cycle_commit import CommitBase


class AttemptRecoveryTests(unittest.TestCase):
    setUp = fixtures.ModeAwareCouncilTests.setUp

    def claim(self, progress=None):
        return council.begin_mode(self.root, 'consultation', 'adrs/subject.txt', 'Judge this proposal.',
                                  identity='recovery-fixture', progress=progress)

    def relative(self, path):
        return path.relative_to(self.docs).as_posix()

    def test_await_refreshes_a_running_row_after_the_owner_finishes_during_probe(self):
        cfg,path,attempt,_=self.claim()
        original=council.probe_attempt
        def complete_before_probe(*args):
            council.finish_mode(cfg,path,attempt,council.base_record(cfg,path,attempt))
            return original(*args)
        with patch.object(council,'probe_attempt',side_effect=complete_before_probe):
            result=council.await_attempt(self.root,self.relative(path),1)
        self.assertEqual(result['status'],'finished')
        self.assertNotEqual(result['outcome'],'recovery-required')

    def test_legacy_terminal_without_a_lock_keeps_its_original_reader_protocol(self):
        path=self.docs/'adrs/councils/attempt-legacy.json'
        atomic(path,{'status':'finished','record':None})
        before=path.read_bytes()
        result=council.await_attempt(self.root,self.relative(path),1)
        self.assertEqual((result['status'],result['outcome']),('finished','finished'))
        self.assertEqual(path.read_bytes(),before)
        self.assertFalse(path.with_suffix('.lock').exists())

    def test_free_flock_without_result_is_interrupted_and_next_attempt_keeps_count(self):
        cfg, path, attempt, data = self.claim()
        recovered = council.recover(self.root, self.relative(path))
        self.assertEqual(recovered['status'], 'interrupted')
        council.validate_mode_schema(recovered, 'cycle-council-attempt')
        self.assertEqual(recovered['id'], attempt['id'])
        _, _, second, _ = self.claim('The interrupted runner was recovered; proposal unchanged.')
        self.assertEqual(second['round'], 2)
        self.assertEqual(second['history'][0]['status'], 'interrupted')

    def test_retry_after_a_recovery_commit_failure_commits_without_rewriting_or_requests(self):
        _,path,_,_=self.claim();relative=self.relative(path)
        with patch.object(council,'commit_evidence',side_effect=OSError('interrupted evidence commit')):
            with self.assertRaises(OSError):council.recover(self.root,relative)
        before=path.read_bytes()
        recovered=council.recover(self.root,relative)
        self.assertEqual(recovered['status'],'interrupted')
        self.assertEqual(path.read_bytes(),before)
        dirty=subprocess.check_output(['git','-C',str(self.root),'status','--porcelain','--',str(path)],text=True)
        self.assertEqual(dirty,'')
        self.assertEqual(council.recover(self.root,relative),recovered)

    def test_retry_after_finished_result_commit_failure_retains_the_original_result(self):
        cfg,path,attempt,_=self.claim()
        with patch.object(council,'commit_evidence',side_effect=OSError('interrupted result commit')):
            with self.assertRaises(OSError):
                council.finish_mode(cfg,path,attempt,council.base_record(cfg,path,attempt))
        before=path.read_bytes()
        result=council.recover(self.root,self.relative(path))
        self.assertEqual(result['status'],'finished')
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(len(list(self.docs.rglob('council-*.json'))),1)
        output=self.docs/result['record']
        pending=subprocess.check_output(['git','-C',str(self.root),'status','--porcelain','--',str(path),str(output)],text=True)
        self.assertEqual(pending,'')

    def test_held_flock_is_reported_running_and_never_recovered(self):
        _, path, attempt, _ = self.claim()
        with path.with_suffix('.lock').open('a') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            self.assertEqual(council.probe_attempt(self.root, self.relative(path))['flock'], 'held')
            with self.assertRaisesRegex(CycleError, 'still running'):
                council.recover(self.root, self.relative(path))
        self.assertEqual(json.loads(path.read_text()), attempt)

    def test_persisted_result_recovered_without_a_new_request(self):
        cfg, path, attempt, _ = self.claim()
        record = policy.seal(council.base_record(cfg, path, attempt))
        output = path.with_name('council-' + attempt['id'] + '.json'); atomic(output, record)
        result = council.recover(self.root, self.relative(path))
        self.assertEqual(result['status'], 'finished')
        self.assertEqual(result['record'], self.relative(output))
        self.assertEqual(len(list(self.docs.rglob('attempt-*.json'))), 1)

    def test_result_with_a_conflicting_purpose_cannot_close_the_claim(self):
        cfg,path,attempt,_=self.claim()
        record=council.base_record(cfg,path,attempt);record['purpose']='adr'
        atomic(path.with_name('council-'+attempt['id']+'.json'),policy.seal(record))
        before=path.read_bytes()
        with self.assertRaisesRegex(CycleError,'another attempt'):
            council.recover(self.root,self.relative(path))
        self.assertEqual(path.read_bytes(),before)

    def test_recovery_and_late_finish_preserve_a_completed_cycles_bytes(self):
        from cycle_workflow import create
        cycle=create(self.root,'iterate','Fixture','Bounded',['src'],['Correct'],'builder','tester')
        cfg,path,attempt,_=council.begin_mode(self.root,'consultation','adrs/subject.txt','Judge.',
                                             identity='closed',cycle_id=cycle['id'])
        cycle['status']='completed';atomic(self.docs/'cycles'/cycle['id']/'cycle.json',cycle)
        before=path.read_bytes()
        with self.assertRaisesRegex(CycleError,'active cycle'):
            council.recover(self.root,self.relative(path))
        with self.assertRaisesRegex(CycleError,'closed cycle'):
            council.finish_mode(cfg,path,attempt,council.base_record(cfg,path,attempt))
        self.assertEqual(path.read_bytes(),before)

    def test_late_runner_cannot_finish_an_interrupted_attempt(self):
        cfg, path, attempt, _ = self.claim()
        council.recover(self.root, self.relative(path))
        with self.assertRaisesRegex(CycleError, 'interrupted|closed'):
            council.finish_mode(cfg, path, attempt, council.base_record(cfg, path, attempt))
        self.assertFalse(path.with_name('council-' + attempt['id'] + '.json').exists())

    def test_lock_is_taken_before_the_claim_is_persisted(self):
        acquired = []
        original = council.atomic
        def observe(path, value):
            if path.name.startswith('attempt-'):
                with path.with_suffix('.lock').open('a') as probe:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return original(path, value)
        try:
            with patch.object(council, 'atomic', side_effect=observe):
                council.begin_mode(self.root, 'consultation', 'adrs/subject.txt', 'Judge.',
                                   identity='claimed', claim_locks=acquired)
        finally:
            for fd in acquired:
                os.close(fd)

    def test_recovery_holds_flock_until_state_is_persisted(self):
        _, path, _, _ = self.claim()
        original = council.atomic
        def observe(where, value):
            if where == path:
                with path.with_suffix('.lock').open('a') as probe:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return original(where, value)
        with patch.object(council, 'atomic', side_effect=observe):
            council.recover(self.root, self.relative(path))

    def test_finish_holds_flock_through_both_persisted_files(self):
        cfg, path, attempt, _ = self.claim()
        original = council.atomic
        def observe(where, value):
            with path.with_suffix('.lock').open('a') as probe:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return original(where, value)
        with patch.object(council, 'atomic', side_effect=observe):
            council.finish_mode(cfg, path, attempt, council.base_record(cfg, path, attempt))

    def test_preallocated_attempt_id_cannot_replay_an_existing_claim(self):
        ident = 'a' * 32
        _, path, _, _ = council.begin_mode(self.root, 'consultation', 'adrs/subject.txt', 'Judge.', identity='claimed', attempt_id=ident)
        council.recover(self.root, self.relative(path))
        with self.assertRaises(CycleError):
            council.begin_mode(self.root, 'consultation', 'adrs/subject.txt', 'Judge.', identity='claimed',
                               progress='Do not overwrite the first claim', attempt_id=ident)

    def test_two_recoverers_preserve_one_interrupted_claim(self):
        _,path,attempt,_=self.claim();relative=self.relative(path)
        code='import sys;sys.path.insert(0,sys.argv[1]);from cycle_council import recover;from cycle_workflow import CycleError\ntry:print(recover(sys.argv[2],sys.argv[3])["status"])\nexcept CycleError as exc:\n if "flock is held" not in str(exc):raise\n print("held")'
        processes=[subprocess.Popen([sys.executable,'-c',code,str(Path(council.__file__).parent),str(self.root),relative],
                                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
        outcomes=[]
        for process in processes:
            out,err=process.communicate(timeout=15)
            self.assertEqual(process.returncode,0,err)
            self.assertIn(out.strip(),('interrupted','held'));outcomes.append(out.strip())
        self.assertIn('interrupted',outcomes)
        self.assertEqual(council.recover(self.root,relative)['status'],'interrupted')
        self.assertEqual((json.loads(path.read_text())['id'],len(list(self.docs.rglob('attempt-*.json')))),(attempt['id'],1))

    def test_cli_defaults_to_detached_without_running_seats_in_the_launcher(self):
        question=self.root/'q.txt';question.write_text('Judge.')
        with patch.object(fixtures.cli,'launch_detached',return_value={'outcome':'running','attempt':'claimed'}) as launch, \
             patch.object(fixtures.cli,'convene') as seats,contextlib.redirect_stdout(__import__('io').StringIO()):
            self.assertEqual(fixtures.cli.main(['--repo-root',str(self.root),'--purpose','consultation',
                                                '--subject','adrs/subject.txt','--identity','cli','--question',str(question)]),0)
        launch.assert_called_once();seats.assert_not_called()


class DetachedRunnerTests(unittest.TestCase):
    def setUp(self):
        fixtures.ModeAwareCouncilTests.setUp(self)
        self.runner_registered = False

    def register_runner(self):
        """Join only this fixture's acknowledged execution, by its lifetime flock rather than a pid."""
        if self.runner_registered:
            return
        path = self.root / 'runner.lifecycle.lock'
        with path.open('r') as stream:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.runner_registered = True
        self.addCleanup(self.join_runner)

    def join_runner(self):
        for name in ('start.gate', 'provider.gate', 'commit.gate'):
            (self.root / name).touch()
        # The controlled child holds this fd until os._exit, after its synchronous CLI/commit tail.
        with (self.root / 'runner.lifecycle.lock').open('r') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)

    def program(self, phase='normal'):
        script=self.root/'fake-runner.py'
        scripts=Path(council.__file__).parent
        script.write_text(f'''import asyncio,fcntl,importlib.util,json,os,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,AsyncMock
sys.path.insert(0,{str(scripts)!r})
sys.path.insert(0,{str(scripts/'tests')!r})
from test_cycle_council import checkpointed_result
import cycle_council as council
if sys.argv[1:2]==['--client']:
    result=council.launch_detached({str(self.root)!r},sys.argv[2:],purpose='consultation',subject='adrs/subject.txt',identity='process-fixture',runner=[sys.executable,__file__])
    print(json.dumps(result),flush=True)
    sys.exit(0)
lifecycle=open({str(self.root/'runner.lifecycle.lock')!r},'a')
fcntl.flock(lifecycle,fcntl.LOCK_EX)
phase={phase!r}
if phase=='preclaim':os._exit(23)
if phase=='delayed':
    Path({str(self.root/'started')!r}).write_text('started')
    while not Path({str(self.root/'start.gate')!r}).exists():__import__('time').sleep(.01)
spec=importlib.util.spec_from_file_location('council_cli',{str(scripts/'cycle-council.py')!r})
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
if phase=='postcommit':
    cli.notify_runner=lambda fd,message:os._exit(24)
if phase in ('commit-tail','commit-failure'):
    original_commit=council.commit_evidence
    def controlled_commit(repo,paths,message):
        if message=='Record exact council result':
            Path({str(self.root/'commit.started')!r}).touch()
            if phase=='commit-failure':raise council.CycleError('fixture evidence commit failure')
            while not Path({str(self.root/'commit.gate')!r}).exists():__import__('time').sleep(.01)
        return original_commit(repo,paths,message)
    council.commit_evidence=controlled_commit
from crux.core.data_classes import CouncilVote,CouncilDeliberation
async def deliberate(*args):
    deadline=__import__('time').monotonic()+20
    while not Path({str(self.root/'provider.gate')!r}).exists():
        if __import__('time').monotonic()>deadline:raise RuntimeError('fixture gate was never released')
        await asyncio.sleep(.01)
    votes=[CouncilVote(model=p+'/model',provider=p,decision='APPROVE',reasoning='fixture',confidence=.9) for p in ('openai','anthropic','google')]
    return checkpointed_result(provider.call_args.args[0],CouncilDeliberation(votes=votes,consensus='UNANIMOUS_APPROVE',consensus_confidence=.9,key_agreements=[],key_disagreements=[],final_recommendation={{}}))
with patch('crux_env.get',return_value='test-gateway-credential'),patch('crux.council.async_council.validate_gate_assignment',return_value={{'openai_top':'one','anthropic_top':'two','google_top':'three'}}),patch('crux.core.llm_caller.get_model_config',return_value=SimpleNamespace(max_output_tokens=65536)),patch('crux.council.async_council.AsyncCouncil') as provider:
    provider.return_value.deliberate=AsyncMock(side_effect=deliberate)
    status=cli.main()
    sys.stdout.flush();sys.stderr.flush()
    os._exit(status)
''')
        return script

    def arguments(self):
        question=self.root/'question.txt';question.write_text('Judge the bounded fixture.')
        return ['--repo-root',str(self.root),'--purpose','consultation','--subject','adrs/subject.txt',
                '--question',str(question),'--identity','process-fixture']

    def launch(self,phase='normal'):
        result=council.launch_detached(self.root,self.arguments(),purpose='consultation',subject='adrs/subject.txt',
                                       identity='process-fixture',runner=[sys.executable,str(self.program(phase))])
        if result.get('outcome')=='running':
            self.register_runner()
        return result

    def wait_for_commit_tail(self):
        deadline=time.monotonic()+10
        while not (self.root/'commit.started').exists() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue((self.root/'commit.started').exists())

    def test_terminal_file_does_not_finish_await_while_evidence_commit_owns_flock(self):
        result=self.launch('commit-tail')
        (self.root/'provider.gate').touch()
        self.wait_for_commit_tail()
        row=json.loads((self.docs/result['attempt']).read_text())
        self.assertEqual(row['status'],'finished')
        self.assertEqual(council.probe_attempt(self.root,result['attempt'])['flock'],'held')
        self.assertEqual(council.await_attempt(self.root,result['attempt'],.02)['outcome'],'running')
        (self.root/'commit.gate').touch()
        finished=council.await_attempt(self.root,result['attempt'],10)
        self.assertEqual(finished['outcome'],'awaiting-architect')
        self.join_runner()
        record=self.docs/finished['record']
        stored=subprocess.run(['git','-C',str(self.root),'show','HEAD:'+record.relative_to(self.root).as_posix()],
                              check=True,capture_output=True).stdout
        self.assertEqual(stored,record.read_bytes())

    def test_failed_commit_tail_offers_recovery_and_preserves_original_result(self):
        result=self.launch('commit-failure')
        (self.root/'provider.gate').touch()
        self.join_runner()
        row=json.loads((self.docs/result['attempt']).read_text())
        attempt_before=(self.docs/result['attempt']).read_bytes()
        record=self.docs/row['record'];before=record.read_bytes()
        waiting=council.await_attempt(self.root,result['attempt'],1)
        self.assertEqual(waiting['outcome'],'recovery-required')
        with patch.object(council,'convene',side_effect=AssertionError('recovery cannot request new votes')):
            council.recover(self.root,result['attempt'])
        self.assertEqual(record.read_bytes(),before)
        self.assertEqual((self.docs/result['attempt']).read_bytes(),attempt_before)
        self.assertEqual(len(list(self.docs.rglob('attempt-*.json'))),1)
        self.assertEqual(council.await_attempt(self.root,result['attempt'],1)['outcome'],'awaiting-architect')

    def test_detached_returns_before_answers_and_await_reports_persisted_outcome(self):
        result=self.launch()
        self.assertEqual(result['outcome'],'running')
        self.assertFalse((self.root/'provider.gate').exists())
        self.assertEqual(council.probe_attempt(self.root,result['attempt'])['flock'],'held')
        waiting=council.await_attempt(self.root,result['attempt'],.02)
        self.assertEqual((waiting['outcome'],waiting['window_expired']),('running',True))
        (self.root/'provider.gate').touch()
        finished=council.await_attempt(self.root,result['attempt'],10)
        self.assertEqual(finished['outcome'],'awaiting-architect')
        self.assertTrue((self.docs/finished['record']).is_file())

    def test_death_before_claim_reports_absence_only_after_child_exit(self):
        result=self.launch('preclaim')
        self.assertEqual((result['outcome'],result['attempt'],result['exit_code']),('could-not-run',None,23))
        self.assertFalse(list(self.docs.rglob('attempt-*.json')))

    def test_death_after_commit_before_pipe_retains_exact_counted_claim(self):
        result=self.launch('postcommit')
        self.assertEqual((result['outcome'],result['exit_code']),('recovery-required',24))
        row=json.loads((self.docs/result['attempt']).read_text())
        self.assertEqual((row['round'],row['subject']), (1,'adrs/subject.txt'))
        recovered=council.recover(self.root,result['attempt'])
        self.assertEqual(recovered['status'],'interrupted')
        self.assertEqual(len(list(self.docs.rglob('attempt-*.json'))),1)

    def test_killed_claimed_runner_releases_flock_and_recovers_without_a_result(self):
        result=self.launch()
        os.kill(result['runner']['pid'],signal.SIGKILL)
        deadline=time.monotonic()+10
        while council.probe_attempt(self.root,result['attempt'])['flock']=='held' and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(council.probe_attempt(self.root,result['attempt'])['flock'],'not-held')
        self.assertEqual(council.recover(self.root,result['attempt'])['status'],'interrupted')
        self.assertFalse(list(self.docs.rglob('council-*.json')))

    def test_runner_survives_actual_launching_process_exit(self):
        client=subprocess.run([sys.executable,str(self.program()),'--client',*self.arguments()],
                              capture_output=True,text=True,timeout=15)
        self.assertEqual(client.returncode,0,client.stderr)
        result=json.loads(client.stdout)
        self.assertEqual(result['outcome'],'running')
        self.register_runner()
        self.assertEqual(council.probe_attempt(self.root,result['attempt'])['flock'],'held')
        (self.root/'provider.gate').touch()
        self.assertEqual(council.await_attempt(self.root,result['attempt'],10)['outcome'],'awaiting-architect')
        self.join_runner()

    def test_delayed_child_has_no_parent_written_attempt(self):
        client=subprocess.Popen([sys.executable,str(self.program('delayed')),'--client',*self.arguments()],
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(lambda: client.kill() if client.poll() is None else None)
        deadline=time.monotonic()+10
        while not (self.root/'started').exists() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue((self.root/'started').exists())
        self.register_runner()
        self.assertIsNone(client.poll())
        self.assertFalse(list(self.docs.rglob('attempt-*.json')))
        (self.root/'start.gate').touch();out,err=client.communicate(timeout=15)
        self.assertEqual(client.returncode,0,err)
        result=json.loads(out)
        (self.root/'provider.gate').touch()
        self.assertEqual(council.await_attempt(self.root,result['attempt'],10)['outcome'],'awaiting-architect')

    def test_caller_killed_before_acknowledgement_does_not_cancel_child(self):
        client=subprocess.Popen([sys.executable,str(self.program('delayed')),'--client',*self.arguments()],
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(lambda: client.kill() if client.poll() is None else None)
        deadline=time.monotonic()+10
        while not (self.root/'started').exists() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue((self.root/'started').exists())
        self.register_runner()
        client.kill();client.communicate(timeout=10)
        self.assertLess(client.returncode,0)
        (self.root/'start.gate').touch();(self.root/'provider.gate').touch()
        claims=[]
        while not claims and time.monotonic()<deadline:
            claims=list(self.docs.rglob('attempt-*.json'));time.sleep(.01)
        self.assertEqual(len(claims),1)
        relative=claims[0].relative_to(self.docs).as_posix()
        self.assertEqual(council.await_attempt(self.root,relative,10)['outcome'],'awaiting-architect')


class LockObservationTests(CommitBase):
    def test_read_only_probe_reports_stale_holder_and_preserves_it(self):
        lock = self.common_lock(); holder = {'pid': 1, 'head': self.head(), 'started_at': 'historical'}
        lock.write_text(json.dumps(holder))
        state = cycle_commit.suite_lock_state(tree(self.repo))
        self.assertEqual((state['flock'], state['holder']), ('not-held', holder))
        self.assertEqual(json.loads(lock.read_text()), holder)
        with lock.open('a') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            self.assertEqual(cycle_commit.suite_lock_state(tree(self.repo))['flock'], 'held')

    def test_index_lock_has_no_removal_route_and_is_retained(self):
        lock = self.repo / '.git/index.lock'; lock.write_text('unknown owner')
        state = cycle_commit.pending_record(self.repo, self.cid)['locks']['index']
        self.assertEqual(state['state'], 'present-owner-unknown')
        self.assertEqual(lock.read_text(), 'unknown owner')


if __name__ == '__main__':
    unittest.main()
