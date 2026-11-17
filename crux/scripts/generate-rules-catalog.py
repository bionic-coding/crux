#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml>=6.0,<7", "httpx>=0.27,<1"]
# ///
"""generate-rules-catalog.py — project this project's own rules into a catalog the plugin ships.

WHY THIS EXISTS. The plugin cites its own rules by slug on the surfaces it ships, and until this
catalog it shipped nothing that defined one. The release artifact carries no decision tree, so
every one of those citations was unresolvable for the reader it shipped to, while the shipped
contract said a citation must resolve. Per rule:citation-resolves-by-its-citing-surface, a
citation on a shipped surface resolves against this catalog; per
rule:shipped-catalog-is-derived-and-names-no-decision-record, this catalog is derived and carries
no decision-record identifier.

INPUT DOMAIN, and why it is the cited set rather than every rule. The catalog carries the DISTINCT
slugs cited on shipped surfaces, excluding test fixtures and the catalog's own output so the
projection cannot feed on itself. A citation naming a slug the catalog does not yet carry drifts
it until this runs; a citation naming a slug already carried drifts nothing, and removing a slug's
last citation drifts it again. That is what makes the drift gate a coverage gate for slugs.

NO DECISION-RECORD IDENTIFIER. `source_adr` is deliberately dropped. The catalog directory is not
one of the three prose surfaces the release-content scan governs, so carrying it would be legal —
it is omitted because a reader without this project cannot open that record, and the citation form
those surfaces use names a rule rather than a record.

PUBLICATION ELIGIBILITY, and why it lives here rather than in the citation lint. A slug reaching
this catalog is published to a reader who cannot open the record behind it -- the payload carries
no decision-record identifier by design. So the question "has the decision behind this rule been
accepted?" has to be answered at the moment of projection, which is here. It is a SECOND check
beside resolution, never a stricter first one: `lint-governs-references.py` still resolves every
citation on every surface exactly as before, and a citation on a reader-owned surface is never
asked this question at all. Per rule:shipped-citation-requires-an-accepted-decision the verdict
comes from `publication_eligibility`, and per rule:an-ineligible-citation-refuses-the-projection an
ineligible citation REFUSES this projection rather than being filtered out of it -- filtering would
leave the shipped surface citing a slug the catalog no longer carries, which is the unresolvable
state the catalog exists to end.

The refusal runs before the target is read, before its parent is created, and before anything is
written, so a refused run leaves an existing catalog byte-unchanged and creates no absent one. It
runs in BOTH modes, and the drift mode is the load-bearing one: a status change moves no byte of
this file, so a byte comparison alone can never see it.

Exit codes follow the repository convention: 0 clean, 1 drift OR a validation error (valid JSON on
stdout), 2 environment or input error (stderr, no stdout payload). An eligibility refusal is a
DOCUMENT-lane finding and so takes exit 1 with `validation_errors` on stdout: its remedy is to
accept the decision or drop the citation, never to re-run this script, and exit 2 would be read by
every CI classifier as "the gate did not execute".

INPUT LANES. The surface-absent lane needs a CONFIRMED-absent adrs directory: one whose presence
cannot be determined takes the environment lane, with or without --require-surface. Before the
authority proof or the build reads an input, the input census
(`summaries_projection.input_census`, driver `generate-rules-catalog`) examines the declared inputs
once. When the census meets anything, the citing-surface scan still runs, and one run reports both:
any environment failure gives exit 2 with stdout empty and stderr naming every census finding and
every blocking scan row; otherwise the census findings, as `{path, reason}` rows, and the blocking
scan rows share one `validation_errors` list at exit 1. The scan lists each directory itself: a
directory it cannot list is an environment failure, and a listed text-suffix entry it cannot read for
a cause attributable to its path is a blocking row. The read of the existing catalog follows the
output-read rule: an absent catalog reads as empty.
"""

from __future__ import annotations

import argparse
import bisect
import errno
import json
import os
import re
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import authoring_scope as _scope  # noqa: E402

import input_lanes  # noqa: E402
import publication_eligibility as pe  # noqa: E402
import summaries_projection as sp  # noqa: E402
import implementation_migration as migration  # noqa: E402

SCRIPT = "generate-rules-catalog"

# The repository's one bound-and-redact helper, reached through the projection
# exactly as the sibling citation lint reaches it. Every untrusted value this
# script emits -- a slug read out of an arbitrary file, a `status:` cell copied
# verbatim off ADR frontmatter with no enum validation, an OS error string --
# goes through it before reaching stdout. The payload's consumer is a model that
# renders these rows into a report, where an unbounded value carrying control
# characters or injected prose is no longer inside JSON quotes.
redact = sp.redact

# The citation token the contract's grammar defines: `rule:` followed by a lowercase
# letter, then lowercase letters, digits and hyphens. The token ends at the first
# character outside that set, which is what makes the `rule:<slug>` placeholder form
# a non-token.
CITATION_RE = re.compile(r"rule:([a-z][a-z0-9-]*)")

