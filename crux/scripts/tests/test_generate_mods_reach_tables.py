"""Fixture tests for `generate-mods-reach-tables.py`.

The regenerator projects the capability manifest's names and its `notes` key into
the user guide's crux-mods section. Every fixture test builds its own tree in a
temporary directory at run time: a `USER_GUIDE.md` with text above and below the
markers, a seeded authoring probe, and a `crux-mods/hooks/capabilities.ts` that
holds the marker lines and `export const capabilities = {...} as const;`. No `.ts`
file is committed by this module and nothing here registers a mod hook under
`crux/`, so the no-mod-hooks-in-crux test stays clean.

Every expected region and every `validation_errors` list below is a literal written
out by hand. No test computes an expected value with the code under test.

A CONSEQUENCE FOR LATER BOOKS. The live surface-parts literal, the pinned `never`
literal and the From cross-check belong to this file, and a later book's phase
radius (`crux-mods/hooks/`, `crux-mods/tests/` and the guide's crux-mods section)
does not reach it. A phase book that changes a drawn part, a reader key, an event
property the dashboard reads or `notes.never` must declare
`crux/scripts/tests/test_generate_mods_reach_tables.py`. A book that adds a
manifest name must also add its note, or the regenerator fails closed.

Refused characters are built with `chr()`, never written raw.

The classes after the fixture tests read the plugin's own checkout: the live
manifest, the guide, the dashboard's TypeScript, `tools/mods_gate.py` and the public
guide. They skip on the staged artifact, keyed on the repo-root `AGENTS.md`.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _authoring_fixture import seed_authoring_probe
from _dev_surface import REPO_ROOT, require_dev_surface

SCRIPTS = Path(__file__).resolve().parents[1]
SCRIPT = SCRIPTS / "generate-mods-reach-tables.py"

GUIDE = "USER_GUIDE.md"
MANIFEST = "crux-mods/hooks/capabilities.ts"
BEGIN = "<!-- BEGIN GENERATED: mods-reach -->"
END = "<!-- END GENERATED: mods-reach -->"

MIDDOT = chr(0xB7)
BAND = "ui.render{component=Band}"
OBS = "session.start"
FINGERPRINT = ("<!-- generated-from: USER_GUIDE.md@sha256:" + "ab" * 32
               + "; model: claude-x; date: 2026-10-14 -->")

PREFIX = "# The guide\n\nIntro text above the region.\n\n### What it can reach\n\n"
SUFFIX = "\n\nText below the region.\n\n### When it cannot show a view\n\nBody.\n"
STALE = "\nstale text a person typed here\n"


def entry(sees, keeps):
    return {"sees": sees, "keeps": keeps}


def base_manifest():
    return {
        "format_version": 1,
        "plugin": "crux-mods",
        "claude_code": {"min": "2.1.287"},
        "events": [
            {"event": BAND, "behaviour": "draw", "decision": None},
            {"event": OBS, "behaviour": "observe", "decision": None},
        ],
        "calls": ["$.agent.list", "$.fs.read"],
        "env_reads": ["HOME", "LD_PRELOAD", "LD_AUDIT"],
        "env_writes": [],
        "launch": {
            "launcher": "/usr/bin/env",
            "launcher_args": ["-i"],
            "uv_locations": ["/opt/uv", "{HOME}/.local/bin/uv"],
            "uv_args": ["run", "--offline"],
            "env_allow": ["HOME", "PATH"],
            "loader_vars": ["LD_PRELOAD", "LD_AUDIT"],
            "scripts": {"reader-one": {"path": "scripts/reader-one.py",
                                       "args": ["--json", "{project_root}"]}},
            "timeout_ms": 10000,
        },
        "notes": {
            "events": {
                BAND: {"sees": "the run files " + MIDDOT + " a book title | its state",
                       "keeps": "nothing; it draws and forgets",
                       "surface": "the band above the prompt"},
                OBS: entry("the session start", "nothing"),
            },
            "calls": {
                "$.agent.list": entry("the running subagents", "nothing"),
                "$.fs.read": entry("run files, using `$.fs.read`", "nothing"),
            },
            "env_reads": {"HOME": entry("your home directory", "the path passed to the reader")},
            "loader_vars": entry("the dynamic loader settings", "nothing; each is refused"),
            "env_writes": {},
            "launch": {"reader-one": entry("the project's run files", "nothing")},
            "never": "It makes no network request.",
            "surfaces": [
                {"event": BAND, "part": "the book title",
                 "from": ["reader-one:runs[].title", "$.agent.list:status",
                          BAND + ":props.placement", "launch:outcome"]},
            ],
        },
    }


def with_write(m):
    m["env_writes"] = ["CRUX_FLAG"]
    m["notes"]["env_writes"]["CRUX_FLAG"] = entry("a flag it sets", "the flag value")


REGION_HEAD = (
    "\n\n"
    "The capability manifest, `crux-mods/hooks/capabilities.ts`, lists everything the mod can "
    "reach. Each row is one entry: an event it handles, a call it makes on `$`, an "
    "environment variable it reads, or the process it starts.\n\n"
    "| Through | Kind | What it sees | What it keeps |\n"
    "|---|---|---|---|\n"
    "| `ui.render{component=Band}` | event (draw) | the run files " + MIDDOT
    + " a book title \\| its state | nothing; it draws and forgets |\n"
    "| `session.start` | event (observe) | the session start | nothing |\n"
    "| `$.agent.list` | call | the running subagents | nothing |\n"
    "| `$.fs.read` | call | run files, using `$.fs.read` | nothing |\n"
    "| `HOME` | environment read | your home directory | the path passed to the reader |\n"
    "| `LD_PRELOAD`, `LD_AUDIT` | environment read (dynamic loader) | "
    "the dynamic loader settings | nothing; each is refused |\n"
)
REGION_PROCESS_ROW = "| `reader-one` | process | the project's run files | nothing |\n\n"
REGION_WRITE_ROW = "| `CRUX_FLAG` | environment write | a flag it sets | the flag value |\n"
REGION_NO_OTHER = ("It handles no other event, makes no other call and reads no other "
                   "environment variable. ")
REGION_LAUNCH = (
    "To run `reader-one`, it starts `/usr/bin/env -i <variables> <uv> run --offline "
    "<crux>/scripts/reader-one.py --json {project_root}`. "
    "`<variables>` stands for the only variables the process starts with: `HOME` and `PATH`. "
    "`<uv>` is the first file found among `/opt/uv` and `{HOME}/.local/bin/uv`. "
    "`<crux>` is the installed crux plugin's directory. "
    "`{project_root}` is the session's project root. "
    "`{HOME}` is the value of `HOME`.\n\n"
    "It makes no network request.\n\n"
    "Each row below is one part of what the mod draws. The From column names what that part "
    "draws from: a field of the reader's output, a subagent field, a property of the event, "
    "or the launch outcome.\n\n"
    "| Where | Shows | From |\n"
    "|---|---|---|\n"
    "| the band above the prompt | the book title | `reader-one:runs[].title`, "
    "`$.agent.list:status`, `ui.render{component=Band}:props.placement`, `launch:outcome` |\n\n"
    "To see the same events, calls, environment variables and session state listed by Claude Code itself, "
    "run `claude plugin validate --strict` on the installed `crux-mods` directory.\n\n"
)
REGION_WRITES = (REGION_HEAD + REGION_WRITE_ROW + REGION_PROCESS_ROW + REGION_NO_OTHER
                 + "It sets only these variables in Claude Code's environment: `CRUX_FLAG`.\n\n"
                 + REGION_LAUNCH)
REGION = (REGION_HEAD + REGION_PROCESS_ROW + REGION_NO_OTHER
          + "It sets no variable in Claude Code's environment.\n\n" + REGION_LAUNCH)

MANIFEST_HEADER = "// The capability manifest (a test fixture).\n// BEGIN CAPABILITIES\n"
MANIFEST_FOOTER = " as const;\n// END CAPABILITIES\n"


def manifest_text(manifest):
    return (MANIFEST_HEADER + "export const capabilities = "
            + json.dumps(manifest, indent=2) + MANIFEST_FOOTER)


def guide_text(body=STALE, first=None):
    text = PREFIX + BEGIN + body + END + SUFFIX
    return text if first is None else first + "\n" + text


def expected_guide(region):
    return PREFIX + BEGIN + region + END + SUFFIX


def build(root, manifest=None, *, guide=None, text=None, probe=True):
    """A fixture tree: guide, manifest, authoring probe. Returns (guide, manifest) paths."""
    root = Path(root)
    if probe:
        seed_authoring_probe(root, "generate-mods-reach-tables.py")
    gpath = root / GUIDE
    if guide is not False:
        gpath.write_text(guide_text() if guide is None else guide, encoding="utf-8", newline="")
    mpath = root / MANIFEST
    mpath.parent.mkdir(parents=True, exist_ok=True)
    if text is None:
        text = manifest_text(base_manifest() if manifest is None else manifest)
    mpath.write_text(text, encoding="utf-8")
    return gpath, mpath


def run(root, *args, cwd=None, repo_root=True):
    cmd = [sys.executable, str(SCRIPT)]
    if repo_root:
        cmd += ["--repo-root", str(root)]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, text=True, check=False,
                          cwd=None if cwd is None else str(cwd))


def load_module():
    spec = importlib.util.spec_from_file_location("_mods_reach_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_mods_reach_under_test"] = module
    spec.loader.exec_module(module)
    return module


class TmpTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # macOS resolves the temporary root through /private; compare resolved paths.
        self.tmp = Path(tmp.name).resolve()
        self.root = self.tmp / "project"
        self.root.mkdir()

    def read_guide(self):
        return (self.root / GUIDE).read_bytes()


# ---------------------------------------------------------------------------- scope lanes


class SurfaceAbsentTests(TmpTestCase):
    def assert_absent(self, result):
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIs(True, payload["surface_absent"])
        self.assertIs(False, payload["drift"])
        self.assertNotEqual("", payload["reason"].strip())

    def test_the_positive_control_a_stale_region_is_rewritten(self):
        build(self.root)
        result = run(self.root)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            {"drift": False, "paths": [], "written": [GUIDE]}, json.loads(result.stdout))
        self.assertEqual(expected_guide(REGION).encode("utf-8"), self.read_guide())

    def test_no_authoring_probe_is_surface_absent(self):
        build(self.root, probe=False)
        before = self.read_guide()
        self.assert_absent(run(self.root))
        self.assertEqual(before, self.read_guide())

    def test_no_guide_is_surface_absent(self):
        build(self.root, guide=False)
        self.assert_absent(run(self.root))
        self.assertFalse((self.root / GUIDE).exists())

    def test_no_manifest_is_surface_absent(self):
        gpath, mpath = build(self.root)
        mpath.unlink()
        before = self.read_guide()
        self.assert_absent(run(self.root))
        self.assertEqual(before, self.read_guide())

    def test_an_exact_fingerprint_is_surface_absent(self):
        for ending in ("\n", "\r\n"):
            with self.subTest(ending=repr(ending)):
                guide = FINGERPRINT + ending + "# The public guide\n\nNo markers here.\n"
                build(self.root, guide=guide)
                self.assert_absent(run(self.root))
                self.assertEqual(guide.encode("utf-8"), self.read_guide())

    def test_near_miss_fingerprints_are_broken_not_absent(self):
        near = {
            "bare prefix": "<!-- generated-from:",
            "other source": FINGERPRINT.replace("USER_GUIDE.md@", "README.md@"),
            "short digest": FINGERPRINT.replace("ab" * 32, "ab" * 31 + "a"),
            "no fingerprint": "# A heading",
            "trailing text": FINGERPRINT + " extra",
        }
        for label, line in near.items():
            with self.subTest(case=label):
                guide = line + "\n\nNo markers here.\n"
                build(self.root, guide=guide)
                result = run(self.root)
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertEqual(
                    {"validation_errors": [{"code": "marker-missing", "where": GUIDE}]},
                    json.loads(result.stdout))
                self.assertEqual(guide.encode("utf-8"), self.read_guide())

    def test_is_public_fingerprint_accepts_only_the_whole_line(self):
        mod = load_module()
        self.assertTrue(mod.is_public_fingerprint(FINGERPRINT))
        self.assertFalse(mod.is_public_fingerprint(FINGERPRINT + " "))
        self.assertFalse(mod.is_public_fingerprint("x" + FINGERPRINT))
        self.assertFalse(mod.is_public_fingerprint(FINGERPRINT.replace("2026-10-14", "2026-1-14")))
        self.assertFalse(mod.is_public_fingerprint(FINGERPRINT.replace("model: claude-x", "model: ")))

    def test_help_shows_repo_root_and_dry_run(self):
        result = run(self.root, "--help", repo_root=False)
        self.assertEqual(0, result.returncode)
        self.assertIn("--repo-root", result.stdout)
        self.assertIn("--dry-run", result.stdout)

    def test_the_default_root_is_the_working_directory(self):
        build(self.root)
        result = run(self.root, "--dry-run", cwd=self.root, repo_root=False)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertEqual(
            {"drift": True, "paths": [GUIDE], "fix": "generate-mods-reach-tables.py"},
            json.loads(result.stdout))

    def test_a_working_directory_without_the_probe_is_surface_absent(self):
        other = self.tmp / "other"
        other.mkdir()
        result = run(other, "--dry-run", cwd=other, repo_root=False)
        self.assert_absent(result)


# ---------------------------------------------------------------------------- rendering


class RenderingTests(TmpTestCase):
    def test_the_fixture_region_is_written_exactly(self):
        build(self.root)
        result = run(self.root)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(expected_guide(REGION), self.read_guide().decode("utf-8"))

    def test_an_environment_write_renders_its_row_and_its_sentence(self):
        manifest = base_manifest()
        with_write(manifest)
        build(self.root, manifest)
        result = run(self.root)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(expected_guide(REGION_WRITES), self.read_guide().decode("utf-8"))

    def test_the_list_of_written_variables_joins_with_and(self):
        manifest = base_manifest()
        manifest["env_writes"] = ["A_ONE", "B_TWO", "C_THREE"]
        for name in manifest["env_writes"]:
            manifest["notes"]["env_writes"][name] = entry("a flag", "its value")
        build(self.root, manifest)
        self.assertEqual(0, run(self.root).returncode)
        self.assertIn(
            "It sets only these variables in Claude Code's environment: "
            "`A_ONE`, `B_TWO` and `C_THREE`.\n\n",
            self.read_guide().decode("utf-8"))

    def test_a_second_run_is_byte_identical_and_dry_run_is_clean(self):
        build(self.root)
        self.assertEqual(0, run(self.root).returncode)
        first = self.read_guide()
        second = run(self.root)
        self.assertEqual(0, second.returncode)
        self.assertEqual({"drift": False, "paths": [], "written": []}, json.loads(second.stdout))
        self.assertEqual(first, self.read_guide())
        dry = run(self.root, "--dry-run")
        self.assertEqual(0, dry.returncode)
        self.assertEqual({"drift": False, "paths": []}, json.loads(dry.stdout))

    def test_dry_run_on_an_edited_region_reports_drift_and_writes_nothing(self):
        build(self.root)
        self.assertEqual(0, run(self.root).returncode)
        edited = self.read_guide().replace(b"nothing", b"something", 1)
        (self.root / GUIDE).write_bytes(edited)
        result = run(self.root, "--dry-run")
        self.assertEqual(1, result.returncode)
        self.assertEqual(
            {"drift": True, "paths": [GUIDE], "fix": "generate-mods-reach-tables.py"},
            json.loads(result.stdout))
        self.assertEqual(edited, self.read_guide())

    def test_crlf_is_tolerated_and_bytes_outside_the_region_survive(self):
        guide = guide_text().replace("\n", "\r\n")
        build(self.root, guide=guide)
        result = run(self.root)
        self.assertEqual(0, result.returncode, result.stderr)
        expected = (PREFIX.replace("\n", "\r\n") + BEGIN + "\r" + REGION + END
                    + SUFFIX.replace("\n", "\r\n")).encode("utf-8")
        self.assertEqual(expected, self.read_guide())

    def test_permission_bits_survive_a_write(self):
        build(self.root)
        os.chmod(self.root / GUIDE, 0o640)
        self.assertEqual(0, run(self.root).returncode)
        self.assertEqual(0o640, (self.root / GUIDE).stat().st_mode & 0o777)
        self.assertFalse((self.root / ".USER_GUIDE.md.tmp").exists())

    def test_every_admitted_non_ascii_character_is_accepted(self):
        glyphs = "".join(chr(c) for c in (
            0xB7, 0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2026, 0x2205, 0x2296,
            0x2297, 0x2298, 0x25AC, 0x25AE, 0x25AF, 0x25B8, 0x25CC, 0x2713, 0x2717, 0x2B26))
        manifest = base_manifest()
        manifest["notes"]["calls"]["$.fs.read"]["keeps"] = glyphs
        build(self.root, manifest)
        self.assertEqual(0, run(self.root).returncode)
        self.assertIn("| " + glyphs + " |", self.read_guide().decode("utf-8"))

    def test_a_launch_with_no_placeholder_explains_none(self):
        # The positive control is REGION, whose launch carries both placeholders.
        manifest = base_manifest()
        manifest["launch"]["uv_locations"] = ["/opt/uv"]
        manifest["launch"]["scripts"]["reader-one"]["args"] = ["--json"]
        build(self.root, manifest)
        self.assertEqual(0, run(self.root).returncode)
        guide = self.read_guide().decode("utf-8")
        self.assertIn(
            "`<crux>` is the installed crux plugin's directory.\n\nIt makes no network request.",
            guide)
        self.assertNotIn("{project_root}", guide)
        self.assertNotIn("{HOME}", guide)

    def test_a_400_code_point_note_is_accepted(self):
        manifest = base_manifest()
        manifest["notes"]["calls"]["$.fs.read"]["keeps"] = "a" * 400
        build(self.root, manifest)
        self.assertEqual(0, run(self.root).returncode)

    def test_load_manifest_returns_the_whole_object_with_notes(self):
        _, mpath = build(self.root)
        mod = load_module()
        loaded = mod.load_manifest(mpath)
        self.assertEqual(base_manifest(), loaded)
        self.assertEqual(["session.start"], [e["event"] for e in loaded["events"]][1:])

    def test_load_manifest_refuses_a_duplicate_key(self):
        text = manifest_text(base_manifest()).replace(
            '"plugin": "crux-mods",', '"plugin": "crux-mods", "plugin": "other",')
        _, mpath = build(self.root, text=text)
        mod = load_module()
        with self.assertRaises(mod.ManifestError) as caught:
            mod.load_manifest(mpath)
        self.assertEqual(MANIFEST, caught.exception.where)


# ---------------------------------------------------------------------------- validation


class ValidationTests(TmpTestCase):
    def check(self, mutate, *errors, text=None, guide=None):
        manifest = base_manifest()
        if mutate is not None:
            mutate(manifest)
        gpath, _ = build(self.root, manifest, text=text, guide=guide)
        before = gpath.read_bytes()
        result = run(self.root)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertEqual(
            {"validation_errors": [{"code": c, "where": w} for c, w in errors]},
            json.loads(result.stdout))
        self.assertEqual(before, gpath.read_bytes())

    # the five kinds of manifest name, missing and orphan

    def test_missing_and_orphan_note_for_an_event(self):
        self.check(lambda m: m["notes"]["events"].pop(OBS),
                   ("missing-note", "notes.events[session.start]"))
        self.check(lambda m: m["notes"]["events"].update({"ghost.event": entry("a", "b")}),
                   ("orphan-note", "notes.events[ghost.event]"))

    def test_missing_and_orphan_note_for_a_call(self):
        self.check(lambda m: m["notes"]["calls"].pop("$.fs.read"),
                   ("missing-note", "notes.calls[$.fs.read]"))
        self.check(lambda m: m["notes"]["calls"].update({"$.ghost.call": entry("a", "b")}),
                   ("orphan-note", "notes.calls[$.ghost.call]"))

    def test_missing_and_orphan_note_for_an_environment_read(self):
        self.check(lambda m: m["notes"]["env_reads"].pop("HOME"),
                   ("missing-note", "notes.env_reads[HOME]"))
        self.check(lambda m: m["notes"]["env_reads"].update({"GHOST": entry("a", "b")}),
                   ("orphan-note", "notes.env_reads[GHOST]"))

    def test_missing_and_orphan_note_for_an_environment_write(self):
        self.check(lambda m: m.update(env_writes=["CRUX_FLAG"]),
                   ("missing-note", "notes.env_writes[CRUX_FLAG]"))
        self.check(lambda m: m["notes"]["env_writes"].update({"GHOST": entry("a", "b")}),
                   ("orphan-note", "notes.env_writes[GHOST]"))

    def test_missing_and_orphan_note_for_a_launch_script(self):
        self.check(lambda m: m["notes"]["launch"].pop("reader-one"),
                   ("missing-note", "notes.launch[reader-one]"))
        self.check(lambda m: m["notes"]["launch"].update({"ghost": entry("a", "b")}),
                   ("orphan-note", "notes.launch[ghost]"))

    def test_an_orphan_key_outside_the_name_grammar_is_named_by_position(self):
        self.check(lambda m: m["notes"]["events"].update({"has space": entry("a", "b")}),
                   ("orphan-note", "notes.events[#2]"))

    # the loader set

    def test_double_note(self):
        self.check(lambda m: m["notes"]["env_reads"].update({"LD_PRELOAD": entry("a", "b")}),
                   ("double-note", "notes.env_reads[LD_PRELOAD]"))

    def test_missing_loader_note(self):
        self.check(lambda m: m["notes"].pop("loader_vars"),
                   ("missing-loader-note", "notes.loader_vars"))

    def test_orphan_loader_note(self):
        def mutate(m):
            m["launch"]["loader_vars"] = []
            m["notes"]["env_reads"]["LD_PRELOAD"] = entry("a", "b")
            m["notes"]["env_reads"]["LD_AUDIT"] = entry("a", "b")
        self.check(mutate, ("orphan-loader-note", "notes.loader_vars"))

    def test_loader_var_unread(self):
        self.check(lambda m: m["env_reads"].remove("LD_AUDIT"),
                   ("loader-var-unread", "launch.loader_vars[1]"))

    # the closed key sets

    def test_unknown_and_missing_notes_keys(self):
        self.check(lambda m: m["notes"].update({"extra": {}}),
                   ("unknown-notes-key", "notes.extra"))
        self.check(lambda m: m["notes"].pop("calls"),
                   ("missing-notes-key", "notes.calls"))
        self.check(lambda m: m["notes"].update({"calls": []}),
                   ("missing-notes-key", "notes.calls"))

    def test_a_manifest_with_no_notes_key(self):
        self.check(lambda m: m.pop("notes"), ("missing-notes-key", "notes"))

    def test_unknown_and_missing_note_keys(self):
        self.check(lambda m: m["notes"]["calls"]["$.fs.read"].update({"extra": "x"}),
                   ("unknown-note-key", "notes.calls[$.fs.read].extra"))
        self.check(lambda m: m["notes"]["calls"]["$.fs.read"].pop("keeps"),
                   ("missing-note-key", "notes.calls[$.fs.read].keeps"))
        self.check(lambda m: m["notes"]["calls"].update({"$.fs.read": "a string"}),
                   ("missing-note-key", "notes.calls[$.fs.read]"))

    # the surface rows

    def test_missing_surface_and_surface_on_non_draw(self):
        self.check(lambda m: m["notes"]["events"][BAND].pop("surface"),
                   ("missing-surface", "notes.events[ui.render{component=Band}].surface"))
        self.check(lambda m: m["notes"]["events"][OBS].update({"surface": "somewhere"}),
                   ("surface-on-non-draw", "notes.events[session.start].surface"))

    def test_row_not_draw_and_draw_without_row(self):
        def mutate(m):
            m["notes"]["surfaces"][0]["event"] = OBS
            m["notes"]["surfaces"][0]["from"] = ["launch:outcome"]
        self.check(mutate, ("row-not-draw", "notes.surfaces[0].event"),
                   ("draw-without-row", "notes.events[ui.render{component=Band}]"))
        self.check(lambda m: m["notes"].update({"surfaces": []}),
                   ("draw-without-row", "notes.events[ui.render{component=Band}]"))

    def test_duplicate_row(self):
        self.check(lambda m: m["notes"]["surfaces"].append(copy.deepcopy(m["notes"]["surfaces"][0])),
                   ("duplicate-row", "notes.surfaces[1]"))

    def test_empty_from(self):
        self.check(lambda m: m["notes"]["surfaces"][0].update({"from": []}),
                   ("empty-from", "notes.surfaces[0].from"))

    def test_duplicate_source(self):
        self.check(lambda m: m["notes"]["surfaces"][0].update(
            {"from": ["launch:outcome", "launch:outcome"]}),
            ("duplicate-source", "notes.surfaces[0].from[1]"))

    def test_bad_field(self):
        cases = {
            "reader grammar": "reader-one:runs[].1bad",
            "event field is not props.name": BAND + ":placement",
            "event field has two segments": BAND + ":props.a.b",
            "agent field has two segments": "$.agent.list:a.b",
        }
        for label, source in cases.items():
            with self.subTest(case=label):
                self.check(lambda m, s=source: m["notes"]["surfaces"][0].update({"from": [s]}),
                           ("bad-field", "notes.surfaces[0].from[0]"))

    def test_bad_field_for_a_from_that_is_not_a_list_of_strings(self):
        self.check(lambda m: m["notes"]["surfaces"][0].update({"from": "launch:outcome"}),
                   ("bad-field", "notes.surfaces[0].from"))
        self.check(lambda m: m["notes"]["surfaces"][0].update({"from": [1]}),
                   ("bad-field", "notes.surfaces[0].from[0]"))

    def test_an_unexplained_placeholder_is_refused(self):
        cases = {
            "uv location": (lambda m: m["launch"]["uv_locations"].append("{OTHER}/uv"),
                            "launch.uv_locations[2]"),
            "script argument": (lambda m: m["launch"]["scripts"]["reader-one"]["args"].append(
                "--root={OTHER}"), "launch.scripts[0].args[2]"),
            "launcher argument": (lambda m: m["launch"]["launcher_args"].append("{OTHER}"),
                                  "launch.launcher_args[1]"),
            "uv argument": (lambda m: m["launch"]["uv_args"].append("{OTHER}"),
                            "launch.uv_args[2]"),
            "script path": (lambda m: m["launch"]["scripts"]["reader-one"].update(
                {"path": "{OTHER}/reader-one.py"}), "launch.scripts[0].path"),
            "launcher": (lambda m: m["launch"].update({"launcher": "{OTHER}/env"}),
                         "launch.launcher"),
            "allowed variable": (lambda m: m["launch"]["env_allow"].append("{OTHER}"),
                                 "launch.env_allow[2]"),
            "unpaired brace": (lambda m: m["launch"]["uv_locations"].append("{HOME/uv"),
                               "launch.uv_locations[2]"),
            "unpaired closing brace": (lambda m: m["launch"]["uv_locations"].append("HOME}/uv"),
                                       "launch.uv_locations[2]"),
        }
        for label, (mutate, where) in cases.items():
            with self.subTest(field=label):
                self.check(mutate, ("unexplained-placeholder", where))

    def test_bad_name_for_a_name_and_a_behaviour_word(self):
        def rename(m):
            m["events"][1]["event"] = "bad name"
            m["notes"]["events"]["bad name"] = m["notes"]["events"].pop(OBS)
        self.check(rename, ("bad-name", "events[1].event"))
        self.check(lambda m: m["events"][1].update({"behaviour": "Observe"}),
                   ("bad-name", "events[1].behaviour"))

    # origins

    def test_origins(self):
        bad_origin = {
            "another call": "$.fs.read:x",
            "a clock call": "$.clock.every:y",
            "another row's event": OBS + ":props.placement",
            "an unknown name": "unknown-reader:x",
            "no colon": "nocolon",
        }
        for label, source in bad_origin.items():
            with self.subTest(case=label):
                self.check(lambda m, s=source: m["notes"]["surfaces"][0].update({"from": [s]}),
                           ("bad-origin", "notes.surfaces[0].from[0]"))
        with self.subTest(case="launch field"):
            self.check(lambda m: m["notes"]["surfaces"][0].update({"from": ["launch:anything"]}),
                       ("bad-launch-field", "notes.surfaces[0].from[0]"))

    def test_another_draw_events_property_is_a_bad_origin(self):
        def mutate(m):
            other = "ui.render{component=Panel}"
            m["events"].append({"event": other, "behaviour": "draw", "decision": None})
            m["notes"]["events"][other] = {"sees": "a", "keeps": "b", "surface": "the panel"}
            m["notes"]["surfaces"].append(
                {"event": other, "part": "the panel row", "from": [BAND + ":props.placement"]})
        self.check(mutate, ("bad-origin", "notes.surfaces[1].from[0]"))

    def test_the_agent_list_origin_needs_the_call_in_the_manifest(self):
        def mutate(m):
            m["calls"].remove("$.agent.list")
            m["notes"]["calls"].pop("$.agent.list")
        self.check(mutate, ("bad-origin", "notes.surfaces[0].from[1]"))

    # note text

    def text_case(self, value):
        self.check(lambda m: m["notes"]["calls"]["$.fs.read"].update({"sees": value}),
                   ("bad-note-text", "notes.calls[$.fs.read].sees"))

    def test_refused_character_classes(self):
        cases = {
            "newline": "a\nb",
            "tab": "a\tb",
            "C0 control": "a" + chr(1) + "b",
            "C1 control": "a" + chr(0x85) + "b",
            "bidi control": "a" + chr(0x202E) + "b",
            "bidi isolate": "a" + chr(0x2066) + "b",
            "zero-width space": "a" + chr(0x200B) + "b",
            "BOM": "a" + chr(0xFEFF) + "b",
            "line separator": "a" + chr(0x2028) + "b",
            "paragraph separator": "a" + chr(0x2029) + "b",
            "tag character": "a" + chr(0xE0041) + "b",
            "combining mark": "a" + chr(0x301) + "b",
            "lone surrogate": "a" + chr(0xD800) + "b",
            "soft hyphen": "a" + chr(0xAD) + "b",
            "backslash": "a" + chr(0x5C) + "b",
            "less-than": "a<b",
            "greater-than": "a>b",
            "ampersand": "a&b",
            "open bracket": "a[b",
            "close bracket": "a]b",
            "empty": "",
            "401 code points": "a" * 401,
            "odd backtick count": "a`b",
            "adjacent backticks": "a``b",
            "dollar outside a span": "costs $5",
            "dollar in the unpaired part": "a $ `b`",
            "not a string": 7,
        }
        for label, value in cases.items():
            with self.subTest(case=label):
                self.text_case(value)

    def test_a_dollar_inside_a_span_is_accepted(self):
        manifest = base_manifest()
        manifest["notes"]["calls"]["$.fs.read"]["sees"] = "reads via `$.fs.read` and `$`"
        build(self.root, manifest)
        self.assertEqual(0, run(self.root).returncode)

    def test_every_autolink_form_is_refused(self):
        cases = [
            "https://example.invalid",
            "http://example.invalid",
            "ftp://example.invalid",
            "www.example.invalid",
            "WwW.example.invalid",
            "user@example.invalid",
            "mailto:user@example.invalid",
            "xmpp:user@example.invalid",
            "`https://example.invalid`",
        ]
        for value in cases:
            with self.subTest(form=value):
                self.text_case("see " + value)

    def test_the_never_sentence_must_start_with_a_letter(self):
        self.check(lambda m: m["notes"].update({"never": "# A heading"}),
                   ("bad-note-text", "notes.never"))
        self.check(lambda m: m["notes"].update({"never": 7}),
                   ("bad-note-text", "notes.never"))

    def test_the_surface_and_part_text_are_checked(self):
        self.check(lambda m: m["notes"]["events"][BAND].update({"surface": "a<b"}),
                   ("bad-note-text", "notes.events[ui.render{component=Band}].surface"))
        self.check(lambda m: m["notes"]["surfaces"][0].update({"part": "a<b"}),
                   ("bad-note-text", "notes.surfaces[0].part"))
        self.check(lambda m: m["notes"]["loader_vars"].update({"keeps": "a<b"}),
                   ("bad-note-text", "notes.loader_vars.keeps"))

    # the guide's markers and the manifest's parse

    def test_marker_codes(self):
        # Each guard has two halves, BEGIN and END. Each half has its own case.
        cases = [
            ("BEGIN missing", "marker-missing", PREFIX + END + SUFFIX),
            ("END missing", "marker-missing", PREFIX + BEGIN + STALE + SUFFIX),
            ("BEGIN duplicated", "marker-duplicated",
             PREFIX + BEGIN + "\n" + BEGIN + "\n" + END + SUFFIX),
            ("END duplicated", "marker-duplicated",
             PREFIX + BEGIN + STALE + END + "\n" + END + SUFFIX),
            ("END before BEGIN", "marker-misordered", PREFIX + END + "\n" + BEGIN + SUFFIX),
        ]
        for label, code, guide in cases:
            with self.subTest(case=label):
                self.check(None, (code, GUIDE), guide=guide)

    def test_a_marker_quoted_mid_line_is_not_a_delimiter(self):
        guide = PREFIX + "Mention " + BEGIN + " inline.\n" + BEGIN + STALE + END + SUFFIX
        build(self.root, guide=guide)
        self.assertEqual(0, run(self.root).returncode)

    def test_manifest_marker_faults_are_unparsed(self):
        # The manifest's own marker pair, each half with its own case.
        good = manifest_text(base_manifest())
        begin, end = "// BEGIN CAPABILITIES\n", "// END CAPABILITIES\n"
        cases = {
            "BEGIN missing": good.replace(begin, ""),
            "END missing": good.replace(end, ""),
            "BEGIN duplicated": good.replace(begin, begin + begin),
            "BEGIN after END": good + begin,
            "END duplicated": good + end,
            "END before BEGIN": end + good.replace(begin, "").replace(end, "") + begin,
        }
        for label, text in cases.items():
            with self.subTest(case=label):
                self.check(None, ("manifest-unparsed", MANIFEST), text=text)

    def test_a_duplicate_json_key_and_nan_are_unparsed(self):
        dup = manifest_text(base_manifest()).replace(
            '"plugin": "crux-mods",', '"plugin": "crux-mods", "plugin": "other",')
        self.check(None, ("manifest-unparsed", MANIFEST), text=dup)
        nan = manifest_text(base_manifest()).replace('"timeout_ms": 10000', '"timeout_ms": NaN')
        self.check(None, ("manifest-unparsed", MANIFEST), text=nan)

    def test_manifest_shape_faults_are_unparsed(self):
        self.check(lambda m: m.update({"events": {}}), ("manifest-unparsed", "events"))
        self.check(lambda m: m.update({"calls": ["$.fs.read", "$.fs.read"]}),
                   ("manifest-unparsed", "calls[1]"))

    def test_every_list_that_must_be_unique_refuses_a_duplicate(self):
        cases = {
            "events": (lambda m: m["events"].append(
                {"event": OBS, "behaviour": "observe", "decision": None}), "events[2].event"),
            "env_reads": (lambda m: m["env_reads"].append("HOME"), "env_reads[3]"),
            "env_writes": (lambda m: m.update({"env_writes": ["CRUX_FLAG", "CRUX_FLAG"]}),
                           "env_writes[1]"),
            "loader_vars": (lambda m: m["launch"]["loader_vars"].append("LD_PRELOAD"),
                            "launch.loader_vars[2]"),
        }
        for label, (mutate, where) in cases.items():
            with self.subTest(key=label):
                self.check(mutate, ("manifest-unparsed", where))

    def test_every_failure_is_collected_in_one_report(self):
        def mutate(m):
            m["notes"]["calls"].pop("$.fs.read")
            m["notes"]["surfaces"][0]["from"] = []
        self.check(mutate, ("missing-note", "notes.calls[$.fs.read]"),
                   ("empty-from", "notes.surfaces[0].from"),
                   ("marker-missing", GUIDE),
                   guide=PREFIX + SUFFIX)  # the marker failure follows the manifest's
        # the same report with a valid guide drops only the marker code
        self.check(mutate, ("missing-note", "notes.calls[$.fs.read]"),
                   ("empty-from", "notes.surfaces[0].from"))


# ---------------------------------------------------------------------------- exit 2


class ContainmentTests(TmpTestCase):
    def setUp(self):
        super().setUp()
        self.outside = self.tmp / "outside"
        self.outside.mkdir()

    def assert_refused(self, result):
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertEqual("", result.stdout)
        self.assertIn("symlink", result.stderr)

    def test_the_positive_control_real_directories_write(self):
        build(self.root)
        result = run(self.root)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(expected_guide(REGION), self.read_guide().decode("utf-8"))

    def test_a_symlinked_guide_is_refused(self):
        target = self.outside / "guide.md"
        target.write_text(guide_text(), encoding="utf-8")
        build(self.root, guide=False)
        (self.root / GUIDE).symlink_to(target)
        self.assert_refused(run(self.root))
        self.assertEqual(guide_text(), target.read_text(encoding="utf-8"))

    def test_a_symlink_inside_the_root_is_refused_too(self):
        build(self.root, guide=False)
        real = self.root / "real-guide.md"
        real.write_text(guide_text(), encoding="utf-8")
        (self.root / GUIDE).symlink_to(real)
        self.assert_refused(run(self.root))
        self.assertEqual(guide_text(), real.read_text(encoding="utf-8"))

    def test_a_symlinked_manifest_is_refused(self):
        _, mpath = build(self.root)
        target = self.outside / "capabilities.ts"
        target.write_text(manifest_text(base_manifest()), encoding="utf-8")
        mpath.unlink()
        mpath.symlink_to(target)
        before = self.read_guide()
        self.assert_refused(run(self.root))
        self.assertEqual(before, self.read_guide())

    def test_a_symlinked_temporary_file_is_refused(self):
        build(self.root)
        victim = self.outside / "victim.txt"
        victim.write_text("keep", encoding="utf-8")
        (self.root / ".USER_GUIDE.md.tmp").symlink_to(victim)
        before = self.read_guide()
        self.assert_refused(run(self.root))
        self.assertEqual("keep", victim.read_text(encoding="utf-8"))
        self.assertEqual(before, self.read_guide())

    def test_a_symlinked_crux_mods_directory_is_refused(self):
        build(self.root)
        moved = self.outside / "crux-mods"
        (self.root / "crux-mods").rename(moved)
        (self.root / "crux-mods").symlink_to(moved)
        before = self.read_guide()
        self.assert_refused(run(self.root))
        self.assertEqual(before, self.read_guide())

    def test_a_symlinked_hooks_directory_is_refused(self):
        build(self.root)
        moved = self.outside / "hooks"
        (self.root / "crux-mods" / "hooks").rename(moved)
        (self.root / "crux-mods" / "hooks").symlink_to(moved)
        before = self.read_guide()
        self.assert_refused(run(self.root))
        self.assertEqual(before, self.read_guide())

    def test_the_containment_helpers_refuse_what_the_command_line_cannot_reach(self):
        """The command line resolves the root and refuses a symlinked component first,
        so these inner layers are driven directly. Each has a positive control."""
        build(self.root)
        mod = load_module()
        self.assertEqual(self.root / GUIDE, mod._check_path(self.root, GUIDE))
        link = self.tmp / "link-to-project"
        link.symlink_to(self.root)
        with self.assertRaises(mod.EnvironmentFault) as caught:
            mod._check_path(link, GUIDE)
        self.assertIn("outside the repository root", str(caught.exception))
        # the write helper refuses a directory outside the root it was given
        with self.assertRaises(mod.EnvironmentFault) as caught:
            mod._atomic_write_text(self.root / GUIDE, "x", contained_under=self.outside)
        self.assertIn("outside the repository root", str(caught.exception))
        self.assertEqual(guide_text(), self.read_guide().decode("utf-8"))
        mod._atomic_write_text(self.root / GUIDE, "written", contained_under=self.root)
        self.assertEqual(b"written", self.read_guide())
        # the guide reader refuses a symlink even when the walk did not
        target = self.outside / "g.md"
        target.write_text("x", encoding="utf-8")
        reader_link = self.root / "reader-link.md"
        reader_link.symlink_to(target)
        self.assertEqual("written", mod._read_guide(self.root / GUIDE))
        with self.assertRaises(mod.EnvironmentFault):
            mod._read_guide(reader_link)

    def test_a_guide_that_is_a_directory_is_an_environment_fault(self):
        build(self.root, guide=False)
        (self.root / GUIDE).mkdir()
        result = run(self.root)
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("not a regular file", result.stderr)


# --------------------------------------------------------------------------- live checkout
#
# The classes below read the plugin's own checkout: the live manifest, the guide, the
# dashboard's TypeScript and `tools/mods_gate.py`. Each calls `require_dev_surface` on the
# repo-root `AGENTS.md`, a signal independent of the guide's fingerprint, so a dev guide that
# gained a fingerprint line fails the no-`surface_absent` assertion rather than skipping it.
# On the staged artifact, where that file does not ship, they skip.

_LIVE_SCRIPT = Path(__file__).resolve().parents[1] / "generate-mods-reach-tables.py"
_LIVE_MANIFEST = REPO_ROOT / "crux-mods" / "hooks" / "capabilities.ts"
_LIVE_VIEW = REPO_ROOT / "crux-mods" / "hooks" / "lib" / "view.ts"
_LIVE_REGISTER = REPO_ROOT / "crux-mods" / "hooks" / "register.tsx"
_LIVE_GATE = REPO_ROOT / "tools" / "mods_gate.py"
_LIVE_PUBLIC_GUIDE = REPO_ROOT / "public" / "USER_GUIDE.md"

_BAND = "ui.render{component=AbovePrompt}"
_PANE = "ui.render{component=Pane}"

# Every band segment and every pane row or panel, in the order the notes list them. Written by
# hand from `crux-mods/hooks/lib/draw.ts` (bandSegments, docked, runLines, idleLines, mini). A
# book that changes a drawn part edits this list and the manifest's notes together.
LIVE_PARTS = [
    (_BAND, "the book and run of the run whose run file changed last"),
    (_BAND, "the prompt strip: one glyph per prompt, with `|` between modules"),
    (_BAND, "the current prompt's module kind word"),
    (_BAND, "the current prompt's position out of the total"),
    (_BAND, "the percent done"),
    (_BAND, "the time the current prompt has run"),
    (_BAND, "an escalation of the current prompt's module"),
    (_BAND, "a stall"),
    (_BAND, "the current prompt's title"),
    (_BAND, "the last council round and its aggregate action"),
    (_BAND, "the last gate with a recorded state"),
    (_BAND, "the number of running subagents"),
    (_BAND, "how many other runs are in progress"),
    (_BAND, "the last completed run, for 48 hours after it completed"),
    (_BAND, "the line `run in progress, view refused`"),
    (_BAND, "the status code"),
    (_BAND, "the band's width"),
    (_BAND, "no band while a survey shows"),
    (_PANE, "the legend of the glyphs and module kinds in view"),
    (_PANE, "each run panel's heading: book, run, status, current prompt and percent"),
    (_PANE, "the prompt strip, each module labelled with its kind word"),
    (_PANE, "the progress bar of `\u25ae` and `\u25af`"),
    (_PANE, "when the run started, and how long it has run or took"),
    (_PANE, "one lane per prompt on one time axis"),
    (_PANE, "`lanes withheld`, in place of the lanes of a long run or of a pane past its size budget"),
    (_PANE, "the counts of prompts by state"),
    (_PANE, "the stall line and its note"),
    (_PANE, "the escalation lines and their note"),
    (_PANE, "a row per prompt: its state, module tag, title and duration"),
    (_PANE, "the count of refused council files"),
    (_PANE, "the count of runs past the five shown"),
    (_PANE, "the councils grid, with the newest record's aggregate action and whether it converged"),
    (_PANE, "the gates panel"),
    (_PANE, "the agents panel"),
    (_PANE, "the last run when none is in progress, with its summary"),
    (_PANE, "the `undetermined` row"),
    (_PANE, "the line saying the reader refused a run in progress"),
    (_PANE, "the reader's version and the count of refused run files"),
    (_PANE, "the status code"),
    (_PANE, "the layout: borders, one or two columns, and the inline layout with its `+N more` row"),
]

# The manifest's `notes.never`, pinned. It restates rule:mods-hold-a-closed-capability-set and
# rule:mods-read-tree-state-and-write-none in its own words, and names no key-value store because
# the manifest lists no store call. No gate compares this prose with the manifest, so a change to
# it needs a deliberate edit here, beside the Accepted decision that justifies it.
PINNED_NEVER = (
    "Directly or through the process it starts, it makes no network request, calls no model "
    "and reads no credential or environment secret. It writes nothing in your documentation "
    "tree or your project: its only write is uv's cache, and it refuses a uv cache inside "
    "your project."
)

_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _load_live_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _quoted_names(text: str) -> set[str]:
    return set(re.findall(r"'([A-Za-z_][A-Za-z0-9_]*)'", text))


def reader_keys(view_ts: str) -> set[str]:
    """Every key name in `view.ts`'s `obj(<value>, [<keys>])` calls, with `STATES`."""
    keys: set[str] = set()
    for m in re.finditer(r"\bobj\(\s*[^,()]+,\s*\[([^\]]*)\]\s*\)", view_ts):
        keys |= _quoted_names(m.group(1))
    states = re.search(r"export const STATES = \[([^\]]*)\]", view_ts)
    if states is not None:
        keys |= _quoted_names(states.group(1))
    return keys


