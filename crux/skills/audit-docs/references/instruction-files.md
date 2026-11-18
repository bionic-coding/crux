---
title: Repository instruction files
read_when: Discovering or migrating repository instruction files (`AGENTS.md`, `CLAUDE.md`)
sections:
  - "§18"
---

# Repository instruction files

A task reference of the documentation tree's operational schema, `<docs_dir>/AGENTS.md`. Read it only when its task applies. Section numbers keep their `<docs_dir>/AGENTS.md` meaning: a citation of a section held here, such as `docs/AGENTS.md §18`, resolves to this file.

## 18. Repository instruction files

`AGENTS.md` is the canonical instruction file at every managed instruction scope:
the repository root, the configured documentation-tree root, repo-controlled nested
project scopes, and `init-docs` output. A managed scope carries no committed
`CLAUDE.md` sibling.[^instr-canonical] This section is the single source of truth for
the concern; `audit-docs` (the CHK-INSTR rules), `migrate-instructions.py`, and
`instruction_migration.py` reference it by name and restate none of it.

### 18.1 Two sets, and they are not the same set

| set | what it holds | what may happen to it |
|---|---|---|
| **mutation** | the entries and index paths of each touched scope in THIS checkout, minus the exclusions below | renamed into `AGENTS.md`, set aside, or left where it is; `AGENTS.md` created |
| **suppression** | every `CLAUDE.md`, `.claude/CLAUDE.md` and `CLAUDE.local.md` under the checkout, tracked or not | reported only, never written |

A *family member* is an entry or index path whose name, lowercased, is `claude.md` (the
`CLAUDE.md` family) or `agents.md` (the `AGENTS.md` family). `CLAUDE.local.md` and a
`CLAUDE.md` under `.claude/` belong to neither. A member is *managed* when git tracks it
and no exclusion below claims it. A *touched scope* is a directory whose listing and
index, read together, hold at least one managed member.

Discovery lists each touched scope's directory, reads its index paths, and matches names
by Unicode lowercasing. It never decides presence by probing a path.[^instr-discovery]
The checkout is resolved from an explicit repository root and never from the tool's own
path. A vendored dependency cache and a linked worktree fall outside the mutation set by
construction, because neither holds a file tracked here. Migration mutates an untracked
entry only when it is a losing `AGENTS.md`-family entry or an entry a migration run created.

The suppression set is wider **on purpose**, and this is the clause most easily
lost.[^instr-suppression] Under the host's default mode a Claude-named file anywhere
from the repository root to the working directory suppresses `AGENTS.md` entirely, so
a single leftover file silences the canonical one rather than competing with it. Some
of those files are private and uncommitted, and crux must not touch them. Reporting a
suppressor and failing a compatibility check on one are therefore **two different
acts**: every suppressor under the checkout is reported, and only one on the chain
from the root to the working directory, under a mode in which it suppresses, fails
the check.

The suppression scan skips any directory **below the root** carrying its own `.git`
entry, which is what a nested or linked checkout is. The qualifier is load-bearing:
the root carries one too, and a scan that skipped it would scan nothing. The rule
cannot key on the ignore file instead, because a `.claude/CLAUDE.md` and a linked
worktree commonly share one ignore rule while only the worktree is a separate checkout.

### 18.2 Exclusions, declared rather than recognised

Never mutated, each reported with a named disposition: `CLAUDE.local.md`; a `CLAUDE.md`
under a `.claude/` directory, **even when tracked**, because no host is known to load
`.claude/AGENTS.md` and renaming it would silence it while the receipt recorded a clean
migration; templates; symlinks, which are never followed; and every path named by the
`instruction_migration_denylist` key in the tree's configuration — the one declaration
surface for a test fixture or a generated runtime copy. `init-docs` creates that key and
defaults it to empty. An absent key, and an absent configuration, are both an empty
denylist rather than an error, so a project audited before initialization still reports.

### 18.3 CLAUDE.md wins a scope holding both families

The *winner* is the `CLAUDE.md`-family entry no exclusion claims, tracked or not. Every
`AGENTS.md`-family entry beside it is a *loser*. Where a touched scope holds a winner and
a loser, the result is one entry spelled exactly `AGENTS.md`. Its bytes are the winner's
working-tree bytes with each *import line* replaced by the loser's bytes. An import line
is a line whose bytes, without the line ending, are exactly `@`, an optional `./`, and the
loser's name, or on a case-folding volume a name that lowercases to it. A line inside a
fenced code block is not one. The replacement takes the line and its line ending, appends
that line ending only where the loser's bytes lack a final one, and does not recurse.
Migration merges, deduplicates and decodes nothing else.[^instr-winner] The report names
each import line it replaced. It also names every other line importing a family name,
with the next step "replace that line with the instructions you meant it to load".

A scope holding one family keeps its behaviour: a lone `CLAUDE.md` becomes `AGENTS.md`
with its bytes unchanged, and a lone variant takes the exact `AGENTS.md` spelling.

