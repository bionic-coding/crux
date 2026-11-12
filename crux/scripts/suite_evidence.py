"""Registry and adapter of the reused suites and checks.

``release-preflight.py``, ``sync.sh``, ``tools/test-suite.py`` and ``tools/release.py`` read a suite's
declaration and requirement only from here, so the tester's run and a release run produce
interchangeable receipts. The registered checks are the main run (the checkout core suite and the
checkout tools suite) and, for each supported Python minor, the staged ``flagged`` and ``health``
checks. A receipt is a reuse candidate for a registered check only when its recorded declaration
equals the registered one.

Test tiers add three registered checks (IDR test-tiers, CYC-0105). Each checkout suite has a
release-tier declaration, ``checkout:unittest-release:<start>:<pattern>``, whose inputs equal the full
suite's and whose command adds ``--tier release``. ``checkout:test-tiers`` runs the shipped tier checker
over the five test roots. A release-tier receipt never stands in for a full suite at Build exit or at
completion; ``release_groups`` is the one reader of the per-suite rule that lets release verify accept
either the full or the release-tier declaration of one suite.

A check that is not registered, such as a cycle's focused check, validates against its own recorded
declaration. Its default requirement is the subject's locked project environment.

Scheduling and diagnostic destinations do not change test discovery. They are kept in the executed
command, while the canonical discovery command is shared. The broad input declaration includes
documentation because tests read it.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import sys
import time
import tomllib

from test_evidence import EvidenceError, execute, forge_log_preamble, lookup, normalize, read_receipts, storage

DEFAULT_PATTERN = "test*.py"
INPUTS = ["crux", "crux-mods", "tools", "opencode", "bionic", "public", "*.md",
          "*.sh", "pyproject.toml", "uv.lock", ".bionic.yml", ".claude-plugin",
          ".agents/plugins", ".codex-plugin", ".github", ".claude/skills",
          ".agents/skills", ".opencode/skills", ".opencode/skill", ".omp/skills", ".generated"]
# Each local root's forge-log.md is projected in the registered checkout declarations with the selecting
# kind `forge-log-preamble`: only the bytes before the first line that begins `## [` are fingerprinted, so
# an engine-written `used` entry, which lands after the preamble, leaves the checkout receipts reusable.
# The live-read audit (bionic/cycles/CYC-0120/evidence/build/forge-log-live-read-audit.md) found one
# reader past the preamble, tools/tests/test_canonical_instruction_file.py; it now reads only the
# preamble of every root's forge log (CYC-0127). A second copy of cycle_local_skills.ALL_ROOTS, because
# this module must not import the cycle engine; a test holds the two equal.
LOCAL_SKILL_ROOTS = (".claude/skills", ".agents/skills", ".opencode/skills", ".opencode/skill", ".omp/skills")
FORGE_LOGS = tuple(f"{root}/forge-log.md" for root in LOCAL_SKILL_ROOTS)
FORGE_LOG_PROJECTIONS = {path: ["forge-log-preamble"] for path in FORGE_LOGS}
# `uv.lock` and `pyproject.toml` stay inputs on purpose. The requirement's lock digest (the export,
# with the project left out) is separate from the files a test reads, and tests read both files and
# stage or scan the whole checkout. Narrowing INPUTS to exclude the version-bump files needs an
# audit that no suite test reads an excluded path, which a search of the tests cannot prove.
# Paths under the docs directory that no test in a registered suite reads. Each is a bookkeeping
# record, not an input: the cycle records, the journal, the operations log, the inbox, the garden
# notes, the next-steps record and the cycle queue. They change with every logged operation, and a
# suite whose receipt they invalidate runs again for nothing. The live-read audit adds a name here
# only after it removes or narrows every suite test that reads that path. A test that needs a gate's
# verdict on the live tree runs the gate over a committed copy that omits these paths
# (crux/scripts/tests/_live_copy.py). Schemas, templates, instruction files, decisions,
# observations, invariants, arch, research and briefs stay inputs. The audit and the coverage
# comparison for each removed duplicate are in bionic/cycles/CYC-0016/evidence/build/b1-* and, for
# `queue`, in bionic/cycles/CYC-0036/evidence/build/live-read-audit.md. `log` is the operations log's
# monthly directory, which the log writer creates beside or in place of `log.md`; at its addition no
# tracked file lay under `bionic/log/`, so no suite test read one (CYC-0134 build-slice-v2).
# Live-read audit of the log exclusion (CYC-0134 build-readers-v2, br-paths): a search of both test roots
# for reads of the live tree's `log.md` or `log/` found none. `git ls-files bionic/log` is empty; the
# tests that open a log (the writer, the repair, the summary, the migration, the cycle and release
# record tests) build a temporary tree; the live copy keeps a committed fixture of `log.md`
# (crux/scripts/tests/_live_copy.py); `_dev_surface.TREE_LOG_MD` has no reader. So no test needs an
# excluded path and nothing was narrowed. The `drift-gates` preset alone runs the summary gate, so
# `drift_gates_exclusions` adds the settled log files back to its inputs.
DOCS_EXCLUSIONS = ("cycles", "journal", "log.md", "log", "inbox", "garden", "whats_next.md", "queue")
# Docs-relative decision records. The registered CHECKOUT declarations leave them out of their inputs, so
# a commit that changes only decisions reuses the main run's receipt (IDR one-main-test-run, revision 4).
# A separate tuple, not part of DOCS_EXCLUSIONS, because DOCS_EXCLUSIONS also feeds every preset and the
# tests' live copy (crux/scripts/tests/_live_copy.py), and those must keep the records: the linting tests
# read them, and the `drift-gates`, `governs-references` and `governs-coverage` checks judge them.
# The kept entries are AGENTS.md, invariants, code and promptbooks; a test pins that every top-level
# docs entry belongs to exactly one of the three groups. Narrowing the kept entries needs a live-read
# audit that no suite test reads them, which a search of the tests cannot prove.
DECISION_RECORDS = ("adrs", "arch", "observations", "research", "briefs", "index.md", "manifest.yml", "objectives.md")
# Files outside the docs directory are bookkeeping only when the repository names them in
# `.bionic.yml` `evidence.bookkeeping_paths`. An entry needs a live-read audit first.
BOOKKEEPING_SETTING = ("evidence", "bookkeeping_paths")
_GLOB_CHARACTERS = frozenset("*?[]{}")
# Release-only exclusions and projections of the registered suites (CYC-0038, IDR release-neutral-evidence
# revision 2; CYC-0064, IDR changelog-citation-projection revision 1). Every entry matches one verdict of
# the release read audit (bionic/cycles/CYC-0038/evidence/build/release-read-audit.md, section 1); a path
# joins only with a cleared verdict. `CHANGELOG.md` is projected in the checkout suites (P9) by
# `_changelog_projection`: the kind `changelog-citations:<tokens>` fingerprints the rows the migration
# citation readers consume, so a prepended release section or a new footnote leaves the fingerprint alone.
# The checkout declares no projection, which leaves CHANGELOG.md a whole-file input, when no batch binds
# it, the token set is empty, a binding batch is unpublished, or the token reader raises anything. The
# staged suites exclude it (P11). `public` is a bookkeeping rendition of the checkout's release
# documents, not an input there (P10). The staged suites read the stage's own README.md (the public
# rendition), so it is projected there, not excluded.
RELEASE_EXCLUSIONS = {"checkout": ("public",), "staged": ("CHANGELOG.md",)}
_MANIFEST_VERSION = {path: ["json-string:version"] for path in (
    "crux/plugin.json", "crux/.claude-plugin/plugin.json", "crux/.codex-plugin/plugin.json",
    "crux-mods/.claude-plugin/plugin.json")}  # P1, in the checkout and in the stage
RELEASE_PROJECTIONS = {
    "checkout": {**_MANIFEST_VERSION,
                 "pyproject.toml": ["toml-project-version"],  # P2
                 "uv.lock": ["uv-lock-package-version:crux"],  # P3
                 "tools/bionic-catalog/crux-learning-catalog-guide.json": ["json-string:reviewed_plugin_version"],  # P4
                 "README.md": ["readme-footer-version"]},  # P5
    "staged": {**_MANIFEST_VERSION,
               ".generated": ["json-string:version"],  # P6
               "README.md": ["generated-fingerprint-line", "readme-footer-version"]},  # P7, P8
}
# Executables the suites' tests invoke, from a search of the tests' subprocess calls.
CORE_TOOLS = ("git", "uv")
TOOLS_TOOLS = ("git", "uv", "node")
STAGED_VARIABLES = {"PYTHONPATH": "${REPOSITORY}/crux/scripts", "PYTHONDONTWRITEBYTECODE": "1"}
FALLBACK_MINORS = ("3.13", "3.14")
# Test tiers (IDR test-tiers A3, A4). The five roots whose tests carry a tier manifest, the two roots
# that must hold a release unit, and the registered ids. `TIER_INPUTS` widens the suite INPUTS by the two
# TS roots the Python suites do not read, so a TS edit reruns the tier check and no Python suite.
TIER_ROOTS = ("crux/scripts/tests", "tools/tests", "crux-mods/tests", "crux-opencode/tests", "crux-omp/tests")
TIER_REQUIRE_RELEASE = ("crux/scripts/tests", "tools/tests")
TIER_INPUTS = [*INPUTS, "crux-opencode", "crux-omp"]
TIER_CHECK_ID = "checkout:test-tiers"
RELEASE_TIER_PREFIX = "checkout:unittest-release:"
TIER_CHECKER = "crux/scripts/test-tiers.py"


def _docs_relative(root):
    root = Path(root)
    if any((root / name).exists() for name in (".bionic.yml", ".crux", "bionic/manifest.yml", "docs/manifest.yml")):
        from bionic_config import load_config
        return load_config(root).docs_root.relative_to(root.resolve()).as_posix()
    return "docs"


def _configured_entries(root):
    config = Path(root) / ".bionic.yml"
    if not config.is_file():
        return []
    from bionic_config import load_yaml
    try:
        raw = load_yaml(config.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # the layout reader reports a malformed file; this reader refuses to guess
        raise EvidenceError(f".bionic.yml cannot be read for {'.'.join(BOOKKEEPING_SETTING)}: {type(exc).__name__}") from exc
    section = raw.get(BOOKKEEPING_SETTING[0]) if isinstance(raw, dict) else None
    if section is None:
        return []
    if not isinstance(section, dict):
        raise EvidenceError("evidence must be a mapping")
    entries = section.get(BOOKKEEPING_SETTING[1])
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise EvidenceError("evidence.bookkeeping_paths must be a list of repository-relative file paths")
    return entries


def bookkeeping_paths(root):
    """The repository-relative bookkeeping files the repository names, validated.

    An absent setting is an empty list. A missing file is allowed, so the setting is portable. An
    entry is refused, with the reason, when it is empty or not a string, absolute, contains `..`,
    contains a glob character, lies inside the docs directory, names a directory or is a symlink.
    """
    root = Path(root)
    docs = None
    result = []
    for entry in _configured_entries(root):
        label = f"evidence.bookkeeping_paths entry {entry!r}"
        if not isinstance(entry, str):
            raise EvidenceError(f"{label} must be a string path")
        if not entry.strip():
            raise EvidenceError("evidence.bookkeeping_paths entry is empty")
        if entry.startswith("/") or Path(entry).is_absolute():
            raise EvidenceError(f"{label} is absolute; use a repository-relative path")
        if ".." in Path(entry).parts:
            raise EvidenceError(f"{label} contains '..'; it must stay inside the repository")
        if _GLOB_CHARACTERS & set(entry):
            raise EvidenceError(f"{label} contains a glob character; list one regular file per entry")
        if docs is None:
            docs = _docs_relative(root)
        normalized = Path(entry).as_posix()
        if normalized == docs or normalized.startswith(docs + "/"):
            raise EvidenceError(f"{label} lies inside the docs directory ({docs}); add a docs-relative name to DOCS_EXCLUSIONS instead")
        try:
            mode = os.lstat(root / entry).st_mode
        except FileNotFoundError:
            mode = None
        if mode is not None and stat.S_ISLNK(mode):
            raise EvidenceError(f"{label} is a symlink; list the regular file")
        if (mode is not None and stat.S_ISDIR(mode)) or entry.endswith("/"):
            raise EvidenceError(f"{label} is a directory; list regular files")
        result.append(normalized)
    return result


def runtime_exclusions(root, names=None):
    """Operational records are outputs, not inputs of these static suites.

    The only producer of the bookkeeping-exclusion list: the docs-relative names, then the files
    `.bionic.yml` configures. The registered suites, every preset and the tests' live copy read it.
    Checks that explicitly test live records declare those inputs themselves without this
    suite-specific exclusion.
    """
    root = Path(root)
    docs = _docs_relative(root)
    return [docs + "/" + name for name in (DOCS_EXCLUSIONS if names is None else names)] + bookkeeping_paths(root)


def drift_gates_exclusions(root, today=None):
    """The `drift-gates` preset's exclusions: the shared list, with the log directory narrowed.

    The preset's command runs the summary gate, which reads the settled detail files and
    `log/summary.md`, so those stay inputs together with the completion record, the transaction file
    and the kept files. What it excludes of `log/` is the legacy `log.md` (already in the shared list),
    the current month's detail file by the recording host's local date, and the staged legacy files and
    staged strays that exist. Each excluded path sits in the declaration by name, so the fingerprint
    covers the names and never the bytes: a month change, or any incomplete split state, lapses a
    receipt, which only costs a rerun. ``today`` (YYYY-MM-DD) replaces the host's local date for tests.
    """
    import operation_log
    today = operation_log.resolve_today(today, write=False)
    docs = _docs_relative(root)
    log = f"{docs}/{operation_log.LOG_DIR}"
    kept = tuple(name for name in DOCS_EXCLUSIONS if name != operation_log.LOG_DIR)
    found = [f"{log}/{today[:7]}.md"]
    directory = Path(root) / log
    try:
        listed = sorted(os.listdir(directory)) if stat.S_ISDIR(os.lstat(directory).st_mode) else []
    except OSError:
        listed = []
    found += [f"{log}/{name}" for name in listed
              if operation_log.STAGED_LEGACY_NAME.fullmatch(name) or operation_log.STAGED_STRAY_NAME.fullmatch(name)]
    return [*runtime_exclusions(root, names=kept), *found]


def dev_minor(root):
    """The development default minor from ``.python-version``, else the running interpreter's."""
    version = Path(root) / ".python-version"
    if version.is_file():
        parts = version.read_text().strip().split(".")
        if len(parts) >= 2 and all(p.isdigit() for p in parts[:2]):
            return ".".join(parts[:2])
    return f"{sys.version_info[0]}.{sys.version_info[1]}"


