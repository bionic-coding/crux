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


class RecoveryInterfaceInstructionContracts(unittest.TestCase):
    """Active guidance must expose delivered authority and recovery boundaries."""

    def test_commander_reads_bound_context_without_widening_its_shell(self):
        text = flat("agents/commander.md")
        for clause in ("`context-read`", "`dispatch-invocation`", "`next_offset`",
                       "`--sha256`", "unique current", "owner-decision",
                       "advisory", "contradicted", "`task --task-id`"):
            self.assertIn(clause, text)
        self.assertNotIn("Read result paths with Read, not shell scripts", text)
        self.assertNotIn("as its first action, apply it", text)

    def test_reviewer_reader_is_inside_its_exhaustive_shell_boundary(self):
        text = flat("agents/reviewer.md")
        boundary = text.split("## Shell and capability boundaries", 1)[1]
        self.assertIn("`cycle.py context-read`", boundary)
        self.assertIn("read-only", boundary)
        self.assertIn("Request other execution", boundary)

    def test_dev_lead_handoff_uses_recorded_base_instead_of_current_head(self):
        text = flat("agents/dev-lead.md")
        handoff = text.split("**Name the", 1)[1].split("- **Dispatch through", 1)[0]
        self.assertIn("immutable `task_base`", handoff)
        self.assertIn("`execution-check`", handoff)
        self.assertNotIn("Every developer dispatch carries your `git rev-parse HEAD`", handoff)
        self.assertNotIn("fast-forwards to your SHA before any edit, or reports `BLOCKED`", handoff)

    def test_opencode_guide_scopes_gateway_keys_and_council_execution(self):
        text = repo_flat(self, "OPENCODE_GUIDE.md")
        self.assertIn("Gateway council calls and LLM-router calls require", text)
        self.assertIn("Native Lite needs no OpenRouter key", text)
        self.assertIn("### Historical promptbook council recovery", text)
        self.assertIn("`architect` runs cycle councils", text)
        self.assertNotIn("required for any council", text)
        self.assertNotIn("may run the council runner", text)

    def test_workers_keep_review_base_and_use_exact_source_checkpoints(self):
        for role in ("developer", "dev-lead"):
            text = flat(f"agents/{role}.md")
            for clause in ("`execution-check`", "immutable", "`edited_paths`",
                           "stage", "bookkeeping", "original review base"):
                self.assertIn(clause, text, role)
        self.assertNotIn("Otherwise, report `BLOCKED` with both SHAs", flat("agents/developer.md"))

    def test_frozen_context_and_actual_codex_wait_are_explicit(self):
        text = flat("skills/cycle/SKILL.md")
        for clause in ("`dispatch-invocation`", "canonical origin", "every selected body",
                       "`task_name`", "`timeout_ms`", "no `ids`", "wake-up",
                       "1 MiB", "16 KiB", "unavailable-original-context"):
            self.assertIn(clause, text)
        self.assertNotIn("No host is recorded as observed", text)

    def test_owner_answer_and_council_checkpoint_boundaries(self):
        text = flat("skills/cycle/references/commands.md")
        for clause in ("owner-decision present", "`presentation`", "`supersedes`",
                       "`source`", "`owner_date`", "unique current unsuperseded",
                       "already_applied", "`lifecycle_changed:false`",
                       "request checkpoint", "outcome checkpoint", "unknown",
                       "`execution-check`", "`dispatch-invocation`"):
            self.assertIn(clause, text)
        self.assertNotIn("so the owner runs it", text)

    def test_test_evidence_separates_actual_command_and_reuse(self):
        text = flat("skills/cycle/references/testing.md")
        for clause in ("`executed_command`", "requested argv", "canonical identity",
                       "workers", "records", "timings", "creates no new output"):
            self.assertIn(clause, text)

    def test_tree_and_template_explain_prospective_conversation_handling(self):
        for relative in ("bionic/AGENTS.md", "crux/templates/AGENTS.md.tmpl"):
            text = repo_flat(self, relative)
            for clause in ("owner-decision", "`context-read`", "`execution-check`",
                           "`dispatch-invocation`", "historical", "advisory"):
                self.assertIn(clause, text, relative)


class ReleaseListInstructionContracts(unittest.TestCase):
    """A release cycle runs one of two fixed lists; the instructions delete what they retire."""

    def test_cycle_skill_describes_the_two_lists_and_retires_the_old_release(self):
        text = flat("skills/cycle/SKILL.md")
        for clause in ("`--list beta` or `--list official`",
                       "The release verify step (`release.py verify`) is the only step that runs the registered suites",
                       "A failed release step stops the release",
                       "sets that step's task back to pending",
                       "reopens every later task",
                       "A release queue item starts a beta-list cycle",
                       "An item added with `queue add --release-list official` starts an official-list cycle",
                       "An official cycle not started from the queue is created directly"):
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
        self.assertIn("The release verify step (`release.py verify`) is the only release step that runs the registered suites", text)
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


