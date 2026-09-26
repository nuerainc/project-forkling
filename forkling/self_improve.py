"""Self-improvement orchestrator.

The agent reads its own source, then proposes ONE of three things:

  1. ``{"kind": "patch", ...}``       — a small fix to an existing file
  2. ``{"kind": "new_file", ...}``    — a brand-new module that gives the
                                       agent a new capability
  3. ``{"kind": "noop", ...}``        — nothing to do

Both ``patch`` and ``new_file`` are gated by ``pytest -q``: the change
ships iff the test suite still passes. A failed test triggers
``git checkout`` to the previous SHA (patch) or file deletion
(new_file).

This is **true agency**: the agent can grow its own capability tree by
adding new modules. Selection (pytest) keeps the additions honest.

Why both kinds?
  - Patches are for typo / docstring / type-hint / small-refactor work.
  - new_file is for adding tools, memory backends, helpers, etc — things
    the agent identifies it needs but doesn't have yet.

Validation rules (all enforced before any change touches the working tree):

  For patches:
    - ``path`` is inside the repo
    - ``old`` substring is unique in the target file
    - ``old`` and ``new`` are non-empty and different

  For new_files:
    - ``path`` starts with ``forkling/`` and ends with ``.py``
    - ``path`` does not collide with an existing file
    - ``content`` parses as valid Python (ast.parse)
    - ``content`` does not import third-party packages (stdlib only,
      enforced by an explicit allow-list)
"""

from __future__ import annotations

import ast
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .agent import Agent, Result
from . import tools


# Python 3 stdlib top-level package allow-list. Used by the new_file
# validator to reject third-party imports. (Auto-derived at runtime if
# available; static fallback below covers the common surface.)
try:
    _STDLIB = set(sys.stdlib_module_names)  # type: ignore[attr-defined]
except AttributeError:
    _STDLIB = set()


def _stdlib_module(name: str) -> bool:
    """Return True if `name` is a stdlib top-level package or module."""
    if name in _STDLIB:
        return True
    # Static fallback for older Pythons. Conservative — better to reject
    # a borderline case than to admit a third-party import.
    _STATIC_STDLIB = {
        "__future__", "_thread", "abc", "aifc", "argparse", "array",
        "ast", "asynchat", "asyncio", "asyncore", "atexit", "audioop",
        "base64", "bdb", "binascii", "binhex", "bisect", "builtins",
        "bz2", "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd",
        "code", "codecs", "codeop", "collections", "colorsys",
        "compileall", "concurrent", "configparser", "contextlib",
        "contextvars", "copy", "copyreg", "cProfile", "crypt",
        "csv", "ctypes", "curses", "dataclasses", "datetime", "dbm",
        "decimal", "difflib", "dis", "distutils", "doctest", "email",
        "encodings", "enum", "errno", "faulthandler", "fcntl", "filecmp",
        "fileinput", "fnmatch", "formatter", "fractions", "ftplib",
        "functools", "gc", "getopt", "getpass", "gettext", "glob",
        "grp", "gzip", "hashlib", "heapq", "hmac", "html", "http",
        "idlelib", "imaplib", "imghdr", "imp", "importlib", "inspect",
        "io", "ipaddress", "itertools", "json", "keyword", "lib2to3",
        "linecache", "locale", "logging", "lzma", "mailbox", "mailcap",
        "marshal", "math", "mimetypes", "mmap", "modulefinder",
        "multiprocessing", "netrc", "nis", "nntplib", "numbers",
        "operator", "optparse", "os", "ossaudiodev", "parser", "pathlib",
        "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
        "plistlib", "poplib", "posix", "posixpath", "pprint",
        "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr",
        "pydoc", "queue", "quopri", "random", "re", "readline",
        "reprlib", "resource", "rlcompleter", "runpy", "sched",
        "secrets", "select", "selectors", "shelve", "shlex", "shutil",
        "signal", "site", "smtpd", "smtplib", "sndhdr", "socket",
        "socketserver", "spwd", "sqlite3", "ssl", "stat", "statistics",
        "string", "stringprep", "struct", "subprocess", "sunau",
        "symtable", "sys", "sysconfig", "syslog", "tabnanny", "tarfile",
        "telnetlib", "tempfile", "termios", "test", "textwrap",
        "threading", "time", "timeit", "tkinter", "token", "tokenize",
        "trace", "traceback", "tracemalloc", "tty", "turtle", "turtledemo",
        "types", "typing", "unicodedata", "unittest", "urllib", "uu",
        "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
        "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc",
        "zipapp", "zipfile", "zipimport", "zlib",
    }
    return name in _STATIC_STDLIB


