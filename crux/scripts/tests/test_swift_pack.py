"""Tests for the Swift arch stack pack (ADR-0129 and ADR-0130).

`RecoveryTests` covers the grammar-only recovery primitives ADR-0129 clause 7
requires, calling the module's functions directly rather than through a
derive. The other classes cover the walk, the renderers, the declaration and
manifest fixtures, the registered derive path, and the Xcode project reader
through `crux.arch.packs.swift`'s three extractors and the fixture harness
under `fixtures/xcodeproj/`.

Requires `tree_sitter` and `tree_sitter_swift==0.7.3` (ADR-0129 clause 2). A
missing grammar FAILS these tests rather than skipping them; the missing-grammar
lane itself is tested through a subprocess derive. The cache-dependent real-file
tests skip (the FETCH_HINT pattern `test_arch_corpus.py` uses) when the pinned
NetNewsWire checkout is not present under `arch-corpus/.cache/`.
"""

from __future__ import annotations

import importlib
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]  # crux/scripts
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _timing  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "swiftdecls"
CACHE_ROOT = Path(__file__).resolve().parent / "arch-corpus" / ".cache"
REAL_FILE = (
    CACHE_ROOT
    / "netnewswire"
    / "Modules"
    / "ErrorLog"
    / "Sources"
    / "ErrorLog"
    / "ErrorLogDatabase.swift"
)
PINNED_NETNEWSWIRE_HEAD = "b4361413fc1850110f9f42652f0f84e7a51e9d64"

FETCH_HINT = (
    "The pinned NetNewsWire checkout is not present under "
    "crux/scripts/tests/arch-corpus/.cache/netnewswire — fetch the corpus "
    "(see crux/scripts/tests/arch-corpus/fetch.py) to run this test."
)


def _swift_module():
    # No SkipTest lane: a missing grammar is a FAILURE here — the
    # missing-grammar lane is tested separately, through a subprocess, in
    # `MissingGrammarTests`.
    import tree_sitter  # noqa: F401
    import tree_sitter_swift  # noqa: F401

    return importlib.import_module("crux.arch.packs.swift")


def _real_file_head() -> str | None:
    head_file = CACHE_ROOT / "netnewswire" / ".git" / "HEAD"
    if not head_file.exists():
        return None
    return head_file.read_text().strip()


class RecoveryTests(unittest.TestCase):
    """ADR-0129 clause 7: grammar-only recovery of a top-level-ERROR-dropped decl.

    (a) a fresh synthetic fixture whose trigger was found by probing snippets
    against the pinned grammar (probe command + trigger recorded in the report,
    not reproduced here — the fixture bytes ARE the finding). (b) the real
    NetNewsWire file the owner's own probe named. (c) a clean-parse control.
    Plus two negatives: no type keyword, and an acceptance failure.
    """

    def setUp(self):
        self.swift = _swift_module()

    # ---- (a) fresh synthetic fixture --------------------------------------

    def test_synthetic_fixture_detects_dropped_declaration(self):
        path = FIXTURES / "13-dropped-declaration.swift"
        src = path.read_bytes()
        tree = self.swift._parse(src)
        dropped = self.swift._dropped_declarations(tree)
        self.assertEqual(len(dropped), 1, "exactly one top-level ERROR drops a declaration")
        record = dropped[0]
        self.assertEqual(record.keyword.type, "actor")
        self.assertEqual(src[record.name.start_byte:record.name.end_byte], b"ShelfCatalog")

    def test_synthetic_fixture_recovery_accepts_and_returns_facts_at_file_lines(self):
        path = FIXTURES / "13-dropped-declaration.swift"
        src = path.read_bytes()
        tree = self.swift._parse(src)
        dropped = self.swift._dropped_declarations(tree)
        result = self.swift._recover(dropped[0], src)

        self.assertIsInstance(result, self.swift.RecoveredDeclaration)
        self.assertEqual(result.keyword, "actor")
        self.assertEqual(result.name, "ShelfCatalog")
        self.assertEqual(result.error_span, (4, 25))
        self.assertEqual(result.slice_span, (4, 14))

        # File-line mapping: row_offset + a row read from `result.tree` recovers
        # the file's 1-based line (row_offset is 0-based; +1 for 1-based; the
        # recovered tree's own rows are 0-based within the slice).
        root = result.tree.root_node
        decl = root.children[0]
        self.assertEqual(decl.type, "class_declaration")  # tree-sitter-swift's node kind for `actor`
        self.assertEqual(decl.start_point[0] + result.row_offset + 1, 4)

        body = decl.child_by_field_name("body")
        members = [c for c in body.children if c.type.endswith("_declaration")]
        self.assertEqual(len(members), 3)  # property, init, isEmpty — NOT absorb, the trigger
        member_file_lines = [m.start_point[0] + result.row_offset + 1 for m in members]
        self.assertEqual(member_file_lines, [6, 8, 12])

        # The only error node left in the recovered subtree is a MISSING `}`.
        bad = []

        def walk(n):
            if n.is_error or n.is_missing:
                bad.append(n)
            for c in n.children:
                walk(c)

        walk(root)
        self.assertEqual(len(bad), 1)
        self.assertTrue(bad[0].is_missing)
        self.assertEqual(bad[0].type, "}")

    def test_recovery_runs_at_most_once_per_dropped_declaration(self):
        path = FIXTURES / "13-dropped-declaration.swift"
        src = path.read_bytes()
        tree = self.swift._parse(src)
        dropped = self.swift._dropped_declarations(tree)

        calls = []
        real_parse = self.swift._parse

        def counting_parse(raw):
            calls.append(raw)
            return real_parse(raw)

        self.swift._parse = counting_parse
        try:
            self.swift._recover(dropped[0], src)
        finally:
            self.swift._parse = real_parse

        self.assertEqual(len(calls), 1, "recovery re-parses the slice exactly once")

    def test_synthetic_recovery_is_byte_stable_across_two_runs(self):
        path = FIXTURES / "13-dropped-declaration.swift"
        src = path.read_bytes()

        def run_once():
            tree = self.swift._parse(src)
            dropped = self.swift._dropped_declarations(tree)
            result = self.swift._recover(dropped[0], src)
            return (
                result.keyword,
                result.name,
                result.error_span,
                result.slice_span,
                result.row_offset,
                bytes(result.slice_bytes),
            )

        self.assertEqual(run_once(), run_once())

    def test_recovery_survives_nesting_deeper_than_the_recursion_limit(self):
        # ADR-0129 clause 2: content never exhausts the interpreter stack. A
        # complete member nested 1,200 parentheses deep sits inside the slice,
        # so the recovery's own check of the re-parsed tree must not recurse.
        src = (FIXTURES / "13-dropped-declaration.swift").read_bytes()
        deep = b"\tpublic let depth: Int = " + b"(" * 1200 + b"0" + b")" * 1200 + b"\n\n"
        marker = b"\tfunc absorb("
        src = src.replace(marker, deep + marker, 1)
        tree = self.swift._parse(src)
        dropped = self.swift._dropped_declarations(tree)
        self.assertEqual(len(dropped), 1, "the deep member no longer leaves the trigger's ERROR")
        result = self.swift._recover(dropped[0], src)
        self.assertIsInstance(result, self.swift.RecoveredDeclaration)
        self.assertEqual(result.name, "ShelfCatalog")

    def test_text_the_grammar_lexed_into_a_string_stays_inside_the_residual_span(self):
        # The trigger's `?? ""` opens a string the grammar never closes, so
        # every later line becomes string text inside the ERROR. No node is
        # left to walk, and grammar-only recovery cannot bring those lines
        # back. The `declaration-recovered` span covers them instead.
        src = (FIXTURES / "13-dropped-declaration.swift").read_bytes()
        self.assertTrue(src.endswith(b"\t}\n}\n"))
        src = src[: -len(b"}\n")] + (b"\n\tpublic func later() {}\n}\n\n"
                                     b"public struct After {\n\tpublic let a: Int\n}\n")
        facts = self.swift._parse_file("T.swift", src)
        self.assertNotIn("After", {t["name"] for t in facts.types})
        recovered = [r for r in facts.residuals if r[0] == "declaration-recovered"]
        self.assertEqual(len(recovered), 1)
        last_line = src.count(b"\n")
        self.assertEqual(recovered[0][1], [(4, last_line)])

    def test_members_under_an_unrecovered_error_still_render(self):
        # ADR-0129 clause 7: the reader walks whole subtrees. When recovery
        # fails its postcondition, the complete members under the ERROR still
        # render, unqualified, each with a `nesting unconfirmed` residual.
        from unittest import mock
        src = (FIXTURES / "13-dropped-declaration.swift").read_bytes()

        def refuse(err, raw):
            return self.swift.DroppedDeclarationRecord(keyword="actor", name="ShelfCatalog",
                                                       error_span=(4, 25))

        def interfaces_and_residuals():
            facts = self.swift._parse_file("T.swift", src)
            return {i["name"] for i in facts.interfaces}, facts.residuals

        with mock.patch.object(self.swift, "_recover", refuse):
            interfaces, residuals = interfaces_and_residuals()
            self.assertIn("declaration-dropped", {r[0] for r in residuals})
            self.assertTrue({"shelfCount", "init(shelves:)", "isEmpty()"} <= interfaces)
            self.assertFalse(any(n.startswith("ShelfCatalog.") for n in interfaces))
            unconfirmed = [r for r in residuals
                           if r[2] == "location member; effect nesting unconfirmed"]
            self.assertEqual(len(unconfirmed), 3)
            # Positive control: without the detached walk the members vanish.
            with mock.patch.object(self.swift._Walk, "run_detached", lambda self, nodes: None):
                interfaces, _ = interfaces_and_residuals()
            self.assertNotIn("isEmpty()", interfaces)

    def test_detached_members_under_a_top_level_if_render_conditional(self):
        # ADR-0129 clause 7, the `run_detached` half: when recovery fails, the members
        # walked from the ERROR's tail carry the `#if` state the ERROR sat in.
        # The unwrapped fixture is the control: the same members, unmarked.
        from unittest import mock

        def refuse(err, raw):
            return self.swift.DroppedDeclarationRecord(keyword="actor", name="ShelfCatalog",
                                                       error_span=(err.node.start_point[0] + 1, 0))

        def members(name):
            src = (FIXTURES / name).read_bytes()
            with mock.patch.object(self.swift, "_recover", refuse):
                facts = self.swift._parse_file("T.swift", src)
            return {i["name"]: i["conditional"] for i in facts.interfaces}

        wrapped = members("13-dropped-declaration-conditional.swift")
        plain = members("13-dropped-declaration.swift")
        detached = {"shelfCount", "init(shelves:)", "isEmpty()"}
        self.assertTrue(detached <= set(wrapped), wrapped)
        self.assertEqual({n: wrapped[n] for n in detached}, dict.fromkeys(detached, True))
        self.assertEqual({n: plain[n] for n in detached}, dict.fromkeys(detached, False))

    def test_the_detached_walk_reads_the_if_state_recorded_at_the_error(self):
        # ADR-0129 clause 7: the dropping ERROR runs to the end of the file on every input
        # the pinned grammar drops a declaration for, so the main walk ends in
        # the `#if` state the ERROR sat in. The detached walk must not depend
        # on that: it reads the state recorded when the walk skipped the ERROR.
        # Clearing the walk's final state here stands in for any later
        # directive that would change it.
        from unittest import mock
        src = (FIXTURES / "13-dropped-declaration-conditional.swift").read_bytes()
        tree = self.swift._parse(src)
        dropped = self.swift._dropped_declarations(tree)
        skip = frozenset(self.swift._node_span_key(d.node) for d in dropped)
        facts = self.swift.FileFacts(path="T.swift")
        walk = self.swift._Walk(src, facts)
        walk.run(tree.root_node, skip)
        walk.cond = []

        def refuse(err, raw):
            return self.swift.DroppedDeclarationRecord(keyword="actor", name="ShelfCatalog",
                                                       error_span=(5, 27))

        with mock.patch.object(self.swift, "_recover", refuse):
            self.swift._recover_dropped(dropped, src, facts, walk)
        conditional = {i["name"]: i["conditional"] for i in facts.interfaces}
        self.assertEqual(conditional.get("isEmpty()"), True, conditional)

    # ---- (c) clean-parse control -------------------------------------------

    def test_clean_control_matches_recovered_facts(self):
        recovered_path = FIXTURES / "13-dropped-declaration.swift"
        control_path = FIXTURES / "13-dropped-declaration-control.swift"

        src = recovered_path.read_bytes()
        tree = self.swift._parse(src)
        dropped = self.swift._dropped_declarations(tree)
        result = self.swift._recover(dropped[0], src)

        control_src = control_path.read_bytes()
        control_tree = self.swift._parse(control_src)
        self.assertFalse(control_tree.root_node.has_error, "the control parses clean")
        control_decl = control_tree.root_node.children[-1]
        self.assertEqual(control_decl.type, "class_declaration")

        recovered_root = result.tree.root_node
        recovered_decl = recovered_root.children[0]
        recovered_body = recovered_decl.child_by_field_name("body")
        control_body = control_decl.child_by_field_name("body")

        recovered_members = [c for c in recovered_body.children if c.type.endswith("_declaration")]
        # The control's clean parse still carries the trailing (empty)
        # absorb function_declaration; recovery's slice ends
        # before it, so compare only the members recovery actually returned.
        control_members = [c for c in control_body.children if c.type.endswith("_declaration")][
            : len(recovered_members)
        ]

        self.assertEqual(len(recovered_members), len(control_members))
        for rec_m, ctrl_m in zip(recovered_members, control_members):
            self.assertEqual(rec_m.type, ctrl_m.type)
            rec_line = rec_m.start_point[0] + result.row_offset + 1
            ctrl_line = ctrl_m.start_point[0] + 1  # the control has no ERROR, so no offset
            self.assertEqual(rec_line, ctrl_line)
            rec_text = result.slice_bytes[rec_m.start_byte : rec_m.end_byte]
            ctrl_text = control_src[ctrl_m.start_byte : ctrl_m.end_byte]
            self.assertEqual(rec_text, ctrl_text)

    # ---- negatives -----------------------------------------------------------

    def test_no_type_keyword_yields_no_dropped_declaration(self):
        # A bare `@` at top level after an import: a top-level ERROR with no
        # type keyword among its direct children.
        src = b"import Foundation\n\n@\n"
        tree = self.swift._parse(src)
        self.assertEqual(self.swift._dropped_declarations(tree), [])

    def test_acceptance_failure_yields_dropped_record(self):
        # A top-level ERROR whose direct children carry a type keyword, name
        # and `{`, but no `_declaration` child follows the brace (the trigger
        # method is the FIRST member, so there is nothing complete to recover).
        src = (
            b"import Foundation\n"
            b"import Core\n\n"
            b"public actor ShelfCatalog {\n\n"
            b"\tfunc absorb(_ table: NSDictionary) {\n"
            b"\t\tguard let code = table[CatalogField.code] as? String,\n"
            b"\t\t\t  let width = table[CatalogField.width] as? Double else {\n"
            b"\t\t\treturn\n"
            b"\t\t}\n"
            b"\t\tlet note = table[CatalogField.note] as? String ?? \"\"\n"
            b"\t\tlet owner = table[CatalogField.owner] as? String ?? \"\"\n"
            b"\t\tlet rank = table[CatalogField.rank] as? Int ?? 0\n"
            b"\t}\n"
            b"}\n"
        )
        tree = self.swift._parse(src)
        dropped = self.swift._dropped_declarations(tree)
        self.assertEqual(len(dropped), 1)
        result = self.swift._recover(dropped[0], src)
        self.assertIsInstance(result, self.swift.DroppedDeclarationRecord)
        self.assertEqual(result.keyword, "actor")
        self.assertEqual(result.name, "ShelfCatalog")

    # ---- (b) the real file ----------------------------------------------------

    def test_real_file_recovery_meets_the_postcondition(self):
        head = _real_file_head()
        if head is None or not REAL_FILE.exists():
            self.skipTest(FETCH_HINT)
        self.assertEqual(
            head,
            PINNED_NETNEWSWIRE_HEAD,
            "the cached NetNewsWire checkout is not pinned at the recorded commit",
        )

        src = REAL_FILE.read_bytes()

        def run_once():
            tree = self.swift._parse(src)
            dropped = self.swift._dropped_declarations(tree)
            self.assertEqual(len(dropped), 1, "exactly one dropped declaration")
            return self.swift._recover(dropped[0], src)

        calls = []
        real_parse = self.swift._parse

        def counting_parse(raw):
            calls.append(raw)
            return real_parse(raw)

        self.swift._parse = counting_parse
        try:
            result = run_once()
        finally:
            self.swift._parse = real_parse

        self.assertIsInstance(
            result,
            self.swift.RecoveredDeclaration,
            "ADR-0129 clause 7's GATE: grammar-only recovery must meet the "
            "postcondition on the real file, or the run stops",
        )
        # `run_once` itself calls `_parse` once (the whole-file parse that
        # finds the dropped declaration); `_recover` calls it a second time
        # (the one slice re-parse clause 7 permits). Both are counted here.
        self.assertEqual(len(calls), 2, "the file parse plus exactly one slice re-parse")

        self.assertEqual(result.keyword, "actor")
        self.assertEqual(result.name, "ErrorLogDatabase")

        root = result.tree.root_node
        decl = root.children[0]
        modifiers = decl.children[0]
        self.assertEqual(modifiers.type, "modifiers")
        self.assertIn(
            b"public",
            result.slice_bytes[modifiers.start_byte : modifiers.end_byte],
        )
        self.assertEqual(decl.start_point[0] + result.row_offset + 1, 13)

        body = decl.child_by_field_name("body")
        members = [c for c in body.children if c.type.endswith("_declaration")]

        def line_of(node) -> int:
            return node.start_point[0] + result.row_offset + 1

        properties = [m for m in members if m.type == "property_declaration"]
        inits = [m for m in members if m.type == "init_declaration"]
        functions = [m for m in members if m.type == "function_declaration"]
        self.assertEqual(len(properties), 4)
        self.assertEqual(len(inits), 1)
        self.assertEqual(len(functions), 3)

        # databasePath is the first stored property.
        self.assertEqual(line_of(properties[0]), 15)
        self.assertIn(
            b"databasePath",
            result.slice_bytes[properties[0].start_byte : properties[0].end_byte],
        )
        self.assertEqual(line_of(inits[0]), 23)

        def function_name(node) -> bytes:
            name_node = node.child_by_field_name("name")
            return result.slice_bytes[name_node.start_byte : name_node.end_byte]

        add_entry = next(f for f in functions if function_name(f) == b"addEntry")
        self.assertEqual(line_of(add_entry), 37)

        bad = []

        def walk(n):
            if n.is_error or n.is_missing:
                bad.append(n)
            for c in n.children:
                walk(c)

        walk(root)
        self.assertEqual(len(bad), 1, "the only reparse error is one MISSING `}`")
        self.assertTrue(bad[0].is_missing)
        self.assertEqual(bad[0].type, "}")

        # Byte-stable: running detection + recovery twice gives byte-identical
        # results (a canonical serialisation of the records and recovered
        # facts, compared across two independent runs).
        def canonical(res):
            return (
                res.keyword,
                res.name,
                res.error_span,
                res.slice_span,
                res.row_offset,
                bytes(res.slice_bytes),
            )

        self.assertEqual(canonical(result), canonical(run_once()))


