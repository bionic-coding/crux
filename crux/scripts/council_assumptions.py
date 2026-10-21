"""The operating assumptions and blocker test every council seat prompt carries.

One constant, appended to the system text of every seat. `with_assumptions` is idempotent, so a
caller that already includes the text and the shared seat call do not duplicate it.
"""

COUNCIL_OPERATING_ASSUMPTIONS = (
    "Operating assumptions: a trusted owner, cooperating agents, a trusted local checkout and one "
    "release coordinator. Plausible mistakes and crashes are in scope. Deliberate local tampering "
    "and identity authentication are outside these assumptions. "
    "Blocker test: a blocker states a plausible failure within these assumptions, its consequence "
    "and the smallest necessary fix. Everything else is an advisory or a documented limit. "
    "A finding that is safety-related alone is not a blocker. "
    "A recommendation that adds complexity (more code, tests, instructions, execution, configuration "
    "or concepts) names the concrete failure it prevents, why a simpler fix is insufficient, and its "
    "maintenance and testing cost; otherwise it is an advisory."
)


def with_assumptions(system):
    """Return `system` with the operating assumptions appended once."""
    base = (system or "").rstrip()
    if COUNCIL_OPERATING_ASSUMPTIONS in base:
        return base
    return (base + "\n\n" if base else "") + COUNCIL_OPERATING_ASSUMPTIONS
