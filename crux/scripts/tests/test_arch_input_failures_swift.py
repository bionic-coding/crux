"""ADR-0181 in the Swift pack — absent, unreadable, unparseable and unlistable inputs.

`SwiftPackLaneTests` holds the cases the core's shared reader and walk give
every pack. The classes below hold the Swift pack's own sites: the
`*.xcodeproj` bundle census and its listing, the `project.pbxproj`,
workspace, `.xcconfig` and XcodeGen reads, the Swift reader's own `scandir`
listings (`swift_xcinputs._listing`, `_listed_names_live`,
`swift_xcode._sorted_entries`), the generator listing, the strict decode of
each Swift source and manifest, the per-file boundaries and their
`MemoryError` lane, the aggregate scan cap, the whole-input residual lines
that become omissions keeping their kind. The broad-handler rule covers
every pack module from `test_arch_input_failures_core.py`.

Each case derives a fixture through `derive-arch.py` and asserts the lane: an
omission named in the map and in `coverage.json` with exit 0, a document
finding with exit 1, or an environment failure with exit 2. Every refusing
case asserts the byte-unchanged arch tree, and the clean derive of the same
fixture in `setUp` is the positive control.
"""

from __future__ import annotations

import errno
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from arch_input_failures_support import (
    CORE,
    PackLaneCases,
    active_ledger,
    arch_snapshot,
    coverage,
    run_cli,
    skip_if_root,
    write,
)

SWIFT = __import__("crux.arch.packs.swift", fromlist=["extract_module_graph"])
XCODE = __import__("crux.arch.packs.swift_xcode", fromlist=["read_projects"])
XCINPUTS = __import__("crux.arch.packs.swift_xcinputs", fromlist=["read_workspace"])
PBXPROJ = __import__("crux.arch.packs.swift_pbxproj", fromlist=["read_pbxproj"])
GENERATORS = __import__("crux.arch.packs.swift_generators", fromlist=["check_xcodegen"])
PRODUCTS = __import__("crux.arch.packs.swift_xcode_products", fromlist=["resolve_product_dependencies"])

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "xcodeproj"
#: An Xcode project, a standalone workspace and a local package: every
#: Swift concern populates and no input is omitted.
PROJECT = FIXTURES / "76-hostile-workspace-well-formed-project-and-package"
#: An Xcode project beside two `.xcconfig` inputs.
XCCONFIG = FIXTURES / "41-limitation-build-settings"
#: A qualifying XcodeGen `project.yml` with its companion `App.xcodeproj`.
XCODEGEN = FIXTURES / "60-clause16-with-project"

PBX = "App.xcodeproj/project.pbxproj"
WORKSPACE = "App.xcworkspace/contents.xcworkspacedata"
SOURCE = "Sources/Lib/Lib.swift"
CONCERNS = ("data-model", "api-surface", "module-graph")


class SwiftPackLaneTests(PackLaneCases, unittest.TestCase):
    SOURCE = "Sources/Core/Widget.swift"
    SUBDIR = "Sources/Core"

    def build(self, root: Path) -> None:
        write(root, "Package.swift",
              '// swift-tools-version:5.9\nimport PackageDescription\n\n'
              'let package = Package(\n    name: "Core",\n'
              '    products: [.library(name: "Core", targets: ["Core"])],\n'
              '    targets: [.target(name: "Core")]\n)\n')
        write(root, "Sources/Core/Widget.swift", "public struct Widget {\n    public let id: Int\n}\n")


