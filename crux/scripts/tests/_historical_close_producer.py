"""Fixture producer for historical-format migration closes and witnesses. Test support only.

Historical-format migration writes are retired: `advance-run.py --migration-batch` refuses with
`historical-migration-writes-retired`. The read path still verifies a close already recorded in
a run and a publication already committed, and its tests need such records. This module
records them with the production close code, so a fixture never differs from a close the
retired command wrote:

* `close` calls advance-run's private `_advance` in process with the migration selector,
  the same body `main` ran after parsing. It takes parsed values, never `sys.argv`, and it
  performs no process-wide `chdir`.
* `publication_witness` writes `<batch_id>.application.json` beside the batch with
  `implementation_migration._publication_locator_bytes`, the formatter the retired writer used.
* `assert_close_admitted` and `assert_publication_admitted` make a template build fail, not
  pass falsely, when the production readers do not admit what was recorded.

Documented limit: this producer reaches the production close code without passing the refusal
in `main`. That is acceptable only because a deliberate private call is outside the project's
operating assumptions (a trusted owner, cooperating agents, one trusted checkout). The producer
lives in `crux/scripts/tests` and is named by no template, skill or instruction. No environment
variable, flag or patched guard bypasses the refusal in any production entry point. A
`SystemExit` that advance-run's `_fail` raises is caught and reported as a fixture build
failure, so a refused close can never read as a recorded one.

This file is a helper, not a test module: unittest discovery matches `test*.py` only.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import os
import subprocess
import sys
from pathlib import Path

import _council_gate_support as sup

_MODULE = None


class FixtureBuildFailure(AssertionError):
    """The production close code refused or failed while building a fixture."""

    def __init__(self, message, output=""):
        super().__init__(message)
        self.output = output


def _advance_run():
    """advance-run.py loaded once per process as a module; never executed as `__main__`."""
    global _MODULE
    if _MODULE is None:
        spec = importlib.util.spec_from_file_location("_historical_close_advance_run",
                                                      sup.SCRIPTS / "advance-run.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _MODULE = module
    return _MODULE


def close(run_path, book_path, artifacts, batch):
    """Record the migration close of `batch` in the run at its declared gate prompt.

    `artifacts` is the comma-separated artifact string the command took. Returns advance-run's
    JSON report text. Raises FixtureBuildFailure on any refusal or fault."""
    import council_records
    import git_read_cache
    module = _advance_run()
    arguments = argparse.Namespace(run=str(run_path), outcome="done", result="", artifacts=artifacts,
        abandon=False, reason="", book=str(book_path), gate_info=False, prompt=None,
        implementation_revision=None, migration_batch=str(batch))
    out, err = io.StringIO(), io.StringIO()
    # The retired command ran in a child with git-redirecting variables removed; do the same,
    # restoring them afterwards.
    removed = {name: os.environ.pop(name) for name in council_records.GIT_REDIRECT_VARS if name in os.environ}
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), git_read_cache.scope():
            status = module._advance(arguments)
    except SystemExit as exc:
        raise FixtureBuildFailure("production close refused: %s" % (out.getvalue() + err.getvalue()).strip(),
                                  out.getvalue() + err.getvalue()) from exc
    finally:
        os.environ.update(removed)
    if status != 0:
        raise FixtureBuildFailure("production close returned %r: %s" % (status, out.getvalue() + err.getvalue()),
                                  out.getvalue() + err.getvalue())
    return out.getvalue()


def publication_witness(root, proof, run_rel, batch_path, batch_id):
    """Write the witness the retired writer published, beside the batch; the caller commits it."""
    import implementation_migration as migration
    witness = Path(root) / Path(batch_path).with_name(batch_id + ".application.json")
    witness.write_bytes(migration._publication_locator_bytes(proof, run_rel))
    return witness


def assert_close_admitted(root, run_path, *, slot, batch_path, batch_sha256):
    """The production verifier admits the recorded close; returns its proof."""
    import implementation_migration as migration
    proof = migration.ap.validate_historical_migration_binding(root, run_path, slot=slot,
        batch_path=batch_path, batch_sha256=batch_sha256)
    if proof.binding["batch"] != {"path": batch_path, "sha256": batch_sha256}:
        raise FixtureBuildFailure("the verifier admitted a different batch than the fixture closed")
    return proof


def assert_publication_admitted(root):
    """The authority view reads the committed publication; returns the view."""
    import implementation_migration as migration
    view = migration.authority_view(root)
    if view["state"] != "published":
        raise FixtureBuildFailure("the authority view does not admit the fixture publication: %r"
                                  % (view["state"],))
    return view


def tree_bytes(root):
    """Every entry under `root`, `.git` refs, index and objects included, by relative path.

    A regular file maps to its sha256, a symlink to its target, a directory to None. Two equal
    results mean the tree is byte-identical, so a refusal that wrote, staged or committed
    anything cannot equal the tree it started from."""
    root = Path(root)
    found = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            found[rel] = ("link", os.readlink(path))
        elif path.is_dir():
            found[rel] = ("dir", None)
        elif path.is_file():
            found[rel] = ("file", hashlib.sha256(path.read_bytes()).hexdigest())
    return found


def script(name, *args, home):
    """A crux script as a child process.

    It holds no provider credential: `CRUX_HOME` is `home`, an empty directory. No variable
    that redirects its repository reads and writes to another repository reaches it."""
    env = sup.scrubbed_env()
    env["CRUX_HOME"] = str(home)
    return subprocess.run([sys.executable, str(sup.SCRIPTS / name), *args], capture_output=True,
                          text=True, env=env)