def supported_minors(dev_root):
    if dev_root is not None and (Path(dev_root) / "pyproject.toml").is_file():
        data = tomllib.loads((Path(dev_root) / "pyproject.toml").read_text())
        found = data.get("tool", {}).get("crux", {}).get("python-versions")
        if found:
            return tuple(found)
    return FALLBACK_MINORS


def _changelog_projection(root):
    """The changelog projection, computed once per subject inside a call scope (see ``_changelog_tokens``)."""
    import test_evidence
    scope = test_evidence._SCOPE
    if scope is None:
        return _changelog_tokens(root)
    key = str(Path(root).resolve())
    if key not in scope["changelog"]:
        scope["changelog"][key] = _changelog_tokens(root)
    return {path: list(kinds) for path, kinds in scope["changelog"][key].items()}


def _changelog_tokens(root):
    """``{"CHANGELOG.md": [kind]}`` when the migration batches certify the token set, else ``{}``.

    The tokens come from ``implementation_migration.changelog_citation_tokens``, imported lazily so this
    module loads where that one cannot. Every uncertain state returns ``{}``, which leaves CHANGELOG.md a
    whole-file input: the call raises, no batch binds CHANGELOG.md, the token set is empty (an empty kind
    never validates), or a binding batch has no committed application.
    """
    try:
        # A tree with no batch file has no tokens. The reader walks the commit history, so skip it there.
        if not any((Path(root) / _docs_relative(root) / "adrs/migrations").glob("*.yaml")):
            return {}
        from implementation_migration import changelog_citation_tokens
        found = changelog_citation_tokens(root)
        tokens, binding, unpublished = found["tokens"], found["binding"], found["unpublished"]
        if not tokens or not binding or unpublished or tokens != sorted(set(tokens)):
            return {}
        return {"CHANGELOG.md": ["changelog-citations:" + " ".join(tokens)]}
    except Exception:
        return {}