def agent_fields(view_ts: str) -> set[str]:
    """The fields `agents()` reads from each entry of the engine's agent list."""
    m = re.search(r"export function agents\(list: unknown\): Agents \{(.*?)\n\}\n", view_ts, re.S)
    return set() if m is None else set(re.findall(r"\bo\.([A-Za-z_][A-Za-z0-9_]*)", m.group(1)))


def event_props(register_tsx: str) -> dict[str, set[str]]:
    """Each handler's `e.props.<name>` reads, keyed by the manifest's event string."""
    heads = list(re.finditer(
        r"\bon\(\s*'([a-z][a-z.]*)'(?:\s*,\s*\{\s*([a-z]+):\s*'([^']+)'\s*\})?", register_tsx))
    out: dict[str, set[str]] = {}
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(register_tsx)
        event = h.group(1) + ("{%s=%s}" % (h.group(2), h.group(3)) if h.group(2) else "")
        out.setdefault(event, set()).update(
            re.findall(r"\be\.props\.([A-Za-z_][A-Za-z0-9_]*)", register_tsx[h.start():end]))
    return out


class UncheckedOrigin(AssertionError):
    """A source whose origin is none of the four kinds the cross-check checks."""


def cross_check(source: str, row_event: str, *, scripts: set[str], keys: set[str],
                agents: set[str], props: dict[str, set[str]]) -> bool:
    """Whether a From source names a field the dashboard's code reads.

    It dispatches on the four origin kinds and has no default branch: any other origin
    raises `UncheckedOrigin`, so an origin it cannot check fails the test, never passes it.
    """
    origin, _, field = source.rpartition(":")
    if origin in scripts:
        segments = [s.removesuffix("[]") for s in field.split(".")]
        return bool(segments) and all(s in keys for s in segments)
    if origin == "$.agent.list":
        return field in agents
    if origin == row_event:
        name = field.removeprefix("props.")
        return field.startswith("props.") and _NAME.fullmatch(name) is not None \
            and name in props.get(row_event, set())
    if origin == "launch":
        return field == "outcome"
    raise UncheckedOrigin(source)


