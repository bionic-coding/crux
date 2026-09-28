# Audit Docs — recover an older tree

Read this when a tree schema is not the current supported value, or when an
in-flight `.migrating` marker exists. The current distribution does not carry
its old tree-schema ladder. It preserves the tree and reports the mismatch.

## Recover schemas 2, 3, and 4

Use the public crux `v3.23.2` release, annotated tag
`c1298c4a9229ed41ae7017c25321d27e5b3f6e4d`, which resolves to commit
`08ee30ec2f1d1b4b0ce970f2e1582bb4f83cd20d`. Verify that mapping when
acquiring the release. Use one plugin version at a time and work on a copy or
backup of the project. The tagged release carries `audit-docs --migrate` and
the old 2→3→4→5 ladder. Run its dry run, apply each rung in order, and validate
the resulting schema-5 tree before loading the current distribution. The old
release's audit instructions and CLI own the actual migration procedure.

If a `.migrating` marker remains, do not clear or rewrite it with the current
version. On the copy, use the tagged release to inspect and resume the partial
4→5 move, or invoke its `migrate-tree.py --abandon` procedure only after the
old tool confirms the tree is coherent. An invalid marker or two trees without
a valid recorded source are ambiguous. Stop and inspect the originals; do not
choose a tree by directory name.

This tagged ladder is a supported route only for tree schemas 2, 3, and 4.
A missing, earlier, newer, or unrecognized `schema_version` is incompatible;
inspect the actual tree and matching release. Do not claim the tagged ladder
can convert it, reinitialize it, or bump its manifest by hand.

Promptbook format conversion is separate from the tree ladder. In the tagged
release, finish an active Markdown run only when its remaining prompts can
truthfully be completed. Archive it, then convert its book before its paired
run, preserving originals. An already archived eligible run can also be
converted. Validate each YAML book and run, including their content-hash
binding, before returning to the current release. The tagged release does not
provide deliberate Markdown abandonment. If a run cannot finish, preserve its
original bytes as stranded, readable history; neither release provides a
verified close-and-convert path for that state. New YAML work can continue
beside that record. Historical Markdown is not executable by the current
release.

## The instruction-file migration (independent of tree schema)

The current `audit-docs --migrate` procedure migrates repository instruction
files onto the canonical `AGENTS.md`. It is not a tree-schema rung: it has no
`schema_version`, and a schema-5 tree can still owe this migration. If the tree
needs the old schema ladder, finish that work on the tagged release first.

Delegated to the vendored script — **do not reimplement discovery or the merge here**:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/migrate-instructions.py" --repo-root . --dry-run   # report only
uv run "${CRUX_PLUGIN_ROOT}/scripts/migrate-instructions.py" --repo-root . --migrate   # perform
```

Exit codes follow the shared convention: `0` clean, `1` findings or refusal with JSON on
stdout, `2` capability error on stderr. Run `--dry-run` first and show the user its
`actions`, `suppressors` and `validation_errors` before performing the migration.

### The two sets, which are not the same set

| | what it holds | what may happen to it |
|---|---|---|
| **mutation** | the tracked files of THIS checkout | renamed, collapsed, or merged |
| **suppression** | every `CLAUDE.md`, `.claude/CLAUDE.md` and `CLAUDE.local.md` under the checkout, tracked or not | reported only, never written |

The mutation set is bounded by `git ls-files`, so a vendored dependency cache and a
linked worktree fall outside it by construction rather than by an enumerated exclusion.
The suppression set is wider on purpose: a file crux must not touch can still silence
the canonical file, and an untouchable suppressor that nobody reports is the failure
this whole concern exists to prevent.

### What the script does, and what it refuses to infer

- A lone managed `CLAUDE.md` becomes `AGENTS.md` with its bytes unchanged.
- A case variant normalizes to the exact `AGENTS.md` spelling, through a staged
  case-only rename where the filesystem requires one.
- Byte-identical siblings collapse. Differing siblings merge.
- **Deduplication matches on (heading path, bytes), never bytes alone.** Two identical
  blocks under different parents are two blocks. A placement that would change a
  block's ancestry escalates rather than being taken.
- The tool detects an identical block, a colliding heading path with differing bodies,
  and a reparenting. It **never infers a contradiction** — that judgment is a human
  step over the full preview. A reviewed JSON resolution copies `source_hashes` from
  the preview receipt and supplies each scope, heading path and replacement text;
  `uv run "${CRUX_PLUGIN_ROOT}/scripts/migrate-instructions.py" --repo-root . --migrate --resolution <path>` refuses it if a source has
  changed since the preview.
- Excluded from mutation and reported with a named disposition: `CLAUDE.local.md`, a
  `CLAUDE.md` under `.claude/`, templates, symlinks, untracked files, and every path
  the `instruction_migration_denylist` config key names. An absent key and an absent
  configuration are both an empty denylist rather than an error.

### Recovery and the honest limit

The whole plan validates before any mutation. Staging is per file: a temporary file
beside the target, then a rename. A crash leaves committed files committed and the rest
untouched, and a rerun converges — after a partial run `git ls-files` still lists a path
that is already gone, and discovery steps over it rather than failing on it.

**No multi-file filesystem atomicity is claimed**, and the receipt says so in as many
words. The receipt records each source's hash and disposition, and pairs each merged
block's source heading path with its resulting one so a reparenting cannot balance.

### Instruction-migration red flags

- About to delete a `CLAUDE.local.md` because it suppresses the canonical file.
  **NEVER.** It is private and untracked. Report it with its remedy.
- About to rename a tracked `.claude/CLAUDE.md` to `.claude/AGENTS.md`. **NEVER.** No
  host is known to load that path, so the rename would silence it while the receipt
  recorded a clean migration.
- About to resolve a heading collision by picking the longer body, the newer file, or
  the one that "looks canonical." **NEVER.** Flag it and leave both sources on disk.
- About to widen discovery past `git ls-files` to catch a file you can see. That file
  belongs to another checkout or is deliberately untracked; report it instead.
- About to log one entry per migrated file. **One `schema` op per migration.**
