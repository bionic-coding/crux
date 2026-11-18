# Cycle testing

## Focused and selected checks

During development, run focused tests for changed behavior and for its callers,
dependencies, fixtures and integration points. After a fix, rerun the failed and the
affected checks. Before completion, the lead selects final checks by the change's scope
and risk.[^scope] A phase boundary never requires a full suite, because a cycle has no
phases.

Record each observation with `cycle.py check ID --file FILE`, or several with
`cycle.py batch`. An observation holds the command, the result, the tested revision, a
summary and the reason the check applies. A claim that a check passed cites such an
observation.[^claims] The tested revision is agent-attested: the writer does not run the
command and does not prove that the tested bytes equal the current checkout. Record
failures as well as passes. The latest failure of a selected check blocks `finish`.

```bash
uv run /abs/plugin-root/scripts/cycle.py --repo-root /abs/repo --compact check CYC-0123 --actor session-a --expect-revision 4 --file /abs/repo/check.json
```

Run the example in the project's selected environment and record the command you
actually used. A recorded observation is reused only explicitly, within its own cycle.
It is never reused across cycles or after a later failure of the same check, and only
while the final change leaves the inputs it checked as they were at its tested
revision.[^reuse] After edits, reassess which observations still apply and rerun the
others. The reviewer assesses the selection and its applicability to the final change.
Comprehensive PR CI is the integration backstop; it does not excuse a known local failure.

One test coordinator runs any full suite the selected checks include. A dev-lead
dispatched for another task, developers and reviewers run focused checks only.[^coordinator]
Avoid duplicate broad runs and do not edit the inputs of a running check. A developer in
a linked worktree runs focused checks only: `crux/scripts/tests/parallel_suite.py`
refuses a whole suite root there with the code `focused-check-rule`.

Select related tests by behavior and dependency reach. Include every test that imports,
invokes, reads, globs or enumerates a changed path. A test that enumerates a directory
holding a changed path reads every file below it, so select the suite that contains it.
A new regression test alone does not cover existing behavior. When automated tests do
not apply, say why and record a verifiable inspection or smoke check. Name the checks
you did not select and the gap that leaves in the plan's `verification.gaps`.

In the Crux development repository two tools shorten a focused loop.
`crux/scripts/related-tests.py PATH...` lists the test files under `crux/scripts/tests`
and `tools/tests` that name a changed path, by repository path, file name or module
stem, with one hop through a script that reads a changed template or data file.
`crux/scripts/tests/parallel_suite.py DIR --records FILE` records each outcome, and a
later run with `--failed-from FILE` reruns only the tests that failed or errored.
`--select ID` runs only the named module, class or method. Both tools take `--tier`.
Neither proves the selection is sufficient.

For a root instruction file `related-tests.py` lists about half the suite: 209 of the
451 test files in its two roots for `AGENTS.md`, reached through 38 scripts that read it. That list is no
focused loop. Select the tests that read the edited text, and leave the broad run to the
test coordinator's suite.

## Final checks

The final selected checks include the drift gates relevant to the change: at least each
gate any of whose checked inputs the change adds, removes or edits. No fixed roster
runs in every cycle.[^gates] In a project that adopts test tiers, they also include the
tier check whenever the change adds, removes or edits a test or a tier manifest.
The `check-drift` skill runs the whole drift roster (in the Crux development repository,
its runner is `tools/run-drift-gates.py`), and `uv run python3 crux/scripts/test-tiers.py check` runs the tier
check. Select a narrower gate when the change reaches only some of them, and record the
reason with the observation.
In the Crux development repository, `tools/drift-audit.py` runs the whole roster once a
week on the commit local `main` names, outside every cycle and release.

A completed cycle records a summary of its delivered outcome; no reflection step exists.[^summary]
Completion requires the agreed tasks done, the selected checks passing and an approving
review of the current plan revision.[^completion] Merging is a separate fact, recorded
with `cycle.py delivery`.

## Test tiers

Every test carries exactly one tier label in its root's `test-tiers.json`: `dev`,
`release` or `ephemeral`.[^one] The `test-tiers` skill states the manifest, the check
and the rubric. A change that adds a test file or test method labels it in the same
change.[^label] An ephemeral test carries a reason and an end condition, and stays until
a change names it for removal.[^ephemeral]

