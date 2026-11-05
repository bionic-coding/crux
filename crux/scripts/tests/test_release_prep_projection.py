"""A prep-shaped release leaves the main-run fingerprints alone.

CYC-0093 item 29: `verify` reuses the main-run receipts (the checkout core and tools suites) when the code state
matches. The release prep bumps the version surfaces, promotes the changelog's `[Unreleased]` section and
regenerates the README footer. The registered checkout declarations project those spans, so a receipt written
before the prep still matches after it. This test builds that prep on a clone of the committed tree and compares
the two snapshots, so a prep-touched path that is not projected fails here instead of at `verify`.
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _dev_surface import IS_STAGED_ARTIFACT, REPO_ROOT
import suite_evidence
import test_evidence as te

CORE = "checkout:unittest:crux/scripts/tests:test*.py"
TOOLS = "checkout:unittest:tools/tests:test*.py"
BUMPED = "99.0.0"
NEXT_RELEASE_DATE = "2099-01-01"


def run(argv, cwd):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=True)


def vcs(root, *args):
    return run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *args], root)


def replace_once(path, pattern, replacement):
    text = path.read_text()
    new, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
    if count != 1:
        raise AssertionError(f"{path.name}: expected one match of {pattern!r}, found {count}")
    path.write_text(new)


class PrepShapedReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if IS_STAGED_ARTIFACT:
            raise unittest.SkipTest("the clone needs the dev checkout's history, which a staged artifact lacks")
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name) / "clone"
        run(["git", "clone", "-q", "--no-hardlinks", str(REPO_ROOT), str(cls.root)], cls.temp.name)
        cls.version = json.loads((cls.root / "crux/plugin.json").read_text())["version"]
        cls.open_unreleased_section()
        cls.before = cls.fingerprints()
        cls.prep()
        cls.after = cls.fingerprints()

    @classmethod
    def open_unreleased_section(cls):
        """The pre-prep state: the changelog has an `## [Unreleased]` section for `promote-changelog.py` to promote.

        The committed changelog may carry the next release's entries with no heading yet; the prep needs one.
        """
        changelog = cls.root / "CHANGELOG.md"
        text = changelog.read_text()
        if not re.search(r"^## \[Unreleased\]", text, re.M):
            changelog.write_text(re.sub(r"^### ", "## [Unreleased]\n\n### ", text, count=1, flags=re.M))
        vcs(cls.root, "add", "-A")
        vcs(cls.root, "commit", "-qm", "open the unreleased section", "--allow-empty")

    @classmethod
    def fingerprints(cls):
        result = {}
        for check in (CORE, TOOLS):
            declaration = suite_evidence.registered_declaration(cls.root, check, dev_root=cls.root)
            result[check] = te.snapshot(cls.root, declaration, source_root=cls.root)["fingerprint"]
        return result

    @classmethod
    def prep(cls):
        """What root AGENTS.md's release comment lists, applied to the clone, then committed."""
        old = re.escape(cls.version)
        for relative in ("crux/plugin.json", "crux/.claude-plugin/plugin.json", "crux/.codex-plugin/plugin.json",
                         "crux-mods/.claude-plugin/plugin.json", "tools/bionic-catalog/crux-learning-catalog-guide.json"):
            replace_once(cls.root / relative, rf'("(?:version|reviewed_plugin_version)":\s*)"{old}"', rf'\g<1>"{BUMPED}"')
        replace_once(cls.root / "pyproject.toml", rf'^(version = )"{old}"', rf'\g<1>"{BUMPED}"')
        replace_once(cls.root / "uv.lock", rf'(name = "crux"\nversion = )"{old}"', rf'\g<1>"{BUMPED}"')
        # `-E -s`, not `-I`: both scripts import their sibling modules, and `-I` drops the script directory from
        # sys.path. The registered check runs in an isolated environment with no crux distribution to supply them.
        run([sys.executable, "-E", "-s", "crux/scripts/promote-changelog.py", "--version", BUMPED, "--date", NEXT_RELEASE_DATE], cls.root)
        run([sys.executable, "-E", "-s", "crux/scripts/generate-readme-footer.py", "--repo-root", "."], cls.root)
        vcs(cls.root, "add", "-A")
        vcs(cls.root, "commit", "-qm", "prep")

    def test_the_prep_changed_files_the_declarations_read(self):
        # Positive control: the prep is not a no-op, so equal fingerprints below mean the projections held.
        changed = vcs(self.root, "diff", "--name-only", "HEAD~1", "HEAD").stdout.split()
        for expected in ("crux/plugin.json", "pyproject.toml", "uv.lock", "CHANGELOG.md", "README.md"):
            self.assertIn(expected, changed)

    def test_the_main_run_fingerprints_survive_a_prep_shaped_release(self):
        self.assertEqual(self.after, self.before)

    def test_a_non_release_edit_after_the_prep_still_moves_them(self):
        # Negative control: the equality above is a measurement of the projection, not of an empty input set.
        marker = self.root / "AGENTS.md"
        original = marker.read_text()
        self.addCleanup(marker.write_text, original)
        marker.write_text(original + "\nan authored edit\n")
        self.assertNotEqual(self.fingerprints()[CORE], self.before[CORE])


if __name__ == "__main__":
    unittest.main()