class SkeletonTests(unittest.TestCase):
    """`DETECT_EXCLUDE`, `detect()`, `detect_containers()`, the walk and
    `_scan()` aggregate caps + read split (ADR-0129 clauses 3-6, 8)."""

    def setUp(self):
        self.swift = _swift_module()

    def test_detect_exclude_names_bundle_dirs_and_suffixes(self):
        self.assertEqual(
            self.swift.DETECT_EXCLUDE,
            frozenset({"Pods", "Carthage", "DerivedData", "SourcePackages",
                       "*.xcodeproj", "*.xcworkspace"}),
        )

    def test_entity_nouns_names_api_surface_interface_row(self):
        self.assertEqual(self.swift.ENTITY_NOUNS, {"api-surface": "interface row"})

    def test_detect_matches_package_swift(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Package.swift").write_text("// swift-tools-version:5.9\n")
            result = self.swift.detect(root)
            self.assertTrue(result.matched)
            self.assertEqual(result.markers, ("Package.swift",))

    def test_detect_matches_xcodeproj_with_pbxproj(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            proj = root / "App.xcodeproj"
            proj.mkdir()
            (proj / "project.pbxproj").write_text("// !$*UTF8*$!\n")
            result = self.swift.detect(root)
            self.assertTrue(result.matched)
            self.assertEqual(result.markers, ("App.xcodeproj",))

    def test_detect_matches_xcworkspace_with_contents(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ws = root / "App.xcworkspace"
            ws.mkdir()
            (ws / "contents.xcworkspacedata").write_text("<Workspace/>\n")
            result = self.swift.detect(root)
            self.assertTrue(result.matched)
            self.assertEqual(result.markers, ("App.xcworkspace",))

    def test_bare_xcodeproj_without_pbxproj_is_not_a_marker(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "App.xcodeproj").mkdir()
            result = self.swift.detect(root)
            self.assertFalse(result.matched)

    def test_bare_project_yml_and_stray_swift_are_not_markers(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "project.yml").write_text("name: App\n")
            (root / "main.swift").write_text("print(\"hi\")\n")
            result = self.swift.detect(root)
            self.assertFalse(result.matched)

    def test_detect_containers_sorted_repo_relative(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Package.swift").write_text("// x\n")
            (root / "Modules" / "Account").mkdir(parents=True)
            (root / "Modules" / "Account" / "Package.swift").write_text("// x\n")
            proj = root / "App.xcodeproj"
            proj.mkdir()
            (proj / "project.pbxproj").write_text("// x\n")
            containers = self.swift.detect_containers(root)
            self.assertEqual(
                containers,
                ("App.xcodeproj", "Modules/Account/Package.swift", "Package.swift"),
            )

    def test_detect_containers_never_follows_a_directory_symlink(self):
        # ADR-0129 clause 4: a walk never follows a directory symlink. A
        # symlinked `.xcodeproj` whose target holds `project.pbxproj` outside
        # the checkout is not a container. The real bundle beside it is the
        # positive control: the same check finds it.
        import tempfile
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            root = Path(d)
            elsewhere = Path(outside) / "Far.xcodeproj"
            elsewhere.mkdir()
            (elsewhere / "project.pbxproj").write_text("// x\n")
            (root / "Link.xcodeproj").symlink_to(elsewhere, target_is_directory=True)
            real = root / "Real.xcodeproj"
            real.mkdir()
            (real / "project.pbxproj").write_text("// x\n")
            self.assertEqual(self.swift.detect_containers(root), ("Real.xcodeproj",))

    def test_verify_parser_load_does_not_raise_when_grammar_present(self):
        self.swift.verify_parser_load()

    def test_input_classes_declare_all_three_concerns_with_swift_parser(self):
        for concern in ("data-model", "api-surface", "module-graph"):
            ic = self.swift.INPUT_CLASSES[concern]
            self.assertTrue(ic.expected)
            self.assertIn("*.swift", ic.globs)
        # data-model and api-surface declare only the Swift grammar;
        # module-graph's parser tuple also gains `yaml` for the XcodeGen
        # `project.yml` manifest (ADR-0130 clause 13).
        self.assertEqual(self.swift.INPUT_CLASSES["data-model"].parser, self.swift.SWIFT_PARSER_MODULES)
        self.assertEqual(self.swift.INPUT_CLASSES["api-surface"].parser, self.swift.SWIFT_PARSER_MODULES)
        self.assertEqual(self.swift.INPUT_CLASSES["module-graph"].parser,
                          self.swift.SWIFT_PARSER_MODULES + ("yaml",))

    def test_input_classes_add_the_adr_0130_project_globs_per_concern(self):
        # ADR-0130 clause 1: data-model reads no project input;
        # api-surface adds only the `project.pbxproj` globs; module-graph
        # adds `project.pbxproj`, the standalone-workspace glob, `*.xcconfig`
        # and `project.yml`.
        dm_globs = set(self.swift.INPUT_CLASSES["data-model"].globs)
        api_globs = set(self.swift.INPUT_CLASSES["api-surface"].globs)
        mg_globs = set(self.swift.INPUT_CLASSES["module-graph"].globs)
        self.assertFalse(any("pbxproj" in g for g in dm_globs))
        self.assertTrue(any(g.endswith("project.pbxproj") for g in api_globs))
        self.assertFalse(any("xcworkspacedata" in g or "xcconfig" in g or "project.yml" in g
                              for g in api_globs))
        for needle in ("project.pbxproj", "contents.xcworkspacedata", ".xcconfig", "project.yml"):
            self.assertTrue(any(needle in g for g in mg_globs), needle)

    def test_data_model_declares_the_swift_source_globs_only(self):
        # data-model reads and hashes `.swift` sources and never
        # `Package.swift` (its `expected` text says so), so its declared set
        # names the two `.swift` globs and no manifest glob. The other two
        # concerns read the manifest and keep its globs.
        self.assertEqual(self.swift.INPUT_CLASSES["data-model"].globs,
                         ("*.swift", "**/*.swift"))
        for concern in ("api-surface", "module-graph"):
            with self.subTest(concern=concern):
                globs = self.swift.INPUT_CLASSES[concern].globs
                self.assertIn("Package.swift", globs)
                self.assertIn("**/Package.swift", globs)

    def test_probes_returns_one_parser_probe_per_concern(self):
        registry = self.swift.probes()
        self.assertEqual(set(registry), {"data-model", "api-surface", "module-graph"})
        for concern, ps in registry.items():
            self.assertEqual(len(ps), 1)
            self.assertEqual(ps[0].kind, "parser")

    def test_walk_prunes_every_class_and_both_walkers_share_swift_walk(self):
        # ADR-0129 clause 8: one `_swift_walk(root)` generator carries the prune
        # rule once. A tree holding every prune class -- a core `_SKIP_DIRS`
        # entry, a dot-directory, a `DETECT_EXCLUDE` exact name and a
        # `DETECT_EXCLUDE` suffix (`*.xcodeproj`) -- proves the rule, and
        # patching `_swift_walk` to yield nothing empties BOTH
        # `_walk_swift_files` and `detect_containers`, proving they share it
        # rather than each carrying its own `os.walk` prune copy.
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Sources" / "App").mkdir(parents=True)
            (root / "Sources" / "App" / "Main.swift").write_text("struct A {}\n")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "Vendor.swift").write_text("struct B {}\n")
            (root / ".hidden").mkdir()
            (root / ".hidden" / "Skip.swift").write_text("struct C {}\n")
            (root / "Pods" / "Dep").mkdir(parents=True)
            (root / "Pods" / "Dep" / "Vendored.swift").write_text("struct D {}\n")
            (root / "Real.xcodeproj").mkdir()
            (root / "Real.xcodeproj" / "project.pbxproj").write_text("// x\n")
            (root / "Real.xcodeproj" / "Ignored.swift").write_text("struct E {}\n")

            with mock.patch.object(self.swift, "_swift_walk", return_value=iter(())):
                self.assertEqual(list(self.swift._walk_swift_files(root)), [])
                self.assertEqual(self.swift.detect_containers(root), ())

            files = sorted(self.swift._rel_str(root, p) for p in self.swift._walk_swift_files(root))
            self.assertEqual(files, ["Sources/App/Main.swift"])
            self.assertEqual(self.swift.detect_containers(root), ("Real.xcodeproj",))

    def test_walk_prunes_bundle_dirs_and_dot_dirs(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Sources" / "App").mkdir(parents=True)
            (root / "Sources" / "App" / "Main.swift").write_text("struct A {}\n")
            (root / "Pods" / "Dep").mkdir(parents=True)
            (root / "Pods" / "Dep" / "Vendored.swift").write_text("struct B {}\n")
            (root / ".hidden").mkdir()
            (root / ".hidden" / "Skip.swift").write_text("struct C {}\n")
            found = list(self.swift._walk_swift_files(root))
            rels = sorted(self.swift._rel_str(root, p) for p in found)
            self.assertEqual(rels, ["Sources/App/Main.swift"])

    def test_scan_hashes_read_files_and_reports_oversize(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "A.swift").write_text("struct A {}\n")
            big = root / "Big.swift"
            big.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
            reads, project_reads, sources, residuals = self.swift._scan(root, "api-surface")
            rels = sorted(self.swift._rel_str(root, p) for p, _raw in reads)
            self.assertEqual(rels, ["A.swift"])
            self.assertEqual(list(sources), ["A.swift"])
            self.assertEqual([(r[0], r[1]) for r in residuals], [("oversize", "Big.swift")])
            self.assertEqual(project_reads, self.swift.ProjectReads())

    def test_scan_reads_no_project_input_for_data_model(self):
        # ADR-0130 clause 1: data-model declares no project glob,
        # so its scan never touches project.pbxproj at all.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "A.swift").write_text("struct A {}\n")
            proj = root / "App.xcodeproj"
            proj.mkdir()
            (proj / "project.pbxproj").write_text("// !$*UTF8*$!\n")
            reads, project_reads, sources, _residuals = self.swift._scan(root, "data-model")
            self.assertEqual(project_reads, self.swift.ProjectReads())
            self.assertNotIn("App.xcodeproj/project.pbxproj", sources)

    def test_scan_reads_project_pbxproj_for_api_surface_and_hashes_it(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "A.swift").write_text("struct A {}\n")
            proj = root / "App.xcodeproj"
            proj.mkdir()
            pbx = proj / "project.pbxproj"
            pbx.write_text("// !$*UTF8*$!\n")
            reads, project_reads, sources, _residuals = self.swift._scan(root, "api-surface")
            rel = "App.xcodeproj/project.pbxproj"
            self.assertIn(rel, project_reads.files)
            self.assertEqual(project_reads.files[rel], pbx.read_bytes())
            self.assertIn(rel, sources)
            self.assertEqual(sources[rel], self.swift._sha256_hex(pbx.read_bytes()))
            # The pbxproj bytes are NOT parsed as Swift source -- they never
            # land in the swift/manifest `reads` list `_analyse` iterates.
            self.assertNotIn(rel, [self.swift._rel_str(root, p) for p, _raw in reads])

    def test_scan_module_graph_reads_workspace_xcconfig_and_project_yml(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "A.swift").write_text("struct A {}\n")
            ws = root / "App.xcworkspace"
            ws.mkdir()
            (ws / "contents.xcworkspacedata").write_text("<Workspace/>\n")
            (root / "App.xcconfig").write_text("SWIFT_VERSION = 5.0\n")
            (root / "project.yml").write_text("name: App\n")
            _reads, project_reads, sources, _residuals = self.swift._scan(root, "module-graph")
            for rel in ("App.xcworkspace/contents.xcworkspacedata", "App.xcconfig", "project.yml"):
                self.assertIn(rel, project_reads.files, rel)
                self.assertIn(rel, sources, rel)
            # api-surface consumes none of these -- only project.pbxproj.
            _r2, project_reads_api, sources_api, _res2 = self.swift._scan(root, "api-surface")
            self.assertEqual(project_reads_api.files, {})
            for rel in ("App.xcworkspace/contents.xcworkspacedata", "App.xcconfig", "project.yml"):
                self.assertNotIn(rel, sources_api, rel)

    def test_scan_bundle_census_reports_missing_and_non_regular_pbxproj(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "A.swift").write_text("struct A {}\n")
            # Missing: an .xcodeproj bundle holding no project.pbxproj at all.
            (root / "NoPbx.xcodeproj").mkdir()
            # Regular: a real project.pbxproj.
            real_proj = root / "Real.xcodeproj"
            real_proj.mkdir()
            (real_proj / "project.pbxproj").write_text("// !$*UTF8*$!\n")
            # Non-regular: project.pbxproj is a symlink to a real file elsewhere.
            target = root / "Elsewhere.pbxproj"
            target.write_text("// !$*UTF8*$!\n")
            link_proj = root / "Linked.xcodeproj"
            link_proj.mkdir()
            (link_proj / "project.pbxproj").symlink_to(target)
            _reads, project_reads, _sources, _residuals = self.swift._scan(root, "module-graph")
            by_bundle = {b: (present, regular) for b, present, regular in project_reads.bundles}
            self.assertEqual(by_bundle["NoPbx.xcodeproj"], (False, False))
            self.assertEqual(by_bundle["Real.xcodeproj"], (True, True))
            self.assertEqual(by_bundle["Linked.xcodeproj"], (True, False))
            # The symlinked pbxproj was attempted and refused, not silently dropped.
            self.assertEqual(project_reads.refusals.get("Linked.xcodeproj/project.pbxproj"), "not-regular")
            self.assertNotIn("Linked.xcodeproj/project.pbxproj", project_reads.files)

    def test_scan_pbxproj_honors_the_16mib_bound_not_the_2mb_one(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "A.swift").write_text("struct A {}\n")
            proj = root / "Big.xcodeproj"
            proj.mkdir()
            pbx = proj / "project.pbxproj"
            # 3 MB: over the Swift-source 2 MB bound, under the pbxproj 16 MiB one.
            pbx.write_bytes(b"x" * (3 * 1024 * 1024))
            _reads, project_reads, sources, _residuals = self.swift._scan(root, "api-surface")
            rel = "Big.xcodeproj/project.pbxproj"
            self.assertIn(rel, project_reads.files)
            self.assertIn(rel, sources)
            self.assertEqual(project_reads.refusals, {})

    def test_scan_pbxproj_over_16mib_is_refused_as_oversize(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "A.swift").write_text("struct A {}\n")
            proj = root / "Huge.xcodeproj"
            proj.mkdir()
            pbx = proj / "project.pbxproj"
            pbx.write_bytes(b"x" * (self.swift._MAX_PBXPROJ_BYTES + 1))
            _reads, project_reads, sources, _residuals = self.swift._scan(root, "api-surface")
            rel = "Huge.xcodeproj/project.pbxproj"
            self.assertEqual(project_reads.refusals.get(rel), "oversize")
            self.assertNotIn(rel, project_reads.files)
            self.assertNotIn(rel, sources)

    def test_scan_shares_one_budget_across_swift_and_project_candidates(self):
        # ADR-0130 clause 2: "Every read counts against the aggregate
        # per-concern file and byte caps." A project input and a Swift file
        # compete for the SAME cap: capping the aggregate at 1 file reads
        # only the alphabetically-first candidate, whichever kind it is.
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Z.swift").write_text("struct Z {}\n")
            proj = root / "A.xcodeproj"
            proj.mkdir()
            (proj / "project.pbxproj").write_text("// !$*UTF8*$!\n")
            with mock.patch.object(self.swift, "_MAX_SCAN_FILES", 1):
                reads, project_reads, sources, residuals = self.swift._scan(root, "api-surface")
            self.assertEqual(len(reads) + len(project_reads.files), 1)
            # The one candidate read is the alphabetically-first repo-relative
            # path: "A.xcodeproj/project.pbxproj" sorts before "Z.swift".
            self.assertIn("A.xcodeproj/project.pbxproj", sources)
            self.assertNotIn("Z.swift", sources)
            cap_classes = [r[0] for r in residuals] + [r[0] for r in project_reads.residuals]
            self.assertIn("scan-cap", cap_classes)


MANIFESTS = Path(__file__).resolve().parent / "fixtures" / "swiftmanifests"


def _fresh_swift():
    """The pack module with its per-derive parse cache emptied, so a test's
    monkeypatch reaches every file it derives."""
    swift = _swift_module()
    swift._CACHE.update(root=None, files={}, manifests={})
    return swift


def _core():
    return importlib.import_module("crux.arch.core")


def _with_ancestors(root_node):
    """Every node under `root_node` with its ancestors, parent first, from one
    explicit-stack walk: the shape `_is_benign_missing_bang` reads."""
    stack = [(root_node, ())]
    while stack:
        node, ancestors = stack.pop()
        yield node, ancestors
        stack.extend((c, (node,) + ancestors) for c in reversed(node.children))


def _section_rows(markdown: str, heading: str) -> list[dict]:
    """Rows of the pipe table under `## <heading>`, keyed by header cell.

    Written for these tests alone, so the renderer is checked by a reader that
    shares no code with it or with the corpus matcher.
    """
    rows: list[dict] = []
    header = None
    inside = False
    for line in markdown.split("\n"):
        if line.startswith("## "):
            inside = line == f"## {heading}"
            header = None
            continue
        if not inside or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if header is None:
            header = cells
            continue
        if set(line.replace("|", "")) <= {"-"}:
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def _unquote(cell: str) -> str:
    return cell[1:-1] if len(cell) >= 2 and cell.startswith("`") and cell.endswith("`") else cell


def _at(cell: str) -> tuple:
    path, rng = _unquote(cell).rsplit(":", 1)
    a, b = rng.split("-")
    return path, (int(a), int(b))


def _residual_bullets(markdown: str) -> set:
    """`(class, path, lines, detail)` for every bullet under `## Residuals`."""
    out = set()
    inside = False
    for line in markdown.split("\n"):
        if line.startswith("## "):
            inside = line == "## Residuals"
            continue
        if not inside or not line.startswith("- `"):
            continue
        parts = line.split("`")
        klass, path = parts[1], parts[3]
        rest = line.split("` lines ", 1)[1]
        if rest.startswith("— — "):
            lines, detail = None, rest[len("— — "):]
        else:
            lines, detail = rest.split(" — ", 1)
        out.add((klass, path, lines, detail))
    return out


def _real_path_open_recorder():
    """An `open` audit hook and the two lists it fills: each opened path as
    passed, and the same path resolved. An open that follows an in-checkout
    symlink is recorded under the in-checkout name, so only the resolved list
    shows where the bytes came from (see the aliasing control in
    `DetectGeneratorFormsTests`)."""
    import os
    as_passed, resolved = [], []

    def hook(event, args):
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            as_passed.append(os.fsdecode(args[0]))
            resolved.append(os.path.realpath(args[0]))
    return hook, as_passed, resolved


def _edges(markdown: str) -> set:
    out = set()
    for line in markdown.split("\n"):
        if "-->" not in line or not line.startswith("  "):
            continue
        left, right = line.split(" --> ")
        out.add((left.split('["', 1)[1][:-2], right.split('["', 1)[1][:-2]))
    return out


def _derive_fixture(swift, source: Path):
    """The three rendered concerns for one fixture file, derived alone."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / source.name).write_bytes(source.read_bytes())
        return {
            "data-model": swift.extract_data_model(root, "bionic")[0],
            "api-surface": swift.extract_api_surface(root, "bionic")[0],
            "module-graph": swift.extract_module_graph(root, "bionic")[0],
        }


def _derive_tree(swift, source_dir: Path):
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "case"
        shutil.copytree(source_dir, root)
        return {
            "data-model": swift.extract_data_model(root, "bionic")[0],
            "api-surface": swift.extract_api_surface(root, "bionic")[0],
            "module-graph": swift.extract_module_graph(root, "bionic")[0],
        }


class RendererTests(unittest.TestCase):
    """The renderers' shapes, and the four ErrorLogDatabase facts through the
    full extractor path (ADR-0129 clause 7's recovery postcondition)."""

    def setUp(self):
        self.swift = _fresh_swift()

    def test_error_log_database_renders_through_full_extractor_path(self):
        head = _real_file_head()
        if head is None or not REAL_FILE.exists():
            self.skipTest(FETCH_HINT)
        self.assertEqual(head, PINNED_NETNEWSWIRE_HEAD)
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rel = "Modules/ErrorLog/Sources/ErrorLog/ErrorLogDatabase.swift"
            (root / rel).parent.mkdir(parents=True)
            (root / rel).write_bytes(REAL_FILE.read_bytes())
            dm, dm_sources = self.swift.extract_data_model(root, "bionic")
            api, _ = self.swift.extract_api_surface(root, "bionic")
            self.assertIn(f"| `ErrorLogDatabase` | actor | public | `{rel}:13-13` | — |", dm)
            self.assertIn(f"| `ErrorLogDatabase` | `databasePath` | `String` | public | `{rel}:15-15` |", dm)
            self.assertIn(f"| `ErrorLogDatabase.init(databasePath:)` | init | public | `{rel}:23-23` |", api)
            self.assertIn(
                "| `ErrorLogDatabase.addEntry(sourceName:sourceID:operation:fileName:functionName:"
                f"lineNumber:errorMessage:)` | func | public | `{rel}:37-37` |", api)
            recovered = [b for b in _residual_bullets(api) if b[0] == "declaration-recovered"]
            self.assertEqual(len(recovered), 1)
            self.assertEqual(recovered[0][1:3], (rel, "13-67"))
            self.assertIn("recovered from lines 13-47", recovered[0][3])
            self.assertEqual(list(dm_sources), [rel])

    def test_module_graph_renders_package_container_and_target(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Package.swift").write_text(
                'let package = Package(\n'
                '    name: "MyLib",\n'
                '    products: [.library(name: "MyLib", targets: ["MyLib"])],\n'
                '    targets: [.target(name: "MyLib", dependencies: [])]\n'
                ')\n'
            )
            md, sources = self.swift.extract_module_graph(root, "bionic")
            self.assertIn("| `Package.swift` | swift package |", md)
            self.assertIn("| `MyLib` | `Package.swift` | library | — | `Package.swift:4-4` |", md)
            self.assertEqual(list(sources), ["Package.swift"])

    def _graph_under_edge_bound(self, bound: int) -> str:
        """The module graph of a three-target package whose manifest draws
        three edges (A -> B, A -> C, B -> C), rendered under `bound`."""
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Package.swift").write_text(
                'let package = Package(name: "P", targets: [\n'
                '    .target(name: "A", dependencies: ["B", "C"]),\n'
                '    .target(name: "B", dependencies: ["C"]),\n'
                '    .target(name: "C"),\n'
                '])\n')
            with mock.patch.object(self.swift, "_MAX_GRAPH_EDGES", bound):
                md, _ = self.swift.extract_module_graph(root, "bionic")
        return md

    def test_module_graph_over_the_edge_bound_renders_the_first_edges_and_a_scan_cap(self):
        md = self._graph_under_edge_bound(2)
        self.assertEqual(_edges(md), {("A (Package.swift)", "B (Package.swift)"),
                                      ("A (Package.swift)", "C (Package.swift)")})
        caps = [b for b in _residual_bullets(md) if b[0] == "scan-cap"]
        # ADR-0129 clause 7 (`scan-cap`): the bounded edge set cannot count
        # the full set, so the line states the bound, not the total.
        self.assertEqual(caps, [("scan-cap", ".", None, "the module graph holds more than 2 edges; 2 render")])

    def test_module_graph_at_the_edge_bound_renders_every_edge_and_no_scan_cap(self):
        md = self._graph_under_edge_bound(3)
        self.assertEqual(_edges(md), {("A (Package.swift)", "B (Package.swift)"),
                                      ("A (Package.swift)", "C (Package.swift)"),
                                      ("B (Package.swift)", "C (Package.swift)")})
        self.assertEqual([b for b in _residual_bullets(md) if b[0] == "scan-cap"], [])

    def test_residuals_section_absent_when_no_bullets(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "A.swift").write_text("public struct Foo {}\n")
            md, _ = self.swift.extract_data_model(root, "bionic")
            self.assertNotIn("## Residuals", md)

    def test_no_row_carries_a_triple_hash_heading(self):
        render = _derive_fixture(self.swift, FIXTURES / "04-if-os.swift")
        for concern, md in render.items():
            with self.subTest(concern=concern):
                self.assertFalse([ln for ln in md.split("\n") if ln.startswith("### ")])

    def test_project_facts_producer_is_empty_when_no_bundle_is_named(self):
        # An empty `ProjectReads` (no `*.xcodeproj` bundle the walk
        # reached) yields an empty `ProjectFacts` -- there is nothing to
        # read. An isolated empty temp directory stands in for the checkout
        # root: `_generator_residuals` walks the WHOLE checkout
        # looking for nested Tuist/XcodeGen candidates, so `Path(".")` --
        # this dev repo's own root, carrying real `project.yml` fixtures
        # under `crux/scripts/tests/fixtures/` -- is no longer an inert
        # placeholder root.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            pf = self.swift._project_facts(Path(d), [], self.swift.ProjectReads())
        self.assertEqual(pf, self.swift.ProjectFacts())

    def test_main_owning_target_comes_from_the_literal_manifest(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Package.swift").write_text(
                'let package = Package(name: "T", targets: [\n'
                '    .executableTarget(name: "Tool"),\n'
                '    .executableTarget(name: "Other", path: "Custom/Other"),\n'
                '])\n')
            (root / "Sources" / "Tool").mkdir(parents=True)
            (root / "Sources" / "Tool" / "Main.swift").write_text("@main struct ToolMain {}\n")
            (root / "Custom" / "Other").mkdir(parents=True)
            (root / "Custom" / "Other" / "Entry.swift").write_text(
                "import Tool\n@main enum OtherMain {}\n")
            (root / "Loose.swift").write_text("@main struct LooseMain {}\n")
            api, _ = self.swift.extract_api_surface(root, "bionic")
            mains = {_unquote(r["@main type"]): r["owning target"]
                     for r in _section_rows(api, "@main declarations")}
            self.assertEqual(mains, {
                "ToolMain": "`Tool (Package.swift)`",
                "OtherMain": "`Other (Package.swift)`",
                "LooseMain": "—",
            })
            mg, _ = self.swift.extract_module_graph(root, "bionic")
            imports = _section_rows(mg, "Imports")
            self.assertEqual(len(imports), 1)
            self.assertEqual(imports[0]["owning target"], "`Other (Package.swift)`")
            self.assertEqual(imports[0]["resolves to"], "`Tool (Package.swift)`")
            self.assertIn(("Other (Package.swift)", "Tool (Package.swift)"), _edges(mg))

    def test_two_derives_are_byte_identical(self):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            shutil.copytree(FIXTURES, root / "Sources" / "Decls")
            shutil.copytree(MANIFESTS / "literal-subset", root / "Pkg")
            first = [f(root, "bionic") for f in (self.swift.extract_data_model,
                                                self.swift.extract_api_surface,
                                                self.swift.extract_module_graph)]
            self.swift._CACHE.update(root=None, files={}, manifests={})
            second = [f(root, "bionic") for f in (self.swift.extract_data_model,
                                                 self.swift.extract_api_surface,
                                                 self.swift.extract_module_graph)]
            self.assertEqual(first, second)


class RealXcodeReaderIntegrationTests(unittest.TestCase):
    """`swift_xcode.read_projects` wired into `_project_facts` end to
    end -- a real `.xcodeproj`/`project.pbxproj` on disk, read through the
    real pipeline (no monkeypatched `_project_facts`), renders a `@main`
    owning-target cell for a file that is a member through the
    folder-synced route (ADR-0130 clause 16's postcondition: "the owning-
    target cell names every target whose resolved membership includes the
    file")."""

    _PBXPROJ = (
        "// !$*UTF8*$!\n"
        "{\n"
        "\tarchiveVersion = 1;\n"
        "\tobjectVersion = 56;\n"
        "\trootObject = PROJ;\n"
        "\tobjects = {\n"
        "\t\tPROJ = {\n"
        "\t\t\tisa = PBXProject;\n"
        "\t\t\tmainGroup = MAIN;\n"
        "\t\t\ttargets = (\n"
        "\t\t\t\tT,\n"
        "\t\t\t);\n"
        "\t\t};\n"
        "\t\tMAIN = {\n"
        "\t\t\tisa = PBXGroup;\n"
        '\t\t\tsourceTree = "<group>";\n'
        "\t\t\tchildren = (\n"
        "\t\t\t\tROOT,\n"
        "\t\t\t);\n"
        "\t\t};\n"
        "\t\tROOT = {\n"
        "\t\t\tisa = PBXFileSystemSynchronizedRootGroup;\n"
        '\t\t\tsourceTree = "<group>";\n'
        "\t\t\tpath = Sources;\n"
        "\t\t};\n"
        "\t\tT = {\n"
        "\t\t\tisa = PBXNativeTarget;\n"
        "\t\t\tname = App;\n"
        '\t\t\tproductType = "com.apple.product-type.application";\n'
        "\t\t\tbuildPhases = (\n"
        "\t\t\t);\n"
        "\t\t\tfileSystemSynchronizedGroups = (\n"
        "\t\t\t\tROOT,\n"
        "\t\t\t);\n"
        "\t\t};\n"
        "\t};\n"
        "}\n"
    )

    def test_main_in_synced_root_renders_owning_target_qualified_by_container(self):
        import tempfile
        self.swift = _fresh_swift()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            proj = root / "App.xcodeproj"
            proj.mkdir()
            (proj / "project.pbxproj").write_text(self._PBXPROJ)
            (root / "Sources").mkdir()
            (root / "Sources" / "Main.swift").write_text("@main struct AppMain {}\n")
            api, _ = self.swift.extract_api_surface(root, "bionic")
        mains = {_unquote(r["@main type"]): r["owning target"]
                 for r in _section_rows(api, "@main declarations")}
        self.assertEqual(mains, {"AppMain": "`App (App.xcodeproj)`"})


class ProjectFactsRenderContractTests(unittest.TestCase):
    """The render contract for every `ProjectFacts` row form the Xcode reader
    produces (ADR-0129 clause 10), exercised against a monkeypatched
    `_project_facts` so each row form is driven in isolation. The render
    code existed before these tests, so they could not go RED against it;
    each one was confirmed non-vacuous by a mutation control (temporarily
    breaking the renderer line it covers, observing the assertion fail,
    then restoring the line), recorded in the run's developer report
    rather than committed here."""

    def setUp(self):
        self.swift = _fresh_swift()
        self._orig_project_facts = self.swift._project_facts

    def tearDown(self):
        self.swift._project_facts = self._orig_project_facts

    def _patch(self, **kwargs):
        pf = self.swift.ProjectFacts(**kwargs)
        self.swift._project_facts = lambda root, manifests, reads, collection=None: pf
        return pf

    def test_xcode_target_row_and_six_column_header(self):
        self._patch(targets=({
            "name": "App", "container": "App.xcodeproj", "kind": "app",
            "product_type": "application", "path": "App.xcodeproj/project.pbxproj",
            "loc": (10, 20), "conditional": False,
        },))
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            md, _ = self.swift.extract_module_graph(Path(d), "bionic")
        self.assertIn(
            "| target | container | target kind | product type | conditional | declared at |", md)
        self.assertEqual(_section_rows(md, "Targets"), [{
            "target": "`App`", "container": "`App.xcodeproj`", "target kind": "app",
            "product type": "application", "conditional": "—",
            "declared at": "`App.xcodeproj/project.pbxproj:10-20`",
        }])

    def test_five_column_header_byte_identical_with_no_xcode_target(self):
        self._patch()
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Package.swift").write_text(
                'let package = Package(\n'
                '    name: "MyLib",\n'
                '    products: [],\n'
                '    targets: [.target(name: "MyLib", dependencies: [])]\n'
                ')\n')
            md, _ = self.swift.extract_module_graph(root, "bionic")
        self.assertIn("| target | container | target kind | conditional | declared at |", md)
        self.assertNotIn("product type", md)

    def test_target_dependency_edge_and_xcode_node_label(self):
        self._patch(target_deps=({"from": "App", "to": "Lib", "container": "App.xcodeproj"},))
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            md, _ = self.swift.extract_module_graph(Path(d), "bionic")
        self.assertIn(("App (App.xcodeproj)", "Lib (App.xcodeproj)"), _edges(md))

    def test_cross_project_target_dependency_keeps_the_declaring_node(self):
        """A cross-project edge starts at the declaring project's node and
        ends at the other project's node (ADR-0130 clause 6)."""
        self._patch(target_deps=({"from": "App", "to": "Lib", "container": "App.xcodeproj",
                                  "to_container": "Lib.xcodeproj"},))
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            md, _ = self.swift.extract_module_graph(Path(d), "bionic")
        self.assertIn(("App (App.xcodeproj)", "Lib (Lib.xcodeproj)"), _edges(md))
        self.assertNotIn(("App (Lib.xcodeproj)", "Lib (Lib.xcodeproj)"), _edges(md))

    def test_resolved_product_dependency_draws_an_edge_not_a_row(self):
        self._patch(product_deps=({
            "from": "App", "container": "App.xcodeproj", "kind": "product",
            "product": "Core", "location": None, "requirement": None,
            "path": "App.xcodeproj/project.pbxproj", "loc": (30, 30),
            "edge_to": ("App.xcodeproj", "Core"),
        },))
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            md, _ = self.swift.extract_module_graph(Path(d), "bionic")
        self.assertIn(("App (App.xcodeproj)", "Core (App.xcodeproj)"), _edges(md))
        self.assertEqual(_section_rows(md, "Dependencies"), [])

    def test_remote_product_dependency_renders_a_row(self):
        self._patch(product_deps=({
            "from": "App", "container": "App.xcodeproj", "kind": "remote product",
            "product": "Alamofire", "location": "https://example.com/Alamofire",
            "requirement": "upToNextMajor 5.0.0",
            "path": "App.xcodeproj/project.pbxproj", "loc": (40, 40),
            "edge_to": None,
        },))
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            md, _ = self.swift.extract_module_graph(Path(d), "bionic")
        self.assertEqual(_section_rows(md, "Dependencies"), [{
            "from": "`App`", "dependency": "`Alamofire`", "dependency kind": "remote product",
            "location": "`https://example.com/Alamofire`", "requirement": "upToNextMajor 5.0.0",
            "declared at": "`App.xcodeproj/project.pbxproj:40-40`",
        }])

    def test_project_remote_reference_row_from_is_the_literal_project(self):
        self._patch(dependencies=({
            "location": "https://example.com/bar", "requirement": "upToNextMajor 1.0.0",
            "path": "App.xcodeproj/project.pbxproj", "loc": (50, 50),
        },))
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            md, _ = self.swift.extract_module_graph(Path(d), "bionic")
        rows = _section_rows(md, "Dependencies")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["from"], "`project`")
        self.assertEqual(rows[0]["location"], "`https://example.com/bar`")
        self.assertEqual(rows[0]["requirement"], "upToNextMajor 1.0.0")
        self.assertEqual(rows[0]["declared at"], "`App.xcodeproj/project.pbxproj:50-50`")

    def test_plugin_product_dependency_row_kind(self):
        self._patch(product_deps=({
            "from": "App", "container": "App.xcodeproj", "kind": "plugin product",
            "product": "SwiftLintPlugin", "location": None, "requirement": None,
            "path": "App.xcodeproj/project.pbxproj", "loc": (45, 45),
            "edge_to": None,
        },))
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            md, _ = self.swift.extract_module_graph(Path(d), "bionic")
        rows = _section_rows(md, "Dependencies")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dependency kind"], "plugin product")

    def test_membership_rows_sorted_covering_every_route(self):
        memberships = tuple(
            {"file": f, "target": t, "container": "App.xcodeproj", "route": r,
             "root": None, "loc": (i, i), "conditional": False,
             "path": "App.xcodeproj/project.pbxproj"}
            for i, (f, t, r) in enumerate([
                ("Sources/C.swift", "App", "classic Sources build phase"),
                ("Sources/A.swift", "App", "added by an exception set"),
                ("Sources/B.swift", "App", "excluded by an exception set"),
                ("Sources/D.swift", "App", "folder-synced root Sources"),
            ], start=1))
        self._patch(memberships=memberships)
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            md, _ = self.swift.extract_module_graph(Path(d), "bionic")
        rows = _section_rows(md, "Membership")
        files_in_order = [_unquote(r["file"]) for r in rows]
        self.assertEqual(files_in_order, sorted(files_in_order))
        routes = {_unquote(r["file"]): r["route"] for r in rows}
        self.assertEqual(routes, {
            "Sources/A.swift": "added by an exception set",
            "Sources/B.swift": "excluded by an exception set",
            "Sources/C.swift": "classic Sources build phase",
            "Sources/D.swift": "folder-synced root Sources",
        })

    def test_main_owning_target_cell_several_owners_and_dash(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Shared.swift").write_text("@main struct SharedMain {}\n")
            (root / "Lonely.swift").write_text("@main struct LonelyMain {}\n")
            memberships = (
                {"file": "Shared.swift", "target": "Widget", "container": "App.xcodeproj",
                 "route": "classic Sources build phase", "root": None, "loc": (1, 1),
                 "conditional": False, "path": "App.xcodeproj/project.pbxproj"},
                {"file": "Shared.swift", "target": "App", "container": "App.xcodeproj",
                 "route": "classic Sources build phase", "root": None, "loc": (2, 2),
                 "conditional": False, "path": "App.xcodeproj/project.pbxproj"},
            )
            self._patch(memberships=memberships)
            api, _ = self.swift.extract_api_surface(root, "bionic")
        mains = {_unquote(r["@main type"]): r["owning target"]
                 for r in _section_rows(api, "@main declarations")}
        self.assertEqual(mains, {
            "SharedMain": "`App (App.xcodeproj), Widget (App.xcodeproj)`",
            "LonelyMain": "—",
        })

    def test_import_owner_edges_resolve_against_xcode_target_names(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Consumer.swift").write_text("import Widget\n")
            targets = ({
                "name": "Widget", "container": "App.xcodeproj", "kind": "library",
                "product_type": "framework", "path": "App.xcodeproj/project.pbxproj",
                "loc": (5, 5), "conditional": False,
            },)
            memberships = ({
                "file": "Consumer.swift", "target": "App", "container": "App.xcodeproj",
                "route": "classic Sources build phase", "root": None, "loc": (6, 6),
                "conditional": False, "path": "App.xcodeproj/project.pbxproj",
            },)
            self._patch(targets=targets, memberships=memberships)
            mg, _ = self.swift.extract_module_graph(root, "bionic")
        imports = _section_rows(mg, "Imports")
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0]["owning target"], "`App (App.xcodeproj)`")
        self.assertEqual(imports[0]["resolves to"], "`Widget (App.xcodeproj)`")
        self.assertIn(("App (App.xcodeproj)", "Widget (App.xcodeproj)"), _edges(mg))

    def test_project_residuals_render_in_module_graph_and_read_level_in_api_surface(self):
        # A module-graph-only class from the closed set (`unresolved-
        # reference`) stands in for every project-level class that renders
        # in module-graph only.
        residuals = (
            ("unresolved-reference", "App.xcodeproj/project.pbxproj", [(7, 7)],
             "a project-level residual"),
            ("oversize", "App.xcodeproj/project.pbxproj", None, "project.pbxproj exceeds the bound"),
        )
        self._patch(residuals=residuals)
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            mg, _ = self.swift.extract_module_graph(root, "bionic")
            api, _ = self.swift.extract_api_surface(root, "bionic")
        mg_classes = {b[0] for b in _residual_bullets(mg)}
        api_classes = {b[0] for b in _residual_bullets(api)}
        self.assertEqual(mg_classes, {"unresolved-reference", "oversize"})
        self.assertEqual(api_classes, {"oversize"})


class FixtureFactsTests(unittest.TestCase):
    """ADR-0129 clause 9(d): every declaration fixture extracts exactly as its
    expected file states. Each listed section is compared as an exact set, so
    a missing row and an extra row both fail."""

    def setUp(self):
        self.swift = _fresh_swift()

    def _check(self, name: str, expected: dict, render: dict):
        fname = f"{name}.swift"

        def at(values):
            return (fname, tuple(values))

        if "types" in expected:
            got = {(_unquote(r["type"]), r["kind"], r["access"], _at(r["declared at"]),
                    r["conditional"] == "yes")
                   for r in _section_rows(render["data-model"], "Types")}
            want = {(t["name"], t["kind"], t["access"], at(t["at"]), t["conditional"])
                    for t in expected["types"]}
            self.assertEqual(got, want, f"{name}: types")
        if "stored_properties" in expected:
            got = {(_unquote(r["owner"]), _unquote(r["property"]),
                    None if r["declared type"] == "—" else _unquote(r["declared type"]),
                    r["access"], _at(r["declared at"]))
                   for r in _section_rows(render["data-model"], "Stored properties")}
            want = {(p["owner"], p["name"], p["type"], p["access"], at(p["at"]))
                    for p in expected["stored_properties"]}
            self.assertEqual(got, want, f"{name}: stored properties")
        if "relationships" in expected:
            got = {(_unquote(r["from type"]), r["relation"], _unquote(r["to type"]),
                    _at(r["declared at"]))
                   for r in _section_rows(render["data-model"], "Relationships")}
            want = {(r["from"], r["relation"], r["to"], at(r["at"]))
                    for r in expected["relationships"]}
            self.assertEqual(got, want, f"{name}: relationships")
        if "interfaces" in expected:
            got = {(_unquote(r["interface"]), r["kind"], r["access"], _at(r["declared at"]),
                    r["attributes"], r["conditional"] == "yes")
                   for r in _section_rows(render["api-surface"], "Interfaces")}
            want = {(i["name"], i["kind"], i["access"], at(i["at"]),
                     ", ".join(i["attributes"]) if i["attributes"] else "—", i["conditional"])
                    for i in expected["interfaces"]}
            self.assertEqual(got, want, f"{name}: interfaces")
        if "requirements" in expected:
            got = {(_unquote(r["protocol"]), _unquote(r["requirement"]), r["kind"],
                    _at(r["declared at"]))
                   for r in _section_rows(render["api-surface"], "Protocol requirements")}
            want = {(r["protocol"], r["name"], r["kind"], at(r["at"]))
                    for r in expected["requirements"]}
            self.assertEqual(got, want, f"{name}: requirements")
        if "mains" in expected:
            got = {(_unquote(r["@main type"]), r["kind"], _at(r["declared at"]))
                   for r in _section_rows(render["api-surface"], "@main declarations")}
            want = {(m["type"], m["kind"], at(m["at"])) for m in expected["mains"]}
            self.assertEqual(got, want, f"{name}: @main declarations")
        if "imports" in expected:
            got = {(_unquote(r["module"]), r["import kind"], _at(r["file"])[1][0])
                   for r in _section_rows(render["module-graph"], "Imports")}
            want = {(i["module"], i["kind"], i["line"]) for i in expected["imports"]}
            self.assertEqual(got, want, f"{name}: imports")
        if "residuals" in expected:
            for concern in ("data-model", "api-surface"):
                got = {(k, lines, detail) for k, path, lines, detail in
                       _residual_bullets(render[concern])}
                want = {(r["class"], r["lines"], r["detail"]) for r in expected["residuals"]
                        if r["concern"] == concern}
                self.assertEqual(got, want, f"{name}: {concern} residuals")

    def test_every_fixture_matches_its_expected_facts(self):
        import yaml
        expected_files = sorted(FIXTURES.glob("[0-9][0-9]-*.expected.yml"))
        # 17 mandatory fixtures plus the `-conditional` twin of 13 (ADR-0129 clause 7).
        self.assertEqual(len(expected_files), 18)
        for expected_path in expected_files:
            name = expected_path.name[: -len(".expected.yml")]
            with self.subTest(fixture=name):
                expected = yaml.safe_load(expected_path.read_text(encoding="utf-8"))
                render = _derive_fixture(self.swift, FIXTURES / f"{name}.swift")
                self._check(name, expected, render)

    def test_mandatory_fixtures_01_through_17_all_exist(self):
        missing = []
        for n in range(1, 18):
            sources = [p for p in FIXTURES.glob(f"{n:02d}-*.swift")
                       if not p.stem.endswith(("-control", "-conditional"))]
            if len(sources) != 1 or not sources[0].with_suffix(".expected.yml").exists():
                missing.append(n)
        self.assertEqual(missing, [])

    def test_the_harness_fails_on_an_extra_row(self):
        """Positive control: one row the expected file does not name turns the
        comparison red, so the exact-set check reads the rendered file."""
        import yaml
        expected = yaml.safe_load((FIXTURES / "01-actor.expected.yml").read_text())
        render = _derive_fixture(self.swift, FIXTURES / "01-actor.swift")
        render["data-model"] = render["data-model"].replace(
            "| `Counter` | actor |", "| `Extra` | struct | public | `01-actor.swift:1-1` | — |\n"
                                   "| `Counter` | actor |")
        with self.assertRaises(AssertionError):
            self._check("01-actor", expected, render)

    def test_benign_missing_bang_matches_the_same_code_without_parentheses(self):
        source = (FIXTURES / "17-benign-missing-bang.swift").read_text()
        tree = self.swift._parse(source.encode())
        missing = [(n, a) for n, a in _with_ancestors(tree.root_node) if n.is_missing]
        self.assertEqual(len(missing), 1, "the fixture no longer produces the grammar's MISSING `!`")
        self.assertTrue(self.swift._is_benign_missing_bang(*missing[0]))
        self.assertEqual(self.swift._stray_errors(tree.root_node, frozenset()), [])
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a"
            b = Path(d) / "b"
            a.mkdir()
            b.mkdir()
            (a / "W.swift").write_text(source)
            (b / "W.swift").write_text(source.replace("@Stored()", "@Stored"))
            self.assertEqual(self.swift.extract_data_model(a, "x")[0],
                             self.swift.extract_data_model(b, "x")[0])

    def test_benign_shape_positive_control_an_argument_is_an_ordinary_error(self):
        # The same inserted `!` after an empty attribute on a FUNCTION is not
        # the benign shape, so it stays an ordinary parse error.
        tree = self.swift._parse(b"struct W {\n\t@Stored() func f() {}\n}\n")
        errors = self.swift._stray_errors(tree.root_node, frozenset())
        self.assertTrue(errors, "the control input no longer produces an error node")
        bad = [(n, a) for n, a in _with_ancestors(tree.root_node) if n.is_missing or n.is_error]
        self.assertTrue(bad)
        self.assertFalse(any(self.swift._is_benign_missing_bang(n, a) for n, a in bad))


class ManifestFixtureTests(unittest.TestCase):
    """ADR-0129 clauses 4 and 9(d): the literal `Package.swift` subset."""

    def setUp(self):
        self.swift = _fresh_swift()

    def _check(self, case: str):
        import yaml
        expected = yaml.safe_load((MANIFESTS / case / "expected.yml").read_text(encoding="utf-8"))
        render = _derive_tree(self.swift, MANIFESTS / case)
        mg, api = render["module-graph"], render["api-surface"]
        got = {_unquote(r["container"]) for r in _section_rows(mg, "Containers")}
        self.assertEqual(got, set(expected["containers"]), "containers")
        got = {(_unquote(r["product"]), r["product kind"], _unquote(r["container"]),
                _at(r["declared at"])[1]) for r in _section_rows(api, "Products")}
        want = {(p["name"], p["kind"], p["container"], tuple(p["at"])) for p in expected["products"]}
        self.assertEqual(got, want, "products")
        core = _core()
        got = {(_unquote(r["target"]), _unquote(r["container"]), r["target kind"],
                r["conditional"] == "yes", _at(r["declared at"])[1])
               for r in _section_rows(mg, "Targets")}
        want = {(core._cell(t["name"]), t["container"], t["kind"], t["conditional"], tuple(t["at"]))
                for t in expected["targets"]}
        self.assertEqual(got, want, "targets")
        self.assertEqual(_edges(mg), {tuple(e) for e in expected["edges"]}, "edges")
        got = {(_unquote(r["from"]), _unquote(r["dependency"]), r["dependency kind"],
                None if r["location"] == "—" else _unquote(r["location"]),
                None if r["requirement"] == "—" else r["requirement"], _at(r["declared at"]))
               for r in _section_rows(mg, "Dependencies")}
        want = {(d["from"], d["dependency"], d["kind"], d["location"], d["requirement"],
                 (d["path"], tuple(d["at"]))) for d in expected["dependencies"]}
        self.assertEqual(got, want, "dependencies")
        got = {(k, p, lines) for k, p, lines, _d in _residual_bullets(mg)}
        want = {(r["class"], r["path"], r["lines"]) for r in expected["residuals"]}
        self.assertEqual(got, want, "module-graph residuals")
        return render

    def test_literal_subset(self):
        self._check("literal-subset")

    def test_non_literal_constructs(self):
        render = self._check("non-literal")
        kinds = {d.split(" is outside", 1)[0] for k, _p, _l, d in _residual_bullets(render["module-graph"])
                 if k == "non-literal-manifest"}
        self.assertEqual(kinds, {f"construct {k}" for k in self.swift._NON_LITERAL_KINDS})

    def test_if_block_inside_a_list(self):
        """An `#if` inside a list keeps every element: conditional inside the
        block, unconditional after `#endif`, one residual per block."""
        render = self._check("if-in-list")
        kinds = {d.split(" is outside", 1)[0] for k, _p, _l, d in _residual_bullets(render["module-graph"])
                 if k == "non-literal-manifest"}
        self.assertEqual(kinds, {"construct #if block"})

    def test_path_dependency_normalised_or_escaping(self):
        render = self._check("path-dependency")
        for md in render.values():
            self.assertNotIn("outside", md)
            self.assertNotIn("/etc", md)

    def test_path_dependency_cache_recomputes_real_path_containment(self):
        # ADR-0129 clause 4: a cached manifest entry is a pure function of
        # `(rel, sha256)`. The `.package(path:)` real-path containment check
        # reads live filesystem state (a symlink target), so it must run
        # OUTSIDE `_cached` -- otherwise a second derive in the same process,
        # against the identical manifest bytes, would replay the FIRST
        # derive's containment verdict instead of the second's.
        import tempfile
        swift = _fresh_swift()
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            root = Path(d)
            (root / "Package.swift").write_text(
                "// swift-tools-version:5.9\n"
                "import PackageDescription\n"
                "let package = Package(\n"
                "    name: \"App\",\n"
                "    dependencies: [\n"
                "        .package(path: \"Sibling\"),\n"
                "    ]\n"
                ")\n"
            )
            elsewhere = Path(outside) / "Elsewhere"
            elsewhere.mkdir()
            (root / "Sibling").symlink_to(elsewhere, target_is_directory=True)

            first = swift.extract_module_graph(root, "bionic")[0]
            self.assertIn("path-escape", first)
            self.assertNotIn("path dependency", first)

            inside = root / "Inside"
            inside.mkdir()
            (root / "Sibling").unlink()
            (root / "Sibling").symlink_to(inside, target_is_directory=True)

            second = swift.extract_module_graph(root, "bionic")[0]
            self.assertIn("path dependency", second)
            self.assertNotIn("path-escape", second)

    def test_path_dependency_cache_recomputes_refused_identities(self):
        # The refused `.package(path:)` identities are the live half of the
        # same resolution: the first derive refuses `Sibling` (it escapes),
        # the second finds it a real in-checkout package. A refusal carried
        # over from the first derive through the cached entry would keep the
        # second derive's edge from drawing.
        import tempfile
        swift = _fresh_swift()
        refused = ("- `unresolved-reference` `Package.swift` lines 7-7 — product CoreKit of target Core "
                   "names a package whose `.package(path:)` reference was refused; no edge is drawn")
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            root = Path(d).resolve()
            (root / "Package.swift").write_text(
                "let package = Package(\n"
                "    name: \"App\",\n"
                "    dependencies: [\n"
                "        .package(path: \"Sibling\"),\n"
                "    ],\n"
                "    targets: [\n"
                "        .target(name: \"Core\", dependencies: [.product(name: \"CoreKit\", package: \"Sibling\")]),\n"
                "    ]\n"
                ")\n"
            )
            (root / "Sibling").symlink_to(Path(outside), target_is_directory=True)

            first = swift.extract_module_graph(root, "bionic")[0]
            self.assertIn(refused, first)
            self.assertNotIn("-->", first)

            (root / "Sibling").unlink()
            (root / "Sibling").mkdir()
            (root / "Sibling" / "Package.swift").write_text(
                'let package = Package(name: "Sibling", products: [.library(name: "CoreKit", '
                'targets: ["CoreKit"])], targets: [.target(name: "CoreKit")])\n')

            second = swift.extract_module_graph(root, "bionic")[0]
            self.assertNotIn("was refused", second)
            self.assertEqual(_edges(second), {("Core (Package.swift)", "CoreKit (Sibling/Package.swift)")})

    def test_credential_location_is_stripped(self):
        render = self._check("credential-location")
        for concern, md in render.items():
            with self.subTest(concern=concern):
                for leak in ("tok", "u:", "q=1", "#f"):
                    self.assertNotIn(leak, md)

    def test_credential_check_positive_control(self):
        """The same check turns red when the location is rendered unstripped."""
        from unittest import mock
        with mock.patch.object(self.swift, "_strip_location", lambda loc: loc):
            render = _derive_tree(_fresh_swift(), MANIFESTS / "credential-location")
        self.assertIn("tok", render["module-graph"])

    def test_every_string_escape_decodes(self):
        source = b'let s = "a\\nb\\rc\\td\\0e\\\\f\\"g\\\'h\\u{2122}"\n'
        tree = self.swift._parse(source)
        literal = [n for n in self.swift._preorder(tree.root_node) if n.type == "line_string_literal"][0]
        self.assertEqual(self.swift._string_literal(literal, source),
                         "a\nb\rc\td\0e\\f\"g'h™")

    def test_hostile_names_count_like_plain_names(self):
        core = _core()
        hostile = _derive_tree(self.swift, MANIFESTS / "hostile-names")
        plain = _derive_tree(self.swift, MANIFESTS / "plain-names")
        for concern in ("api-surface", "module-graph"):
            with self.subTest(concern=concern):
                self.assertEqual(core.count_concern_entities(concern, hostile[concern]),
                                 core.count_concern_entities(concern, plain[concern]))
                self.assertEqual(core.count_concern_entities(concern, hostile[concern]), 1)
                self.assertEqual(len(hostile[concern].split("\n")), len(plain[concern].split("\n")))
        fence = hostile["module-graph"].split("```mermaid\n", 1)[1].split("\n```", 1)[0].split("\n")
        self.assertEqual(fence[0], "graph LR")
        self.assertTrue(all(" --> " in line for line in fence[1:]))

    def test_hostile_names_positive_control_bypassing_the_escapers(self):
        """With `_cell` and the label escaper replaced by the identity, the
        hostile names break a row or the fence, so the counts or the line
        structure move; the check above would turn red."""
        from unittest import mock
        core = _core()
        plain = _derive_tree(self.swift, MANIFESTS / "plain-names")
        swift = _fresh_swift()
        with mock.patch.object(swift, "_cell", lambda s: str(s)), \
                mock.patch.object(swift, "_swift_label", lambda s: str(s)):
            hostile = _derive_tree(swift, MANIFESTS / "hostile-names")
        moved = [c for c in ("api-surface", "module-graph")
                 if core.count_concern_entities(c, hostile[c]) != core.count_concern_entities(c, plain[c])
                 or len(hostile[c].split("\n")) != len(plain[c].split("\n"))]
        self.assertTrue(moved)


class ResidualVocabularyTests(unittest.TestCase):
    """ADR-0129 clause 7's closed residual vocabulary and the location stripper."""

    def setUp(self):
        self.swift = _fresh_swift()

    def test_residual_classes_is_the_closed_adr_0129_tuple(self):
        self.assertEqual(self.swift._RESIDUAL_CLASSES, (
            "parse-error", "declaration-recovered", "declaration-dropped",
            "conditional-declaration", "macro-not-expanded", "non-literal-manifest",
            "unresolved-reference", "path-escape", "oversize", "scan-cap",
            "conditional-setting", "missing-input",
            "project-unreadable", "unsupported-project-form", "xcconfig-include"))

    def test_residual_line_refuses_a_class_outside_the_closed_set(self):
        with self.assertRaises(ValueError):
            self.swift._residual_line("not-a-real-class", "x.swift", (1, 1), "detail")

    def test_residual_line_flattens_line_breaks_in_a_detail(self):
        line = self.swift._residual_line("parse-error", "x.swift", (1, 1), "a\nb\rc")
        self.assertNotIn("\n", line)
        self.assertNotIn("\r", line)

    def test_a_name_inside_a_residual_detail_passes_the_cell_escaper(self):
        # ADR-0129 clause 6: every rendered string passes the core's cell
        # escaping. A backtick-escaped Swift identifier carries backticks,
        # which would unbalance the bullet's code spans if rendered raw.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "T.swift").write_text(
                "#if os(macOS)\npublic struct `Type` {}\n#else\npublic struct `Type` {}\n#endif\n")
            md, _sources = self.swift.extract_data_model(root, "bionic")
        bullets = [ln for ln in md.split("\n") if ln.startswith("- `conditional-declaration`")]
        self.assertEqual(len(bullets), 1)
        self.assertIn("— ʼTypeʼ is declared in 2 `#if` branches", bullets[0])

    def test_strip_location_cases(self):
        cases = [
            ("https://u:tok@host/x.git?q=1#f", "https://host/x.git"),
            ("ssh://git@host/x.git", "ssh://host/x.git"),
            ("git@host:x.git", "host:x.git"),
            ("https://host/path/x.git", "https://host/path/x.git"),
            # A userinfo holding `/` still ends at its `@`, so no part of the
            # credential survives.
            ("https://u:p/ss@host/x.git", "https://host/x.git"),
            # An `@` after a `?` or `#` is undecidable: a userinfo holding
            # `?`/`#`, or a query/fragment holding `@`
            # (`https://host/x.git?q=1@SECRET`) read the same. Neither side
            # renders, so neither credential nor query survives.
            ("https://u:p#ss@host/x.git", "https://"),
            ("https://u:p?ss@host/x.git", "https://"),
            ("https://host/x.git?q=1@ss", "https://"),
            ("u:p/ss@host:x.git", "host:x.git"),
        ]
        for loc, expected in cases:
            with self.subTest(loc=loc):
                self.assertEqual(self.swift._strip_location(loc), expected)


class DeclaredInputDescriptionTests(unittest.TestCase):
    """A concern's `INPUT_CLASSES` `expected` text renders on its stub line, so
    it must name every kind of file the concern hashes into `sources`
    (ADR-0129 clause 4: every consumed file is hashed; ADR-0130 clause 1: each
    consuming concern declares the project inputs it reads). A file kind the
    text omits would make the stub line describe a package-only pack."""

    #: One tree holding every file kind a Swift concern can consume.
    FILES = {
        "Package.swift": "// swift-tools-version:5.9\n",
        "Sources/Core/A.swift": "public struct A {}\n",
        "App.xcodeproj/project.pbxproj": "// !$*UTF8*$!\n{\n}\n",
        "Dev.xcworkspace/contents.xcworkspacedata": "<?xml version=\"1.0\"?>\n<Workspace version=\"1.0\"/>\n",
        "Config/Base.xcconfig": "SWIFT_VERSION = 5.0\n",
        "project.yml": "name: App\n",
    }

    #: Every token the fixture must reach; the token is the file name for a
    #: fixed-name input and the suffix for any other.
    ALL_TOKENS = {"Package.swift", ".swift", "project.pbxproj", "contents.xcworkspacedata",
                  ".xcconfig", "project.yml"}

    def setUp(self):
        self.swift = _fresh_swift()

    @staticmethod
    def _token(rel: str) -> str:
        name = rel.rsplit("/", 1)[-1]
        if name in ("Package.swift", "project.pbxproj", "contents.xcworkspacedata", "project.yml"):
            return name
        return "." + name.rsplit(".", 1)[-1]

    def _tokens_per_concern(self):
        import tempfile
        extractors = {
            "data-model": self.swift.extract_data_model,
            "api-surface": self.swift.extract_api_surface,
            "module-graph": self.swift.extract_module_graph,
        }
        out = {}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel, text in self.FILES.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(text)
            for concern, extract in extractors.items():
                _md, sources = extract(root, "bionic")
                out[concern] = {self._token(rel) for rel in sources}
        return out

    def test_the_fixture_reaches_every_input_kind(self):
        # Positive control for the check below: the module-graph scan hashes
        # all six kinds, so a missing name there cannot pass by absence.
        self.assertEqual(self._tokens_per_concern()["module-graph"], self.ALL_TOKENS)

    def test_every_hashed_file_kind_is_named_in_the_expected_text(self):
        for concern, tokens in self._tokens_per_concern().items():
            expected = self.swift.INPUT_CLASSES[concern].expected
            for token in sorted(tokens):
                with self.subTest(concern=concern, token=token):
                    self.assertIn(f"`{token}`", expected)


class ProjectFileBoundTests(unittest.TestCase):
    """ADR-0130 clause 2 sets the `project.pbxproj` bound at 16 MiB. The pin
    is the literal byte count, so a change to the core's aggregate byte cap
    cannot move this bound without turning this test red."""

    def test_the_pbxproj_bound_is_16_mib(self):
        self.assertEqual(_swift_module()._MAX_PBXPROJ_BYTES, 16_777_216)


class ExpressionValueLeakTests(unittest.TestCase):
    """ADR-0129 clause 5: no initializer, default argument or raw value renders."""

    CANARIES = ("8675309", "8675310", "8675311")

    def test_no_seeded_value_reaches_a_spine_file(self):
        render = _derive_fixture(_fresh_swift(), FIXTURES / "16-seeded-initializer.swift")
        for concern, md in render.items():
            for canary in self.CANARIES:
                with self.subTest(concern=concern, canary=canary):
                    self.assertNotIn(canary, md)

    def test_positive_control_a_declared_type_read_from_the_whole_declaration_leaks(self):
        """If the property reader took the declaration text instead of its type
        annotation, the initializer would render; the check above catches it."""
        from unittest import mock
        swift = _fresh_swift()
        real_norm = swift._norm_ws

        def leaky(text):
            return real_norm(text) + " = 8675309" if text.strip() == "Int" else real_norm(text)

        with mock.patch.object(swift, "_norm_ws", leaky):
            render = _derive_fixture(swift, FIXTURES / "16-seeded-initializer.swift")
        self.assertIn("8675309", render["data-model"])


class PerFileBoundaryTests(unittest.TestCase):
    """ADR-0129 clause 2: content never makes the deriver exit 2. A failed
    per-file step renders one `parse-error` naming the file and the step, and
    the derive continues; the outcome splits at the read."""

    def setUp(self):
        self.swift = _fresh_swift()
        import tempfile
        self._d = tempfile.TemporaryDirectory()
        self.addCleanup(self._d.cleanup)
        self.root = Path(self._d.name)
        (self.root / "Good.swift").write_text("public struct Good {}\n")
        (self.root / "Bad.swift").write_text("public struct Bad {}\n")

    def _raise_on_bad(self, exc):
        real = self.swift._parse

        def parse(raw):
            if b"Bad" in raw:
                raise exc
            return real(raw)
        return parse

    def test_each_exception_class_renders_one_parse_error_and_the_derive_continues(self):
        from unittest import mock
        for exc in (RecursionError("deep"), MemoryError(), ValueError("x")):
            with self.subTest(exc=type(exc).__name__):
                self.swift._CACHE.update(root=None, files={}, manifests={})
                with mock.patch.object(self.swift, "_parse", self._raise_on_bad(exc)):
                    md, sources = self.swift.extract_data_model(self.root, "bionic")
                bullets = _residual_bullets(md)
                self.assertEqual(bullets, {("parse-error", "Bad.swift", None,
                                            "location none; effect step parse failed")})
                self.assertIn("| `Good` | struct |", md)
                self.assertEqual(sorted(sources), ["Bad.swift", "Good.swift"])

    def test_a_failed_walk_after_the_parse_names_the_walk_step(self):
        from unittest import mock
        real_run = self.swift._Walk.run

        def run(walk, root_node, skip=frozenset()):
            if b"Bad" in walk.src:
                raise RecursionError("deep")
            return real_run(walk, root_node, skip)

        with mock.patch.object(self.swift._Walk, "run", run):
            md, sources = self.swift.extract_data_model(self.root, "bionic")
        self.assertIn(("parse-error", "Bad.swift", None, "location none; effect step walk failed"),
                      _residual_bullets(md))
        self.assertIn("Bad.swift", sources)

    def test_deep_nesting_fixture_with_a_raised_recursion_error(self):
        from unittest import mock
        import shutil
        shutil.copy(FIXTURES / "15-deep-nesting.swift", self.root / "Deep.swift")
        real = self.swift._parse

        def parse(raw):
            if raw.count(b"(") > 1000:
                raise RecursionError("maximum recursion depth exceeded")
            return real(raw)

        with mock.patch.object(self.swift, "_parse", parse):
            md, _ = self.swift.extract_data_model(self.root, "bionic")
        self.assertIn(("parse-error", "Deep.swift", None, "location none; effect step parse failed"),
                      _residual_bullets(md))
        self.assertIn("| `Good` | struct |", md)

    def test_a_failed_manifest_read_renders_one_parse_error(self):
        from unittest import mock
        (self.root / "Package.swift").write_text('let package = Package(name: "P", targets: [])\n')

        def boom(self_reader, tree):
            raise MemoryError()

        with mock.patch.object(self.swift._ManifestReader, "read", boom):
            md, sources = self.swift.extract_module_graph(self.root, "bionic")
        self.assertIn(("parse-error", "Package.swift", None, "location none; effect step manifest failed"),
                      _residual_bullets(md))
        self.assertIn("Package.swift", sources)

    def test_a_symlinked_source_is_refused_and_not_hashed(self):
        import os
        (self.root / "Real.txt").write_text("public struct Linked {}\n")
        os.symlink(self.root / "Real.txt", self.root / "Linked.swift")
        md, sources = self.swift.extract_data_model(self.root, "bionic")
        self.assertIn(("parse-error", "Linked.swift", None, "location none; effect step read failed"),
                      _residual_bullets(md))
        self.assertNotIn("Linked.swift", sources)
        self.assertNotIn("`Linked`", md)

    def test_a_fifo_is_refused_without_blocking(self):
        import os
        if not hasattr(os, "mkfifo"):
            self.skipTest("no FIFOs on this platform")
        os.mkfifo(self.root / "Pipe.swift")
        md, sources = self.swift.extract_data_model(self.root, "bionic")
        self.assertIn(("parse-error", "Pipe.swift", None, "location none; effect step read failed"),
                      _residual_bullets(md))
        self.assertNotIn("Pipe.swift", sources)

    def test_an_over_bound_file_renders_oversize(self):
        (self.root / "Big.swift").write_bytes(b"//" + b"x" * (2 * 1024 * 1024))
        md, sources = self.swift.extract_data_model(self.root, "bionic")
        self.assertIn(("oversize", "Big.swift", None,
                       "location none; the file exceeds the 2 MB per-file bound and is not read"),
                      _residual_bullets(md))
        self.assertNotIn("Big.swift", sources)


class ConcernDecodeVerdictTests(unittest.TestCase):
    """`parse_failed` exactly when the concern names at least one declared
    input that was not decoded and none was decoded (ADR-0129 clause 7)."""

    def setUp(self):
        self.swift = _fresh_swift()

    def test_parse_failed_when_every_declared_input_failed_to_decode(self):
        from unittest import mock
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "A.swift").write_text("struct A {}\n")
            with mock.patch.object(self.swift, "_parse", side_effect=ValueError("x")):
                md, sources = self.swift.extract_data_model(root, "bionic")
        verdict = self.swift.concern_decode_verdict("data-model", md, sources)
        self.assertIsNotNone(verdict)
        self.assertEqual(verdict.reason, self.swift.StubReason.PARSE_FAILED)

    def test_parse_failed_when_the_failed_file_name_needs_escaping(self):
        # The residual renders the path through `_cell`, which escapes a pipe;
        # the source map keys the raw path. The two must still be matched.
        from unittest import mock
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a|b.swift").write_text("struct A {}\n")
            with mock.patch.object(self.swift, "_parse", side_effect=ValueError("x")):
                md, sources = self.swift.extract_data_model(root, "bionic")
        self.assertIn("a|b.swift", sources)
        verdict = self.swift.concern_decode_verdict("data-model", md, sources)
        self.assertIsNotNone(verdict)
        self.assertEqual(verdict.reason, self.swift.StubReason.PARSE_FAILED)

    def test_parse_failed_when_the_only_input_was_refused_at_the_read(self):
        content = ("# Data model\n\n## Types\n\n_None._\n\n## Residuals\n\n"
                   "- `parse-error` `a.swift` lines — — location none; effect step read failed\n")
        verdict = self.swift.concern_decode_verdict("data-model", content, {})
        self.assertEqual(verdict.reason, self.swift.StubReason.PARSE_FAILED)

    def test_none_when_one_input_decoded_beside_a_failed_one(self):
        content = ("# Data model\n\n## Residuals\n\n"
                   "- `parse-error` `a.swift` lines — — location none; effect step parse failed\n")
        self.assertIsNone(self.swift.concern_decode_verdict(
            "data-model", content, {"a.swift": "0" * 64, "b.swift": "1" * 64}))

    def test_none_when_residuals_name_only_errors_inside_decoded_files(self):
        content = ("# Data model\n\n## Residuals\n\n"
                   "- `parse-error` `a.swift` lines 3-3 — location body; effect enclosing func f\n")
        self.assertIsNone(self.swift.concern_decode_verdict("data-model", content, {"a.swift": "0" * 64}))


