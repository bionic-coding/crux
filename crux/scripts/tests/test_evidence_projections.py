"""Input projections and the release-neutral project version.

A declaration may name, for a path, the spans a release rewrites (``input_projections``): the digest
of that path then covers every other byte but not the located values. A lock requirement may bind the
project by name rather than by version (``project_version: release-neutral``). Both are opt-in: a
declaration without them normalizes, fingerprints and looks up exactly as it did before.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence_fixtures import PYPROJECT, SCRIPTS, conditional_dists, lock_requirement, make_venv, reseal_in_place, write_lock_project
import test_evidence as te
from test_evidence import EvidenceError, execute, lookup, normalize, snapshot

CLI = SCRIPTS / "test-evidence.py"
SHA = "a" * 64
FINGERPRINT = f"<!-- generated-from: README.md@sha256:{SHA}; model: model-x; date: 2026-01-01 -->"
FOOTER = "MIT licensed (see [LICENSE](./LICENSE)). v1.2.3 and an authored tail"

JSON_TEXT = '{\n  "name": "plugin",\n  "version": "1.2.3",\n  "meta": {"version": "9.9.9"}\n}\n'
TOML_TEXT = '[project]\nname = "p"\nversion = "1.2.3"\n\n[tool.other]\nversion = "9.9.9"\n'
LOCK_TEXT = ('version = 1\n\n[[package]]\nname = "dep"\nversion = "4.5.6"\n\n'
             '[[package]]\nname = "crux"\nversion = "1.2.3"\nsource = { editable = "." }\n')
README_TEXT = f"{FINGERPRINT}\n# Title\n\nBody text.\n\n{FOOTER}\n"

KINDS = {
    "json-string:version": ("a.json", JSON_TEXT),
    "toml-project-version": ("pyproject.toml", TOML_TEXT),
    "uv-lock-package-version:crux": ("uv.lock", LOCK_TEXT),
    "readme-footer-version": ("README.md", f"# Title\n\n{FOOTER}\n"),
    "generated-fingerprint-line": ("README.md", README_TEXT.replace(FOOTER, "")),
}


def bump(text, old="1.2.3", new="2.0.0"):
    return text.replace(f'"{old}"', f'"{new}"', 1) if f'"{old}"' in text else text.replace(f"v{old}", f"v{new}", 1)


def _raw(data):
    return hashlib.sha256(data).hexdigest()


def projected(text, *kinds):
    return te.projected_digest(text.encode(), kinds)


class DeclarationShapeTests(unittest.TestCase):
    def declaration(self, **extra):
        return dict({"check_id": "c", "command": ["python", "-c", "1"], "inputs": ["a.json"]}, **extra)

    def test_a_declaration_without_the_field_normalizes_without_it(self):
        self.assertNotIn("input_projections", normalize(self.declaration()))

    def test_the_field_is_validated_and_canonical(self):
        normalized = normalize(self.declaration(input_projections={"README.md": ["readme-footer-version", "generated-fingerprint-line"]}))
        self.assertEqual(normalized["input_projections"], {"README.md": ["generated-fingerprint-line", "readme-footer-version"]})
        for bad in ({}, {"a.json": []}, {"a.json": ["no-such-kind"]}, {"a.json": ["json-string:"]},
                    {"a.json": "json-string:version"}, {"/abs.json": ["json-string:version"]}, {"../x.json": ["json-string:version"]},
                    {"a.json": ["json-string:version", "json-string:version"]}, {"a.json": ["uv-lock-package-version:"]},
                    [["a.json", ["json-string:version"]]]):
            with self.assertRaises(EvidenceError, msg=bad):
                normalize(self.declaration(input_projections=bad))

    def test_project_version_is_emitted_only_when_release_neutral(self):
        def lock(**extra):
            return {"packages": {"lock": dict({"project": True}, **extra)}}
        neutral = normalize(self.declaration(requirement=lock(project_version="release-neutral")))
        self.assertEqual(neutral["requirement"]["packages"]["lock"]["project_version"], "release-neutral")
        for explicit in (lock(project_version="bound"), lock()):
            self.assertNotIn("project_version", normalize(self.declaration(requirement=explicit))["requirement"]["packages"]["lock"])
        for bad in (lock(project_version="loose"), lock(project_version=True), {"packages": {"lock": {"project": False, "project_version": "release-neutral"}}}):
            with self.assertRaises(EvidenceError, msg=bad):
                normalize(self.declaration(requirement=bad))


class GoldenTests(unittest.TestCase):
    """Computed with the engine before the projection change, then hard-coded."""

    DECLARATION = {"check_id": "golden", "command": ["python", "-c", "print(1)"], "inputs": ["a.txt", "sub"],
                   "environment": ["X"], "exclude_inputs": ["sub/skip"],
                   "requirement": {"interpreter": {"implementation": "cpython", "minors": ["3.13"]},
                                   "packages": {"lock": {"source": "subject", "project": True}}, "tools": ["git"]}}

    def test_a_declaration_without_the_new_fields_fingerprints_as_before(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.txt").write_text("alpha\n")
            (root / "sub").mkdir()
            (root / "sub" / "b.txt").write_text("beta\n")
            (root / "uv.lock").write_text('version = 1\n[[package]]\nname = "p"\nversion = "1.2.3"\n')
            (root / "pyproject.toml").write_text('[project]\nname = "p"\nversion = "1.2.3"\n')
            self.assertEqual(te.digest(normalize(self.DECLARATION)), "2af382818e70037f70e9b5e2d167576d9330ce8514fb03bd35666f157e7b13dc")
            self.assertEqual(snapshot(root, self.DECLARATION)["fingerprint"], "3d9c20aba491da993586461be2489af7dd8c11be50ec719590443a03d590e3f6")


class ProjectionTests(unittest.TestCase):
    def test_each_kind_masks_only_its_span(self):
        for kind, (_, text) in KINDS.items():
            with self.subTest(kind=kind):
                base = projected(text, kind)
                self.assertIsNotNone(base)
                if kind == "generated-fingerprint-line":
                    other = text.replace(SHA, "b" * 64).replace("model-x", "model-y").replace("2026-01-01", "2027-02-02")
                else:
                    other = bump(text)
                self.assertNotEqual(other, text)
                self.assertEqual(projected(other, kind), base)
                edited = text.replace("Title", "Titled").replace('"plugin"', '"plugin2"').replace('"p"', '"q"').replace('"dep"', '"dap"')
                if kind != "generated-fingerprint-line":
                    self.assertNotEqual(edited, text)
                    self.assertNotEqual(projected(edited, kind), base)

    def test_the_other_values_of_a_file_stay_hashed(self):
        self.assertNotEqual(projected(bump(JSON_TEXT, "9.9.9", "8.8.8"), "json-string:version"), projected(JSON_TEXT, "json-string:version"))
        self.assertNotEqual(projected(bump(TOML_TEXT, "9.9.9", "8.8.8"), "toml-project-version"), projected(TOML_TEXT, "toml-project-version"))
        self.assertNotEqual(projected(LOCK_TEXT.replace("4.5.6", "4.5.7"), "uv-lock-package-version:crux"), projected(LOCK_TEXT, "uv-lock-package-version:crux"))

    def test_a_nested_same_named_key_is_never_masked(self):
        nested_only = '{"name": "plugin", "meta": {"version": "1.2.3"}}\n'
        self.assertIsNone(projected(nested_only, "json-string:version"))
        self.assertNotEqual(te.input_digest(nested_only.encode(), ("json-string:version",)),
                            te.input_digest(nested_only.replace("1.2.3", "2.0.0").encode(), ("json-string:version",)))
        self.assertNotEqual(projected(JSON_TEXT.replace('"9.9.9"', '"8.8.8"'), "json-string:version"), projected(JSON_TEXT, "json-string:version"))
        toml_nested = '[project]\nname = "p"\n[tool.other]\nversion = "1.2.3"\n'
        self.assertIsNone(projected(toml_nested, "toml-project-version"))
        self.assertIsNone(projected('[tool.project]\nversion = "1.2.3"\n', "toml-project-version"))

    def test_the_staged_readme_projects_both_spans_and_nothing_else(self):
        kinds = ("generated-fingerprint-line", "readme-footer-version")
        base = projected(README_TEXT, *kinds)
        self.assertIsNotNone(base)
        both = README_TEXT.replace(SHA, "c" * 64).replace("date: 2026-01-01", "date: 2026-03-03").replace("v1.2.3", "v1.2.4")
        self.assertEqual(projected(both, *kinds), base)
        self.assertNotEqual(projected(README_TEXT.replace("Body text.", "Body edited."), *kinds), base)
        self.assertNotEqual(projected(README_TEXT.replace("authored tail", "edited tail"), *kinds), base)
        malformed_line = both.replace("c" * 64, "c" * 63)
        self.assertIsNone(projected(malformed_line, *kinds))
        self.assertNotEqual(te.input_digest(malformed_line.encode(), kinds), te.input_digest(README_TEXT.encode(), kinds))
        malformed_footer = README_TEXT.replace("v1.2.3", "v1.2")
        self.assertIsNone(projected(malformed_footer, *kinds))

    def test_a_value_outside_strict_format_falls_back_to_the_raw_digest(self):
        for value in ("1.2", "1.2.3-rc1", "01.2.3", "1.2.3.4", " 1.2.3", "v1.2.3", "@@projected@@"):
            with self.subTest(value=value):
                text = JSON_TEXT.replace('"1.2.3"', f'"{value}"', 1)
                self.assertIsNone(projected(text, "json-string:version"))
                self.assertEqual(te.input_digest(text.encode(), ("json-string:version",)), _raw(text.encode()))
                other = text.replace(f'"{value}"', f'"{value}0"', 1)
                self.assertNotEqual(te.input_digest(other.encode(), ("json-string:version",)), te.input_digest(text.encode(), ("json-string:version",)))
        self.assertIsNone(projected(TOML_TEXT.replace('"1.2.3"', '"1.2"', 1), "toml-project-version"))
        self.assertIsNone(projected(LOCK_TEXT.replace('"1.2.3"', '"1.2"'), "uv-lock-package-version:crux"))
        self.assertIsNone(projected(JSON_TEXT.replace('"version": "1.2.3"', '"version": 123'), "json-string:version"))

    def test_an_ambiguous_locator_falls_back_to_the_raw_digest(self):
        duplicate_json = '{"version": "1.2.3", "name": "x", "version": "1.2.3"}\n'
        self.assertIsNone(projected(duplicate_json, "json-string:version"))
        self.assertIsNone(projected(LOCK_TEXT + '\n[[package]]\nname = "crux"\nversion = "1.2.3"\n', "uv-lock-package-version:crux"))
        self.assertIsNone(projected(README_TEXT + f"\n{FOOTER}\n", "readme-footer-version", "generated-fingerprint-line"))
        self.assertIsNone(projected(LOCK_TEXT, "uv-lock-package-version:absent"))
        self.assertIsNone(projected("not json", "json-string:version"))
        self.assertIsNone(projected("[unterminated", "toml-project-version"))
        self.assertIsNone(projected(JSON_TEXT, "no-such-kind"))
        self.assertIsNone(te.projected_digest(b"\xff\xfe", ("json-string:version",)))

    def test_dotted_and_inline_tables_that_hide_the_span_fall_back(self):
        self.assertIsNone(projected('project.version = "1.2.3"\nproject.name = "p"\n', "toml-project-version"))
        self.assertIsNone(projected('project = { name = "p", version = "1.2.3" }\n', "toml-project-version"))
        fake = 'notes = """\n[project]\nversion = "1.2.3"\n"""\n[project]\nname = "p"\nversion = "3.0.0"\n'
        self.assertIsNone(projected(fake, "toml-project-version"))
        self.assertNotEqual(te.input_digest(fake.encode(), ("toml-project-version",)),
                            te.input_digest(fake.replace('"1.2.3"', '"1.2.4"', 1).encode(), ("toml-project-version",)))

    def test_a_raw_file_holding_the_placeholder_never_equals_a_projected_digest(self):
        placeholder = JSON_TEXT.replace("1.2.3", te.PROJECTION_PLACEHOLDER, 1)
        raw = te.input_digest(placeholder.encode(), ("json-string:version",))
        self.assertEqual(raw, _raw(placeholder.encode()))
        self.assertNotEqual(raw, projected(JSON_TEXT, "json-string:version"))
        masked = JSON_TEXT.replace("1.2.3", te.PROJECTION_PLACEHOLDER, 1)
        self.assertNotEqual(_raw(masked.encode()), projected(JSON_TEXT, "json-string:version"))

    def test_the_kind_list_is_part_of_the_digest(self):
        text = README_TEXT
        self.assertNotEqual(projected(text, "readme-footer-version"), projected(text, "readme-footer-version", "generated-fingerprint-line"))

    def test_overlapping_spans_fall_back(self):
        one_line = f"{FINGERPRINT}"
        self.assertIsNone(te.projected_digest(one_line.encode(), ("generated-fingerprint-line", "generated-fingerprint-line")))


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "a.json").write_text(JSON_TEXT)
        (self.root / "pyproject.toml").write_text(TOML_TEXT)
        (self.root / "README.md").write_text(README_TEXT)
        (self.root / "other.txt").write_text("other\n")

    def declaration(self, git=False, **extra):
        declaration = {"check_id": "c", "command": ["python", "-c", "1"], "inputs": ["a.json", "pyproject.toml", "README.md", "other.txt"],
                       "input_projections": {"a.json": ["json-string:version"], "pyproject.toml": ["toml-project-version"],
                                             "README.md": ["generated-fingerprint-line", "readme-footer-version"]}}
        if git:
            declaration["git_tracked"] = True
        return dict(declaration, **extra)

    def fingerprint(self, git=False):
        return snapshot(self.root, self.declaration(git))["fingerprint"]

    def release(self):
        for name in ("a.json", "pyproject.toml", "README.md"):
            path = self.root / name
            text = path.read_text().replace("1.2.3", "2.0.0", 1) if name != "README.md" else path.read_text().replace("v1.2.3", "v2.0.0").replace(SHA, "d" * 64)
            path.write_text(text)

    def test_a_release_only_change_keeps_the_fingerprint(self):
        before = self.fingerprint()
        self.release()
        self.assertEqual(self.fingerprint(), before)

    def test_a_non_version_edit_of_a_projected_file_changes_it(self):
        before = self.fingerprint()
        for name, old, new in (("a.json", '"plugin"', '"plugin2"'), ("pyproject.toml", '"p"', '"q"'), ("README.md", "Body text.", "Body edited."),
                               ("other.txt", "other", "another")):
            path = self.root / name
            original = path.read_text()
            path.write_text(original.replace(old, new))
            self.assertNotEqual(self.fingerprint(), before, name)
            path.write_text(original)
        self.assertEqual(self.fingerprint(), before)

    def test_a_declaration_with_and_without_projections_has_different_fingerprints(self):
        plain = self.declaration()
        del plain["input_projections"]
        self.assertNotEqual(snapshot(self.root, plain)["fingerprint"], self.fingerprint())

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=self.root,
                              capture_output=True, text=True, check=True)

    def test_worktree_index_and_head_each_project(self):
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        before = self.fingerprint(git=True)
        self.release()
        self.assertEqual(self.fingerprint(git=True), before)  # the worktree file projects; index and HEAD still old
        self.git("add", "-A")
        self.assertEqual(self.fingerprint(git=True), before)  # the index entry projects; HEAD still old
        self.git("commit", "-q", "-m", "release")
        self.assertEqual(self.fingerprint(git=True), before)  # the HEAD entry projects

    def test_a_non_version_edit_changes_each_git_place(self):
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        before = self.fingerprint(git=True)
        path = self.root / "a.json"
        path.write_text(JSON_TEXT.replace('"plugin"', '"plugin2"'))
        self.assertNotEqual(self.fingerprint(git=True), before)  # the worktree
        self.git("add", "a.json")
        path.write_text(JSON_TEXT)
        self.assertNotEqual(self.fingerprint(git=True), before)  # the index only: the worktree matches HEAD again
        self.git("add", "a.json")
        self.assertEqual(self.fingerprint(git=True), before)
        path.write_text(JSON_TEXT.replace('"plugin"', '"plugin2"'))
        self.git("add", "a.json")
        self.git("commit", "-q", "-m", "edit")
        path.write_text(JSON_TEXT)
        self.git("add", "a.json")
        self.assertNotEqual(self.fingerprint(git=True), before)  # HEAD only: worktree and index equal the base again

    def test_a_malformed_value_invalidates_in_the_git_places_too(self):
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        before = self.fingerprint(git=True)
        (self.root / "a.json").write_text(JSON_TEXT.replace("1.2.3", "2.0"))
        self.assertNotEqual(self.fingerprint(git=True), before)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "malformed")
        (self.root / "a.json").write_text(JSON_TEXT)
        self.assertNotEqual(self.fingerprint(git=True), before)


class ReleaseNeutralLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        parent = Path(cls._tmp.name)
        cls.python = make_venv(parent, "current", conditional_dists(True))
        cls.other_version = make_venv(parent, "other", [("dep-a", "1.0"), *conditional_dists(False)[1:], ("fixture-project", "0.0.9")])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        patcher = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.root / "evidence")})
        patcher.start()
        self.addCleanup(patcher.stop)
        write_lock_project(self.root)
        (self.root / "input.txt").write_text("one")

    def declaration(self, neutral=True):
        requirement = lock_requirement(True)
        if neutral:
            requirement["packages"]["lock"]["project_version"] = "release-neutral"
        return {"check_id": "tools", "command": ["python", "-c", "print('ok')"], "inputs": ["input.txt"], "environment": [], "requirement": requirement}

    def record(self, neutral=True, python=None):
        return execute(self.root, self.declaration(neutral), interpreter=python or self.python)["evidence"]

    def edit_lock(self, old, new):
        path = self.root / "uv.lock"
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new))

    def bump_project_version(self):
        self.edit_lock('name = "fixture-project"\nversion = "0.1.0"', 'name = "fixture-project"\nversion = "0.1.1"')
        (self.root / "pyproject.toml").write_text(PYPROJECT.replace('version = "0.1.0"', 'version = "0.1.1"'))

    def test_a_version_only_change_keeps_the_receipt(self):
        passed = self.record()
        before = snapshot(self.root, self.declaration())["lock_sha256"]
        self.bump_project_version()
        self.assertEqual(snapshot(self.root, self.declaration())["lock_sha256"], before)
        found = lookup(self.root, self.declaration())
        self.assertEqual((found["state"], found["record"]["id"]), ("passed", passed["id"]))

    def test_the_default_binding_still_invalidates_on_a_version_change(self):
        self.record(neutral=False)
        self.bump_project_version()
        found = lookup(self.root, self.declaration(neutral=False))
        self.assertNotEqual(found["state"], "passed")

    def test_the_neutral_digest_differs_from_the_bound_digest(self):
        self.assertNotEqual(snapshot(self.root, self.declaration())["lock_sha256"], snapshot(self.root, self.declaration(neutral=False))["lock_sha256"])

    def test_a_recorded_project_distribution_at_another_version_is_accepted_only_when_neutral(self):
        neutral = self.record(python=self.other_version)
        self.assertEqual(lookup(self.root, self.declaration())["state"], "passed")
        self.assertEqual(lookup(self.root, self.declaration())["record"]["id"], neutral["id"])
        bound = lookup(self.root, self.declaration(neutral=False))
        self.assertNotEqual(bound["state"], "passed")

    def test_a_third_party_package_change_invalidates(self):
        self.record()
        self.edit_lock('name = "dep-a"\nversion = "1.0"', 'name = "dep-a"\nversion = "1.1"')
        self.assertEqual(lookup(self.root, self.declaration())["state"], "inputs-changed")

    def test_a_third_party_hash_change_invalidates(self):
        hash_a, hash_b = "sha256:" + "a" * 64, "sha256:" + "b" * 64
        dep = 'name = "dep-a"\nversion = "1.0"\nsource = { registry = "https://pypi.org/simple" }\n'
        self.edit_lock(dep, dep + f'sdist = {{ url = "https://example.invalid/dep-a-1.0.tar.gz", hash = "{hash_a}" }}\n')
        self.record()
        self.assertEqual(lookup(self.root, self.declaration())["state"], "passed")
        self.edit_lock(hash_a, hash_b)
        self.assertEqual(lookup(self.root, self.declaration())["state"], "inputs-changed")

    def test_the_project_distribution_must_be_recorded_exactly_once_by_name(self):
        recorded = self.record()
        store = self.root / "evidence"
        reseal_in_place(store, recorded["id"], lambda r: r["environment"]["distributions"].append(["fixture-project", "9.9.9"]))
        self.assertNotEqual(lookup(self.root, self.declaration())["state"], "passed")
        reseal_in_place(store, recorded["id"], lambda r: r["environment"].update(
            distributions=[d for d in r["environment"]["distributions"] if d[0] != "fixture-project"]))
        self.assertNotEqual(lookup(self.root, self.declaration())["state"], "passed")

    def test_a_third_party_package_set_difference_is_still_refused(self):
        recorded = self.record()
        store = self.root / "evidence"
        reseal_in_place(store, recorded["id"], lambda r: r["environment"]["distributions"].append(["extra-package", "1.0"]))
        self.assertNotEqual(lookup(self.root, self.declaration())["state"], "passed")


class CommandLineBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = self.root / "store"
        patcher = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.store)})
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.root / "a.json").write_text(JSON_TEXT)
        self.base = {"check_id": "unit", "command": ["python", "-c", "print('ok')"], "inputs": ["a.json"], "environment": []}
        self.projected = dict(self.base, input_projections={"a.json": ["json-string:version"]})
        self.neutral = dict(self.base, requirement={"packages": {"lock": {"project": True, "project_version": "release-neutral"}}})

    def check(self, declaration):
        path = self.root / "check.json"
        path.write_text(json.dumps(declaration))
        return path

    def run_cli(self, *args):
        run = subprocess.run([sys.executable, str(CLI), "--repo-root", str(self.root), *args], capture_output=True, text=True)
        return run.returncode, run.stdout, run.stderr

    def test_run_and_lookup_refuse_an_unregistered_declaration_with_either_field(self):
        for action in ("run", "lookup"):
            for declaration, field in ((self.projected, "input_projections"), (self.neutral, "project_version")):
                with self.subTest(action=action, field=field):
                    code, out, err = self.run_cli(action, "--check", str(self.check(declaration)))
                    self.assertEqual(code, 2)
                    self.assertIn(field, err)
                    self.assertEqual(out, "")
        self.assertFalse(self.store.exists() and any(self.store.glob("TE-*.json")))

    def test_the_plain_declaration_is_unaffected(self):
        code, out, err = self.run_cli("run", "--check", str(self.check(self.base)))
        self.assertEqual((code, err), (0, ""), out)
        code, out, _ = self.run_cli("lookup", "--check", str(self.check(self.base)))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["state"], "passed")

    def test_a_default_project_version_normalizes_away_and_is_allowed(self):
        write_lock_project(self.root)
        bound = dict(self.base, requirement={"packages": {"lock": {"project": True, "project_version": "bound"}}})
        code, out, err = self.run_cli("lookup", "--check", str(self.check(bound)))
        self.assertEqual((code, err), (1, ""), out)
        self.assertEqual(json.loads(out)["state"], "missing")

    def load_cli(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("test_evidence_cli_under_test", CLI)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_a_declaration_equal_to_the_registered_one_is_accepted(self):
        module = self.load_cli()
        registered = copy.deepcopy(self.projected)
        argv = ["test-evidence.py", "--repo-root", str(self.root), "run", "--check", str(self.check(self.projected))]
        with patch.object(module.suite_evidence, "registered_declaration", return_value=registered), patch.object(sys, "argv", argv), \
                patch("builtins.print"):
            self.assertEqual(module.main(), 0)
        different = dict(registered, input_projections={"a.json": ["json-string:name"]})
        with patch.object(module.suite_evidence, "registered_declaration", return_value=different), patch.object(sys, "argv", argv), \
                patch("sys.stderr") as stderr:
            self.assertEqual(module.main(), 2)
        self.assertIn("input_projections", "".join(call.args[0] for call in stderr.write.call_args_list))

    def test_declare_refuses_a_requirement_with_project_version(self):
        requirement = json.dumps({"packages": {"lock": {"project": True, "project_version": "release-neutral"}}})
        code, out, err = self.run_cli("declare", "--preset", "whole-tree", "--check-id", "x", "--command", '["python", "-c", "1"]', "--requirement", requirement)
        self.assertEqual(code, 2)
        self.assertIn("project_version", err)
        self.assertEqual(out, "")
        plain = json.dumps({"tools": ["git"]})
        code, out, err = self.run_cli("declare", "--preset", "whole-tree", "--check-id", "x", "--command", '["python", "-c", "1"]', "--requirement", plain)
        self.assertEqual((code, err), (0, ""))
        self.assertNotIn("project_version", out)

    def test_validate_and_report_read_receipts_that_carry_the_fields(self):
        ran = execute(self.root, self.projected)["evidence"]
        self.assertEqual(ran["declaration"]["input_projections"], {"a.json": ["json-string:version"]})
        for args in (("validate", "--evidence-id", ran["id"]), ("report", "--evidence-id", ran["id"])):
            code, out, err = self.run_cli(*args)
            self.assertEqual((code, err), (0, ""), args)
            self.assertTrue(out.strip())
        (self.root / "a.json").write_text(JSON_TEXT.replace("1.2.3", "2.0.0"))
        self.assertEqual(self.run_cli("validate", "--evidence-id", ran["id"])[0], 0)
        (self.root / "a.json").write_text(JSON_TEXT.replace('"plugin"', '"plugin2"'))
        self.assertEqual(self.run_cli("validate", "--evidence-id", ran["id"])[0], 2)


if __name__ == "__main__":
    unittest.main()