class LiveCheckoutTests(unittest.TestCase):
    """The plugin's own guide and manifest, through the regenerator itself."""

    def setUp(self):
        require_dev_surface(self, REPO_ROOT / "AGENTS.md", "repo-root AGENTS.md")

    def _manifest(self) -> dict:
        regen = _load_live_module(_LIVE_SCRIPT, "_live_regen")
        return regen.load_manifest(_LIVE_MANIFEST)

    def test_the_live_dry_run_is_clean_and_not_surface_absent(self):
        result = subprocess.run(
            [sys.executable, str(_LIVE_SCRIPT), "--dry-run", "--repo-root", str(REPO_ROOT)],
            capture_output=True, text=True, check=False)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual({"drift": False, "paths": []}, json.loads(result.stdout))

    def test_the_live_surface_parts_are_the_drawn_parts(self):
        notes = self._manifest().get("notes", {})
        rows = notes.get("surfaces", []) if isinstance(notes, dict) else []
        self.assertEqual(LIVE_PARTS, [(r.get("event"), r.get("part")) for r in rows])

    def test_the_live_never_text_is_the_pinned_text(self):
        notes = self._manifest().get("notes", {})
        self.assertEqual(PINNED_NEVER, notes.get("never") if isinstance(notes, dict) else None)