class EntityCountingTests(unittest.TestCase):
    """ADR-0129 clause 6's counting pairs at the renderer level; the strict and
    `arch.require` exits are tested through the registered derive path."""

    def setUp(self):
        self.swift = _fresh_swift()
        self.core = _core()

    def _render(self, files: dict, extractor):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel, text in files.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(text)
            return extractor(root, "bionic")[0]

    def test_data_model_counts_each_type(self):
        md = self._render({"A.swift": "struct A {}\nenum B {}\nclass C {}\nactor D {}\n"},
                          self.swift.extract_data_model)
        self.assertEqual(self.core.count_concern_entities("data-model", md), 4)

    def test_data_model_counts_zero_for_protocols_extensions_and_free_functions(self):
        md = self._render({"A.swift": "public protocol P {}\nextension String {}\nfunc f() {}\n"},
                          self.swift.extract_data_model)
        self.assertEqual(self.core.count_concern_entities("data-model", md), 0)

    def test_api_surface_counts_one_public_struct(self):
        md = self._render({"A.swift": "public struct A {}\n"}, self.swift.extract_api_surface)
        self.assertEqual(self.core.count_concern_entities("api-surface", md), 1)

    def test_api_surface_counts_a_lone_main(self):
        md = self._render({"A.swift": "@main struct App {}\n"}, self.swift.extract_api_surface)
        self.assertGreaterEqual(self.core.count_concern_entities("api-surface", md), 1)

    def test_api_surface_counts_zero_for_internal_only_code(self):
        md = self._render({"A.swift": "struct A {}\nfunc f() {}\n"}, self.swift.extract_api_surface)
        self.assertEqual(self.core.count_concern_entities("api-surface", md), 0)

    def test_module_graph_counts_one_edge_for_two_targets_and_one_dependency(self):
        md = self._render({"Package.swift": (
            'let package = Package(name: "M", targets: [\n'
            '    .target(name: "Core"),\n'
            '    .target(name: "App", dependencies: ["Core"]),\n'
            '])\n')}, self.swift.extract_module_graph)
        self.assertEqual(self.core.count_concern_entities("module-graph", md), 1)

    def test_module_graph_counts_zero_for_one_target_importing_an_sdk_module(self):
        md = self._render({
            "Package.swift": 'let package = Package(name: "M", targets: [.target(name: "Core")])\n',
            "Sources/Core/A.swift": "import Foundation\n",
        }, self.swift.extract_module_graph)
        self.assertEqual(self.core.count_concern_entities("module-graph", md), 0)
        self.assertIn("sdk-or-unresolved", md)


