"""Role x skill x harness pairing gate (rule:declared-skill-is-runnable-or-routed).

Envelopes are read from the projections, never restated
(rule:envelope-is-read-from-the-projections): the Claude Code `tools` line less
`disallowedTools`, the `sandbox_mode` `codex_agents.render_agent` emits, and the
permission rules `opencode_agents.transform` emits. Two constants remain: the
coverage table `ROWS` (rule:each-need-has-a-grant-per-harness,
rule:coverage-is-cumulative), which `evaluate` refuses to run unless it matches
the catalog validator's access ladder, and the residual map in `Role.residuals`.
Static compatibility only: unverified host facts print as residuals
(rule:unverified-host-facts-are-residuals).

Run:

    uv run python3 crux/scripts/tests/_role_skill_pairing.py [--plugin-dir PATH]

Output, one line each:

    <role> x <skill> x <harness> need=<token> route=<envelope|lane:<kind>> <verdict>
        verdict is `pass`, `pass (residual: <fact>, ...)` or `FAIL (<reason>; ...)`
    ERROR <role>: <skill_lanes syntax defect>
    FAIL lane <role> x <skill> (<kind>) carries no triple
    pairs=N triples=N passing=N failing=N
    lane-carried <role> x <skill> x <harness> via <kind>
    residual <the passing triple line that carries residuals>

A residual is a host fact this static gate cannot observe. Each residual is
a fact the triple depends on, not a failure:

    codex-skill-binding     Codex binds the role's declared skills at spawn; not observed here.
    codex-uv-cache          a `uv run` script needs the uv cache writable under the Codex sandbox.
    codex-egress            a script that fetches dependencies needs network egress under the Codex sandbox.
    codex-git-writable      a write that touches `.git` needs it writable; recorded in the run as
                            observed-denied for Codex CLI 0.160.0 (an ADR correction is pending).
    codex-shell-permit      Codex shell use, granted by Bash or a declared shell_scope, not by the sandbox.
    opencode-external-read  OpenCode reads outside the project directory only on the host's own grant.
    opencode-host-write     a write-host need relies on the OpenCode host's own grant.
    claude-host-write       a write-host need relies on the Claude Code host's own grant.

Exit codes:

    0  no failing triple, no unused lane and no lane error
    1  at least one failing triple, unused lane or lane error
    2  environment or capability error: no role under <dir>/agents, no skill under
       <dir>/skills, no role that declares a skill, a file with no frontmatter, a
       coverage table that disagrees with the ladder, or any uncaught exception;
       one line `error: ...` on stderr and no summary line
"""
from __future__ import annotations

import argparse
import fnmatch
import functools
import importlib.util
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

PLUGIN_DIR = Path(__file__).resolve().parents[2]
HARNESSES = ("claude-code", "codex", "opencode")
# need -> grants it adds per harness (claude-code, codex, opencode).
ROWS = {
    "read-local": (("Read",), ("shell-permit",), ("read",)),
    "run-plugin-script": (("Bash",), ("workspace-write",), ("shell",)),
    "write-run": ((), (), ()),
    "write-tree": (("Edit", "Write"), (), ("edit",)),
    "write-host": ((), ("never",), ()),
}


class PairingError(RuntimeError):
    """The gate cannot run: the environment or the coverage table is unusable."""


@functools.lru_cache(maxsize=1)
def _modules():
    """Load the projection modules and the validator once; evaluate() calls this many times."""
    sys.path.insert(0, str(PLUGIN_DIR / "scripts"))
    import codex_agents, opencode_agents, yaml  # noqa: E401,PLC0415

    path = PLUGIN_DIR / "scripts" / "validate-catalog.py"
    spec = importlib.util.spec_from_file_location("vc_pairing", path)
    vc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vc)
    return vc, codex_agents, opencode_agents, yaml


@dataclass
class Triple:
    """One role x skill x harness verdict: `ok`, its `route`, the reasons `why` it failed and its `residuals`."""

    role: str
    skill: str
    harness: str
    need: str
    route: str = "envelope"
    ok: bool = False
    why: list = field(default_factory=list)
    residuals: tuple = ()

    def line(self) -> str:
        head = f"{self.role} x {self.skill} x {self.harness} need={self.need} route={self.route}"
        if not self.ok:
            return f"{head} FAIL ({'; '.join(self.why)})"
        return f"{head} pass" + (f" (residual: {', '.join(self.residuals)})" if self.residuals else "")


