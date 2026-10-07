"""Implementation reasoning, delivery evidence and source observations stay separate.

Schemas define closed record shapes. Reviewed bytes never receive editorial edits;
annotations are separate evidence. Only the shared historical verifier supplies
approval. Results and queries create no governing authority or authorization.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import yaml

import bionic_config
import council_gate as cg
import council_records as cr
import implementation_approval as ap

Refused = ap.Refused
ABSENT = "absent"
SCHEMAS = Path(__file__).resolve().parent.parent / "schemas"
KINDS = {"implementation-decision", "implementation-result", "implementation-annotation"}


def schema_errors(doc: dict) -> list:
    kind = doc.get("record_type") if isinstance(doc, dict) else None
    if kind not in KINDS:
        return [{"error": "record-type-refused"}]
    vp = cr._validator()
    schema = vp.load_schema(SCHEMAS / (kind + ".schema.json"))
    errors = []
    vp.validate(doc, schema, "#", "#", errors, kind)
    return errors


def load(path: Path) -> dict:
    ap.require(not path.is_symlink(), "record-symlink-refused")
    try:
        doc = yaml.safe_load(path.read_bytes())
    except (OSError, ValueError, yaml.YAMLError):
        raise Refused("record-unreadable") from None
    ap.require(not schema_errors(doc), "record-schema-refused")
    return doc


def _owner_run(repo: Path, path: Path) -> dict:
    absolute, _ = ap.checked_path(repo, str(path))
    ap.require(not absolute.is_symlink(), "record-symlink-refused")
    ap.require(absolute.is_file(), "owning-run-missing")
    try:
        run = yaml.safe_load(absolute.read_bytes())
    except (OSError, ValueError, yaml.YAMLError):
        raise Refused("owner-run-unreadable") from None
    ap.require(isinstance(run, dict), "owner-run-shape-refused")
    return run


def _decision(repo: Path, path: Path) -> tuple[dict, Path, str]:
    absolute, rel = ap.checked_path(repo, str(path))
    doc = load(absolute)
    ap.require(doc["record_type"] == "implementation-decision", "decision-type-refused")
    run_path = _identity_path(repo, absolute, doc)
    for entry in doc["scope"]:
        ap.checked_path(repo, entry)
    for label in doc["source_labels"]:
        ap.checked_path(repo, label["path"])
    return doc, run_path, rel


def _identity_path(repo: Path, absolute: Path, doc: dict) -> Path:
    parents = absolute.parents
    ap.require(len(parents) >= 7, "decision-layout-refused")
    ap.require(absolute.name == f"revision-{doc['revision']:03d}.yaml" and
               absolute.parent.name == doc["slug"] and parents[1].name == doc["run_id"] and
               parents[2].name == "implementations" and parents[4].name == "runs" and
               parents[5].name == "promptbooks", "decision-layout-refused")
    tree = bionic_config.load_config(repo).docs_root
    ap.require(parents[6] == tree, "decision-tree-refused")
    run_path = parents[3] / ("run-" + doc["run_id"] + ".yaml")
    run = _owner_run(repo, run_path)
    ap.require(run.get("book_id") == doc["book_id"] and run.get("run_id") == doc["run_id"],
               "decision-identity-refused")
    return run_path


def validate_decision(repo_root, path) -> dict:
    repo = Path(repo_root).resolve()
    doc, run_path, rel = _decision(repo, Path(path))
    ap.live_constraints(repo, doc["constraint_refs"])
    return {"valid": True, "identity": [doc[k] for k in ("book_id", "run_id", "slug", "revision")],
            "path": rel, "sha256": cr.sha256_file(repo / rel), "authority": "none"}


def _write_new(path: Path, doc: dict) -> Path:
    ap.require(not schema_errors(doc), "record-schema-refused")
    path.parent.mkdir(parents=True, exist_ok=True)
    owned = False
    try:
        with path.open("xb") as stream:
            owned = True
            stream.write(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True).encode())
    except FileExistsError:
        raise Refused("immutable-artifact-exists") from None
    except BaseException:
        if owned:
            path.unlink(missing_ok=True)
        raise
    return path


def write_decision(repo_root, path, doc: dict) -> Path:
    """Create a revision, or update only an unreviewed draft at its declared path."""
    repo = Path(repo_root).resolve()
    absolute, rel = ap.checked_path(repo, str(path))
    ap.require(not schema_errors(doc), "record-schema-refused")
    _identity_path(repo, absolute, doc)
    if absolute.exists():
        previous, run_path, _ = _decision(repo, absolute)
        run = _owner_run(repo, run_path)
        referenced = any(b.get("revision", {}).get("path") == rel for b in run.get("implementation_bindings", []))
        records = cr.discover_records(run_path.parent)
        reviewed = any(s.get("path") == rel for r in records if r.record_type == "council-record"
                       for s in r.doc["subjects"])
        ap.require(not referenced and not reviewed, "reviewed-revision-immutable")
        ap.require(all(previous[k] == doc[k] for k in ("book_id", "run_id", "slug", "revision", "slot")),
                   "decision-identity-refused")
        # Draft replacement is atomic. Reviewed revisions never reach this path.
        temporary = absolute.with_name(absolute.name + ".draft-tmp")
        owned = False
        try:
            _write_new(temporary, doc)
            owned = True
            os.replace(temporary, absolute)
        finally:
            if owned:
                temporary.unlink(missing_ok=True)
        return absolute
    # Validate declared path/owner before publishing even a new draft.
    expected = f"/implementations/{doc['run_id']}/{doc['slug']}/revision-{doc['revision']:03d}.yaml"
    ap.require(rel.endswith(expected), "decision-layout-refused")
    owner = absolute.parents[3] / ("run-" + doc["run_id"] + ".yaml")
    run = _owner_run(repo, owner)
    ap.require(run.get("book_id") == doc["book_id"] and run.get("run_id") == doc["run_id"],
               "decision-identity-refused")
    return _write_new(absolute, doc)


def validate_annotation(repo: Path, decision_path: Path, annotation: dict) -> None:
    ap.require(not schema_errors(annotation), "annotation-schema-refused")
    doc, _, rel = _decision(repo, decision_path)
    digest = cr.sha256_file(repo / rel)
    ap.require(annotation["decision"] == {"path": rel, "sha256": digest}, "annotation-decision-mismatch")
    target = annotation["target"]
    if target == "display_title":
        original = doc["display_title"]
    else:
        match = re.fullmatch(r"source_labels\.([0-9]+)\.label", target)
        ap.require(match is not None and int(match[1]) < len(doc["source_labels"]), "annotation-target-refused")
        original = doc["source_labels"][int(match[1])]["label"]
    ap.require(annotation["original_sha256"] == cr.sha256_bytes(original.encode()), "annotation-original-mismatch")


def write_annotation(repo_root, decision_path, doc: dict, output: Path) -> Path:
    repo = Path(repo_root).resolve()
    decision, run_path, rel = _decision(repo, Path(decision_path))
    ap.validate_implementation_binding(repo, run_path, slot=decision["slot"], revision_path=rel,
                                       revision_sha256=cr.sha256_file(repo / rel), historical_revision=True)
    validate_annotation(repo, repo / rel, doc)
    path, _ = ap.checked_path(repo, str(output))
    ap.require(path.parent == (repo / rel).parent and re.fullmatch(r"annotation-[0-9]{3}\.yaml", path.name),
               "annotation-layout-refused")
    # A second correction cannot silently reuse a previously corrected original label.
    for _, prior_doc in _revision_artifacts(repo, repo / rel, "annotation"):
        ap.require(prior_doc["target"] != doc["target"], "annotation-correction-reused")
    return _write_new(path, doc)


def source_hash(repo: Path, revision: str, path: str) -> str:
    ap.checked_path(repo, path)
    # A missing blob is absence only when the committed tree proves no entry.
    listing = cr.git(repo, "ls-tree", "-z", revision, "--", path)
    ap.require(listing.returncode == 0, "source-unreadable")
    if not listing.stdout:
        return ABSENT
    rows = [row.split(b"\t", 1) for row in listing.stdout.split(b"\0") if row]
    ap.require(len(rows) == 1 and os.fsdecode(rows[0][1]) == path and
               rows[0][0].split()[0] in (b"100644", b"100755"), "source-not-regular")
    blob = cr.git(repo, "cat-file", "blob", revision + ":" + path)
    ap.require(blob.returncode == 0, "source-unreadable")
    return cr.sha256_bytes(blob.stdout)


def commit_id(repo: Path, revision: str) -> str:
    ap.require(isinstance(revision, str) and revision and not revision.startswith("-"), "revision-refused")
    value = cr.git(repo, "rev-parse", "--verify", revision + "^{commit}")
    ap.require(value.returncode == 0, "revision-unavailable")
    return value.stdout.decode().strip()


def _revision_artifacts(repo: Path, path: Path, kind: str) -> list[tuple[Path, dict]]:
    """Select one immutable revision; validate other references before excluding them.

    A matching path with a wrong digest is corrupt evidence, never another revision.
    Other revisions in the same slug remain readable without affecting this choice.
    """
    decision, _, rel = _decision(repo, path)
    digest = cr.sha256_file(path)
    selected = []
    for candidate in sorted(path.parent.glob(kind + "-*.yaml")):
        doc = load(candidate)
        ap.require(doc["record_type"] == "implementation-" + kind, "artifact-type-refused")
        target, target_rel = ap.checked_path(repo, doc["decision"]["path"])
        ap.require(target.parent == path.parent, kind + "-decision-mismatch")
        other, _, _ = _decision(repo, target)
        ap.require(all(other[k] == decision[k] for k in ("book_id", "run_id", "slug")) and
                   doc["decision"]["sha256"] == cr.sha256_file(target), kind + "-decision-mismatch")
        if kind == "annotation":
            validate_annotation(repo, target, doc)
        if target_rel == rel:
            ap.require(doc["decision"]["sha256"] == digest, kind + "-decision-mismatch")
            selected.append((candidate, doc))
    return selected


def _annotation_inventory(repo: Path, path: Path) -> list[dict]:
    return [{"path": p.relative_to(repo).as_posix(), "sha256": cr.sha256_file(p)}
            for p, _ in _revision_artifacts(repo, path, "annotation")]


def _review_coverage(repo: Path, result: dict) -> None:
    expected = {result["decision"]["path"]: result["decision"]["sha256"]}
    expected.update({a["path"]: a["sha256"] for a in result["annotations"]})
    expected.update({s["path"]: s["delivered"] for s in result["sources"]})
    covered = set()
    for item in result["reviews"]:
        raw = json.loads(ap.committed_bytes(repo, item))
        ap.require(not cr.schema_errors(raw, "reviewer-report"), "review-schema-refused")
        subject = raw["subject"]
        if subject["form"] == "paths":
            for entry in subject["paths"]:
                if expected.get(entry["path"]) == entry["sha256"]:
                    covered.add(entry["path"])
        else:
            base, end = subject["range"].split("..")
            base, end = commit_id(repo, base), commit_id(repo, end)
            ap.require(cr.git(repo, "merge-base", "--is-ancestor", base, end).returncode == 0,
                       "review-range-refused")
            diff = cr.git(repo, "diff", "--name-only", "-z", base, end, "--")
            ap.require(diff.returncode == 0, "review-range-refused")
            changed = {os.fsdecode(x) for x in diff.stdout.split(b"\0") if x}
            for path, digest in expected.items():
                if path in changed and source_hash(repo, end, path) == digest:
                    covered.add(path)
    ap.require(set(expected).issubset(covered), "independent-review-scope-missing")


def _validate_result(repo_root, decision_path, evidence: dict, *, writing: bool):
    repo = Path(repo_root).resolve()
    decision, run_path, rel = _decision(repo, Path(decision_path))
    ap.require(not schema_errors(evidence), "result-schema-refused")
    digest = cr.sha256_file(repo / rel)
    ap.require(evidence["decision"] == {"path": rel, "sha256": digest}, "result-decision-mismatch")
    consumer = ap.validate_implementation_binding if writing else ap.validate_historical_implementation_binding
    proof = consumer(repo, run_path, slot=decision["slot"], revision_path=rel, revision_sha256=digest)
    ap.require(decision["scope"] == proof.slot["scope"] and
               decision["constraint_refs"] == proof.slot["constraint_refs"] and
               decision["slug"] == proof.slot["slug"], "decision-slot-mismatch")
    ap.require(all(ap.within_scope(path, decision["scope"]) for path in evidence["scope"]), "result-scope-refused")
    ap.require({s["path"] for s in evidence["sources"]} == set(evidence["scope"]) and
               len(evidence["sources"]) == len(evidence["scope"]), "result-source-scope-mismatch")
    if evidence["delivery_state"] == "complete":
        ap.require(set(evidence["scope"]) == set(decision["scope"]), "complete-scope-missing")
    if evidence["delivery_state"] == "unimplemented":
        ap.require(not evidence["scope"] and not evidence["sources"], "unimplemented-has-delivery")
    delivered, preimage = (commit_id(repo, evidence[k]) for k in ("source_revision", "preimage_revision"))
    ap.require(delivered == evidence["source_revision"] and preimage == evidence["preimage_revision"],
               "source-revision-not-exact")
    ap.require(cr.git(repo, "merge-base", "--is-ancestor", preimage, delivered).returncode == 0,
               "delivery-lineage-refused")
    if writing:
        ap.require(cr.git(repo, "merge-base", "--is-ancestor", delivered, "HEAD").returncode == 0,
                   "delivery-lineage-refused")
    for source in evidence["sources"]:
        ap.require(ap.within_scope(source["path"], proof.slot["scope"]), "result-scope-refused")
        ap.require(source_hash(repo, preimage, source["path"]) == source["preimage"] and
                   source_hash(repo, delivered, source["path"]) == source["delivered"], "source-evidence-mismatch")
        if writing:
            state = cr.path_state(repo, source["path"])
            clean = state.clean if source["delivered"] != ABSENT else not state.tracked and not (repo / source["path"]).exists()
            ap.require(clean and source_hash(repo, "HEAD", source["path"]) == source["delivered"], "delivered-source-dirty")
    annotations = evidence["annotations"]
    if writing:
        ap.require(annotations == _annotation_inventory(repo, repo / rel), "annotation-review-scope-missing")
    for item in annotations:
        annotation = yaml.safe_load(ap.committed_bytes(repo, item))
        validate_annotation(repo, repo / rel, annotation)
    for item in evidence["reviews"]:
        report = json.loads(ap.committed_bytes(repo, item))
        ap.require(report.get("book") == {"id": proof.run["book_id"], "content_hash": proof.run["book_content_hash"]}
                   and report.get("run_id") == proof.run["run_id"], "review-identity-refused")
        if writing:
            ap.require(not cg.subject_problems(repo, report["subject"]), "review-source-stale")
    _review_coverage(repo, evidence)
    return proof


def write_result(repo_root, decision_path, evidence: dict, output: Path | None = None) -> Path:
    _validate_result(repo_root, decision_path, evidence, writing=True)
    repo = Path(repo_root).resolve()
    _, _, rel = _decision(repo, Path(decision_path))
    if output is None:
        numbers = [int(p.stem.split("-")[1]) for p in (repo / rel).parent.glob("result-*.yaml")
                   if re.fullmatch(r"result-[0-9]{3}\.yaml", p.name)]
        output = (repo / rel).with_name(f"result-{max(numbers, default=0) + 1:03d}.yaml")
    output, _ = ap.checked_path(repo, str(output))
    ap.require(output.parent == (repo / rel).parent and re.fullmatch(r"result-[0-9]{3}\.yaml", output.name),
               "result-layout-refused")
    return _write_new(output, evidence)


def query(repo_root, decision_path, revision="HEAD") -> dict:
    repo = Path(repo_root).resolve()
    decision, run_path, rel = _decision(repo, Path(decision_path))
    digest = cr.sha256_file(repo / rel)
    approved = False
    reason = None
    try:
        ap.validate_historical_implementation_binding(repo, run_path, slot=decision["slot"], revision_path=rel,
                                                      revision_sha256=digest)
        approved = True
    except (Refused, cr.RecordError) as exc:
        reason = exc.code if isinstance(exc, Refused) else "approval-evidence-refused"
    eligibility = {"eligible": False, "limit": None, "constraint_refs": decision["constraint_refs"]}
    try:
        view = ap.live_constraints(repo, decision["constraint_refs"])
        undeclared = ap.undeclared_governing_constraints(repo, decision["scope"], decision["constraint_refs"],
                                                         view)
        if undeclared["overlapping"]:
            eligibility.update(limit="undeclared-governing-constraint", undeclared_refs=undeclared["overlapping"])
        else:
            eligibility["eligible"] = True
        if undeclared["unscoped"]:
            eligibility["unscoped_unchecked_refs"] = undeclared["unscoped"]
    except (Refused, cr.RecordError) as exc:
        eligibility["limit"] = exc.code if isinstance(exc, Refused) else "constraint-evidence-refused"
    except (bionic_config.BionicConfigError, OSError, ValueError, TypeError, KeyError, yaml.YAMLError):
        eligibility["limit"] = "constraint-evidence-refused"
    annotations = []
    for item in _annotation_inventory(repo, repo / rel):
        annotation = load(repo / item["path"])
        validate_annotation(repo, repo / rel, annotation)
        annotations.append({"evidence": item, "annotation": annotation})
    answer = {"authority": "none", "reviewed_intent": {"approved": approved, "limit": reason,
              "original": decision, "sha256": digest, "annotations": annotations}, "historical_delivery": [],
              "current_eligibility": eligibility,
              "current_state": {"requested_revision": revision, "observed_revision": None, "state": "UNOBSERVED"}}
    try:
        current = commit_id(repo, revision)
        answer["current_state"]["observed_revision"] = current
        ap.full_history(repo)
    except Refused as exc:
        answer["current_state"]["limit"] = exc.code
        return answer
    for path, result in _revision_artifacts(repo, repo / rel, "result"):
        result_rel = path.relative_to(repo).as_posix()
        ap.require(cr.is_clean(repo, result_rel), "result-not-committed")
        ap.require(result["decision"] == {"path": rel, "sha256": digest}, "result-decision-mismatch")
        history = {"path": result_rel, "state": result["delivery_state"], "source_revision": result["source_revision"],
                   "scope": result["scope"], "observed": "UNOBSERVED"}
        answer["historical_delivery"].append(history)
        if not approved:
            continue
        try:
            _validate_result(repo, repo / rel, result, writing=False)
            delivered = commit_id(repo, result["source_revision"])
            preimage = commit_id(repo, result["preimage_revision"])
            ap.require(cr.git(repo, "merge-base", "--is-ancestor", preimage, delivered).returncode == 0,
                       "delivery-lineage-refused")
            for source in result["sources"]:
                ap.require(source_hash(repo, delivered, source["path"]) == source["delivered"] and
                           source_hash(repo, preimage, source["path"]) == source["preimage"], "source-evidence-mismatch")
            if result["delivery_state"] == "unimplemented":
                history["observed"] = "unimplemented"
                continue
            if cr.git(repo, "merge-base", "--is-ancestor", delivered, current).returncode != 0:
                history["observed"] = "unrelated-lineage"
                continue
            observed = []
            for source in result["sources"]:
                if revision == "HEAD":
                    state = cr.path_state(repo, source["path"])
                    if state.head is None:
                        ap.require(not state.tracked and not (repo / source["path"]).exists(), "queried-source-dirty")
                    else:
                        ap.require(state.clean, "queried-source-dirty")
                value = source_hash(repo, current, source["path"])
                observed.append("delivered" if value == source["delivered"] else
                                "reverted" if value == source["preimage"] else "diverged")
            history["observed"] = ("delivered" if observed and all(s == "delivered" for s in observed) else
                                   "reverted" if observed and all(s == "reverted" for s in observed) else "diverged")
            history["paths"] = [{"path": s["path"], "state": state} for s, state in zip(result["sources"], observed)]
            answer["current_state"] = {"requested_revision": revision, "observed_revision": current,
                                        "state": history["observed"], "delivery_state": result["delivery_state"],
                                        "scope": result["scope"]}
        except Refused as exc:
            history["limit"] = exc.code
    return answer
