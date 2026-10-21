"""Project crux's role definitions into OMP (Oh My Pi) agent Markdown.

`crux/agents/*.md` (Claude Code format) is the single source of truth. This
module projects the 10 roles into OMP's native task-agent Markdown format
(`omp://task-agent-discovery.md`), shared by:

  - `generate-omp-agents.py` — the standalone CLI generator (`--output-dir`).
  - `crux/skills/install-omp-agents/scripts/install.py` — the installer that
    writes the projection into `~/.omp/agent/agents/` by default (personal
    scope) or `<repo>/.omp/agents/` when `--repo-root` is selected.
  - `omp_agent_health.py` — the static health and shadow inspector.

Transformation rules:
  - name: preserved verbatim (exact bare role name: `architect`, `commander`, …)
  - description: verbatim
  - model: ordered selector list `["@crux_<role_underscored>", "<resolved_openrouter_model>"]`
    so OMP users can customize per-role models via `modelRoles` in
    `~/.omp/agent/config.yml` while falling back to the catalog's resolved
    OpenRouter model out of the box.
  - effort -> thinking-level: when `effort:` is present in source frontmatter,
    projected as `thinking-level: <effort>`.
  - read-summarize: `false` for `wayfinder` and `librarian` so reconnaissance
    and doc-retrieval roles read exact file text without structural code
    summaries.
  - skills: omitted from `autoloadSkills` so OMP keeps its native lazy `skill://`
    discovery (loading skills via `read skill://<name>` only when needed, rather
    than bloating every child session's initial prompt).
  - tools & spawns:
      Claude Code's `tools:` mixes regular tools (`Read`, `Edit`, `Write`, `Bash`,
      `Grep`, `Glob`, `TodoWrite`, `WebSearch`, `WebFetch`, `Skill`, `SendMessage`)
      and subagent grants (`Agent` or `Agent(role)`).
      OMP parses `tools:` and `spawns:` as separate frontmatter fields:
        * Regular tools map to OMP built-in tool names:
          Read -> read, Grep -> grep + find (OMP's semantic search), Glob -> glob,
          Edit -> edit, Write -> write, Bash -> bash, TodoWrite -> todo,
          WebSearch -> web_search.
          WebFetch and Skill are dropped because OMP's `read` handles URLs and
          `skill://<name>` URIs natively.
          SendMessage is dropped because OMP subagents return results via `yield`
          and receive parent steering natively.
        * `Agent(role)` entries populate `spawns: [role1, role2, ...]` (sorted);
          `wayfinder` is also mapped alongside OMP's native `scout` so callers
          can use eitherOMP's `scout` or `wayfinder`.
        * Bare `Agent` sets `spawns: "*"` and adds `task` to `tools`.
        * No `Agent` grant (or `Agent` in `disallowedTools`) omits `task` from
          `tools` and omits `spawns` (so the child cannot spawn subagents).
  - body: preserved verbatim, preceded by a concise OMP runtime compatibility
    header binding tool names and OMP's native capabilities.
"""

from __future__ import annotations

import importlib.util
import os
import re
import stat
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class _BrokenInstall(Exception):
    """Stands in for `models_catalog.SpecViolation` when that module is absent."""


class _DeferredCatalogFault:
    """A `models_catalog` stand-in that raises on first real use."""

    def __init__(self, path: Path, cause: BaseException) -> None:
        self._path = path
        self._cause = cause
        self.SpecViolation = _BrokenInstall

    def __getattr__(self, name: str) -> Any:
        raise _BrokenInstall(
            f"cannot load {self._path}: {self._cause} — this file ships beside "
            "omp_agents.py and the install is missing it"
        ) from self._cause


try:  # pragma: no cover - one branch per caller's sys.path
    import models_catalog
except ImportError:  # pragma: no cover
    models_catalog = None

if models_catalog is None:
    _CATALOG_PATH = Path(__file__).resolve().parent / "models_catalog.py"
    _spec = importlib.util.spec_from_file_location("models_catalog", _CATALOG_PATH)
    if _spec is not None and _spec.loader is not None and _CATALOG_PATH.is_file():
        models_catalog = importlib.util.module_from_spec(_spec)
        sys.modules.setdefault("models_catalog", models_catalog)
        try:
            _spec.loader.exec_module(models_catalog)
        except Exception as _exc:  # noqa: BLE001
            sys.modules.pop("models_catalog", None)
            models_catalog = _DeferredCatalogFault(_CATALOG_PATH, _exc)
    else:
        models_catalog = _DeferredCatalogFault(
            _CATALOG_PATH, FileNotFoundError(str(_CATALOG_PATH))
        )


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PLUGIN_ROOT / "agents"

