"""`crux.llm` is `crux.core`: the LLM convenience surface under its public name.

`from crux.llm import call_model` imports this module, which binds the name to
the `crux.core` module object itself, so both names share one module and one
set of globals. The package `__init__` stays free of the import, so a script
that never calls a model never needs httpx.
"""

import sys as _sys

from . import core as _core

_sys.modules[__name__] = _core
