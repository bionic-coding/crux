"""One fixture cycle driven from Build to completion by the actions `inspect` returns alone.

Every step is an action the previous `inspect` returned, filled with the caller's values only.
The test never writes the record between steps. The Test and Review declarations (required checks,
coverage, the review report) are the low-level argv actions `inspect` offers; the test runs each
argv in process and supplies only its `caller_fills`. The receipt is executed with the test-evidence
runner; every dispatch step, advance and the finish are typed."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle
from cycle_workflow import load
from test_cycle_ops_advance import AdvanceBase, PASSING, REVIEW
from test_cycle_slice import TEXT


class ChainedTypedOperationsTests(AdvanceBase):
    def doc_of(self):
        return load(self.repo, self.cid)

    def offered(self, op, **match):
        """Inspect, then return it with the one action it offers for `op`."""
        seen = self.ok({'op': 'inspect', 'host': 'claude-code'})
        found = [a for a in seen['actions'] if a.get('request', {}).get('op') == op
                 and all(a['request'].get(k) == v for k, v in match.items())]
        offers = [a.get('request', {}).get('op') for a in seen['actions']]
        self.assertEqual(len(found), 1, f'inspect offered {offers}, not exactly one {op}')
        return seen, found[0]

    def follow(self, op, fills, **match):
        """Submit the action inspect offers for `op`, adding only the values it asks the caller to fill."""
        seen, action = self.offered(op, **match)
        self.assertEqual(sorted(action['caller_fills']), sorted(fills), f'{op} asks for {action["caller_fills"]}')
        return self.ok({**action['request'], **fills})

    def lowlevel_actions(self):
        return [a for a in self.ok({'op': 'inspect', 'host': 'claude-code'})['actions'] if 'argv' in a]

    def follow_argv(self, command, fills):
        """Run the one low-level action inspect offers, appending only the flags its caller_fills names."""
        offered = self.lowlevel_actions()
        self.assertEqual([a['argv'][6] for a in offered], [command], f'inspect offered {[a["argv"][6:] for a in offered]}')
        action = offered[0]
        self.assertEqual(action['caller_fills'], list(fills), f'{command} asks for {action["caller_fills"]}')
        argv = action['argv'][3:]
        for flag, value in fills.items():
            if flag == '--json':
                value = json.dumps(value)
            argv += [flag, value]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(argv)
        self.assertEqual(code, 0, out.getvalue())

    def test_one_task_from_inspect_to_finish(self):
        # Build: inspect offers the dispatch.
        seen = self.ok({'op': 'inspect', 'host': 'claude-code'})
        self.assertEqual((seen['phase'], seen['status']), ('build', 'active'))
        self.assertEqual([a['request']['op'] for a in seen['actions'] if 'request' in a], ['prepare-dispatch'])
        prepared = self.follow('prepare-dispatch', {'op_id': 'chain-prep-1'})

        # The default claude-code mode blocks and returns no handle: inspect offers no attach-execution.
        seen = self.ok({'op': 'inspect'})
        self.assertEqual(seen['assignments'][0]['observation'], 'reserved-unbound')
        self.assertEqual(seen['assignments'][0]['recovery'], ['await-marker', 'deliver', 'mark-lost'])
        self.assertEqual([a for a in seen['actions'] if a.get('request', {}).get('op') == 'attach-execution'], [])

        # The developer runs: a trailered commit and a result file with its end marker.
        sha = self.work(prepared)
        seen, action = self.offered('deliver', assignment=prepared['assignment'], attempt=1)
        self.assertEqual(sorted(action['caller_fills']), ['op_id', 'outcome'])
        self.assertEqual(seen['assignments'][0]['observation'], 'result-arrived')
        delivered = self.ok({**action['request'], 'op_id': 'chain-deliver-1', 'outcome': 'done', 'commits': [sha]})
        self.assertEqual((delivered['status'], delivered['untrailered_commits']), ('done', []))
        self.assertEqual(self.doc_of()['plan']['tasks'][0]['commits'], [sha])

        # Build complete: inspect offers advance to Test.
        advanced = self.follow('advance', {'op_id': 'chain-advance-1'})
        self.assertEqual(advanced['phase'], 'verify')

        # Test: inspect offers the checks declaration, then the coverage declaration, then a typed receipt-reusing advance.
        self.follow_argv('checks', {'--check': 'unit'})
        self.follow_argv('coverage', {'--json': {'affected': ['the answer'], 'checks': [{'check_id': 'unit', 'rationale': 'reads src/a.py'}],
                                                'not_selected': 'no other behavior'}})
        self.assertEqual(self.lowlevel_actions(), [])
        receipt = self.receipt(PASSING)
        advanced = self.follow('advance', {'op_id': 'chain-advance-2'})
        self.assertEqual(advanced['phase'], 'review')

        # Review: inspect offers the report record, the move is typed.
        self.follow_argv('review', {'--json': {**REVIEW, 'evidence': [receipt]}})
        self.assertEqual(self.lowlevel_actions(), [])
        advanced = self.follow('advance', {'op_id': 'chain-advance-3'})
        self.assertEqual(advanced['phase'], 'reflect')

        # Reflect: inspect no longer offers advance; it offers finish.
        seen = self.ok({'op': 'inspect'})
        self.assertEqual(seen['unmet']['completion'], [])
        self.assertEqual([a for a in seen['actions'] if a.get('request', {}).get('op') == 'advance'], [])
        finished = self.follow('finish', {'op_id': 'chain-finish-1', 'lessons': ['the chain holds'], 'remaining': ['none']})
        self.assertEqual((finished['status'], finished['completion']['tip']), ('completed', sha))
        doc = self.doc_of()
        self.assertEqual((doc['status'], doc['completion']['commits']), ('completed', [sha]))
        self.assertEqual([e['action'] for e in doc['history'] if e.get('op_id', '').startswith('chain-')],
                         ['prepare-dispatch', 'deliver', 'advance', 'advance', 'advance', 'finish'])


if __name__ == '__main__':
    unittest.main()
