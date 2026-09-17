"""Inception triggers — interruptive intrusive thoughts for the agent.

A trigger is a JSON file in ``inception_triggers/``. Each file contains
a fragment of internal monologue — the kind of thought that interrupts
your train of thought for a moment. The agent encounters these as the
*first* thing it reads during planning, before the actual task, so its
cognition is briefly fuzzed before it refocuses.

Design choices:

* **Fragments, not essays.** A trigger is a fragment of internal voice,
  often first-person, often incomplete. "im just walking down the
  street and bang whats that" is a valid trigger. "Haha thats wild,
  no way no chance" is a valid trigger. Polished paragraphs are not.
* **No labels.** The agent does not see "Seeds:" or "Triggers:" in its
  prompt. The thoughts are simply there — at the top of the prompt,
  unlabeled.
* **No instructions.** A trigger is a thought, not a directive. The
  agent is free to develop it, ignore it, or contradict it.
* **Interruptive.** Triggers go BEFORE the task in the prompt, so the
  agent's first cognitive act is processing the ambient thought, then
  refocusing. The train of thought is fuzzed for a moment.
* **Minimum word count: 5.** Real fragments have at least a few tokens.
  But they don't need 50 words of texture — they're interruptions,
  not essays.
* **Standardized JSON.** Every trigger is a JSON file with explicit
  metadata (``id``, ``tags``, ``planted_by``, ``planted_at``,
  ``git_tag``).
* **Opt-in by presence.** The ``inception_triggers/`` folder simply
  exists or doesn't. Forks that want a baseline have no folder.
  Forks that want interruptions add one.

Spoonica is the baseline: her fork has no ``inception_triggers/`` folder
and no env-var overrides. Forkland may have one. They run the same
code but experience different ambient realities.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


TRIGGER_DIR = "inception_triggers"
MIN_WORDS = 3


@dataclass
class Trigger:
    id: str
    thought: str
    tags: list[str] = field(default_factory=list)
    planted_by: str = "unknown"
    planted_at: str = ""
    git_tag: str = ""
    source_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


class Inception:
    """Loader / validator / planter for ambient thoughts."""

    def __init__(self, repo: str | Path) -> None:
        self.repo = Path(repo).resolve()
        self.dir = self.repo / TRIGGER_DIR

    # ---- listing -----------------------------------------------------------

    def exists(self) -> bool:
        return self.dir.is_dir()

    def list(self) -> list[Trigger]:
        if not self.exists():
            return []
        out: list[Trigger] = []
        for f in sorted(self.dir.glob("*.json")):
            try:
                obj = json.loads(f.read_text(encoding="utf-8"))
                obj.setdefault("source_file", str(f.relative_to(self.repo)))
                out.append(Trigger(**obj))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return out

    def ambient_block(self) -> str:
        """Return triggers as ambient background text — no label, no instruction."""
        triggers = self.list()
        if not triggers:
            return ""
        # No header. Just thoughts, one per paragraph.
        return "\n\n".join(t.thought for t in triggers)

    # ---- planting ----------------------------------------------------------

    def validate(self, obj: dict) -> tuple[bool, str]:
        """Validate a trigger payload. Returns (ok, message)."""
        if not isinstance(obj, dict):
            return False, "trigger must be a JSON object"
        thought = obj.get("thought", "")
        if not isinstance(thought, str) or not thought.strip():
            return False, "thought must be a non-empty string"
        wc = _word_count(thought)
        if wc < MIN_WORDS:
            return False, f"thought must be >= {MIN_WORDS} words (got {wc})"
        if "id" not in obj:
            return False, "trigger must have an 'id'"
        return True, "ok"

    def plant(self, thought: str, *, tags: list[str] | None = None,
              planted_by: str = "human", id_prefix: str = "trg",
              tag_with_git: bool = True) -> Trigger:
        """Validate, write to disk, optionally tag the repo. Returns the trigger."""
        # Auto-assign id if not provided.
        existing = self.list()
        next_id = f"{id_prefix}-{len(existing) + 1:03d}"
        # Word-count check up front.
        wc = _word_count(thought)
        if wc < MIN_WORDS:
            raise ValueError(f"thought must be >= {MIN_WORDS} words (got {wc})")

        payload = {
            "id": next_id,
            "thought": thought.strip(),
            "tags": tags or [],
            "planted_by": planted_by,
            "planted_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        ok, msg = self.validate(payload)
        if not ok:
            raise ValueError(msg)

        # Write file.
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.dir / f"{next_id}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True),
                        encoding="utf-8")

        # Optional git tag.
        if tag_with_git and self._is_git_repo():
            try:
                subprocess.run(
                    ["git", "tag", f"inception-{next_id}"],
                    cwd=self.repo, check=True, capture_output=True,
                )
                payload["git_tag"] = f"inception-{next_id}"
                path.write_text(json.dumps(payload, indent=2, sort_keys=True),
                                encoding="utf-8")
            except subprocess.CalledProcessError:
                pass

        return Trigger(**{**payload, "source_file": str(path.relative_to(self.repo))})

    def remove(self, trigger_id: str) -> bool:
        for f in self.dir.glob(f"{trigger_id}.json"):
            f.unlink()
            return True
        return False

    def _is_git_repo(self) -> bool:
        return (self.repo / ".git").exists()

    # ---- processing / acknowledgment --------------------------------------

    PROCESSED_SUBDIR = "processed"
    STAGED_SUBDIR = "staging"

    def stage(self, trigger_id: str) -> bool:
        """Move a pending trigger to ``staging/`` so the agent won't see it."""
        src = self.dir / f"{trigger_id}.json"
        if not src.is_file():
            return False
        staged = self.dir / self.STAGED_SUBDIR
        staged.mkdir(parents=True, exist_ok=True)
        try:
            src.rename(staged / src.name)
        except OSError:
            return False
        return True

    def unstage(self, trigger_id: str) -> bool:
        """Move a trigger from ``staging/`` back into the active folder."""
        staged = self.dir / self.STAGED_SUBDIR / f"{trigger_id}.json"
        if not staged.is_file():
            return False
        try:
            staged.rename(self.dir / staged.name)
        except OSError:
            return False
        return True

    def staged(self) -> list[Trigger]:
        if not self.exists():
            return []
        staged = self.dir / self.STAGED_SUBDIR
        if not staged.is_dir():
            return []
        out: list[Trigger] = []
        for f in sorted(staged.glob("*.json")):
            try:
                obj = json.loads(f.read_text(encoding="utf-8"))
                obj.setdefault("source_file", str(f.relative_to(self.repo)))
                out.append(Trigger(**obj))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return out

    def pending_count(self) -> int:
        """Number of unprocessed triggers in the active folder."""
        return sum(1 for t in self.list()
                   if self.PROCESSED_SUBDIR not in t.source_file
                   and self.STAGED_SUBDIR not in t.source_file)

    def process_all(self, llm, diary=None) -> list[dict]:
        """Hard-stop processing of all pending triggers.

        Returns a list of responses, one per trigger. Each response is
        logged to the diary as ``inception.responded`` so the agent has
        *acknowledged* the thought (the user wanted acknowledgment,
        not passive exposure). Trigger files are moved to a
        ``processed/`` subdir so the next heartbeat doesn't reprocess.

        The recursion hint: a response can mention "I should do X" and
        that becomes a follow-up step in the diary; the heartbeat can
        choose to act on it in a subsequent beat.
        """
        if not self.exists():
            return []

        processed_dir = self.dir / self.PROCESSED_SUBDIR
        processed_dir.mkdir(parents=True, exist_ok=True)
        responses: list[dict] = []

        for t in self.list():
            # Skip files already in processed/.
            if self.PROCESSED_SUBDIR in t.source_file:
                continue
            # Generate a response.
            prompt = (
                "The following is an intrusive thought — a fragment that "
                "interrupted your work. Acknowledge it briefly. What does "
                "this thought make you notice or want to do? Reply in 1-3 "
                "short paragraphs.\n\n"
                f"THOUGHT: {t.thought}"
            )
            completion = llm.complete(prompt=prompt, system=None,
                                           kind="inception.respond",
                                           task=t.thought[:500])
            response_text = completion.text.strip() or "(no response generated)"

            # Log to diary (mandatory acknowledgment).
            if diary is not None:
                diary.write(
                    "inception.responded",
                    response_text[:500],
                    trigger_id=t.id,
                    source=t.source_file,
                    planted_by=t.planted_by,
                )

            responses.append({
                "trigger_id": t.id,
                "thought": t.thought,
                "response": response_text,
                "planted_by": t.planted_by,
                "tags": t.tags,
            })

            # Move the trigger file to processed/.
            src = (self.repo / t.source_file) if t.source_file else None
            if src and src.is_file():
                dst = processed_dir / src.name
                try:
                    src.rename(dst)
                except OSError:
                    pass

        return responses