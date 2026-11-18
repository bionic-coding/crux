"""`suite_evidence._changelog_tokens` rereads the changelog tokens after a transient head change.

A commit that lands while ``implementation_migration.changelog_citation_tokens`` walks the history makes the
walk refuse ``migration-history-head-changed``. The registered declarations would then lose their CHANGELOG.md
projection and read the whole file. The reader runs again on that refusal, at most ``CHANGELOG_TOKEN_READS``
reads in all; a refusal that keeps coming keeps the ``{}`` fallback, and another refusal code is not reread.

Every seeded commit lands through a deterministic hook on the walk's own head check, in a temporary repository,
never by timing and never in the checkout that runs the tests. Each case pairs with a positive control that
shows the fixture reaches the behaviour the case asserts.
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _council_gate_support as sup
from _classifier_isolation import isolate_classifier
import implementation_migration as migration
import suite_evidence
import test_implementation_migration_shared_reads as shared

CHANGELOG = "# Changelog\n\n## [3.10.0] — 2026-08-01\n\nrule:rotation\n"
HEAD_CHANGED = "migration-history-head-changed"


class SeededCommits:
    """Lands ``count`` empty commits in ``root``, one inside each history walk's head check, then stops.

    The hook wraps ``_InvocationHistory.unchanged_head``: the commit lands after the walk read HEAD and before
    the walk compares it, which is the race the reader rereads on.
    """

    def __init__(self, root, count):
        self.root, self.left, self.landed = root, count, 0
        self.real = migration._InvocationHistory.unchanged_head

    def __enter__(self):
        hook = self

        def unchanged_head(history):
            if hook.left:
                hook.left -= 1
                hook.landed += 1
                sup.git(hook.root, "commit", "-q", "--allow-empty", "-m", f"seeded commit {hook.landed}")
            return hook.real(history)

        self.patcher = patch.object(migration._InvocationHistory, "unchanged_head", unchanged_head)
        self.patcher.start()
        return self

    def __exit__(self, *exc):
        self.patcher.stop()


class PublishedBatch(unittest.TestCase):
    """A temporary repository whose published migration batch binds CHANGELOG.md."""

    prepare = shared.CitationKinds.prepare

    def setUp(self):
        isolate_classifier(self)
        shared.CitationKinds.setUp(self)
        self.prepare(CHANGELOG)
        self.f.witness.write_text('{"synthetic": "discovery only"}\n')
        sup.commit_all(self.root, "a published batch that binds CHANGELOG.md")


class ChangelogTokenReadTests(PublishedBatch):
    def setUp(self):
        super().setUp()
        self.tokens = suite_evidence._changelog_tokens(self.root)
        self.assertTrue(self.tokens.get("CHANGELOG.md"), "the fixture certifies a CHANGELOG.md token set")

    def test_the_seeded_commit_alone_makes_the_strict_reader_refuse(self):
        # Positive control for the hook: the commit lands inside the walk and the reader refuses on it.
        with SeededCommits(self.root, 1) as seeded, self.assertRaises(migration.ap.Refused) as raised:
            migration.changelog_citation_tokens(self.root)
        self.assertEqual(raised.exception.code, HEAD_CHANGED)
        self.assertEqual(seeded.landed, 1)

    def test_one_transient_head_change_is_read_again_and_keeps_the_tokens(self):
        with SeededCommits(self.root, 1) as seeded:
            found = suite_evidence._changelog_tokens(self.root)
        self.assertEqual(seeded.landed, 1)
        self.assertEqual(found, self.tokens)

    def test_without_the_reread_one_head_change_loses_the_tokens(self):
        # Positive control: with one read allowed, the same single seeded commit drops to the fallback.
        with patch.object(suite_evidence, "CHANGELOG_TOKEN_READS", 1), SeededCommits(self.root, 1) as seeded:
            found = suite_evidence._changelog_tokens(self.root)
        self.assertEqual(seeded.landed, 1)
        self.assertEqual(found, {})

    def test_a_head_change_on_every_read_keeps_the_empty_fallback(self):
        # The reread is bounded: a head change on each of the CHANGELOG_TOKEN_READS reads keeps the fallback.
        reads = suite_evidence.CHANGELOG_TOKEN_READS
        with SeededCommits(self.root, reads) as seeded:
            found = suite_evidence._changelog_tokens(self.root)
        self.assertEqual(seeded.landed, reads)
        self.assertEqual(found, {})

    def test_one_head_change_fewer_than_the_bound_still_keeps_the_tokens(self):
        # Positive control for the bound: the last allowed read succeeds when the changes stop one read earlier.
        with SeededCommits(self.root, suite_evidence.CHANGELOG_TOKEN_READS - 1) as seeded:
            found = suite_evidence._changelog_tokens(self.root)
        self.assertEqual(seeded.landed, suite_evidence.CHANGELOG_TOKEN_READS - 1)
        self.assertEqual(found, self.tokens)


class RefusalCodeTests(PublishedBatch):
    """Which refusal codes are read again, counted over a reader that refuses with a chosen code."""

    def reads(self, code):
        calls = []

        def refuse(root):
            calls.append(root)
            raise migration.ap.Refused(code)

        with patch.object(migration, "changelog_citation_tokens", refuse):
            found = suite_evidence._changelog_tokens(self.root)
        return found, len(calls)

    def test_another_refusal_is_not_read_again(self):
        self.assertEqual(self.reads("migration-config-not-committed"), ({}, 1))

    def test_a_head_change_refusal_from_the_same_reader_is_read_again(self):
        # Positive control: the same counting reader, refusing on a head change, is called up to the bound.
        self.assertEqual(self.reads(HEAD_CHANGED), ({}, suite_evidence.CHANGELOG_TOKEN_READS))


if __name__ == "__main__":
    unittest.main()
