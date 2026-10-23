# Shared test evidence

Test evidence belongs to the repository and is reusable across phases and cycles.
Before running a check, look for valid passing evidence. Execute only when inputs
changed, evidence is missing, or an explicit freshness requirement expired. Record
the reason. A failure remains visible; retry unchanged inputs only with a stated
reason, such as infrastructure recovery or investigation of flakiness.

One coordinator per cycle owns lookup and execution. Other agents request checks
through it. Matching executions already running across cycles are awaited, not
duplicated. Use the repository evidence runner and its supported check declaration
format; consult its help rather than inventing records or claiming reused checks ran.

Declare broad conservative input sets initially: source, tests, fixtures,
configuration, dependencies, toolchain, and relevant environment identity. Never
record secret values. Capture exact command, working-tree fingerprints, source
revision for traceability, result, time, output reference, and freshness policy.
Commit identity alone neither proves nor invalidates a result. A pre-existing
Tester note without these inputs does not automatically satisfy the reuse contract.

A matching pass is reused by reference. A relevant input change invalidates the
affected check; uncertain dependency scope invalidates conservatively. Bookkeeping
changes do not invalidate checks unless the bookkeeping is an input. A phase change,
review request, new commit, or new cycle alone is no reason to execute again.

Evidence proves only its declared coverage. Packaging and installation checks
bind the actual artifact. Deployment smoke checks run against the new deployment.
External checks use explicit freshness requirements. Release reuses matching
correctness evidence and produces only missing or invalidated evidence.

In the Crux development repository, a release has no separate test step. verify is
the only release step that runs the registered suites. It reuses the newest passing receipt whose inputs match exactly
and executes a suite only when no receipt matches. Finish the prep (version surfaces,
changelog, generated release documents and the prep commit) before verify. A late
change to anything a suite reads makes verify execute that suite again; nothing
refuses, and the release takes longer. The release command's prepare step prints an
advisory naming the suites that verify would execute. The advisory changes no verdict.

Report reused, newly executed, invalidated, retried, and awaited checks with their
reasons. Do not impose a second full suite simply at integration, review, or release.
The required coverage must be established, whether by valid reuse or execution.

Declare affected behavior and integration points through `cycle.py coverage`.
Select related tests, including checks that import, invoke, read, or enumerate
changed inputs. Give each selected check a coverage rationale and explain omitted
checks. New regression tests alone do not establish related behavior. If automated
tests do not apply, explain why and declare an appropriate verifiable inspection
or smoke check. Unknown reach needs conservative coverage, not an automatic full
suite. Review examines this declaration alongside valid run/reuse evidence.

## The lookup rule

One question decides every lookup, execution and validation: did this check run and
pass, in an environment that satisfies its requirement, on the subject's relevant
inputs? No caller re-probes its own process, so a receipt that ran in another
interpreter validates in any process.

- **Inputs** are the declared files, the Git inventory and HEAD tree of a git-tracked
  declaration, and the digest of the lock the requirement names. They decide the
  receipt's fingerprint.
- **Environment** is what the executing process reported before the entry started.
  Python checks run through `test_evidence_capture.py`, which writes an identity file:
  implementation, version, marker environment, flags, encodings, the distribution list
  and a digest of each allowlisted variable. The engine records no pass without it.
- A **requirement** names the interpreter implementation and minors, the packages (the
  subject's `uv.lock` with group selection and the project included or excluded, or exact
  pins), whether the check is isolated, the tools it invokes, the variables it registers,
  and optional flag values and a freshness limit. A receipt satisfies it only when its
  recorded package set equals the expected set exactly, with no allowance for pip,
  setuptools or wheel. The expected set evaluates the lock export's markers offline
  against the receipt's recorded marker environment. A recorded tool version must equal
  the version found on this machine. The engine removes unregistered behavior variables
  (`PYTHONPATH`, `PYTHONHASHSEED` and the rest of the interpreter set) from the child.
  `sys.flags`, warning options and `-X` options must hold interpreter defaults, and the
  encodings must be UTF-8. A check that is not registered validates against its own
  recorded declaration, and its default requirement is the subject's locked project
  environment.
- **Candidates** are version-2 receipts with the same declaration and fingerprint. A
  candidate counts when its environment satisfies the requirement. A pass also needs its
  output log to match its sha256, but a sealed failure blocks even when its log is
  missing. The newest counted candidate decides: reuse a pass unless `freshness_seconds`
  expired, require `--retry-reason` to run again after a failure, and execute when no
  candidate counts.
- A failure from an environment that does not satisfy the requirement, an interrupted
  receipt and any version-1 receipt neither pass nor block. Version-1 receipts are
  history. Naming one to `validate` refuses with
  `environment-not-comparable (schema_version 1)`.
