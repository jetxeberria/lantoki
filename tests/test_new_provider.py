"""PRI-4 / QLT-2: adding a provider is adding one profile file, with no code changes."""

import shutil
from pathlib import Path

import pytest

from lantoki.app import Selection, Workspace, run_scope
from lantoki.config import load_settings
from lantoki.sources import Kind, Scope
from tests.conftest import FAKE_PROVIDERS_DIR, REAL_PROVIDERS_DIR


@pytest.fixture
def providers_dir(tmp_path: Path, acme_env: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copy the shipped profiles into a providers directory the new one can be dropped into."""
    del acme_env
    directory = tmp_path / "providers"
    shutil.copytree(REAL_PROVIDERS_DIR, directory)
    monkeypatch.setenv("LANTOKI_PROVIDERS_DIR", str(directory))
    return directory


def test_given_new_profile_file_when_dropped_in_then_every_supported_kind_is_installed_for_it(
    providers_dir: Path,
    home: Path,
    repo: Path,
) -> None:
    before = {profile.id for profile in Workspace.load(load_settings()).profiles}
    shutil.copy(FAKE_PROVIDERS_DIR / "acme.toml", providers_dir)

    workspace = Workspace.load(load_settings())
    user = run_scope(workspace, Scope.USER, apply=True)
    project = run_scope(workspace, Scope.PROJECT, repo, selection=Selection.ALL, apply=True)

    acme_targets = {step.target for step in user.plan.steps + project.plan.steps if "acme" in step.target}
    assert {profile.id for profile in workspace.profiles} == before | {"acme"}
    assert {
        str(home / ".acme" / "rules" / "general.md"),
        str(home / ".acme" / "commands" / "review"),
        str(home / ".acme" / "agents" / "helper.md"),
        str(home / ".acme" / "skills" / "demo"),
        "command:acme:user:gate",
        str(repo / ".acme" / "rules" / "python.md"),
        str(repo / ".acme" / "skills" / "lint"),
        str(repo / ".acme" / "mcp.json"),
    } <= acme_targets
    assert (repo / "ACME.md").is_symlink()
    assert {output.kind for output in next(p for p in workspace.profiles if p.id == "acme").outputs} == set(Kind)
