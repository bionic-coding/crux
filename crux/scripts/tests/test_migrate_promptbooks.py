"""Tests for migrate-promptbooks.py (ADR-0024).

Exercises the engine end-to-end: a synthetic legacy book/run fixture pair plus a
real archived corpus book/run, asserting that migrated YAML validates against
the schemas and that a migrated run's book_content_hash equals a fresh
compute_book_hash of its migrated book (the CHK-PB-BIND contract).
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

# Guard: skip entire module when PyYAML is absent.  The skip also prevents
# validate-promptbook's PyYAML re-exec lane from exec-replacing the unittest
# process — keep any main() invocation behind this guard.
try:
    import yaml  # noqa: F401
except ImportError as exc:
    raise unittest.SkipTest(f"PyYAML unavailable (uv lane required): {exc}")

_SCRIPTS = Path(__file__).resolve().parent.parent
_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_REPO = _SCRIPTS.parent.parent


def _load(mod_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(mod_name, _SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mp = _load("_migrate_promptbooks_t", "migrate-promptbooks.py")
vp = _load("_validate_promptbook_t", "validate-promptbook.py")
load_yaml = mp.load_yaml


def _validate(text: str, kind: str) -> tuple[int, list]:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = Path(f.name)
    try:
        return vp.validate_file(path, kind)
    finally:
        path.unlink()


class FixtureBookTests(unittest.TestCase):
    def setUp(self):
        self.book_md = (_FIXTURES / "legacy-book.md").read_text(encoding="utf-8")
        self.book_yaml = mp.migrate_book_text(self.book_md)
        self.book = load_yaml(self.book_yaml)

    def test_migrated_book_validates(self):
        code, errors = _validate(self.book_yaml, "promptbook")
        self.assertEqual(code, 0, errors)

    def test_format_version_and_core_fields(self):
        self.assertEqual(self.book["format_version"], "1")
        self.assertEqual(self.book["id"], "PB-9001")
        self.assertEqual(self.book["status"], "archived")
        self.assertEqual(self.book["total_prompts"], 2)
        self.assertEqual(self.book["modules"], {"adrs": 1, "dev_loops": 1, "review_cycles": 1})

    def test_blockquote_prompt_preserved_with_paragraph_break(self):
        prompt = self.book["prompts"][0]["prompt"]
        self.assertIn("Dispatch planning agents", prompt)
        self.assertNotIn("> ", prompt)            # blockquote prefix stripped
        self.assertIn("\n\n", prompt)             # the blank `>` line is a paragraph break

    def test_side_effects_parsed_as_list(self):
        self.assertEqual(self.book["prompts"][0]["side_effects"], ["propose-adr", "query-docs"])

    def test_module_boundary_comment_not_leaked(self):
        # MF-3 regression: the `<!-- MODULE BOUNDARY -->` comment between Prompt 1
        # and Prompt 2 must NOT be absorbed into Prompt 1's side_effects (it would
        # otherwise corrupt the frozen-plan hash subset).
        for p in self.book["prompts"]:
            for se in p.get("side_effects", []):
                self.assertNotIn("MODULE BOUNDARY", se)
            self.assertNotIn("MODULE BOUNDARY", p["prompt"])
            self.assertNotIn("MODULE BOUNDARY", p["expected_output"])

    def test_expected_output_dewrapped(self):
        eo = self.book["prompts"][0]["expected_output"]
        self.assertIn("status: Proposed", eo)
        self.assertNotIn("\n", eo)                # cosmetic wrap collapsed

    def test_archive_note_extracted(self):
        note = self.book["archive_note"]
        self.assertEqual(note["archived_at"], "2026-05-29")
        self.assertEqual(note["final_run"], "RUN-001")
        self.assertIn("terminal", note["note"])

    def test_module_tag_omitted(self):
        # Legacy books carry no per-prompt module_tag; it must be absent, not null.
        for p in self.book["prompts"]:
            self.assertNotIn("module_tag", p)

    def test_emit_round_trips_stable(self):
        # Re-emitting the loaded book reproduces byte-identical YAML (idempotent).
        again = mp.emit_book(load_yaml(self.book_yaml))
        self.assertEqual(again, self.book_yaml)


class FixtureRunTests(unittest.TestCase):
    def setUp(self):
        self.book_yaml = mp.migrate_book_text((_FIXTURES / "legacy-book.md").read_text("utf-8"))
        self.run_md = (_FIXTURES / "legacy-run.md").read_text(encoding="utf-8")
        self.run_yaml = mp.migrate_run_text(self.run_md, self.book_yaml)
        self.run = load_yaml(self.run_yaml)

    def test_migrated_run_validates(self):
        code, errors = _validate(self.run_yaml, "run")
        self.assertEqual(code, 0, errors)

    def test_book_content_hash_matches_book(self):
        expected = mp.compute_book_hash(load_yaml(self.book_yaml))
        self.assertEqual(self.run["book_content_hash"], expected)
        self.assertRegex(self.run["book_content_hash"], r"^sha256:[0-9a-f]{64}$")

    def test_interleaved_notes_captured(self):
        self.assertIn("interleaved BEFORE", self.run["notes"])
        self.assertIn("### A nested subsection", self.run["notes"])

    def test_prompts_contiguous_despite_interleave(self):
        self.assertEqual([p["n"] for p in self.run["prompts"]], [1, 2])

    def test_empty_result_and_artifacts(self):
        p2 = self.run["prompts"][1]
        self.assertEqual(p2["result"], "")        # legacy `—` -> ""
        self.assertEqual(p2["artifacts"], [])      # legacy `—` -> []

    def test_result_dewrapped(self):
        p1 = self.run["prompts"][0]
        self.assertIn("Proposed ADR-9001", p1["result"])
        self.assertNotIn("\n", p1["result"])

    def test_artifact_with_paren_comma_not_split(self):
        # MF-2 regression: a comma INSIDE parentheses must not split the artifact.
        p1 = self.run["prompts"][0]
        self.assertEqual(
            p1["artifacts"],
            ["docs/adrs/ADR-9001-x.md (rev 2, frozen on accept)", "docs/adrs/index.md"],
        )

    def test_fenced_pr_draft_preserved_and_not_truncating(self):
        # MF-1 regression: a fenced `### PR Draft` whose body contains literal
        # `## Summary` / `## Test plan` lines must NOT (a) truncate the run, nor
        # (b) pollute the embedding prompt's fields. Its content is preserved in notes.
        self.assertEqual([p["n"] for p in self.run["prompts"]], [1, 2])
        # The REAL Summary section survives (not replaced by the fenced `## Summary`).
        self.assertIn("fixture run summary", self.run["summary"])
        # Prompt 2's fields are NOT polluted by the trailing PR draft.
        self.assertEqual(self.run["prompts"][1]["artifacts"], [])
        self.assertEqual(self.run["prompts"][1]["result"], "")
        # The embedded PR draft content is preserved (in notes, under a marker).
        self.assertIn("Migrated from Prompt 2 body", self.run["notes"])
        self.assertIn("did the thing", self.run["notes"])

    def test_retired_blocked_confirmed_field_is_dropped(self):
        # ADR-0077 clause 5(b) deleted the per-prompt flag, so run.schema.json no
        # longer accepts it (additionalProperties: false). Carrying it across would
        # emit an invalid run; the `.md` original keeps it verbatim under legacy/.
        # The fixture's prompt 2 DOES carry `blocked-confirmed: true`, so this
        # exercises the drop rather than an absence.
        self.assertIn("blocked-confirmed", (_FIXTURES / "legacy-run.md").read_text())
        self.assertEqual(self.run["prompts"][1]["state"], "blocked")
        self.assertNotIn("blocked_confirmed", self.run["prompts"][1])

    def test_migrated_run_validates_against_the_current_run_schema(self):
        errors: list[dict] = []
        vp.validate(self.run, vp.load_schema(vp.RUN_SCHEMA), "#", "#", errors, "<t>")
        self.assertEqual(errors, [])

    def test_summary_captured(self):
        self.assertIn("fixture run summary", self.run["summary"])


class FilenameNormalizationTests(unittest.TestCase):
    def test_legacy_run_001_normalizes(self):
        self.assertEqual(mp._live_yaml_path(Path("x/run-001.md")).name, "run-RUN-001.yaml")

    def test_modern_run_filename_preserved(self):
        self.assertEqual(mp._live_yaml_path(Path("x/run-RUN-002.md")).name, "run-RUN-002.yaml")

    def test_book_filename(self):
        self.assertEqual(mp._live_yaml_path(Path("a/PB-0001-x.md")).name, "PB-0001-x.yaml")


class RealCorpusTests(unittest.TestCase):
    """Migrate a real corpus book + run and assert it validates and binds. After
    the ADR-0024 corpus migration the legacy `.md` originals live under
    docs/promptbooks/legacy/ (the live dirs are `.yaml`); these tests read the
    preserved originals so the real-data coverage survives the migration."""

    _LEGACY = _REPO / "docs" / "promptbooks" / "legacy"
    BOOK = _LEGACY / "archive" / "PB-0015-unified-docs-inbox.md"
    RUN = _LEGACY / "runs" / "PB-0015-unified-docs-inbox" / "run-RUN-001.md"

    def test_real_book_migrates_and_validates(self):
        if not self.BOOK.is_file():
            self.skipTest("PB-0015 book not present")
        book_yaml = mp.migrate_book_text(self.BOOK.read_text(encoding="utf-8"))
        code, errors = _validate(book_yaml, "promptbook")
        self.assertEqual(code, 0, errors)

    def test_real_run_migrates_validates_and_binds(self):
        if not (self.BOOK.is_file() and self.RUN.is_file()):
            self.skipTest("PB-0015 book/run not present")
        book_yaml = mp.migrate_book_text(self.BOOK.read_text(encoding="utf-8"))
        run_yaml = mp.migrate_run_text(self.RUN.read_text(encoding="utf-8"), book_yaml)
        code, errors = _validate(run_yaml, "run")
        self.assertEqual(code, 0, errors)
        run = load_yaml(run_yaml)
        self.assertEqual(run["book_content_hash"], mp.compute_book_hash(load_yaml(book_yaml)))

    def test_pb0005_modules_inferred(self):
        # PB-0005 is a cycle-tagged book predating the modules frontmatter block;
        # the migrator infers {1,1,1} from its canonical 13-prompt structure.
        book = _REPO / "docs/promptbooks/legacy/archive/PB-0005-release-skill-zips-via-github-actions.md"
        if not book.is_file():
            self.skipTest("PB-0005 not present")
        book_yaml = mp.migrate_book_text(book.read_text(encoding="utf-8"))
        code, errors = _validate(book_yaml, "promptbook")
        self.assertEqual(code, 0, errors)
        self.assertEqual(load_yaml(book_yaml)["modules"],
                         {"adrs": 1, "dev_loops": 1, "review_cycles": 1})

    def test_pb0008_run_dedup_to_contiguous(self):
        # PB-0008's run carries a stale duplicate of prompts 9-13; the migrator
        # keeps only the contiguous-from-1 authoritative sequence.
        book = _REPO / "docs/promptbooks/legacy/archive/PB-0008-execute-adr-0008-skill-naming-cleanup.md"
        run = _REPO / "docs/promptbooks/legacy/runs/PB-0008-execute-adr-0008-skill-naming-cleanup/run-RUN-001.md"
        if not (book.is_file() and run.is_file()):
            self.skipTest("PB-0008 not present")
        book_yaml = mp.migrate_book_text(book.read_text(encoding="utf-8"))
        run_yaml = mp.migrate_run_text(run.read_text(encoding="utf-8"), book_yaml)
        code, errors = _validate(run_yaml, "run")
        self.assertEqual(code, 0, errors)
        ns = [p["n"] for p in load_yaml(run_yaml)["prompts"]]
        self.assertEqual(ns, list(range(1, 14)))   # 1..13, no stale dupe
        # The authoritative Prompt 9 is the 'done' one, not the stale 'pending' dupe.
        self.assertEqual(load_yaml(run_yaml)["prompts"][8]["state"], "done")


if __name__ == "__main__":
    unittest.main()
