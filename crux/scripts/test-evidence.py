# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Look up, execute, validate or report on repository-shared checks.

``run``, ``lookup`` and ``validate`` read one JSON check declaration or one receipt. ``report``
reads a named receipt and prints two separate verdicts, and neither implies the other:

* ``completeness``: the receipt is present, its seal verifies, and the output log it names is
  present with the recorded sha256 (over the decompressed bytes of a compressed copy). It says the
  historical result is intact.
* ``reuse_eligibility``: lookup would reuse the receipt for the subject's current inputs and
  environment. A version-1 receipt, or one whose inputs changed, is complete and not eligible.

``lookup`` prints the state (``passed``, ``failed``, ``expired``, ``inputs-changed`` or
``missing``), the deciding receipt, the earlier failures a later pass supersedes, and each receipt
it ignored with the reason. ``report --directory DIR`` reads a retained copy and writes nothing.

``declare --preset NAME --check-id ID [--command JSON] [--requirement JSON] [--output PATH]`` prints
a concrete JSON declaration for a cycle check from an evidence preset (see
``suite_evidence.PRESETS``). The preset supplies the shared bookkeeping exclusions, so a check is
never hand-listed. The declaration carries no preset field. Exit 2 refuses an unknown preset, a
missing ``--command`` for ``whole-tree``, a preset whose script is absent, and an invalid
``evidence.bookkeeping_paths`` entry.

Two declaration fields have no flag: ``input_projections`` and a lock's ``project_version``. Only a
registered suite carries them. ``run`` and ``lookup`` exit 2 for a ``--check`` declaration that
carries one unless it equals the registered declaration of its check id, and ``declare`` exits 2 for
a ``--requirement`` that names ``project_version``. ``validate`` and ``report`` read receipts that
carry them unchanged.
"""
import argparse
import json
from pathlib import Path
import sys
import suite_evidence
from test_evidence import (EvidenceError, completeness, execute, lookup, normalize, registered_only_fields,
                           requirement_names_project_version, reuse_eligibility, storage, validate_evidence)


def refuse_unregistered_fields(declaration, repo_root, source_root):
    """Exit-2 refusal of a command-line declaration whose registered-only fields are not the registered ones."""
    normalized = normalize(declaration)
    fields = registered_only_fields(normalized)
    if not fields:
        return
    registered = suite_evidence.registered_declaration(repo_root, normalized["check_id"], dev_root=source_root)
    if registered is None or normalize(registered) != normalized:
        raise EvidenceError(f"{' and '.join(fields)} may appear only in the registered declaration of {normalized['check_id']}; "
                            "a declaration passed on the command line does not equal it")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("run", "lookup", "validate", "report", "declare"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-root", type=Path, help="the dev checkout that holds uv.lock and the durable store, when --repo-root is a stage")
    parser.add_argument("--check", type=Path, help="JSON check declaration")
    parser.add_argument("--evidence-id")
    parser.add_argument("--directory", type=Path, help="report: read receipts from this directory instead of the evidence store")
    parser.add_argument("--retry-reason")
    parser.add_argument("--preset", help="declare: the evidence preset name")
    parser.add_argument("--check-id", help="declare: the check id of the declaration")
    parser.add_argument("--command", help="declare: the command as a JSON array (whole-tree only)")
    parser.add_argument("--requirement", help="declare: a requirement as a JSON object; it replaces the preset's default")
    parser.add_argument("--output", type=Path, help="declare: write the declaration here instead of stdout")
    args = parser.parse_args()
    try:
        if args.action == "declare":
            if not args.preset or args.check_id is None:
                parser.error("--preset and --check-id are required")
            requirement = json.loads(args.requirement) if args.requirement is not None else None
            if requirement_names_project_version(requirement):
                raise EvidenceError("project_version may be set only by a registered declaration, not by declare --requirement")
            declaration = suite_evidence.preset_declaration(
                args.repo_root, args.preset, args.check_id,
                command=json.loads(args.command) if args.command is not None else None, requirement=requirement)
            text = json.dumps(declaration, indent=2) + "\n"
            if args.output is not None:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(text)
            else:
                print(text, end="")
            return 0
        if args.action == "validate":
            result = validate_evidence(args.repo_root, args.evidence_id, source_root=args.source_root)
            passed = True
        elif args.action == "report":
            if not args.evidence_id:
                parser.error("--evidence-id is required")
            directory = args.directory if args.directory is not None else storage(args.repo_root, args.source_root)
            result = {"evidence_id": args.evidence_id,
                      "completeness": {k: v for k, v in completeness(directory, args.evidence_id).items() if k != "record"},
                      "reuse_eligibility": reuse_eligibility(args.repo_root, args.evidence_id, source_root=args.source_root, directory=directory)}
            passed = result["completeness"]["complete"] and result["reuse_eligibility"]["eligible"]
        else:
            if args.check is None:
                parser.error("--check is required")
            declaration = json.loads(args.check.read_text())
            refuse_unregistered_fields(declaration, args.repo_root, args.source_root)
            if args.action == "run":
                result = execute(args.repo_root, declaration, args.retry_reason, source_root=args.source_root)
                passed = result["evidence"]["status"] == "passed"
            else:
                found = lookup(args.repo_root, declaration, source_root=args.source_root)
                result = {"state": found["state"], "record": found["record"], "earlier_failures": found["earlier_failures"],
                          "ignored": found["ignored"], "fingerprint": found["snapshot"]["fingerprint"], "store": found["store"]}
                passed = found["state"] == "passed"
        print(json.dumps(result, indent=2))
        return 0 if passed else 1
    except (EvidenceError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