def _suites(root, dev_root):
    """``(scope, start, minor-or-None, requirement)`` for the two registered checkout suites."""
    local = dev_minor(root if dev_root is None else dev_root)
    yield ("checkout", "crux/scripts/tests", None,
           {"interpreter": {"implementation": "cpython", "minors": [local]},
            "packages": {"lock": {"source": "subject", "project": False}},
            "isolated": True, "tools": list(CORE_TOOLS)})
    yield ("checkout", "tools/tests", None,
           {"interpreter": {"implementation": "cpython", "minors": [local]},
            "packages": {"lock": {"source": "subject", "project": True, "project_version": "release-neutral"}},
            "isolated": False, "tools": list(TOOLS_TOOLS)})


def staged_check_id(minor, name):
    return f"staged:py{minor}:{name}"


# The two registered checks per supported minor that replace the staged full suite. `flagged` runs the
# committed list of tests (crux/scripts/tests/flagged_tests.json) that can differ between interpreters
# or the packaged tree; `health` compiles every staged .py file and imports every staged module
# (crux/scripts/staged_health.py). Both run against the stage, and the evidence engine runs the
# canonical command in the minor's locked requirement. Receipts of the earlier staged full suite
# (`staged:py<minor>:unittest:...`) stay readable: a receipt whose check id is not registered
# validates against its own recorded declaration.
STAGED_CHECKS = {
    "flagged": ["python", "crux/scripts/tests/parallel_suite.py", "crux/scripts/tests", "--flagged"],
    "health": ["python", "crux/scripts/staged_health.py"],
}


