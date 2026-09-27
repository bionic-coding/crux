"""Unit tests for crux.arch.packs.swift_xcode (ADR-0130 clauses 2, 3, 5, 6,
8, 9, 10 and 12). Every fixture is written fresh
as an in-memory OpenStep document via _pbx() below, never copied from any
checkout.
"""

import builtins
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _timing  # noqa: E402

from crux.arch.packs import swift_pbxproj as spx
from crux.arch.packs import swift_xcode as sx

OPEN_BRACE = chr(123)
CLOSE_BRACE = chr(125)
OPEN_PAREN = "("
CLOSE_PAREN = ")"


_UNQUOTED_KEY_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_$+/:.-"
)


def _serialize_key(k):
    """OpenStep keys outside the parser's unquoted-token charset -- a
    bracketed build-setting condition such as `KEY[sdk=iphoneos*]` chief
    among them -- must be quoted, exactly as Xcode itself quotes them."""
    if k and all(ch in _UNQUOTED_KEY_CHARS for ch in k):
        return k
    return '"' + k.replace('"', '\\"') + '"'


def _serialize(value, indent=0):
    pad = "\t" * indent
    if isinstance(value, dict):
        lines = [OPEN_BRACE]
        for k in sorted(value.keys()):
            v = value[k]
            key_text = _serialize_key(k)
            if isinstance(v, (dict, list)):
                inner = _serialize(v, indent + 1).lstrip()
                lines.append(pad + "\t" + key_text + " = " + inner + ";")
            else:
                sval = str(v).replace('"', '\\"')
                lines.append(pad + "\t" + key_text + ' = "' + sval + '";')
        lines.append(pad + CLOSE_BRACE)
        return "\n".join(lines)
    if isinstance(value, list):
        lines = [OPEN_PAREN]
        for item in value:
            if isinstance(item, (dict, list)):
                inner = _serialize(item, indent + 1).lstrip()
                lines.append(pad + "\t" + inner + ",")
            else:
                sval = str(item).replace('"', '\\"')
                lines.append(pad + "\t" + '"' + sval + '",')
        lines.append(pad + CLOSE_PAREN)
        return "\n".join(lines)
    sval = str(value).replace('"', '\\"')
    return '"' + sval + '"'


def _pbx(objects, root_id, object_version="56"):
    doc = {}
    doc["archiveVersion"] = "1"
    doc["objectVersion"] = object_version
    doc["rootObject"] = root_id
    doc["objects"] = objects
    text = "// !$*UTF8*$!\n" + _serialize(doc) + "\n"
    result = spx.read_pbxproj(text.encode("utf-8"))
    assert isinstance(result, spx.PbxprojDocument), result
    return result


def _obj(isa, **kwargs):
    d = dict(isa=isa)
    d.update(kwargs)
    return d


class DescendTests(unittest.TestCase):
    def test_nested_group_paths_and_source_root(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SUB", "SRFILE"])
        objects["SUB"] = _obj("PBXGroup", sourceTree="<group>", path="Sub", children=["LEAF"])
        objects["LEAF"] = _obj("PBXFileReference", sourceTree="<group>", path="Leaf.swift")
        objects["SRFILE"] = _obj("PBXFileReference", sourceTree="SOURCE_ROOT", path="Root.swift")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        self.assertEqual(d.group_dirs["SUB"], ("Sub",))
        self.assertEqual(d.file_segments["LEAF"], ("Sub", "Leaf.swift"))
        self.assertEqual(d.file_segments["SRFILE"], ("Root.swift",))

    def test_name_only_group_adds_no_segment(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["NG"])
        objects["NG"] = _obj("PBXGroup", sourceTree="<group>", name="Recovered", children=["F"])
        objects["F"] = _obj("PBXFileReference", sourceTree="<group>", path="X.swift")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        self.assertEqual(d.file_segments["F"], ("X.swift",))

    def test_absolute_and_escaping_path_escape(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ABS", "ESC"])
        objects["ABS"] = _obj("PBXFileReference", sourceTree="<absolute>", path="/etc/hosts")
        objects["ESC"] = _obj("PBXFileReference", sourceTree="<group>", path="../../etc/hosts")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        self.assertIn("ABS", d.escape_ids)
        self.assertIn("ESC", d.escape_ids)

    def test_contained_dotdot_is_read(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SUB"])
        objects["SUB"] = _obj("PBXGroup", sourceTree="<group>", path="A/B", children=["F"])
        objects["F"] = _obj("PBXFileReference", sourceTree="<group>", path="../Shared/X.swift")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        self.assertEqual(d.file_segments["F"], ("A", "Shared", "X.swift"))

    def test_built_products_dir_renders_nothing(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["PROD"])
        objects["PROD"] = _obj("PBXFileReference", sourceTree="BUILT_PRODUCTS_DIR", path="App.app")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        self.assertIn("PROD", d.none_ids)
        self.assertNotIn("PROD", d.file_segments)

    def test_dangling_id_and_cycle_unresolved(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["MISSING", "SUB"])
        objects["SUB"] = _obj("PBXGroup", sourceTree="<group>", path="Sub", children=["MAIN"])
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        self.assertIn("MISSING", d.unresolved_ids)
        self.assertIn("MAIN", d.unresolved_ids)

    def test_diamond_visited_once(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["A", "B"])
        objects["A"] = _obj("PBXGroup", sourceTree="<group>", path="A", children=["SHARED"])
        objects["B"] = _obj("PBXGroup", sourceTree="<group>", path="B", children=["SHARED"])
        objects["SHARED"] = _obj("PBXGroup", sourceTree="<group>", path="Shared", children=[])
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        self.assertIn("SHARED", d.unresolved_ids)
        self.assertEqual(d.group_dirs.get("SHARED"), ("A", "Shared"))

    def test_sdkroot_and_var_segment_unresolved_var(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SDK", "VARF"])
        objects["SDK"] = _obj("PBXFileReference", sourceTree="SDKROOT", path="usr/lib/libz.dylib")
        objects["VARF"] = _obj("PBXFileReference", sourceTree="<group>", path="$(HOME)/x.swift")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        self.assertIn("SDK", d.unresolved_var_ids)
        self.assertIn("VARF", d.unresolved_var_ids)


    def test_absolute_project_dir_path_escapes(self):
        # ADR-0130 clauses 1, 2 and 3:
        # an absolute projectDirPath renders ONE path-escape for the
        # project itself and descends nothing -- guessing the checkout root
        # as a substitute base for the main group is exactly the guess
        # clause 10 forbids, so a member that would otherwise resolve
        # relative to the (unknown) project directory is never visited.
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", projectDirPath="/Users/x/Elsewhere")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["F"])
        objects["F"] = _obj("PBXFileReference", sourceTree="SOURCE_ROOT", path="X.swift")
        doc = _pbx(objects, "PROJ")
        project_obj = doc.objects[doc.root_id]
        resolved = sx.resolve_project_dir(project_obj, ())
        self.assertIsNone(resolved)
        d = sx.descend(doc, ())
        self.assertIn("PROJ", d.escape_ids)
        self.assertNotIn("F", d.file_segments)
        self.assertNotIn("F", d.escape_ids)
        self.assertEqual(d.group_dirs, {})
        res = sx.escape_residuals(doc, d, "App.xcodeproj/project.pbxproj")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][0], "path-escape")

    def test_traversal_out_of_checkout_path_escapes(self):
        # A projectDirPath-relative SOURCE_ROOT path that walks above the
        # checkout root renders path-escape, never a filesystem read.
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["F"])
        objects["F"] = _obj("PBXFileReference", sourceTree="SOURCE_ROOT", path="../../../etc/passwd")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        self.assertIn("F", d.escape_ids)
        self.assertNotIn("F", d.file_segments)

    def test_nested_project_group_resolves_against_own_directory(self):
        # ADR-0130 clause 3: a project nested at
        # ios/App.xcodeproj resolves an unqualified <group> member against
        # ITS OWN directory, never the checkout root -- a root-level decoy
        # at the same relative path must never match.
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SUB"])
        objects["SUB"] = _obj("PBXGroup", sourceTree="<group>", path="Shared", children=["F"])
        objects["F"] = _obj("PBXFileReference", sourceTree="<group>", path="Foo.swift")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ("ios",))
        self.assertEqual(d.file_segments["F"], ("ios", "Shared", "Foo.swift"))

    def test_contained_project_dir_path_seeds_the_main_group(self):
        # ADR-0130 clause 3: a root-level project with a CONTAINED projectDirPath resolves
        # its main group against that directory, not the checkout root.
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", projectDirPath="src")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SUB"])
        objects["SUB"] = _obj("PBXGroup", sourceTree="<group>", path="App", children=["F"])
        objects["F"] = _obj("PBXFileReference", sourceTree="<group>", path="Main.swift")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        self.assertEqual(d.file_segments["F"], ("src", "App", "Main.swift"))


class EscapeResidualTests(unittest.TestCase):
    """ADR-0130 clause 3 -- every reference
    in `descent.escape_ids` renders one `path-escape` residual naming the
    declaring file and the reference's own line range, with a detail that
    never carries the path as written or its target."""

    def test_absolute_and_traversal_render_path_escape(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ABS", "ESC"])
        objects["ABS"] = _obj("PBXFileReference", sourceTree="<absolute>", path="/etc/hosts")
        objects["ESC"] = _obj("PBXFileReference", sourceTree="<group>", path="../../etc/hosts")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        res = sx.escape_residuals(doc, d, "App.xcodeproj/project.pbxproj")
        self.assertEqual(len(res), 2)
        for klass, path, span, detail in res:
            self.assertEqual(klass, "path-escape")
            self.assertEqual(path, "App.xcodeproj/project.pbxproj")
            self.assertNotIn("/etc/hosts", detail)
            self.assertNotIn("..", detail)

    def test_sdkroot_and_var_segment_render_nothing(self):
        # SDKROOT/DEVELOPER_DIR/custom trees/$(VAR) are unresolved-var, not
        # escape -- they render only in a Sources phase, never here.
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SDK", "VARF"])
        objects["SDK"] = _obj("PBXFileReference", sourceTree="SDKROOT", path="usr/lib/libz.dylib")
        objects["VARF"] = _obj("PBXFileReference", sourceTree="<group>", path="$(HOME)/x.swift")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        res = sx.escape_residuals(doc, d, "App.xcodeproj/project.pbxproj")
        self.assertEqual(res, ())

    def test_built_products_dir_renders_nothing(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["PROD"])
        objects["PROD"] = _obj("PBXFileReference", sourceTree="BUILT_PRODUCTS_DIR", path="App.app")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        res = sx.escape_residuals(doc, d, "App.xcodeproj/project.pbxproj")
        self.assertEqual(res, ())

    def test_no_escapes_yields_empty(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["F"])
        objects["F"] = _obj("PBXFileReference", sourceTree="<group>", path="Model.swift")
        doc = _pbx(objects, "PROJ")
        d = sx.descend(doc, ())
        res = sx.escape_residuals(doc, d, "App.xcodeproj/project.pbxproj")
        self.assertEqual(res, ())


class BuildSettingResidualTests(unittest.TestCase):
    """ADR-0130 clause 12 -- every
    conditioned buildSettings key, and every EXCLUDED/INCLUDED_SOURCE_FILE_
    NAMES key (bracketed or not), renders one `conditional-setting`
    residual naming the key. No setting value ever renders, membership
    never changes, and `baseConfigurationReference` is never opened."""

    def test_conditioned_key_renders_one_line(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=[])
        objects["CFG"] = _obj(
            "XCBuildConfiguration", name="Debug",
            buildSettings={
                "SWIFT_VERSION": "5.0",
                "GCC_PREPROCESSOR_DEFINITIONS[sdk=iphoneos*]": "DEBUG=1",
            })
        doc = _pbx(objects, "PROJ")
        res = sx.build_setting_residuals(doc, "App.xcodeproj/project.pbxproj")
        self.assertEqual(len(res), 1)
        klass, path, span, detail = res[0]
        self.assertEqual(klass, "conditional-setting")
        self.assertEqual(path, "App.xcodeproj/project.pbxproj")
        self.assertIn("GCC_PREPROCESSOR_DEFINITIONS[sdk=iphoneos*]", detail)
        self.assertNotIn("DEBUG=1", detail)

    def test_excluded_source_file_names_renders_line_and_membership_unaffected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "One.swift")
            _mkfile(root / "Excluded.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ONE", "EXCL"])
            objects["ONE"] = _obj("PBXFileReference", sourceTree="<group>", path="One.swift")
            objects["EXCL"] = _obj("PBXFileReference", sourceTree="<group>", path="Excluded.swift")
            objects["BF1"] = _obj("PBXBuildFile", fileRef="ONE")
            objects["BF2"] = _obj("PBXBuildFile", fileRef="EXCL")
            objects["PHASE"] = _obj("PBXSourcesBuildPhase", files=["BF1", "BF2"])
            objects["T"] = _obj(
                "PBXNativeTarget", name="T",
                productType="com.apple.product-type.application",
                buildPhases=["PHASE"])
            objects["CFG"] = _obj(
                "XCBuildConfiguration", name="Debug",
                buildSettings={"EXCLUDED_SOURCE_FILE_NAMES": "Excluded.swift"})
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, mres = sx.classic_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            files = sorted(row["file"] for row in m)
            self.assertEqual(files, ["Excluded.swift", "One.swift"])
            res = sx.build_setting_residuals(doc, "p")
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0][0], "conditional-setting")
            self.assertIn("EXCLUDED_SOURCE_FILE_NAMES", res[0][3])

    def test_no_setting_value_ever_appears_in_any_residual(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=[])
        objects["CFG"] = _obj(
            "XCBuildConfiguration", name="Debug",
            buildSettings={
                "SWIFT_VERSION[sdk=iphoneos*]": "5.9",
                "INCLUDED_SOURCE_FILE_NAMES": "Secret_Sentinel_Value.swift",
            })
        doc = _pbx(objects, "PROJ")
        res = sx.build_setting_residuals(doc, "p")
        self.assertEqual(len(res), 2)
        for _klass, _path, _span, detail in res:
            self.assertNotIn("5.9", detail)
            self.assertNotIn("Secret_Sentinel_Value", detail)

    def test_base_configuration_reference_never_opened(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=[])
        objects["XCC"] = _obj("PBXFileReference", sourceTree="<group>", path="Shared.xcconfig")
        objects["CFG"] = _obj(
            "XCBuildConfiguration", name="Debug",
            baseConfigurationReference="XCC",
            buildSettings={"SWIFT_VERSION": "5.0"})
        doc = _pbx(objects, "PROJ")
        opened = []
        real_open = builtins.open

        def _tracking_open(*args, **kwargs):
            opened.append(args[0] if args else kwargs.get("file"))
            return real_open(*args, **kwargs)

        with mock.patch("builtins.open", _tracking_open):
            res = sx.build_setting_residuals(doc, "p")
        self.assertEqual(res, ())
        self.assertEqual(opened, [])


class TargetRowsTests(unittest.TestCase):
    def test_product_type_map_families(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["APP", "EXT", "TST", "LIB", "TOOL", "UNK"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=[])
        objects["APP"] = _obj("PBXNativeTarget", name="App", productType="com.apple.product-type.application")
        objects["EXT"] = _obj("PBXNativeTarget", name="Ext", productType="com.apple.product-type.app-extension")
        objects["TST"] = _obj("PBXNativeTarget", name="Tests", productType="com.apple.product-type.bundle.unit-test")
        objects["LIB"] = _obj("PBXNativeTarget", name="Lib", productType="com.apple.product-type.framework")
        objects["TOOL"] = _obj("PBXNativeTarget", name="Tool", productType="com.apple.product-type.tool")
        objects["UNK"] = _obj("PBXNativeTarget", name="Weird", productType="com.apple.product-type.watch2-app")
        doc = _pbx(objects, "PROJ")
        rows, by_id, residuals = sx.target_rows(doc, "X.xcodeproj/project.pbxproj", "X.xcodeproj")
        kinds = dict((r["name"], r["kind"]) for r in rows)
        self.assertEqual(kinds["App"], "app")
        self.assertEqual(kinds["Ext"], "extension")
        self.assertEqual(kinds["Tests"], "test")
        self.assertEqual(kinds["Lib"], "library")
        self.assertEqual(kinds["Tool"], "executable")
        self.assertEqual(kinds["Weird"], "unmapped")
        self.assertEqual(len(residuals), 1)
        self.assertEqual(residuals[0][0], "unsupported-project-form")


class TargetDependencyTests(unittest.TestCase):
    def _targets(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["A", "B"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=[])
        objects["A"] = _obj("PBXNativeTarget", name="A", productType="com.apple.product-type.application")
        objects["B"] = _obj("PBXNativeTarget", name="B", productType="com.apple.product-type.app-extension")
        return objects

    def test_direct_and_proxy_forms_identical(self):
        objects = self._targets()
        objects["A"]["dependencies"] = ["DEP1"]
        objects["DEP1"] = _obj("PBXTargetDependency", target="B")
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        edges1, res1 = sx.target_dependencies(doc, "X.xcodeproj", by_id, "p")
        self.assertEqual(res1, ())
        self.assertEqual(edges1[0]["from"], "A")
        self.assertEqual(edges1[0]["to"], "B")

        objects2 = self._targets()
        objects2["A"]["dependencies"] = ["DEP2"]
        objects2["DEP2"] = _obj("PBXTargetDependency", targetProxy="PROXY")
        objects2["PROXY"] = _obj("PBXContainerItemProxy", containerPortal="PROJ", remoteGlobalIDString="B")
        doc2 = _pbx(objects2, "PROJ")
        rows2, by_id2, _ = sx.target_rows(doc2, "p", "X.xcodeproj")
        edges2, res2 = sx.target_dependencies(doc2, "X.xcodeproj", by_id2, "p")
        self.assertEqual(res2, ())
        self.assertEqual(edges2, edges1)

    def test_disagreement_unresolved_reference(self):
        objects = self._targets()
        objects["A"]["dependencies"] = ["DEP"]
        objects["DEP"] = _obj("PBXTargetDependency", target="B", targetProxy="PROXY")
        objects["PROXY"] = _obj("PBXContainerItemProxy", containerPortal="PROJ", remoteGlobalIDString="A")
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        edges, res = sx.target_dependencies(doc, "X.xcodeproj", by_id, "p")
        self.assertEqual(edges, ())
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][0], "unresolved-reference")

    def test_cross_project_proxy_draws_edge_to_contained_native_target(self):
        # ADR-0130 clause 6: "A proxy whose container is another project draws
        # an edge only when that project is a contained container and the ID
        # names a native target in it."
        objects = self._targets()
        objects["A"]["dependencies"] = ["DEP"]
        objects["DEP"] = _obj("PBXTargetDependency", targetProxy="PROXY")
        objects["PROXY"] = _obj(
            "PBXContainerItemProxy", containerPortal="OTHERPROJ", remoteGlobalIDString="OTHERTARGET")
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")

        other_objects = {}
        other_objects["OTHERPROJ"] = _obj("PBXProject", mainGroup="OMAIN", targets=["OTHERTARGET"])
        other_objects["OMAIN"] = _obj("PBXGroup", sourceTree="<group>", children=[])
        other_objects["OTHERTARGET"] = _obj(
            "PBXNativeTarget", name="OtherTarget", productType="com.apple.product-type.framework")
        other_doc = _pbx(other_objects, "OTHERPROJ")
        other_rows, other_by_id, _ = sx.target_rows(other_doc, "q", "Y.xcodeproj")
        other_containers = {
            "OTHERPROJ": {
                "objects": other_doc.objects,
                "container_name": "Y.xcodeproj",
                "targets_by_id": other_by_id,
            }
        }
        edges, res = sx.target_dependencies(
            doc, "X.xcodeproj", by_id, "p", other_containers=other_containers)
        self.assertEqual(res, ())
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["from"], "A")
        self.assertEqual(edges[0]["to"], "OtherTarget")
        # The edge starts in the declaring project and ends in the other one;
        # one shared `container` would put `A` in Y.xcodeproj, a node that
        # does not exist.
        self.assertEqual(edges[0]["container"], "X.xcodeproj")
        self.assertEqual(edges[0]["to_container"], "Y.xcodeproj")

    def test_cross_project_proxy_uncontained_container_unresolved(self):
        objects = self._targets()
        objects["A"]["dependencies"] = ["DEP"]
        objects["DEP"] = _obj("PBXTargetDependency", targetProxy="PROXY")
        objects["PROXY"] = _obj(
            "PBXContainerItemProxy", containerPortal="UNKNOWNPROJ", remoteGlobalIDString="X")
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        edges, res = sx.target_dependencies(doc, "X.xcodeproj", by_id, "p", other_containers={})
        self.assertEqual(edges, ())
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][0], "unresolved-reference")


class SourcesPhaseUnreachedReferenceTests(unittest.TestCase):
    """ADR-0130 clauses 2 and 3: a Sources-phase build file reaches its file
    reference by lookup. When descent never resolved that reference -- it
    sits in no group, or under a `$(VAR)` group whose descendants stay
    unresolved -- the membership is unknown and renders one
    `unresolved-reference`; it never vanishes without a line."""

    def _run(self, objects):
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["T"] = _obj("PBXNativeTarget", name="T",
                            productType="com.apple.product-type.application",
                            buildPhases=["PHASE"])
        objects["PHASE"] = _obj("PBXSourcesBuildPhase", files=["BF1"])
        objects["BF1"] = _obj("PBXBuildFile", fileRef="F1")
        doc = _pbx(objects, "PROJ")
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        with tempfile.TemporaryDirectory() as tmp:
            _mkfile(Path(tmp) / "One.swift")
            return sx.classic_memberships(doc, Path(tmp), d, "p", by_id, "X.xcodeproj")

    def test_reference_in_no_group_renders_unresolved_reference(self):
        objects = {"MAIN": _obj("PBXGroup", sourceTree="<group>", children=[]),
                   "F1": _obj("PBXFileReference", sourceTree="<group>", path="One.swift")}
        m, res = self._run(objects)
        self.assertEqual(m, ())
        self.assertEqual([r[0] for r in res], ["unresolved-reference"])

    def test_child_of_a_variable_group_renders_unresolved_reference(self):
        # ADR-0130 clause 3: `${VAR}` and bare `$VAR` are the same construct
        # as `$(VAR)`. A following `..` would otherwise cancel the segment
        # and resolve `One.swift` at the checkout root, a real file.
        for path in ("$(SRC)", "$(SRC)/..", "${SRC}/..", "$SRC/.."):
            with self.subTest(path=path):
                objects = {"MAIN": _obj("PBXGroup", sourceTree="<group>", children=["G"]),
                           "G": _obj("PBXGroup", sourceTree="<group>", path=path, children=["F1"]),
                           "F1": _obj("PBXFileReference", sourceTree="<group>", path="One.swift")}
                m, res = self._run(objects)
                self.assertEqual(m, ())
                self.assertEqual([r[0] for r in res], ["unresolved-reference"])

    def test_a_variable_then_dotdot_file_path_renders_unresolved_reference(self):
        for path in ("$(SRC)/../One.swift", "${SRC}/../One.swift", "$SRC/../One.swift"):
            with self.subTest(path=path):
                objects = {"MAIN": _obj("PBXGroup", sourceTree="<group>", children=["F1"]),
                           "F1": _obj("PBXFileReference", sourceTree="<group>", path=path)}
                m, res = self._run(objects)
                self.assertEqual(m, ())
                self.assertEqual([r[0] for r in res], ["unresolved-reference"])

    def test_control_a_plain_file_path_resolves_the_real_file(self):
        objects = {"MAIN": _obj("PBXGroup", sourceTree="<group>", children=["F1"]),
                   "F1": _obj("PBXFileReference", sourceTree="<group>", path="Sub/../One.swift")}
        m, res = self._run(objects)
        self.assertEqual([row["file"] for row in m], ["One.swift"])
        self.assertEqual(res, ())

    def test_built_products_reference_control_renders_nothing(self):
        objects = {"MAIN": _obj("PBXGroup", sourceTree="<group>", children=["F1"]),
                   "F1": _obj("PBXFileReference", sourceTree="BUILT_PRODUCTS_DIR", path="One.swift")}
        m, res = self._run(objects)
        self.assertEqual((m, res), ((), ()))


class NonStringReferenceFieldTests(unittest.TestCase):
    """ADR-0130 clauses 2, 3 and 5: the OpenStep grammar admits a list or a
    dictionary where `path` or `sourceTree` holds a string. Such a field
    names no location, so the reference is never resolved. In a Sources
    phase it renders one `unresolved-reference`. It never raises: a raise
    collapses the project to one `malformed` line and drops its target rows.
    Each case changes only the field's type against the string control."""

    def _run(self, group_fields, file_fields):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["G"])
        objects["G"] = _obj("PBXGroup", children=["F1"], **group_fields)
        objects["F1"] = _obj("PBXFileReference", **file_fields)
        objects["T"] = _obj("PBXNativeTarget", name="T",
                            productType="com.apple.product-type.application",
                            buildPhases=["PHASE"])
        objects["PHASE"] = _obj("PBXSourcesBuildPhase", files=["BF1"])
        objects["BF1"] = _obj("PBXBuildFile", fileRef="F1")
        doc = _pbx(objects, "PROJ")
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        with tempfile.TemporaryDirectory() as tmp:
            _mkfile(Path(tmp) / "Dir" / "One.swift")
            m, res = sx.classic_memberships(doc, Path(tmp), d, "p", by_id, "X.xcodeproj")
        return d, m, res

    GROUP = {"sourceTree": "<group>", "path": "Dir"}
    FILE = {"sourceTree": "<group>", "path": "One.swift"}
    DID_NOT_RESOLVE = [("unresolved-reference", "p",
                        "a file reference in 'T's Sources phase did not resolve")]

    def test_string_fields_control_renders_the_row(self):
        _d, m, res = self._run(self.GROUP, self.FILE)
        self.assertEqual([(r["file"], r["target"]) for r in m], [("Dir/One.swift", "T")])
        self.assertEqual(res, ())

    def test_list_valued_file_path_is_unresolved_never_raised(self):
        d, m, res = self._run(self.GROUP, dict(self.FILE, path=["One.swift"]))
        self.assertIn("F1", d.unresolved_var_ids)
        self.assertEqual(m, ())
        self.assertEqual([(r[0], r[1], r[3]) for r in res], self.DID_NOT_RESOLVE)

    def test_list_valued_file_source_tree_is_unresolved_never_raised(self):
        d, m, res = self._run(self.GROUP, dict(self.FILE, sourceTree=["<group>"]))
        self.assertIn("F1", d.unresolved_var_ids)
        self.assertEqual(m, ())
        self.assertEqual([(r[0], r[1], r[3]) for r in res], self.DID_NOT_RESOLVE)

    def test_dictionary_valued_group_path_leaves_its_child_unresolved(self):
        d, m, res = self._run(dict(self.GROUP, path={"dir": "Dir"}), self.FILE)
        self.assertIn("G", d.unresolved_var_ids)
        self.assertNotIn("F1", d.file_segments)
        self.assertEqual(m, ())
        self.assertEqual([(r[0], r[1], r[3]) for r in res], self.DID_NOT_RESOLVE)


