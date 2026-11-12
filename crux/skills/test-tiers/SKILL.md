---
name: test-tiers
description: "Label every test with one tier (dev, release or ephemeral) in a per-root test-tiers.json manifest, check the labels, and list a tier for any language's test runner."
metadata:
  tags: "testing, test-tiers, release, evidence, labelling"
  bundles: "crux-docs"
  risk_level: "medium"
  requires_access: "write-tree"
  triggers: "label the tests | label this test | check the test tiers | check the test labels | list the release tier | which tests are release tests | adopt test tiers | set up test tiers | mark this test ephemeral"
  routing_note: "Writes test-tiers.json manifests and runs the shipped `test-tiers.py check` and `list`; never deletes a test and never narrows a cycle gate. Running the tests themselves stays with the project's runner and the cycle's test coordinator."
---

# Test Tiers

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, OpenCode, and OMP (Oh My Pi). This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex, OpenCode, and OMP, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory (in OMP `bash`, `skill://<name>` resolves to the skill directory). In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, `.opencode/skills` in OpenCode (which also reads the singular `.opencode/skill`), and `.omp/skills` in OMP. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`; OMP uses `task`, `read`, `edit`, `write`, `bash`, `grep`, `glob`, `find`, `todo`, and `web_search` (where `read` also handles URLs and `skill://` URIs). Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode, `install-omp-agents` in OMP. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode and OMP use the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder` (in OMP, `scout` may also be used for reconnaissance alongside `wayfinder`). If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->

A project labels each test with exactly one of three tiers. The labels live in data,
one `test-tiers.json` manifest per test root, so test source stays untouched and any
language can use them. The shipped reader `crux/scripts/test_tiers.py` and its command
`crux/scripts/test-tiers.py` use the Python standard library only, so they run in any
project without the crux environment.

## The three tiers

- **`dev`**: tests for the focused checks of what a change touches. Every test that is
  neither release nor ephemeral is dev.
- **`release`**: a chosen subset, never every test, that covers each system area the
  project declares. Release verification runs it.
- **`ephemeral`**: a test that verified a behaviour once and carries no long-term value,
  such as a completed migration or a pinned historical record. Its label carries a
  reason and an expiry date or a retirement condition. The test is labelled, not deleted.

Every test unit resolves to exactly one tier through a label.[^one-tier] A change that
adds a test file or test method labels it in the same change.[^same-change] A test added
under an existing file or class label inherits that label; its author confirms or
overrides it in the same change. The release tier is a non-empty proper subset of all
test units.[^subset] Every declared system area has at least one release-tier test
unit.[^areas] An ephemeral label carries a reason[^reason] and an expiry date or a
retirement condition.[^end] An ephemeral test leaves only through an explicit change
that names it.[^leave]

## Where each tier runs

Tiers narrow development loops only: a unit's focused checks, fix-step reruns and
reviewer probes. No gate's test selection narrows by tier.[^gates] A unit gate still runs
every test the change could reach.

- **Cycle completion.** Completing a cycle of any type except release needs current
  passing evidence for every test of every tier.[^complete] A tier-filtered receipt
  never counts as an all-tests pass. A release cycle completes on its fixed step list.
- **Verify.** The tier check is a required check at Verify, or Test on older records,
  of every cycle type that has one.[^verify]
- **Release verification.** It establishes passing evidence for every release-tier
  test[^release] and runs the tier check.[^release-check] Matching evidence is reused;
  otherwise only the release tier executes.
- **Pull requests.** Merging needs every test to pass on the head.[^merge] Pull-request
  CI runs every test its environment can run[^ci-all] and the tier check.[^ci-check] A
  test CI cannot run needs recorded passing evidence for the head before the
  merge.[^unrunnable] A project with no pull-request CI therefore records evidence for
  every test before a merge.

A project adopts tiers only when it has at least two test units[^two] and declares at
least one system area.[^declare]

## The manifest

Each test root holds one file named `test-tiers.json`. The schema
`crux/schemas/test-tiers.schema.json` documents its shape; the reader is authoritative.

```json
{
  "format": "crux.test-tiers",
  "version": 1,
  "kind": "python-unittest",
  "pattern": "test*.py",
  "areas": {"billing": "Invoices are created, charged and refunded end to end"},
  "files": {
    "test_invoice.py": {
      "tier": "dev",
      "overrides": {
        "InvoiceFlowTests": {"tier": "release", "area": "billing"},
        "InvoiceFlowTests.test_2024_rate_migration": {
          "tier": "ephemeral",
          "reason": "Proved the one-time 2024 rate migration",
          "retire_when": "The 2024 rate table is removed"
        }
      }
    },
    "test_refund.py": {"tier": "release", "area": "billing"}
  }
}
```

