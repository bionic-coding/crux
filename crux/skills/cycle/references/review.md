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

Review the diff, criteria, and relevant integration points. Expand only for a
concrete dependency or failure path. Record unrelated existing issues separately
unless they prevent the change working safely. Reuse valid test evidence; request
new checks for a specific gap. After fixes, revisit changed portions and their
consequences; repeat full review only when earlier conclusions were invalidated.
Blocking findings use the cycle's return path and pass limit, never a hidden loop.

Return a consolidated report with reviewer identity, scrutiny and rationale,
scope, evidence and limitations, blocking/advisory/cosmetic findings, and verdict.
Council approval does not replace independent implementation review. The reviewer
must differ from the implementer and must not modify the work under review.

In a simplify cycle, check the diff against the selected proposals. Check the
reduction record against the dimensions the cycle skill defines for each area: every
dimension the diff changes must appear in that area's `before` and `after`, and its
`change` must follow the no-netting rule. Work for an unselected proposal is blocking.
