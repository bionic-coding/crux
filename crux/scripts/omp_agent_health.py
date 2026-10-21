#!/usr/bin/env python3
"""Inspect the static health of an installed Crux OMP-agent roster."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import models_catalog  # noqa: E402
import omp_agents  # noqa: E402


RUNTIME_UNVERIFIED = {
    "status": "unverified",
    "client_version": None,
    "reason": "fresh-session host evidence has not been recorded",
}


def _plugin(plugin_root: Path) -> dict[str, str]:
    root = plugin_root.resolve()
    manifest = root / "plugin.json"
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise omp_agents.SpecViolation(f"cannot read plugin manifest {manifest}: {exc}") from exc
    if not isinstance(raw, dict):
        raise omp_agents.SpecViolation(f"plugin manifest root must be an object: {manifest}")
    version = raw.get("version")
    if not isinstance(version, str) or not version.strip():
        raise omp_agents.SpecViolation(f"plugin manifest has no version: {manifest}")
    return {"root": str(root), "version": version}


def _is_contained(candidate: Path, root: Path) -> bool:
    try:
        resolved = candidate.resolve()
        return resolved == root or resolved.is_relative_to(root)
    except (OSError, ValueError):
        return False


def _parse_bracket_list(raw: str) -> list[str] | None:
    val = raw.strip()
    if not (val.startswith("[") and val.endswith("]")):
        return None
    inner = val[1:-1].strip()
    if not inner:
        return []
    items = [item.strip() for item in inner.split(",")]
    if any(not item for item in items):
        return None
    return [omp_agents._unquote_token(item) for item in items]


def _parse_agent_markdown(text: str) -> dict[str, Any]:
    match = re.match(r"\A---\n(?P<frontmatter>.*?)\n---\n(?P<body>.*)\Z", text, re.DOTALL)
    if not match:
        raise ValueError("missing YAML frontmatter block")
    fm = match.group("frontmatter")
    body = match.group("body").strip()
    if not body:
        raise ValueError("empty agent body")

    parsed: dict[str, Any] = {}
    for line in fm.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line or line[:1] in (" ", "\t"):
            raise ValueError(f"unsupported frontmatter line: {line!r}")
        key, _, raw_val = line.partition(":")
        key = key.strip()
        val = omp_agents._strip_yaml_comment(raw_val).strip()
        if key in ("tools", "autoloadSkills"):
            arr = _parse_bracket_list(val)
            if arr is None:
                raise ValueError(f"malformed bracket list for {key!r}")
            parsed[key] = arr
        elif key == "model":
            if val.startswith("["):
                arr = _parse_bracket_list(val)
                if arr is None or not arr:
                    raise ValueError("malformed model list")
                parsed[key] = arr
            else:
                parsed[key] = omp_agents._unquote_token(val)
        elif key == "read-summarize":
            if val == "false":
                parsed[key] = False
            elif val == "true":
                parsed[key] = True
            else:
                raise ValueError("malformed read-summarize boolean")
        elif key == "spawns":
            if val in ('"*"', "'*'", "*"):
                parsed[key] = "*"
            else:
                arr = _parse_bracket_list(val)
                if arr is None:
                    raise ValueError("malformed spawns field")
                parsed[key] = arr
        else:
            parsed[key] = omp_agents._unquote_token(val)
    if not isinstance(parsed.get("name"), str) or not parsed["name"]:
        raise ValueError("missing string name")
    if not isinstance(parsed.get("description"), str) or not parsed["description"]:
        raise ValueError("missing string description")
    return parsed


def _resolve_project_omp_root(context: Path) -> Path:
    """Find the nearest ancestor containing `.omp` or `.git`, else `context`."""
    for candidate in (context, *context.parents):
        if (candidate / ".omp").exists() or (candidate / ".omp").is_symlink():
            return candidate
        if (candidate / ".git").exists() or (candidate / ".git").is_symlink():
            return candidate
    return context


def _shadow_report(project_context: Path | None, source_names: list[str]) -> dict[str, Any]:
    if project_context is None:
        return {"status": "unverified", "project_context": None, "roles": [], "malformed": [], "unsafe": []}
    context = project_context.resolve()
    if not context.is_dir():
        raise omp_agents.SpecViolation(f"project context is not a directory: {context}")
    project_root = _resolve_project_omp_root(context)
    result: dict[str, Any] = {
        "status": "clean",
        "project_context": str(context),
        "roles": [],
        "malformed": [],
        "unsafe": [],
    }
    omp_dir = project_root / ".omp"
    if (omp_dir.exists() or omp_dir.is_symlink()) and not _is_contained(omp_dir, project_root):
        result["unsafe"].append({"file": ".omp", "reason": "resolves outside project context"})
        result["status"] = "findings"
        return result
    if omp_dir.exists() and not omp_dir.is_dir():
        result["unsafe"].append({"file": ".omp", "reason": "is not a directory"})
        result["status"] = "findings"
        return result
    agents_dir = omp_dir / "agents"
    if not agents_dir.exists() and not agents_dir.is_symlink():
        return result
    if not _is_contained(agents_dir, project_root):
        result["unsafe"].append({"file": ".omp/agents", "reason": "resolves outside project context"})
        result["status"] = "findings"
        return result
    if not agents_dir.is_dir():
        result["unsafe"].append({"file": ".omp/agents", "reason": "is not a directory"})
        result["status"] = "findings"
        return result
    expected = set(source_names)
    for path in sorted(agents_dir.glob("*.md")):
        if path.is_symlink():
            result["unsafe"].append({"file": path.name, "reason": "agent file is a symlink"})
            continue
        status, text, reason = omp_agents.read_managed_file(agents_dir, path.name)
        if status == "unsafe":
            result["unsafe"].append({"file": path.name, "reason": reason})
            continue
        if status != "regular" or text is None:
            result["malformed"].append({"file": path.name, "reason": reason or status})
            continue
        try:
            parsed = _parse_agent_markdown(text)
        except ValueError as exc:
            result["malformed"].append({"file": path.name, "reason": str(exc)})
            continue
        name = parsed.get("name")
        if name in expected:
            result["roles"].append({"role": name, "file": path.name, "name": name})
    if result["roles"] or result["malformed"] or result["unsafe"]:
        result["status"] = "findings"
    return result


def _installed_role(
    target: Path | omp_agents.PinnedDirectory,
    filename: str,
    source: omp_agents.SourceAgent,
) -> dict[str, Any]:
    base = {"role": source.name, "file": filename}
    status, text, reason = omp_agents.read_managed_file(target, filename)
    if status == "unsafe":
        return {
            **base,
            "status": "unsafe",
            "model": None,
            "thinking_level": None,
            "read_summarize": None,
            "tools": [],
            "spawns": None,
            "reason": reason,
        }
    if status == "malformed":
        return {
            **base,
            "status": "malformed",
            "model": None,
            "thinking_level": None,
            "read_summarize": None,
            "tools": [],
            "spawns": None,
            "reason": reason,
        }
    if status == "missing" or text is None:
        return {
            **base,
            "status": "missing",
            "model": None,
            "thinking_level": None,
            "read_summarize": None,
            "tools": [],
            "spawns": None,
        }
    try:
        parsed = _parse_agent_markdown(text)
    except ValueError as exc:
        return {
            **base,
            "status": "malformed",
            "model": None,
            "thinking_level": None,
            "read_summarize": None,
            "tools": [],
            "spawns": None,
            "reason": str(exc),
        }
    return {
        **base,
        "status": "installed",
        "model": parsed.get("model"),
        "thinking_level": (
            parsed.get("thinking-level")
            if isinstance(parsed.get("thinking-level"), str)
            else None
        ),
        "read_summarize": parsed.get("read-summarize"),
        "tools": parsed.get("tools", []),
        "spawns": parsed.get("spawns"),
    }


def inspect_install(
    *,
    target: Path | omp_agents.PinnedDirectory,
    plugin_root: Path,
    scope: str,
    project_context: Path | None = None,
) -> dict[str, Any]:
    """Return stable static state of an OMP agent installation."""
    plugin = _plugin(plugin_root)
    sources = [omp_agents.parse_source(path) for path in sorted((plugin_root / "agents").glob("*.md"))]
    catalog = models_catalog.load(plugin_root / "catalog" / "models.yml", plugin_root / "agents")
    generated = omp_agents.generate(plugin_root / "agents", catalog)
    added, changed, removed, _problems = omp_agents.safe_diff(target, generated, managed=catalog.managed_filenames)
    roles = []
    installed_roles = []
    for source in sources:
        model = [omp_agents.omp_role_alias(source.name), catalog.resolve(source.name).opencode]
        omp_tools, spawns = omp_agents.resolve_tools_and_spawns(source)
        roles.append({
            "role": source.name,
            "name": source.name,
            "model": model,
            "thinking_level": source.effort,
            "read_summarize": False if source.name in omp_agents.DISABLE_READ_SUMMARIZE_ROLES else None,
            "tools": omp_tools,
            "spawns": spawns,
        })
        installed_roles.append(
            _installed_role(target, omp_agents.omp_agent_filename(source.name), source)
        )
    drift = {
        "status": "clean" if not (added or changed or removed) else "drift",
        "added": added,
        "changed": changed,
        "removed": removed,
    }
    installed_roles.sort(key=lambda item: item["role"])
    installed_status = "clean"
    if any(role["status"] != "installed" for role in installed_roles):
        installed_status = "findings"
    return {
        "scope": scope,
        "target": str(target.path if isinstance(target, omp_agents.PinnedDirectory) else target),
        "plugin": plugin,
        "roles": sorted(roles, key=lambda item: item["role"]),
        "installed": {"status": installed_status, "roles": installed_roles},
        "drift": drift,
        "shadows": _shadow_report(
            project_context if scope == "personal" else None,
            [source.name for source in sources],
        ),
        "runtime": dict(RUNTIME_UNVERIFIED),
    }


def exit_status(report: dict[str, Any]) -> int:
    return 1 if (
        report["drift"]["status"] == "drift"
        or report["shadows"]["status"] == "findings"
        or report["installed"]["status"] == "findings"
    ) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--plugin-root", required=True, type=Path)
    parser.add_argument("--scope", choices=("personal", "project"), required=True)
    parser.add_argument("--project-context", type=Path)
    args = parser.parse_args(argv)
    try:
        report = inspect_install(
            target=args.target,
            plugin_root=args.plugin_root,
            scope=args.scope,
            project_context=args.project_context,
        )
    except omp_agents.SpecViolation as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    print(json.dumps(report, indent=2))
    return exit_status(report)


if __name__ == "__main__":
    raise SystemExit(main())