- `format` is `crux.test-tiers` and `version` is `1`.
- `kind` is `python-unittest` or `file-glob`. A `python-unittest` root labels files,
  classes and methods. A `file-glob` root labels files only, for a runner that selects
  whole files, such as a TypeScript or Go test directory.
- `pattern` is the root's non-recursive file glob, such as `test*.py` or `*.test.ts`.
- `areas` maps an area id to a one-line description of a system area.
- `files` maps each bare file name that matches `pattern` to an entry. A key holds no
  path separator and no `..`.
- `overrides`, on `python-unittest` entries only, are keyed `ClassName` or
  `ClassName.test_method`. A method override wins over a class override, which wins
  over the file entry.
- A `release` label carries `area`, naming an id in its own manifest's `areas`. An
  area id declared in two manifests carries the same description in both.
- An `ephemeral` label carries `reason`, and `expires` (`YYYY-MM-DD`), `retire_when`
  (text) or both.
- A `dev` label carries none of those fields; a `release` label carries only `area`;
  an `ephemeral` label carries no `area`.

Name a documentation example `test-tiers.example.json`, never `test-tiers.json`, so the
check does not read it as a manifest. The check finds manifests as git-tracked files of
that exact name, or by a filesystem walk outside git that skips `.git`.

## The check

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/test-tiers.py" check --repo-root . --expect-root tests
```

The check prints JSON with `configured`, `roots`, the counts per tier and root, the
counting rule, `findings` (each with `code`, `path` and `detail`) and `expired`. It exits
0 when clean, 1 on findings and 2 on an environment error. It fails on:[^check]

- **unlabelled**: a file directly under a root that matches its pattern and has no
  entry. A matching file in a discoverable subdirectory fails as `unlabelled-nested`.
- **doubly-labelled**: a duplicate JSON key, a file covered by two manifests, or an
  override that repeats what it would inherit.
- **stale**: an entry naming an absent file, or an override naming a class or method
  the file does not define.
- **subset**: zero release units, or zero units outside release, across all manifests.
- **areas**: a release label naming an undeclared area, a declared area with no
  release unit, no declared area at all, or one area id with two descriptions.
- **ephemeral**: a missing reason, or neither `expires` nor `retire_when`.
- **fields**: a field the tier does not allow, an unknown key or an invalid date.

An ephemeral label whose `expires` date has passed is listed under `expired` as a
warning and never fails the check.[^expired] Elapsed time alone never turns it red.

`--expect-root ROOT`, repeatable, names a root that must hold a manifest. A missing one
fails as `missing-root`; in a git checkout, an untracked one fails as `untracked-root`.
Without `--expect-root`, a project with no manifest exits 0 with `configured: false`.
`--require-release-units ROOT` fails a named root that holds no release unit or has no
checked manifest.

`check --root ROOT` runs only the per-root rules. `check --shard PATH --root ROOT`
checks a partial manifest without the unlabelled rules, and `merge --root ROOT --shard
PATH...` writes the union of shards to `ROOT/test-tiers.json`. Merge refuses a file two
shards name, an area with two descriptions, and shards whose format, version, kind or
pattern differ. Shards let several classifiers label one root in parallel.

Units are counted from the source: one per `test*` method of each class a Python file
defines (an AST walk), and one per file for `file-glob`. Two limits follow. A class
imported from another module is absent from the file's AST, so only the file entry
labels it there. A method a local class inherits takes the file entry or a class
override, never a method override. The independent review of the labels is the
semantic coverage check; the counts drive the subset and area rules.

## The runner contract

Any runner can consume a tier through `list`:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/test-tiers.py" list --root tests --tier release
uv run "${CRUX_PLUGIN_ROOT}/scripts/test-tiers.py" list --root tests --tier dev --tier release --ids
```

`list` prints one line per file that holds at least one unit of a selected tier. With
`--ids` it prints `module.Class.test_method` selection ids instead. It checks the root's
per-root rules first and exits 2 on a finding or on a missing or invalid manifest, so a
runner never selects from a broken manifest. A runner that selects by tier fails closed
when the manifest is missing or invalid, when the selection is empty, and when a
discovered test has no entry. It always keeps a test that failed to load, so an import
error still runs and fails. In the Crux development repository,
`parallel_suite.py --tier` and `related-tests.py --tier` implement this contract.

## Adopt tiers in a project

1. Commit a `test-tiers.json` in each test root, with at least one area and a label for
   every test file.