def _copy(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    (dst / "expected.yml").unlink(missing_ok=True)
    return dst


class _Repo(unittest.TestCase):
    FIXTURE = PROJECT

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = _copy(self.FIXTURE, Path(self._tmp.name).resolve() / "case")
        SWIFT._CACHE.update(root=None, files={}, manifests={})
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
        SWIFT._CACHE.update(root=None, files={}, manifests={})
        self._tmp.cleanup()

    def fresh(self) -> None:
        """Drop the per-derive parse cache, so a patched parser runs."""
        SWIFT._CACHE.update(root=None, files={}, manifests={})

    def omissions(self, concern: str) -> list[dict]:
        return coverage(self.root)[concern]["omissions"]

    def spine(self, concern: str) -> str:
        return (self.root / "bionic" / "arch" / f"{concern}.md").read_text()

    def described(self, concern: str) -> str:
        """The spine file without its Omissions section."""
        return self.spine(concern).split("## Omissions")[0]

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

    def assert_not_omitted(self, *concerns: str) -> None:
        for concern in concerns:
            self.assertEqual(self.omissions(concern), [], concern)

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
        for concern in CONCERNS:
            self.assertEqual(cov[concern]["omissions"], [], concern)
        for concern in ("data-model", "api-surface"):
            self.assertEqual(cov[concern]["verdict"], "populated", concern)
        self.assertIn("| `App.xcodeproj` | xcode project |", self.spine("module-graph"))
        self.assertIn(PBX, cov["module-graph"]["inputs_found"])
        self.assertIn(WORKSPACE, cov["module-graph"]["inputs_found"])


class XcodeprojBundleTests(_Repo):
    """The `*.xcodeproj` bundle census (`swift._bundle_member`): ADR-0181
    approaches 3 and 7, and the ADR-0130 clause 1 `missing-input` line."""

    #: A bundle below the core's stack-detection depth, so only the Swift
    #: census lists it.
    DEEP = "x/y/z/Other.xcodeproj"

    def deep_bundle(self) -> Path:
        bundle = self.root / self.DEEP
        bundle.mkdir(parents=True)
        shutil.copy2(self.root / PBX, bundle / "project.pbxproj")
        return bundle

    def test_positive_control_a_listable_deep_bundle_is_read(self):
        self.deep_bundle()
        self.derive_ok()
        self.assertIn(f"{self.DEEP}/project.pbxproj", coverage(self.root)["module-graph"]["inputs_found"])
        self.assert_not_omitted(*CONCERNS)

    def test_an_unlistable_bundle_is_an_environment_failure_not_missing_input(self):
        skip_if_root(self)
        os.chmod(self.deep_bundle(), 0o300)      # searchable, not listable
        self.assert_refused(2, self.DEEP)

    def test_a_bundle_without_a_pbxproj_is_named_absent_and_not_as_a_residual(self):
        (self.root / PBX).unlink()
        self.assert_omitted("App.xcodeproj", "absent", "missing-input", "module-graph")
        self.assertNotIn("`missing-input` `App.xcodeproj`", self.spine("module-graph"))

    def test_a_symbolic_link_bundle_is_named_not_a_file(self):
        (self.root / "App.xcodeproj").rename(self.root / "elsewhere")
        os.symlink("elsewhere", self.root / "App.xcodeproj")
        self.assert_omitted("App.xcodeproj", "not-a-file", "symbolic-link",
                            "api-surface", "module-graph")
        # The data model reads no project input, so it names none.
        self.assert_not_omitted("data-model")

    def test_a_symbolic_link_pbxproj_is_named_not_a_file_and_not_as_a_residual(self):
        pbx = self.root / PBX
        pbx.rename(self.root / "App.xcodeproj" / "real.pbxproj")
        os.symlink("real.pbxproj", pbx)
        self.assert_omitted(PBX, "not-a-file", "symbolic-link", "api-surface", "module-graph")
        self.assertNotIn("`project-unreadable`", self.spine("module-graph"))

    def test_a_directory_at_the_pbxproj_is_named_not_a_file(self):
        (self.root / PBX).unlink()
        (self.root / PBX).mkdir()
        self.assert_omitted(PBX, "not-a-file", "directory", "api-surface", "module-graph")

    def test_a_mode_000_pbxproj_is_a_document_finding(self):
        skip_if_root(self)
        os.chmod(self.root / PBX, 0)
        self.assert_refused(1, PBX)

    def test_a_fifo_pbxproj_is_an_environment_failure(self):
        (self.root / PBX).unlink()
        os.mkfifo(self.root / PBX)
        self.assert_refused(2, PBX)

    def test_an_oversize_pbxproj_is_named_over_cap_and_not_as_a_residual(self):
        with mock.patch.object(SWIFT, "_MAX_PBXPROJ_BYTES", 64):
            self.assert_omitted(PBX, "over-cap", "oversize", "api-surface", "module-graph")
        self.assertNotIn("`oversize`", self.spine("module-graph"))

    def test_an_undecodable_pbxproj_is_named_and_still_hashed(self):
        with (self.root / PBX).open("ab") as f:
            f.write(b"/* \xff */\n")
        self.assert_omitted(PBX, "undecodable", "undecodable", "api-surface", "module-graph")
        self.assertNotIn("`project-unreadable`", self.spine("module-graph"))
        self.assertIn(PBX, coverage(self.root)["module-graph"]["inputs_found"])

    def test_a_malformed_pbxproj_is_named_unparseable_keeping_its_kind(self):
        write(self.root, PBX, "// !$*UTF8*$!\n{ <<<<<<< HEAD\n")
        self.assert_omitted(PBX, "unparseable", "malformed", "api-surface", "module-graph")
        self.assertNotIn("`project-unreadable`", self.spine("module-graph"))


class SourceTests(_Repo):
    """The strict decode of each Swift source and manifest, and the
    location-less `parse failed` line (ADR-0181 approaches 5 and 6)."""

    def test_an_undecodable_source_is_named_and_still_hashed(self):
        write(self.root, "Sources/Lib/Bad.swift", b"public struct Ba\xffd {}\n")
        self.assert_omitted("Sources/Lib/Bad.swift", "undecodable", "undecodable", *CONCERNS)
        self.assertIn("Sources/Lib/Bad.swift", coverage(self.root)["data-model"]["inputs_found"])
        self.assertNotIn("�", self.spine("data-model"))

    def test_an_undecodable_manifest_is_named(self):
        with (self.root / "Package.swift").open("ab") as f:
            f.write(b"// \xff\n")
        self.assert_omitted("Package.swift", "undecodable", "undecodable", "api-surface", "module-graph")

    def test_a_source_with_no_parse_tree_is_named_unparseable_and_not_as_a_residual(self):
        real = SWIFT._parse

        def parse(raw):
            if b"struct Lib" in raw:
                raise RecursionError("deep")
            return real(raw)

        self.fresh()
        with mock.patch.object(SWIFT, "_parse", parse):
            self.assert_omitted(SOURCE, "unparseable", "unparseable", *CONCERNS)
        self.assertNotIn("step parse failed", self.spine("data-model"))

    def test_a_located_parse_error_stays_a_residual(self):
        write(self.root, "Sources/Lib/Broken.swift", "public struct Broken {\n    let x: = 1\n}\n")
        self.derive_ok()
        self.assertIn("- `parse-error` `Sources/Lib/Broken.swift` lines ", self.spine("data-model"))
        self.assertNotIn("Sources/Lib/Broken.swift", [r.get("path") for r in self.omissions("data-model")])


class MemoryErrorTests(_Repo):
    """ADR-0181 point 3 and ADR-0130 clause 2: a `MemoryError` at every Swift
    per-file boundary is the environment failure naming the file."""

    def assert_memory_lane(self, name: str, target, attr: str) -> None:
        self.fresh()
        with mock.patch.object(target, attr, side_effect=MemoryError()):
            code, out, _payload, err = run_cli(self.root)
        self.assertEqual((code, out), (2, ""), err)
        self.assertIn(name, err)
        self.assertIn("MemoryError", err)
        self.assertEqual(arch_snapshot(self.root), self.before)

    def test_while_parsing_a_source(self):
        real = SWIFT._parse

        def parse(raw):
            if b"struct Lib" in raw:
                raise MemoryError()
            return real(raw)

        self.fresh()
        with mock.patch.object(SWIFT, "_parse", parse):
            code, out, _payload, err = run_cli(self.root)
        self.assertEqual((code, out), (2, ""), err)
        self.assertIn(SOURCE, err)
        self.assertEqual(arch_snapshot(self.root), self.before)

    def test_while_reading_a_manifest(self):
        self.assert_memory_lane("Package.swift", SWIFT._ManifestReader, "read")

    def test_while_parsing_the_pbxproj(self):
        self.assert_memory_lane(PBX, PBXPROJ, "_tokenize")

    def test_while_resolving_target_dependencies(self):
        self.assert_memory_lane(PBX, XCODE, "target_dependencies")

    def test_while_resolving_package_products(self):
        self.assert_memory_lane(PBX, PRODUCTS, "_resolve_project_dir")

    def test_while_reading_the_workspace(self):
        self.assert_memory_lane(WORKSPACE, XCINPUTS, "_parse_workspace_xml")

    def test_positive_control_a_content_failure_in_the_pbxproj_is_named_malformed(self):
        with mock.patch.object(PBXPROJ, "_tokenize", side_effect=RecursionError()):
            self.assert_omitted(PBX, "unparseable", "malformed", "module-graph")

    def test_without_a_ledger_the_boundary_re_raises(self):
        with mock.patch.object(PBXPROJ, "_tokenize", side_effect=MemoryError()):
            with self.assertRaises(MemoryError):
                SWIFT.extract_module_graph(self.root, "bionic")


class WorkspaceTests(_Repo):
    """The workspace boundary: content kinds are omissions, an OS error takes
    its lane by cause (ADR-0181 approach 3)."""

    def test_an_entity_declaration_is_named_unparseable_keeping_its_kind(self):
        write(self.root, WORKSPACE, '<?xml version="1.0"?>\n<!DOCTYPE w [<!ENTITY a "b">]>\n'
                                    '<Workspace version = "1.0"></Workspace>\n')
        self.assert_omitted(WORKSPACE, "unparseable", "entity-declaration", "module-graph")
        self.assertNotIn("`project-unreadable`", self.spine("module-graph"))

    def test_a_permission_failure_inside_the_reader_is_a_document_finding(self):
        err = PermissionError(errno.EACCES, "Permission denied")
        with mock.patch.object(XCINPUTS, "read_workspace", side_effect=err):
            self.assert_refused(1, WORKSPACE)

    def test_another_os_error_inside_the_reader_is_an_environment_failure(self):
        err = OSError(errno.EIO, "Input/output error")
        with mock.patch.object(XCINPUTS, "read_workspace", side_effect=err):
            self.assert_refused(2, WORKSPACE)

    def test_without_a_ledger_an_os_error_renders_read_failed(self):
        err = OSError(errno.EIO, "Input/output error")
        with mock.patch.object(XCINPUTS, "read_workspace", side_effect=err):
            content, _ = SWIFT.extract_module_graph(self.root, "bionic")
        self.assertIn(f"- `project-unreadable` `{WORKSPACE}` lines — — read-failed", content)


class XcconfigTests(_Repo):
    FIXTURE = XCCONFIG

    def test_positive_control_no_omission(self):
        self.assert_not_omitted(*CONCERNS)

    def test_an_undecodable_xcconfig_is_named_and_not_as_a_residual(self):
        with (self.root / "Shared.xcconfig").open("ab") as f:
            f.write(b"OTHER = a\xffb\n")
        self.assert_omitted("Shared.xcconfig", "undecodable", "undecodable", "module-graph")
        self.assertNotIn("`project-unreadable`", self.spine("module-graph"))

    def test_an_oversize_xcconfig_is_named_over_cap(self):
        write(self.root, "Big.xcconfig", "// " + "x" * (2 * 1024 * 1024) + "\n")
        self.assert_omitted("Big.xcconfig", "over-cap", "oversize", "module-graph")
        self.assertNotIn("`oversize`", self.spine("module-graph"))


class GeneratorTests(_Repo):
    """The XcodeGen check: its `missing-input` line, its listing and its
    per-file boundary (`swift_generators`)."""

    FIXTURE = XCODEGEN

    def test_positive_control_a_companion_project_names_nothing(self):
        self.assert_not_omitted(*CONCERNS)

    def test_a_manifest_without_its_project_is_named_absent_missing_input(self):
        shutil.rmtree(self.root / "App.xcodeproj")
        self.assert_omitted("project.yml", "absent", "missing-input", "module-graph")
        self.assertNotIn("`missing-input`", self.spine("module-graph"))

    def test_a_memory_error_in_the_shape_check_is_an_environment_failure(self):
        with mock.patch.object(GENERATORS, "_scan_events_safe", side_effect=MemoryError()):
            code, out, _payload, err = run_cli(self.root)
        self.assertEqual((code, out), (2, ""), err)
        self.assertIn("project.yml", err)
        self.assertEqual(arch_snapshot(self.root), self.before)

    def test_an_unlistable_candidate_directory_is_an_environment_failure(self):
        skip_if_root(self)
        (self.root / "ios").mkdir()
        os.chmod(self.root / "ios", 0o300)
        with active_ledger(self.root, "module-graph"):
            with self.assertRaises(CORE.ArchEnvironmentFailure) as caught:
                GENERATORS._has_companion_project(self.root, "ios")
        self.assertIn("ios", caught.exception.failures[0])

    def test_outside_a_derive_an_unlistable_candidate_directory_has_no_project(self):
        skip_if_root(self)
        (self.root / "ios").mkdir()
        os.chmod(self.root / "ios", 0o300)
        self.assertFalse(GENERATORS._has_companion_project(self.root, "ios"))
        self.assertTrue(GENERATORS._has_companion_project(self.root, ""))


class ReaderListingTests(unittest.TestCase):
    """The Swift reader's own `scandir` sites (ADR-0181 approach 7): an
    unlistable directory is the environment failure naming it under a
    ledger, absence stays absence, and with no ledger each keeps its answer."""

    def setUp(self):
        skip_if_root(self)
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        (self.root / "Sources" / "App").mkdir(parents=True)
        write(self.root, "Sources/App/Main.swift", "struct Main {}\n")
        os.chmod(self.root / "Sources", 0o300)

    def tearDown(self):
        os.chmod(self.root / "Sources", 0o755)
        self._tmp.cleanup()

    def calls(self):
        return {
            "_listing": lambda: XCINPUTS.directory_entries(self.root, ("Sources",)),
            "_listed_names_live": lambda: XCINPUTS.listed_names(self.root, ("Sources", "App")),
            "_sorted_entries": lambda: XCODE._sorted_entries(self.root / "Sources"),
        }

    def test_an_unlistable_directory_is_an_environment_failure(self):
        for site, call in self.calls().items():
            with self.subTest(site=site), active_ledger(self.root, "module-graph"):
                with self.assertRaises(CORE.ArchEnvironmentFailure) as caught:
                    call()
                self.assertIn("Sources", caught.exception.failures[0])

    def test_without_a_ledger_each_site_answers_as_before(self):
        answers = {site: call() for site, call in self.calls().items()}
        self.assertEqual(len(answers["_listing"]), 0)
        self.assertFalse(answers["_listed_names_live"])
        self.assertEqual(answers["_sorted_entries"], [])

    def test_positive_control_a_listable_directory_lists_under_a_ledger(self):
        os.chmod(self.root / "Sources", 0o755)
        with active_ledger(self.root, "module-graph") as ledger:
            self.assertIn("App", XCINPUTS.directory_entries(self.root, ("Sources",)))
            self.assertTrue(XCINPUTS.listed_names(self.root, ("Sources", "App")))
            self.assertEqual([e.name for e in XCODE._sorted_entries(self.root / "Sources")], ["App"])
        self.assertEqual(ledger.findings, [])

    def test_an_absent_directory_stays_absent_under_a_ledger(self):
        with active_ledger(self.root, "module-graph"):
            self.assertEqual(len(XCINPUTS.directory_entries(self.root, ("Missing",))), 0)
            self.assertFalse(XCINPUTS.listed_names(self.root, ("Missing", "App")))
            self.assertEqual(XCODE._sorted_entries(self.root / "Missing"), [])


class ScanCapTests(_Repo):
    """The aggregate scan cap (`swift._scan`) is a counted over-cap omission
    over the sorted candidates (ADR-0181 approach 8)."""

    def test_the_cap_names_the_skipped_count_and_drops_the_residual_line(self):
        with mock.patch.object(SWIFT, "_MAX_SCAN_FILES", 1):
            self.derive_ok()
        caps = [r for r in self.omissions("data-model") if "cap" in r]
        # Sorted candidates: `Modules/Pkg/Sources/Pkg/Pkg.swift` is read, and
        # `Sources/Lib/Lib.swift` is skipped.
        self.assertEqual(caps, [{"cap": "_MAX_SCAN_FILES", "dir": ".", "skipped": 1,
                                 "reason": "over-cap", "kind": "scan-cap"}])
        self.assertIn("- scan cap `_MAX_SCAN_FILES` under `.` skipped 1 input(s)",
                      self.spine("data-model"))
        self.assertNotIn("aggregate file or byte cap", self.spine("data-model"))

    def test_positive_control_without_a_ledger_the_residual_line_renders(self):
        with mock.patch.object(SWIFT, "_MAX_SCAN_FILES", 1):
            content, _ = SWIFT.extract_data_model(self.root, "bionic")
        self.assertIn("aggregate file or byte cap", content)


class LedgerParityTests(unittest.TestCase):
    """The direct-extractor fixture with no omission, run once more under an
    active ledger and concern: the same content and an empty ledger."""

    EXTRACTORS = (("data-model", "extract_data_model"),
                  ("api-surface", "extract_api_surface"),
                  ("module-graph", "extract_module_graph"))

    def test_each_extractor_matches_under_an_active_ledger(self):
        for fixture in (PROJECT, XCCONFIG, XCODEGEN):
            for concern, name in self.EXTRACTORS:
                with self.subTest(fixture=fixture.name, extractor=name), \
                        tempfile.TemporaryDirectory() as d:
                    root = _copy(fixture, Path(d).resolve() / "case")
                    fn = getattr(SWIFT, name)
                    SWIFT._CACHE.update(root=None, files={}, manifests={})
                    direct = fn(root, "bionic")
                    SWIFT._CACHE.update(root=None, files={}, manifests={})
                    with active_ledger(root, concern) as ledger:
                        under = fn(root, "bionic")
                    self.assertEqual(under, direct)
                    self.assertEqual(ledger.omissions(concern), [])
                    self.assertEqual(ledger.findings, [])

    def test_positive_control_the_wrapper_records_a_content_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = _copy(PROJECT, Path(d).resolve() / "case")
            write(root, "Sources/Lib/Bad.swift", b"\xff\n")
            with active_ledger(root, "data-model") as ledger:
                SWIFT.extract_data_model(root, "bionic")
            self.assertEqual([r["path"] for r in ledger.omissions("data-model")],
                             ["Sources/Lib/Bad.swift"])


class DirectCallTests(unittest.TestCase):
    """With no active ledger the pack answers as before."""

    def test_an_oversize_pbxproj_keeps_its_residual_line_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = _copy(PROJECT, Path(d).resolve() / "case")
            with mock.patch.object(SWIFT, "_MAX_PBXPROJ_BYTES", 64):
                content, _ = SWIFT.extract_module_graph(root, "bionic")
            self.assertIn(f"- `oversize` `{PBX}` lines —", content)
            self.assertNotIn("Omissions", content)

    def test_an_undecodable_source_is_described_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = _copy(PROJECT, Path(d).resolve() / "case")
            write(root, "Sources/Lib/Legacy.swift", b"// \xff\npublic struct Legacy {}\n")
            content, sources = SWIFT.extract_data_model(root, "bionic")
            self.assertIn("`Legacy`", content)
            self.assertIn("Sources/Lib/Legacy.swift", sources)

    def test_the_markers_answer_as_the_predicates_with_or_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = _copy(PROJECT, Path(d).resolve() / "case")
            direct = SWIFT.detect(root)
            with active_ledger(root, None) as ledger:
                under = SWIFT.detect(root)
            self.assertEqual(under, direct)
            self.assertEqual(direct.markers, ("App.xcodeproj", "App.xcworkspace", "Package.swift"))
            self.assertEqual(ledger.findings, [])



if __name__ == "__main__":
    unittest.main()
