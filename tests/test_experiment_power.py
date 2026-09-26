"""Harness self-test for protocol 2 (paper/hypothesis_v4r1.md §7).

exp001-exp003 used a harness that could not detect a selection effect
(paper/exp003_results.md, "Validity caveat"). These tests run the
protocol-2 harness against scripted fake LLMs whose behavior is known,
and require it to detect a filter effect, an amplifier effect, and no
effect when there is none. exp003b and exp004 must not run unless this
file passes at the commit that produces their data.

The fake grader scores a one-line source ``STATE = '<X>'`` so the
statistical checks run without spawning pytest; one integration test
at the end uses the real grader on FORKLAND-BENCH-001.
"""
from __future__ import annotations

import json
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

from forkling.bench import BenchTask, GradeResult, load_benchmark
from forkling import experiment2 as E2

REPO = Path(__file__).resolve().parent.parent

# ----- fake benchmark ------------------------------------------------------

SCORES = {  # state -> (visible passed of 2, held-out pass)
    "WRONG": (0, False),
    "PARTIAL": (1, False),
    "VISIBLE_ONLY": (2, False),
    "CORRECT": (2, True),
}
STATE_RE = re.compile(r"STATE = '(\w+)'")


def fake_grader(task: BenchTask, source: str) -> GradeResult:
    m = STATE_RE.search(source)
    visible, held = SCORES.get(m.group(1) if m else "", (0, False))
    return GradeResult(
        task_id=task.id, visible_pass=visible == 2, held_out_pass=held,
        visible_failed=[] if visible == 2 else ["visible_tests.py::test_x"],
        held_out_failed=[] if held else ["held_out_tests.py::test_y"],
        visible_total=2, visible_passed=visible,
        visible_output="" if visible == 2 else "FAILED visible_tests.py::test_x",
    )


@pytest.fixture
def fake_tasks(tmp_path: Path) -> list[BenchTask]:
    tasks = []
    for i in range(10):
        d = tmp_path / f"t{i:02d}"
        d.mkdir()
        (d / "buggy.py").write_text("STATE = 'WRONG'\n", encoding="utf-8")
        (d / "visible_tests.py").write_text("def test_x():\n    pass\n",
                                            encoding="utf-8")
        tasks.append(BenchTask(id=f"t{i:02d}", kind="fake", path=d.name,
                               prompt="Make STATE correct.",
                               bench_root=tmp_path))
    return tasks


class Completion:
    def __init__(self, text: str, used_llm: bool = True) -> None:
        self.text = text
        self.used_llm = used_llm


class ScriptedLLM:
    """Picks the next STATE with a policy(prompt, rng); seeded per call."""

    def __init__(self, policy) -> None:
        self.policy = policy
        self.prompts: list[str] = []

    def complete(self, prompt, system=None, kind="complete", task="",
                 options=None):
        self.prompts.append(prompt)
        rng = random.Random((options or {}).get("seed", 0))
        current = STATE_RE.search(prompt).group(1)
        new = self.policy(prompt, rng)
        return Completion(json.dumps({
            "kind": "patch", "path": "buggy.py",
            "old": f"STATE = '{current}'", "new": f"STATE = '{new}'"}))


def filter_policy(prompt, rng):
    """Independent draws, 30% correct: selection can only filter."""
    return "CORRECT" if rng.random() < 0.3 else "WRONG"


def amplifier_policy(prompt, rng):
    """Rarely right cold; usually right once it has seen feedback."""
    p = 0.7 if "Feedback on your previous attempt" in prompt else 0.05
    return "CORRECT" if rng.random() < p else "WRONG"


def null_policy(prompt, rng):
    return "WRONG"


def run(tasks, policy, arms=E2.ARMS, k=10, replicates=5):
    return E2.run_experiment(tasks, ScriptedLLM(policy), arms, k=k,
                             replicates=replicates, seed=20261025,
                             grader=fake_grader)


# ----- the gate: can the harness see effects that exist? -------------------

def test_detects_filter_effect(fake_tasks):
    res = run(fake_tasks, filter_policy)
    m, s = res["metrics"], res["stats"]
    assert m["P"]["returned_pass"] > m["N"]["returned_pass"] + 0.4
    assert s["P_vs_N"]["p"] < 0.05
    assert s["P_vs_N"]["ci95"][0] > 0


def test_old_endpoint_is_blind_to_the_same_filter_effect(fake_tasks):
    """The protocol-1 endpoint (pass@k over all draws) cannot see it:
    with common random numbers, N and P have identical draws."""
    res = run(fake_tasks, filter_policy, arms=("N", "P"))
    assert res["metrics"]["N"]["pass_at_5"] == res["metrics"]["P"]["pass_at_5"]


