"""Tests for the corpus golden-diff classifier (ADR-0096 clause 12's re-bless gate).

`golden_diff_classify.py` is the one mechanical thing standing between "the
three coverage keys came out" and "a route table silently lost nine rows in the
same commit". Its whole value is the `stub-line` / `extraction-content`
boundary, so that boundary is what these tests pin.

The boundary was once a prefix pair — `("> _no extractor for this stack",
"> _")` — whose second entry subsumed the first and classified EVERY
blockquote-italic line as a stub line. Every spine renderer emits
blockquote-italic prose (`> _Derived from db/schema.rb._` is not a stub line;
it is a rendered prose cell), so that prefix could not tell a moved stub line
from moved extraction content. `test_blockquote_italic_prose_is_extraction_content`
is the regression pin for it.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import unittest
import unittest.mock
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
CORPUS_DIR = TESTS_DIR / "arch-corpus"

sys.path.insert(0, str(TESTS_DIR.parent))          # crux/scripts


def _load(name: str):
    """Import a module from `arch-corpus/` by path (the dir name has a hyphen)."""
    spec = importlib.util.spec_from_file_location(
        f"_arch_corpus_{name}", CORPUS_DIR / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GDC = _load("golden_diff_classify")

MD = "crux/scripts/tests/arch-corpus/golden/codetriage/data-model.md"
COV = "crux/scripts/tests/arch-corpus/golden/codetriage/_meta/coverage.json"


class StubLineGrammarTests(unittest.TestCase):
    """The `stub-line` class matches the renderer's grammar, and only it."""

    def test_legacy_no_extractor_line_is_a_stub_line(self):
        line = "> _no extractor for this stack — empty-but-valid spine file._"
        self.assertEqual(GDC.classify_line(MD, line), "stub-line")

    def test_every_clause_4_reason_renders_a_recognized_stub_line(self):
        for reason in GDC.STUB_REASONS:
            line = f"> _stub: {reason} — expected a thing, found nothing._"
            with self.subTest(reason=reason):
                self.assertEqual(GDC.classify_line(MD, line), "stub-line")

    def test_blockquote_italic_prose_is_extraction_content(self):
        """The defect this file exists for.

        These are real blockquote-italic lines a spine file can carry that are
        NOT stub lines. Under the old `"> _"` prefix every one of them
        classified as `stub-line`, so a unit allowed to move stub lines could
        have moved any of them unremarked.
        """
        prose = [
            "> _Derived from `db/schema.rb` (ActiveRecord's committed schema dump)._",
            "> _Static parse of `config/routes.rb`; the DSL is not executed._",
            "> _No resolved import edges detected._",
            "> _stubbed: something the renderer never emits._",
            "> _stub without a colon token._",
            "> _stub: not_a_real_reason — expected x, found y._",
        ]
        for line in prose:
            with self.subTest(line=line):
                self.assertEqual(GDC.classify_line(MD, line), "extraction-content")

    def test_a_table_row_and_a_graph_edge_stay_extraction_content(self):
        self.assertEqual(
            GDC.classify_line(MD, "| doc_classes | `created_at` | datetime | no | — | — |"),
            "extraction-content",
        )
        self.assertEqual(
            GDC.classify_line(MD, '  Repo["Repo"] --> User["User"]'),
            "extraction-content",
        )

    def test_stub_reason_vocabulary_matches_the_core_enum(self):
        """The classifier's copy of the six reasons cannot drift from the enum.

        The classifier is stdlib-only and standalone on purpose (importing
        `crux.arch` pulls the package's eager httpx chain), so it restates the
        vocabulary. This is the assertion that keeps the copy honest.
        """
        from crux.arch.core import StubReason

        self.assertEqual(
            sorted(GDC.STUB_REASONS),
            sorted(r.value for r in StubReason),
        )


