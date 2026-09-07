"""ADR-0096 clause 6: detection resolves or names its ambiguity.

Four claims, one test class each.

  * The pack registry is ONE structure and it records a PAIRWISE precedence.
    Before this unit the registry was a five-name tuple whose ORDER was the
    precedence, so "registered" and "beats" were the same fact read two ways and
    every pair was decided whether or not anything justified deciding it.
  * A pin still wins, and an unregistered pin is still the fail-closed error of
    ADR-0066 clause 10.
  * Auto-detection scans marker files at a depth of at most two directories
    below the repository root, not at the root only.
  * A multi-match the recorded precedence does not resolve reports
    `stubbed: ambiguous_stack` NAMING each candidate and the marker that matched
    it, and more than one candidate package reports `stubbed: ambiguous_package`
    naming them. Neither detector returns a silent pick and neither returns a
    silent None.

Stdlib only. Every test builds its repository in a fresh tempdir — never this
repo's real tree.
"""

from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]      # crux/scripts
sys.path.insert(0, str(SCRIPTS))

core = importlib.import_module("crux.arch.core")
python_pack = importlib.import_module("crux.arch.packs.python")


class _Cfg:
    """Minimal stand-in for a BionicConfig — only the attributes the seam reads."""

    def __init__(self, arch_stack=None, arch_extractors=None, source=".bionic.yml"):
        self.arch_stack = arch_stack
        self.arch_extractors = arch_extractors or {}
        self.source = source