def _staged_checks(dev_root):
    """``(minor, name, command, requirement)`` for the registered staged checks."""
    for minor in supported_minors(dev_root):
        requirement = {"interpreter": {"implementation": "cpython", "minors": [minor]},
                       "packages": {"lock": {"source": "dev-root", "project": False}},
                       "isolated": True, "tools": list(CORE_TOOLS),
                       "variables": dict(STAGED_VARIABLES), "flags": {"dont_write_bytecode": 1}}
        for name, command in STAGED_CHECKS.items():
            yield minor, name, command, requirement


def check_id_for(scope, start, pattern, minor=None, *, tier=None):
    """The check id of a suite run; ``tier="release"`` names the release-tier declaration of the suite."""
    prefix = f"{scope}:py{minor}:" if scope == "staged" and minor else f"{scope}:"
    return f"{prefix}{'unittest-release' if tier else 'unittest'}:{start}:{pattern}"


def _declaration(scope, start, pattern, top, root, minor, requirement, *, registered=False, changelog=None, tier=None):
    command = ["python", "crux/scripts/tests/parallel_suite.py", start, "--pattern", pattern]
    if top:
        command += ["--top-level-directory", top]
    if tier:
        command += ["--tier", tier]
    declaration = {"check_id": check_id_for(scope, start, pattern, minor, tier=tier), "command": command,
                   "inputs": list(INPUTS) if start.split("/")[0] in INPUTS else [*INPUTS, start],
                   "environment": [], "git_tracked": scope == "checkout",
                   "exclude_inputs": runtime_exclusions(root) if scope == "checkout" else []}
    if registered:
        records = [_docs_relative(root) + "/" + name for name in DECISION_RECORDS] if scope == "checkout" else []
        declaration["exclude_inputs"] = [*declaration["exclude_inputs"], *records, *RELEASE_EXCLUSIONS[scope]]
        declaration["input_projections"] = {path: list(kinds) for path, kinds in RELEASE_PROJECTIONS[scope].items()}
        if scope == "checkout":
            declaration["input_projections"].update({path: list(kinds) for path, kinds in FORGE_LOG_PROJECTIONS.items()})
            # A caller building several declarations passes the projection it computed once.
            declaration["input_projections"].update(_changelog_projection(root) if changelog is None else changelog)
    if requirement is not None:
        declaration["requirement"] = requirement
    return declaration


def registered_declarations(root, *, dev_root=None):
    """The registered declarations, keyed by check id."""
    root = Path(root).resolve()
    suites = list(_suites(root, dev_root))
    changelog = _changelog_projection(root) if any(scope == "checkout" for scope, *_ in suites) else None
    found = {}
    for tier in (None, "release"):
        for scope, start, minor, requirement in suites:
            found[check_id_for(scope, start, DEFAULT_PATTERN, minor, tier=tier)] = _declaration(
                scope, start, DEFAULT_PATTERN, None, root, minor, requirement, registered=True, tier=tier,
                changelog=None if changelog is None else {path: list(kinds) for path, kinds in changelog.items()})
    if changelog is not None:
        found[TIER_CHECK_ID] = _tier_check_declaration(root, changelog)
    for minor, name, command, requirement in _staged_checks(dev_root):
        found[staged_check_id(minor, name)] = _staged_declaration(minor, name, command, requirement)
    return found


def tier_check_command(expect=TIER_ROOTS, require_release=TIER_REQUIRE_RELEASE, checker=TIER_CHECKER):
    """The tier check's command: ``check`` over the project with each expected root named."""
    command = ["python", checker, "check"]
    for item in expect:
        command += ["--expect-root", item]
    for item in require_release:
        command += ["--require-release-units", item]
    return command


