"""Versioned engine and document question sets, constant text and the version-bump guard."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_classify
import cycle_questions as questions
from crux import decisions

# Each set's text digest at its current version, written from the committed text. A change to any instruction or
# option description changes the digest, so this table forces the author to bump `version` and record the new digest.
PINNED = {
    'public-document-relevance': ('1', 'ed03d00f76c169df61287f6a3630928acca5202ef30709a36812e09552c457b1'),
    'work-sizing': ('1', 'e203808ee6acf9f1e5365940807c1250ed4fd36e0b0b02befd0a9f88f82b3b2d'),
    'review-routing': ('2', '6f8ead535b4e2fc9813d86d54461192121b939e0e37552af6a92946ba9ca440e'),
    'finding-disposition': ('2', 'be339d86ec3da1ad3321972c98fc6be8ca62fdd07c84d368712c92314bd4f2e6'),
    'failure-routing': ('2', '93a6ea10592ccdabdba247e8e10fd8f8cf5b633655b6845200fce669701c5bd5'),
    'context-selection': ('1', '7461353c5808de6a19866cd3d5056022fb41e26d11cac70c4012aed39a95f788'),
    'handoff-completeness': ('1', 'a2363f83cee8b4cdebdaedf556bdd85f6bf133352a5bc1642771812b26453079'),
    'review-finding-grouping': ('1', 'b862b3663a5b884f58cc21ed5aa5709d817d5a80337b5b49e7f29aef2808ba42'),
    'focused-test-ranking': ('1', 'c324a3c648e6afa16327a09399ef9cca5c65c5ff62c3e4abc853cd65c0f74a94'),
}


def text_digest(qset):
    fields = {'instructions': qset.instructions, 'descriptions': dict(qset.descriptions)}
    if qset.kind in questions.PREFIX_DESCRIPTIONS:
        fields['prefix_descriptions'] = questions.PREFIX_DESCRIPTIONS[qset.kind]
    body = json.dumps(fields, sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()


class QuestionSetTests(unittest.TestCase):
    def test_sets_cover_engine_kinds_and_the_external_document_question(self):
        self.assertEqual(set(questions.QUESTION_SETS), {*cycle_classify.KINDS, 'public-document-relevance'})
        self.assertEqual(tuple(kind for kind in questions.QUESTION_SETS if kind in cycle_classify.KINDS), cycle_classify.KINDS)
        for kind, qset in questions.QUESTION_SETS.items():
            self.assertEqual(qset.kind, kind)
            self.assertIsInstance(qset.version, str); self.assertTrue(qset.version)
            self.assertTrue(qset.instructions.strip())

    def test_options_are_the_permitted_routes_then_insufficient_information(self):
        for kind, qset in questions.QUESTION_SETS.items():
            routes = list(qset.descriptions)
            built = questions.options(kind, routes[:2])
            self.assertEqual(list(built), [*routes[:2], decisions.INSUFFICIENT_INFORMATION])
            self.assertEqual(built[routes[0]], qset.descriptions[routes[0]])
            self.assertEqual(questions.INSUFFICIENT, decisions.INSUFFICIENT_INFORMATION)

    def test_question_text_comes_only_from_the_set_a_route_without_a_description_is_refused(self):
        with self.assertRaises(ValueError):
            questions.options('work-sizing', ['a route policy made up'])
        self.assertFalse(questions.route_exists('work-sizing', 'release'))
        self.assertFalse(questions.route_exists('retired-set', 'dev'))
        self.assertFalse(questions.route_exists('work-sizing', decisions.INSUFFICIENT_INFORMATION))

    def test_every_route_the_engine_can_offer_has_a_description(self):
        for ident in cycle_classify.SPECIALISTS:
            self.assertTrue(questions.route_exists('review-routing', f'add:{ident}'), ident)
        self.assertEqual({r for r in questions.QUESTION_SETS['review-routing'].descriptions if r.startswith('add:')},
                         {f'add:{i}' for i in cycle_classify.SPECIALISTS})
        self.assertEqual(set(questions.QUESTION_SETS['work-sizing'].descriptions), set(cycle_classify.sizing_types()))
        for route in ('fix-step', 'return', 'follow-up', 'agent-assessment'):
            self.assertTrue(questions.route_exists('finding-disposition', route))
        for route in ('re-dispatch', 'mark-lost', 'return', 'agent-assessment', 'stale-state-refresh', 'request-repair',
                      'owning-developer', 'environment-investigation', 'missing-evidence-request', 'acceptance-fix'):
            self.assertTrue(questions.route_exists('failure-routing', route))

    def test_a_text_change_needs_a_version_bump(self):
        self.assertEqual(set(PINNED), set(questions.QUESTION_SETS))
        for kind, (version, digest) in PINNED.items():
            qset = questions.QUESTION_SETS[kind]
            self.assertEqual((qset.version, text_digest(qset)), (version, digest), f'{kind}: bump its version when its text changes')

    def test_descriptions_carry_no_cycle_derived_text(self):
        for qset in questions.QUESTION_SETS.values():
            for text in (qset.instructions, *qset.descriptions.values()):
                self.assertNotRegex(text, r'CYC-[0-9]{4}')


if __name__ == '__main__':
    unittest.main()
