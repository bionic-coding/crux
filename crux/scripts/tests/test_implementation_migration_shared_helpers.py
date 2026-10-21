"""Shared historical proof adapters; every publication/human input here is synthetic."""
import copy
import unittest
from dataclasses import replace
import yaml
import implementation_migration as migration
import test_implementation_authority as fixtures


class RecoveryLink(unittest.TestCase):
    def setUp(self):
        f = fixtures.RecoveryView(); f.setUp(); self.addCleanup(f.doCleanups)
        self.f = f; self.root = f.root
        f.close(); self.parent = f.publish(); self.parent_proof = f.proof
        self.parent_batch = migration.load_batch(self.root, f.f.rel)
        ledger = self.root / 'docs/adrs/doctrine/reconciliations.yml'
        original = ledger.read_bytes()
        # Keep dependencies unchanged: stale-ledger preclose eligibility is a separate U17 unit.
        def unchanged(batch, path):
            ledger.write_bytes(original)
            batch['signed_dependencies'][0]['sha256'] = migration._digest(original)
            path.write_text(yaml.safe_dump(batch, sort_keys=False))
        f.prepare_successor = unchanged
        self.proof = f.successor()
        self.batch = migration.load_batch(self.root, self.proof.binding['batch']['path'])

    def validate(self, *, batch=None, proof=None, parent=None):
        before = self.f.snapshot()
        try:
            migration._validate_recovery_link(self.root,
                parent_publication=parent or self.parent, parent_proof=self.parent_proof,
                parent_batch=self.parent_batch, batch=batch or self.batch, proof=proof or self.proof)
        finally: self.assertEqual(self.f.snapshot(), before)

    def test_two_actual_closes_share_successor_checks_and_original_chain(self):
        self.validate()
        chain, proof = migration._publication_chain(self.root, migration._discover_publications(self.root))
        self.assertEqual(len(chain), 2)
        self.assertEqual(proof.binding, self.proof.binding)

    def test_wrong_parent_source_disposition_destination_and_close_order_refuse(self):
        faults = [('witness', 'path'), ('batch', 'sha256'), ('source_identities', None)]
        for key, field in faults:
            batch = copy.deepcopy(self.batch)
            if field: batch['recovery_from'][key][field] = 'wrong'
            else: batch['recovery_from'][key] = []
            with self.subTest(key=key), self.assertRaises(migration.Refused): self.validate(batch=batch)
        for key, value in (('disposition', 'enduring-architecture'),
                           ('historical_destination', {'source_adr': 'ADR-0110', 'clause_sha256': '0'*64})):
            batch = copy.deepcopy(self.batch); batch['entries'][0][key] = value
            with self.subTest(key=key), self.assertRaises(migration.Refused): self.validate(batch=batch)
        oldest = migration.cr.git(self.root, 'rev-list', '--max-parents=0', 'HEAD').stdout.decode().strip()
        with self.assertRaises(migration.Refused): self.validate(proof=replace(self.proof, proof_commit=oldest))


if __name__ == '__main__': unittest.main()