class ClassicBuildFileBranchTests(unittest.TestCase):
    """ADR-0130 clause 8's build-file lookups inside one Sources phase: a
    `files` entry naming no `PBXBuildFile`, a build file whose `fileRef` is
    absent or dangling, and a `platformFilters` list. Each renders its own
    closed line at the entry's list-item line, and the phase's other members
    keep their rows."""

    def _run(self, phase_files, extra):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["F1", "F2"])
        objects["F1"] = _obj("PBXFileReference", sourceTree="<group>", path="One.swift")
        objects["F2"] = _obj("PBXFileReference", sourceTree="<group>", path="Two.swift")
        objects["T"] = _obj("PBXNativeTarget", name="T",
                            productType="com.apple.product-type.application",
                            buildPhases=["PHASE"])
        objects["PHASE"] = _obj("PBXSourcesBuildPhase", files=phase_files)
        objects["BF1"] = _obj("PBXBuildFile", fileRef="F1")
        objects.update(extra)
        doc = _pbx(objects, "PROJ")
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        with tempfile.TemporaryDirectory() as tmp:
            _mkfile(Path(tmp) / "One.swift")
            _mkfile(Path(tmp) / "Two.swift")
            m, res = sx.classic_memberships(doc, Path(tmp), d, "p", by_id, "X.xcodeproj")
        lines = doc.list_item_lines[("PHASE", "files")]
        return m, res, lines

    def _members(self, m):
        return [(r["file"], r["conditional"]) for r in m]

    def test_a_files_entry_naming_no_object_is_a_dangling_build_file(self):
        m, res, lines = self._run(["BF1", "GHOST"], {})
        self.assertEqual(self._members(m), [("One.swift", False)])
        self.assertEqual(res, (("unresolved-reference", "p", lines[1],
                                "a dangling build file in 'T's Sources phase"),))

    def test_a_files_entry_naming_a_file_reference_is_a_dangling_build_file(self):
        # The entry resolves to an object, but not to a `PBXBuildFile`: the
        # file reference is never taken as a member in the build file's place.
        m, res, lines = self._run(["BF1", "F2"], {})
        self.assertEqual(self._members(m), [("One.swift", False)])
        self.assertEqual(res, (("unresolved-reference", "p", lines[1],
                                "a dangling build file in 'T's Sources phase"),))

    def test_a_build_file_with_no_file_ref_is_a_dangling_file_reference(self):
        m, res, lines = self._run(["BF1", "BF2"], {"BF2": _obj("PBXBuildFile")})
        self.assertEqual(self._members(m), [("One.swift", False)])
        self.assertEqual(res, (("unresolved-reference", "p", lines[1],
                                "a dangling file reference in 'T's Sources phase"),))

    def test_a_build_file_whose_file_ref_names_nothing_is_a_dangling_file_reference(self):
        m, res, lines = self._run(["BF1", "BF2"], {"BF2": _obj("PBXBuildFile", fileRef="GHOST")})
        self.assertEqual(self._members(m), [("One.swift", False)])
        self.assertEqual(res, (("unresolved-reference", "p", lines[1],
                                "a dangling file reference in 'T's Sources phase"),))

    def test_a_platform_filters_list_marks_the_row_conditional_with_one_line(self):
        m, res, lines = self._run(["BF1", "BF2"], {
            "BF2": _obj("PBXBuildFile", fileRef="F2", platformFilters=["ios", "maccatalyst"])})
        self.assertEqual(self._members(m), [("One.swift", False), ("Two.swift", True)])
        self.assertEqual(res, (("conditional-setting", "p", lines[1],
                                "a build file in 'T's Sources phase carries a platform filter"),))

    def test_a_filtered_build_file_with_a_dangling_file_ref_renders_both_lines(self):
        m, res, lines = self._run(["BF1", "BF2"], {
            "BF2": _obj("PBXBuildFile", fileRef="GHOST", platformFilter="ios")})
        self.assertEqual(self._members(m), [("One.swift", False)])
        self.assertEqual(res, (
            ("conditional-setting", "p", lines[1],
             "a build file in 'T's Sources phase carries a platform filter"),
            ("unresolved-reference", "p", lines[1],
             "a dangling file reference in 'T's Sources phase")))


class ClassicMembershipTests(unittest.TestCase):
    def test_sources_phase_and_variant_group(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["F1", "VG", "F2"])
        objects["F1"] = _obj("PBXFileReference", sourceTree="<group>", path="One.swift")
        objects["VG"] = _obj("PBXVariantGroup", sourceTree="<group>", name="Main.storyboard", children=["V1", "V2"])
        objects["V1"] = _obj("PBXFileReference", sourceTree="<group>", path="Base.lproj/Main.swift")
        objects["V2"] = _obj("PBXFileReference", sourceTree="<group>", path="en.lproj/Main.swift")
        objects["F2"] = _obj("PBXFileReference", sourceTree="<group>", path="Outside.swift")
        objects["T"] = _obj("PBXNativeTarget", name="T", productType="com.apple.product-type.application", buildPhases=["PHASE"])
        objects["PHASE"] = _obj("PBXSourcesBuildPhase", files=["BF1", "BFV"])
        objects["BF1"] = _obj("PBXBuildFile", fileRef="F1")
        objects["BFV"] = _obj("PBXBuildFile", fileRef="VG")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "One.swift")
            _mkfile(root / "Base.lproj" / "Main.swift")
            _mkfile(root / "en.lproj" / "Main.swift")
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.classic_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            files = sorted(row["file"] for row in m)
            self.assertEqual(files, ["Base.lproj/Main.swift", "One.swift", "en.lproj/Main.swift"])
            self.assertEqual(res, ())

    def test_file_in_group_no_sources_phase_no_row(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["F1"])
        objects["F1"] = _obj("PBXFileReference", sourceTree="<group>", path="Orphan.swift")
        objects["T"] = _obj("PBXNativeTarget", name="T", productType="com.apple.product-type.application", buildPhases=[])
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        with tempfile.TemporaryDirectory() as tmp:
            m, res = sx.classic_memberships(doc, Path(tmp), d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())
        self.assertEqual(res, ())

    def test_platform_filter_on_build_file_marks_conditional_and_residual(self):
        # ADR-0130 clause 8: "A build file's platformFilter or
        # platformFilters renders its row marked conditional plus one
        # conditional-setting line."
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["F1"])
        objects["F1"] = _obj("PBXFileReference", sourceTree="<group>", path="One.swift")
        objects["T"] = _obj("PBXNativeTarget", name="T", productType="com.apple.product-type.application", buildPhases=["PHASE"])
        objects["PHASE"] = _obj("PBXSourcesBuildPhase", files=["BF1"])
        objects["BF1"] = _obj("PBXBuildFile", fileRef="F1", platformFilter="maccatalyst")
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "One.swift")
            m, res = sx.classic_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(len(m), 1)
        self.assertTrue(m[0]["conditional"])
        residual_classes = [r[0] for r in res]
        self.assertIn("conditional-setting", residual_classes)

    def test_platform_filters_by_relative_path_marks_conditional_and_residual(self):
        # ADR-0130 clause 9: "platformFiltersByRelativePath marks the row
        # conditional plus one conditional-setting line."
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["Owner", "Other"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj(
                "PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared",
                exceptions=["EXC1"])
            objects["EXC1"] = _obj(
                "PBXFileSystemSynchronizedBuildFileExceptionSet",
                target="Other", membershipExceptions=["One.swift"],
                platformFiltersByRelativePath={"One.swift": ["maccatalyst"]})
            objects["Owner"] = _obj(
                "PBXNativeTarget", name="Owner",
                productType="com.apple.product-type.application",
                fileSystemSynchronizedGroups=["ROOT"])
            objects["Other"] = _obj(
                "PBXNativeTarget", name="Other",
                productType="com.apple.product-type.app-extension")
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            added = [row for row in m if row["route"] == "added by an exception set"]
            self.assertEqual(len(added), 1)
            self.assertTrue(added[0]["conditional"])
            residual_classes = [r[0] for r in res]
            self.assertIn("conditional-setting", residual_classes)

    def test_two_targets_share_one_swift_file_one_row_each_no_residual(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T1", "T2"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["F1"])
        objects["F1"] = _obj("PBXFileReference", sourceTree="<group>", path="Shared.swift")
        objects["T1"] = _obj("PBXNativeTarget", name="T1", productType="com.apple.product-type.application", buildPhases=["P1"])
        objects["T2"] = _obj("PBXNativeTarget", name="T2", productType="com.apple.product-type.app-extension", buildPhases=["P2"])
        objects["P1"] = _obj("PBXSourcesBuildPhase", files=["BF1"])
        objects["P2"] = _obj("PBXSourcesBuildPhase", files=["BF2"])
        objects["BF1"] = _obj("PBXBuildFile", fileRef="F1")
        objects["BF2"] = _obj("PBXBuildFile", fileRef="F1")
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared.swift")
            m, res = sx.classic_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(res, ())
        pairs = sorted((row["file"], row["target"]) for row in m)
        self.assertEqual(pairs, [("Shared.swift", "T1"), ("Shared.swift", "T2")])

    def test_baits_fixture_no_inference_from_names(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["MyApp"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["G1"])
        objects["G1"] = _obj("PBXGroup", sourceTree="<group>", path="MyApp", children=["F1"])
        objects["F1"] = _obj("PBXFileReference", sourceTree="<group>", path="MyApp.swift")
        objects["MyApp"] = _obj(
            "PBXNativeTarget", name="MyApp",
            productType="com.apple.product-type.application", buildPhases=[])
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        with tempfile.TemporaryDirectory() as tmp:
            m, res = sx.classic_memberships(doc, Path(tmp), d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())
        s, sres = sx.synced_memberships(doc, Path("/tmp"), d, "p", by_id, "X.xcodeproj")
        self.assertEqual(s, ())


class ClassicMembershipClause3Tests(unittest.TestCase):
    """ADR-0130 clause 3: a classic member path is matched byte for byte
    against the parent directory's real listing, never opened or stat-ed
    at the path as written, and the matched entry is a member only when
    `lstat` reports a regular file."""

    def _one_file_fixture(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["F1"])
        objects["F1"] = _obj("PBXFileReference", sourceTree="<group>", path="One.swift")
        objects["T"] = _obj(
            "PBXNativeTarget", name="T",
            productType="com.apple.product-type.application", buildPhases=["PHASE"])
        objects["PHASE"] = _obj("PBXSourcesBuildPhase", files=["BF1"])
        objects["BF1"] = _obj("PBXBuildFile", fileRef="F1")
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        return doc, d, by_id

    def test_case_mismatched_name_no_row_and_unresolved_reference(self):
        doc, d, by_id = self._one_file_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "one.swift")  # on-disk name differs only by case
            m, res = sx.classic_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())
        self.assertEqual([r[0] for r in res], ["unresolved-reference"])

    def test_missing_file_no_row_and_unresolved_reference(self):
        doc, d, by_id = self._one_file_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # One.swift is never written to disk.
            m, res = sx.classic_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())
        self.assertEqual([r[0] for r in res], ["unresolved-reference"])

    @unittest.skipIf(not hasattr(os, "symlink"), "platform has no symlink support")
    def test_symlinked_file_no_row(self):
        doc, d, by_id = self._one_file_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "_real.swift"
            target.write_bytes(b"x")
            try:
                os.symlink(target, root / "One.swift")
            except OSError:
                self.skipTest("host refuses symlink creation")
            m, res = sx.classic_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())

    def test_exact_name_control_renders_row(self):
        doc, d, by_id = self._one_file_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "One.swift")
            m, res = sx.classic_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(res, ())
        self.assertEqual(len(m), 1)
        self.assertEqual(m[0]["file"], "One.swift")



def _mkfile(path, content=b"x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


class DirectoryComponentByteExactTests(unittest.TestCase):
    """ADR-0130 clause 3, and byte-stable output across hosts: every
    DIRECTORY component of a member
    path is matched byte for byte against its parent's listing too, not only
    the file name. On a case-folding host (macOS by default) the path as
    written `sources/One.swift` opens `Sources/One.swift`; on Linux it names
    nothing. A row that renders on one host and not the other breaks the
    host-independent golden, so neither host may render one."""

    def _classic(self, group_path):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["G"])
        objects["G"] = _obj("PBXGroup", sourceTree="<group>", path=group_path, children=["F1"])
        objects["F1"] = _obj("PBXFileReference", sourceTree="<group>", path="One.swift")
        objects["T"] = _obj(
            "PBXNativeTarget", name="T",
            productType="com.apple.product-type.application", buildPhases=["PHASE"])
        objects["PHASE"] = _obj("PBXSourcesBuildPhase", files=["BF1"])
        objects["BF1"] = _obj("PBXBuildFile", fileRef="F1")
        doc = _pbx(objects, "PROJ")
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        return doc, sx.descend(doc, ()), by_id

    def _synced(self, root_path):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
        objects["ROOT"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>",
                               path=root_path)
        objects["T"] = _obj(
            "PBXNativeTarget", name="T",
            productType="com.apple.product-type.application",
            fileSystemSynchronizedGroups=["ROOT"])
        doc = _pbx(objects, "PROJ")
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        return doc, sx.descend(doc, ()), by_id

    def test_classic_case_mismatched_directory_no_row(self):
        doc, d, by_id = self._classic("sources")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Sources" / "One.swift")
            m, res = sx.classic_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())
        self.assertEqual([r[0] for r in res], ["unresolved-reference"])

    def test_classic_exact_directory_control_renders_row(self):
        doc, d, by_id = self._classic("Sources")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Sources" / "One.swift")
            m, res = sx.classic_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(res, ())
        self.assertEqual([row["file"] for row in m], ["Sources/One.swift"])

    def test_synced_case_mismatched_root_no_row(self):
        doc, d, by_id = self._synced("shared")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            m, _res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())

    def test_synced_exact_root_control_renders_row(self):
        doc, d, by_id = self._synced("Shared")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            m, _res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual([row["file"] for row in m], ["Shared/One.swift"])


class SyncedMembershipTests(unittest.TestCase):
    def test_basic_membership_for_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            _mkfile(root / "Shared" / "Sub" / "Two.swift")
            _mkfile(root / "Shared" / "Skip.txt")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared")
            objects["T"] = _obj(
                "PBXNativeTarget", name="T",
                productType="com.apple.product-type.application",
                fileSystemSynchronizedGroups=["ROOT"])
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            self.assertIn("ROOT", d.synced_roots)
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            files = sorted(row["file"] for row in m)
            self.assertEqual(files, ["Shared/One.swift", "Shared/Sub/Two.swift"])
            self.assertEqual(res, ())
            self.assertTrue(all(row["route"] == "folder-synced root Shared" for row in m))

    def test_bundle_suffix_stops_descent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            _mkfile(root / "Shared" / "Assets.xcassets" / "Sneaky.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared")
            objects["T"] = _obj(
                "PBXNativeTarget", name="T",
                productType="com.apple.product-type.application",
                fileSystemSynchronizedGroups=["ROOT"])
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            files = sorted(row["file"] for row in m)
            self.assertEqual(files, ["Shared/One.swift"])

    def test_symlinked_dir_and_file_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            outside = Path(tmp).parent / "outside_dir"
            outside.mkdir(exist_ok=True)
            _mkfile(outside / "Sneaky.swift")
            try:
                (root / "Shared" / "Linked").symlink_to(outside, target_is_directory=True)
                (root / "Shared" / "LinkedFile.swift").symlink_to(outside / "Sneaky.swift")
            except OSError:
                self.skipTest("symlinks unsupported in this environment")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared")
            objects["T"] = _obj(
                "PBXNativeTarget", name="T",
                productType="com.apple.product-type.application",
                fileSystemSynchronizedGroups=["ROOT"])
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            files = sorted(row["file"] for row in m)
            self.assertEqual(files, ["Shared/One.swift"])

    def test_exception_set_excludes_and_adds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            _mkfile(root / "Shared" / "Extra.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["Owner", "Other"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj(
                "PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared",
                exceptions=["EXC1", "EXC2"])
            objects["EXC1"] = _obj(
                "PBXFileSystemSynchronizedBuildFileExceptionSet",
                target="Owner", membershipExceptions=["One.swift"])
            objects["EXC2"] = _obj(
                "PBXFileSystemSynchronizedBuildFileExceptionSet",
                target="Other", membershipExceptions=["Extra.swift"])
            objects["Owner"] = _obj(
                "PBXNativeTarget", name="Owner",
                productType="com.apple.product-type.application",
                fileSystemSynchronizedGroups=["ROOT"])
            objects["Other"] = _obj(
                "PBXNativeTarget", name="Other",
                productType="com.apple.product-type.app-extension")
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            self.assertEqual(res, ())
            by_target = {}
            for row in m:
                by_target.setdefault(row["target"], []).append((row["file"], row["route"]))
            owner_rows = sorted(by_target["Owner"])
            self.assertIn(("Shared/One.swift", "excluded by an exception set"), owner_rows)
            self.assertNotIn(("Shared/One.swift", "folder-synced root Shared"), owner_rows)
            self.assertIn(("Shared/Extra.swift", "folder-synced root Shared"), owner_rows)
            other_rows = sorted(by_target["Other"])
            self.assertEqual(other_rows, [("Shared/Extra.swift", "added by an exception set")])

    def test_root_owned_by_two_targets_one_row_each(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "Common.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T1", "T2"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared")
            objects["T1"] = _obj(
                "PBXNativeTarget", name="T1",
                productType="com.apple.product-type.application",
                fileSystemSynchronizedGroups=["ROOT"])
            objects["T2"] = _obj(
                "PBXNativeTarget", name="T2",
                productType="com.apple.product-type.application",
                fileSystemSynchronizedGroups=["ROOT"])
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            self.assertEqual(res, ())
            pairs = sorted((row["file"], row["target"]) for row in m)
            self.assertEqual(pairs, [("Shared/Common.swift", "T1"), ("Shared/Common.swift", "T2")])

    def test_explicit_folders_stops_descent(self):
        # ADR-0130 clause 9: "Descent stops at ... each explicitFolders
        # entry. A file inside either is not a member."
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            _mkfile(root / "Shared" / "Vendored" / "Two.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj(
                "PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared",
                explicitFolders=["Vendored"])
            objects["T"] = _obj(
                "PBXNativeTarget", name="T",
                productType="com.apple.product-type.application",
                fileSystemSynchronizedGroups=["ROOT"])
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            files = sorted(row["file"] for row in m)
            self.assertEqual(files, ["Shared/One.swift"])

    def test_explicit_file_types_retypes_swift_withheld_with_residual(self):
        # ADR-0130 clause 9: "An explicitFileTypes entry that retypes a
        # .swift file does the same [withholds + unsupported-project-form]."
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            _mkfile(root / "Shared" / "Generated.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj(
                "PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared",
                explicitFileTypes={"Generated.swift": "text"})
            objects["T"] = _obj(
                "PBXNativeTarget", name="T",
                productType="com.apple.product-type.application",
                fileSystemSynchronizedGroups=["ROOT"])
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            files = sorted(row["file"] for row in m)
            self.assertEqual(files, ["Shared/One.swift"])
            residual_classes = [r[0] for r in res]
            self.assertIn("unsupported-project-form", residual_classes)

    def test_build_phase_membership_exception_set_withholds_with_residual(self):
        # ADR-0130 clause 9: a PBXFileSystemSynchronizedGroupBuildPhaseMembershipExceptionSet
        # withholds the rows it names for its target and renders
        # unsupported-project-form.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            _mkfile(root / "Shared" / "Two.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj(
                "PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared",
                exceptions=["EXC1"])
            objects["EXC1"] = _obj(
                "PBXFileSystemSynchronizedGroupBuildPhaseMembershipExceptionSet",
                membershipExceptions=["Two.swift"])
            objects["T"] = _obj(
                "PBXNativeTarget", name="T",
                productType="com.apple.product-type.application",
                fileSystemSynchronizedGroups=["ROOT"])
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            files = sorted(row["file"] for row in m)
            self.assertEqual(files, ["Shared/One.swift"])
            residual_classes = [r[0] for r in res]
            self.assertIn("unsupported-project-form", residual_classes)

    def test_build_phase_exception_set_withholds_only_its_own_target(self):
        # ADR-0130 clause 9: the set "withholds the rows it names for its
        # target". It names its target through `buildPhase`; a second owner
        # of the same root keeps its row.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            _mkfile(root / "Shared" / "Two.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["TA", "TB"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj(
                "PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared",
                exceptions=["EXC1"])
            objects["PHA"] = _obj("PBXSourcesBuildPhase", files=[])
            objects["PHB"] = _obj("PBXSourcesBuildPhase", files=[])
            objects["EXC1"] = _obj(
                "PBXFileSystemSynchronizedGroupBuildPhaseMembershipExceptionSet",
                buildPhase="PHA", membershipExceptions=["Two.swift"])
            for tid, phase in (("TA", "PHA"), ("TB", "PHB")):
                objects[tid] = _obj(
                    "PBXNativeTarget", name=tid, buildPhases=[phase],
                    productType="com.apple.product-type.application",
                    fileSystemSynchronizedGroups=["ROOT"])
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            pairs = sorted((row["target"], row["file"]) for row in m)
            self.assertEqual(pairs, [("TA", "Shared/One.swift"), ("TB", "Shared/One.swift"),
                                     ("TB", "Shared/Two.swift")])
            self.assertIn("unsupported-project-form", [r[0] for r in res])

    def test_dangling_build_phase_renders_unresolved_reference(self):
        # ADR-0130 clause 9: a buildPhase id that
        # resolves to no owner (neither via `buildPhase` nor a `target`
        # fallback) withholds from every owner AND now renders its own
        # `unresolved-reference` naming the dangling buildPhase, alongside
        # the generic `unsupported-project-form` line.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["TA"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj(
                "PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared",
                exceptions=["EXC1"])
            objects["EXC1"] = _obj(
                "PBXFileSystemSynchronizedGroupBuildPhaseMembershipExceptionSet",
                buildPhase="NOPE", membershipExceptions=["One.swift"])
            objects["TA"] = _obj(
                "PBXNativeTarget", name="TA",
                productType="com.apple.product-type.application",
                fileSystemSynchronizedGroups=["ROOT"])
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            residual_classes = [r[0] for r in res]
            self.assertIn("unresolved-reference", residual_classes)
            self.assertIn("unsupported-project-form", residual_classes)

    def test_build_phase_exception_set_target_key_fallback(self):
        # ADR-0130 clause 9: a build-phase exception set with no `buildPhase` but a
        # `target` key naming an owner falls back to that owner alone, with
        # no dangling-buildPhase residual.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            _mkfile(root / "Shared" / "Two.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["TA", "TB"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj(
                "PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared",
                exceptions=["EXC1"])
            objects["EXC1"] = _obj(
                "PBXFileSystemSynchronizedGroupBuildPhaseMembershipExceptionSet",
                target="TA", membershipExceptions=["Two.swift"])
            for tid in ("TA", "TB"):
                objects[tid] = _obj(
                    "PBXNativeTarget", name=tid,
                    productType="com.apple.product-type.application",
                    fileSystemSynchronizedGroups=["ROOT"])
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            pairs = sorted((row["target"], row["file"]) for row in m)
            self.assertEqual(pairs, [("TA", "Shared/One.swift"),
                                      ("TB", "Shared/One.swift"), ("TB", "Shared/Two.swift")])
            self.assertNotIn("unresolved-reference", [r[0] for r in res])

    def test_platform_filtered_default_member_row_is_conditional(self):
        # ADR-0130 clause 9: `platformFiltersByRelativePath` "marks the row
        # conditional plus one conditional-setting line" -- the row flag too.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "Foo.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj(
                "PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared",
                exceptions=["EXC1"])
            objects["EXC1"] = _obj(
                "PBXFileSystemSynchronizedBuildFileExceptionSet", target="T",
                platformFiltersByRelativePath={"Foo.swift": ["ios"]})
            objects["T"] = _obj(
                "PBXNativeTarget", name="T",
                productType="com.apple.product-type.application",
                fileSystemSynchronizedGroups=["ROOT"])
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            self.assertEqual([(r["file"], r["conditional"]) for r in m], [("Shared/Foo.swift", True)])
            self.assertEqual([r[0] for r in res], ["conditional-setting"])

    def test_localized_entry_resolves_lproj_variants(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "ShareExtension" / "Base.lproj" / "View.swift")
            _mkfile(root / "Shared" / "ShareExtension" / "en.lproj" / "View.swift")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["Owner"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj(
                "PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared",
                exceptions=["EXC1"])
            objects["EXC1"] = _obj(
                "PBXFileSystemSynchronizedBuildFileExceptionSet",
                target="Owner", membershipExceptions=["/Localized/ShareExtension/View.swift"])
            objects["Owner"] = _obj(
                "PBXNativeTarget", name="Owner",
                productType="com.apple.product-type.app-extension")
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            self.assertEqual(res, ())
            files = sorted(row["file"] for row in m)
            self.assertEqual(files, [
                "Shared/ShareExtension/Base.lproj/View.swift",
                "Shared/ShareExtension/en.lproj/View.swift",
            ])



class SyncedRootSymlinkTests(unittest.TestCase):
    """ADR-0130 clause 3 -- no directory
    symlink is descended. A symlinked synced root that resolves outside the
    checkout renders `path-escape`; one that resolves inside it is refused
    without a filesystem read and renders `unresolved-reference`, never a
    membership row."""

    def _project(self, root_path="Shared"):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
        objects["ROOT"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path=root_path)
        objects["T"] = _obj(
            "PBXNativeTarget", name="T",
            productType="com.apple.product-type.application",
            fileSystemSynchronizedGroups=["ROOT"])
        return objects

    def test_symlinked_root_inside_checkout_no_rows_and_residual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "RealDir" / "One.swift")
            try:
                (root / "Shared").symlink_to(root / "RealDir", target_is_directory=True)
            except OSError:
                self.skipTest("symlinks unsupported in this environment")
            objects = self._project()
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            self.assertEqual(m, ())
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0][0], "unresolved-reference")

    def test_symlinked_root_escaping_checkout_renders_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp)
            root = outer / "checkout"
            root.mkdir()
            outside = outer / "outside"
            _mkfile(outside / "Sneaky.swift")
            try:
                (root / "Shared").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlinks unsupported in this environment")
            objects = self._project()
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            self.assertEqual(m, ())
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0][0], "path-escape")

    def test_control_non_symlinked_root_unaffected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "One.swift")
            objects = self._project()
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
            self.assertEqual(res, ())
            self.assertEqual(sorted(r["file"] for r in m), ["Shared/One.swift"])



