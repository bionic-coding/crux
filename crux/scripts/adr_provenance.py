# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml>=6.0,<7"]
# ///
"""adr_provenance.py — the ADR provenance record: parse, validate, render, and read standing.

WHY THIS EXISTS. Text added to an ADR during the run that accepts it is guidance, and binding
text is the ADR as it stood at that run's `base_commit` plus what the owner has promoted.
Accepting an ADR inside a run writes one record per ADR under
`<docs_dir>/adrs/provenance/ADR-NNNN.yaml`, and the projections read each rule's standing and
binding version from that record, never from git history. This module is the one parser of
that record, so the CLI that writes it (`adr-provenance.py`), the summaries projection and the
doctrine projection cannot disagree about what a record says.

WHAT IS HERE, AND WHAT IS NOT. This module reads no git, reads no directory and computes no
diff: the diff runs once, at acceptance, in `adr-provenance.py`, and its result is the record.
`summaries_projection.provenance_entries` is the one reader of `adrs/provenance/`. Here are the
record grammar (`parse_record`, `render_record`), the effective standing after promotions
(`effective_rules`), the open promotion request a record still carries (`open_request`), the
deletions that still bind (`removed_entries`), the join of records onto live governs rows
(`join_standing`), and the digest the projections hash into their input domain
(`records_sha256`). The record shape is also published as
`crux/schemas/adr-provenance.schema.json`; the parser enforces the cross-field rules a JSON
Schema cannot state.

THE RECORD. Each rule carries `entry`, its governs entry as accepted, and `base`, its governs
entry at `base_commit`, or null when the rule did not stand there; both omit `handle`. A
promotion appends to `promotions` and never changes `base`.

STANDING. A rule absent from the ADR at `base_commit` is guidance and has no binding version. A
rule present there is binding at its `base` entry. When any governs field but `provenance`
differs between `entry` and `base`, that edit is in-run text, which is guidance. A rule present
at `base_commit` that the run deleted is listed in `removed_in_run`; it stays binding at its
`base` entry until the owner promotes the deletion. A promotion, recorded from the owner's own
instruction (rule:owner-promotes-guidance), makes a rule binding at its `entry`, or makes a
deletion take effect. Standing is not liveness: a guidance rule stays live and resolves wherever
a binding rule resolves (rule:guidance-rules-keep-resolving), so nothing here removes a rule.

Every refusal is a `ProvenanceError` carrying problem rows in the summaries projection's
`{source_adr, handle, problem}` shape, so a projection can surface them as validation errors.
"""

from __future__ import annotations

import datetime
import hashlib
import re

SCHEMA = "1"
DIRNAME = "provenance"
STANDING_BINDING = "binding"
STANDING_GUIDANCE = "guidance"
STANDINGS = (STANDING_BINDING, STANDING_GUIDANCE)

#: The governs fields a recorded entry may carry, in the order a record renders them: the
#: closed governs sub-field set minus `handle`, which keys the rule instead.
ENTRY_FIELDS = ("domain", "rule", "scope", "anchor", "provenance", "retires")
#: The fields whose in-run change is in-run text. `provenance` says how the rule text was
#: produced, not what the rule says, so a change to it alone is no in-run edit.
COMPARED_FIELDS = tuple(f for f in ENTRY_FIELDS if f != "provenance")

#: `in_run_edit` tokens beside the compared field names: a rule added in-run, and a rule the
#: run deleted. The second is never the bare word `removed`, which the rule table already uses
#: for a tombstoned handle.
ADDED = "added"
DELETED = "deleted-in-run"

RECORD_NAME_RE = re.compile(r"^(ADR-[0-9]{4})\.yaml\Z")
_ADR_RE = re.compile(r"^ADR-[0-9]{4}\Z")
_HANDLE_RE = re.compile(r"^(ADR-[0-9]{4})/[a-z][a-z0-9-]*\Z")
_BOOK_RE = re.compile(r"^(?:[A-Z][A-Z0-9]{1,9}-)?PB-[0-9]{4}\Z")
_RUN_RE = re.compile(r"^RUN-[0-9]{3,}\Z")
_COMMIT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}\Z")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")

