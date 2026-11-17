"""_census_fixture.py — a documentation tree holding every input-census member kind.

Shared by the census tests. It builds, under a temporary repository root:

  - ADR-0901 to ADR-0903, Accepted, and ADR-0904, Deprecated and carrying a
    `retires` list (a host whose retirement persists by its date alone);
  - two ADRs accepted through a real native Lite council: the first stays
    active and Accepted (a prospective Accepted ADR with its proposal,
    receipt and council record), the second is archived as Superseded (an
    archived policy host with its acceptance record);
  - a signed backfill batch, a signed reconciliation ledger record, and the
    observations concern with one record and one survey batch signed off to
    S9 through the real sign-off tooling, with its receipt;
  - an empty provenance directory and a run snapshot under promptbooks/runs.

It is a helper module, not a test module, so discovery never collects it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

DATE = "2026-08-30"


def adr(num: int, *, status: str = "Accepted", extra: str = "") -> str:
    return "\n".join([
        "---", f"id: ADR-{num:04d}", f'title: "Decision {num}"', f"status: {status}",
        "date: 2026-08-01", "proposed_date: 2026-08-01", "accepted_date: 2026-08-01",
        "supersedes: []", "superseded_by: null", "tags: [test]", "governs:",
        f"  - handle: ADR-{num:04d}/rule-{num}", "    domain: alpha",
        f'    rule: "Rule {num} holds."', "    scope: crux/scripts", "    provenance: authored",
        *([extra] if extra else []),
        "---", "", f"# ADR-{num:04d}", "", "Body.", ""])


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          check=True).stdout.decode()


def _vote(request, context, decision):
    body = {"decision": decision, "reasoning": "Check completed.", "findings": []}
    return {"tool": "collaboration.spawn_agent", "input": request["dispatch"],
            "result": {"task_name": context},
            "final": f"Message Type: FINAL_ANSWER\nTask name: /root\nSender: {context}\n"
                     "Payload:\n" + json.dumps(body)}


def accept(root: Path, title: str, handle: str) -> Path:
    """Propose and accept one ADR through a native Lite council; its path."""
    import decision_policy as dp
    from council_native import ingest, prepare
    from council_policy import disposition
    docs = root / "bionic"
    subject = dp.propose(root, {
        "title": title, "body": "# Decision\nDecide.\n",
        "governs": [{"domain": "alpha", "scope": "crux/scripts", "rule": f"{title} holds.",
                     "handle": handle}]}, origin="direct")["path"]
    args = {"harness": "codex", "author_context": "/root/author"}
    first = prepare(root, "adr", subject, "Review", **args)
    ingest(root, first["request"], _vote(first, "/root/challenger", "REQUEST_CHANGES"))
    final = prepare(root, "adr", subject, "Review", phase="final",
                    attempt_path=first["attempt"], response="Architect response", **args)
    reviewed = ingest(root, final["request"], _vote(final, "/root/final", "APPROVE"))
    disposition(root, reviewed["record"], {
        "agrees": True,
        "subject_sha256": hashlib.sha256((docs / subject).read_bytes()).hexdigest(),
        "rationale": "Proceed", "dissent": []})
    dp.accept(root, subject, reviewed["record"], human_approval="Owner accepts this")
    return docs / subject


def council_record(docs: Path, adr_id: str) -> Path:
    """The council record an ADR's acceptance receipt names."""
    receipt = json.loads((docs / "adrs" / "acceptances" / f"{adr_id}.json").read_text())
    return docs / receipt["council"]


REVIEWS = """config_version: '1'
batches:
- id: B1
  signed: 2026-08-27
  handles: []
  no_rule: []
receipts: []
no_rule: []
"""

LEDGER = """config_version: "1"
reconciliations:
  - invariant: INV-0001
    handle: ADR-0901/rule-901
    verdict: compatible
    content_digest: "%s"
    rationale: null
    signed: 2026-08-28
""" % ("0" * 64)

RUN = """book_id: PB-0001
run_id: RUN-001
prompts:
  - artifacts:
      - "ADR-0901 implementation"
"""