2. Classify with the rubric below. Record each area's release tests.
3. Run the check until it exits 0, then declare it as a cycle check:
   `uv run python3 "${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py" declare --repo-root .
   --preset test-tiers --check-id CYC-ID-test-tiers --output check.json`. The preset
   refuses when the project holds no manifest. It records the present roots as
   `--expect-root` arguments. Its inputs are those of `whole-tree` plus each expected
   root directory, so a new untracked test file changes them.
4. Add the check and every runnable test to pull-request CI. Point the release
   verification at the release tier through `list`.
5. Have someone who classified nothing review every release and ephemeral label and a
   seeded sample of the dev labels.

## Rubric

- **release**: its failure would show a shipped system area broken end to end, or a
  release-path or safety guard regressed: a staging allowlist, a secret scan, path
  containment or an authorization refusal. A test the release path itself depends on is
  release. Every declared area gets at least one.
- **ephemeral**: it proved a one-time transition or a specific historical record, and
  protects no behaviour that can still regress: a completed migration, a pinned past
  record, a removed code path. Give it a reason and an end condition.
- **dev**: every other test.
- **Before any label**: check a new test against
  [What makes a test worth keeping](#what-makes-a-test-worth-keeping), and label only a
  test that passes it.

Declare one area per part of the system a release could break on its own. A single coarse area reduces the
coverage rule to "at least one release test".

## What makes a test worth keeping

A test is worth keeping when its failure would show that a behaviour a program, a user
or a release depends on has regressed, and no other kept test or gate would show the
same regression. A program here is code in the repository or a script the project
ships. A program parses content when it reads that specific content out of the text.
An agent is not a program. A program that copies, embeds or pattern-scans a whole file
parses none of its sentences.

A test fails the rule in any of four shapes:

- **Wording pin**: it asserts that a document people or agents read carries a phrase, a
  sentence or a heading. Such documents include an `AGENTS.md`, a skill, a role
  definition, a template and a guide. The test keeps its value in two cases only. In
  the first, a program parses the asserted content: frontmatter, trigger phrases,
  generated-region markers, or a table a program reads. In the second, the test checks
  an identifier the text names against the code that defines it: a command, flag,
  field, path, exit or refusal code, environment variable or operation name.
- **Removed-text guard**: it asserts that text already removed stays absent, and no
  program can write that text back.
- **Duplicate**: it asserts what another kept test or a drift gate already asserts
  about the same behaviour.
- **Host-dependent fixture**: its result depends on machine state the test does not
  set. That state is a git identity, the hostname, the home directory and the
  configuration files under it, an environment variable the test does not set, the
  locale, the time zone, the user id, the network, or a tool or tool version outside
  the project's declared prerequisites. The declared prerequisites are the project's
  stated toolchain and its supported interpreter versions. A declared tool is a
  prerequisite, not host state. A test that checks for state no fixture can set, and
  skips with a stated reason when that state is absent, does not fail this shape.

Apply one disposition to each test the rule reaches:

- Delete a test that fails the rule. The change names the coverage that remains, or
  states why none is needed.
- Label it ephemeral instead, with a reason and an end condition, when an explicit later
  change should retire it. A test already labelled ephemeral stays until its end
  condition is met.
- Keep a test whose only fault is a host-dependent fixture, and make its fixture set
  that state. When no fixture can set the state, such as the network, the user id or a
  tool outside the declared prerequisites, the test checks for the state and skips with
  a stated reason when it is absent.
- Keep a test that a live rule names as its mechanism.

The tier commands never delete a test; the change that applies the rule does. The
reviewer of a change applies the rule to every test the change adds.

[^one-tier]: rule:every-test-has-exactly-one-tier
[^same-change]: rule:new-tests-are-labelled-in-the-same-change
[^subset]: rule:release-tier-is-a-proper-subset
[^areas]: rule:release-tier-covers-every-declared-area
[^reason]: rule:ephemeral-labels-carry-a-reason
[^end]: rule:ephemeral-labels-carry-an-end-condition
[^leave]: rule:ephemeral-tests-leave-only-by-explicit-change
[^gates]: rule:tiers-never-narrow-a-cycle-gate
[^complete]: rule:completion-requires-every-tier
[^verify]: rule:tier-check-is-required-at-verify
[^release]: rule:release-verify-covers-the-release-tier
[^release-check]: rule:release-verify-runs-the-tier-check
[^merge]: rule:merge-requires-every-test-on-the-head
[^ci-all]: rule:pr-ci-runs-every-runnable-test
[^ci-check]: rule:pr-ci-runs-the-tier-check
[^unrunnable]: rule:unrunnable-ci-tests-need-recorded-evidence
[^two]: rule:adoption-needs-two-test-units
[^declare]: rule:adopting-project-declares-an-area
[^check]: rule:tier-check-fails-on-rule-violations
[^expired]: rule:expired-ephemeral-labels-only-warn
