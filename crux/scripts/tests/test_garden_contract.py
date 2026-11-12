"""Contract tests for the garden log op.

Operative guarantees (per ADR-0039 §4, §5, and the SSOT mechanism defined by
ADR-0012):

  (a) The `garden` token appears in BOTH §6 SSOT regexes in BOTH
      docs/AGENTS.md and crux/templates/AGENTS.md.tmpl (4 assertions total:
      token-in-alternation check by extracting the regex lines from each file).

  (b) Both regexes still compile (re.compile) and match a synthetic heading
      of the canonical form:
        ## [2026-06-12] garden | morning note 2026-06-12 (3 headlines, 2 artifacts)

Uses only stdlib (unittest, re, pathlib).  No mocks needed — everything
resolves from repo-relative paths so the test is cwd-independent.

Files tested by (a) and (b) (CLAUDE-surface pairs) must be kept in
lock-step; this test pins both.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

try:
    from ._dev_surface import TREE, TREE_AGENTS_MD, require_dev_surface
except ImportError:  # unittest discover imports test modules top-level
    from _dev_surface import TREE, TREE_AGENTS_MD, require_dev_surface

# ─── repo paths ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCS_CLAUDE_MD = TREE_AGENTS_MD
TMPL_CLAUDE_MD = REPO_ROOT / "crux" / "templates" / "AGENTS.md.tmpl"

# ─── canonical strings ───────────────────────────────────────────────────────

# The op token added to the §6 SSOT alternation groups.
GARDEN_TOKEN: str = "garden"

# Synthetic heading the regex must match (per ADR-0039 §5 heading form).
SYNTHETIC_HEADING: str = (
    "## [2026-06-12] garden | morning note 2026-06-12 (3 headlines, 2 artifacts)"
)

# ─── helpers ─────────────────────────────────────────────────────────────────

# The SSOT regex block in §6 has a specific pattern we can extract.
# Each line has the form:
#   ^## \[\d{4}-\d{2}-\d{2}\] (init|...|<token>) \|
# We extract the alternation group from each regex line for token-presence
# checking.  The two distinct regex lines are distinguished by whether they
# contain "cleanup|" (historical reader) or not (current writer).


def _extract_regex_lines(text: str) -> list[str]:
    """Return all lines in ``text`` that look like the §6 op-enum regex lines.

    These lines appear inside fenced code blocks and start with:
        ^## \\[\\d{4}-\\d{2}-\\d{2}\\] (alternation) \\|
    """
    matches = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(r"^## \[") and r"\d{4}" in stripped and "(" in stripped:
            matches.append(stripped)
    return matches


def _token_in_alternation(regex_line: str, token: str) -> bool:
    """Return True if ``token`` appears as a bare word in the alternation group.

    We look for the token surrounded by | or ( on the left and | or ) on
    the right (accounting for any spacing), so "garden" does not accidentally
    match "garden-bed".
    """
    # Extract everything between the first ( and the last )
    start = regex_line.find("(")
    end = regex_line.rfind(")")
    if start == -1 or end == -1:
        return False
    alternation = regex_line[start + 1:end]
    # Split on |
    parts = [p.strip() for p in alternation.split("|")]
    return token in parts


_CLAUDE_SURFACES = [
    (DOCS_CLAUDE_MD, f"{TREE}/AGENTS.md"),
    (TMPL_CLAUDE_MD, "crux/templates/AGENTS.md.tmpl"),
]


# ─── test classes ─────────────────────────────────────────────────────────────


class TestGardenTokenInSSOTRegexes(unittest.TestCase):
    """(a) The garden token appears in BOTH §6 SSOT regexes in BOTH CLAUDE surfaces."""

    def _assert_garden_in_both_regexes(self, path: Path, label: str) -> None:
        """Helper: extract both regex lines from path and assert garden is present."""
        if path == DOCS_CLAUDE_MD:
            require_dev_surface(self, path, label)
        self.assertTrue(
            path.exists(),
            msg=f"{label} not found at {path}",
        )
        text = path.read_text(encoding="utf-8")
        regex_lines = _extract_regex_lines(text)
        self.assertGreaterEqual(
            len(regex_lines),
            2,
            msg=(
                f"{label}: expected to find at least 2 op-enum regex lines "
                f"(current-writer and historical-reader) in §6, found {len(regex_lines)}.\n"
                f"  Extracted lines: {regex_lines!r}"
            ),
        )
        for i, rline in enumerate(regex_lines):
            with self.subTest(surface=label, regex_index=i):
                self.assertTrue(
                    _token_in_alternation(rline, GARDEN_TOKEN),
                    msg=(
                        f"{label}: regex line {i} does not contain '{GARDEN_TOKEN}' "
                        f"as a distinct alternation token.\n"
                        f"  regex line: {rline!r}"
                    ),
                )

    def test_docs_claude_md_both_regexes_contain_garden(self) -> None:
        """docs/AGENTS.md: both §6 SSOT regex lines must contain 'garden'."""
        self._assert_garden_in_both_regexes(DOCS_CLAUDE_MD, f"{TREE}/AGENTS.md")

    def test_tmpl_claude_md_both_regexes_contain_garden(self) -> None:
        """crux/templates/AGENTS.md.tmpl: both §6 SSOT regex lines must contain 'garden'."""
        self._assert_garden_in_both_regexes(TMPL_CLAUDE_MD, "crux/templates/AGENTS.md.tmpl")


class TestGardenRegexCompileAndMatch(unittest.TestCase):
    """(b) Both extracted regexes compile and match the synthetic heading."""

    def _regexes_from(self, path: Path, label: str) -> list[re.Pattern[str]]:
        """Extract and compile the op-enum regex lines from path."""
        if path == DOCS_CLAUDE_MD:
            require_dev_surface(self, path, label)
        self.assertTrue(
            path.exists(),
            msg=f"{label} not found at {path}",
        )
        text = path.read_text(encoding="utf-8")
        regex_lines = _extract_regex_lines(text)
        compiled = []
        for rline in regex_lines:
            try:
                compiled.append(re.compile(rline))
            except re.error as exc:
                self.fail(
                    f"{label}: failed to compile regex line {rline!r}: {exc}"
                )
        return compiled

    def test_docs_claude_md_regexes_compile_and_match(self) -> None:
        """docs/AGENTS.md: extracted regexes compile and match the synthetic heading."""
        patterns = self._regexes_from(DOCS_CLAUDE_MD, f"{TREE}/AGENTS.md")
        self.assertGreaterEqual(len(patterns), 2, msg="Expected at least 2 regex patterns")
        for i, pat in enumerate(patterns):
            with self.subTest(regex_index=i):
                self.assertIsNotNone(
                    pat.match(SYNTHETIC_HEADING),
                    msg=(
                        f"docs/AGENTS.md regex {i} did not match synthetic heading.\n"
                        f"  heading: {SYNTHETIC_HEADING!r}\n"
                        f"  pattern: {pat.pattern!r}"
                    ),
                )

    def test_tmpl_claude_md_regexes_compile_and_match(self) -> None:
        """crux/templates/AGENTS.md.tmpl: extracted regexes compile and match the synthetic heading."""
        patterns = self._regexes_from(TMPL_CLAUDE_MD, "crux/templates/AGENTS.md.tmpl")
        self.assertGreaterEqual(len(patterns), 2, msg="Expected at least 2 regex patterns")
        for i, pat in enumerate(patterns):
            with self.subTest(regex_index=i):
                self.assertIsNotNone(
                    pat.match(SYNTHETIC_HEADING),
                    msg=(
                        f"crux/templates/AGENTS.md.tmpl regex {i} did not match "
                        f"synthetic heading.\n"
                        f"  heading: {SYNTHETIC_HEADING!r}\n"
                        f"  pattern: {pat.pattern!r}"
                    ),
                )