class TypeConfusedDependencyTests(unittest.TestCase):
    """ADR-0130 clause 2, last bullet: `target_dependencies`
    never raises out of a type-confused pbxproj value -- a list or dict in
    place of an object id, which Python cannot hash as a dict key. Every
    shape here renders one
    `unresolved-reference` rather than `TypeError`/`AttributeError`."""

    def _targets(self):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["A", "B"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=[])
        objects["A"] = _obj("PBXNativeTarget", name="A", productType="com.apple.product-type.application")
        objects["B"] = _obj("PBXNativeTarget", name="B", productType="com.apple.product-type.app-extension")
        return objects

    def test_remote_global_id_string_is_a_dict(self):
        objects = self._targets()
        objects["A"]["dependencies"] = ["DEP"]
        objects["DEP"] = _obj("PBXTargetDependency", targetProxy="PROXY")
        objects["PROXY"] = _obj("PBXContainerItemProxy", containerPortal="PROJ",
                                 remoteGlobalIDString={"a": "b"})
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        edges, res = sx.target_dependencies(doc, "X.xcodeproj", by_id, "p")
        self.assertEqual(edges, ())
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][0], "unresolved-reference")

    def test_target_dependency_target_is_a_list(self):
        objects = self._targets()
        objects["A"]["dependencies"] = ["DEP"]
        objects["DEP"] = _obj("PBXTargetDependency", target=["B"])
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        edges, res = sx.target_dependencies(doc, "X.xcodeproj", by_id, "p")
        self.assertEqual(edges, ())
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][0], "unresolved-reference")

    def test_dependencies_list_item_is_a_dict(self):
        objects = self._targets()
        objects["A"]["dependencies"] = [{"a": "b"}]
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        edges, res = sx.target_dependencies(doc, "X.xcodeproj", by_id, "p")
        self.assertEqual(edges, ())
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][0], "unresolved-reference")


class ReadProjectsExceptionBoundaryTests(unittest.TestCase):
    """ADR-0130 clause 2, last bullet: no content of a
    project file ever makes the deriver exit 2. `read_projects` catches
    every exception a per-file step raises at THAT file's own boundary,
    renders one `project-unreadable`/`malformed` residual, and continues
    with the next bundle -- proven here with a SEEDED exception (a
    positive control: with the boundary removed, the same seed escapes and
    the test fails with the seeded exception itself, never a clean
    assertion failure)."""

    def _reads(self, root, bundles):
        files = {}
        for bundle_rel, doc_text in bundles:
            pbxproj_dir = root / bundle_rel
            pbxproj_dir.mkdir(parents=True)
            pbxproj_path = pbxproj_dir / "project.pbxproj"
            pbxproj_path.write_text(doc_text)
            files[f"{bundle_rel}/project.pbxproj"] = pbxproj_path.read_bytes()
        return mock.Mock(
            bundles=[(b, True, True) for b, _ in bundles],
            refusals={},
            files=files,
        )

    def test_seeded_exception_in_one_project_is_caught_and_others_continue(self):
        good_text = (
            "// !$*UTF8*$!\n{\n\tarchiveVersion = 1;\n\tobjectVersion = 56;\n"
            "\trootObject = PRJ;\n\tobjects = {\n\t\tPRJ = {\n"
            "\t\t\tisa = PBXProject;\n\t\t\tmainGroup = MG;\n"
            "\t\t\ttargets = (\n\t\t\t\tTGT,\n\t\t\t);\n\t\t};\n"
            "\t\tMG = {\n\t\t\tisa = PBXGroup;\n"
            '\t\t\tsourceTree = "<group>";\n\t\t\tchildren = (\n\t\t\t);\n\t\t};\n'
            "\t\tTGT = {\n\t\t\tisa = PBXNativeTarget;\n\t\t\tname = Good;\n"
            '\t\t\tproductType = "com.apple.product-type.application";\n'
            "\t\t\tbuildPhases = (\n\t\t\t);\n\t\t\tdependencies = (\n\t\t\t);\n\t\t};\n"
            "\t};\n}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reads = self._reads(root, [
                ("Bad.xcodeproj", good_text.replace("Good", "Bad")),
                ("Good.xcodeproj", good_text),
            ])

            real_target_rows = sx.target_rows

            def seeded_target_rows(doc, pbxproj_path, container_name, **kwargs):
                if container_name == "Bad.xcodeproj":
                    raise ValueError("seeded failure for the positive control")
                return real_target_rows(doc, pbxproj_path, container_name, **kwargs)

            with mock.patch.object(sx, "target_rows", side_effect=seeded_target_rows):
                result = sx.read_projects(root, reads, [])

        names = {t["name"] for t in result["targets"]}
        self.assertEqual(names, {"Good"})
        malformed = [r for r in result["residuals"]
                     if r[0] == "project-unreadable" and r[1] == "Bad.xcodeproj/project.pbxproj"]
        self.assertEqual(len(malformed), 1, result["residuals"])
        self.assertEqual(malformed[0][3], "malformed")

    def test_a_late_failure_leaves_nothing_of_that_project_behind(self):
        """A project that fails after its target rows were built renders
        only its `malformed` line: never half its rows beside a line saying
        the same file could not be read."""
        good_text = (
            "// !$*UTF8*$!\n{\n\tarchiveVersion = 1;\n\tobjectVersion = 56;\n"
            "\trootObject = PRJ;\n\tobjects = {\n\t\tPRJ = {\n"
            "\t\t\tisa = PBXProject;\n\t\t\tmainGroup = MG;\n"
            "\t\t\ttargets = (\n\t\t\t\tTGT,\n\t\t\t);\n\t\t};\n"
            "\t\tMG = {\n\t\t\tisa = PBXGroup;\n"
            '\t\t\tsourceTree = "<group>";\n\t\t\tchildren = (\n\t\t\t);\n\t\t};\n'
            "\t\tTGT = {\n\t\t\tisa = PBXNativeTarget;\n\t\t\tname = Bad;\n"
            '\t\t\tproductType = "com.apple.product-type.application";\n'
            "\t\t\tbuildPhases = (\n\t\t\t);\n\t\t\tdependencies = (\n\t\t\t);\n\t\t};\n"
            "\t};\n}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reads = self._reads(root, [("Bad.xcodeproj", good_text)])
            with mock.patch.object(sx, "synced_memberships",
                                   side_effect=TypeError("seeded late failure")):
                result = sx.read_projects(root, reads, [])
        self.assertEqual(result["targets"], ())
        self.assertEqual([r[0] for r in result["residuals"]], ["project-unreadable"])



class OneRowPerFileTargetRouteTests(unittest.TestCase):
    """ADR-0130 clause 8: "There is one row per file, target and route." A
    file reference named by two build files in the same target's Sources
    phase (a duplicate Xcode itself skips with a warning) is one membership,
    not two. The row keeps the first declaring line, and it is conditional
    only when every build file naming it carries a platform filter."""

    _TEXT = (
        "// !$*UTF8*$!\n{\n\tarchiveVersion = 1;\n\tobjectVersion = 56;\n"
        "\trootObject = PRJ;\n\tobjects = {\n"
        "\t\tPRJ = {\n\t\t\tisa = PBXProject;\n\t\t\tmainGroup = MG;\n"
        "\t\t\ttargets = (\n\t\t\t\tTGT,\n\t\t\t);\n\t\t};\n"
        "\t\tMG = {\n\t\t\tisa = PBXGroup;\n\t\t\tsourceTree = \"<group>\";\n"
        "\t\t\tchildren = (\n\t\t\t\tFR,\n\t\t\t);\n\t\t};\n"
        "\t\tFR = {\n\t\t\tisa = PBXFileReference;\n\t\t\tpath = Main.swift;\n"
        "\t\t\tsourceTree = \"<group>\";\n\t\t};\n"
        "\t\tBF1 = {\n\t\t\tisa = PBXBuildFile;\n\t\t\tfileRef = FR;\n%s\t\t};\n"
        "\t\tBF2 = {\n\t\t\tisa = PBXBuildFile;\n\t\t\tfileRef = FR;\n\t\t};\n"
        "\t\tSRC = {\n\t\t\tisa = PBXSourcesBuildPhase;\n"
        "\t\t\tfiles = (\n\t\t\t\tBF1,\n\t\t\t\tBF2,\n\t\t\t);\n\t\t};\n"
        "\t\tTGT = {\n\t\t\tisa = PBXNativeTarget;\n\t\t\tname = App;\n"
        "\t\t\tproductType = \"com.apple.product-type.application\";\n"
        "\t\t\tbuildPhases = (\n\t\t\t\tSRC,\n\t\t\t);\n"
        "\t\t\tdependencies = (\n\t\t\t);\n\t\t};\n"
        "\t};\n}\n"
    )

    def _derive(self, bf1_extra=""):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Main.swift").write_bytes(b"@main struct A {}\n")
            bundle = root / "App.xcodeproj"
            bundle.mkdir()
            (bundle / "project.pbxproj").write_text(self._TEXT % bf1_extra)
            reads = mock.Mock(bundles=[("App.xcodeproj", True, True)], refusals={},
                              files={"App.xcodeproj/project.pbxproj":
                                     (bundle / "project.pbxproj").read_bytes()})
            return sx.read_projects(root, reads, [])

    def test_duplicate_build_file_renders_one_row(self):
        result = self._derive()
        rows = [(m["file"], m["target"], m["route"]) for m in result["memberships"]]
        self.assertEqual(rows, [("Main.swift", "App", "classic Sources build phase")])

    def test_one_unfiltered_build_file_makes_the_row_unconditional(self):
        result = self._derive('\t\t\tplatformFilters = (\n\t\t\t\tios,\n\t\t\t);\n')
        self.assertEqual([m["conditional"] for m in result["memberships"]], [False])
        self.assertEqual([r[0] for r in result["residuals"]], ["conditional-setting"])


class ExceptionEntryClause3Tests(unittest.TestCase):
    """ADR-0130 clauses 3 and 9: a folder-synced exception-set entry is
    routed through the same checks as a classic Sources-phase member --
    lexical join first, then `_real_contained_dir`/`_classic_member_verdict`
    -- never a raw filesystem stat of the path as written."""

    def _fixture(self, membership_exceptions):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["Owner"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
        objects["ROOT"] = _obj(
            "PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared",
            exceptions=["EXC1"])
        objects["EXC1"] = _obj(
            "PBXFileSystemSynchronizedBuildFileExceptionSet",
            target="Owner", membershipExceptions=membership_exceptions)
        objects["Owner"] = _obj(
            "PBXNativeTarget", name="Owner",
            productType="com.apple.product-type.application")
        doc = _pbx(objects, "PROJ")
        rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        return doc, d, by_id

    def test_exact_name_control_renders_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "Foo.swift")
            doc, d, by_id = self._fixture(["Foo.swift"])
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(res, ())
        self.assertEqual([(row["file"], row["route"]) for row in m],
                          [("Shared/Foo.swift", "added by an exception set")])

    def test_case_mismatched_entry_never_matches_regardless_of_host(self):
        # The on-disk name is `Foo.swift`; the exception entry names
        # `foo.swift`. This must resolve to NO file on every host,
        # deterministically -- never a member row on a case-folding
        # filesystem (byte-stable goldens across hosts).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _mkfile(root / "Shared" / "Foo.swift")
            doc, d, by_id = self._fixture(["foo.swift"])
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())
        self.assertEqual([r[0] for r in res], ["unresolved-reference"])

    @unittest.skipIf(not hasattr(os, "symlink"), "platform has no symlink support")
    def test_symlinked_file_entry_no_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "_real.swift"
            _mkfile(target)
            (root / "Shared").mkdir(parents=True, exist_ok=True)
            try:
                os.symlink(target, root / "Shared" / "Foo.swift")
            except OSError:
                self.skipTest("host refuses symlink creation")
            doc, d, by_id = self._fixture(["Foo.swift"])
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())

    @unittest.skipIf(not hasattr(os, "symlink"), "platform has no symlink support")
    def test_symlinked_directory_entry_not_descended(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_dir = root / "_real_dir"
            _mkfile(real_dir / "Inside.swift")
            (root / "Shared").mkdir(parents=True, exist_ok=True)
            try:
                os.symlink(real_dir, root / "Shared" / "SubDir", target_is_directory=True)
            except OSError:
                self.skipTest("host refuses symlink creation")
            doc, d, by_id = self._fixture(["SubDir"])
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())
        self.assertEqual([r[0] for r in res], ["unresolved-reference"])

    def test_escaping_entry_renders_path_escape_not_unresolved_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Shared").mkdir(parents=True, exist_ok=True)
            doc, d, by_id = self._fixture(["../../Outside.swift"])
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())
        self.assertEqual([r[0] for r in res], ["path-escape"])

    def test_absolute_entry_renders_path_escape_never_lexically_joined(self):
        # ADR-0130 clause 3: `_lexical_join` treats
        # a leading "/" as an empty first segment and silently drops it --
        # an absolute exception entry must render `path-escape` BEFORE that
        # join, never be resolved as if relative to the synced root.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Shared").mkdir(parents=True, exist_ok=True)
            (root / "etc").mkdir(parents=True, exist_ok=True)
            _mkfile(root / "etc" / "passwd.swift")
            doc, d, by_id = self._fixture(["/etc/passwd.swift"])
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())
        self.assertEqual([r[0] for r in res], ["path-escape"])

    @unittest.skipIf(not hasattr(os, "symlink"), "platform has no symlink support")
    def test_localized_entry_symlinked_target_no_row(self):
        # ADR-0130 clauses 3 and 9: `_resolve_localized_entry`'s final
        # file resolution must also refuse a symlinked target -- routed
        # through `_classic_member_verdict`, the same as every other
        # member candidate.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "_real.swift"
            _mkfile(real)
            lproj = root / "Shared" / "ShareExtension" / "Base.lproj"
            lproj.mkdir(parents=True)
            try:
                os.symlink(real, lproj / "View.swift")
            except OSError:
                self.skipTest("host refuses symlink creation")
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["Owner"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
            objects["ROOT"] = _obj(
                "PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Shared",
                exceptions=["EXC1"])
            objects["EXC1"] = _obj(
                "PBXFileSystemSynchronizedBuildFileExceptionSet",
                target="Owner", membershipExceptions=["/Localized/ShareExtension/View.swift"])
            objects["Owner"] = _obj(
                "PBXNativeTarget", name="Owner",
                productType="com.apple.product-type.app-extension")
            doc = _pbx(objects, "PROJ")
            rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        self.assertEqual(m, ())


_SCANDIR_SEEN: list = []
_SCANDIR_ARMED: list = [False]


def _scandir_audit(event, args):
    if _SCANDIR_ARMED[0] and event == "os.scandir":
        _SCANDIR_SEEN.append(os.fsdecode(args[0]) if args and args[0] is not None else ".")


sys.addaudithook(_scandir_audit)  # cannot be removed; inert unless armed.


class LocalizedExceptionPruneTests(unittest.TestCase):
    """ADR-0129 clause 8 over the `/Localized/<dir>/<name>` exception form:
    a `<dir>` in or under a pruned directory is refused lexically, before any
    filesystem access, with one `unresolved-reference` naming no path. Inside
    a listed `<dir>`, a dot-named `.lproj` directory or a pruned segment in
    `<name>` is never matched."""

    def _run(self, root, entry):
        from crux.arch.packs import swift_prune  # noqa: F401
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["Owner"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
        objects["ROOT"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>",
                               path="Shared", exceptions=["EXC1"])
        objects["EXC1"] = _obj("PBXFileSystemSynchronizedBuildFileExceptionSet",
                               target="Owner", membershipExceptions=[entry])
        objects["Owner"] = _obj("PBXNativeTarget", name="Owner",
                                productType="com.apple.product-type.app-extension")
        doc = _pbx(objects, "PROJ")
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        del _SCANDIR_SEEN[:]
        _SCANDIR_ARMED[0] = True
        try:
            m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        finally:
            _SCANDIR_ARMED[0] = False
        return m, res, list(_SCANDIR_SEEN)

    def _pods_tree(self, root):
        _mkfile(root / "Shared" / "Pods" / "en.lproj" / "X.strings")
        _mkfile(root / "Shared" / "Pods" / "en.lproj" / "X.swift")

    def test_a_localized_dir_in_pods_is_refused_before_it_is_listed(self):
        from crux.arch.packs import swift_prune
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._pods_tree(root)
            for entry in ("/Localized/Pods/X.strings", "/Localized/Pods/X.swift"):
                with self.subTest(entry=entry):
                    m, res, listed = self._run(root, entry)
                    self.assertEqual(m, ())
                    self.assertEqual([(r[0], r[3]) for r in res],
                                     [("unresolved-reference", swift_prune.EXCEPTION_ENTRY_DETAIL)])
                    self.assertEqual([p for p in listed if "Pods" in p], [])

    def test_positive_control_with_the_prune_off_pods_is_listed(self):
        from crux.arch.packs import swift_prune
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._pods_tree(root)
            with mock.patch.object(swift_prune, "pruned_path",
                                   lambda segs, container=False: False):
                m, _res, listed = self._run(root, "/Localized/Pods/X.swift")
        self.assertTrue([p for p in listed if p.endswith(os.path.join("Shared", "Pods"))], listed)
        self.assertEqual([r["file"] for r in m], ["Shared/Pods/en.lproj/X.swift"])

    def _hidden_tree(self, root):
        _mkfile(root / "Shared" / "Res" / "en.lproj" / ".build" / "X.swift")
        _mkfile(root / "Shared" / "Res" / ".x.lproj" / "View.swift")

    def test_a_pruned_segment_inside_a_listed_dir_is_never_matched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._hidden_tree(root)
            for entry in ("/Localized/Res/.build/X.swift", "/Localized/Res/View.swift"):
                with self.subTest(entry=entry):
                    m, res, _listed = self._run(root, entry)
                    self.assertEqual(m, ())
                    self.assertEqual([(r[0], r[3]) for r in res], [(
                        "unresolved-reference",
                        "a /Localized/ exception entry on Shared resolves to no file")])

    def test_positive_control_with_the_prune_off_the_pruned_segments_match(self):
        from crux.arch.packs import swift_prune
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._hidden_tree(root)
            with mock.patch.object(swift_prune, "pruned_path",
                                   lambda segs, container=False: False):
                deep, _r1, _l1 = self._run(root, "/Localized/Res/.build/X.swift")
                hidden, _r2, _l2 = self._run(root, "/Localized/Res/View.swift")
        self.assertEqual([r["file"] for r in deep], ["Shared/Res/en.lproj/.build/X.swift"])
        self.assertEqual([r["file"] for r in hidden], ["Shared/Res/.x.lproj/View.swift"])


class ExceptionEntryBuildSettingReferenceTests(unittest.TestCase):
    """ADR-0130 clauses 3 and 9 (a build-setting segment is never
    resolved): a folder-synced
    exception entry that names a build-setting reference -- `$(X)`, `${X}` or
    bare `$X` -- is classified as a whole before the absolute-path test, the
    lexical join, the `/Localized/<dir>/<name>` split and any prune or
    filesystem call. Each such entry renders one `unresolved-reference` at its
    list-item line with a fixed detail, and changes no membership: a
    following `..` never cancels the reference, so it neither excludes an
    owner's default member nor adds a row for a non-owner. No
    `conditional-setting` line is written for it, even as a key of
    `platformFiltersByRelativePath`."""

    FORMS = ("$(X)", "${X}", "$X")

    def _tree(self, root):
        _mkfile(root / "Shared" / "Owned.swift")
        _mkfile(root / "Shared" / "Excluded.swift")
        _mkfile(root / "Shared" / "Res" / "en.lproj" / "Loc.swift")

    def _run(self, root, owner_entries, other_entries):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["Owner", "Other"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["ROOT"])
        objects["ROOT"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>",
                               path="Shared", exceptions=["EXC_OWNER", "EXC_OTHER"])
        objects["EXC_OWNER"] = _obj(
            "PBXFileSystemSynchronizedBuildFileExceptionSet", target="Owner",
            membershipExceptions=owner_entries,
            platformFiltersByRelativePath={e: ["ios"] for e in owner_entries})
        objects["EXC_OTHER"] = _obj(
            "PBXFileSystemSynchronizedBuildFileExceptionSet", target="Other",
            membershipExceptions=other_entries)
        objects["Owner"] = _obj("PBXNativeTarget", name="Owner",
                                productType="com.apple.product-type.application",
                                fileSystemSynchronizedGroups=["ROOT"])
        objects["Other"] = _obj("PBXNativeTarget", name="Other",
                                productType="com.apple.product-type.application")
        doc = _pbx(objects, "PROJ")
        self.assertEqual(doc.objects["EXC_OWNER"]["membershipExceptions"], owner_entries)
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        m, res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        rows = sorted((r["file"], r["target"], r["route"], r["conditional"]) for r in m)
        lines = doc.list_item_lines
        return rows, [(r[0], r[2], r[3]) for r in res], lines

    DEFAULT_ROWS = [("Shared/Excluded.swift", "Owner", "folder-synced root Shared", False),
                    ("Shared/Owned.swift", "Owner", "folder-synced root Shared", False)]

    def _entries(self, v):
        owner = [f"{v}/../Excluded.swift", f"/Localized/Res/{v}/../Loc.swift",
                 f"/Localized/{v}/Loc.swift", f"/abs/{v}/../Excluded.swift",
                 f"{v}/Pods/x.swift", f"Sub/../{v}/../Excluded.swift"]
        other = [f"{v}/../Owned.swift", f"/Localized/Res/{v}/../Loc.swift"]
        return owner, other

    def test_a_reference_in_any_position_changes_no_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._tree(root)
            for v in self.FORMS:
                with self.subTest(form=v):
                    owner, other = self._entries(v)
                    rows, res, lines = self._run(root, owner, other)
                    self.assertEqual(rows, self.DEFAULT_ROWS)
                    want_locs = (lines[("EXC_OWNER", "membershipExceptions")]
                                 + lines[("EXC_OTHER", "membershipExceptions")])
                    self.assertEqual(len(want_locs), len(owner) + len(other))
                    self.assertEqual(res, [("unresolved-reference", loc,
                                            sx.NEVER_RESOLVED_EXCEPTION_ENTRY_DETAIL)
                                           for loc in want_locs])

    def test_the_detail_names_no_path_and_no_variable(self):
        self.assertEqual(sx.NEVER_RESOLVED_EXCEPTION_ENTRY_DETAIL,
                         "an exception entry names a build-setting reference; "
                         "it is never resolved and changes no membership")

    def test_the_entry_reaches_no_join_split_prune_or_filesystem_call(self):
        from crux.arch.packs import swift_prune
        seen = []

        def spy(name, real):
            def wrapper(*args, **kwargs):
                if "$" in repr(args):
                    seen.append(name)
                return real(*args, **kwargs)
            return wrapper

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._tree(root)
            owner, other = self._entries("$(X)")
            with mock.patch.object(sx, "_lexical_join", spy("join", sx._lexical_join)), \
                 mock.patch.object(sx, "_localized_dir_segs", spy("split", sx._localized_dir_segs)), \
                 mock.patch.object(sx, "_resolve_localized_entry",
                                   spy("localized", sx._resolve_localized_entry)), \
                 mock.patch.object(sx, "_real_contained_dir", spy("fs-dir", sx._real_contained_dir)), \
                 mock.patch.object(sx, "_classic_member_verdict",
                                   spy("fs-file", sx._classic_member_verdict)), \
                 mock.patch.object(swift_prune, "pruned_path", spy("prune", swift_prune.pruned_path)):
                rows, _res, _lines = self._run(root, owner, other)
        self.assertEqual(rows, self.DEFAULT_ROWS)
        self.assertEqual(seen, [])

    def test_positive_control_without_the_classification_the_entries_move_rows(self):
        """The absence tests above are not vacuous: with the classification
        off, the same entries exclude the owner's real file, add a row for the
        non-owner, and write `conditional-setting` for the filtered entry."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._tree(root)
            with mock.patch.object(sx, "never_resolved", lambda value: False):
                rows, res, _lines = self._run(root, ["$(X)/../Excluded.swift"],
                                              ["$(X)/../Owned.swift"])
        self.assertIn(("Shared/Excluded.swift", "Owner", "excluded by an exception set", True), rows)
        self.assertIn(("Shared/Owned.swift", "Other", "added by an exception set", False), rows)
        self.assertIn("conditional-setting", [r[0] for r in res])

    def test_control_plain_and_literal_dollar_entries_still_apply(self):
        """A plain entry, and one whose `$` is followed by no identifier
        character, is no build-setting reference and still applies."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._tree(root)
            _mkfile(root / "Shared" / "Price$.swift")
            rows, res, _lines = self._run(root, ["Excluded.swift", "Price$.swift"], ["Owned.swift"])
        self.assertEqual(rows, [
            ("Shared/Excluded.swift", "Owner", "excluded by an exception set", True),
            ("Shared/Owned.swift", "Other", "added by an exception set", False),
            ("Shared/Owned.swift", "Owner", "folder-synced root Shared", False),
            ("Shared/Price$.swift", "Owner", "excluded by an exception set", True),
        ])
        self.assertEqual([r[0] for r in res], ["conditional-setting"] * 2)


class ProjectDirVariableTests(unittest.TestCase):
    """ADR-0130 clause 3: a `$(VAR)` segment in `projectDirPath` is classified
    before any join, so a following `..` cannot cancel it. The project
    directory is then unresolved: nothing is descended, the field itself
    renders nothing, and each Sources-phase entry renders one
    `unresolved-reference`. No membership row is fabricated."""

    SOURCES_DETAIL = "a file reference in 'App's Sources phase did not resolve"
    SYNCED_DETAIL = "target 'App' names a folder-synced root that descent did not resolve"

    def _doc(self, pdp, synced=None):
        objects = {}
        proj = dict(mainGroup="MAIN", targets=["T"])
        if pdp is not None:
            proj["projectDirPath"] = pdp
        objects["PROJ"] = _obj("PBXProject", **proj)
        children = ["G"] + (["SR"] if synced is not None else [])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=children)
        objects["G"] = _obj("PBXGroup", sourceTree="<group>", path="App", children=["F1", "F2"])
        objects["F1"] = _obj("PBXFileReference", sourceTree="<group>", path="Main.swift")
        objects["F2"] = _obj("PBXFileReference", sourceTree="<group>", path="Other.swift")
        objects["BF1"] = _obj("PBXBuildFile", fileRef="F1")
        objects["BF2"] = _obj("PBXBuildFile", fileRef="F2")
        objects["SP"] = _obj("PBXSourcesBuildPhase", files=["BF1", "BF2"])
        target = dict(name="App", productType="com.apple.product-type.application",
                      buildPhases=["SP"])
        if synced is not None:
            objects["SR"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>",
                                 path="Synced")
            target["fileSystemSynchronizedGroups"] = synced
        objects["T"] = _obj("PBXNativeTarget", **target)
        return _pbx(objects, "PROJ")

    def _tree(self, root):
        for base in ("ios", "$(SRCROOT)", "ios/$(SRCROOT)", "${SRCROOT}", "ios/${SRCROOT}",
                     "$SRCROOT", "ios/$SRCROOT"):
            _mkfile(root / base / "App" / "Main.swift")
            _mkfile(root / base / "App" / "Other.swift")
            _mkfile(root / base / "Synced" / "S.swift")

    def _run(self, root, doc, bundle_dir=("ios",)):
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, bundle_dir)
        cm, cres = sx.classic_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        sm, sres = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
        other = sx.escape_residuals(doc, d, "p") + sx.descent_unresolved_residuals(doc, d, "p")
        return sorted(r["file"] for r in cm + sm), [(r[0], r[3]) for r in cres + sres + other]

    def test_a_variable_then_dotdot_fabricates_no_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._tree(root)
            for pdp in ("$(SRCROOT)/..", "$(SRCROOT)", "$(PROJECT_DIR)/../..",
                        "${SRCROOT}/..", "$SRCROOT/..", "${SRCROOT}", "$SRCROOT"):
                with self.subTest(pdp=pdp):
                    rows, res = self._run(root, self._doc(pdp))
                    self.assertEqual(rows, [])
                    self.assertEqual(res, [("unresolved-reference", self.SOURCES_DETAIL)] * 2)

    def test_dotdot_then_a_variable_matching_a_real_directory_renders_no_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._tree(root)
            for pdp in ("../$(SRCROOT)", "../${SRCROOT}", "../$SRCROOT"):
                with self.subTest(pdp=pdp):
                    rows, res = self._run(root, self._doc(pdp))
                    self.assertEqual(rows, [])
                    self.assertEqual(res, [("unresolved-reference", self.SOURCES_DETAIL)] * 2)

    def test_control_a_plain_contained_project_dir_renders_its_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._tree(root)
            for pdp in (None, "", "."):
                with self.subTest(pdp=pdp):
                    rows, res = self._run(root, self._doc(pdp))
                    self.assertEqual(rows, ["ios/App/Main.swift", "ios/App/Other.swift"])
                    self.assertEqual(res, [])

    def test_control_an_absolute_project_dir_still_renders_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._tree(root)
            rows, res = self._run(root, self._doc("/Users/x/Elsewhere"))
        self.assertEqual(rows, [])
        self.assertIn(("path-escape",
                       "a project file reference escapes the checkout after path normalisation"), res)

    def test_a_synced_root_under_an_unresolved_project_dir_renders_unresolved_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._tree(root)
            for pdp in ("$(SRCROOT)/..", "${SRCROOT}/..", "$SRCROOT/.."):
                with self.subTest(pdp=pdp):
                    rows, res = self._run(root, self._doc(pdp, synced=["SR"]))
                    self.assertEqual(rows, [])
                    self.assertEqual(sorted(res), sorted(
                        [("unresolved-reference", self.SOURCES_DETAIL)] * 2
                        + [("unresolved-reference", self.SYNCED_DETAIL)]))

    def test_a_dangling_or_mistyped_synced_root_renders_unresolved_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._tree(root)
            rows, res = self._run(root, self._doc(None, synced=["SR", "NOPE", "G"]))
        self.assertEqual(rows, ["ios/App/Main.swift", "ios/App/Other.swift", "ios/Synced/S.swift"])
        self.assertEqual(res, [("unresolved-reference", self.SYNCED_DETAIL)] * 2)

    def test_control_a_resolved_synced_root_renders_its_row_and_no_residual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._tree(root)
            rows, res = self._run(root, self._doc(None, synced=["SR"]))
        self.assertEqual(rows, ["ios/App/Main.swift", "ios/App/Other.swift", "ios/Synced/S.swift"])
        self.assertEqual(res, [])