class CoverageVocabularyTests(unittest.TestCase):
    """`coverage.json` keys: vocabulary vs. what the extractor actually read."""

    def test_verdict_keys_are_vocabulary(self):
        for key in ("verdict", "stub_reason", "expected", "found",
                    "n_sources", "n_entities", "status", "reason"):
            with self.subTest(key=key):
                self.assertEqual(
                    GDC.classify_line(COV, f'      "{key}": "x",'),
                    "coverage-vocabulary",
                )

    def test_inputs_found_is_not_vocabulary(self):
        self.assertEqual(
            GDC.classify_line(COV, '      "inputs_found": ['),
            "extraction-content",
        )

    def test_a_key_changed_on_both_sides_is_never_vocabulary(self):
        """Membership in the key set is necessary, not sufficient."""
        for key in ("verdict", "n_entities", "stub_reason"):
            with self.subTest(key=key):
                self.assertEqual(
                    GDC.classify_line(COV, f'      "{key}": "x",', frozenset({key})),
                    "extraction-content",
                )


def _diff(*files: tuple[str, str, list[str]]) -> str:
    """A unified diff over `(a_path, b_path, hunk_lines)` triples.

    `a_path` or `b_path` may be `/dev/null` for a creation or a deletion. The
    hunk lines carry their own leading `+`/`-`/space.
    """
    out: list[str] = []
    for a_path, b_path, lines in files:
        named = b_path if b_path != "/dev/null" else a_path
        out.append(f"diff --git a/{named} b/{named}")
        out.append("index 1111111..2222222 100644")
        out.append(f"--- {a_path if a_path == '/dev/null' else 'a/' + a_path}")
        out.append(f"+++ {b_path if b_path == '/dev/null' else 'b/' + b_path}")
        out.append("@@ -1,4 +1,4 @@")
        out.extend(lines)
    return "\n".join(out) + "\n"


def _cov(repo: str) -> str:
    return f"crux/scripts/tests/arch-corpus/golden/{repo}/_meta/coverage.json"


def _md(repo: str, name: str = "data-model.md") -> str:
    return f"crux/scripts/tests/arch-corpus/golden/{repo}/{name}"


def _enclosed_record(key: str, tail: tuple[str, ...] = ()) -> list[str]:
    """Hunk lines of one concern record whose existing `key` array encloses a
    changed `reason`, followed by `tail`."""
    return [
        '       "n_sources": 3,',
        f'       "{key}": [',
        '         {',
        '           "kind": "file",',
        '           "path": "x.rb",',
        '-          "reason": "unparseable"',
        '+          "reason": "undecodable"',
        '         }',
        '       ],',
        *tail,
    ]


class ExtractionRegressionIsNotVocabularyTests(unittest.TestCase):
    """Defect (a): the classifier bucketed by key NAME, not by what moved.

    A `populated` concern regressing to `no_entities` moves exactly the lines
    whose keys the vocabulary set names — `verdict`, `n_entities`, `stub_reason`
    — and in the spine file `_apply_stub_line` INSERTS the stub line rather than
    replacing content, so the table rows stay and the only `.md` change is one
    `stub-line`. The gate saw zero `extraction-content` and exited 0 over a
    repository that had just lost its whole extraction.
    """

    REGRESSION = [
        '-      "verdict": "populated",',
        '-      "n_entities": 56,',
        '+      "verdict": "stubbed",',
        '+      "stub_reason": "no_entities",',
        '+      "n_entities": 0,',
    ]

    def test_a_populated_to_no_entities_regression_is_extraction_content(self):
        findings = GDC.classify_diff(_diff(
            (_cov("codetriage"), _cov("codetriage"), self.REGRESSION),
            (_md("codetriage"), _md("codetriage"),
             ['+> _stub: no_entities — expected a schema, found none._', '+']),
        ))
        classes = findings["codetriage"]
        self.assertIn("extraction-content", classes,
                      "an extraction regression classified entirely as vocabulary")
        moved = " ".join(classes["extraction-content"])
        self.assertIn('"verdict"', moved)
        self.assertIn('"n_entities"', moved)

    def test_the_same_keys_are_still_vocabulary_when_they_only_appear(self):
        """The three re-blesses this gate guarded ADD these keys and never
        change their values. That case must stay classified as vocabulary, or
        the repair would make the gate refuse the units it was written for."""
        findings = GDC.classify_diff(_diff((
            _cov("codetriage"), _cov("codetriage"),
            ['-      "status": "ok",',
             '-      "reason": "x",',
             '+      "verdict": "populated",',
             '+      "n_sources": 3,',
             '+      "n_entities": 56,'],
        )))
        self.assertEqual(sorted(findings["codetriage"]), ["coverage-vocabulary"])


