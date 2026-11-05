"""Receipt matching reads only the cycle's checks, once per operation, and finds the same receipts.

`inspect` and `advance` used to read and seal-check the whole evidence store once per lookup, and a
cycle with nine declared checks paid that about eighteen times per call. The tests here pin the
replacement: a call scope parses each receipt of the cycle's checks at most once and parses no other
receipt, the scoped read finds exactly what the whole-store read finds, and `inspect` with
`summary` prints the short form while the full output keeps every field.
"""
from collections import Counter
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_ops
from cycle_workflow import load, mutate
import test_evidence as te
from test_evidence import execute
from _evidence_fixtures import variant
from test_cycle_ops_advance import AdvanceBase

CYCLE_CHECKS = ('c00', 'c01', 'c02')
ALL_CHECKS = tuple(f'c{i:02d}' for i in range(20))


def declaration(check_id):
    return {'check_id': check_id, 'command': [sys.executable, '-c', "from pathlib import Path; assert Path('src/a.py').read_text() == 'answer = 2\\n'"],
            'inputs': ['src'], 'environment': []}


def may_hold(raw, check_ids):
    """What receipts_for decides from a file's bytes: parse unless the readable check ids miss every wanted one."""
    values = te._check_id_values(raw)
    return values is None or not values.isdisjoint(check_ids)


class CountingParse:
    """Patches `test_evidence._parse` and records the receipt id of every parse."""

    def __init__(self):
        self.ids = Counter()
        self.real = te._parse

    def __call__(self, path, text):
        self.ids[Path(path).stem] += 1
        return self.real(path, text)

    def __enter__(self):
        self.patcher = patch.object(te, '_parse', self)
        self.patcher.start()
        return self

    def __exit__(self, *exc):
        self.patcher.stop()