class RoleOutcomeContracts(unittest.TestCase):
    """Role files state outcomes, judgment and authority; the typed operations hold the procedure."""

    REMOVED = (
        "--state running --role", "run `handoff` first", "Do not bypass dev-lead",
        "retained under", "Retain substantive delivery reports",
        "Have delivery reports retained", "coordinator-created OS-temp",
        "OS-temp result directory", "cycle.py assignment", "--result-path",
        "start the matching `await` line", "stay inside `wait_agent`",
        "`sleep` is no wait primitive", "Wait on the host's native mechanism",
        "- Claude Code: record the task active", "- OpenCode: dispatch a child",
        "- Codex: stay inside", "- Every host: each window",
    )

    def test_commander_and_dev_lead_drop_the_manual_sequences(self):
        for name in ("commander", "dev-lead"):
            text = flat(f"agents/{name}.md")
            self.assertEqual([x for x in self.REMOVED if x in text], [], name)

    def test_operations_roles_name_inspect_as_their_entry_point(self):
        for name in ("commander", "dev-lead", "architect", "historian"):
            text = flat(f"agents/{name}.md")
            self.assertIn("`inspect`, then the action it returns", text, name)

    def test_commander_holds_the_developer_grant_and_the_typed_operations_rules(self):
        raw = read("agents/commander.md")
        tools = raw.split("tools:", 1)[1].split("\n", 1)[0]
        self.assertIn("Agent(developer)", tools)
        self.assertIn("Agent(reviewer)", tools)
        text = flat("agents/commander.md")
        for clause in (
            "single-quoted `--json`", "\\u0027", "\\n",
            "`prepare-dispatch`", "`attach-execution`", "`deliver`", "`mark-lost`",
            "with your own dispatch tool",
            "Never re-dispatch a running attempt",
            "the execution terminated or never started",
            "Wait windows are uncapped", "an ended window pauses nothing",
            "dispatch a developer and an independent reviewer",
            "Dispatch a dev-lead for parallel streams, integration across units",
            "one at a time",
            "contradicted premise",
        ):
            self.assertIn(clause, text)

    def test_commander_keeps_its_authority_anchors(self):
        text = flat("agents/commander.md")
        for clause in (
            "No host enforces these uses in full",
            "You edit no files and run no tests",
            "Carry objectives, outcome, evidence, constraints",
            "The reviewer never authored the work under review",
            "Publish only on the owner's own words",
            "`queue-empty`, `not-authorized`, `previous-abandoned`",
            "return the invocation and its attach request to your caller",
        ):
            self.assertIn(clause, text)
        raw = read("agents/commander.md")
        self.assertIn('skills: [cycle]', raw)
        self.assertIn('skill_lanes: "cycle=delegates:historian"', raw)
        self.assertIn('Only architect runs councils', text)
        self.assertIn('Delegate judgment-bearing documents to the historian', text)

    def test_dev_lead_keeps_the_integration_procedure_and_uses_the_operations(self):
        text = flat("agents/dev-lead.md")
        for clause in (
            "git merge-base --is-ancestor HEAD <unit commit>",
            "git diff --name-only HEAD...<branch>", "git merge --ff-only <branch>",
            "sealed commit", "original base", "git merge-tree", "custom merge drivers",
            "`prepare-dispatch`", "`attach-execution`",
            "`deliver`", "`mark-lost`", "own task", "Cycle-Task: <task-id>",
            "TDD (Iron Law)",
            "independent reviewer",
        ):
            self.assertIn(clause, text)

    def test_trailers_share_one_final_paragraph(self):
        for path in ("agents/developer.md", "agents/dev-lead.md"):
            text = flat(path)
            for clause in ("one final paragraph", "no blank line", "Co-Authored-By"):
                with self.subTest(path=path, clause=clause):
                    self.assertIn(clause, text)

    def test_developer_without_a_dev_lead_and_no_cycle_operation(self):
        text = flat("agents/developer.md")
        for clause in (
            "call no cycle operation", "Developer without a dev-lead",
            "trailer-tagged commits", "without resetting",
            "test coordinator", "receipt ids", "no changed-path check",
            "Result-End",
        ):
            self.assertIn(clause, text)
        self.assertNotIn("return the required dev-lead handoff", text)

    def test_historian_does_judgment_work_only(self):
        text = flat("agents/historian.md")
        self.assertIn("reflections with real lessons", text)
        self.assertIn("never clerical record work", text)
        self.assertNotIn("**Cycle bookkeeping:**", text)
        self.assertNotIn("turn it into the tree record", text)