_TOP_KEYS = ("schema", "adr", "run", "base_commit", "base_path", "base_sha256", "rules",
             "removed_in_run", "promotions")
_RUN_KEYS = ("book_id", "run_id", "snapshot")
_RULE_KEYS = ("handle", "standing", "entry", "base")
_REMOVED_KEYS = ("handle", "base")
_PROMOTION_KEYS = ("date", "instruction", "handles", "body")

#: A record is a short authored document; anything larger is refused before parsing.
MAX_RECORD_BYTES = 1_000_000


class ProvenanceError(ValueError):
    """A record, a record set, or a join that refuses. `problems` holds
    `{source_adr, handle, problem}` rows, the summaries projection's validation shape."""

    def __init__(self, problems: list[dict]):
        self.problems = problems
        super().__init__("; ".join(p["problem"] for p in problems))


def _problem(source: str | None, handle: str | None, problem: str) -> dict:
    return {"source_adr": source, "handle": handle, "problem": problem}


def _relative_path(value) -> bool:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        return False
    parts = value.split("/")
    return all(part not in ("", ".", "..") for part in parts)


def _text(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _strings(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _date(value):
    """A YAML date or a YYYY-MM-DD string, as the string; anything else None."""
    if isinstance(value, datetime.datetime):
        return None
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, str) and _DATE_RE.match(value):
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            return None
        return value
    return None


# ── governs entries ─────────────────────────────────────────────────────────

def entry_problems(value, source: str | None, handle: str | None, what: str) -> list[dict]:
    """Why `value` is not a recordable governs entry (empty when it is): a mapping over
    `ENTRY_FIELDS` with the rule's non-empty text, `anchor` a string or a list of strings,
    `retires` a list of strings, and every other field a string."""
    if not isinstance(value, dict):
        return [_problem(source, handle, f"{what} must be a mapping of governs fields")]
    problems = []
    unknown = sorted(str(k) for k in set(value) - set(ENTRY_FIELDS))
    if unknown:
        problems.append(_problem(source, handle, f"{what} carries fields outside {list(ENTRY_FIELDS)}: {unknown}"))
    if not _text(value.get("rule")):
        problems.append(_problem(source, handle, f"{what} must carry the rule's non-empty text"))
    for key in ENTRY_FIELDS:
        if key not in value or key == "rule":
            continue
        item = value[key]
        ok = (isinstance(item, str) or _strings(item)) if key == "anchor" else \
            _strings(item) if key == "retires" else isinstance(item, str)
        if not ok:
            problems.append(_problem(source, handle, f"{what}: `{key}` has the wrong type"))
    return problems


def normal_entry(value: dict) -> dict:
    """A recordable entry in `ENTRY_FIELDS` order, lists copied."""
    return {k: (list(value[k]) if isinstance(value[k], list) else value[k])
            for k in ENTRY_FIELDS if k in value}


def comparable(entry: dict) -> dict:
    """The six governs fields as `summaries_projection._record_from_entry` normalizes them, so a
    recorded entry and a live rule row compare field by field."""
    retires = entry.get("retires")
    return {"domain": str(entry.get("domain", "")), "rule": str(entry.get("rule", "")),
            "scope": str(entry.get("scope", "")), "anchor": entry.get("anchor"),
            "provenance": str(entry.get("provenance", "")),
            "retires": [str(h) for h in retires] if isinstance(retires, list) else []}


def edited_fields(entry: dict, base: dict) -> list[str]:
    """The compared fields whose value differs between an accepted entry and its base."""
    now, then = comparable(entry), comparable(base)
    return [f for f in COMPARED_FIELDS if now[f] != then[f]]


def promotable(rule: dict) -> bool:
    """True when a recorded rule carries in-run text: guidance, or a binding rule edited in-run."""
    return rule["standing"] == STANDING_GUIDANCE or bool(edited_fields(rule["entry"], rule["base"]))


# ── the record grammar ──────────────────────────────────────────────────────

def yaml_problem(exc: Exception) -> str:
    """A YAML parse failure by its type and line only: PyYAML's own message quotes the text
    around the failure, and a record or snapshot is never echoed."""
    mark = getattr(exc, "problem_mark", None)
    where = f" at line {mark.line + 1}" if mark is not None else ""
    return f"not valid YAML ({type(exc).__name__}{where})"


def _load_yaml(text: str, source: str):
    import yaml
    from _yaml_min import CatalogYamlError, _refuse_duplicate_keys_bounded
    try:
        _refuse_duplicate_keys_bounded(text, yaml)
    except CatalogYamlError as exc:
        if isinstance(exc.__cause__, yaml.YAMLError):
            raise ProvenanceError([_problem(source, None, f"record is {yaml_problem(exc.__cause__)}")]) from None
        raise ProvenanceError([_problem(source, None, str(exc))]) from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ProvenanceError([_problem(source, None, f"record is {yaml_problem(exc)}")]) from None


def parse_record(text: str, *, name: str | None = None) -> dict:
    """Parse and validate one record; return its normalized dict (dates as strings).

    `name` is the record's file name; when given it must be `<adr>.yaml`. Every problem the
    record carries is collected and raised together as one `ProvenanceError`."""
    if len(text.encode("utf-8")) > MAX_RECORD_BYTES:
        raise ProvenanceError([_problem(name, None, f"record exceeds {MAX_RECORD_BYTES} bytes")])
    doc = _load_yaml(text, name or "provenance record")
    source = name or "provenance record"
    if not isinstance(doc, dict):
        raise ProvenanceError([_problem(source, None, "record is not a mapping")])
    problems: list[dict] = []
    keys = set(doc)
    if keys != set(_TOP_KEYS):
        raise ProvenanceError([_problem(source, None, "record keys must be exactly "
            f"{sorted(_TOP_KEYS)}; missing {sorted(set(_TOP_KEYS) - keys)}, "
            f"unknown {sorted(str(k) for k in keys - set(_TOP_KEYS))}")])
    adr = doc["adr"]
    if not (isinstance(adr, str) and _ADR_RE.match(adr)):
        raise ProvenanceError([_problem(source, None, f"adr must be ADR-NNNN, got {adr!r}")])
    source = adr
    if name is not None and name != f"{adr}.yaml":
        problems.append(_problem(adr, None, f"record file {name!r} must be named {adr}.yaml"))
    if doc["schema"] != SCHEMA:
        problems.append(_problem(adr, None, f"schema must be the string {SCHEMA!r}, got {doc['schema']!r}"))
    run = doc["run"]
    if not (isinstance(run, dict) and set(run) == set(_RUN_KEYS)):
        problems.append(_problem(adr, None, f"run must be a mapping with exactly {list(_RUN_KEYS)}"))
    else:
        if not (isinstance(run["book_id"], str) and _BOOK_RE.match(run["book_id"])):
            problems.append(_problem(adr, None, f"run.book_id is not a book id: {run['book_id']!r}"))
        if not (isinstance(run["run_id"], str) and _RUN_RE.match(run["run_id"])):
            problems.append(_problem(adr, None, f"run.run_id is not a run id: {run['run_id']!r}"))
        if not _relative_path(run["snapshot"]):
            problems.append(_problem(adr, None, "run.snapshot must be a repo-relative path"))
    if not (isinstance(doc["base_commit"], str) and _COMMIT_RE.match(doc["base_commit"])):
        problems.append(_problem(adr, None, "base_commit must be a full lowercase commit id"))
    base_path, base_sha = doc["base_path"], doc["base_sha256"]
    if base_path is None:
        if base_sha is not None:
            problems.append(_problem(adr, None, "base_sha256 must be null when base_path is null"))
    else:
        if not _relative_path(base_path):
            problems.append(_problem(adr, None, "base_path must be a repo-relative path or null"))
        if not (isinstance(base_sha, str) and _DIGEST_RE.match(base_sha)):
            problems.append(_problem(adr, None, "base_sha256 must be 64 lowercase hex when base_path is set"))

    rules = doc["rules"]
    handles: list[str] = []
    norm_rules: list[dict] = []
    if not isinstance(rules, list):
        problems.append(_problem(adr, None, "rules must be a list"))
        rules = []
    for rule in rules:
        if not (isinstance(rule, dict) and set(rule) == set(_RULE_KEYS)):
            problems.append(_problem(adr, None, f"each rule must carry exactly {list(_RULE_KEYS)}"))
            continue
        handle = rule["handle"]
        match = _HANDLE_RE.match(handle) if isinstance(handle, str) else None
        if match is None or match.group(1) != adr:
            problems.append(_problem(adr, None, f"rule handle {handle!r} must be {adr}/<slug>"))
            continue
        if handle in handles:
            problems.append(_problem(adr, handle, "rule handle appears twice"))
            continue
        handles.append(handle)
        standing, entry, base = rule["standing"], rule["entry"], rule["base"]
        if standing not in STANDINGS:
            problems.append(_problem(adr, handle, f"standing must be one of {list(STANDINGS)}, got {standing!r}"))
            continue
        found = entry_problems(entry, adr, handle, "entry")
        if standing == STANDING_GUIDANCE and base is not None:
            found.append(_problem(adr, handle, "a guidance rule has no binding version (base: null)"))
        if standing == STANDING_BINDING:
            found += (entry_problems(base, adr, handle, "base") if base is not None else
                      [_problem(adr, handle, "a binding rule carries its base_commit entry in base")])
        if base_path is None and standing == STANDING_BINDING:
            found.append(_problem(adr, handle, "an ADR with no text at base_commit binds nothing; every rule is guidance"))
        if found:
            problems.extend(found)
            continue
        norm_rules.append({"handle": handle, "standing": standing, "entry": normal_entry(entry),
                           "base": normal_entry(base) if base is not None else None})

    removed = doc["removed_in_run"]
    norm_removed: list[dict] = []
    if not isinstance(removed, list):
        problems.append(_problem(adr, None, "removed_in_run must be a list"))
        removed = []
    if removed and base_path is None:
        problems.append(_problem(adr, None, "removed_in_run must be empty when the ADR had no text at base_commit"))
    for item in removed:
        if not (isinstance(item, dict) and set(item) == set(_REMOVED_KEYS)):
            problems.append(_problem(adr, None, f"each removed_in_run entry carries exactly {list(_REMOVED_KEYS)}"))
            continue
        handle = item["handle"]
        match = _HANDLE_RE.match(handle) if isinstance(handle, str) else None
        if match is None or match.group(1) != adr:
            problems.append(_problem(adr, None, f"removed handle {handle!r} must be {adr}/<slug>"))
            continue
        if handle in handles:
            problems.append(_problem(adr, handle, "a handle is either a rule or removed in-run, never both"))
            continue
        found = entry_problems(item["base"], adr, handle, "base")
        if found:
            problems.extend(found)
            continue
        handles.append(handle)
        norm_removed.append({"handle": handle, "base": normal_entry(item["base"])})

    by_handle = {r["handle"]: r for r in norm_rules}
    removed_handles = {r["handle"] for r in norm_removed}
    promotions = doc["promotions"]
    norm_promotions: list[dict] = []
    promoted: set[str] = set()
    if not isinstance(promotions, list):
        problems.append(_problem(adr, None, "promotions must be a list"))
        promotions = []
    for index, promo in enumerate(promotions, 1):
        where = f"promotion {index}"
        if not (isinstance(promo, dict) and set(promo) == set(_PROMOTION_KEYS)):
            problems.append(_problem(adr, None, f"{where} carries exactly {list(_PROMOTION_KEYS)}"))
            continue
        date = _date(promo["date"])
        if date is None:
            problems.append(_problem(adr, None, f"{where}: date must be YYYY-MM-DD"))
        if not _text(promo["instruction"]):
            problems.append(_problem(adr, None, f"{where}: instruction must quote the owner's own words"))
        if not isinstance(promo["body"], bool):
            problems.append(_problem(adr, None, f"{where}: body must be true or false"))
        promo_handles = promo["handles"]
        if not _strings(promo_handles):
            problems.append(_problem(adr, None, f"{where}: handles must be a list of rule handles"))
            continue
        if not promo_handles and promo["body"] is not True:
            problems.append(_problem(adr, None, f"{where} promotes nothing"))
        if len(set(promo_handles)) != len(promo_handles):
            problems.append(_problem(adr, None, f"{where} names a handle twice"))
        for handle in promo_handles:
            rule = by_handle.get(handle)
            if rule is None and handle not in removed_handles:
                problems.append(_problem(adr, handle, f"{where} names a handle that is not a rule of this record"))
            elif rule is not None and not promotable(rule):
                problems.append(_problem(adr, handle, f"{where} promotes a rule that carries no in-run text"))
            elif handle in promoted:
                problems.append(_problem(adr, handle, f"{where} promotes a rule an earlier promotion already promoted"))
        promoted.update(promo_handles)
        norm_promotions.append({"date": date, "instruction": promo["instruction"],
                                "handles": list(promo_handles), "body": promo["body"]})
    if problems:
        raise ProvenanceError(problems)
    return {"schema": SCHEMA, "adr": adr, "run": {k: run[k] for k in _RUN_KEYS},
            "base_commit": doc["base_commit"], "base_path": base_path, "base_sha256": base_sha,
            "rules": norm_rules, "removed_in_run": norm_removed, "promotions": norm_promotions}


def render_record(record: dict) -> str:
    """Deterministic YAML for a record. Refuses a record `parse_record` would refuse, and
    guarantees `parse_record(render_record(r)) == r` for a normalized record."""
    import yaml
    ordered = {k: record[k] for k in _TOP_KEYS}
    text = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, default_flow_style=False,
                          width=1_000_000)   # never wrap a rule's wording across lines
    if parse_record(text, name=f"{record['adr']}.yaml") != ordered:
        raise ProvenanceError([_problem(record.get("adr"), None, "record does not round-trip")])
    return text


