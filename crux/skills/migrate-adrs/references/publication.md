# Exact packages and publication

Run `uv run "${CRUX_PLUGIN_ROOT}/scripts/adr-migration.py" --help` for arguments.
Resolve all paths relative to the repository, except council subjects relative to
the configured documentation root. Schemas live in `crux/schemas/adr-migration-*.schema.json`.

1. Validate a supplied explicit machine map with `package --path PACKAGE`; use
   `bundle --path PACKAGE` to present every bound byte. Source and successor handles,
   exact clause digests, rationale, obligations, dependencies, connected item IDs and
   owner stops belong to the package. No free-form TXT parser invents dispositions.
2. Run `cycle-council.py --purpose disposition --subject SUBJECT --question QUESTION`
   with committed readiness for the initial bootstrap, or verified installed support
   for a later consuming project. This is distinct from ADR review and respects its
   actual configured threshold and round limit.
3. Record the genuine owner instruction when required, then `approve --id ID
   --package PACKAGE --council COUNCIL --readiness READINESS --owner OWNER`.
   Commit this receipt separately before activation. `approval --path APPROVAL`
   validates exact bindings, readiness and the policy from its action's first parent.
   Owner approval can precede or follow tooling/council; preserve its actual provenance.
4. `candidate --id ID --package PACKAGE --approval APPROVAL` writes a non-authoritative
   candidate. `candidate-show --path CANDIDATE` validates it without publishing.
5. `publication-stage --path CANDIDATE --input CHANGES` validates the exact prior reader
   and candidate reader. CHANGES is a JSON object mapping declared destination paths
   to contained source paths (or null for deletion). Include the byte-exact candidate
   at its top-level publication destination. Later publications can stage that one file
   only. The initial transition also requires `--scope SCOPE` with the reviewed path list;
   it includes the whole approved routing, reader, citation and regeneration transition.
6. Independently review the prepared connected tree and related evidence, then commit
   it once. Activation writes no approval record. Only the committed immutable publication
   enters public authority discovery. Run the canonical regenerators and drift checks
   for summaries, doctrine, resolver and affected catalogs; never hand-edit outputs.
7. Immediately after the activation commit, run `uv run "${CRUX_PLUGIN_ROOT}/scripts/migration-receipt.py"
   write --repo-root . --publication PUBLICATION` and commit the receipt alone in the next commit.
   The command replays the prior reader against the exact recorded parent with every receipt
   ignored. Only on success does it write `<docs_dir>/adrs/migrations/receipts/ID.json`. It
   refuses, and writes nothing, on any refusal or when a receipt with other bytes exists.
   Activation never writes the receipt, and `publication-stage` refuses a receipt path.

## Replay receipts

A receipt replaces one step of every authority read: running the parent commit's own
approval reader in a clean clone of that parent. The receipt binds, by hash, the
publication (id, path, sha256, introducing commit), the parent commit, the approval and
package, and the reader (its source, a fixed identifier and the sha256 of the script bytes
that ran). The result field admits `approved` only; no refusal is ever recorded. Receipt
bytes are deterministic. They carry no timestamp, host path, interpreter version or
environment value.

A read trusts a receipt only when it is committed, unedited since its introducing commit,
and introduced strictly after the publication commit. A trusted receipt with every binding
equal skips the reader run and nothing else. The clean clone, the installed-support checks,
the current reader's validation of the approval and the standing of the parent tree still
run on every read that reaches them. A read that finds no receipt, or one that is new or
changed in the tree being read, replays as before, and the prior reader's refusal refuses.
A receipt with any unequal binding, one introduced at or before its publication commit, or
an unreadable, malformed, symlinked, oversized or non-regular receipt file refuses. Deleting
a receipt changes no verdict wherever the prior reader still runs.

A receipt is not approval evidence. It records no approval, owner instruction or council
verdict and cannot create or alter one. A read that trusts a receipt does not observe an
environment-only failure of the prior reader, such as an interpreter or library that no
longer runs the old code. That failure now surfaces when a receipt is written or verified.
For an installed-support receipt, the installed reader's imports outside the pinned
installed inventory, including the receipt reader itself, are unbound in the same way as
the environment. Installed-support records do not pin the receipt reader.

Verify receipts with `migration-receipt.py verify --repo-root . (--since COMMIT | --all)`.
Each receipt in scope is replayed against its publication with every receipt ignored. With
`--since`, the scope is every receipt added or changed since COMMIT. COMMIT must be a full
commit that is an ancestor of HEAD; anything else exits 2 and never narrows the scope.
Exit 0 is clean, 1 reports findings as JSON (an invalid, orphaned, untrusted or mismatched
receipt, or a refused replay), and 2 reports an environment or usage error.

To recover from a stale or mismatched receipt, delete it in a reviewed commit, so reads fall
back to the replay. Then run `migration-receipt.py write` again and commit the new receipt
alone.

`queue-page --path QUEUE --size 5 --offset 0` presents without modifying state.
`evidence --path SOURCE` renders bounded redacted fenced data. These read operations
change no approvals. Unknown prospective formats refuse rather than falling back to
historical interpretation. Historical `.application.json` publications retain their
original proof, authorizing/replacement bindings and publication references.