A loser whose bytes equal the result becomes the result, respelled `AGENTS.md` where
needed. Every other loser is **set aside**, whether tracked, dirty, untracked or
ignored.[^instr-set-aside] A set-aside renames the entry within its own directory,
without replacing any entry, to the first unused name of this sequence:

```text
<name>.crux-set-aside-<hash>
<name>.crux-set-aside-<hash>-2
<name>.crux-set-aside-<hash>-3
```

`<name>` is the entry's own name. `<hash>` is the first 12 lowercase hexadecimal digits of
the SHA-256 of the entry's bytes. A name is used when an entry of that directory holds it
or a name that lowercases to it. A candidate the volume folds onto an entry some other
way stops the scope at its no-replace rename. No name in the sequence ends in `.md` or
lowercases to a
family name, and none of Claude Code, Codex and OpenCode loads one by default. Migration
neither tracks nor ignores a set-aside, and the report states whether git ignores it.
Every run, dry runs included, reports each set-aside it finds. A set-aside loser's
content stops loading until the user acts on the report, unless the winner imported it.

### 18.4 Refusals

A touched scope is refused when one of these conditions holds. A refused scope changes
nothing and blocks no other scope. The report names the blocking entry and its next
step.[^instr-refusal]

| condition | next step |
|---|---|
| a loser is named by the denylist, or is a template | remove the denylist entry or move the file yourself, then migrate |
| a loser is a symlink (the report names its target) | replace it with a regular file or remove the link |
| a loser is not a regular file, or is unreadable | make it a readable regular file or move it out of the directory |
| the winner is not a readable regular file | make it a readable regular file or move it out of the directory |
| a loser is ignored, and git would not ignore its set-aside name | move your private file to a name that does not exist yet, that git ignores, and that no harness loads by default |
| one family holds two spellings, across the listing and the index | move one spelling to a name that does not exist yet and no harness loads by default, saving any index-only version first |
| a family member's index entry is unmerged, skip-worktree or assume-unchanged | save each index-only stage, `git show :<stage>:<path>`, under its own new name that does not exist yet, then finish that merge or clear that flag, then migrate |
| the volume cannot establish identity, or offers no atomic no-replace create and rename | migrate from a clone on a volume that offers them |
| the scope directory is reached through a symlink | replace the link with a real directory or remove the link, then migrate |

Every next step, followed literally, loses no byte and publishes nothing.

### 18.5 Steps, staging, and the honest limit

No migration step replaces an existing entry, case-fold aliases included, or removes any
entry except a temporary one the run created. Each winner and loser is renamed into
`AGENTS.md`, set aside, or left where it is.[^instr-steps] The whole plan validates before
any mutation, and it binds to the sources observed at planning. Immediately before each
step, a source whose identity or bytes changed stops that scope. The steps run in order:
each loser to set aside is set aside and verified; `AGENTS.md` is created, the winner
renamed in, or an equal-bytes loser kept or respelled as it, and its bytes verified; then the winner step
runs. A temporary entry an interrupted run left is reported and never removed.

Migration stages nothing in a scope whose result carries bytes read from an untracked or
ignored entry, where the exact path `AGENTS.md` is untracked and ignored, or where a
family member's index entry holds a blob that neither HEAD nor any working-tree entry
holds.[^instr-staging] In such a scope the winner stays where it is and `AGENTS.md` is
created beside it. The report says that committing `AGENTS.md` publishes any untracked or
ignored bytes it holds. After a scope that stages, the index holds the result at the exact
path `AGENTS.md`, no other `AGENTS.md`-family path of that scope, and no winner path. A
tracked winner whose bytes differ from the result is set aside as a loser is.

A scope that stages nothing, or stops, is a finding (exit 1). So is a scope whose index
holds a family path its directory no longer lists and the plan does not remove. The
report gives a next step that saves that blob first. Before a scope's first step, the
receipt records the hash and index path of a tracked winner and of the loser input. A
rerun reads that record, so it reaches the state an uninterrupted run reaches, apart
from a temporary entry an interrupted run left, and a second run on a completed tree
changes nothing. The
receipt records each set-aside with its hash and git state, each inlined import line, each
family member's index blob hash, each index change, and each refusal. **No durability
across power loss is claimed** for the written `AGENTS.md`, and no multi-file filesystem
atomicity is claimed. Every winner and loser byte stays in its entry, because no step
unlinks one.

A migration writes one `schema` op, never one entry per file.

[^instr-canonical]: rule:one-canonical-agents-file
[^instr-discovery]: rule:discovery-reads-entries-in-tracked-scopes
[^instr-suppression]: rule:one-canonical-agents-file
[^instr-winner]: rule:claude-family-wins-a-dual-family-scope
[^instr-set-aside]: rule:losing-agents-file-is-moved-aside-and-reported
[^instr-refusal]: rule:unsafe-scope-refuses-alone-with-a-next-step
[^instr-steps]: rule:migration-writes-no-unplanned-entry
[^instr-staging]: rule:staging-publishes-no-untracked-bytes-and-drops-no-index-blob
