"""Every code path that builds a council seat prompt carries the operating assumptions
and the blocker test. Builders covered:

* AsyncCouncil seat call (ad-hoc, cycle councils and run-council all pass through it)
* cycle_council.SYSTEM (consultation, idr, adr, disposition and the verify path)
* run-council.py SYSTEM_PROMPT (gate councils)
* council_native.prepare (sealed native Lite challenge and final requests, both harnesses)
* crux.council.council get_opinion and synthesize_opinions (synchronous council)
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

try:
    import httpx  # noqa: F401
    HAVE_HTTPX = True
except ImportError:
    HAVE_HTTPX = False


def _text():
    from council_assumptions import COUNCIL_OPERATING_ASSUMPTIONS
    return COUNCIL_OPERATING_ASSUMPTIONS


COMPLEXITY = "maintenance and testing cost"


class ConstantTests(unittest.TestCase):
    def test_states_assumptions_and_blocker_test(self):
        text = _text()
        for needle in ("trusted owner", "cooperating agents", "trusted local checkout",
                       "one release coordinator", "Plausible mistakes and crashes",
                       "tampering", "authentication", "plausible failure", "consequence",
                       "smallest necessary fix", "advisory", "documented limit",
                       "safety-related"):
            self.assertIn(needle, text)
        self.assertLess(len(text.split()), 160)

    def test_states_the_complexity_test_once(self):
        text = _text()
        for needle in ("adds complexity", "more code, tests, instructions, execution, configuration or concepts",
                       "concrete failure it prevents", "why a simpler fix is insufficient",
                       "maintenance and testing cost", "otherwise it is an advisory"):
            self.assertIn(needle, text)
        self.assertEqual(text.count("adds complexity"), 1)


@unittest.skipUnless(HAVE_HTTPX, "httpx not installed")
class SeatBuilderTests(unittest.TestCase):
    def _sent_systems(self, system):
        from crux.council import async_council
        council = async_council.AsyncCouncil.__new__(async_council.AsyncCouncil)
        council.config = async_council.AsyncCouncilConfig(timeout_seconds=1.0, max_retries=0)
        council._seat_models = {s: getattr(council.config, f"{s}_model")
                                for s in ("openai", "anthropic", "gemini")}
        council.available_providers = ["openai", "anthropic", "gemini"]
        council._retry = lambda fn: fn
        seen = []

        async def _post(cfg, prompt, system=None, response_format=None, attempt=None):
            seen.append(system)
            return '{"decision": "APPROVE", "confidence": 0.8, "dissents": [], "reasoning": ""}'

        council._post_seat = _post
        council.deliberate_sync("Ship?", system)
        return seen

    def test_default_system_carries_text(self):
        seen = self._sent_systems(None)
        self.assertEqual(len(seen), 3)
        for s in seen:
            self.assertIn(_text(), s)
            self.assertIn(COMPLEXITY, s)

    def test_caller_system_carries_text_once(self):
        seen = self._sent_systems("Custom reviewer.")
        for s in seen:
            self.assertTrue(s.startswith("Custom reviewer."))
            self.assertEqual(s.count(_text()), 1)

    def test_cycle_council_system(self):
        import cycle_council
        self.assertIn(_text(), cycle_council.SYSTEM)
        self.assertIn(COMPLEXITY, cycle_council.SYSTEM)

    def test_run_council_system_prompt(self):
        spec = importlib.util.spec_from_file_location("run_council_under_test", SCRIPTS / "run-council.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["run_council_under_test"] = mod
        spec.loader.exec_module(mod)
        self.assertIn(_text(), mod.SYSTEM_PROMPT)
        self.assertIn(COMPLEXITY, mod.SYSTEM_PROMPT)


class SyncCouncilTests(unittest.TestCase):
    def test_get_opinion_and_arbiter_systems(self):
        from crux.council import council
        calls = []

        def fake(model, prompt, system=None, **kw):
            calls.append((prompt, system))
            return '{"position": "p", "reasoning": "r", "confidence": 0.5, "considerations": []}'

        with patch.object(council, "call_model", fake):
            op = council.get_opinion("m", "Q?")
            council.synthesize_opinions("Q?", [op], arbiter_model="m")
        self.assertEqual(len(calls), 2)
        for prompt, system in calls:
            self.assertIn(_text(), (system or "") + prompt)
            self.assertIn(COMPLEXITY, (system or "") + prompt)


class NativeBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        docs = self.root / "bionic"
        docs.mkdir()
        (self.root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: bionic\n')
        (docs / "manifest.yml").write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (docs / "objectives.md").write_text("Use proportional review with durable history.")
        (docs / "adrs").mkdir()
        (docs / "adrs/subject.txt").write_text("Read-only proposal, exact content.")
        for a in (("init", "-q"), ("config", "user.email", "t@example.invalid"), ("config", "user.name", "T")):
            self.git(*a)
        from council_policy import initialize
        initialize(self.root, "lite", selection="Explicit test setup selects Lite")
        self.git("add", ".")
        self.git("commit", "-qm", "Initialize Lite fixture")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, check=True).stdout.decode()

    def prepare(self, harness, **kw):
        from council_native import prepare
        return prepare(self.root, "consultation", "adrs/subject.txt", "Check all five dimensions.",
                       harness=harness, author_context="/root/author", identity="fx-" + harness, **kw)

    def test_challenge_request_prompt_carries_text(self):
        out = self.prepare("codex")
        self.assertIn(_text(), out["dispatch"]["message"])
        self.assertIn(COMPLEXITY, out["dispatch"]["message"])

    def test_claude_dispatch_carries_text(self):
        out = self.prepare("claude")
        self.assertIn(_text(), out["dispatch"]["stdin"])
        self.assertIn(COMPLEXITY, out["dispatch"]["stdin"])

    def test_final_request_prompt_carries_text(self):
        from council_native import ingest
        first = self.prepare("codex")
        vote = {"decision": "REQUEST_CHANGES", "reasoning": "x", "findings": []}
        host = {"tool": first["tool"], "input": first["dispatch"], "result": {"task_name": "/root/challenger"},
                "final": "Message Type: FINAL_ANSWER\nTask name: /root\nSender: /root/challenger\nPayload:\n" + json.dumps(vote)}
        ingest(self.root, first["request"], host)
        final = self.prepare("codex", phase="final", attempt_path=first["attempt"],
                             response="Architect checked each finding; unchanged final content is justified.")
        self.assertIn(_text(), final["dispatch"]["message"])
        self.assertIn(COMPLEXITY, final["dispatch"]["message"])


if __name__ == "__main__":
    unittest.main()


class VoteInstructionTests(unittest.TestCase):
    """Cycle councils classify blocking findings by the blocker test, not by a safety tag.

    Historical promptbook gate councils keep their original instruction text."""

    LEGACY = "Any finding on Security, or that is safety-adjacent, is blocking."

    def test_historical_gate_instruction_is_unchanged(self):
        from crux.council.async_council import GATE_COUNCIL_KINDS, gate_vote_instruction
        for kind in GATE_COUNCIL_KINDS:
            self.assertIn(self.LEGACY, gate_vote_instruction(kind))

    def test_blocker_test_instruction_drops_the_safety_veto(self):
        from crux.council.async_council import GATE_COUNCIL_KINDS, gate_vote_instruction
        for kind in GATE_COUNCIL_KINDS:
            text = gate_vote_instruction(kind, blocker_test=True)
            self.assertNotIn(self.LEGACY, text)
            self.assertIn("blocker test", text)
            self.assertIn("safety_adjacent", text)

    @unittest.skipUnless(HAVE_HTTPX, "httpx required")
    def test_seat_uses_the_configured_instruction(self):
        from crux.council import async_council
        for flag in (False, True):
            council = async_council.AsyncCouncil.__new__(async_council.AsyncCouncil)
            council.config = async_council.AsyncCouncilConfig(gate=True, council_kind="adr", blocker_test=flag)
            council._council_kind = "adr"
            self.assertEqual(council._seat_instruction(True),
                             async_council.gate_vote_instruction("adr", blocker_test=flag))

    def test_cycle_councils_request_the_blocker_test(self):
        source = (SCRIPTS / "cycle_council.py").read_text()
        configs = [line for line in source.splitlines() if "AsyncCouncilConfig(gate=True" in line]
        self.assertEqual(len(configs), 2)
        for line in configs:
            self.assertIn("blocker_test=True", line)
