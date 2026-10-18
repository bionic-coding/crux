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

## Evidence commands

A JSON check declaration names `check_id`, `command` as an argument array, `inputs`
as repository-relative paths/globs, optional `environment` variable names, and an
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
from the declared inputs. For example, `"inputs": ["src", "tests", "bionic"]`
can use `"exclude_inputs": ["bionic/cycles"]` when cycle bookkeeping is irrelevant
to that check. This prevents progress updates invalidating its evidence. Never
exclude a file the check reads merely to obtain reuse; tests of cycle records must
include those records. Prefer declaring the relevant documentation paths instead
of all `bionic/` when possible. Record the exclusion rationale in coverage.

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py" lookup --repo-root . --check check.json
uv run "${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py" run --repo-root . --check check.json
uv run "${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py" validate --repo-root . --evidence-id TE-ID
```

The runner reuses a valid pass and coordinates matching execution. After a failure,
use `--retry-reason TEXT` only when a new attempt is justified. Attach its evidence
ID through `cycle.py evidence`; use the returned disposition rather than inventing
an execution. Repository records live under `<git-common-dir>/crux/test-evidence/` in Git
repositories, or `.crux-test-evidence/` outside Git. `CRUX_TEST_EVIDENCE_STORE`
can select an external store for staged artifacts. Evidence is not published
as part of those artifacts. Preserve diagnostic output according to the repository policy.
