#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Render the portable guide from one prose template and shipped source contracts.

Scope: plugin authoring (including staged plugin trees), never consumer projects.
Both outputs contain the same bytes. The root preview is maintained only when
already present or when the development checkout has its root AGENTS.md.
Missing/malformed inputs refuse before any output is replaced. Exit 0 means
generated/clean, 1 means findings or dry-run drift, 2 means environment failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import authoring_scope

FORMAT_VERSION = 1
SCHEMAS = (
    "cycle.schema.json", "cycle-queue.schema.json", "test-evidence.schema.json",
    "adr-provenance.schema.json", "cycle-council-attempt.schema.json", "cycle-council.schema.json",
)
# Prefixes identify canonical sections without depending on historical citation suffixes.
CONTRACTS = {
    "## 5.B.": ("### Objectives contract", "objectives-contract"),
    "## 6.": ("### Operation log contract", "operation-log-contract"),
    "### journal (": ("### Journal contract", "journal-contract"),
    "### briefs (": ("### Brief lifecycle and authorship", "brief-contract"),
    "## 7.": ("### Complete manifest contract", "manifest-contract"),
    "## 11.A.": ("### ADR frontmatter and governs", "adr-contract"),
    "## 11.D.": ("### ADR body contract", "adr-body-contract"),
    "### 15.2": ("### Invariant frontmatter", "invariant-contract"),
    "### 15.4": ("### Invariant reconciliation", "reconciliation-contract"),
    "### 17.1": ("### Observation frontmatter", "observation-contract"),
    "### 17.2": ("### Observation lifecycle", "observation-lifecycle"),
}
SEMANTIC_SOURCES = (
    "scripts/bionic_config.py", "scripts/cycle_workflow.py", "scripts/decision_policy.py",
    "scripts/adr_provenance.py", "scripts/cycle_queue.py", "scripts/test_evidence.py",
    "scripts/cycle_council.py", "scripts/council_policy.py",
    "skills/ingest-research/SKILL.md", "skills/refresh-research-sources/SKILL.md",
    "skills/transition-brief/SKILL.md", "skills/cycle/references/testing.md",
    "skills/cycle/references/review.md", "templates/BRIEF-template.md",
    "templates/objectives.md.tmpl", "templates/ADR-template.md", "templates/manifest.yml.tmpl",
)


class GuideError(ValueError):
    """An invalid or unavailable source contract; do not publish partial output."""


def section(text: str, prefix: str) -> str:
    """A complete ATX section, ignoring example headings inside fenced blocks."""
    headings = []
    fence = None
    offset = 0
    for line in text.splitlines(keepends=True):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if match:
            marker, tail = match.groups()
            if fence is None:
                fence = (marker[0], len(marker))
            elif marker[0] == fence[0] and len(marker) >= fence[1] and not tail.strip():
                fence = None
        elif fence is None and (match := re.match(r"^(#{1,6}) (.+)", line)):
            headings.append((offset, len(match[1]), line.rstrip()))
        offset += len(line)
    found = [h for h in headings if h[2].startswith(prefix)
             and (not prefix.endswith(".") or len(h[2]) == len(prefix) or h[2][len(prefix)].isspace())]
    if len(found) != 1:
        raise GuideError(f"expected exactly one source section {prefix!r}, found {len(found)}")
    start, level, _ = found[0]
    end = next((pos for pos, depth, _ in headings if pos > start and depth <= level), len(text))
    return text[start:end].rstrip()


def validate_refs(schema: dict) -> None:
    """Reject required file/network references; every reference resolves in this block."""
    def visit(node):
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                if not isinstance(ref, str) or not (ref == "#" or ref.startswith("#/")):
                    raise GuideError(f"schema reference must resolve offline inside its own block: {ref!r}")
                target = schema
                try:
                    for token in ref[2:].split("/") if ref != "#" else ():
                        token = unquote(token).replace("~1", "/").replace("~0", "~")
                        target = target[int(token)] if isinstance(target, list) else target[token]
                except (KeyError, ValueError, TypeError, IndexError) as exc:
                    raise GuideError(f"unresolved schema reference: {ref}") from exc
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(schema)


def input_paths(plugin_root: Path) -> tuple[Path, ...]:
    """Exact generation input domain, relative to the selected plugin root."""
    names = (
        "templates/micro-crux.md.tmpl", "templates/AGENTS.md.tmpl",
        "scripts/generate-micro-crux.py", "scripts/authoring_scope.py", *SEMANTIC_SOURCES,
        *(f"schemas/{name}" for name in SCHEMAS),
    )
    return tuple(Path(plugin_root) / name for name in sorted(set(names)))


