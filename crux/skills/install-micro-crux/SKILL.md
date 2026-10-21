---
name: install-micro-crux
description: "Install or update the standalone micro-crux guide and its repository read instruction while preserving local edits."
metadata:
  tags: "documentation, installation, continuity"
  bundles: "crux-docs"
  risk_level: "medium"
  requires_access: "write-tree"
  triggers: "install micro-crux | add micro-crux to this project | update micro-crux | install the standalone crux guide"
---

# Install Micro-crux

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, OpenCode, and OMP (Oh My Pi). This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex, OpenCode, and OMP, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory (in OMP `bash`, `skill://<name>` resolves to the skill directory). In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, `.opencode/skills` in OpenCode (which also reads the singular `.opencode/skill`), and `.omp/skills` in OMP. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`; OMP uses `task`, `read`, `edit`, `write`, `bash`, `grep`, `glob`, `find`, `todo`, and `web_search` (where `read` also handles URLs and `skill://` URIs). Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode, `install-omp-agents` in OMP. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode and OMP use the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder` (in OMP, `scout` may also be used for reconnaissance alongside `wayfinder`). If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->

Use this skill when the user requests installation or an update of the
standalone project guide. Installation is opt-in. `init-docs` does not enable it.
The guide supports understanding, review, bounded authorized changes, and
manual maintenance of supported records without installed skills or roles.
It preserves the meaning of local policy, approval, evidence, and history.

## Install or inspect

Use the user's selected project root; otherwise use the current working
directory. Set `REPO_ROOT` to that absolute directory. Derive `CRUX_PLUGIN_ROOT`
from this selected skill's absolute path: the parent of its `skills/` directory.
An installed plugin supplies the payload; the project supplies the targets.

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/install-micro-crux.py" --repo-root "${REPO_ROOT}"
```

Add `--dry-run` when the user requests a preview. It reports the complete
intended change without writing. The actual invocation preflights again.
An authorized install needs no extra confirmation between its internal steps.

The installer resolves `.bionic.yml` through the canonical configuration reader.
It requires an existing tree at supported schema "5". A missing, ambiguous,
malformed, or unsupported tree refuses before enrollment. Explain the exact
error; do not silently initialize, migrate, or select a different tree.

It copies `box/micro-crux.md` byte-for-byte to root `micro-crux.md`. It adds an
explicit read instruction inside this owned root `AGENTS.md` region:

```markdown
<!-- BEGIN CRUX: micro-crux -->
Read `micro-crux.md` before reviewing or changing this project.
<!-- END CRUX: micro-crux -->
```

It preserves every existing instruction byte outside the region. Read the JSON
result. Report the target paths, whether anything changed, and any reach limitation.
The installer never rerenders consumer contracts or needs this development
repository's `tools/`, documentation tree, or plugin cache layout.

## Conflicts and reach

Exit `0` means installed, unchanged, or a valid preview. Exit `1` names a
preserved conflict. Exit `2` describes an environment failure, possibly after
partial installation. Do not claim success from file existence alone.

- A different unmanaged guide, a local guide edit, or a changed owned pointer
  remains intact. Report the path and the returned installed/actual/upstream
  digest differences. Have the user integrate the difference explicitly;
  there is no force overwrite.
- An identical unmanaged guide can be adopted only by exact bytes. Markers in
  `AGENTS.md` alone establish no ownership. Missing metadata with an existing
  region requires restoration of known metadata or explicit reconciliation.
- Case variants, multiple instruction spellings, symlinks, escaping paths,
  nonregular targets, and a declared instruction exclusion refuse before writes.
  State the named remedy and preserve every original entry.
- A root `CLAUDE.md` family member blocks the managed root instruction. Preserve
  it. Its owner can migrate instructions through the project's existing process
  or add an explicit instruction to read the standalone guide manually. Do not
  silently edit it or create a competing instruction file.
- `CLAUDE.local.md` and `.claude/CLAUDE.md` remain intact and are reported as
  possible suppressors. The pointer reaches harnesses that read root `AGENTS.md`.
  A harness reading only `CLAUDE.md` needs an owner-maintained explicit read
  instruction. Installation does not establish automatic inclusion there.

## Installation bookkeeping

The configured tree holds `.micro-crux-install.json`. This is ownership and
recovery data, never decision authority. Format version 1 has exactly:

| Field | Meaning |
|---|---|
| `format` | `crux.micro-crux-install` |
| `format_version` | Integer `1` |
| `docs_dir` | The configured project-relative tree path |
| `targets` | Exactly `guide: micro-crux.md`, `instructions: AGENTS.md` |
| `installed` | Null during first installation, otherwise the last committed installation identity |
| `pending` | Null after completion, otherwise the intended recoverable replacement |

`installed` has exactly `guide_sha256`, `pointer_sha256`, and `upstream`.
The first hashes all guide bytes; the second hashes only the delimited region,
including its final newline. `upstream` has exactly `source: box/micro-crux.md`
and `sha256`, equal to `guide_sha256`.

`pending` has exactly `upstream`, `guide_sha256`, `pointer_sha256`, `before`,
and `after`. Each of the latter mappings has exactly `guide` and `instructions`.
Those values hash whole target files; `before` can be null for an absent file.
All other digests are lowercase 64-character SHA-256 values. Neither metadata
nor a digest establishes user approval or independent execution.

An unchanged repeat writes nothing. An upstream update replaces only managed,
unchanged bytes. Instruction edits outside the owned region remain valid.
Unknown, malformed, or unsupported bookkeeping refuses instead of guessing
ownership. Do not manually clear metadata to force an update.

## Interruption recovery

The installer preflights every destination, then atomically writes pending
intent **before** replacing either target. It replaces the guide, replaces the
instruction file, then atomically finalizes metadata. Individual writes are
atomic; the installation across files is recoverable, not atomic.

Run one installer at a time. After interruption, rerun the same payload/version.
Recovery checks exact before/after target digests or the exact owned region.
It preserves outside instruction edits. A changed partial target or a different
upstream payload blocks recovery with a cause; preserve both the target and
pending intent for explicit reconciliation. Never infer that a target belongs
to the installer merely because a marker is present.

After the command returns, use its actual result. Report a retained pending
installation as incomplete, with the exact cause and next step. Do not describe
an installer invocation as an accepted decision, test execution, or completed
cycle operation.