# ── standing ────────────────────────────────────────────────────────────────

def numbered(record: dict) -> list[tuple[int, str, dict]]:
    """(number, handle, item) for every rule and then every deletion, in record order. The
    numbers are the ones a promotion reply uses: rules 1..R, then deletions R+1..R+D."""
    items = [*record["rules"], *record["removed_in_run"]]
    return [(number, item["handle"], item) for number, item in enumerate(items, 1)]


def effective_rules(record: dict) -> dict[str, dict]:
    """handle -> {standing, binding, in_run_edit, promoted, removed} after every promotion, for
    each rule and each deletion. `binding` is the entry the rule binds at, or None. `in_run_edit`
    names the unpromoted in-run change: `added` for a guidance rule, the edited fields for a
    binding rule, `deleted-in-run` for a deletion, and nothing once promoted or when there is none. A
    promoted deletion has taken effect: standing None, nothing binds."""
    promoted = {h for promo in record["promotions"] for h in promo["handles"]}
    out: dict[str, dict] = {}
    for rule in record["rules"]:
        handle = rule["handle"]
        if handle in promoted:
            out[handle] = {"standing": STANDING_BINDING, "binding": rule["entry"],
                           "in_run_edit": [], "promoted": True, "removed": False}
        elif rule["standing"] == STANDING_GUIDANCE:
            out[handle] = {"standing": STANDING_GUIDANCE, "binding": None,
                           "in_run_edit": [ADDED], "promoted": False, "removed": False}
        else:
            out[handle] = {"standing": STANDING_BINDING, "binding": rule["base"],
                           "in_run_edit": edited_fields(rule["entry"], rule["base"]),
                           "promoted": False, "removed": False}
    for item in record["removed_in_run"]:
        handle = item["handle"]
        if handle in promoted:
            out[handle] = {"standing": None, "binding": None, "in_run_edit": [],
                           "promoted": True, "removed": True}
        else:
            out[handle] = {"standing": STANDING_BINDING, "binding": item["base"],
                           "in_run_edit": [DELETED], "promoted": False, "removed": True}
    return out


