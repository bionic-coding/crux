"""input_lanes.py — which lane a regenerator's failed read of an input takes.

The vendored regenerators share an exit convention with two lanes. The DOCUMENT
lane is exit 1 with a non-empty `validation_errors` payload on stdout naming
each input and its reason; `check-drift` reads it as "the named input must be
repaired first". The ENVIRONMENT lane is exit 2 with nothing on stdout and a
message on stderr; `check-drift` reads it as an environment failure.

A failed read of a recognizable input file takes the document lane when its
cause is attributable to the file's path, because the repair is at that path:
a permission refusal, an overlong name, a file listed and then absent at open,
a directory where the file was expected, a symbolic-link loop, or content that
is not valid UTF-8.[^file] Every other cause — descriptor or memory exhaustion,
a device I/O error, any errno outside that closed list — is a fact about the
process or host and takes the environment lane, naming the file.[^process]

A directory the regenerator must list is absent only when a `stat` of it fails
with ENOENT or ENOTDIR, never because a predicate such as `is_dir()` returned
False.[^absence] A directory that exists and cannot be listed, or whose
existence cannot be determined, takes the environment lane and is never read
as empty.[^unlistable]

A REGULAR FILE WHERE AN INPUT DIRECTORY IS EXPECTED. Its `stat` succeeds, so it
is not confirmed absent, and listing it fails with ENOTDIR. This module reads
it as the unlistable-directory case: the environment lane, naming the path.
The other reading, confirmed absence, would turn a misplaced file into an
empty input tier, so this module does not take it. ENOTDIR from the `stat`
itself, raised because an ANCESTOR is not a directory, stays confirmed
absence.

A run that meets an environment-lane failure takes that lane, and its stderr
names every document-lane finding the same run met.[^precedence]

Stdlib only.

[^file]: rule:path-attributable-read-failure-is-a-document-finding
[^process]: rule:process-level-read-failure-is-an-environment-failure
[^absence]: rule:absence-is-confirmed-by-enoent-or-enotdir
[^unlistable]: rule:unlistable-input-directory-is-an-environment-failure
[^precedence]: rule:environment-failure-takes-precedence
"""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path

#: The closed list of errno values attributable to the path being read.
PATH_ATTRIBUTABLE_ERRNOS = frozenset({
    errno.EACCES,
    errno.EPERM,
    errno.ENAMETOOLONG,
    errno.ENOENT,
    errno.ENOTDIR,
    errno.EISDIR,
    errno.ELOOP,
})

#: The errno values that confirm a path is absent.
ABSENCE_ERRNOS = frozenset({errno.ENOENT, errno.ENOTDIR})


def is_path_attributable(exc: BaseException) -> bool:
    """True when a failed read of a recognizable file takes the document lane."""
    if isinstance(exc, UnicodeDecodeError):
        return True
    if isinstance(exc, OSError):
        return exc.errno in PATH_ATTRIBUTABLE_ERRNOS
    return False


def _errno_name(exc: OSError) -> str:
    return errno.errorcode.get(exc.errno, str(exc.errno)) if exc.errno is not None else "no errno"


def document_reason(exc: BaseException) -> str:
    """The `validation_errors` reason for a document-lane read failure.

    The text tells a permission repair from a re-encoding and from an absent
    target, and carries no absolute path: the `file` key beside it names the
    input relative to the repository.
    """
    if isinstance(exc, UnicodeDecodeError):
        return (f"is not valid UTF-8 (byte {exc.start}: {exc.reason}) — re-encode the "
                "file as UTF-8")
    assert isinstance(exc, OSError), exc
    name = _errno_name(exc)
    detail = exc.strerror or str(exc)
    if exc.errno == errno.ENOENT:
        return (f"was listed but could not be opened ({name}: {detail}) — a dangling "
                "symbolic link, or a file removed during the run; restore the target "
                "or remove the entry")
    if exc.errno in (errno.EACCES, errno.EPERM):
        return (f"could not be read ({name}: {detail}) — grant this process read "
                "permission on the file")
    return f"could not be read ({name}: {detail})"


def environment_reason(path: str, exc: BaseException) -> str:
    """The stderr text for an environment-lane failure on `path`."""
    return f"{path}: {type(exc).__name__}: {exc}"


