#!/usr/bin/env python
"""CI entry point — invoked by .github/workflows/forkling.yml.

The agent reads its own source, proposes a tiny safe change, and either
ships it (commit + tag) or rolls back. The whole thing must complete in
the configured CI timeout. Exits 0 on success or graceful noop, 1 only
on an internal failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make `forkling` importable when this script is run from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from forkling import Agent, Config, LLM, Memory, Planner, SelfImprover  # noqa: E402


def main() -> int:
    cfg = Config.from_env()
    cfg.repo_root = str(Path(__file__).resolve().parents[1])
    # In CI, only run the test subset that matters for the self-edit gate.
    cfg.test_command = "pytest -q tests/test_tools.py tests/test_memory.py tests/test_planner.py tests/test_llm.py"
    llm = LLM(url=cfg.ollama_url, model=cfg.ollama_model, timeout=cfg.llm_timeout)
    agent = Agent(cfg=cfg, llm=llm, memory=Memory(cfg.memory_dir), planner=Planner(llm))

    result = SelfImprover(agent).propose_and_apply()
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())