def build(root: Path, *, chains: bool = True, survey: bool = True) -> dict:
    """Build the fixture under `root`; returns the named paths."""
    root = Path(root)
    docs = root / "bionic"
    adrs = docs / "adrs"
    adrs.mkdir(parents=True)
    (root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: bionic\n', encoding="utf-8")
    concerns = "[adrs, observations, arch]" if survey else "[adrs]"
    (docs / "manifest.yml").write_text(
        f'schema_version: "5"\nconcerns_enabled: {concerns}\n'
        "adr:\n  next_number: 1000\n  governs_from: 1\n"
        "observation:\n  next_number: 2\n  stale_days: 90\n", encoding="utf-8")
    (docs / "objectives.md").write_text("Use proportional review with durable history.\n",
                                        encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    out = {"root": root, "docs": docs, "adrs": adrs}
    if survey:
        # First, on a tree that holds nothing else: the admission the
        # scaffold runs reads the whole tree.
        out.update(_survey(root, docs))
    for num in (901, 902, 903):
        (adrs / f"ADR-{num:04d}-x.md").write_text(adr(num), encoding="utf-8")
    (adrs / "ADR-0904-x.md").write_text(adr(904, status="Deprecated", extra=(
        "    retires: [ADR-0903/rule-903]")), encoding="utf-8")
    (adrs / "summaries").mkdir(exist_ok=True)
    (adrs / "summaries" / "backfill-reviews.yml").write_text(REVIEWS, encoding="utf-8")
    (adrs / "doctrine").mkdir(exist_ok=True)
    (adrs / "doctrine" / "reconciliations.yml").write_text(LEDGER, encoding="utf-8")
    (adrs / "provenance").mkdir()
    run_dir = docs / "promptbooks" / "runs" / "PB-0001-x"
    run_dir.mkdir(parents=True)
    (run_dir / "run-RUN-001.yaml").write_text(RUN, encoding="utf-8")
    out["run"] = run_dir / "run-RUN-001.yaml"
    if chains:
        for args in (("init", "-q"), ("config", "user.email", "t@example.invalid"),
                     ("config", "user.name", "T")):
            git(root, *args)
        from council_policy import initialize
        initialize(root, "lite", selection="Explicit test setup selects Lite")
        git(root, "add", ".")
        git(root, "commit", "-qm", "fixture")
        active = accept(root, "Keep", "keep-rule")
        gone = accept(root, "Gone", "gone-rule")
        archive = adrs / "archive"
        archive.mkdir()
        archived = archive / gone.name
        archived.write_text(gone.read_text().replace("status: Accepted", "status: Superseded", 1),
                            encoding="utf-8")
        gone.unlink()
        out.update(active=active, archived=archived,
                   active_id=active.name[:8], archived_id=archived.name[:8],
                   active_council=council_record(docs, active.name[:8]),
                   archived_council=council_record(docs, archived.name[:8]))
    return out


def _survey(root: Path, docs: Path) -> dict:
    """The observations concern with one record and one batch signed off to S9."""
    import importlib.util
    from crux.arch.recover import StateFile, candidate_id
    obs = docs / "observations"
    obs.mkdir()
    (docs / "log.md").write_text("# Log\n", encoding="utf-8")
    (docs / "AGENTS.md").write_bytes(
        (SCRIPTS.parent / "templates" / "AGENTS.md.tmpl").read_bytes())
    state = StateFile(docs / "arch" / "_recovered" / "state.yml")
    cid = candidate_id("external-dependency", "httpx")
    state.rows[cid] = {"id": cid, "anchor_kind": "external-dependency",
                       "canonical_anchor": "httpx", "state": "observed",
                       "rule": "The gateway depends on httpx",
                       "evidence": ["src/a.py:1-1"], "domain": "runtime"}
    state.save()

    def load(name, filename):
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault(name, module)
        spec.loader.exec_module(module)
        return module
    ss = load("survey_sheet", "survey_sheet.py")
    proc = subprocess.run([sys.executable, str(SCRIPTS / "scaffold-survey-sheet.py"),
                           "--repo-root", str(root), "--date", DATE],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    bid = json.loads(proc.stdout)["batch_id"]
    sheet_path = obs / f"survey-{bid}.yml"
    sheet = ss.read_sheet(sheet_path)
    for row in sheet["rows"]:
        row["verdict"] = "ratify"
        row["rationale"] = "Reviewed."
    ss.write_sheet(sheet_path, sheet, contained_under=docs)
    proc = subprocess.run([sys.executable, str(SCRIPTS / "signoff-survey.py"),
                           "--repo-root", str(root), "--date", DATE, "--batch", bid],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return {"obs": obs, "batch": obs / "_surveys" / bid,
            "receipt": obs / "_surveys" / bid / "receipt.yml"}
