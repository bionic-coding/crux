# audit-docs — the `--migrate` schema-ladder mode (reference)

Read this only when running `audit-docs --migrate` (the recovery path when a
plain audit reports CHK-SCHEMA-1 BROKEN). The normal full audit never needs it.

## The `--migrate` mode

`audit-docs --migrate` is the **schema-version-ladder** that brings a `docs/` tree up to the `schema_version` this plugin supports, then runs the normal full audit as verification. It is the documented recovery path when a plain audit reports `CHK-SCHEMA-1` BROKEN ("needs migration"), and the recovery path the install-time refuse-to-operate guard points users to.

The ladder runs the steps for each version below the supported version, in order, until the tree reaches `schema_version == "5"`. Implemented rungs: **2→3**, **3→4**, and **4→5**. A tree already at `"5"` is a no-op (verify only); a tree at a version with no ladder rung (e.g. an unrecognized future value) STOPs with a clear message rather than guessing.

**Rung 4→5 (unify the invariants concern; relocate a conventionally-located tree):** delegated to the vendored script — **do not reimplement it here**:

```bash
python3 "${CRUX_PLUGIN_ROOT}/scripts/migrate-tree.py" --repo-root . --dry-run   # report only
python3 "${CRUX_PLUGIN_ROOT}/scripts/migrate-tree.py" --repo-root .            # perform
```

The rung also merges (never overwrites) the repo config into `.bionic.yml`, preserving `artifact_prefix`. Exit codes follow the shared convention: `0` clean, `1` refusal with JSON on stdout, `2` capability error on stderr. Run `--dry-run` first and show the user its `source` / `destination` / `form` before performing the migration.

Two forms, chosen by the script from the resolved layout:

- **default** — a tree at `docs/` merges into `bionic/` at the repo root, and the invariants check suite folds into `<docs_dir>/invariants/checks/`.
- **custom** — a tree at a configured `docs_dir` (`.bionic.yml` or legacy `.crux`) **stays where it is**; only the root-level invariants suite merges into it. A relocated tree is often deliberately placed and frequently gitignored, so relocating it would change the repository's privacy posture — a schema migration is not entitled to do that.

The script resolves the source through the repo's own config, so it finds a relocated tree without help. `--docs-dir <path>` is the escape hatch for a layout no config declares. It fails closed on two valid trees with no marker, on a config that names a third location, and on any collision it did not create; it is resumable after a crash (a `.migrating` marker records the source inventory, and `manifest.yml` moves last so an interrupted run still resolves to the source). `--abandon` clears a stale marker.

**Rung 3→4 (add the invariants concern, per `docs/CLAUDE.md` §15):** (1) bump `schema_version` to `"4"`; (2) **opt-in enablement** — add `invariants` to `concerns_enabled` only when the `bionic/` layout is present or the user confirms; otherwise the concern is available-but-disabled and the tree still bumps to `"4"` (an existing repo with no `bionic/` degrades gracefully — no unreconciled suite to mistreat); (3) when enabled, create the ledger dir `<docs_dir>/invariants/` (+ its `index.md`) and the check suite `<tree>/invariants/checks/` (the v4 peer root; folded into the tree by rung 4→5) (+ its reconciliation manifest, empty entry list); (4) **idempotent** (re-running once at `"4"` is a no-op) and **fail-closed** (any partial/ambiguous state aborts with the error, never a half-migrated tree). No pin data is invented — migration creates empty surfaces; `recover-invariants` populates them later under the human-ratify gate.

**CLI / exit contract (locked):**
- **Idempotent and safe to re-run.** Every step below is individually guarded so a second run is a clean no-op. When no work remains the mode exits **0** with `already at schema 3`.
- **Confirmation.** Outside an authorized cycle/run, confirm the destructive moves (the `git mv`/`mv` relocations + the `research/new/` removal) before executing them. Inside an authorized `run-promptbook`/`dev-cycle` run, the plan is the authorization — proceed without pausing (see `docs/CLAUDE.md` §11 "Run execution autonomy"; in-repo file moves are internal and reversible, NOT an irreversible/outward-facing action).
- **Exit codes.** Non-zero exit **only** on a STOP condition (e.g. step 4 cannot empty `docs/research/new/`). A successful migration, a no-op re-run, and a clean verifying audit all exit 0. File moves are reported to the user.
- **Reversibility.** Every action is a `git mv`/`mv` (recoverable) or an additive write. `--migrate` NEVER runs `rm -rf`, NEVER overwrites a file, and NEVER touches `docs/research/raw/` (immutable captures).

### The 2→3 ladder step

Run these steps in order. Each is guarded so re-running is a clean no-op.

