"""LLM client.

Primary: Ollama at ``$DOGFOOD_OLLAMA_URL`` (default ``http://localhost:11434``)
          using ``POST /api/generate``. Free, local, no API keys.
Fallback: deterministic rule-based completion. The agent stays useful on
          low-memory devices with no LLM at all.

Only stdlib is used so the package has zero required dependencies.
"""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable


@dataclass
class Completion:
    text: str
    used_llm: bool        # True if Ollama answered, False if rule-based
    model: str = ""
    error: str | None = None


class LLM:
    """Thin wrapper around a local Ollama daemon with a graceful fallback."""

    def __init__(self, url: str = "http://localhost:11434", model: str = "qwen3:4b", timeout: int = 120) -> None:
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    # ---- public API --------------------------------------------------------

    def complete(self, prompt: str, system: str | None = None) -> Completion:
        """Return a Completion. Tries Ollama; falls back to the rule-based planner."""
        try:
            text = self._call_ollama(prompt, system=system, stream=False)
            if text:
                return Completion(text=text, used_llm=True, model=self.model)
        except Exception as e:  # connection refused, timeout, model missing, …
            err = f"{e.__class__.__name__}: {e}"
            text = self._rule_based(prompt, system)
            return Completion(text=text, used_llm=False, model="rule-based", error=err)
        # Ollama reachable but returned empty — fall back too
        text = self._rule_based(prompt, system)
        return Completion(text=text, used_llm=False, model="rule-based", error="empty-ollama-response")

    def stream(self, prompt: str, system: str | None = None) -> Iterable[str]:
        """Yield chunks of the model's response. Falls back to a single chunk."""
        try:
            yield from self._stream_ollama(prompt, system)
        except Exception:
            yield self._rule_based(prompt, system)

    def available_models(self) -> list[str]:
        try:
            with urllib.request.urlopen(self.url + "/api/tags", timeout=2) as r:
                data = json.loads(r.read().decode("utf-8"))
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    # ---- internals ---------------------------------------------------------

    def _call_ollama(self, prompt: str, system: str | None, stream: bool) -> str:
        body = {"model": self.model, "prompt": prompt, "stream": stream}
        # qwen3 (and other "thinking" models) emit huge "thinking" blocks by
        # default that dwarf the actual answer. Disable when supported.
        if self._supports_think_option():
            body["think"] = False
        if system:
            body["system"] = system
        req = urllib.request.Request(
            self.url + "/api/generate",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            chunks = []
            for raw in r.read().decode("utf-8").splitlines():
                if not raw.strip():
                    continue
                obj = json.loads(raw)
                if obj.get("response"):
                    chunks.append(obj["response"])
                if obj.get("done"):
                    break
            return "".join(chunks).strip()

    def _stream_ollama(self, prompt: str, system: str | None) -> Iterable[str]:
        body = {"model": self.model, "prompt": prompt, "stream": True}
        if self._supports_think_option():
            body["think"] = False
        if system:
            body["system"] = system
        req = urllib.request.Request(
            self.url + "/api/generate",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            for raw in r.read().decode("utf-8").splitlines():
                if not raw.strip():
                    continue
                obj = json.loads(raw)
                piece = obj.get("response", "")
                if piece:
                    yield piece
                if obj.get("done"):
                    return

    def _supports_think_option(self) -> bool:
        # Heuristic: qwen3 family supports the `think` toggle. Keeping this
        # narrowly scoped avoids surprising other models.
        return "qwen3" in self.model.lower()

    # ---- rule-based fallback ----------------------------------------------

    @staticmethod
    def _rule_based(prompt: str, system: str | None) -> str:
        """Deterministic, no-LLM completion used when Ollama is unreachable.

        It emits a tiny JSON plan the planner can parse. Good enough for the
        self-improvement loop to keep functioning on a Raspberry Pi with no
        model loaded.
        """
        p = prompt.lower()
        # Self-improvement prompts ask the model to emit a single small JSON patch.
        if "json" in p and ("patch" in p or "edit" in p or "improve" in p):
            return json.dumps({
                "kind": "noop",
                "reason": "rule-based fallback: no edit proposed",
            })
        # Generic planner prompts: emit an empty step list to let the planner fall back too.
        return json.dumps({
            "steps": [],
            "note": "rule-based fallback: planner will use heuristic",
        })
# dogfood: reviewed
