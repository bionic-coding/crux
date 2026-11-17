"""ADR-0181 in the crux pack — absent, unreadable, unparseable and unlistable inputs.

Each case derives the crux-pack fixture through `derive-arch.py` and asserts the
lane: an omission named in the map and in `coverage.json` with exit 0, a
document finding with exit 1, or an environment failure with exit 2. Every
refusing case asserts the byte-unchanged arch tree and pairs with a positive
control on the same fixture.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from arch_input_failures_support import (
    CORE,
    active_ledger,
    arch_snapshot,
    coverage,
    crux_repo,
    run_cli,
    skip_if_root,
    write,
)

CRUX = __import__("crux.arch.packs.crux", fromlist=["extract_data_model"])


class _Repo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        crux_repo(self.root)
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.before = arch_snapshot(self.root)

    def tearDown(self):
        for path in [self.root, *self.root.rglob("*")]:
            try:
                if not path.is_symlink():
                    os.chmod(path, 0o755 if path.is_dir() else 0o644)
            except OSError:
                pass
        self._tmp.cleanup()

    def omissions(self, concern: str = "data-model") -> list[dict]:
        return coverage(self.root)[concern]["omissions"]

    def assert_omitted(self, rel: str, reason: str, kind: str, concern: str = "data-model"):
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.assertIn({"path": rel, "reason": reason, "kind": kind}, self.omissions(concern))
        text = (self.root / "bionic" / "arch" / f"{concern}.md").read_text()
        self.assertIn(f"- `{rel}` — {reason} ({kind})", text)

    def assert_refused(self, code_want: int, name: str) -> None:
        for argv in ((), ("--dry-run",)):
            with self.subTest(argv=argv):
                code, out, payload, err = run_cli(self.root, *argv)
                self.assertEqual(code, code_want, (payload, err))
                if code_want == 1:
                    self.assertIn(name, [f["file"] for f in payload["validation_errors"]])
                else:
                    self.assertEqual(out, "")
                    self.assertIn(name, err)
                self.assertEqual(arch_snapshot(self.root), self.before)


class PositiveControlTests(_Repo):

    def test_the_fixture_derives_with_no_omission_in_any_concern(self):
        for concern, rec in coverage(self.root).items():
            self.assertEqual(rec["omissions"], [], concern)
            self.assertEqual(rec["verdict"], "populated", concern)


class AbsentTests(_Repo):

    def test_an_absent_manifest_is_no_input(self):
        (self.root / "bionic" / "manifest.yml").unlink()
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.assertEqual(self.omissions(), [])
        self.assertNotIn("## Manifest shape",
                         (self.root / "bionic/arch/data-model.md").read_text())

    def test_an_absent_schema_directory_stubs_without_an_omission(self):
        for p in (self.root / "crux" / "schemas").iterdir():
            p.unlink()
        (self.root / "crux" / "schemas").rmdir()
        (self.root / "crux" / "schemas").mkdir()   # the marker stays; no schema
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.assertEqual(coverage(self.root)["data-model"]["verdict"], "stubbed")
        self.assertEqual(self.omissions(), [])

    def test_a_skill_directory_without_a_skill_file_is_no_input(self):
        (self.root / "crux" / "skills" / "empty-skill").mkdir()
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.assertEqual(self.omissions("api-surface"), [])


class UnreadableTests(_Repo):

    def test_a_mode_000_schema_is_a_document_finding(self):
        skip_if_root(self)
        os.chmod(self.root / "crux/schemas/w.schema.json", 0)
        self.assert_refused(1, "crux/schemas/w.schema.json")

    def test_a_mode_000_skill_file_is_a_document_finding(self):
        skip_if_root(self)
        os.chmod(self.root / "crux/skills/zeta-skill/SKILL.md", 0)
        self.assert_refused(1, "crux/skills/zeta-skill/SKILL.md")

    def test_an_undecodable_schema_is_named(self):
        write(self.root, "crux/schemas/bad.json", b"{\"title\": \"\xff\"}")
        self.assert_omitted("crux/schemas/bad.json", "undecodable", "undecodable")

    def test_an_undecodable_skill_file_is_named(self):
        write(self.root, "crux/skills/bad-skill/SKILL.md", b"---\nname: b\xff\n---\n")
        self.assert_omitted("crux/skills/bad-skill/SKILL.md", "undecodable", "undecodable",
                            concern="api-surface")

    def test_a_symbolic_link_schema_is_named_not_a_file(self):
        os.symlink("w.schema.json", self.root / "crux/schemas/link.json")
        self.assert_omitted("crux/schemas/link.json", "not-a-file", "symbolic-link")

    def test_a_directory_at_a_fixed_input_path_is_not_a_file(self):
        (self.root / "crux/scripts/crux-env.py").mkdir()
        self.assert_omitted("crux/scripts/crux-env.py", "not-a-file", "directory",
                            concern="api-surface")

    def test_a_dangling_link_at_a_fixed_input_path_is_not_a_file(self):
        os.symlink("nowhere.py", self.root / "crux/scripts/crux-env.py")
        self.assert_omitted("crux/scripts/crux-env.py", "not-a-file", "symbolic-link",
                            concern="api-surface")

    def test_positive_control_a_regular_file_at_the_fixed_path_is_read(self):
        write(self.root, "crux/scripts/crux-env.py", "sub.add_parser('init')\n")
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.assertEqual(self.omissions("api-surface"), [])
        self.assertIn("`init`", (self.root / "bionic/arch/api-surface.md").read_text())

    def test_the_manifest_path_classifies_through_the_reader(self):
        """`<docs_dir>/manifest.yml` is also read by the configuration loader
        before any derive, so its faults are driven through the extractor
        under an active ledger rather than through the CLI."""
        man = self.root / "bionic/manifest.yml"
        man.unlink()
        man.mkdir()
        with active_ledger(self.root, "data-model") as ledger:
            CRUX.extract_data_model(self.root, "bionic")
        self.assertIn({"path": "bionic/manifest.yml", "reason": "not-a-file",
                       "kind": "directory"}, ledger.omissions("data-model"))
        man.rmdir()
        os.symlink("nowhere.yml", man)
        with active_ledger(self.root, "data-model") as ledger:
            CRUX.extract_data_model(self.root, "bionic")
        self.assertIn({"path": "bionic/manifest.yml", "reason": "not-a-file",
                       "kind": "symbolic-link"}, ledger.omissions("data-model"))

    def test_a_fifo_schema_is_an_environment_failure(self):
        os.mkfifo(self.root / "crux/schemas/trap.json")
        self.assert_refused(2, "crux/schemas/trap.json")


class UnparseableTests(_Repo):

    def test_a_schema_that_does_not_parse_is_named(self):
        write(self.root, "crux/schemas/broken.json", "{not json")
        self.assert_omitted("crux/schemas/broken.json", "unparseable", "unparseable")

    def test_a_schema_whose_shape_raises_is_named(self):
        """JSON that parses into a list raises in the render: named unparseable."""
        write(self.root, "crux/schemas/list.json", "[1, 2]")
        self.assert_omitted("crux/schemas/list.json", "unparseable", "unparseable")

    def test_an_unparseable_manifest_is_named_and_not_rendered(self):
        """Driven through the extractor: the configuration loader refuses an
        unparseable manifest before any derive."""
        write(self.root, "bionic/manifest.yml", "a: [unclosed\n")
        with active_ledger(self.root, "data-model") as ledger:
            content, sources = CRUX.extract_data_model(self.root, "bionic")
        self.assertEqual(ledger.omissions("data-model"),
                         [{"path": "bionic/manifest.yml", "reason": "unparseable",
                           "kind": "unparseable"}])
        self.assertNotIn("## Manifest shape", content)
        self.assertIn("bionic/manifest.yml", sources)
        # Without a ledger the empty key list renders, as before.
        content, _sources = CRUX.extract_data_model(self.root, "bionic")
        self.assertIn("## Manifest shape", content)

    def test_an_unparseable_cli_is_named(self):
        write(self.root, "crux/scripts/crux-env.py", "def (\n")
        self.assert_omitted("crux/scripts/crux-env.py", "unparseable", "unparseable",
                            concern="api-surface")

    def test_a_memory_error_while_parsing_a_schema_exits_2(self):
        real = CRUX.json.loads

        def boom(text, *a, **k):
            if '"title": "W"' in text:
                raise MemoryError()
            return real(text, *a, **k)
        with mock.patch.object(CRUX.json, "loads", side_effect=boom):
            code, out, _payload, err = run_cli(self.root)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("crux/schemas/w.schema.json", err)
        self.assertIn("MemoryError", err)
        self.assertEqual(arch_snapshot(self.root), self.before)


class UnlistableTests(_Repo):

    def test_an_unlistable_schema_directory_is_an_environment_failure(self):
        skip_if_root(self)
        os.chmod(self.root / "crux/schemas", 0o300)   # searchable, not listable
        self.assert_refused(2, "crux/schemas")

    def test_an_unlistable_skills_directory_is_an_environment_failure(self):
        skip_if_root(self)
        os.chmod(self.root / "crux/skills", 0o300)
        self.assert_refused(2, "crux/skills")

    def test_an_unlistable_package_subdirectory_is_an_environment_failure(self):
        skip_if_root(self)
        write(self.root, "crux/scripts/crux/sub/m.py", "")
        os.chmod(self.root / "crux/scripts/crux/sub", 0)
        self.assert_refused(2, "crux/scripts/crux/sub")


class LedgerParityTests(unittest.TestCase):
    """The direct-extractor fixtures with no omission, run once more under an
    active ledger and concern: the same content and an empty ledger."""

    def test_each_extractor_matches_under_an_active_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            crux_repo(root)
            for concern, fn in (("data-model", CRUX.extract_data_model),
                                ("api-surface", CRUX.extract_api_surface),
                                ("module-graph", CRUX.extract_module_graph)):
                with self.subTest(concern=concern):
                    direct = fn(root, "bionic")
                    with active_ledger(root, concern) as ledger:
                        under = fn(root, "bionic")
                    self.assertEqual(under, direct)
                    self.assertEqual(ledger.omissions(concern), [])
                    self.assertEqual(ledger.findings, [])

    def test_positive_control_the_wrapper_records_a_content_failure(self):
        """The parity wrapper is not vacuous: the same call records an
        omission when an input fails."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            crux_repo(root)
            write(root, "crux/schemas/bad.json", b"\xff")
            with active_ledger(root, "data-model") as ledger:
                CRUX.extract_data_model(root, "bionic")
            self.assertEqual([r["path"] for r in ledger.omissions("data-model")],
                             ["crux/schemas/bad.json"])


class DirectCallTests(unittest.TestCase):
    """With no active ledger the pack answers as before."""

    def test_an_undecodable_schema_is_skipped_silently_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            crux_repo(root)
            write(root, "crux/schemas/bad.json", b"\xff")
            content, sources = CRUX.extract_data_model(root, "bionic")
            self.assertNotIn("Omissions", content)
            self.assertIn("crux/schemas/bad.json", sources)
            self.assertIsNone(CORE._ACTIVE_LEDGER.get())


if __name__ == "__main__":
    unittest.main()
