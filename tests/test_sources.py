"""Tests for loading neutral sources (SPECIFICATION §5)."""

lazy from pathlib import Path

import pytest

from lantoki.exceptions import SourceError
from lantoki.sources import InstructionMetadata, Kind, Scope, load_sources
from tests.conftest import write_tree


def test_given_sample_tree_when_loading_then_every_kind_and_scope_is_found(sources_root: Path) -> None:
    sources = load_sources(sources_root)

    found = {(source.scope, source.kind, source.name) for source in sources}
    assert found == {
        (Scope.USER, Kind.INSTRUCTION, "general"),
        (Scope.USER, Kind.INSTRUCTION, "python"),
        (Scope.USER, Kind.PROMPT, "review"),
        (Scope.USER, Kind.AGENT, "helper"),
        (Scope.USER, Kind.SKILL, "demo"),
        (Scope.USER, Kind.MCP, "gate"),
        (Scope.PROJECT, Kind.REPO_INSTRUCTIONS, "repo-instructions"),
        (Scope.PROJECT, Kind.INSTRUCTION, "python"),
        (Scope.PROJECT, Kind.INSTRUCTION, "airflow"),
        (Scope.PROJECT, Kind.PROMPT, "docs"),
        (Scope.PROJECT, Kind.SKILL, "lint"),
        (Scope.PROJECT, Kind.MCP, "db"),
    }


def test_given_instruction_and_server_when_reading_fields_then_templates_see_their_values(sources_root: Path) -> None:
    sources = {(source.scope, source.name): source for source in load_sources(sources_root)}

    python_fields = sources[Scope.USER, "python"].fields()
    gate_fields = sources[Scope.USER, "gate"].fields()

    assert python_fields["name"] == "python"
    assert python_fields["title"] == "Python Standards"
    assert python_fields["applies_to"] == ["**/*.py", "**/*.pyi"]
    assert "overrides" not in python_fields
    assert gate_fields == {
        "name": "gate",
        "command": "gate",
        "args": ["--fast"],
        "env": {"TOKEN": "{{env:GATE_TOKEN}}"},
    }
    assert sources[Scope.USER, "review"].overrides == {"acme": {"color": "blue"}}
    assert sources[Scope.USER, "review"].key == "prompt:review"


def test_given_instruction_without_applies_to_when_loading_then_it_applies_everywhere(sources_root: Path) -> None:
    general = next(source for source in load_sources(sources_root) if source.name == "general")

    assert isinstance(general.metadata, InstructionMetadata)
    assert general.metadata.applies_to is None


@pytest.mark.parametrize(
    ("relative", "text", "expected"),
    [
        ("user/instructions/Bad_Name.md", "---\ndescription: x\n---\n", "name 'Bad_Name' must match"),
        ("user/instructions/typo.md", "---\ndescription: x\napplies-to: ['*']\n---\n", "applies-to: Extra inputs"),
        ("user/instructions/empty.md", "---\ntitle: x\n---\n", "description: Field required"),
        ("user/agents/bad-tool.md", "---\ndescription: x\ntools: [Read]\n---\n", "unknown tool 'Read'"),
        ("user/prompts/scoped.md", "---\ndescription: x\napplies_to: ['*']\n---\n", "applies_to: Extra inputs"),
        ("user/instructions/list.md", "---\n- a\n---\n", "Front matter must be a YAML mapping"),
        ("user/skills/no-skill-file/README.md", "x", "a skill directory needs a SKILL.md"),
        ("user/mcp.toml", "[servers.x]\nargs = []\n", "servers.x: command: Field required"),
        ("project/mcp.toml", "[servers\n", "invalid TOML"),
    ],
)
def test_given_invalid_source_when_loading_then_error_names_file_and_problem(
    tmp_path: Path,
    relative: str,
    text: str,
    expected: str,
) -> None:
    root = write_tree(tmp_path / "sources", {relative: text})

    with pytest.raises(SourceError, match=expected) as error_info:
        load_sources(root)

    assert relative.split("/", maxsplit=1)[0] in error_info.value.message


def test_given_several_invalid_sources_when_loading_then_all_problems_are_reported(tmp_path: Path) -> None:
    root = write_tree(
        tmp_path / "sources",
        {"user/instructions/a.md": "---\n---\n", "user/agents/b.md": "---\ndescription: x\ntools: [nope]\n---\n"},
    )

    with pytest.raises(SourceError) as error_info:
        load_sources(root)

    assert error_info.value.context["error_count"] == 2


def test_given_missing_root_when_loading_then_source_error_is_raised(tmp_path: Path) -> None:
    with pytest.raises(SourceError, match="Sources root not found"):
        load_sources(tmp_path / "missing")


def test_given_repo_instructions_in_user_scope_when_loading_then_it_is_ignored(tmp_path: Path) -> None:
    root = write_tree(tmp_path / "sources", {"user/repo-instructions.md": "---\ndescription: x\n---\n"})

    assert load_sources(root) == []