# Shipped surfaces scanned for citations. `crux/catalog` is excluded so the projection
# cannot feed on itself, and `crux/scripts/tests` because a fixture citation is test
# data rather than a claim a reader acts on.
SCAN_ROOTS = ("skills", "agents", "templates", "scripts")
EXCLUDED_PARTS = ("tests", "catalog", "__pycache__")
MAX_FILE_BYTES = 4 * 1024 * 1024  # the sibling lint's ceiling
# The sibling lint's file-count ceiling, adopted for the same reason: an unbounded
# walk over a large tree stalls every enforcement point rather than failing, and a
# gate that never returns is a gate that did not execute. Hitting it is a REFUSAL,
# not a truncation, because the surfaces past the ceiling were not examined.
MAX_SCANNED_FILES = 5000
TEXT_SUFFIXES = {".md", ".tmpl", ".py", ".yaml", ".yml", ".json", ".toml", ".sh", ".txt"}


def _guarded_citing_paths(directory: Path, plugin_root: Path, source_io):
    """Enumerate each directory through the operation transport before descent."""
    pending = [directory]
    while pending:
        directory = pending.pop()
        if source_io.kind(directory) != "directory":
            continue
        for path in source_io.glob(directory, "*"):
            if any(part in EXCLUDED_PARTS for part in path.relative_to(plugin_root).parts):
                continue
            entry = source_io.metadata(path)
            if entry is None:
                continue
            if stat.S_ISDIR(entry["st_mode"]):
                pending.append(path)
            else:
                # Like Path.rglob, do not recurse through directory symlinks.
                yield path


def _scan_failure(label: str, exc: BaseException) -> str:
    """One environment-lane stderr line naming `label`, with no absolute path.

    An OSError's own text carries the path it failed on, which is absolute; this
    names the errno and its description instead, beside the plugin-relative label.
    """
    if isinstance(exc, OSError) and exc.errno is not None:
        detail = f"{errno.errorcode.get(exc.errno, exc.errno)}: {exc.strerror or 'no detail'}"
    else:
        detail = redact(exc, quoted=False)
    return f"{label}: {type(exc).__name__}: {detail}"


def _listed_citing_paths(base: Path, plugin_root: Path,
                         failures: list[str]) -> list[tuple[Path, OSError | None]]:
    """The candidates beneath `base`, each with the lstat failure it met, or None.

    The walk lists each directory itself and descends real directories only, as
    `Path.rglob` does, pruning `EXCLUDED_PARTS`. A directory it cannot list is an
    environment failure naming its `crux/` label: an unlisted directory would
    otherwise hide every surface beneath it. A candidate is a listed entry whose
    suffix is in `TEXT_SUFFIXES` and whose lstat shows a regular file or a symbolic
    link. A FIFO, socket or device is skipped, as today. A listed entry whose lstat
    fails for a cause attributable to its path is a candidate carrying that failure
    when its suffix is a text suffix; any other lstat failure is an environment
    failure, because the walk cannot tell whether it hides a directory.
    """
    candidates: list[tuple[Path, OSError | None]] = []
    pending = [base]
    while pending:
        directory = pending.pop()
        try:
            names = input_lanes.list_directory(directory)
        except OSError as exc:
            failures.append(_scan_failure(f"crux/{directory.relative_to(plugin_root)}", exc))
            continue
        for name in names:
            if name in EXCLUDED_PARTS:
                continue
            path = directory / name
            try:
                mode = os.lstat(path).st_mode
            except OSError as exc:
                if path.suffix in TEXT_SUFFIXES and input_lanes.is_path_attributable(exc):
                    candidates.append((path, exc))
                else:
                    failures.append(_scan_failure(f"crux/{path.relative_to(plugin_root)}", exc))
                continue
            if stat.S_ISDIR(mode):
                pending.append(path)
            elif path.suffix in TEXT_SUFFIXES and (stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
                candidates.append((path, None))
    return sorted(candidates, key=lambda entry: entry[0])


def _read_listed_candidate(path: Path, lstat_error: OSError | None, plugin_real: Path,
                           label: str, refusals: list[dict], failures: list[str]) -> str | None:
    """The text of one listed candidate, or None after recording why it gave none.

    The order is the approved one. A symbolic link is resolved first, without
    requiring its target: a target outside the plugin root keeps the advisory row,
    dangling or not. The candidate is then stat-ed with the link followed, BEFORE any
    open: a regular file is read; a directory is a blocking EISDIR row; a FIFO, socket
    or device is skipped unopened, so a link to a FIFO can never block the scan. A
    failure attributable to the path is a blocking row whose reason is
    `input_lanes.document_reason`, which carries no absolute path; any other failure
    is an environment failure naming the label.
    """
    def classify(exc: BaseException) -> None:
        if input_lanes.is_path_attributable(exc):
            refusals.append({"path": label, "reason": input_lanes.document_reason(exc)})
        else:
            failures.append(_scan_failure(label, exc))

    if lstat_error is not None:
        classify(lstat_error)
        return None
    real = Path(os.path.realpath(path))
    try:
        real.relative_to(plugin_real)
    except ValueError:
        # Deliberately NOT a refusal that reds the gate: a symlink leaving the
        # plugin root does not ship, so it is not a shipped surface and has no
        # citations to hide. Recorded for visibility only.
        refusals.append({"path": label, "reason": "resolves outside the plugin "
                                                  "root; not a shipped surface",
                         "advisory": True})
        return None
    try:
        st = os.stat(path)
    except OSError as exc:
        classify(exc)
        return None
    if stat.S_ISDIR(st.st_mode):
        classify(IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR)))
        return None
    if not stat.S_ISREG(st.st_mode):
        return None
    if st.st_size > MAX_FILE_BYTES:
        refusals.append({
            "path": label,
            "reason": f"larger than MAX_FILE_BYTES ({MAX_FILE_BYTES}); "
                      "refused rather than read whole",
        })
        return None
    try:
        # O_NONBLOCK, and the kind checked again on the open descriptor: a path
        # replaced by a FIFO after the stat still cannot block the scan.
        fd = os.open(real, os.O_RDONLY | os.O_NONBLOCK)
        with open(fd, encoding="utf-8") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                failures.append(f"{label}: changed kind during the scan; not read")
                return None
            return handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        classify(exc)
    except MemoryError as exc:
        failures.append(_scan_failure(label, exc))
    return None