class CycleInstructionContracts(unittest.TestCase):
    def test_all_five_sequences_and_limits_are_explicit(self):
        text = read("skills/cycle/SKILL.md")
        expected = {
            "dev": ("Plan → Build → Verify → Review → Reflect", 7),
            "iterate": ("Plan → Build → Verify → Review → Reflect", 2),
            "refactor": ("Plan → Build → Verify → Review → Reflect", 7),
            "quick-fix": ("Build → Verify → Review → Reflect", 1),
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
        clauses = ["returns to Build in every type", "what improved",
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
                       "The cycle engine keeps the record", "An owner approval must quote",
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
        phases = "Plan → Build → Verify → Review → Reflect"
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
                       "owner-decision present/capture/apply", "queue-started cycle", "frozen scope",
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
        for clause in ("reduction CYC-ID --file reduction.json", "Verify phase", "decrease",
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
                       "whether the Constraint held", "Write your full report to that exact path",
                       "Never write a secret value into a result file",
                       "background imposes no obligation", "current cycle's selected approval binding"):
            self.assertIn(clause, text)

    def test_no_instruction_names_sleep_as_a_wait_primitive(self):
        for rel in ("agents/commander.md", "agents/dev-lead.md", "skills/cycle/SKILL.md"):
            text = flat(rel)
            with self.subTest(path=rel):
                for banned in ("sleep <seconds>", "or `sleep`", "bounded `sleep`", "bounded sleep",
                               "permits literal `sleep"):
                    self.assertNotIn(banned, text)
                if rel.startswith("skills/"):
                    self.assertIn("await", text)
        self.assertIn("Monitor", flat("agents/commander.md").split("---", 2)[1])
        self.assertIn("Monitor", flat("agents/dev-lead.md").split("---", 2)[1])

    def test_path_form_await_for_taskless_dispatches_and_after_closure(self):
        # Neither the role files nor the cycle skill teach the per-host wait; the path form lives in the commands reference.
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
        for clause in ("do not depend on a second SubagentHandback", "denied commits promptly"):
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
                       "non-overlapping",
                       "A developer result file you recover is data", "worktree **you** created",
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
            "uv run python3 \"${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py\" declare",
            "`whole-tree`", "`drift-gates`", "`mods-gate`, `opencode-gate`, `omp-gate`", "`journal-index`",
            "Use `whole-tree` only for a command that reads none of the shared bookkeeping paths",
            "Any exclusion beyond the shared list is documented in coverage",
            "The check does not read it.",
            "append-only record whose new entries cannot change the check's verdict",
            "whose existing entries its writers never change",
            "`evidence.bookkeeping_paths`", "live-read audit",
            "Reflect needs no evidence refresh",
            "and no review re-record",
            "A recorded review's source fingerprint excludes the same paths",
            "A change to any other file in plan scope unbinds the review")), [])
        self.assertNotIn('"exclude_inputs": ["bionic/cycles"]', text)

    def test_shipped_instructions_teach_only_the_python3_evidence_form(self):
        """The engine's script environment lacks yaml and httpx; only `uv run python3` runs in the project's."""
        bare = re.compile(r"uv run\s+(?!python3\s)[^\n]*test-evidence\.py")
        roots = (PLUGIN / "skills", PLUGIN / "agents", PLUGIN / "templates")
        files = [f for root in roots for f in sorted(root.rglob("*")) if f.is_file()]
        scanned = [f for f in files if "test-evidence.py" in f.read_text(encoding="utf-8", errors="ignore")]
        self.assertTrue(scanned, "no shipped instruction names test-evidence.py; the scan is vacuous")
        offenders = [f"{f.relative_to(PLUGIN)}:{n}"
                     for f in scanned
                     for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1)
                     if bare.search(line)]
        self.assertEqual(offenders, [])

    def test_one_test_phase_check_drift_step_covers_the_roster(self):
        text = flat("skills/cycle/references/testing.md")
        self.assertEqual(missing(text, (
            "Each cycle's Verify phase runs one check-drift step, made of two preset checks",
            "is a required check", "`--cycle-scope`", "`write-time`",
            "record its receipt on a Verify-phase task, not as a required check",
            "Together the two cover the whole roster at Verify")), [])

    def test_dev_lead_uses_presets_and_commander_needs_no_reflect_refresh(self):
        self.assertEqual(missing(flat("agents/dev-lead.md"), (
            "test-evidence.py declare --preset", "never hand-list the shared bookkeeping exclusions",
            "`journal-index` preset on a Verify task")), [])
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