def _tier_check_declaration(root, changelog):
    """The registered ``checkout:test-tiers`` declaration: the checkout suites' exclusions and projections
    over ``TIER_INPUTS``, git-tracked, so an added or edited test file changes its fingerprint."""
    declaration = _declaration("checkout", "crux/scripts/tests", DEFAULT_PATTERN, None, root, None, None,
                               registered=True, changelog={path: list(kinds) for path, kinds in changelog.items()})
    declaration["check_id"] = TIER_CHECK_ID
    declaration["command"] = tier_check_command()
    declaration["inputs"] = list(TIER_INPUTS)
    declaration["requirement"] = {"tools": ["git"]}
    return declaration


def release_groups(check_ids):
    """The per-suite rule as groups of acceptable ids: ``[(id, ...), ...]``.

    A checkout suite and its release-tier declaration form one group, satisfied by evidence for either.
    Every other id is its own group. Callers that need every suite proven by the full declaration
    (Build exit, completion) do not call this reader; they use ``full_checkout_ids`` instead.
    """
    ids = sorted(set(check_ids))
    groups, used = [], set()
    for check_id in ids:
        if check_id in used:
            continue
        if check_id.startswith("checkout:unittest:"):
            twin = RELEASE_TIER_PREFIX + check_id[len("checkout:unittest:"):]
            members = tuple(i for i in (check_id, twin) if i in ids)
        elif check_id.startswith(RELEASE_TIER_PREFIX):
            if "checkout:unittest:" + check_id[len(RELEASE_TIER_PREFIX):] in ids:
                continue
            members = (check_id,)
        else:
            members = (check_id,)
        used.update(members)
        groups.append(members)
    return groups


def full_checkout_ids(declarations):
    """The checkout ids that prove a whole code state: every ``checkout:`` id except the release-tier ones."""
    return sorted(i for i in declarations if i.startswith("checkout:") and not i.startswith(RELEASE_TIER_PREFIX))


def _staged_declaration(minor, name, command, requirement):
    return {"check_id": staged_check_id(minor, name), "command": list(command), "inputs": list(INPUTS),
            "environment": [], "git_tracked": False, "exclude_inputs": list(RELEASE_EXCLUSIONS["staged"]),
            "input_projections": {path: list(kinds) for path, kinds in RELEASE_PROJECTIONS["staged"].items()},
            "requirement": json.loads(json.dumps(requirement))}


def flagged_list_problems(root, dev_root):
    """The problems of the committed flagged list at ``root``, judged against ``dev_root``'s supported minors.

    The staged tree carries no project file, so the minor check runs here, where the dev checkout is known.
    """
    import flagged_tests
    try:
        entries = flagged_tests.load(Path(root) / flagged_tests.DEFAULT_RELATIVE)
    except flagged_tests.FlaggedError as exc:
        return [str(exc)]
    return flagged_tests.validate(entries, list(supported_minors(dev_root)),
                                  tiers_dir=(Path(root) / flagged_tests.DEFAULT_RELATIVE).parent)


def staged_check_declaration(root, name, minor, *, dev_root=None):
    """The registered declaration of the staged check ``name`` on ``minor``."""
    declaration = registered_declaration(root, staged_check_id(minor, name), dev_root=dev_root)
    if declaration is None:
        raise EvidenceError(f"no registered staged check {name!r} for Python {minor}")
    return declaration


def registered_declaration(root, check_id, *, dev_root=None):
    """The registered declaration for ``check_id``, or None when the check is not registered."""
    if not isinstance(check_id, str) or not check_id.startswith(("checkout:", "staged:")):
        return None
    return registered_declarations(root, dev_root=dev_root).get(check_id)


def declaration_for(scope, start, pattern, top, root, *, minor=None, dev_root=None, tier=None):
    """``(declaration, registered)`` for a suite run. An unregistered run uses the default requirement.

    ``tier="release"`` selects the release-tier declaration of a registered checkout suite; any other
    run that names a tier is unregistered and carries the tier in its command.
    """
    root = Path(root).resolve()
    if top is None and pattern == DEFAULT_PATTERN and (tier is None or (tier == "release" and scope == "checkout")):
        for suite_scope, suite_start, suite_minor, requirement in _suites(root, dev_root):
            if (suite_scope, suite_start) == (scope, start) and suite_minor in (None, minor):
                return _declaration(scope, start, pattern, None, root, suite_minor, requirement, registered=True,
                                    tier=tier), True
    return _declaration(scope, start, pattern, top, root, minor if scope == "staged" else None, None, tier=tier), False


# Presets for a cycle-declared check. Each expands to a concrete declaration with no preset field, so
# a receipt records the exclusions it was recorded with and lookup needs no preset reader. Every
# preset but journal-index carries the registered checkout projection: the broad INPUTS and
# runtime_exclusions(root). journal-index runs the one gate whose verdict depends on every journal
# entry (the gate `drift-gates` skips) over exactly the inputs it reads, with no exclusions.
# `tools` lists the executables a gate invokes, from the CYC-0036 live-read audit section 3.
#
# The three dashboard gates declare what their script reads, not the whole tree (CYC-0096). A change outside
# these paths reuses the receipt: CYC-0095 spent about 105 s per change running all three. `git_tracked` is
# False for them, because a tracked-file inventory and HEAD tree digest cover the whole repository and would
# move on every commit, which defeats the narrow selection. The reads sit beside the presets so a gate's reads
# and its command change together. Two reads stay undeclared: the git index that opencode_gate.py checks for
# tracked lockfiles (a tracked entry deleted from disk without staging reuses the receipt), and the repository
# path a capability `refuse` entry names as its counterpart (none exists today; adding one must add it here).
# The root package.json, tsconfig.json and bunfig.toml that node and bun look up are declared even while
# absent: an absent input fingerprints as missing, so its later addition re-executes the gate.
_GATE_PROJECT_FILES = ("pyproject.toml", "uv.lock", ".python-version")
_GATE_TS_CONFIG = ("package.json", "tsconfig.json", "bunfig.toml")


