# Native Lite council

Lite uses the configured `levels.apex` directly, rather than the reviewer role's
model override. The owning writer prepares sealed requests and alone records
results. The host coordinator performs the actual dispatch. No OpenRouter key,
gateway call, daemon or emulated agent API is involved.

Supported verified adapters are Codex's `collaboration.spawn_agent` and the Claude
CLI JSON contract. Unsupported hosts refuse before dispatch. OpenCode retains
gateway Standard/Strict until a verifiable native host adapter is available.

## Prepare, dispatch and ingest

Use an explicitly initialized Lite project or an authorized existing-project
selection. Human acceptance remains independent. First Crux setup defaults to
Standard and can explicitly select Lite:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle-council.py" --repo-root <project> \
  --initialize-council lite --selection "Owner selects Lite during initial setup"
```

Prepare the challenge through the writer:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle-council.py" --repo-root <project> \
  --purpose consultation --identity <stable-decision-name> --subject <docs-relative-subject> \
  --question <question-file> --harness codex --author-context <actual-author-context> \
  --prepare-pass challenge
```

The output contains `request`, `request_sha256`, `attempt`, `tool`, and the exact
`dispatch` input. The request and trace are committed before dispatch. Preserve
those bytes. Never modify a prepared request, replace its reviewer or repeat an
uncertain dispatch. Input capability or credential failure never selects another
model or mode.

For Codex, call the actual `collaboration.spawn_agent` with emitted `dispatch`.
It selects the catalog Apex model/effort and `fork_turns: none`. Capture the
unmodified input and actual result. The actual result's `task_name` is the context
identity. Retain the delivered final message with its original Sender metadata.
Write a host envelope containing `tool`, `input`, `result`, and `final` (the exact
delivered final transcript). Model-authored identity claims are not evidence.

For Claude, select `--harness claude`. The emitted `dispatch` contains the actual
CLI `argv`, sealed `stdin`, and fresh `session_id`. Run that argv with stdin in an
empty scratch directory outside the project. Keep the actual cwd in input
metadata. Preserve raw stdout/stderr and the actual return code. The host envelope
contains `tool: claude-cli`, `input`, and `result` with `stdout`, `stderr`, and
`returncode`. The adapter validates the returned session and actual `modelUsage`
against the requested Apex. Its safe-mode, empty tools, fresh session, explicit
model/effort and no-resume argv are fixed by the request.

Ingest the actual result through the writer:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle-council.py" --repo-root <project> \
  --request <docs-relative-request> --ingest-result <host-envelope-json>
```

The writer verifies the exact sealed dispatch, model and independent context.
It also verifies protected subject, configuration, catalog, policy and this
decision's evidence bytes/inventory. Unrelated cycles do not invalidate a pass.
A protected edit, stale result, malformed output, missing context or execution
failure closes the attempt without approval. A challenge never grants approval.

## Architect response and final review

After the challenge is durably closed, the architect responds or revises the
subject. Record that response in a file. Prepare the final pass with the same
purpose, subject, identity, harness and author context, adding:

```text
--prepare-pass final --native-attempt <attempt> --response <response-file>
```

The final request includes the original findings, response and exact resulting
subject. A migration final pass revalidates and includes its final bound package.
Dispatch through a fresh context/session and ingest its actual result. Neither
the author nor first reviewer can serve as the final reviewer.

Final reviewer approval still needs architect agreement on the exact final hash.
Pass an agreement JSON with `agrees`, `subject_sha256`, `rationale`, and `dissent`
(an empty list for Lite) to `--architect <file> --record <result>`. This records
agreement without another reviewer call. Required binding failures or missing
authorization cannot be waived.

## Recovery and limits

Use `--recover <attempt>` only for already-produced results whose persistence was
interrupted. Recovery restores or recognizes the original result and sends no
request. An uncertain dispatch without a retained result blocks progression.
Two Lite passes are one attempt. A failed pass permits no replacement within it.
Later attempts retain findings and total count. Stop when progress stalls or the
frozen limit is exhausted. Explicit owner extensions remain bound to subsequent
attempts; mode changes never reset the history.

Automated fake-host controls establish protocol behavior. They are not evidence
that a native model actually ran. Report actual native acceptance separately.