class ParallelStreamContracts(unittest.TestCase):
    """A commander may run several dev-leads at once, one per independent stream."""

    def test_commander_and_dev_lead_describe_parallel_streams(self):
        commander = flat("agents/commander.md")
        self.assertEqual(missing(commander, (
            "Run several dev-leads at once",
            "one dev-lead per independent stream with disjoint owned paths recorded in the plan",
            "Each dev-lead integrates its own units",
            "You stay accountable for the cycle")), [])
        lead = flat("agents/dev-lead.md")
        self.assertEqual(missing(lead, (
            "You may be one of several dev-leads",
            "Edit only your stream's owned paths",
            "integrate your own units into the shared branch one at a time",
            "never stash, reset, check out or reformat another stream's paths")), [])

    # Each role and the cycle skill carry the workflow rules of CYC-0076 against
    # the `assignment` and `checks --phase build` interface the approved IDR fixes.
    WORKFLOW = {
        "skills/cycle/SKILL.md": (
            "first Build task delivers one working end-to-end path",
            "description starts `Hand-over:`",
            "Elapsed time never makes an attempt lost",
            "Never message an agent whose attempt is still running",
            "every test that imports, invokes, reads, globs or enumerates a changed path",
            "`checks --phase build`",
            "the queue writer owns active/history commits",
            "`commit-record`",
            "Reports cite rather than restate"),
        "agents/commander.md": (
            "`Hand-over:`", "relay it to the owning dev-lead",
            "Never re-dispatch a running attempt", "`mark-lost`",
            "vertical slice", "`checks --phase build`"),
        "agents/dev-lead.md": (
            "description starts `Hand-over:`", "`prepare-dispatch`",
            "never re-dispatch a running attempt",
            "every test that imports, invokes, reads, globs or enumerates a changed path",
            "`checks --phase build`", "one coherent change"),
        "skills/cycle/references/review.md": (
            "Check that the Build checks include every test that imports, invokes, reads, globs or enumerates a changed path",),
        "agents/developer.md": (
            "imports, invokes, reads, globs or enumerates a path you changed",
            "one coherent change"),
    }
    SUPERSEDED = {
        "agents/dev-lead.md": ("Include existing tests that import, invoke, read, or enumerate changed inputs.",
                               "import, invoke, read, or enumerate its inputs"),
        "agents/commander.md": ("Dispatch independent implementation units with non-overlapping ownership.",),
        "skills/cycle/SKILL.md": ("Commit the cycle record and queue only at a phase close",),
    }

    RETIRED_SCHEMA_RULES = (
        "records an `assignment` running before each dispatch and resume",
        "`lost` only with host evidence")

    def test_workflow_rules_reach_every_role_and_the_skill(self):
        for rel, clauses in self.WORKFLOW.items():
            with self.subTest(path=rel):
                self.assertEqual(missing(flat(rel), clauses), [])
        for rel, stale in self.SUPERSEDED.items():
            with self.subTest(path=rel):
                self.assertEqual([s for s in stale if s in flat(rel)], [])


    SCHEMA_RULES = (
        "Commander may run several dev-leads at once, one per independent stream with disjoint owned paths recorded in the plan",
        "description starts `Hand-over:`",
        "first Build task delivers one working end-to-end path",
        "`prepare-dispatch` reserves an attempt",
        "`mark-lost` needs affirmative evidence",
        "every test that imports, invokes, reads, globs or enumerates a changed path",
        "Build ends only when they pass")

    def test_shipped_operational_schema_template_carries_the_stream_rules(self):
        text = flat("templates/AGENTS.md.tmpl")
        self.assertEqual(missing(text, self.SCHEMA_RULES), [])
        self.assertEqual([r for r in self.RETIRED_SCHEMA_RULES if r in text], [])

    def test_live_operational_schema_twin_carries_the_stream_rules(self):
        require_dev_surface(self, TREE_AGENTS_MD, "docs-tree AGENTS.md")
        text = " ".join(TREE_AGENTS_MD.read_text(encoding="utf-8").split())
        self.assertEqual(missing(text, self.SCHEMA_RULES), [])
        self.assertEqual([r for r in self.RETIRED_SCHEMA_RULES if r in text], [])

class FixStepInstructionContracts(unittest.TestCase):
    """Test and Review may answer one small in-scope finding with a fix task."""

    BOUNDS = ("stays in plan scope", "changes no approved decision, schema, interface or dependency",
              "states its cause", "a few files, about 50 changed lines")
    RETURN = "An ineligible finding, a failed fix, or a blocking fix-diff review returns to Build"
    SURFACES = {
        "skills/cycle/SKILL.md": BOUNDS + (
            "One fix per phase per pass", "`fix: {finding, eligibility}`",
            "the commander records why it qualifies",
            "A developer writes the fix; the commander's shell stays the cycle writer and read-only git",
            "A blocking Verify or Review finding returns to Build in every type",
            RETURN, "checks only the fix diff against the finding",
            "the normal Review covers it"),
        "agents/commander.md": BOUNDS + (
            "one fix per phase per pass", "records why it qualifies", "through the dev-lead that runs the stream", RETURN),
        "agents/dev-lead.md": (
            "fix task", "a developer writes it", "finding id",
            "an ineligible finding returns to the conductor"),
        "agents/reviewer.md": (
            "fix-diff review", "only the fix diff against the finding",
            "differ from the fix assignee", "`fix_task`"),
        "skills/cycle/references/review.md": (
            "fix-diff review", "only the fix diff against the finding",
            "blocking fix-diff review returns to Build"),
        "skills/cycle/references/commands.md": (
            "`fix: {finding, eligibility}`", "--fix-before", "--fix-after", "`fix_task`",
            "bookkeeping for the review basis", "one fix per phase per pass",
            "`handoff` lists fixes"),
    }
    SCHEMA = BOUNDS + (
        "one fix per phase per pass", "commander records why it qualifies", RETURN,
        "no pass is consumed")

    def test_each_surface_states_the_fix_step(self):
        for rel, clauses in self.SURFACES.items():
            with self.subTest(path=rel):
                self.assertEqual(missing(flat(rel), clauses), [])

    def test_operational_schema_and_template_state_the_fix_step(self):
        self.assertEqual(missing(flat("templates/AGENTS.md.tmpl"), self.SCHEMA), [])
        require_dev_surface(self, TREE_AGENTS_MD, "docs-tree AGENTS.md")
        text = " ".join(TREE_AGENTS_MD.read_text(encoding="utf-8").split())
        self.assertEqual(missing(text, self.SCHEMA), [])

    def test_root_instructions_name_the_fix_exception(self):
        text = repo_flat(self, "AGENTS.md")
        self.assertIn("a small in-scope finding may be answered by a fix task", text)