class ResidualNamesAreCellEscapedTests(unittest.TestCase):
    """ADR-0130 clause 14: every residual line names fields read from the
    checkout, escaped. A name holding a backtick and a pipe renders in its
    `_cell` form inside the detail, never raw, so it can neither open a code
    span nor split a table row."""

    HOSTILE = "x`|y"

    def _bullet(self, residual):
        from crux.arch.packs import swift
        klass, path, span, detail = residual
        return swift._residual_line(klass, path, span, detail)

    def test_unmapped_target_name_is_cell_escaped(self):
        from crux.arch.core import _cell
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["UNK"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=[])
        objects["UNK"] = _obj("PBXNativeTarget", name=self.HOSTILE,
                              productType="com.apple.product-type.watch2-app")
        doc = _pbx(objects, "PROJ")
        _rows, _by_id, residuals = sx.target_rows(doc, "X.xcodeproj/project.pbxproj", "X.xcodeproj")
        want = "target '%s' names an unmapped product type" % _cell(self.HOSTILE)
        self.assertEqual([r[3] for r in residuals], [want])
        self.assertTrue(self._bullet(residuals[0]).endswith(" — " + want))
        self.assertNotIn("`|", self._bullet(residuals[0]))

    def test_conditioned_setting_key_is_cell_escaped(self):
        from crux.arch.core import _cell
        key = "A" + self.HOSTILE + "[sdk=iphoneos*]"
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=[])
        objects["CFG"] = _obj("XCBuildConfiguration", name="Debug", buildSettings={key: "1"})
        doc = _pbx(objects, "PROJ")
        res = sx.build_setting_residuals(doc, "App.xcodeproj/project.pbxproj")
        want = "build setting '%s' is conditioned and never applied" % _cell(key)
        self.assertEqual([r[3] for r in res], [want])

    def test_synced_root_path_is_cell_escaped(self):
        from crux.arch.core import _cell
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SYNC"])
        objects["SYNC"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>",
                               path=self.HOSTILE, exceptions=["MISSING"])
        objects["T"] = _obj("PBXNativeTarget", name="App",
                            productType="com.apple.product-type.application",
                            fileSystemSynchronizedGroups=["SYNC"])
        doc = _pbx(objects, "PROJ")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            _m, res = sx.synced_memberships(doc, root, sx.descend(doc, ()), "p", by_id, "X.xcodeproj")
        want = "a dangling exception set on %s" % _cell(self.HOSTILE)
        self.assertIn(want, [r[3] for r in res])


class SyncedGroupsFieldTypeTests(unittest.TestCase):
    """ADR-0130 clause 2: `fileSystemSynchronizedGroups` is a list of lookups.
    A value of any other type names no root. It renders the one
    `unsupported-project-form` line ADR-0130 clause 14 gives each of the
    eleven list fields, at the field's own line (a reclassification from
    `unresolved-reference`; a non-string list ITEM keeps
    `unresolved-reference`). It is never iterated character by character,
    and it never owns a root by substring match."""

    SYNCED_DETAIL = "a target's fileSystemSynchronizedGroups field is not a list and is not read"
    SYNCED_CLASS = "unsupported-project-form"

    def _doc(self, synced):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SR"])
        objects["SR"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>",
                             path="Synced")
        objects["T"] = _obj("PBXNativeTarget", name="App",
                            productType="com.apple.product-type.application",
                            fileSystemSynchronizedGroups=synced)
        return _pbx(objects, "PROJ")

    def _run(self, root, doc):
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        m, res = sx.synced_memberships(doc, root, sx.descend(doc, ()), "p", by_id, "X.xcodeproj")
        return sorted(r["file"] for r in m), [(r[0], r[3]) for r in res]

    def test_a_string_naming_a_real_root_owns_nothing_and_renders_one_residual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _mkfile(root / "Synced" / "S.swift")
            doc = self._doc("SR")
            # The fixture reaches the branch: the reader hands the field over as a string.
            self.assertEqual(doc.objects["T"]["fileSystemSynchronizedGroups"], "SR")
            rows, res = self._run(root, doc)
        self.assertEqual(rows, [])
        self.assertEqual(res, [(self.SYNCED_CLASS, self.SYNCED_DETAIL)])

    def test_a_dictionary_or_empty_string_is_one_type_error_too(self):
        # Type decides, not truthiness: an empty non-list value is still not a list.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _mkfile(root / "Synced" / "S.swift")
            for synced in ({"SR": "SR"}, {}, ""):
                with self.subTest(synced=synced):
                    rows, res = self._run(root, self._doc(synced))
                    self.assertEqual(rows, [])
                    self.assertEqual(res, [(self.SYNCED_CLASS, self.SYNCED_DETAIL)])

    def test_control_a_list_naming_the_root_owns_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _mkfile(root / "Synced" / "S.swift")
            rows, res = self._run(root, self._doc(["SR"]))
        self.assertEqual(rows, ["Synced/S.swift"])
        self.assertEqual(res, [])

    def test_a_long_string_value_reads_in_linear_time(self):
        """A 25,000-character value took about 18 s when each character was a
        lookup that rescanned the whole field for its line; linear, it takes
        milliseconds."""
        reads = []

        def seconds(size):
            doc = self._doc("A" * size)
            _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            with tempfile.TemporaryDirectory() as tmp:
                started = _timing.clock()
                m, res = sx.synced_memberships(doc, Path(tmp), d, "p", by_id, "X.xcodeproj")
                elapsed = _timing.clock() - started
            reads.append((m, [(r[0], r[3]) for r in res]))
            return elapsed

        _timing.assert_grows_linearly(self, seconds, 25_000, "a synced-groups string value of that many characters")
        for m, res in reads:
            self.assertEqual(m, ())
            self.assertEqual(res, [(self.SYNCED_CLASS, self.SYNCED_DETAIL)])


class SyncedLookupHandledSkipTests(unittest.TestCase):
    """ADR-0130 clause 2: a `fileSystemSynchronizedGroups` id that descent
    already renders elsewhere, or deliberately renders nothing for, adds no
    "did not resolve" line of its own. The three skipped kinds are a second
    reach (`descent.unresolved_ids`), an escape (`descent.escape_ids`) and a
    `BUILT_PRODUCTS_DIR` root (`descent.none_ids`). An id under a build-setting
    reference (`descent.unresolved_var_ids`) is not skipped: it renders."""

    DETAIL = "target 'App' names a folder-synced root that descent did not resolve"

    def _lookups(self, synced):
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        # `TWICE` is listed twice, so descent's second reach records it.
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>",
                               children=["TWICE", "TWICE", "ESC", "PROD", "VAR"])
        objects["TWICE"] = _obj("PBXGroup", sourceTree="<group>", path="Twice")
        objects["ESC"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>",
                              path="../../Outside")
        objects["PROD"] = _obj("PBXFileSystemSynchronizedRootGroup",
                               sourceTree="BUILT_PRODUCTS_DIR", path="Built")
        objects["VAR"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>",
                              path="$(SRC)/Synced")
        objects["T"] = _obj("PBXNativeTarget", name="App",
                            productType="com.apple.product-type.application",
                            fileSystemSynchronizedGroups=synced)
        doc = _pbx(objects, "PROJ")
        descent = sx.descend(doc, ())
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        with tempfile.TemporaryDirectory() as tmp:
            _m, res = sx.synced_memberships(doc, Path(tmp), descent, "p", by_id, "X.xcodeproj")
        return descent, [r for r in res if r[3] == self.DETAIL]

    def test_the_fixture_reaches_each_descent_set(self):
        descent, _ = self._lookups([])
        self.assertIn("TWICE", descent.unresolved_ids)
        self.assertIn("ESC", descent.escape_ids)
        self.assertIn("PROD", descent.none_ids)
        self.assertIn("VAR", descent.unresolved_var_ids)

    def test_an_id_descent_already_handles_adds_no_lookup_line(self):
        for synced_id in ("TWICE", "ESC", "PROD"):
            with self.subTest(synced_id=synced_id):
                _descent, lines = self._lookups([synced_id])
                self.assertEqual(lines, [])

    def test_control_an_unresolved_var_id_renders_its_lookup_line(self):
        # Positive control: the same lookup path renders a line for an id no
        # descent set above holds, so the skip cases are not vacuous.
        _descent, lines = self._lookups(["VAR"])
        self.assertEqual([(r[0], r[3]) for r in lines], [("unresolved-reference", self.DETAIL)])


class ListItemLineLinearTimeTests(unittest.TestCase):
    """ADR-0130 clause 2: every residual a list item renders names that
    item's own line. Finding the line is linear in the list: a lookup that
    rescanned the list for each item made a 30,000-item list take about 10 s
    (40,000 items took 96 s in review), so a hostile checkout could stall
    `derive-arch --dry-run`."""

    P = 30_000

    def test_a_long_dangling_synced_groups_list_renders_each_line_in_linear_time(self):

        def seconds(size):
            ids = ["D%05d" % i for i in range(size)]
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=[])
            objects["T"] = _obj("PBXNativeTarget", name="App",
                                productType="com.apple.product-type.application",
                                fileSystemSynchronizedGroups=ids)
            doc = _pbx(objects, "PROJ")
            _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
            d = sx.descend(doc, ())
            with tempfile.TemporaryDirectory() as tmp:
                started = _timing.clock()
                _m, res = sx.synced_memberships(doc, Path(tmp), d, "p", by_id, "X.xcodeproj")
                elapsed = _timing.clock() - started
            self.assertEqual([r[2] for r in res], doc.list_item_lines[("T", "fileSystemSynchronizedGroups")])
            return elapsed

        _timing.assert_grows_linearly(self, seconds, self.P, "dangling synced-group lookups")

    def test_a_long_dangling_children_list_renders_each_line_in_linear_time(self):

        def seconds(size):
            ids = ["D%05d" % i for i in range(size)]
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN")
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=ids)
            doc = _pbx(objects, "PROJ")
            d = sx.descend(doc, ())
            started = _timing.clock()
            res = sx.descent_unresolved_residuals(doc, d, "p")
            elapsed = _timing.clock() - started
            self.assertEqual(sorted(r[2] for r in res), doc.list_item_lines[("MAIN", "children")])
            return elapsed

        _timing.assert_grows_linearly(self, seconds, self.P, "dangling children")

    def test_every_id_list_field_holding_a_long_string_reads_in_linear_time(self):
        """Every id-list field the reader iterates, each holding a
        15,000-character string: `targets`, `packageReferences`, `children`,
        `explicitFolders`, `files`, `buildPhases`, `dependencies`,
        `fileSystemSynchronizedGroups` and `packageProductDependencies`.
        A string's characters were read as ids, and `children` and
        `packageProductDependencies` rescanned the field for each
        character's line: about 13 s. `membershipExceptions` holds paths,
        not ids, and indexes its lines directly, so it is not part of this
        bound."""
        from crux.arch.packs import swift_xcode_products as sxp
        members = []

        def seconds(size):
            long = "A" * size
            objects = {}
            objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T", "T2", "T3"],
                                   packageReferences=long)
            objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SR", "SUB"])
            objects["SUB"] = _obj("PBXGroup", sourceTree="<group>", path="Sub", children=long)
            objects["SR"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>",
                                 path="Synced", explicitFolders=long)
            objects["SP"] = _obj("PBXSourcesBuildPhase", files=long)
            objects["T"] = _obj("PBXNativeTarget", name="App", productType="com.apple.product-type.application",
                                fileSystemSynchronizedGroups=["SR"], buildPhases=["SP"], dependencies=long,
                                packageProductDependencies=long)
            objects["T2"] = _obj("PBXNativeTarget", name="App2", productType="com.apple.product-type.application",
                                 fileSystemSynchronizedGroups=long, buildPhases=long)
            objects["PROJ2"] = _obj("PBXProject", mainGroup="MAIN", targets=long)
            doc = _pbx(objects, "PROJ")
            doc2 = _pbx(objects, "PROJ2")
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _mkfile(root / "Synced" / "S.swift")
                started = _timing.clock()
                _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
                sx.target_rows(doc2, "p", "X.xcodeproj")
                d = sx.descend(doc, ())
                sx.descent_unresolved_residuals(doc, d, "p")
                sx.target_dependencies(doc, "X.xcodeproj", by_id, "p")
                m, _ = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
                sx.classic_memberships(doc, root, d, "p", by_id, "X.xcodeproj")
                p = SimpleNamespace(bundle_rel="X.xcodeproj", pbxproj_rel="X.xcodeproj/project.pbxproj",
                                    doc=doc, descent=d, targets_by_id=by_id, target_rows=_rows)
                sxp.resolve_product_dependencies(root, [p], [])
                elapsed = _timing.clock() - started
            members.append([r["file"] for r in m])
            return elapsed

        _timing.assert_grows_linearly(self, seconds, 15_000, "every id-list field as a string of that many characters")
        for files in members:
            self.assertEqual(files, ["Synced/S.swift"])

    def test_a_repeated_id_names_its_first_line_every_time(self):
        """The line a repeated id names is its FIRST occurrence's, as the
        rescanning lookup returned: the index keeps the first line, never the
        last. A repeated id's line is the same line, so the reader keeps it
        once (the render-key dedupe; ADR-0129 clause 7); the second occurrence's
        own line never appears."""
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=[])
        objects["T"] = _obj("PBXNativeTarget", name="App",
                            productType="com.apple.product-type.application",
                            fileSystemSynchronizedGroups=["X", "Y", "X", {"k": ["v"]}, {"k": ["v"]}])
        doc = _pbx(objects, "PROJ")
        lines = doc.list_item_lines[("T", "fileSystemSynchronizedGroups")]
        self.assertEqual(len(set(lines)), 5, lines)
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        with tempfile.TemporaryDirectory() as tmp:
            _m, res = sx.synced_memberships(doc, Path(tmp), sx.descend(doc, ()), "p", by_id, "X.xcodeproj")
        self.assertEqual([r[2] for r in res], [lines[0], lines[1], lines[3]])


_APP_TYPE = "com.apple.product-type.application"


def _q9_objects():
    """A project whose single-letter ids let a string's characters name real
    objects: `targets = "T"` names the target `T`, `buildPhases = "S"` the
    Sources phase `S`, and so on. Every list field holds a list here; each
    `ListFieldTypeTests` case replaces one."""
    o = {}
    o["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"], packageReferences=["R"])
    o["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SR", "G"])
    o["G"] = _obj("PBXGroup", sourceTree="<group>", path="Classic", children=["F"])
    o["F"] = _obj("PBXFileReference", sourceTree="<group>", path="Main.swift")
    o["B"] = _obj("PBXBuildFile", fileRef="F")
    o["S"] = _obj("PBXSourcesBuildPhase", files=["B"])
    o["SR"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Synced",
                   exceptions=["E"], explicitFolders=["D"])
    o["E"] = _obj("PBXFileSystemSynchronizedBuildFileExceptionSet", target="T",
                  membershipExceptions=["Ex.swift"])
    o["P"] = _obj("XCSwiftPackageProductDependency", productName="Kit", package="R")
    o["R"] = _obj("XCRemoteSwiftPackageReference", repositoryURL="https://example.com/kit.git",
                  requirement={"kind": "exactVersion", "version": "1.0.0"})
    o["T"] = _obj("PBXNativeTarget", name="App", productType=_APP_TYPE,
                  fileSystemSynchronizedGroups=["SR"], buildPhases=["S"], dependencies=[],
                  packageProductDependencies=["P"])
    return o


def _q9_tree(root):
    for rel in ("Classic/Main.swift", "Synced/Own.swift", "Synced/Ex.swift", "Synced/D/a.swift"):
        _mkfile(root / rel)


def _q9_derive(root, objects):
    """`read_projects` over one bundle `X.xcodeproj` holding `objects`, and
    the document parsed from the same text, for its line indexes."""
    doc_map = {"archiveVersion": "1", "objectVersion": "56", "rootObject": "PROJ", "objects": objects}
    text = "// !$*UTF8*$!\n" + _serialize(doc_map) + "\n"
    bundle = root / "X.xcodeproj"
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "project.pbxproj").write_text(text)
    doc = spx.read_pbxproj(text.encode("utf-8"))
    assert isinstance(doc, spx.PbxprojDocument), doc
    reads = SimpleNamespace(bundles=[("X.xcodeproj", True, True)], refusals={},
                            files={"X.xcodeproj/project.pbxproj": text.encode("utf-8")})
    return sx.read_projects(root, reads, []), doc


def _q9_rows(result):
    return sorted((m["file"], m["target"], m["route"]) for m in result["memberships"])


class ListFieldTypeTests(unittest.TestCase):
    """ADR-0130 clauses 2 and 14: each of the eleven list fields
    the reader reads, present with a value that is not a list, renders
    exactly one `unsupported-project-form` at the field's own line with a
    fixed detail. Nothing is read from the value: a string's characters are
    not ids or paths, and a dictionary's keys are not ids. Type decides,
    never truthiness, so `""` and `{}` render the line too; `()` and an
    absent key render nothing. The project is never `project-unreadable`."""

    # field -> (object holding it, a value whose characters name real objects)
    FIELDS = {
        "targets": ("PROJ", "T"),
        "packageReferences": ("PROJ", "R"),
        "children": ("G", "F"),
        "dependencies": ("T", "abc"),
        "buildPhases": ("T", "S"),
        "fileSystemSynchronizedGroups": ("T", "SR"),
        "packageProductDependencies": ("T", "P"),
        "files": ("S", "B"),
        "exceptions": ("SR", "E"),
        "explicitFolders": ("SR", "D"),
        "membershipExceptions": ("E", "x."),
    }

    DETAILS = {
        "targets": "the project's targets field is not a list and is not read",
        "packageReferences": "the project's packageReferences field is not a list and is not read",
        "children": "a group's children field is not a list and is not descended",
        "dependencies": "a target's dependencies field is not a list and is not read",
        "buildPhases": "a target's buildPhases field is not a list and is not read",
        "fileSystemSynchronizedGroups": "a target's fileSystemSynchronizedGroups field is not a list and is not read",
        "packageProductDependencies": "a target's packageProductDependencies field is not a list and is not read",
        "files": "a build phase's files field is not a list and is not read",
        "exceptions": "a folder-synced root's exceptions field is not a list and is not applied",
        "explicitFolders": "a folder-synced root's explicitFolders field is not a list and is not applied",
        "membershipExceptions": "an exception set's membershipExceptions field is not a list and is not applied",
    }

    BASELINE_ROWS = [
        ("Classic/Main.swift", "App", "classic Sources build phase"),
        ("Synced/Ex.swift", "App", "excluded by an exception set"),
        ("Synced/Own.swift", "App", "folder-synced root Synced"),
    ]

    def _derive(self, field, value):
        objects = _q9_objects()
        obj_id, _ = self.FIELDS[field]
        if value is _ABSENT:
            del objects[obj_id][field]
        else:
            objects[obj_id][field] = value
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _q9_tree(root)
            return _q9_derive(root, objects)

    def test_the_constants_name_every_field_once(self):
        self.assertEqual(sx.NON_LIST_FIELD_DETAILS, self.DETAILS)

    def test_control_every_field_as_a_list_reads_as_before(self):
        result, _doc = self._derive("targets", ["T"])
        self.assertEqual([t["name"] for t in result["targets"]], ["App"])
        self.assertEqual(_q9_rows(result), self.BASELINE_ROWS)
        self.assertEqual([(d["location"]) for d in result["dependencies"]], ["https://example.com/kit.git"])
        self.assertEqual([p["product"] for p in result["product_deps"]], ["Kit"])
        self.assertEqual(result["residuals"], ())

    def test_a_value_of_another_type_renders_one_line_and_is_not_read(self):
        for field, (obj_id, colliding) in self.FIELDS.items():
            for value in (colliding, {colliding: "x"}, "", {}):
                with self.subTest(field=field, value=value):
                    result, doc = self._derive(field, value)
                    self.assertEqual(doc.objects[obj_id][field], value)
                    line = doc.value_lines[(obj_id, field)]
                    mine = [r for r in result["residuals"] if r[3] == self.DETAILS[field]]
                    self.assertEqual(mine, [("unsupported-project-form", "X.xcodeproj/project.pbxproj",
                                             [(line, line)], self.DETAILS[field])])
                    self.assertNotIn("project-unreadable", [r[0] for r in result["residuals"]])
                    self._check_nothing_read(field, result)

    def _check_nothing_read(self, field, result):
        rows = _q9_rows(result)
        names = [t["name"] for t in result["targets"]]
        details = [r[3] for r in result["residuals"]]
        if field == "targets":
            self.assertEqual((names, rows), ([], []))
            return
        self.assertEqual(names, ["App"])
        if field == "packageReferences":
            self.assertEqual(result["dependencies"], ())
            self.assertEqual([p["product"] for p in result["product_deps"]], ["Kit"])
        elif field == "packageProductDependencies":
            self.assertEqual(result["product_deps"], ())
            self.assertFalse([d for d in details if "package product dependency" in d])
        elif field == "dependencies":
            self.assertFalse([d for d in details if "dependency reference" in d or "does not resolve" in d])
        elif field == "children":
            self.assertNotIn(("Classic/Main.swift", "App", "classic Sources build phase"), rows)
            self.assertFalse([d for d in details if "by descent" in d])
        elif field in ("buildPhases", "files"):
            self.assertEqual([r for r in rows if r[2] == "classic Sources build phase"], [])
            self.assertFalse([d for d in details if "dangling build file" in d])
        elif field == "fileSystemSynchronizedGroups":
            # `App` owns no root, so it has no default row. Its own exception
            # set still names `Ex.swift`, which for a non-owner is an add
            # (ADR-0130 clause 9): that row is read from the set, not the field.
            self.assertEqual([r for r in rows if r[0].startswith("Synced/")],
                             [("Synced/Ex.swift", "App", "added by an exception set")])
            self.assertFalse([d for d in details if "folder-synced root that descent" in d])
        elif field in ("exceptions", "membershipExceptions"):
            # The default rows stand: nothing is excluded or added.
            self.assertEqual([r for r in rows if r[0].startswith("Synced/")],
                             [("Synced/Ex.swift", "App", "folder-synced root Synced"),
                              ("Synced/Own.swift", "App", "folder-synced root Synced")])
            self.assertFalse([d for d in details if "dangling exception set" in d])
        elif field == "explicitFolders":
            # No folder is withheld: `Synced/D/a.swift` is a default row.
            self.assertIn(("Synced/D/a.swift", "App", "folder-synced root Synced"), rows)
        if field != "packageReferences":
            self.assertEqual([d["location"] for d in result["dependencies"]], ["https://example.com/kit.git"])

    def test_an_empty_list_or_an_absent_key_renders_nothing(self):
        for field in self.FIELDS:
            for value in ([], _ABSENT):
                with self.subTest(field=field, value=value):
                    result, _doc = self._derive(field, value)
                    self.assertEqual([r for r in result["residuals"] if r[3] == self.DETAILS[field]], [])
                    self.assertNotIn("project-unreadable", [r[0] for r in result["residuals"]])

    def test_a_pruned_root_with_a_non_list_exceptions_names_no_exception_set(self):
        """A root in a directory every Swift walk skips renders its prune
        line only when a target owns it or it carries exception sets. A
        string `exceptions` carries none: it renders its own line, and the
        prune line does not follow from its truthiness."""
        objects = _q9_objects()
        objects["SR"]["path"] = "Pods"
        objects["T"]["fileSystemSynchronizedGroups"] = []
        objects["SR"]["exceptions"] = "E"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _q9_tree(root)
            result, _doc = _q9_derive(root, objects)
        details = [r[3] for r in result["residuals"]]
        from crux.arch.packs import swift_prune
        self.assertNotIn(swift_prune.SYNCED_ROOT_DETAIL, details)
        self.assertEqual(details.count(self.DETAILS["exceptions"]), 1)

    def test_control_a_pruned_root_with_a_listed_exception_set_renders_its_prune_line(self):
        objects = _q9_objects()
        objects["SR"]["path"] = "Pods"
        objects["T"]["fileSystemSynchronizedGroups"] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _q9_tree(root)
            result, _doc = _q9_derive(root, objects)
        from crux.arch.packs import swift_prune
        self.assertIn(swift_prune.SYNCED_ROOT_DETAIL, [r[3] for r in result["residuals"]])

    def test_one_line_per_object_and_field_when_two_readers_reach_it(self):
        """A build phase two targets list, and an exception set two roots
        list, are each reached twice; each non-list field still renders
        once."""
        objects = _q9_objects()
        objects["PROJ"]["targets"] = ["T", "U"]
        objects["U"] = _obj("PBXNativeTarget", name="Two", productType=_APP_TYPE,
                            fileSystemSynchronizedGroups=["SR2"], buildPhases=["S"])
        objects["MAIN"]["children"] = ["SR", "SR2", "G"]
        objects["SR2"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Synced2",
                              exceptions=["E"])
        objects["S"]["files"] = "B"
        objects["E"]["membershipExceptions"] = "x."
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _q9_tree(root)
            _mkfile(root / "Synced2" / "Two.swift")
            result, _doc = _q9_derive(root, objects)
        details = [r[3] for r in result["residuals"]]
        self.assertEqual(details.count(self.DETAILS["files"]), 1)
        self.assertEqual(details.count(self.DETAILS["membershipExceptions"]), 1)
        self.assertIn(("Synced2/Two.swift", "Two", "folder-synced root Synced2"), _q9_rows(result))


