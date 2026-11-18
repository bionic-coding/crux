"""Every PEP 723 script under crux/scripts runs in its own declared environment.

A consumer runs a shipped script by absolute path with `uv run`, and uv builds the
script's environment from its inline `# /// script` block alone. The dev `.venv`
carries httpx and an editable `.pth`, so a dev-venv pass proves nothing about that
environment. In 6.0.0 the rule-handle collision check reached `survey_sheet`, which
imports `crux.arch.recover`; the `crux` package `__init__` then imported the council
and the LLM caller, so `decision-policy.py propose` and `adr-precouncil.py rules`
died with `ModuleNotFoundError: No module named 'httpx'` while `--help` still worked.

`--help` alone cannot see that class, because the failing import sits inside a
function. This test therefore runs one child per script, from an empty directory,
with `uv run --isolated --no-project` on a harness that carries the script's own
inline block. The child runs the script's `--help` when it parses arguments, then
imports every in-tree module the script can reach and every third-party module
those modules import. The reach is a static walk of the import statements,
function bodies included, plus the sibling `.py` files a module loads by path.
Imports guarded by an `ImportError` handler or `TYPE_CHECKING` are optional and
skipped. The walk over-approximates: a module the script never imports on any
real path still counts, so the declared dependencies cover every path.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]  # crux/scripts

# Variables that could put the dev venv's site-packages on the child's import path.
_LEAK_VARS = ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", "UV_PROJECT_ENVIRONMENT")

_BLOCK_RE = re.compile(r"(?m)^# /// script\s*$\n((?:^#.*$\n)*?)^# ///\s*$")
_PY_LITERAL_RE = re.compile(r"^[A-Za-z0-9_.-]+\.py$")
_OPTIONAL_HANDLERS = {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}

# A `*.py` literal that names a file the module reads as text and never imports.
# Each entry is (reader, named file) relative to crux/scripts, with the reason.
_READ_NOT_IMPORTED = {
    ("visualize-run-progress.py", "run-council.py"):
        "parses run-council.py source with ast to read the council gate; never imports it",
}


def inline_block(text: str) -> str | None:
    """The script's `# /// script` block, delimiters included, or None."""
    match = _BLOCK_RE.search(text)
    return match.group(0) if match else None


def pep723_scripts() -> list[Path]:
    found = []
    for path in sorted(SCRIPTS.rglob("*.py")):
        rel = path.relative_to(SCRIPTS)
        if rel.parts[0] == "tests" or "__pycache__" in rel.parts:
            continue
        if inline_block(path.read_text(encoding="utf-8")) is not None:
            found.append(path)
    return found