SpecViolation = models_catalog.SpecViolation

# Ordered canonical OMP tool emission order.
OMP_TOOL_ORDER = (
    "read",
    "grep",
    "glob",
    "find",
    "edit",
    "write",
    "bash",
    "task",
    "todo",
    "web_search",
)

# Claude Code tool name -> OMP built-in tool name(s).
# `Grep` also grants OMP's native `find` (semantic search).
# `WebFetch` and `Skill` are handled natively by OMP's `read` (which every role
# already holds), and `SendMessage` is handled by OMP's native task/yield/steer
# channels, so none of those add redundant tool entries.
TOOL_MAP: dict[str, tuple[str, ...]] = {
    "Read": ("read",),
    "Grep": ("grep", "find"),
    "Glob": ("glob",),
    "Edit": ("edit",),
    "Write": ("write",),
    "Bash": ("bash",),
    "TodoWrite": ("todo",),
    "WebSearch": ("web_search",),
}

HOST_ONLY_TOOLS = frozenset({"SendMessage", "Monitor", "Skill", "WebFetch"})

DENY_TOOL_MAP: dict[str, tuple[str, ...]] = {
    **TOOL_MAP,
    "WebFetch": ("read",),
    "Skill": ("read",),
    "Agent": ("task",),
}

# Reconnaissance and retrieval roles that should read raw text without
# structural code summarization.
DISABLE_READ_SUMMARIZE_ROLES = frozenset({"wayfinder", "librarian"})

_AGENT_TOKEN_RE = re.compile(r"^Agent(?:\((?P<role>[a-z0-9-]+)\))?$")


@dataclass(frozen=True)
class SourceAgent:
    name: str
    description: str
    tools: tuple[str, ...]
    disallowed_tools: tuple[str, ...]
    effort: str | None
    skills: tuple[str, ...]
    body: str


@dataclass
class PinnedDirectory:
    """An open agent directory whose identity remains stable across path swaps."""

    path: Path
    _fd: int

    def duplicate_fd(self) -> int:
        return os.dup(self._fd)

    def close(self) -> None:
        if self._fd >= 0:
            os.close(self._fd)
            self._fd = -1

    def __enter__(self) -> "PinnedDirectory":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


def managed_filenames(catalog: Any | None = None) -> frozenset[str]:
    """The crux-managed output filenames — `<role>.md` for each role in the roster."""
    if catalog is None:
        catalog = models_catalog.load()
    return catalog.managed_filenames


def __getattr__(name: str) -> Any:
    if name == "MANAGED_FILENAMES":
        return managed_filenames()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _frontmatter_field(frontmatter: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}:[ \t]*(.+)$", frontmatter, re.MULTILINE)
    if not match:
        raise SpecViolation(f"missing {name}: frontmatter field")
    value = match.group(1).strip()
    if not value:
        raise SpecViolation(f"empty {name}: frontmatter field")
    return value


def _optional_frontmatter_field(frontmatter: str, name: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}:[ \t]*(.*)$", frontmatter, re.MULTILINE)
    if not match:
        return None
    val = _strip_yaml_comment(match.group(1)).strip()
    return val if val else None


def _strip_yaml_comment(value: str) -> str:
    """Remove a YAML comment while preserving hashes inside quoted strings."""
    out: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(value):
        char = value[index]
        if quote == '"' and char == "\\" and index + 1 < len(value):
            out.extend((char, value[index + 1]))
            index += 2
            continue
        if quote == "'" and char == "'" and index + 1 < len(value) and value[index + 1] == "'":
            out.extend((char, value[index + 1]))
            index += 2
            continue
        if quote is not None:
            out.append(char)
            if char == quote:
                quote = None
            index += 1
            continue
        if char in ('"', "'"):
            quote = char
            out.append(char)
        elif char == "#":
            break
        else:
            out.append(char)
        index += 1
    return "".join(out)


