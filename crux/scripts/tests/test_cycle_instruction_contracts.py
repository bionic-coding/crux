"""Live instruction contracts for cycles; retired book prose has frozen fixtures."""
from pathlib import Path
import re
import unittest

try:
    from ._dev_surface import TREE_AGENTS_MD, require_dev_surface
except ImportError:
    from _dev_surface import TREE_AGENTS_MD, require_dev_surface

PLUGIN = Path(__file__).resolve().parents[2]


def read(relative):
    return (PLUGIN / relative).read_text(encoding="utf-8")


def flat(relative):
    return " ".join(read(relative).split())


def missing(text, requirements):
    return [item for item in requirements if item not in text]


REPO = PLUGIN.parent
RETIRED_RELEASE_TEXT = ("release-ready", "release-verified", "before the last Test run",
                        "final Test run", "independent review before publication",
                        "Plan → Release → Reflect")


def repo_flat(testcase, relative):
    path = REPO / relative
    require_dev_surface(testcase, path, relative)
    return " ".join(path.read_text(encoding="utf-8").split())


class ReleaseListInstructionContracts(unittest.TestCase):
    """A release cycle runs one of two fixed lists; the instructions delete what they retire."""

    def test_cycle_skill_describes_the_two_lists_and_retires_the_old_release(self):
        text = flat("skills/cycle/SKILL.md")
        for clause in ("`--list beta` or `--list official`",
                       "verify is the only step that runs the registered suites",
                       "A failed release step stops the release",
                       "sets that step's task back to pending",
                       "reopens every later task",
                       "A release queue item starts a beta-list cycle",
                       "An official cycle is created directly"):
            self.assertIn(clause, text)
        self.assertEqual([x for x in RETIRED_RELEASE_TEXT if x in text], [])
        self.assertNotIn("Release findings requiring replanning return to Plan", text)

    def test_commands_reference_documents_create_list_and_drops_release_ready(self):
        text = flat("skills/cycle/references/commands.md")
        for clause in ("create --type release --list beta|official",
                       "A listed release cycle allows only",
                       "refuses every other action",
                       "task CYC-ID --task-id ID --state pending",
                       "reopens every later task"):
            self.assertIn(clause, text)
        self.assertEqual([x for x in RETIRED_RELEASE_TEXT if x in text], [])

    def test_testing_reference_makes_verify_the_only_suite_step(self):
        text = flat("skills/cycle/references/testing.md")
        self.assertIn("verify is the only release step that runs the registered suites", text)
        self.assertEqual([x for x in RETIRED_RELEASE_TEXT if x in text], [])

    def test_agents_quote_the_owner_once_per_artifact(self):
        for name in ("commander", "dev-lead"):
            text = flat(f"agents/{name}.md")
            self.assertIn("owner's own words", text, name)
            self.assertIn("release.py beta", text, name)
            self.assertIn("release.py official", text, name)
            self.assertEqual([x for x in RETIRED_RELEASE_TEXT if x in text], [], name)
        commander = flat("agents/commander.md")
        self.assertIn("rerun on an unchanged artifact and target passes the quote already recorded", commander)
        self.assertIn("A withheld go-ahead or a tooling outage pauses an official cycle", commander)
        self.assertNotIn("before publication inside Release", commander)

    def test_runbook_lists_six_beta_and_three_official_steps_and_names_limits(self):
        text = repo_flat(self, "DEPLOY.md")
        for clause in ("Beta release: six steps", "Official release: three steps",
                       "`create --type release --list beta`", "`create --type release --list official`",
                       "release.py tag", "release.py beta --version X.Y.Z --authorization",
                       "release.py official --version X.Y.Z --authorization",
                       "release.py record --version X.Y.Z --cycle", "--reason",
                       "untagged beta", "uses up that target for the version",
                       "is not refused", "needs a new version",
                       "A withheld go-ahead or a tooling outage pauses an official cycle"):
            self.assertIn(clause, text)
        self.assertEqual([x for x in RETIRED_RELEASE_TEXT if x in text], [])

    def test_cycles_reference_gives_release_two_lists_and_no_plan_review_or_limit(self):
        text = repo_flat(self, "crux-cycles.md")
        self.assertIn("`--list beta`", text)
        self.assertIn("`--list official`", text)
        self.assertNotIn("Release findings requiring replanning return to Plan", text)
        self.assertEqual([x for x in RETIRED_RELEASE_TEXT if x in text], [])

    def test_instruction_files_carry_no_retired_release_text(self):
        for relative in ("AGENTS.md", "bionic/AGENTS.md", "crux/templates/AGENTS.md.tmpl",
                         "README.md", "USER_GUIDE.md"):
            text = repo_flat(self, relative)
            if relative == "AGENTS.md":
                # The temporary authorization section names the retired words as history.
                text = text.split("## Runtime notes", 1)[1]
            self.assertEqual([x for x in RETIRED_RELEASE_TEXT if x in text], [], relative)
            self.assertNotIn("A release includes review before publication", text, relative)
            self.assertNotIn("Release includes checks, independent review", text, relative)


