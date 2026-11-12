"""adr_frontmatter.py — the one fence reader the three ADR generators share.

`generate-adr-index.py`, `generate-lineage.py` and `generate-index-rollup.py`
each build a derived output from ADR frontmatter, and each used to carry its
own copy of the fence regex plus a bare `continue` on no match. A file that
passed the `ADR-*.md` glob but failed that regex was dropped in silence: the
output was written without it, and the next drift check compared the
shortened output against what the generator would now write and found them
equal. The gate was correct about the only thing it measured.

ONE TRAILING SPACE IS ENOUGH. `--- ` does not match `^---\\n`, while
`yaml.safe_load` still parses the block underneath. The corruption is
invisible in a diff viewer and survives review.

THIS MODULE MAKES THE PARSER NO MORE PERMISSIVE. `FENCE_RE` is the regex the
three generators already used, unchanged. A file this module reports is a
file they already refused to read; the difference is that the refusal is now
said out loud, against the INPUT, rather than resolved by omission.

WHY THE INPUT AND NOT THE OUTPUT. The release suite already caught this, via
a lineage test that derives ADR ids from filenames. Its message names
`lineage.md`, so the remedy it implies — regenerate lineage — cannot work:
the generator is the thing that cannot read the file. Every message here
names the path that will not parse.

REFUSAL BEFORE WRITING, the discipline `generate-reviews-index.py` states in
its own docstring: a drift gate that passes on a corpus the writer would
refuse is a crash. Callers validate the WHOLE glob, both tiers, before any
output is written. One unparseable ADR therefore cannot leave a half-written
index, and cannot create an output that did not exist. `generate-index-rollup.py`
reads its output before validating, to locate the region it owns; that read has
no side effect, and its write still follows validation.

Stdlib only. Importers are the three generators named above, four other
readers of ADR frontmatter — `adr-precouncil.py`, `implementation_migration.py`,
`migration_disposition.py` and `observation_admission.py` — and the tests under
`crux/scripts/tests/` that drive them.
"""

from __future__ import annotations

import fnmatch as _fnmatch
import os as _os
import re
import sys as _sys
from pathlib import Path

_sys.path.insert(0, str(Path(__file__).resolve().parent))

import input_lanes as _input_lanes  # noqa: E402

#: The ADR frontmatter fence. Byte-for-byte what the three generators carried
#: before this module existed — the opening `---` on a line of its own, the
#: block, then a closing `---` on a line of its own. Deliberately strict:
#: widening it here would change which documents the generators accept, which
#: is a different decision from reporting the ones they already reject.
FENCE_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)

#: The input glob all three generators walk, in both tiers.
ADR_GLOB = "*.md"
_PREFIXED_ADR_FILENAME_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}-ADR-\d{4}(?:-.+)?\.md$")


def is_adr_filename(name: str) -> bool:
    """Preserve the historical bare glob and admit canonical prefixed ADR names."""
    return (name.startswith("ADR-") and name.endswith(".md")) or bool(_PREFIXED_ADR_FILENAME_RE.fullmatch(name))

#: The one explanation every refusal carries. It names the glob, so a reader
#: knows why the file was considered at all, and it names the fence, so they
#: know what to repair. It also names the failure mode that produced the
#: incident, because that one is invisible on screen.
FENCE_ERROR = (
    "matched the ADR input glob but its frontmatter fence could not be parsed — the file must "
    "open with a line containing exactly `---`, and that block must close with a line "
    "containing exactly `---`. A trailing space on a fence line is enough to fail this while "
    "the YAML underneath still parses, so check the fence bytes rather than the fields."
)


class FenceValidationError(Exception):
    """Raised by a loader when one or more inputs are document-lane findings.

    A finding is an input that fails `FENCE_RE`, or one the process cannot
    read for a cause attributable to its path.

    Carries `errors`, a list of `{"file", "error"}` mappings — one per
    offending file, never one per run, because each file is repaired
    separately and a reader needs every path named.
    """

    def __init__(self, errors: list[dict]) -> None:
        super().__init__(f"{len(errors)} ADR file(s) that could not be read or whose fence does not parse")
        self.errors = errors


def adr_paths(adrs_dir: Path, *, include_archive: bool = True) -> list[Path]:
    """Every file matching the ADR glob under `adrs_dir`, both tiers, sorted.

    The archive tier is included by default because all three generators read
    it: an archived ADR keeps its row in the index, its node in the lineage
    graph and its line in the rollup.

    A tier that does not exist is an empty tier. A tier that exists but cannot
    be listed RAISES the `OSError` that names it: `glob.glob` returns `[]` for
    a directory it cannot read, which would let a caller write an output that
    silently lost every ADR in that tier. Callers map the raise to exit 2.
    """
    found = _list_tier(Path(adrs_dir))
    if include_archive:
        found += _list_tier(Path(adrs_dir) / "archive")
    return [p for p in sorted(found, key=str) if is_adr_filename(p.name)]