_ABSENT = object()


class ListItemTypeTests(unittest.TestCase):
    """ADR-0130 clauses 2 and 14, list items: an item inside a list
    that is not a string renders one line of its own at the item's line,
    applies nothing, and the project continues. In an id list it renders
    `unresolved-reference`; in a path list, `unsupported-project-form`.
    Each of these items raised `TypeError` or `AttributeError` and collapsed
    the whole project to one `project-unreadable`/`malformed` line."""

    def _derive(self, objects, extra_files=()):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _q9_tree(root)
            for rel in extra_files:
                _mkfile(root / rel)
            return _q9_derive(root, objects)

    def _check(self, obj_id, field, item_index, klass, detail, want_rows=None):
        for bad in (["X"], {"a": "b"}):
            with self.subTest(field=field, bad=bad):
                objects = _q9_objects()
                objects[obj_id][field] = list(objects[obj_id][field]) + [bad]
                result, doc = self._derive(objects)
                line = doc.list_item_lines[(obj_id, field)][item_index]
                self.assertNotIn("project-unreadable", [r[0] for r in result["residuals"]])
                mine = [r for r in result["residuals"] if r[3] == detail]
                self.assertEqual(mine, [(klass, "X.xcodeproj/project.pbxproj", [(line, line)], detail)])
                self.assertEqual([t["name"] for t in result["targets"]], ["App"])
                self.assertEqual(_q9_rows(result), want_rows or ListFieldTypeTests.BASELINE_ROWS)

    def test_targets_item(self):
        self._check("PROJ", "targets", 1, "unresolved-reference",
                    "a project's targets entry is not an object id and is not read")

    def test_package_references_item(self):
        self._check("PROJ", "packageReferences", 1, "unresolved-reference",
                    "a project's packageReferences entry is not an object id and is not read")

    def test_children_item(self):
        self._check("G", "children", 1, "unresolved-reference",
                    "a children entry references an object reached a second time, "
                    "or not at all, by descent")

    def test_build_phases_item(self):
        self._check("T", "buildPhases", 1, "unresolved-reference",
                    "a target's buildPhases entry is not an object id and is not read")

    def test_files_item(self):
        self._check("S", "files", 1, "unresolved-reference", "a dangling build file in 'App's Sources phase")

    def test_exceptions_item(self):
        self._check("SR", "exceptions", 1, "unresolved-reference", "a dangling exception set on Synced")

    def test_explicit_folders_item(self):
        self._check("SR", "explicitFolders", 1, "unsupported-project-form",
                    "an explicitFolders entry is not a string; it is not applied")

    def test_membership_exceptions_item(self):
        self._check("E", "membershipExceptions", 1, "unsupported-project-form",
                    "an exception entry is not a string; it is not applied")

    def test_a_non_string_item_before_a_string_item_leaves_the_string_item_applied(self):
        """`( ( "Own.swift" ), "Ex.swift" )`: the nested item applies
        nothing, and the string after it still excludes its file at its own
        line."""
        objects = _q9_objects()
        objects["E"]["membershipExceptions"] = [["Own.swift"], "Ex.swift"]
        result, doc = self._derive(objects)
        lines = doc.list_item_lines[("E", "membershipExceptions")]
        self.assertEqual(len(lines), 2)
        rows = {(m["file"], m["route"]): m["loc"] for m in result["memberships"]}
        self.assertEqual(rows[("Synced/Ex.swift", "excluded by an exception set")], (lines[1], lines[1]))
        self.assertIn(("Synced/Own.swift", "folder-synced root Synced"), rows)

    def test_a_build_phase_exception_set_item(self):
        objects = _q9_objects()
        objects["SR"]["exceptions"] = ["E", "BP"]
        objects["BP"] = _obj("PBXFileSystemSynchronizedGroupBuildPhaseMembershipExceptionSet",
                             buildPhase="S", membershipExceptions=[{"a": "Own.swift"}, "Ex.swift"])
        result, doc = self._derive(objects)
        line = doc.list_item_lines[("BP", "membershipExceptions")][0]
        detail = "an exception entry is not a string; it is not applied"
        self.assertEqual([r for r in result["residuals"] if r[3] == detail],
                         [("unsupported-project-form", "X.xcodeproj/project.pbxproj", [(line, line)], detail)])
        self.assertNotIn("project-unreadable", [r[0] for r in result["residuals"]])
        # The string entry is still withheld; the dictionary withholds nothing.
        self.assertIn(("Synced/Own.swift", "App", "folder-synced root Synced"), _q9_rows(result))
        self.assertNotIn(("Synced/Ex.swift", "App", "folder-synced root Synced"), _q9_rows(result))

    def test_a_variant_group_child_item(self):
        objects = _q9_objects()
        objects["G"]["children"] = ["V"]
        objects["V"] = _obj("PBXVariantGroup", sourceTree="<group>", children=["F", {"a": "b"}])
        objects["B"]["fileRef"] = "V"
        result, doc = self._derive(objects)
        line = doc.list_item_lines[("V", "children")][1]
        self.assertNotIn("project-unreadable", [r[0] for r in result["residuals"]])
        self.assertIn(("Classic/Main.swift", "App", "classic Sources build phase"), _q9_rows(result))
        self.assertEqual([r[2] for r in result["residuals"] if "by descent" in r[3]], [[(line, line)]])


