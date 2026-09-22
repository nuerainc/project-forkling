"""Configuration. All settings are env-overridable.

Keep this tiny on purpose — the agent should boot with zero config.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v is not None and v != "" else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class Config:
    repo_root: str = "."                 # working directory of the agent
    memory_dir: str = "~/.forkling"      # where persistent state lives
    ollama_url: str = "http://localhost:11434"
    # Default model chosen from the user's hardware benchmark (see
    # .forkling/model-benchmark.json): on CPU-only Ollama installs,
    # llama3.2:3b is ~10x faster than qwen3:4b with comparable output
    # quality, so it's the real default. Override per-fork with
    # FORKLING_OLLAMA_MODEL or the `--model` flag on `forkling evolve`.
    ollama_model: str = "llama3.2:3b"
    llm_timeout: int = 120               # seconds for one completion
    max_steps: int = 20                   # hard cap on plan length per run
    test_command: str = "pytest -q"      # gate that decides ship-vs-rollback
    stream: bool = True                  # stream Ollama responses
    sovereign: bool = False              # Pi-Zero mode: strip optional features

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            repo_root=_env("FORKLING_REPO", "."),
            memory_dir=_env("FORKLING_MEMORY", "~/.forkling"),
            ollama_url=_env("FORKLING_OLLAMA_URL", "http://localhost:11434"),
            ollama_model=_env("FORKLING_OLLAMA_MODEL", "llama3.2:3b"),
            llm_timeout=_env_int("FORKLING_LLM_TIMEOUT", 120),
            max_steps=_env_int("FORKLING_MAX_STEPS", 20),
            test_command=_env("FORKLING_TEST", "pytest -q"),
            stream=_env("FORKLING_STREAM", "1") not in ("0", "false", "False"),
            sovereign=_env("FORKLING_SOVEREIGN", "0") in ("1", "true", "True"),
        )