DRIVER = SCRIPTS / "derive-arch.py"
SAP_CACHE = CACHE_ROOT / "swift-argument-parser"
PINNED_SAP_HEAD = "cdc5f0c6e836de848699ae11f6480f2d99ac5ef1"


def _load_driver():
    spec = importlib.util.spec_from_file_location("_test_swift_derive_arch_cli", DRIVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _SwiftTree(unittest.TestCase):
    """A repository the swift pack resolves: a `Package.swift`, a `bionic/`
    tree and whatever sources a test writes."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.swift = _fresh_swift()
        self.core = _core()
        (self.root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: bionic\n')
        self.write_manifest()
        self.write("Package.swift",
                   'let package = Package(name: "M", targets: [.target(name: "Core")])\n')

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_manifest(self, extra: str = "") -> None:
        (self.root / "bionic").mkdir(exist_ok=True)
        (self.root / "bionic" / "manifest.yml").write_text(
            'schema_version: "5"\nadr:\n  next_number: 1\n' + extra, encoding="utf-8")

    def run_cli(self, *argv: str):
        import contextlib
        import io
        import json
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = _load_driver().main(["--repo-root", str(self.root), *argv])
        text = out.getvalue()
        return code, (json.loads(text) if text.strip() else {}), err.getvalue()

    def verdicts(self) -> dict:
        report: list = []
        self.swift._CACHE.update(root=None, files={}, manifests={})
        self.core._build(self.root, "bionic", "complete", None, report=report)
        return {r["concern"]: r for r in self.core.reported_coverage(report)}


class RegisteredDerivePathTests(_SwiftTree):
    """ADR-0129 clauses 6 and 9(e)-(g) through the registered derive path."""

    def test_the_tree_resolves_to_the_swift_pack(self):
        self.assertEqual(self.core.resolve_stack(self.root).pack_name, "swift")

    def test_each_concern_populates_with_its_own_entities(self):
        self.write("Sources/Core/Model.swift", "public struct Model {}\nstruct Hidden {}\n")
        self.write("Package.swift", 'let package = Package(name: "M", targets: [\n'
                   '    .target(name: "Core"),\n    .target(name: "App", dependencies: ["Core"]),\n])\n')
        v = self.verdicts()
        self.assertEqual((v["data-model"]["verdict"], v["data-model"]["n_entities"]), ("populated", 2))
        self.assertEqual((v["api-surface"]["verdict"], v["api-surface"]["n_entities"]), ("populated", 1))
        self.assertEqual((v["module-graph"]["verdict"], v["module-graph"]["n_entities"]), ("populated", 1))

    def _no_entities_case(self, concern: str):
        self.write("Sources/Core/A.swift", {
            "data-model": "public protocol P {}\nextension String {}\nfunc f() {}\n",
            "api-surface": "struct A {}\nfunc f() {}\n",
            "module-graph": "import Foundation\n",
        }[concern])
        v = self.verdicts()[concern]
        self.assertEqual((v["verdict"], v["stub_reason"]), ("stubbed", "no_entities"))
        return v

    def test_no_entities_cases_exit_1_under_strict(self):
        for concern in ("data-model", "api-surface", "module-graph"):
            with self.subTest(concern=concern):
                self.setUp()
                self._no_entities_case(concern)
                code, payload, _err = self.run_cli("--strict")
                self.assertEqual(code, 1)
                failed = {f["concern"]: f for f in payload["strict_failures"]}
                self.assertEqual(failed[concern]["stub_reason"], "no_entities")
                self.assertEqual(failed[concern]["required_by"], "--strict")

    def test_no_entities_cases_exit_1_under_arch_require(self):
        for concern in ("data-model", "api-surface", "module-graph"):
            with self.subTest(concern=concern):
                self.setUp()
                self._no_entities_case(concern)
                self.write_manifest(f"arch:\n  require: [{concern}]\n")
                code, payload, _err = self.run_cli()
                self.assertEqual(code, 1)
                self.assertEqual([f["concern"] for f in payload["strict_failures"]], [concern])
                self.assertEqual(payload["strict_failures"][0]["required_by"], "arch.require")

    def test_the_api_surface_stub_line_names_an_interface_row(self):
        self._no_entities_case("api-surface")
        self.assertIn("interface row", self.verdicts()["api-surface"]["expected"])

    def test_parse_failed_when_no_declared_input_decodes(self):
        from unittest import mock
        self.write("Sources/Core/A.swift", "public struct A {}\n")
        with mock.patch.object(self.swift, "_parse", side_effect=MemoryError()):
            v = self.verdicts()
        self.assertEqual((v["data-model"]["verdict"], v["data-model"]["stub_reason"]),
                         ("stubbed", "parse_failed"))

    def test_two_derives_write_identical_bytes(self):
        self.write("Sources/Core/Model.swift", "public struct Model {\n    let id: Int\n}\n")
        self.assertEqual(self.run_cli()[0], 0)
        arch = self.root / "bionic" / "arch"
        first = {p.relative_to(arch).as_posix(): p.read_bytes() for p in arch.rglob("*") if p.is_file()}
        self.swift._CACHE.update(root=None, files={}, manifests={})
        self.assertEqual(self.run_cli()[0], 0)
        second = {p.relative_to(arch).as_posix(): p.read_bytes() for p in arch.rglob("*") if p.is_file()}
        self.assertEqual(first, second)
        self.assertIn("parser:tree_sitter_swift", (arch / "_meta" / "manifest.json").read_text())

    def test_dry_run_drifts_on_a_swift_input_edit_and_not_outside_the_inputs(self):
        self.write("Sources/Core/Model.swift", "public struct Model {}\n")
        self.assertEqual(self.run_cli()[0], 0)
        self.write("README.md", "# notes\n")
        self.write("Sources/Core/notes.txt", "not a declared input\n")
        code, payload, _ = self.run_cli("--dry-run")
        self.assertEqual((code, payload["drift"]), (0, []))
        self.write("Sources/Core/Model.swift", "public struct Model {}\npublic struct Added {}\n")
        self.swift._CACHE.update(root=None, files={}, manifests={})
        code, payload, _ = self.run_cli("--dry-run")
        self.assertEqual(code, 1)
        self.assertIn("bionic/arch/data-model.md", payload["drift"])

    def _pbxproj(self) -> Path:
        proj = self.root / "App.xcodeproj"
        proj.mkdir(exist_ok=True)
        pbx = proj / "project.pbxproj"
        pbx.write_text("// !$*UTF8*$!\nAAA\n")
        return pbx

    def test_dry_run_drifts_when_a_project_pbxproj_becomes_a_consumed_input(self):
        # The `INPUT_CLASSES`/`_scan` wiring (ADR-0130 clause 1), checked at
        # the edit-set level `--dry-run` exercises: bringing a
        # `project.pbxproj` INTO the walk moves `coverage.json`'s recorded
        # input count and `module-graph.md` (both non-`sources` manifest
        # fields, so `_manifest_drifted`'s exclusion of `sources` never
        # hides it). An in-place edit is covered by
        # `test_dry_run_drifts_on_a_meaningful_in_place_pbxproj_edit`.
        self.write("Sources/Core/Model.swift", "public struct Model {}\n")
        self.assertEqual(self.run_cli()[0], 0)
        self._pbxproj()
        self.swift._CACHE.update(root=None, files={}, manifests={})
        code, payload, _ = self.run_cli("--dry-run")
        self.assertEqual(code, 1)
        self.assertIn("bionic/arch/module-graph.md", payload["drift"])
        self.assertIn("bionic/arch/_meta/coverage.json", payload["drift"])

    def test_dry_run_none_after_editing_a_file_no_concern_glob_admits(self):
        self.write("Sources/Core/Model.swift", "public struct Model {}\n")
        self._pbxproj()
        self.assertEqual(self.run_cli()[0], 0)
        self.write("App.xcodeproj/xcuserdata/notes.txt", "not a declared input\n")
        code, payload, _ = self.run_cli("--dry-run")
        self.assertEqual((code, payload["drift"]), (0, []))

    def _valid_pbxproj(self, target_name: str) -> str:
        return (
            "// !$*UTF8*$!\n"
            "{\n"
            "\tarchiveVersion = 1;\n"
            "\tobjectVersion = 56;\n"
            "\trootObject = PROJ;\n"
            "\tobjects = {\n"
            "\t\tPROJ = {\n"
            "\t\t\tisa = PBXProject;\n"
            "\t\t\tmainGroup = MAIN;\n"
            "\t\t\ttargets = (\n"
            "\t\t\t\tT,\n"
            "\t\t\t);\n"
            "\t\t};\n"
            "\t\tMAIN = {\n"
            "\t\t\tisa = PBXGroup;\n"
            '\t\t\tsourceTree = "<group>";\n'
            "\t\t\tchildren = (\n"
            "\t\t\t);\n"
            "\t\t};\n"
            "\t\tT = {\n"
            "\t\t\tisa = PBXNativeTarget;\n"
            f"\t\t\tname = {target_name};\n"
            '\t\t\tproductType = "com.apple.product-type.application";\n'
            "\t\t\tbuildPhases = (\n"
            "\t\t\t);\n"
            "\t\t};\n"
            "\t};\n"
            "}\n"
        )

    def test_dry_run_drifts_on_a_meaningful_in_place_pbxproj_edit(self):
        # ADR-0130 clause 18: "`--dry-run` reports drift on an edit to any
        # consumed `project.pbxproj`, workspace or xcconfig file." Renaming
        # a target's `name` field moves `module-graph.md`'s rendered target
        # row.
        self.write("Sources/Core/Model.swift", "public struct Model {}\n")
        proj = self.root / "App.xcodeproj"
        proj.mkdir(exist_ok=True)
        pbx = proj / "project.pbxproj"
        pbx.write_text(self._valid_pbxproj("App"))
        self.assertEqual(self.run_cli()[0], 0)
        pbx.write_text(self._valid_pbxproj("AppRenamed"))
        self.swift._CACHE.update(root=None, files={}, manifests={})
        code, payload, _ = self.run_cli("--dry-run")
        self.assertEqual(code, 1)
        self.assertIn("bionic/arch/module-graph.md", payload["drift"])

    def test_dry_run_none_on_a_pure_trailing_comment_edit_to_pbxproj(self):
        # Investigative: names come from FIELDS, never `/* ... */` comments
        # (swift_pbxproj's own contract), and a trailing same-line comment
        # adds no newline, so it shifts no object's recorded line span.
        # `--dry-run` therefore reports NO drift here -- the rendered
        # content is byte-identical even though the file's own bytes, and
        # so its hash, changed. No ADR clause settles this case: the drift
        # gate compares rendered content and excludes the `sources` hashes.
        # The test pins the observed behaviour so a change to it is visible.
        self.write("Sources/Core/Model.swift", "public struct Model {}\n")
        proj = self.root / "App.xcodeproj"
        proj.mkdir(exist_ok=True)
        pbx = proj / "project.pbxproj"
        pbx.write_text(self._valid_pbxproj("App"))
        self.assertEqual(self.run_cli()[0], 0)
        edited = self._valid_pbxproj("App").rstrip("\n") + " /* trailing comment */\n"
        pbx.write_text(edited)
        self.swift._CACHE.update(root=None, files={}, manifests={})
        code, payload, _ = self.run_cli("--dry-run")
        self.assertEqual((code, payload["drift"]), (0, []))

    def test_a_runtime_load_refusal_is_parser_unavailable_before_any_write(self):
        from unittest import mock
        self.swift._PARSERS.clear()
        with mock.patch.object(self.swift, "_swift_parser", side_effect=OSError("ABI refused")):
            with self.assertRaises(self.core.ParserUnavailable):
                self.core.derive(self.root, "bionic")
        self.assertFalse((self.root / "bionic" / "arch").exists())


_BLOCKER = r"""
import sys
class _Block:
    def find_spec(self, name, path=None, target=None):
        if name == "tree_sitter_swift" or name.startswith("tree_sitter_swift."):
            raise ImportError("blocked for the test: " + name)
        return None
sys.meta_path.insert(0, _Block())
"""


_CANARY_PBXPROJ = """// !$*UTF8*$!
{
	archiveVersion = 1;
	classes = {
	};
	objectVersion = 56;
	objects = {
		PRJ = {
			isa = PBXProject;
			mainGroup = MG;
			packageReferences = (
				RR1,
				RR2,
				RR3,
			);
			targets = (
				TGT,
			);
		};
		MG = {
			isa = PBXGroup;
			sourceTree = "<group>";
			children = (
			);
		};
		TGT = {
			isa = PBXNativeTarget;
			name = "App";
			productType = "com.apple.product-type.application";
			buildPhases = (
			);
			dependencies = (
			);
			packageProductDependencies = (
				PD1,
			);
		};
		PD1 = {
			isa = XCSwiftPackageProductDependency;
			package = RR1;
			productName = "Kit";
		};
		RR1 = {
			isa = XCRemoteSwiftPackageReference;
			repositoryURL = "deploy:CANARY@git.example.com:org/a.git?ref=https://x";
			requirement = {
				kind = upToNextMajorVersion;
				minimumVersion = 1.0.0;
			};
		};
		RR2 = {
			isa = XCRemoteSwiftPackageReference;
			repositoryURL = "https://git.example.com/org/b.git?q=1@CANARY";
			requirement = {
				kind = upToNextMajorVersion;
				minimumVersion = 1.0.0;
			};
		};
		RR3 = {
			isa = XCRemoteSwiftPackageReference;
			repositoryURL = "user:pa://CANARY@host:r";
			requirement = {
				kind = upToNextMajorVersion;
				minimumVersion = 1.0.0;
			};
		};
	};
	rootObject = PRJ;
}
"""

_CANARY_MANIFEST = (
    'let package = Package(name: "App", dependencies: [\n'
    '    .package(url: "https://git.example.com/org/b.git?q=1@CANARY", from: "1.0.0"),\n'
    '    .package(url: "CANARY:tok@host/x?y=https://z", from: "1.0.0"),\n'
    '    .package(url: "https://git.example.com/org/c.git#f@CANARY", from: "1.0.0"),\n'
    '    .package(path: "Pods/PodPkg"),\n'
    '], targets: [.target(name: "Core")])\n'
)


class DependencyLocationCanaryTests(unittest.TestCase):
    """`rule:swift-dependency-location-strips-credentials` end to end: fixture
    96's tree gains `Package.swift` and `project.pbxproj` dependency locations
    whose credential, query or fragment carries a canary. After a real derive
    the canary appears in no spine file, no residual line and no output the
    driver prints."""

    def _derive(self, root: Path):
        import contextlib
        import io
        swift = _fresh_swift()
        swift._CACHE.update(root=None, files={}, manifests={})
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = _load_driver().main(["--repo-root", str(root)])
        spine = "".join(p.read_text(encoding="utf-8")
                        for p in sorted((root / "bionic" / "arch").rglob("*")) if p.is_file())
        return code, spine, out.getvalue() + err.getvalue()

    def _tree(self, dest: Path) -> Path:
        h = _harness()
        fixture = h.FIXTURES_ROOT / "96-pruned-package-path-dependency"
        h.materialize(fixture, dest, h.load_expected(fixture))
        (dest / "Package.swift").write_text(_CANARY_MANIFEST, encoding="utf-8")
        (dest / "App.xcodeproj").mkdir()
        (dest / "App.xcodeproj" / "project.pbxproj").write_text(_CANARY_PBXPROJ, encoding="utf-8")
        return dest

    def test_no_canary_reaches_the_spine_a_residual_or_the_output(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            code, spine, printed = self._derive(self._tree(Path(d).resolve() / "case"))
        self.assertEqual(code, 0)
        self.assertIn("## Dependencies", spine)
        self.assertIn("git.example.com:org/a.git", spine)
        self.assertNotIn("CANARY", spine)
        self.assertNotIn("CANARY", printed)

    def test_positive_control_without_stripping_the_canary_renders(self):
        import tempfile
        from unittest import mock
        swift = _fresh_swift()
        products = importlib.import_module("crux.arch.packs.swift_xcode_products")
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(swift, "_strip_location", str), \
                mock.patch.object(products, "_strip_location", str):
            code, spine, _printed = self._derive(self._tree(Path(d).resolve() / "case"))
        self.assertEqual(code, 0)
        self.assertIn("CANARY", spine)


#: Every `App/Package.swift` the path-dependency tests write: the reference
#: sits on line 5 and the target dependency on line 8 (the layout fixtures
#: 101-106 share).
_APP_MANIFEST = (
    'let package = Package(\n'
    '    name: "App",\n'
    '    products: [.library(name: "AppCore", targets: ["AppCore"])],\n'
    '    dependencies: [\n'
    '        .package(path: "{path}"),\n'
    '    ],\n'
    '    targets: [\n'
    '        .target(name: "AppCore", dependencies: [{dep}]),\n'
    '    ]\n'
    ')\n'
)


def _core_kit_manifest(name: str) -> str:
    return (f'let package = Package(name: "{name}", products: [.library(name: "CoreKit", '
            'targets: ["CoreKit"])], targets: [.target(name: "CoreKit")])\n')


#: The armed window of `_PathReadRecorder`'s one process-wide audit hook.
_PATH_READS: list = []
_PATH_READS_ARMED = [False]


def _path_read_hook(event, args):
    if _PATH_READS_ARMED[0] and event in ("open", "os.listdir", "os.scandir") and args:
        target = args[0]
        if isinstance(target, (str, bytes, os.PathLike)):
            _PATH_READS.append(os.fsdecode(target))


_PATH_READ_HOOK_INSTALLED = [False]


class PathDependencySymlinkTests(_SwiftTree):
    """ADR-0129:143, :153 and :137 over a contained `.package(path:)` with a
    symlinked component. ADR-0130 clause 3 governs project, workspace and
    xcconfig paths only, and `Package.swift` is none of those, so the
    reference renders its dependency row with its lexical location. The row
    reads nothing through the symlink. Its identity names no manifest the
    walk reaches, so a product qualified by it, or a by-name product with no
    other local candidate, renders "resolves to 0 containers" and draws no
    edge (ADR-0129:151): no checkout-wide product-name search guesses one."""

    def _link(self, link, target):
        (self.root / target).mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(self.root / target, self.root / link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("host refuses symlink creation")

    def _graph(self):
        self.swift._CACHE.update(root=None, files={}, manifests={})
        return self.swift.extract_module_graph(self.root, "bionic")[0]

    def _recorded_graph(self):
        if not _PATH_READ_HOOK_INSTALLED[0]:
            sys.addaudithook(_path_read_hook)  # cannot be removed; inert unless armed.
            _PATH_READ_HOOK_INSTALLED[0] = True
        _PATH_READS.clear()
        _PATH_READS_ARMED[0] = True
        try:
            return self._graph(), list(_PATH_READS)
        finally:
            _PATH_READS_ARMED[0] = False

    def _alias_tree(self, dep: str) -> None:
        self._link("Alias", "Vendor/CorePkg")
        self.write("Vendor/CorePkg/Package.swift", _core_kit_manifest("CorePkg"))
        self.write("App/Package.swift", _APP_MANIFEST.format(path="../Alias", dep=dep))

    def _assert_row_and_no_edge(self, md: str, row: str) -> None:
        self.assertIn(row, md)
        self.assertEqual(
            md.count("product CoreKit of target AppCore resolves to 0 containers; no edge is drawn"), 1)
        self.assertIn("- `unresolved-reference` `App/Package.swift` lines 8-8 — product CoreKit of target "
                      "AppCore resolves to 0 containers; no edge is drawn", md)
        self.assertNotIn("-->", md)
        self.assertNotIn("symlinked", md)
        self.assertNotIn("Vendor_CorePkg_Package_swift__CoreKit", md)
        self.assertNotIn("path-escape", md)

    def test_a_symlinked_path_dependency_renders_its_row_and_no_edge(self):
        for dep in ('.product(name: "CoreKit", package: "Alias")', '"CoreKit"'):
            with self.subTest(dep=dep):
                self.setUp()
                self._alias_tree(dep)
                md, reads = self._recorded_graph()
                self._assert_row_and_no_edge(
                    md, "| `App` | `../Alias` | path dependency | `Alias` | — | `App/Package.swift:5-5` |")
                alias = str(self.root / "Alias")
                self.assertEqual([p for p in reads if p == alias or p.startswith(alias + os.sep)], [])

    def test_a_symlink_into_a_pruned_directory_renders_its_lexical_row(self):
        self._link("PodLink", "Pods")
        self.write("Pods/PodPkg/Package.swift", _core_kit_manifest("PodPkg"))
        self.write("App/Package.swift", _APP_MANIFEST.format(
            path="../PodLink/PodPkg", dep='.product(name: "CoreKit", package: "PodPkg")'))
        md = self._graph()
        self._assert_row_and_no_edge(
            md, "| `App` | `../PodLink/PodPkg` | path dependency | `PodLink/PodPkg` | — | "
                "`App/Package.swift:5-5` |")

    def test_positive_control_the_read_recorder_sees_a_read_through_the_alias(self):
        """The recorder above is armed: a listing through `Alias` inside the
        armed window is recorded, so an empty list there is a measurement."""
        self._alias_tree('"CoreKit"')
        real_graph = self.swift.extract_module_graph

        def graph_then_list(root, docs_dir):
            os.listdir(self.root / "Alias")
            return real_graph(root, docs_dir)

        with mock.patch.object(self.swift, "extract_module_graph", graph_then_list):
            _md, reads = self._recorded_graph()
        self.assertIn(str(self.root / "Alias"), reads)

    def test_control_a_real_directory_path_dependency_renders_its_row_and_its_edge(self):
        self.write("Vendor/CorePkg/Package.swift", _core_kit_manifest("CorePkg"))
        self.write("App/Package.swift", _APP_MANIFEST.format(
            path="../Vendor/CorePkg", dep='.product(name: "CoreKit", package: "CorePkg")'))
        md = self._graph()
        self.assertIn("| `App` | `../Vendor/CorePkg` | path dependency | `Vendor/CorePkg` | — | "
                      "`App/Package.swift:5-5` |", md)
        self.assertEqual(_edges(md), {("AppCore (App/Package.swift)",
                                       "CoreKit (Vendor/CorePkg/Package.swift)")})
        self.assertNotIn("unresolved-reference", md)


#: The check-order root manifest: `.package(path: "Pods/X")` on line 4, the
#: product qualified by `X` on line 7.
_POD_ROOT_MANIFEST = (
    'let package = Package(\n'
    '    name: "M",\n'
    '    dependencies: [\n'
    '        .package(path: "Pods/X"),\n'
    '    ],\n'
    '    targets: [\n'
    '        .target(name: "Core", dependencies: [.product(name: "CoreKit", package: "X")]),\n'
    '    ]\n'
    ')\n'
)


class PathDependencyCheckOrderTests(_SwiftTree):
    """ADR-0129 clause 4 and ADR-0130 clause 3, the check order at
    `.package(path:)`: lexical
    normalisation (escape), then the lexical prune test, then real-path
    containment, then the row. A reference into a pruned directory renders
    the pruned `unresolved-reference` whatever `Pods/X` is on disk, and no
    filesystem call touches it. Audit hooks raise no event for `lstat` or
    `readlink`, so a spy on the containment call is the proof. The check is
    `swift_xcinputs.contained`, the core's verdict in time linear in the
    path, so the spy wraps it there."""

    def _pods_tree(self, link_target: Path) -> None:
        self.write("Package.swift", _POD_ROOT_MANIFEST)
        self.write("Other/Package.swift", _core_kit_manifest("Other"))
        (self.root / "Pods").mkdir()
        try:
            os.symlink(link_target, self.root / "Pods" / "X", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("host refuses symlink creation")

    def _spied_graph(self):
        self.swift._CACHE.update(root=None, files={}, manifests={})
        xi = self.swift.swift_xcinputs
        with mock.patch.object(xi, "contained", wraps=xi.contained) as spy:
            md = self.swift.extract_module_graph(self.root, "bionic")[0]
        return md, [str(c.args[1]) for c in spy.call_args_list]

    def _assert_pruned_and_untouched(self, md: str, touched: list) -> None:
        self.assertEqual(md.count(self.swift.swift_prune.PATH_DEPENDENCY_DETAIL), 1)
        self.assertIn("- `unresolved-reference` `Package.swift` lines 4-4 — "
                      + self.swift.swift_prune.PATH_DEPENDENCY_DETAIL, md)
        self.assertIn("- `unresolved-reference` `Package.swift` lines 7-7 — product CoreKit of target "
                      "Core names a package whose `.package(path:)` reference was refused; "
                      "no edge is drawn", md)
        self.assertNotIn("path-escape", md)
        self.assertNotIn("path dependency", md)
        self.assertNotIn("-->", md)
        self.assertEqual([p for p in touched if "Pods" in p], [])

    def test_a_pruned_reference_symlinked_outside_the_checkout_is_pruned_not_escaped(self):
        import tempfile
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside).resolve() / "X"
            target.mkdir()
            (target / "Package.swift").write_text(_core_kit_manifest("X"), encoding="utf-8")
            self._pods_tree(target)
            md, touched = self._spied_graph()
        self._assert_pruned_and_untouched(md, touched)

    def test_a_pruned_reference_symlinked_inside_the_checkout_is_pruned(self):
        self.write("Vendor/X/Package.swift", 'let package = Package(name: "X", targets: [.target(name: "XT")])\n')
        self._pods_tree(self.root / "Vendor" / "X")
        md, touched = self._spied_graph()
        self._assert_pruned_and_untouched(md, touched)

    def test_positive_control_the_spy_sees_a_contained_reference(self):
        """The same spy records the containment call for a reference outside
        every pruned directory, so its empty list above is a measurement."""
        self.write("Vendor/X/Package.swift", _core_kit_manifest("X"))
        self.write("Package.swift", _POD_ROOT_MANIFEST.replace("Pods/X", "Vendor/X"))
        md, touched = self._spied_graph()
        self.assertEqual(touched, [str(self.root / "Vendor" / "X")])
        self.assertEqual(_edges(md), {("Core (Package.swift)", "CoreKit (Vendor/X/Package.swift)")})


class MissingGrammarTests(_SwiftTree):
    """ADR-0129 clause 2: a missing grammar is `ParserUnavailable`, exit 2 with
    nothing written; a derive that does not resolve to swift never loads it."""

    def _run(self, root: Path, block: bool):
        import subprocess
        script = (_BLOCKER if block else "") + (
            "import sys\n"
            f"sys.argv = ['derive-arch.py', '--repo-root', {str(root)!r}]\n"
            f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
            "import importlib.util\n"
            f"spec = importlib.util.spec_from_file_location('drv', {str(DRIVER)!r})\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "sys.exit(m.main())\n")
        return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)

    def test_a_blocked_grammar_exits_2_and_writes_nothing(self):
        proc = self._run(self.root, block=True)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("ParserUnavailable", proc.stderr + proc.stdout)
        self.assertIn("tree_sitter_swift", proc.stderr + proc.stdout)
        self.assertFalse((self.root / "bionic" / "arch").exists())

    def test_positive_control_the_unblocked_derive_exits_0_and_writes(self):
        proc = self._run(self.root, block=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((self.root / "bionic" / "arch" / "data-model.md").is_file())

    def test_a_python_derive_with_the_swift_grammar_blocked_exits_0(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: bionic\n')
            (root / "bionic").mkdir()
            (root / "pyproject.toml").write_text('[project]\nname = "pkg"\n')
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("")
            proc = self._run(root, block=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((root / "bionic" / "arch" / "data-model.md").is_file())


def _deep_expression(depth: int) -> str:
    """A one-line Swift file whose parse tree nests `depth` levels deep: an
    initializer of `depth` parentheses. The pinned grammar gives up before the
    innermost level and inserts one MISSING token there."""
    return "let x = " + "(" * depth + ")" * depth + "\n"


class DeepParseTreeTests(_SwiftTree):
    """ADR-0129 clause 2: content never crashes the derive. A tree-sitter
    `Node.parent` call searches down from the root, so walking the ancestors of
    an error node costs time quadratic in its depth, and past about 70,000
    levels the native call overflows the C stack. The error classifier reads
    the ancestors the walk already visited instead."""

    def _derive(self):
        import subprocess
        script = (
            "import sys\n"
            f"sys.argv = ['derive-arch.py', '--repo-root', {str(self.root)!r}]\n"
            f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
            "import importlib.util\n"
            f"spec = importlib.util.spec_from_file_location('drv', {str(DRIVER)!r})\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "sys.exit(m.main())\n")
        return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                              timeout=600)

    def test_a_100000_deep_file_derives_with_one_parse_error(self):
        import json
        self.write("Sources/Core/Deep.swift", _deep_expression(100_000))
        self.write("Sources/Core/Good.swift", "public struct Good {}\n")
        proc = self._derive()
        self.assertNotIn(proc.returncode, (139, -11), "the derive crashed on a deep parse tree")
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        json.loads(proc.stdout)
        md = (self.root / "bionic" / "arch" / "data-model.md").read_text(encoding="utf-8")
        deep = [b for b in _residual_bullets(md)
                if b[0] == "parse-error" and b[1] == "Sources/Core/Deep.swift"]
        self.assertEqual(len(deep), 1, md[-2000:])
        self.assertIn("| `Good` | struct |", md)

    def test_a_10000_deep_file_classifies_within_the_time_bound(self):
        # Timed on `_timing.clock`, the calling thread's CPU time: the parse
        # and the classification run in this thread, and time spent waiting
        # for a core on a loaded host is not charged to them.
        raw = _deep_expression(10_000).encode()
        started = _timing.clock()
        facts = self.swift._parse_file("Deep.swift", raw)
        elapsed = _timing.clock() - started
        # The classification is the same one the ancestor walk produced.
        self.assertEqual(facts.residuals, [
            ("parse-error", [(1, 1)], "location declaration header; effect enclosing var x")])
        # About 0.05 s linear; the ancestor walk through `Node.parent` took 3-6 s.
        self.assertLess(elapsed, 1.0,
                        f"classifying a 10,000-deep file took {elapsed:.1f} s of thread CPU time")


def _nested_structs(depth: int) -> str:
    return "struct A {\n" * depth + "}\n" * depth


_NESTING_DETAIL = "declaration nesting passes 64 levels; declarations nested deeper do not render"
_BUDGET_DETAIL = ("the declaration rows pass the per-file name bound of 8 times the file's size "
                  "plus 64 KiB; later declarations do not render")


class DeclarationOutputBoundTests(unittest.TestCase):
    """ADR-0129 clause 2: a row names its type qualified by every enclosing declaration, so
    unbounded nesting makes the rendered text grow with the square of the
    depth, and a long type name repeats in every member row. Declaration
    nesting is bounded at 64 levels, and the name text one file's rows carry is
    bounded at 8 times the file's size plus 64 KiB. Each bound renders one
    `scan-cap` line: a scan limit, in ADR-0129 clause 7's closed vocabulary."""

    def setUp(self):
        self.swift = _fresh_swift()

    def _caps(self, facts):
        return [r for r in facts.residuals if r[0] == "scan-cap"]

    def test_64_levels_render_every_type_and_no_residual(self):
        facts = self.swift._parse_file("N.swift", _nested_structs(64).encode())
        self.assertEqual(len(facts.types), 64)
        self.assertEqual(facts.types[-1]["name"], ".".join(["A"] * 64))
        self.assertEqual(facts.residuals, [])

    def test_65_levels_render_64_types_and_one_scan_cap(self):
        facts = self.swift._parse_file("N.swift", _nested_structs(65).encode())
        self.assertEqual(len(facts.types), 64)
        self.assertEqual(self._caps(facts), [("scan-cap", [(65, 65)], _NESTING_DETAIL)])

    def test_an_extension_counts_as_a_nesting_level(self):
        src = "extension E {\n" + _nested_structs(64) + "}\n"
        facts = self.swift._parse_file("N.swift", src.encode())
        self.assertEqual(len(facts.types), 63)
        self.assertEqual(self._caps(facts), [("scan-cap", [(65, 65)], _NESTING_DETAIL)])

    def test_a_10000_deep_file_renders_a_bounded_data_model(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "N.swift").write_text(_nested_structs(10_000))
            md, _ = self.swift.extract_data_model(Path(d), "bionic")
        self.assertLess(len(md.encode()), 200_000)
        self.assertIn(("scan-cap", "N.swift", "65-65", _NESTING_DETAIL), _residual_bullets(md))

    def test_a_long_name_with_many_members_renders_linear_in_the_file(self):
        import tempfile
        name = "T" * 10_000
        src = ("public struct " + name + " {\n"
               + "".join(f"  public let p{i}: Int\n" for i in range(10_000)) + "}\n")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "L.swift").write_text(src)
            md, _ = self.swift.extract_data_model(Path(d), "bionic")
            api, _ = self.swift.extract_api_surface(Path(d), "bionic")
        bound = 2 * (8 * len(src) + 64 * 1024)
        self.assertLess(len(md.encode()), bound)
        self.assertLess(len(api.encode()), bound)
        caps = [b for b in _residual_bullets(md) if b[0] == "scan-cap"]
        self.assertEqual(len(caps), 1)
        self.assertEqual((caps[0][1], caps[0][3]), ("L.swift", _BUDGET_DETAIL))
        self.assertIn("| `" + name + "` | struct | public |", md)