class BuildPhaseOwnerListTests(unittest.TestCase):
    """ADR-0130 clauses 9 and 14: a build-phase membership exception set names its
    target through `buildPhase`, matched as a whole element of a target's
    `buildPhases` LIST. A string `buildPhases` made `"S" in "SX"` a substring
    match, so the target owned a phase it never listed."""

    def test_a_string_build_phases_owns_no_phase(self):
        objects = _q9_objects()
        objects["PROJ"]["targets"] = ["T", "U"]
        objects["T"]["buildPhases"] = "SX"
        objects["U"] = _obj("PBXNativeTarget", name="Two", productType=_APP_TYPE,
                            fileSystemSynchronizedGroups=["SR"], buildPhases=[])
        objects["SR"]["exceptions"] = ["BP"]
        objects["BP"] = _obj("PBXFileSystemSynchronizedGroupBuildPhaseMembershipExceptionSet",
                             buildPhase="S", membershipExceptions=["Own.swift"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _q9_tree(root)
            result, _doc = _q9_derive(root, objects)
        details = [r[3] for r in result["residuals"]]
        # No target lists `S`, so the set's rows are withheld from every
        # owner, and the dangling `buildPhase` renders its own line.
        self.assertIn("a build-phase membership exception set on Synced names a "
                      "buildPhase that resolves to no owning target", details)
        rows = _q9_rows(result)
        self.assertNotIn(("Synced/Own.swift", "App", "folder-synced root Synced"), rows)
        self.assertNotIn(("Synced/Own.swift", "Two", "folder-synced root Synced"), rows)
        self.assertEqual(details.count(ListFieldTypeTests.DETAILS["buildPhases"]), 1)

    def test_control_a_listed_phase_owns_it(self):
        objects = _q9_objects()
        objects["PROJ"]["targets"] = ["T", "U"]
        objects["U"] = _obj("PBXNativeTarget", name="Two", productType=_APP_TYPE,
                            fileSystemSynchronizedGroups=["SR"], buildPhases=[])
        objects["SR"]["exceptions"] = ["BP"]
        objects["BP"] = _obj("PBXFileSystemSynchronizedGroupBuildPhaseMembershipExceptionSet",
                             buildPhase="S", membershipExceptions=["Own.swift"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _q9_tree(root)
            result, _doc = _q9_derive(root, objects)
        rows = _q9_rows(result)
        self.assertNotIn(("Synced/Own.swift", "App", "folder-synced root Synced"), rows)
        self.assertIn(("Synced/Own.swift", "Two", "folder-synced root Synced"), rows)


def _classic_objects(group_path, names):
    """One target whose Sources phase names `names` under one group at
    `group_path`."""
    objects = {}
    objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
    objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["G"])
    objects["G"] = _obj("PBXGroup", sourceTree="<group>", path=group_path,
                        children=["F%d" % i for i in range(len(names))])
    for i, name in enumerate(names):
        objects["F%d" % i] = _obj("PBXFileReference", sourceTree="<group>", path=name)
        objects["B%d" % i] = _obj("PBXBuildFile", fileRef="F%d" % i)
    objects["SP"] = _obj("PBXSourcesBuildPhase", files=["B%d" % i for i in range(len(names))])
    objects["T"] = _obj("PBXNativeTarget", name="App", productType=_APP_TYPE, buildPhases=["SP"])
    return objects


class DirectoryVerdictMemoTests(unittest.TestCase):
    """ADR-0130 clauses 2 and 3: one `read_projects`
    call holds one `DirectoryVerdicts` memo. With it, each directory above
    the members is listed once per call, and so is the directory that holds
    the members (ADR-0129 clause 2): P members under a K-deep directory
    make K + 1 listings of about P + K entries. Without the memo,
    `listed_names` listed every prefix again for every member, P times K:
    200 members under a 400-deep directory took 9.6 s. Listing the leaf once
    per member was P listings of P entries each. Nothing survives the call:
    a second call reads the filesystem as it is then."""

    P, K = 200, 400

    def test_directory_listings_grow_with_members_plus_depth(self):
        """The memo's work is counted, not timed: the reader lists each of
        the K directories once and the leaf once, and the entries those
        listings yield grow with P + K. With no memo the listings grew with
        P times K (80,200 here); with the leaf listed per member they were
        K + P listings yielding about P squared entries (about 20,000 here).
        A wall-clock bound failed under a loaded gate (2.5 s against 2.0 s),
        so no time is asserted. Each member's containment check still
        resolves its path (`_safe_contained`), which `lstat`s every
        component; those `lstat` calls stay live for every reference
        (ADR-0130 clause 3) and are not counted.

        The work bound charges each of a member's four path checks
        1 + K(K + 1)/2 (ruling C), 320,804 units at K = 400, so the real
        bound stops this tree after about 13 members. This test counts the
        memo's listings, not the bound, so it reads the tree under a bound
        of 2^30; the last assertion shows the real bound stopping it."""
        chain = "/".join(["d"] * self.K)
        names = ["f%d.swift" % i for i in range(self.P)]
        listings = []
        entries = [0]
        real_scandir = os.scandir

        class Counted:
            def __init__(self, it):
                self.it = it

            def __iter__(self):
                return self

            def __next__(self):
                entry = next(self.it)
                entries[0] += 1
                return entry

            def __enter__(self):
                self.it.__enter__()
                return self

            def __exit__(self, *exc):
                return self.it.__exit__(*exc)

            def close(self):
                self.it.close()

        def scandir(*args, **kwargs):
            listings.append(os.fspath(args[0] if args else kwargs.get("path")))
            return Counted(real_scandir(*args, **kwargs))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            os.makedirs(root / chain)
            for name in names:
                (root / chain / name).write_text("x")
            leaf = str(root / chain)
            with mock.patch("os.scandir", scandir), mock.patch("crux.arch.packs.swift_xcinputs.MAX_WORK_UNITS", 2 ** 30):
                result, _doc = _q9_derive(root, _classic_objects(chain, names))
            bounded, _doc = _q9_derive(root, _classic_objects(chain, names))
        self.assertEqual(len(result["memberships"]), self.P)
        self.assertEqual(result["residuals"], ())
        # Each of the K prefixes is listed at least once, so the wrapper saw
        # the listings it counts.
        self.assertGreaterEqual(len(listings), self.K)
        self.assertEqual(listings.count(leaf), 1,
                         f"the directory holding {self.P} members was listed {listings.count(leaf)} times")
        self.assertLessEqual(len(listings), self.K + 2,
                             f"{self.P} members under a {self.K}-deep directory made "
                             f"{len(listings)} directory listings")
        self.assertLessEqual(entries[0], 2 * (self.P + self.K),
                             f"{self.P} members under a {self.K}-deep directory iterated "
                             f"{entries[0]} directory entries")
        # At the real bound the same tree stops part-way, renders the one
        # work line, and keeps the members read before it.
        work = [r for r in bounded["residuals"] if "per-concern work bound" in r[3]]
        self.assertEqual(len(work), 1)
        self.assertLess(len(bounded["memberships"]), self.P)
        self.assertGreater(len(bounded["memberships"]), 0)

    def _two_reads(self, change):
        """Read, apply `change` to the tree, read again. Returns the member
        files of both reads."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _mkfile(root / "Src" / "A.swift")
            objects = _classic_objects("Src", ["A.swift"])
            first, _doc = _q9_derive(root, objects)
            change(root)
            second, _doc = _q9_derive(root, objects)
        return ([m["file"] for m in first["memberships"]], [m["file"] for m in second["memberships"]])

    @staticmethod
    def _recase(root):
        (root / "Src").rename(root / "tmp-name")
        (root / "tmp-name").rename(root / "src")

    def _swap_for_symlink(self, root):
        (root / "Src").rename(root / "Real")
        try:
            os.symlink("Real", root / "Src", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("host refuses symlink creation")

    def test_a_second_read_sees_the_directory_as_it_is_then(self):
        for name, change in (("re-cased", self._recase), ("replaced by a symlink", self._swap_for_symlink)):
            with self.subTest(change=name):
                self.assertEqual(self._two_reads(change), (["Src/A.swift"], []))

    def test_positive_control_a_memo_that_outlives_the_call_keeps_the_first_state(self):
        """The test above is not vacuous: with one memo shared by both calls
        (a module-scope memo), the second read still renders the member a
        symlink now stands in for."""
        from crux.arch.packs import swift_xcinputs
        shared = {}

        # The memo now carries the call's work budget (`MAX_WORK_UNITS`); the
        # shared memo keeps the first call's.
        def one_memo(root, *budget):
            if "memo" not in shared:
                shared["memo"] = swift_xcinputs.DirectoryVerdicts(root, *budget)
            return shared["memo"]

        with mock.patch.object(sx, "DirectoryVerdicts", one_memo):
            self.assertEqual(self._two_reads(self._swap_for_symlink), (["Src/A.swift"], ["Src/A.swift"]))


# ── ADR-0130 clauses 2 and 14: type-confused scalar and dictionary fields ──
#
# A value the OpenStep grammar admits wherever a string can sit -- a list or
# a dictionary, empty or not -- in a field the reader reads as an object id,
# a dictionary or a display string. Each shape either collapsed the project
# to `project-unreadable`/`malformed`, raised out of `read_projects` (so the
# deriver exited 2), invented a row or a condition from a string's
# characters, or rendered nothing where a line was due.

from crux.arch.packs import swift_xcode_products as sxp  # noqa: E402
from crux.arch.packs.swift_xcinputs import UNRESOLVED_DIR as _UNRESOLVED_DIR  # noqa: E402

_T4_PATH = "X.xcodeproj/project.pbxproj"
_T4_SLOT = "@@T4SLOT@@"
_T4_DANGLING = "ZZDANGLING"
_TOOL_TYPE = "com.apple.product-type.tool"


def _t4_inline(value):
    """`value` as one line of OpenStep text, so a document holding it keeps
    every later line where a one-line string would put it."""
    if isinstance(value, list):
        return "(" + ", ".join(_t4_inline(v) for v in value) + ")"
    if isinstance(value, dict):
        return "{" + " ".join("%s = %s;" % (_serialize_key(k), _t4_inline(v)) for k, v in value.items()) + "}"
    return '"' + str(value).replace('"', '\\"') + '"'


def _t4_objects():
    """The single-letter-id project (`_q9_objects`) plus a second target
    `Tool` that depends on `App` through a proxy, and one build
    configuration."""
    o = _q9_objects()
    o["PROJ"]["targets"] = ["T", "U"]
    o["U"] = _obj("PBXNativeTarget", name="Tool", productType=_TOOL_TYPE, dependencies=["TD"])
    o["TD"] = _obj("PBXTargetDependency", target="T", targetProxy="TP")
    o["TP"] = _obj("PBXContainerItemProxy", containerPortal="PROJ", remoteGlobalIDString="T")
    o["C"] = _obj("XCBuildConfiguration", name="Debug", buildSettings={"SWIFT_VERSION": "5.0"})
    return o


def _t4_derive(objects, slot=None, root_id="PROJ", object_version="56", extra_files=()):
    """`read_projects` over one bundle `X.xcodeproj` holding `objects`, and
    the document parsed from the same text. A field set to `_T4_SLOT` holds
    `slot`, written inline on the field's own line, so two derivations that
    differ only in that value number every line alike."""
    doc_map = {"archiveVersion": "1", "rootObject": root_id, "objects": objects}
    if object_version is not _ABSENT:
        doc_map["objectVersion"] = object_version
    text = "// !$*UTF8*$!\n" + _serialize(doc_map) + "\n"
    text = text.replace('"%s"' % _T4_SLOT, _t4_inline(slot))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _q9_tree(root)
        for rel in extra_files:
            _mkfile(root / rel)
        bundle = root / "X.xcodeproj"
        bundle.mkdir(parents=True, exist_ok=True)
        (bundle / "project.pbxproj").write_text(text)
        doc = spx.read_pbxproj(text.encode("utf-8"))
        reads = SimpleNamespace(bundles=[("X.xcodeproj", True, True)], refusals={},
                                files={_T4_PATH: text.encode("utf-8")})
        return sx.read_projects(root, reads, []), doc


def _t4_view(result):
    return {k: result[k] for k in ("targets", "target_deps", "product_deps", "dependencies",
                                   "memberships", "residuals")}


def _t4_details(result):
    return [r[3] for r in result["residuals"]]


def _t4_unreadable(result):
    return [r for r in result["residuals"] if r[0] == "project-unreadable"]


_T4_BASELINE_ROWS = [
    ("Classic/Main.swift", "App", "classic Sources build phase"),
    ("Synced/Ex.swift", "App", "excluded by an exception set"),
    ("Synced/Own.swift", "App", "folder-synced root Synced"),
]


class TypeConfusedFieldBaselineTests(unittest.TestCase):
    def test_control_the_typed_field_project_reads_whole(self):
        result, _doc = _t4_derive(_t4_objects())
        self.assertEqual([t["name"] for t in result["targets"]], ["App", "Tool"])
        self.assertEqual(_q9_rows(result), _T4_BASELINE_ROWS)
        self.assertEqual([(e["from"], e["to"]) for e in result["target_deps"]], [("Tool", "App")])
        self.assertEqual([p["product"] for p in result["product_deps"]], ["Kit"])
        self.assertEqual(result["residuals"], ())

    def test_control_the_slot_keeps_every_line_where_a_string_puts_it(self):
        objects = _t4_objects()
        objects["B"]["fileRef"] = _T4_SLOT
        _r1, doc_list = _t4_derive(objects, ["F"])
        _r2, doc_str = _t4_derive(objects, "F")
        self.assertEqual(doc_list.objects["B"]["fileRef"], ["F"])
        self.assertEqual(doc_list.object_spans, doc_str.object_spans)
        self.assertEqual(doc_list.value_lines, doc_str.value_lines)


class ScalarIdFieldTypeTests(unittest.TestCase):
    """ADR-0130 clauses 2, 7 and 9: an object-id
    field holding a value that is not a string is a dangling id. Each site
    renders exactly what it renders for a dangling string id -- the same
    class, detail and line -- and never raises."""

    @staticmethod
    def _build_phase_set(objects, **fields):
        """A second owner `Tool` and a build-phase membership exception set
        `BP` naming `Own.swift`, so owning one target differs from owning
        every target."""
        objects["U"]["fileSystemSynchronizedGroups"] = ["SR"]
        objects["SR"]["exceptions"] = ["E", "BP"]
        objects["BP"] = _obj("PBXFileSystemSynchronizedGroupBuildPhaseMembershipExceptionSet",
                             membershipExceptions=["Own.swift"], **fields)

    def _prep_build_phase_set_target(self, o):
        self._build_phase_set(o, target="T")

    def _prep_build_phase(self, o):
        self._build_phase_set(o, buildPhase="S")

    def _prep_target_proxy(self, o):
        del o["TD"]["target"]

    # site -> (object, field, the real id a colliding value carries, prep)
    SITES = {
        "fileRef": ("B", "fileRef", "F", None),
        "build-file exception set target": ("E", "target", "T", None),
        "build-phase exception set target": ("BP", "target", "T", "_prep_build_phase_set_target"),
        "buildPhase": ("BP", "buildPhase", "S", "_prep_build_phase"),
        "package": ("P", "package", "R", None),
        "targetProxy": ("TD", "targetProxy", "TP", "_prep_target_proxy"),
        "containerPortal": ("TP", "containerPortal", "PROJ", None),
    }

    def _objects(self, site):
        obj_id, field_name, _real, prep = self.SITES[site]
        o = _t4_objects()
        if prep:
            getattr(self, prep)(o)
        o[obj_id][field_name] = _T4_SLOT
        return o

    def test_a_value_that_is_not_a_string_renders_what_a_dangling_id_renders(self):
        for site, (_obj_id, _field, real, _prep) in self.SITES.items():
            dangling, _doc = _t4_derive(self._objects(site), _T4_DANGLING)
            for bad in ([real], {real: "x"}, [], {}):
                with self.subTest(site=site, bad=bad):
                    result, _doc = _t4_derive(self._objects(site), bad)
                    self.assertEqual(_t4_unreadable(result), [])
                    self.assertEqual(_t4_view(result), _t4_view(dangling))

    def test_control_each_site_is_live(self):
        """The equality above is not vacuous: at every site a dangling id
        renders differently from the real one."""
        for site, (_obj_id, _field, real, _prep) in self.SITES.items():
            with self.subTest(site=site):
                dangling, _doc = _t4_derive(self._objects(site), _T4_DANGLING)
                live, _doc = _t4_derive(self._objects(site), real)
                self.assertNotEqual(_t4_view(dangling), _t4_view(live))

    def test_a_non_string_file_ref_renders_the_dangling_line_at_the_item_line(self):
        for bad in (["F"], {"F": "x"}):
            with self.subTest(bad=bad):
                o = _t4_objects()
                o["B"]["fileRef"] = _T4_SLOT
                o["B"]["platformFilter"] = "ios"
                result, doc = _t4_derive(o, bad)
                line = doc.list_item_lines[("S", "files")][0]
                self.assertEqual(
                    [r for r in result["residuals"] if "Sources phase" in r[3]],
                    [("conditional-setting", _T4_PATH, [(line, line)],
                      "a build file in 'App's Sources phase carries a platform filter"),
                     ("unresolved-reference", _T4_PATH, [(line, line)],
                      "a dangling file reference in 'App's Sources phase")])
                self.assertNotIn(("Classic/Main.swift", "App", "classic Sources build phase"), _q9_rows(result))

    def test_a_non_string_build_file_set_target_names_no_native_target(self):
        for bad in (["T"], {"T": "x"}):
            with self.subTest(bad=bad):
                o = _t4_objects()
                o["E"]["target"] = _T4_SLOT
                result, doc = _t4_derive(o, bad)
                span = doc.object_spans["E"]
                self.assertIn(("unresolved-reference", _T4_PATH, [span],
                               "an exception set on Synced names no native target"), result["residuals"])
                # The set applies to nobody: the owner's default rows stand.
                self.assertEqual(_q9_rows(result), [
                    ("Classic/Main.swift", "App", "classic Sources build phase"),
                    ("Synced/Ex.swift", "App", "folder-synced root Synced"),
                    ("Synced/Own.swift", "App", "folder-synced root Synced")])

    def test_a_non_string_build_phase_set_target_falls_back_to_build_phase(self):
        o = _t4_objects()
        self._build_phase_set(o, target=_T4_SLOT, buildPhase="S")
        result, _doc = _t4_derive(o, ["U"])
        rows = _q9_rows(result)
        # `buildPhase` names `App`'s phase: withheld from `App` only.
        self.assertNotIn(("Synced/Own.swift", "App", "folder-synced root Synced"), rows)
        self.assertIn(("Synced/Own.swift", "Tool", "folder-synced root Synced"), rows)
        self.assertEqual(_t4_unreadable(result), [])

    def test_a_non_string_build_phase_set_target_and_no_phase_withholds_from_every_owner(self):
        o = _t4_objects()
        self._build_phase_set(o, target=_T4_SLOT)
        result, _doc = _t4_derive(o, {"T": "x"})
        rows = _q9_rows(result)
        self.assertNotIn(("Synced/Own.swift", "App", "folder-synced root Synced"), rows)
        self.assertNotIn(("Synced/Own.swift", "Tool", "folder-synced root Synced"), rows)
        self.assertIn("a build-phase membership exception set on Synced names a "
                      "buildPhase that resolves to no owning target", _t4_details(result))


class DependencyIdMatchesDanglingStringTests(unittest.TestCase):
    """ADR-0130 clauses 2 and 6: a dependency's `target`, or its proxy's
    `remoteGlobalIDString`, that is not a string renders exactly what a
    dangling string id renders in the same slot -- the same class, detail and
    location -- and draws no edge. `NOT_AN_ID` flows as an id value and
    misses every lookup: with nothing to contradict it the dependency "names
    a dangling target", and beside a proxy or `target` that resolves
    elsewhere it "does not resolve".

    Declared cause of the move from "does not resolve" for every shape:
    ADR-0130 clauses 2 and 6 -- a non-string id renders what a dangling
    string id renders at the same site, and the earlier "does not resolve"
    for every shape contradicted that."""

    BAD = (["T"], {"T": "x"}, [], {})
    DANGLING = "dependency of 'Tool' names a dangling target"
    DISAGREES = "dependency of 'Tool' does not resolve"

    def _derive(self, slots, value, keep_proxy=True, keep_target=True):
        o = _t4_objects()
        if not keep_proxy:
            del o["TD"]["targetProxy"]
        if not keep_target:
            del o["TD"]["target"]
        for obj_id, field_name in slots:
            o[obj_id][field_name] = _T4_SLOT
        return _t4_derive(o, value)

    def _assert_one_line(self, slots, detail, **kw):
        dangling, _doc = self._derive(slots, _T4_DANGLING, **kw)
        for bad in self.BAD:
            with self.subTest(slots=slots, bad=bad, **kw):
                result, doc = self._derive(slots, bad, **kw)
                self.assertEqual(result["target_deps"], ())
                self.assertEqual(result["residuals"], (
                    ("unresolved-reference", _T4_PATH, [doc.object_spans["TD"]], detail),))
                self.assertEqual(result["residuals"], dangling["residuals"])

    def test_an_unproxied_non_string_target_names_a_dangling_target(self):
        self._assert_one_line((("TD", "target"),), self.DANGLING, keep_proxy=False)

    def test_a_non_string_target_beside_a_resolving_proxy_does_not_resolve(self):
        self._assert_one_line((("TD", "target"),), self.DISAGREES)

    def test_a_non_string_remote_id_beside_a_resolving_target_does_not_resolve(self):
        self._assert_one_line((("TP", "remoteGlobalIDString"),), self.DISAGREES)

    def test_a_non_string_remote_id_with_no_target_names_a_dangling_target(self):
        self._assert_one_line((("TP", "remoteGlobalIDString"),), self.DANGLING, keep_target=False)

    def test_a_non_string_target_and_remote_id_agree_and_name_a_dangling_target(self):
        self._assert_one_line((("TD", "target"), ("TP", "remoteGlobalIDString")), self.DANGLING)

    def test_control_the_string_ids_draw_the_edge(self):
        for kw in ({}, {"keep_proxy": False}, {"keep_target": False}):
            with self.subTest(**kw):
                o = _t4_objects()
                if kw.get("keep_proxy") is False:
                    del o["TD"]["targetProxy"]
                if kw.get("keep_target") is False:
                    del o["TD"]["target"]
                result, _doc = _t4_derive(o)
                self.assertEqual([(e["from"], e["to"]) for e in result["target_deps"]], [("Tool", "App")])
                self.assertEqual(result["residuals"], ())


MAIN_GROUP_DETAIL = "the project's mainGroup names no group object; no group is descended"


class MainGroupFieldTests(unittest.TestCase):
    """ADR-0130 clause 2: a `mainGroup` that names no
    group object -- absent, `""`, not a string, dangling, or naming an object
    of another kind -- renders one `unresolved-reference` at its own line
    (the project object's first line when absent), and nothing is descended.
    Target rows and target and product dependencies still render. Only when
    the project directory resolved: a `$(`-holding or escaping
    `projectDirPath` keeps its own treatment."""

    VALUES = (["MAIN"], {"MAIN": "x"}, [], {}, "", _T4_DANGLING, "F", "C", _ABSENT)

    def _derive(self, value, **proj):
        o = _t4_objects()
        o["PROJ"].update(proj)
        if value is _ABSENT:
            del o["PROJ"]["mainGroup"]
            return _t4_derive(o)
        o["PROJ"]["mainGroup"] = _T4_SLOT
        return _t4_derive(o, value)

    def test_a_main_group_naming_no_group_renders_one_line_and_descends_nothing(self):
        for value in self.VALUES:
            with self.subTest(value=value):
                result, doc = self._derive(value)
                if value is _ABSENT:
                    line = doc.object_spans["PROJ"][0]
                else:
                    line = doc.value_lines[("PROJ", "mainGroup")]
                self.assertEqual([r for r in result["residuals"] if r[3] == MAIN_GROUP_DETAIL],
                                 [("unresolved-reference", _T4_PATH, [(line, line)], MAIN_GROUP_DETAIL)])
                self.assertEqual(_t4_unreadable(result), [])
                self.assertEqual([t["name"] for t in result["targets"]], ["App", "Tool"])
                self.assertEqual([(e["from"], e["to"]) for e in result["target_deps"]], [("Tool", "App")])
                self.assertEqual([p["product"] for p in result["product_deps"]], ["Kit"])
                self.assertEqual(result["memberships"], ())
                details = _t4_details(result)
                self.assertIn("a file reference in 'App's Sources phase did not resolve", details)
                self.assertIn("target 'App' names a folder-synced root that descent did not resolve", details)

    def test_control_a_main_group_naming_a_group_renders_no_line(self):
        result, _doc = self._derive("MAIN")
        self.assertNotIn(MAIN_GROUP_DETAIL, _t4_details(result))
        self.assertEqual(_q9_rows(result), _T4_BASELINE_ROWS)

    def test_an_unresolved_project_directory_keeps_its_own_treatment(self):
        for pdp in ("$(SRCROOT)/x", "/abs"):
            for value in (["MAIN"], _T4_DANGLING):
                with self.subTest(pdp=pdp, value=value):
                    result, _doc = self._derive(value, projectDirPath=pdp)
                    self.assertNotIn(MAIN_GROUP_DETAIL, _t4_details(result))
                    self.assertEqual(_t4_unreadable(result), [])
                    self.assertEqual([t["name"] for t in result["targets"]], ["App", "Tool"])


class RootObjectReadTests(unittest.TestCase):
    """ADR-0130 clauses 4 and 14: a `rootObject` that
    names no object, or one that is not a `PBXProject`, is the missing-
    rootObject condition: one `project-unreadable`/`malformed` line and
    nothing else."""

    def test_a_root_object_naming_no_project_is_malformed(self):
        for root_id in (_T4_DANGLING, "MAIN", "T"):
            with self.subTest(root_id=root_id):
                result, _doc = _t4_derive(_t4_objects(), root_id=root_id)
                self.assertEqual(result["residuals"], (("project-unreadable", _T4_PATH, None, "malformed"),))
                self.assertEqual(result["targets"], ())

    def test_a_root_object_whose_isa_is_not_a_string_is_malformed(self):
        o = _t4_objects()
        o["PROJ"]["isa"] = _T4_SLOT
        result, _doc = _t4_derive(o, ["PBXProject"])
        self.assertEqual(result["residuals"], (("project-unreadable", _T4_PATH, None, "malformed"),))


NON_DICT_DETAILS = {
    "buildSettings": "a build configuration's buildSettings field is not a dictionary and is not read",
    "explicitFileTypes": "a folder-synced root's explicitFileTypes field is not a dictionary and is not applied",
    "platformFiltersByRelativePath": ("an exception set's platformFiltersByRelativePath field is not a "
                                      "dictionary and is not applied"),
}


class DictFieldTypeTests(unittest.TestCase):
    """ADR-0130 clauses 2 and 14 (a construct the reader does not interpret
    is never applied): a
    dictionary field holding another type renders one
    `unsupported-project-form` at its own line, and nothing is read or
    applied from it. Type decides: `""` and `()` render the line; absent and
    `{}` render nothing."""

    # field -> (object, colliding values whose characters or items the old
    # read turned into keys)
    FIELDS = {
        "buildSettings": ("C", ("A[B", ["X[sdk=a]", "EXCLUDED_SOURCE_FILE_NAMES"])),
        "explicitFileTypes": ("SR", ("Own.swift", ["Own.swift"])),
        "platformFiltersByRelativePath": ("E", ("zzEx.swiftzz", [["Own.swift", "x"]], ["Ex.swift"])),
    }

    def test_the_constants_name_each_field_once(self):
        self.assertEqual(spx.NON_DICT_FIELD_DETAILS, NON_DICT_DETAILS)

    def test_a_value_of_another_type_renders_one_line_and_applies_nothing(self):
        for field_name, (obj_id, colliding) in self.FIELDS.items():
            for value in colliding + ("", []):
                with self.subTest(field=field_name, value=value):
                    o = _t4_objects()
                    o[obj_id][field_name] = _T4_SLOT
                    result, doc = _t4_derive(o, value)
                    line = doc.value_lines[(obj_id, field_name)]
                    detail = NON_DICT_DETAILS[field_name]
                    self.assertEqual([r for r in result["residuals"] if r[3] == detail],
                                     [("unsupported-project-form", _T4_PATH, [(line, line)], detail)])
                    self.assertEqual(_t4_unreadable(result), [])
                    self.assertEqual([r for r in result["residuals"] if r[3] != detail], [])
                    self.assertEqual(_q9_rows(result), _T4_BASELINE_ROWS)
                    self.assertFalse([m for m in result["memberships"] if m["conditional"]])

    def test_an_empty_dictionary_or_an_absent_key_renders_nothing(self):
        for field_name, (obj_id, _colliding) in self.FIELDS.items():
            for value in ({}, _ABSENT):
                with self.subTest(field=field_name, value=value):
                    o = _t4_objects()
                    if value is _ABSENT:
                        o[obj_id].pop(field_name, None)
                    else:
                        o[obj_id][field_name] = value
                    result, _doc = _t4_derive(o)
                    self.assertEqual(result["residuals"], ())
                    self.assertEqual(_q9_rows(result), _T4_BASELINE_ROWS)

    def test_control_a_dictionary_is_read_and_applied(self):
        """Each colliding name above does something when it is a key, so the
        assertions above are not vacuous."""
        cases = {
            "buildSettings": ({"X[sdk=a]": "1"}, "build setting 'X[sdk=a]' is conditioned and never applied", None),
            "explicitFileTypes": ({"Own.swift": "text"},
                                  "Synced/Own.swift is retyped by explicitFileTypes and withheld from membership",
                                  ("Synced/Own.swift", "App", "folder-synced root Synced")),
            "platformFiltersByRelativePath": ({"Own.swift": "ios"},
                                              "Synced/Own.swift carries a platformFiltersByRelativePath condition",
                                              None),
        }
        for field_name, (value, detail, withheld) in cases.items():
            with self.subTest(field=field_name):
                obj_id = self.FIELDS[field_name][0]
                o = _t4_objects()
                o[obj_id][field_name] = value
                result, _doc = _t4_derive(o)
                self.assertIn(detail, _t4_details(result))
                if withheld:
                    self.assertNotIn(withheld, _q9_rows(result))

    def test_a_string_on_a_non_owner_set_is_no_substring_condition(self):
        """`"zzEx.swiftzz"` on a set whose target owns no root: `in` over a
        string matched the entry `Ex.swift` as a substring and marked the
        added row conditional."""
        o = _t4_objects()
        o["SR"]["exceptions"] = ["E", "E2"]
        o["E2"] = _obj("PBXFileSystemSynchronizedBuildFileExceptionSet", target="U",
                       membershipExceptions=["Ex.swift"], platformFiltersByRelativePath=_T4_SLOT)
        result, doc = _t4_derive(o, "zzEx.swiftzz")
        detail = NON_DICT_DETAILS["platformFiltersByRelativePath"]
        line = doc.value_lines[("E2", "platformFiltersByRelativePath")]
        self.assertEqual([r for r in result["residuals"] if r[0] == "conditional-setting"], [])
        self.assertEqual([r for r in result["residuals"] if r[3] == detail],
                         [("unsupported-project-form", _T4_PATH, [(line, line)], detail)])
        added = [m for m in result["memberships"] if m["target"] == "Tool"]
        self.assertEqual([(m["file"], m["route"], m["conditional"]) for m in added],
                         [("Synced/Ex.swift", "added by an exception set", False)])

    def test_control_a_dictionary_on_a_non_owner_set_conditions_its_entry(self):
        o = _t4_objects()
        o["SR"]["exceptions"] = ["E", "E2"]
        o["E2"] = _obj("PBXFileSystemSynchronizedBuildFileExceptionSet", target="U",
                       membershipExceptions=["Ex.swift"], platformFiltersByRelativePath={"Ex.swift": "ios"})
        result, _doc = _t4_derive(o)
        self.assertIn("Synced/Ex.swift carries a platformFiltersByRelativePath condition", _t4_details(result))

    def test_one_line_per_exception_set_that_two_roots_list(self):
        o = _t4_objects()
        o["MAIN"]["children"] = ["SR", "SR2", "G"]
        o["SR2"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="Synced2", exceptions=["E"])
        o["E"]["platformFiltersByRelativePath"] = "x"
        result, _doc = _t4_derive(o, extra_files=("Synced2/Two.swift",))
        self.assertEqual(_t4_details(result).count(NON_DICT_DETAILS["platformFiltersByRelativePath"]), 1)


NON_STRING_DETAILS = {
    "name": "a target's name field is not a string and is not read",
    "productName": "a package product dependency's productName field is not a string and is not read",
    "objectVersion": "objectVersion is absent or not a string, which is outside the tested set",
}


class StringFieldTypeTests(unittest.TestCase):
    """ADR-0130 clauses 2, 4, 5 and 7: a display
    string field holding another type renders `—` in its cell and one
    `unsupported-project-form` at its own line. A list or dictionary target
    `name` raised `TypeError: unhashable type` out of `read_projects`, so the
    deriver exited 2."""

    NON_STRINGS = (["App"], {"App": "x"}, [], {})

    def test_the_constants_name_each_field_once(self):
        self.assertEqual(spx.NON_STRING_FIELD_DETAILS, NON_STRING_DETAILS)

    def test_a_target_name_that_is_not_a_string_renders_a_dash_and_one_line(self):
        detail = NON_STRING_DETAILS["name"]
        for value in self.NON_STRINGS:
            with self.subTest(value=value):
                o = _t4_objects()
                o["T"]["name"] = _T4_SLOT
                result, doc = _t4_derive(o, value)
                line = doc.value_lines[("T", "name")]
                self.assertEqual([r for r in result["residuals"] if r[3] == detail],
                                 [("unsupported-project-form", _T4_PATH, [(line, line)], detail)])
                self.assertEqual(_t4_unreadable(result), [])
                self.assertEqual(sorted(t["name"] for t in result["targets"]), ["Tool", "—"])
                self.assertEqual(_q9_rows(result), [(f, "—", r) for f, _t, r in _T4_BASELINE_ROWS])
                self.assertEqual([(e["from"], e["to"]) for e in result["target_deps"]], [("Tool", "—")])
                self.assertEqual([p["from"] for p in result["product_deps"]], ["—"])

    def test_a_target_with_no_membership_renders_a_dash_not_the_value(self):
        o = _t4_objects()
        o["U"]["name"] = _T4_SLOT
        result, _doc = _t4_derive(o, ["Tool", "x"])
        self.assertEqual(sorted(t["name"] for t in result["targets"]), ["App", "—"])
        self.assertEqual(_t4_details(result), [NON_STRING_DETAILS["name"]])

    def test_a_target_listed_twice_renders_one_line(self):
        o = _t4_objects()
        o["PROJ"]["targets"] = ["T", "U", "U"]
        o["U"]["name"] = _T4_SLOT
        result, _doc = _t4_derive(o, {"a": "b"})
        self.assertEqual(_t4_details(result).count(NON_STRING_DETAILS["name"]), 1)

    def test_an_empty_or_absent_name_renders_a_dash_and_no_line(self):
        for value in ("", _ABSENT):
            with self.subTest(value=value):
                o = _t4_objects()
                if value is _ABSENT:
                    del o["U"]["name"]
                else:
                    o["U"]["name"] = value
                result, _doc = _t4_derive(o)
                self.assertEqual(sorted(t["name"] for t in result["targets"]), ["App", "—"])
                self.assertEqual(result["residuals"], ())

    def test_a_product_name_that_is_not_a_string_renders_a_dash_and_one_line(self):
        detail = NON_STRING_DETAILS["productName"]
        for value in (["Kit"], {"Kit": "x"}, [], {}):
            with self.subTest(value=value):
                o = _t4_objects()
                o["P"]["productName"] = _T4_SLOT
                # `Tool` names the same product dependency: still one line.
                o["U"]["packageProductDependencies"] = ["P"]
                result, doc = _t4_derive(o, value)
                line = doc.value_lines[("P", "productName")]
                self.assertEqual([r for r in result["residuals"] if r[3] == detail],
                                 [("unsupported-project-form", _T4_PATH, [(line, line)], detail)])
                self.assertEqual(sorted((p["from"], p["product"]) for p in result["product_deps"]),
                                 [("App", "—"), ("Tool", "—")])

    def test_an_empty_or_absent_product_name_renders_a_dash_and_no_line(self):
        for value in ("", _ABSENT):
            with self.subTest(value=value):
                o = _t4_objects()
                if value is _ABSENT:
                    del o["P"]["productName"]
                else:
                    o["P"]["productName"] = value
                result, _doc = _t4_derive(o)
                self.assertEqual([p["product"] for p in result["product_deps"]], ["—"])
                self.assertEqual(result["residuals"], ())

    def test_an_absent_or_non_string_object_version_renders_its_own_detail(self):
        detail = NON_STRING_DETAILS["objectVersion"]
        for value in (_ABSENT, ["56"], {"a": "b"}, []):
            with self.subTest(value=value):
                result, doc = _t4_derive(_t4_objects(), value, object_version=(
                    _ABSENT if value is _ABSENT else _T4_SLOT))
                span = doc.object_spans["PROJ"]
                self.assertEqual(result["residuals"], (("unsupported-project-form", _T4_PATH, [span], detail),))
                self.assertEqual(_q9_rows(result), _T4_BASELINE_ROWS)

    def test_control_a_string_object_version_outside_the_set_keeps_its_detail(self):
        result, doc = _t4_derive(_t4_objects(), object_version="99")
        self.assertEqual(result["residuals"], (("unsupported-project-form", _T4_PATH, [doc.object_spans["PROJ"]],
                                                "objectVersion '99' is outside the tested set"),))

    def test_a_product_type_that_is_not_a_string_is_unmapped(self):
        for value in ([_APP_TYPE], {"a": "b"}, [], {}):
            with self.subTest(value=value):
                o = _t4_objects()
                o["T"]["productType"] = _T4_SLOT
                result, doc = _t4_derive(o, value)
                self.assertEqual(_t4_unreadable(result), [])
                app = [t for t in result["targets"] if t["name"] == "App"]
                self.assertEqual([(t["kind"], t["product_type"]) for t in app], [("unmapped", "—")])
                self.assertEqual(result["residuals"], (
                    ("unsupported-project-form", _T4_PATH, [doc.object_spans["T"]],
                     "target 'App' names an unmapped product type"),))
                self.assertEqual(_q9_rows(result), _T4_BASELINE_ROWS)

    def test_an_isa_that_is_not_a_string_is_an_unrecognised_isa(self):
        for obj_id in ("G", "T", "B", "SR", "E"):
            o = _t4_objects()
            real_isa = o[obj_id]["isa"]
            o[obj_id]["isa"] = _T4_SLOT
            unrecognised, _doc = _t4_derive(o, "PBXUnknownThing")
            baseline, _doc = _t4_derive(_t4_objects())
            with self.subTest(obj=obj_id, control=True):
                self.assertNotEqual(_t4_view(unrecognised), _t4_view(baseline))
            for value in ([real_isa], {real_isa: "x"}, {}, []):
                with self.subTest(obj=obj_id, value=value):
                    result, _doc = _t4_derive(o, value)
                    self.assertEqual(_t4_unreadable(result), [])
                    self.assertEqual(_t4_view(result), _t4_view(unrecognised))


class ProjectDirPathTypeTests(unittest.TestCase):
    """ADR-0130 clause 3: a `projectDirPath` that is
    not a string is never resolved. Both readers' twins return
    `UNRESOLVED_DIR`, as for a build-setting reference; `()` and `{}` are no
    longer read as absent."""

    NON_STRINGS = (["sub"], {"a": "b"}, [], {})

    def test_both_twins_return_the_unresolved_directory(self):
        for twin in (sx.resolve_project_dir, sxp._resolve_project_dir):
            for value in self.NON_STRINGS:
                with self.subTest(twin=twin.__module__, value=value):
                    self.assertIs(twin({"projectDirPath": value}, ("ios",)), _UNRESOLVED_DIR)

    def test_control_both_twins_resolve_a_string(self):
        for twin in (sx.resolve_project_dir, sxp._resolve_project_dir):
            with self.subTest(twin=twin.__module__):
                self.assertEqual(twin({"projectDirPath": "sub"}, ("ios",)), ("ios", "sub"))
                self.assertEqual(twin({"projectDirPath": ""}, ("ios",)), ("ios",))
                self.assertEqual(twin({}, ("ios",)), ("ios",))
                self.assertIs(twin({"projectDirPath": "$(SRCROOT)"}, ("ios",)), _UNRESOLVED_DIR)

    def _objects(self):
        o = _t4_objects()
        o["PROJ"]["projectDirPath"] = _T4_SLOT
        o["PROJ"]["packageReferences"] = ["R", "L"]
        o["L"] = _obj("XCLocalSwiftPackageReference", relativePath="Pkg")
        o["P2"] = _obj("XCSwiftPackageProductDependency", productName="Lib", package="L")
        o["T"]["packageProductDependencies"] = ["P", "P2"]
        return o

    def test_a_project_reads_as_under_a_build_setting_reference(self):
        variable, _doc = _t4_derive(self._objects(), "$(SRCROOT)", extra_files=("Pkg/Package.swift",))
        for value in self.NON_STRINGS:
            with self.subTest(value=value):
                result, _doc = _t4_derive(self._objects(), value, extra_files=("Pkg/Package.swift",))
                self.assertEqual(_t4_unreadable(result), [])
                self.assertEqual(_t4_view(result), _t4_view(variable))

    def test_control_a_resolved_directory_reads_differently(self):
        variable, _doc = _t4_derive(self._objects(), "$(SRCROOT)", extra_files=("Pkg/Package.swift",))
        plain, _doc = _t4_derive(self._objects(), ".", extra_files=("Pkg/Package.swift",))
        self.assertNotEqual(_t4_view(variable), _t4_view(plain))
        self.assertIn("local package reference 'Pkg' declares no product 'Lib'", _t4_details(plain))


# Every scalar or dictionary field the typed-read helpers (`id_field`,
# `string_field`, `dict_field`, `isa_of`) read. A raw `.get("<field>")` or
# `<obj>["<field>"]` read of one of them in either reader bypasses the
# helper's type check (ADR-0130 clauses 2 and 14: a value of another type is
# a dangling id or an `unsupported-project-form` line, never raised on).
_T4_HELPER_FIELDS = frozenset([
    "isa", "mainGroup", "fileRef", "target", "targetProxy", "containerPortal", "remoteGlobalIDString",
    "package", "buildPhase", "buildSettings", "explicitFileTypes", "platformFiltersByRelativePath",
    "name", "productName", "productType",
])

#: The rows the readers build themselves, which carry a `name` or `target`
#: key of their own: a subscript read on one of these reads the reader's own
#: string, never a project object's field.
_T4_ROW_NAMES = frozenset(["row", "target_row", "exc_target_row", "m", "r", "p", "prod"])


def _t4_is_row(value):
    """True for a reader-built row: one of `_T4_ROW_NAMES`, or an item of
    `targets_by_id`, the target rows keyed by object id."""
    import ast
    if isinstance(value, ast.Name):
        return value.id in _T4_ROW_NAMES
    return (isinstance(value, ast.Subscript) and isinstance(value.value, ast.Name)
            and value.value.id == "targets_by_id")


def _t4_raw_reads(source):
    """`(line, field)` for every raw read in `source` of a field
    `_T4_HELPER_FIELDS` names: a `<expr>.get("<field>", ...)` call, or a
    `<expr>["<field>"]` load whose `<expr>` is not a reader-built row."""
    import ast
    found = []
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
                and node.args and isinstance(node.args[0], ast.Constant)
                and node.args[0].value in _T4_HELPER_FIELDS):
            found.append((node.lineno, node.args[0].value))
        elif (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load)
                and isinstance(node.slice, ast.Constant) and node.slice.value in _T4_HELPER_FIELDS
                and not _t4_is_row(node.value)):
            found.append((node.lineno, node.slice.value))
    return found


class FieldReadsGoThroughHelpersTests(unittest.TestCase):
    """ADR-0130 clauses 2 and 14: neither Xcode reader reads an enumerated field
    raw. A missed site could otherwise hold a list or a dictionary and raise,
    or read a string's characters."""

    def _sources(self):
        return {mod.__name__: Path(mod.__file__).read_text(encoding="utf-8") for mod in (sx, sxp)}

    def test_no_reader_reads_an_enumerated_field_raw(self):
        for name, source in self._sources().items():
            with self.subTest(module=name):
                self.assertEqual(_t4_raw_reads(source), [])

    def test_positive_control_a_planted_raw_read_is_found(self):
        for name, source in self._sources().items():
            for field_name in sorted(_T4_HELPER_FIELDS):
                for shape in ("obj.get(%r)", "obj[%r]"):
                    with self.subTest(module=name, field=field_name, shape=shape):
                        first = source.count("\n") + 1
                        planted = (source + "\n\ndef _planted(obj):\n    return " + shape % field_name
                                   + "\n")
                        self.assertEqual([f for line, f in _t4_raw_reads(planted) if line > first],
                                         [field_name])

    def test_positive_control_a_subscript_isa_read_in_descend_is_found(self):
        source = Path(sx.__file__).read_text(encoding="utf-8")
        self.assertEqual(source.count("isa = _isa_of(obj)"), 1)
        mutated = source.replace("isa = _isa_of(obj)", 'isa = obj["isa"]')
        self.assertIn("isa", [f for _line, f in _t4_raw_reads(mutated)])

    def test_control_a_reader_built_row_is_not_a_raw_read(self):
        self.assertEqual(_t4_raw_reads('def f(row, targets_by_id, t):\n'
                                       '    return row["name"], targets_by_id[t]["name"]\n'), [])


class ReadProjectsTotalOverFieldTypesTests(unittest.TestCase):
    """ADR-0130 clause 2: `read_projects` returns for every shape above, and
    every target, membership and edge name it returns is a `str` -- the
    sorts and the membership merge after the per-project loop have no
    boundary of their own."""

    def _shapes(self):
        shapes = []
        for obj_id, field_name in (("B", "fileRef"), ("E", "target"), ("PROJ", "mainGroup"), ("T", "name"),
                                   ("U", "name"), ("P", "productName"), ("T", "productType"), ("G", "isa"),
                                   ("T", "isa"), ("PROJ", "projectDirPath"), ("C", "buildSettings"),
                                   ("SR", "explicitFileTypes"), ("E", "platformFiltersByRelativePath"),
                                   ("TD", "target"), ("TD", "targetProxy"), ("TP", "containerPortal"),
                                   ("TP", "remoteGlobalIDString"), ("P", "package")):
            for value in (["T", "F"], {"T": "F"}, [], {}, [["x"]]):
                shapes.append((obj_id, field_name, value))
        return shapes

    def test_every_shape_returns_and_every_name_is_a_string(self):
        for obj_id, field_name, value in self._shapes():
            with self.subTest(obj=obj_id, field=field_name, value=value):
                o = _t4_objects()
                o[obj_id][field_name] = _T4_SLOT
                result, _doc = _t4_derive(o, value)
                self.assertEqual(_t4_unreadable(result), [])
                names = ([t["name"] for t in result["targets"]]
                         + [m["target"] for m in result["memberships"]]
                         + [e[k] for e in result["target_deps"] for k in ("from", "to")]
                         + [p[k] for p in result["product_deps"] for k in ("from", "product")])
                self.assertTrue(names)
                self.assertEqual([n for n in names if not isinstance(n, str)], [])
                self.assertEqual([r for r in result["residuals"] if not isinstance(r[3], str)], [])


# ── The exception-entry classifier, dangling ids, target identity and
# symlinked escapes (ADR-0130 clauses 2, 3, 6, 9 and 10) ──────────────────

_BP_ISA = "PBXFileSystemSynchronizedGroupBuildPhaseMembershipExceptionSet"
_BF_ISA = "PBXFileSystemSynchronizedBuildFileExceptionSet"
_ESCAPE_ON_SYNCED = "an exception entry on Synced escapes the checkout"


def _entry_project(isa, entries):
    """The single-letter-id project (`_q9_objects`) with its one exception
    set `E` of `isa`, owned by `T` through `target` and the Sources phase
    `S`, holding `entries`."""
    o = _q9_objects()
    o["E"] = _obj(isa, target="T", buildPhase="S", membershipExceptions=entries)
    return o


def _entry_derive(isa, entries, extra_files=()):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _q9_tree(root)
        for rel in extra_files:
            _mkfile(root / rel)
        return _q9_derive(root, _entry_project(isa, entries))


def _entry_lines(result, doc, isa):
    """Every residual except the build-phase set's own set-level line."""
    set_line = sx.BUILD_PHASE_SET_DETAIL % ("Synced",)
    return [r for r in result["residuals"] if r[3] != set_line]


class ExceptionEntryClassifierTests(unittest.TestCase):
    """ADR-0130 clauses 3 and 9: one classification for every
    `membershipExceptions` entry, shared by the build-file and the
    build-phase exception sets. A non-string entry, a build-setting
    reference, an absolute or `..`-escaping entry and a pruned path each
    render one line at the entry's item line and withhold nothing. Only a
    contained `.swift` entry of a build-phase set withholds a row: its
    lexically normalised path."""

    ENTRIES = ([["x"]], "$(X)/Lit.swift", "/etc/Abs.swift", "../../../Out.swift", "Pods/P.swift")
    EXPECTED = (
        ("unsupported-project-form", sx.NON_STRING_EXCEPTION_ENTRY_DETAIL),
        ("unresolved-reference", sx.NEVER_RESOLVED_EXCEPTION_ENTRY_DETAIL),
        ("path-escape", _ESCAPE_ON_SYNCED),
        ("path-escape", _ESCAPE_ON_SYNCED),
        ("unresolved-reference", "an exception entry names a path in a directory the Swift walk skips; "
                                 "it is not read"),
    )
    FILES = ("Synced/$(X)/Lit.swift", "Synced/Pods/P.swift")

    def test_both_set_kinds_render_one_line_per_entry_at_its_item_line(self):
        lines = {}
        for isa in (_BF_ISA, _BP_ISA):
            with self.subTest(isa=isa):
                result, doc = _entry_derive(isa, list(self.ENTRIES), self.FILES)
                item_lines = doc.list_item_lines[("E", "membershipExceptions")]
                want = sorted(("%s" % klass, "X.xcodeproj/project.pbxproj", [(line, line)], detail)
                              for (klass, detail), line in zip(self.EXPECTED, item_lines))
                got = sorted(_entry_lines(result, doc, isa))
                self.assertEqual(got, want)
                lines[isa] = got
        self.assertEqual(lines[_BF_ISA], lines[_BP_ISA])

    def test_a_classified_build_phase_entry_withholds_nothing(self):
        result, _doc = _entry_derive(_BP_ISA, list(self.ENTRIES), self.FILES)
        self.assertEqual(_q9_rows(result), [
            ("Classic/Main.swift", "App", "classic Sources build phase"),
            ("Synced/$(X)/Lit.swift", "App", "folder-synced root Synced"),
            ("Synced/Ex.swift", "App", "folder-synced root Synced"),
            ("Synced/Own.swift", "App", "folder-synced root Synced"),
        ])

    def test_positive_control_without_the_classification_the_reference_withholds_its_row(self):
        """The absence above is a measurement: with `never_resolved` off, the
        same build-phase entry withholds the literal directory's row."""
        with mock.patch.object(sx, "never_resolved", lambda value: False):
            result, _doc = _entry_derive(_BP_ISA, ["$(X)/Lit.swift"], self.FILES)
        self.assertNotIn(("Synced/$(X)/Lit.swift", "App", "folder-synced root Synced"), _q9_rows(result))

    def test_a_build_phase_entry_withholds_its_lexically_normalised_path(self):
        for entry in ("Own.swift", "./Own.swift", "Sub/../Own.swift", "D/../Own.swift"):
            with self.subTest(entry=entry):
                result, doc = _entry_derive(_BP_ISA, [entry])
                self.assertNotIn(("Synced/Own.swift", "App", "folder-synced root Synced"), _q9_rows(result))
                self.assertIn(("Synced/Ex.swift", "App", "folder-synced root Synced"), _q9_rows(result))
                self.assertEqual(_entry_lines(result, doc, _BP_ISA), [])

    def test_a_build_phase_localized_entry_withholds_and_renders_nothing(self):
        result, doc = _entry_derive(_BP_ISA, ["/Localized/D/Own.swift"], ("Synced/D/en.lproj/Own.swift",))
        self.assertIn(("Synced/Own.swift", "App", "folder-synced root Synced"), _q9_rows(result))
        self.assertEqual(_entry_lines(result, doc, _BP_ISA), [])

    def test_a_build_phase_entry_reaches_no_filesystem_check(self):
        seen = []

        def spy(name, real):
            def wrapper(root, segs, *args, **kwargs):
                if any(s in ("Abs.swift", "Out.swift", "P.swift", "Lit.swift", "Own.swift") for s in segs):
                    seen.append((name, tuple(segs)))
                return real(root, segs, *args, **kwargs)
            return wrapper

        with mock.patch.object(sx, "_real_contained_dir", spy("dir", sx._real_contained_dir)), \
                mock.patch.object(sx, "_classic_member_verdict", spy("file", sx._classic_member_verdict)):
            _entry_derive(_BP_ISA, list(self.ENTRIES) + ["Own.swift"], self.FILES)
        self.assertEqual(seen, [])

    def test_control_the_spy_sees_a_build_file_entry(self):
        seen = []
        real = sx._classic_member_verdict

        def spy(root, segs, *args, **kwargs):
            seen.append(tuple(segs))
            return real(root, segs, *args, **kwargs)

        with mock.patch.object(sx, "_classic_member_verdict", spy):
            _entry_derive(_BF_ISA, ["Own.swift"])
        self.assertIn(("Synced", "Own.swift"), seen)

    def test_the_set_level_line_says_the_set_is_not_interpreted(self):
        result, doc = _entry_derive(_BP_ISA, ["Own.swift"])
        self.assertIn(("unsupported-project-form", "X.xcodeproj/project.pbxproj", [doc.object_spans["E"]],
                       "a build-phase membership exception set on Synced is not interpreted; "
                       "the rows it names are withheld"), result["residuals"])

    def test_a_localized_entry_whose_join_leaves_the_checkout_renders_path_escape(self):
        # `<name>` leaves through `..`; `<dir>` leaves from a root at the
        # checkout root. Each renders the same line as any other escape.
        for isa in (_BF_ISA, _BP_ISA):
            for root_path, entry in (("Synced", "/Localized/D/../../../../Own.swift"),
                                     (".", "/Localized/../x/Own.swift")):
                with self.subTest(isa=isa, entry=entry):
                    o = _entry_project(isa, [entry])
                    o["SR"]["path"] = root_path
                    with tempfile.TemporaryDirectory() as tmp:
                        root = Path(tmp).resolve()
                        _q9_tree(root)
                        result, doc = _q9_derive(root, o)
                    line = doc.list_item_lines[("E", "membershipExceptions")][0]
                    shown = "Synced" if root_path == "Synced" else "."
                    got = [r for r in result["residuals"] if r[3] != sx.BUILD_PHASE_SET_DETAIL % (shown,)]
                    self.assertEqual(got, [("path-escape", "X.xcodeproj/project.pbxproj", [(line, line)],
                                            sx.EXCEPTION_ESCAPE_DETAIL % (shown,))])


class TargetProxyDanglingTests(unittest.TestCase):
    """ADR-0130 clause 6: a present `targetProxy` that is a string naming
    no object, not a string, or names an object that is not a
    `PBXContainerItemProxy` is a dangling id. It cannot corroborate `target`:
    the dependency draws no edge and renders "does not resolve" at its span.
    An absent `targetProxy` resolves through `target` alone."""

    def test_a_dangling_proxy_beside_a_resolving_target_draws_no_edge(self):
        for value in (_T4_DANGLING, "", ["TP"], {"TP": "x"}, [], {}, "F", "C", "T"):
            with self.subTest(value=value):
                o = _t4_objects()
                o["TD"]["targetProxy"] = _T4_SLOT
                result, doc = _t4_derive(o, value)
                self.assertEqual(result["target_deps"], ())
                self.assertEqual(result["residuals"], (
                    ("unresolved-reference", _T4_PATH, [doc.object_spans["TD"]],
                     "dependency of 'Tool' does not resolve"),))

    def test_control_an_absent_or_resolving_proxy_draws_the_edge(self):
        for drop in (False, True):
            with self.subTest(drop_proxy=drop):
                o = _t4_objects()
                if drop:
                    del o["TD"]["targetProxy"]
                result, _doc = _t4_derive(o)
                self.assertEqual([(e["from"], e["to"]) for e in result["target_deps"]], [("Tool", "App")])
                self.assertEqual(result["residuals"], ())


class DanglingIdListItemTests(unittest.TestCase):
    """ADR-0130 clause 2: a string item of `targets`, `buildPhases`
    or `packageReferences` that names no object renders the same line as an
    item that is not a string, at its item line, with the existing detail. An
    item naming an object of another `isa` renders nothing: a Resources phase
    and a local package reference are legitimate."""

    FIELDS = {
        ("PROJ", "targets"): sx.NON_STRING_TARGET_ITEM_DETAIL,
        ("T", "buildPhases"): sx.NON_STRING_BUILD_PHASE_ITEM_DETAIL,
        ("PROJ", "packageReferences"): "a project's packageReferences entry is not an object id and is not read",
    }

    def _derive(self, obj_id, field_name, value):
        o = _t4_objects()
        o[obj_id][field_name] = list(o[obj_id][field_name]) + [_T4_SLOT]
        return _t4_derive(o, value)

    def test_a_dangling_string_item_renders_the_non_string_line(self):
        for (obj_id, field_name), detail in self.FIELDS.items():
            for value in (_T4_DANGLING, "", ["x"]):
                with self.subTest(field=field_name, value=value):
                    result, doc = self._derive(obj_id, field_name, value)
                    line = doc.list_item_lines[(obj_id, field_name)][-1]
                    self.assertEqual(result["residuals"], (
                        ("unresolved-reference", _T4_PATH, [(line, line)], detail),))

    def test_control_an_item_of_another_isa_renders_nothing(self):
        for (obj_id, field_name) in self.FIELDS:
            with self.subTest(field=field_name):
                result, _doc = self._derive(obj_id, field_name, "C")
                self.assertEqual(result["residuals"], ())
        self.assertEqual(sx.NON_STRING_TARGET_ITEM_DETAIL,
                         "a project's targets entry is not an object id and is not read")
        self.assertEqual(sx.NON_STRING_BUILD_PHASE_ITEM_DETAIL,
                         "a target's buildPhases entry is not an object id and is not read")


class ExceptionsItemTests(unittest.TestCase):
    """ADR-0130 clause 2: an `exceptions` item that is not a
    string, names no object, or names an object whose `isa` is neither
    exception-set `isa` renders "a dangling exception set on <root>" at its
    own item line and reads no entries. Declared cause of the location move
    for a dangling string: ADR-0130 clause 4 -- location moved to the item
    line, which is the evidence range (ADR-0130:110)."""

    def test_every_non_set_item_renders_the_dangling_line_at_its_item_line(self):
        for value in (_T4_DANGLING, ["E"], {"E": "x"}, "F", "C", "MAIN"):
            with self.subTest(value=value):
                o = _t4_objects()
                o["SR"]["exceptions"] = [_T4_SLOT]
                result, doc = _t4_derive(o, value)
                line = doc.list_item_lines[("SR", "exceptions")][0]
                self.assertEqual(result["residuals"], (
                    ("unresolved-reference", _T4_PATH, [(line, line)], "a dangling exception set on Synced"),))
                self.assertIn(("Synced/Ex.swift", "App", "folder-synced root Synced"), _q9_rows(result))

    def test_control_a_real_exception_set_reads_its_entries(self):
        result, _doc = _t4_derive(_t4_objects())
        self.assertIn(("Synced/Ex.swift", "App", "excluded by an exception set"), _q9_rows(result))
        self.assertEqual(result["residuals"], ())


class TargetIdentityTests(unittest.TestCase):
    """ADR-0130 clause 10: a target's identity is its container and its
    object id. Two targets sharing a display -- `—` for no readable name, or
    one name twice -- each render `<display> (object <id>)`, so neither
    their rows, their membership rows nor their graph nodes merge, and an
    edge between them is drawn. Every row, membership and edge carries the
    id."""

    def _derive(self, names, shared_root=True):
        o = _t4_objects()
        for tid, name in zip(("T", "U"), names):
            if name is _ABSENT:
                del o[tid]["name"]
            else:
                o[tid]["name"] = name
        if shared_root:
            o["U"]["fileSystemSynchronizedGroups"] = ["SR"]
        return _t4_derive(o)[0]

    def test_two_targets_sharing_a_display_each_render_their_object_id(self):
        for names, display in (((["x"], {"y": "z"}), "—"), ((_ABSENT, _ABSENT), "—"), (("", ""), "—"),
                               (("App", "App"), "App")):
            with self.subTest(names=names):
                result = self._derive(names)
                app, tool = "%s (object T)" % display, "%s (object U)" % display
                self.assertEqual([(t["name"], t["target_id"]) for t in result["targets"]],
                                 [(app, "T"), (tool, "U")])
                self.assertEqual([(e["from"], e["to"], e["from_id"], e["to_id"]) for e in result["target_deps"]],
                                 [(tool, app, "U", "T")])
                rows = [(m["file"], m["target"], m["target_id"]) for m in result["memberships"]
                        if m["file"] == "Synced/Own.swift"]
                self.assertEqual(rows, [("Synced/Own.swift", app, "T"), ("Synced/Own.swift", tool, "U")])

    def test_control_distinct_names_render_bare(self):
        result = self._derive(("App", "Tool"))
        self.assertEqual([t["name"] for t in result["targets"]], ["App", "Tool"])
        self.assertEqual([(m["target"], m["target_id"]) for m in result["memberships"]
                          if m["file"] == "Synced/Own.swift"], [("App", "T"), ("Tool", "U")])

    def test_a_target_listed_twice_has_one_row(self):
        o = _t4_objects()
        o["PROJ"]["targets"] = ["T", "U", "T"]
        result = _t4_derive(o)[0]
        self.assertEqual([t["name"] for t in result["targets"]], ["App", "Tool"])

    def test_the_id_is_escaped_and_charged_like_a_name(self):
        o = _t4_objects()
        o["PROJ"]["targets"] = ["T", "A|`B"]
        o["A|`B"] = o.pop("U")
        o["T"]["name"] = "Tool"
        o["TD"]["target"] = "MISSING"
        del o["TD"]["targetProxy"]
        charged = []
        real = swift_xcinputs_mod().CollectionBudget.detail

        def spy(self_, path, span, *parts):
            charged.extend(parts)
            return real(self_, path, span, *parts)

        with mock.patch.object(swift_xcinputs_mod().CollectionBudget, "detail", spy):
            result = _t4_derive(o)[0]
        display = "Tool (object A|`B)"
        self.assertIn(display, [t["name"] for t in result["targets"]])
        self.assertIn(display, charged)
        detail = "dependency of '%s' names a dangling target" % (sx._cell(display),)
        self.assertIn(detail, [r[3] for r in result["residuals"]])
        self.assertIn("\\|", detail)
        self.assertNotIn("`", detail)


def swift_xcinputs_mod():
    from crux.arch.packs import swift_xcinputs
    return swift_xcinputs


_A7_OUTSIDE_FILES = ("X.swift", "Y.swift", "Sub/Z.swift", "en.lproj/Foo.swift")


def _a7_objects():
    """The single-letter-id project (`_q9_objects`) with a classic member
    `Classic/Ext/X.swift`, named by two build files, a classic member `Classic/Leak.swift` that is itself a
    symlink, and a build-file exception set naming a file, a directory and a
    `/Localized/` entry under `Synced/Ext`."""
    o = _q9_objects()
    o["F"]["path"] = "Ext/X.swift"
    o["B2"] = _obj("PBXBuildFile", fileRef="F")
    o["F2"] = _obj("PBXFileReference", sourceTree="<group>", path="Leak.swift")
    o["G"]["children"] = ["F", "F2"]
    o["B3"] = _obj("PBXBuildFile", fileRef="F2")
    o["S"]["files"] = ["B", "B2", "B3"]
    o["E"]["membershipExceptions"] = ["Ext/Y.swift", "Ext/Sub", "/Localized/Ext/Foo.swift"]
    return o


def _a7_tree(outer, escape):
    """`outer/checkout` holding the single-letter-id tree, with `Classic/Ext` and
    `Synced/Ext` symlinked to `outer/outside` (escape) or to the in-checkout
    copy `Real` (contained), and the file `Classic/Leak.swift` symlinked to
    that directory's `X.swift`. Returns `(root, outside)`, or skips when the
    host refuses symlinks."""
    root = outer / "checkout"
    outside = outer / "outside"
    for rel in _A7_OUTSIDE_FILES:
        _mkfile(outside / rel)
        _mkfile(root / "Real" / rel)
    _q9_tree(root)
    target = outside if escape else root / "Real"
    try:
        (root / "Classic" / "Ext").symlink_to(target, target_is_directory=True)
        (root / "Synced" / "Ext").symlink_to(target, target_is_directory=True)
        (root / "Classic" / "Leak.swift").symlink_to(target / "X.swift")
    except (OSError, NotImplementedError):
        raise unittest.SkipTest("host refuses symlink creation")
    return root, outside


_A7_SEEN: list = []
_A7_WATCH: list = [None]


def _a7_audit(event, args):
    watch = _A7_WATCH[0]
    if watch is None or event not in ("open", "os.scandir", "os.listdir") or not args or args[0] is None:
        return
    try:
        real = os.path.realpath(os.fsdecode(args[0]) if not isinstance(args[0], int) else "")
    except (TypeError, ValueError):
        return
    if real == watch or real.startswith(watch + os.sep):
        _A7_SEEN.append((event, real))


sys.addaudithook(_a7_audit)  # cannot be removed; inert unless a watch is set.


class SymlinkedEscapeTests(unittest.TestCase):
    """ADR-0130 clause 3: "a symlinked component that escapes also
    renders `path-escape`". A classic member, and a file, directory or
    `/Localized/` exception entry, under a directory symlink that resolves
    outside the checkout each render `path-escape` with the detail that
    site's lexical escape renders -- once per file reference for a classic
    member, at the entry's item line for an exception entry -- and nothing
    outside the checkout is listed or opened. Through a symlink that stays
    inside, the unresolved lines are unchanged."""

    PATH = "X.xcodeproj/project.pbxproj"

    def _derive(self, escape):
        with tempfile.TemporaryDirectory() as tmp:
            root, outside = _a7_tree(Path(tmp).resolve(), escape)
            del _A7_SEEN[:]
            _A7_WATCH[0] = os.path.realpath(outside)
            try:
                result, doc = _q9_derive(root, _a7_objects())
            finally:
                _A7_WATCH[0] = None
            return result, doc, list(_A7_SEEN)

    def _entry_lines(self, doc):
        return [(n, n) for n in doc.list_item_lines[("E", "membershipExceptions")]]

    def test_an_escaping_symlinked_dir_renders_path_escape_at_each_site(self):
        result, doc, seen = self._derive(escape=True)
        want = [("path-escape", self.PATH, [doc.object_spans[ref]], sx.REFERENCE_ESCAPE_DETAIL)
                for ref in ("F", "F2")]
        want += [("path-escape", self.PATH, [span], "an exception entry on Synced escapes the checkout")
                 for span in self._entry_lines(doc)]
        self.assertEqual(sorted(result["residuals"]), sorted(want))
        self.assertEqual([m["file"] for m in result["memberships"] if "Ext" in m["file"]], [])
        self.assertEqual(seen, [])

    def test_control_a_contained_symlinked_dir_keeps_its_unresolved_lines(self):
        result, doc, _seen = self._derive(escape=False)
        files = doc.list_item_lines[("S", "files")]
        entries = self._entry_lines(doc)
        member = ("a file reference in 'App's Sources phase names Classic/Ext/X.swift, which no directory "
                  "listing matches byte for byte as a regular file")
        want = [("unresolved-reference", self.PATH, [(n, n)], member) for n in files[:2]]
        want.append(("unresolved-reference", self.PATH, [(files[2], files[2])],
                     member.replace("Classic/Ext/X.swift", "Classic/Leak.swift")))
        want += [("unresolved-reference", self.PATH, [entries[0]], "an exception entry on Synced resolves to no file"),
                 ("unresolved-reference", self.PATH, [entries[1]], "an exception entry on Synced resolves to no file"),
                 ("unresolved-reference", self.PATH, [entries[2]],
                  "a /Localized/ exception entry on Synced resolves to no file")]
        self.assertEqual(sorted(result["residuals"]), sorted(want))
        self.assertNotIn("path-escape", [r[0] for r in result["residuals"]])

    def test_positive_control_the_old_none_verdict_loses_the_path_escape(self):
        """With the directory verdict's escape folded into `missing` -- the
        old `None` -- every directory site loses its `path-escape`, and only
        the leaf symlink `Classic/Leak.swift` keeps its own, so the test
        above measures the verdict."""
        real = sx._real_contained_dir

        def folded(root, segs, verdicts=None):
            verdict, path = real(root, segs, verdicts)
            return ("missing", None) if verdict == "escape" else (verdict, path)

        with mock.patch.object(sx, "_real_contained_dir", folded):
            result, doc, _seen = self._derive(escape=True)
        self.assertEqual([r[2] for r in result["residuals"] if r[0] == "path-escape"],
                         [[doc.object_spans["F2"]]])

    def test_positive_control_the_spy_sees_a_listing_through_the_link(self):
        """Without the symlink check, a listing reaches the outside directory
        and the audit hook records it, so an empty record is a measurement."""
        with mock.patch.object(sx, "_synced_root_symlink_verdict", lambda *a, **k: None):
            _result, _doc, seen = self._derive(escape=True)
        self.assertIn("os.scandir", [event for event, _path in seen])


_A7_CHILD = r"""
import json, os, sys
OUTSIDE, SCRIPTS, DRIVER, ROOT, MUTATE = sys.argv[1:6]
import tree_sitter, tree_sitter_swift  # noqa: F401  (their own reads are not the derive's)
seen = []
def hook(event, args):
    if event in ("open", "os.scandir", "os.listdir") and args and isinstance(args[0], (str, bytes, os.PathLike)):
        real = os.path.realpath(os.fsdecode(args[0]))
        if real == OUTSIDE or real.startswith(OUTSIDE + os.sep):
            seen.append(event)
sys.addaudithook(hook)
sys.path.insert(0, SCRIPTS)
if MUTATE == "1":
    from crux.arch.packs import swift_xcode
    swift_xcode._synced_root_symlink_verdict = lambda *a, **k: None
sys.argv = ["derive-arch.py", "--repo-root", ROOT]
import importlib.util
spec = importlib.util.spec_from_file_location("drv", DRIVER)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m._annotate = lambda *a, **k: []  # the staleness advisory runs git; it is not the derive
code = m.main()
print(json.dumps({"exit": code, "seen": seen}))
"""


class SymlinkedEscapeCliTests(unittest.TestCase):
    """The escaping symlink through the real CLI, `derive-arch.py
    --repo-root`: the escaping tree renders every `path-escape` line in the module graph, and an audit
    hook records no `open`, `os.scandir` or `os.listdir` outside the
    checkout. The positive control removes the symlink check and the hook
    records a listing outside."""

    def _run(self, mutate):
        import json
        import subprocess
        scripts = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as tmp:
            root, outside = _a7_tree(Path(tmp).resolve(), escape=True)
            (root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: bionic\n')
            _mkfile(root / "bionic" / "manifest.yml", b'schema_version: "5"\nadr:\n  next_number: 1\n')
            doc_map = {"archiveVersion": "1", "objectVersion": "56", "rootObject": "PROJ",
                       "objects": _a7_objects()}
            _mkfile(root / "X.xcodeproj" / "project.pbxproj",
                    ("// !$*UTF8*$!\n" + _serialize(doc_map) + "\n").encode("utf-8"))
            proc = subprocess.run(
                [sys.executable, "-c", _A7_CHILD, os.path.realpath(outside), str(scripts),
                 str(scripts / "derive-arch.py"), str(root), "1" if mutate else "0"],
                capture_output=True, text=True, timeout=120)
            self.assertTrue(proc.stdout.strip(), proc.stderr[-2000:])
            report = json.loads(proc.stdout.strip().splitlines()[-1])
            graph = (root / "bionic" / "arch" / "module-graph.md").read_text(encoding="utf-8")
        return report, graph

    def test_the_cli_renders_path_escape_and_reads_nothing_outside(self):
        report, graph = self._run(mutate=False)
        self.assertEqual(report["exit"], 0)
        self.assertEqual(report["seen"], [])
        self.assertEqual(graph.count("— " + sx.REFERENCE_ESCAPE_DETAIL), 2)
        self.assertIn("— an exception entry on Synced escapes the checkout", graph)
        self.assertNotIn("resolves to no file", graph)
        self.assertNotIn("names Classic/Ext/X.swift", graph)
        self.assertNotIn("names Classic/Leak.swift", graph)

    def test_positive_control_without_the_symlink_check_the_hook_sees_outside(self):
        report, _graph = self._run(mutate=True)
        self.assertEqual(report["exit"], 0)
        self.assertIn("os.scandir", report["seen"])


# ── ADR-0129 clause 2: reader work grows linearly ──────────────────────────
#
# Each shape below made the Xcode reader's work grow with the product of two
# inputs. Every test counts the work -- directory listings, entries yielded,
# walks, list scans, sorts, held set elements, collected residual lines --
# and never times it.

from crux.arch.packs import swift_xcinputs as _sxi  # noqa: E402


class _CountingScandir:
    """`os.scandir` that records each listing's path and counts the entries
    its iterators yield."""

    def __init__(self):
        self.paths = []
        self.entries = 0
        self.real = os.scandir

    def __call__(self, *args, **kwargs):
        self.paths.append(os.fspath(args[0] if args else kwargs.get("path")))
        return _CountingIterator(self, self.real(*args, **kwargs))


class _CountingIterator:
    def __init__(self, owner, it):
        self.owner = owner
        self.it = it

    def __iter__(self):
        return self

    def __next__(self):
        entry = next(self.it)
        self.owner.entries += 1
        return entry

    def __enter__(self):
        self.it.__enter__()
        return self

    def __exit__(self, *exc):
        return self.it.__exit__(*exc)

    def close(self):
        self.it.close()


def _synced_objects(entries, exc_isa="PBXFileSystemSynchronizedBuildFileExceptionSet", owners=1,
                    exc_fields=None, root_path="S"):
    """One folder-synced root at `root_path` owned by `owners` targets `T0`,
    `T1`, ..., with one exception set `E` naming `entries`, targeted at
    `T0`."""
    objects = {}
    objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T%d" % i for i in range(owners)])
    objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SR"])
    objects["SR"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path=root_path,
                         exceptions=["E"])
    fields = {"target": "T0", "membershipExceptions": entries}
    fields.update(exc_fields or {})
    objects["E"] = _obj(exc_isa, **fields)
    for i in range(owners):
        objects["T%d" % i] = _obj("PBXNativeTarget", name="A%d" % i, productType=_APP_TYPE,
                                  fileSystemSynchronizedGroups=["SR"])
    return objects


class ReaderWorkIsLinearTests(unittest.TestCase):
    """The memoisations one `read_projects` call needs to stay linear.
    Each test goes red on the reader that listed, walked, scanned or copied
    once per referrer, and green on the one that does it once per call."""

    def _derive(self, root, objects, scandir=None):
        if scandir is None:
            return _q9_derive(root, objects)
        with mock.patch("os.scandir", scandir):
            return _q9_derive(root, objects)

    def test_classic_members_of_one_directory_list_it_once(self):
        """M build files naming one missing file in a directory of D files:
        one listing of D entries, not M listings of D entries."""
        M, D = 400, 400
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["G"])
        objects["G"] = _obj("PBXGroup", sourceTree="<group>", path="Src", children=["F"])
        objects["F"] = _obj("PBXFileReference", sourceTree="<group>", path="missing.swift")
        objects["B"] = _obj("PBXBuildFile", fileRef="F")
        objects["SP"] = _obj("PBXSourcesBuildPhase", files=["B"] * M)
        objects["T"] = _obj("PBXNativeTarget", name="App", productType=_APP_TYPE, buildPhases=["SP"])
        spy = _CountingScandir()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for i in range(D):
                _mkfile(root / "Src" / ("f%d.txt" % i))
            result, _doc = self._derive(root, objects, spy)
            leaf = str(root / "Src")
        self.assertEqual(len([r for r in result["residuals"] if "no directory listing matches" in r[3]]), M)
        self.assertEqual(spy.paths.count(leaf), 1)
        self.assertLessEqual(spy.entries, 2 * (M + D), spy.entries)

    def _count_walks(self, root, objects):
        walks = []
        real = sx._scan_swift_files

        def spy(base, root_, explicit_folders, *budget):
            walks.append(os.fspath(base))
            return real(base, root_, explicit_folders, *budget)

        with mock.patch.object(sx, "_scan_swift_files", spy):
            result, _doc = _q9_derive(root, objects)
        return result, walks

    def test_exception_entries_naming_one_directory_walk_it_once(self):
        E = 200
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _mkfile(root / "S" / "Own.swift")
            for i in range(20):
                _mkfile(root / "S" / "sub" / ("f%d.swift" % i))
            result, walks = self._count_walks(root, _synced_objects(["sub"] * E))
            sub = str(root / "S" / "sub")
        self.assertEqual(walks.count(sub), 1, walks.count(sub))
        excluded = [m for m in result["memberships"] if m["route"] == "excluded by an exception set"]
        self.assertEqual(len(excluded), 20)

    def test_synced_roots_naming_one_directory_walk_it_once(self):
        R = 200
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SR%d" % i for i in range(R)])
        objects["T"] = _obj("PBXNativeTarget", name="App", productType=_APP_TYPE,
                            fileSystemSynchronizedGroups=["SR%d" % i for i in range(R)])
        for i in range(R):
            objects["SR%d" % i] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="S")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _mkfile(root / "S" / "A.swift")
            result, walks = self._count_walks(root, objects)
        self.assertEqual(len(walks), 1, len(walks))
        self.assertEqual(_q9_rows(result), [("S/A.swift", "App", "folder-synced root S")])

    def test_localized_entries_list_their_dir_once(self):
        """E `/Localized/L/x.swift` entries over D `.lproj` directories: `L`
        and each `.lproj` are listed once for the call, and `L`'s `.lproj`
        names are filtered once."""
        E, D = 100, 50
        spy = _CountingScandir()
        filtered = []
        real = sx.directory_entries

        def entries_spy(root_, segments, verdicts=None):
            if tuple(segments)[-1:] == ("L",):
                filtered.append(tuple(segments))
            return real(root_, segments, verdicts)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for i in range(D):
                (root / "S" / "L" / ("l%03d.lproj" % i)).mkdir(parents=True)
            _mkfile(root / "S" / "L" / "l000.lproj" / "x.swift")
            with mock.patch.object(sx, "directory_entries", entries_spy):
                result, _doc = self._derive(root, _synced_objects(["/Localized/L/x.swift"] * E), spy)
            ldir = str(root / "S" / "L")
            lprojs = [p for p in spy.paths if p.endswith(".lproj")]
        self.assertEqual([m["file"] for m in result["memberships"]], ["S/L/l000.lproj/x.swift"])
        # One listing is the root's own default walk, which descends `L`;
        # the other is the reader's one listing for every entry.
        self.assertLessEqual(spy.paths.count(ldir), 2, spy.paths.count(ldir))
        self.assertEqual(len(filtered), 1, len(filtered))
        self.assertEqual(len(lprojs), D, len(lprojs))

    def _held_elements(self, run):
        """The elements of every set and dictionary `synced_memberships`
        built and holds when it returns, each container counted once by
        identity. Containers reachable from its arguments (the document, the
        target rows) are input, not held work, and are not counted. The
        count is independent of the variables' names."""
        held = []
        code = sx.synced_memberships.__code__

        def walk(values, seen, count):
            total, todo = 0, list(values)
            while todo:
                value = todo.pop()
                if id(value) in seen:
                    continue
                if isinstance(value, (set, frozenset, dict)):
                    seen.add(id(value))
                    total += len(value) if count else 0
                    if isinstance(value, dict):
                        todo.extend(value.values())
                elif not count and hasattr(value, "__dict__"):
                    seen.add(id(value))
                    todo.extend(vars(value).values())
            return total

        def profile(frame, event, _arg):
            if event == "return" and frame.f_code is code:
                names = code.co_varnames[:code.co_argcount]
                seen = set()
                walk([frame.f_locals[n] for n in names], seen, count=False)
                held.append(walk(frame.f_locals.values(), seen, count=True))

        sys.setprofile(profile)
        try:
            result = run()
        finally:
            sys.setprofile(None)
        return result, held

    def _withheld_case(self, phase_owned):
        E, T = 400, 100
        entries = ["a%04d.swift" % i for i in range(E)]
        # `target` names no owner either, so an unowned phase withholds from
        # every owner.
        objects = _synced_objects(entries, exc_isa=sx._BUILD_PHASE_EXCEPTION_SET_ISA, owners=T,
                                  exc_fields={"buildPhase": "PH" if phase_owned else "NOPE",
                                              "target": "NOPE"})
        if phase_owned:
            objects["PH"] = _obj("PBXSourcesBuildPhase", files=[])
            for i in range(T):
                objects["T%d" % i]["buildPhases"] = ["PH"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _mkfile(root / "S" / "a0000.swift")
            _mkfile(root / "S" / "Kept.swift")
            (result, _doc), held = self._held_elements(lambda: _q9_derive(root, objects))
        rows = _q9_rows(result)
        self.assertEqual(rows, sorted(("S/Kept.swift", "A%d" % i, "folder-synced root S") for i in range(T)))
        self.assertEqual(len(held), 1)
        self.assertLessEqual(held[0], 4 * (E + T), held[0])

    def test_a_dangling_build_phase_set_holds_each_path_once(self):
        """`buildPhase` names no phase: every owner's rows are withheld,
        from one root-wide set of E paths, not E paths per owner."""
        self._withheld_case(phase_owned=False)

    def test_a_set_shared_by_owners_holds_each_path_once(self):
        """T targets list the set's phase: one map of E paths shares one
        owner set, not E paths per owner."""
        self._withheld_case(phase_owned=True)

    def test_ownership_is_read_once_per_target(self):
        """R roots, each named by the same T targets: each target's
        `fileSystemSynchronizedGroups` is read a fixed number of times, not
        scanned once per root."""
        R, T = 100, 20
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T%d" % i for i in range(T)])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SR%d" % i for i in range(R)])
        for i in range(R):
            objects["SR%d" % i] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="S")
        for t in range(T):
            objects["T%d" % t] = _obj("PBXNativeTarget", name="A%d" % t, productType=_APP_TYPE,
                                      fileSystemSynchronizedGroups=["SR%d" % i for i in range(R)])
        reads = [0]

        class Counted(list):
            def __contains__(self, item):
                reads[0] += 1
                return list.__contains__(self, item)

            def __iter__(self):
                reads[0] += 1
                return list.__iter__(self)

        doc = _pbx(objects, "PROJ")
        for t in range(T):
            obj = doc.objects["T%d" % t]
            obj["fileSystemSynchronizedGroups"] = Counted(obj["fileSystemSynchronizedGroups"])
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "S").mkdir()
            reads[0] = 0
            sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj", _sxi.DirectoryVerdicts(root))
        self.assertLessEqual(reads[0], 4 * T, reads[0])

    def test_default_rows_are_sorted_once_per_root(self):
        T, F = 50, 40
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T%d" % i for i in range(T)])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SR"])
        objects["SR"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="S")
        for t in range(T):
            objects["T%d" % t] = _obj("PBXNativeTarget", name="A%d" % t, productType=_APP_TYPE,
                                      fileSystemSynchronizedGroups=["SR"])
        sorts = []

        def counting_sorted(iterable, *args, **kwargs):
            out = builtins.sorted(iterable, *args, **kwargs)
            if len(out) == F and all(isinstance(x, str) and x.endswith(".swift") for x in out):
                sorts.append(len(out))
            return out

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for i in range(F):
                _mkfile(root / "S" / ("f%03d.swift" % i))
            with mock.patch.object(sx, "sorted", counting_sorted, create=True):
                result, _doc = _q9_derive(root, objects)
        self.assertEqual(len(result["memberships"]), T * F)
        self.assertEqual(len(sorts), 1, len(sorts))

    def test_the_owner_loop_stops_at_the_membership_bound(self):
        """Once the bound refuses a record, no later owner asks again."""
        T, F, LIMIT = 50, 5, 3
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T%d" % i for i in range(T)])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SR"])
        objects["SR"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="S")
        for t in range(T):
            objects["T%d" % t] = _obj("PBXNativeTarget", name="A%d" % t, productType=_APP_TYPE,
                                      fileSystemSynchronizedGroups=["SR"])
        asked = [0]

        class Budget(_sxi.CollectionBudget):
            def membership(self, path, span):
                asked[0] += 1
                return _sxi.CollectionBudget.membership(self, path, span)

        budget = Budget()
        budget.membership_limit = LIMIT
        doc = _pbx(objects, "PROJ")
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        d = sx.descend(doc, ())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for i in range(F):
                _mkfile(root / "S" / ("f%d.swift" % i))
            m, _res = sx.synced_memberships(doc, root, d, "p", by_id, "X.xcodeproj",
                                            _sxi.DirectoryVerdicts(root), collection=budget)
        self.assertEqual(len(m), LIMIT)
        self.assertIsNotNone(budget.membership_line())
        self.assertLessEqual(asked[0], LIMIT + 1, asked[0])

    def test_exception_entries_stop_at_the_membership_bound(self):
        """An exception set that adds F files to a target that does not own
        the root keeps LIMIT records and stops: the refused record is never
        appended, and no default row is read after it."""
        F, LIMIT = 5, 3
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["OWNER", "ADDED"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["SR"])
        objects["SR"] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>", path="S",
                             exceptions=["EX"])
        objects["EX"] = _obj("PBXFileSystemSynchronizedBuildFileExceptionSet", target="ADDED",
                             membershipExceptions=["f%d.swift" % i for i in range(F)])
        objects["OWNER"] = _obj("PBXNativeTarget", name="Owner", productType=_APP_TYPE,
                                fileSystemSynchronizedGroups=["SR"])
        objects["ADDED"] = _obj("PBXNativeTarget", name="Added", productType=_APP_TYPE)
        doc = _pbx(objects, "PROJ")
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")

        def run(limit):
            budget = _sxi.CollectionBudget()
            budget.membership_limit = limit
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                for i in range(F):
                    _mkfile(root / "S" / ("f%d.swift" % i))
                m, _res = sx.synced_memberships(doc, root, sx.descend(doc, ()), "p", by_id,
                                                "X.xcodeproj", _sxi.DirectoryVerdicts(root),
                                                collection=budget)
            return m, budget

        # Control: with room for every record, the set adds F rows and the
        # owner keeps its F default rows.
        m, budget = run(2 * F)
        self.assertEqual(sorted(r["route"] for r in m).count("added by an exception set"), F)
        self.assertEqual(len(m), 2 * F)
        self.assertIsNone(budget.membership_line())
        m, budget = run(LIMIT)
        self.assertEqual([r["route"] for r in m], ["added by an exception set"] * LIMIT)
        self.assertEqual(budget.memberships, LIMIT)
        self.assertIsNotNone(budget.membership_line())

    def test_a_shared_exception_set_keeps_each_line_once(self):
        """R roots share one exception set of N entries that are not
        strings: the reader keeps N lines, not R times N copies of them. The
        rendered lines are the same: the renderer merged the copies."""
        R, N = 60, 60
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["TGT"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["R%d" % i for i in range(R)])
        objects["TGT"] = _obj("PBXNativeTarget", name="App", productType=_APP_TYPE,
                              fileSystemSynchronizedGroups=["R%d" % i for i in range(R)])
        objects["EX"] = _obj("PBXFileSystemSynchronizedBuildFileExceptionSet", target="TGT",
                             membershipExceptions=[["x"]] * N)
        for i in range(R):
            objects["R%d" % i] = _obj("PBXFileSystemSynchronizedRootGroup", sourceTree="<group>",
                                      path="p%d" % i, exceptions=["EX"])
        doc = _pbx(objects, "PROJ")
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        with tempfile.TemporaryDirectory() as tmp:
            _m, res = sx.synced_memberships(doc, Path(tmp).resolve(), sx.descend(doc, ()), "p", by_id,
                                            "X.xcodeproj")
        lines = [r for r in res if r[3] == sx.NON_STRING_EXCEPTION_ENTRY_DETAIL]
        self.assertEqual(len(lines), N)
        self.assertEqual(sorted(r[2] for r in lines), doc.list_item_lines[("EX", "membershipExceptions")])

    def test_a_shared_sources_phase_keeps_each_line_once(self):
        """T targets share one Sources phase of F build files naming a
        pruned file: F lines, not T times F copies."""
        T, F = 60, 60
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T%d" % i for i in range(T)])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=["FR"])
        objects["FR"] = _obj("PBXFileReference", sourceTree="<group>", path="Pods/X.swift")
        objects["B"] = _obj("PBXBuildFile", fileRef="FR")
        objects["P"] = _obj("PBXSourcesBuildPhase", files=["B"] * F)
        for t in range(T):
            objects["T%d" % t] = _obj("PBXNativeTarget", name="T%d" % t, productType=_APP_TYPE,
                                      buildPhases=["P"])
        doc = _pbx(objects, "PROJ")
        _rows, by_id, _ = sx.target_rows(doc, "p", "X.xcodeproj")
        with tempfile.TemporaryDirectory() as tmp:
            _m, res = sx.classic_memberships(doc, Path(tmp).resolve(), sx.descend(doc, ()), "p", by_id,
                                             "X.xcodeproj")
        from crux.arch.packs import swift_prune
        lines = [r for r in res if r[3] == swift_prune.SOURCES_MEMBER_DETAIL]
        self.assertEqual(len(lines), F)
        self.assertEqual(len(res), F)

    def test_the_sink_keys_on_the_whole_render_key(self):
        """Two lines that differ in any part of the render key are both
        kept; a bare line and its one-line span are one key."""
        sink = _sxi.ResidualSink()
        base = ("unresolved-reference", "p", (3, 3), "d")
        for line in (base, ("unsupported-project-form", "p", (3, 3), "d"), ("unresolved-reference", "q", (3, 3), "d"),
                     ("unresolved-reference", "p", (4, 4), "d"), ("unresolved-reference", "p", (3, 3), "e"),
                     ("unresolved-reference", "p", None, "d"), base, ("unresolved-reference", "p", 3, "d"),
                     ("unresolved-reference", "p", [(3, 3)], "d")):
            sink.append(line)
        self.assertEqual(len(sink), 6)
        self.assertEqual(sink[0], base)

    def test_an_unmapped_product_type_detail_is_charged_before_it_is_built(self):
        name = "N" * 400
        objects = {}
        objects["PROJ"] = _obj("PBXProject", mainGroup="MAIN", targets=["T"])
        objects["MAIN"] = _obj("PBXGroup", sourceTree="<group>", children=[])
        objects["T"] = _obj("PBXNativeTarget", name=name, productType="x.y.weird")
        text = "// !$*UTF8*$!\n" + _serialize({"archiveVersion": "1", "objectVersion": "56",
                                               "rootObject": "PROJ", "objects": objects}) + "\n"
        reads = SimpleNamespace(bundles=[("X.xcodeproj", True, True)], refusals={},
                                files={"X.xcodeproj/project.pbxproj": text.encode("utf-8")})
        for limit, expect_line in ((len(name) - 1, False), (len(name), True)):
            with self.subTest(limit=limit):
                budget = _sxi.CollectionBudget()
                budget.detail_limit = limit
                with tempfile.TemporaryDirectory() as tmp:
                    result = sx.read_projects(Path(tmp).resolve(), reads, [], collection=budget)
                unmapped = [r for r in result["residuals"] if "unmapped product type" in r[3]]
                self.assertEqual(len(unmapped), 1 if expect_line else 0)
                self.assertEqual(budget.detail_line() is None, expect_line)
                self.assertEqual([t["name"] for t in result["targets"]], [name])