def removed_entries(record: dict) -> list[tuple[str, dict]]:
    """(handle, base entry) for each rule the run deleted whose deletion the owner has not
    promoted: each still binds at its base entry, so the summaries record collection keeps it
    as a live row."""
    effective = effective_rules(record)
    return [(item["handle"], item["base"]) for item in record["removed_in_run"]
            if not effective[item["handle"]]["promoted"]]


def open_request(record: dict) -> dict | None:
    """The promotion request a record still carries, or None when no in-run change is left
    unpromoted. `guidance` lists the rules whose whole text is guidance, `edited` the binding
    rules with an in-run edit, and `removed` the deletions, each numbered as a promotion reply
    numbers it."""
    effective = effective_rules(record)
    guidance, edited, removed = [], [], []
    for number, handle, item in numbered(record):
        state = effective[handle]
        if not state["in_run_edit"]:
            continue
        if state["removed"]:
            removed.append({"number": number, "handle": handle, "base": item["base"]})
        elif state["standing"] == STANDING_GUIDANCE:
            guidance.append({"number": number, "handle": handle, "entry": item["entry"]})
        else:
            edited.append({"number": number, "handle": handle, "edited": state["in_run_edit"],
                           "entry": item["entry"], "base": item["base"]})
    if not (guidance or edited or removed):
        return None
    return {"adr": record["adr"], "run": dict(record["run"]), "guidance": guidance,
            "edited": edited, "removed": removed}