def _unquote_token(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
        if token[0] == "'":
            return token[1:-1].replace("''", "'")
        return token[1:-1]
    return token


def _frontmatter_skills(frontmatter: str, path: Path) -> tuple[str, ...]:
    """Read the explicit, compact ``skills: [a, b]`` source declaration."""
    declarations = re.findall(r"(?m)^skills:[ \t]*(.*)$", frontmatter)
    if len(declarations) > 1:
        raise SpecViolation(f"{path}: duplicate top-level skills key")
    value = _strip_yaml_comment(_frontmatter_field(frontmatter, "skills")).strip()
    if not (value.startswith("[") and value.endswith("]")):
        raise SpecViolation(f"{path}: skills must use a bracketed list")
    inner = value[1:-1].strip()
    tokens = tuple(token.strip() for token in inner.split(",")) if inner else ()
    if any(not token for token in tokens):
        raise SpecViolation(f"{path}: skills list contains an empty element")
    skills = tuple(_unquote_token(token) for token in tokens)
    if any(not re.fullmatch(r"[a-z0-9][a-z0-9-]*", skill) for skill in skills):
        raise SpecViolation(f"{path}: invalid skills declaration")
    if len(set(skills)) != len(skills):
        raise SpecViolation(f"{path}: duplicate skill declaration")
    return tuple(sorted(skills))


def _frontmatter_disallowed_tools(frontmatter: str, path: Path) -> tuple[str, ...]:
    dt_key = re.search(r"^disallowedTools[ \t]*:[ \t]*(.*)$", frontmatter, re.MULTILINE)
    if not dt_key:
        return ()
    raw = _strip_yaml_comment(dt_key.group(1)).strip()
    if not raw:
        raise SpecViolation(
            f"{path}: disallowedTools has no inline value — write it inline, e.g. `disallowedTools: Bash, Edit`"
        )
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    tokens: list[str] = []
    for piece in raw.split(","):
        tok = _unquote_token(piece.strip()).strip()
        if tok:
            tokens.append(tok)
    return tuple(tokens)


def parse_source(path: Path) -> SourceAgent:
    """Parse a source agent file under `crux/agents/*.md`, refusing symlinks."""
    if path.is_symlink():
        raise SpecViolation(
            f"{path}: source agent is a symlink — refusing to follow it, because its "
            "target's content would be rendered into the generated agent file"
        )
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(?P<frontmatter>.*?)\n---\n(?P<body>.*)\Z", text, re.DOTALL)
    if not match:
        raise SpecViolation(f"{path}: missing frontmatter block")

    frontmatter = match.group("frontmatter")
    name = _frontmatter_field(frontmatter, "name")
    if name != path.stem:
        raise SpecViolation(f"{path}: name {name!r} does not match filename")

    tools = tuple(
        token.strip()
        for token in _frontmatter_field(frontmatter, "tools").split(",")
        if token.strip()
    )
    has_edit, has_write = "Edit" in tools, "Write" in tools
    if has_edit != has_write:
        raise SpecViolation(f"{path}: Edit and Write must be granted together")

    body = match.group("body").strip()
    if not body:
        raise SpecViolation(f"{path}: empty agent body")

    effort = _optional_frontmatter_field(frontmatter, "effort")
    if effort is not None:
        effort = _unquote_token(effort)

    return SourceAgent(
        name=name,
        description=_frontmatter_field(frontmatter, "description"),
        tools=tools,
        disallowed_tools=_frontmatter_disallowed_tools(frontmatter, path),
        effort=effort,
        skills=_frontmatter_skills(frontmatter, path),
        body=body,
    )


def omp_agent_filename(source_name: str) -> str:
    return f"{source_name}.md"


def resolve_tools_and_spawns(source: SourceAgent) -> tuple[list[str], list[str] | str | None]:
    """Translate Claude Code `tools` + `disallowedTools` to `(omp_tools, omp_spawns)`."""
    allowed: set[str] = set()
    agent_roles: list[str] = []
    has_bare_agent = False

    for tool in source.tools:
        agent_m = _AGENT_TOKEN_RE.match(tool)
        if agent_m:
            role = agent_m.group("role")
            if role:
                agent_roles.append(role)
            else:
                has_bare_agent = True
        elif tool in TOOL_MAP:
            allowed.update(TOOL_MAP[tool])
        elif tool in HOST_ONLY_TOOLS:
            continue
        else:
            raise SpecViolation(
                f"{source.name}: tool {tool!r} has no OMP TOOL_MAP entry; "
                "refusing to silently drop a grant"
            )

    denied: set[str] = set()
    agent_denied = False
    for token in source.disallowed_tools:
        if _AGENT_TOKEN_RE.match(token):
            agent_denied = True
            denied.add("task")
        elif token in DENY_TOOL_MAP:
            denied.update(DENY_TOOL_MAP[token])
        else:
            raise SpecViolation(
                f"{source.name}: disallowedTools entry {token!r} has no OMP mapping"
            )

    spawns: list[str] | str | None
    if agent_denied:
        spawns = None
    elif has_bare_agent:
        spawns = "*"
        allowed.add("task")
    elif agent_roles:
        expanded_roles = set(agent_roles)
        if "wayfinder" in expanded_roles:
            expanded_roles.add("scout")
        spawns = sorted(expanded_roles)
        allowed.add("task")
    else:
        spawns = None

    allowed -= denied
    if "task" not in allowed:
        spawns = None

    ordered_tools = [t for t in OMP_TOOL_ORDER if t in allowed]
    return ordered_tools, spawns


def omp_role_alias(source_name: str) -> str:
    """OMP `modelRoles` alias for a Crux role (`@crux_<role_underscored>`)."""
    return f"@crux_{source_name.replace('-', '_')}"

def _omp_compatibility_preamble(source: SourceAgent) -> str:
    return f"""<!-- BEGIN GENERATED: omp-compat -->
You are the OMP (Oh My Pi) projection of Crux's `{source.name}` role.

OMP runtime rules:
- Use OMP's native tools instead of Claude Code labels: `task` (for `Agent`), `read` (for `Read`, `WebFetch` URLs, and `skill://<name>` skills), `edit` (hashline edits), `write`, `bash`, `grep`, `glob`, `find` (semantic search), `todo` (for `TodoWrite`), and `web_search`.
- When OMP has a simpler or better native capability (`task` parallel batches, `local://<name>.md` shared artifacts, `agent://<id>` peer messaging, `find` semantic search, `scout` for fast read-only reconnaissance), prefer OMP's native way over heavier multi-step workarounds.
- Only load a Crux skill (`read` on `skill://<skill-name>`) when the task needs Crux's tree schema, cycle state, council, or regenerator workflow (declared skills for this role: {', '.join(source.skills) if source.skills else 'none'}). Derive `CRUX_PLUGIN_ROOT` as the parent of the skill's `skills/` directory (or the checkout's `crux/` directory).
- Respect your role's tool and spawn boundaries strictly. Never use `bash` to edit or write files that your role is forbidden from mutating.
<!-- END GENERATED: omp-compat -->"""


def render_agent(source: SourceAgent, model: str) -> str:
    """Render one OMP custom-agent Markdown file (`<role>.md`)."""
    bad = sorted({c for c in model if ord(c) < 0x20 or ord(c) == 0x7F})
    if bad:
        raise SpecViolation(
            f"{source.name}: model value {model!r} contains a control character "
            f"({', '.join(repr(c) for c in bad)})"
        )

    omp_tools, spawns = resolve_tools_and_spawns(source)
    tools_csv = ", ".join(omp_tools)
    role_alias = omp_role_alias(source.name)

    lines = [
        "---",
        f"name: {source.name}",
        f"description: {source.description}",
        f'model: ["{role_alias}", "{model}"]',
    ]
    if source.effort is not None:
        lines.append(f"thinking-level: {source.effort}")
    if source.name in DISABLE_READ_SUMMARIZE_ROLES:
        lines.append("read-summarize: false")
    if omp_tools:
        lines.append(f"tools: [{tools_csv}]")
    else:
        lines.append("tools: []")

    if spawns == "*":
        lines.append('spawns: "*"')
    elif isinstance(spawns, list) and spawns:
        lines.append(f"spawns: [{', '.join(spawns)}]")

    lines.append("---")
    lines.append("")
    lines.append(_omp_compatibility_preamble(source))
    lines.append("")
    lines.append(source.body)
    lines.append("")
    return "\n".join(lines)

def generate(
    source_dir: Path = SOURCE_DIR,
    catalog: Any | None = None,
) -> dict[str, str]:
    """Return generated OMP agent files keyed by their output filename (`<role>.md`)."""
    paths = sorted(source_dir.glob("*.md"))
    if not paths:
        raise SpecViolation(f"no source agents under {source_dir}")
    if catalog is None:
        catalog = models_catalog.load(agents_dir=source_dir)

    generated: dict[str, str] = {}
    for path in paths:
        source = parse_source(path)
        filename = omp_agent_filename(source.name)
        if filename in generated:
            raise SpecViolation(f"duplicate generated filename {filename!r}")
        model = catalog.resolve(source.name).opencode
        generated[filename] = render_agent(source, model)
    return generated


def _is_contained(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def pin_directory(output_dir: Path, *, containment_root: Path | None = None) -> PinnedDirectory:
    """Create and pin ``output_dir`` before a managed read or write."""
    if (output_dir.is_symlink() or output_dir.exists()) and not output_dir.is_dir():
        raise SpecViolation(f"refusing to write: {output_dir} exists and is not a directory")

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    nofollow_flags = flags | getattr(os, "O_NOFOLLOW", 0)
    if containment_root is None:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            resolved = output_dir.resolve()
            directory_fd = os.open(resolved, nofollow_flags)
        except OSError as exc:
            raise SpecViolation(f"cannot create or open {output_dir}: {exc}") from exc
        return PinnedDirectory(resolved, directory_fd)

    try:
        containment_root.mkdir(parents=True, exist_ok=True)
        resolved_root = containment_root.resolve()
        resolved_output = output_dir.resolve()
    except OSError as exc:
        raise SpecViolation(f"cannot resolve agent target {output_dir}: {exc}") from exc
    if not _is_contained(resolved_output, resolved_root):
        raise SpecViolation(
            f"refusing to write: {output_dir} resolves outside selected root {resolved_root}"
        )
    try:
        root_fd = os.open(resolved_root, nofollow_flags)
    except OSError as exc:
        raise SpecViolation(f"cannot open selected root {resolved_root}: {exc}") from exc
    current_fd = root_fd
    try:
        for component in resolved_output.relative_to(resolved_root).parts:
            try:
                os.mkdir(component, dir_fd=current_fd)
            except FileExistsError:
                pass
            next_fd = os.open(component, nofollow_flags, dir_fd=current_fd)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
    except OSError as exc:
        if current_fd != root_fd:
            os.close(current_fd)
        os.close(root_fd)
        raise SpecViolation(f"cannot create or open {output_dir}: {exc}") from exc
    if current_fd != root_fd:
        os.close(root_fd)
    return PinnedDirectory(resolved_output, current_fd)


def _directory_fd(output_dir: Path | PinnedDirectory) -> int | None:
    if isinstance(output_dir, PinnedDirectory):
        return output_dir.duplicate_fd()
    if not output_dir.is_dir():
        return None
    try:
        return os.open(output_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError as exc:
        raise SpecViolation(f"cannot open {output_dir}: {exc}") from exc


def _managed_names(
    output_dir: Path | PinnedDirectory,
    managed: frozenset[str] | None = None,
) -> list[str]:
    """List managed leaves present in ``output_dir`` without following leaf links."""
    if managed is None:
        managed = managed_filenames()
    directory_fd = _directory_fd(output_dir)
    if directory_fd is None:
        return []
    try:
        entries = os.listdir(directory_fd)
    except OSError as exc:
        raise SpecViolation(f"cannot list {output_dir}: {exc}") from exc
    finally:
        os.close(directory_fd)
    return sorted(name for name in entries if name in managed)


def read_managed_file(output_dir: Path | PinnedDirectory, name: str) -> tuple[str, str | None, str | None]:
    """Read one leaf safely as ``(status, text, reason)``."""
    try:
        directory_fd = _directory_fd(output_dir)
    except SpecViolation as exc:
        return "unsafe", None, f"cannot open agent directory: {exc}"
    if directory_fd is None:
        return "missing", None, None
    try:
        try:
            before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return "missing", None, None
        except OSError as exc:
            return "unsafe", None, str(exc)
        if stat.S_ISLNK(before.st_mode):
            return "unsafe", None, "managed agent file is a symlink"
        if not stat.S_ISREG(before.st_mode):
            return "unsafe", None, "managed agent file is not a regular file"
        leaf_flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            leaf_fd = os.open(name, leaf_flags, dir_fd=directory_fd)
        except OSError as exc:
            return "unsafe", None, str(exc)
        try:
            after = os.fstat(leaf_fd)
            if not stat.S_ISREG(after.st_mode):
                return "unsafe", None, "managed agent file changed to a nonregular file"
            chunks = []
            while True:
                chunk = os.read(leaf_fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
        finally:
            os.close(leaf_fd)
    finally:
        os.close(directory_fd)
    try:
        return "regular", b"".join(chunks).decode("utf-8"), None
    except UnicodeDecodeError as exc:
        return "malformed", None, f"invalid UTF-8: {exc}"


def safe_diff(
    output_dir: Path | PinnedDirectory,
    generated: dict[str, str],
    *,
    managed: frozenset[str] | None = None,
) -> tuple[list[str], list[str], list[str], dict[str, tuple[str, str | None]]]:
    """Return drift and reportable unsafe/malformed managed entries without reading them unsafely."""
    if managed is None:
        managed = managed_filenames()
    on_disk: dict[str, str] = {}
    problems: dict[str, tuple[str, str | None]] = {}
    names = _managed_names(output_dir, managed)
    for name in names:
        status, text, reason = read_managed_file(output_dir, name)
        if status == "regular":
            assert text is not None
            on_disk[name] = text
        else:
            problems[name] = (status, reason)
    present = set(names)
    added = sorted(set(generated) - present)
    changed = sorted(
        name for name in set(generated) & present
        if name in problems or generated[name] != on_disk.get(name)
    )
    removed = sorted(present - set(generated))
    return added, changed, removed, problems


def diff(
    output_dir: Path | PinnedDirectory,
    generated: dict[str, str],
    *,
    managed: frozenset[str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """Return drift for a strict installer operation, refusing unsafe leaves."""
    added, changed, removed, problems = safe_diff(output_dir, generated, managed=managed)
    if problems:
        details = ", ".join(f"{name} ({reason or status})" for name, (status, reason) in sorted(problems.items()))
        raise SpecViolation(f"refusing to diff through unsafe or malformed managed agent leaf(s): {details}")
    return added, changed, removed


def _refuse_leaf_symlinks(output_dir: Path | PinnedDirectory, names: list[str]) -> None:
    offenders = []
    for name in names:
        status, _, reason = read_managed_file(output_dir, name)
        if status not in {"regular", "missing"}:
            offenders.append(f"{name} ({reason or status})")
    if offenders:
        raise SpecViolation(
            "refusing to write through unsafe managed agent leaf(s): " + ", ".join(offenders)
        )


def write(
    output_dir: Path | PinnedDirectory,
    generated: dict[str, str],
    *,
    remove_stale: bool = True,
    managed: frozenset[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Write Crux-managed OMP agent files without touching unrelated agents."""
    if not isinstance(output_dir, PinnedDirectory):
        with pin_directory(output_dir) as pinned:
            return write(pinned, generated, remove_stale=remove_stale, managed=managed)

    added, changed, removed = diff(output_dir, generated, managed=managed)
    stale = removed if remove_stale else []
    written = sorted(added + changed)
    _refuse_leaf_symlinks(output_dir, written + stale)
    try:
        directory_fd = output_dir.duplicate_fd()
    except OSError as exc:
        raise SpecViolation(f"cannot open {output_dir}: {exc}") from exc
    try:
        for name in written:
            temporary = f".{name}.{uuid.uuid4().hex}.tmp"
            try:
                temporary_fd = os.open(
                    temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory_fd
                )
                with os.fdopen(temporary_fd, "wb") as handle:
                    handle.write(generated[name].encode("utf-8"))
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
            except OSError as exc:
                try:
                    os.unlink(temporary, dir_fd=directory_fd)
                except OSError:
                    pass
                raise SpecViolation(f"cannot atomically replace {name}: {exc}") from exc
        for name in stale:
            try:
                os.unlink(name, dir_fd=directory_fd)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise SpecViolation(f"cannot remove stale {name}: {exc}") from exc
    finally:
        os.close(directory_fd)
    return written, stale
