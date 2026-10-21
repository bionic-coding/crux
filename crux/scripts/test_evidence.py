"""Repository-owned test evidence. One question decides every lookup, execution and validation.

Did this check run and pass, in an environment that satisfies its requirement, on the subject's
relevant inputs? No caller re-probes the validating process or hashes its ambient variables.

Two things are kept apart:

* **Inputs** are the subject's declared projection: file digests, the Git inventory and HEAD tree
  of a git-tracked declaration, and the digest of the lock file the requirement names. They
  decide the receipt's ``fingerprint``.
* **Environment** is what the executing process reported about itself. Python checks run through
  ``test_evidence_capture.py``, which writes an identity file before the entry starts. The receipt
  records it. A receipt counts only when that recorded environment satisfies the check's
  *requirement*: interpreter implementation and minor, the exact locked package set, flags and
  encodings at their defaults, behavior variables unset unless registered, and tool versions.

Lookup rule, the same for every caller: candidates are version-2 receipts whose recorded declaration
equals the asked declaration and whose fingerprint equals the subject's. A candidate counts when its
environment satisfies the requirement and, for a pass, its output log matches ``output_sha256``. A
sealed failure blocks even when its log is missing. The newest counted candidate decides. Version-1
receipts, interrupted receipts and failures from a non-satisfying environment neither pass nor
block. A seal-failing receipt stops the lookup and names the file; moving that file into the
store's ``quarantine/`` subdirectory is the operator's remedy.

Secret environment values are never recorded: variable digests cover normalized values. Commands
and test output must not contain credentials. This is local evidence integrity, not a signature or
trust service; deliberate local tampering is out of scope.
"""
from __future__ import annotations

import codecs
import contextlib
import copy
from functools import lru_cache
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import uuid


class EvidenceError(ValueError):
    pass


SCHEMA_VERSION = 2
ENGINE_DIR = Path(__file__).resolve().parent
CAPTURE = ENGINE_DIR / "test_evidence_capture.py"

# Names that can change what an interpreter does without a repository file changing. A name here
# must be unset in a check's environment unless the check registers it; the engine removes an
# unregistered one from the child's environment and the capture wrapper confirms the result.
BEHAVIOR_VARIABLES = (
    "PYTHONPATH", "PYTHONHOME", "PYTHONPLATLIBDIR", "PYTHONSAFEPATH", "PYTHONNOUSERSITE",
    "PYTHONSTARTUP", "PYTHONHASHSEED", "PYTHONOPTIMIZE", "PYTHONWARNINGS", "PYTHONUTF8",
    "PYTHONIOENCODING", "PYTHONDEVMODE",
)
# Interpreter defaults for sys.flags. A value outside this table must be falsy. The tolerated
# flags are decided by the build or the locale rather than by an environment the check controls
# (the encoding checks cover the locale), or do not change what a test observes. A requirement
# that registers a flag value is held to it, tolerated or not.
FLAG_DEFAULTS = {"hash_randomization": (1,), "int_max_str_digits": (-1, 4300)}
FLAG_TOLERATED = ("utf8_mode", "gil", "thread_inherit_context", "context_aware_warnings", "dont_write_bytecode")
SCHEDULING_FLAGS = ("--workers", "--records", "--timings")
STATUSES = ("passed", "failed", "inputs-changed", "interrupted")
LOG_COMPRESSION_THRESHOLD = 1024 * 1024
INTERRUPT_GRACE_SECONDS = 10


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- input projections
#
# A declaration may name, per path, the spans a release rewrites (``input_projections``). The path's
# digest then covers every other byte and not the located values. The kind set is closed. A kind
# applies only when it locates exactly one span, each located value has its strict format, and the
# spans of one path are disjoint. Anything else (an unknown kind, a duplicate locator, a nested
# same-named key, a malformed value, bytes that are not UTF-8) falls back to the raw digest, so an
# unrecognised change always invalidates. The projected digest starts from the fixed prefix
# ``projected:<sorted kinds>``; a raw digest is the bare sha256 of the file, so a raw file cannot
# equal a projected digest unless its own bytes begin with that prefix and hold the placeholder.
PROJECTION_PLACEHOLDER = "@@projected@@"
PROJECTION_KINDS = ("json-string:<top-level key>", "toml-project-version", "uv-lock-package-version:<name>",
                    "readme-footer-version", "generated-fingerprint-line")
_PROJECTION_STATIC = ("toml-project-version", "readme-footer-version", "generated-fingerprint-line")
_SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
# Line 1 of a staged public rendition. This is a second copy of the grammar in tools/sync_stage.py
# (FINGERPRINT_RE) because tools/ does not ship and the engine does. A change to one needs the other.
# The engine is stricter than sync_stage: line 1 must match in full, not merely contain a match.
_FINGERPRINT_LINE = re.compile(
    r"<!--\s*generated-from:\s*(?P<source>[^@\s]+)@sha256:(?P<digest>[0-9a-f]{64});"
    r"\s*model:\s*(?P<model>[^;]+);\s*date:\s*(?P<date>\d{4}-\d{2}-\d{2})\s*-->")
_TOML_HEADER = re.compile(r"\[\s*([^\[\]]*?)\s*\]\s*(?:#.*)?")
_PACKAGE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _valid_projection_kind(kind):
    if kind in _PROJECTION_STATIC:
        return True
    if kind.startswith("json-string:"):
        key = kind[len("json-string:"):]
        return bool(key) and "\n" not in key
    if kind.startswith("uv-lock-package-version:"):
        return bool(_PACKAGE_NAME.fullmatch(kind[len("uv-lock-package-version:"):]))
    return False


def _normalize_projections(projections):
    if not isinstance(projections, dict) or not projections:
        raise EvidenceError("input_projections must map paths to kind lists")
    result = {}
    for path, kinds in sorted(projections.items()):
        if (not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts
                or str(PurePosixPath(path)) != path):
            raise EvidenceError("input_projections paths must be normalized repository-relative paths")
        if (not isinstance(kinds, list) or not kinds or not all(isinstance(k, str) and _valid_projection_kind(k) for k in kinds)
                or len(set(kinds)) != len(kinds)):
            raise EvidenceError(f"input_projections for {path} must list distinct kinds from the closed set: "
                                + ", ".join(PROJECTION_KINDS))
        result[path] = sorted(kinds)
    return result