def cited_slug_paths(
        plugin_root: Path, *, _source_io=None) -> tuple[dict[str, list[str]], list[dict]]:
    """`(slug -> sorted `path:line` locations, refusals)` over the shipped surfaces.

    Raises `input_lanes.EnvironmentLaneError` when the scan met an environment-lane
    failure, such as a directory it could not list; the error's `findings` name every
    blocking refusal row the same scan met. `_cited_slug_scan` returns the failures
    instead, for a caller that reports them beside other findings.
    """
    found, refusals, failures = _cited_slug_scan(plugin_root, _source_io=_source_io)
    if failures:
        raise input_lanes.EnvironmentLaneError(failures, [
            {"file": row["path"], "error": row["reason"]}
            for row in refusals if not row.get("advisory")])
    return found, refusals


def _cited_slug_scan(
        plugin_root: Path, *, _source_io=None
) -> tuple[dict[str, list[str]], list[dict], list[str]]:
    """`(slug -> sorted `path:line` locations, refusals)` over the shipped surfaces.

    The CITING PATH is what makes a refusal actionable: a finding naming only the slug
    leaves the author grepping sixty skills for it. Per
    rule:an-ineligible-citation-refuses-the-projection the finding names where the
    citation sits, so the scan has to carry the location rather than discard it.

    A FILE THIS SCAN CANNOT READ IS A REFUSAL, NEVER A SKIP. This is the difference
    between a guard and a suggestion. A file that is not read contributes no citations,
    so it produces no finding — while the release still ships it, because the stage
    allowlists `crux/` wholesale. Dropping unreadable files silently therefore let a
    committed shipped file HIDE an ineligible citation from every enforcement point at
    once: one invalid UTF-8 byte, or padding past `MAX_FILE_BYTES`, or a suffix outside
    the allowlist, and the citation ships unexamined while the gate stays green. The
    sibling citation lint already had the right shape — it records refusal rows and
    makes a non-empty list part of its exit condition — and this now matches it.

    The corpus, the roots and the exclusions are unchanged: a richer return and a
    refusal list, not a wider scan. Two readers of "what is shipped" giving two answers
    is a defect this repository has already paid to fix once.

    A SCAN THAT CANNOT LIST IS AN ENVIRONMENT FAILURE. `Path.rglob` returns nothing for
    a directory it cannot list, with no error, so an unlistable directory used to hide
    every surface beneath it. Without `_source_io` the scan lists each directory itself
    (`_listed_citing_paths`) and returns, as its third item, one stderr line per
    environment-lane failure: an unlistable directory, or a read that failed for a cause
    outside the path-attributable list. A listed candidate whose read failed for a cause
    attributable to its path, including a dangling link inside the plugin root, is a
    blocking refusal row whose reason carries no absolute path. The seamed branch
    (`_source_io`) is unchanged and returns no failures.
    """
    found: dict[str, list[str]] = {}
    refusals: list[dict] = []
    failures: list[str] = []
    scanned = 0
    plugin_real = plugin_root.resolve() if _source_io is None else None
    for root in SCAN_ROOTS:
        base = plugin_root / root
        if _source_io is None:
            try:
                if not input_lanes.directory_exists(base):
                    continue
            except OSError as exc:
                failures.append(_scan_failure(f"crux/{root}", exc))
                continue
            entries = _listed_citing_paths(base, plugin_root, failures)
        else:
            if not sp._source_is_dir(base, _source_io):
                continue
            entries = [(path, None) for path in
                       sorted(_guarded_citing_paths(base, plugin_root, _source_io))]
        for path, lstat_error in entries:
            if _source_io is not None and not sp._source_is_file(path, _source_io):
                continue
            rel = path.relative_to(plugin_root)
            if any(part in EXCLUDED_PARTS for part in rel.parts):
                continue
            label = f"crux/{rel}"
            if path.suffix not in TEXT_SUFFIXES:
                # NOT a refusal: the extension allowlist is the scan's DEFINITION of a
                # text surface, and a binary asset legitimately carries no citation.
                # Recording every image as a refusal would bury the real ones. The
                # residual — a citation inside an unlisted text extension — is a
                # roster question about SCAN_ROOTS/TEXT_SUFFIXES, not a read failure.
                continue
            # The walk is bounded, matching the sibling lint's ceiling. Without one, a
            # tree with enough shipped files stalls every enforcement point rather than
            # failing, and a stalled gate is a gate that did not execute.
            if scanned >= MAX_SCANNED_FILES:
                refusals.append({
                    "path": label,
                    "reason": f"scope exceeds MAX_SCANNED_FILES ({MAX_SCANNED_FILES}); "
                              "the walk stopped and the remaining surfaces were not read",
                })
                break
            scanned += 1
            if _source_io is None:
                # Containment, kind and size, in the approved order; see
                # `_read_listed_candidate`.
                text = _read_listed_candidate(path, lstat_error, plugin_real, label,
                                              refusals, failures)
                if text is None:
                    continue
            else:
                # Containment and size refusals, matching the sibling citation lint
                # rather than diverging from it: a symlink out of the plugin root is not
                # a shipped surface, and an oversized file is refused rather than read
                # whole. Each is now RECORDED rather than skipped.
                try:
                    real = _source_io.resolve(path)
                except OSError as exc:
                    refusals.append({"path": label,
                                     "reason": f"cannot resolve: {redact(exc, quoted=False)}"})
                    continue
                plugin_real = sp._source_resolve(plugin_root, _source_io)
                try:
                    real.relative_to(plugin_real)
                except ValueError:
                    refusals.append({"path": label, "reason": "resolves outside the plugin "
                                                              "root; not a shipped surface",
                                     "advisory": True})
                    continue
                try:
                    size = _source_io.metadata(real)["st_size"]
                    if size > MAX_FILE_BYTES:
                        refusals.append({
                            "path": label,
                            "reason": f"larger than MAX_FILE_BYTES ({MAX_FILE_BYTES}); "
                                      "refused rather than read whole",
                        })
                        continue
                    text = _source_io.read_text(real, max_bytes=MAX_FILE_BYTES)
                except (OSError, UnicodeDecodeError) as exc:
                    refusals.append({
                        "path": label,
                        "reason": f"unreadable as UTF-8 text: {type(exc).__name__}: "
                                  f"{redact(exc, quoted=False)}",
                    })
                    continue
            # Newline offsets computed ONCE per file, then bisected. The obvious
            # `text.count("\n", 0, m.start())` per match rescans the buffer from zero
            # every time, which is quadratic: measured at 1.37s / 5.43s / 21.96s for
            # 32k / 64k / 128k citations in one file — a clean 4x per 2x. At the 4 MiB
            # ceiling that is minutes for a single committed file, enough to exhaust the
            # workflow timeout and to wedge the release gates, which have none.
            starts = [0]
            for i, ch in enumerate(text):
                if ch == "\n":
                    starts.append(i + 1)
            for m in CITATION_RE.finditer(text):
                line = bisect.bisect_right(starts, m.start())
                found.setdefault(m.group(1), []).append(f"{label}:{line}")
        else:
            continue
        break
    return ({slug: sorted(set(locs)) for slug, locs in found.items()}, refusals, failures)