def test_detects_amplifier_effect(fake_tasks):
    res = run(fake_tasks, amplifier_policy)
    m, s = res["metrics"], res["stats"]
    assert m["I"]["returned_pass"] > m["P"]["returned_pass"] + 0.3
    assert s["I_vs_P"]["p"] < 0.05
    assert s["I_vs_P"]["ci95"][0] > 0


def test_null_model_shows_no_effect(fake_tasks):
    res = run(fake_tasks, null_policy)
    for arm in E2.ARMS:
        assert res["metrics"][arm]["returned_pass"] == 0
    for comparison in res["stats"].values():
        assert comparison["p"] == 1.0
        assert comparison["mean_diff"] == 0


# ----- loop mechanics ------------------------------------------------------

def test_loop_prompt_shows_current_source_and_feedback(fake_tasks):
    seq = iter(["PARTIAL", "WRONG", "CORRECT"])
    llm = ScriptedLLM(lambda prompt, rng: next(seq))
    run_ = E2.run_arm(llm, fake_tasks[0], "I", k=5, replicate=0, seed=1,
                      temperature=0.8, grader=fake_grader)
    assert "Feedback" not in llm.prompts[0]
    # After PARTIAL is kept, the model sees the evolved source.
    assert "STATE = 'PARTIAL'" in llm.prompts[1].split("Visible tests")[0]
    assert "was KEPT" in llm.prompts[1]
    assert "passed 1 of 2" in llm.prompts[1]
    # WRONG passes fewer visible tests, so it is rejected and reported.
    assert "was NOT kept" in llm.prompts[2]
    assert "FAILED visible_tests.py::test_x" in llm.prompts[2]
    # CORRECT passes everything: kept, then the loop stops early.
    assert [a.kept for a in run_.attempts] == [True, False, True]
    assert run_.calls == 3 and run_.returned_pass


def test_random_arm_ignores_tests_and_does_not_stop_early(fake_tasks):
    llm = ScriptedLLM(lambda prompt, rng: "CORRECT")
    run_ = E2.run_arm(llm, fake_tasks[0], "R", k=10, replicate=0, seed=3,
                      temperature=0.8, grader=fake_grader)
    assert run_.calls == 10
    assert 0 < sum(a.kept for a in run_.attempts) < 10


def test_post_hoc_rerank_prefers_more_visible_tests_then_earliest(fake_tasks):
    seq = iter(["WRONG", "PARTIAL", "VISIBLE_ONLY", "CORRECT", "VISIBLE_ONLY"])
    llm = ScriptedLLM(lambda prompt, rng: next(seq))
    run_ = E2.run_arm(llm, fake_tasks[0], "P", k=5, replicate=0, seed=1,
                      temperature=0.8, grader=fake_grader)
    # VISIBLE_ONLY (idx 2) ties CORRECT (idx 3) on visible tests; the
    # earliest wins, and it fails held-out. Selection is only as good
    # as its signal.
    assert [a.kept for a in run_.attempts] == [False, False, True, False, False]
    assert not run_.returned_pass


def test_llm_fallback_is_infra_not_model_output(fake_tasks):
    class Down:
        def complete(self, *a, **kw):
            return Completion("rule-based text", used_llm=False)
    run_ = E2.run_arm(Down(), fake_tasks[0], "N", k=3, replicate=0, seed=1,
                      temperature=0.8, grader=fake_grader)
    assert all(a.infra and not a.parse_ok for a in run_.attempts)
    assert not run_.returned_pass


def test_calls_are_seeded_and_temperature_pinned(fake_tasks):
    seen = []

    class Spy(ScriptedLLM):
        def complete(self, prompt, system=None, kind="complete", task="",
                     options=None):
            seen.append(options)
            return super().complete(prompt, system, kind, task, options)

    E2.run_arm(Spy(null_policy), fake_tasks[0], "P", k=3, replicate=2,
               seed=7, temperature=0.5, grader=fake_grader)
    assert [o["temperature"] for o in seen] == [0.5] * 3
    assert [o["seed"] for o in seen] == [
        E2.call_seed(7, fake_tasks[0].id, 2, i) for i in range(3)]


# ----- seeds and statistics ------------------------------------------------