def check_record_name(name: str) -> str | None:
    """The ADR id a provenance directory entry names, or None when the name is not a record's."""
    match = RECORD_NAME_RE.match(name)
    return match.group(1) if match else None


def parse_records(entries: list[tuple[str, bytes]]) -> dict[str, dict]:
    """Parse a provenance directory's entries, given as (file name, bytes). A name that is not
    `ADR-NNNN.yaml` refuses: the directory holds records and nothing else."""
    problems: list[dict] = []
    records: dict[str, dict] = {}
    for name, data in sorted(entries):
        adr = check_record_name(name)
        if adr is None:
            problems.append(_problem(f"adrs/{DIRNAME}/{name}", None,
                                     "the provenance directory holds only ADR-NNNN.yaml records"))
            continue
        try:
            records[adr] = parse_record(data.decode("utf-8"), name=name)
        except UnicodeDecodeError:
            problems.append(_problem(adr, None, "record is not UTF-8"))
        except ProvenanceError as exc:
            problems.extend(exc.problems)
    if problems:
        raise ProvenanceError(problems)
    return records


def records_sha256(entries: list[tuple[str, bytes]]) -> str:
    """The input digest a projection stamps for the record set: names and bytes, order-free."""
    digest = hashlib.sha256()
    for name, data in sorted(entries):
        digest.update(name.encode("utf-8") + b"\0" + hashlib.sha256(data).hexdigest().encode() + b"\n")
    return digest.hexdigest()