def _load_catalog_inputs(repo_root: Path, plugin_root: Path, *, _prepared=None) -> tuple[dict, dict]:
    import implementation_migration as migration
    target = plugin_root / "catalog/rules.json"
    if not target.parent.resolve().is_relative_to(repo_root.resolve()) or target.is_symlink():
        raise OSError("catalog destination is not contained under the repository or is symlinked")
    docs = sp.resolve_tree(repo_root)
    view = migration.authority_view(repo_root) if _prepared is None else _prepared['view']
    declared = sp.declared_input_domain(docs / "adrs/summaries")
    sp._projection_require(not isinstance(declared, list) or "implementation-migration" not in declared
        or view["state"] in ("published","prepared"), "catalog declared migration input unavailable")
    manifest = sp.read_manifest(repo_root)
    observations = sp.observations_source(repo_root, manifest) or docs / "observations"
    records = sp.collect_records(docs / "adrs", governs_from=None, observations=observations)
    reviews = sp.read_reviews(docs / "adrs")
    aliases = sp.collect_observation_alias_rows(observations, records)
    cited, refusals = cited_slug_paths(plugin_root)
    migration._unchanged_inputs(repo_root, view["dependency_fingerprints"])
    return dict(root=repo_root, target=target, records=records,
        reviews=reviews, aliases=aliases, cited=cited, refusals=refusals,
        persisted_edges=sp.persisted_retirement_edges(docs / "adrs")), view