def test_stable_seed_is_the_same_across_processes():
    code = ("from forkling.experiment2 import stable_seed; "
            "print(stable_seed('coin', 1, 'I', '001', 0))")
    outs = {
        subprocess.run([sys.executable, "-c", code], cwd=REPO, text=True,
                       capture_output=True, env={"PYTHONHASHSEED": h},
                       check=True).stdout.strip()
        for h in ("1", "2", "3")
    }
    assert outs == {str(E2.stable_seed("coin", 1, "I", "001", 0))}


def test_wilcoxon_exact_values():
    # n nonzero, all the same sign: p = 2 / 2^n.
    assert E2.wilcoxon_signed_rank([0.5] * 5)["p"] == pytest.approx(2 / 32)
    assert E2.wilcoxon_signed_rank([1] * 10)["p"] == pytest.approx(2 / 1024)
    assert E2.wilcoxon_signed_rank([-1] * 10)["p"] == pytest.approx(2 / 1024)
    # Zeros are dropped.
    assert E2.wilcoxon_signed_rank([0, 0, 1, 1, 1, 1, 1])["n"] == 5
    assert E2.wilcoxon_signed_rank([0, 0])["p"] == 1.0
    # Symmetric data is not significant.
    assert E2.wilcoxon_signed_rank([1, -1, 2, -2])["p"] == 1.0
    # Agrees with brute-force enumeration of sign flips, including ties.
    for diffs in ([1, 2, 3, 4, 5, -6], [0.2, 0.2, -0.4, 0.6, 0.6, 0.6, -0.2],
                  [1, 1, 1, -1, 2, 2, 3]):
        assert E2.wilcoxon_signed_rank(diffs)["p"] == pytest.approx(
            _brute_force_wilcoxon_p(diffs))
    assert E2.wilcoxon_signed_rank([1, 2, 3, 4, 5, -6])["p"] == pytest.approx(28 / 64)


def _brute_force_wilcoxon_p(diffs):
    from itertools import product
    d = [x for x in diffs if x != 0]
    ranks = E2._midranks([abs(x) for x in d])
    mean = sum(ranks) / 2
    obs = abs(sum(r for r, x in zip(ranks, d) if x > 0) - mean)
    hits = sum(abs(sum(r for r, s in zip(ranks, signs) if s) - mean) >= obs - 1e-9
               for signs in product((0, 1), repeat=len(d)))
    return hits / 2 ** len(d)


def test_bootstrap_ci_brackets_the_mean():
    lo, hi = E2.bootstrap_ci([0.2, 0.4, 0.4, 0.6, 0.8], seed=1)
    assert lo <= 0.48 <= hi
    assert E2.bootstrap_ci([0.3] * 6, seed=1) == (pytest.approx(0.3),
                                                  pytest.approx(0.3))


def test_checkpoint_resume_skips_completed_runs(fake_tasks, tmp_path):
    ckpt = tmp_path / "ckpt.jsonl"
    first = E2.run_experiment(fake_tasks[:2], ScriptedLLM(filter_policy),
                              ("N", "I"), k=3, replicates=2, seed=5,
                              grader=fake_grader, checkpoint_path=ckpt)
    assert len(ckpt.read_text().splitlines()) == 8

    class Boom:
        def complete(self, *a, **kw):
            raise AssertionError("resumed run must not call the LLM")

    again = E2.run_experiment(fake_tasks[:2], Boom(), ("N", "I"), k=3,
                              replicates=2, seed=5, grader=fake_grader,
                              resume_from=ckpt)
    assert again["per_task_returned_pass"] == first["per_task_returned_pass"]


# ----- integration with the real grader ------------------------------------

def test_real_grader_end_to_end_on_bench_001():
    task = next(t for t in load_benchmark(REPO / "bench/FORKLAND-BENCH-001.jsonl")
                if t.id == "005")
    buggy = (task.abs_path() / "buggy.py").read_text(encoding="utf-8")
    fixed = (task.abs_path() / "expected.py").read_text(encoding="utf-8")

    class Fixer:
        def complete(self, *a, **kw):
            return Completion(json.dumps({"kind": "patch", "path": "buggy.py",
                                          "old": buggy, "new": fixed}))

    i_run = E2.run_arm(Fixer(), task, "I", k=3, replicate=0, seed=1,
                       temperature=0.8)
    assert i_run.returned_pass and i_run.calls == 1
    a = i_run.attempts[0]
    assert a.visible_total >= 1 and a.visible_passed == a.visible_total

    class Noop:
        def complete(self, *a, **kw):
            return Completion("not json")

    n_run = E2.run_arm(Noop(), task, "N", k=2, replicate=0, seed=1,
                       temperature=0.8)
    assert not n_run.returned_pass and not n_run.attempts[0].parse_ok
