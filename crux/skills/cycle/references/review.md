# Proportionate independent review

Read `.bionic.yml` `review.scrutiny`; absent means `standard`. Allowed values are
`focused`, `standard`, `intensive`. A plan may record its own `scrutiny` level with
its reason. Record the effective level and the reason for an adjustment.

- Focused: one independent reviewer checks correctness, relevant tests, clarity,
  and security on the changed surface.
- Standard: review affected behavior and integration points; add specialists
  only for relevant risks.
- Intensive: use threat analysis, adversarial checks, and specialist review of
  affected boundaries, failure modes, and operational consequences.

Depth and coverage determine scrutiny, not a fixed reviewer count. Consider
untrusted users/input, sensitive data, privileges, distribution, consequences,
and reversibility. Internal or open-source labels do not establish safety.

Target specialist checks at authentication/authorization/tenant isolation,
credentials/sensitive data/encryption, untrusted input reaching execution or file
operations, dependency installation/release distribution, and destructive
operations/migrations/recovery. One trigger does not require every category.
Several trust boundaries or broad irreversible effects warrant intensive review.
Omit irrelevant categories instead of dispatching agents to report N/A.

Classify findings as blocking, advisory, or cosmetic. Blocking means a demonstrated
defect, violated requirement, or missing evidence needed for an acceptance criterion.
Security findings name the reachable path, conditions, and consequence. Investigate
plausible concerns with targeted checks; a security label alone is not a blocker.
Missing evidence of a required safety property can block. Confirmed defects retain
their severity at every scrutiny level.

A demonstrated defect blocks only when the finding names a plausible failure within
the operating assumptions, its consequence and the smallest fix. The assumptions are a
trusted owner, cooperating agents, a trusted local checkout and one release
coordinator. Crux runs locally with a trusted caller, environment and interpreter, so
denial of service from hostile input never blocks.[^trust] An accidental malformed or
oversized input that hangs or crashes Crux is a plausible mistake and can block.[^blocker]

Check the implementation against the approved plan and any council verdict on it. A
design objection is a finding only when the implementation diverges from the plan or
shows a plausible failure the plan did not consider. Design is settled in the plan, and
a council dispute is never raised to the owner from review.

Review the diff, criteria, and relevant integration points. The reviewer reads the
diff, history and check observations itself unless the host denies it that shell.
Expand only for a concrete dependency or failure path. Record unrelated existing issues
separately unless they prevent the change working safely. Assess the selected checks,
their coverage rationale, tested revisions and applicability after edits. Request a
specific gap; broad shared changes can justify a full suite, but review alone does not.
The reviewer runs focused probes; the test coordinator owns broad checks. Explicit
reuse of an observation stays within the current cycle.

The lead commits the final code, records the selected checks and requests review with
`review-start ID --reviewer NAME`. The reviewer reads the cycle with `show`, assesses the
change from the cycle's base commit to the head it names, and submits its own verdict
with `review ID --actor NAME --expect-revision N --file FILE`.[^verdict] The writer refuses the
lead, an unrequested reviewer and anyone who led or implemented the cycle. A reviewer
differs from every implementer and does not modify the work under review. Council
approval of a plan does not replace independent review of the implementation.

The report names the reviewer, the plan revision, the base and head commits, the
verdict (`approve` or `changes-required`), the unresolved `blocking` findings, one
`acceptance` entry per criterion (zero-based `criterion`, `met`, `evidence`), a
`test_selection` assessment and a `summary`. Optional keys are `advisory`, `lessons` and
`remaining`. Name what the reviewer read and ran, and its limits.

A blocking finding, or an acceptance failure the review observes, becomes a task in the
same cycle. The lead fixes it within the authorized scope and requests a review of the
changed work. A change to scope takes effect only with the owner's recorded words, except
that the lead may add each path that a blocking finding, recorded by the cycle's
requested independent reviewer, names as the place to fix an unmet acceptance criterion
of the current plan.[^scope] A finding that needs a path outside the scope names that
path and the criterion. The lead adds it with `plan --finding TASK --criterion N`, and
the writer checks that the finding is blocking, recorded by the requested reviewer
for this cycle and names every added path. The next review judges whether the finding
named each added path as the place to fix and whether the named criterion requires the
fix. A failing check qualifies nothing on its own: the lead may request review while a
check fails, and the reviewer can name the path in a blocking finding. The reviewer revisits the changed portions and their consequences, and
repeats a full review only when the change invalidated earlier conclusions. No counted
return applies. A review counts for the plan revision and the code
range it names:[^binds] a later plan revision, new implementation work, or a change to a
reviewed path after the reviewed head makes it obsolete. A commit confined to cycle
records, council records, the journal, the operations log or the queue leaves it valid.
The reviewed paths are the code paths that differ between the cycle base and the
reviewed head. One rule applies when the writer records the report and again at
`finish`: the report stands while every reviewed path holds its content at the reviewed
head. A later commit that changes only other paths, such as the next cycle's work on
the same branch, refuses no report. Name a head that holds the code committed when the
lead requested review; the writer refuses an earlier one.

[^binds]: rule:review-binds-plan-revision-and-code-range
[^blocker]: rule:blocking-finding-names-a-plausible-failure
[^scope]: rule:scope-changes-with-the-owner-or-a-review-finding
[^trust]: rule:crux-trusts-its-local-environment
[^verdict]: rule:reviewer-records-its-own-verdict