class TypedOperationInstructionContracts(unittest.TestCase):
    """The cycle skill states outcomes and authority; the typed operations own the procedure."""

    SKILL = "skills/cycle/SKILL.md"
    COMMANDS = "skills/cycle/references/commands.md"
    REMOVED_FROM_SKILL = (
        "## Temporary result files", "tempfile.mkdtemp", "crux-results-",
        "have dev-lead or historian retain substantive delivery reports",
        "## Record at execution boundaries", "--state running --role",
        "Run `handoff` first", "`--seen --agent`", "Record `finished` only after",
        "Record `lost` only with a note citing host evidence",
        "## Background work", "`await --path ABS`", "run_in_background",
        "re-issued per window", "Do not call developer directly from the main session",
    )
    REMOVED_FROM_COMMANDS = (
        "Before dispatching the unit, substitute the actual coordinator-supplied path",
        "Record it before every dispatch and before resuming an agent's work",
        "has already returned a handle",
    )
    OPERATIONS = ("inspect", "prepare-dispatch", "attach-execution", "deliver", "mark-lost",
                  "advance", "finish", "owner-exception", "upgrade")

    def test_removed_manual_sequences_are_absent(self):
        skill = flat(self.SKILL)
        self.assertEqual([x for x in self.REMOVED_FROM_SKILL if x in skill], [])
        commands = flat(self.COMMANDS)
        self.assertEqual([x for x in self.REMOVED_FROM_COMMANDS if x in commands], [])

    def test_skill_names_inspect_as_the_entry_point_and_every_operation(self):
        skill = flat(self.SKILL)
        self.assertEqual(missing(skill, (
            "Run `inspect`, then the action it returns", "cycle.py\" op")), [])
        for op in self.OPERATIONS:
            self.assertIn(f"`{op}`", skill)
        self.assertEqual(missing(skill, (
            "performs it with its own dispatch tool",
            "never through the cycle writer",
            "handle-less mode skips `attach-execution`")), [])

    def test_skill_states_the_dispatch_rule_and_the_direct_developer_duties(self):
        skill = flat(self.SKILL)
        self.assertEqual(missing(skill, (
            "dispatches a developer and an independent reviewer",
            "parallel streams, integration across units, or complexity the plan names",
            "Direct developer dispatches on the main checkout run one at a time",
            "A developer dispatched without a dev-lead",
            "acts as the cycle's test coordinator without calling any other cycle operation beyond execution-check",
            "A refusal that names a missing grant or role is a contradicted premise",
            "The dev-lead's changed-path check has no equivalent")), [])

    def test_skill_states_waiting_loss_and_limits_as_judgment_and_authority(self):
        skill = flat(self.SKILL)
        self.assertEqual(missing(skill, (
            "`Result-End: <assignment>/<attempt>`", "`cycle.py await --marker`",
            "affirmative host evidence", "a dispatch-call refusal the adapter lists",
            "the owner's confirmation, quoted, that the execution terminated or never started",
            "Elapsed time never makes an attempt lost",
            "three attempts in one pass",
            "windows are uncapped", "is no escalation stop",
            "returns the wait descriptor again and the caller starts the next window",
            "otherwise with the owner's statement; it counts as one of the three attempts",
            "A cycle paused under the removed window limit keeps its recorded reason",
            "a stated limit for the owner to judge",
            "hands the invocation back to its caller",
            "Report planned, dispatched, confirmed running, completed, failed, and unknown work separately",
            )), [])

    def test_skill_states_the_commander_json_form_completion_and_old_records(self):
        skill = flat(self.SKILL)
        self.assertEqual(missing(skill, (
            "\\u0027", "\\n", "--json '{\"op\":\"inspect\"}'",
            "field, expected, observed, problem and recovery",
            "lessons and remaining need judgment", "routine outcome text is generated",
            "exact words and conversation reference",
            "references are optional and never invented",
            "`needs-upgrade`", "`assignments-running`",
            "cannot read version-3 records", "`upgrade` keeps the version-2 bytes")), [])

    def test_commands_reference_documents_op_and_marks_low_level_commands(self):
        commands = flat(self.COMMANDS)
        self.assertEqual(missing(commands, (
            "cycle.py --repo-root . op CYC-0001 --json", "--json -", "--file PATH",
            "`expect_revision`", "`Result-End: <assignment>/<attempt>`",
            "Low-level commands", "diagnosis", "version-1 and version-2 records",
            "`operation-unavailable`")), [])
        for op in self.OPERATIONS:
            self.assertIn(f"`{op}`", commands)

    def test_testing_and_review_references_state_typed_advance_reuse(self):
        testing = flat("skills/cycle/references/testing.md")
        self.assertEqual(missing(testing, (
            "Typed `advance` attaches a matching reusable receipt",
            "never executes a check and never attaches a failure")), [])
        self.assertIn("independent", flat("skills/cycle/references/review.md"))

    def test_kept_anchors_survive(self):
        skill = flat(self.SKILL)
        self.assertEqual(missing(skill, (
            "Beta list:", "Official list:", "### Simplify cycles", "## Return paths and stops",
            "### Fix step", "## Queue", "Publication, external sends, and other outward actions",
            "Pass objectives, outcome, evidence, constraints",
            "A developer never reviews its own change",
            "Old promptbooks, snapshots, templates")), [])


