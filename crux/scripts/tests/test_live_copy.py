"""The bookkeeping-free committed copy that live-view tests run their gates over.

WHY THESE TESTS EXIST. `_live_copy.committed_copy` stands between a gate and the live
bookkeeping documents (journal, operations log, inbox, garden, next-steps record). If it
copied one of them, a test built on it would read a document the checkout suites do not
declare as an input, and a bookkeeping commit would again invalidate the suite's receipt.
If it dropped something else, the gate would judge a smaller tree than this checkout.

Each test builds its own miniature repository, so these run in the staged artifact too.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import _council_gate_support as support
import _live_copy
import suite_evidence

FILES = {
    "bionic/journal/2026-10.md": "entry\n",
    "bionic/log.md": "log\n",
    "bionic/inbox/note.md": "note\n",
    "bionic/garden/2026-10-01.md": "idea\n",
    "bionic/whats_next.md": "next\n",
    "bionic/queue/cycles.yaml": "queue: []\n",
    "bionic/cycles/CYC-0001/cycle.json": "{}\n",
    "crux-authority-reset.md": "candidates\n",
    "crux-implementation-evidence.md": "notes\n",
    "crux-unlisted-note.md": "an ordinary root document\n",
    ".bionic.yml": ('config_version: "1"\ndocs_dir: bionic\nevidence:\n  bookkeeping_paths:\n'
                    "    - crux-authority-reset.md\n    - crux-implementation-evidence.md\n"),
    "bionic/adrs/ADR-0001-x.md": "decision\n",
    "bionic/manifest.yml": "schema_version: 5\n",
    "crux/source.py": "VALUE = 1\n",
    ".claude/skills/example/SKILL.md": "skill\n",
    ".claude/worktrees/other/payload.txt": "another checkout\n",
}


def _repo(root: Path, *, committed: bool = True) -> Path:
    support.init_repo(root)
    for rel, text in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if committed:
        support.git(root, "add", "-A")
        support.git(root, "commit", "-q", "-m", "base")
    return root


def _listed(base: Path) -> set[str]:
    return {p.relative_to(base).as_posix() for p in base.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(base).parts}


class CommittedCopyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_the_copy_omits_every_bookkeeping_document_and_keeps_the_rest(self):
        repo = _repo(self.tmp / "repo")
        copy = _live_copy.committed_copy(repo, self.tmp / "copy")
        listed = _listed(copy)
        # The bookkeeping documents are replaced only by the frozen corroboration entries.
        for rel in ("bionic/journal/2026-10.md", "bionic/inbox/note.md",
                    "bionic/garden/2026-10-01.md", "bionic/whats_next.md", "bionic/queue/cycles.yaml",
                    "crux-authority-reset.md", "crux-implementation-evidence.md"):
            with self.subTest(omitted=rel):
                self.assertNotIn(rel, listed)
        self.assertEqual((copy / "bionic" / "log.md").read_text(encoding="utf-8"),
                         (_live_copy.CORROBORATION_FIXTURE / "log.md").read_text(encoding="utf-8"))
        self.assertEqual(
            (copy / "bionic" / "journal" / "2026-08.md").read_text(encoding="utf-8"),
            (_live_copy.CORROBORATION_FIXTURE / "journal" / "2026-08.md").read_text(encoding="utf-8"))
        # POSITIVE DISCRIMINATOR: everything else the repository holds is in the copy.
        # The cycle records stay in the copy (a published migration proof may read a historical one),
        # and so does a root document the repository does not configure as bookkeeping.
        for rel in ("bionic/adrs/ADR-0001-x.md", "bionic/manifest.yml", "crux/source.py",
                    ".claude/skills/example/SKILL.md", "bionic/cycles/CYC-0001/cycle.json",
                    "crux-unlisted-note.md", ".bionic.yml"):
            with self.subTest(kept=rel):
                self.assertEqual((copy / rel).read_text(encoding="utf-8"), FILES[rel])
        # Another checkout under the harness directory is isolation state, not source.
        self.assertNotIn(".claude/worktrees/other/payload.txt", listed)

    def test_the_omitted_names_are_the_shared_list_less_the_cycle_records(self):
        # The one list: suite_evidence.DOCS_EXCLUSIONS. The copy keeps `cycles`.
        self.assertEqual(_live_copy.BOOKKEEPING, frozenset(suite_evidence.DOCS_EXCLUSIONS) - {"cycles"})
        self.assertIn("queue", _live_copy.BOOKKEEPING)
        self.assertNotIn("cycles", _live_copy.BOOKKEEPING)

    def test_the_omitted_files_are_read_from_the_shared_producer(self):
        repo = _repo(self.tmp / "repo")
        self.assertEqual(_live_copy.omitted(repo, str(repo), ["crux-authority-reset.md", "crux-unlisted-note.md", "crux"]),
                         {"crux-authority-reset.md"})
        self.assertEqual(_live_copy.omitted(repo, str(repo / "bionic"), ["queue", "cycles", "adrs", "log.md"]),
                         {"queue", "log.md"})
        # A configured file is matched by its repository-relative path, not by its name anywhere.
        self.assertEqual(_live_copy.omitted(repo, str(repo / "crux"), ["crux-authority-reset.md"]), set())

    def test_the_copy_carries_uncommitted_edits_and_is_itself_committed(self):
        repo = _repo(self.tmp / "repo")
        (repo / "crux" / "source.py").write_text("VALUE = 2\n", encoding="utf-8")
        (repo / "crux" / "new.py").write_text("NEW = True\n", encoding="utf-8")
        copy = _live_copy.committed_copy(repo, self.tmp / "copy")
        self.assertEqual((copy / "crux" / "source.py").read_text(encoding="utf-8"), "VALUE = 2\n")
        self.assertTrue((copy / "crux" / "new.py").is_file())
        self.assertEqual(support.git(copy, "status", "--porcelain").strip(), "")
        # The copy descends from the real HEAD, so history-backed proofs still resolve.
        real_head = support.git(repo, "rev-parse", "HEAD").strip()
        support.git(copy, "merge-base", "--is-ancestor", real_head, "HEAD")

    def test_a_repository_with_no_operations_log_is_given_no_frozen_entries(self):
        repo = self.tmp / "repo"
        support.init_repo(repo)
        (repo / "crux").mkdir()
        (repo / "crux" / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
        support.git(repo, "add", "-A")
        support.git(repo, "commit", "-q", "-m", "base")
        copy = _live_copy.committed_copy(repo, self.tmp / "copy")
        self.assertEqual(_listed(copy), {"crux/source.py"})

    def test_the_frozen_entries_are_the_nine_signed_batches_and_the_survey_batch(self):
        log = (_live_copy.CORROBORATION_FIXTURE / "log.md").read_text(encoding="utf-8")
        journal = (_live_copy.CORROBORATION_FIXTURE / "journal" / "2026-08.md").read_text(encoding="utf-8")
        for n in range(1, 10):
            with self.subTest(batch=f"B{n}"):
                self.assertIn(f"] backfill | B{n}\n", log)
                self.assertIn(f"] review | backfill sign-off B{n}\n", journal)
        self.assertNotIn("B10", log)
        self.assertIn("] observation | survey batch SVY-0001\n", log)
        self.assertIn("] review | survey sign-off SVY-0001\n", journal)


if __name__ == "__main__":
    unittest.main()