def provenance(plugin_root: Path) -> dict:
    inputs = {}
    for path in input_paths(plugin_root):
        try:
            if path.is_symlink() or not path.is_file():
                raise GuideError(f"missing or nonregular source: crux/{path.relative_to(plugin_root).as_posix()}")
            inputs["crux/" + path.relative_to(plugin_root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise OSError(f"cannot read guide input {path.name}: {exc.strerror}") from exc
    return {"format": "crux.micro-crux-guide", "format_version": FORMAT_VERSION,
            "tree_schema_version": "5", "sources": inputs}


def fenced_example(name: str, language: str, text: str) -> str:
    return f"<!-- BEGIN EXAMPLE: {name} -->\n```{language}\n{text.rstrip()}\n```\n<!-- END EXAMPLE: {name} -->"


def operational_contracts(plugin_root: Path) -> str:
    source = (plugin_root / "templates/AGENTS.md.tmpl").read_text(encoding="utf-8")
    parts = []
    for prefix, (heading, name) in CONTRACTS.items():
        excerpt = section(source, prefix).split("\n", 1)[1].strip()
        # Mark the complete manifest block so examples can be evaluated independently.
        if name == "manifest-contract":
            pattern = r"```yaml\n(.*?)\n```"
            match = re.search(pattern, excerpt, re.S)
            if not match:
                raise GuideError("manifest contract has no YAML field definition")
            excerpt = excerpt[:match.start()] + fenced_example(name, "yaml", match[1]) + excerpt[match.end():]
        parts.append(f"{heading}\n\nSource extract: `crux/templates/AGENTS.md.tmpl`, section `{prefix.lstrip('# ').rstrip('.')}`.\n\n{excerpt}")
    research = (plugin_root / "skills/ingest-research/SKILL.md").read_text(encoding="utf-8")
    registry = section(research, "### 6c.").split("\n", 1)[1].strip()
    parts.append("### Research source registry\n\nSource extract: `crux/skills/ingest-research/SKILL.md`, section 6c.\n\n" + registry)
    return "\n\n".join(parts)


def schema_contracts(plugin_root: Path) -> str:
    parts = []
    for name in SCHEMAS:
        raw = (plugin_root / "schemas" / name).read_bytes()
        schema = json.loads(raw)
        validate_refs(schema)
        title = schema.get("title", name)
        parts.append(f"### {title}\n\nSource: `crux/schemas/{name}`  \nSource SHA-256: `{hashlib.sha256(raw).hexdigest()}`\n\n" +
                     fenced_example(name, "json", json.dumps(schema, indent=2, ensure_ascii=False)))
    return "\n\n".join(parts)


def render(plugin_root: Path) -> str:
    """Return one deterministic guide; read only the supplied source plugin."""
    plugin_root = Path(plugin_root)
    identity = provenance(plugin_root)  # Audit the whole input domain before rendering.
    template = (plugin_root / "templates/micro-crux.md.tmpl").read_text(encoding="utf-8")
    # The prose template uses a variable for illustrative record identity.
    # Rendered examples remain valid records without leaking a development ADR
    # reference into shipped template prose.
    template = template.replace("{{EXAMPLE_ADR_ID}}", "ADR-0001")
    inserts = {
        "{{MICRO_CRUX_PROVENANCE}}": fenced_example("guide-provenance", "json", json.dumps(identity, indent=2, sort_keys=True)),
        "{{MICRO_CRUX_OPERATIONAL_CONTRACTS}}": operational_contracts(plugin_root),
        "{{MICRO_CRUX_JSON_SCHEMAS}}": schema_contracts(plugin_root),
    }
    for marker, value in inserts.items():
        if template.count(marker) != 1:
            raise GuideError(f"guide template requires exactly one {marker}")
        template = template.replace(marker, value)
    if re.search(r"\{\{MICRO_CRUX_[A-Z_]+\}\}", template):
        raise GuideError("unknown guide insertion marker")
    return template.rstrip() + "\n"


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        os.fchmod(descriptor, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, help="target repository; defaults to cwd")
    parser.add_argument("--dry-run", action="store_true", help="report drift without writing")
    args = parser.parse_args(argv)
    root = authoring_scope.resolve_repo_root(args.repo_root)
    if not authoring_scope.is_authoring_checkout(root, __file__):
        return authoring_scope.print_surface_absent()
    try:
        plugin = root / "crux"
        data = render(plugin).encode("utf-8")
        targets = [plugin / "box/micro-crux.md"]
        if (root / "micro-crux.md").exists() or (root / "AGENTS.md").is_file():
            targets.append(root / "micro-crux.md")
        # Refuse symlinks before replacing either target, including symlinked parents.
        for target in targets:
            if any(p.is_symlink() for p in (target, *target.parents) if p == root or root in p.parents):
                raise GuideError(f"symlink guide target: {target.relative_to(root)}")
        changed = [path for path in targets if not path.exists() or path.read_bytes() != data]
        if not args.dry_run:
            for target in changed:
                write_atomic(target, data)
        print(json.dumps({"drift": bool(changed) if args.dry_run else False,
                          "changed": [p.relative_to(root).as_posix() for p in changed],
                          "targets": [p.relative_to(root).as_posix() for p in targets],
                          "guide_sha256": hashlib.sha256(data).hexdigest()}, sort_keys=True))
        return int(args.dry_run and bool(changed))
    except (GuideError, ValueError, KeyError, UnicodeError) as exc:
        print(json.dumps({"drift": True, "error": str(exc)}, sort_keys=True))
        return 1
    except OSError as exc:
        print(f"micro-crux: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
