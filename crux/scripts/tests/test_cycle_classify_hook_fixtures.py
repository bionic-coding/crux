"""The fixture provider keeps automatic hook questions separate from legacy scripts."""
from pathlib import Path
import sys
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from crux import decisions
from cycle_workflow import load, tree
import cycle_context
from _classify_support import ClassifyBase, answered


class ProviderAdapterTests(ClassifyBase):
    def test_automatic_questions_do_not_consume_unrelated_scripted_replies(self):
        self.replies = [answered('return')]
        question = decisions.ChoiceQuestion('optional context', {'include': 'include', 'omit': 'omit'})
        with self.engine_questions():
            result = self.scripted_many({'candidates': [{'id': 'ctx'}]}, {'ctx': question},
                                        deadline=decisions.Deadline(), kinds=('context-selection',))
        self.assertEqual(result['ctx'].choice, 'omit')
        self.assertEqual([reply.choice for reply in self.replies], ['return'])
        self.assertEqual(self.asked, [])
        self.assertEqual(len(self.auto_hook_asked), 1)
        self.assertEqual(len(self.provider_calls), 1)

    def test_fixture_reports_cite_real_evidence_before_the_marker(self):
        prepared = self.prepare()
        self.work(prepared)
        report = Path(prepared['result_path']).read_text()
        references = cycle_context.references(report)
        self.assertTrue(any(ref['kind'] == 'commit' for ref in references))
        for ref in references:
            self.assertTrue(cycle_context.resolve_reference(tree(self.repo), ref, {})['valid'])
        self.assertTrue(report.rstrip().splitlines()[-1].startswith('Result-End:'))

    def test_enabled_prepare_hook_records_answers_without_hiding_them(self):
        self.prepare()
        self.assertTrue(self.auto_hook_asked, 'actual enabled prepare hook must reach the scripted provider')
        entries = load(self.repo, self.cid).get('classifications', [])
        self.assertTrue(any(entry['kind'] == 'context-selection' for entry in entries))
        self.assertEqual(self.entries(), entries)
        self.assertEqual(self.legacy_entries(), [])

    def test_direct_new_kind_question_still_uses_its_explicit_script(self):
        self.replies = [answered('include')]
        question = decisions.ChoiceQuestion('optional context', {'include': 'include', 'omit': 'omit'})
        result = self.scripted_many({'candidates': []}, {'ctx': question}, deadline=decisions.Deadline(), kinds=('context-selection',))
        self.assertEqual(result['ctx'].choice, 'include')
        self.assertEqual(len(self.asked), 1)
        self.assertEqual(self.auto_hook_asked, [])


if __name__ == '__main__':
    unittest.main()
