"""The governs-reference lint leaves the owner-authored queue out of its default scope.

A queue item's text is the owner's words as captured, bound by the authorization digests,
and copied unchanged into an immutable `queue/history/items/` record when its cycle ends.
A citation there is history, never a claim an agent can repair, so the default scope skips
`<docs_dir>/queue`. Naming a queue record with `--path` still lints it (positive control).
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "lint_governs_queue_scope", Path(__file__).resolve().parents[1] / "lint-governs-references.py")
LGR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LGR)


class QueueScopeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / ".bionic.yml").write_text("docs_dir: bionic\n", encoding="utf-8")
        adrs = self.root / "bionic" / "adrs"
        adrs.mkdir(parents=True)
        (self.root / "crux").mkdir()
        (adrs / "ADR-0001-x.md").write_text("\n".join([
            "---", "id: ADR-0001", 'title: "T1"', "status: Accepted", "date: 2026-08-26",
            "governs:", "  - domain: test-domain", '    rule: "a test rule"',
            "    scope: test scope", "    handle: ADR-0001/alpha", "    provenance: authored",
            "---", "", "# ADR-0001", "", "Body.", ""]), encoding="utf-8")

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_lint(self, *args: str) -> tuple[int, dict]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = LGR.main(["--repo-root", str(self.root), *args])
        return rc, json.loads(buf.getvalue())

    def test_queue_records_are_excluded_only_from_default_scope(self):
        active = self.write("bionic/queue/cycles.yaml", 'outcome: "ADR-9999/old and rule:ghost"\n')
        history = self.write("bionic/queue/history/items/Q-0001.json",
                             '{"outcome": "ADR-9999/old and rule:ghost"}\n')
        original = {path: path.read_bytes() for path in (active, history)}
        current = self.write("bionic/briefs/BRIEF-current.md", "ADR-9999/old and rule:ghost\n")
        rc, payload = self.run_lint()
        self.assertEqual(rc, 1, payload)
        self.assertEqual(set(payload["scanned"]), {str(current.resolve())})
        self.assertEqual({row["path"] for row in payload["unresolved"]}, {str(current.resolve())})
        self.assertEqual({row["path"] for row in payload["rule_findings"]}, {str(current.resolve())})
        # Positive control: naming a queue record by --path lints it, so the default
        # scope's exclusion, not the matcher, kept it quiet above.
        for path in (active, history, self.root / "bionic" / "queue"):
            with self.subTest(path=path):
                rc, payload = self.run_lint("--path", str(path))
                self.assertEqual(rc, 1, payload)
                self.assertTrue(any(row["handle"] == "ADR-9999/old" for row in payload["unresolved"]))
                self.assertTrue(any(row["token"] == "rule:ghost" for row in payload["rule_findings"]))
        self.assertEqual(original, {path: path.read_bytes() for path in (active, history)})

    def test_operations_log_detail_files_are_excluded_and_the_summary_stays_in_scope(self):
        # `log.md` in this list denotes the operations log in its current files: the monthly detail
        # files and the split's staged, transaction, completion and kept files are dated records. The
        # summary holds a narrative, so the lint checks its citations.
        bad = "ADR-9999/old and rule:ghost\n"
        dated = [self.write(f"bionic/log/{name}", bad) for name in (
            "2026-09.md", "2026-10.md", ".legacy-" + "a" * 64 + ".md", ".stray-" + "b" * 64 + ".md",
            ".split-" + "c" * 64 + ".json", ".split-complete.json", ".kept-" + "d" * 64 + ".txt")]
        summary = self.write("bionic/log/summary.md", bad)
        rc, payload = self.run_lint()
        self.assertEqual(rc, 1, payload)
        self.assertEqual(set(payload["scanned"]), {str(summary.resolve())}, payload["scanned"])
        self.assertEqual({row["path"] for row in payload["unresolved"]}, {str(summary.resolve())})
        self.assertEqual({row["path"] for row in payload["rule_findings"]}, {str(summary.resolve())})
        # Positive control: naming a detail file by --path lints it, so the default scope's exclusion,
        # not the matcher, kept it quiet above.
        for path in dated:
            with self.subTest(path=path.name):
                rc, payload = self.run_lint("--path", str(path))
                self.assertTrue(any(row["handle"] == "ADR-9999/old" for row in payload["unresolved"]) or
                                any(row["token"] == "rule:ghost" for row in payload["rule_findings"]), payload)

    def test_an_undefined_name_under_the_log_directory_is_linted(self):
        # The exclusion is the name grammar, not the directory: a stray file in `log/` is in scope.
        bad = "ADR-9999/old and rule:ghost\n"
        stray = self.write("bionic/log/notes.md", bad)
        month = self.write("bionic/log/2026-13.md", bad)
        rc, payload = self.run_lint()
        self.assertEqual(rc, 1, payload)
        self.assertEqual(set(payload["scanned"]), {str(stray.resolve()), str(month.resolve())})


if __name__ == "__main__":
    unittest.main()