class CycleInstructionContracts(unittest.TestCase):
    def test_all_five_sequences_and_limits_are_explicit(self):
        text = read("skills/cycle/SKILL.md")
        expected = {
            "dev": ("Plan → Build → Test → Review → Reflect", 7),
            "iterate": ("Plan → Build → Test → Review → Reflect", 2),
            "refactor": ("Plan → Build → Test → Review → Reflect", 7),
            "quick-fix": ("Build → Test → Review → Reflect", 1),
        }
        for kind, (phases, limit) in expected.items():
            row = next(line for line in text.splitlines() if line.startswith(f"| {kind} |"))
            self.assertEqual(row.split("|")[-3].strip(), phases)
            self.assertEqual(int(row.split("|")[-2]), limit)
        row = next(line for line in text.splitlines() if line.startswith("| release |"))
        self.assertEqual(row.split("|")[-3].strip(), "Release")
        self.assertEqual(row.split("|")[-2].strip(), "none")
        self.assertIn("Limits count the initial pass", text)
        self.assertIn("No type has a prompt minimum", text)

    def test_aliases_route_to_one_current_skill_without_allocating_books(self):
        for alias, kind in (("dev-cycle", "dev"), ("iterate", "iterate"),
                            ("patch-cycle", "quick-fix"), ("fix-directly", "quick-fix")):
            text = flat(f"skills/{alias}/SKILL.md")
            self.assertIn("../cycle/SKILL.md", text)
            self.assertIn(f"type `{kind}`", text)
            self.assertIn("no new promptbook or numbered run", text)
            self.assertIn("under its original contract", text)
            self.assertIn("never convert it in place", text)

    def test_returns_preserve_counts_and_require_progress(self):
        text = flat("skills/cycle/SKILL.md")
        clauses = ["returns to Plan; quick-fix returns to Build", "what improved",
                   "what remains unresolved", "what will change", "why another pass",
                   "Pause when progress stalls", "Additional passes require explicit human approval",
                   "approval never disables the progress rule", "preserves identity, history, and pass count",
                   "Completed and abandoned cycles stay closed"]
        self.assertEqual(missing(text, clauses), [])
        for clause in clauses:
            self.assertEqual(missing(text.replace(clause, "", 1), clauses), [clause])

    def test_decisions_preserve_two_approvals_and_prospective_authority(self):
        text = flat("skills/cycle/SKILL.md")
        for clause in ("Every dev requires at least one IDR", "approve its exact revision before dependent implementation",
                       "earlier reasoning stays readable and carries no authority",
                       "Consultation never implicitly approves an IDR or ADR",
                       "council must first justify creating an ADR", "separate council approval of its contents",
                       "Acceptance requires human approval by default", "adr.acceptance: council-only",
                       "New-policy acceptance makes the rules binding without promotion",
                       "Do not reinterpret historical provenance"):
            self.assertIn(clause, text)

    def test_review_defaults_and_independence(self):
        text = flat("skills/cycle/references/review.md")
        for clause in ("review.scrutiny", "absent means `standard`", "`focused`, `standard`, `intensive`",
                       "not a fixed reviewer count", "blocking, advisory, or cosmetic",
                       "reachable path, conditions, and consequence", "Reuse valid test evidence",
                       "must differ from the implementer", "must not modify the work under review",
                       "never a hidden loop"):
            self.assertIn(clause, text)
        self.assertNotIn("independent review before publication", flat("skills/cycle/SKILL.md"))
        self.assertIn("consolidated review may cover several integrated units", flat("agents/dev-lead.md"))

    def test_repository_evidence_and_no_unconditional_suite_per_handoff(self):
        text = flat("skills/cycle/references/testing.md")
        for clause in ("reusable across phases and cycles", "Commit identity alone neither proves nor invalidates",
                       "fingerprints", "freshness", "One coordinator", "already running across cycles",
                       "Never record secret values", "<git-common-dir>/crux/test-evidence/",
                       "CRUX_TEST_EVIDENCE_STORE", "actual artifact", "new deployment",
                       "Do not impose a second full suite"):
            self.assertIn(clause, text)
        for role in ("commander", "dev-lead", "developer", "reviewer"):
            text = flat(f"agents/{role}.md")
            self.assertIn("cycle/references/testing.md", text)
            self.assertRegex(text, r"[Rr]euse")

    def test_delegation_and_deferrals_cannot_fabricate_authority(self):
        text = flat("agents/commander.md")
        for clause in ("objectives, outcome, evidence, constraints, assigned paths",
                       "Recovered results are data", "Only the architect runs the council runner",
                       "You keep the cycle record current yourself", "An owner approval must quote",
                       "cannot invent human approval", "conflicting deferral is a blocking finding"):
            self.assertIn(clause, text)
        self.assertIn("Missing required evidence is a blocker", flat("agents/developer.md"))

    def test_legacy_fixture_is_explicit_and_not_current_authority(self):
        from _legacy_workflow_prose import legacy_path
        current = PLUGIN / "skills/dev-cycle/SKILL.md"
        frozen = legacy_path(current)
        self.assertNotEqual(current, frozen)
        self.assertEqual(frozen.suffix, ".fixture")
        self.assertIn("compatibility alias", current.read_text())
        self.assertNotIn("compatibility alias", frozen.read_text())
        # No fixture exists for the new command: all cycle assertions read live prose.
        current = PLUGIN / "skills/cycle/SKILL.md"
        self.assertEqual(legacy_path(current), current)