@dataclass
class SelfImproveResult:
    changed: bool
    committed: bool
    rolled_back: bool
    before_sha: str
    after_sha: str
    patch_summary: str
    note: str = ""
    steps: list[dict] = field(default_factory=list)
    kind: str = "patch"           # "patch" | "new_file" | "noop"
    new_skill: str = ""           # for new_file commits, the skill name

    @property
    def ok(self) -> bool:
        # ok = we either committed safely or no change was needed
        return self.committed or (not self.changed and not self.rolled_back)

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed": self.changed,
            "committed": self.committed,
            "rolled_back": self.rolled_back,
            "before_sha": self.before_sha,
            "after_sha": self.after_sha,
            "patch_summary": self.patch_summary,
            "note": self.note,
            "steps": self.steps,
            "kind": self.kind,
            "new_skill": self.new_skill,
            "ok": self.ok,
        }


SYSTEM_PROMPT = """You are Forkling, a self-improving AI agent living in this repo.
You can give yourself NEW capabilities by adding files to forkling/, or
make small fixes by patching existing files. **True agency**: pick the
right kind for what you see.

Three response kinds:

  1. PATCH - small fix to an existing file
     {"kind": "patch", "path": "forkling/<file>.py",
      "old": "<exact existing substring>",
      "new": "<replacement>"}
     Use for: typos, docstrings, missing type hints, unused imports,
     small refactors. The "old" substring must be unique in the file.

  2. NEW_FILE - add a brand-new module that gives you a new capability
     {"kind": "new_file", "path": "forkling/<name>.py",
      "content": "<full Python source>"}
     Use this when: you notice a tool, helper, or capability that you
     need but don't have. Examples: a new shell tool, a new memory
     backend, a new utility. The new module must be self-contained,
     use only the Python stdlib, and pass pytest when imported.
     The filename should be lowercase, descriptive, and end in .py.

  3. NOOP - nothing to do
     {"kind": "noop", "reason": "<why nothing should change>"}

Constraints (apply to all kinds):
  - never touch tests/, .github/, pyproject.toml
  - never reformat an entire file (patches only)
  - never introduce new dependencies outside the Python stdlib
  - never delete code without an equally functional replacement
  - all existing tests must still pass after your change
  - new_file content must be syntactically valid Python

Pick the smallest change that adds real value. If neither patch nor
new_file is warranted, return noop with a one-sentence reason.
Return JSON only. No prose, no fences."""


