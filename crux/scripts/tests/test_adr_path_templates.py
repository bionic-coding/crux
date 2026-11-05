"""The ADR-path cycle templates run council deliberation through the council runner
and gate independent review on reviewer reports.

Three templates carry the ADR module or the review module's first prompt:
`cycle-module-adr.yaml`, `cycle-promptbook-template.yaml` (which embeds a copy of
the ADR module and of the review module) and `cycle-module-review.yaml`. This suite
parses each as YAML and checks:

1. the council prompt (ordinal 2 of the ADR module) names `run-council.py`, names the
   five dimensions, and carries no `srde` and no withdrawn council alternative;
2. the ADR module copy in the canonical book equals the module file's prompts for
   ordinals 2 to 4 byte for byte after the `{M}` substitution;
3. the review prompt (ordinal 1 of the review module) carries the independent-review
   gate paragraph byte for byte as its last paragraph, in the module and in the book;
4. the canonical book's `run_autonomy` lists the stop for a council that cannot run;
5. no block-scalar line opens with `rule:`, `[`, `{` or `--`, which YAML or the
   templates' own grammar would misread.

Every check takes injected text, so each positive control seeds one violation in
memory and expects the check to report it. Stdlib plus PyYAML; reads only the
shipped templates, so it is safe against the staged artifact.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

# Frozen historical orchestration contract; live-cycle coverage is separate.
from _legacy_workflow_prose import legacy_path

import yaml

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import council_alternative  # noqa: E402

TEMPLATES = SCRIPTS.parent / "templates"
ADR_MODULE = TEMPLATES / "cycle-module-adr.yaml"
REVIEW_MODULE = TEMPLATES / "cycle-module-review.yaml"
BOOK = TEMPLATES / "cycle-promptbook-template.yaml"

DIMENSIONS = ("Completeness", "Correctness", "Consistency", "Clarity", "Security")

REVIEW_GATE_PARAGRAPH = """\
**The independent-review gate.** This prompt advances only with reviewer
reports attached (rule:review-gate-needs-a-reviewer-report). Commit the
work, then fix the reviewed range as
`<the run's base_commit>..<HEAD at dispatch>`. The gate check does not
compare the base, so hold it. Each reviewer writes its own
report: `uv run "${CRUX_PLUGIN_ROOT}/scripts/write-review-report.py"
<run-RUN-NNN.yaml> --prompt <n> --range <base>..<end> --verdict
'<verdict>'`, adding one `--finding '<finding>'` per finding. Single-quote
each value and write an embedded `'` as `'\\''`; never put model-written
text inside double quotes. Text with quotes or several lines goes in a
file passed with `--verdict-file` or `--finding-file`. A reviewer whose
harness grants no shell returns those fields, and the agent that
commissioned the review runs the writer with them. From the range end to
the advance, write nothing to the run snapshot or the book: the range
covers both, so a later write to either refuses every report. Commit only
the reports before the advance: a commit after the range end that changes
a reviewed path refuses every report. Record notes, deferrals and gate
tokens after the advance. Attach every report with `--artifacts`. A
council record never satisfies this gate."""

FORBIDDEN_LINE_START = re.compile(r"^\s*(?:rule:|\[|\{|--)")


def load(path: Path):
    return yaml.safe_load(legacy_path(path).read_text(encoding="utf-8"))


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def book_module(book: dict, tag: str) -> list[dict]:
    return [p for p in book["prompts"] if p.get("module_tag") == tag]


def adr_council_problems(prompt: str) -> list[str]:
    """What is wrong with an ADR-module council prompt."""
    problems = []
    if "run-council.py" not in prompt:
        problems.append("does not name run-council.py")
    for dim in DIMENSIONS:
        if dim not in prompt:
            problems.append(f"drops the dimension {dim}")
    if "srde" in prompt:
        problems.append("names srde")
    for hit in council_alternative.find_withdrawn_alternative(prompt):
        problems.append(f"carries a withdrawn alternative: {hit}")
    return problems


def review_gate_problems(prompt: str) -> list[str]:
    if "write-review-report.py" not in prompt:
        return ["does not name write-review-report.py"]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", prompt) if p.strip()]
    if paragraphs[-1] != REVIEW_GATE_PARAGRAPH:
        return ["the independent-review gate paragraph is not the last paragraph"]
    return []


def run_autonomy_problems(text: str) -> list[str]:
    problems = []
    if ("(c) a council that cannot run through the council runner "
            "yields DEFER_TO_HUMAN") not in text:
        problems.append("lacks the stop for a council that cannot run")
    if "The only stops are (a)" not in text:
        problems.append("lacks the stop list")
    return problems


def line_start_problems(raw: str) -> list[str]:
    """Lines of a block scalar that open with a shape the templates forbid."""
    problems = []
    in_block = False
    block_indent = 0
    for number, line in enumerate(raw.splitlines(), 1):
        if not in_block:
            if re.search(r":\s*[|>][+-]?\s*$", line):
                in_block = True
                block_indent = len(line) - len(line.lstrip()) + 1
            continue
        if line.strip() == "":
            continue
        indent = len(line) - len(line.lstrip())
        if indent < block_indent:
            in_block = bool(re.search(r":\s*[|>][+-]?\s*$", line))
            if in_block:
                block_indent = indent + 1
            continue
        if FORBIDDEN_LINE_START.match(line):
            problems.append(f"line {number}: {line.strip()[:40]!r}")
    return problems


class CouncilPromptTests(unittest.TestCase):

    def test_module_council_prompt_runs_the_council_runner(self):
        council = load(ADR_MODULE)[1]
        self.assertEqual(adr_council_problems(council["prompt"]), [])
        self.assertEqual(council["side_effects"], ["run-adr-council"])
        self.assertEqual(
            norm(council["expected_output"]),
            "the council record's path attached; per-seat decisions and blocking "
            "findings listed from it")

    def test_book_copy_equals_module_for_ordinals_two_to_four(self):
        module = load(ADR_MODULE)
        embedded = book_module(load(BOOK), "adr-1")
        self.assertEqual(len(module), len(embedded))
        for i in (1, 2, 3):
            for key in ("purpose", "prompt", "expected_output", "side_effects"):
                with self.subTest(ordinal=i + 1, field=key):
                    a, b = module[i][key], embedded[i][key]
                    if isinstance(a, str):
                        a = a.replace("{M}", "1")
                    self.assertEqual(a, b)

    # ---- positive controls ----

    def test_review_prompt_records_security_deferrals_after_the_advance(self):
        # The review range covers the run snapshot, so a Notes write before the advance
        # refuses every reviewer report.
        for name, prompt in (("module", load(REVIEW_MODULE)[0]["prompt"]),
                             ("book", book_module(load(BOOK), "review-1")[0]["prompt"])):
            with self.subTest(copy=name):
                self.assertIn("with residual-risk rationale, written after this prompt's advance",
                              norm(prompt))

    def test_control_council_check_reports_each_seeded_violation(self):
        good = load(ADR_MODULE)[1]["prompt"]
        self.assertEqual(adr_council_problems(good), [])
        for seeded, needle in (
            (good.replace("run-council.py", "the runner"), "run-council.py"),
            (good.replace("Security", "Safety"), "Security"),
            (good + "\nRun the srde skill.\n", "srde"),
            (good + "\nOr, equivalently, dispatch 5 parallel review agents.\n", "withdrawn"),
        ):
            with self.subTest(needle=needle):
                self.assertTrue(any(needle in p for p in adr_council_problems(seeded)))


class RoutingTests(unittest.TestCase):
    """The council, findings and close prompts tell the conductor what
    advance-run.py and the gate check accept."""

    def both(self):
        return (("module", load(ADR_MODULE)), ("book", book_module(load(BOOK), "adr-1")))

    def test_council_prompt_decides_could_not_run_from_exit_code_and_outcome(self):
        for name, prompts in self.both():
            with self.subTest(copy=name):
                text = norm(prompts[1]["prompt"])
                self.assertIn("Never decide whether the council ran from the aggregate action", text)
                self.assertIn("a council that ran also carries the action DEFER_TO_HUMAN", text)
                self.assertIn("Exit 1 with `outcome: could-not-run`", text)
                self.assertIn("`refusal_reason.code`", text)
                self.assertIn("Exit 1 with `outcome: ran`", text)
                self.assertIn("secret scan", text)
                self.assertIn("Exit 2: no committed council record exists", text)
                self.assertIn("Exit 0:", text)
                self.assertNotIn("A record whose action is DEFER_TO_HUMAN means", text)


class ReviewGateTests(unittest.TestCase):

    def test_module_review_prompt_carries_the_gate_paragraph_last(self):
        self.assertEqual(review_gate_problems(load(REVIEW_MODULE)[0]["prompt"]), [])

    def test_book_review_prompt_carries_the_gate_paragraph_last(self):
        review = book_module(load(BOOK), "review-1")[0]
        self.assertEqual(review_gate_problems(review["prompt"]), [])

    def test_control_gate_check_reports_a_missing_or_misplaced_paragraph(self):
        good = load(REVIEW_MODULE)[0]["prompt"]
        self.assertEqual(review_gate_problems(good), [])
        self.assertTrue(review_gate_problems(good.replace("write-review-report.py", "the writer")))
        self.assertTrue(review_gate_problems(good + "\nOne more paragraph.\n"))
        self.assertTrue(review_gate_problems(good.replace(REVIEW_GATE_PARAGRAPH, "")))


class RunAutonomyTests(unittest.TestCase):

    def test_run_autonomy_stops_when_the_council_cannot_run(self):
        self.assertEqual(run_autonomy_problems(norm(load(BOOK)["run_autonomy"])), [])

    def test_control_the_check_reads_the_stop_text(self):
        text = norm(load(BOOK)["run_autonomy"])
        self.assertEqual(run_autonomy_problems(text), [])
        seeded = text.replace(
            "a council that cannot run through the council runner yields DEFER_TO_HUMAN",
            "a council that cannot run is replaced by native agents")
        self.assertNotEqual(seeded, text)
        self.assertTrue(run_autonomy_problems(seeded))
        dropped = text.replace("The only stops are (a)", "The stops are (a)")
        self.assertNotEqual(dropped, text)
        self.assertTrue(run_autonomy_problems(dropped))


class RoundAndCommitRuleTests(unittest.TestCase):
    """Every council prompt of every cycle template states the round rule and the commit rule.

    `--round` is the number of council records with outcome `ran` already in the module
    (in a patch book, the prompt), plus one. `run-council.py` refuses a mismatch before any
    call. The commit rule: the council runner commits the attempt record and the council
    record itself, so no prompt tells the conductor to commit a council record. Prose
    states both rules for books authored after the template; it enforces neither, and no
    template corrects a book that already exists.
    """

    TEMPLATE_NAMES = (
        "cycle-module-adr.yaml",
        "cycle-module-verify.yaml",
        "cycle-promptbook-template.yaml",
        "iterate-promptbook-template.yaml",
        "patch-promptbook-template.yaml",
    )
    STALE = re.compile(r"next round number|module's next round")
    PINNED = "The council runner commits the attempt record and the council record itself."
    #: An instruction to the conductor to commit a council record. In a council prompt a
    #: bare "Commit the record" names the council record too. "commits" and "committed"
    #: do not match, so the pinned sentence and "has committed the record" pass. The
    #: plural and the attempt record match too: the council runner commits both.
    CONDUCTOR_COMMIT = re.compile(
        r"\b[Cc]ommit (?:the|each|every|this|both) (?:new )?(?:council |attempt )?records?\b"
        r"|\b[Cc]ommit it, then attach")
    #: The same instruction outside a council prompt, where "commit that record" or
    #: "commit both records" may name a refutation or owner-exception record: only a
    #: phrase naming a council record or an attempt record counts.
    CONDUCTOR_COMMIT_COUNCIL = re.compile(
        r"\b[Cc]ommit (?:the|each|every|this|both) (?:new )?(?:council|attempt) records?\b")

    @staticmethod
    def prompts_of(doc) -> list[str]:
        if isinstance(doc, dict):
            doc = doc.get("prompts")
        return [str(p.get("prompt") or "") for p in (doc or []) if isinstance(p, dict)]

    @classmethod
    def council_prompts(cls, name: str) -> list[str]:
        return [t for t in cls.prompts_of(load(TEMPLATES / name)) if "run-council.py" in t and "--round" in t]

    @staticmethod
    def rule_problems(text: str) -> list[str]:
        flat = norm(text)
        problems = []
        if "the number of council records with outcome `ran` already" not in flat:
            problems.append("does not define --round as the counted ran records plus one")
        if "could-not-run record takes no place" not in flat:
            problems.append("does not say a could-not-run record takes no place")
        if '`"record": null`' not in flat:
            problems.append("does not state the refusal shape")
        if RoundAndCommitRuleTests.PINNED not in flat:
            problems.append("does not say the council runner commits the attempt and council records")
        if RoundAndCommitRuleTests.CONDUCTOR_COMMIT.search(flat):
            problems.append("tells the conductor to commit the council record")
        return problems

    def test_each_template_has_a_council_prompt_and_it_states_both_rules(self):
        for name in self.TEMPLATE_NAMES:
            prompts = self.council_prompts(name)
            with self.subTest(template=name):
                self.assertTrue(prompts, "no council prompt found, so nothing was checked")
                for text in prompts:
                    self.assertEqual(self.rule_problems(text), [])

    def test_no_prompt_tells_the_conductor_to_commit_a_council_record(self):
        for name in self.TEMPLATE_NAMES:
            prompts = self.prompts_of(load(TEMPLATES / name))
            with self.subTest(template=name):
                self.assertTrue(prompts, "no prompt found, so nothing was checked")
                hits = [m.group(0) for t in prompts
                        for m in self.CONDUCTOR_COMMIT_COUNCIL.finditer(norm(t))]
                self.assertEqual(hits, [])

    def test_control_the_check_reports_each_missing_rule(self):
        good = self.council_prompts("cycle-module-adr.yaml")[0]
        self.assertEqual(self.rule_problems(good), [])
        for needle in ("the number of council records with outcome `ran` already",
                       "could-not-run record takes no place",
                       '`"record": null`',
                       self.PINNED):
            with self.subTest(needle=needle):
                broken = norm(good).replace(needle, "x")
                self.assertNotEqual(broken, norm(good))
                self.assertEqual(len(self.rule_problems(broken)), 1)
        for stale in ("Commit the council record before you advance.",
                      "Commit each council record before you advance.",
                      "Commit the record, then attach it.",
                      "Commit it, then attach it.",
                      "Commit the council records before you advance.",
                      "Commit both records, then attach the council record.",
                      "Commit this record before you advance.",
                      "Commit the attempt record before the council runs.",
                      "Commit every attempt record before you advance."):
            with self.subTest(stale=stale):
                seeded = norm(good) + " " + stale
                self.assertEqual(self.rule_problems(seeded),
                                 ["tells the conductor to commit the council record"])
        for fine in ("The council runner has committed the record.",
                     "The council runner commits the record.",
                     "Commit the refutation record before the advance."):
            with self.subTest(fine=fine):
                self.assertEqual(self.rule_problems(norm(good) + " " + fine), [])
        self.assertIsNotNone(self.CONDUCTOR_COMMIT_COUNCIL.search(
            "then commit the new council record, and attach it"))
        for stale in ("then commit both council records, and attach one",
                      "commit the attempt record before the council runs",
                      "commit this council record before you advance"):
            with self.subTest(stale_outside=stale):
                self.assertIsNotNone(self.CONDUCTOR_COMMIT_COUNCIL.search(stale))
        for fine in ("commit that record, attach it",
                     "Commit the refutation record before the advance.",
                     "Commit both records before the advance."):
            with self.subTest(fine_outside=fine):
                self.assertIsNone(self.CONDUCTOR_COMMIT_COUNCIL.search(fine))
        stale = "Round `<r>` is this module's next round number, starting at 1."
        self.assertIsNotNone(self.STALE.search(stale))


class RecoveryRouteProseTests(unittest.TestCase):
    """Every conductor surface routes a council runner that ended without a summary to recovery.

    A runner killed after its result commit leaves a resolved attempt, so nothing holds the
    scope. A conductor that then counts the committed `ran` record and convenes round R+1
    repeats a deliberation. Each surface says to recover first, and every recovery or probe
    command carries `--prompt <n>`: without it recovery cannot recognise a record whose
    pending copy is already removed. Prose states both rules; it enforces neither.
    """

    ROOT = TEMPLATES.parent
    SKILL_FILES = (
        "skills/run-promptbook/references/gates.md",
        "skills/council/SKILL.md",
        "skills/run-adr-council/SKILL.md",
        "skills/dev-cycle/SKILL.md",
        "skills/iterate/SKILL.md",
        "skills/patch-cycle/SKILL.md",
        "agents/commander.md",
        "agents/dev-lead.md",
        "agents/reviewer.md",
    )
    TEMPLATE_FILES = RoundAndCommitRuleTests.TEMPLATE_NAMES
    #: A runner that ended before it reported: no exit code, a signal, or a code outside 0, 1, 2.
    ENDED = re.compile(r"ended without an exit code|ends without an exit code|no exit code, a signal")
    #: The rule that no round convenes until recovery has reported.
    NEVER_BEFORE = re.compile(r"(?:until|before) recovery reports")

    def texts(self) -> dict[str, str]:
        out = {name: norm((legacy_path(self.ROOT / name)).read_text(encoding="utf-8")) for name in self.SKILL_FILES}
        for name in self.TEMPLATE_FILES:
            out["templates/" + name] = norm((legacy_path(TEMPLATES / name)).read_text(encoding="utf-8"))
        return out

    @staticmethod
    def bare_recover_commands(text: str) -> list[str]:
        """Legacy runner commands require a prompt; flag descriptions are not commands."""
        found = []
        for match in re.finditer(r"\brun-council\.py\b[^`\n]*", text):
            command = match.group()
            if "--recover" in command and not re.search(
                r"--prompt(?:\s+|=)(?:<[^>]+>|N|[1-9]\d*)(?=\s|$)", command
            ):
                found.append(command)
        return found

    def test_every_surface_routes_a_runner_that_ended_without_a_summary_to_recovery(self):
        for name, text in self.texts().items():
            if name in ("agents/reviewer.md",):
                continue  # one sentence: it hands the commissioning agent the same rule
            with self.subTest(surface=name):
                self.assertIsNotNone(self.ENDED.search(text), "no sentence for a runner that ended")
                self.assertIsNotNone(self.NEVER_BEFORE.search(text), "no rule against convening before recovery reports")

    def test_every_recovery_command_names_the_prompt_and_each_surface_shows_one(self):
        for name, text in self.texts().items():
            with self.subTest(surface=name):
                self.assertEqual(self.bare_recover_commands(text), [])
                if name != "agents/reviewer.md":
                    self.assertIn("--recover", text, "no recovery command, so nothing was checked")

    def test_control_the_check_reports_a_bare_recovery_command_and_a_missing_sentence(self):
        good = self.texts()["skills/council/SKILL.md"]
        self.assertEqual(self.bare_recover_commands(good), [])
        seeded = good + " Then run `run-council.py --recover <run>` and wait."
        self.assertEqual(len(self.bare_recover_commands(seeded)), 1)
        self.assertIsNone(self.ENDED.search("An exit 2 that names a claimed attempt."))
        self.assertIsNone(self.NEVER_BEFORE.search("Never convene another round over a claimed attempt."))
        self.assertIsNotNone(self.ENDED.search(good))
        self.assertIsNotNone(self.NEVER_BEFORE.search(good))

    def test_recovery_detector_distinguishes_flag_prose_and_complete_commands(self):
        for good in (
            "`--recover ATTEMPT` sends no request.",
            '`run-council.py --recover <run> --prompt <n>`',
            'uv run "/absolute/plugin/scripts/run-council.py" --recover <run> --prompt 2 --probe',
        ):
            with self.subTest(text=good):
                self.assertEqual(self.bare_recover_commands(good), [])
        for bad in (
            "`run-council.py --recover <run>`",
            "`run-council.py --recover <run> --prompt`",
            "`run-council.py --recover <run> --prompt --probe`",
            "`run-council.py --recover <run>` then mention `--prompt N`.",
        ):
            with self.subTest(text=bad):
                self.assertEqual(len(self.bare_recover_commands(bad)), 1)


class WitnessRefusalAndLandedRouteTests(unittest.TestCase):
    """Each conductor surface gives one next step, with one actor, for a witness refusal and a landed commit.

    A witness `commit` refusal with `"refused": "commit"` is a git refusal. The path stays a
    retryable `commit-run-work` subject, so a council runner run would spend a retry rather than
    record `preflight-needs-owner`: the owner stop comes from the conductor. A
    `commit-refused` recovery report with `"commit_landed": true` names its branch (a timeout's
    remedy order first) before the sentence that advances an open attempt. Prose states both
    rules; it enforces neither.
    """

    ROOT = TEMPLATES.parent
    GATES = "skills/run-promptbook/references/gates.md"
    SURFACES = (GATES, "agents/commander.md") + tuple("templates/" + n for n in RoundAndCommitRuleTests.TEMPLATE_NAMES)
    ADVANCE_OPEN = re.compile(r"advances? (?:the prompt )?`--outcome blocked` with the attempt record attached")
    GIT_REFUSAL = '"refused": "commit"'
    LANDED = '"commit_landed": true'

    def texts(self) -> dict[str, str]:
        out = {}
        for name in self.SURFACES + ("agents/dev-lead.md", "agents/reviewer.md", "skills/council/SKILL.md"):
            path = TEMPLATES / name[len("templates/"):] if name.startswith("templates/") else self.ROOT / name
            out[name] = norm(legacy_path(path).read_text(encoding="utf-8"))
        return out

    @classmethod
    def git_refusal_problems(cls, text: str) -> list[str]:
        """Problems with a surface's next step for a witness `commit` git refusal."""
        i = text.find(cls.GIT_REFUSAL)
        if i < 0:
            return ["no sentence names a witness commit git refusal"]
        j = text.find("contradicted-premise", i, i + 600)
        if j < 0:
            return ["a git refusal names no contradicted-premise stop"]
        # Only the text between the refusal and its stop can lead the conductor astray.
        return ["a git refusal leads to preflight-needs-owner"] if "preflight-needs-owner" in text[i:j] else []

    @classmethod
    def landed_problems(cls, text: str, advance: "re.Pattern[str] | None" = None) -> list[str]:
        """Problems with the placement and content of the `commit_landed` branch."""
        i = text.find(cls.LANDED)
        if i < 0:
            return ["no commit_landed branch"]
        out = []
        m = (advance or cls.ADVANCE_OPEN).search(text)
        if m and m.start() < i:
            out.append("the open-attempt sentence precedes the commit_landed branch")
        window = text[i:i + 450]
        if "timeout" not in window:
            out.append("the commit_landed branch has no timeout remedy order")
        return out

    def test_a_witness_commit_git_refusal_is_an_owner_stop_not_a_council_runner_rerun(self):
        for name in self.SURFACES:
            with self.subTest(surface=name):
                self.assertEqual(self.git_refusal_problems(self.texts()[name]), [])

    def test_the_commit_landed_branch_precedes_the_open_attempt_sentence_and_names_the_timeout_order(self):
        for name in self.SURFACES:
            with self.subTest(surface=name):
                self.assertEqual(self.landed_problems(self.texts()[name]), [])

    def test_control_the_checks_report_the_old_wording(self):
        old = ("When `run-work-witness.py commit` refuses, do not retry the commit. "
               "Run the council runner again, and it records `preflight-needs-owner` for the owner.")
        self.assertEqual(self.git_refusal_problems(old), ["no sentence names a witness commit git refusal"])
        seeded = '`"refused": "commit"` leads the council runner to record `preflight-needs-owner`, a contradicted-premise stop.'
        self.assertEqual(self.git_refusal_problems(seeded), ["a git refusal leads to preflight-needs-owner"])
        self.assertEqual(self.git_refusal_problems('`"refused": "commit"` is a refusal by the owner.'),
                         ["a git refusal names no contradicted-premise stop"])
        late = ('advance `--outcome blocked` with the attempt record attached. After `commit-refused` with '
                '`"commit_landed": true`, run recovery once more.')
        self.assertEqual(self.landed_problems(late),
                         ["the open-attempt sentence precedes the commit_landed branch",
                          "the commit_landed branch has no timeout remedy order"])
        good = ('After `commit-refused` with `"commit_landed": true` and code `timeout`, follow the remedy order. '
                'Advance `--outcome blocked` with the attempt record attached.')
        self.assertEqual(self.landed_problems(good), [])


class LineStartTests(unittest.TestCase):

    def test_no_block_scalar_line_opens_with_a_forbidden_shape(self):
        for path in (ADR_MODULE, REVIEW_MODULE, BOOK):
            with self.subTest(template=path.name):
                self.assertEqual(line_start_problems(legacy_path(path).read_text(encoding="utf-8")), [])

    def test_control_the_scan_sees_each_forbidden_shape(self):
        for bad in ("rule:some-slug", "[link]", "{token}", "--flag"):
            raw = f"- prompt: |\n    ok line\n    {bad} opens a line\n"
            with self.subTest(bad=bad):
                self.assertEqual(len(line_start_problems(raw)), 1)
        self.assertEqual(line_start_problems("- prompt: |\n    fine (rule:a-slug)\n"), [])


if __name__ == "__main__":
    unittest.main()
