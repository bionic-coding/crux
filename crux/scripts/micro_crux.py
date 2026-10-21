"""Install the standalone guide without claiming ownership of user instructions.

Installation bookkeeping is <docs_dir>/.micro-crux-install.json, format
crux.micro-crux-install, format_version 1. It is not decision authority.
Only the guide bytes and the delimited instruction region are managed.

Four atomic replacements: pending intent, guide, instructions, final metadata.
Between-file interruption is recoverable, not a multi-file atomic transaction.
Recovery accepts only observed before/after digests or exact owned region bytes.
Run one installer at a time; a changed observed target stops the next write.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from bionic_config import BionicConfigError, load_config, require_schema_version
from instruction_migration import CapabilityError, load_denylist

STATE_NAME = ".micro-crux-install.json"
FORMAT = "crux.micro-crux-install"
VERSION = 1
BEGIN = b"<!-- BEGIN CRUX: micro-crux -->"
END = b"<!-- END CRUX: micro-crux -->"
POINTER = BEGIN + b"\nRead `micro-crux.md` before reviewing or changing this project.\n" + END + b"\n"
TARGETS = {"guide": "micro-crux.md", "instructions": "AGENTS.md"}
_DIGEST = re.compile(r"[0-9a-f]{64}")


class InstallConflict(ValueError):
    """A local conflict; preserve all target bytes and describe the remedy."""

    def __init__(self, message, *, differences=None):
        super().__init__(message)
        self.differences = differences or []


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _digest(data: bytes | None) -> str | None:
    return sha(data) if data is not None else None


def _safe(root: Path, path: Path) -> None:
    """No symlinks in any managed path, including an inward-pointing parent."""
    if not path.is_relative_to(root) or path == root:
        raise InstallConflict("managed path escapes the project; correct the configured tree")
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink():
            raise InstallConflict(f"{part.relative_to(root)} is a symlink; replace the link with a regular project path")
    if path.exists() and not path.is_file():
        raise InstallConflict(f"{path.relative_to(root)} is not a regular file; preserve it elsewhere before installing")
    if not path.parent.is_dir():
        raise InstallConflict(f"parent of {path.relative_to(root)} is missing; repair the documentation tree first")
    aliases = [p.name for p in path.parent.iterdir() if p.name.casefold() == path.name.casefold() and p.name != path.name]
    if aliases:
        raise InstallConflict(f"case variant {aliases[0]} blocks {path.name}; reconcile its spelling without discarding its content")


def _read(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def _region(data: bytes | None) -> tuple[int, int] | None:
    if data is None or (BEGIN not in data and END not in data):
        return None
    if data.count(BEGIN) != 1 or data.count(END) != 1:
        raise InstallConflict("AGENTS.md has incomplete or duplicate micro-crux markers; reconcile the region manually")
    start, end = data.index(BEGIN), data.index(END)
    if end <= start or (start and data[start - 1:start] != b"\n"):
        raise InstallConflict("AGENTS.md has malformed micro-crux markers; preserve the text and reconcile the region manually")
    end += len(END)
    if data[end:end + 1] != b"\n":
        raise InstallConflict("AGENTS.md micro-crux region changed; restore the owned region or integrate it explicitly")
    return start, end + 1


def _region_digest(data: bytes | None) -> str | None:
    span = _region(data)
    return sha(data[span[0]:span[1]]) if span is not None else None


def _instructions(data: bytes | None) -> bytes:
    if data is not None:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InstallConflict("AGENTS.md is not UTF-8; preserve and convert it before adding an instruction") from exc
    span = _region(data)
    if span is not None:
        return data[:span[0]] + POINTER + data[span[1]:]
    if not data:
        return POINTER
    separator = b"\n" if data.endswith(b"\n") else b"\n\n"
    return data + separator + POINTER


def _instruction_policy(root: Path) -> list[str]:
    for entry in root.iterdir():
        name = entry.name
        if name.casefold() == "agents.md" and name != "AGENTS.md":
            raise InstallConflict(f"{name} is a case variant of AGENTS.md; reconcile its spelling before installation")
        if name.casefold() == "claude.md":
            raise InstallConflict(f"{name} blocks managed AGENTS.md installation; preserve it and use instruction migration, or have its owner add an explicit instruction to read micro-crux.md")
    try:
        denylist = load_denylist(root)
    except CapabilityError as exc:
        raise InstallConflict(str(exc)) from exc
    if "AGENTS.md" in denylist:
        raise InstallConflict("AGENTS.md is named by instruction_migration_denylist; obtain the owner's instruction before changing that exclusion")
    notes = [
        "Installed guidance reaches harnesses that read root AGENTS.md. A harness reading only CLAUDE.md needs its owner to add an explicit instruction to read micro-crux.md; no automatic inclusion is claimed.",
    ]
    for entry in root.iterdir():
        if entry.name.casefold() == "claude.local.md":
            notes.append(f"Preserved {entry.name}; it can suppress AGENTS.md in some host modes. Its owner can add an explicit read instruction or select a mode that reads AGENTS.md.")
    private = root / ".claude"
    if private.is_dir() and not private.is_symlink():
        for entry in private.iterdir():
            if entry.name.casefold() == "claude.md":
                notes.append(f"Preserved .claude/{entry.name}; it can suppress AGENTS.md. Its owner can add an explicit instruction to read micro-crux.md.")
    return notes


def _hash(value) -> bool:
    return isinstance(value, str) and bool(_DIGEST.fullmatch(value))


def _upstream(value) -> bool:
    return isinstance(value, dict) and set(value) == {"source", "sha256"} and value["source"] == "box/micro-crux.md" and _hash(value["sha256"])


def _state(data: bytes | None, docs_dir: str) -> dict:
    if data is None:
        return {"format": FORMAT, "format_version": VERSION, "docs_dir": docs_dir,
                "targets": dict(TARGETS), "installed": None, "pending": None}
    try:
        state = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise InstallConflict("installation metadata is malformed; restore its known version before retrying") from exc
    if (not isinstance(state, dict) or set(state) != {"format", "format_version", "docs_dir", "targets", "installed", "pending"}
            or state.get("format") != FORMAT or type(state.get("format_version")) is not int or state["format_version"] != VERSION
            or state.get("docs_dir") != docs_dir or state.get("targets") != TARGETS):
        raise InstallConflict("installation metadata has an unsupported format or target identity; restore or explicitly reconcile the metadata")
    installed, pending = state["installed"], state["pending"]
    if installed is not None:
        if (not isinstance(installed, dict) or set(installed) != {"guide_sha256", "pointer_sha256", "upstream"}
                or not _hash(installed["guide_sha256"]) or not _hash(installed["pointer_sha256"])
                or not _upstream(installed["upstream"]) or installed["guide_sha256"] != installed["upstream"]["sha256"]):
            raise InstallConflict("installed ownership metadata is malformed; restore its known version")
    if pending is not None:
        if (not isinstance(pending, dict) or set(pending) != {"upstream", "guide_sha256", "pointer_sha256", "before", "after"}
                or not _upstream(pending["upstream"]) or not _hash(pending["guide_sha256"])
                or not _hash(pending["pointer_sha256"]) or pending["guide_sha256"] != pending["upstream"]["sha256"]):
            raise InstallConflict("pending installation metadata is malformed; preserve targets and restore the intent record")
        for field in ("before", "after"):
            values = pending[field]
            if (not isinstance(values, dict) or set(values) != set(TARGETS)
                    or any(not _hash(value) and not (value is None and field == "before") for value in values.values())):
                raise InstallConflict("pending installation target digests are malformed; restore the intent record")
        if pending["after"]["guide"] != pending["guide_sha256"]:
            raise InstallConflict("pending guide identity is inconsistent; restore the intent record")
    if installed is None and pending is None:
        raise InstallConflict("installation metadata establishes no ownership; restore it or explicitly reconcile the existing files")
    return state


def write_atomic(path: Path, data: bytes) -> None:
    """Preserve old bytes on failure before replacement; remove only our temporary file."""
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        os.fchmod(descriptor, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(repo_root: Path, plugin_root: Path, *, dry_run: bool = False) -> dict:
    root = Path(repo_root).resolve()
    try:
        cfg = load_config(root, require_tree=True)
        require_schema_version(cfg.docs_root)
    except BionicConfigError as exc:
        raise InstallConflict(str(exc)) from exc
    # Check the configured spelling as well as the resolved target; the reader
    # allows contained directory links, while managed installation does not.
    configured = root / cfg.docs_dir
    for path in (configured / "manifest.yml", cfg.docs_root / "manifest.yml"):
        _safe(root, path)
    guide = root / TARGETS["guide"]
    instructions = root / TARGETS["instructions"]
    metadata = cfg.docs_root / STATE_NAME
    for path in (guide, instructions, metadata):
        _safe(root, path)
    notes = _instruction_policy(root)
    payload_path = Path(plugin_root) / "box/micro-crux.md"
    if payload_path.is_symlink() or not payload_path.is_file():
        raise InstallConflict("shipped box/micro-crux.md is missing or a symlink; restore the plugin payload")
    payload = payload_path.read_bytes()
    if not payload:
        raise InstallConflict("shipped micro-crux.md is empty; restore the plugin payload")
    upstream = {"source": "box/micro-crux.md", "sha256": sha(payload)}
    old = {"guide": _read(guide), "instructions": _read(instructions)}
    old_metadata = _read(metadata)
    state = _state(old_metadata, cfg.docs_dir)
    installed, pending = state["installed"], state["pending"]
    region_hash = _region_digest(old["instructions"])
    if pending is None:
        if installed is None:
            if old["guide"] not in (None, payload):
                raise InstallConflict("micro-crux.md has unknown ownership and different bytes; preserve it and integrate the upstream guide explicitly",
                                      differences=[{"path": "micro-crux.md", "installed_sha256": None,
                                                    "actual_sha256": _digest(old["guide"]), "upstream_sha256": sha(payload)}])
            if region_hash is not None:
                raise InstallConflict("AGENTS.md markers establish no ownership without installation metadata; restore the metadata or reconcile the region explicitly")
        else:
            if _digest(old["guide"]) != installed["guide_sha256"]:
                raise InstallConflict("micro-crux.md was locally edited or removed; preserve it and integrate the upstream difference explicitly",
                                      differences=[{"path": "micro-crux.md", "installed_sha256": installed["guide_sha256"],
                                                    "actual_sha256": _digest(old["guide"]), "upstream_sha256": sha(payload)}])
            if region_hash != installed["pointer_sha256"]:
                raise InstallConflict("AGENTS.md managed pointer was locally edited or removed; preserve it and integrate the instruction explicitly",
                                      differences=[{"path": "AGENTS.md", "region": "micro-crux", "installed_sha256": installed["pointer_sha256"],
                                                    "actual_sha256": region_hash, "upstream_sha256": sha(POINTER)}])
        desired_instructions = _instructions(old["instructions"])
        desired_installed = {"guide_sha256": sha(payload), "pointer_sha256": sha(POINTER), "upstream": upstream}
        if installed == desired_installed and old["instructions"] == desired_instructions:
            return {"changed": False, "changes": [], "dry_run": dry_run, "docs_dir": cfg.docs_dir,
                    "metadata": metadata.relative_to(root).as_posix(), "guide_sha256": sha(payload), "notes": notes}
        pending = {"upstream": upstream, "guide_sha256": sha(payload), "pointer_sha256": sha(POINTER),
                   "before": {key: _digest(value) for key, value in old.items()},
                   "after": {"guide": sha(payload), "instructions": sha(desired_instructions)}}
        state["pending"] = pending
    else:
        if pending["upstream"] != upstream or pending["pointer_sha256"] != sha(POINTER):
            raise InstallConflict("pending installation binds another upstream guide or pointer; resume with that version before updating")
        if _digest(old["guide"]) not in {pending["before"]["guide"], pending["after"]["guide"]}:
            raise InstallConflict("micro-crux.md changed during interrupted installation; preserve the edit and reconcile it with the pending intent")
        current = _digest(old["instructions"])
        if current in {pending["before"]["instructions"], pending["after"]["instructions"]}:
            desired_instructions = _instructions(old["instructions"])
            if sha(desired_instructions) != pending["after"]["instructions"]:
                raise InstallConflict("pending instruction identity is inconsistent; restore the intent record")
        elif region_hash == pending["pointer_sha256"]:
            # Only the region is owned: outside edits do not invalidate it.
            desired_instructions = old["instructions"]
        elif installed and region_hash == installed["pointer_sha256"]:
            desired_instructions = _instructions(old["instructions"])
        else:
            raise InstallConflict("AGENTS.md changed during interrupted installation; preserve its bytes and reconcile the pending instruction")
    final = deepcopy(state)
    final["installed"] = {"guide_sha256": sha(payload), "pointer_sha256": sha(POINTER), "upstream": upstream}
    final["pending"] = None
    changes = [path.relative_to(root).as_posix() for path, before, after in (
        (guide, old["guide"], payload), (instructions, old["instructions"], desired_instructions),
        (metadata, old_metadata, encoded(final))) if before != after]
    result = {"changed": bool(changes), "changes": changes, "dry_run": dry_run,
              "docs_dir": cfg.docs_dir, "metadata": metadata.relative_to(root).as_posix(),
              "guide_sha256": sha(payload), "notes": notes}
    if dry_run:
        return result

    def replace_if_current(path, before, after):
        _safe(root, path)
        if _read(path) != before:
            raise InstallConflict(f"{path.relative_to(root)} changed during installation; preserve it and retry after reconciliation")
        if before != after:
            write_atomic(path, after)

    intent = encoded(state)
    replace_if_current(metadata, old_metadata, intent)
    replace_if_current(guide, old["guide"], payload)
    replace_if_current(instructions, old["instructions"], desired_instructions)
    if guide.read_bytes() != payload or _region_digest(instructions.read_bytes()) != sha(POINTER):
        raise InstallConflict("installed targets changed before finalization; preserve the pending intent for reconciliation")
    replace_if_current(metadata, intent, encoded(final))
    return result