class ReviewFixInstructionContracts(unittest.TestCase):
    """Review-found gaps in the typed-operation prose stay closed."""

    def test_attach_execution_carries_the_host_handle_and_a_handleless_mode_skips_it(self):
        for path in ("agents/commander.md", "agents/dev-lead.md"):
            text = flat(path)
            with self.subTest(path=path):
                self.assertNotIn("or with none", text)
                self.assertNotIn("none for a handle-less", text)
                self.assertIn("skips `attach-execution`", text)

    def test_review_is_recorded_through_the_review_command_json_form(self):
        review = flat("skills/cycle/references/review.md")
        self.assertIn("`review --json`", review)
        self.assertNotIn("records the review through `advance`", review)
        for path in ("agents/commander.md", "skills/cycle/SKILL.md"):
            with self.subTest(path=path):
                self.assertIn("through that command's `--json` form", flat(path))
        self.assertIn("Every command that takes `--file` also accepts `--json`",
                      flat("skills/cycle/references/commands.md"))

    def test_reflect_closes_through_finish_and_owner_exception(self):
        skill = flat("skills/cycle/SKILL.md")
        self.assertIn("`finish` records their full SHAs", skill)
        self.assertNotIn("using `completion`", skill)
        self.assertIn("is `owner-exception`, quoting the owner", skill)
        self.assertIn("`owner-exception`", flat("agents/commander.md"))

    def test_wording_fixes_stay(self):
        skill = flat("skills/cycle/SKILL.md")
        self.assertIn("has no version-2 form", skill)
        self.assertIn("across assignment ids", skill)
        self.assertNotIn("per task and role in one pass", skill)
        for path in ("agents/commander.md", "agents/dev-lead.md"):
            with self.subTest(path=path):
                self.assertIn("path form of `await`", flat(path))
        self.assertIn("return the invocation and its `attach-execution` request",
                      flat("agents/dev-lead.md"))
        self.assertIn("`--stage integrated`", flat("agents/dev-lead.md"))
        self.assertNotIn("until the Test phase observes", flat("agents/commander.md"))