class FromCrossCheckTests(unittest.TestCase):
    """Every live From source names a field the dashboard's code reads.

    LIMITS, stated. It proves that a cited field EXISTS, not that the part draws from it: it
    reads no drawing code, so a real reader key cited for the wrong part passes. It checks each
    segment's name, not its nesting, so a real key at the wrong depth passes. The independent
    review checks every Shows / From row against `draw.ts` and `view.ts`.
    """

    def setUp(self):
        require_dev_surface(self, REPO_ROOT / "AGENTS.md", "repo-root AGENTS.md")
        view = _LIVE_VIEW.read_text(encoding="utf-8")
        register = _LIVE_REGISTER.read_text(encoding="utf-8")
        regen = _load_live_module(_LIVE_SCRIPT, "_live_regen_x")
        self.manifest = regen.load_manifest(_LIVE_MANIFEST)
        self.ctx = {
            "scripts": set(self.manifest["launch"]["scripts"]),
            "keys": reader_keys(view),
            "agents": agent_fields(view),
            "props": event_props(register),
        }

    def test_the_extraction_is_not_vacuous(self):
        for key in ("runs", "prompts", "started_s", "state", "status"):
            self.assertIn(key, self.ctx["keys"])
        self.assertEqual({"status", "type", "description"}, self.ctx["agents"])
        self.assertEqual({"hasSurvey", "bodyColumns"}, self.ctx["props"].get(_BAND))
        self.assertEqual({"bodyColumns", "placement"}, self.ctx["props"].get(_PANE))
        self.assertEqual({"visualize-run-progress"}, self.ctx["scripts"])

    def test_every_live_source_names_a_field_the_code_reads(self):
        notes = self.manifest.get("notes", {})
        rows = notes.get("surfaces", []) if isinstance(notes, dict) else []
        checked = 0
        for row in rows:
            for source in row["from"]:
                with self.subTest(part=row["part"], source=source):
                    self.assertTrue(cross_check(source, row["event"], **self.ctx), source)
            checked += 1
        self.assertEqual(40, checked, "every surface row is checked")

    def test_seeded_sources_fail_the_cross_check(self):
        for source, event in (
            ("visualize-run-progress:runs[].no_such_key", _PANE),
            ("$.agent.list:no_such_field", _PANE),
            ("ui.render{component=Pane}:props.no_such_prop", _PANE),
            # Only the pane handler reads `placement`.
            ("ui.render{component=AbovePrompt}:props.placement", _BAND),
            ("launch:anything", _BAND),
        ):
            with self.subTest(source=source):
                self.assertFalse(cross_check(source, event, **self.ctx))

    def test_an_origin_of_no_checked_kind_fails_as_unchecked(self):
        for source in ("$.fs.read:x", "$.clock.every:y", "ui.render{component=Pane}:props.placement"):
            with self.subTest(source=source):
                # The last one names the pane's event from a band row: another row's event.
                with self.assertRaises(UncheckedOrigin):
                    cross_check(source, _BAND, **self.ctx)