def _catalog_payload(loaded: dict, facts: dict, *, _prepared=False) -> dict:
    """Pure publication policy, shared by ordinary reads and private candidate plans."""
    for value in (loaded["records"], loaded["reviews"], loaded["aliases"], loaded["cited"], loaded["refusals"], facts):
        sp._plain_summary_value(value)
    overlay = sp._summary_authority_records(loaded["records"], facts,
        sp.removed_handles(loaded["reviews"]), loaded["aliases"], _prepared=_prepared,
        persisted_edges=loaded.get("persisted_edges"))
    records = sp.live_records(overlay["records"])
    slugs = overlay["slugs"]
    by_handle = {r["handle"]: r for r in records}
    by_slug = {slug: by_handle[handle] for slug, handle in slugs.items()}
    cited = loaded["cited"]
    sp._projection_require(isinstance(cited, dict) and all(re.fullmatch(r"[a-z][a-z0-9-]*", slug)
        and isinstance(paths, list) and all(isinstance(p, str) for p in paths)
        for slug, paths in cited.items()), "catalog citing paths invalid")
    wanted = set(cited)
    historical = wanted.intersection(overlay["historical_slugs"])
    # A known proposal remains an ineligible source, not an unknown slug.
    # Keep the publication refusal and its citing-path diagnostics while giving
    # a live accepted rule precedence over any proposed reuse of its slug.
    proposals = {sp.slug_of(r["handle"]): r for r in sp.proposed_records(overlay["records"])
                 if sp.slug_of(r["handle"]) not in by_slug}
    known = {**proposals, **by_slug}
    ineligible = pe.findings({s: cited[s] for s in wanted.intersection(known)}, known)
    resolution = sp.resolve_replacements(
        [h for slug in historical for h in overlay["historical_slugs"][slug]["replacements"]],
        overlay["records"], persisted_edges=loaded.get("persisted_edges"))
    for slug in sorted(historical):
        row = overlay["historical_slugs"][slug]
        # Suggest the live rules that displace a recorded replacement, never a retired one.
        suggested = sorted({"rule:" + sp.slug_of(h)
                            for h in sp.resolved_replacement_handles(row["replacements"], resolution)})
        for path in sorted(set(cited[slug]))[:pe.MAX_LOCATIONS_PER_FINDING]:
            ineligible.append(dict(path=path, citation="rule:" + slug, slug=slug,
                reason="historical implementation citation; replace with " + ", ".join(suggested)))
    rules = {}
    for slug in sorted(wanted.intersection(by_slug)):
        row = by_slug[slug]
        sp._projection_require(isinstance(row.get("rule"), str) and isinstance(row.get("domain"), str),
                               "catalog rule or domain is not text")
        rules[slug] = dict(rule=row.get("effective_rule", row["rule"]), domain=row["domain"])
    return dict(schema="1", rules=rules, unresolved=sorted(wanted - set(known) - historical),
                ineligible=ineligible, refusals=loaded["refusals"])


class _CatalogOutputPlan(tuple):
    """Immutable compiled bytes; schema one has no deferred provenance fields."""
    __slots__ = ()


def _plan_rules_catalog_outputs(loaded: dict, migration_facts: dict,
                               pending_publication: dict | None) -> _CatalogOutputPlan:
    # `persisted_edges` is route one of the retirement handoff; an input without it
    # takes route two, the records' own field.
    sp._projection_require(set(loaded) - {"persisted_edges"} ==
                           {"root", "target", "records", "reviews", "aliases", "cited", "refusals"},
                           "catalog loaded input shape invalid")
    sp._projection_require(loaded.get("persisted_edges") is None or
                           sp._persisted_edges_shape(loaded["persisted_edges"]),
                           "catalog persisted retirement edges invalid")
    root, target = loaded["root"], loaded["target"]
    sp._projection_require(isinstance(root, Path) and root.is_absolute() and
        isinstance(target, Path) and target == root / "crux/catalog/rules.json", "catalog destination invalid")
    sp._plain_summary_value(str(target))
    if pending_publication is not None:
        sp._summary_pending_publication(pending_publication)
    payload = _catalog_payload(loaded, migration_facts, _prepared=pending_publication is not None and
        pending_publication['close_identity'].get('format')=='crux.adr-migration-publication.v1')
    sp._projection_require(not payload["unresolved"] and not payload["ineligible"] and
        not any(not row.get("advisory") for row in payload["refusals"]), "catalog publication refused")
    return _CatalogOutputPlan(((target, render(payload).encode("utf-8")),))


def _materialize_rules_catalog_outputs(plan: _CatalogOutputPlan, committed_publication_ref=None) -> dict[Path, bytes]:
    """Return compiled bytes. Actual provenance belongs to the publication boundary."""
    return dict(plan)


def build_catalog(repo_root: Path, plugin_root: Path) -> dict:
    """The catalog payload, plus the two diagnostic lists `main` consumes and strips.

    Returns `{"schema", "rules", "unresolved", "ineligible", "refusals"}`. Only the
    first three reach `render`; `main` refuses on the last two and serializes neither. The
    payload shape the plugin ships is therefore UNCHANGED -- this guard needs no change
    to the distributed catalog schema, and does not make one.

    `by_slug` holds the WHOLE record rather than the two fields the catalog emits,
    because eligibility is decided from `source_kind` and `source_status`, which the
    two-field projection discarded. The two emitted fields are projected at the end
    instead, so the bytes are identical to before.
    """
    loaded, view = _load_catalog_inputs(repo_root, plugin_root)
    payload = _catalog_payload(loaded, view)
    if not payload["unresolved"] and not payload["ineligible"] and not any(
            not row.get("advisory") for row in payload["refusals"]):
        _plan_rules_catalog_outputs(loaded, view, None)
    return payload