class _RepoCase(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.addCleanup(self._d.cleanup)
        self.root = Path(self._d.name)

    def write(self, rel: str, text: str = "") -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def mark_crux(self, prefix: str = "") -> None:
        base = self.root / prefix if prefix else self.root
        (base / "crux" / "skills").mkdir(parents=True)
        (base / "crux" / "schemas").mkdir(parents=True)


class PackRegistryTests(_RepoCase):
    """The registry is one structure, and the precedence in it is pairwise."""

    def test_registry_is_the_single_structure_and_the_views_derive_from_it(self):
        names = tuple(e.name for e in core.PACK_REGISTRY)
        self.assertEqual(core.PACK_NAMES, names)
        self.assertEqual(core.REGISTERED_PACKS, frozenset(names))
        self.assertEqual(len(set(names)), len(names), "a pack is registered twice")

    def test_every_registry_row_carries_a_pairwise_beats_set_and_a_reason(self):
        for entry in core.PACK_REGISTRY:
            with self.subTest(pack=entry.name):
                self.assertIsInstance(entry.beats, frozenset)
                self.assertNotIn(entry.name, entry.beats, "a pack beats itself")
                unknown = entry.beats - core.REGISTERED_PACKS
                self.assertEqual(unknown, set(), f"beats an unregistered pack: {unknown}")
                if entry.beats:
                    self.assertTrue(entry.why.strip(),
                                    "a recorded precedence with no recorded reason")

    def test_the_precedence_is_partial_not_a_total_order(self):
        """The point of the change, asserted rather than described.

        A total order decides every pair, so `ambiguous_stack` would be
        unreachable and clause 6's second half would be dead code. At least one
        pair must be UNRECORDED, and the registry must not silently rank it.
        """
        undecided = [
            (a.name, b.name)
            for a in core.PACK_REGISTRY for b in core.PACK_REGISTRY
            if a.name < b.name and b.name not in a.beats and a.name not in b.beats
        ]
        self.assertTrue(undecided, "every pair is decided — the precedence is a total "
                                   "order again and ambiguous_stack is unreachable")

    def test_the_recorded_precedence_is_antisymmetric_and_acyclic(self):
        beats = {e.name: e.beats for e in core.PACK_REGISTRY}
        for a, wins in beats.items():
            for b in wins:
                self.assertNotIn(a, beats[b], f"{a} and {b} each beat the other")
        # No cycle: repeated removal of an unbeaten pack must exhaust the set.
        remaining = set(beats)
        while remaining:
            unbeaten = {c for c in remaining
                        if not any(c in beats[o] for o in remaining if o != c)}
            self.assertTrue(unbeaten, f"precedence cycle among {sorted(remaining)}")
            remaining -= unbeaten


class PinFirstTests(_RepoCase):
    """Pin-first is unchanged (ADR-0066 clause 10)."""

    def test_a_pin_wins_over_every_detected_candidate(self):
        self.mark_crux()
        self.write("pyproject.toml", "[project]\n")
        self.write("Gemfile", "")
        for name in sorted(core.REGISTERED_PACKS):
            with self.subTest(pin=name):
                res = core.resolve_stack(self.root, _Cfg(arch_stack=name))
                self.assertEqual(res.pack_name, name)
                self.assertTrue(res.pinned)
                self.assertIsNone(res.ambiguity)

    def test_an_unregistered_pin_is_still_the_fail_closed_error(self):
        with self.assertRaises(ValueError):
            core.resolve_stack(self.root, _Cfg(arch_stack="cobol"))
        with self.assertRaises(ValueError):
            core.detect_stack(self.root, _Cfg(arch_stack="cobol"))

    def test_a_pin_does_not_scan_so_an_otherwise_ambiguous_repo_resolves(self):
        self.write("pyproject.toml", "[project]\n")
        self.write("Gemfile", "")
        self.assertEqual(core.detect_stack(self.root, _Cfg(arch_stack="ruby")), "ruby")


class DepthTwoScanTests(_RepoCase):
    """Markers are scanned at depth <= 2, not at the root only."""

    def test_the_declared_depth_is_two(self):
        self.assertEqual(core.DETECTION_MAX_DEPTH, 2)

    def test_a_marker_one_directory_down_is_found(self):
        self.write("app/package.json", "{}")
        cands = core.detect_candidates(self.root)
        self.assertEqual(sorted(cands), ["node"])
        self.assertEqual(cands["node"], ("app/package.json",))
        self.assertEqual(core.detect_stack(self.root, None), "node")

    def test_a_marker_two_directories_down_is_found(self):
        self.write("services/api/mix.exs", "")
        self.assertEqual(core.detect_stack(self.root, None), "elixir")
        self.assertEqual(core.detect_candidates(self.root)["elixir"],
                         ("services/api/mix.exs",))

    def test_a_marker_three_directories_down_is_not(self):
        self.write("a/b/c/Gemfile", "")
        self.assertEqual(core.detect_candidates(self.root), {})
        self.assertEqual(core.detect_stack(self.root, None), core.STUB_PACK_NAME)

    def test_the_scan_skips_vendor_and_dot_directories(self):
        self.write("node_modules/thing/package.json", "{}")
        self.write(".hidden/pkg/mix.exs", "")
        self.assertEqual(core.detect_candidates(self.root), {})

    def test_markers_are_reported_repo_relative_and_sorted(self):
        self.write("package.json", "{}")
        self.write("web/package.json", "{}")
        self.write("api/package.json", "{}")
        self.assertEqual(core.detect_candidates(self.root)["node"],
                         ("api/package.json", "package.json", "web/package.json"))

    def test_no_marker_anywhere_is_still_the_empty_pack(self):
        self.write("README.md", "hi\n")
        self.assertEqual(core.detect_stack(self.root, None), core.STUB_PACK_NAME)


class RecordedPrecedenceResolvesTests(_RepoCase):
    """A multi-match the registry DOES decide resolves silently and correctly."""

    def test_ruby_over_node_the_rails_asset_pipeline_case(self):
        self.write("Gemfile", "")
        self.write("package.json", "{}")
        self.assertEqual(core.detect_stack(self.root, None), "ruby")
        self.assertIsNone(core.resolve_stack(self.root, None).ambiguity)

    def test_python_over_node_the_python_service_with_a_js_frontend(self):
        """Co-located ON PURPOSE — this is the pair's own measured shape.

        The registry's `python beats node` entry was measured on
        `fastapi-fullstack`, which carries `pyproject.toml` and `package.json`
        at the ROOT. Writing the `package.json` one directory down would let
        `_undominated`'s depth stage resolve this before the pair is ever
        consulted, and the test would then pass without exercising the thing it
        is named for.
        """
        self.write("pyproject.toml", "[project]\n")
        self.write("package.json", "{}")
        self.assertEqual(core.detect_stack(self.root, None), "python")

    def test_elixir_over_node_the_phoenix_assets_case(self):
        self.write("mix.exs", "")
        self.write("assets/package.json", "{}")
        self.assertEqual(core.detect_stack(self.root, None), "elixir")

    def test_crux_over_python_this_repository_s_own_shape(self):
        self.mark_crux()
        self.write("pyproject.toml", "[project]\n")
        self.assertEqual(core.detect_stack(self.root, None), "crux")


class DepthScopedPrecedenceTests(_RepoCase):
    """`beats` is depth-scoped: a shallower marker never loses to a deeper one.

    Every pair in the registry was measured on a repository carrying both
    markers at ONE depth, and root-only detection made that the only shape a
    multi-match could take. Clause 6's depth-two scan removed that premise. A
    depth-blind `beats` then resolved matches nothing ever measured, and the
    cost was a whole pack's extraction: an Express repository that vendors a
    Python helper directory resolved to `python` and rendered three
    `precondition_missing` stubs where node routes, models and edges belong.
    """

    def test_a_root_marker_is_not_beaten_by_a_deeper_one(self):
        """The regression case, verbatim.

        `package.json` at the root, `tools/setup.py` one directory down. The
        registry records `python beats node`, measured on a repository carrying
        both at the root. Applying it here resolves `python` — three stubs for a
        Node repository — from a pair that says nothing about this shape.
        """
        self.write("package.json", "{}")
        self.write("tools/setup.py", "from setuptools import setup\n")

        markers, depths = core._scan_candidates(self.root)
        self.assertEqual(markers, {"python": ("tools/setup.py",),
                                   "node": ("package.json",)})
        self.assertEqual(depths, {"python": 1, "node": 0})

        res = core.resolve_stack(self.root, None)
        self.assertEqual(res.pack_name, "node")
        self.assertIsNone(res.ambiguity, "a depth-resolved match is not an ambiguity")

    def test_the_deeper_pack_loses_even_two_directories_down(self):
        self.write("package.json", "{}")
        self.write("services/helper/Gemfile", "")
        self.assertEqual(core.detect_stack(self.root, None), "node")

    def test_depth_decides_in_the_direction_the_registry_already_agreed_with(self):
        """`elixir beats node` and depth agree on the Phoenix shape, so the
        relation becoming depth-scoped changes nothing there. Asserted so the
        two rules are known to point the same way rather than assumed to."""
        self.write("mix.exs", "")
        self.write("assets/package.json", "{}")
        _markers, depths = core._scan_candidates(self.root)
        self.assertEqual(depths, {"node": 1, "elixir": 0})
        self.assertEqual(core.detect_stack(self.root, None), "elixir")

    def test_beats_still_decides_among_packs_at_the_same_depth(self):
        """Both markers one directory down — equal depth, so the pair applies
        exactly as it does at the root. Depth scopes the relation; it does not
        retire it."""
        self.write("app/Gemfile", "")
        self.write("app/package.json", "{}")
        self.assertEqual(core.detect_stack(self.root, None), "ruby")

    def test_an_unrecorded_pair_at_the_floor_is_still_an_ambiguity(self):
        """Depth resolves what it can and hands the rest to `beats`. Where
        `beats` records nothing, the verdict is still named rather than picked —
        a deeper third candidate does not rescue it."""
        self.write("pyproject.toml", "[project]\n")
        self.write("Gemfile", "")
        self.write("web/package.json", "{}")
        res = core.resolve_stack(self.root, None)
        self.assertIsNotNone(res.ambiguity)
        self.assertEqual(res.pack_name, core.STUB_PACK_NAME)

    def test_the_ambiguity_names_every_matched_pack_including_a_dominated_one(self):
        """The report is not pruned to the contenders. A reader looking at three
        stubs needs to see everything the scan found."""
        self.write("pyproject.toml", "[project]\n")
        self.write("Gemfile", "")
        self.write("web/package.json", "{}")
        res = core.resolve_stack(self.root, None)
        self.assertEqual(res.ambiguity.candidates, ("node", "python", "ruby"))
        self.assertEqual(res.ambiguity.markers["node"], ("web/package.json",))

    def test_the_shallowest_of_several_markers_for_one_pack_is_the_depth(self):
        """A pack matching at two depths contends at the shallower one."""
        self.write("api/package.json", "{}")
        self.write("api/web/package.json", "{}")
        self.write("api/pyproject.toml", "[project]\n")
        _markers, depths = core._scan_candidates(self.root)
        self.assertEqual(depths["node"], 1)
        # Equal depth with python, so the recorded pair decides — not the fact
        # that node also matched deeper.
        self.assertEqual(core.detect_stack(self.root, None), "python")


class AmbiguousStackTests(_RepoCase):
    """An UNRECORDED multi-match names its candidates and their markers."""

    def _ambiguous_root(self) -> None:
        # python vs ruby: no precedence is recorded between them, because
        # nothing measured justifies one.
        self.write("pyproject.toml", "[project]\n")
        self.write("Gemfile", "")

    def test_an_unrecorded_multi_match_is_named_not_picked(self):
        self._ambiguous_root()
        res = core.resolve_stack(self.root, None)
        self.assertIsNotNone(res.ambiguity, "an unrecorded multi-match was picked silently")
        self.assertEqual(res.ambiguity.candidates, ("python", "ruby"))
        self.assertEqual(res.ambiguity.markers["python"], ("pyproject.toml",))
        self.assertEqual(res.ambiguity.markers["ruby"], ("Gemfile",))

    def test_the_three_stack_concerns_record_ambiguous_stack(self):
        self._ambiguous_root()
        tree = core._build(self.root, "bionic", "complete", None)
        cov = {r["concern"]: r for r in json.loads(tree["_meta/coverage.json"])["concerns"]}
        for concern in ("data-model", "api-surface", "module-graph"):
            with self.subTest(concern=concern):
                self.assertEqual(cov[concern]["verdict"], "stubbed")
                self.assertEqual(cov[concern]["stub_reason"], "ambiguous_stack")

    def test_the_stub_line_names_each_candidate_and_its_marker(self):
        self._ambiguous_root()
        tree = core._build(self.root, "bionic", "complete", None)
        line = [ln for ln in tree["data-model.md"].split("\n")
                if ln.startswith("> _stub:")]
        self.assertEqual(len(line), 1)
        for token in ("ambiguous_stack", "python", "pyproject.toml", "ruby", "Gemfile"):
            self.assertIn(token, line[0], f"the stub line does not name {token!r}")

    def test_decision_index_is_universal_and_is_not_made_ambiguous(self):
        """The ADR tree is stack-independent, so a stack ambiguity is not its
        ambiguity. It keeps whatever verdict its own input earns."""
        self._ambiguous_root()
        tree = core._build(self.root, "bionic", "complete", None)
        cov = {r["concern"]: r for r in json.loads(tree["_meta/coverage.json"])["concerns"]}
        self.assertNotEqual(cov["decision-index"]["stub_reason"], "ambiguous_stack")

    def test_ambiguity_never_renders_the_reserved_sentence(self):
        self._ambiguous_root()
        tree = core._build(self.root, "bionic", "complete", None)
        for fname in ("data-model.md", "api-surface.md", "module-graph.md"):
            self.assertNotIn(core.UNSUPPORTED_STACK_SENTENCE, tree[fname])

    def test_a_hostile_marker_filename_cannot_break_the_stub_line(self):
        """Ruby's marker is a `*.gemspec` GLOB, so a marker name is repo content
        — the first repo-derived token the stub line has ever carried.

        Two properties, and they are the two ways this line can be broken out
        of: a newline would end the blockquote, and a backtick would end a
        surrounding code span. A pipe is escaped rather than dropped, which is
        `_cell`'s table-safety behaviour and lossless here.
        """
        self.write("pyproject.toml", "[project]\n")
        self.write("a|b`c.gemspec", "")
        tree = core._build(self.root, "bionic", "complete", None)
        lines = [ln for ln in tree["data-model.md"].split("\n")
                 if ln.startswith("> _stub:")]
        self.assertEqual(len(lines), 1, "the marker name split the stub line")
        line = lines[0]
        self.assertNotIn("`", line)
        self.assertIn(r"a\|b", line)
        self.assertTrue(line.endswith("._"))


class AmbiguousPackageTests(_RepoCase):
    """Package detection reports EVERY candidate (clause 6)."""

    def _packages(self, *names: str) -> None:
        for n in names:
            self.write(f"{n}/__init__.py", "")
            self.write(f"{n}/mod.py", "x = 1\n")
        self.write("pyproject.toml", "[project]\nname = \"nothing-resolves\"\n")

    def test_detect_packages_returns_every_candidate(self):
        self._packages("alpha", "beta", "gamma")
        found = python_pack.detect_packages(self.root)
        self.assertEqual([name for _dir, name in found], ["alpha", "beta", "gamma"])

    def test_a_src_layout_and_a_top_level_package_are_both_candidates(self):
        """The tier-2 union, and the reason it is a union.

        The single-package detector returned early on exactly one `src/`
        package and otherwise fell through to the top-level scan. Carrying that
        shape forward as first-non-empty inverted the loss rather than fixing
        it: two `src/` packages plus one top-level package reported `alpha` and
        `beta` and never saw `gamma`. Three candidates exist here, and clause 6
        asks for every one.
        """
        self.write("src/alpha/__init__.py", "")
        self.write("src/beta/__init__.py", "")
        self.write("gamma/__init__.py", "")
        self.write("pyproject.toml", "[project]\nname = \"nothing-resolves\"\n")
        found = python_pack.detect_packages(self.root)
        self.assertEqual([name for _dir, name in found], ["alpha", "beta", "gamma"])
        self.assertIsNone(python_pack.detect_package(self.root),
                          "three candidates resolved to a single silent pick")

    def test_a_resolving_pyproject_hint_still_short_circuits_the_union(self):
        """Tier 1 is one candidate BY DECLARATION, so the union never runs."""
        self.write("src/declared/__init__.py", "")
        self.write("other/__init__.py", "")
        self.write("pyproject.toml", "[project]\nname = \"declared\"\n")
        found = python_pack.detect_packages(self.root)
        self.assertEqual([name for _dir, name in found], ["declared"])

    def test_one_candidate_still_resolves_and_the_single_accessor_agrees(self):
        self._packages("alpha")
        found = python_pack.detect_packages(self.root)
        self.assertEqual([name for _dir, name in found], ["alpha"])
        self.assertEqual(python_pack.detect_package(self.root)[1], "alpha")

    def test_more_than_one_candidate_records_ambiguous_package(self):
        self._packages("alpha", "beta")
        tree = core._build(self.root, "bionic", "complete", None)
        cov = {r["concern"]: r for r in json.loads(tree["_meta/coverage.json"])["concerns"]}
        self.assertEqual(cov["module-graph"]["stub_reason"], "ambiguous_package")

    def test_the_stub_line_names_every_candidate_package(self):
        self._packages("alpha", "beta")
        line = [ln for ln in core._build(self.root, "bionic", "complete", None)[
            "module-graph.md"].split("\n") if ln.startswith("> _stub:")][0]
        self.assertIn("alpha", line)
        self.assertIn("beta", line)

    def test_no_candidate_is_precondition_missing_not_ambiguity(self):
        """Zero candidates is an absent input, not a choice between candidates.
        Reusing `ambiguous_package` for it would break clause 3's "no reason is
        reused for a second condition"."""
        self.write("pyproject.toml", "[project]\nname = \"nothing-resolves\"\n")
        tree = core._build(self.root, "bionic", "complete", None)
        cov = {r["concern"]: r for r in json.loads(tree["_meta/coverage.json"])["concerns"]}
        self.assertEqual(cov["module-graph"]["stub_reason"], "precondition_missing")


class RequirementsTxtMarkerTests(_RepoCase):
    """`requirements.txt` is a python marker, because omitting it produced a
    SILENT WRONG PICK — the failure clause 6 exists to prevent.

    `wagtail-bakerydemo` is the measured case: a Django application with a root
    `package.json`, a root `requirements.txt`, and neither `pyproject.toml` nor
    `setup.py`. The python pack's markers fired NOWHERE, so `_undominated` saw a
    single contender and `resolve_stack` answered `node` with no ambiguity
    recorded — there was no multi-match to be ambiguous about. Three
    `precondition_missing` stubs followed, for a repository whose models, URLconf
    and package the python pack reads.

    An ambiguity is a legitimate answer here and a silent wrong pack is not,
    which is why the fix is a marker rather than a carve-out.
    """

    def test_a_requirements_txt_alone_resolves_to_python(self):
        self.write("requirements.txt", "django>=5.0\n")
        markers, depths = core._scan_candidates(self.root)
        self.assertEqual(markers.get("python"), ("requirements.txt",))
        self.assertEqual(core.resolve_stack(self.root, None).pack_name, "python")

    def test_the_django_shape_no_longer_resolves_silently_to_node(self):
        """The regression case, verbatim: both files at the root."""
        self.write("package.json", "{}")
        self.write("requirements.txt", "django>=5.0\n")

        markers, depths = core._scan_candidates(self.root)
        self.assertEqual(markers, {"python": ("requirements.txt",),
                                   "node": ("package.json",)})
        self.assertEqual(depths, {"python": 0, "node": 0})

        res = core.resolve_stack(self.root, None)
        self.assertEqual(res.pack_name, "python",
                         "a Django application resolved to node, silently")
        self.assertIsNone(
            res.ambiguity,
            "`python beats node` is recorded and both markers sit at depth 0, "
            "so this is a measured precedence rather than a guess")

    def test_a_deeper_requirements_txt_still_loses_to_a_root_package_json(self):
        """The new marker does not escape the depth rule: a vendored Python
        helper directory must not take a Node repository's extraction."""
        self.write("package.json", "{}")
        self.write("tools/requirements.txt", "requests\n")
        self.assertEqual(core.resolve_stack(self.root, None).pack_name, "node")

    def test_the_marker_list_is_what_detect_reports(self):
        pack = python_pack
        self.write("pyproject.toml", "")
        self.write("requirements.txt", "")
        self.write("setup.py", "")
        result = pack.detect(self.root)
        self.assertTrue(result.matched)
        self.assertEqual(result.markers, pack._PYTHON_MARKERS)
        self.assertIn("requirements.txt", pack._PYTHON_MARKERS)


class ThisRepositoryTests(unittest.TestCase):
    """The one real repository these tests may read: this checkout."""

    def test_this_checkout_still_resolves_to_the_crux_pack_unpinned(self):
        repo_root = SCRIPTS.parents[1]
        self.assertEqual(core.detect_stack(repo_root, None), "crux")
        self.assertIsNone(core.resolve_stack(repo_root, None).ambiguity)


if __name__ == "__main__":
    unittest.main()
