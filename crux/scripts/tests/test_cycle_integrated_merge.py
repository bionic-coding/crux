"""Only deterministic conflict-free merges of sealed declared child tips are proved."""
from copy import deepcopy
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_execution
from cycle_workflow import load, tree
import test_cycle_dirty_resume as resume_fixtures
import test_cycle_slice as fixtures


class IntegratedMergeTests(fixtures.SliceBase):
    add_integrator = resume_fixtures.IntegratedChildTests.add_integrator
    def child_git(self, *args):
        return subprocess.run(['git', '-C', str(self.child), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def merged_fixture(self, *, conflict=False):
        self.add_integrator()
        directory = tempfile.TemporaryDirectory(prefix='crux-merge-child-')
        self.addCleanup(directory.cleanup)
        self.child = Path(directory.name).resolve() / 'checkout'
        self.git('worktree', 'add', '-q', '--detach', str(self.child), self.base)
        self.addCleanup(lambda: subprocess.run(['git', '-C', str(self.repo), 'worktree', 'remove', '--force',
                                                str(self.child)], capture_output=True))
        prepared = self.prepare(mode='background')
        self.ok({'op': 'attach-execution', 'op_id': 'merge-child-attach', 'assignment': 'build-it',
                 'attempt': 1, 'handle': 'isolated-child'})
        self.ok({'op': 'execution-check', 'op_id': 'merge-child-clean', 'assignment': 'build-it',
                 'attempt': 1, 'checkout': str(self.child)})
        name = 'src/a.py' if conflict else 'src/child.py'
        (self.child / name).write_text('child = 2\n')
        self.child_git('add', name)
        self.ok({'op': 'execution-check', 'op_id': 'merge-child-staged', 'assignment': 'build-it',
                 'attempt': 1, 'checkout': str(self.child), 'edited_paths': [name]})
        self.child_git('commit', '-q', '-m', 'Child source\n\nCycle-Task: build-it')
        child_sha = self.child_git('rev-parse', 'HEAD')
        self.write_result(prepared)
        self.ok({'op': 'deliver', 'op_id': 'merge-child-delivered', 'assignment': 'build-it',
                 'attempt': 1, 'outcome': 'done', 'stage': 'implemented', 'commits': [child_sha]})
        main_name = 'src/a.py' if conflict else 'src/main.py'
        (self.repo / main_name).write_text('main = 3\n')
        self.git('add', main_name); self.git('commit', '-q', '-m', 'Already integrated main stream')
        main_sha = self.git('rev-parse', 'HEAD')
        if conflict:
            done = subprocess.run(['git', '-C', str(self.repo), 'merge', '--no-ff', '--no-edit', child_sha], capture_output=True)
            self.assertNotEqual(done.returncode, 0)
            (self.repo / name).write_text('manually_resolved = 4\n')
            self.git('add', name); self.git('commit', '-q', '-m', 'Resolve conflict\n\nCycle-Task: integrator')
        else:
            self.git('merge', '--no-ff', '-m', 'Integrate declared child\n\nCycle-Task: integrator', child_sha)
        parent = {'id': 'integrator', 'task': 'integrator', 'attempt': 1,
                  'base': main_sha, 'delivery_token': 'f' * 32}
        return tree(self.repo), load(self.repo, self.cid), parent, child_sha

    def test_exact_declared_child_merge_is_proved(self):
        cfg, doc, parent, child_sha = self.merged_fixture()
        proof = cycle_execution.prove(cfg, doc, parent)
        self.assertEqual(proof['commits'][-1]['kind'], 'integrated-task-merge')
        self.assertEqual(proof['commits'][-1]['provenance']['child_parent'], child_sha)

    def test_extra_edit_and_unknown_child_refuse(self):
        cfg, doc, parent, _ = self.merged_fixture()
        unknown = deepcopy(doc)
        next(task for task in unknown['plan']['tasks'] if task['id'] == 'integrator')['integrates'] = ['other']
        with self.assertRaisesRegex(cycle_execution.ExecutionError, 'execution-foreign-source'):
            cycle_execution.prove(cfg, unknown, parent)
        (self.repo / 'src/extra.py').write_text('not_a_merge = True\n')
        self.git('add', 'src/extra.py'); self.git('commit', '--amend', '-q', '--no-edit')
        with self.assertRaisesRegex(cycle_execution.ExecutionError, 'execution-foreign-source'):
            cycle_execution.prove(cfg, doc, parent)

    def test_manual_conflict_resolution_refuses(self):
        cfg, doc, parent, _ = self.merged_fixture(conflict=True)
        with self.assertRaisesRegex(cycle_execution.ExecutionError, 'execution-foreign-source'):
            cycle_execution.prove(cfg, doc, parent)

    def test_configured_custom_merge_driver_is_not_executed(self):
        cfg, doc, parent, _ = self.merged_fixture()
        self.git('config', 'merge.custom.driver', 'false')
        with self.assertRaisesRegex(cycle_execution.ExecutionError, 'execution-foreign-source'):
            cycle_execution.prove(cfg, doc, parent)

    def test_effective_worktree_merge_driver_refuses_without_execution(self):
        (self.repo / '.gitattributes').write_text('*.py merge=custom\n')
        self.git('add', '.gitattributes')
        self.git('commit', '-q', '-m', 'Fixture merge attributes')
        self.base = self.git('rev-parse', 'HEAD')
        cfg, doc, parent, _ = self.merged_fixture(conflict=True)
        marker = self.repo / 'driver.marker'
        driver = self.repo / 'driver.py'
        driver.write_text('from pathlib import Path\nimport sys\n'
                          + f'Path({str(marker)!r}).write_text("executed")\n'
                          + 'Path(sys.argv[1]).write_text("manually_resolved = 4\\n")\n')
        self.git('config', 'extensions.worktreeConfig', 'true')
        self.git('config', '--worktree', 'merge.custom.driver',
                 shlex.quote(sys.executable) + ' ' + shlex.quote(str(driver)) + ' %A')
        local = subprocess.run(['git', '-C', str(self.repo), 'config', '--local', '--get-regexp',
                                r'^merge\..*\.driver$'], capture_output=True)
        self.assertEqual(local.returncode, 1)
        self.assertFalse(marker.exists())
        with self.assertRaisesRegex(cycle_execution.ExecutionError, 'execution-foreign-source'):
            cycle_execution.prove(cfg, doc, parent)
        self.assertFalse(marker.exists(), 'proof must refuse before invoking an effective external driver')
