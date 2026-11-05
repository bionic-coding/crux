"""Contract: the commander batches pending owner decisions into one message."""
from pathlib import Path
import re
import unittest

PLUGIN = Path(__file__).resolve().parents[2]


def flat(relative):
    return " ".join((PLUGIN / relative).read_text(encoding="utf-8").split())


def writer_commit_operations(text):
    """Operations whose own writer commits the record, independent of list ordering."""
    clause = re.search(r"The cycle writer commits the cycle record:\s*(.*?)\s+commit\b", text)
    return set(re.findall(r"`([a-z-]+)`", clause.group(1))) if clause else set()


class CommanderBatchesOwnerDecisionsTests(unittest.TestCase):
    def test_pending_owner_decisions_go_in_one_message(self):
        body = flat("agents/commander.md")
        self.assertIn("in one message", body)
        for kind in ("owner approvals", "ADR human acceptance", "pass extensions",
                     "owner exceptions", "outward authorizations"):
            self.assertIn(kind, body, kind)
        self.assertIn("continue all work that does not depend on them", body)

    def test_council_disputes_are_not_owner_decisions(self):
        body = flat("agents/commander.md")
        self.assertIn("A council dispute is never an owner decision", body)
        self.assertIn(
            "data policy, publishing, owner exceptions and product-scope change", body)

    def test_the_writer_commits_the_record_text_stays(self):
        body = flat("agents/commander.md")
        self.assertTrue({"owner-exception", "pause"} <= writer_commit_operations(body))

    def test_missing_writer_commit_obligation_is_detected(self):
        body = flat("agents/commander.md")
        self.assertNotIn("pause", writer_commit_operations(body.replace("`pause`, ", "")))
        self.assertEqual(writer_commit_operations(body.replace(
            "The cycle writer commits the cycle record:", "The caller commits the cycle record:"
        )), set())

    def test_roles_name_the_one_main_run_policy(self):
        for relative in ("agents/commander.md", "agents/dev-lead.md"):
            body = flat(relative)
            self.assertIn("main test run once per code state on the floor minor", body, relative)
            self.assertIn("`flagged` and `health` checks per minor", body, relative)
            self.assertIn("bash sync.sh --public-repo idyll/crux --dry-run --skip-fingerprints",
                          body, relative)
            self.assertNotIn("staged suites on both supported Python minors", body, relative)


if __name__ == "__main__":
    unittest.main()
