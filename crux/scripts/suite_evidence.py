"""Registry and adapter of the four reused suites.

``release-preflight.py``, ``sync.sh``, ``tools/test-suite.py`` and ``tools/release.py`` read a suite's
declaration and requirement only from here, so the tester's run and a release run produce
interchangeable receipts. The four suites are the checkout core suite, the checkout tools suite, and
the staged suite for each supported Python minor. A receipt is a reuse candidate for a registered
check only when its recorded declaration equals the registered one.

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

from test_evidence import EvidenceError, execute, lookup, normalize, read_receipts, storage

DEFAULT_PATTERN = "test*.py"
INPUTS = ["crux", "crux-mods", "tools", "opencode", "bionic", "public", "*.md",
          "*.sh", "pyproject.toml", "uv.lock", ".bionic.yml", ".claude-plugin",
          ".agents/plugins", ".codex-plugin", ".github", ".claude/skills",
          ".agents/skills", ".opencode/skills", ".opencode/skill", ".generated"]
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
# `queue`, in bionic/cycles/CYC-0036/evidence/build/live-read-audit.md.
DOCS_EXCLUSIONS = ("cycles", "journal", "log.md", "inbox", "garden", "whats_next.md", "queue")
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
    """``(scope, start, minor-or-None, requirement)`` for the four registered suites."""
    local = dev_minor(root if dev_root is None else dev_root)
    yield ("checkout", "crux/scripts/tests", None,
           {"interpreter": {"implementation": "cpython", "minors": [local]},
            "packages": {"lock": {"source": "subject", "project": False}},
            "isolated": True, "tools": list(CORE_TOOLS)})
    yield ("checkout", "tools/tests", None,
           {"interpreter": {"implementation": "cpython", "minors": [local]},
            "packages": {"lock": {"source": "subject", "project": True, "project_version": "release-neutral"}},
            "isolated": False, "tools": list(TOOLS_TOOLS)})
    for minor in supported_minors(dev_root):
        yield ("staged", "crux/scripts/tests", minor,
               {"interpreter": {"implementation": "cpython", "minors": [minor]},
                "packages": {"lock": {"source": "dev-root", "project": False}},
                "isolated": True, "tools": list(CORE_TOOLS),
                "variables": dict(STAGED_VARIABLES), "flags": {"dont_write_bytecode": 1}})


def check_id_for(scope, start, pattern, minor=None):
    prefix = f"{scope}:py{minor}:" if scope == "staged" and minor else f"{scope}:"
    return f"{prefix}unittest:{start}:{pattern}"


def _declaration(scope, start, pattern, top, root, minor, requirement, *, registered=False):
    command = ["python", "crux/scripts/tests/parallel_suite.py", start, "--pattern", pattern]
    if top:
        command += ["--top-level-directory", top]
    declaration = {"check_id": check_id_for(scope, start, pattern, minor), "command": command,
                   "inputs": list(INPUTS) if start.split("/")[0] in INPUTS else [*INPUTS, start],
                   "environment": [], "git_tracked": scope == "checkout",
                   "exclude_inputs": runtime_exclusions(root) if scope == "checkout" else []}
    if registered:
        declaration["exclude_inputs"] = [*declaration["exclude_inputs"], *RELEASE_EXCLUSIONS[scope]]
        declaration["input_projections"] = {path: list(kinds) for path, kinds in RELEASE_PROJECTIONS[scope].items()}
        if scope == "checkout":
            declaration["input_projections"].update(_changelog_projection(root))
    if requirement is not None:
        declaration["requirement"] = requirement
    return declaration


def registered_declarations(root, *, dev_root=None):
    """The registered declarations, keyed by check id."""
    root = Path(root).resolve()
    return {check_id_for(scope, start, DEFAULT_PATTERN, minor):
            _declaration(scope, start, DEFAULT_PATTERN, None, root, minor, requirement, registered=True)
            for scope, start, minor, requirement in _suites(root, dev_root)}


def registered_declaration(root, check_id, *, dev_root=None):
    """The registered declaration for ``check_id``, or None when the check is not registered."""
    if not isinstance(check_id, str) or not check_id.startswith(("checkout:", "staged:")):
        return None
    return registered_declarations(root, dev_root=dev_root).get(check_id)


def declaration_for(scope, start, pattern, top, root, *, minor=None, dev_root=None):
    """``(declaration, registered)`` for a suite run. An unregistered run uses the default requirement."""
    root = Path(root).resolve()
    if top is None and pattern == DEFAULT_PATTERN:
        for suite_scope, suite_start, suite_minor, requirement in _suites(root, dev_root):
            if (suite_scope, suite_start) == (scope, start) and suite_minor in (None, minor):
                return _declaration(scope, start, pattern, None, root, suite_minor, requirement, registered=True), True
    return _declaration(scope, start, pattern, top, root, minor if scope == "staged" else None, None), False


# Presets for a cycle-declared check. Each expands to a concrete declaration with no preset field, so
# a receipt records the exclusions it was recorded with and lookup needs no preset reader. Every
# preset but journal-index carries the registered checkout projection: the broad INPUTS and
# runtime_exclusions(root). journal-index runs the one gate whose verdict depends on every journal
# entry (the gate `drift-gates` skips) over exactly the inputs it reads, with no exclusions.
# `tools` lists the executables a gate invokes, from the CYC-0036 live-read audit section 3.
PRESETS = {
    "whole-tree": {"command": None, "script": None, "tools": None},
    "drift-gates": {"command": ["python", "tools/run-drift-gates.py", "--cycle-scope"],
                    "script": "tools/run-drift-gates.py", "tools": None},
    "mods-gate": {"command": ["python", "tools/mods_gate.py", "--plugin-dir", "crux-mods", "--phase", "dev"],
                  "script": "tools/mods_gate.py", "tools": ["claude", "uv"]},
    "opencode-gate": {"command": ["python", "tools/opencode_gate.py", "--plugin-dir", "crux-opencode", "--phase", "dev"],
                      "script": "tools/opencode_gate.py", "tools": ["claude", "git", "uv"]},
    "omp-gate": {"command": ["python", "tools/omp_gate.py", "--plugin-dir", "crux-omp", "--phase", "dev"],
                 "script": "tools/omp_gate.py", "tools": ["node", "uv"]},
    # The release-metadata check holds at any commit and reads the version files the suites project away,
    # so it declares the broad INPUTS with no release exclusion or projection. It invokes `uv run` only.
    "release-metadata": {"command": ["python", "tools/release-preflight.py", "--metadata"],
                         "script": "tools/release-preflight.py", "tools": ["uv"]},
    "journal-index": {"command": ["python", "crux/scripts/generate-journal-index.py", "--dry-run"],
                      "script": "crux/scripts/generate-journal-index.py", "tools": None},
}


def preset_declaration(root, preset, check_id, *, command=None, requirement=None):
    """The concrete declaration for ``preset``, validated by the engine's own normalizer.

    Only ``whole-tree`` takes the caller's command, and it needs one; every other preset fixes its
    own. A caller requirement replaces the preset's default. A preset whose script is absent from
    ``root`` refuses as not applicable, because the check cannot run there.
    """
    root = Path(root).resolve()
    if preset not in PRESETS:
        raise EvidenceError(f"unknown preset {preset!r}; choose one of {', '.join(sorted(PRESETS))}")
    if not isinstance(check_id, str) or not check_id.strip():
        raise EvidenceError("check_id must be nonempty")
    spec = PRESETS[preset]
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
    else:
        declaration = {"check_id": check_id, "command": chosen, "inputs": list(INPUTS), "environment": [],
                       "git_tracked": True, "exclude_inputs": runtime_exclusions(root)}
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
    declaration, registered = declaration_for(args.evidence_scope, args.start, args.pattern, args.top, root,
                                              minor=minor, dev_root=source_root)
    actual = [sys.executable, "crux/scripts/tests/parallel_suite.py", args.start, "--pattern", args.pattern]
    if args.top:
        actual += ["--top-level-directory", args.top]
    if args.workers:
        actual += ["--workers", str(args.workers)]
    if args.records:
        actual += ["--records", args.records]
    if args.timings:
        actual += ["--timings", args.timings]
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
        result = execute(root, declaration, args.retry_reason, execution_command=actual, source_root=source_root)
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
