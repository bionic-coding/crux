"""Shared fixtures for the ADR-0181 input-failure tests (`test_arch_input_failures_*`).

Not a test module: it holds no `TestCase`, so importing it from each pack's test
file runs nothing twice. Every helper builds the tree it examines, so the tests
hold in the staged public artifact, which ships `crux/` without `bionic/`.
"""

from __future__ import annotations

import ast
import contextlib
import importlib
import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

CORE = importlib.import_module("crux.arch.core")
D = importlib.import_module("crux.arch.derive")
DRIVER = SCRIPTS / "derive-arch.py"
ARCH_PKG = SCRIPTS / "crux" / "arch"


def _load_driver():
    spec = importlib.util.spec_from_file_location("_test_arch_input_failures_cli", DRIVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CLI = _load_driver()


def skip_if_root(case: unittest.TestCase) -> None:
    """A mode-000 fixture is still readable to the superuser."""
    if os.geteuid() == 0:
        case.skipTest("running as root: a mode-000 path is still readable")


def run_cli(root: Path, *argv: str) -> tuple[int, str, dict, str]:
    """Run `derive-arch.py` in process. Returns (exit, stdout, stdout JSON, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = CLI.main(["--repo-root", str(root), *argv])
    text = out.getvalue()
    try:
        payload = json.loads(text) if text.strip() else {}
    except ValueError:
        payload = {}
    return code, text, payload, err.getvalue()


def arch_snapshot(root: Path, docs_dir: str = "bionic") -> dict[str, bytes]:
    """Every file under `<docs_dir>/arch/`, relative path to bytes."""
    arch = root / docs_dir / "arch"
    if not arch.is_dir():
        return {}
    return {p.relative_to(arch).as_posix(): p.read_bytes()
            for p in sorted(arch.rglob("*")) if p.is_file()}


def coverage(root: Path, docs_dir: str = "bionic") -> dict[str, dict]:
    """The written `coverage.json`, keyed by concern."""
    doc = json.loads((root / docs_dir / "arch" / "_meta" / "coverage.json")
                     .read_text(encoding="utf-8"))
    return {r["concern"]: r for r in doc["concerns"]}


def write(root: Path, rel: str, text: str | bytes) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


def bionic(root: Path) -> None:
    """The documentation tree every fixture derives into."""
    write(root, ".bionic.yml", 'config_version: "1"\ndocs_dir: bionic\n')
    write(root, "bionic/manifest.yml", 'schema_version: "5"\nadr:\n  next_number: 2\n')


def crux_repo(root: Path) -> None:
    """A tree the crux pack resolves, with data-model, api-surface and
    decision-index populated and module-graph populated from one module."""
    bionic(root)
    write(root, "crux/schemas/w.schema.json",
          '{\n  "title": "W",\n  "type": "object",\n'
          '  "properties": {"id": {"type": "string"}},\n  "required": ["id"]\n}\n')
    write(root, "crux/skills/zeta-skill/SKILL.md",
          "---\nname: zeta-skill\ndescription: \"Does the zeta thing.\"\n"
          "metadata:\n  tags: \"a, b\"\n---\n\n# zeta-skill\n")
    write(root, "crux/scripts/crux/__init__.py", "")
    write(root, "crux/scripts/crux/alpha.py", "from . import beta\n")
    write(root, "crux/scripts/crux/beta.py", "X = 1\n")
    write(root, "bionic/adrs/ADR-0001-fixture.md",
          "---\nid: ADR-0001\ntitle: \"Accept a thing\"\nstatus: Accepted\n"
          "date: 2026-01-02\ntags: [fixture]\n---\n\n# ADR-0001 — Accept a thing\n")


@contextlib.contextmanager
def active_ledger(root: Path, concern: str | None = "data-model"):
    """Set the input ledger and the active concern, as `_build` does, and
    reset both on exit. Yields the ledger."""
    ledger = CORE.InputLedger(Path(root))
    token = CORE._ACTIVE_LEDGER.set(ledger)
    ctoken = CORE._ACTIVE_CONCERN.set(concern)
    try:
        yield ledger
    finally:
        CORE._ACTIVE_CONCERN.reset(ctoken)
        CORE._ACTIVE_LEDGER.reset(token)


# ───────────────────────── the broad-handler rule ────────────────────────────

_BROAD = {"Exception", "BaseException"}


def _names(node) -> set[str]:
    if node is None:
        return set()
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    if isinstance(node, ast.Tuple):
        out: set[str] = set()
        for elt in node.elts:
            out |= _names(elt)
        return out
    return set()


def broad_handler_violations(source: str, label: str = "<source>") -> list[str]:
    """Every broad handler in `source` not preceded, in the same `try`, by
    `except _LANE_RAISES: raise` (IDR approach 16).

    A broad handler is a bare `except`, or one naming `Exception` or
    `BaseException` alone or inside a tuple. A `contextlib.suppress` of either
    is refused outright, because it has no place for the clause.
    """
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) or type(node).__name__ == "TryStar":
            lane_seen = False
            for handler in node.handlers:
                names = _names(handler.type)
                if "_LANE_RAISES" in names:
                    body = handler.body
                    if len(body) == 1 and isinstance(body[0], ast.Raise) and body[0].exc is None:
                        lane_seen = True
                    continue
                broad = handler.type is None or bool(names & _BROAD)
                if broad and not lane_seen:
                    found.append(f"{label}:{handler.lineno}")
        if isinstance(node, ast.Call):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else "")
            if called == "suppress" and any(_names(a) & _BROAD for a in node.args):
                found.append(f"{label}:{node.lineno}")
    return found


def pack_handler_violations(arch_pkg: Path) -> tuple[list[str], list[str]]:
    """Scan every `packs/*.py` under `arch_pkg` with `broad_handler_violations`.

    Returns the scanned module labels (`packs/<name>.py`, sorted) and every
    finding across them, so a new pack module is covered without being named.
    """
    labels: list[str] = []
    found: list[str] = []
    for path in sorted((Path(arch_pkg) / "packs").glob("*.py")):
        label = f"packs/{path.name}"
        labels.append(label)
        found.extend(broad_handler_violations(path.read_text(encoding="utf-8"), label))
    return labels, found


# ───────────────────── the per-pack positive-control cases ───────────────────


class PackLaneCases:
    """The lane cases a pack already satisfies through the core's shared
    reader and walk, before its own stream conforms its sites.

    A pack's test file mixes this into a `unittest.TestCase` and sets
    `SOURCE` (a walked source file the fixture writes) and `SUBDIR` (a walked
    directory holding a source file), and implements `build(root)`. Not a
    `TestCase` itself, so importing it runs nothing.

    Each refusing case asserts the exit code, the payload and the
    byte-unchanged arch tree, and the clean derive of the same fixture is its
    positive control.
    """

    SOURCE: str = ""
    SUBDIR: str = ""

    def build(self, root: Path) -> None:      # pragma: no cover - overridden
        raise NotImplementedError

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        bionic(self.root)
        self.build(self.root)
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.before = arch_snapshot(self.root)

    def tearDown(self):
        for path in [self.root, *self.root.rglob("*")]:
            try:
                if not path.is_symlink():
                    os.chmod(path, 0o755 if path.is_dir() else 0o644)
            except OSError:
                pass
        self._tmp.cleanup()

    def test_positive_control_the_fixture_derives_with_no_omission(self):
        for concern, rec in coverage(self.root).items():
            self.assertEqual(rec["omissions"], [], concern)
        code, _out, payload, _err = run_cli(self.root, "--dry-run")
        self.assertEqual(code, 0, payload)

    def test_a_mode_000_source_is_a_document_finding(self):
        skip_if_root(self)
        os.chmod(self.root / self.SOURCE, 0)
        for argv in ((), ("--dry-run",)):
            code, _out, payload, err = run_cli(self.root, *argv)
            self.assertEqual(code, 1, (payload, err))
            self.assertIn(self.SOURCE, [f["file"] for f in payload["validation_errors"]])
            self.assertEqual(arch_snapshot(self.root), self.before)

    def test_an_unlistable_source_directory_is_an_environment_failure(self):
        skip_if_root(self)
        os.chmod(self.root / self.SUBDIR, 0)
        for argv in ((), ("--dry-run",)):
            code, out, _payload, err = run_cli(self.root, *argv)
            self.assertEqual((code, out), (2, ""), err)
            self.assertIn(self.SUBDIR, err)
            self.assertEqual(arch_snapshot(self.root), self.before)

    def test_a_fifo_among_the_walked_sources_is_an_environment_failure(self):
        fifo = Path(self.SOURCE).with_name("trap" + Path(self.SOURCE).suffix)
        os.mkfifo(self.root / fifo)
        code, out, _payload, err = run_cli(self.root)
        self.assertEqual((code, out), (2, ""), err)
        self.assertIn(fifo.as_posix(), err)
        self.assertEqual(arch_snapshot(self.root), self.before)