1. **Already migrated?** Read `docs/manifest.yml` `schema_version` with a real YAML parse (`python3 -c 'import yaml; ...'`). If it is already `"3"` → **no-op**: skip steps 2–6, run the normal full audit (the pipeline above) as verification, report `already at schema 3`, and exit 0. (If it is neither `"2"` nor `"3"`, STOP — there is no ladder rung for that value; surface "tree schema is newer/older than this plugin's 2→3 ladder supports; align plugin versions first.")

2. **Create `docs/inbox/`.** If `docs/inbox/` does not exist, create it with a `.gitkeep` placeholder. If it already exists, leave it (and its `.gitkeep`) untouched. Never overwrite an existing `.gitkeep`.

3. **Relocate `docs/research/new/` contents → `docs/inbox/`.** Only if `docs/research/new/` exists. For every entry in `docs/research/new/` that is **not** `.gitkeep`:
   - Compute the destination **basename-only**: `docs/inbox/<basename>`. **Path confinement** — if the source entry's name, when normalized, escapes its directory (e.g. a `../`-bearing name), **reject/sanitize it and never pass it to `mv`** (the destination MUST stay confined to the literal `docs/inbox/` subtree).
   - **Collision handling:** if `docs/inbox/<basename>` already exists, append a **monotonic suffix `-2`, `-3`, …** before the file extension (`report.md` → `report-2.md`, then `report-3.md`), probing upward until a free name is found. **NEVER overwrite** an existing inbox file.
   - Move with `git mv -- "<src>" "<dst>"`; if that fails (e.g. file not tracked, or not a git repo), fall back to `mv -- "<src>" "<dst>"`. **Quote both paths and use the `--` terminator** so a basename containing spaces or a leading dash cannot be mis-parsed as a flag. (For an extension-less name or a dotfile, the collision suffix in the previous step is appended at the end of the whole name.)
   - **NEVER touch `docs/research/raw/`** — it is not under `research/new/` and is immutable regardless.

4. **Remove the emptied `docs/research/new/`.** After step 3, `docs/research/new/` should contain at most a `.gitkeep`. Remove the directory **only once it is empty of non-`.gitkeep` content** (remove the `.gitkeep` first if present, then the now-empty dir; `git rm`/`rmdir`, never `rm -rf`). If any non-`.gitkeep` entry remains (e.g. a `../`-bearing name that was rejected in step 3, or an unmovable file), **STOP** and surface the residual paths to the user with a non-zero exit — do not delete the directory and do not proceed to the schema bump. (A clean re-run after the user resolves the residue completes the migration.)

5. **Bump `schema_version` `"2"` → `"3"`.** Edit `docs/manifest.yml` to set `schema_version: "3"` (a **quoted string** — the quoting is deliberate; preserve it). This is the single authoritative value in the tree; do not touch any prose copies (those live in `${CRUX_PLUGIN_ROOT}/templates/` and `init-docs`, not in a target tree's `manifest.yml`).

6. **Log the migration.** Append a new entry to the **top** of `docs/log.md` (newest-first):
   ```
   ## [YYYY-MM-DD] schema | migrate docs schema 2→3 (research/new → inbox)
   ```
   Body (terse, 1–5 lines): the count of items relocated into `docs/inbox/`, any collision-renamed targets, and a note that `docs/research/new/` was removed. The `schema` op is already in the `docs/CLAUDE.md` §6 enum — **no enum change** is needed.

7. **Verify.** Run the normal full audit (the pipeline above, steps 1–6) as migration verification. With the tree now at `"3"`, CHK-SCHEMA-1 passes, CHK-INBOX-1 passes (inbox exists), CHK-INBOX-2 passes (`research/new/` is gone), and CHK-INBOX-3 reports a WARNING with the count of any relocated items now pending in `docs/inbox/`. Report the audit result alongside the migration summary.

### `--migrate` red flags

- About to `rm -rf docs/research/new/` because step 3 "should have emptied it." **NEVER.** Step 4 removes the directory only once it holds no non-`.gitkeep` content; any residue is a STOP, not a force-delete.
- About to overwrite a same-named file in `docs/inbox/` during the relocation. **NEVER.** Append the monotonic `-2`/`-3` suffix instead.
- About to `mv` a source whose name contains `../` or otherwise escapes `docs/research/new/`. **NEVER.** Reject/sanitize it; the destination must be confined to `docs/inbox/`.
- About to touch anything under `docs/research/raw/`. **NEVER** — raw captures are immutable and are not part of the migration.
- About to bump `schema_version` before steps 2–4 succeeded. The bump is the LAST mutation before verification; if any earlier step STOPped, do not bump.
- About to write `schema_version: 3` (unquoted). It is a **quoted string** `"3"` — preserve the discipline.
