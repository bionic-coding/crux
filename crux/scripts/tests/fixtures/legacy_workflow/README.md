# Historical workflow instruction fixtures

These files preserve the promptbook-era instruction contracts from commit
`0ee6f08aaac799325f6240da67d5570686f167ea` before the cycle cutover.
They are test data, never instructions for an agent or a source of current authority.

The `.fixture` suffix prevents instruction and catalog discovery. The explicit
`_legacy_workflow_prose.legacy_path` adapter uses a fixture only for named historical
prose tests; other files still read the shipped source. No runtime reader imports it.

`test_cycle_instruction_contracts.py` asserts the live replacement: type-specific
phases and limits, progress stops, decision approval and authority, review scrutiny,
shared evidence, and delegation. Live safety and capability-reflex suites remain
bound to current agent files. Legacy runtime tests remain bound to their original
schemas and execution machinery.
