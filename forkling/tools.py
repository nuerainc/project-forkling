"""Tools the agent uses to act on the world.

All primitives here are *safe by construction*:

* file writes are atomic (write-to-temp, fsync, rename)
* patch application is exact-match + uniqueness-checked
* shell commands run with a timeout and never via ``shell=True`` for argv paths
* git operations never push, force-push, or rewrite history — they only move
  forward (``commit``, ``tag``) or jump to a previously committed SHA
  (``checkout``) so rollback is always one step away.

Stdlib only. No third-party deps.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


# ---------- filesystem -----------------------------------------------------


class ToolError(RuntimeError):
    """A tool refused to run because the request was unsafe or unfulfillable."""


def read_file(path: str | os.PathLike) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8")


def write_file(path: str | os.PathLike, content: str) -> None:
    """Atomic write: tmp file in the same dir → fsync → rename."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=".dogfood.", dir=str(p.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, p)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def list_dir(path: str | os.PathLike) -> list[str]:
    p = Path(path)
    if not p.is_dir():
        raise ToolError(f"not a directory: {p}")
    return sorted(e.name for e in p.iterdir())


def apply_patch(path: str | os.PathLike, old: str, new: str) -> bool:
    """Replace *exactly one* occurrence of ``old`` with ``new`` in ``path``.

    Returns True on success, raises ToolError otherwise. The agent uses this
    to edit its own source — uniqueness keeps patches honest.
    """
    if not old:
        raise ToolError("refusing to apply empty patch")
    text = read_file(path)
    count = text.count(old)
    if count == 0:
        raise ToolError(f"patch target not found in {path}")
    if count > 1:
        raise ToolError(
            f"patch target appears {count} times in {path}; refusing to be ambiguous"
        )
    write_file(path, text.replace(old, new, 1))
    return True


# ---------- shell ----------------------------------------------------------


@dataclass
class ShellResult:
    stdout: str
    stderr: str
    returncode: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_shell(cmd: Sequence[str], cwd: str | os.PathLike | None = None,
              timeout: int = 60, env: dict | None = None) -> ShellResult:
    """Run a command. argv form only — never ``shell=True`` — to avoid injection."""
    if not cmd or not all(isinstance(x, str) for x in cmd):
        raise ToolError("cmd must be a non-empty sequence of strings")
    try:
        cp = subprocess.run(
            list(cmd),
            cwd=str(cwd) if cwd else None,
            env={**os.environ, **(env or {})},
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as e:
        raise ToolError(f"timeout after {timeout}s: {' '.join(cmd)}") from e
    except FileNotFoundError as e:
        raise ToolError(f"command not found: {cmd[0]}") from e
    return ShellResult(stdout=cp.stdout, stderr=cp.stderr, returncode=cp.returncode)


# ---------- git -------------------------------------------------------------


def _git(cwd: str | os.PathLike | None, *args: str, timeout: int = 30,
         env: dict | None = None) -> ShellResult:
    return run_shell(("git", *args), cwd=cwd, timeout=timeout, env=env)


def git_available(cwd: str | os.PathLike | None = None) -> bool:
    return shutil.which("git") is not None


def find_repo_root(start: str | os.PathLike | None = None) -> Path | None:
    """Walk up from ``start`` looking for a ``.git`` directory."""
    p = Path(start or os.getcwd()).resolve()
    for candidate in (p, *p.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def git_status(cwd: str | os.PathLike | None = None) -> ShellResult:
    return _git(cwd, "status", "--porcelain")


def git_current_sha(cwd: str | os.PathLike | None = None) -> str:
    res = _git(cwd, "rev-parse", "HEAD")
    if not res.ok:
        raise ToolError(f"git rev-parse failed: {res.stderr.strip() or res.stdout.strip() or '(no output)'}")
    return res.stdout.strip()


def git_is_detached(cwd: str | os.PathLike | None = None) -> bool:
    """True if HEAD is detached (no current branch)."""
    res = _git(cwd, "symbolic-ref", "--quiet", "HEAD")
    return not res.ok


def git_clean(cwd: str | os.PathLike | None = None) -> tuple[bool, str]:
    """Return (clean, porcelain_output). Useful before destructive operations."""
    res = _git(cwd, "status", "--porcelain")
    return (res.ok and res.stdout.strip() == ""), res.stdout


def git_diff(cwd: str | os.PathLike | None = None, staged: bool = False) -> str:
    args = ["diff"]
    if staged:
        args.append("--staged")
    return _git(cwd, *args).stdout


def git_commit(message: str, cwd: str | os.PathLike | None = None) -> ShellResult:
    # -c user.* overrides so commits work on a fresh clone without git config.
    env = {"GIT_AUTHOR_NAME": "forkling", "GIT_AUTHOR_EMAIL": "dogfood@local",
           "GIT_COMMITTER_NAME": "forkling", "GIT_COMMITTER_EMAIL": "dogfood@local"}
    # Stage everything we might have touched.
    _git(cwd, "add", "-A", env=env)
    return _git(cwd, "commit", "-m", message, env=env)


def git_tag(tag: str, cwd: str | os.PathLike | None = None) -> ShellResult:
    return _git(cwd, "tag", tag)


def git_checkout(sha: str, cwd: str | os.PathLike | None = None) -> ShellResult:
    return _git(cwd, "checkout", "--quiet", sha)


def git_log(n: int = 5, cwd: str | os.PathLike | None = None) -> str:
    return _git(cwd, "log", f"--pretty=format:%h %s", f"-n{n}").stdout


def git_init(cwd: str | os.PathLike | None = None) -> ShellResult:
    return _git(cwd, "init", "-b", "main")


# ---------- helpers ---------------------------------------------------------


_SAFE_NAME = re.compile(r"^[A-Za-z0-9._\-/]+$")


def safe_path(root: str | os.PathLike, *parts: str) -> Path:
    """Resolve a path inside ``root`` and refuse to escape it."""
    base = Path(root).resolve()
    target = (base.joinpath(*parts)).resolve()
    try:
        target.relative_to(base)
    except ValueError as e:
        raise ToolError(f"path escapes repo root: {target}") from e
    return target