def _list_tier(directory: Path) -> list[Path]:
    """Every non-hidden `*.md` entry of `directory`, matching `ADR_GLOB`.

    The tier is absent only when the operating system says so: the listing
    fails with ENOENT, or it fails with ENOTDIR and a `stat` of the tier then
    fails with ENOENT or ENOTDIR (an ancestor is not a directory). Every other
    failure to list it propagates, because a listing failure is not evidence
    that the tier holds nothing: a permission error, a parent that cannot be
    searched, or a regular file at the tier's path, whose `stat` succeeds.
    The last is read as a directory that cannot be listed, the environment
    lane, rather than as an absent tier (see `input_lanes`).
    """
    try:
        names = _os.listdir(directory)
    except FileNotFoundError:
        return []
    except NotADirectoryError:
        if not _input_lanes.directory_exists(directory):
            return []
        raise  # a directory by now: the listing's own failure stands
    # `glob.glob` skips hidden names unless the pattern names them; keep that.
    return [directory / n for n in names
            if not n.startswith(".") and _fnmatch.fnmatchcase(n, ADR_GLOB)]


def frontmatter_block(text: str) -> str | None:
    """The YAML block between the fences, or None when the fence does not parse."""
    m = FENCE_RE.match(text)
    return m.group(1) if m else None


def read_adr_inputs(paths, rel) -> tuple[dict[Path, str], list[dict]]:
    """Read every path once; return `(texts, findings)`.

    `texts` maps each readable path to its UTF-8 text. `findings` holds one
    `{"file", "error"}` document-lane entry per path that cannot be read for a
    cause attributable to it — a permission refusal, a listed file absent at
    open, a directory in its place, a symbolic-link loop, content that is not
    valid UTF-8 — and per readable path whose fence does not parse. `rel`
    renders the reported path, so a path inside the checkout is named
    relative to it.

    A read that fails for a cause in the process or host — descriptor or
    memory exhaustion, a device I/O error, any errno outside the closed list
    `input_lanes` holds — raises `input_lanes.EnvironmentLaneError` once every
    path has been tried. It carries the document-lane findings the run met,
    so the caller names them on stderr beside the failure.
    """
    texts: dict[Path, str] = {}
    findings: list[dict] = []
    failures: list[str] = []
    for path in paths:
        path = Path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, MemoryError) as exc:
            if _input_lanes.is_path_attributable(exc):
                findings.append({"file": rel(path), "error": _input_lanes.document_reason(exc)})
            else:
                failures.append(_input_lanes.environment_reason(rel(path), exc))
            continue
        texts[path] = text
        if frontmatter_block(text) is None:
            findings.append({"file": rel(path), "error": FENCE_ERROR})
    if failures:
        raise _input_lanes.EnvironmentLaneError(failures, findings)
    return texts, findings


def fence_validation_errors(paths, rel) -> list[dict]:
    """`{"file", "error"}` for every path in `paths` that is a document-lane finding.

    `rel` renders a path for reporting — callers pass `repo_relative(root)`, so
    a path inside the checkout is reported relative to it.

    A fence that does not parse is a finding. So is a file the process cannot
    read for a cause attributable to its path, such as a permission refusal or
    a byte sequence that is not UTF-8: the repair is at that path, so the
    document lane gives the right advice. A read that fails for a cause in the
    process or host raises `input_lanes.EnvironmentLaneError`, which the caller
    maps to the environment lane (exit 2).
    """
    return read_adr_inputs(paths, rel)[1]


def repo_relative(root):
    """A path reporter: renders relative to `root`, never absolute.

    Owned here rather than pasted into each generator, because how a refusal
    names a file is part of the reporting contract this module defines.
    """
    root = Path(root)

    def _rel(p) -> str:
        p = Path(p)
        return str(p.relative_to(root)) if p.is_relative_to(root) else str(p)

    return _rel


def validated_adr_texts(adrs_dir: Path, rel, *, include_archive: bool = True) -> dict[Path, str]:
    """Every ADR input's text, after refusing the whole run on any finding.

    The single entry point a loader calls: it lists BOTH tiers, reads each file
    once, validates all of them, and raises before the caller has read an
    output to diff against or opened one to write. A tier it cannot list raises
    `OSError`; a process-level read failure raises
    `input_lanes.EnvironmentLaneError`; both are the environment lane. Any
    document-lane finding raises `FenceValidationError` carrying every one.
    """
    texts, findings = read_adr_inputs(adr_paths(adrs_dir, include_archive=include_archive), rel)
    if findings:
        raise FenceValidationError(findings)
    return texts


def validated_adr_paths(adrs_dir: Path, rel, *, include_archive: bool = True) -> list[Path]:
    """`adr_paths`, after refusing the whole run on any finding (see `validated_adr_texts`)."""
    return sorted(validated_adr_texts(adrs_dir, rel, include_archive=include_archive), key=str)


def print_validation_errors(errors: list[dict], script: str, out, err) -> int:
    """Emit the exit-1 payload and a stderr summary. Returns 1.

    JSON on stdout on every lane, because `check-drift` and `audit-docs` parse
    each gate's stdout as JSON regardless of exit code.
    """
    import json

    print(json.dumps({"validation_errors": errors}, sort_keys=True), file=out)
    err.write(f"{script}: " + "; ".join(f"{e['file']}: {e['error']}" for e in errors) + "\n")
    return 1