class DeletedFileAttributionTests(unittest.TestCase):
    """Defect (b): a deleted file's hunk landed under the PREVIOUS repository.

    `git diff` writes `+++ /dev/null` for a deletion, which matches no `+++ b/`
    prefix, so the walker kept the path it had. Every removed row of repository
    B was attributed to repository A, and an `--allow-content A` licensed a
    deletion in B. The `+++ /dev/null` header was counted as a changed line too.
    """

    DIFF = _diff(
        (_md("codetriage"), _md("codetriage"),
         ['-| old | row |', '+| new | row |']),
        (_md("rubygems-org"), "/dev/null",
         ['-| gone | row |', '-| also gone | row |']),
    )

    def test_the_deletion_is_attributed_to_its_own_repository(self):
        findings = GDC.classify_diff(self.DIFF)
        self.assertIn("rubygems-org", findings,
                      "the deleted file's repository is missing from the findings")
        self.assertEqual(len(findings["rubygems-org"]["extraction-content"]), 2)

    def test_the_previous_repository_is_not_charged_for_the_deletion(self):
        findings = GDC.classify_diff(self.DIFF)
        self.assertEqual(len(findings["codetriage"]["extraction-content"]), 2)
        charged = " ".join(findings["codetriage"]["extraction-content"])
        self.assertNotIn("gone", charged)
        self.assertNotIn("rubygems-org", charged)

    def test_the_dev_null_header_is_not_counted_as_a_changed_line(self):
        for _path, _sign, line in GDC._changed_lines(self.DIFF):
            self.assertNotIn("/dev/null", line)

    def test_a_creation_is_attributed_to_its_own_repository(self):
        findings = GDC.classify_diff(_diff(
            (_md("codetriage"), _md("codetriage"), ['-| old | row |']),
            ("/dev/null", _md("papercups"), ['+| brand | new |']),
        ))
        self.assertEqual(len(findings["papercups"]["extraction-content"]), 1)
        self.assertEqual(len(findings["codetriage"]["extraction-content"]), 1)

    def test_a_content_line_that_looks_like_a_file_header_does_not_retarget(self):
        """A removed line reading `-- x` is written `--- x` in a unified diff.
        Inside a hunk that is content, not a header; reading it as a header
        would silently point every following line at the wrong file."""
        findings = GDC.classify_diff(_diff((
            _md("codetriage"), _md("codetriage"),
            ['--- a dashed list item', '+++ another one', '-| row |'],
        )))
        self.assertEqual(len(findings["codetriage"]["extraction-content"]), 3)
        self.assertEqual(sorted(findings), ["codetriage"])