class WindowPauseRemovalContracts(unittest.TestCase):
    """The window-exhaustion pause is gone from every site; the other pause triggers stay."""

    PAUSE_TEXT = ("three wait windows", "three 30-minute", "90 minutes", "90-minute",
                  "three new windows", "window exhaustion", "returns the pause action",
                  "wait windows (about")
    PLUGIN_SITES = ("agents/commander.md", "skills/cycle/SKILL.md", "skills/cycle/references/commands.md",
                    "templates/AGENTS.md.tmpl")
    REPO_SITES = ("AGENTS.md", "bionic/AGENTS.md", "USER_GUIDE.md", "OPENCODE_GUIDE.md", "OMP_GUIDE.md",
                  "opencode/agents/commander.md")

    def test_the_pause_text_is_absent_from_every_site(self):
        for relative in self.PLUGIN_SITES:
            with self.subTest(site=relative):
                self.assertEqual([x for x in self.PAUSE_TEXT if x in flat(relative)], [])
        for relative in self.REPO_SITES:
            with self.subTest(site=relative):
                self.assertEqual([x for x in self.PAUSE_TEXT if x in repo_flat(self, relative)], [])

    def test_the_other_pause_triggers_survive(self):
        triggers = ("Pause when progress stalls", "the limit is exhausted", "scope changes materially",
                    "a decision needs owner input", "an explicit pause applies", "contradicts the premise")
        self.assertEqual(missing(flat("skills/cycle/SKILL.md"), triggers), [])
        for twin in ("bionic/AGENTS.md", "crux/templates/AGENTS.md.tmpl"):
            text = repo_flat(self, twin)
            with self.subTest(site=twin):
                self.assertEqual(missing(text, (
                    "Pause when progress stalls or the limit is exhausted",
                    "is a contradicted premise and pauses the cycle",
                    "refuses `attempt-limit`",
                    "No liveness, loss, pause or escalation is inferred from elapsed time")), [])
        root = repo_flat(self, "AGENTS.md")
        autonomy = root[root.index("### Cycle execution autonomy"):root.index("## Historical authority preservation")]
        self.assertEqual(missing(autonomy, (
            "Pause when progress stalls", "the limit is exhausted", "scope changes materially",
            "an owner decision is needed", "a premise is contradicted", "an explicit pause applies",
            "Elapsed time pauses nothing")), [])
        self.assertIn("## Temporary authorization: cycle workflow replacement", root)

    def test_exhausted_attempts_offer_only_an_available_return(self):
        rule = ("A counted `return` is offered only in Verify/Test or Review with a remaining "
                "pass, outside fixed release lists; otherwise stop or pause.")
        for relative in ("skills/cycle/SKILL.md", "templates/AGENTS.md.tmpl", "../bionic/AGENTS.md"):
            with self.subTest(site=relative):
                text = repo_flat(self, "bionic/AGENTS.md") if relative == "../bionic/AGENTS.md" else flat(relative)
                self.assertTrue(rule in text, f"{relative}: missing conditional return rule")
                self.assertFalse("returns `return` and `pause`" in text,
                                 f"{relative}: promises an unconditional return")


def section(relative, heading):
    """The text of one `## ` section, heading included, up to the next `## ` heading."""
    text = read(relative)
    start = text.index(heading + "\n")
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end < 0 else text[start:end + 1]


class CommandShapeContracts(unittest.TestCase):
    """Developers and dev-leads carry one block of shell shapes the host guard accepts."""

    HEADING = "## Shell command shapes"
    SHAPES = ("One command per call", "`&&`", "`cd`", "`git -C DIR`", "No heredoc",
              "`$VAR`", "Write or Edit tool", "Quote every glob argument", "--include='*.py'",
              "`sed -i ''", "`uv run python3 -m unittest discover -s DIR -p FILE`", "`-k NAME`",
              "`--json '@PATH'`", "`related-tests.py PATH...`", "--failed-from RECORDS",
              "zsh", "refuses a call it cannot verify")

    def test_developer_and_dev_lead_carry_the_same_block(self):
        developer = section("agents/developer.md", self.HEADING)
        self.assertEqual(developer, section("agents/dev-lead.md", self.HEADING))
        self.assertEqual(missing(" ".join(developer.split()), self.SHAPES), [])

    def test_plan_guidance_gives_a_contract_test_to_the_text_owner(self):
        self.assertEqual(missing(flat("skills/cycle/SKILL.md"), (
            "give each test that asserts instruction text to the stream that owns that text",
            "reports the wording to the owning stream and leaves the test alone")), [])

    def test_inspect_summary_is_documented(self):
        self.assertIn("`{\"op\":\"inspect\",\"summary\":true}`", flat("skills/cycle/SKILL.md"))
        commands = flat("skills/cycle/references/commands.md")
        self.assertEqual(missing(commands, (
            "`host` and `summary` (both optional)", "With `summary: true`, `inspect` prints",
            "`open_attempts`", "The full output is the default and keeps every field")), [])


