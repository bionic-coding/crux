"""A delivered child can join an active lead without rewriting execution identity."""
from copy import deepcopy
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_ops
from cycle_workflow import load, mutate
from test_cycle_ops_hooks import HookBase


class ChildLinkTests(HookBase):
    provider_helpers = False
    def setup_children(self, *, deliver=True):
        mutate(self.repo, self.cid, 'task-add', task={'id': 'base-unit', 'phase': 'build',
               'description': 'Already integrated base', 'status': 'done', 'depends_on': [],
               'expected_evidence': ['base'], 'commits': [self.base]})
        mutate(self.repo, self.cid, 'task-add', task={'id': 'child-unit', 'phase': 'build',
               'description': 'Bounded child', 'status': 'pending', 'depends_on': [], 'expected_evidence': ['commit']})
        def plan(doc):
            doc['plan']['tasks'][0]['depends_on'] = ['base-unit']
            doc['plan']['streams'] = [{'id': 'a', 'paths': ['src/a.py'], 'independent': True},
                                      {'id': 'b', 'paths': ['src/child.py'], 'independent': True}]
        self.edit(plan)
        parent = self.ok({'op': 'prepare-dispatch', 'op_id': 'link-parent-prepare', 'task_id': 'build-it',
                          'host': 'codex', 'role': 'dev-lead'})
        self.ok({'op': 'attach-execution', 'op_id': 'link-parent-attach', 'assignment': parent['assignment'],
                 'attempt': 1, 'handle': 'lead-native'})
        child = self.ok({'op': 'prepare-dispatch', 'op_id': 'link-child-prepare', 'task_id': 'child-unit',
                         'host': 'codex', 'role': 'developer'})
        if deliver:
            (self.repo / 'src/child.py').write_text('answer = 3\n')
            self.git('add', 'src/child.py')
            self.git('commit', '-q', '-m', 'Bounded child\n\nCycle-Task: child-unit')
            self.write_result(child)
            self.ok({'op': 'deliver', 'op_id': 'link-child-deliver', 'assignment': child['assignment'],
                     'attempt': 1, 'outcome': 'done', 'commits': [self.git('rev-parse', 'HEAD')]})
        return parent

    def test_link_keeps_active_identity_and_replays(self):
        parent = self.setup_children()
        before = load(self.repo, self.cid)
        original = deepcopy(before['assignments'][0])
        request = {'op': 'child-link', 'op_id': 'link-completed-child', 'assignment': parent['assignment'],
                   'attempt': 1, 'child_task': 'child-unit'}
        self.ok(request)
        after = load(self.repo, self.cid)
        self.assertEqual(after['assignments'][0], original)
        task = after['plan']['tasks'][0]
        self.assertEqual(task['status'], 'active')
        self.assertEqual(task['integrates'], ['base-unit', 'child-unit'])
        self.assertEqual(task['depends_on'], ['base-unit', 'child-unit'])
        self.assertEqual(after['plan']['scope'], before['plan']['scope'])
        self.assertTrue(self.ok(request)['replayed'])

    def test_unfinished_child_is_refused_without_mutation(self):
        parent = self.setup_children(deliver=False)
        self.refused({'op': 'child-link', 'op_id': 'link-unfinished-child', 'assignment': parent['assignment'],
                      'attempt': 1, 'child_task': 'child-unit'}, 'child-integration-ineligible')

    def test_dependency_cycle_is_refused(self):
        parent = self.setup_children()
        self.edit(lambda doc: next(t for t in doc['plan']['tasks'] if t['id'] == 'child-unit').update(depends_on=['build-it']))
        self.refused({'op': 'child-link', 'op_id': 'link-recursive-child', 'assignment': parent['assignment'],
                      'attempt': 1, 'child_task': 'child-unit'}, 'dependency-cycle')