class ParserParityTests(unittest.TestCase):
    """The regenerator parses the manifest as the mods gate does."""

    def test_both_parsers_read_the_same_compared_entries(self):
        require_dev_surface(self, REPO_ROOT / "AGENTS.md", "repo-root AGENTS.md")
        require_dev_surface(self, _LIVE_GATE, "tools/mods_gate.py")
        gate = _load_live_module(_LIVE_GATE, "_live_mods_gate")
        regen = _load_live_module(_LIVE_SCRIPT, "_live_regen_p")
        projected, _sha = gate.load_manifest(REPO_ROOT / "crux-mods")
        parsed = regen.load_manifest(_LIVE_MANIFEST)
        for key in ("events", "calls", "env_reads", "env_writes", "state_declared", "state_reads", "state_writes"):
            with self.subTest(key=key):
                self.assertEqual(projected[key], parsed[key])
        self.assertEqual(6, len(parsed["events"]))
        self.assertEqual(14, len(parsed["calls"]))
        self.assertEqual(14, len(parsed["env_reads"]))
        self.assertEqual([], parsed["env_writes"])
        self.assertEqual(["crux-mods.current"], parsed["state_declared"])
        self.assertEqual(["crux-mods.current"], parsed["state_reads"])
        self.assertEqual(["crux-mods.current"], parsed["state_writes"])


class PublicFingerprintTests(unittest.TestCase):
    """The fingerprint lane is pinned to its real producer, the public guide's line 1."""

    def test_the_public_guide_line_one_is_a_fingerprint(self):
        require_dev_surface(self, _LIVE_PUBLIC_GUIDE, "public/USER_GUIDE.md")
        regen = _load_live_module(_LIVE_SCRIPT, "_live_regen_f")
        line1 = _LIVE_PUBLIC_GUIDE.read_text(encoding="utf-8").splitlines()[0]
        self.assertTrue(regen.is_public_fingerprint(line1), line1)


if __name__ == "__main__":
    unittest.main()
