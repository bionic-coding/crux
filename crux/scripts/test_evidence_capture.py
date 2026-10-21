"""Record the executing interpreter's identity, then run a check entry as a direct invocation would.

Usage, by absolute path, so no repository module is ever imported here:

    <python> /abs/test_evidence_capture.py IDENTITY_FILE [--variables A,B] -- ENTRY [ARGS...]

ENTRY is a script path, ``-m MODULE`` or ``-c CODE``. The wrapper is stdlib-only and imports
no repository module. It removes its own directory from ``sys.path`` before any other import,
so the repository modules beside it are never importable by accident. It then sets
``sys.path[0]``, ``sys.argv`` and ``__main__`` as ``python ENTRY ARGS`` would: ``runpy.run_path``
for a script, ``runpy.run_module`` with ``alter_sys`` for ``-m``. A module that the stage lacks
therefore fails here exactly as it fails under a direct invocation, whether or not the
development checkout has a module of that name.

Before it runs the entry the wrapper writes IDENTITY_FILE (outside the stage and the checkout):
implementation, full version, the PEP 508 marker environment, ``sys.prefix``, ``sys.flags``,
``sys.warnoptions``, ``sys._xoptions``, the filesystem and preferred encodings, the distribution
list, and a digest of each allowlisted variable. A digest covers the normalized value, with the
repository root (the working directory), ``sys.prefix`` and the uv cache root replaced by fixed
tokens. No value is stored. The engine refuses to record a pass without this file.
"""
import os
import sys

# Remove the entry Python inserted for this script's directory before any other import, so a
# repository module beside this file never resolves by accident. Python inserts it as sys.path[0];
# a later entry equal to this directory (a staged PYTHONPATH value) is the caller's and stays.
_HERE = os.path.dirname(os.path.realpath(__file__))
if sys.path and os.path.realpath(sys.path[0] or ".") == _HERE:
    del sys.path[0]

import hashlib  # noqa: E402
import importlib.metadata  # noqa: E402
import json  # noqa: E402
import locale  # noqa: E402
import platform  # noqa: E402
import re  # noqa: E402
import runpy  # noqa: E402
import types  # noqa: E402

# The interpreter behavior set. Each name can change what an interpreter does without any file
# in the repository changing, so a name here must be unset unless the check registers it.
BEHAVIOR_VARIABLES = (
    "PYTHONPATH", "PYTHONHOME", "PYTHONPLATLIBDIR", "PYTHONSAFEPATH", "PYTHONNOUSERSITE",
    "PYTHONSTARTUP", "PYTHONHASHSEED", "PYTHONOPTIMIZE", "PYTHONWARNINGS", "PYTHONUTF8",
    "PYTHONIOENCODING", "PYTHONDEVMODE",
)


def _normalized_name(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def _implementation_version():
    info = sys.implementation.version
    text = "%d.%d.%d" % (info.major, info.minor, info.micro)
    return text if info.releaselevel == "final" else text + info.releaselevel[0] + str(info.serial)


def marker_environment():
    version = platform.python_version()
    return {
        "implementation_name": sys.implementation.name,
        "implementation_version": _implementation_version(),
        "os_name": os.name,
        "platform_machine": platform.machine(),
        "platform_python_implementation": platform.python_implementation(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python_full_version": version,
        "python_version": ".".join(version.split(".")[:2]),
        "sys_platform": sys.platform,
    }


def _uv_cache_root():
    explicit = os.environ.get("UV_CACHE_DIR")
    if explicit:
        return explicit
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "uv")


def _tokens():
    pairs = []
    for raw, token in ((os.getcwd(), "${REPOSITORY}"), (sys.prefix, "${PYTHON_ENV}"),
                       (_uv_cache_root(), "${UV_CACHE}")):
        for form in {raw, os.path.realpath(raw)}:
            if form:
                pairs.append((form, token))
    return sorted(pairs, key=lambda pair: -len(pair[0]))


def variable_digests(names):
    tokens = _tokens()
    digests = {}
    for name in sorted(set(names)):
        value = os.environ.get(name)
        if value is None:
            digests[name] = None
            continue
        for form, token in tokens:
            value = value.replace(form, token)
        digests[name] = hashlib.sha256(value.encode("utf-8", "surrogateescape")).hexdigest()
    return digests


def _flags():
    names = [n for n in dir(sys.flags) if not n.startswith("_")
             and n not in ("count", "index", "n_fields", "n_sequence_fields", "n_unnamed_fields")]
    return {n: getattr(sys.flags, n) for n in names}


def identity(variables):
    distributions = sorted({(_normalized_name(d.metadata["Name"] or ""), d.version or "")
                            for d in importlib.metadata.distributions()})
    return {
        "format": 1,
        "implementation": sys.implementation.name,
        "version": platform.python_version(),
        "version_info": list(sys.version_info[:3]),
        "marker_environment": marker_environment(),
        "sys_prefix": sys.prefix,
        "sys_flags": _flags(),
        "warnoptions": list(sys.warnoptions),
        "xoptions": {str(k): str(v) for k, v in sorted(getattr(sys, "_xoptions", {}).items())},
        "filesystem_encoding": sys.getfilesystemencoding(),
        "preferred_encoding": locale.getpreferredencoding(False),
        "distributions": [list(d) for d in distributions],
        "variables": variable_digests([*BEHAVIOR_VARIABLES, *variables]),
    }


def write_identity(path, variables):
    record = identity(variables)
    temporary = "%s.%d.tmp" % (path, os.getpid())
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(record, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _run_entry(entry):
    if not entry:
        sys.stderr.write("test_evidence_capture: no entry after --\n")
        raise SystemExit(2)
    if entry[0] == "-m":
        if len(entry) < 2:
            sys.stderr.write("test_evidence_capture: -m needs a module name\n")
            raise SystemExit(2)
        sys.path.insert(0, os.getcwd())
        sys.argv = [entry[1], *entry[2:]]
        runpy.run_module(entry[1], run_name="__main__", alter_sys=True)
    elif entry[0] == "-c":
        if len(entry) < 2:
            sys.stderr.write("test_evidence_capture: -c needs code\n")
            raise SystemExit(2)
        sys.path.insert(0, "")
        sys.argv = ["-c", *entry[2:]]
        main = types.ModuleType("__main__")
        sys.modules["__main__"] = main
        exec(compile(entry[1], "<string>", "exec"), main.__dict__)
    else:
        script = entry[0]
        sys.path.insert(0, os.path.dirname(os.path.realpath(script)))
        sys.argv = [script, *entry[1:]]
        runpy.run_path(script, run_name="__main__")


def main(argv):
    if "--" not in argv or len(argv) < 3:
        sys.stderr.write("usage: test_evidence_capture.py IDENTITY_FILE [--variables A,B] -- ENTRY [ARGS...]\n")
        return 2
    split = argv.index("--")
    head, entry = argv[:split], argv[split + 1:]
    variables = []
    if head[1:2] == ["--variables"] and len(head) == 3:
        variables = [name for name in head[2].split(",") if name]
    elif len(head) != 1:
        sys.stderr.write("usage: test_evidence_capture.py IDENTITY_FILE [--variables A,B] -- ENTRY [ARGS...]\n")
        return 2
    write_identity(head[0], variables)
    _run_entry(entry)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