def _gate_reads(root, gate):
    """The repository-relative inputs the dashboard ``gate`` reads, with the docs directory resolved from ``root``."""
    docs = _docs_relative(root)
    decisions = [f"{docs}/adrs/ADR-*.md", f"{docs}/adrs/archive/ADR-*.md", f"{docs}/adrs/summaries/resolver.json", ".bionic.yml"]
    if gate == "mods-gate":
        # tools/mods_gate.py:83-88 (manifest, fixtures), :288-345 (.bionic.yml, ADR status, resolver), :736 (plugin dir);
        # `claude plugin validate|test` read the plugin directory and may read the marketplace catalog (uncertain).
        return ["crux-mods", "tools/mods_gate.py", ".claude-plugin", *decisions, *_GATE_PROJECT_FILES, *_GATE_TS_CONFIG]
    if gate == "opencode-gate":
        # tools/opencode_gate.py:56-58 (opencode_gate_lib), opencode_gate_lib/harness.py:19 and manifest.py:19 (import
        # mods_gate), harness.py:108 (crux-mods/hooks/capabilities.ts), model.py:204-240 (crux-opencode and the core
        # import closure under crux-mods/hooks/lib), manifest.py:298-320 (ADR status through mods_gate).
        return ["crux-opencode", "crux-mods/hooks/lib", "crux-mods/hooks/capabilities.ts", "tools/opencode_gate.py",
                "tools/opencode_gate_lib", "tools/mods_gate.py", *decisions, *_GATE_PROJECT_FILES]
    if gate == "omp-gate":
        # tools/omp_gate.py:298-420 (crux-omp tree, imports under crux-mods/hooks/lib), :448-462 (snapshot of both).
        return ["crux-omp", "crux-mods/hooks/lib", "tools/omp_gate.py", *_GATE_PROJECT_FILES, *_GATE_TS_CONFIG]
    raise EvidenceError(f"no declared reads for {gate!r}")


PRESETS = {
    "whole-tree": {"command": None, "script": None, "tools": None},
    "drift-gates": {"command": ["python", "tools/run-drift-gates.py", "--cycle-scope"],
                    "script": "tools/run-drift-gates.py", "tools": None},
    # The two governs checks judge the decision records, so their inputs include them: the declaration is
    # the broad INPUTS minus only the bookkeeping exclusions, like drift-gates. A cycle's Test declares both.
    "governs-references": {"command": ["python", "crux/scripts/lint-governs-references.py"],
                           "script": "crux/scripts/lint-governs-references.py", "tools": None},
    "governs-coverage": {"command": ["python", "crux/scripts/check-governs-coverage.py"],
                         "script": "crux/scripts/check-governs-coverage.py", "tools": None},
    "mods-gate": {"command": ["python", "tools/mods_gate.py", "--plugin-dir", "crux-mods", "--phase", "dev"],
                  "script": "tools/mods_gate.py", "tools": ["claude", "uv"], "reads": "mods-gate"},
    "opencode-gate": {"command": ["python", "tools/opencode_gate.py", "--plugin-dir", "crux-opencode", "--phase", "dev"],
                      "script": "tools/opencode_gate.py", "tools": ["claude", "git", "uv"], "reads": "opencode-gate"},
    "omp-gate": {"command": ["python", "tools/omp_gate.py", "--plugin-dir", "crux-omp", "--phase", "dev"],
                 "script": "tools/omp_gate.py", "tools": ["node", "uv"], "reads": "omp-gate"},
    # The release-metadata check holds at any commit and reads the version files the suites project away,
    # so it declares the broad INPUTS with no release exclusion or projection. It invokes `uv run` only.
    "release-metadata": {"command": ["python", "tools/release-preflight.py", "--metadata"],
                         "script": "tools/release-preflight.py", "tools": ["uv"]},
    "journal-index": {"command": ["python", "crux/scripts/generate-journal-index.py", "--dry-run"],
                      "script": "crux/scripts/generate-journal-index.py", "tools": None},
    # The shipped tier checker over the manifests the project holds. It applies in any project: the command
    # is built from the manifests present, so it carries no fixed command and needs no script in the root.
    "test-tiers": {"command": [], "script": None, "tools": ["git"], "tiers": True},
}


def _tier_preset_roots(root):
    """The test roots, relative to ``root`` and sorted, whose manifests the project holds.

    Refuses when the project holds no manifest, because a check that expects nothing proves nothing.
    """
    import test_tiers
    try:
        roots, _ = test_tiers.discover_manifests(root, "auto")
    except test_tiers.ManifestError as exc:
        raise EvidenceError(f"preset test-tiers cannot find the manifests: {exc}") from exc
    if not roots:
        raise EvidenceError(f"preset test-tiers is not applicable here: the project holds no {test_tiers.MANIFEST_NAME}")
    return sorted(Path(os.path.relpath(r, root)).as_posix() for r in roots)