def join_standing(records: dict[str, dict], live_rows: list[dict]) -> dict[str, dict]:
    """handle -> {standing, binding_rule, in_run_edit} for every live ADR rule row whose ADR has
    a record. `binding_rule` is the binding version's rule text, or None for guidance.

    A rule with no record is absent from the result, so it keeps its current presentation. A
    live row of an ADR that has a record must be a rule of that record, or one of its unpromoted
    deletions, and must match the entry the record captured in every governs field; otherwise
    the join refuses rather than guessing a standing. A record handle with no live row (its ADR
    archived, the handle retired, or a deletion promoted) contributes nothing."""
    problems: list[dict] = []
    out: dict[str, dict] = {}
    for row in live_rows:
        if row.get("source_kind", "adr") != "adr":
            continue
        record = records.get(row["source_adr"])
        if record is None:
            continue
        handle = row["handle"]
        effective = effective_rules(record)
        captured = {r["handle"]: r["entry"] for r in record["rules"]}
        captured.update((h, base) for h, base in removed_entries(record))
        if handle not in captured:
            problems.append(_problem(row["source_adr"], handle,
                                     "governs handle has no rule in its ADR's provenance record"))
            continue
        moved = [f for f in ENTRY_FIELDS if comparable(row)[f] != comparable(captured[handle])[f]]
        if moved:
            problems.append(_problem(row["source_adr"], handle,
                                     "governs entry differs from the entry its provenance record captured "
                                     f"at acceptance (fields: {', '.join(moved)})"))
            continue
        state = effective[handle]
        out[handle] = {"standing": state["standing"],
                       "binding_rule": state["binding"]["rule"] if state["binding"] is not None else None,
                       "in_run_edit": list(state["in_run_edit"])}
    if problems:
        raise ProvenanceError(problems)
    return out
