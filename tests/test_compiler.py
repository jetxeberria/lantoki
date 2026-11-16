"""Tests for compiling sources with profiles, using only the fictional ``acme`` provider (QLT-2)."""

import json
from pathlib import Path

import pytest

from lantoki import frontmatter
from lantoki.app import Workspace
from lantoki.compiler import Artifact, CompileContext, compile_scope
from lantoki.exceptions import CompileError
from lantoki.profiles import load_profile
from lantoki.sources import Scope
from tests.conftest import FAKE_PROVIDERS_DIR


def _by_target(artifacts: list[Artifact], home: Path, relative: str) -> Artifact:
    return next(artifact for artifact in artifacts if artifact.target == str(home / relative))


def test_given_user_sources_when_compiling_then_markdown_front_matter_follows_the_profile(
    acme_workspace: Workspace,
    home: Path,
) -> None:
    result = acme_workspace.compile(Scope.USER)

    python_rule = frontmatter.parse(_by_target(result.artifacts, home, ".acme/rules/python.md").content or "")
    general_rule = frontmatter.parse(_by_target(result.artifacts, home, ".acme/rules/general.md").content or "")
    assert python_rule.front_matter == {
        "title": "Python Standards",
        "summary": "About: Python rules",
        "globs": "**/*.py;**/*.pyi",
    }
    assert general_rule.front_matter == {"summary": "About: Applies everywhere", "globs": "*"}
    assert general_rule.body.startswith(frontmatter.GENERATED_MARKER.format(source="user/instructions/general.md"))


def test_given_prompt_with_override_when_compiling_then_placeholders_tools_and_override_apply(
    acme_workspace: Workspace,
    home: Path,
) -> None:
    result = acme_workspace.compile(Scope.USER)

    prompt = frontmatter.parse(_by_target(result.artifacts, home, ".acme/commands/review").content or "")
    assert prompt.front_matter == {
        "summary": "Review code",
        "hint": "path",
        "allowed": ["view", "gate.*"],
        "user_only": True,
        "color": "blue",
    }
    assert prompt.body.endswith("Review %ARGS% now.\n")


def test_given_agent_with_unmapped_tool_when_compiling_then_tool_is_dropped_with_warning(
    acme_workspace: Workspace,
    home: Path,
) -> None:
    result = acme_workspace.compile(Scope.USER)

    agent = frontmatter.parse(_by_target(result.artifacts, home, ".acme/agents/helper.md").content or "")
    assert agent.front_matter == {"name": "helper", "tools": "view,shell,gate.run_lint"}
    assert "acme: agent:helper uses tools with no acme equivalent: ['search']" in result.warnings


def test_given_skill_and_mcp_when_compiling_user_scope_then_directory_link_and_command_are_produced(
    acme_workspace: Workspace,
    home: Path,
    sources_root: Path,
) -> None:
    result = acme_workspace.compile(Scope.USER)

    skill = _by_target(result.artifacts, home, ".acme/skills/demo")
    command = next(artifact for artifact in result.artifacts if artifact.is_command)
    assert skill.mode == "symlink"
    assert skill.link_source == sources_root / "user" / "skills" / "demo"
    assert command.target == "command:acme:user:gate"
    assert command.apply[:3] == ("{cli}", "add", "gate")
    assert json.loads(command.apply[3]) == {"cmd": "gate", "argv": ["--fast"], "environment": {"TOKEN": "%GATE_TOKEN%"}}
    assert command.remove == ("{cli}", "rm", "gate")
    assert command.cli_candidates == ("acme-cli-that-does-not-exist", f"{home}/acme/*/acme")


def test_given_project_sources_when_compiling_then_json_aggregates_and_unsupported_kinds_are_reported(
    acme_workspace: Workspace,
    repo: Path,
) -> None:
    result = acme_workspace.compile(Scope.PROJECT, repo)

    targets = {artifact.target: artifact for artifact in result.artifacts}
    mcp = json.loads(targets[str(repo / ".acme" / "mcp.json")].content or "")
    rule = targets[str(repo / ".acme" / "rules" / "python.md")]
    assert mcp == {"version": 1, "servers": {"db": {"cmd": "db-mcp", "argv": []}}}
    assert rule.mode == "copy"
    assert frontmatter.parse(rule.content or "").front_matter == {"globs": ["**/*.py"]}
    assert str(repo / "ACME.md") in targets
    assert "acme: does not support prompt at project scope (1 skipped)" in result.warnings


def test_given_two_providers_with_identical_output_when_compiling_then_artifacts_are_merged(
    acme_workspace: Workspace,
    repo: Path,
    tmp_path: Path,
) -> None:
    twin_path = tmp_path / "twin.toml"
    twin_path.write_text(
        (FAKE_PROVIDERS_DIR / "acme.toml").read_text(encoding="utf-8").replace('id = "acme"', 'id = "twin"'),
        encoding="utf-8",
    )
    profiles = [*acme_workspace.profiles, load_profile(twin_path)]
    context = CompileContext(Scope.PROJECT, Path.home(), acme_workspace.settings.sources_root, repo)

    result = compile_scope(acme_workspace.sources, profiles, context)

    repo_file = next(artifact for artifact in result.artifacts if artifact.target == str(repo / "ACME.md"))
    assert repo_file.providers == ("acme", "twin")
    assert len([artifact for artifact in result.artifacts if artifact.target == repo_file.target]) == 1


def test_given_two_providers_with_different_output_on_same_target_when_compiling_then_compile_error(
    acme_workspace: Workspace,
    repo: Path,
    tmp_path: Path,
) -> None:
    rival_path = tmp_path / "rival.toml"
    rival_text = (FAKE_PROVIDERS_DIR / "acme.toml").read_text(encoding="utf-8")
    rival_path.write_text(
        rival_text.replace('id = "acme"', 'id = "rival"').replace(
            "document = { version = 1 }", "document = { version = 2 }"
        ),
        encoding="utf-8",
    )
    profiles = [*acme_workspace.profiles, load_profile(rival_path)]
    context = CompileContext(Scope.PROJECT, Path.home(), acme_workspace.settings.sources_root, repo)

    with pytest.raises(CompileError, match="produce different content for the same target"):
        compile_scope(acme_workspace.sources, profiles, context)


def test_given_project_target_template_when_compiling_without_repo_then_compile_error(
    acme_workspace: Workspace,
) -> None:
    context = CompileContext(Scope.PROJECT, Path.home(), acme_workspace.settings.sources_root)

    with pytest.raises(CompileError, match="unknown placeholder 'repo'"):
        compile_scope(acme_workspace.sources, acme_workspace.profiles, context)