def _tier_preset_command(root, roots):
    """The ``test-tiers`` preset's command: ``check`` with one ``--expect-root`` per manifest the project holds."""
    checker = TIER_CHECKER if (root / TIER_CHECKER).is_file() else str(Path(__file__).resolve().with_name("test-tiers.py"))
    return tier_check_command(roots, (), checker)


def preset_declaration(root, preset, check_id, *, command=None, requirement=None, today=None):
    """The concrete declaration for ``preset``, validated by the engine's own normalizer.

    Only ``whole-tree`` takes the caller's command, and it needs one; every other preset fixes its
    own. A caller requirement replaces the preset's default. A preset whose script is absent from
    ``root`` refuses as not applicable, because the check cannot run there. ``today`` (YYYY-MM-DD)
    replaces the host's local date, which only the ``drift-gates`` preset reads (see
    ``drift_gates_exclusions``).
    """
    root = Path(root).resolve()
    if preset not in PRESETS:
        raise EvidenceError(f"unknown preset {preset!r}; choose one of {', '.join(sorted(PRESETS))}")
    if not isinstance(check_id, str) or not check_id.strip():
        raise EvidenceError("check_id must be nonempty")
    spec = PRESETS[preset]
    if spec.get("tiers"):
        if command is not None:
            raise EvidenceError(f"preset {preset} fixes its command; only whole-tree takes --command")
        roots = _tier_preset_roots(root)
        # The whole-tree inputs, plus each expected root as a directory: a test file added there but not yet
        # tracked by git still moves the fingerprint, so the earlier receipt is not reused for it.
        declaration = {"check_id": check_id, "command": _tier_preset_command(root, roots),
                       "inputs": [*INPUTS, *(r for r in roots if r not in INPUTS)],
                       "environment": [], "git_tracked": True, "exclude_inputs": runtime_exclusions(root)}
        declaration["requirement"] = requirement if requirement is not None else {"tools": list(spec["tools"])}
        normalize(declaration)
        return declaration
    if spec["command"] is None:
        if command is None:
            raise EvidenceError(f"preset {preset} needs the caller's --command (a JSON array)")
        chosen = list(command)
    else:
        if command is not None:
            raise EvidenceError(f"preset {preset} fixes its command; only whole-tree takes --command")
        chosen = list(spec["command"])
    if spec["script"] is not None and not (root / spec["script"]).is_file():
        raise EvidenceError(f"preset {preset} is not applicable here: {spec['script']} is absent")
    if preset == "journal-index":
        declaration = {"check_id": check_id, "command": chosen,
                       "inputs": [_docs_relative(root) + "/journal", "crux/scripts", ".bionic.yml"],
                       "environment": [], "git_tracked": False, "exclude_inputs": []}
    elif spec.get("reads"):
        declaration = {"check_id": check_id, "command": chosen, "inputs": _gate_reads(root, spec["reads"]), "environment": [],
                       "git_tracked": False, "exclude_inputs": runtime_exclusions(root)}
    else:
        declaration = {"check_id": check_id, "command": chosen, "inputs": list(INPUTS), "environment": [],
                       "git_tracked": True,
                       "exclude_inputs": drift_gates_exclusions(root, today) if preset == "drift-gates" else runtime_exclusions(root)}
    if requirement is not None:
        declaration["requirement"] = requirement
    elif spec["tools"] is not None:
        declaration["requirement"] = {"tools": list(spec["tools"])}
    normalize(declaration)
    return declaration


def evidence_plan(root, declaration, *, source_root=None):
    """Describe reuse without executing a check or exposing environment values."""
    found = lookup(root, declaration, source_root=source_root)
    previous = found["record"]
    if previous is None:
        candidates = [r for r in read_receipts(storage(root, source_root))
                      if r["declaration"]["check_id"] == declaration["check_id"] and r["schema_version"] == 2]
        previous = max(candidates, key=lambda r: r["finished_at"], default=None)
    report = {"check_id": declaration["check_id"], "state": found["state"],
              "evidence_id": previous["id"] if previous else None}
    if found["ignored"]:
        report["ignored"] = found["ignored"][:20]
    if found["earlier_failures"]:
        report["earlier_failures"] = found["earlier_failures"]
    if previous and found["state"] == "inputs-changed":
        before, after = previous["snapshot"]["inputs"], found["snapshot"]["inputs"]
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        report["changed_inputs"] = changed[:100]
        report["changed_input_count"] = len(changed)
        if not changed:
            report["other_changes"] = "Declaration, Git inventory, HEAD tree or lock differs."
    if found["state"] != "passed":
        report["remedy"] = ("Establish evidence with the registered suite command (run it without a planning flag). "
                            "A matching failure also requires CRUX_TEST_RETRY_REASON.")
    return found, report


def _source_root(args):
    if getattr(args, "source_root", None):
        return Path(args.source_root).resolve()
    if args.evidence_scope != "staged":
        return None
    # Compatibility: sync.sh before its ledger mode keeps the staged store beside the dev root's files.
    value = os.environ.get("CRUX_TEST_EVIDENCE_STORE")
    if value and (Path(value).absolute().parent / "uv.lock").is_file():
        return Path(value).absolute().parent.resolve()
    raise EvidenceError("staged evidence needs --source-root (the dev checkout that holds uv.lock and the durable store)")


SHOW_REUSED_OUTPUT_ENV = "CRUX_SHOW_REUSED_TEST_OUTPUT"


def _stored_verdict(output):
    """The last non-blank line of the stored log (the suite's own verdict line), or None."""
    try:
        lines = [line.strip() for line in output.read_text(errors="replace").splitlines() if line.strip()]
    except OSError:
        return None
    return lines[-1] if lines else None