class SyntheticStoreTests(AdvanceBase):
    """A store of 200 receipts over 20 check ids, three of which the cycle declares."""

    def setUp(self):
        super().setUp()
        self.deliver_build()
        self.ok(self.advance('advance-b1'))
        mutate(self.repo, self.cid, 'checks', checks=list(CYCLE_CHECKS))
        mutate(self.repo, self.cid, 'coverage', coverage={
            'affected': ['the answer'], 'checks': [{'check_id': c, 'rationale': 'reads src/a.py'} for c in CYCLE_CHECKS],
            'not_selected': 'no other behavior'})
        self.store = Path(os.environ['CRUX_TEST_EVIDENCE_STORE'])
        self.current = {c: execute(self.repo, declaration(c))['evidence'] for c in CYCLE_CHECKS}
        seed = self.current[CYCLE_CHECKS[0]]
        self.by_check = {c: {r['id']} for c, r in self.current.items()}
        for index in range(200 - len(CYCLE_CHECKS)):
            check = ALL_CHECKS[index % len(ALL_CHECKS)]

            def mutate_record(record, check=check, index=index):
                record['declaration']['check_id'] = check
                # Older than every executed receipt, so lookup still decides on the executed one.
                record['finished_at'] = seed['started_at'] - 1000 - index
                record['started_at'] = record['finished_at'] - 1
            made = variant(self.store, seed['id'], mutate_record)
            self.by_check.setdefault(check, set()).add(made['id'])
        self.assertEqual(sum(len(v) for v in self.by_check.values()), 200)
        self.assertEqual(len(self.by_check), 20)
        self.cycle_receipts = set().union(*(self.by_check[c] for c in CYCLE_CHECKS))

    def test_inspect_parses_only_the_cycle_checks_each_once(self):
        with CountingParse() as parses:
            seen = self.ok({'op': 'inspect'})
        self.assertEqual(seen['reusable_evidence'], [{'check_id': c, 'evidence_id': self.current[c]['id']} for c in CYCLE_CHECKS])
        self.assertEqual(set(parses.ids), self.cycle_receipts, 'every receipt of a declared check, and no other, is parsed')
        self.assertEqual(max(parses.ids.values()), 1, 'one parse per receipt per call')

    def test_the_unscoped_read_parses_the_whole_store(self):
        """The positive control: the counter sees every receipt when the whole store is read."""
        with CountingParse() as parses:
            found = te.lookup(self.repo, declaration('c00'), scoped=False)
        self.assertEqual(len(parses.ids), 200)
        self.assertEqual(found['record']['id'], self.current['c00']['id'])

    def test_scoped_and_unscoped_lookups_agree_for_every_check(self):
        for check in ALL_CHECKS:
            with self.subTest(check=check):
                scoped = te.lookup(self.repo, declaration(check))
                whole = te.lookup(self.repo, declaration(check), scoped=False)
                self.assertEqual((scoped['state'], scoped['record'] and scoped['record']['id']),
                                 (whole['state'], whole['record'] and whole['record']['id']))
                self.assertEqual(scoped['ignored'], whole['ignored'])
                self.assertEqual({r['id'] for r in te.receipts_for(self.store, {check})}, self.by_check[check])

    def test_advance_attaches_the_receipts_and_parses_only_the_cycle_checks(self):
        with CountingParse() as parses:
            done = self.ok(self.advance('advance-t1'))
        self.assertEqual(done['phase'], 'review')
        self.assertEqual(sorted(done['reused']), sorted(CYCLE_CHECKS))
        attached = {(r['check_id'], r['evidence_id'], r['use']) for r in load(self.repo, self.cid)['evidence']}
        self.assertEqual(attached, {(c, self.current[c]['id'], 'reused') for c in CYCLE_CHECKS})
        self.assertEqual(set(parses.ids), self.cycle_receipts)
        # The lookup before the lock and the validation under it each read in their own scope.
        self.assertLessEqual(max(parses.ids.values()), 2)

    def test_the_reuse_finder_parses_only_receipts_on_the_current_fingerprint(self):
        current = self.current['c00']

        def elsewhere(record):
            record['fingerprint'] = record['end_fingerprint'] = record['snapshot']['fingerprint'] = '0' * 64
            record['finished_at'] = current['started_at'] - 5000
        stale = {variant(self.store, current['id'], elsewhere)['id'] for _ in range(3)}
        with CountingParse() as parses:
            found = te.lookup(self.repo, declaration('c00'), matching_only=True)
        self.assertTrue(stale.isdisjoint(parses.ids), 'a receipt on another fingerprint is not parsed')
        with CountingParse() as control:
            full = te.lookup(self.repo, declaration('c00'))
        self.assertLessEqual(stale, set(control.ids), 'the full lookup parses them')
        self.assertEqual((found['state'], found['record']['id']), (full['state'], full['record']['id']))
        self.assertEqual(full['record']['id'], current['id'])

    def test_the_pre_lock_finder_asks_for_matching_receipts_only(self):
        modes, real = [], te.lookup
        with patch.object(te, 'lookup', lambda *a, **k: modes.append(k.get('matching_only')) or real(*a, **k)):
            self.assertEqual(set(cycle_ops.advance_lookup(self.repo, self.cid)), set(CYCLE_CHECKS))
        self.assertEqual(modes, [True] * len(CYCLE_CHECKS))

    def test_a_corrupt_receipt_of_a_declared_check_still_fails_closed(self):
        victim = next(iter(self.by_check['c01'] - {self.current['c01']['id']}))
        path = self.store / f'{victim}.json'
        record = json.loads(path.read_text())
        record['record_sha256'] = '0' * 64
        path.write_text(json.dumps(record, indent=2))
        with self.assertRaisesRegex(te.EvidenceError, victim):
            te.lookup(self.repo, declaration('c01'))
        with self.assertRaisesRegex(te.EvidenceError, victim):
            te.lookup(self.repo, declaration('c01'), scoped=False)

    def test_a_file_with_no_check_id_key_is_parsed_and_fails_closed(self):
        (self.store / ('TE-' + '0' * 32 + '.json')).write_text('{"not": "a receipt"}')
        with self.assertRaisesRegex(te.EvidenceError, 'TE-0{32}'):
            te.lookup(self.repo, declaration('c00'))

    def test_an_escaped_check_id_is_still_found(self):
        """A receipt whose bytes spell the check id with JSON escapes is parsed, not skipped."""
        seed = self.current['c00']
        made = variant(self.store, seed['id'], lambda r: r['declaration'].update(check_id='c19'))
        path = self.store / f"{made['id']}.json"
        text = path.read_text()
        path.write_text(text.replace('"c19"', '"\\u0063\\u0031\\u0039"'))
        self.assertIn(made['id'], {r['id'] for r in te.receipts_for(self.store, {'c19'})})


class CheckIdScanTests(unittest.TestCase):
    """The cheap read of a receipt's check id is exact or declines; it never names the wrong check alone."""

    def test_the_declared_value_is_read_beside_escapes_elsewhere(self):
        raw = json.dumps({'command': ['python', '-c', 'print("a\\nb")'], 'declaration': {'check_id': 'c03'}}, indent=2).encode()
        self.assertEqual(te._check_id_values(raw), {'c03'})
        self.assertFalse(may_hold(raw, {'c04'}))

    def test_a_check_id_text_inside_a_string_adds_a_candidate_and_hides_nothing(self):
        raw = json.dumps({'command': ['echo', '"check_id": "c09"'], 'declaration': {'check_id': 'c03'}}).encode()
        self.assertIn('c03', te._check_id_values(raw))
        self.assertTrue(may_hold(raw, {'c03'}))

    def test_undecidable_bytes_are_parsed(self):
        for raw in (b'{"declaration": {"\\u0063heck_id": "c03"}}', b'{"nothing": 1}', b'{"check_id": "' + b'x' * 5000 + b'"}'):
            with self.subTest(raw=raw[:40]):
                self.assertIsNone(te._check_id_values(raw))
                self.assertTrue(may_hold(raw, {'c99'}))


