"""Keep a developer's own git configuration out of execution-proof tests.

The execution proof's dirty check reads the effective core.excludesFile outside its
configuration isolation. Without this helper, a developer whose global configuration
ignores a fixture's untracked file would see that file admitted where the test
expects a refusal. `isolate_git_config` points GIT_CONFIG_GLOBAL at a test-owned file
and sets GIT_CONFIG_NOSYSTEM=1, so a host system file cannot change results either.
"""
import os
from pathlib import Path
import tempfile
from unittest import mock


def isolate_git_config(case, text=''):
    """Point GIT_CONFIG_GLOBAL at a test-owned file holding `text`; return its path."""
    home = tempfile.TemporaryDirectory()
    case.addCleanup(home.cleanup)
    path = Path(home.name).resolve() / 'gitconfig'
    path.write_text(text)
    environment = mock.patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': str(path), 'GIT_CONFIG_NOSYSTEM': '1'})
    environment.start()
    case.addCleanup(environment.stop)
    return path