@dataclass
class Report:
    """Every triple the gate resolved, the declared lanes, and the lane syntax errors."""

    triples: list = field(default_factory=list)
    lanes: dict = field(default_factory=dict)  # (role, skill) -> kind
    errors: list = field(default_factory=list)

    @property
    def pairs(self) -> set:
        return {(t.role, t.skill) for t in self.triples}

    @property
    def lane_carried(self) -> set:
        return {(t.role, t.skill, t.harness, t.route.removeprefix("lane:")) for t in self.triples if t.ok and t.route != "envelope"}

    @property
    def unused_lanes(self) -> list:
        return sorted(set(self.lanes) - {(r, s) for r, s, _h, _k in self.lane_carried})

    @property
    def failures(self) -> list:
        return [t for t in self.triples if not t.ok]

    @property
    def ok(self) -> bool:
        return not (self.failures or self.unused_lanes or self.errors)


def _list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value]
    return [t.strip().strip("'\"") for t in str(value or "").strip("[]").split(",") if t.strip()]


def _meta(path: Path, vc) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if not lines or lines[0].strip() != "---" or end is None:
        raise PairingError(f"{path} has no frontmatter")
    return vc.load_yaml("\n".join(lines[1:end]))


class Role:
    def __init__(self, path: Path, mods) -> None:
        vc, codex, opencode, yaml = mods
        fm = _meta(path, vc)
        meta = fm.get("metadata") or {}
        self.name, self.skills, self.scope = path.stem, _list(fm.get("skills")), meta.get("shell_scope") or None
        self.lanes, self.lane_errors = vc.parse_skill_lanes(meta["skill_lanes"]) if "skill_lanes" in meta else ({}, [])
        granted, denied = _list(fm.get("tools")), _list(fm.get("disallowedTools"))
        # Any denied Agent grant drops every Agent(...) grant. Conservative: it fails closed, so a role
        # that denies one delegate is treated as dispatching none.
        no_agent = any(d.startswith("Agent") for d in denied)
        self.tools = {t for t in granted if t not in denied and not (t.startswith("Agent") and no_agent)}
        self.broken = ["role holds Edit without Bash"] if "Edit" in self.tools and "Bash" not in self.tools else []
        self.broken += [f"disallowedTools withholds {t} the tools line grants" for t in ("Edit", "Write")
                        if t in granted and t in denied]
        if self.scope is not None and self.scope not in vc.ACCESS_LADDER:
            self.broken.append(f"unknown shell_scope {self.scope!r}")
        stub = SimpleNamespace(model="stub", reasoning_effort="stub")
        self.sandbox = tomllib.loads(codex.render_agent(codex.parse_source(path), stub))["sandbox_mode"]
        text = opencode.transform(self.name, opencode.parse_source(path)[0], "stub-model")
        self.rules = yaml.safe_load(text.split("\n---\n", 1)[0].removeprefix("---\n"))["permissions"]

    def _oc(self, action: str, resource: str = "*") -> bool:
        verdict = False  # last matching rule wins, as the projection orders them
        for r in self.rules:
            if r["action"] == action and fnmatch.fnmatchcase(resource, r["resource"]):
                verdict = r["effect"] == "allow"
        return verdict

    def held(self, harness: str, grant: str) -> bool:
        if harness == "claude-code":
            return grant in self.tools
        if harness == "opencode":
            return self._oc(grant)
        return {"shell-permit": "Bash" in self.tools or self.scope is not None,
                "workspace-write": self.sandbox == "workspace-write"}.get(grant, False)

    def dispatch(self, harness: str, target: str) -> bool:
        """Whether this role may dispatch `target` in `harness`."""
        # Codex is always true: the projected execution override returns every dispatch to the parent.
        if harness == "claude-code":
            return "Agent" in self.tools or f"Agent({target})" in self.tools
        return harness == "codex" or self._oc("subagent", target)

    def missing(self, harness: str, need: str, ladder) -> list[str]:
        """Grants the role lacks in `harness` to meet `need`; empty means its envelope covers the need."""
        if self.broken:
            return list(self.broken)
        skill_grant = {"claude-code": "Skill", "opencode": "skill"}.get(harness)
        out = ["skill grant"] if skill_grant and not self.held(harness, skill_grant) else []
        for level in ladder[: ladder.index(need) + 1]:
            out += [g for g in ROWS[level][HARNESSES.index(harness)] if not self.held(harness, g)]
        if self.scope and ladder.index(need) > ladder.index(self.scope):
            out.append(f"shell_scope={self.scope} below {need}")
        return out

    def residuals(self, harness: str, need: str, ladder) -> tuple:
        """Sorted host facts a passing triple depends on and this gate cannot observe."""
        at, res = ladder.index(need), set()
        script, run = ladder.index("run-plugin-script"), ladder.index("write-run")
        if harness == "codex":
            res = {"codex-skill-binding"} | ({"codex-uv-cache", "codex-egress"} if at >= script else set())
            res |= {"codex-git-writable"} if at >= run else set()
            res |= {"codex-shell-permit"} if "Bash" not in self.tools and self.scope else set()
        elif harness == "opencode":
            res = {"opencode-external-read"} | ({"opencode-host-write"} if need == "write-host" else set())
        elif need == "write-host":
            res = {"claude-host-write"}
        return tuple(sorted(res))


