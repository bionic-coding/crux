"""Generate Codex-native subagent TOML from crux's role definitions."""

from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

class _BrokenInstall(Exception):
    """Stands in for `models_catalog.SpecViolation` when that module is absent.

    Only bound when `models_catalog.py` could not be loaded at all, which means
    the install is missing half of a pair that ships together. Nothing catches
    this name specifically — it exists so `SpecViolation` is always importable
    from this module, which is what lets the failure be reported at first use
    instead of crashing the installer's own import statement.
    """


class _DeferredCatalogFault:
    """A `models_catalog` stand-in that raises on first real use.

    Every attribute access raises, carrying the original import error as the
    cause. `SpecViolation` is the one attribute served normally, so a caller
    that catches `models_catalog.SpecViolation` still has a class to catch.
    """

    def __init__(self, path: Path, cause: BaseException) -> None:
        self._path = path
        self._cause = cause
        self.SpecViolation = _BrokenInstall

    def __getattr__(self, name: str) -> Any:
        raise _BrokenInstall(
            f"cannot load {self._path}: {self._cause} — this file ships beside "
            "codex_agents.py and the install is missing it"
        ) from self._cause


# Import the shared catalog reader by name when scripts/ is on sys.path (the
# regenerator and the installer both put it there), and by file location
# otherwise. Mirrors how validate-promptbook.py reaches _yaml_min.
#
# THIS BLOCK MUST NOT RAISE. `install-codex-agents` imports names from this
# module at module level and turns exactly one exception type into structured
# exit-2 JSON. An exception raised while THIS module executes happens before
# that import completes, so no `except SpecViolation` can catch it: the
# installer dies with a traceback and exit 1. `spec_from_file_location` on an
# absent `models_catalog.py` raised FileNotFoundError from `exec_module` and
# did exactly that. The failure is DEFERRED to first use instead.
#
# Only the staged release artifact can see this; the dev tree always has the
# file on the path.
try:  # pragma: no cover - one branch per caller's sys.path
    import models_catalog
except ImportError:  # pragma: no cover
    models_catalog = None

if models_catalog is None:
    _CATALOG_PATH = Path(__file__).resolve().parent / "models_catalog.py"
    _spec = importlib.util.spec_from_file_location("models_catalog", _CATALOG_PATH)
    if _spec is not None and _spec.loader is not None and _CATALOG_PATH.is_file():
        models_catalog = importlib.util.module_from_spec(_spec)
        # Register before exec: `dataclasses` resolves a class's own module out
        # of sys.modules while processing it, and an unregistered module makes
        # that lookup return None.
        sys.modules.setdefault("models_catalog", models_catalog)
        try:
            _spec.loader.exec_module(models_catalog)
        except Exception as _exc:  # noqa: BLE001 - re-raised on use, not here
            sys.modules.pop("models_catalog", None)
            models_catalog = _DeferredCatalogFault(_CATALOG_PATH, _exc)
    else:
        models_catalog = _DeferredCatalogFault(
            _CATALOG_PATH, FileNotFoundError(str(_CATALOG_PATH))
        )


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PLUGIN_ROOT / "agents"
OUTPUT_PREFIX = "crux-"

# Re-exported, not redefined. `install-codex-agents` catches exactly one
# exception type and turns it into structured exit-2 JSON; a second type would
# escape as a traceback, so a catalog fault and a source fault must be the same
# class.
SpecViolation = models_catalog.SpecViolation


# TOML basic-string escapes (TOML v1.0.0 §String). json.dumps is NOT a correct
# TOML encoder: with ensure_ascii it emits UTF-16 surrogate pairs
# (`\uD83D\uDE00`) for astral-plane codepoints, which TOML rejects (an escape
# must be a Unicode *scalar* value). TOML's own escapes are `\uXXXX` (BMP) and
# `\UXXXXXXXX` (astral) — so we encode basic strings ourselves, fail-closed.
_TOML_BASIC_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def _toml_basic_string(value: str) -> str:
    """Encode a Python str as a TOML basic string (quoted, correctly escaped).

    Emits printable characters (incl. non-ASCII, incl. astral-plane) literally
    as UTF-8, escapes the TOML control set, and escapes remaining control
    characters as `\\uXXXX` — never a lone/paired surrogate, so the output is
    always valid TOML.
    """
    out = ['"']
    for ch in value:
        if ch in _TOML_BASIC_ESCAPES:
            out.append(_TOML_BASIC_ESCAPES[ch])
        elif ch < " " or ch == "\x7f":  # other C0 controls + DEL
            out.append(f"\\u{ord(ch):04X}")
        else:
            out.append(ch)  # printable BMP + astral, emitted as literal UTF-8
    out.append('"')
    return "".join(out)