def _table_cells(markdown: str, heading: str) -> list:
    """The cells of every data row in the table under `## <heading>`."""
    rows, inside = [], False
    for line in markdown.split("\n"):
        if line.startswith("## "):
            inside = line == "## " + heading
            continue
        if inside and line.startswith("| ") and not line.startswith("|---"):
            rows.append([c.strip() for c in line.strip().strip("|").split(" | ")])
    return rows[1:] if rows else rows


class NameBudgetCoverageTests(unittest.TestCase):
    """Every text a row repeats counts against the per-file name bound
    (ADR-0129 clause 2): attribute text on every interface row, the owner on
    every `stores` relationship, the protocol on every requirement, and the
    type on every conformance row. Each case renders unbounded without its
    charge and renders one budget `scan-cap` with it."""

    def setUp(self):
        self.swift = _fresh_swift()

    def _derive(self, src: str):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "L.swift").write_text(src)
            self.swift._CACHE.update(root=None, files={}, manifests={})
            md, _ = self.swift.extract_data_model(Path(d), "bionic")
            api, _ = self.swift.extract_api_surface(Path(d), "bionic")
        return md, api

    def _budget_caps(self, markdown: str) -> list:
        return [b for b in _residual_bullets(markdown) if b[0] == "scan-cap" and b[3] == _BUDGET_DETAIL]

    def test_attribute_text_counts_against_the_name_budget(self):
        attribute = "@A." + ".".join(f"B{i}" for i in range(2000))
        src = attribute + " public var " + ", ".join(f"v{i} = 0" for i in range(2000)) + "\n"
        _md, api = self._derive(src)
        rows = _table_cells(api, "Interfaces")
        self.assertTrue(rows)
        rendered = sum(len(r[0]) + len(r[4]) for r in rows)
        self.assertLessEqual(rendered, 8 * len(src.encode()) + 64 * 1024)
        self.assertEqual(len(self._budget_caps(api)), 1)

    def test_attribute_text_control_a_small_file_renders_every_row(self):
        src = "@A.B public var " + ", ".join(f"v{i} = 0" for i in range(20)) + "\n"
        _md, api = self._derive(src)
        self.assertEqual(len(_table_cells(api, "Interfaces")), 20)
        self.assertEqual(self._budget_caps(api), [])
        self.assertIn("@A.B", api)

    def test_stored_type_names_count_against_the_name_budget(self):
        owner = "O" * 5000
        types = "".join(f"struct T{i} {{}}\n" for i in range(1000))
        src = types + f"struct {owner} {{\n  var p: (" + ", ".join(f"T{i}" for i in range(1000)) + ")\n}\n"
        md, _api = self._derive(src)
        self.assertLess(len(md.encode()), 2 * (8 * len(src.encode()) + 64 * 1024))
        self.assertEqual(len(self._budget_caps(md)), 1)

    def test_protocol_requirements_count_against_the_name_budget(self):
        name = "P" * 10_000
        src = (f"public protocol {name} {{\n"
               + "".join(f"  func f{i}()\n" for i in range(1000)) + "}\n")
        _md, api = self._derive(src)
        self.assertLess(len(api.encode()), 2 * (8 * len(src.encode()) + 64 * 1024))
        self.assertEqual(len(self._budget_caps(api)), 1)

    def test_type_conformances_count_against_the_name_budget(self):
        name = "S" * 10_000
        src = f"struct {name}: " + ", ".join(f"P{i}" for i in range(1000)) + " {}\n"
        md, _api = self._derive(src)
        self.assertLess(len(md.encode()), 2 * (8 * len(src.encode()) + 64 * 1024))
        self.assertEqual(len(self._budget_caps(md)), 1)

    def test_extension_conformances_count_against_the_name_budget(self):
        name = "E" * 10_000
        src = f"extension {name}: " + ", ".join(f"P{i}" for i in range(1000)) + " {}\n"
        md, _api = self._derive(src)
        self.assertLess(len(md.encode()), 2 * (8 * len(src.encode()) + 64 * 1024))
        self.assertEqual(len(self._budget_caps(md)), 1)

    def test_conformance_control_a_short_list_renders_every_row(self):
        src = "struct S: P0, P1, P2 {}\nextension E: Q0, Q1 {}\n"
        md, _api = self._derive(src)
        self.assertEqual(len(_table_cells(md, "Relationships")), 5)
        self.assertEqual(self._budget_caps(md), [])


#: One CJK ideograph: one code point, three UTF-8 bytes.
_CJK = "名"


class NameBoundCountsUtf8BytesTests(unittest.TestCase):
    """The per-file name bound and the parse-error bound compare against 8
    times the file's size in BYTES, so they charge the UTF-8 bytes of the
    text, not its code points. Each case below charges between one third of
    the bound and the whole bound in code points, and more than the bound in
    bytes: counting code points renders every line and no `scan-cap`."""

    def setUp(self):
        self.swift = _fresh_swift()

    def test_a_cjk_type_name_over_many_conformances_trips_the_name_bound(self):
        src = (f"struct {_CJK * 10_000}: " + ", ".join(f"P{i}" for i in range(20)) + " {}\n").encode()
        facts = self.swift._parse_file("C.swift", src)
        budget = 8 * len(src) + 64 * 1024
        code_points = sum(10_000 + len(f"P{i}") for i in range(20))
        self.assertLess(code_points, budget)
        self.assertEqual(facts.name_budget, budget)
        self.assertLessEqual(facts.name_bytes - (30_000 + len("P19")), budget)
        self.assertGreater(facts.name_bytes, budget)
        self.assertLess(len(facts.relationships), 20)
        self.assertEqual([r for r in facts.residuals if r[0] == "scan-cap"],
                         [("scan-cap", [(1, 1)], _BUDGET_DETAIL)])

    def test_the_same_trip_through_the_registered_extractor(self):
        import tempfile
        src = f"struct {_CJK * 10_000}: " + ", ".join(f"P{i}" for i in range(20)) + " {}\n"
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "C.swift").write_text(src, encoding="utf-8")
            self.swift._CACHE.update(root=None, files={}, manifests={})
            md, _ = self.swift.extract_data_model(Path(d), "bionic")
        self.assertIn(("scan-cap", "C.swift", "1-1", _BUDGET_DETAIL), _residual_bullets(md))

    def test_control_a_cjk_name_within_the_bound_renders_every_row(self):
        src = (f"struct {_CJK * 10_000}: " + ", ".join(f"P{i}" for i in range(5)) + " {}\n").encode()
        facts = self.swift._parse_file("C.swift", src)
        self.assertEqual(len(facts.relationships), 5)
        # The type row charges the name once; each conformance row charges
        # the name and its protocol.
        self.assertEqual(facts.name_bytes, 30_000 + 5 * 30_000 + sum(len(f"P{i}") for i in range(5)))
        self.assertEqual([r for r in facts.residuals if r[0] == "scan-cap"], [])

    def test_a_cjk_label_over_many_parse_errors_trips_the_error_bound(self):
        src = ("func " + _CJK * 3000 + "() {\n" + "x(]\n" * 30 + "}\n").encode()
        facts = self.swift._parse_file("E.swift", src)
        errors = [r for r in facts.residuals if r[0] == "parse-error"]
        caps = [r for r in facts.residuals if r[0] == "scan-cap"]
        budget = 8 * len(src) + 64 * 1024
        self.assertLessEqual(sum(len(r[2].encode("utf-8")) for r in errors), budget)
        self.assertLess(len(errors), 30)
        self.assertEqual(len(caps), 1)
        self.assertEqual(caps[0][2], "the parse-error lines pass the per-file bound of 8 times the "
                                     "file's size plus 64 KiB; later parse errors do not render")

    def test_control_a_cjk_label_over_few_errors_renders_every_error(self):
        src = ("func " + _CJK * 3000 + "() {\n" + "x(]\n" * 10 + "}\n").encode()
        facts = self.swift._parse_file("E.swift", src)
        self.assertEqual(len([r for r in facts.residuals if r[0] == "parse-error"]), 10)
        self.assertEqual([r for r in facts.residuals if r[0] == "scan-cap"], [])


_IF_DEPTH_DETAIL = ("`#if` nesting passes 64 levels; declarations nested deeper do not render")


class IfDirectiveDepthTests(unittest.TestCase):
    """ADR-0129 clause 2: `#if` nesting is bounded at 64 levels, the same
    bound declaration nesting has. Every occurrence records its `#if` stack,
    so an unbounded depth multiplies the work and memory by the depth.
    Declarations nested past 64 levels do not render, and the first 65th
    `#if` renders one `scan-cap` line."""

    def setUp(self):
        self.swift = _fresh_swift()

    def _caps(self, facts):
        return [r for r in facts.residuals if r[0] == "scan-cap"]

    def test_if_directive_depth_is_bounded(self):
        depth, count = 3000, 3000
        src = ("#if A\n" * depth + "".join(f"public var v{i} = 0\n" for i in range(count))
               + "#endif\n" * depth + "public var after = 0\n")
        facts = self.swift._parse_file("D.swift", src.encode())
        self.assertEqual(self._caps(facts), [("scan-cap", [(65, 65)], _IF_DEPTH_DETAIL)])
        self.assertEqual([i["name"] for i in facts.interfaces], ["after"])
        self.assertFalse(facts.interfaces[0]["conditional"])
        self.assertLessEqual(max((len(o[2]) for o in facts.conditional_occurrences), default=0), 64)

    def test_if_directive_depth_control_64_levels_render_every_declaration(self):
        src = ("#if A\n" * 64 + "public var v0 = 0\npublic struct S {}\n" + "#endif\n" * 64
               + "public var after = 0\n")
        facts = self.swift._parse_file("D.swift", src.encode())
        self.assertEqual(facts.residuals, [])
        self.assertEqual([(i["name"], i["conditional"]) for i in facts.interfaces],
                         [("v0", True), ("S", True), ("after", False)])

    def test_a_deep_if_file_renders_a_bounded_api_surface(self):
        import tempfile
        src = ("#if A\n" * 3000 + "".join(f"public var v{i} = 0\n" for i in range(3000))
               + "#endif\n" * 3000)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "D.swift").write_text(src)
            self.swift._CACHE.update(root=None, files={}, manifests={})
            api, _ = self.swift.extract_api_surface(Path(d), "bionic")
        self.assertLess(len(api.encode()), 64 * 1024)
        self.assertIn(("scan-cap", "D.swift", "65-65", _IF_DEPTH_DETAIL), _residual_bullets(api))

    def _dropped_under(self, depth):
        """`_parse_file` over fixture 13's dropped actor wrapped in `depth`
        `#if` blocks, with every `_recover` call recorded."""
        body = (FIXTURES / "13-dropped-declaration.swift").read_text()
        src = ("#if A\n" * depth + body + "#endif\n" * depth).encode()
        calls = []
        real = self.swift._recover

        def spy(err, raw):
            calls.append(err)
            return real(err, raw)

        with mock.patch.object(self.swift, "_recover", spy):
            facts = self.swift._parse_file("D.swift", src)
        return facts, calls

    def test_a_declaration_dropped_past_the_if_bound_is_not_recovered(self):
        # A declaration the grammar dropped inside `#if` blocks past the bound
        # sits where nothing renders. Recovery is skipped there: no re-parse,
        # no `declaration-recovered` or `declaration-dropped` line. The
        # `scan-cap` line is the only residual.
        facts, calls = self._dropped_under(65)
        self.assertEqual(calls, [])
        self.assertEqual(facts.residuals, [("scan-cap", [(65, 65)], _IF_DEPTH_DETAIL)])
        self.assertEqual(facts.interfaces, [])

    def test_control_a_declaration_dropped_at_the_if_bound_is_recovered(self):
        # Positive control: at 64 levels the same dropped actor is recovered
        # once and renders conditional, so the case above is not vacuous.
        facts, calls = self._dropped_under(64)
        self.assertEqual(len(calls), 1)
        self.assertEqual([r[0] for r in facts.residuals], ["declaration-recovered"])
        self.assertEqual({i["name"]: i["conditional"] for i in facts.interfaces},
                         dict.fromkeys(("ShelfCatalog", "ShelfCatalog.shelfCount",
                                        "ShelfCatalog.init(shelves:)",
                                        "ShelfCatalog.isEmpty()"), True))