class AncestryTests(AdvanceBase):
    """One rev-list walk answers what a merge-base call per pair answered."""

    def commit(self, name):
        (self.repo / 'src' / name).write_text(name)
        self.git('add', 'src')
        self.git('commit', '-q', '-m', name)
        return self.git('rev-parse', 'HEAD')

    def test_the_walk_equals_the_pairwise_answer_on_a_branching_history(self):
        cfg = cycle_ops.tree(self.repo)
        first = self.commit('one')
        second = self.commit('two')
        self.git('checkout', '-q', '-b', 'side', first)
        side = self.commit('side')
        self.git('checkout', '-q', '-')
        self.git('merge', '-q', '--no-edit', 'side')
        merged = self.git('rev-parse', 'HEAD')
        commits = [first, second, side, merged, self.base]
        pairwise = {c: {o for o in commits if o != c and cycle_ops.is_ancestor(cfg, o, c)} for c in commits}
        self.assertEqual(cycle_ops.ancestry(cfg, commits), pairwise)
        self.assertEqual(pairwise[merged], {first, second, side, self.base})

    def test_an_abbreviated_or_unknown_commit_falls_back(self):
        cfg = cycle_ops.tree(self.repo)
        self.assertIsNone(cycle_ops.ancestry(cfg, [self.base[:12]]))
        self.assertIsNone(cycle_ops.ancestry(cfg, ['0' * 40]))


class SummaryTests(AdvanceBase):
    def test_summary_prints_the_short_form_and_the_full_output_is_unchanged(self):
        self.to_test()
        self.receipt()
        full = self.ok({'op': 'inspect'})
        short = self.ok({'op': 'inspect', 'summary': True})
        for name in ('revision', 'status', 'phase', 'pass', 'pass_limit', 'unmet', 'problems', 'record'):
            self.assertEqual(short[name], full[name], name)
        self.assertEqual([a.get('request') for a in short['actions']], [a.get('request') for a in full['actions']])
        self.assertTrue(short['summary'])
        self.assertNotIn('reusable_evidence', short)
        for name in ('reusable_evidence', 'assignments', 'classifier', 'head', 'test_runs', 'councils'):
            self.assertIn(name, full, name)
        self.assertLessEqual(len(json.dumps(short, indent=2)), 3 * 1024)

    def test_summary_lists_open_attempts_with_state_and_recovery(self):
        prepared = self.prepare()
        short = self.ok({'op': 'inspect', 'summary': True, 'host': 'claude-code'})
        attempts = short['open_attempts']
        self.assertEqual([(a['id'], a['state']) for a in attempts], [(prepared['assignment'], 'reserved')])
        self.assertIn('recovery', attempts[0])

    def test_summary_must_be_a_boolean(self):
        self.refused({'op': 'inspect', 'summary': 'yes'}, 'invalid-request')


class LiveStoreEquivalenceTests(unittest.TestCase):
    """The scoped read never rules out a receipt of its own check, over every receipt in the live store."""

    def setUp(self):
        store = te.git_common_store(Path(__file__).resolve().parent)
        if store is None or not store.is_dir() or not any(store.glob('TE-*.json')):
            self.skipTest('no live evidence store in this checkout')
        self.store = store

    def test_every_live_receipt_passes_the_filter_for_its_own_check(self):
        paths = sorted(self.store.glob('TE-*.json'))
        by_check = {}
        for path in paths:
            raw = path.read_bytes()
            record = te._parse(path, raw.decode())
            check = record['declaration']['check_id']
            by_check.setdefault(check, set()).add(record['id'])
            self.assertTrue(may_hold(raw, {check}), f'{path.name} would be skipped for {check}')
        # The scoped read for the cycle-sized busiest checks returns exactly the whole-store group.
        for check, ids in sorted(by_check.items(), key=lambda item: -len(item[1]))[:3]:
            with self.subTest(check=check):
                found = {r['id'] for r in te.receipts_for(self.store, {check}) if r['id'] in {p.stem for p in paths}}
                self.assertEqual(found, ids)


if __name__ == '__main__':
    unittest.main()