def _require_surface_refusal(why: str) -> int:
    """The refusal an ENFORCEMENT POINT gets where a consumer gets the N/A lane.

    WHY A CALLER DECLARES THIS RATHER THAN THE SCRIPT INFERRING IT. Surface-absent
    exits 0 so a consuming project, which owns no decision tree, files the row N/A
    instead of failing — correct, and the whole reason the lane exists. But the same
    exit 0 reads as GREEN to a shell that tests only the return code, and all three of
    this guard's enforcement points are such shells. The tree can go absent from a
    well-formed config naming a directory that is not there, from a rename, or from a
    move; the gate then fires, prints OK, and has examined nothing. Worse, the config
    file is inside the CI trigger's own paths list, so the edit that disables the guard
    is the edit that fires the gate that then passes it.

    A script cannot tell the two callers apart -- both run the same command in a
    directory -- so the caller says which it is. Per
    rule:one-guard-called-from-every-enforcement-point, no enforcement point is
    satisfied by a check that reports a pass without executing; "cannot verify" is not
    "nothing to verify".

    Exit 2 with empty stdout: this is the environment lane, and every consumer of this
    gate already refuses on it rather than reading it as a document finding.
    """
    print(f"generate-rules-catalog: --require-surface was passed and the surface is "
          f"absent: {why}. Refusing to report a pass from a check that inspected "
          f"nothing.", file=sys.stderr)
    return 2


# The remedy line, in one place because it is wrong in three different ways if it is
# written once per call site. "Accept the decision" is the remedy for a PROPOSED host
# only: the state machine offers no transition back from Deprecated or Superseded, so
# there the remedy is to migrate the citation to whatever displaced the rule, and an
# observation-backed row needs an owner decision that nobody has made yet. The per-row
# `reason` was always accurate; the summary beside it was not.
REMEDY = ("Accept a Proposed decision; for a Deprecated or Superseded one, migrate the "
          "citation to the rule that displaced it or remove it; an observation-backed "
          "rule needs an owner decision before it can ship.")

SHIPPED_KEYS = ("schema", "rules", "unresolved")



def _portable_rule_text(text: str) -> str:
    """Publish rule references by slug while preserving the source decision text."""
    text = re.sub(r"\b(?:[A-Z][A-Z0-9]{1,9}-)?(?:ADR|OBS)-\d{4}/([a-z][a-z0-9-]*)",
                  r"rule:\1", text)
    sp._projection_require(not re.search(r"\b(?:ADR|OBS)-\d{4}\b", text),
        "catalog rule text names a private decision record without a rule handle")
    return text


def render(catalog: dict) -> str:
    """The bytes the plugin ships. `build_catalog` returns two diagnostic keys beside
    the payload; they are projected out here so the distributed schema is unchanged and
    a diagnostic can never leak into the artifact by someone adding a key upstream."""
    shipped = {k: catalog[k] for k in SHIPPED_KEYS}
    shipped["rules"] = {slug: {**row, "rule": _portable_rule_text(row["rule"])}
                        for slug, row in catalog["rules"].items()}
    return json.dumps(shipped, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _print_rows(rows: list[dict], repo_root: Path, target: Path) -> int:
    """Report document-lane rows in the catalog's row shape and return 1."""
    print(json.dumps({"validation_errors": rows, "path": str(target.relative_to(repo_root)),
                      "written": None}, sort_keys=True))
    print(f"generate-rules-catalog: {len(rows)} input(s) could not be read for a cause "
          "attributable to the path; nothing was written. Each row's `reason` names the "
          "repair.", file=sys.stderr)
    return 1


def _census_and_scan_exit(census, repo_root: Path, plugin_root: Path, target: Path) -> int:
    """Report what the census met beside what the citing-surface scan meets, in one run.

    Any environment failure from either gives exit 2 with stdout empty, and stderr names
    every census finding and every blocking scan row. Otherwise the census findings,
    rendered as `{path, reason}` with the path relative to the repository, and the
    blocking scan rows share one `validation_errors` list at exit 1.
    """
    _, refusals, failures = _cited_slug_scan(plugin_root)
    blocking = [row for row in refusals if not row.get("advisory")]
    if census.failures or failures:
        return input_lanes.emit_environment_failure(input_lanes.EnvironmentLaneError(
            census.failures + failures,
            census.findings + [{"file": row["path"], "error": row["reason"]} for row in blocking]),
            SCRIPT, sys.stderr)
    rows = [{"path": f["file"], "reason": f["error"]} for f in census.findings] + blocking
    return _print_rows(rows, repo_root, target)


def _read_current_catalog(target: Path) -> str | None:
    """The existing catalog's text, under the output-read rule.

    A confirmed-absent catalog reads as None. A failure attributable to the path is an
    `InputLaneRefusal` naming the catalog with `input_lanes.output_reason`; any other
    failure, and a FIFO, socket or device at the path, which is never opened, is an
    environment-lane failure naming it.
    """
    label = "crux/catalog/rules.json"
    try:
        st = input_lanes.path_state(target)
        if st is None:
            return None
        if stat.S_ISDIR(st.st_mode):
            raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), str(target))
        if not stat.S_ISREG(st.st_mode):
            raise OSError(f"is a {input_lanes.file_kind(st.st_mode)}, not a regular file; "
                          "not opened")
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        if input_lanes.is_path_attributable(exc):
            raise sp.InputLaneRefusal([{"file": label,
                                        "error": input_lanes.output_reason(exc)}]) from None
        raise input_lanes.EnvironmentLaneError([_scan_failure(label, exc)]) from None
    except MemoryError as exc:
        raise input_lanes.EnvironmentLaneError([_scan_failure(label, exc)]) from None


