"""Tests for keeping repository outputs out of git with a managed exclude block (INS-9)."""

import subprocess
lazy from pathlib import Path

import pytest

from lantoki.app import Selection, Workspace, run_scope
from lantoki.gitexclude import BEGIN, END, Git, merge, render_block
from lantoki.sources import Scope


GIT = ["git", "-c", "user.email=test@example.com", "-c", "user.name=test"]


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run([*GIT, "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return completed.stdout


def _block_lines(repo: Path) -> list[str]:
    text = (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    lines = text.splitlines()
    if BEGIN not in lines:
        return []
    return lines[lines.index(BEGIN) + 1 : lines.index(END)]


@pytest.fixture
def git_repo(repo: Path) -> Path:
    """Turn the empty target repository into a git repository."""
    _git(repo, "init", "-q")
    return repo


def test_given_paths_when_rendering_then_block_is_sorted_anchored_and_unique() -> None:
    block = render_block(["b/c", "a.md", "a.md"])

    assert block == f"{BEGIN}\n/a.md\n/b/c\n{END}\n"


def test_given_no_paths_when_rendering_then_block_is_empty() -> None:
    assert not render_block([])


def test_given_foreign_lines_when_merging_then_they_are_kept_and_block_replaced() -> None:
    existing = f"*.log\n{BEGIN}\n/old\n{END}\nbuild/"

    merged = merge(existing, render_block(["new"]))

    assert merged == f"*.log\nbuild/\n{BEGIN}\n/new\n{END}\n"


def test_given_empty_block_when_merging_then_block_is_removed() -> None:
    assert merge(f"*.log\n{BEGIN}\n/old\n{END}\n", "") == "*.log\n"


def test_given_git_repo_when_syncing_repo_then_every_file_target_is_excluded(
    acme_workspace: Workspace,
    git_repo: Path,
) -> None:
    outcome = run_scope(acme_workspace, Scope.PROJECT, git_repo, selection=Selection.ALL, apply=True)

    assert outcome.ok
    assert "/ACME.md" in _block_lines(git_repo)
    assert "/.acme/skills/lint" in _block_lines(git_repo)
    assert not _git(git_repo, "status", "--porcelain")


def test_given_deselected_source_when_syncing_repo_then_its_target_leaves_the_block(
    acme_workspace: Workspace,
    git_repo: Path,
) -> None:
    run_scope(acme_workspace, Scope.PROJECT, git_repo, selection=Selection.ALL, apply=True)

    run_scope(
        acme_workspace,
        Scope.PROJECT,
        git_repo,
        selection=Selection.ASK,
        ask=lambda source: source.key != "instruction:airflow",
        apply=True,
    )

    assert "/.acme/rules/airflow.md" not in _block_lines(git_repo)
    assert "/.acme/rules/python.md" in _block_lines(git_repo)


def test_given_nothing_selected_when_syncing_repo_then_no_block_and_foreign_lines_kept(
    acme_workspace: Workspace,
    git_repo: Path,
) -> None:
    exclude = git_repo / ".git" / "info" / "exclude"
    exclude.write_text("*.log\n", encoding="utf-8")
    run_scope(acme_workspace, Scope.PROJECT, git_repo, selection=Selection.ALL, apply=True)

    run_scope(acme_workspace, Scope.PROJECT, git_repo, selection=Selection.ASK, ask=lambda _: False, apply=True)

    assert exclude.read_text(encoding="utf-8") == "*.log\n"


def test_given_project_file_tracked_on_a_target_when_planning_then_it_is_reported_and_not_excluded(
    acme_workspace: Workspace,
    git_repo: Path,
) -> None:
    (git_repo / "ACME.md").write_text("Our own instructions.\n", encoding="utf-8")
    _git(git_repo, "add", "ACME.md")

    planned = run_scope(acme_workspace, Scope.PROJECT, git_repo, selection=Selection.ALL)
    run_scope(acme_workspace, Scope.PROJECT, git_repo, selection=Selection.ALL, apply=True)

    assert any(warning.startswith("ACME.md is tracked by git") for warning in planned.warnings)
    assert "/ACME.md" not in _block_lines(git_repo)


def test_given_installed_target_later_committed_when_syncing_then_it_is_reported_and_leaves_the_block(
    acme_workspace: Workspace,
    git_repo: Path,
) -> None:
    run_scope(acme_workspace, Scope.PROJECT, git_repo, selection=Selection.ALL, apply=True)
    _git(git_repo, "add", "--force", "ACME.md")

    synced = run_scope(acme_workspace, Scope.PROJECT, git_repo, selection=Selection.ALL, apply=True)

    assert any(warning.startswith("ACME.md is tracked by git") for warning in synced.warnings)
    assert "/ACME.md" not in _block_lines(git_repo)


def test_given_worktree_when_syncing_repo_then_block_goes_to_the_shared_exclude_file(
    acme_workspace: Workspace,
    git_repo: Path,
    tmp_path: Path,
) -> None:
    _git(git_repo, "commit", "-q", "--allow-empty", "-m", "init")
    worktree = tmp_path / "worktree"
    _git(git_repo, "worktree", "add", "-q", str(worktree))

    run_scope(acme_workspace, Scope.PROJECT, worktree, selection=Selection.ALL, apply=True)

    assert "/ACME.md" in _block_lines(git_repo)
    assert not _git(worktree, "status", "--porcelain")


def test_given_plain_folder_when_syncing_repo_then_it_installs_and_warns(
    acme_workspace: Workspace,
    repo: Path,
) -> None:
    outcome = run_scope(acme_workspace, Scope.PROJECT, repo, selection=Selection.ALL, apply=True)

    assert (repo / "ACME.md").is_symlink()
    assert any("is not a git repository" in warning for warning in outcome.warnings)


def test_given_no_git_executable_when_querying_then_nothing_is_tracked_or_excluded(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("lantoki.gitexclude.shutil.which", lambda _: None)

    git = Git(repo)

    assert git.exclude_file() is None
    assert git.tracked(["ACME.md"]) == set()
