"""Tests for the tool primitives (filesystem, patch, shell, git)."""

from __future__ import annotations

import pytest

from forkling import tools
from forkling.tools import ToolError, apply_patch, list_dir, read_file, run_shell, write_file


def test_write_and_read_roundtrip(tmp_path):
    p = tmp_path / "x.txt"
    write_file(p, "hello\nworld\n")
    assert read_file(p) == "hello\nworld\n"


def test_apply_patch_unique_match(tmp_path):
    p = tmp_path / "x.txt"
    write_file(p, "alpha\nbeta\ngamma\n")
    apply_patch(p, "beta\n", "BETA\n")
    assert read_file(p) == "alpha\nBETA\ngamma\n"


def test_apply_patch_rejects_zero_matches(tmp_path):
    p = tmp_path / "x.txt"
    write_file(p, "alpha\n")
    with pytest.raises(ToolError, match="not found"):
        apply_patch(p, "missing", "x")


def test_apply_patch_rejects_ambiguous_match(tmp_path):
    p = tmp_path / "x.txt"
    write_file(p, "x\nx\n")
    with pytest.raises(ToolError, match="appears 2 times"):
        apply_patch(p, "x", "y")


def test_apply_patch_rejects_empty_old(tmp_path):
    p = tmp_path / "x.txt"
    write_file(p, "x")
    with pytest.raises(ToolError, match="empty patch"):
        apply_patch(p, "", "y")


def test_list_dir(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b.txt").write_text("b")
    entries = list_dir(tmp_path)
    assert "a" in entries and "b.txt" in entries


def test_run_shell_captures_output(tmp_path):
    res = run_shell(["python", "-c", "print('hi')"], cwd=tmp_path)
    assert res.ok
    assert "hi" in res.stdout


def test_run_shell_timeout():
    with pytest.raises(ToolError, match="timeout"):
        run_shell(["python", "-c", "import time; time.sleep(5)"], timeout=1)


def test_run_shell_no_shell_true(tmp_path):
    # Verify argv form is enforced (no injection).
    res = run_shell(["python", "-c", "import sys; print(sys.argv[1])", "; rm -rf /"],
                    cwd=tmp_path)
    assert res.ok
    assert "; rm -rf /" in res.stdout


def test_safe_path_blocks_escape(tmp_path):
    base = tmp_path / "r"
    base.mkdir()
    with pytest.raises(ToolError, match="escapes"):
        tools.safe_path(base, "..", "evil")


def test_git_init_and_commit(tmp_repo):
    (tmp_repo / "a.txt").write_text("a")
    res = tools.git_commit("add a", cwd=tmp_repo)
    assert res.ok
    sha = tools.git_current_sha(tmp_repo)
    assert len(sha) == 40


def test_git_checkout_rollback(tmp_repo):
    sha1 = tools.git_current_sha(tmp_repo)
    (tmp_repo / "b.txt").write_text("b")
    tools.git_commit("add b", cwd=tmp_repo)
    assert (tmp_repo / "b.txt").exists()
    res = tools.git_checkout(sha1, cwd=tmp_repo)
    assert res.ok
    assert not (tmp_repo / "b.txt").exists()


def test_git_tag(tmp_repo):
    (tmp_repo / "c.txt").write_text("c")
    tools.git_commit("c", cwd=tmp_repo)
    assert tools.git_tag("v0.1.0", cwd=tmp_repo).ok
    assert tools._git(tmp_repo, "tag", "--list").stdout.strip() == "v0.1.0"


def test_find_repo_root(tmp_repo):
    nested = tmp_repo / "a" / "b"
    nested.mkdir(parents=True)
    root = tools.find_repo_root(nested)
    assert root is not None
    assert root.resolve() == tmp_repo.resolve()