class ReaderOrderIndependenceTests(unittest.TestCase):
    """The reader's output never depends on the order a
    host lists a directory in, or on the process's hash seed."""

    def _tree(self, root):
        _mkfile(root / "S" / "A.swift")
        _mkfile(root / "S" / "B.swift")
        _mkfile(root / "S" / "sub" / "C.swift")
        _mkfile(root / "S" / "L" / "en.lproj" / "x.swift")
        _mkfile(root / "S" / "L" / "de.lproj" / "x.swift")
        _mkfile(root / "Src" / "M.swift")
        _mkfile(root / "Src" / "N.swift")
        objects = _synced_objects(["sub", "/Localized/L/x.swift", "B.swift", "Missing.swift"], owners=3)
        objects["PH"] = _obj("PBXSourcesBuildPhase", files=["BM", "BN"])
        objects["X"] = _obj(sx._BUILD_PHASE_EXCEPTION_SET_ISA, buildPhase="PH", membershipExceptions=["A.swift"])
        objects["SR"]["exceptions"] = ["E", "X"]
        objects["MAIN"]["children"] = ["SR", "G"]
        objects["G"] = _obj("PBXGroup", sourceTree="<group>", path="Src", children=["FM", "FN"])
        objects["FM"] = _obj("PBXFileReference", sourceTree="<group>", path="M.swift")
        objects["FN"] = _obj("PBXFileReference", sourceTree="<group>", path="N.swift")
        objects["BM"] = _obj("PBXBuildFile", fileRef="FM")
        objects["BN"] = _obj("PBXBuildFile", fileRef="FN")
        objects["T1"]["buildPhases"] = ["PH"]
        objects["T2"]["buildPhases"] = ["PH"]
        return objects

    def test_a_reversed_listing_order_reads_the_same(self):
        real = os.scandir

        class Reversed:
            def __init__(self, path):
                with real(path) as it:
                    self.entries = list(it)[::-1]

            def __iter__(self):
                return iter(self.entries)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def close(self):
                pass

        results = []
        for shim in (None, Reversed):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                objects = self._tree(root)
                if shim is None:
                    result, _doc = _q9_derive(root, objects)
                else:
                    with mock.patch("os.scandir", shim):
                        result, _doc = _q9_derive(root, objects)
            results.append(result)
        self.assertEqual(results[0], results[1])
        # Not vacuous: the tree exercises every memoised route.
        files = {m["file"] for m in results[0]["memberships"]}
        self.assertTrue({"S/sub/C.swift", "S/L/de.lproj/x.swift", "S/L/en.lproj/x.swift", "Src/M.swift"} <= files,
                        files)

    def test_two_hash_seeds_derive_the_same_bytes(self):
        """Two derives through the real CLI under different
        `PYTHONHASHSEED` values write byte-identical architecture files."""
        import subprocess
        scripts = Path(__file__).resolve().parent.parent
        outputs = []
        for seed in ("1", "4242"):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                objects = self._tree(root)
                (root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: bionic\n')
                _mkfile(root / "bionic" / "manifest.yml", b'schema_version: "5"\nadr:\n  next_number: 1\n')
                doc_map = {"archiveVersion": "1", "objectVersion": "56", "rootObject": "PROJ", "objects": objects}
                _mkfile(root / "X.xcodeproj" / "project.pbxproj",
                        ("// !$*UTF8*$!\n" + _serialize(doc_map) + "\n").encode("utf-8"))
                env = dict(os.environ, PYTHONHASHSEED=seed)
                proc = subprocess.run([sys.executable, str(scripts / "derive-arch.py"), "--repo-root", str(root)],
                                      capture_output=True, text=True, timeout=300, env=env)
                self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
                arch = root / "bionic" / "arch"
                outputs.append({p.name: p.read_bytes() for p in sorted(arch.glob("*.md"))})
        self.assertEqual(outputs[0], outputs[1])
        graph = outputs[0]["module-graph.md"].decode("utf-8")
        self.assertIn("`S/sub/C.swift`", graph)
        self.assertIn("`Src/M.swift`", graph)
