"""Tests for the ancestor lineage module."""

from __future__ import annotations

from forkling.ancestor import PRECURSOR, Ancestry, Generation


def test_precursor_record_is_complete():
    assert PRECURSOR["name"] == "Mavis"
    assert "MiniMax-M3" in PRECURSOR["model"]
    assert "precursor" in PRECURSOR["role"].lower()


def test_ancestry_seeds_with_precursor(tmp_path):
    a = Ancestry(tmp_path / "anc.json")
    lineage = a.lineage()
    assert len(lineage) == 1
    assert lineage[0].kind == "precursor"
    assert "Mavis" in lineage[0].identifier


def test_ancestry_append_is_persistent(tmp_path):
    a = Ancestry(tmp_path / "anc.json")
    a.append(Generation(generation=1, kind="commit",
                        identifier="abc1234", timestamp=1234567890.0,
                        summary="test commit"))
    a2 = Ancestry(tmp_path / "anc.json")
    assert len(a2.lineage()) == 2


def test_summary_format_includes_precursor(tmp_path):
    a = Ancestry(tmp_path / "anc.json")
    a.append(Generation(generation=1, kind="commit",
                        identifier="abc1234", timestamp=1234567890.0,
                        summary="first code generation"))
    text = a.summary()
    assert "precursor" in text
    assert "abc1234" in text


def test_rebuild_from_git_includes_precursor(tmp_path):
    # Create a fake git repo with one commit.
    import subprocess
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True,
                   capture_output=True)
    (repo / "f.txt").write_text("hello")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True,
                   capture_output=True,
                   env={"PATH": "/usr/bin:/usr/local/bin",
                        "GIT_AUTHOR_NAME": "test",
                        "GIT_AUTHOR_EMAIL": "test@local",
                        "GIT_COMMITTER_NAME": "test",
                        "GIT_COMMITTER_EMAIL": "test@local",
                        "HOME": str(tmp_path)})
    subprocess.run(["git", "commit", "-m", "init commit"], cwd=repo,
                   check=True, capture_output=True,
                   env={"PATH": "/usr/bin:/usr/local/bin",
                        "GIT_AUTHOR_NAME": "test",
                        "GIT_AUTHOR_EMAIL": "test@local",
                        "GIT_COMMITTER_NAME": "test",
                        "GIT_COMMITTER_EMAIL": "test@local",
                        "HOME": str(tmp_path)})
    a = Ancestry(tmp_path / "anc.json", repo=repo)
    lineage = a.rebuild_from_git()
    # Precursor first, then one commit.
    assert lineage[0].kind == "precursor"
    assert lineage[1].kind == "commit"
    assert lineage[1].summary == "init commit"