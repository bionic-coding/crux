"""Shared evidence adapter for the checkout and staged unittest suites.

Scheduling and diagnostic destinations do not change test discovery. Preserve
those in the executed command while sharing a canonical discovery command.
The broad input declaration includes documentation because tests read it.
"""
import json
from pathlib import Path
import sys

from test_evidence import execute, lookup, storage, _read

INPUTS = ["crux", "crux-mods", "tools", "opencode", "bionic", "public", "*.md",
          "*.sh", "pyproject.toml", "uv.lock", ".bionic.yml", ".claude-plugin",
          ".agents/plugins", ".codex-plugin", ".github", ".claude/skills",
          ".agents/skills", ".opencode/skills", ".opencode/skill", ".generated"]
ENVIRONMENT = ["PYTHONPATH", "UV_PYTHON", "PYTHONHASHSEED", "PYTHONSAFEPATH",
               "PYTHONNOUSERSITE", "PYTHONOPTIMIZE", "PATH", "LANG", "LC_ALL", "TZ",
               "CI", "UV_OFFLINE", "UV_INDEX_URL", "UV_EXTRA_INDEX_URL"]


def runtime_exclusions(root):
    """Operational cycle records are outputs, not inputs of these static suites.

    Checks explicitly testing live cycle records should declare those inputs
    themselves without this suite-specific exclusion.
    """
    root = Path(root)
    if any((root / name).exists() for name in (".bionic.yml", ".crux", "bionic/manifest.yml", "docs/manifest.yml")):
        from bionic_config import load_config
        docs = load_config(root).docs_root.relative_to(root.resolve()).as_posix()
    else:
        docs = "docs"
    return [docs + "/cycles"]


def evidence_plan(root, declaration):
    """Describe reuse without executing a check or exposing environment values."""
    found = lookup(root, declaration)
    previous = found["record"]
    if previous is None:
        candidates = [_read(path) for path in storage(root).glob("TE-*.json")]
        candidates = [r for r in candidates if r["declaration"]["check_id"] == declaration["check_id"]]
        previous = max(candidates, key=lambda r: r["finished_at"], default=None)
    report = {"check_id": declaration["check_id"], "state": found["state"],
              "evidence_id": previous["id"] if previous else None}
    if previous and found["state"] == "inputs-changed":
        before, after = previous["snapshot"], found["snapshot"]
        changed = sorted(k for k in set(before["inputs"]) | set(after["inputs"])
                         if before["inputs"].get(k) != after["inputs"].get(k))
        report["changed_inputs"] = changed[:100]
        report["changed_input_count"] = len(changed)
        report["changed_identity_fields"] = sorted(
            k for k in set(before["identity"]) | set(after["identity"])
            if before["identity"].get(k) != after["identity"].get(k))
        if "environment_sha256" in report["changed_identity_fields"]:
            report["environment_detail"] = "Only environment hashes are stored; exact variable differences are unavailable."
        if not changed and not report["changed_identity_fields"]:
            report["other_changes"] = "Declaration or Git inventory/HEAD tree differs."
    if found["state"] != "passed":
        report["remedy"] = "Establish evidence explicitly with sync.sh --dry-run --refresh-test-evidence (or preflight --refresh-test-evidence). Matching failures also require CRUX_TEST_RETRY_REASON."
    return found, report


def run_shared(args):
    root = Path.cwd().resolve()
    command = [sys.executable, "crux/scripts/tests/parallel_suite.py", args.start,
               "--pattern", args.pattern]
    if args.top:
        command += ["--top-level-directory", args.top]
    actual = list(command)
    if args.workers:
        actual += ["--workers", str(args.workers)]
    if args.records:
        actual += ["--records", args.records]
    if args.timings:
        actual += ["--timings", args.timings]
    declaration = {"check_id": f"{args.evidence_scope}:unittest:{args.start}:{args.pattern}",
                   "command": command, "inputs": INPUTS,
                   "environment": ENVIRONMENT, "git_tracked": args.evidence_scope == "checkout",
                   "exclude_inputs": runtime_exclusions(root)}
    found, report = evidence_plan(root, declaration)
    print("Test evidence plan: " + json.dumps(report, sort_keys=True), flush=True)
    if getattr(args, "plan_test_evidence", False):
        return 0 if found["state"] == "passed" else 3
    if getattr(args, "reuse_test_evidence_only", False):
        if found["state"] != "passed":
            print("REFUSE: test evidence is " + found["state"] + "; " + report["remedy"], file=sys.stderr)
            return 2
        result = {"action": "reused", "evidence": found["record"]}
    else:
        result = execute(root, declaration, args.retry_reason, execution_command=actual)
    record = result["evidence"]
    output = storage(root) / record["output"]
    # Replayed output is labeled as evidence, never a fresh execution.
    print(f"Test evidence {result['action']}: {record['id']} ({record['reason']}; {record['seconds']:.2f}s)", flush=True)
    print(output.read_text(errors="replace"), end="", flush=True)
    return 0 if record["status"] == "passed" else (1 if record["status"] == "failed" and record["returncode"] == 1 else 2)
