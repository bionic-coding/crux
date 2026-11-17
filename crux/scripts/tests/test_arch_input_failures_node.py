"""ADR-0181 in the Node.js pack — absent, unreadable, unparseable and unlistable inputs.

`NodePackLaneTests` holds the cases the core's shared reader and walk give
every pack. The classes below hold the Node.js pack's own sites: its OpenAPI
candidate probe, its fixed `package.json` and `tsconfig.json` reads, the walked
sources and `schema.prisma` files, its decode and tree-sitter parse sites, its
three aggregate scan caps and its oversize and cap residuals. The
broad-handler rule covers every pack module from
`test_arch_input_failures_core.py`.

Each case derives a fixture through `derive-arch.py` and asserts the lane: an
omission named in the map and in `coverage.json` with exit 0, a document
finding with exit 1, or an environment failure with exit 2. Every refusing
case asserts the byte-unchanged arch tree, and the clean derive of the same
fixture in `setUp` is the positive control.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from arch_input_failures_support import (
    CORE,
    PackLaneCases,
    active_ledger,
    arch_snapshot,
    bionic,
    coverage,
    run_cli,
    skip_if_root,
    write,
)

NODE = __import__("crux.arch.packs.node", fromlist=["extract_node_module_graph"])


class NodePackLaneTests(PackLaneCases, unittest.TestCase):
    SOURCE = "src/lib/util.js"
    SUBDIR = "src/lib"

    def build(self, root: Path) -> None:
        write(root, "package.json", '{"name": "app", "version": "1.0.0", "main": "src/index.js"}\n')
        write(root, "src/index.js", 'const util = require("./lib/util");\n')
        write(root, "src/lib/util.js", "module.exports = { f() { return 1; } };\n")


_PACKAGE = '{"name": "shop", "dependencies": {"express": "^4.0.0"}}\n'

_INDEX = (
    'const express = require("express");\n'
    'const util = require("@lib/util");\n'
    "const app = express();\n"
    'app.get("/items", util.list);\n'
)

_SCHEMA = (
    "model User {\n"
    "  id    Int    @id @default(autoincrement())\n"
    "  name  String\n"
    "}\n"
)

_TSCONFIG = '{"compilerOptions": {"baseUrl": ".", "paths": {"@lib/*": ["src/lib/*"]}}}\n'

_BIG = 2 * 1024 * 1024


#: A Node.js repository the pack populates in all three descriptive concerns:
#: `prisma/schema.prisma` (data-model), an Express verb call (api-surface) and
#: an import graph whose one edge resolves through a `tsconfig.json` alias
#: (module-graph).
def node_repo(root: Path) -> None:
    bionic(root)
    write(root, "package.json", _PACKAGE)
    write(root, "tsconfig.json", _TSCONFIG)
    write(root, "prisma/schema.prisma", _SCHEMA)
    write(root, "src/index.js", _INDEX)
    write(root, "src/lib/util.js", "module.exports = { list() { return []; } };\n")


class _Repo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        node_repo(self.root)
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

    def omissions(self, concern: str) -> list[dict]:
        return coverage(self.root)[concern]["omissions"]

    def spine(self, concern: str) -> str:
        return (self.root / "bionic" / "arch" / f"{concern}.md").read_text()

    def derive_ok(self) -> None:
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))

    def assert_omitted(self, rel: str, reason: str, kind: str, *concerns: str) -> None:
        self.derive_ok()
        for concern in concerns:
            with self.subTest(concern=concern):
                self.assertIn({"path": rel, "reason": reason, "kind": kind},
                              self.omissions(concern))
                self.assertIn(f"- `{rel}` — {reason} ({kind})", self.spine(concern))

    def assert_no_omission(self) -> None:
        self.derive_ok()
        for concern, rec in coverage(self.root).items():
            self.assertEqual(rec["omissions"], [], concern)

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

    def test_every_concern_populates_with_no_omission(self):
        cov = coverage(self.root)
        for concern in ("data-model", "api-surface", "module-graph"):
            self.assertEqual(cov[concern]["verdict"], "populated", concern)
            self.assertEqual(cov[concern]["omissions"], [], concern)
        self.assertIn("| User |", self.spine("data-model"))
        self.assertIn("`/items`", self.spine("api-surface"))
        self.assertIn("`express`", self.spine("api-surface"))
        graph = self.spine("module-graph")
        self.assertIn('"src/index.js"] --> ', graph)
        self.assertIn('"src/lib/util.js"]', graph)


class AbsentTests(_Repo):

    def test_an_absent_tsconfig_is_no_input(self):
        (self.root / "tsconfig.json").unlink()
        self.assert_no_omission()
        self.assertNotIn("-->", self.spine("module-graph"))

    def test_an_absent_prisma_schema_is_no_input_and_the_next_rung_answers(self):
        (self.root / "prisma" / "schema.prisma").unlink()
        self.assert_no_omission()
        self.assertNotEqual(coverage(self.root)["data-model"]["verdict"], "populated")

    def test_an_absent_openapi_document_is_no_input(self):
        self.assert_no_omission()
        self.assertIn("`/items`", self.spine("api-surface"))

    def test_no_openapi_candidate_present_records_nothing(self):
        with active_ledger(self.root, "api-surface") as ledger:
            self.assertIsNone(NODE._node_openapi_path(self.root))
        self.assertEqual(ledger.omissions("api-surface"), [])
        self.assertEqual(ledger.findings, [])


class OpenApiCandidateTests(_Repo):
    """`_node_openapi_path` tries `openapi.json`, then `swagger.json`, … (nits F1)."""

    SWAGGER = '{"paths": {"/pets": {"get": {"summary": "list", "tags": ["pets"]}}}}'

    def test_positive_control_an_absent_first_candidate_reads_the_second(self):
        write(self.root, "swagger.json", self.SWAGGER)
        self.assert_no_omission()
        self.assertIn("_Derived from `swagger.json`._", self.spine("api-surface"))

    def test_a_dangling_link_at_the_first_candidate_is_named_and_ends_the_probe(self):
        write(self.root, "swagger.json", self.SWAGGER)
        os.symlink("nowhere.json", self.root / "openapi.json")
        self.assert_omitted("openapi.json", "not-a-file", "symbolic-link", "api-surface")
        # The second candidate is not read in its place; the route scan answers.
        self.assertNotIn("swagger.json", self.spine("api-surface"))
        self.assertIn("`/items`", self.spine("api-surface"))

    def test_a_directory_at_the_first_candidate_is_named_and_ends_the_probe(self):
        write(self.root, "swagger.json", self.SWAGGER)
        (self.root / "openapi.json").mkdir()
        self.assert_omitted("openapi.json", "not-a-file", "directory", "api-surface")
        self.assertNotIn("swagger.json", self.spine("api-surface"))

    def test_a_mode_000_openapi_document_is_a_document_finding(self):
        skip_if_root(self)
        write(self.root, "openapi.json", self.SWAGGER)
        self.derive_ok()
        self.before = arch_snapshot(self.root)
        os.chmod(self.root / "openapi.json", 0)
        self.assert_refused(1, "openapi.json")


class UnreadableTests(_Repo):

    def test_an_undecodable_source_is_named_and_still_hashed(self):
        write(self.root, "src/bad.js", b"const bad = '\xff';\n")
        self.assert_omitted("src/bad.js", "undecodable", "undecodable",
                            "module-graph", "api-surface")
        self.assertNotIn("src/bad.js", self.spine("module-graph").split("## Omissions")[0])
        self.assertIn("src/bad.js", coverage(self.root)["module-graph"]["inputs_found"])

    def test_a_symbolic_link_source_is_named_not_a_file(self):
        os.symlink("util.js", self.root / "src" / "lib" / "alias.js")
        self.assert_omitted("src/lib/alias.js", "not-a-file", "symbolic-link",
                            "module-graph", "api-surface")

    def test_an_oversize_source_is_named_and_not_as_a_residual(self):
        write(self.root, "src/huge.js", "// " + "x" * _BIG + "\n")
        self.assert_omitted("src/huge.js", "over-cap", "oversize", "module-graph")
        self.assertNotIn("2 MB bound", self.spine("module-graph"))

    def test_an_undecodable_tsconfig_is_named(self):
        write(self.root, "tsconfig.json", _TSCONFIG.encode() + b"// \xff\n")
        self.assert_omitted("tsconfig.json", "undecodable", "undecodable", "module-graph")
        self.assertNotIn("-->", self.spine("module-graph"))

    def test_a_directory_at_the_tsconfig_is_not_a_file(self):
        (self.root / "tsconfig.json").unlink()
        (self.root / "tsconfig.json").mkdir()
        self.assert_omitted("tsconfig.json", "not-a-file", "directory", "module-graph")

    def test_a_dangling_link_at_the_tsconfig_is_not_a_file(self):
        (self.root / "tsconfig.json").unlink()
        os.symlink("nowhere.json", self.root / "tsconfig.json")
        self.assert_omitted("tsconfig.json", "not-a-file", "symbolic-link", "module-graph")

    def test_a_mode_000_tsconfig_is_a_document_finding(self):
        skip_if_root(self)
        os.chmod(self.root / "tsconfig.json", 0)
        self.assert_refused(1, "tsconfig.json")

    def test_an_undecodable_package_json_is_named(self):
        write(self.root, "package.json", _PACKAGE.encode()[:-2] + b'\xff}\n')
        self.assert_omitted("package.json", "undecodable", "undecodable", "api-surface")
        self.assertNotIn("`express`", self.spine("api-surface"))

    def test_an_undecodable_prisma_schema_is_named(self):
        write(self.root, "prisma/schema.prisma", _SCHEMA.encode() + b"// \xff\n")
        self.assert_omitted("prisma/schema.prisma", "undecodable", "undecodable", "data-model")
        self.assertNotIn("| User |", self.spine("data-model"))

    def test_an_oversize_prisma_schema_is_named(self):
        write(self.root, "prisma/schema.prisma", _SCHEMA + "// " + "x" * _BIG + "\n")
        self.assert_omitted("prisma/schema.prisma", "over-cap", "oversize", "data-model")

    def test_a_dangling_link_prisma_schema_is_named(self):
        (self.root / "prisma" / "schema.prisma").unlink()
        os.symlink("nowhere.prisma", self.root / "prisma" / "schema.prisma")
        self.assert_omitted("prisma/schema.prisma", "not-a-file", "symbolic-link",
                            "data-model")

    def test_a_mode_000_prisma_schema_is_a_document_finding(self):
        skip_if_root(self)
        os.chmod(self.root / "prisma" / "schema.prisma", 0)
        self.assert_refused(1, "prisma/schema.prisma")

    def test_a_linked_graphql_schema_is_named_not_listed(self):
        write(self.root, "schema/real.graphql", "type Query { a: Int }\n")
        os.symlink("real.graphql", self.root / "schema" / "alias.graphql")
        self.assert_omitted("schema/alias.graphql", "not-a-file", "symbolic-link",
                            "api-surface")
        text = self.spine("api-surface").split("## Omissions")[0]
        self.assertIn("`schema/real.graphql`", text)
        self.assertNotIn("alias.graphql", text)

    def test_a_fifo_at_the_tsconfig_is_an_environment_failure(self):
        (self.root / "tsconfig.json").unlink()
        os.mkfifo(self.root / "tsconfig.json")
        self.assert_refused(2, "tsconfig.json")


class UnparseableTests(_Repo):

    def test_an_unparseable_openapi_json_is_named(self):
        write(self.root, "openapi.json", "{not json")
        self.assert_omitted("openapi.json", "unparseable", "unparseable", "api-surface")

    def test_an_unparseable_tsconfig_is_named_and_not_as_a_residual(self):
        write(self.root, "tsconfig.json", "{not json")
        self.assert_omitted("tsconfig.json", "unparseable", "unparseable", "module-graph")
        self.assertNotIn("present but unparseable", self.spine("module-graph"))

    def test_an_unparseable_package_json_is_named(self):
        write(self.root, "package.json", "{not json")
        self.assert_omitted("package.json", "unparseable", "unparseable", "api-surface")

    def test_a_memory_error_while_parsing_a_source_exits_2(self):
        with mock.patch.object(NODE, "_js_parse", side_effect=MemoryError()):
            code, out, _payload, err = run_cli(self.root)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("src/index.js", err)
        self.assertIn("MemoryError", err)
        self.assertEqual(arch_snapshot(self.root), self.before)

    def test_a_content_failure_while_parsing_a_source_is_named(self):
        with mock.patch.object(NODE, "_js_parse", side_effect=RecursionError()):
            self.assert_omitted("src/index.js", "unparseable", "unparseable", "api-surface")
        self.assertNotIn("`/items`", self.spine("api-surface"))


class ScanCapTests(_Repo):
    """The three aggregate scan caps (`_scan_node_files`, `_detect_node_scan`,
    `_detect_node_mongoose`) are counted over-cap omissions over the sorted
    walk (ADR-0181 approach 8)."""

    def test_the_source_scan_cap_names_the_skipped_count_and_drops_the_residual_line(self):
        with mock.patch.object(NODE, "_MAX_SCAN_FILES", 1):
            self.derive_ok()
        caps = [r for r in self.omissions("module-graph") if "cap" in r]
        self.assertEqual(caps, [{"cap": "_MAX_SCAN_FILES", "dir": ".", "skipped": 1,
                                 "reason": "over-cap", "kind": "scan-cap"}])
        text = self.spine("module-graph")
        self.assertIn("- scan cap `_MAX_SCAN_FILES` under `.` skipped 1 input(s)", text)
        self.assertNotIn("Aggregate scan cap reached", text)

    def test_positive_control_without_a_ledger_the_residual_line_renders(self):
        with mock.patch.object(NODE, "_MAX_SCAN_FILES", 1):
            _entries, _sources, residuals = NODE._scan_node_files(self.root)
        self.assertTrue(any("Aggregate scan cap reached" in r for r in residuals))

    def test_the_detector_scan_caps_are_counted_per_loop(self):
        write(self.root, "src/a.ts", "export const a = 1;\n")
        write(self.root, "src/b.ts", "export const b = 2;\n")
        with mock.patch.object(NODE, "_MAX_SCAN_FILES", 1):
            with active_ledger(self.root, "data-model") as ledger:
                self.assertFalse(NODE._detect_node_typeorm(self.root))
                self.assertFalse(NODE._detect_node_mongoose(self.root))
        caps = {(r["cap"], r["skipped"]) for r in ledger.omissions("data-model")}
        total = len(list(self.root.rglob("*.js"))) + len(list(self.root.rglob("*.ts")))
        # typeorm scans `.ts`/`.tsx` only (2), mongoose every JS/TS source.
        self.assertEqual(caps, {("_MAX_SCAN_FILES", 1), ("_MAX_SCAN_FILES", total - 1)})
        self.assertEqual(len(ledger.omissions("data-model")), 2)

    def test_positive_control_a_detector_under_its_cap_records_nothing(self):
        with active_ledger(self.root, "data-model") as ledger:
            self.assertFalse(NODE._detect_node_typeorm(self.root))
            self.assertFalse(NODE._detect_node_mongoose(self.root))
        self.assertEqual(ledger.omissions("data-model"), [])


class UnlistableTests(_Repo):

    def test_an_unlistable_prisma_directory_is_an_environment_failure(self):
        skip_if_root(self)
        os.chmod(self.root / "prisma", 0o300)   # searchable, not listable
        self.assert_refused(2, "prisma")

    def test_an_unlistable_source_root_is_an_environment_failure(self):
        skip_if_root(self)
        os.chmod(self.root / "src", 0o300)
        self.assert_refused(2, "src")

    def test_the_prisma_listing_raises_the_environment_lane(self):
        skip_if_root(self)
        prisma = self.root / "prisma"
        os.chmod(prisma, 0o300)
        with active_ledger(self.root, "data-model"):
            with self.assertRaises(CORE.ArchEnvironmentFailure) as caught:
                NODE._find_prisma_schemas(self.root)
        self.assertTrue(any(line.startswith("prisma:")
                            for line in caught.exception.failures),
                        caught.exception.failures)
        os.chmod(prisma, 0o755)
        with active_ledger(self.root, "data-model"):        # positive control
            self.assertEqual(NODE._find_prisma_schemas(self.root),
                             [self.root / "prisma" / "schema.prisma"])

    def test_outside_a_derive_an_unlistable_directory_is_skipped(self):
        skip_if_root(self)
        os.chmod(self.root / "prisma", 0o300)
        self.assertEqual(NODE._find_prisma_schemas(self.root), [])


class LedgerParityTests(unittest.TestCase):
    """The direct-extractor fixture with no omission, run once more under an
    active ledger and concern: the same content and an empty ledger."""

    EXTRACTORS = (("data-model", "extract_node_data_model_prisma"),
                  ("api-surface", "extract_node_api_surface_routes"),
                  ("module-graph", "extract_node_module_graph"))

    def test_each_extractor_matches_under_an_active_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            node_repo(root)
            for concern, name in self.EXTRACTORS:
                with self.subTest(concern=concern):
                    fn = getattr(NODE, name)
                    direct = fn(root, "bionic")
                    with active_ledger(root, concern) as ledger:
                        under = fn(root, "bionic")
                    self.assertEqual(under, direct)
                    self.assertEqual(ledger.omissions(concern), [])
                    self.assertEqual(ledger.findings, [])

    def test_positive_control_the_wrapper_records_a_content_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            node_repo(root)
            write(root, "src/bad.js", b"\xff\n")
            with active_ledger(root, "module-graph") as ledger:
                NODE.extract_node_module_graph(root, "bionic")
            self.assertEqual([r["path"] for r in ledger.omissions("module-graph")],
                             ["src/bad.js"])


class DirectCallTests(unittest.TestCase):
    """With no active ledger the pack answers as before."""

    def test_an_oversize_source_keeps_its_residual_line_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            node_repo(root)
            write(root, "src/huge.js", "// " + "x" * _BIG + "\n")
            content, _sources = NODE.extract_node_module_graph(root, "bionic")
            self.assertIn("Skipped for exceeding the 2 MB bound: `src/huge.js`", content)
            self.assertNotIn("Omissions", content)
            self.assertIsNone(CORE._ACTIVE_LEDGER.get())

    def test_an_undecodable_source_is_replacement_decoded_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            node_repo(root)
            write(root, "src/legacy.js", b'// \xff\nconst u = require("./lib/util");\n')
            content, sources = NODE.extract_node_module_graph(root, "bionic")
            self.assertIn('"src/legacy.js"] --> ', content)
            self.assertIn("src/legacy.js", sources)

    def test_an_unparseable_tsconfig_keeps_its_residual_line_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            node_repo(root)
            write(root, "tsconfig.json", "{not json")
            content, _sources = NODE.extract_node_module_graph(root, "bionic")
            self.assertIn("`tsconfig.json` present but unparseable", content)

    def test_the_marker_is_the_exists_predicate_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            self.assertFalse(NODE.detect(root).matched)
            (root / "package.json").mkdir()
            self.assertEqual(NODE.detect(root).markers, ("package.json",))



if __name__ == "__main__":
    unittest.main()
