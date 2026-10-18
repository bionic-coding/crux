# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Look up or execute repository-shared checks from an explicit JSON declaration."""
import argparse
import json
from pathlib import Path
import sys
from test_evidence import EvidenceError, execute, lookup, validate_evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "lookup", "validate"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--check", type=Path, help="JSON check declaration")
    parser.add_argument("--evidence-id")
    parser.add_argument("--retry-reason")
    args = parser.parse_args()
    try:
        if args.action == "validate":
            result = validate_evidence(args.repo_root, args.evidence_id)
            passed = True
        else:
            if args.check is None:
                parser.error("--check is required")
            declaration = json.loads(args.check.read_text())
            if args.action == "run":
                result = execute(args.repo_root, declaration, args.retry_reason)
                passed = result["evidence"]["status"] == "passed"
            else:
                result = lookup(args.repo_root, declaration)
                passed = result["state"] == "passed"
        print(json.dumps(result, indent=2))
        return 0 if passed else 1
    except (EvidenceError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