class SwiftPruneTests(unittest.TestCase):
    """Every Swift walk prunes one set of directories, by repo-relative
    name (ADR-0129 clause 8, which governs ADR-0130 clause 9's folder-synced
    walk). A project reference into that set is refused before any
    filesystem access."""

    PRUNED = ("93-pruned-synced-roots", "94-pruned-dirs-inside-synced-root",
              "95-pruned-references-into-pods", "96-pruned-package-path-dependency",
              "97-pruned-dirs-under-an-exception-directory")

    def setUp(self):
        self.swift = _fresh_swift()
        self.prune = importlib.import_module("crux.arch.packs.swift_prune")
        self.h = _harness()
        import tempfile
        self._d = tempfile.TemporaryDirectory()
        self.addCleanup(self._d.cleanup)
        self.tmp = Path(self._d.name).resolve()

    def _tree(self, name: str, dest: Path, with_pruned: bool = True) -> Path:
        fixture = self.h.FIXTURES_ROOT / name
        spec = self.h.load_expected(fixture) if with_pruned else {}
        self.h.materialize(fixture, dest, spec)
        return dest

    def _derive(self, root: Path) -> dict:
        self.swift._CACHE.update(root=None, files={}, manifests={})
        return {c: f(root, "bionic")[0] for c, f in (
            ("data-model", self.swift.extract_data_model),
            ("api-surface", self.swift.extract_api_surface),
            ("module-graph", self.swift.extract_module_graph))}

    def test_the_predicate_reads_each_repo_relative_component(self):
        for segs in (("Pods",), ("App", "Pods", "X.swift"), ("App", ".build", "B.swift"),
                     ("node_modules",), ("DerivedData", "A.swift"), ("App", "build"),
                     ("Carthage",), ("SourcePackages", "x"), ("App.xcodeproj", "x")):
            with self.subTest(segs=segs):
                self.assertTrue(self.prune.pruned_path(segs))
        for segs in ((), ("App", "Main.swift"), ("Podsicle",), ("App", "Carthagen"),
                     ("App", "builds")):
            with self.subTest(segs=segs):
                self.assertFalse(self.prune.pruned_path(segs))
        # A workspace reference names a bundle as a container the walk reaches.
        self.assertFalse(self.prune.pruned_path(("ios", "App.xcodeproj"), container=True))
        self.assertTrue(self.prune.pruned_path(("ios", "App.xcodeproj")))
        self.assertTrue(self.prune.pruned_path(("Pods", "Pods.xcodeproj"), container=True))
        self.assertTrue(self.prune.pruned_path(("App.xcodeproj", "x"), container=True))

    def test_the_spine_is_identical_with_and_without_the_pruned_directories(self):
        for name in self.PRUNED:
            with self.subTest(fixture=name):
                with_dirs = self._derive(self._tree(name, self.tmp / name / "with"))
                without = self._derive(self._tree(name, self.tmp / name / "without",
                                                  with_pruned=False))
                self.assertEqual(with_dirs, without)

    def test_a_checkout_under_an_absolute_path_holding_pods_still_renders(self):
        root = self._tree("94-pruned-dirs-inside-synced-root", self.tmp / "Pods" / "case")
        md = self._derive(root)["module-graph"]
        self.assertIn("| `App/Main.swift` | `App` | folder-synced root App | — |", md)

    def test_positive_control_with_the_predicate_disabled_pruned_paths_render(self):
        from unittest import mock
        with mock.patch.object(self.prune, "pruned_path", lambda segs, container=False: False), \
                mock.patch.object(self.prune, "pruned_name", lambda name: False):
            synced = self._derive(self._tree("93-pruned-synced-roots", self.tmp / "a"))
            inside = self._derive(self._tree("94-pruned-dirs-inside-synced-root", self.tmp / "b"))
            refs = self._derive(self._tree("95-pruned-references-into-pods", self.tmp / "c"))
            dep = self._derive(self._tree("96-pruned-package-path-dependency", self.tmp / "d"))
        self.assertIn("DerivedData/Gen.swift", synced["module-graph"])
        self.assertIn("App/Pods/P.swift", inside["module-graph"])
        self.assertIn("App/Pods/Extra.swift", refs["module-graph"])
        self.assertIn("path dependency", dep["module-graph"])

    def test_positive_control_the_exception_directory_walk_prunes_by_name(self):
        """An exception entry naming an ordinary directory walks it with the
        same prune rule. With `pruned_name` forced False, the files under
        `Sub/Pods`, `Sub/.build` and `Sub/build` render as rows for `Other`,
        which only that exception walk produces; with the rule in force,
        none does."""
        from unittest import mock
        name = "97-pruned-dirs-under-an-exception-directory"
        needles = tuple("| `App/Sub/%s` | `Other` | added by an exception set |" % f
                        for f in ("Pods/X.swift", ".build/Z.swift", "build/W.swift"))
        pruned = self._derive(self._tree(name, self.tmp / "on"))["module-graph"]
        self.assertIn("| `App/Sub/Y.swift` | `Other` | added by an exception set |", pruned)
        for needle in needles:
            self.assertNotIn(needle, pruned)
        with mock.patch.object(self.prune, "pruned_name", lambda name: False):
            unpruned = self._derive(self._tree(name, self.tmp / "off"))["module-graph"]
        for needle in needles:
            self.assertIn(needle, unpruned)

    def test_the_synced_walk_holds_no_recursion(self):
        import inspect
        root = self._tree("94-pruned-dirs-inside-synced-root", self.tmp / "deep", with_pruned=False)
        deep = root / "App"
        for _ in range(200):
            deep = deep / "d"
        deep.mkdir(parents=True)
        (deep / "Leaf.swift").write_text("struct Leaf {}\n")
        limit = sys.getrecursionlimit()
        sys.setrecursionlimit(len(inspect.stack()) + 120)
        try:
            md = self._derive(root)["module-graph"]
        finally:
            sys.setrecursionlimit(limit)
        self.assertIn("/d/Leaf.swift` | `App` | folder-synced root App |", md)


_TRAP = r"""
import sys, json, hashlib
fired = []
_EVENTS = ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn",
           "os.fork", "os.forkpty")
def _hook(event, args):
    if event in _EVENTS:
        fired.append(event)
        raise RuntimeError("process creation trapped: " + event)
sys.addaudithook(_hook)
"""