Tiers select development loops: a unit's focused checks and reviewer probes. No gate
narrows its test selection by tier.[^narrow] A full suite a cycle selects still runs every
test. A release cycle completes on its fixed step list. Release verification establishes
passing evidence for the release tier and runs the tier check.[^release] Merging a pull
request requires every test to pass on its head.[^merge]

In the Crux development repository the tier check covers all five roots
(`crux/scripts/tests`, `tools/tests`, `crux-mods/tests`, `crux-opencode/tests` and
`crux-omp/tests`). Every test the staged per-minor `flagged` list selects is in the
release tier.[^flagged]

## Release verification

In the Crux development repository a release has no separate test step. `release.py
verify` is the only release step that runs the registered suites, through the evidence
engine (`scripts/test-evidence.py`). For each suite it looks up the full declaration
without executing and reuses an eligible full pass. A current failing full receipt fails
the step. Otherwise it runs that suite's release-tier declaration. It also runs the
registered tier check. Finish the release prep before this step: a late change to
anything a suite reads makes the step run that suite again.

Every test runs in the main run once per code state on the floor minor (3.13). The
staged artifact gets two short checks on every minor in `pyproject.toml`
`[tool.crux] python-versions` (3.13 and 3.14): `flagged` runs the committed list of tests
that can differ between interpreters or the packaged tree, and `health` compiles every
staged `.py` file and imports every staged module. The test coordinator runs the staged
dry run once, after the last commit, on a clean tree:

    bash sync.sh --public-repo idyll/crux --dry-run --skip-fingerprints

The dry run stages the tree, runs the staged gates and runs `flagged` and `health` on
every minor. Each run writes a receipt, which `release.py verify` reuses while the staged
inputs match. `--skip-fingerprints` skips only the check that `public/` matches its
sources, because the release prep regenerates `public/` after the cycle's checks;
`release.py prepare` still checks it. The command publishes nothing and takes no ledger.
A change whose paths all fall outside the staged allowlist, such as the documentation
tree alone, needs no staged run.

The main run keeps its receipts across a docs-tree decision-only commit (`adrs`, `arch`,
`observations`, `research`, `briefs`, `index.md`, `manifest.yml` and `objectives.md`),
which leaves the main-run receipts reusable. A commit that touches the root instruction
or guide documents still runs the main run. A rerun of the main run on an unchanged code
state needs `--retry-reason`.

The evidence engine's receipts, lookup rule and declaration format describe release
evidence only: read `test-evidence.py --help`. A cycle's own checks use `cycle.py check`.
Release evidence lives in the durable store `<git-common-dir>/crux/test-evidence`.
Evidence is not published in the release artifact.

## Historical cycles

Historical cycles recorded under the typed engine carry their own evidence contract:
test-evidence receipts attached with `cycle.py evidence`, phase gates and full-suite
requirements. Their records and receipts stay intact and are read-only through
`cycle.py status`; nothing in this reference applies to them.

[^scope]: rule:checks-follow-scope-and-risk
[^claims]: rule:check-claims-cite-recorded-observations
[^reuse]: rule:observations-are-reused-only-within-their-cycle
[^coordinator]: rule:one-coordinator-runs-selected-full-suites
[^gates]: rule:final-checks-include-relevant-gates
[^summary]: rule:closure-records-a-summary
[^completion]: rule:completion-needs-work-checks-and-review
[^one]: rule:every-test-has-exactly-one-tier
[^label]: rule:new-tests-are-labelled-in-the-same-change
[^ephemeral]: rule:ephemeral-labels-carry-a-reason, rule:ephemeral-labels-carry-an-end-condition, rule:ephemeral-tests-leave-only-by-explicit-change
[^narrow]: rule:tiers-never-narrow-a-cycle-gate
[^release]: rule:release-verify-covers-the-release-tier, rule:release-verify-runs-the-tier-check
[^merge]: rule:merge-requires-every-test-on-the-head
[^flagged]: rule:staged-per-minor-tests-are-release-tier
