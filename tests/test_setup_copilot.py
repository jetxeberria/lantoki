#!/usr/bin/env python

"""Tests for Copilot setup symlink creation."""

import argparse
import importlib.util
import os
import subprocess
import sys
from types import ModuleType
from pathlib import Path

import pytest


@pytest.fixture
def setup_paths(tmp_path: Path) -> dict[str, Path]:
    """Create an isolated HOME and target repo for setup_copilot tests."""
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "src" / "lantoki" / "setup_copilot.py"
    sync_root = repo_root / "src" / "lantoki" / "copilot-instructions-set"

    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)

    target_repo = tmp_path / "target-repo"
    target_repo.mkdir(parents=True, exist_ok=True)

    return {
        "script": script_path,
        "sync_root": sync_root,
        "home": fake_home,
        "target_repo": target_repo,
    }


def _run_setup(
    script_path: Path,
    home_path: Path,
    args: list[str],
    user_input: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home_path)

    return subprocess.run(
        [sys.executable, str(script_path)] + args,
        input=user_input,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def _load_setup_module(script_path: Path) -> ModuleType:
    """Load setup_copilot.py as a module for in-process testing."""
    spec = importlib.util.spec_from_file_location("setup_copilot_module", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _skill_dirs(sync_root: Path) -> list[Path]:
    """Return project skill directories from the instruction sync root."""
    skills_path = sync_root / "project-level" / "project-skills"
    return [path for path in skills_path.glob("*") if path.is_dir()]


def test_user_mode_creates_expected_user_symlinks(setup_paths: dict[str, Path]) -> None:
    script = setup_paths["script"]
    sync_root = setup_paths["sync_root"]
    fake_home = setup_paths["home"]

    result = _run_setup(script, fake_home, ["user"])
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    vscode_user = fake_home / ".config" / "Code" / "User"
    copilot_cli = fake_home / ".copilot"

    expected_links = [
        (
            sync_root / "user-level" / "mcp" / "vscode-mcp.json",
            vscode_user / "mcp.json",
        ),
        (
            sync_root / "user-level" / "mcp" / "cli-mcp-config.json",
            copilot_cli / "mcp-config.json",
        ),
    ]

    for src in (sync_root / "user-level" / "instructions").glob("*"):
        expected_links.append((src, vscode_user / "instructions" / src.name))

    for src in (sync_root / "user-level" / "prompts").glob("*"):
        expected_links.append((src, vscode_user / "prompts" / src.name))

    for src, dest in expected_links:
        assert dest.is_symlink(), f"Expected symlink missing: {dest}"
        assert dest.resolve() == src.resolve()


def test_repo_mode_creates_expected_repo_symlinks(setup_paths: dict[str, Path]) -> None:
    script = setup_paths["script"]
    sync_root = setup_paths["sync_root"]
    fake_home = setup_paths["home"]
    target_repo = setup_paths["target_repo"]

    # Answer "y" for every interactive prompt so all optional links are created.
    prompt_count = len(
        list((sync_root / "project-level" / "scoped-instructions").glob("*.instructions.md"))
    )
    prompt_count += len(list((sync_root / "project-level" / "project-prompts").glob("*.prompt.md")))
    prompt_count += len(_skill_dirs(sync_root))
    user_input = ("y\n" * prompt_count) if prompt_count else None

    result = _run_setup(
        script,
        fake_home,
        ["repo", str(target_repo)],
        user_input=user_input,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    expected_links = [
        (
            sync_root / "project-level" / "global-repo" / "copilot-instructions.md",
            target_repo / ".github" / "copilot-instructions.md",
        ),
        (
            sync_root / "project-level" / "global-repo" / "AGENTS.md",
            target_repo / "AGENTS.md",
        ),
    ]

    shared_mcp = sync_root / "project-level" / "project-mcp" / "shared-mcp.json"
    if shared_mcp.is_file():
        expected_links.append((shared_mcp, target_repo / ".vscode" / "mcp.json"))

    for src in (sync_root / "project-level" / "scoped-instructions").glob("*.instructions.md"):
        expected_links.append((src, target_repo / ".github" / "instructions" / src.name))

    for src in (sync_root / "project-level" / "project-prompts").glob("*.prompt.md"):
        expected_links.append((src, target_repo / ".github" / "prompts" / src.name))

    for src in _skill_dirs(sync_root):
        expected_links.append((src, target_repo / ".github" / "skills" / src.name))

    for src, dest in expected_links:
        assert dest.is_symlink(), f"Expected symlink missing: {dest}"
        assert dest.resolve() == src.resolve()


def test_safe_link_tracks_missing_source(
    setup_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    module = _load_setup_module(setup_paths["script"])
    missing_src = tmp_path / "does-not-exist.txt"
    dest = tmp_path / "dest" / "link.txt"

    module.safe_link(missing_src, dest)

    assert any(item.startswith("[Source Missing]") for item in module.skipped_items)


def test_safe_link_tracks_existing_conflict_and_already_linked(
    setup_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    module = _load_setup_module(setup_paths["script"])
    src = tmp_path / "source.txt"
    src.write_text("data", encoding="utf-8")

    linked_dest = tmp_path / "linked-dest.txt"
    linked_dest.symlink_to(src)
    module.safe_link(src, linked_dest)

    conflict_dest = tmp_path / "conflict.txt"
    conflict_dest.write_text("conflict", encoding="utf-8")
    module.safe_link(src, conflict_dest)

    assert any(item.startswith("[Already Linked]") for item in module.skipped_items)
    assert any(item.startswith("[Conflict]") for item in module.skipped_items)


def test_setup_repo_invalid_target_exits(setup_paths: dict[str, Path]) -> None:
    module = _load_setup_module(setup_paths["script"])
    with pytest.raises(SystemExit) as exc_info:
        module.setup_repo(setup_paths["sync_root"], Path("/path/that/does/not/exist"))

    assert exc_info.value.code == 1


def test_setup_user_in_process_creates_expected_links(
    setup_paths: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_setup_module(setup_paths["script"])
    sync_root = setup_paths["sync_root"]
    fake_home = tmp_path / "home-in-process"
    fake_home.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(module.Path, "home", lambda: fake_home)
    module.setup_user(sync_root)

    vscode_user = fake_home / ".config" / "Code" / "User"
    copilot_cli = fake_home / ".copilot"

    expected_links = [
        (
            sync_root / "user-level" / "mcp" / "vscode-mcp.json",
            vscode_user / "mcp.json",
        ),
        (
            sync_root / "user-level" / "mcp" / "cli-mcp-config.json",
            copilot_cli / "mcp-config.json",
        ),
    ]

    for src in (sync_root / "user-level" / "instructions").glob("*"):
        expected_links.append((src, vscode_user / "instructions" / src.name))

    for src in (sync_root / "user-level" / "prompts").glob("*"):
        expected_links.append((src, vscode_user / "prompts" / src.name))

    for src, dest in expected_links:
        assert dest.is_symlink(), f"Expected symlink missing: {dest}"
        assert dest.resolve() == src.resolve()


def test_setup_repo_in_process_declines_optional_links(
    setup_paths: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_setup_module(setup_paths["script"])
    sync_root = setup_paths["sync_root"]
    target_repo = tmp_path / "target-repo-decline"
    target_repo.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(module, "ask_yes_no", lambda _: False)
    module.setup_repo(sync_root, target_repo)

    assert (target_repo / ".github" / "copilot-instructions.md").is_symlink()
    assert (target_repo / "AGENTS.md").is_symlink()

    for src in (sync_root / "project-level" / "scoped-instructions").glob("*.instructions.md"):
        assert not (target_repo / ".github" / "instructions" / src.name).exists()

    for src in (sync_root / "project-level" / "project-prompts").glob("*.prompt.md"):
        assert not (target_repo / ".github" / "prompts" / src.name).exists()

    for src in _skill_dirs(sync_root):
        assert not (target_repo / ".github" / "skills" / src.name).exists()


def test_parse_args_and_main_dispatch(
    setup_paths: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_setup_module(setup_paths["script"])

    monkeypatch.setattr(sys, "argv", ["setup_copilot.py", "user"])
    args = module.parse_args()
    assert args.mode == "user"

    monkeypatch.setattr(sys, "argv", ["setup_copilot.py", "repo", "/tmp/repo"])
    args = module.parse_args()
    assert args.mode == "repo"
    assert args.path == "/tmp/repo"

    called: dict[str, Path] = {}
    monkeypatch.setattr(module, "parse_args", lambda: argparse.Namespace(mode="user"))
    monkeypatch.setattr(module, "setup_user", lambda root: called.setdefault("user", root))
    module.main()
    assert "user" in called

    monkeypatch.setattr(
        module,
        "parse_args",
        lambda: argparse.Namespace(mode="repo", path="/tmp/repo"),
    )
    monkeypatch.setattr(
        module,
        "setup_repo",
        lambda root, target: called.update({"repo_root": root, "repo_target": target}),
    )
    module.main()

    assert isinstance(called["repo_root"], Path)
    assert called["repo_target"] == Path("/tmp/repo")