class OmissionClassTests(unittest.TestCase):
    """ADR-0181's three admitted golden moves, and nothing beside them.

    Each positive case is paired with a near miss that must stay extraction
    content, so a class that admitted everything would fail here.
    """

    def test_the_omission_reasons_match_the_core_tuple(self):
        from crux.arch.core import OMISSION_REASONS

        self.assertEqual(sorted(GDC.OMISSION_REASONS), sorted(OMISSION_REASONS))

    def test_the_classifier_grammar_reads_what_core_renders(self):
        from crux.arch import core

        lines = [
            core.omission_line({"path": "Sources/a.swift", "reason": "not-a-file",
                                "kind": "symbolic-link"}),
            core.omission_line({"cap": 500, "dir": "lib", "skipped": 3,
                                "reason": "over-cap", "kind": "scan-cap"}),
            core.OMISSIONS_HEADING,
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertEqual(GDC.classify_line(MD, line), "omission")

    def test_an_added_omissions_section_is_omission(self):
        findings = GDC.classify_diff(_diff((_md("codetriage"), _md("codetriage"), [
            "+## Omissions", "+",
            "+_Recognizable inputs this map does not describe:_", "+",
            "+- `app/x.rb` — unparseable (file)",
        ])))
        self.assertEqual(sorted(findings["codetriage"]), ["omission"])
        self.assertEqual(len(findings["codetriage"]["omission"]), 3)

    def test_an_omission_lookalike_with_an_unknown_reason_is_content(self):
        for line in ("- `app/x.rb` — vanished (file)",
                     "- `app/x.rb` — unparseable",
                     "| `app/x.rb` | unparseable |"):
            with self.subTest(line=line):
                self.assertEqual(GDC.classify_line(MD, line), "extraction-content")

    RESIDUAL = ("- Source(s) Python's parser refused (hashed, not parsed): "
                "`backend/app/api/deps.py`.")

    def test_a_removed_residual_named_by_the_new_section_is_omission(self):
        findings = GDC.classify_diff(_diff((_md("fastapi-fullstack"), _md("fastapi-fullstack"), [
            "-" + self.RESIDUAL,
            "+## Omissions",
            "+- `backend/app/api/deps.py` — unparseable (file)",
        ])))
        self.assertEqual(sorted(findings["fastapi-fullstack"]), ["omission"])

    def test_a_removed_residual_the_section_does_not_name_is_content(self):
        findings = GDC.classify_diff(_diff((_md("fastapi-fullstack"), _md("fastapi-fullstack"), [
            "-" + self.RESIDUAL,
            "+## Omissions",
            "+- `backend/app/other.py` — unparseable (file)",
        ])))
        self.assertEqual(len(findings["fastapi-fullstack"]["extraction-content"]), 1)

    def test_a_residual_named_only_in_another_file_is_content(self):
        findings = GDC.classify_diff(_diff(
            (_md("fastapi-fullstack"), _md("fastapi-fullstack"), ["-" + self.RESIDUAL]),
            (_md("fastapi-fullstack", "api-surface.md"), _md("fastapi-fullstack", "api-surface.md"),
             ["+- `backend/app/api/deps.py` — unparseable (file)"]),
        ))
        self.assertIn("extraction-content", findings["fastapi-fullstack"])

    def test_an_added_residual_or_removed_table_row_is_content(self):
        findings = GDC.classify_diff(_diff((_md("fastapi-fullstack"), _md("fastapi-fullstack"), [
            "+" + self.RESIDUAL,
            "-| `backend/app/api/deps.py` | route |",
            "+- `backend/app/api/deps.py` — unparseable (file)",
        ])))
        self.assertEqual(len(findings["fastapi-fullstack"]["extraction-content"]), 2)

    def test_an_added_coverage_omissions_key_is_omission(self):
        findings = GDC.classify_diff(_diff((_cov("codetriage"), _cov("codetriage"), [
            '+      "omissions": [],',
            '+      "omissions": [',
            '+        {',
            '+          "kind": "file",',
            '+          "path": "x.rb",',
            '+          "reason": "unparseable"',
            '+        }',
            '+      ],',
        ])))
        self.assertEqual(sorted(findings["codetriage"]), ["omission"])
        self.assertEqual(len(findings["codetriage"]["omission"]), 8)

    def test_the_block_ends_at_its_bracket(self):
        findings = GDC.classify_diff(_diff((_cov("codetriage"), _cov("codetriage"), [
            '+      "omissions": [',
            '+        "x.rb"',
            '+      ],',
            '+      "inputs_found": [',
        ])))
        self.assertEqual(len(findings["codetriage"]["omission"]), 3)
        self.assertEqual(len(findings["codetriage"]["extraction-content"]), 1)

    def test_a_both_sided_omissions_key_line_is_omission(self):
        """The key line is omission whether it appears on one side or both."""
        findings = GDC.classify_diff(_diff((_cov("codetriage"), _cov("codetriage"), [
            '-      "omissions": [],',
            '+      "omissions": ["x.rb"],',
        ])))
        self.assertEqual(sorted(findings["codetriage"]), ["omission"])
        self.assertEqual(len(findings["codetriage"]["omission"]), 2)

    def _enclosed(self, key: str = "omissions", tail: tuple[str, ...] = ()) -> list[str]:
        return _enclosed_record(key, tail)

    def test_a_changed_reason_inside_an_existing_omissions_array_is_omission(self):
        findings = GDC.classify_diff(_diff((_cov("codetriage"), _cov("codetriage"),
                                            self._enclosed())))
        self.assertEqual(findings["codetriage"], {"omission": [
            f'{_cov("codetriage")}: -"reason": "unparseable"',
            f'{_cov("codetriage")}: +"reason": "undecodable"',
        ]})

    def test_the_same_change_under_another_key_is_content(self):
        """Near miss: the enclosing array is not `omissions`."""
        findings = GDC.classify_diff(_diff((_cov("codetriage"), _cov("codetriage"),
                                            self._enclosed(key="inputs_missing"))))
        self.assertEqual(sorted(findings["codetriage"]), ["extraction-content"])
        self.assertIn('-"reason": "unparseable"',
                      " ".join(findings["codetriage"]["extraction-content"]))

    def test_a_change_after_the_array_closes_is_content(self):
        """Near miss: the line follows the omissions array, inside the same record."""
        findings = GDC.classify_diff(_diff((_cov("codetriage"), _cov("codetriage"),
                                            self._enclosed(tail=(
                                                '-      "verdict": "populated"',
                                                '+      "verdict": "stubbed"',
                                            )))))
        self.assertEqual(len(findings["codetriage"]["omission"]), 2)
        self.assertEqual(findings["codetriage"]["extraction-content"], [
            f'{_cov("codetriage")}: -"verdict": "populated"',
            f'{_cov("codetriage")}: +"verdict": "stubbed"',
        ])

    def test_each_side_is_enclosed_by_its_own_array(self):
        """Near miss: the old side's array does not enclose a new-side line.

        The removed array is omission. The added `reason` sits where the array
        was, but on the new side no omissions key encloses it, so it keeps the
        classification it has today, a one-sided vocabulary key.
        """
        findings = GDC.classify_diff(_diff((_cov("codetriage"), _cov("codetriage"), [
            '       "n_sources": 3,',
            '-      "omissions": [',
            '-        "x.rb"',
            '-      ],',
            '+      "reason": "x.rb",',
            '       "verdict": "populated"',
        ])))
        self.assertEqual(len(findings["codetriage"]["omission"]), 3)
        self.assertEqual(findings["codetriage"]["coverage-vocabulary"],
                         [f'{_cov("codetriage")}: +"reason": "x.rb",'])

    def test_an_omissions_key_outside_the_hunk_keeps_todays_classification(self):
        """Fallback: the hunk starts inside the array, so the enclosing key is
        not visible and the both-sided `reason` stays extraction content. The
        positive control is the same hunk with the key line visible."""
        invisible = self._enclosed()[3:]
        findings = GDC.classify_diff(_diff((_cov("codetriage"), _cov("codetriage"),
                                            invisible)))
        self.assertEqual(findings["codetriage"], {"extraction-content": [
            f'{_cov("codetriage")}: -"reason": "unparseable"',
            f'{_cov("codetriage")}: +"reason": "undecodable"',
        ]})
        visible = self._enclosed()[1:]
        findings = GDC.classify_diff(_diff((_cov("codetriage"), _cov("codetriage"),
                                            visible)))
        self.assertEqual(sorted(findings["codetriage"]), ["omission"])

    def test_a_new_hunk_does_not_inherit_the_previous_hunks_array(self):
        """Fallback: each hunk starts with no known enclosure."""
        diff = _diff((_cov("codetriage"), _cov("codetriage"), [
            '       "omissions": [',
            '         "a.rb",',
        ])).rstrip("\n") + "\n" + "\n".join([
            "@@ -40,3 +40,3 @@",
            '-          "reason": "unparseable"',
            '+          "reason": "undecodable"',
        ]) + "\n"
        findings = GDC.classify_diff(diff)
        self.assertEqual(sorted(findings["codetriage"]), ["extraction-content"])
        self.assertEqual(len(findings["codetriage"]["extraction-content"]), 2)

    def test_an_overlay_file_is_attributed_to_its_repository(self):
        path = ("crux/scripts/tests/arch-corpus/golden-by-python/3.14/"
                "fastapi-fullstack/_meta/coverage.json")
        findings = GDC.classify_diff(_diff((path, path, ['+      "omissions": [],'])))
        self.assertEqual(findings, {"fastapi-fullstack": {
            "omission": [f'{path}: +"omissions": [],']}})

    def test_files_reports_each_changed_golden_by_class(self):
        files = GDC.classify_files(_diff(
            (_cov("codetriage"), _cov("codetriage"), ['+      "omissions": [],']),
            (_md("codetriage"), _md("codetriage"), ["-| row |"]),
        ))
        self.assertEqual(files, {_cov("codetriage"): {"omission": 1},
                                 _md("codetriage"): {"extraction-content": 1}})


class MainDiffArgvTests(unittest.TestCase):
    """main() asks git for whole-file context, so the enclosing omissions key
    and a file's whole Omissions section are visible to the walk."""

    def _calls(self, diff: str = "") -> tuple[list[list[str]], int]:
        calls: list[list[str]] = []

        def fake_run(args: list[str]) -> str:
            calls.append(args)
            return diff if len(calls) == 1 else ""

        with unittest.mock.patch.object(GDC, "_run", fake_run), \
                unittest.mock.patch("sys.stdout"), unittest.mock.patch("sys.stderr"):
            code = GDC.main([])
        return calls, code

    def test_both_git_diff_calls_request_whole_file_context(self):
        calls, code = self._calls()
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 2)
        for args in calls:
            with self.subTest(args=args):
                self.assertEqual(args[:2], ["git", "diff"])
                self.assertIn(GDC.WHOLE_FILE_CONTEXT, args)
        self.assertNotIn("--cached", calls[0])
        self.assertIn("--cached", calls[1])
        self.assertEqual(GDC.WHOLE_FILE_CONTEXT, f"--unified={2**31 - 1}")

    def test_main_refuses_unnamed_content_and_admits_an_enclosed_change(self):
        """The refusal and its positive control run on one coverage fixture."""
        cov = _cov("codetriage")
        _calls, code = self._calls(_diff((cov, cov, _enclosed_record("omissions"))))
        self.assertEqual(code, 0)
        content = _diff((cov, cov, _enclosed_record("inputs_missing")))
        err = io.StringIO()
        with unittest.mock.patch.object(GDC, "_run", side_effect=[content, ""]), \
                unittest.mock.patch("sys.stdout"), unittest.mock.patch("sys.stderr", err):
            code = GDC.main([])
        self.assertEqual(code, 1)
        self.assertIn("REFUSED — codetriage moved extraction content and was not "
                      "named by --allow-content:", err.getvalue())
        self.assertIn('-"reason": "unparseable"', err.getvalue())


if __name__ == "__main__":
    unittest.main()
