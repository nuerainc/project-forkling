"""forkling — the absolute MVP of a self-contained, self-improving AI agent.

Public surface:
    Agent         — the Plan→Act→Reflect loop
    Planner       — task → ordered steps
    LLM           — Ollama client with rule-based fallback
    Memory        — tiny JSON-backed persistent state
    tools         — filesystem / shell / git / patch primitives
    SelfImprover  — gated self-edit orchestrator
"""

from .agent import Agent, Result
from .config import Config
from .llm import LLM
from .memory import Memory
from .planner import Planner, Step
from .self_improve import SelfImprover

__version__ = "0.1.0"
__all__ = [
    "Agent",
    "Result",
    "Config",
    "LLM",
    "Memory",
    "Planner",
    "Step",
    "SelfImprover",
]