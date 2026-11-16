"""Tests for the generic value transforms (PRF-5)."""

import pytest

from lantoki.profiles import FieldRule, Placeholders, ToolsSpec
from lantoki.transforms import (
    OMIT,
    apply_rule,
    build_front_matter,
    map_tools,
    render_placeholders,
    render_structure,
    render_template,
)


TOOLS = ToolsSpec(
    map={"read": ["Read"], "search": ["Grep", "Glob"], "edit": ["Edit"], "write": ["Edit"]}, mcp="m__{server}__{tool}"
)
PLACEHOLDERS = Placeholders(arguments="$ARGS", env="${{{name}}}")


@pytest.mark.parametrize(
    ("template", "values", "expected"),
    [
        ("{tags}", {"tags": ["a", "b"]}, ["a", "b"]),
        ("{missing}", {}, OMIT),
        ("{title}", {"title": None}, OMIT),
        ("About {name}: {description}", {"name": "x", "description": "y"}, "About x: y"),
        ("About {name}: {title}", {"name": "x", "title": None}, OMIT),
        ("literal", {}, "literal"),
    ],
)
def test_given_template_when_rendering_then_values_are_substituted_or_omitted(
    template: str,
    values: dict[str, object],
    expected: object,
) -> None:
    assert render_template(template, values) == expected


def test_given_neutral_tools_when_mapping_then_names_are_translated_deduplicated_and_unknowns_reported() -> None:
    mapped, unmapped = map_tools(["read", "edit", "write", "mcp:gate/*", "mcp:k8s/pods_list", "teleport"], TOOLS)

    assert mapped == ["Read", "Edit", "m__gate__*", "m__k8s__pods_list"]
    assert unmapped == ["teleport"]


@pytest.mark.parametrize(
    ("rule", "values", "expected"),
    [
        (FieldRule(**{"from": "globs"}), {"globs": ["a", "b"]}, ["a", "b"]),
        (FieldRule(**{"from": "globs", "transform": "join"}), {"globs": ["a", "b"]}, "a, b"),
        (FieldRule(**{"from": "globs", "transform": "join", "sep": ";"}), {"globs": ["a", "b"]}, "a;b"),
        (FieldRule(**{"from": "globs", "transform": "join"}), {"globs": "already"}, "already"),
        (FieldRule(**{"from": "globs", "default": "**"}), {}, "**"),
        (FieldRule(**{"from": "globs"}), {"globs": None}, OMIT),
        (FieldRule(**{"from": "tools", "transform": "tools"}), {"tools": ["read", "search"]}, ["Read", "Grep", "Glob"]),
        (FieldRule(**{"from": "tools", "transform": "tools", "sep": ", "}), {"tools": ["read"]}, "Read"),
    ],
)
def test_given_field_rule_when_applied_then_value_is_transformed(
    rule: FieldRule,
    values: dict[str, object],
    expected: object,
) -> None:
    value, unmapped = apply_rule(rule, values, TOOLS)

    assert value == expected
    assert unmapped == []


def test_given_profile_mapping_when_building_front_matter_then_order_constants_and_omissions_hold() -> None:
    spec = {
        "name": "{title}",
        "description": "{description}",
        "always": True,
        "tags": ["x"],
        "tools": FieldRule(**{"from": "tools", "transform": "tools"}),
    }
    values = {"title": None, "description": "D", "tools": ["read", "teleport"]}

    front_matter, unmapped = build_front_matter(spec, values, TOOLS)

    assert front_matter == {"description": "D", "always": True, "tags": ["x"], "tools": ["Read"]}
    assert list(front_matter) == ["description", "always", "tags", "tools"]
    assert unmapped == ["teleport"]


def test_given_neutral_placeholders_when_rendering_then_provider_syntax_is_used() -> None:
    rendered = render_placeholders("Run {{arguments}} with {{env:API_KEY}} and {{other}}", PLACEHOLDERS)

    assert rendered == "Run $ARGS with ${API_KEY} and {{other}}"


def test_given_server_template_when_rendering_structure_then_missing_values_are_dropped() -> None:
    template = {"type": "stdio", "command": "{command}", "args": "{args}", "env": "{env}", "extra": ["{missing}", "k"]}
    values = {"command": "gate", "args": ["--x", "{{env:HOME}}"], "env": {"TOKEN": "{{env:TOKEN}}"}}

    rendered = render_structure(template, values, PLACEHOLDERS)

    assert rendered == {
        "type": "stdio",
        "command": "gate",
        "args": ["--x", "${HOME}"],
        "env": {"TOKEN": "${TOKEN}"},
        "extra": ["k"],
    }


def test_given_server_without_env_when_rendering_structure_then_env_key_is_omitted() -> None:
    rendered = render_structure(
        {"command": "{command}", "env": "{env}", "port": 8}, {"command": "c", "env": None}, PLACEHOLDERS
    )

    assert rendered == {"command": "c", "port": 8}