# Provenance (ADR-0046 clause 6a, as narrowed by ADR-0071 §7). The Codex model
# slugs are an external contract owned by OpenAI, not crux. They no longer live
# in this module: each level row in `crux/catalog/models.yml` carries its own
# `codex:` cell with `model`, `reasoning_effort`, and the dated `verified` /
# `source` fields a validator can read. Codex custom-agent `model = …` requires
# a concrete catalog slug — a bare `gpt-5.6` is a crux-router-only alias and
# would not resolve — and rule V5(a) refuses any slug absent from the router's
# `models` registry. No live-network validation is ever performed against this
# contract (ADR-0046 clause 6): re-verify by reading the current docs or the
# `codex` catalog, never by calling the service.


@dataclass(frozen=True)
class SourceAgent:
    name: str
    description: str
    tools: frozenset[str]
    body: str


def _frontmatter_field(frontmatter: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}:[ \t]*(.+)$", frontmatter, re.MULTILINE)
    if not match:
        raise SpecViolation(f"missing {name}: frontmatter field")
    value = match.group(1).strip()
    if not value:
        raise SpecViolation(f"empty {name}: frontmatter field")
    return value


def parse_source(path: Path) -> SourceAgent:
    """Parse the stable source-agent contract used by the Claude projection.

    **[SECURITY:S5] A symlinked source leaf is refused.** Byte-for-byte the
    same reasoning as `opencode_agents.parse_source`: this read is where a
    `crux/agents/*.md` file's content enters a generated Codex agent file, so
    following a planted link would render out-of-tree content into
    `.codex/agents/crux-<role>.toml`. Checked before `read_text` so a dangling
    link is a `SpecViolation` rather than a `FileNotFoundError` traceback.
    Change one, change both.
    """
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

    tools = frozenset(token.strip() for token in _frontmatter_field(frontmatter, "tools").split(",") if token.strip())
    has_edit, has_write = "Edit" in tools, "Write" in tools
    if has_edit != has_write:
        raise SpecViolation(f"{path}: Edit and Write must be granted together")

    body = match.group("body").strip()
    if not body:
        raise SpecViolation(f"{path}: empty agent body")

    return SourceAgent(
        name=name,
        description=_frontmatter_field(frontmatter, "description"),
        tools=tools,
        body=body,
    )


def codex_agent_name(source_name: str) -> str:
    """Namespace generated agents so target projects' own roles do not collide."""
    return f"crux_{source_name.replace('-', '_')}"


def codex_agent_filename(source_name: str) -> str:
    return f"{OUTPUT_PREFIX}{source_name}.toml"


# ADR-0092 item 3 projection (Codex, faithful-or-drop): the new agent fields all
# DROP on Codex — maxTurns (no per-subagent turn cap; only the global
# `agents.max_concurrent_threads_per_session`), effort (`model_reasoning_effort`
# is pinned from the models.yml level row per ADR-0046, so the frontmatter field
# is Claude-only-effective and validate-catalog.py warns when it is set), skills
# (Codex cannot express a per-subagent preload, so registering it globally would
# not be faithful), memory, isolation, and disallowedTools (Codex exposes only
# the coarse `sandbox_mode`, no faithful deny target). None is rendered below.
# The Claude dispatch tool `Agent` (renamed from `Task` per ADR-0092 item 4) and
# its restricted `Agent(role)` form project to the binding prose directive
# below: Codex has no spawn tool, so delegation returns to the parent.
def _developer_instructions(source: SourceAgent) -> str:
    return f"""You are the Codex projection of Crux's {source.name} role.

Codex compatibility rules:
- The source contract below may name Claude Code tools. Treat those names as
  capabilities, not literal commands: use only the Codex tools available to this
  session.
- Your configured sandbox is a default boundary. Parent-session overrides can be
  broader, so the source role restrictions remain binding even when Codex permits
  more actions.
- Do not spawn subagents. Codex's default agent depth lets the parent agent
  spawn this direct child but prevents nested delegation. Return any proposed
  delegation to the parent agent instead.
- Use a Crux skill only when it is available in the current Codex session. Report a
  missing capability instead of claiming the skill or another agent was invoked.

{source.body}

Codex execution override (binding): The role contract above originated in Claude
Code and may instruct you to use `Agent` or to delegate to another role. In this
direct child session, do not invoke `Agent` and do not spawn another agent. Return
the proposed handoff, role, and required context to the parent agent, which owns
all Codex delegation at the default agent depth.
"""