def module_index() -> dict[str, Path]:
    """Dotted import name -> file, for every importable module under crux/scripts."""
    index: dict[str, Path] = {}
    for path in SCRIPTS.rglob("*.py"):
        rel = path.relative_to(SCRIPTS)
        if rel.parts[0] == "tests" or "__pycache__" in rel.parts:
            continue
        parts = list(rel.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if parts and all(p.isidentifier() for p in parts):
            index[".".join(parts)] = path
    return index


def _dotted_name(path: Path) -> str | None:
    parts = list(path.relative_to(SCRIPTS).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts and all(p.isidentifier() for p in parts) else None


def _is_optional(handlers) -> bool:
    for handler in handlers:
        names = []
        if handler.type is None:
            return True
        nodes = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
        for node in nodes:
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
        if _OPTIONAL_HANDLERS.intersection(names):
            return True
    return False


class _Imports(ast.NodeVisitor):
    """Collect required imports and `*.py` literals, skipping optional imports."""

    def __init__(self):
        self.imports: list[tuple[str, int, list[str]]] = []  # (module, level, names)
        self.literals: set[str] = set()
        self._optional = 0

    def visit_Try(self, node):
        optional = _is_optional(node.handlers)
        self._optional += optional
        for stmt in node.body:
            self.visit(stmt)
        self._optional -= optional
        for part in (*node.handlers, *node.orelse, *node.finalbody):
            self.visit(part)

    visit_TryStar = visit_Try

    def visit_If(self, node):
        test = node.test
        guarded = (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
            isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")
        if guarded:
            for stmt in node.orelse:
                self.visit(stmt)
            return
        self.generic_visit(node)

    def visit_Import(self, node):
        if not self._optional:
            for alias in node.names:
                self.imports.append((alias.name, 0, []))

    def visit_ImportFrom(self, node):
        if not self._optional:
            self.imports.append((node.module or "", node.level, [a.name for a in node.names]))

    def visit_Constant(self, node):
        if isinstance(node.value, str) and _PY_LITERAL_RE.match(node.value):
            self.literals.add(node.value)


def reach(script: Path, index: dict[str, Path]) -> tuple[set[Path], set[str]]:
    """The in-tree files and the third-party top-level modules `script` can import."""
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    tops = {name.split(".")[0] for name in index}
    files: set[Path] = set()
    third: set[str] = set()
    pending = [script]
    while pending:
        path = pending.pop()
        if path in files:
            continue
        files.add(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = _Imports()
        visitor.visit(tree)
        own = _dotted_name(path)
        package = own if path.name == "__init__.py" else (own.rpartition(".")[0] if own else "")

        def add(name: str) -> None:
            parts = name.split(".")
            for i in range(1, len(parts) + 1):
                target = index.get(".".join(parts[:i]))
                if target is not None:
                    pending.append(target)

        for module, level, names in visitor.imports:
            if level:
                base = package.split(".") if package else []
                if level > 1:
                    base = base[: len(base) - (level - 1)]
                full = ".".join([*base, *([module] if module else [])])
            else:
                full = module
            top = full.split(".")[0]
            if not level and top not in tops:
                if top not in stdlib:
                    third.add(top)
                continue
            add(full)
            for name in names:
                if f"{full}.{name}" in index:
                    add(f"{full}.{name}")
        for literal in visitor.literals:
            if (str(path.relative_to(SCRIPTS)), literal) in _READ_NOT_IMPORTED:
                continue
            for candidate in (path.parent / literal, SCRIPTS / literal):
                if candidate.is_file() and "tests" not in candidate.relative_to(SCRIPTS).parts:
                    pending.append(candidate)
                    break
    return files, third


_HARNESS = '''
import importlib, importlib.util, io, json, runpy, sys, contextlib
SCRIPTS = {scripts!r}
SCRIPT = {script!r}
RUN_HELP = {run_help!r}
MODULES = {modules!r}
FILES = {files!r}
sys.path.insert(0, SCRIPTS)
failures = []
if RUN_HELP:
    argv, sys.argv = sys.argv, [SCRIPT, "--help"]
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            runpy.run_path(SCRIPT, run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (0, None):
            failures.append([SCRIPT + " --help", "exit " + repr(exc.code)])
    except BaseException as exc:
        failures.append([SCRIPT + " --help", type(exc).__name__ + ": " + str(exc)])
    sys.argv = argv
for name in MODULES:
    try:
        importlib.import_module(name)
    except BaseException as exc:
        failures.append([name, type(exc).__name__ + ": " + str(exc)])
for i, path in enumerate(FILES):
    try:
        spec = importlib.util.spec_from_file_location("_isolated_probe_%d" % i, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except BaseException as exc:
        failures.append([path, type(exc).__name__ + ": " + str(exc)])
print("ISOLATED-RESULT " + json.dumps(failures))
'''


def harness_source(script: Path, index: dict[str, Path]) -> str:
    text = script.read_text(encoding="utf-8")
    files, third = reach(script, index)
    by_file = {path: name for name, path in index.items()}
    modules = sorted({by_file[p] for p in files if p in by_file} | third)
    loose = sorted(str(p) for p in files if p not in by_file and p != script)
    body = _HARNESS.format(
        scripts=str(SCRIPTS), script=str(script), run_help="argparse" in text,
        modules=modules, files=loose)
    return inline_block(text) + body


def run_isolated(script: Path, index: dict[str, Path]) -> tuple[Path, list, str]:
    """Run `script`'s harness in its own isolated environment from an empty directory."""
    env = {k: v for k, v in os.environ.items() if k not in _LEAK_VARS}
    with tempfile.TemporaryDirectory() as scratch:
        harness = Path(scratch) / "harness.py"
        harness.write_text(harness_source(script, index), encoding="utf-8")
        empty = Path(scratch) / "empty"
        empty.mkdir()
        proc = subprocess.run(
            ["uv", "run", "--isolated", "--no-project", "--quiet", str(harness)],
            cwd=empty, env=env, capture_output=True, text=True, timeout=600)
    for line in proc.stdout.splitlines():
        if line.startswith("ISOLATED-RESULT "):
            return script, json.loads(line[len("ISOLATED-RESULT "):]), ""
    return script, [], f"exit {proc.returncode}\n{proc.stderr[-2000:]}"


class ReachTests(unittest.TestCase):
    """The static walk itself: the positive control for the isolated run below."""

    def test_reach_follows_function_level_and_path_loaded_imports(self):
        index = module_index()
        files, _third = reach(SCRIPTS / "decision-policy.py", index)
        names = {p.name for p in files}
        # decision_policy imports summaries_projection inside a function, and
        # summaries_projection imports survey_sheet inside a function.
        self.assertIn("summaries_projection.py", names)
        self.assertIn("survey_sheet.py", names)
        self.assertIn(SCRIPTS / "crux" / "arch" / "recover.py", files)
        # summaries_projection loads untrusted.py by path.
        self.assertIn("untrusted.py", names)

    def test_reach_skips_optional_imports(self):
        tree = ast.parse("try:\n    import tomli\nexcept ImportError:\n    tomli = None\n"
                         "if TYPE_CHECKING:\n    import httpx\nimport yaml\n")
        visitor = _Imports()
        visitor.visit(tree)
        self.assertEqual([m for m, _, _ in visitor.imports], ["yaml"])


@unittest.skipUnless(shutil.which("uv"), "uv not on PATH — skip (not pass)")
class IsolatedEnvironmentTests(unittest.TestCase):
    def test_every_inline_script_imports_its_reach_in_its_own_environment(self):
        index = module_index()
        scripts = pep723_scripts()
        self.assertGreater(len(scripts), 50, "the PEP 723 script discovery found too few scripts")
        with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as pool:
            results = list(pool.map(lambda s: run_isolated(s, index), scripts))
        problems = []
        for script, failures, error in results:
            rel = script.relative_to(SCRIPTS)
            if error:
                problems.append(f"{rel}: the isolated child did not report: {error}")
            for target, message in failures:
                problems.append(f"{rel}: {target}: {message}")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_isolated_child_lacks_the_dev_venv(self):
        """Guard against a vacuous pass: a script declaring no dependencies
        cannot import httpx in the child this test builds."""
        probe = SCRIPTS / "crux-config.py"
        self.assertIn("dependencies = []", inline_block(probe.read_text(encoding="utf-8")))
        env = {k: v for k, v in os.environ.items() if k not in _LEAK_VARS}
        with tempfile.TemporaryDirectory() as scratch:
            harness = Path(scratch) / "probe.py"
            harness.write_text(inline_block(probe.read_text(encoding="utf-8"))
                               + "\nimport importlib.util, sys\n"
                               "sys.exit(0 if importlib.util.find_spec('httpx') is None else 3)\n",
                               encoding="utf-8")
            proc = subprocess.run(["uv", "run", "--isolated", "--no-project", "--quiet", str(harness)],
                                  cwd=scratch, env=env, capture_output=True, text=True, timeout=600)
        self.assertEqual(proc.returncode, 0, f"httpx leaked into the isolated child:\n{proc.stderr}")


if __name__ == "__main__":
    unittest.main()