def _lane(role: Role, roles: dict, t: Triple, kind: str, supplied, ladder) -> None:
    """Fill the lane verdict into `t` (rule:lane-has-a-model-visible-route)."""
    h, bad = t.harness, []
    if kind == "returns-to-caller":
        t.ok = True
    elif kind == "caller-supplies":
        if ladder.index(t.need) > ladder.index("run-plugin-script"):
            bad = ["caller-supplies cannot carry a need above run-plugin-script"]
        elif supplied not in ladder:
            bad = ["skill declares no supplied_access"]
        elif role.missing(h, supplied, ladder):
            bad = [f"supplied {supplied} not covered: {', '.join(role.missing(h, supplied, ladder))}"]
        else:
            t.ok, t.residuals = True, role.residuals(h, supplied, ladder)
    else:
        target = roles.get(kind.removeprefix("delegates:"))
        if target is None or t.skill not in target.skills:
            bad = ["target does not declare the skill"]
        elif t.skill in target.lanes:
            bad = ["target holds a lane for the skill"]
        elif target.missing(h, t.need, ladder):
            bad = [f"target {target.name} envelope lacks {', '.join(target.missing(h, t.need, ladder))}"]
        elif not role.dispatch(h, target.name):
            bad = [f"no dispatch grant for {target.name}"]
        else:
            t.ok, t.residuals = True, target.residuals(h, t.need, ladder)
    t.why = [] if t.ok else t.why + bad


def evaluate(plugin_dir: Path = PLUGIN_DIR) -> Report:
    """Resolve every declared role x skill pair under `plugin_dir` in each harness.

    Raises PairingError when the coverage table disagrees with the validator's ladder.
    """
    mods = _modules()
    vc, ladder = mods[0], mods[0].ACCESS_LADDER
    if tuple(ROWS) != tuple(ladder):
        raise PairingError(f"coverage table {tuple(ROWS)} does not match the access ladder {tuple(ladder)}")
    roles = {p.stem: Role(p, mods) for p in sorted((plugin_dir / "agents").glob("*.md"))}
    skills = {p.parent.name: (_meta(p, vc).get("metadata") or {}) for p in sorted((plugin_dir / "skills").glob("*/SKILL.md"))}
    report = Report()
    for role in roles.values():
        report.errors += [f"{role.name}: {e}" for e in role.lane_errors]
        report.lanes.update({(role.name, s): k for s, k in role.lanes.items() if s in role.skills})
        for skill in role.skills:
            meta = skills.get(skill, {})
            need = meta.get("requires_access")
            for h in HARNESSES:
                # A broken role fails every triple on its own defect, so no lane may rescue it.
                t = Triple(role.name, skill, h, str(need))
                report.triples.append(t)
                if need not in ladder:
                    t.why = [f"skill {skill} has no valid requires_access"]
                    continue
                miss = role.missing(h, need, ladder)
                t.ok, t.why = not miss, [f"{h} envelope lacks {', '.join(miss)}"]
                if t.ok:
                    t.residuals = role.residuals(h, need, ladder)
                elif skill in role.lanes and not role.broken:
                    t.route = f"lane:{role.lanes[skill]}"
                    _lane(role, roles, t, role.lanes[skill], meta.get("supplied_access"), ladder)
    return report


def format_report(report: Report) -> str:
    """Render the report in the grammar the module docstring defines."""
    out = [t.line() for t in report.triples] + [f"ERROR {e}" for e in report.errors]
    out += [f"FAIL lane {r} x {s} ({report.lanes[r, s]}) carries no triple" for r, s in report.unused_lanes]
    out.append(f"pairs={len(report.pairs)} triples={len(report.triples)} "
               f"passing={len(report.triples) - len(report.failures)} failing={len(report.failures)}")
    out += [f"lane-carried {r} x {s} x {h} via {k}" for r, s, h, k in sorted(report.lane_carried)]
    return "\n".join(out + [f"residual {t.line()}" for t in report.triples if t.ok and t.residuals])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plugin-dir", type=Path, default=PLUGIN_DIR)
    plugin_dir = ap.parse_args(argv).plugin_dir
    try:
        for kind, pattern in (("role", "agents/*.md"), ("skill", "skills/*/SKILL.md")):
            if not any(plugin_dir.glob(pattern)):
                raise PairingError(f"no {kind} found under {plugin_dir / pattern.split('/')[0]}")
        rep = evaluate(plugin_dir)
        if not rep.pairs:  # a zero denominator passes nothing
            raise PairingError(f"no role declares a skill under {plugin_dir / 'agents'}")
    except Exception as exc:  # noqa: BLE001 - any failure to run is exit 2, never a failing triple
        message = str(exc) if isinstance(exc, PairingError) else f"{type(exc).__name__}: {exc}"
        print(f"error: {message}", file=sys.stderr)
        return 2
    print(format_report(rep))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
