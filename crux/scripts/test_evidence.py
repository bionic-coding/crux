"""Repository-owned test evidence. Input declarations are coverage claims, not discovery.

Only declared inputs and environment influence reuse. Declare dependency lockfiles,
fixtures, tool configuration, and relevant environment names alongside source files.
Secret environment values are never recorded; commands and test output must not
contain credentials. This is local evidence integrity, not a signature/trust service.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid


class EvidenceError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(declaration):
    allowed = {"check_id", "command", "inputs", "environment", "freshness_seconds", "git_tracked", "exclude_inputs"}
    if not isinstance(declaration, dict) or set(declaration) - allowed:
        raise EvidenceError("unknown check declaration fields")
    result = dict(declaration)
    if not isinstance(result.get("check_id"), str) or not result["check_id"].strip():
        raise EvidenceError("check_id must be nonempty")
    for name in ("command", "inputs"):
        if not isinstance(result.get(name), list) or not result[name] or not all(isinstance(x, str) and x for x in result[name]):
            raise EvidenceError(f"{name} must be a nonempty string array")
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
    return result


def snapshot(root, declaration):
    root = Path(root).resolve()
    declaration = normalize(declaration)
    files = {}
    def excluded(relative):
        return any(relative == prefix.rstrip("/") or relative.startswith(prefix.rstrip("/") + "/")
                   for prefix in declaration.get("exclude_inputs", []))
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
                inventory_entries.append(entry)
                path = root / name
                selection.append((name, [path] if path.exists() or path.is_symlink() else []))
            git_inventory = hashlib.sha256(b"\0".join(inventory_entries)).hexdigest()
            head = subprocess.run(["git", "ls-tree", "-r", "-z", "HEAD"], cwd=root, capture_output=True)
            if head.returncode == 0:
                # HEAD-relative assertions depend on committed contents, not on
                # the commit ID. Ignore operational records just as for the index.
                entries = [entry for entry in head.stdout.split(b"\0") if entry
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
                    files[relative] = {"sha256": file_digest(path), "executable": bool(path.stat().st_mode & 0o111)}
    command_path = declaration["command"][0]
    executable = str(root / command_path) if "/" in command_path and not Path(command_path).is_absolute() else shutil.which(command_path)
    if executable is None:
        raise EvidenceError("check executable is unavailable")
    executable = Path(executable).resolve()
    environment = {name: os.environ.get(name) for name in declaration["environment"]}
    environment = {name: value.replace(str(root), "${REPOSITORY}") if value is not None else None for name, value in environment.items()}
    # Inspect the interpreter that actually runs the check, not the coordinator's
    # environment. Cycle validation may itself run in another uv environment.
    packages = []
    python_version = None
    if "python" in executable.name.lower():
        probe = "import importlib.metadata as m,json,sys; print(json.dumps({'version':sys.version,'prefix':sys.prefix,'packages':sorted((d.metadata.get('Name',''),d.version) for d in m.distributions())}))"
        inspected = subprocess.run([declaration["command"][0], "-c", probe], cwd=root, capture_output=True, text=True)
        if inspected.returncode:
            raise EvidenceError("cannot inspect check interpreter")
        try:
            details = json.loads(inspected.stdout)
            packages, python_version = details["packages"], details["version"]
            environment = {name: value.replace(details["prefix"], "${PYTHON_ENV}") if value is not None else None for name, value in environment.items()}
        except (ValueError, KeyError) as exc:
            raise EvidenceError("invalid check interpreter identity") from exc
    identity = {"platform": platform.platform(), "python": python_version,
                "executable": str(executable), "executable_sha256": file_digest(executable),
                "engine_sha256": file_digest(Path(__file__)),
                "packages": packages,
                "environment_sha256": digest(environment)}
    fingerprint_declaration = dict(declaration)
    fingerprint_declaration["command"] = [str(executable), *declaration["command"][1:]]
    value = {"declaration": fingerprint_declaration, "files": files, "identity": identity,
             "git_inventory": git_inventory, "git_head_tree": git_head_tree}
    return {"fingerprint": digest(value), "inputs": files, "identity": identity}


def storage(root):
    root = Path(root).resolve()
    override = os.environ.get("CRUX_TEST_EVIDENCE_STORE")
    if override:
        current = Path(override).absolute()
    else:
        git = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=root, capture_output=True, text=True)
        current = Path(git.stdout.strip()) / "crux" / "test-evidence" if git.returncode == 0 else root / ".crux-test-evidence"
    for path in [*reversed(current.parents), current]:
        if path.is_symlink():
            raise EvidenceError("evidence directory must not be a symlink")
    current.mkdir(mode=0o700, parents=True, exist_ok=True)
    return current


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
        if record.get("status") not in ("passed", "failed", "inputs-changed"):
            raise EvidenceError("invalid evidence result")
        normalize(record["declaration"])
        if record["status"] == "passed" and (record["returncode"] != 0 or record["fingerprint"] != record["end_fingerprint"]):
            raise EvidenceError("passing evidence has failed or changed inputs")
        record["record_sha256"] = seal
        return record
    except (ValueError, KeyError, TypeError) as exc:
        raise EvidenceError(f"invalid evidence: {path.name}") from exc


def lookup(root, declaration):
    declaration = normalize(declaration)
    current = snapshot(root, declaration)
    records = []
    for path in storage(root).glob("TE-*.json"):
        record = _read(path)
        if record["declaration"]["check_id"] == declaration["check_id"]:
            records.append(record)
    records.sort(key=lambda r: r["finished_at"], reverse=True)
    for record in records:
        if record["fingerprint"] != current["fingerprint"]:
            continue
        if record["status"] != "passed":
            return {"state": "failed", "record": record, "snapshot": current}
        freshness = declaration.get("freshness_seconds")
        if freshness is not None and time.time() - record["finished_at"] >= freshness:
            return {"state": "expired", "record": record, "snapshot": current}
        log = storage(root) / record["output"]
        if log.is_symlink() or not log.is_file() or file_digest(log) != record["output_sha256"]:
            raise EvidenceError("evidence output missing or changed")
        return {"state": "passed", "record": record, "snapshot": current}
    return {"state": "inputs-changed" if records else "missing", "record": None, "snapshot": current}


def validate_evidence(repo_root, evidence_id, check_id=None):
    if not isinstance(evidence_id, str) or not re.fullmatch(r"TE-[0-9a-f]{32}", evidence_id):
        raise EvidenceError("invalid evidence ID")
    record = _read(storage(repo_root) / (evidence_id + ".json"))
    if record.get("id") != evidence_id:
        raise EvidenceError("evidence identity mismatch")
    if check_id is not None and record["declaration"]["check_id"] != check_id:
        raise EvidenceError("evidence covers a different check")
    declaration = record["declaration"]
    command_path = declaration["command"][0]
    if "/" in command_path and not Path(command_path).is_absolute():
        command_path = str(Path(repo_root).resolve() / command_path)
    if (shutil.which(command_path) is None
            and record.get("snapshot", {}).get("identity", {}).get("python") is not None):
        # A reused Python receipt can outlive its temporary virtual environment.
        # The current interpreter is only a candidate: lookup must recompute the
        # complete fingerprint, including executable, packages and environment.
        # Preserve the original declaration and receipt as execution history.
        declaration = dict(declaration, command=[sys.executable, *declaration["command"][1:]])
    found = lookup(repo_root, declaration)
    if found["state"] != "passed" or found["record"]["id"] != evidence_id:
        raise EvidenceError("evidence is not the current valid passing result")
    return record


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


def _execution_command(declaration, actual):
    canonical = declaration["command"]
    if actual is None or actual == canonical:
        return canonical
    # The suite adapter may vary scheduling and output destinations, but not
    # discovery, interpreter, or tests. No arbitrary command substitution.
    def strip_scheduling(command):
        if len(command) < 3 or command[1] != "crux/scripts/tests/parallel_suite.py":
            raise EvidenceError("execution command differs from declared check")
        result = command[:2]
        index = 2
        while index < len(command):
            if command[index] in ("--workers", "--records", "--timings"):
                if index + 1 == len(command):
                    raise EvidenceError("missing scheduling argument")
                index += 2
            else:
                result.append(command[index])
                index += 1
        return result
    if strip_scheduling(actual) != strip_scheduling(canonical):
        raise EvidenceError("execution command changes test discovery")
    return actual


def execute(repo_root, declaration, retry_reason=None, *, execution_command=None):
    root = Path(repo_root).resolve()
    declaration = normalize(declaration)
    execution_command = _execution_command(declaration, execution_command)
    secrets = [value.encode() for name, value in os.environ.items()
               if re.search(r"TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY", name, re.I) and len(value) >= 4]
    if any(secret.decode() in argument for secret in secrets for argument in execution_command):
        raise EvidenceError("commands must not contain credential environment values")
    directory = storage(root)
    with _lock(directory / (digest(declaration) + ".lock")) as lock_fd:
        found = lookup(root, declaration)
        if found["state"] == "passed":
            return {"action": "reused", "evidence": found["record"]}
        if found["state"] == "failed" and not (isinstance(retry_reason, str) and retry_reason.strip()):
            raise EvidenceError("matching failure requires an explicit retry reason")
        before = found["snapshot"]
        evidence_id = "TE-" + uuid.uuid4().hex
        output = directory / (evidence_id + ".log")
        started = time.time()
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
        result = subprocess.run(execution_command, cwd=root, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, pass_fds=(lock_fd,))
        diagnostic = result.stdout
        for secret in sorted(secrets, key=len, reverse=True):
            diagnostic = diagnostic.replace(secret, b"[REDACTED]")
        with output.open("xb") as stream:
            os.chmod(output, 0o600)
            stream.write(diagnostic)
        after = snapshot(root, declaration)
        finished = time.time()
        status = "passed" if result.returncode == 0 else "failed"
        if before["fingerprint"] != after["fingerprint"]:
            status = "inputs-changed"
        record = {"schema_version": 1, "id": evidence_id, "declaration": declaration,
                  "fingerprint": before["fingerprint"], "snapshot": before,
                  "executed_command": execution_command or declaration["command"],
                  "end_fingerprint": after["fingerprint"], "revision": revision.stdout.strip() if revision.returncode == 0 else None,
                  "started_at": started, "finished_at": finished, "seconds": finished - started,
                  "status": status, "returncode": result.returncode,
                  "reason": retry_reason if found["state"] == "failed" else found["state"],
                  "output": output.name, "output_sha256": file_digest(output)}
        record["record_sha256"] = digest(record)
        temp = directory / (evidence_id + ".tmp")
        with temp.open("x") as stream:
            os.chmod(temp, 0o600)
            json.dump(record, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(directory / (evidence_id + ".json"))
        return {"action": "executed", "evidence": record}
