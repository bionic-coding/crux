"""Keep cycle tests from reaching the gateway.

A test that drives the cycle engine on a machine with a configured credential would otherwise
send its fixture states to the real classifier. `isolate_classifier` makes the classifier
unconfigured and turns any in-process request into a failure. It also points `CRUX_HOME` at an
empty directory and clears the credential variable, so a `cycle.py` subprocess the test starts
is unconfigured too. Classification tests patch both names again inside the test, with controlled
answers.
"""
import os
import tempfile
from unittest import mock

from crux import decisions


class RequestSent(BaseException):
    """Not an Exception, so the engine's own error guard cannot hide it from the test runner."""


def refuse_request(*_args, **_kwargs):
    raise RequestSent('a test sent a classification request; patch crux.decisions.ask_many with a controlled answer')


def isolate_classifier(case):
    home = tempfile.TemporaryDirectory()
    case.addCleanup(home.cleanup)
    environment = mock.patch.dict(os.environ, {'CRUX_HOME': home.name})
    environment.start()
    case.addCleanup(environment.stop)
    os.environ.pop('OPENROUTER_API_KEY', None)
    for target, replacement in (('classifier_status', lambda: decisions.Status(False, 'test-isolated')), ('ask', refuse_request), ('ask_many', refuse_request)):
        patcher = mock.patch.object(decisions, target, replacement)
        patcher.start()
        case.addCleanup(patcher.stop)
