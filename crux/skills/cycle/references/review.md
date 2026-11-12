# Proportionate independent review

Read `.bionic.yml` `review.scrutiny`; absent means `standard`. Allowed values are
`focused`, `standard`, `intensive`. Record the effective level and the reason for
an adjustment. Cycle type and scrutiny are separate.

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

Check the implementation against the approved plan and its Implementation Decisions.
A design objection is a finding only when the implementation diverges from the
approved record or shows a plausible failure the record did not consider. Nits that
the architect agreement of the approved revision marks `apply-in-build` are not
findings; the reviewer reads that record. Design is settled in Plan, and a council
dispute is never raised to the owner from Review.

Review the diff, criteria, and relevant integration points. The reviewer reads the
diff, history and receipts itself unless the host denies it that shell. Expand only
for a concrete dependency or failure path. Record unrelated existing issues separately
unless they prevent the change working safely. Reuse valid test evidence; request new
checks for a specific gap. The reviewer runs focused checks only, the tests that
exercise a finding; full suites, the staged dry run and per-minor runs belong to the
test coordinator, the dev-lead. Check that the Build checks include every test that
imports, invokes, reads, globs or enumerates a changed path; an omitted related test
is missing evidence. After fixes, revisit changed portions and their consequences;
repeat full review only when earlier conclusions were invalidated. Blocking findings
use the cycle's return path and pass limit, never a hidden loop.

A fix-diff review follows the Review findings the commander answered with a fix task.
The reviewer checks only the fix diff against the finding or findings, once. A
blocking fix-diff review returns to Build. After a Verify finding, the normal Review
covers the fix.

The delegator commissions the reviewer with an assignment that carries the outcome,
evidence and constraint. The reviewer writes its own report to the result file the
dispatch names; the commander records it with `review --json`, and a report without
`scope` records the plan scope; typed `advance` then attaches the receipts the review
rests on. Each report scope entry claims a full review of every plan path it covers,
a directory entry included.[^scope] The writer checks coverage, and the reviewer's
evidence carries the claim: it names what the reviewer read and ran for each scope
entry. A reviewer differs from every implementer of the range under review.

A return from Build retains `execution_refusal` in its `return-requested` event: one range
per task whose base the return abandoned, with every commit the new pass placed below every
new task base. The reviewer reads each retained `execution_refusal` and reviews the commit
of every non-bookkeeping row of every range with the range under review. A refused row whose
commit carries a `Cycle-Task` trailer naming a task of this cycle, and which a finished
delivery of that task lists, is reviewed as that task's work, such as a sibling's committed
work in progress. Only such a trailered commit that no finished delivery of its task lists
is a scope finding.

Return a consolidated report with reviewer identity, scrutiny and rationale,
scope, evidence and limitations, blocking/advisory/cosmetic findings, and verdict.
Council approval does not replace independent implementation review. The reviewer
must differ from the implementer and must not modify the work under review.

In a simplify cycle, check the diff against the selected proposals. Check the
reduction record against the dimensions the cycle skill defines for each area: every
dimension the diff changes must appear in that area's `before` and `after`, and its
`change` must follow the no-netting rule. Work for an unselected proposal is blocking.

[^blocker]: rule:blocking-finding-names-a-plausible-failure
[^scope]: rule:review-covers-the-declared-scope
[^trust]: rule:crux-trusts-its-local-environment