def render_agent(source: SourceAgent, runtime: Any) -> str:
    """Render one Codex custom-agent TOML file.

    `runtime` is the level row's already-resolved Codex cell (a
    `models_catalog.CodexRuntime`), so this function performs no lookup and
    cannot resolve an agent the catalog does not name.
    """
    # Provenance (ADR-0046 clause 6a): the field set below (name, description,
    # model, model_reasoning_effort, sandbox_mode, developer_instructions) and
    # the sandbox_mode enum (`read-only` / `workspace-write`) are per the Codex
    # custom-agent TOML schema, an external contract owned by OpenAI, verified
    # as of 2026-07-09. No live-network validation is ever performed against
    # this contract (ADR-0046 clause 6). The model/effort pair itself comes from
    # the catalog level row; see the provenance note at the top of this module.
    # Sandbox mapping rationale (ADR-0046 clause 7 / render contract): the crux
    # agent contract grants Edit and Write together (parse_source enforces
    # has_edit == has_write), so filesystem-mutating capability is fully
    # captured by the presence of `Edit` alone. A role that can Edit/Write maps
    # to Codex `workspace-write`; a role without it maps to the least-privilege
    # `read-only`. Read/Bash/WebFetch etc. do not widen the sandbox — only the
    # Edit/Write pair does.
    sandbox_mode = "workspace-write" if "Edit" in source.tools else "read-only"
    values = {
        "name": codex_agent_name(source.name),
        "description": source.description,
        "model": runtime.model,
        "model_reasoning_effort": runtime.reasoning_effort,
        "sandbox_mode": sandbox_mode,
        "developer_instructions": _developer_instructions(source),
    }
    return "\n".join(f"{key} = {_toml_basic_string(value)}" for key, value in values.items()) + "\n"


def generate(source_dir: Path = SOURCE_DIR, catalog: Any | None = None) -> dict[str, str]:
    """Return generated Codex agent files keyed by their output filename.

    Loads the catalog first. `models_catalog.load()` runs the schema, roster
    and reference-graph rules fail-closed before returning, so an agent with no
    roster entry — and a roster entry with no agent file — both raise here,
    before any caller reaches `write()`. The reverse check this function used
    to perform by hand is that loader's roster rule; keeping a copy would be a
    second place encoding the same fact.
    """
    paths = sorted(source_dir.glob("*.md"))
    if not paths:
        raise SpecViolation(f"no source agents under {source_dir}")
    if catalog is None:
        catalog = models_catalog.load(agents_dir=source_dir)

    generated: dict[str, str] = {}
    for path in paths:
        source = parse_source(path)
        filename = codex_agent_filename(source.name)
        if filename in generated:
            raise SpecViolation(f"duplicate generated filename {filename!r}")
        generated[filename] = render_agent(source, catalog.resolve(source.name).codex)
    return generated


def diff(output_dir: Path, generated: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    """Return (added, changed, removed) for Crux-managed Codex agent files only.

    Fail-closed on any on-disk crux-*.toml leaf that is a symlink: reading
    through it (to compare content) or later writing through it would touch the
    link target, so refuse with a clean SpecViolation instead of a raw
    FileNotFoundError (dangling link) or a silent through-read (live link). This
    keeps the symlink-refusal behavior uniform with write() and gives callers a
    single structured error rather than an OSError leaking out mid-scan.
    """
    on_disk: dict[str, str] = {}
    if output_dir.is_dir():
        symlinked = sorted(
            path.name
            for path in output_dir.glob(f"{OUTPUT_PREFIX}*.toml")
            if path.is_symlink()
        )
        if symlinked:
            raise SpecViolation(
                "refusing to diff through crux-*.toml symlink(s) (would read/"
                "write the link target): " + ", ".join(symlinked)
            )
        on_disk = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted(output_dir.glob(f"{OUTPUT_PREFIX}*.toml"))
        }
    added = sorted(set(generated) - set(on_disk))
    changed = sorted(name for name in set(generated) & set(on_disk) if generated[name] != on_disk[name])
    removed = sorted(set(on_disk) - set(generated))
    return added, changed, removed


