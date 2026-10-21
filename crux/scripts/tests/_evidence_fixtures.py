"""Shared fixtures for the evidence engine tests: lock projects, bare venvs, resealed receipts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import venv

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import test_evidence as te  # noqa: E402

PYPROJECT = '''[project]
name = "fixture-project"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["dep-a==1.0", "dep-b==2.0 ; python_full_version < '3.14'", "dep-c==3.0 ; python_full_version >= '3.14'"]
'''
LOCK = '''version = 1
revision = 3
requires-python = ">=3.13"

[[package]]
name = "dep-a"
version = "1.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "dep-b"
version = "2.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "dep-c"
version = "3.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "fixture-project"
version = "0.1.0"
source = { virtual = "." }
dependencies = [
    { name = "dep-a" },
    { name = "dep-b", marker = "python_full_version < '3.14'" },
    { name = "dep-c", marker = "python_full_version >= '3.14'" },
]

[package.metadata]
requires-dist = [
    { name = "dep-a", specifier = "==1.0" },
    { name = "dep-b", marker = "python_full_version < '3.14'", specifier = "==2.0" },
    { name = "dep-c", marker = "python_full_version >= '3.14'", specifier = "==3.0" },
]
'''
EMPTY_PYPROJECT = '[project]\nname = "empty-project"\nversion = "0.2.0"\nrequires-python = ">=3.13"\ndependencies = []\n'
EMPTY_LOCK = '''version = 1
revision = 3
requires-python = ">=3.13"

[[package]]
name = "empty-project"
version = "0.2.0"
source = { virtual = "." }
'''
MINOR = f"{sys.version_info[0]}.{sys.version_info[1]}"
# The packages the fixture lock exports for this interpreter's minor.
CONDITIONAL = ("dep-b", "2.0") if sys.version_info < (3, 14) else ("dep-c", "3.0")


def write_lock_project(root, empty=False):
    root = Path(root)
    (root / "pyproject.toml").write_text(EMPTY_PYPROJECT if empty else PYPROJECT)
    (root / "uv.lock").write_text(EMPTY_LOCK if empty else LOCK)


def make_venv(parent, name, dists=()):
    """An unseeded venv (no pip) holding exactly the distributions named; returns its interpreter."""
    directory = Path(parent) / name
    venv.EnvBuilder(with_pip=False, symlinks=True).create(directory)
    python = directory / "bin" / "python"
    site = Path(subprocess.check_output([str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"], text=True).strip())
    for dist_name, version in dists:
        info = site / f"{dist_name.replace('-', '_')}-{version}.dist-info"
        info.mkdir()
        (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {dist_name}\nVersion: {version}\n")
    return python


def lock_requirement(project=False, **extra):
    requirement = {"interpreter": {"implementation": "cpython", "minors": [MINOR]},
                   "packages": {"lock": {"source": "subject", "project": project}}, "isolated": not project}
    requirement.update(extra)
    return requirement


def conditional_dists(project=False):
    dists = [("dep-a", "1.0"), CONDITIONAL]
    if project:
        dists.append(("fixture-project", "0.1.0"))
    return dists


def raw_receipt(store, evidence_id):
    return json.loads((Path(store) / f"{evidence_id}.json").read_text())


def variant(store, evidence_id, mutate, *, new_log=None):
    """Write a resealed copy of a receipt, with ``mutate(record)`` applied, under a fresh id.

    Test-only: it builds the hard-to-reach states (a version-1 receipt, a pass with no identity, a
    set behavior variable) that no honest execution produces. Returns the new record.
    """
    store = Path(store)
    record = raw_receipt(store, evidence_id)
    record.pop("record_sha256")
    old_log = store / record["output"]
    new_id = "TE-" + os.urandom(16).hex()
    record["id"] = new_id
    record["output"] = new_id + ".log"
    # A later finish time makes the newest variant the one lookup decides on.
    record["finished_at"] = max(json.loads(p.read_text())["finished_at"] for p in store.glob("TE-*.json")) + 1
    if old_log.exists():
        (store / record["output"]).write_bytes(old_log.read_bytes() if new_log is None else new_log)
    mutate(record)
    record["record_sha256"] = te.digest(record)
    (store / f"{new_id}.json").write_text(json.dumps(record, indent=2))
    return record


def reseal_in_place(store, evidence_id, mutate):
    path = Path(store) / f"{evidence_id}.json"
    record = json.loads(path.read_text())
    record.pop("record_sha256")
    mutate(record)
    record["record_sha256"] = te.digest(record)
    path.write_text(json.dumps(record, indent=2))
    return record