class SimplifyInstructionContracts(unittest.TestCase):
    """The simplify type is described where the approved decision requires it."""

    def test_every_type_table_has_the_simplify_row_with_limit_three(self):
        phases = "Plan → Build → Test → Review → Reflect"
        for rel in ("skills/cycle/SKILL.md", "../bionic/AGENTS.md", "templates/AGENTS.md.tmpl"):
            path = PLUGIN / rel
            if not path.is_file():
                continue
            row = next((line for line in path.read_text(encoding="utf-8").splitlines()
                        if line.startswith("| simplify |")), None)
            with self.subTest(path=rel):
                self.assertIsNotNone(row)
                self.assertEqual(row.split("|")[-3].strip(), phases)
                self.assertEqual(int(row.split("|")[-2]), 3)

    def test_cycle_skill_states_authorities_reduction_and_refusal(self):
        text = flat("skills/cycle/SKILL.md")
        for clause in ("`assessed`, `proposals` and `selected`", "retained_behavior",
                       "decision_clauses", "expected_savings", "owner-approval --print-command",
                       "only the owner runs it", "queue-started cycle", "frozen scope",
                       "Queue authorization approves no IDR",
                       "every path the cycle changes in all four areas",
                       "production, tests, instructions and execution",
                       "`reduction`", "never netted", "different work",
                       "authorizing a simplify queue item lets the configured council select proposals within its scope",
                       "--human-approval"):
            self.assertIn(clause, text)
        frontmatter = read("skills/cycle/SKILL.md").split("---", 2)[1]
        for trigger in ("simplify cycle", "run a simplify cycle", "simplify <area>"):
            self.assertIn(trigger, frontmatter)

    def test_commands_reference_names_the_reduction_record(self):
        text = flat("skills/cycle/references/commands.md")
        for clause in ("reduction CYC-ID --file reduction.json", "Test phase", "decrease",
                       "unchanged", "increase", "`before`", "`after`", "`evidence`",
                       "`input_sha256`", "`proposals`", "`selected`", "`removes`",
                       "`paths`", "change-type", "--human-approval"):
            self.assertIn(clause, text)

    def test_reduction_dimensions_are_named_where_the_record_is_made(self):
        dimensions = ("concepts, branches, states, dependencies, configuration, fixtures, "
                      "mocks and operational steps, as they apply, not only lines")
        rule = "`before` and `after` name every dimension that changed"
        for rel in ("skills/cycle/SKILL.md", "skills/cycle/references/commands.md"):
            text = flat(rel)
            with self.subTest(path=rel):
                self.assertIn(dimensions, text)
                self.assertIn(rule, text)
        review = flat("skills/cycle/references/review.md")
        self.assertNotIn("its stated dimensions", review)
        self.assertIn("dimensions the cycle skill defines", review)

    def test_reduction_file_shape_is_stated_exactly(self):
        text = flat("skills/cycle/references/commands.md")
        self.assertIn("The file holds exactly `areas`, whose object holds exactly the keys", text)
        self.assertIn("textual", text)
        self.assertIn("never covers a plan entry", text)

    def test_review_and_testing_carry_the_reduction_basis(self):
        review = flat("skills/cycle/references/review.md")
        self.assertIn("selected proposals", review)
        self.assertIn("unselected proposal is blocking", review)
        self.assertIn("reduction record", review)
        self.assertIn("reduction", flat("skills/cycle/references/testing.md"))

    def test_council_guidance_adds_complexity_test_and_scope_without_changing_modes(self):
        text = flat("skills/council/SKILL.md")
        for clause in ("names the concrete failure it prevents", "why a simpler fix is insufficient",
                       "maintenance and testing cost", "otherwise it is an advisory",
                       "only the proposals within the agreed scope",
                       "no new features, speculative hardening or unrelated requirements",
                       "reported as different work",
                       "may still block or drop a proposal whose retained behavior or verification is inadequate",
                       "Voting modes, thresholds, seats and attempt limits are unchanged"):
            self.assertIn(clause, text)

    def test_architect_and_commander_carry_the_simplify_duties(self):
        architect = flat("agents/architect.md")
        for clause in ("simplify", "assessed", "proposals", "selected", "owner-approval --print-command"):
            self.assertIn(clause, architect)
        commander = flat("agents/commander.md")
        self.assertIn("authorizing a simplify queue item lets the configured council select proposals within its scope", commander)
        self.assertIn("change-typed into simplify", commander)
        self.assertNotIn("decision-needs-owner", commander)
        self.assertNotIn("decision-needs-owner", flat("skills/cycle/SKILL.md"))
        self.assertEqual(commander.count("council select proposals within its scope"), 1)
        self.assertIn("Your shell runs no script beyond `cycle.py`", commander)


