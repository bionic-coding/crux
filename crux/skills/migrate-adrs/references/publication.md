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

`queue-page --path QUEUE --size 5 --offset 0` presents without modifying state.
`evidence --path SOURCE` renders bounded redacted fenced data. These read operations
change no approvals. Unknown prospective formats refuse rather than falling back to
historical interpretation. Historical `.application.json` publications retain their
original proof, authorizing/replacement bindings and publication references.
