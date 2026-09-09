"""Credential-format scan over the arch-corpus goldens.

G1 finding: the arch-corpus goldens at crux/scripts/tests/arch-corpus/golden/
are derived from ten pinned third-party checkouts and ARE republished to the
public repo (tools/sync_stage.py grants the whole crux subtree; golden/ is
excluded by neither STAGE_IGNORE_NAMES nor DENY_FILES). A scan found ZERO
credentials present today -- this is a LATENT channel, not a live leak. This
test keeps it that way: it fails the build the day any golden file starts
matching a credential format, so a future re-derive from a re-cloned upstream
cannot silently reintroduce a leaked secret.

Stdlib-only, read-only, no network.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

GOLDEN = Path(__file__).resolve().parent / "arch-corpus" / "golden"

# Files that are unambiguously binary in this corpus (images etc.). The
# corpus is markdown-only today, but this list exists so a future binary
# asset added to the goldens is skipped deliberately (with a stated reason)
# rather than silently, and never skipped by extension-sniffing alone.
_BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".zip"}

# Each pattern is named so a failure message says which credential FORMAT
# matched. Patterns are deliberately format-shaped (prefix/structure), not
# semantic, since this scan runs over prose/markdown, not live config.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("openai-sk", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("aws-akia", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github-pat", re.compile(r"ghp_[A-Za-z0-9]{36,}")),
    ("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("google-api-key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")),
    ("pem-block", re.compile(r"-----BEGIN")),
    # Assignment-shaped secret: SECRET|PASSWORD|TOKEN|API_KEY|PRIVATE_KEY
    # followed by `[:=]` then >=6 non-whitespace chars.
    #
    # Case-SENSITIVE and word-boundary-anchored on the left, and both
    # choices were MEASURED against the 50 committed goldens rather than
    # assumed. Counting line matches over the real corpus:
    #
    #   this pattern (uppercase, \b-anchored)          0 matches
    #   the same pattern with re.IGNORECASE            1 match
    #
    # The single case-insensitive match is
    # `golden/rubygems-org/module-graph.md:632`, on the Ruby constant
    # `Password::CompromisedComponent` — the `::` scope operator supplies
    # the `:` the pattern reads as an assignment. Derived module-graph prose
    # is full of such constants, so a case-insensitive variant would report
    # class names as credentials.
    #
    # Uppercase is the env-var and config-key spelling convention, so
    # anchoring there keeps the pattern aimed at assignment-shaped text
    # (`API_KEY=...`, `SECRET: ...`) without narrowing it below what the
    # finding asked for. It is the only pattern in the table with a
    # meaningful false-positive risk against markdown prose.
    #
    # WHAT IT DOES NOT REACH: an all-caps Ruby or Elixir constant of the
    # form `SECRET::Foo` would match. None exists in the corpus today. If
    # one appears, the honest fix is to exempt that path with the constant
    # named, never to relax the pattern.
    (
        "assignment-secret",
        re.compile(r"\b(SECRET|PASSWORD|TOKEN|API_KEY|PRIVATE_KEY)\s*[:=]\s*\S{6,}"),
    ),
]


def _scan_for_credentials(root: Path) -> list[str]:
    """Scan every file under `root` for credential-shaped matches.

    Returns a list of human-readable finding strings: "<name> in <path>:<line>
    -> <truncated match>". Never raises on decode errors -- files are read
    with errors="replace" so a stray non-UTF8 byte cannot hide a real match
    (and cannot crash the scan either).
    """
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        # Corpus is markdown-only; skip only the known-binary suffixes, and
        # do so loudly here (in findings-free silence there is nothing to
        # report, but the exclusion itself is stated, not implicit).
        if path.suffix.lower() in _BINARY_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for name, pattern in PATTERNS:
                match = pattern.search(line)
                if match:
                    snippet = match.group(0)[:12]
                    findings.append(f"{name} in {path}:{lineno} -> {snippet}...")
    return findings


def _count_scanned_files(root: Path) -> int:
    return sum(
        1
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() not in _BINARY_SUFFIXES
    )


class ArchCorpusCredentialScanTests(unittest.TestCase):
    def test_golden_dir_exists_and_is_committed(self) -> None:
        # The goldens are committed on disk regardless of any .cache/ state;
        # this scan must never silently skip because of that.
        self.assertTrue(
            GOLDEN.is_dir(),
            f"expected committed golden corpus at {GOLDEN}; "
            "if this is genuinely absent, the scan below is vacuous",
        )

    def test_no_credentials_in_golden_corpus(self) -> None:
        # The real gate: no credential-shaped text anywhere in the goldens.
        findings = _scan_for_credentials(GOLDEN)
        self.assertEqual(findings, [])

        # Non-vacuity guard: prove the scan actually walked real files and
        # the pattern table did not collapse to nothing. There are ~50
        # golden files across ten pinned repos as of authoring; 30 is a
        # floor safely below that, so a future corpus shrink still trips
        # this guard before the corpus could vanish out from under the glob.
        scanned = _count_scanned_files(GOLDEN)
        self.assertGreater(scanned, 30, f"only scanned {scanned} files")
        self.assertGreater(len(PATTERNS), 5)

    def test_positive_control_every_pattern_fires_on_a_synthetic_credential(
        self,
    ) -> None:
        # Mandatory positive control: prove _scan_for_credentials actually
        # detects each pattern, not merely that it returns nothing on the
        # (currently clean) real corpus. Without this, the absence
        # assertion above would pass vacuously if the golden glob ever
        # stopped matching real files (e.g. the dir moved or was renamed).
        #
        # All values below are obviously-fake synthetic test fixtures,
        # modeled on each vendor's well-known public "this is a fake key"
        # example format (e.g. AWS's own docs use AKIAIOSFODNN7EXAMPLE).
        synthetic = {
            "openai-sk.md": "key = sk-000000000000000000000000example\n",
            "aws-akia.md": "id = AKIAIOSFODNN7EXAMPLE\n",
            "github-pat.md": "token = ghp_000000000000000000000000000000000000\n",
            # Vendor-prefix plus a same-length run of "x": fires each PATTERNS
            # entry above without matching GitHub's push-protection detectors,
            # which refused a push carrying a digit-shaped Slack value.
            "slack-token.md": "slack = xoxb-xxxxxxxxxxxxxxxxxxxxxxxxxxx\n",
            "google-api-key.md": "key = AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n",
            "jwt.md": (
                "jwt = eyJxxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxx."
                "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n"
            ),
            "pem-block.md": "-----BEGIN RSA PRIVATE KEY-----\nMIIExample\n",
            "assignment-secret.md": "API_KEY = abcdef1234567890\n",
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for filename, content in synthetic.items():
                (tmp_path / filename).write_text(content, encoding="utf-8")

            findings = _scan_for_credentials(tmp_path)

        matched_names = {finding.split(" in ", 1)[0] for finding in findings}
        for name, _pattern in PATTERNS:
            self.assertIn(
                name,
                matched_names,
                f"positive control fixture for {name!r} did not fire; "
                f"findings were: {findings}",
            )


if __name__ == "__main__":
    unittest.main()