class NoExecutionTests(unittest.TestCase):
    """ADR-0129 clause 2's postcondition: a derive with no `swift` on `PATH`
    and process creation trapped completes with identical bytes."""

    def _tree(self, tmp: Path) -> Path:
        import shutil
        root = tmp / "repo"
        shutil.copytree(FIXTURES, root / "Sources" / "Decls")
        shutil.copytree(MANIFESTS / "literal-subset", root / "Pkg")
        shutil.copy(MANIFESTS / "literal-subset" / "Package.swift", root / "Package.swift")
        return root

    def _child(self, root: Path, spawn: bool = False):
        import os
        import subprocess
        script = _TRAP + (
            f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
            "from pathlib import Path\n"
            "from crux.arch import core\n"
            "from crux.arch.packs import swift\n")
        if spawn:
            script += (
                "import subprocess\n"
                "_real = swift.extract_data_model\n"
                "def _spawning(root, docs):\n"
                "    try:\n"
                "        subprocess.run(['swift', '--version'])\n"
                "    except Exception:\n"
                "        pass\n"
                "    return _real(root, docs)\n"
                "swift.extract_data_model = _spawning\n"
                "swift.probes = lambda: {'data-model': [core.Probe(swift._always_swift, _spawning, kind='parser')],\n"
                "    'api-surface': [core.Probe(swift._always_swift, swift.extract_api_surface, kind='parser')],\n"
                "    'module-graph': [core.Probe(swift._always_swift, swift.extract_module_graph, kind='parser')]}\n")
        script += (
            f"tree = core._build(Path({str(root)!r}), 'bionic')\n"
            "digest = hashlib.sha256(json.dumps(tree, sort_keys=True).encode()).hexdigest()\n"
            "print(json.dumps({'fired': fired, 'digest': digest}))\n")
        env = {k: v for k, v in os.environ.items() if k not in ("PATH",)}
        env["PATH"] = "/nonexistent"
        return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=env)

    def _parent_digest(self, root: Path) -> str:
        import hashlib
        import json
        swift = _fresh_swift()
        tree = _core()._build(root, "bionic")
        swift._CACHE.update(root=None, files={}, manifests={})
        return hashlib.sha256(json.dumps(tree, sort_keys=True).encode()).hexdigest()

    def _assert_silent_and_identical(self, root: Path):
        import json
        proc = self._child(root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(result["fired"], [])
        self.assertEqual(result["digest"], self._parent_digest(root))

    def test_a_fixture_derive_runs_no_process(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = self._tree(Path(d))
            self.assertEqual(_core().resolve_stack(root).pack_name, "swift")
            self._assert_silent_and_identical(root)

    def test_the_pinned_package_derive_runs_no_process(self):
        head = SAP_CACHE / ".git" / "HEAD"
        if not head.is_file():
            self.skipTest(f"swift-argument-parser is not fetched — {FETCH_HINT}")
        self.assertEqual(head.read_text().strip(), PINNED_SAP_HEAD)
        self._assert_silent_and_identical(SAP_CACHE)

    def test_positive_control_a_probe_that_spawns_fires_the_trap(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = self._tree(Path(d))
            proc = self._child(root, spawn=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout.strip().splitlines()[-1])["fired"], ["subprocess.Popen"])


def _harness():
    return importlib.import_module("xcode_fixture_harness")


class XcodeFixtureTests(unittest.TestCase):
    """The data-driven Xcode-fixture harness (ADR-0130 clause 17): every case
    under `fixtures/xcodeproj/<case>/` runs through a real derive. See
    `xcode_fixture_harness.py`'s module docstring for the `expected.yml`
    schema every fixture is authored against."""

    def test_every_fixture_case(self):
        h = _harness()
        fixtures = h.discover_fixtures()
        self.assertGreaterEqual(len(fixtures), 1, "no fixtures discovered under fixtures/xcodeproj/")
        for fixture_dir in fixtures:
            with self.subTest(fixture=fixture_dir.name):
                h.run_case(fixture_dir, timeout=60)

    def test_positive_control_an_outside_open_is_caught(self):
        result = _harness().positive_control_outside_open_is_caught()
        self.assertEqual(len(result["outside_opens"]), 1)
        self.assertIn("canary.txt", result["outside_opens"][0])

    def test_positive_control_a_process_spawn_is_caught(self):
        result = _harness().positive_control_process_spawn_is_caught()
        self.assertEqual(result["fired"], ["subprocess.Popen"])

    def test_positive_control_an_outside_listing_is_caught(self):
        # One `os.listdir` and one `os.scandir` of the canary directory; the
        # same two calls on the fixture root record nothing.
        result = _harness().positive_control_outside_listing_is_caught()
        self.assertEqual(len(result["outside_listings"]), 2, result)
        self.assertEqual(len(set(result["outside_listings"])), 1, result)
        self.assertEqual(result["outside_opens"], [])

    def test_positive_control_a_derive_listing_outside_the_allowed_set_is_caught(self):
        # The same hook inside a real derive: with the fixture root withheld
        # from the allowed set, the derive's own listings of it are recorded,
        # and with the root allowed none is.
        import tempfile
        h = _harness()
        fixture = h.FIXTURES_ROOT / "00-harness-control"
        expected = h.load_expected(fixture)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve() / "case"
            h.materialize(fixture, root, expected)
            withheld = [p for p in h.allowed_prefixes(root) if p != str(root)]
            self.assertNotEqual(withheld, h.allowed_prefixes(root))
            outside = h._run_child(["--repo-root", str(root)], withheld, 60)
            inside = h._run_child(["--repo-root", str(root)], h.allowed_prefixes(root), 60)
        self.assertIn(str(root), outside["outside_listings"])
        self.assertEqual(inside["outside_listings"], [])



class ProjectInputWiringTests(unittest.TestCase):
    """The workspace, xcconfig and generator readers wired into module-graph
    via `_project_facts` -- xcconfig residuals (clause 12), a standalone
    workspace's classified facts passed through as `workspace_facts`
    (clause 11), and the Tuist/XcodeGen `missing-input` check (clause 13)."""

    def setUp(self):
        self.swift = _fresh_swift()

    def _pbxproj(self, target_name="App"):
        return (
            "// !$*UTF8*$!\n{\n\tarchiveVersion = 1;\n\tobjectVersion = 56;\n"
            "\trootObject = PROJ;\n\tobjects = {\n\t\tPROJ = {\n"
            "\t\t\tisa = PBXProject;\n\t\t\tmainGroup = MAIN;\n"
            "\t\t\ttargets = (\n\t\t\t\tT,\n\t\t\t);\n\t\t};\n"
            "\t\tMAIN = {\n\t\t\tisa = PBXGroup;\n"
            '\t\t\tsourceTree = "<group>";\n\t\t\tchildren = (\n\t\t\t);\n\t\t};\n'
            f"\t\tT = {{\n\t\t\tisa = PBXNativeTarget;\n\t\t\tname = {target_name};\n"
            '\t\t\tproductType = "com.apple.product-type.application";\n'
            "\t\t\tbuildPhases = (\n\t\t\t);\n\t\t};\n\t};\n}\n"
        )

    def test_xcconfig_include_and_conditional_setting_render_in_module_graph(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            proj = root / "App.xcodeproj"
            proj.mkdir()
            (proj / "project.pbxproj").write_text(self._pbxproj())
            (root / "Shared").mkdir()
            (root / "Shared" / "S.xcconfig").write_text("// c\n")
            (root / "App.xcconfig").write_text(
                '#include "Shared/S.xcconfig"\n'
                'OTHER_SWIFT_FLAGS[sdk=iphonesimulator*] = -DDEBUG\n'
            )
            md, _ = self.swift.extract_module_graph(root, "bionic")
        self.assertIn("`xcconfig-include` `App.xcconfig` lines 1-1", md)
        self.assertIn("`conditional-setting` `App.xcconfig` lines 2-2", md)

    def test_escaping_include_renders_identical_bytes_whether_or_not_target_exists(self):
        import tempfile

        def derive(create_target: bool):
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                proj = root / "App.xcodeproj"
                proj.mkdir()
                (proj / "project.pbxproj").write_text(self._pbxproj())
                if create_target:
                    (root.parent / "SharedXcodeSettings").mkdir(exist_ok=True)
                (root / "App.xcconfig").write_text(
                    '#include? "../../SharedXcodeSettings/Shared.xcconfig"\n')
                md, _ = self.swift.extract_module_graph(root, "bionic")
                if create_target:
                    import shutil
                    shutil.rmtree(root.parent / "SharedXcodeSettings", ignore_errors=True)
                return md

        without = derive(False)
        with_target = derive(True)
        self.assertIn("`path-escape` `App.xcconfig` lines 1-1", without)
        self.assertEqual(without, with_target)

    def test_standalone_workspace_facts_pass_through_to_read_projects(self):
        # `_project_facts` builds `workspace_facts` from `swift_xcinputs.
        # read_workspace` and hands it to `swift_xcode.read_projects` as a
        # positional 4th argument (ADR-0130 clause 7). A workspace adds no
        # container itself.
        calls = []
        real = self.swift.swift_xcode.read_projects

        def spy(root, reads, manifests, workspace_facts=None, collection=None):
            calls.append(workspace_facts)
            return real(root, reads, manifests, workspace_facts, collection)

        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            proj = root / "App.xcodeproj"
            proj.mkdir()
            (proj / "project.pbxproj").write_text(self._pbxproj())
            ws = root / "App.xcworkspace"
            ws.mkdir()
            (ws / "contents.xcworkspacedata").write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<Workspace version = "1.0">\n'
                '   <FileRef location = "group:App.xcodeproj">\n'
                '   </FileRef>\n'
                '</Workspace>\n'
            )
            self.swift.swift_xcode.read_projects = spy
            try:
                md, _ = self.swift.extract_module_graph(root, "bionic")
            finally:
                self.swift.swift_xcode.read_projects = real
        self.assertEqual(len(calls), 1)
        workspace_facts = calls[0]
        self.assertEqual(len(workspace_facts), 1)
        wf = workspace_facts[0]
        self.assertEqual(wf.path, "App.xcworkspace/contents.xcworkspacedata")
        self.assertEqual([r.path for r in wf.refs], ["App.xcodeproj"])
        # A workspace adds no container row of its own.
        self.assertNotIn("| `App.xcworkspace` |", md)

    def test_package_row_renders_dash_in_product_type_column_when_xcode_target_present(self):
        # A `Package.swift` target sits beside a real
        # Xcode target, so module-graph renders in six-column mode; the
        # package row's product-type cell must render em dash, never blank.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Package.swift").write_text(
                'let package = Package(\n'
                '    name: "MyLib",\n'
                '    products: [.library(name: "MyLib", targets: ["MyLib"])],\n'
                '    targets: [.target(name: "MyLib", dependencies: [])]\n'
                ')\n'
            )
            proj = root / "App.xcodeproj"
            proj.mkdir()
            (proj / "project.pbxproj").write_text(self._pbxproj())
            md, _ = self.swift.extract_module_graph(root, "bionic")
        rows = _section_rows(md, "Targets")
        package_rows = [r for r in rows if r["target"] == "`MyLib`"]
        self.assertEqual(len(package_rows), 1)
        self.assertEqual(package_rows[0]["product type"], "—")


class Clause16PairDiffTests(unittest.TestCase):
    """ADR-0130 clause 16's postcondition: fixtures `60-clause16-with-project/` and
    `61-clause16-without-project/` carry identical Swift sources (one file
    holding `@main`) and the same qualifying XcodeGen `project.yml`; the
    "with" member adds a companion `App.xcodeproj` naming the `@main` file
    in its Sources phase. Per ADR-0130 clause 16's postcondition:
    data-model and api-surface differ ONLY in owning-target cells (no row
    appears or disappears), and module-graph differs only by target rows,
    membership rows and the `missing-input` line the "without" member
    renders. This is the line-by-line diff proof `XcodeFixtureTests`
    (substring `rows`/`absent`/`residuals` assertions) does not itself
    make -- a mutation control (an extra stray row) turns it red."""

    WITH_DIR = FIXTURES.parent / "xcodeproj" / "60-clause16-with-project"
    WITHOUT_DIR = FIXTURES.parent / "xcodeproj" / "61-clause16-without-project"

    def setUp(self):
        self.swift = _fresh_swift()

    def _derive_all(self, root):
        self.swift._CACHE.update(root=None, files={}, manifests={})
        dm, _ = self.swift.extract_data_model(root, "bionic")
        api, _ = self.swift.extract_api_surface(root, "bionic")
        mg, _ = self.swift.extract_module_graph(root, "bionic")
        return {"data-model": dm, "api-surface": api, "module-graph": mg}

    def _assert_api_surface_diff(self, with_rendered: dict, without_rendered: dict) -> None:
        """The api-surface half of the clause-16 pair diff, shared by the
        real test and its mutation control -- every line
        is identical EXCEPT the `@main` row, which differs only in its
        owning-target cell."""
        with_lines = with_rendered["api-surface"].splitlines()
        without_lines = without_rendered["api-surface"].splitlines()
        self.assertEqual(len(with_lines), len(without_lines),
                          "api-surface must not gain or lose a row between the pair")
        main_row_diffs = 0
        for a, b in zip(with_lines, without_lines):
            if a == b:
                continue
            self.assertIn("AppMain", a)
            self.assertIn("AppMain", b)
            self.assertIn("App (App.xcodeproj)", a)
            self.assertNotIn("App (App.xcodeproj)", b)
            main_row_diffs += 1
        self.assertEqual(main_row_diffs, 1, "exactly the @main owning-target cell differs")

    def test_pair_differs_only_in_the_permitted_cells(self):
        with_rendered = self._derive_all(self.WITH_DIR)
        without_rendered = self._derive_all(self.WITHOUT_DIR)

        # data-model: this concern consumes no ProjectFacts at all
        # (`with_manifests=False`) -- byte-identical between the pair.
        self.assertEqual(with_rendered["data-model"], without_rendered["data-model"])

        self._assert_api_surface_diff(with_rendered, without_rendered)

        # module-graph: differs only by target rows, membership rows and
        # the `missing-input` line the "without" member renders.
        self.assertIn("| `App` | `App.xcodeproj` |", with_rendered["module-graph"])
        self.assertNotIn("| `App` | `App.xcodeproj` |", without_rendered["module-graph"])
        self.assertNotIn("`missing-input` `project.yml`", with_rendered["module-graph"])
        self.assertIn("`missing-input` `project.yml`", without_rendered["module-graph"])

    def test_mutation_control_an_extra_row_fails_the_diff(self):
        """Proves `_assert_api_surface_diff` (the SAME diff assertion the
        real test above drives) is non-vacuous: a stray extra line inserted
        into the "without" render must be caught by THAT assertion, not
        merely by a standalone line-count comparison."""
        with_rendered = self._derive_all(self.WITH_DIR)
        without_rendered = self._derive_all(self.WITHOUT_DIR)
        mutated = dict(without_rendered)
        mutated["api-surface"] = (
            without_rendered["api-surface"] + "\n| `Stray` | struct | — | `Extra.swift:1-1` |"
        )
        with self.assertRaises(AssertionError):
            self._assert_api_surface_diff(with_rendered, mutated)


class WorkspaceSeamTests(unittest.TestCase):
    """ADR-0130 clause 7's workspace candidates: `swift._workspace_facts_list`
    passes `swift_xcode_products._workspace_dirs` a tuple of
    `swift_xcinputs.WorkspaceFacts` records, and `_workspace_dirs` reads
    that shape. Fixture `78-workspace-resolves-unlinked-product/` proves
    this end to end through `XcodeFixtureTests`: under a shape mismatch the
    product renders `unresolved-reference` instead of the resolved edge.
    This is the unit-level proof, direct against `_workspace_dirs`."""

    def setUp(self):
        self.products = importlib.import_module("crux.arch.packs.swift_xcode_products")
        self.xcinputs = importlib.import_module("crux.arch.packs.swift_xcinputs")

    def test_enclosing_workspace_package_ref_becomes_a_candidate(self):
        wf = self.xcinputs.WorkspaceFacts(
            path="App.xcworkspace/contents.xcworkspacedata",
            refs=(
                self.xcinputs.WorkspaceRef(kind="xcodeproject", path="App.xcodeproj"),
                self.xcinputs.WorkspaceRef(kind="package", path="External/Foo"),
            ),
            residuals=(),
        )
        dirs = self.products._workspace_dirs((wf,), "App.xcodeproj")
        self.assertEqual(dirs, {"External/Foo"})

    def test_a_workspace_that_never_names_this_project_contributes_nothing(self):
        # A sibling workspace naming a DIFFERENT project must not leak its
        # packages into THIS project's unlinked-product candidate set.
        wf = self.xcinputs.WorkspaceFacts(
            path="Other.xcworkspace/contents.xcworkspacedata",
            refs=(
                self.xcinputs.WorkspaceRef(kind="xcodeproject", path="Other.xcodeproj"),
                self.xcinputs.WorkspaceRef(kind="package", path="External/Bar"),
            ),
            residuals=(),
        )
        dirs = self.products._workspace_dirs((wf,), "App.xcodeproj")
        self.assertEqual(dirs, set())

    def test_none_or_empty_workspace_facts_contribute_nothing(self):
        self.assertEqual(self.products._workspace_dirs(None, "App.xcodeproj"), set())
        self.assertEqual(self.products._workspace_dirs((), "App.xcodeproj"), set())


class DetectGeneratorFormsTests(unittest.TestCase):
    """`detect()`'s Tuist and XcodeGen forms (ADR-0130 clause 13)."""

    def setUp(self):
        self.swift = _fresh_swift()

    def test_tuist_project_and_config_at_root_is_a_marker(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Project.swift").write_text("// tuist\n")
            (root / "Tuist.swift").write_text("// config\n")
            result = self.swift.detect(root)
        self.assertTrue(result.matched)
        self.assertIn("Project.swift", result.markers)

    def test_qualifying_xcodegen_project_yml_at_root_is_a_marker(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "project.yml").write_text(
                "name: App\ntargets:\n  App:\n    type: application\n    platform: iOS\n")
            result = self.swift.detect(root)
        self.assertTrue(result.matched)
        self.assertIn("project.yml", result.markers)

    def test_bare_project_yml_is_not_a_marker(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "project.yml").write_text("not a mapping: [\n")
            result = self.swift.detect(root)
        self.assertFalse(result.matched)

    def test_bare_project_swift_with_no_tuist_file_is_not_a_marker(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Project.swift").write_text("// tuist manifest, no companion\n")
            result = self.swift.detect(root)
        self.assertFalse(result.matched)

    def test_hostile_project_yml_symlink_outside_checkout_is_not_a_marker(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            outer = Path(d)
            root = outer / "repo"
            root.mkdir()
            outside = outer / "outside.yml"
            outside.write_text(
                "name: App\ntargets:\n  App:\n    type: application\n    platform: iOS\n")
            os.symlink(outside, root / "project.yml")

            # Real path on both sides (see the FIFO test below): an open that
            # follows the symlink records the in-checkout name, not this one.
            # The aliasing control below proves the recorder catches it.
            outside_real = os.path.realpath(outside)
            hook, _as_passed, opened = _real_path_open_recorder()
            sys.addaudithook(hook)  # cannot be removed; harmless for later tests.
            result = self.swift.detect(root)
        self.assertFalse(result.matched)
        self.assertNotIn(outside_real, opened)

    def test_hostile_project_yml_symlink_aliasing_control_is_caught_only_by_real_path(self):
        """The discriminating control for the test above: the same symlink,
        the same `detect()` entry point and the same recorder, with only the
        generator check's safe read replaced by one that follows the
        symlink. The manifest then becomes a marker, the resolved list holds
        the outside file, and the as-passed list names only the in-checkout
        `project.yml`. A by-name absence check would read green over this
        read; the real-path one does not."""
        import os
        import tempfile
        from unittest import mock
        from crux.arch.packs import swift_generators

        def unguarded(_root, path, _oversize, **_kw):
            with open(path, "rb") as f:
                return f.read()

        with tempfile.TemporaryDirectory() as d:
            outer = Path(d)
            root = outer / "repo"
            root.mkdir()
            outside = outer / "outside.yml"
            outside.write_text(
                "name: App\ntargets:\n  App:\n    type: application\n    platform: iOS\n")
            os.symlink(outside, root / "project.yml")
            hook, as_passed, resolved = _real_path_open_recorder()
            sys.addaudithook(hook)  # cannot be removed; harmless for later tests.
            with mock.patch.object(swift_generators, "_safe_read_bytes", unguarded):
                result = self.swift.detect(root)
            outside_real = os.path.realpath(outside)
            self.assertTrue(result.matched)
            self.assertIn(outside_real, resolved)
            self.assertIn(str(root / "project.yml"), as_passed)
            self.assertNotIn(str(outside), as_passed)
            self.assertNotIn(outside_real, as_passed)

    def test_hostile_project_yml_symlink_positive_control_would_open(self):
        """ADR-0130 clause 17's positive control: proves the audit hook above is not
        vacuous -- an unguarded plain `open()` of the SAME outside target
        DOES have its open observed by the same hook, so `detect()`'s
        silence in the test above is a real refusal, not an artifact of
        the target being unreachable."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            outer = Path(d)
            outside = outer / "outside.yml"
            outside.write_text(
                "name: App\ntargets:\n  App:\n    type: application\n    platform: iOS\n")

            opened = []

            def hook(event, args):
                if event == "open":
                    opened.append(str(args[0]))

            sys.addaudithook(hook)
            open(outside).close()
        self.assertIn(str(outside), opened)

    def test_hostile_project_yml_fifo_is_not_a_marker_and_does_not_hang(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            os.mkfifo(root / "project.yml")

            # Real path on both sides: the hook records the path as passed,
            # and on macOS a `/var` temporary directory resolves to
            # `/private/var`, so a resolved-vs-recorded comparison matched
            # nothing there and read green vacuously (the prompt-15 Linux
            # cells saw the probe open). The only admissible open of the
            # FIFO is the safe-read contract's own probe -- `os.open` with
            # O_NONBLOCK|O_NOFOLLOW, refused by the following fstat
            # (ADR-0130 clause 17: "a FIFO refused").
            fifo_real = os.path.realpath(root / "project.yml")
            opened = []

            def hook(event, args):
                if event == "open":
                    opened.append(args)

            sys.addaudithook(hook)
            try:
                result = self.swift.detect(root)
            finally:
                pass  # sys.addaudithook cannot be removed; harmless for later tests.
            fifo_opens = [a for a in opened
                          if isinstance(a[0], (str, bytes, os.PathLike))
                          and os.path.realpath(a[0]) == fifo_real]
        self.assertFalse(result.matched)
        probe_flags = os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
        for path, mode, flags in fifo_opens:
            self.assertIsNone(mode, f"a builtin open() reached the FIFO: {path!r}")
            self.assertEqual(flags & probe_flags, probe_flags,
                             f"the FIFO was opened without O_NONBLOCK|O_NOFOLLOW: {flags:#x}")

    def test_project_facts_missing_input_when_no_companion_xcodeproj(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "project.yml").write_text(
                "name: App\ntargets:\n  App:\n    type: application\n    platform: iOS\n")
            md, _ = self.swift.extract_module_graph(root, "bionic")
        self.assertIn("`missing-input` `project.yml` lines — — XcodeGen", md)

    def test_nested_qualifying_manifest_with_companion_renders_no_missing_input(self):
        """ADR-0130 clause 13: a qualifying NESTED XcodeGen
        manifest with a companion `*.xcodeproj` beside it renders NO
        `missing-input` line -- the residual is scoped to the manifest's
        OWN directory, not the checkout root. Root carries an unrelated
        `Package.swift` and no `.xcodeproj` at all, so a root-scoped-only
        check (pre-fix `_generator_residuals`) would find nothing to
        conflate this with; this case instead proves the nested manifest
        is reached and correctly suppressed by its own companion."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Package.swift").write_text(
                'let package = Package(name: "Lib", products: [], targets: [])\n')
            ios = root / "ios"
            ios.mkdir()
            (ios / "project.yml").write_text(
                "name: App\ntargets:\n  App:\n    type: application\n    platform: iOS\n")
            proj = ios / "App.xcodeproj"
            proj.mkdir()
            (proj / "project.pbxproj").write_text("// !$*UTF8*$!\n")
            md, _ = self.swift.extract_module_graph(root, "bionic")
        self.assertNotIn("missing-input", md)

    def test_nested_qualifying_manifest_without_companion_renders_scoped_missing_input(self):
        """ADR-0130 clause 13: a qualifying NESTED XcodeGen
        manifest with NO companion project renders `missing-input` scoped
        to `ios/project.yml`, not silently dropped because it is not at
        the checkout root."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Package.swift").write_text(
                'let package = Package(name: "Lib", products: [], targets: [])\n')
            ios = root / "ios"
            ios.mkdir()
            (ios / "project.yml").write_text(
                "name: App\ntargets:\n  App:\n    type: application\n    platform: iOS\n")
            md, _ = self.swift.extract_module_graph(root, "bionic")
        self.assertIn("`missing-input` `ios/project.yml` lines — — XcodeGen", md)


    def test_generator_check_reads_only_the_bytes_the_scan_hashed(self):
        """ADR-0129 clause 2 / ADR-0130 clause 2: every read counts against
        the per-concern caps and is hashed into `sources`. The XcodeGen check
        therefore interprets the `project.yml` bytes `_scan` read, never a
        second read of its own: a manifest the scan did not read (capped or
        refused) renders nothing, so no unhashed input moves the spine."""
        import tempfile
        from unittest import mock
        manifest = b"name: App\ntargets:\n  App:\n    type: application\n    platform: iOS\n"
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "project.yml").write_bytes(manifest)
            generators = self.swift.swift_generators
            with mock.patch.object(generators, "_safe_read_bytes",
                                   side_effect=AssertionError("second read of project.yml")):
                unread = self.swift._generator_residuals(root, self.swift.ProjectReads())
                read = self.swift._generator_residuals(
                    root, self.swift.ProjectReads(files={"project.yml": manifest}))
        self.assertEqual(unread, ())
        self.assertEqual([r[0] for r in read], ["missing-input"])

class StdlibOnlyReaderImportTests(unittest.TestCase):
    """ADR-0130 clause 17: a stdlib-only import check over the five
    Xcode-reader modules (`swift_pbxproj.py`, `swift_xcode.py`,
    `swift_xcinputs.py`, `swift_xcode_products.py` and `swift_prune.py`, the
    prune rule they all import), with a planted-import positive control
    proving the AST walk actually flags an offender."""

    _MODULES = (
        "swift_pbxproj.py", "swift_xcode.py", "swift_xcinputs.py", "swift_xcode_products.py",
        "swift_prune.py",
    )

    def _offenders(self, source: str) -> list:
        import ast
        tree = ast.parse(source)
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module.split(".")[0]] if node.module else []
            else:
                continue
            for name in names:
                if name in sys.stdlib_module_names or name == "__future__":
                    continue
                offenders.append(name)
        return offenders

    def test_top_level_imports_are_stdlib_or_crux_own(self):
        pack_dir = SCRIPTS / "crux" / "arch" / "packs"
        checked = []
        for name in self._MODULES:
            path = pack_dir / name
            checked.append(name)
            offenders = self._offenders(path.read_text(encoding="utf-8"))
            with self.subTest(module=name):
                self.assertEqual(offenders, [], f"non-stdlib top-level imports in {name}: {offenders}")
        self.assertEqual(len(checked), len(self._MODULES))

    def test_planted_third_party_import_is_flagged(self):
        offenders = self._offenders("import httpx\n")
        self.assertEqual(offenders, ["httpx"])


class PackageContainerIdentityTests(unittest.TestCase):
    """ADR-0129 clause 5 names a container by its `Package.swift` path, and
    ADR-0130 clause 7 draws a resolved package-product dependency as a graph
    edge into that container. Every graph node that names a package container
    must carry the id the Containers table lists, or one package renders as
    two nodes and the distinct-edge count double-counts (ADR-0129 clause 6)."""

    _PBXPROJ = (
        "// !$*UTF8*$!\n{\n\tarchiveVersion = 1;\n\tobjectVersion = 56;\n"
        "\trootObject = PRJ;\n\tobjects = {\n"
        "\t\tPRJ = {\n\t\t\tisa = PBXProject;\n\t\t\tmainGroup = MG;\n"
        "\t\t\ttargets = (\n\t\t\t\tT_UNLINKED,\n\t\t\t\tT_LOCAL,\n\t\t\t);\n"
        "\t\t\tpackageReferences = (\n\t\t\t\tLOCALREF,\n\t\t\t);\n\t\t};\n"
        "\t\tMG = {\n\t\t\tisa = PBXGroup;\n\t\t\tsourceTree = \"<group>\";\n"
        "\t\t\tchildren = (\n\t\t\t\tSYNCED,\n\t\t\t);\n\t\t};\n"
        "\t\tSYNCED = {\n\t\t\tisa = PBXFileSystemSynchronizedRootGroup;\n"
        "\t\t\tpath = Modules;\n\t\t\tsourceTree = \"<group>\";\n"
        "\t\t\texplicitFolders = (\n\t\t\t);\n\t\t};\n"
        "\t\tT_UNLINKED = {\n\t\t\tisa = PBXNativeTarget;\n\t\t\tname = AppUnlinked;\n"
        "\t\t\tproductType = \"com.apple.product-type.application\";\n"
        "\t\t\tbuildPhases = (\n\t\t\t);\n\t\t\tdependencies = (\n\t\t\t);\n"
        "\t\t\tpackageProductDependencies = (\n\t\t\t\tPD_FOO,\n\t\t\t);\n\t\t};\n"
        "\t\tPD_FOO = {\n\t\t\tisa = XCSwiftPackageProductDependency;\n"
        "\t\t\tproductName = Foo;\n\t\t};\n"
        "\t\tT_LOCAL = {\n\t\t\tisa = PBXNativeTarget;\n\t\t\tname = AppLocal;\n"
        "\t\t\tproductType = \"com.apple.product-type.application\";\n"
        "\t\t\tbuildPhases = (\n\t\t\t);\n\t\t\tdependencies = (\n\t\t\t);\n"
        "\t\t\tpackageProductDependencies = (\n\t\t\t\tPD_LOC,\n\t\t\t);\n\t\t};\n"
        "\t\tPD_LOC = {\n\t\t\tisa = XCSwiftPackageProductDependency;\n"
        "\t\t\tpackage = LOCALREF;\n\t\t\tproductName = Loc;\n\t\t};\n"
        "\t\tLOCALREF = {\n\t\t\tisa = XCLocalSwiftPackageReference;\n"
        "\t\t\trelativePath = \"Vendor/Local\";\n\t\t};\n"
        "\t};\n}\n"
    )

    def _render(self):
        import tempfile
        swift = _fresh_swift()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "App.xcodeproj").mkdir()
            (root / "App.xcodeproj" / "project.pbxproj").write_text(self._PBXPROJ)
            unique = root / "Modules" / "Unique"
            unique.mkdir(parents=True)
            (unique / "Package.swift").write_text(
                'let package = Package(\n'
                '    name: "Unique",\n'
                '    products: [.library(name: "Foo", targets: ["Foo"])],\n'
                '    targets: [.target(name: "Foo")]\n'
                ')\n')
            local = root / "Vendor" / "Local"
            local.mkdir(parents=True)
            (local / "Package.swift").write_text(
                'let package = Package(\n'
                '    name: "Local",\n'
                '    products: [.library(name: "Loc", targets: ["Loc"])],\n'
                '    dependencies: [.package(url: "https://example.invalid/dep.git", from: "1.0.0")],\n'
                '    targets: [.target(name: "Loc")]\n'
                ')\n')
            md, _ = swift.extract_module_graph(root, "bionic")
        return md

    @staticmethod
    def _container_of(label: str) -> str:
        _name, container = label.rsplit(" (", 1)
        return container[:-1]

    def test_every_package_edge_endpoint_names_a_listed_container(self):
        md = self._render()
        containers = {_unquote(r["container"]) for r in _section_rows(md, "Containers")}
        self.assertIn("Modules/Unique/Package.swift", containers)
        self.assertIn("Vendor/Local/Package.swift", containers)
        edges = _edges(md)
        self.assertIn(("AppUnlinked (App.xcodeproj)", "Foo (Modules/Unique/Package.swift)"), edges)
        self.assertIn(("AppLocal (App.xcodeproj)", "Loc (Vendor/Local/Package.swift)"), edges)
        endpoints = {self._container_of(label) for edge in edges for label in edge}
        self.assertEqual(endpoints - containers, set())

    def test_every_dependencies_from_cell_names_a_listed_container_directory(self):
        # The Dependencies `from` cell names the declaring package by its
        # directory, the form the pinned corpus facts use for a path or remote
        # package dependency (`Modules/Account -> local package ../X`). It is a
        # table cell, not a graph node, so it draws no second node; it must
        # still be the directory of a container the Containers table lists.
        md = self._render()
        containers = {_unquote(r["container"]) for r in _section_rows(md, "Containers")}
        directories = {c.rsplit("/", 1)[0] if "/" in c else "." for c in containers
                       if c.endswith("Package.swift")}
        targets = {_unquote(r["target"]) for r in _section_rows(md, "Targets")}
        rows = _section_rows(md, "Dependencies")
        package_rows = [r for r in rows if "example.invalid/dep" in r["location"]]
        self.assertEqual(len(package_rows), 1, rows)
        self.assertEqual(_unquote(package_rows[0]["from"]), "Vendor/Local")
        for r in rows:
            frm = _unquote(r["from"])
            with self.subTest(frm=frm):
                self.assertIn(frm, directories | targets | {"project"})


# ═══════════ the per-concern output bound and collection bounds ═══════════
# ADR-0129 clauses 2 and 7: one output bound per concern file, in the
# existing `scan-cap` class, plus collection-time bounds so memory does not
# grow with a product of inputs either. Every hostile shape below is a
# reduced copy of an earlier reproduction; the tracemalloc ceiling each test
# states is below every figure those reproductions reached (5 GB, 400 MB,
# 101 MB, 100 MB, 1.65 GB).

_O4_UNQUOTED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_$+/:.-")
_O4_APP = "com.apple.product-type.application"
_O4_CAP = 1_835_008
_O4_FILE_BOUND = 2 * 1024 * 1024
#: The tracemalloc peak every module-graph amplifier test stays under. The
#: unfixed code peaks at 30-102 MB on these shapes; the fixed code at 10-17 MB.
_O4_PEAK_CEILING = 24 * 1024 * 1024


def _o4_key(k):
    return k if k and all(c in _O4_UNQUOTED for c in k) else '"' + k.replace('"', '\\"') + '"'


def _o4_serialize(value, indent=0):
    pad = "\t" * indent
    if isinstance(value, dict):
        out = ["{"]
        for k in sorted(value):
            v = value[k]
            if isinstance(v, (dict, list)):
                out.append(pad + "\t" + _o4_key(k) + " = " + _o4_serialize(v, indent + 1).lstrip() + ";")
            else:
                out.append(pad + "\t" + _o4_key(k) + ' = "' + str(v).replace('"', '\\"') + '";')
        out.append(pad + "}")
        return "\n".join(out)
    out = ["("]
    for v in value:
        out.append(pad + "\t" + '"' + str(v).replace('"', '\\"') + '",')
    out.append(pad + ")")
    return "\n".join(out)


def _o4_obj(isa, **kw):
    d = {"isa": isa}
    d.update(kw)
    return d


def _o4_write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _o4_pbx(root: Path, objects: dict) -> None:
    doc = {"archiveVersion": "1", "objectVersion": "56", "rootObject": "PROJ", "objects": objects}
    _o4_write(root, "X.xcodeproj/project.pbxproj", "// !$*UTF8*$!\n" + _o4_serialize(doc) + "\n")


def _o4_owners(root: Path, targets=10, name_len=2000, imports=1000, mains=0):
    """One file owned by `targets` long-named targets through classic Sources
    phases, with `imports` imports and `mains` `@main` types: the owners cell
    repeats on every import and `@main` row."""
    o = {"PROJ": _o4_obj("PBXProject", mainGroup="MAIN", targets=[f"T{i}" for i in range(targets)]),
         "MAIN": _o4_obj("PBXGroup", sourceTree="<group>", children=["G"]),
         "G": _o4_obj("PBXGroup", sourceTree="<group>", path="Src", children=["F"]),
         "F": _o4_obj("PBXFileReference", sourceTree="<group>", path="Main.swift")}
    for i in range(targets):
        o[f"B{i}"] = _o4_obj("PBXBuildFile", fileRef="F")
        o[f"S{i}"] = _o4_obj("PBXSourcesBuildPhase", files=[f"B{i}"])
        o[f"T{i}"] = _o4_obj("PBXNativeTarget", name=f"{i:04d}" + "N" * name_len, productType=_O4_APP,
                             buildPhases=[f"S{i}"])
    _o4_pbx(root, o)
    _o4_write(root, "Src/Main.swift",
              "".join(f"import M{i}\n" for i in range(imports))
              + "".join(f"@main struct A{i} {{ static func main() {{}} }}\n" for i in range(mains)))


def _o4_package_deps(root: Path, name_len=20000, deps=500):
    """A `Package.swift` target whose long name repeats in one residual per
    unresolved dependency."""
    items = ", ".join(f'"p{i}"' for i in range(deps))
    _o4_write(root, "Package.swift",
              'let package = Package(name: "P", targets: [\n'
              f'    .target(name: "{"Q" * name_len}", dependencies: [{items}]),\n])\n')


def _o4_product_deps(root: Path, name_len=20000, deps=500):
    """A long-named target whose `packageProductDependencies` name dangling ids."""
    _o4_pbx(root, {"PROJ": _o4_obj("PBXProject", mainGroup="MAIN", targets=["T"]),
                   "MAIN": _o4_obj("PBXGroup", sourceTree="<group>", children=[]),
                   "T": _o4_obj("PBXNativeTarget", name="R" * name_len, productType=_O4_APP,
                                packageProductDependencies=[f"MISSING{i}" for i in range(deps)])})


def _o4_target_deps(root: Path, name_len=20000, deps=500):
    """A long-named target whose `dependencies` name objects of another kind."""
    o = {"PROJ": _o4_obj("PBXProject", mainGroup="MAIN", targets=["T"]),
         "MAIN": _o4_obj("PBXGroup", sourceTree="<group>", children=[]),
         "T": _o4_obj("PBXNativeTarget", name="D" * name_len, productType=_O4_APP,
                      dependencies=[f"X{i}" for i in range(deps)])}
    for i in range(deps):
        o[f"X{i}"] = _o4_obj("PBXBuildFile")
    _o4_pbx(root, o)


def _o4_build_files(root: Path, name_len=20000, files=500):
    """A long-named target whose Sources phase names dangling build files."""
    _o4_pbx(root, {"PROJ": _o4_obj("PBXProject", mainGroup="MAIN", targets=["T"]),
                   "MAIN": _o4_obj("PBXGroup", sourceTree="<group>", children=[]),
                   "SP": _o4_obj("PBXSourcesBuildPhase", files=[f"MISSING{i}" for i in range(files)]),
                   "T": _o4_obj("PBXNativeTarget", name="C" * name_len, productType=_O4_APP,
                                buildPhases=["SP"])})


def _o4_synced_entries(root: Path, depth=100, entries=30000):
    """A deep folder-synced root whose path repeats in one residual per
    absolute exception entry."""
    path = "/".join(["d"] * depth)
    _o4_pbx(root, {"PROJ": _o4_obj("PBXProject", mainGroup="MAIN", targets=["T"]),
                   "MAIN": _o4_obj("PBXGroup", sourceTree="<group>", children=["SR"]),
                   "SR": _o4_obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path=path,
                                 exceptions=["E"]),
                   "E": _o4_obj("PBXFileSystemSynchronizedBuildFileExceptionSet", target="T",
                                membershipExceptions=[f"/abs{i}.swift" for i in range(entries)]),
                   "T": _o4_obj("PBXNativeTarget", name="App", productType=_O4_APP,
                                fileSystemSynchronizedGroups=["SR"])})
    (root / path).mkdir(parents=True, exist_ok=True)


def _o4_members(root: Path, name_len=20000, files=500, targets=1):
    """A synced root of `files` empty files owned by `targets` long-named
    targets: one membership row per file per target."""
    o = {"PROJ": _o4_obj("PBXProject", mainGroup="MAIN", targets=[f"T{i}" for i in range(targets)]),
         "MAIN": _o4_obj("PBXGroup", sourceTree="<group>", children=["SR"]),
         "SR": _o4_obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Src")}
    for i in range(targets):
        o[f"T{i}"] = _o4_obj("PBXNativeTarget", name=f"{i:04d}" + "M" * name_len, productType=_O4_APP,
                             fileSystemSynchronizedGroups=["SR"])
    _o4_pbx(root, o)
    for i in range(files):
        _o4_write(root, f"Src/f{i:05d}.swift", "")


def _o4_candidates(root: Path, candidates=100, dir_len=100, deps=1000):
    """`deps` unlinked product dependencies that match nothing, in a project
    reaching `candidates` package directories: each residual lists them all."""
    o = {"PROJ": _o4_obj("PBXProject", mainGroup="MAIN", targets=["T"]),
         "MAIN": _o4_obj("PBXGroup", sourceTree="<group>", children=["PK"]),
         "PK": _o4_obj("PBXGroup", sourceTree="<group>", path="Pkgs", children=[]),
         "T": _o4_obj("PBXNativeTarget", name="App", productType=_O4_APP,
                      packageProductDependencies=[f"PD{i}" for i in range(deps)])}
    for i in range(deps):
        o[f"PD{i}"] = _o4_obj("XCSwiftPackageProductDependency", productName=f"prod{i}")
    _o4_pbx(root, o)
    for c in range(candidates):
        _o4_write(root, f"Pkgs/{c:04d}{'k' * dir_len}/Package.swift",
                  f'let package = Package(name: "K{c}", products: [.library(name: "Lib{c}", '
                  'targets: ["L"])], targets: [.target(name: "L")])\n')


def _o4_edges(root: Path, targets=400):
    """One file owned by `targets` targets that imports every one of them:
    targets squared import edges."""
    o = {"PROJ": _o4_obj("PBXProject", mainGroup="MAIN", targets=[f"T{i}" for i in range(targets)]),
         "MAIN": _o4_obj("PBXGroup", sourceTree="<group>", children=["G"]),
         "G": _o4_obj("PBXGroup", sourceTree="<group>", path="Src", children=["F"]),
         "F": _o4_obj("PBXFileReference", sourceTree="<group>", path="Main.swift")}
    for i in range(targets):
        o[f"B{i}"] = _o4_obj("PBXBuildFile", fileRef="F")
        o[f"S{i}"] = _o4_obj("PBXSourcesBuildPhase", files=[f"B{i}"])
        o[f"T{i}"] = _o4_obj("PBXNativeTarget", name=f"M{i}", productType=_O4_APP, buildPhases=[f"S{i}"])
    _o4_pbx(root, o)
    _o4_write(root, "Src/Main.swift", "".join(f"import M{i}\n" for i in range(targets)))


def _o4_is_output_cap(line: str) -> bool:
    return (line.startswith("- `scan-cap` `.` lines — — the ")
            and " rows pass the per-concern output bound of " in line)


def _o4_charged(markdown: str) -> list:
    """`(section, line)` for every line the output bound charges, in order:
    table rows (not the header or separator), Mermaid edge lines, and
    residual bullets other than the output bound's own line."""
    out = []
    section = None
    table_lines = 0
    for line in markdown.split("\n"):
        if line.startswith("## "):
            section, table_lines = line[3:], 0
            continue
        if line.startswith("|"):
            table_lines += 1
            if table_lines > 2:
                out.append((section, line))
        elif line.startswith("  ") and " --> " in line:
            out.append((section, line))
        elif section == "Residuals" and line.startswith("- `") and not _o4_is_output_cap(line):
            out.append((section, line))
    return out


def _o4_charged_bytes(markdown: str) -> int:
    return sum(len(line.encode("utf-8")) + 1 for _s, line in _o4_charged(markdown))


def _o4_peak(fn):
    """`(result, tracemalloc peak bytes)` of one call."""
    import tracemalloc
    tracemalloc.start()
    try:
        result = fn()
        _cur, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, peak


_O4_EXTRACTORS = ("data-model", "api-surface", "module-graph")


def _o4_derive(swift, root: Path, concern: str) -> str:
    fn = {"data-model": swift.extract_data_model, "api-surface": swift.extract_api_surface,
          "module-graph": swift.extract_module_graph}[concern]
    swift._CACHE.update(root=None, files={}, manifests={})
    return fn(root, "bionic")[0]


class ConcernOutputBoundTests(unittest.TestCase):
    """The per-concern output bound: its size, byte identity under it, and a
    prefix of the same output in file order over it, with one `scan-cap`
    line last, later sections absent, the Mermaid fence closed and the
    summary counting what renders."""

    def setUp(self):
        import tempfile
        self.swift = _fresh_swift()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "case"
        self.root.mkdir()

    def _mixed_tree(self):
        """Rows in every table of every concern, Mermaid edges, and residuals:
        the declaration fixtures, a package with target edges and an
        unresolved product, and the synced-exceptions Xcode fixture."""
        import shutil
        for name in ("01-actor.swift", "02-access-levels.swift", "03-macros.swift", "04-if-os.swift"):
            shutil.copy2(FIXTURES / name, self.root / name)
        xc = Path(__file__).resolve().parent / "fixtures" / "xcodeproj" / "21-synced-app-exceptions"
        for item in xc.iterdir():
            if item.name in ("expected.yml", "bionic"):
                continue
            if item.is_dir():
                shutil.copytree(item, self.root / item.name)
            else:
                shutil.copy2(item, self.root / item.name)
        _o4_write(self.root, "Package.swift",
                  'let package = Package(name: "P", products: [.library(name: "Core", targets: ["Core"])], '
                  'targets: [\n    .target(name: "Core"),\n'
                  '    .target(name: "App", dependencies: ["Core", "Missing"]),\n'
                  '    .target(name: "Tool", dependencies: ["Core", "App"]),\n])\n')
        _o4_write(self.root, "Sources/Core/Core.swift", "import Foundation\npublic struct Core {}\n")
        _o4_write(self.root, "Sources/App/App.swift", "import Core\n@main struct AppMain { static func main() {} }\n")
        _o4_write(self.root, "Sources/Tool/Tool.swift", "import Core\nimport App\nfunc f() { x(]\n}\n")

    def _derive_under(self, concern: str, limit: int) -> str:
        from unittest import mock
        with mock.patch.object(self.swift, "_MAX_CONCERN_BYTES", limit):
            return _o4_derive(self.swift, self.root, concern)

    def test_the_bound_is_the_core_read_bound_less_256_kib(self):
        core = _core()
        self.assertEqual(self.swift._MAX_CONCERN_BYTES, core._MAX_FILE_BYTES - 256 * 1024)
        self.assertEqual(self.swift._MAX_CONCERN_BYTES, _O4_CAP)

    def test_control_output_under_the_bound_is_byte_identical(self):
        self._mixed_tree()
        for concern in _O4_EXTRACTORS:
            with self.subTest(concern=concern):
                normal = _o4_derive(self.swift, self.root, concern)
                unbounded = self._derive_under(concern, 10 ** 12)
                self.assertEqual(normal, unbounded)
                self.assertFalse(any(_o4_is_output_cap(line) for line in normal.split("\n")))

    def _check_prefix(self, concern: str, full: str, capped: str, limit: int) -> None:
        full_rows = _o4_charged(full)
        rows = _o4_charged(capped)
        self.assertEqual(rows, full_rows[:len(rows)])
        self.assertLessEqual(_o4_charged_bytes(capped), limit)
        tripped = _o4_charged_bytes(full) > limit
        caps = [line for line in capped.split("\n") if _o4_is_output_cap(line)]
        self.assertEqual(len(caps), 1 if tripped else 0)
        if not tripped:
            self.assertEqual(capped, full)
            return
        self.assertLess(len(rows), len(full_rows))
        lines = capped.rstrip("\n").split("\n")
        self.assertEqual(lines[-1], caps[0], "the bound line renders last")
        self.assertEqual(capped.count("```") % 2, 0, "the Mermaid fence closes")
        headings = [line for line in lines if line.startswith("## ")]
        full_headings = [line for line in full.split("\n") if line.startswith("## ")]
        self.assertEqual(headings[-1], "## Residuals")
        body_headings = headings[:-1]
        # The trip lands on the first row that did not render. Every section
        # before it renders whole (an empty one as `_None._`); the section it
        # lands in keeps its heading only when some of its rows rendered; no
        # section after it renders anything.
        trip_section = full_rows[len(rows)][0]
        full_body = [h for h in full_headings if h != "## Residuals"]
        if trip_section == "Residuals":
            self.assertEqual(body_headings, full_body)
        else:
            at = full_body.index("## " + trip_section)
            partial = any(r[0] == trip_section for r in rows)
            self.assertEqual(body_headings, full_body[:at + (1 if partial else 0)])
            if partial:
                tail = capped.split("## " + trip_section, 1)[1].split("## Residuals", 1)[0]
                self.assertNotIn("_None._", tail)
        if concern == "data-model":
            n = len([r for r in rows if r[0] == "Types"])
            self.assertIn(f"_{n} Swift model types", capped)
        if concern == "module-graph":
            n_edges = len([r for r in rows if r[0] == "Graph"])
            self.assertIn(f" {n_edges} in-tree dependency edges", capped)

    def test_over_the_bound_each_concern_renders_a_prefix_in_file_order(self):
        self._mixed_tree()
        for concern in _O4_EXTRACTORS:
            full = _o4_derive(self.swift, self.root, concern)
            total = 0
            limits = {0, 1}
            for _section, line in _o4_charged(full):
                total += len(line.encode("utf-8")) + 1
                limits.update({total - 1, total, total + 1})
            self.assertGreater(len(_o4_charged(full)), 5, concern)
            for limit in sorted(limits):
                with self.subTest(concern=concern, limit=limit):
                    self._check_prefix(concern, full, self._derive_under(concern, limit), limit)

    def test_a_trip_inside_the_mermaid_fence_closes_the_fence(self):
        self._mixed_tree()
        full = _o4_derive(self.swift, self.root, "module-graph")
        rows = _o4_charged(full)
        edges = [i for i, (s, _l) in enumerate(rows) if s == "Graph"]
        self.assertGreaterEqual(len(edges), 2)
        limit = sum(len(line.encode("utf-8")) + 1 for _s, line in rows[:edges[0] + 1])
        capped = self._derive_under("module-graph", limit)
        graph = capped.split("## Graph", 1)[1].split("## ", 1)[0]
        self.assertEqual(graph.count("```"), 2)
        self.assertEqual(graph.count(" --> "), 1)
        self.assertNotIn("## Dependencies", capped)
        self.assertIn(" 1 in-tree dependency edges", capped)

    def test_sections_after_the_trip_render_nothing(self):
        self._mixed_tree()
        for concern in _O4_EXTRACTORS:
            with self.subTest(concern=concern):
                capped = self._derive_under(concern, 0)
                headings = [line for line in capped.split("\n") if line.startswith("## ")]
                self.assertEqual(headings, ["## Residuals"])
                self.assertNotIn("_None._", capped)
                self.assertNotIn("```", capped)
                self.assertEqual(_o4_charged(capped), [])

    def test_the_bound_line_is_fixed_text(self):
        self._mixed_tree()
        capped = self._derive_under("data-model", 100)
        self.assertIn("- `scan-cap` `.` lines — — the data-model rows pass the per-concern output "
                      "bound of 100 bytes; later rows do not render", capped)
        normal_bound = ("the module-graph rows pass the per-concern output bound of 1835008 bytes; "
                        "later rows do not render")
        self.assertEqual(self.swift._OUTPUT_CAP_TEMPLATE.format(concern="module-graph", limit=_O4_CAP),
                         normal_bound)

    def test_residual_bullets_count_against_the_bound(self):
        # Residuals alone: a file of stray errors and nothing else.
        _o4_write(self.root, "E.swift", "func f() {\n" + "x(]\n" * 200 + "}\n")
        full = _o4_derive(self.swift, self.root, "data-model")
        bullets = [r for r in _o4_charged(full) if r[0] == "Residuals"]
        self.assertEqual(len(bullets), 200)
        limit = sum(len(line.encode("utf-8")) + 1 for _s, line in bullets[:50])
        capped = self._derive_under("data-model", limit)
        self.assertEqual(len([r for r in _o4_charged(capped) if r[0] == "Residuals"]), 50)
        self.assertEqual(sum(1 for line in capped.split("\n") if _o4_is_output_cap(line)), 1)

    def test_path_cells_count_against_the_bound(self):
        # The path dominates every row: charging the row without its path
        # would render several times the rows this bound allows.
        deep = "/".join(["p" * 50] * 8)
        _o4_write(self.root, f"{deep}/T.swift", "".join(f"struct S{i} {{}}\n" for i in range(200)))
        full = _o4_derive(self.swift, self.root, "data-model")
        rows = [r for r in _o4_charged(full) if r[0] == "Types"]
        self.assertEqual(len(rows), 200)
        limit = sum(len(line.encode("utf-8")) + 1 for _s, line in rows[:20])
        capped = self._derive_under("data-model", limit)
        self.assertEqual(len([r for r in _o4_charged(capped) if r[0] == "Types"]), 20)
        self.assertLessEqual(_o4_charged_bytes(capped), limit)

    def test_two_derives_over_the_bound_are_byte_identical(self):
        self._mixed_tree()
        for concern in _O4_EXTRACTORS:
            with self.subTest(concern=concern):
                self.assertEqual(self._derive_under(concern, 700), self._derive_under(concern, 700))


#: Each concern's summary once its output bound has
#: tripped, as fixed text with its counts, and today's summary untripped.
_A9_TRIPPED = {
    "module-graph": re.compile(
        r"_\d+ containers, \d+ targets, \d+ in-tree dependency edges and the Swift imports "
        r"rendered before the output bound, read from the literal manifest subset and the "
        r"pinned Swift grammar; no manifest was evaluated and no dependency resolved\._"),
    "data-model": re.compile(
        r"_\d+ Swift model types \(struct, enum, class, actor\) with the stored properties and "
        r"declared relationships rendered before the output bound, read through the pinned "
        r"Swift grammar; nothing was compiled or executed\._"),
    "api-surface": re.compile(
        r"_\d+ interfaces \(public, package or open declarations, and protocols at any access "
        r"level\), \d+ protocol requirements, \d+ package products and \d+ `@main` declarations "
        r"rendered before the output bound, read through the pinned Swift grammar; nothing was "
        r"compiled or executed\._"),
}
_A9_UNTRIPPED = {
    "module-graph": re.compile(
        r"_\d+ containers, \d+ targets, \d+ in-tree dependency edges and every Swift import, "
        r"read from the literal manifest subset and the pinned Swift grammar; no manifest was "
        r"evaluated and no dependency resolved\._"),
    "data-model": re.compile(
        r"_\d+ Swift model types \(struct, enum, class, actor\) with their stored properties and "
        r"declared relationships, read through the pinned Swift grammar; nothing was compiled "
        r"or executed\._"),
    "api-surface": re.compile(
        r"_\d+ interfaces \(public, package or open declarations, and every protocol\), \d+ "
        r"protocol requirements, \d+ package products and \d+ `@main` declarations, read "
        r"through the pinned Swift grammar; nothing was compiled or executed\._"),
}


class OutputBudgetMeterTests(unittest.TestCase):
    """ADR-0129 clause 2: the output meter is total. A lone surrogate that
    reached a line is counted at its `surrogatepass` width, never raised on;
    the decoders are what keep one out of the spine."""

    def test_a_lone_surrogate_is_counted_not_raised(self):
        budget = _fresh_swift()._OutputBudget("module-graph")
        self.assertTrue(budget.take("a\ud800b"))
        self.assertEqual(budget.spent, len("a\ud800b".encode("utf-8", "surrogatepass")) + 1)
        self.assertEqual(budget.spent, 6)

    def test_ascii_and_scalar_lines_are_counted_as_before(self):
        budget = _fresh_swift()._OutputBudget("module-graph")
        self.assertTrue(budget.take("abc"))
        self.assertTrue(budget.take("\u00e9\U0001F600"))
        self.assertEqual(budget.spent, 4 + 7)


class TrippedSummaryWordingTests(unittest.TestCase):
    """A concern whose output bound tripped renders the
    fixed summary variant, which counts the rows rendered before the bound
    and claims no "every"; an untripped concern renders today's summary."""

    setUp = ConcernOutputBoundTests.setUp
    _mixed_tree = ConcernOutputBoundTests._mixed_tree
    _derive_under = ConcernOutputBoundTests._derive_under

    @staticmethod
    def _summary(markdown: str) -> str:
        lines = markdown.split("\n")
        return lines[2]

    def test_a_tripped_concern_renders_the_variant(self):
        self._mixed_tree()
        for concern in _O4_EXTRACTORS:
            full = _o4_derive(self.swift, self.root, concern)
            half = _o4_charged_bytes(full) // 2
            for limit in (0, 100, half):
                with self.subTest(concern=concern, limit=limit):
                    capped = self._derive_under(concern, limit)
                    self.assertTrue(any(_o4_is_output_cap(line) for line in capped.split("\n")),
                                    "the bound must trip for this check to mean anything")
                    self.assertRegex(self._summary(capped), "^" + _A9_TRIPPED[concern].pattern + "$")

    def test_an_untripped_concern_renders_todays_summary(self):
        self._mixed_tree()
        for concern in _O4_EXTRACTORS:
            with self.subTest(concern=concern):
                normal = _o4_derive(self.swift, self.root, concern)
                self.assertFalse(any(_o4_is_output_cap(line) for line in normal.split("\n")))
                self.assertRegex(self._summary(normal), "^" + _A9_UNTRIPPED[concern].pattern + "$")

    def test_no_tripped_summary_carries_every(self):
        self._mixed_tree()
        for concern in _O4_EXTRACTORS:
            full = _o4_derive(self.swift, self.root, concern)
            total, limits = 0, {0}
            for _section, line in _o4_charged(full):
                total += len(line.encode("utf-8")) + 1
                limits.add(total - 1)
            for limit in sorted(limits):
                with self.subTest(concern=concern, limit=limit):
                    capped = self._derive_under(concern, limit)
                    self.assertTrue(any(_o4_is_output_cap(line) for line in capped.split("\n")))
                    self.assertNotIn("every", self._summary(capped))
        # Control: the same check reads today's untripped summary, which
        # does carry "every" in two of the three concerns.
        self.assertIn("every", self._summary(_o4_derive(self.swift, self.root, "module-graph")))
        self.assertIn("every", self._summary(_o4_derive(self.swift, self.root, "api-surface")))


class OutputAmplifierBoundTests(unittest.TestCase):
    """Each earlier output amplifier, reduced: the output per concern stays
    under the bound (charged lines under `_MAX_CONCERN_BYTES`, the whole
    file under
    the core's 2 MiB read bound) and the derive's tracemalloc peak stays
    under `_O4_PEAK_CEILING`. Production bounds throughout; nothing is
    patched."""

    def setUp(self):
        import tempfile
        self.swift = _fresh_swift()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "case"
        self.root.mkdir()

    def _bounded(self, concern: str, ceiling: int = _O4_PEAK_CEILING) -> str:
        md, peak = _o4_peak(lambda: _o4_derive(self.swift, self.root, concern))
        with self.subTest(concern=concern, bound="charged bytes"):
            self.assertLessEqual(_o4_charged_bytes(md), _O4_CAP)
        with self.subTest(concern=concern, bound="file bytes"):
            self.assertLessEqual(len(md.encode("utf-8")), _O4_FILE_BOUND)
        with self.subTest(concern=concern, bound="tracemalloc peak"):
            self.assertLess(peak, ceiling, f"{concern} tracemalloc peak {peak}")
        return md

    def _caps(self, md: str) -> list:
        return sorted(b[3] for b in _residual_bullets(md) if b[0] == "scan-cap")

    def test_owners_cell_on_every_import_and_main_row(self):
        # 2,000 rows of a 20 KB owners cell: 40 MB if the rows were built
        # before the bound reads them, so the peak also proves they are not.
        _o4_owners(self.root, targets=10, name_len=2000, imports=2000, mains=2000)
        for concern in ("module-graph", "api-surface"):
            with self.subTest(concern=concern):
                md = self._bounded(concern)
                self.assertIn("the %s rows pass the per-concern output bound of 1835008 bytes; "
                              "later rows do not render" % concern, self._caps(md))

    def test_package_target_name_per_dependency(self):
        _o4_package_deps(self.root)
        md = self._bounded("module-graph")
        # Declared cause of this pin's move: the template said "later
        # residuals are not recorded", but a residual with a fixed detail is
        # still recorded past the bound; only the details that repeat a name
        # are refused. The class and the location are unchanged.
        self.assertIn(("scan-cap", "Package.swift", "2-2",
                       "the residual details pass the per-concern collection bound of 1835008 bytes; "
                       "later residual details that repeat a name are not recorded"),
                      _residual_bullets(md))

    def test_xcode_target_name_per_product_dependency(self):
        _o4_product_deps(self.root)
        md = self._bounded("module-graph")
        self.assertTrue(any(c.startswith("the residual details pass the per-concern collection bound")
                            for c in self._caps(md)))
        self._bounded("api-surface", 8 * 1024 * 1024)

    def test_xcode_target_name_per_target_dependency(self):
        _o4_target_deps(self.root)
        md = self._bounded("module-graph")
        self.assertTrue(any(c.startswith("the residual details pass the per-concern collection bound")
                            for c in self._caps(md)))
        self._bounded("api-surface", 8 * 1024 * 1024)

    def test_xcode_target_name_per_build_file(self):
        _o4_build_files(self.root)
        md = self._bounded("module-graph")
        self.assertTrue(any(c.startswith("the residual details pass the per-concern collection bound")
                            for c in self._caps(md)))
        self._bounded("api-surface", 8 * 1024 * 1024)

    def test_synced_root_path_per_exception_entry(self):
        _o4_synced_entries(self.root)
        self._bounded("module-graph")

    def test_membership_rows_repeat_the_target_name(self):
        _o4_members(self.root)
        md = self._bounded("module-graph")
        self.assertIn("the module-graph rows pass the per-concern output bound of 1835008 bytes; "
                      "later rows do not render", self._caps(md))

    def test_candidate_list_per_unlinked_product(self):
        _o4_candidates(self.root)
        md = self._bounded("module-graph")
        self.assertTrue(any(c.startswith("the residual details pass the per-concern collection bound")
                            for c in self._caps(md)))
        self._bounded("api-surface", 12 * 1024 * 1024)

    def test_import_edges_square_of_the_targets(self):
        # Timed on `_timing.clock`, the calling thread's CPU time: the derive
        # runs in this thread, and time spent waiting for a core on a loaded
        # host is not charged to it.
        _o4_edges(self.root, targets=400)
        start = _timing.clock()
        md = self._bounded("module-graph")
        elapsed = _timing.clock() - start
        self.assertLess(elapsed, 10.0,
                        f"400 targets importing each other took {elapsed:.1f} s of thread CPU time")
        self.assertIn(" --> ", md)


class ParseErrorDetailBoundTests(unittest.TestCase):
    """The `parse-error` details count against the per-file bound (8 times
    the file's size plus 64 KiB): each repeats its enclosing declaration's
    label, so a long name over many stray errors is a product."""

    def setUp(self):
        self.swift = _fresh_swift()

    def test_a_long_label_over_many_errors_stops_at_the_per_file_bound(self):
        src = ("func " + "F" * 3000 + "() {\n" + "x(]\n" * 3000 + "}\n").encode()
        self.swift._parse_file("W.swift", b"struct W {}\n")  # the parser loads outside the measurement
        facts, peak = _o4_peak(lambda: self.swift._parse_file("X.swift", src))
        errors = [r for r in facts.residuals if r[0] == "parse-error"]
        caps = [r for r in facts.residuals if r[0] == "scan-cap"]
        budget = 8 * len(src) + 64 * 1024
        with self.subTest(bound="tracemalloc peak"):
            self.assertLess(peak, 6 * 1024 * 1024)
        self.assertLessEqual(sum(len(r[2]) for r in errors), budget)
        self.assertGreater(len(errors), 10)
        stop = errors[-1][1][0][0] + 1
        self.assertEqual(caps, [("scan-cap", [(stop, stop)],
                                 "the parse-error lines pass the per-file bound of 8 times the file's "
                                 "size plus 64 KiB; later parse errors do not render")])

    def test_control_a_few_errors_render_every_line_and_no_scan_cap(self):
        src = ("func f() {\n" + "x(]\n" * 3 + "}\n").encode()
        facts = self.swift._parse_file("X.swift", src)
        self.assertEqual(len([r for r in facts.residuals if r[0] == "parse-error"]), 3)
        self.assertEqual([r for r in facts.residuals if r[0] == "scan-cap"], [])


class CollectionBoundConstantTests(unittest.TestCase):
    """`swift_xcinputs.MAX_DETAIL_BYTES` and `swift._MAX_CONCERN_BYTES` are
    written twice, because `swift_xcinputs` cannot import `swift`. The
    collection bound on held residual detail text is the concern's output
    bound, so the two must stay equal."""

    def test_the_detail_bound_equals_the_output_bound(self):
        swift = _fresh_swift()
        self.assertEqual(swift.swift_xcinputs.MAX_DETAIL_BYTES, swift._MAX_CONCERN_BYTES)
        self.assertEqual(swift._MAX_CONCERN_BYTES, 2 * 1024 * 1024 - 256 * 1024)


class MembershipBoundTests(unittest.TestCase):
    """The Xcode membership records one concern keeps are bounded
    (`swift_xcinputs.MAX_MEMBERSHIPS`): a synced root yields one record per
    file per owning target. Past the bound one read-level `scan-cap` line
    renders in both concerns that read memberships."""

    def setUp(self):
        import tempfile
        self.swift = _fresh_swift()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "case"
        self.root.mkdir()

    def _facts(self):
        analysis = self.swift._analyse(self.root, "module-graph", with_manifests=True)
        return self.swift._project_facts(self.root, analysis.manifests, analysis.project_reads)

    def test_records_past_the_bound_are_not_kept_and_one_line_says_so(self):
        _o4_members(self.root, name_len=1, files=300, targets=200)
        facts = self._facts()
        self.assertEqual(len(facts.memberships), 50_000)
        self.assertEqual(self.swift.swift_xcinputs.MAX_MEMBERSHIPS, 50_000)
        caps = [r for r in facts.residuals if r[0] == "scan-cap"]
        self.assertEqual(len(caps), 1)
        self.assertEqual((caps[0][1], caps[0][3]),
                         ("X.xcodeproj/project.pbxproj",
                          "the Xcode membership records pass the per-concern bound of 50000; "
                          "later memberships are not read"))

    def test_control_a_small_root_keeps_every_record(self):
        _o4_members(self.root, name_len=1, files=3, targets=2)
        facts = self._facts()
        self.assertEqual(len(facts.memberships), 6)
        self.assertEqual([r for r in facts.residuals if r[0] == "scan-cap"], [])


class DecodeVerdictUnderOutputBoundTests(unittest.TestCase):
    """ADR-0129 clause 7's decode verdict is the same whether or not the
    output bound drops the `parse-error` lines it reads."""

    def setUp(self):
        import tempfile
        self.swift = _fresh_swift()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "case"
        self.root.mkdir()

    def _verdict(self, limit: int, fail_all: bool):
        from unittest import mock
        real_parse = self.swift._parse
        calls = {"n": 0}

        def parse(raw):
            calls["n"] += 1
            if fail_all or b"Decoded" not in raw:
                raise ValueError("x")
            return real_parse(raw)

        with mock.patch.object(self.swift, "_parse", side_effect=parse), \
                mock.patch.object(self.swift, "_MAX_CONCERN_BYTES", limit):
            self.swift._CACHE.update(root=None, files={}, manifests={})
            md, sources = self.swift.extract_data_model(self.root, "bionic")
        return md, self.swift.concern_decode_verdict("data-model", md, sources)

    def test_all_inputs_failed_the_verdict_survives_a_bound_that_drops_their_lines(self):
        for i in range(40):
            _o4_write(self.root, f"F{i:02d}.swift", "struct A {}\n")
        _o4_write(self.root, "Big.swift", "x" * (3 * 1024 * 1024))  # oversize: undecoded, not in sources
        full_md, full = self._verdict(10 ** 12, fail_all=True)
        capped_md, capped = self._verdict(400, fail_all=True)
        self.assertEqual(len([b for b in _residual_bullets(full_md) if b[0] in ("parse-error", "oversize")]), 41)
        self.assertLess(len([b for b in _residual_bullets(capped_md) if b[0] == "parse-error"]), 5)
        self.assertIsNotNone(full)
        self.assertIsNotNone(capped)
        self.assertEqual((capped.kind, capped.reason, capped.expected, capped.found),
                         (full.kind, full.reason, full.expected, full.found))
        self.assertEqual(full.found, "41 declared input(s) present and none decoded")
        self.assertIn("later rows do not render; 41 declared input(s) present and none decoded", capped_md)

    def test_control_one_decoded_input_keeps_no_verdict_and_the_plain_line(self):
        for i in range(40):
            _o4_write(self.root, f"F{i:02d}.swift", "struct A {}\n")
        _o4_write(self.root, "Z.swift", "struct Decoded {}\n")
        full_md, full = self._verdict(10 ** 12, fail_all=False)
        capped_md, capped = self._verdict(400, fail_all=False)
        self.assertIsNone(full)
        self.assertIsNone(capped)
        self.assertIn("later rows do not render\n", capped_md)
        self.assertNotIn("none decoded", capped_md)


class BoundedEdgeSetTests(unittest.TestCase):
    """The import-edge set keeps only the `_MAX_GRAPH_EDGES` smallest edges,
    and what renders equals the full set sorted then sliced, with the trip
    exact (ADR-0129 clause 7: the edge-cap line states the bound)."""

    def setUp(self):
        self.swift = _fresh_swift()

    def test_randomized_equal_to_sort_then_slice(self):
        import random
        from unittest import mock
        rng = random.Random(20260925)
        for trial in range(3000):
            limit = rng.randint(1, 12)
            with mock.patch.object(self.swift, "_MAX_GRAPH_EDGES", limit):
                edges = self.swift._BoundedEdges()
                full = set()
                for _ in range(rng.randint(0, 4)):
                    for _ in range(rng.randint(0, 5)):
                        e = (rng.choice("abcde"), rng.choice("abcde"))
                        edges.add(e)
                        full.add(e)
                    owners = sorted({(rng.choice("xyz"), rng.choice(["c", "a", "a::x"]))
                                     for _ in range(rng.randint(1, 4))})
                    targets = {(rng.choice("xyz"), rng.choice(["c", "a", "a::x"]))
                               for _ in range(rng.randint(1, 4))}
                    self.swift._add_import_edges(edges, [(f"{o[1]}::{o[0]}", o) for o in owners],
                                                 [(f"{t[1]}::{t[0]}", t) for t in targets])
                    full.update((f"{o[1]}::{o[0]}", f"{t[1]}::{t[0]}")
                                for o in owners for t in targets if o != t)
            with self.subTest(trial=trial):
                self.assertEqual(edges.held, sorted(full)[:limit])
                self.assertEqual(edges.over, len(full) > limit)
                # The memory pin: the membership set holds exactly the held
                # edges, so it never grows past the edge bound. An evicted
                # edge that stayed in it would be memory the bound does not
                # meter, and the render above could not see it.
                self.assertEqual(len(edges.members), len(edges.held))
                self.assertEqual(edges.members, set(edges.held))

    def test_import_edge_work_is_bounded_by_the_edge_bound(self):
        # 300 owners by 300 imported targets: 89,700 edges. Adding stops at
        # the first edge past a full set, so the work is the bound plus the
        # owners, never their product.
        from unittest import mock
        owners = [(f"c::o{i:03d}", (f"o{i:03d}", "c")) for i in range(300)]
        targets = [(f"c::t{i:03d}", (f"t{i:03d}", "c")) for i in range(300)]
        with mock.patch.object(self.swift, "_MAX_GRAPH_EDGES", 100):
            edges = self.swift._BoundedEdges()
            calls = []
            real_add = edges.add
            edges.add = lambda edge: (calls.append(edge), real_add(edge))
            self.swift._add_import_edges(edges, owners, targets)
        self.assertEqual(edges.held, sorted((a, b) for a, _o in owners for b, _t in targets)[:100])
        self.assertTrue(edges.over)
        # The first owner's first 100 edges fill the set; its 101st is past
        # it, and so is the next owner's first: 100 calls in all.
        self.assertEqual(len(calls), 100)

    def test_the_edge_line_states_the_bound_not_the_total(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _o4_edges(root, targets=30)
            with mock.patch.object(self.swift, "_MAX_GRAPH_EDGES", 50):
                md = _o4_derive(self.swift, root, "module-graph")
        self.assertEqual(len(_edges(md)), 50)
        self.assertIn(("scan-cap", ".", None, "the module graph holds more than 50 edges; 50 render"),
                      _residual_bullets(md))


class HostileTreeDerivePostconditionTests(_SwiftTree):
    """ADR-0129 clause 2, and output the drift gate can compare, through
    the registered derive path: a
    hostile tree derives with exit 0, every spine file stays under the
    core's 2 MiB read bound, a second derive is byte-identical, and
    `--dry-run` then reports no drift."""

    def test_an_owners_amplifier_derives_clean_and_compares_clean(self):
        _o4_owners(self.root, targets=10, name_len=2000, imports=1000, mains=1000)
        self.assertEqual(self.run_cli()[0], 0)
        arch = self.root / "bionic" / "arch"
        first = {p.relative_to(arch).as_posix(): p.read_bytes() for p in arch.rglob("*") if p.is_file()}
        for rel in ("data-model.md", "api-surface.md", "module-graph.md"):
            self.assertLessEqual(len(first[rel]), _O4_FILE_BOUND, rel)
        self.swift._CACHE.update(root=None, files={}, manifests={})
        self.assertEqual(self.run_cli()[0], 0)
        second = {p.relative_to(arch).as_posix(): p.read_bytes() for p in arch.rglob("*") if p.is_file()}
        self.assertEqual(first, second)
        self.swift._CACHE.update(root=None, files={}, manifests={})
        code, payload, _ = self.run_cli("--dry-run")
        self.assertEqual((code, payload["drift"]), (0, []))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