@lru_cache(maxsize=1)
def _footer_pattern():
    """FOOTER_RE of generate-readme-footer.py, which ships beside this engine, or None when it cannot load."""
    try:
        spec = importlib.util.spec_from_file_location("_crux_readme_footer", ENGINE_DIR / "generate-readme-footer.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.FOOTER_RE
    except (OSError, ImportError, AttributeError, SyntaxError, TypeError):
        return None


def _masked_matches(text, span, original, loads, mutate):
    """Whether masking ``span`` leaves a document equal to ``original`` with only ``mutate`` applied."""
    masked = text[:span[0]] + PROJECTION_PLACEHOLDER + text[span[1]:]
    expected = copy.deepcopy(original)
    mutate(expected)
    try:
        return loads(masked) == expected
    except ValueError:
        return False


def _json_string_end(text, start):
    """Index of the closing quote of the string whose opening quote is at ``start``, or None."""
    index = start + 1
    while index < len(text) and text[index] != '"':
        index += 2 if text[index] == "\\" else 1
    return index if index < len(text) else None


def _skip_space(text, index):
    while index < len(text) and text[index] in " \t\r\n":
        index += 1
    return index


def _locate_json_string(text, key):
    """The span of the one top-level string value named ``key``. Nested keys are never located."""
    try:
        original = json.loads(text)
    except ValueError:
        return None
    if not isinstance(original, dict) or not isinstance(original.get(key), str) or not _SEMVER.fullmatch(original[key]):
        return None
    stack, index, expect_key, found = [], 0, False, []
    while index < len(text):
        char = text[index]
        if char in " \t\r\n":
            index += 1
        elif char == '"':
            end = _json_string_end(text, index)
            if end is None:
                return None
            if len(stack) == 1 and stack[0] == "{" and expect_key:
                expect_key = False
                try:
                    named = json.loads(text[index:end + 1]) == key
                except ValueError:
                    return None
                if named:
                    value = _skip_space(text, _skip_space(text, end + 1) + 1)
                    value_end = _json_string_end(text, value) if text[value:value + 1] == '"' else None
                    found.append((value + 1, value_end) if value_end is not None else None)
            index = end + 1
        else:
            if char in "{[":
                stack.append(char)
                expect_key = char == "{" and len(stack) == 1
            elif char in "}]":
                if not stack:
                    return None
                stack.pop()
            elif char == "," and len(stack) == 1:
                expect_key = stack[0] == "{"
            index += 1
    if len(found) != 1 or found[0] is None or text[found[0][0]:found[0][1]] != original[key]:
        return None
    ok = _masked_matches(text, found[0], original, json.loads, lambda doc: doc.__setitem__(key, PROJECTION_PLACEHOLDER))
    return found[0] if ok else None


def _locate_toml_project_version(text):
    """The span of ``version`` in the top-level ``[project]`` table of pyproject.toml."""
    try:
        original = tomllib.loads(text)
    except ValueError:
        return None
    project = original.get("project")
    if not isinstance(project, dict) or not isinstance(project.get("version"), str) or not _SEMVER.fullmatch(project["version"]):
        return None
    pattern = re.compile(r'(\s*version\s*=\s*")(' + _SEMVER.pattern + r')("\s*(?:#.*)?)')
    table, offset, spans = None, 0, []
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        header = _TOML_HEADER.fullmatch(stripped)
        if header:
            table = header.group(1)
        elif stripped.startswith("[["):
            table = None
        elif table == "project":
            match = pattern.fullmatch(line.rstrip("\r\n"))
            if match:
                spans.append((offset + match.start(2), offset + match.end(2)))
        offset += len(line)
    if len(spans) != 1 or text[spans[0][0]:spans[0][1]] != project["version"]:
        return None
    ok = _masked_matches(text, spans[0], original, tomllib.loads,
                         lambda doc: doc["project"].__setitem__("version", PROJECTION_PLACEHOLDER))
    return spans[0] if ok else None


def _locate_uv_lock_version(text, name):
    """The span of ``version`` in the one ``[[package]]`` entry named ``name`` of uv.lock."""
    try:
        original = tomllib.loads(text)
    except ValueError:
        return None
    wanted = normalize_package_name(name)
    def named(entry):
        return isinstance(entry, dict) and isinstance(entry.get("name"), str) and normalize_package_name(entry["name"]) == wanted
    entries = [entry for entry in original.get("package", []) if named(entry)]
    if len(entries) != 1 or not isinstance(entries[0].get("version"), str) or not _SEMVER.fullmatch(entries[0]["version"]):
        return None
    name_line = re.compile(r'\s*name\s*=\s*"([^"]*)"\s*(?:#.*)?')
    version_line = re.compile(r'(\s*version\s*=\s*")(' + _SEMVER.pattern + r')("\s*(?:#.*)?)')
    in_package, block_name, block_span, offset, spans = False, None, None, 0, []
    def close():
        if in_package and block_name is not None and block_span is not None and normalize_package_name(block_name) == wanted:
            spans.append(block_span)
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == "[[package]]" or _TOML_HEADER.fullmatch(stripped) or stripped.startswith("[["):
            close()
            in_package, block_name, block_span = stripped == "[[package]]", None, None
        elif in_package:
            body = line.rstrip("\r\n")
            name_match, version_match = name_line.fullmatch(body), version_line.fullmatch(body)
            if name_match:
                block_name = name_match.group(1)
            elif version_match:
                block_span = (offset + version_match.start(2), offset + version_match.end(2))
        offset += len(line)
    close()
    if len(spans) != 1 or text[spans[0][0]:spans[0][1]] != entries[0]["version"]:
        return None
    def mutate(doc):
        for entry in doc["package"]:
            if named(entry):
                entry["version"] = PROJECTION_PLACEHOLDER
    return spans[0] if _masked_matches(text, spans[0], original, tomllib.loads, mutate) else None


def _locate_readme_footer(text):
    pattern = _footer_pattern()
    if pattern is None:
        return None
    matches = list(pattern.finditer(text))
    if len(matches) != 1 or not _SEMVER.fullmatch(matches[0].group(2)):
        return None
    return matches[0].span(2)


def _locate_fingerprint_line(text):
    line = text.split("\n", 1)[0]
    return (0, len(line)) if _FINGERPRINT_LINE.fullmatch(line) else None


def _locate(text, kind):
    if kind.startswith("json-string:"):
        return _locate_json_string(text, kind[len("json-string:"):])
    if kind.startswith("uv-lock-package-version:"):
        return _locate_uv_lock_version(text, kind[len("uv-lock-package-version:"):])
    return {"toml-project-version": _locate_toml_project_version, "readme-footer-version": _locate_readme_footer,
            "generated-fingerprint-line": _locate_fingerprint_line}.get(kind, lambda _text: None)(text)


def projected_digest(data, kinds):
    """The projected digest of ``data`` under ``kinds``, or None when the raw digest must be used."""
    kinds = tuple(sorted(kinds))
    if not kinds or len(set(kinds)) != len(kinds) or not all(isinstance(k, str) and _valid_projection_kind(k) for k in kinds):
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    spans = []
    for kind in kinds:
        span = _locate(text, kind)
        if span is None:
            return None
        spans.append(span)
    spans.sort()
    if any(later[0] < earlier[1] for earlier, later in zip(spans, spans[1:])):
        return None
    pieces, cursor = [], 0
    for start, end in spans:
        pieces += [text[cursor:start], PROJECTION_PLACEHOLDER]
        cursor = end
    pieces.append(text[cursor:])
    prefix = ("projected:" + ",".join(kinds)).encode() + b"\0"
    return hashlib.sha256(prefix + "".join(pieces).encode()).hexdigest()


def input_digest(data, kinds=None):
    """The digest an input contributes: projected when ``kinds`` apply, the raw sha256 otherwise."""
    if kinds:
        projected = projected_digest(data, kinds)
        if projected is not None:
            return projected
    return hashlib.sha256(data).hexdigest()


def _git_blob(root, blob_id):
    result = subprocess.run(["git", "cat-file", "blob", blob_id], cwd=root, capture_output=True)
    return result.stdout if result.returncode == 0 else None


def _projected_git_entry(root, entry, projections, blob_field):
    """``entry`` with its blob id replaced by the projected digest of that blob, or ``entry`` unchanged.

    ``blob_field`` is the space-separated field holding the blob id: 1 for an index entry
    (``mode blob stage``), 2 for a tree entry (``mode type blob``). Only a regular file projects (an
    index entry only at stage 0); the fallback is the raw blob id, exactly as for a worktree file.
    """
    head, separator, name = entry.partition(b"\t")
    kinds = projections.get(os.fsdecode(name))
    fields = head.split(b" ")
    if not kinds or not separator or len(fields) != 3 or fields[0] not in (b"100644", b"100755"):
        return entry
    if (fields[2] != b"0") if blob_field == 1 else (fields[1] != b"blob"):
        return entry
    blob = _git_blob(root, fields[blob_field].decode())
    projected = projected_digest(blob, kinds) if blob is not None else None
    if projected is None:
        return entry
    fields[blob_field] = projected.encode()
    return b" ".join(fields) + separator + name


_PYTHON_TOKEN = re.compile(r"^python(\d+(\.\d+)*)?(\.exe)?$")


def _is_python(token):
    return bool(_PYTHON_TOKEN.match(os.path.basename(token)))


def canonical_command(command):
    """The command without the interpreter path and without scheduling arguments."""
    result = list(command)
    entry = 0
    if result and _is_python(result[0]):
        result[0] = "python"
        entry = 1
    if len(result) > entry and os.path.basename(result[entry]) == "parallel_suite.py":
        kept = result[:entry + 1]
        index = entry + 1
        while index < len(result):
            if result[index] in SCHEDULING_FLAGS:
                if index + 1 == len(result):
                    raise EvidenceError("missing scheduling argument")
                index += 2
            else:
                kept.append(result[index])
                index += 1
        result = kept
    return result


def _names(values, what):
    if not isinstance(values, list) or not all(isinstance(x, str) and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", x) for x in values):
        raise EvidenceError(f"{what} must list variable names")


def _normalize_requirement(requirement):
    allowed = {"interpreter", "packages", "isolated", "tools", "variables", "flags", "freshness_seconds"}
    if not isinstance(requirement, dict) or set(requirement) - allowed:
        raise EvidenceError("unknown requirement fields")
    result = {}
    interpreter = requirement.get("interpreter")
    if interpreter is not None:
        if not isinstance(interpreter, dict) or set(interpreter) - {"implementation", "minors"}:
            raise EvidenceError("interpreter requires implementation and minors")
        minors = interpreter.get("minors")
        if minors is not None and (not isinstance(minors, list) or not minors
                                   or not all(isinstance(m, str) and re.fullmatch(r"\d+\.\d+", m) for m in minors)):
            raise EvidenceError("interpreter minors must list major.minor strings")
        implementation = interpreter.get("implementation", "cpython")
        if not isinstance(implementation, str) or not implementation:
            raise EvidenceError("interpreter implementation must be a name")
        result["interpreter"] = {"implementation": implementation.lower(), "minors": minors}
    packages = requirement.get("packages")
    if packages is not None:
        if not isinstance(packages, dict) or len(packages) != 1 or set(packages) - {"lock", "pins"}:
            raise EvidenceError("packages must name exactly one of lock or pins")
        if "pins" in packages:
            pins = packages["pins"]
            if not isinstance(pins, list) or not all(isinstance(p, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*==[^\s;]+", p) for p in pins):
                raise EvidenceError("pins must list name==version strings")
            result["packages"] = {"pins": sorted(pins)}
        else:
            lock = packages["lock"]
            if (not isinstance(lock, dict) or set(lock) - {"path", "source", "project", "dev", "groups", "extras", "project_version"}
                    or lock.get("path", "uv.lock") != "uv.lock" or lock.get("source", "subject") not in ("subject", "dev-root")):
                raise EvidenceError("lock must reference uv.lock from the subject or the dev root")
            for key in ("groups", "extras"):
                if not isinstance(lock.get(key, []), list) or not all(isinstance(x, str) and x for x in lock.get(key, [])):
                    raise EvidenceError(f"lock {key} must list names")
            for key in ("project", "dev"):
                if type(lock.get(key, False)) is not bool:
                    raise EvidenceError(f"lock {key} must be boolean")
            if lock.get("project_version", "bound") not in ("bound", "release-neutral"):
                raise EvidenceError("lock project_version must be bound or release-neutral")
            if lock.get("project_version") == "release-neutral" and not lock.get("project", False):
                raise EvidenceError("lock project_version release-neutral needs a lock that includes the project")
            result["packages"] = {"lock": {"path": "uv.lock", "source": lock.get("source", "subject"),
                                           "project": lock.get("project", False), "dev": lock.get("dev", False),
                                           "groups": sorted(lock.get("groups", [])), "extras": sorted(lock.get("extras", []))}}
            if lock.get("project_version") == "release-neutral":
                # Emitted only when set, so a requirement without it normalizes exactly as before.
                result["packages"]["lock"]["project_version"] = "release-neutral"
    if "isolated" in requirement:
        if type(requirement["isolated"]) is not bool:
            raise EvidenceError("isolated must be boolean")
        result["isolated"] = requirement["isolated"]
    if "tools" in requirement:
        tools = requirement["tools"]
        if not isinstance(tools, list) or not all(isinstance(t, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", t) for t in tools):
            raise EvidenceError("tools must list executable names")
        result["tools"] = sorted(set(tools))
    if "variables" in requirement:
        variables = requirement["variables"]
        if isinstance(variables, list):
            _names(variables, "variables")
            variables = {name: None for name in variables}
        if not isinstance(variables, dict) or not all(isinstance(k, str) and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", k)
                                                      and (v is None or isinstance(v, str)) for k, v in variables.items()):
            raise EvidenceError("variables must map names to a value template or null")
        result["variables"] = dict(sorted(variables.items()))
    if "flags" in requirement:
        flags = requirement["flags"]
        if not isinstance(flags, dict) or not all(isinstance(k, str) and type(v) in (int, bool) for k, v in flags.items()):
            raise EvidenceError("flags must map flag names to integer values")
        result["flags"] = dict(sorted(flags.items()))
    freshness = requirement.get("freshness_seconds")
    if freshness is not None:
        if type(freshness) not in (int, float) or not 0 < freshness < float("inf"):
            raise EvidenceError("freshness_seconds must be positive and finite")
        result["freshness_seconds"] = freshness
    return result


def normalize(declaration):
    allowed = {"check_id", "command", "inputs", "environment", "freshness_seconds", "git_tracked", "exclude_inputs", "requirement",
               "input_projections"}
    if not isinstance(declaration, dict) or set(declaration) - allowed:
        raise EvidenceError("unknown check declaration fields")
    result = dict(declaration)
    if not isinstance(result.get("check_id"), str) or not result["check_id"].strip():
        raise EvidenceError("check_id must be nonempty")
    for name in ("command", "inputs"):
        if not isinstance(result.get(name), list) or not result[name] or not all(isinstance(x, str) and x for x in result[name]):
            raise EvidenceError(f"{name} must be a nonempty string array")
    result["command"] = canonical_command(result["command"])
    result.setdefault("environment", [])
    if not isinstance(result["environment"], list) or not all(isinstance(x, str) and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", x) for x in result["environment"]):
        raise EvidenceError("environment must list variable names")
    for pattern in result["inputs"]:
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise EvidenceError("inputs must stay inside the repository")
    if "git_tracked" in result and type(result["git_tracked"]) is not bool:
        raise EvidenceError("git_tracked must be boolean")
    exclusions = result.get("exclude_inputs", [])
    if not isinstance(exclusions, list) or not all(isinstance(x, str) and x and not Path(x).is_absolute() and ".." not in Path(x).parts for x in exclusions):
        raise EvidenceError("exclude_inputs must list repository-relative paths")
    freshness = result.get("freshness_seconds")
    if freshness is not None and (type(freshness) not in (int, float) or not 0 < freshness < float("inf")):
        raise EvidenceError("freshness_seconds must be positive and finite")
    if "input_projections" in result:
        result["input_projections"] = _normalize_projections(result["input_projections"])
    if "requirement" in result:
        result["requirement"] = _normalize_requirement(result["requirement"])
        if result["command"][0] != "python" and (result["requirement"].get("interpreter") or result["requirement"].get("packages")
                                                 or result["requirement"].get("isolated")):
            raise EvidenceError("an interpreter, package or isolation requirement needs a command that starts with a python interpreter")
    return result


def registered_only_fields(declaration):
    """The declaration fields only a registered check may carry, present in the normalized ``declaration``.

    ``input_projections`` and a release-neutral lock widen what a receipt may ignore, so the command
    line refuses them unless the declaration equals the registered one.
    """
    fields = []
    if "input_projections" in declaration:
        fields.append("input_projections")
    lock = (declaration.get("requirement", {}).get("packages") or {}).get("lock") or {}
    if "project_version" in lock:
        fields.append("project_version")
    return fields


def requirement_names_project_version(requirement):
    """Whether a raw requirement carries ``project_version`` in any form, even the default."""
    lock = ((requirement or {}).get("packages") or {}).get("lock") if isinstance(requirement, dict) else None
    return isinstance(lock, dict) and "project_version" in lock


def effective_requirement(declaration, root=None):
    """The declared requirement, or the default: the subject's locked project environment."""
    declared = declaration.get("requirement", {})
    requirement = {"interpreter": declared.get("interpreter"), "packages": declared.get("packages"),
                   "isolated": declared.get("isolated", False), "tools": declared.get("tools", []),
                   "variables": declared.get("variables", {}), "flags": declared.get("flags", {}),
                   "freshness_seconds": declared.get("freshness_seconds", declaration.get("freshness_seconds"))}
    if requirement["interpreter"] is None and declaration["command"][0] == "python":
        requirement["interpreter"] = {"implementation": "cpython", "minors": None}
    if "packages" not in declared and requirement["interpreter"] is not None and root is not None \
            and (Path(root) / "uv.lock").is_file() and (Path(root) / "pyproject.toml").is_file():
        requirement["packages"] = {"lock": {"path": "uv.lock", "source": "subject", "project": True,
                                            "dev": False, "groups": [], "extras": []}}
    return requirement


def permitted_variables(declaration, requirement):
    return sorted(set(declaration.get("environment", [])) | set(requirement["variables"]))


def _lock_file(root, source_root, lock):
    if lock["source"] == "dev-root" and source_root is None:
        raise EvidenceError("the requirement names the dev root's uv.lock; pass the dev root as source_root")
    base = Path(source_root if lock["source"] == "dev-root" else root)
    return base, base / lock["path"]


def _lock_binding(lock_path, lock):
    """The digest a receipt records for the requirement's lock.

    A requirement that includes the project installs the project at its version, so the raw lock
    bytes bind it. A requirement that leaves the project out installs exactly the locked export
    (hashes included), which names no project: a version-only edit of the project's own entry
    leaves that export unchanged and must not invalidate the receipt. Every other edit that
    changes what is installed (a package, its version, its hashes, a marker, a source) changes the
    export. The export's comments carry the command line and the dependents, so they are dropped.
    A digest recorded before this binding was the raw bytes: it no longer matches, so the next
    lookup executes once and records the new digest.

    ``project_version: release-neutral`` (a requirement that includes the project) binds the project
    by name instead of by version: the digest is the project-free export plus a fixed editable entry
    for the project, with no version. Every third-party package, hash, marker and source still changes
    it. The package-set comparison matches the project distribution by name only (see
    ``environment_problems``). Limit: an installed crux distribution whose version differs from
    pyproject.toml is no longer detected. The version-equality check never proved editable
    provenance either, and the project's source files are hashed as inputs.
    """
    neutral = lock.get("project_version") == "release-neutral"
    if lock["project"] and not neutral:
        return file_digest(lock_path)
    lines = [line for line in uv_export(lock_path.parent, lock, hashes=True).replace("\\\n", " ").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    if lock["project"]:
        lines.append("-e .")
    return digest({"lock_export": lines})


def snapshot(root, declaration, source_root=None):
    """The subject's declared projection and its fingerprint. Nothing here reads the environment."""
    root = Path(root).resolve()
    declaration = normalize(declaration)
    files = {}
    def excluded(relative):
        return any(relative == prefix.rstrip("/") or relative.startswith(prefix.rstrip("/") + "/")
                   for prefix in declaration.get("exclude_inputs", []))
    projections = declaration.get("input_projections", {})
    selection = [(pattern, sorted(root.glob(pattern))) for pattern in declaration["inputs"]]
    git_inventory = None
    git_head_tree = None
    if declaration.get("git_tracked", False):
        git = subprocess.run(["git", "ls-files", "--stage", "-z"], cwd=root, capture_output=True)
        if git.returncode == 0:
            inventory_entries = []
            for entry in git.stdout.split(b"\0"):
                if not entry:
                    continue
                name = os.fsdecode(entry.split(b"\t", 1)[1])
                if Path(name).is_absolute() or ".." in Path(name).parts:
                    raise EvidenceError("tracked input escapes repository")
                if excluded(name):
                    continue
                inventory_entries.append(_projected_git_entry(root, entry, projections, 1) if projections else entry)
                path = root / name
                selection.append((name, [path] if path.exists() or path.is_symlink() else []))
            git_inventory = hashlib.sha256(b"\0".join(inventory_entries)).hexdigest()
            head = subprocess.run(["git", "ls-tree", "-r", "-z", "HEAD"], cwd=root, capture_output=True)
            if head.returncode == 0:
                # HEAD-relative assertions depend on committed contents, not on the commit ID.
                # Only the non-excluded projection counts, as for the index.
                entries = [_projected_git_entry(root, entry, projections, 2) if projections else entry
                           for entry in head.stdout.split(b"\0") if entry
                           and not excluded(os.fsdecode(entry.split(b"\t", 1)[1]))]
                git_head_tree = hashlib.sha256(b"\0".join(entries)).hexdigest()

    for pattern, matches in selection:
        if excluded(pattern):
            continue
        if not matches:
            files[pattern] = {"missing": True}
        for match in matches:
            paths = sorted(match.rglob("*")) if match.is_dir() and not match.is_symlink() else [match]
            for path in paths:
                relative = path.relative_to(root).as_posix()
                if excluded(relative):
                    continue
                if any(part in (".git", "__pycache__", ".pytest_cache", ".venv") and part not in Path(pattern).parts for part in path.relative_to(root).parts):
                    continue
                if relative == ".crux-test-evidence" or relative.startswith(".crux-test-evidence/"):
                    continue
                if path.is_symlink():
                    raise EvidenceError(f"symlink input requires an explicit real input path: {relative}")
                if path.is_file():
                    sha256 = input_digest(path.read_bytes(), projections[relative]) if relative in projections else file_digest(path)
                    files[relative] = {"sha256": sha256, "executable": bool(path.stat().st_mode & 0o111)}
    lock_digest = None
    packages = effective_requirement(declaration, root)["packages"]
    if packages and "lock" in packages:
        _, lock_path = _lock_file(root, source_root, packages["lock"])
        if not lock_path.is_file():
            raise EvidenceError(f"the requirement's lock file is missing: {lock_path.name}")
        lock_digest = _lock_binding(lock_path, packages["lock"])
    value = {"declaration": declaration, "files": files, "git_inventory": git_inventory,
             "git_head_tree": git_head_tree, "lock_sha256": lock_digest}
    return {"fingerprint": digest(value), "inputs": files, "lock_sha256": lock_digest}


def git_common_store(base):
    try:
        git = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=base, capture_output=True, text=True)
    except OSError:
        return None
    if git.returncode:
        return None
    return Path(git.stdout.strip()) / "crux" / "test-evidence"


def durable_store(dev_root):
    """The one durable store: ``<git-common-dir>/crux/test-evidence`` of the dev checkout."""
    store = git_common_store(Path(dev_root).resolve())
    if store is None:
        raise EvidenceError("the dev root is not a Git repository, so it has no durable evidence store")
    return store


def durable_store_environment(dev_root, environ=None):
    """The environment a release child inherits so it writes to the durable store and no other.

    Refuses when the caller's environment already names another store, so the release path never
    starts a check that would write elsewhere.
    """
    store = durable_store(dev_root)
    existing = (environ if environ is not None else os.environ).get("CRUX_TEST_EVIDENCE_STORE")
    if existing and os.path.realpath(existing) != os.path.realpath(store):
        raise EvidenceError(f"test evidence store override {existing} is not the durable store {store}; the release path refuses it")
    return {"CRUX_TEST_EVIDENCE_STORE": str(store), "CRUX_TEST_EVIDENCE_DURABLE_ONLY": "1"}


def storage(root, source_root=None):
    root = Path(root).resolve()
    base = Path(source_root).resolve() if source_root is not None else root
    override = os.environ.get("CRUX_TEST_EVIDENCE_STORE")
    if override:
        current = Path(override).absolute()
    else:
        found = git_common_store(base)
        current = found if found is not None else base / ".crux-test-evidence"
    if os.environ.get("CRUX_TEST_EVIDENCE_DURABLE_ONLY") == "1":
        # The release path writes receipts only to the dev checkout's durable store. A cleanup of
        # a stage, a throwaway environment or /tmp must not remove release evidence.
        expected = durable_store(base)
        if current.resolve() != expected.resolve() and Path(os.path.realpath(current)) != Path(os.path.realpath(expected)):
            raise EvidenceError(f"test evidence store {current} is not the durable store {expected}; the release path refuses an override")
    for path in [*reversed(current.parents), current]:
        if path.is_symlink():
            raise EvidenceError("evidence directory must not be a symlink")
    current.mkdir(mode=0o700, parents=True, exist_ok=True)
    return current


V2_REQUIRED = ("environment", "tools", "lock_sha256", "source_revision")


def _read(path):
    if path.is_symlink() or not path.is_file():
        raise EvidenceError("evidence must be a regular file")
    try:
        record = json.loads(path.read_text())
        seal = record.pop("record_sha256")
        if digest(record) != seal:
            raise EvidenceError("evidence record integrity mismatch")
        if record.get("id") != path.stem or not re.fullmatch(r"TE-[0-9a-f]{32}", path.stem):
            raise EvidenceError("evidence identity mismatch")
        if record.get("output") != record["id"] + ".log":
            raise EvidenceError("invalid evidence output path")
        version = record.get("schema_version")
        if version not in (1, 2):
            raise EvidenceError("unknown evidence schema version")
        if record.get("status") not in (STATUSES if version == 2 else STATUSES[:3]):
            raise EvidenceError("invalid evidence result")
        if version == 2 and any(name not in record for name in V2_REQUIRED):
            raise EvidenceError("evidence lacks version 2 fields")
        normalize(record["declaration"])
        if record["status"] == "passed" and (record["returncode"] != 0 or record["fingerprint"] != record["end_fingerprint"]):
            raise EvidenceError("passing evidence has failed or changed inputs")
        record["record_sha256"] = seal
        return record
    except (ValueError, KeyError, TypeError) as exc:
        detail = f" ({exc})" if isinstance(exc, EvidenceError) else ""
        raise EvidenceError(f"invalid evidence: {path.name}{detail}") from exc


def read_receipts(store):
    """Every receipt in the store, failing closed on any unreadable one and naming the file.

    ``quarantine/`` and other subdirectories are not read.
    """
    return [_read(path) for path in sorted(Path(store).glob("TE-*.json"))]


# ---------------------------------------------------------------- output logs and completeness

def _log_bytes(directory, record):
    """The decompressed log bytes, a withheld marker, or None when the log is absent."""
    directory = Path(directory)
    plain = directory / record["output"]
    for candidate, compressed in ((plain, False), (plain.with_name(plain.name + ".gz"), True)):
        if candidate.is_symlink():
            return "invalid"
        if candidate.is_file():
            try:
                data = candidate.read_bytes()
                return gzip.decompress(data) if compressed else data
            except (OSError, EOFError, gzip.BadGzipFile):
                return "invalid"
    if plain.with_name(plain.name + ".withheld.json").is_file():
        return "withheld"
    return None


def log_state(directory, record):
    """``ok``, ``missing``, ``mismatch``, ``withheld`` or ``invalid`` for the record's output log."""
    data = _log_bytes(directory, record)
    if data is None:
        return "missing"
    if isinstance(data, str):
        return data
    return "ok" if hashlib.sha256(data).hexdigest() == record["output_sha256"] else "mismatch"


def completeness(directory, evidence_id):
    """Whether the receipt and its log are the bytes that were recorded. Reads nothing else.

    Complete means: the receipt is present, its ``record_sha256`` seal verifies, and the log it
    names is present with a sha256 equal to ``output_sha256`` over the decompressed bytes. The
    verdict says nothing about reuse; see :func:`reuse_eligibility`.
    """
    directory = Path(directory)
    path = directory / (evidence_id + ".json")
    verdict = {"id": evidence_id, "complete": False, "seal": "missing", "log": "unknown",
               "problems": [], "files": [str(path)], "record": None}
    if not re.fullmatch(r"TE-[0-9a-f]{32}", evidence_id):
        verdict["problems"].append("invalid evidence id")
        return verdict
    if not path.is_file() or path.is_symlink():
        verdict["problems"].append(f"receipt missing: {path.name}")
        return verdict
    try:
        record = _read(path)
    except EvidenceError as exc:
        verdict["seal"] = "invalid"
        verdict["problems"].append(str(exc))
        return verdict
    verdict["seal"] = "valid"
    verdict["record"] = record
    verdict["log"] = log_state(directory, record)
    verdict["files"].append(str(directory / record["output"]))
    if verdict["log"] != "ok":
        verdict["problems"].append(f"output log {verdict['log']}: {record['output']}")
    verdict["complete"] = verdict["log"] == "ok"
    return verdict


def retention_copy(source_store, evidence_id, destination, *, exact=()):
    """Copy a receipt and its log to ``destination`` after the secret scan.

    Every copied file first passes ``secret_scan`` on its uncompressed bytes. A match withholds
    that file and records the withholding in its place (``<name>.withheld.json``, holding the
    shape names and the file's sha256 and size, never a value). A log above 1 MiB is gzip-compressed
    after the scan. Returns ``{"copied": [...], "withheld": [...], "compressed": [...]}``.
    """
    import secret_scan
    source_store, destination = Path(source_store), Path(destination)
    if not re.fullmatch(r"TE-[0-9a-f]{32}", evidence_id):
        raise EvidenceError("invalid evidence ID")
    destination.mkdir(parents=True, exist_ok=True)
    result = {"copied": [], "withheld": [], "compressed": []}
    record = _read(source_store / (evidence_id + ".json"))
    for name in (evidence_id + ".json", record["output"]):
        source = source_store / name
        if source.is_symlink() or not source.is_file():
            result["withheld"].append({"file": name, "shapes": ["missing"]})
            continue
        data = source.read_bytes()
        shapes = secret_scan.scan_text(data.decode("utf-8", "replace"), exact=exact)
        if shapes:
            marker = {"withheld": name, "reason": "secret-scan", "shapes": shapes,
                      "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
            (destination / (name + ".withheld.json")).write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n")
            result["withheld"].append({"file": name, "shapes": shapes})
            continue
        if name.endswith(".log") and len(data) > LOG_COMPRESSION_THRESHOLD:
            (destination / (name + ".gz")).write_bytes(gzip.compress(data, mtime=0))
            result["compressed"].append(name)
        else:
            (destination / name).write_bytes(data)
        result["copied"].append(name)
    return result


def scan_logs(store, evidence_ids, *, exact=()):
    """Secret-scan the output log of each receipt. Returns ``[{"file", "shapes"}]`` for matches."""
    import secret_scan
    findings = []
    for evidence_id in evidence_ids:
        record = _read(Path(store) / (evidence_id + ".json"))
        data = _log_bytes(store, record)
        if isinstance(data, bytes):
            shapes = secret_scan.scan_text(data.decode("utf-8", "replace"), exact=exact)
            if shapes:
                findings.append({"file": record["output"], "shapes": shapes})
    return findings


# ---------------------------------------------------------------- markers, lock export, packages

_MARKER_TOKEN = re.compile(r"\s*(===|==|!=|<=|>=|~=|<|>|\(|\)|'[^']*'|\"[^\"]*\"|[A-Za-z_][A-Za-z0-9_.]*)")
_VERSION = re.compile(r"^\s*v?(\d+(?:\.\d+)*)(?:[-_.]?(a|alpha|b|beta|c|rc|pre|preview)[-_.]?(\d*))?"
                      r"(?:[-_.]?post[-_.]?(\d*))?(?:[-_.]?dev[-_.]?(\d*))?(?:\+[A-Za-z0-9.]+)?\s*$", re.I)
_PRE_ORDER = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "c": 2, "rc": 2, "pre": 2, "preview": 2}


def _version_key(text):
    match = _VERSION.match(text)
    if not match:
        return None
    release = [int(x) for x in match.group(1).split(".")]
    while len(release) > 1 and release[-1] == 0:
        release.pop()
    pre = (_PRE_ORDER[match.group(2).lower()], int(match.group(3) or 0)) if match.group(2) else None
    post = int(match.group(4) or 0) if match.group(4) is not None else None
    dev = int(match.group(5) or 0) if match.group(5) is not None else None
    low, high = (-1, 0), (10 ** 9, 0)
    if pre is None and post is None and dev is not None:
        pre = low
    elif pre is None:
        pre = high
    return (tuple(release), pre, -1 if post is None else post, high[0] if dev is None else dev)


def _compare(left, op, right):
    if op in ("in", "not in"):
        return (left in right) == (op == "in")
    if op == "===":
        return left == right
    wildcard = op in ("==", "!=") and right.endswith(".*")
    lk = _version_key(left)
    rk = _version_key(right[:-2] if wildcard else right)
    if lk is not None and rk is not None:
        if wildcard:
            width = len(rk[0])
            equal = lk[0][:width] == rk[0] or (lk[0] + (0,) * width)[:width] == rk[0]
            return equal if op == "==" else not equal
        if op == "~=":
            width = max(len(rk[0]) - 1, 1)
            return lk >= rk and (lk[0] + (0,) * width)[:width] == (rk[0] + (0,) * width)[:width]
        return {"==": lk == rk, "!=": lk != rk, "<": lk < rk, "<=": lk <= rk, ">": lk > rk, ">=": lk >= rk}[op]
    if op in ("==", "!="):
        return (left == right) == (op == "==")
    raise EvidenceError(f"marker operator {op} needs versions: {left!r} {right!r}")


def evaluate_marker(marker, environment):
    """Evaluate a PEP 508 environment marker offline against a recorded marker environment."""
    tokens, position = [], 0
    marker = marker.strip()
    while position < len(marker):
        match = _MARKER_TOKEN.match(marker, position)
        if not match:
            raise EvidenceError(f"unsupported marker syntax: {marker!r}")
        tokens.append(match.group(1))
        position = match.end()
    # Join "not" "in" into one operator.
    merged, index = [], 0
    while index < len(tokens):
        if tokens[index] == "not" and index + 1 < len(tokens) and tokens[index + 1] == "in":
            merged.append("not in")
            index += 2
        else:
            merged.append(tokens[index])
            index += 1
    state = {"i": 0}
    def peek():
        return merged[state["i"]] if state["i"] < len(merged) else None
    def take():
        token = peek()
        state["i"] += 1
        return token
    def value(token):
        if token is None:
            raise EvidenceError(f"incomplete marker: {marker!r}")
        if token[0] in "'\"":
            return token[1:-1]
        if token == "extra":
            return ""
        if token not in environment:
            raise EvidenceError(f"marker variable {token} is not in the recorded marker environment")
        return environment[token]
    def atom():
        if peek() == "(":
            take()
            result = disjunction()
            if take() != ")":
                raise EvidenceError(f"unbalanced marker: {marker!r}")
            return result
        left = value(take())
        op = take()
        if op not in ("===", "==", "!=", "<=", ">=", "~=", "<", ">", "in", "not in"):
            raise EvidenceError(f"unsupported marker operator in {marker!r}")
        return _compare(left, op, value(take()))
    def conjunction():
        result = atom()
        while peek() == "and":
            take()
            result = atom() and result
        return result
    def disjunction():
        result = conjunction()
        while peek() == "or":
            take()
            result = conjunction() or result
        return result
    result = disjunction()
    if peek() is not None:
        raise EvidenceError(f"trailing marker text: {marker!r}")
    return result


def normalize_package_name(name):
    return re.sub(r"[-_.]+", "-", name).lower()


_EXPORT_LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s;]+)\s*(?:;\s*(.*))?$")


def parse_export(text):
    """``(name, version, marker-or-None)`` for each requirement in ``uv export`` output."""
    entries = []
    for line in text.replace("\\\n", " ").splitlines():
        line = line.split(" #", 1)[0].strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        line = re.sub(r"\s+--hash=\S+", "", line)
        match = _EXPORT_LINE.match(line)
        if not match:
            raise EvidenceError(f"unsupported lock export line: {line!r}")
        entries.append((normalize_package_name(match.group(1)), match.group(2), (match.group(3) or "").strip() or None))
    return entries


def uv_export(project_dir, lock, *, hashes=False):
    """Run ``uv export`` against the frozen lock. The lock is never updated."""
    command = ["uv", "export", "--frozen", "--offline", "-q", "--no-emit-project", "--project", str(project_dir)]
    if not hashes:
        command.append("--no-hashes")
    if not lock.get("dev"):
        command.append("--no-dev")
    for group in lock.get("groups", []):
        command += ["--group", group]
    for extra in lock.get("extras", []):
        command += ["--extra", extra]
    try:
        result = subprocess.run(command, capture_output=True, text=True, cwd=project_dir)
    except OSError as exc:
        raise EvidenceError(f"uv is unavailable to export the lock: {exc}") from exc
    if result.returncode:
        raise EvidenceError("uv export failed: " + result.stderr.strip()[:300])
    return result.stdout


def project_distribution(project_dir):
    data = tomllib.loads((Path(project_dir) / "pyproject.toml").read_text())
    project = data.get("project", {})
    if "name" not in project or "version" not in project:
        raise EvidenceError("pyproject.toml needs a static project name and version")
    return normalize_package_name(project["name"]), str(project["version"])


class _Context:
    """What one lookup needs beyond the receipts: the lock's export and the machine's tool versions."""

    def __init__(self, root, source_root):
        self.root, self.source_root = root, source_root
        self._exports = {}
        self._tools = {}

    def expected_packages(self, spec, marker_environment):
        if "pins" in spec:
            return {(normalize_package_name(name), version) for name, version in (p.split("==", 1) for p in spec["pins"])}
        lock = spec["lock"]
        key = json.dumps(lock, sort_keys=True)
        base, _ = _lock_file(self.root, self.source_root, lock)
        if key not in self._exports:
            project = project_distribution(base) if lock["project"] else None
            if project and lock.get("project_version") == "release-neutral":
                project = (project[0], None)  # name only; environment_problems matches it by name
            self._exports[key] = (parse_export(uv_export(base, lock)), project)
        entries, project = self._exports[key]
        expected = {(n, v) for n, v, marker in entries if marker is None or evaluate_marker(marker, marker_environment)}
        if project:
            expected.add(project)
        return expected

    def tool(self, name):
        if name not in self._tools:
            self._tools[name] = observe_tools([name])[name]
        return self._tools[name]


def observe_tools(names, env=None):
    """Each executable's resolved path and ``--version`` first line on this machine."""
    observed = {}
    for name in names:
        path = shutil.which(name, path=(env or os.environ).get("PATH"))
        version = None
        if path:
            try:
                result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=30, env=env)
                lines = (result.stdout or result.stderr).strip().splitlines()
                version = lines[0].strip() if result.returncode == 0 and lines else "unreadable"
            except (OSError, subprocess.SubprocessError):
                version = "unreadable"
        observed[name] = {"path": path, "version": version}
    return observed


def _utf8(encoding):
    try:
        return codecs.lookup(encoding).name == "utf-8"
    except (LookupError, TypeError):
        return False


def _flag_problems(flags, overrides):
    problems = []
    for name, value in sorted(flags.items()):
        if name in FLAG_TOLERATED:
            continue
        if name in overrides:
            if value != overrides[name]:
                problems.append(f"sys.flags.{name} is {value!r}, registered {overrides[name]!r}")
        elif name in FLAG_DEFAULTS:
            if value not in FLAG_DEFAULTS[name]:
                problems.append(f"sys.flags.{name} is {value!r}, not the default")
        elif value:
            problems.append(f"sys.flags.{name} is set ({value!r})")
    for name in sorted(set(overrides) - set(flags)):
        problems.append(f"sys.flags.{name} was not recorded")
    return problems


def environment_problems(requirement, record, ctx):
    """Reasons the receipt's recorded environment does not satisfy the requirement; none when it does."""
    problems = []
    interpreter = requirement["interpreter"]
    if interpreter is not None:
        environment = record.get("environment")
        if not isinstance(environment, dict):
            return ["identity file missing: the receipt records no execution environment"]
        try:
            minor = ".".join(str(x) for x in environment["version_info"][:2])
            if environment["implementation"].lower() != interpreter["implementation"]:
                problems.append(f"interpreter implementation {environment['implementation']} is not {interpreter['implementation']}")
            if interpreter["minors"] is not None and minor not in interpreter["minors"]:
                problems.append(f"Python {minor} is outside the required minors {', '.join(interpreter['minors'])}")
            problems += _flag_problems(environment["sys_flags"], requirement["flags"])
            if environment["warnoptions"]:
                problems.append("sys.warnoptions is not empty")
            if environment["xoptions"]:
                problems.append("sys._xoptions is not empty")
            for field in ("filesystem_encoding", "preferred_encoding"):
                if not _utf8(environment[field]):
                    problems.append(f"{field} is {environment[field]!r}, not UTF-8")
            permitted = set(requirement["variables"]) | set(record["declaration"].get("environment", []))
            for name, recorded in sorted(environment["variables"].items()):
                if name in BEHAVIOR_VARIABLES and name not in permitted and recorded is not None:
                    problems.append(f"behavior variable {name} was set and is not registered")
            for name, template in requirement["variables"].items():
                if template is not None:
                    expected = hashlib.sha256(template.encode("utf-8", "surrogateescape")).hexdigest()
                    if environment["variables"].get(name) != expected:
                        problems.append(f"variable {name} does not hold its registered value")
            spec = requirement["packages"]
            if spec:
                expected = ctx.expected_packages(spec, environment["marker_environment"])
                actual = {(normalize_package_name(n), v) for n, v in environment["distributions"]}
                for name in sorted(n for n, v in expected if v is None):
                    # A release-neutral project is matched by name: exactly one recorded distribution.
                    recorded = [(n, v) for n, v in environment["distributions"] if normalize_package_name(n) == name]
                    expected.discard((name, None))
                    if len(recorded) == 1:
                        actual.discard((normalize_package_name(recorded[0][0]), recorded[0][1]))
                    else:
                        problems.append(f"project distribution {name} is recorded {len(recorded)} times, not once")
                if expected != actual:
                    extra = sorted(f"{n}=={v}" for n, v in actual - expected)
                    absent = sorted(f"{n}=={v}" for n, v in expected - actual)
                    problems.append("package set differs from the lock: unexpected " + (", ".join(extra[:8]) or "none")
                                    + "; missing " + (", ".join(absent[:8]) or "none"))
        except (KeyError, TypeError, AttributeError) as exc:
            problems.append(f"recorded environment is malformed ({type(exc).__name__}: {exc})")
    recorded_tools = record.get("tools") or {}
    for name in requirement["tools"]:
        recorded = recorded_tools.get(name)
        current = ctx.tool(name)
        if recorded is None:
            problems.append(f"tool {name} was not recorded")
        elif recorded.get("version") != current["version"]:
            problems.append(f"tool {name} version changed: recorded {recorded.get('version')!r}, now {current['version']!r}")
    return problems


def _same_declaration(record, declaration):
    try:
        return normalize(record["declaration"]) == declaration
    except EvidenceError:
        return False


def lookup(root, declaration, *, source_root=None):
    """Find the newest counted receipt for ``declaration`` on the subject's current inputs."""
    declaration = normalize(declaration)
    root = Path(root).resolve()
    current = snapshot(root, declaration, source_root)
    requirement = effective_requirement(declaration, root)
    store = storage(root, source_root)
    ctx = _Context(root, source_root)
    receipts = [r for r in read_receipts(store) if r["declaration"]["check_id"] == declaration["check_id"]]
    receipts.sort(key=lambda r: (r["finished_at"], r["started_at"]), reverse=True)
    ignored, counted = [], []
    for record in receipts:
        if record["schema_version"] != 2:
            ignored.append({"id": record["id"], "reason": "schema_version 1 receipts are history"})
            continue
        if not _same_declaration(record, declaration) or record["fingerprint"] != current["fingerprint"]:
            continue
        if record["status"] in ("interrupted", "inputs-changed"):
            ignored.append({"id": record["id"], "reason": f"status {record['status']} neither passes nor blocks"})
            continue
        problems = environment_problems(requirement, record, ctx)
        if problems:
            ignored.append({"id": record["id"], "reason": "environment does not satisfy the requirement: " + "; ".join(problems)})
            continue
        if record["status"] == "passed":
            state = log_state(store, record)
            if state != "ok":
                ignored.append({"id": record["id"], "reason": f"output log {state}; a pass needs its retained log"})
                continue
        counted.append(record)
    result = {"state": None, "record": None, "snapshot": current, "ignored": ignored,
              "earlier_failures": [], "store": str(store)}
    if counted:
        newest = counted[0]
        result["earlier_failures"] = [r["id"] for r in counted[1:] if r["status"] == "failed"]
        if newest["status"] != "passed":
            result.update(state="failed", record=newest)
            return result
        freshness = requirement["freshness_seconds"]
        if freshness is not None and time.time() - newest["finished_at"] >= freshness:
            result.update(state="expired", record=newest)
            return result
        result.update(state="passed", record=newest)
        return result
    known = any(r["schema_version"] == 2 and r["fingerprint"] != current["fingerprint"] for r in receipts)
    result["state"] = "inputs-changed" if known else "missing"
    return result


def refusal_reason(root, evidence_id, record, found):
    """Why ``record`` is not the current valid passing result, for a refusal message."""
    for item in found["ignored"]:
        if item["id"] == evidence_id:
            return item["reason"]
    if record["status"] != "passed":
        return f"status {record['status']}"
    if record["fingerprint"] != found["snapshot"]["fingerprint"]:
        return "relevant inputs changed"
    if found["record"] is not None and found["record"]["id"] != evidence_id:
        return f"newer evidence {found['record']['id']} decides ({found['state']})"
    return found["state"]


def _lacking_fields(record):
    return sorted(set(V2_REQUIRED) - set(record))


def reuse_eligibility(root, evidence_id, *, source_root=None, directory=None):
    """Whether lookup would reuse this receipt now. Separate from :func:`completeness`."""
    store = Path(directory) if directory is not None else storage(root, source_root)
    try:
        record = _read(store / (evidence_id + ".json"))
    except EvidenceError as exc:
        return {"eligible": False, "reasons": [str(exc)]}
    if record["schema_version"] == 1:
        return {"eligible": False, "reasons": ["environment-not-comparable (schema_version 1): lacks "
                                               + ", ".join(_lacking_fields(record))]}
    try:
        found = lookup(root, record["declaration"], source_root=source_root)
    except EvidenceError as exc:
        return {"eligible": False, "reasons": [str(exc)]}
    if found["state"] == "passed" and found["record"]["id"] == evidence_id:
        return {"eligible": True, "reasons": []}
    return {"eligible": False, "reasons": [refusal_reason(root, evidence_id, record, found)]}


def validate_evidence(repo_root, evidence_id, check_id=None, *, source_root=None):
    """The receipt must be the current valid passing result for its declaration on the subject."""
    if not isinstance(evidence_id, str) or not re.fullmatch(r"TE-[0-9a-f]{32}", evidence_id):
        raise EvidenceError("invalid evidence ID")
    record = _read(storage(repo_root, source_root) / (evidence_id + ".json"))
    if record.get("id") != evidence_id:
        raise EvidenceError("evidence identity mismatch")
    if check_id is not None and record["declaration"]["check_id"] != check_id:
        raise EvidenceError("evidence covers a different check")
    if record["schema_version"] == 1:
        raise EvidenceError("environment-not-comparable (schema_version 1): the receipt lacks "
                            + ", ".join(_lacking_fields(record)) + "; a version 1 receipt is history, never a pass")
    declaration = normalize(record["declaration"])
    try:
        import suite_evidence
        registered = suite_evidence.registered_declaration(repo_root, declaration["check_id"], dev_root=source_root)
    except ImportError:
        registered = None
    if registered is not None and normalize(registered) != declaration:
        raise EvidenceError("the receipt's declaration differs from the registered declaration of " + declaration["check_id"])
    found = lookup(repo_root, declaration, source_root=source_root)
    if found["state"] != "passed" or found["record"]["id"] != evidence_id:
        raise EvidenceError("evidence is not the current valid passing result: " + refusal_reason(repo_root, evidence_id, record, found))
    return record


# ---------------------------------------------------------------- execution

@contextlib.contextmanager
def _lock(path):
    # flock is inherited by the child, preventing duplicates if its coordinator dies.
    import fcntl
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield fd
    finally:
        os.close(fd)


def _execution_entry(declaration, actual):
    """The argument vector after the interpreter, or the whole command for a non-Python check."""
    canonical = declaration["command"]
    if actual is not None and canonical_command(actual) != canonical:
        raise EvidenceError("execution command changes test discovery")
    command = list(actual) if actual is not None else list(canonical)
    return command[1:] if canonical[0] == "python" else command


def child_environment(root, declaration, requirement, base=None):
    """The child's environment: unregistered behavior variables removed, registered values applied."""
    env = dict(base if base is not None else os.environ)
    permitted = set(permitted_variables(declaration, requirement))
    for name in BEHAVIOR_VARIABLES:
        if name not in permitted:
            env.pop(name, None)
    for name, template in requirement["variables"].items():
        if template is not None:
            env[name] = template.replace("${REPOSITORY}", str(root))
    return env


@contextlib.contextmanager
def isolated_environment(root, source_root, requirement):
    """A throwaway environment holding exactly the locked packages: no pip, no crux distribution.

    Built from ``uv export`` of the lock (hashes required) into an unseeded ``uv venv``, outside
    the checkout and the stage, and deleted afterwards. Yields the environment directory.
    """
    spec = (requirement["packages"] or {}).get("lock")
    if not spec:
        raise EvidenceError("an isolated check needs a locked package requirement")
    minors = (requirement["interpreter"] or {}).get("minors")
    here = f"{sys.version_info[0]}.{sys.version_info[1]}"
    minor = here if minors is None or here in minors else minors[0]
    base, _ = _lock_file(root, source_root, spec)
    parent = Path(tempfile.mkdtemp(prefix="crux-evidence-env-"))
    try:
        requirements = parent / "requirements.txt"
        requirements.write_text(uv_export(base, spec, hashes=True))
        env_dir = parent / "env"
        try:
            for command in (["uv", "venv", "--quiet", "--python", minor, str(env_dir)],
                            ["uv", "pip", "install", "--quiet", "--python", str(env_dir / "bin" / "python"),
                             "--no-deps", "--require-hashes", "--compile-bytecode", "-r", str(requirements)]):
                result = subprocess.run(command, capture_output=True, text=True, cwd=parent)
                if result.returncode:
                    raise EvidenceError("cannot build the isolated environment: " + result.stderr.strip()[:400])
        except OSError as exc:
            raise EvidenceError(f"cannot build the isolated environment: {exc}") from exc
        yield env_dir
    finally:
        shutil.rmtree(parent, ignore_errors=True)


def _git_head(path):
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def _launch(argv, root, env, lock_fd):
    """Run the child in its own process group. Returns ``(returncode, output, received_signal)``.

    SIGINT or SIGTERM received by the engine terminates the child's process group; the caller
    records the run as interrupted. A grandchild that outlives the child is stopped with it.
    """
    received = []
    child = subprocess.Popen(argv, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             pass_fds=(lock_fd,), start_new_session=True)
    timer = []
    def stop(group_signal):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(child.pid, group_signal)
    def handler(number, _frame):
        received.append(number)
        stop(signal.SIGTERM)
        escalation = threading.Timer(INTERRUPT_GRACE_SECONDS, stop, (signal.SIGKILL,))
        escalation.daemon = True
        escalation.start()
        timer.append(escalation)
    previous = {}
    if threading.current_thread() is threading.main_thread():
        for number in (signal.SIGINT, signal.SIGTERM):
            previous[number] = signal.signal(number, handler)
    try:
        output, _ = child.communicate()
    finally:
        for number, old in previous.items():
            signal.signal(number, old)
        for escalation in timer:
            escalation.cancel()
    return child.returncode, output, (received[0] if received else None)


def _classify(returncode, received, entry, identity_ok):
    """The receipt status and reason for a finished child."""
    if received is not None:
        return "interrupted", f"engine received signal {received}"
    if returncode == 0:
        if not identity_ok:
            return "interrupted", "identity file missing; an attempt without its environment is incomplete"
        return "passed", None
    if returncode == 3 and entry and os.path.basename(entry[0]) == "parallel_suite.py":
        return "interrupted", "parallel_suite refused the interpreter before any test started"
    return "failed", None


def execute(repo_root, declaration, retry_reason=None, *, execution_command=None, source_root=None, interpreter=None):
    root = Path(repo_root).resolve()
    declared_python = None
    if isinstance(declaration, dict) and declaration.get("command") and isinstance(declaration["command"][0], str):
        first = declaration["command"][0]
        if os.path.isabs(first) and _is_python(first):
            declared_python = first
    declaration = normalize(declaration)
    requirement = effective_requirement(declaration, root)
    entry = _execution_entry(declaration, execution_command)
    python = declaration["command"][0] == "python"
    secrets = [value.encode() for name, value in os.environ.items()
               if re.search(r"TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY", name, re.I) and len(value) >= 4]
    if any(secret.decode() in argument for secret in secrets for argument in entry):
        raise EvidenceError("commands must not contain credential environment values")
    directory = storage(root, source_root)
    with _lock(directory / (digest(declaration) + ".lock")) as lock_fd:
        found = lookup(root, declaration, source_root=source_root)
        if found["state"] == "passed":
            return {"action": "reused", "evidence": found["record"], "earlier_failures": found["earlier_failures"]}
        if found["state"] == "failed" and not (isinstance(retry_reason, str) and retry_reason.strip()):
            raise EvidenceError("matching failure requires an explicit retry reason")
        before = found["snapshot"]
        evidence_id = "TE-" + uuid.uuid4().hex
        output = directory / (evidence_id + ".log")
        started = time.time()
        revision = _git_head(root)
        source_revision = _git_head(source_root) if source_root is not None else revision
        env = child_environment(root, declaration, requirement)
        tools = observe_tools(requirement["tools"], env)
        identity_dir = Path(tempfile.mkdtemp(prefix="crux-identity-"))
        identity_path = identity_dir / "identity.json"
        returncode, diagnostic, received, launch_error = None, b"", None, None
        try:
            with contextlib.ExitStack() as stack:
                if python:
                    if interpreter is not None or declared_python is not None:
                        # An explicit interpreter, or an absolute interpreter the caller declared,
                        # runs the check as given. Validation still judges only the recorded environment.
                        python_path = str(interpreter if interpreter is not None else declared_python)
                    elif requirement["isolated"]:
                        env_dir = stack.enter_context(isolated_environment(root, source_root, requirement))
                        python_path = str(env_dir / "bin" / "python")
                        env["VIRTUAL_ENV"] = str(env_dir)
                        env["PATH"] = str(env_dir / "bin") + os.pathsep + env.get("PATH", "")
                    else:
                        python_path = sys.executable
                    variables = permitted_variables(declaration, requirement)
                    argv = [python_path, str(CAPTURE), str(identity_path),
                            *(["--variables", ",".join(variables)] if variables else []), "--", *entry]
                else:
                    argv = entry
                try:
                    returncode, diagnostic, received = _launch(argv, root, env, lock_fd)
                except OSError as exc:
                    launch_error = f"{type(exc).__name__}: {exc}"
        except EvidenceError as exc:
            launch_error = str(exc)
        identity = None
        if identity_path.is_file():
            with contextlib.suppress(OSError, ValueError):
                identity = json.loads(identity_path.read_text())
        shutil.rmtree(identity_dir, ignore_errors=True)
        for secret in sorted(secrets, key=len, reverse=True):
            diagnostic = diagnostic.replace(secret, b"[REDACTED]")
        if launch_error:
            diagnostic += f"engine: launch failed ({launch_error})\n".encode()
        with output.open("xb") as stream:
            os.chmod(output, 0o600)
            stream.write(diagnostic)
        after = snapshot(root, declaration, source_root)
        finished = time.time()
        if launch_error:
            status, reason = "interrupted", "launch error: " + launch_error[:200]
        else:
            status, reason = _classify(returncode, received, entry, identity is not None or not python)
        if status in ("passed", "failed") and before["fingerprint"] != after["fingerprint"]:
            status = "inputs-changed"
        if reason is None:
            reason = retry_reason if found["state"] == "failed" else found["state"]
        record = {"schema_version": SCHEMA_VERSION, "id": evidence_id, "declaration": declaration,
                  "fingerprint": before["fingerprint"], "snapshot": {"fingerprint": before["fingerprint"], "inputs": before["inputs"]},
                  "executed_command": list(execution_command) if execution_command is not None else list(declaration["command"]),
                  "end_fingerprint": after["fingerprint"], "revision": revision, "source_revision": source_revision,
                  "started_at": started, "finished_at": finished, "seconds": finished - started,
                  "status": status, "returncode": returncode, "reason": reason,
                  "environment": identity, "tools": tools, "lock_sha256": before["lock_sha256"],
                  "output": output.name, "output_sha256": file_digest(output)}
        if status == "interrupted" and received is not None:
            record["signal"] = received
        record["record_sha256"] = digest(record)
        temp = directory / (evidence_id + ".tmp")
        with temp.open("x") as stream:
            os.chmod(temp, 0o600)
            json.dump(record, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(directory / (evidence_id + ".json"))
        if status == "passed":
            problems = environment_problems(requirement, record, _Context(root, source_root))
            if problems:
                raise EvidenceError(f"{evidence_id} passed in an environment that does not satisfy its requirement "
                                    "and will not be reused: " + "; ".join(problems))
        retried = [found["record"]["id"]] if found["state"] == "failed" else []
        return {"action": "executed", "evidence": record, "earlier_failures": retried + found["earlier_failures"]}