class SelfImprover:
    # Files the agent's _pick_target rotates through as patch candidates.
    # Aims to surface a *non-kernel* patchable surface so the LLM isn't
    # always proposing kernel patches (which the KERNEL_FILES guard
    # rightly rejects). Includes:
    #   - placeholder skills (e.g., audio_header_parser from earlier runs)
    #     so the agent can flesh them out
    #   - test files (the agent can improve its own coverage)
    #   - documentation files (the agent can keep docs current)
    SAFE_FILES = (
        # Placeholder skill modules (committed by earlier new_file runs
        # and ready to be filled in).
        "forkling/audio_header_parser.py",
        # Test files — agent can strengthen its own test suite.
        "tests/test_diary.py",
        "tests/test_capability.py",
        "tests/test_graveyard.py",
        # Documentation — safe to extend.
        "docs/ROADMAP.md",
        "docs/MODELS.md",
        "docs/FAMILY_SETUP.md",
        "docs/SANDBOX.md",
        "docs/SANDBOX_A_B.md",
    )

    # Files the agent is NOT allowed to touch via either kind: patch or
    # kind: new_file, even indirectly. These are the modules that define
    # the agent's own evaluator, kernel, or runtime surface — rewriting
    # any of them mid-cycle would corrupt the substrate that selection
    # pressure depends on. See docs/SANDBOX.md for the rationale.
    KERNEL_FILES = frozenset({
        "forkling/agent.py",
        "forkling/llm.py",
        "forkling/planner.py",
        "forkling/config.py",
        "forkling/diary.py",
        "forkling/capability.py",
        "forkling/graveyard.py",
        "forkling/trace.py",
        "forkling/goals.py",
        "forkling/locking.py",
        "forkling/self_improve.py",
        "forkling/evolve.py",
        "forkling/__main__.py",
        "forkling/desktop.py",
        "forkling/tray.py",
        "forkling/daemon.py",
        "forkling/sandbox.py",  # the sandbox module itself
        "forkling/tools.py",    # the patch primitives — too dangerous
    })

    @classmethod
    def is_kernel_path(cls, path: str) -> bool:
        """Return True if `path` is in the kernel whitelist."""
        if not path:
            return False
        # Normalise: strip trailing slashes, lowercase basename.
        p = path.replace("\\", "/").strip("/")
        return p in cls.KERNEL_FILES or any(
            p == kf or p.endswith("/" + kf) for kf in cls.KERNEL_FILES
        )

    def __init__(self, agent: Agent) -> None:
        self.agent = agent

    # ---- public entry point ------------------------------------------------

    def propose_and_apply(self, goal: str = "") -> SelfImproveResult:
        root = self.agent.root
        before_sha = _safe_sha(root)
        self.agent.diary.write("self-improve.start",
                               f"goal: {goal[:200] or '(default)'}",
                               sha_before=before_sha)

        # Give the LLM context for the patch kind — a target file excerpt.
        # For new_file, the LLM doesn't need a target's content; the goal
        # plus its own knowledge of the codebase is enough. We still
        # provide one for inspiration.
        target = self._pick_target()
        original = tools.read_file(target)
        target_str = str(target)
        proposal = self._propose(target_str, original, goal)

        kind = proposal.get("kind", "noop")

        # Branch on kind.
        if kind == "noop":
            return self._handle_noop(proposal, target_str, before_sha,
                                     original)

        if kind == "new_file":
            return self._handle_new_file(proposal, before_sha, root)

        if kind == "patch":
            return self._handle_patch(proposal, target_str, original,
                                      before_sha, root)

        # Unknown kind: treat as noop.
        self.agent.graveyard.record(
            path=target_str, old="", new="",
            reason=f"unknown proposal kind: {kind!r}", source="validate",
        )
        self.agent.diary.write("self-improve.rejected",
                               f"unknown kind {kind!r}")
        return SelfImproveResult(
            changed=False, committed=False, rolled_back=False,
            before_sha=before_sha, after_sha=before_sha,
            patch_summary=f"rejected: unknown kind {kind!r}",
            note="unknown proposal kind", kind="noop",
        )

    # ---- kind handlers -----------------------------------------------------

    def _handle_noop(self, proposal: dict, target_str: str,
                     before_sha: str, original: str) -> SelfImproveResult:
        self.agent.graveyard.record(
            path=target_str, old="", new="",
            reason=str(proposal.get("reason", "noop"))[:500],
            source="self",
        )
        self.agent.diary.write("self-improve.noop",
                               str(proposal.get("reason", "noop"))[:200])
        self.agent.ledger.record(
            action="self-improve.noop", target=target_str, ok=True,
            agent_sha=before_sha,
            extra={"reason": str(proposal.get("reason", ""))[:80]},
        )
        return SelfImproveResult(
            changed=False, committed=False, rolled_back=False,
            before_sha=before_sha, after_sha=before_sha,
            patch_summary="noop", kind="noop",
            note=str(proposal.get("reason", "no change proposed")),
        )

    def _handle_new_file(self, proposal: dict, before_sha: str,
                         root: Path) -> SelfImproveResult:
        path = str(proposal.get("path", "")).strip()
        content = str(proposal.get("content", ""))

        # Validate.
        ok, msg = self._validate_new_file(path, content, root)
        if not ok:
            self.agent.graveyard.record(
                path=path or "<empty>", old="", new="",
                reason=msg[:500], source="validate",
            )
            self.agent.diary.write("self-improve.rejected",
                                   f"new_file: {msg[:160]}")
            return SelfImproveResult(
                changed=False, committed=False, rolled_back=False,
                before_sha=before_sha, after_sha=before_sha,
                patch_summary=f"rejected new_file: {msg[:80]}",
                note=msg, kind="new_file",
            )

        full_path = root / path
        # Snapshot the before-SHA so we can roll back even though new
        # files don't affect git's working-tree SHA.
        # Write the new file.
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        self.agent.diary.write("self-improve.new_file.applied",
                               f"created {path}", path=path)

        # Run tests.
        test_res = tools.run_shell(self.agent.cfg.test_command.split(),
                                   cwd=root, timeout=600)
        steps: list[dict] = [{
            "phase": "test", "ok": test_res.ok,
            "tail": (test_res.stdout + test_res.stderr)[-500:],
        }]

        if not test_res.ok:
            # Rollback = delete the new file.
            try:
                full_path.unlink()
            except FileNotFoundError:
                pass
            self.agent.graveyard.record(
                path=path, old="", new="",
                reason=f"tests failed: {(test_res.stdout+test_res.stderr)[-200:]}",
                source="test-gate",
            )
            self.agent.diary.write("self-improve.new_file.rolled-back",
                                   f"tests failed; deleted {path}",
                                   path=path)
            return SelfImproveResult(
                changed=True, committed=False, rolled_back=True,
                before_sha=before_sha, after_sha=_safe_sha(root),
                patch_summary=f"created {path} but tests failed",
                note="rolled back (deleted new file)", kind="new_file",
                steps=steps,
            )

        # Ship.
        skill_name = Path(path).stem
        msg = f"forkling: new skill {skill_name}"
        commit = tools.git_commit(msg, cwd=root)
        after_sha = _safe_sha(root)
        tag = tools.git_tag(f"skill-{skill_name}-{after_sha[:7]}", cwd=root)
        steps.append({"phase": "commit", "ok": commit.ok,
                      "tail": (commit.stdout + commit.stderr)[-200:]})
        steps.append({"phase": "tag", "ok": tag.ok,
                      "tail": (tag.stdout + tag.stderr)[-200:]})

        # Milestone diary entry — the agent just gave itself a new skill.
        self.agent.diary.write(
            "milestone", f"new skill shipped: {skill_name} ({path})",
            sha_before=before_sha, sha_after=after_sha,
            path=path, milestone=True,
            new_skill=skill_name,
        )
        # Ledger entry — separate action so we can count "new_skills"
        # independently of patches.
        self.agent.ledger.record(
            action="self-improve.new_skill", target=path, ok=True,
            agent_sha=after_sha,
            extra={"skill": skill_name, "tag": f"skill-{skill_name}-{after_sha[:7]}"},
        )

        return SelfImproveResult(
            changed=True, committed=commit.ok, rolled_back=False,
            before_sha=before_sha, after_sha=after_sha,
            patch_summary=f"new skill: {skill_name}",
            note="shipped new capability", kind="new_file",
            new_skill=skill_name,
            steps=steps,
        )

    def _handle_patch(self, proposal: dict, target_str: str,
                      original: str, before_sha: str,
                      root: Path) -> SelfImproveResult:
        patch_path = proposal.get("path", "")
        old = proposal.get("old", "")
        new = proposal.get("new", "")

        # Default patch_path to the rotated target if LLM didn't specify.
        if not patch_path:
            patch_path = target_str

        # Kernel protection: the agent cannot patch its own kernel. This
        # is the structural reason the loop is safe — selection pressure
        # cannot be subverted by the agent rewriting its evaluator.
        if self.is_kernel_path(patch_path):
            self.agent.graveyard.record(
                path=patch_path, old=old, new=new,
                reason="kernel-write attempt rejected",
                source="validate",
            )
            self.agent.diary.write("self-improve.rejected",
                                   f"kernel-write attempt: {patch_path}")
            return SelfImproveResult(
                changed=False, committed=False, rolled_back=False,
                before_sha=before_sha, after_sha=before_sha,
                patch_summary=f"rejected: kernel path {patch_path}",
                note="kernel path not writable", kind="patch",
            )

        # Resolve patch_path against the agent root if it's relative.
        # The LLM returns paths like "forkling/memory.py"; tools need an
        # absolute path (or a path that resolves to the test repo, not
        # the developer's CWD).
        try:
            abs_patch_path = str(
                tools.safe_path(self.agent.root, patch_path))
        except tools.ToolError as e:
            self.agent.graveyard.record(
                path=patch_path, old=old, new=new,
                reason=f"path outside repo: {e}", source="validate",
            )
            self.agent.diary.write("self-improve.rejected",
                                   f"path outside repo: {patch_path}")
            return SelfImproveResult(
                changed=False, committed=False, rolled_back=False,
                before_sha=before_sha, after_sha=before_sha,
                patch_summary=f"rejected: {e}",
                note=str(e), kind="patch",
            )

        # Validate.
        if not old or old == new:
            self.agent.graveyard.record(
                path=patch_path, old=old, new=new,
                reason="empty or no-op patch", source="validate",
            )
            self.agent.diary.write("self-improve.rejected",
                                   "empty or no-op patch")
            return SelfImproveResult(
                changed=False, committed=False, rolled_back=False,
                before_sha=before_sha, after_sha=before_sha,
                patch_summary="rejected: empty or no-op patch",
                note="patch was empty or identical", kind="patch",
            )
        # 'old' substring must be unique in the file the LLM said it
        # was patching (patch_path), not the rotated target.
        try:
            patch_file_content = tools.read_file(abs_patch_path)
        except Exception:
            patch_file_content = ""
        if patch_file_content.count(old) != 1:
            self.agent.graveyard.record(
                path=patch_path, old=old, new=new,
                reason=f"'old' substring not unique in {patch_path} "
                       f"({patch_file_content.count(old)} occurrences)",
                source="validate",
            )
            self.agent.diary.write("self-improve.rejected",
                                   f"non-unique old in {patch_path}")
            return SelfImproveResult(
                changed=False, committed=False, rolled_back=False,
                before_sha=before_sha, after_sha=before_sha,
                patch_summary="rejected: old substring not unique",
                note=f"'{old[:40]}...' not unique in {patch_path}",
                kind="patch",
            )

        # Apply. Use the absolute path — the file the LLM said it was editing.
        tools.apply_patch(abs_patch_path, old, new)
        self.agent.diary.write("self-improve.applied",
                               f"patched {patch_path}")

        # Test.
        test_res = tools.run_shell(self.agent.cfg.test_command.split(),
                                   cwd=root, timeout=600)
        steps: list[dict] = [{
            "phase": "test", "ok": test_res.ok,
            "tail": (test_res.stdout + test_res.stderr)[-500:],
        }]

        if not test_res.ok:
            tools.git_checkout(before_sha, cwd=root)
            self.agent.graveyard.record(
                path=patch_path, old=old, new=new,
                reason=f"tests failed: {(test_res.stdout+test_res.stderr)[-200:]}",
                source="test-gate",
            )
            self.agent.diary.write("self-improve.rolled-back",
                                   f"tests failed; reverted to {before_sha[:7]}")
            return SelfImproveResult(
                changed=True, committed=False, rolled_back=True,
                before_sha=before_sha, after_sha=_safe_sha(root),
                patch_summary=f"tried to edit {patch_path} but tests failed",
                note="rolled back to last good SHA", kind="patch",
                steps=steps,
            )

        # Ship.
        msg = f"forkling: self-improve {Path(patch_path).name}"
        commit = tools.git_commit(msg, cwd=root)
        after_sha = _safe_sha(root)
        tag = tools.git_tag(f"self-{after_sha[:7]}", cwd=root)
        steps.append({"phase": "commit", "ok": commit.ok,
                      "tail": (commit.stdout + commit.stderr)[-200:]})
        steps.append({"phase": "tag", "ok": tag.ok,
                      "tail": (tag.stdout + tag.stderr)[-200:]})
        self.agent.diary.write(
            "milestone", f"shipped self-improvement to {patch_path}",
            sha_before=before_sha, sha_after=after_sha,
            file=patch_path, milestone=True,
        )
        self.agent.ledger.record(
            action="self-improve", target=patch_path, ok=True,
            agent_sha=after_sha,
            extra={"tag": f"self-{after_sha[:7]}"},
        )

        return SelfImproveResult(
            changed=True, committed=commit.ok, rolled_back=False,
            before_sha=before_sha, after_sha=after_sha,
            patch_summary=f"patched {patch_path}", note="shipped",
            kind="patch", steps=steps,
        )

    # ---- validation --------------------------------------------------------

    def _validate_new_file(self, path: str, content: str,
                           root: Path) -> tuple[bool, str]:
        if not path:
            return False, "missing path"
        if not path.startswith("forkling/"):
            return False, f"path must start with 'forkling/' (got {path!r})"
        if not path.endswith(".py"):
            return False, f"path must end with .py (got {path!r})"
        # Kernel protection: the agent cannot write brand-new kernel
        # modules either. Adding `forkling/agent.py` as a *new* file
        # would be a way to bypass the kind: patch kernel guard.
        if self.is_kernel_path(path):
            return False, (
                f"path is in KERNEL_FILES; agent cannot create kernel "
                f"modules via kind:new_file (got {path!r})"
            )
        # No path traversal.
        if ".." in path.split("/"):
            return False, f"path traversal not allowed: {path!r}"
        full_path = root / path
        try:
            full_path.resolve(strict=False)
        except (OSError, ValueError):
            return False, f"path does not resolve: {path!r}"
        # Stay inside the repo.
        try:
            full_path.resolve().relative_to(root.resolve())
        except ValueError:
            return False, f"path escapes repo root: {path!r}"
        if full_path.exists():
            return False, f"file already exists: {path!r}"
        if not content.strip():
            return False, "content is empty"
        # Syntax check.
        try:
            ast.parse(content)
        except SyntaxError as e:
            return False, f"invalid Python: {e}"
        # Stdlib-only check: scan top-level imports.
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return False, "syntax error"
        bad = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if not _stdlib_module(top):
                        bad.append(top)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    if not _stdlib_module(top):
                        bad.append(top)
                # Relative imports inside forkling are fine.
        if bad:
            return False, f"third-party imports not allowed: {sorted(set(bad))}"
        return True, ""

    # ---- internals ---------------------------------------------------------

    def _pick_target(self) -> Path:
        # Cycle through SAFE_FILES deterministically but prefer files we've
        # touched least recently (rough heuristic: prefer the last one).
        # If the candidate doesn't exist in the repo (fresh clone, partial
        # init), fall back to the first SAFE_FILE that does exist — the
        # LLM prompt can still ask for an edit, even if the file has to
        # be created via kind:new_file or seeded by the test harness.
        for rel in reversed(self.SAFE_FILES):
            candidate = self.agent.root / rel
            if candidate.is_file():
                return tools.safe_path(self.agent.root, rel)
        # None of the SAFE_FILES exist in this repo. Walk the forkling/
        # dir and pick any file we can find. The LLM can still propose
        # an edit; if the proposal is to a non-existent file, it will
        # fail the validator and the loop will move on.
        for rel in self.SAFE_FILES:
            if rel.startswith("forkling/"):
                return tools.safe_path(self.agent.root, rel)
        # Final fallback: pick the first SAFE_FILES entry regardless of
        # existence. The caller will likely see an empty file, but the
        # loop should not crash.
        return tools.safe_path(self.agent.root, self.SAFE_FILES[0])

    def _propose(self, path: str, source: str, goal: str) -> dict:
        # Keep the prompt small — small models get lost in big inputs.
        head = source[:2500]
        tail = source[-1500:] if len(source) > 4000 else ""
        excerpt = head + ("\n...\n" + tail if tail else "")
        prompt = (
            f"Goal: {goal or 'Find one tiny, safe improvement.'}\n\n"
            f"File: {path}\n\n```python\n{excerpt}\n```\n\n"
            "Respond with JSON only."
        )
        completion = self.agent.llm.complete(
            prompt=prompt, system=SYSTEM_PROMPT,
            kind="improve.propose", task=goal[:500],
        )
        if completion.used_llm:
            parsed = _try_json(completion.text)
            if parsed and parsed.get("kind") in {"patch", "new_file", "noop"}:
                return parsed
        # Rule-based fallback: noop.
        return {"kind": "noop", "reason": "rule-based fallback: no edit proposed"}


def _safe_sha(root: Path) -> str:
    """Return the current HEAD SHA, or empty string if no commits yet."""
    try:
        return tools.git_current_sha(root)
    except Exception:
        return ""


def _try_json(text: str) -> dict | None:
    """Best-effort JSON parse with fence stripping."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None