- The engine classifies a finished run. Exit 0 with unchanged inputs passes. A non-zero
  exit, including every exit 2, and a death from a signal the engine did not send fail.
  A SIGINT or SIGTERM the engine receives (it stops the child's process group), a launch
  error, and `parallel_suite.py` exit 3 (its interpreter refusal, before any test) record
  interrupted. When the engine itself dies, no receipt exists and the next lookup
  executes.
- A matching execution in progress is awaited, never duplicated.
- A receipt that fails its seal stops the lookup and names the file. The operator moves
  that file into the store's `quarantine/` subdirectory, which lookup does not read.
  Nothing edits or deletes a receipt.

## Completeness and eligibility

Two verdicts, and neither implies the other. A receipt is **complete** when it is
present, its seal verifies, and its output log is present with the recorded sha256,
computed on the decompressed bytes of a compressed copy. It is **eligible** when lookup
would reuse it for the current inputs and environment. A complete version-1 receipt is
ineligible, and an incomplete pass never counts.
`test-evidence.py report --evidence-id ID [--directory DIR]` prints both verdicts and
reads a retained directory without writing to it.

In the Crux development repository, release evidence lives in the durable store
`<git-common-dir>/crux/test-evidence`, for checkout and staged suites alike. With
`CRUX_TEST_EVIDENCE_DURABLE_ONLY=1` the engine refuses any other store. To retain a
receipt and its log, call `test_evidence.retention_copy`. It scans the uncompressed
bytes with the secret scan, withholds a matching file and records the withholding in its
place, then gzips a log above 1 MiB.

## Evidence commands

A JSON check declaration names `check_id`, `command` as an argument array (write the
interpreter as `python`; the engine ignores its path), `inputs` as repository-relative
paths/globs, optional `environment` variable names, an optional `requirement`, and an
optional positive `freshness_seconds`. Include dependency lockfiles and tool config
in inputs. Never put secrets in commands or declarations. For example:

```json
{
  "check_id": "parser",
  "command": ["python3", "-m", "unittest", "tests.test_parser"],
  "inputs": ["src", "tests", "pyproject.toml", "uv.lock"],
  "exclude_inputs": [],
  "environment": []
}
```

`exclude_inputs` is an optional list of repository-relative paths/globs removed
from the declared inputs. Never exclude a file the check reads merely to obtain reuse;
tests of cycle records must include those records. Record each exclusion's rationale
in coverage.

### Declare cycle checks from presets

Declare a cycle check with a preset; never hand-write a declaration that copies the
shared exclusions. `declare` prints a concrete declaration, which the other commands
take unchanged:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py" declare --repo-root . --preset drift-gates --check-id CYC-ID-drift-gates --output check.json
```

| Preset | Command | Inputs and exclusions |
|---|---|---|
| `whole-tree` | the caller's `--command JSON` | every Git-tracked file plus Crux's broad input list, minus the shared exclusions |
| `drift-gates` | `tools/run-drift-gates.py --cycle-scope` | as `whole-tree` |
| `mods-gate`, `opencode-gate`, `omp-gate` | that gate's script with `--phase dev` | as `whole-tree`; refuses when the script is absent |
| `release-metadata` | `tools/release-preflight.py --metadata` | the broad inputs of `whole-tree`; no release exclusion, no projection |
| `journal-index` | `generate-journal-index.py --dry-run` | the journal directory, `crux/scripts` and `.bionic.yml`; no exclusions |

Every preset except `whole-tree` runs a script at a fixed path in the Crux development
repository, under `tools/` or `crux/scripts/`. In any other project it refuses as not
applicable; do not copy or recreate those scripts. A consuming project declares its own
checks with `whole-tree` and its own test command, for example `--preset whole-tree
--check-id CYC-ID-tests --command '["python", "-m", "unittest"]'`. Every Git-tracked
file is an input, so a change to a tracked file invalidates the receipt. That
project's checks also cover its version and changelog changes.

`--requirement JSON` replaces the preset's requirement. The declaration carries the
expanded exclusions and no preset field, so a receipt matches on its contents.

Use `whole-tree` only for a command that reads none of the shared bookkeeping paths.
A check that reads one declares its own inputs and keeps that path, with the reason in
coverage. Any exclusion beyond the shared list is documented in coverage the same way;
the shared list itself is never repeated by hand.

### Bookkeeping exclusions

A path is bookkeeping for a check in one of two cases. The check does not read it. Or
it is an append-only record whose new entries cannot change the check's verdict and
whose existing entries its writers never change. A gate whose verdict depends on every
entry of such a record does not run in a check that excludes the record.

`suite_evidence.runtime_exclusions` produces the one shared list. It holds these
docs-relative names: `cycles`, `journal`, `log.md`, `inbox`, `garden`, `whats_next.md`
and `queue`. It adds the repository files listed under `evidence.bookkeeping_paths` in
`.bionic.yml`. Each entry is a repository-relative regular file outside the docs
directory, with no glob, no `..` and no symlink; a missing file is allowed. Before an
entry joins the setting or a name joins the list, record a live-read audit showing that
every preset command and registered suite reads it not at all, or only under the
append-only case. `.bionic.yml` is itself an input, so a setting change reruns each
check once.

A journal entry, a log append, a queue edit, a cycle-record write and an edit of a
configured file therefore leave the registered suites and every excluding preset
valid. Reflect needs no evidence refresh for them.

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py" lookup --repo-root . --check check.json
uv run "${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py" run --repo-root . --check check.json
uv run "${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py" validate --repo-root . --evidence-id TE-ID
uv run "${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py" report --repo-root . --evidence-id TE-ID
```

The runner reuses a valid pass and coordinates matching execution. After a failure,
use `--retry-reason TEXT` only when a new attempt is justified. Attach its evidence
ID through `cycle.py evidence`; use the returned disposition rather than inventing
an execution. Repository records live under `<git-common-dir>/crux/test-evidence/` in Git
repositories, or `.crux-test-evidence/` outside Git. `CRUX_TEST_EVIDENCE_STORE`
can select an external store. Evidence is not published as part of the release artifact. Preserve diagnostic output according to the repository policy.

## Release-neutral evidence

This section describes the Crux development repository.

A release changes version numbers and release documents, not software behavior. The
registered suites therefore read through a registry in `suite_evidence.py` that keeps
a release-only change from invalidating their receipts.

- **Projections.** A suite fingerprints only the release-varying span of these files, so
  a version bump leaves its receipt valid. In the checkout: the `version` of the four
  plugin manifests, `[project].version` in `pyproject.toml`, the `crux` entry of
  `uv.lock`, `reviewed_plugin_version` in the catalog guide, and the version in the
  `README.md` footer. In the stage: the manifests, the `.generated` version, and the
  `README.md` fingerprint line and footer. The kind set is closed.
- **Exclusions.** A release document that no suite reads is excluded: `public/` from the
  checkout suites, the staged `CHANGELOG.md` from the staged suites.
- **CHANGELOG.md stays an input of the checkout suites.** A migration citation check
  reads one of its footnotes, so a `CHANGELOG.md` edit re-executes them.
- **What reuses.** A release-only change keeps the other receipts. An authored edit to
  `README.md`, `USER_GUIDE.md` or any other source during release prep is a real change,
  and verify executes the suites that read it again.

The metadata check covers what the suites no longer see. Every full preflight executes
it (`tools/release-preflight.py --metadata`). In that repository, record the `release-metadata`
preset at Test when a cycle changes `CHANGELOG.md`, `public/` or a version surface, and when in
doubt, because it takes seconds. Only `README.md` carries a footer projection.

Audit every new projection or release exclusion before it joins the registry, in three
legs:

1. **Static search.** Find every suite module that names the path.
2. **Traced run.** Trace `open()` across the suite on a synthetic release-only commit.
3. **Differential run.** Corrupt each excluded file, and give each projected surface a
   distinct sentinel, then run the suite.

A path joins only when all three legs show no value reader and no relational reader in a
suite that drops it. Otherwise it stays an input.

## Drift gates and when a cycle runs them

This section describes the Crux development repository, whose drift roster runs through
`tools/run-drift-gates.py`. Another project runs the `check-drift` skill when it needs a
drift report, and declares its own checks with `whole-tree`.

Release verification runs every drift gate over a shipped surface: the catalogs, the
rules catalog, the routing table and the other regenerated blocks. It leaves out five
docs-tree gates: `summarize-adrs.py`, `compile-doctrine.py`, `generate-reviews-index.py`,
`derive-arch.py` and `check_observations.py`. Each takes about three minutes over the
decision tree, and a release reads the same tree its cycle already checked.

Each cycle's Test phase runs one check-drift step, made of two preset checks. The
`drift-gates` preset is a required check. It runs the runner with `--cycle-scope`,
which runs every roster gate except `generate-journal-index.py` and reports that gate
under `skipped` with the reason `write-time`. The `journal-index` preset runs that one
gate; record its receipt on a Test-phase task, not as a required check. Together the
two cover the whole roster at Test. Reuse applies to both, so an unchanged tree runs
nothing again.

The journal index is not a required check because its only writer regenerates it on
every journal write, and release verification still runs its gate. The Reflect journal
entry therefore changes no required evidence. A journal month edited outside
`log-work` after Test drifts the index until release verification or an on-demand
`check-drift` reports it.

The five docs-tree gates stay in the roster, in `check-drift` and in the `drift-gates`
preset; only the release run skips them. The runner reports them under `skipped` with
the reason `cycle-time` and refuses when one is no longer declared. Their corroboration
reads past log and journal entries, which the append-only case covers. A hand edit of
a past entry after the last `drift-gates` execution is seen only by the next execution
that a real input change triggers.

A cycle whose changes add or modify a migration replay receipt or a prospective publication
record runs `uv run "${CRUX_PLUGIN_ROOT}/scripts/migration-receipt.py" verify --repo-root .
--since <cycle base commit>` at its Test phase. The command replays the prior reader for each
receipt added or changed since that commit, with every receipt ignored, because a read trusts a
committed receipt without replaying it. Record the command, its exit code and the commit it
ran against as evidence. Release verification runs the same check from the previous release's
source revision, so a receipt is proven when written, in its cycle, and once more before the
first release that contains it. A cycle that changed no receipt or publication record has
nothing to run.

## Simplify reduction evidence

A simplify cycle also records `reduction` in Test, per area, bound to the current source
fingerprint (see the commands reference). A test run on other source does not satisfy it.
