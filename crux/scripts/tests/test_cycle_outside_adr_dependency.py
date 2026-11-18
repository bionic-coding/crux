"""A task may depend on an ADR that another cycle or route proposed, and starts only once that ADR is Accepted.

The cycle does not record such an ADR. The writer finds it under `adrs/` by its id, requires status
Accepted and, when its `acceptance_format` requires an acceptance receipt, a receipt that validates
against the file through `decision_policy.validate_acceptance`. An `acceptance_format` other than
`crux.adr-acceptance.v1` or none refuses, as the summaries projection refuses it; an ADR with no
`acceptance_format` is a legacy ADR read by its status alone. An ADR this cycle proposed keeps the
recorded-entry path, which `test_cycle_writer.py` covers.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_writer as pilot
import decision_policy as dp
from cycle_store import CycleError, digest, encoded, tree


class OutsideAdrDependencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        self.docs = self.repo / 'bionic'
        (self.docs / 'adrs').mkdir(parents=True)
        (self.repo / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\n')
        (self.docs / 'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 7\n')
        (self.docs / 'objectives.md').write_text('Durable decisions.\n')
        (self.repo / 'src').mkdir()
        (self.repo / 'src/value.py').write_text('value = 1\n')
        for args in (('init', '-q'), ('config', 'user.email', 't@example.invalid'), ('config', 'user.name', 'T'),
                     ('add', '.'), ('commit', '-qm', 'baseline')):
            subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)

    def plan(self, name):
        spec = {'goal': 'Implement the decision', 'scope': ['src'], 'acceptance': ['the decision holds'],
                'verification': {'checks': [{'id': 'focused', 'rationale': 'the decision'}], 'gaps': 'none'},
                'council': {'needed': False, 'reason': 'Implements an accepted decision'},
                'tasks': [{'id': 'build', 'description': 'Implement it', 'owner': 'worker', 'adr_dependencies': [name]}]}
        self.doc = pilot.create(self.repo, 'Implements a decision', 'lead', spec)

    def start(self):
        self.doc = pilot.mutate(self.repo, self.doc['id'], 'lead', self.doc['revision'], 'task',
                                SimpleNamespace(task='build', owner='worker', run=1, status='working', checkout=None, summary=None))
        return self.doc

    def record_bytes(self):
        return pilot.path_of(self.repo, self.doc['id']).read_bytes()

    def assertRefused(self, pattern):
        before = self.record_bytes()
        with self.assertRaisesRegex(CycleError, pattern):
            self.start()
        self.assertEqual(self.record_bytes(), before, 'a refused start wrote the record')

    def legacy(self, name, status, extra=''):
        path = self.docs / f'adrs/{name}-test-decision.md'
        path.write_text(f'---\nid: {name}\ntitle: Test decision\nstatus: {status}\n{extra}---\n\nBody.\n')
        return path

    def accepted(self):
        """A prospective ADR proposed outside any cycle and accepted with a council approval and the owner's words."""
        subject = dp.propose(self.repo, {'title': 'Keep durable evidence', 'body': '# Decision\n\nPreserve the evidence.\n',
                                         'governs': [{'domain': 'evidence', 'rule': 'Preserve evidence.', 'scope': 'src/',
                                                      'handle': 'preserve-evidence'}]}, origin='direct')['path']
        row = {'format': 'crux.cycle-council', 'purpose': 'adr', 'subject': subject,
               'subject_sha256': digest((self.docs / subject).read_bytes()), 'outcome': 'approved', 'cycle_id': None,
               'seats': [{'provider': p, 'decision': 'APPROVE', 'errored': False, 'findings': []} for p in ('one', 'two', 'three')]}
        row['record_sha256'] = digest(encoded(row))
        council = self.docs / 'adrs/councils/test.json'
        council.parent.mkdir(exist_ok=True)
        council.write_bytes(encoded(row))
        dp.accept(self.repo, subject, council.relative_to(self.docs).as_posix(), human_approval='Owner: accept this proposal')
        return dp.frontmatter((self.docs / subject).read_text())[0]['id'], self.docs / subject

    def test_an_accepted_adr_of_another_route_lets_the_task_start_and_records_nothing(self):
        name, _ = self.accepted()
        self.plan(name)
        self.start()
        self.assertEqual(self.doc['tasks'][0]['status'], 'working')
        self.assertNotIn('adrs', json.loads(self.record_bytes()))

    def test_a_legacy_accepted_adr_without_an_acceptance_format_lets_the_task_start(self):
        self.legacy('ADR-0003', 'Accepted')
        self.plan('ADR-0003')
        self.start()
        self.assertEqual(self.doc['tasks'][0]['status'], 'working')

    def test_a_legacy_accepted_adr_with_a_null_acceptance_format_lets_the_task_start(self):
        """A null format reads as no format, as the summaries projection reads it."""
        self.legacy('ADR-0003', 'Accepted', 'acceptance_format: null\n')
        self.plan('ADR-0003')
        self.start()
        self.assertEqual(self.doc['tasks'][0]['status'], 'working')

    def test_an_accepted_adr_with_an_unknown_acceptance_format_is_refused(self):
        for value in ('crux.adr-acceptance.v2', 'crux.adr-acceptance.V1', "''", '1', '[crux.adr-acceptance.v1]'):
            with self.subTest(value=value):
                self.legacy('ADR-0003', 'Accepted', f'acceptance_format: {value}\n')
                self.plan('ADR-0003')
                self.assertRefused('^adr-dependency-acceptance-format-unknown: task build names ADR-0003')

    def test_an_adr_that_does_not_exist_is_refused(self):
        self.plan('ADR-0042')
        self.assertRefused('^adr-dependency-unrecorded: task build names ADR-0042.*no ADR file')

    def test_an_adr_that_is_not_accepted_is_refused(self):
        self.plan('ADR-0003')
        for status in ('Proposed', 'Deprecated', 'Superseded', 'Retracted'):
            with self.subTest(status=status):
                self.legacy('ADR-0003', status)
                self.assertRefused(f'^adr-dependency-awaiting-acceptance: task build names ADR-0003, whose status is {status}')

    def test_an_accepted_status_without_its_required_acceptance_record_is_refused(self):
        self.legacy('ADR-0003', 'Accepted', 'acceptance_format: crux.adr-acceptance.v1\n')
        self.plan('ADR-0003')
        self.assertRefused('^adr-dependency-acceptance-invalid: task build names ADR-0003')

    def test_an_accepted_adr_whose_file_no_longer_matches_its_receipt_is_refused(self):
        name, path = self.accepted()
        path.write_text(path.read_text().replace('Preserve the evidence.', 'Discard the evidence.'))
        self.plan(name)
        self.assertRefused(f'^adr-dependency-acceptance-invalid: task build names {name}')

    def test_a_file_whose_id_differs_from_its_name_is_refused(self):
        path = self.docs / 'adrs/ADR-0003-test-decision.md'
        path.write_text('---\nid: ADR-0004\ntitle: Test decision\nstatus: Accepted\n---\n\nBody.\n')
        self.plan('ADR-0003')
        self.assertRefused('^adr-dependency-unrecorded: task build names ADR-0003')


if __name__ == '__main__':
    unittest.main()