def _refusal_exit(repo_root: Path, target: Path, exc: Exception) -> int:
    """Report an exception from the read phase in its lane and return the exit code.

    An OSError naming a path beneath the documentation tree, raised after a clean
    census, goes through the census's classifier first, so a late path-attributable
    failure is a row naming the input rather than an unclassified crash. A dangling
    link at an optional file takes the environment lane. Every other exception keeps
    its present report.
    """
    if isinstance(exc, OSError):
        exc = sp.late_input_failure(repo_root, exc) or exc
    if isinstance(exc, input_lanes.DanglingOptionalLinkError):
        exc = input_lanes.EnvironmentLaneError([str(exc)])
    if isinstance(exc, input_lanes.EnvironmentLaneError):
        return input_lanes.emit_environment_failure(exc, SCRIPT, sys.stderr)
    if isinstance(exc, sp.InputLaneRefusal):
        return _print_rows([{"path": f["file"], "reason": f["error"]} for f in exc.problems],
                           repo_root, target)
    if isinstance(exc, (migration.Refused, sp.GovernsValidationError)):
        problems = (exc.problems if isinstance(exc, sp.GovernsValidationError)
                    else [{"problem": redact(exc, quoted=False)}])
        print(json.dumps({"validation_errors": problems, "written": None}, sort_keys=True))
        return 1
    print(f"generate-rules-catalog: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--require-surface", action="store_true",
        help="refuse instead of reporting surface-absent. An ENFORCEMENT POINT passes "
             "this; a consuming project's drift sweep does not.")
    args = ap.parse_args(argv)

    repo_root = _scope.resolve_repo_root(args.repo_root)
    plugin_root = repo_root / "crux"
    target = plugin_root / "catalog" / "rules.json"

    # SURFACE-ABSENT LANE, on the `extract-code-docs` model and for the same reason the
    # parity check skips a clause whose twin is absent. This regenerator projects THIS
    # project's own governs blocks, which exist only in the authoring checkout; an
    # installed project has the plugin in its plugin cache, not at `<repo>/crux/`.
    # Without this lane a downstream `check-drift` run reported drift against a file it
    # had no business owning, and the remedy that row names WROTE a `crux/` tree into the
    # reader's repository — which the decision explicitly disclaims.
    if not _scope.is_authoring_checkout(repo_root, __file__):
        if args.require_surface:
            return _require_surface_refusal(
                "the plugin's authoring checkout is not here, so there is no source to "
                "project from")
        return _scope.print_surface_absent(written=None)

    # SECOND TRIGGER of the same lane. The catalog is projected from THIS tree's own
    # `governs` blocks, and the release artifact ships `crux/` without the tree. Run
    # from the staged artifact or a public clone, the first probe passes -- both carry
    # `crux/scripts/` -- and then every cited slug resolved to nothing, so the gate
    # exited 2 with empty stdout and `check-drift` filed a CRASH against an artifact
    # that owns no source to project from. No tree, no projection, nothing to drift.
    # A MALFORMED CONFIG IS NOT AN ABSENT SURFACE. This used to be one blanket
    # `except Exception` that turned every failure of `resolve_tree` into the
    # surface-absent lane -- exit 0, `surface_absent: true`, a green. That is right for
    # a tree that genuinely is not here and wrong for a tree whose config cannot be
    # read: the tree contract's §14.1 requires a malformed `.bionic.yml` to fail loud
    # and NEVER to fall back. It mattered more here than for a pure drift gate, because
    # this same command is the CI step, the preflight row and the publication gate, and
    # `.bionic.yml` is inside the workflow's own paths list -- so one edit to it made
    # the workflow fire, report OK, and leave publication eligibility unverified
    # everywhere at once. "Cannot verify" is not "nothing to verify".
    try:
        docs = sp.resolve_tree(repo_root)
    except Exception as exc:  # noqa: BLE001 — the environment/input lane, loudly
        print(f"generate-rules-catalog: cannot resolve the documentation tree: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    # THE TREE PROBE DECIDES BY THE OPERATING SYSTEM'S ANSWER. `is_dir()` answered False
    # for an adrs directory the process could not stat, which read an unsearchable tree
    # as an absent one and reported surface-absent: a green from a gate that examined
    # nothing. Only a confirmed absence (ENOENT or ENOTDIR) takes the surface-absent
    # lane; an adrs path whose presence cannot be determined, or a regular file at it,
    # takes the environment lane, with or without --require-surface.
    adrs_present = False
    if docs is not None:
        try:
            adrs_present = input_lanes.directory_exists(docs / "adrs")
        except OSError as exc:
            label = os.path.relpath(docs / "adrs", repo_root)
            return input_lanes.emit_environment_failure(input_lanes.EnvironmentLaneError(
                [_scan_failure(label, exc) + "; the documentation tree is present but its "
                 "adrs directory cannot be examined, so this is not an absent surface"]),
                SCRIPT, sys.stderr)
    if not adrs_present:
        if args.require_surface:
            return _require_surface_refusal(
                "no documentation tree is present here, so no source record's status "
                "could be read")
        return _scope.print_surface_absent(
            written=None,
            reason="the rules catalog is projected from this tree's own governs blocks, "
                   "and no documentation tree is present here")

    # The input census runs first: it examines the declared inputs once, before the
    # authority proof or the build reads one. When it meets anything, the scan still
    # runs, so one run names every census finding and every blocking scan row.
    try:
        census = sp.input_census(repo_root, driver=SCRIPT)
        if census.findings or census.failures:
            return _census_and_scan_exit(census, repo_root, plugin_root, target)
        catalog = build_catalog(repo_root, plugin_root)
        payload = render(catalog)
    except Exception as exc:  # noqa: BLE001 — each lane is decided in _refusal_exit
        return _refusal_exit(repo_root, target, exc)

    if catalog["unresolved"]:
        print(
            "generate-rules-catalog: shipped surfaces cite slugs no live rule defines: "
            f"{catalog['unresolved']}",
            file=sys.stderr,
        )
        return 2

    # UNREAD-SURFACE REFUSAL, and it comes FIRST because it bounds what the eligibility
    # check below could possibly have seen. A shipped file this scan could not read
    # contributes no citations, so it yields no eligibility finding while the release
    # ships it regardless — which made an unreadable file a way to hide an ineligible
    # citation from every enforcement point at once. A guard that cannot read its own
    # corpus has not measured it, and reporting a pass from that is the false green
    # rule:one-guard-called-from-every-enforcement-point forbids.
    #
    # An advisory row (a symlink leaving the plugin root) is reported and does NOT red
    # the gate: it names a path that does not ship, so it hides nothing.
    blocking = [r for r in catalog["refusals"] if not r.get("advisory")]
    if blocking:
        print(json.dumps({
            "validation_errors": blocking,
            "path": str(target.relative_to(repo_root)),
            "written": None,
        }, sort_keys=True))
        print(
            f"generate-rules-catalog: {len(blocking)} shipped surface(s) could not be "
            "read, so their citations were not examined; nothing was written. Make each "
            "file readable UTF-8 text within the size ceiling, or move it off the "
            "shipped surfaces.",
            file=sys.stderr,
        )
        return 1

    # PUBLICATION-ELIGIBILITY REFUSAL (rule:an-ineligible-citation-refuses-the-projection).
    #
    # POSITION IS THE CONTRACT. This sits before `target.read_text`, before
    # `target.parent.mkdir` and before `target.write_text`, so a refused run leaves an
    # existing catalog byte-unchanged and creates no absent one. It also sits OUTSIDE the
    # `--dry-run` branch below, which is the load-bearing half: a source record's status
    # moves no byte of this file, so a refusal reachable only through the write lane would
    # let the drift gate report clean forever on a catalog holding an unaccepted rule.
    #
    # Every ineligible citation is reported, never the first alone, so the remedy is one
    # round trip. The DOCUMENT lane (exit 1, JSON on stdout) is deliberate: the remedy is
    # to accept the decision or drop the citation, and exit 2 would be announced by every
    # CI classifier as an environment failure the reader cannot act on.
    if catalog["ineligible"]:
        print(json.dumps({
            "validation_errors": catalog["ineligible"],
            "path": str(target.relative_to(repo_root)),
            "written": None,
        }, sort_keys=True))
        print(
            f"generate-rules-catalog: {len(catalog['ineligible'])} shipped citation(s) "
            "name a rule whose source record is not eligible for publication; nothing "
            "was written. The remedy depends on WHY, and each row's `reason` says which: "
            + REMEDY,
            file=sys.stderr,
        )
        return 1

    try:
        current = _read_current_catalog(target)
    except Exception as exc:  # noqa: BLE001 — each lane is decided in _refusal_exit
        return _refusal_exit(repo_root, target, exc)

    if args.dry_run:
        drift = current != payload
        print(json.dumps({"drift": drift, "path": str(target.relative_to(repo_root)),
                          "rules": len(catalog["rules"])}, sort_keys=True))
        return 1 if drift else 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")
    print(json.dumps({"written": str(target.relative_to(repo_root)),
                      "rules": len(catalog["rules"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