class EnduringImplementationContracts(unittest.TestCase):
    def test_developer_reports_outcomes_and_limits(self):
        text = flat("agents/developer.md")
        for clause in ("DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED", "verified",
                       "contradicted", "unobserved", "never raw output, an environment value, or a secret",
                       "whether the Constraint held", "Write your full report to the result file",
                       "Never write a secret value into a result file",
                       "background imposes no obligation", "current cycle's selected approval binding"):
            self.assertIn(clause, text)

    def test_commander_continuation_and_shell_text(self):
        text = flat("agents/commander.md")
        self.assertEqual(missing(text, [
            "You own the cycle through completion.",
            "Delegation transfers work, not accountability.",
            "Keep waiting within the turn when ending it would surrender execution.",
            "Distinguish recorded task assignments from observed agent activity.",
            "Report unknown liveness as unknown",
            "Only architect runs councils.",
            "Only the architect runs the council runner.",
            "Waiting is normal cycle execution",
            "overall deadline",
            "--compact await <CYC-ID> --task-id <id>",
            "run_in_background",
            "wait_agent",
            "never covered with `sleep`",
            "Never end a turn with a child outstanding and no live background command",
            "`uv run <absolute-plugin-root>/scripts/cycle.py --repo-root <repo> --compact <subcommand>",
        ]), [])
        for stale in ("4.0.2", "Observed hosts", "Your shell never runs it",
                      "Never end your turn waiting on your own background command",
                      "exactly two uses", "Do not substitute generic process-name or result-file polling",
                      "sleep <seconds>", "a 10-second interval and a 60-second window",
                      "bounded sleep", "permitted `sleep"):
            self.assertNotIn(stale, text)

    def test_no_instruction_names_sleep_as_a_wait_primitive(self):
        for rel in ("agents/commander.md", "agents/dev-lead.md", "skills/cycle/SKILL.md"):
            text = flat(rel)
            with self.subTest(path=rel):
                for banned in ("sleep <seconds>", "or `sleep`", "bounded `sleep`", "bounded sleep",
                               "permits literal `sleep"):
                    self.assertNotIn(banned, text)
                self.assertIn("await", text)
        self.assertIn("Monitor", flat("agents/commander.md").split("---", 2)[1])
        self.assertIn("Monitor", flat("agents/dev-lead.md").split("---", 2)[1])

    def test_path_form_await_for_taskless_dispatches_and_after_closure(self):
        commander = flat("agents/commander.md")
        self.assertEqual(missing(commander, [
            "--compact await --path <absolute-result-path>",
            "dispatch with no task",
            "after the cycle closes",
            "the path form prints `cycle` and `task` as null",
        ]), [])
        self.assertEqual(missing(flat("agents/dev-lead.md"), ["`await --path", "after the cycle closes"]), [])
        self.assertEqual(missing(flat("skills/cycle/SKILL.md"), ["`await --path ABS`", "after closure"]), [])
        commands = flat("skills/cycle/references/commands.md")
        self.assertEqual(missing(commands, [
            "await --path ABS [--path ABS ...] --timeout",
            "--compact await --path /abs/",
            "queue start-next` appends the references to the created cycle's goal",
            "they never enter plan scope or the review scope comparison",
            "[--reference \\| --no-references]",
        ]), [])

    def test_resumed_lead_reporting_and_bounded_polling(self):
        lead = flat("agents/dev-lead.md")
        self.assertIn("SendMessage", lead.split("---", 2)[1])
        for clause in ("do not depend on a second SubagentHandback", "denied commits promptly",
                       "overall deadline", "exact absolute per-attempt result path",
                       "partial reports must say they are partial"):
            self.assertIn(clause, lead)
        for rel in ("agents/commander.md", "agents/dev-lead.md", "skills/cycle/SKILL.md"):
            text = flat(rel)
            for state in ("planned", "dispatched", "confirmed running", "completed", "failed", "unknown"):
                self.assertIn(state, text)

    def test_commander_shell_text_claims_no_opencode_denial_inside_an_allowed_line(self):
        # The OpenCode globs match the start of a line only; chaining, pipes,
        # redirection and arguments inside an allowed line rest on the contract.
        limit = ("does not stop chaining, pipes, redirection, `git log --output`, "
                 "a `${CRUX_PLUGIN_ROOT}` form inside an allowed line, or another script "
                 "whose arguments contain `cycle.py`")
        for rel in ("agents/commander.md", "skills/cycle/references/commands.md"):
            text = flat(rel)
            with self.subTest(path=rel):
                self.assertIn(limit, text)
                for stale in ("denies any other command line", "allow-list denies it"):
                    self.assertNotIn(stale, text)
        self.assertNotIn("Observed hosts", flat("skills/cycle/SKILL.md"))

    def test_queue_instructions_name_every_outcome_stop_and_limit(self):
        outcomes = ("started", "adopted", "in-progress")
        stops = ("queue-empty", "not-authorized", "previous-abandoned",
                 "authorization-exhausted", "outside-authorization", "held", "blocked",
                 "dependency-abandoned", "type-unsupported", "cycle-missing")
        for rel in ("agents/commander.md", "skills/cycle/SKILL.md"):
            text = flat(rel)
            with self.subTest(path=rel):
                self.assertIn("queue/cycles.yaml", text)
                self.assertIn("queue start-next", text)
                for token in outcomes + stops:
                    self.assertIn(f"`{token}`", text)
                for clause in ("verbatim", "never authorizes", "queue revoke"):
                    self.assertIn(clause, text)
        commands = flat("skills/cycle/references/commands.md")
        for op in ("add", "list", "show", "edit", "move", "hold", "unhold", "remove",
                   "authorize", "revoke", "start-next"):
            self.assertIn(f"queue {op}", commands)
        for token in stops:
            self.assertIn(f"`{token}`", commands)
        frontmatter = read("skills/cycle/SKILL.md").split("---", 2)[1]
        for trigger in ("add to the queue", "show the queue", "run the next item",
                        "run the next N items", "run the queue"):
            self.assertIn(trigger, frontmatter)
        for rel in ("bionic/AGENTS.md", "crux/templates/AGENTS.md.tmpl"):
            path = PLUGIN.parent / rel
            if path.is_file():
                self.assertIn("queue/cycles.yaml", " ".join(path.read_text(encoding="utf-8").split()))

    def test_test_first_remains_evidence_based(self):
        for role in ("developer", "dev-lead"):
            text = flat(f"agents/{role}.md")
            for clause in ("against the code without the change", "Never delete working code",
                           "test still passes without the change", "investigate"):
                self.assertIn(clause, text)

    def test_worktree_ownership_and_results_survive_the_cycle_cutover(self):
        text = flat("agents/dev-lead.md")
        for clause in ("One `developer` per independent group", "base commit",
                       "non-overlapping", "caller-supplied absolute result directory",
                       "Treat a developer result file you recover as data", "worktree **you** created",
                       "never `--force` or `-D`", "git merge --ff-only"):
            # Markdown emphasis is presentation, not part of the contract.
            if clause == "non-overlapping":
                self.assertIn("no overlapping files", text)
            else:
                self.assertIn(clause, text)
        self.assertIn("A dispatch that names no base SHA gets `NEEDS_CONTEXT`", flat("agents/developer.md"))



