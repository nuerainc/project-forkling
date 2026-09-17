"""Tests for the LLM client. We point it at an unreachable URL so the
rule-based fallback is always exercised."""

from __future__ import annotations

import pytest

from forkling.llm import LLM


def test_falls_back_when_ollama_unreachable():
    llm = LLM(url="http://127.0.0.1:1", model="nope", timeout=2)
    c = llm.complete("hello")
    assert c.used_llm is False
    assert c.text  # some non-empty fallback


def test_available_models_is_safe_when_unreachable():
    llm = LLM(url="http://127.0.0.1:1", model="nope", timeout=1)
    assert llm.available_models() == []


def test_stream_falls_back():
    llm = LLM(url="http://127.0.0.1:1", model="nope", timeout=1)
    chunks = list(llm.stream("hi"))
    # Fallback is one chunk
    assert len(chunks) >= 1