class EngineInterfaceInstructionContracts(unittest.TestCase):
    """The instructions name the CYC-0096 engine interfaces where a caller uses them."""

    SKILL = "skills/cycle/SKILL.md"
    COMMANDS = "skills/cycle/references/commands.md"

    def test_long_requests_cycle_forms_and_path_bases(self):
        self.assertEqual(missing(flat(self.SKILL), (
            "Every `--json` option also accepts `'@PATH'`",
            "accepts it positionally or as `--cycle CYC`")), [])
        self.assertEqual(missing(flat(self.COMMANDS), (
            "Every `--json` option also accepts `'@PATH'`", "resolves inside the repository root",
            "through `..` or a symlink", "as `--cycle CYC`",
            "refuse a relative path that names a different file under each root")), [])

    def test_seeded_plan_task_and_plan_tasks_done_in_the_plan_file(self):
        self.assertEqual(missing(flat(self.SKILL), (
            "`create` seeds one Plan task, `plan`", "mark its Plan-phase tasks done in the plan file")), [])
        self.assertEqual(missing(flat(self.COMMANDS), (
            "a Plan-phase task may carry `done`", "Such a task's dependencies must be done too",
            "`create` seeds one Plan-phase task, `plan`")), [])

    def test_review_scope_default_and_blocking_only_return(self):
        self.assertIn("A report that omits `scope` records the plan scope", flat(self.COMMANDS))
        self.assertIn("a report without `scope` records the plan scope", flat("skills/cycle/references/review.md"))
        self.assertIn("offers `return` only for a blocking finding", flat(self.SKILL))
        self.assertIn("permits `return` only for a blocking finding", flat(self.COMMANDS))

    def test_awaiting_architect_is_not_a_rejection(self):
        for relative in (self.SKILL, "skills/council/SKILL.md", self.COMMANDS):
            with self.subTest(site=relative):
                text = flat(relative)
                self.assertIn("awaiting-architect", text)
                self.assertIn("--architect PATH", text)
        self.assertIn("`next_command`", flat(self.COMMANDS))

    def test_friction_command(self):
        self.assertIn("`cycle.py friction CYC --json REQUEST`", flat(self.SKILL))
        self.assertEqual(missing(flat(self.COMMANDS), (
            "## Friction log", "`who`, `what`, `cost`, `category` and `fix`", "`F<N>`",
            "commits the record")), [])

    def test_classification_details_stay_in_inspect_and_finish(self):
        skill = flat(self.SKILL)
        for clause in ("`inspect` (`classifications`) and in the `finish` response",
                       "each question, answer, route or fallback, serving model/provider and reported cost",
                       "`cycle status` and the dashboards show only the line `Classifications: N`",
                       "where N is the number of classifications the cycle record holds"):
            self.assertIn(clause, skill)
        self.assertNotIn("in `cycle status` and the dashboards, and in the `finish` response", skill)
        for relative in ("crux/templates/AGENTS.md.tmpl", "bionic/AGENTS.md"):
            text = repo_flat(self, relative)
            self.assertIn("`cycle status` and the dashboards show only the line `Classifications: N`", text, relative)
            self.assertNotIn("dashboards and the completion record show each classification", text, relative)

    def test_dashboard_refresh_reads_the_record_after_a_write(self):
        self.assertEqual(missing(flat(self.SKILL), (
            "does not reuse that run's result, because the reader read the record when it started",
            "the next refresh shows the record as it stands after the write")), [])

    def test_focused_loop_tools(self):
        self.assertEqual(missing(flat("skills/cycle/references/testing.md"), (
            "related-tests.py PATH...", "--failed-from FILE", "not a receipt")), [])

    def test_queue_writes_commit_and_list_is_compact(self):
        self.assertEqual(missing(flat(self.SKILL), (
            "Every queue write except `start-next` commits its touched active/history paths",
            "`queue list --full`", "a comma-separated value is split into paths")), [])
        self.assertEqual(missing(flat(self.COMMANDS), (
            "`queue list [--full]`", "returns the result as `queue_commit`",
            "split each `--scope` value on commas")), [])

    def test_release_record_closes_the_cycle(self):
        self.assertIn("`release.py record --cycle` completes unheld steps and preserves open attempts", flat(self.SKILL))
        self.assertIn("The last listed delivery finishes the cycle", flat(self.SKILL))
        self.assertIn("With no open assignment, record runs `finish` itself", flat(self.COMMANDS))
        runbook = repo_flat(self, "DEPLOY.md")
        self.assertEqual(missing(runbook, (
            "marks unheld tasks done", "completed with no manual step",
            "an open assignment awaits its delegator's normal delivery",
            "It closes only the cycle it is bound to")), [])
        self.assertEqual([x for x in ('(add "beta" after the version)', 'record completion and advance the cycle')
                          if x in runbook], [])
        self.assertIn("prepends the log op, commits them and completes unheld steps", repo_flat(self, "AGENTS.md"))

    def test_status_labels_and_activity(self):
        self.assertEqual(missing(flat("skills/cycle-status/SKILL.md"), (
            "Tasks, Attempts and Councils", "the line `Classifications: N`", "`idle for <age>`",
            "Activity is not liveness", "never evidence that an attempt is lost", "--activity",
            "`cycle.py status --json --activity`")), [])

    def test_finish_worktrees_field_and_kept_cases(self):
        self.assertEqual(missing(flat(self.SKILL), (
            "`worktrees: {removed, kept}`", "A detached or locked worktree is kept")), [])
        self.assertEqual(missing(flat(self.COMMANDS), (
            "`worktrees: {removed: [{path, branch, task}], kept: [{path, branch, reason}]}`",
            "A detached or locked worktree is kept", "`branch_kept`")), [])

    def test_inspect_activity_is_not_liveness(self):
        self.assertEqual(missing(flat(self.COMMANDS), (
            "`activity: {state, last, text}`", "`last_activity`",
            "Activity age is not liveness and never loss evidence.")), [])

    def test_evidence_validate_and_report_output(self):
        self.assertEqual(missing(flat("skills/cycle/references/testing.md"), (
            "`execution_reason`", "`reuse_eligible`", "starts with a `summary` block")), [])


if __name__ == "__main__":
    unittest.main()