class EnvironmentLaneError(Exception):
    """A run met at least one environment-lane failure.

    `failures` holds one stderr line per environment-lane failure. `findings`
    holds every document-lane `{"file", "error"}` finding the same run met;
    the caller names them on stderr beside the failures, never on stdout.
    """

    def __init__(self, failures: list[str], findings: list[dict] | None = None) -> None:
        super().__init__("; ".join(failures))
        self.failures = list(failures)
        self.findings = list(findings or [])


def emit_environment_failure(exc: EnvironmentLaneError, script: str, err) -> int:
    """Write the environment-lane stderr message and return 2. Stdout stays empty."""
    lines = [f"{script}: environment failure: {f}" for f in exc.failures]
    lines += [f"{script}: document finding met in the same run: {e['file']}: {e['error']}"
              for e in exc.findings]
    err.write("\n".join(lines) + "\n")
    return 2


def directory_exists(path: Path) -> bool:
    """Whether the input directory `path` is present, by the operating system's answer.

    Returns False only when `stat` fails with ENOENT or ENOTDIR. Returns True
    for a directory. Raises `OSError` naming `path` for every other failure to
    stat it, and `NotADirectoryError` naming `path` when it exists and is not
    a directory: both are the unlistable-directory case.
    """
    try:
        st = os.stat(path)
    except OSError as exc:
        if exc.errno in ABSENCE_ERRNOS:
            return False
        raise
    if not stat.S_ISDIR(st.st_mode):
        raise NotADirectoryError(
            errno.ENOTDIR,
            "exists and is not a directory, so it cannot be listed as an input directory",
            str(path))
    return True


def path_state(path, follow: bool = True) -> os.stat_result | None:
    """The `stat` result for `path`, or None when its absence is confirmed.

    Absence is confirmed only when `os.stat` (`os.lstat` when `follow` is
    False) fails with ENOENT or ENOTDIR.[^absence] Every other failure is
    re-raised for the caller to classify with `is_path_attributable`. A
    predicate such as `is_file()` cannot stand in for this: it answers False
    for a path the process cannot stat, and that is not an absent path.
    """
    try:
        return os.stat(path) if follow else os.lstat(path)
    except OSError as exc:
        if exc.errno in ABSENCE_ERRNOS:
            return None
        raise


def list_directory(path) -> list[str]:
    """Every entry name in the directory `path`, sorted, hidden names included.

    Hidden names stay in the listing because `Path.glob('*')`, which this
    replaces, also returns names that begin with '.'. A caller whose input
    policy excludes them filters them itself.

    A listing that fails raises `OSError` naming `path`; this never returns an
    empty list for a directory it could not list.[^unlistable] Decide the
    directory's presence with `directory_exists` before calling this.
    """
    try:
        with os.scandir(path) as entries:
            return sorted(entry.name for entry in entries)
    except OSError as exc:
        if exc.filename is None:
            raise type(exc)(exc.errno, exc.strerror or str(exc), str(path)) from exc
        raise


#: The `validation_errors` reason for each kind of confirmed-absent input.
_ABSENT_REASONS = {
    "file": "is a required input and is absent — restore the file at this path",
    "member": ("is a catalogue member and is absent — restore the file at this path, "
               "or remove the member from its catalogue"),
}


def absent_reason(kind: str) -> str:
    """The `validation_errors` reason for a confirmed-absent required input.

    `kind` is "file" for a required file named by path and "member" for a
    catalogue member. The text names the absence and its repair, and carries
    no absolute path: the `file` key beside it names the input.
    """
    try:
        return _ABSENT_REASONS[kind]
    except KeyError:
        raise ValueError(f"unknown absent-input kind {kind!r}; "
                         f"expected one of {sorted(_ABSENT_REASONS)}") from None


def output_reason(exc: BaseException) -> str:
    """The `validation_errors` reason for a path-attributable failed read of an output.

    The output is wholly generated, so removing it and rerunning the
    regenerator repairs it as well as the repair `document_reason` names.
    """
    return (document_reason(exc) + "; or remove the path and rerun the regenerator, "
            "which recreates this wholly generated output")