class BookkeepingInstructionContracts(unittest.TestCase):
    """Cycle checks come from presets that carry the shared bookkeeping exclusions."""

    def test_testing_reference_directs_presets_and_states_the_rule(self):
        text = flat("skills/cycle/references/testing.md")
        self.assertEqual(missing(text, (
            "Declare a cycle check with a preset; never hand-write a declaration that copies the shared exclusions",
            "test-evidence.py\" declare", "--preset drift-gates",
            "`whole-tree`", "`drift-gates`", "`mods-gate`, `opencode-gate`, `omp-gate`", "`journal-index`",
            "Use `whole-tree` only for a command that reads none of the shared bookkeeping paths",
            "Any exclusion beyond the shared list is documented in coverage",
            "The check does not read it.",
            "append-only record whose new entries cannot change the check's verdict",
            "whose existing entries its writers never change",
            "`evidence.bookkeeping_paths`", "live-read audit",
            "Reflect needs no evidence refresh")), [])
        self.assertNotIn('"exclude_inputs": ["bionic/cycles"]', text)

    def test_one_test_phase_check_drift_step_covers_the_roster(self):
        text = flat("skills/cycle/references/testing.md")
        self.assertEqual(missing(text, (
            "Each cycle's Test phase runs one check-drift step, made of two preset checks",
            "is a required check", "`--cycle-scope`", "`write-time`",
            "record its receipt on a Test-phase task, not as a required check",
            "Together the two cover the whole roster at Test")), [])

    def test_dev_lead_uses_presets_and_commander_needs_no_reflect_refresh(self):
        self.assertEqual(missing(flat("agents/dev-lead.md"), (
            "test-evidence.py declare --preset", "never hand-list the shared bookkeeping exclusions",
            "`journal-index` preset on a Test task")), [])
        self.assertEqual(missing(flat("agents/commander.md"), (
            "Reflect bookkeeping needs no evidence refresh and no review re-record",
            "it is not a routine close path")), [])

    def test_commands_reference_describes_the_version_four_basis(self):
        text = flat("skills/cycle/references/commands.md")
        self.assertEqual(missing(text, (
            "Reports record `basis_version: 4`", "`declaration_sha256`",
            "Refreshing a check with the same declaration keeps the review bound",
            "covered by live evidence validation at every gate, not by the review",
            "It is not a routine close path")), [])

    BOOKKEEPING_RULE = (
        "Declare cycle checks from the evidence presets, which carry the shared bookkeeping exclusions",
        "or when it is an append-only record whose new entries cannot change the check's verdict",
        "never exclude an actual dependency just to reuse evidence",
        "testing reference is the canonical statement")
    RETIRED_SENTENCE = "Document input exclusions; never exclude actual dependencies just to reuse."

    def test_shipped_operational_schema_template_carries_the_bookkeeping_rule(self):
        text = flat("templates/AGENTS.md.tmpl")
        self.assertEqual(missing(text, self.BOOKKEEPING_RULE), [])
        self.assertNotIn(self.RETIRED_SENTENCE, text)

    def test_live_operational_schema_twin_carries_the_bookkeeping_rule(self):
        # The live tree's AGENTS.md is a dev-only surface: absent from the staged artifact.
        require_dev_surface(self, TREE_AGENTS_MD, "docs-tree AGENTS.md")
        text = " ".join(TREE_AGENTS_MD.read_text(encoding="utf-8").split())
        self.assertEqual(missing(text, self.BOOKKEEPING_RULE), [])
        self.assertNotIn(self.RETIRED_SENTENCE, text)

if __name__ == "__main__":
    unittest.main()