def _report_reuse(record, output, lookup_seconds, args):
    """Say plainly that a stored result was reused and no test ran now.

    The first line keeps the ``Test evidence reused: TE-<id> `` prefix that tools/release.py parses.
    The original run's duration and finish time are reported apart from this lookup's duration.
    The stored log is not replayed unless asked for (``show_reused_output`` or the environment
    variable); its path is printed instead. Only passed records are reused, so a failure's output
    is always printed by the executed path.
    """
    finished = datetime.fromtimestamp(record["finished_at"], timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    print(f"Test evidence reused: {record['id']} (stored result of an earlier run; no tests ran now)", flush=True)
    print(f"  original run: finished {finished}, took {record['seconds']:.2f}s, ran because: {record['reason']}", flush=True)
    print(f"  this lookup: {lookup_seconds:.2f}s", flush=True)
    print(f"  stored log: {output}", flush=True)
    if getattr(args, "show_reused_output", False) or os.environ.get(SHOW_REUSED_OUTPUT_ENV):
        print("--- stored log of the earlier run (not run now) ---", flush=True)
        print(output.read_text(errors="replace"), end="", flush=True)
        print("--- end stored log ---", flush=True)
    else:
        print(f"  (the log is not replayed; set {SHOW_REUSED_OUTPUT_ENV}=1 to print it)", flush=True)
    verdict = _stored_verdict(output)
    if verdict:
        print(f"Reused result: {verdict}", flush=True)


def run_shared(args):
    root = Path.cwd().resolve()
    minor = getattr(args, "python_minor", None) or f"{sys.version_info[0]}.{sys.version_info[1]}"
    source_root = _source_root(args)
    check = getattr(args, "staged_check", None)
    if check:
        if args.evidence_scope != "staged":
            raise EvidenceError("--staged-check needs --evidence-scope staged")
        declaration = staged_check_declaration(root, check, minor, dev_root=source_root)
        actual = [sys.executable, *STAGED_CHECKS[check][1:]]
        problems = flagged_list_problems(root, source_root) if check == "flagged" else []
        if problems:
            raise EvidenceError("the flagged list is invalid: " + "; ".join(problems))
    else:
        tier = (getattr(args, "tier", None) or [None])[0]
        declaration, registered = declaration_for(args.evidence_scope, args.start, args.pattern, args.top, root,
                                                  minor=minor, dev_root=source_root, tier=tier)
        actual = [sys.executable, "crux/scripts/tests/parallel_suite.py", args.start, "--pattern", args.pattern]
        if args.top:
            actual += ["--top-level-directory", args.top]
        if tier:
            actual += ["--tier", tier]
    if args.workers and check != "health":
        actual += ["--workers", str(args.workers)]
    if args.records and check != "health":
        actual += ["--records", args.records]
    if args.timings and check != "health":
        actual += ["--timings", args.timings]
    return _plan_and_run(root, declaration, actual, source_root, args)


def run_registered(args):
    """Plan or run a registered non-suite check (today ``checkout:test-tiers``) and print the lines a suite run prints.

    ``release.py`` and the preflight read the same ``Test evidence plan:`` and ``Test evidence executed|reused:``
    lines, so this check's receipt is observed like a suite's. The check runs the registered command unchanged.
    """
    root = Path(getattr(args, "repo_root", None) or Path.cwd()).resolve()
    source_root = _source_root(args)
    declaration = registered_declaration(root, args.check_id, dev_root=source_root)
    if declaration is None or not str(args.check_id).startswith("checkout:"):
        raise EvidenceError(f"no registered checkout check {args.check_id!r}")
    if args.check_id.startswith(("checkout:unittest:", RELEASE_TIER_PREFIX)):
        raise EvidenceError(f"{args.check_id} is a suite; run it through parallel_suite.py --shared-evidence")
    if declaration["command"][0] != "python":
        raise EvidenceError(f"{args.check_id} does not declare a python command")
    actual = [sys.executable, *declaration["command"][1:]]
    return _plan_and_run(root, declaration, actual, source_root, args)


def _plan_and_run(root, declaration, actual, source_root, args):
    """Look the declaration up, print the plan line, then stop, refuse or execute; the shared tail of both runners."""
    lookup_began = time.monotonic()
    found, report = evidence_plan(root, declaration, source_root=source_root)
    print("Test evidence plan: " + json.dumps(report, sort_keys=True), flush=True)
    if getattr(args, "plan_test_evidence", False):
        return 0 if found["state"] == "passed" else 3
    if getattr(args, "reuse_test_evidence_only", False):
        if found["state"] != "passed":
            print("REFUSE: test evidence is " + found["state"] + "; " + report["remedy"], file=sys.stderr)
            return 2
        result = {"action": "reused", "evidence": found["record"]}
    else:
        result = execute(root, declaration, getattr(args, "retry_reason", None), execution_command=actual,
                         source_root=source_root)
    record = result["evidence"]
    output = storage(root, source_root) / record["output"]
    if result["action"] == "reused":
        _report_reuse(record, output, time.monotonic() - lookup_began, args)
    else:
        print(f"Test evidence {result['action']}: {record['id']} ({record['reason']}; {record['seconds']:.2f}s)", flush=True)
        print(output.read_text(errors="replace"), end="", flush=True)
    if record["status"] == "passed":
        return 0
    if record["status"] == "interrupted" and record.get("signal"):
        return 128 + record["signal"]
    return 1 if record["status"] == "failed" and record["returncode"] == 1 else 2
