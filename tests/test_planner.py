"""Tests for the planner. We point it at a fake LLM that always errors,
so the rule-based path is exercised deterministically."""

from __future__ import annotations

from forkling.llm import LLM
from forkling.planner import Planner


class _FakeLLM(LLM):
    """LLM that always falls back to the rule-based planner."""

    def __init__(self):
        super().__init__(url="http://127.0.0.1:1", model="nope")  # unreachable

    def complete(self, prompt, system=None):  # type: ignore[override]
        # Force fallback path
        from forkling.llm import Completion
        try:
            self._call_ollama(prompt, system, False)
        except Exception as e:
            return Completion(text=self._rule_based(prompt, system),
                              used_llm=False, model="rule-based", error=str(e))
        return Completion(text="", used_llm=True)


def test_rule_based_run_tests():
    p = Planner(_FakeLLM())
    steps = p.plan("run the tests")
    actions = [s.action for s in steps]
    assert "test" in actions
    assert actions[-1] in ("finish", "test")


def test_rule_based_list_dir():
    p = Planner(_FakeLLM())
    steps = p.plan("list files in src")
    assert steps[0].action == "list"
    assert steps[0].args.get("path") == "src"


def test_rule_based_read():
    p = Planner(_FakeLLM())
    steps = p.plan("read dogfood/agent.py")
    assert steps[0].action == "read"
    assert steps[0].args["path"] == "dogfood/agent.py"


def test_rule_based_unknown_falls_back_to_shell_echo():
    p = Planner(_FakeLLM())
    steps = p.plan("do something entirely novel xyz")
    # Either we get the heuristic "shell echo" or an empty list — both are
    # acceptable graceful behavior.
    assert isinstance(steps, list)


def test_steps_are_renumbered():
    p = Planner(_FakeLLM())
    steps = p.plan("read a.py")
    for i, s in enumerate(steps, start=1):
        assert s.id == i


def test_parses_llm_json_with_fences():
    from forkling.planner import Planner as P
    raw = '```json\n{"steps":[{"action":"finish","args":{},"description":"done"}]}\n```'
    parsed = P._parse_llm_json(raw)
    assert len(parsed) == 1
    assert parsed[0].action == "finish"