#!/usr/bin/env python3
"""Staged health check: every staged Python file compiles, and every staged script module imports.

The release path runs this against the staged artifact in each supported Python minor's locked
requirement (the registered ``staged:py<minor>:health`` check). It replaces the staged full suite for
the question "does the packaged tree load on this interpreter?"; the tests that can differ between
interpreters run in the flagged check instead.

* **Compile.** Every ``.py`` file under the root is compiled in memory with ``compile()``. A file under
  a test-data directory (``DATA_DIRECTORIES``) is skipped: those files are inputs of tests, and some are
  broken or interpreter-specific on purpose.
* **Import.** Every module under ``crux/scripts`` outside ``tests/`` is imported in a fresh process:
  ``-I -B`` flags, a temporary working directory, the staged ``crux/scripts`` as the one entry added to
  ``sys.path``, and the environment the test driver builds for its tests
  (``parallel_suite.isolated_live_environment``: ``CRUX_HOME`` replaced, live-model variables removed).
  A file whose name is not an identifier (``generate-lineage.py``) loads through
  ``importlib.util.spec_from_file_location``, so its ``__name__`` is not ``__main__`` and a
  ``__main__`` guard keeps it inert. An extractor under ``crux/scripts/extractors/`` reaches the
  dispatcher through ``sys.modules``, where ``extract-code-docs.py`` registers it before it loads an
  extractor; the child registers it the same way first. Files under ``crux/scripts/tests/`` are
  compiled, not imported.
* **No writes.** Nothing is written into the root: bytecode writing is off in this process and in each
  child, and each child runs in its own temporary directory.

A module that runs its command line at import and cannot take a ``__main__`` guard is listed in
``COMPILED_ONLY`` with its reason. It is compiled and not imported. A listed path that is not a staged
file is a finding, so the list cannot go stale.

Exit codes: ``0`` healthy, ``1`` findings (a JSON report is the last line of stdout), ``2`` the root
is not a staged tree or the driver cannot be loaded.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPTS = "crux/scripts"
# Test data: some files are broken or accepted by one interpreter only, on purpose.
DATA_DIRECTORIES = ("fixtures", "arch-corpus")
SKIPPED_PARTS = frozenset({"__pycache__", ".git", ".venv", ".cache", "node_modules", *DATA_DIRECTORIES})
# Modules compiled and not imported, each with its reason. Prefer a `__main__` guard in the module.
_SERVER_REASON = ("needs fastapi, an optional dependency (the `infrastructure` extra) that the locked "
                  "requirement leaves out")
COMPILED_ONLY: dict[str, str] = {
    "crux/scripts/crux/server/__init__.py": _SERVER_REASON,
    "crux/scripts/crux/server/crux_server.py": _SERVER_REASON,
    "crux/scripts/web-to-markdown.py": "declares its own PEP 723 dependencies (requests, beautifulsoup4, html2text), "
                                       "which are not in the locked requirement; `uv run` resolves them",
}
EXTRACTORS = SCRIPTS + "/extractors/"
TIMEOUT_SECONDS = 180
DETAIL_LIMIT = 800

_CHILD = """
import importlib, importlib.util, sys
scripts, how, name, path, dispatcher = sys.argv[1:6]
sys.path.insert(0, scripts)
if dispatcher:
    # An extractor reaches the dispatcher through sys.modules, where `load_extractor_module` registers
    # it first (crux/scripts/extract-code-docs.py). Register it the same way before the extractor loads.
    spec = importlib.util.spec_from_file_location("_health_extract_code_docs", dispatcher)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_health_extract_code_docs"] = module
    spec.loader.exec_module(module)
    sys.modules.setdefault("extract_code_docs_dispatcher", module)
if how == "import":
    importlib.import_module(name)
else:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
"""


def _driver():
    path = Path(__file__).resolve().parent / "tests" / "parallel_suite.py"
    spec = importlib.util.spec_from_file_location("_staged_health_parallel_suite", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def staged_python_files(root):
    """Repository-relative posix paths of every ``.py`` file to compile, sorted."""
    root = Path(root)
    found = []
    for path in root.rglob("*.py"):
        parts = path.relative_to(root).parts
        if SKIPPED_PARTS.intersection(parts[:-1]) or not path.is_file():
            continue
        found.append(path.relative_to(root).as_posix())
    return sorted(found)


def importable(files):
    """The script modules to import: under crux/scripts and not under tests/."""
    prefix = SCRIPTS + "/"
    return [f for f in files if f.startswith(prefix) and "tests" not in f[len(prefix):].split("/")[:-1]]


def _module_plan(relative):
    """``("import", dotted name)`` for an importable path, else ``("path", sanitized name)``."""
    inner = relative[len(SCRIPTS) + 1:-len(".py")].split("/")
    if inner[-1] == "__init__":
        inner = inner[:-1]
    if inner and all(part.isidentifier() for part in inner):
        return "import", ".".join(inner)
    return "path", "_health_" + "".join(c if c.isalnum() else "_" for c in "/".join(inner))


def _import_one(root, relative, environment):
    how, name = _module_plan(relative)
    dispatcher = str(Path(root) / SCRIPTS / "extract-code-docs.py") if relative.startswith(EXTRACTORS) else ""
    with tempfile.TemporaryDirectory(prefix="crux-health-cwd-") as cwd:
        try:
            done = subprocess.run(
                [sys.executable, "-I", "-B", "-c", _CHILD, str(Path(root) / SCRIPTS), how, name, str(Path(root) / relative),
                 dispatcher],
                cwd=cwd, env=environment, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return {"kind": "import", "path": relative, "detail": f"timed out after {TIMEOUT_SECONDS}s"}
    if done.returncode == 0:
        return None
    tail = (done.stderr.strip().splitlines() or [f"exit {done.returncode}"])[-1]
    detail = f"exit {done.returncode}: {tail}"
    return {"kind": "import", "path": relative, "detail": detail[:DETAIL_LIMIT]}


def check(root, *, compiled_only=None, workers=None):
    """Compile and import the staged tree at ``root``. Returns the report; writes nothing under ``root``."""
    root = Path(root).resolve()
    compiled_only = COMPILED_ONLY if compiled_only is None else compiled_only
    files = staged_python_files(root)
    findings = []
    for relative in files:
        try:
            compile((root / relative).read_bytes(), relative, "exec", dont_inherit=True)
        except Exception as exc:  # noqa: BLE001 - any failure to compile is the finding
            findings.append({"kind": "compile", "path": relative, "detail": f"{type(exc).__name__}: {exc}"[:DETAIL_LIMIT]})
    for relative in sorted(compiled_only):
        if relative not in files:
            findings.append({"kind": "stale-compiled-only", "path": relative, "detail": "not a staged Python file"})
    broken = {f["path"] for f in findings if f["kind"] == "compile"}
    targets = [f for f in importable(files) if f not in compiled_only and f not in broken]
    saved_flag = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # loading the driver must not write a .pyc beside it
    try:
        driver = _driver()
    finally:
        sys.dont_write_bytecode = saved_flag
    workers = workers or min(8, os.cpu_count() or 2)
    with driver.isolated_live_environment():
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda relative: _import_one(root, relative, environment), targets))
    findings += [r for r in results if r]
    findings.sort(key=lambda f: (f["path"], f["kind"]))
    return {"compiled": len(files), "imported": targets, "compiled_only": dict(sorted(compiled_only.items())),
            "findings": findings}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="staged_health.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default=".", help="the staged tree (default: the working directory)")
    parser.add_argument("--workers", type=int, default=None, help="parallel import processes (default: up to 8)")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not (root / SCRIPTS).is_dir():
        sys.stderr.write(f"staged_health: {root} has no {SCRIPTS}; run it at the root of a staged tree\n")
        return 2
    try:
        report = check(root, workers=args.workers)
    except (OSError, ImportError) as exc:
        sys.stderr.write(f"staged_health: cannot run: {type(exc).__name__}: {exc}\n")
        return 2
    print(f"staged health: compiled {report['compiled']} files, imported {len(report['imported'])} modules, "
          f"compiled-only {len(report['compiled_only'])}, findings {len(report['findings'])} "
          f"(Python {sys.version_info[0]}.{sys.version_info[1]})", flush=True)
    for finding in report["findings"]:
        print(f"  {finding['kind']}: {finding['path']}: {finding['detail']}", flush=True)
    print(json.dumps(report, sort_keys=True), flush=True)
    return 1 if report["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
