"""Tests for the inception processing flow (hard-stop acknowledgment)."""

from __future__ import annotations

from forkling.diary import Diary
from forkling.inception import Inception
from forkling.llm import LLM


class _FakeLLM:
    def __init__(self):
        self.calls = []

    def complete(self, prompt, system=None, kind="complete", task=""):
        from forkling.llm import Completion
        self.calls.append(prompt)  # keep the full prompt
        return Completion(text="I noticed this. I'll keep going.",
                         used_llm=False, model="fake")


def test_pending_count_zero_when_no_folder(tmp_path):
    inc = Inception(tmp_path)
    assert inc.pending_count() == 0


def test_pending_count_excludes_processed(tmp_path):
    inc = Inception(tmp_path)
    inc.plant("im just walking down the street and bang whats that",
              planted_by="test")
    inc.plant("wait what was that over there", planted_by="test")
    assert inc.pending_count() == 2
    # Move one to processed/.
    (tmp_path / "inception_triggers" / "processed").mkdir(exist_ok=True)
    (tmp_path / "inception_triggers" / "trg-001.json").rename(
        tmp_path / "inception_triggers" / "processed" / "trg-001.json"
    )
    assert inc.pending_count() == 1


def test_process_all_moves_files_to_processed(tmp_path):
    inc = Inception(tmp_path)
    inc.plant("im just walking down the street and bang whats that",
              planted_by="Jeremy")
    diary = Diary(tmp_path / "diary.jsonl")
    llm = _FakeLLM()
    responses = inc.process_all(llm, diary=diary)
    assert len(responses) == 1
    assert responses[0]["trigger_id"] == "trg-001"
    # File moved to processed/.
    processed = list((tmp_path / "inception_triggers" / "processed").glob("*.json"))
    assert len(processed) == 1
    assert processed[0].name == "trg-001.json"


def test_process_all_logs_to_diary(tmp_path):
    inc = Inception(tmp_path)
    inc.plant("haha thats wild no way no chance", planted_by="Jeremy")
    diary = Diary(tmp_path / "diary.jsonl")
    llm = _FakeLLM()
    responses = inc.process_all(llm, diary=diary)
    kinds = [e["kind"] for e in diary.entries()]
    assert "inception.responded" in kinds
    # The response from the LLM is recorded.
    responded = diary.by_kind("inception.responded")
    assert len(responded) == 1
    assert responded[0].get("trigger_id") == "trg-001"


def test_process_all_no_triggers_is_noop(tmp_path):
    inc = Inception(tmp_path)
    diary = Diary(tmp_path / "diary.jsonl")
    llm = _FakeLLM()
    responses = inc.process_all(llm, diary=diary)
    assert responses == []
    assert diary.entries() == []


def test_process_all_handles_already_processed(tmp_path):
    inc = Inception(tmp_path)
    inc.plant("im just walking down the street and bang whats that",
              planted_by="Jeremy")
    diary = Diary(tmp_path / "diary.jsonl")
    llm = _FakeLLM()
    # First pass: process.
    inc.process_all(llm, diary=diary)
    # Second pass: nothing to process.
    responses2 = inc.process_all(llm, diary=diary)
    assert responses2 == []


def test_response_is_brief_acknowledgment(tmp_path):
    inc = Inception(tmp_path)
    inc.plant("wait what was that over there", planted_by="test")
    diary = Diary(tmp_path / "diary.jsonl")
    llm = _FakeLLM()
    inc.process_all(llm, diary=diary)
    # The LLM was called with the thought included in the prompt.
    assert any("wait what was that" in c for c in llm.calls)


def test_real_ollama_call_via_complete(tmp_path):
    """If Ollama is reachable, process_all works end-to-end. Marked xfail-ish."""
    import socket
    try:
        s = socket.create_connection(("localhost", 11434), timeout=1)
        s.close()
    except OSError:
        return  # Ollama not running; skip.
    inc = Inception(tmp_path)
    inc.plant("haha thats wild no way no chance", planted_by="test")
    diary = Diary(tmp_path / "diary.jsonl")
    llm = LLM(url="http://localhost:11434", model="qwen3:4b", timeout=120)
    responses = inc.process_all(llm, diary=diary)
    # If Ollama is reachable, we should get an actual response.
    assert len(responses) == 1
    assert responses[0]["response"] != "(no response generated)"