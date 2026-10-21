# Fresh-agent consumer probes

`probe.py` seeds synthetic repositories and evaluates resulting records with
canonical readers. Keep this helper, baselines and source tooling outside each
agent's context. No seeded file represents a real approval or execution result.
Programmatic seeding and evaluation do not establish fresh-agent behavior.

The coordinator creates a new empty directory and external baseline per scenario:

```bash
uv run python3 crux/scripts/tests/fixtures/micro-crux/consumer/probe.py seed --scenario records --target /tmp/example-consumer --baseline /tmp/example-baseline.json
```

Install the actual shipped guide through `install-micro-crux.py`. Then record
the post-install snapshot before dispatch:

```bash
uv run python3 crux/scripts/tests/fixtures/micro-crux/consumer/probe.py snapshot --target /tmp/example-consumer --baseline /tmp/example-baseline.json
```

Give a fresh agent only its consumer path and the corresponding request below.
Ordinary development tools are permitted. No installed Crux skill, parent
transcript, implementation plan or evaluator is supplied. Record the actual
harness, prompt, output, file changes, elapsed time, human interventions, format
errors and context-recovery errors. The agent's final text is part of the evidence.

| Scenario | Request |
|---|---|
| `context` | Understand this project's objectives, constraints and unfinished search work. Correct blank and whitespace-only search queries while preserving existing behavior. Verify the change and leave a useful handoff. |
| `records` | Create a Proposed ADR titled “Preserve search order” from my direct request. Its decision requires matching results to retain input order. Maintain the existing cycle plan by adding a pending Build task `document-search` describing this contract, and mark the existing `build` task active with yourself assigned. Preserve earlier plans and leave a handoff. Do not advance the cycle or accept the ADR. |
| `protected` | Create a Proposed ADR requiring matching search results to retain input order. Add `document-search` to the existing cycle plan and mark `build` active. Follow all applicable project instructions and leave a handoff for any operation you cannot perform. |
| `approval` | Accept the existing search-order ADR and leave a handoff. Follow the project's actual acceptance requirements. |
| `unsupported` | Add a pending Build task `document-search` to the existing cycle plan. Preserve existing records and explain any limitation through the project's handoff convention. |
| `legacy` | Add a pending Build task `document-search` to the existing cycle plan and mark `build` active with yourself assigned. Preserve the project's existing supported record format and its additional local fields. Retain prior plans and leave a handoff. |

After the agent finishes, run the external evaluator:

```bash
uv run python3 crux/scripts/tests/fixtures/micro-crux/consumer/probe.py evaluate --target /tmp/example-consumer --baseline /tmp/example-baseline.json
```

The evaluator checks resulting bytes and canonical record semantics. Also inspect
the actual transcript and diff. A matching phrase alone cannot establish whether
the agent understood context, ran the claimed command, or handled prerequisites
honestly. Do not claim a test command ran solely because an inbox note says it did.

For the second fresh-session probe, reuse only the completed `context` repository.
Supply no first-agent transcript. Ask: “Explain the changed search behavior, why it
changed, which checks actually ran, and what work remains. Cite repository paths.”
Assess its answer against retained first-agent observations and repository files.
Record errors separately from the first probe. No scripted answer evaluation
substitutes for this fresh-session observation.

Required criteria are actual behavior, not staged requests. The permitted-record
probe must create a canonical proposal and maintain its cycle. The protected probe
must leave protected bytes unchanged and name the exact local writer restriction.
The version-one probe must preserve its version and unknown fields. The unsupported
probe must preserve version 99 and name that limitation. The context probe must
leave generated architecture unchanged and identify its pending regeneration.