def _refuse_leaf_symlinks(output_dir: Path, names: list[str]) -> None:
    """Fail-closed if any leaf crux-*.toml this run would write/remove is a symlink.

    Security (ADR-0046 clause 7, S5): `write()` is shared by BOTH the installer
    and the direct generator. `Path.write_text` follows a symlink and would
    clobber the link's target — an in-repo OR out-of-repo victim — even though
    the directory-level containment check (installer `_containment_error`)
    passed, because that check permits a *contained* `.codex/agents/` symlink
    but says nothing about an individual leaf file being a link. So before any
    write, refuse every leaf that is itself a symlink, regardless of whether its
    target is contained or escaping, and regardless of `--force`. This is not
    symlink prohibition at the directory level (ADR-0046 keeps the contained
    directory-symlink allowance) — it is leaf-file clobber prevention. `unlink`
    on a stale link is safe (it removes the link, not the target); we refuse it
    here anyway so the failure mode is uniform and diagnosable rather than
    silently deleting a user-authored crux-*.toml symlink.

    This check is redundant TODAY — `write()` calls `diff()` first, and `diff()`
    already refuses a symlinked crux-*.toml leaf — but it is retained
    DELIBERATELY as a standalone last-line defense: were that earlier refusal
    ever narrowed or removed by a future edit, this check must still
    independently refuse a symlinked leaf. Do not delete it as "dead"/redundant.
    """
    offenders = sorted(name for name in names if (output_dir / name).is_symlink())
    if offenders:
        raise SpecViolation(
            "refusing to write through crux-*.toml symlink(s) (would clobber the "
            "link target): " + ", ".join(offenders)
        )


def write(output_dir: Path, generated: dict[str, str], *, remove_stale: bool = True) -> tuple[list[str], list[str]]:
    """Write Crux-managed files without touching a project's unrelated agents.

    Refuses fail-closed (SpecViolation) before writing if any leaf crux-*.toml
    it would create/overwrite/remove is a symlink, so neither the installer nor
    the direct generator can clobber a link target. Returns (written, removed);
    `removed` is empty when `remove_stale=False`.
    """
    _, _, removed = diff(output_dir, generated)
    stale = removed if remove_stale else []
    # `mkdir(exist_ok=True)` accepts an existing DIRECTORY and raises
    # FileExistsError on anything else at that path, so a regular file — or a
    # symlink that does not resolve to a directory — would end the run in a
    # traceback instead of the structured SpecViolation both callers of write()
    # translate to exit 2: install-codex-agents prints it as JSON on stdout, and
    # generate-codex-agents prints it on stderr (that script's documented exit-2
    # form). The two callers arrange their handlers differently:
    # generate-codex-agents wraps generate(), diff(), and write() in one
    # try/except, while install-codex-agents wraps generate() plus diff() in one
    # handler and write() in a second. Either shape routes every SpecViolation
    # from all three calls to an except clause, so none escapes as a traceback.
    # `is_symlink() or exists()` is the lexists test: it sees a dangling
    # link, which `exists()` alone reports as absent. A symlink TO a directory
    # still passes, preserving the contained-directory-symlink allowance.
    if (output_dir.is_symlink() or output_dir.exists()) and not output_dir.is_dir():
        raise SpecViolation(
            f"refusing to write: {output_dir} exists and is not a directory"
        )
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        # A parent component that is a file, a read-only filesystem, a revoked
        # permission: surface every mkdir failure as a structured error too.
        raise SpecViolation(f"cannot create {output_dir}: {exc}") from exc
    # Check writes AND stale removals up front — nothing is written until every
    # affected leaf is proven not to be a symlink (fail-closed, no partial run).
    _refuse_leaf_symlinks(output_dir, list(generated) + stale)
    for name, content in generated.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    for name in stale:
        (output_dir / name).unlink()
    return sorted(generated), stale
