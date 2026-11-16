"""The closed, generic set of value transforms profiles can use (PRF-5).

Nothing here knows about any provider: every provider-specific choice comes from the profile.
"""

from __future__ import annotations

import re
import string
from typing import TYPE_CHECKING, Any, Final

from lantoki.profiles import FieldRule
from lantoki.sources import MCP_TOOL_PATTERN


if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from lantoki.profiles import FrontMatterValue, Placeholders, ToolsSpec


class _Omit:
    """Marker for "leave this field out"."""

    def __repr__(self) -> str:
        return "OMIT"


OMIT: Final = _Omit()

_ARGUMENTS_PLACEHOLDER = "{{arguments}}"
_ENV_TOKEN = re.compile(r"\{\{env:(?P<name>[A-Za-z_][A-Za-z0-9_]*)\}\}")
_SINGLE_FIELD = re.compile(r"^\{(?P<field>[A-Za-z_][A-Za-z0-9_]*)\}$")


def render_template(template: str, values: Mapping[str, Any]) -> object:
    """Render a ``{field}`` template.

    A template that is exactly one ``{field}`` returns the raw value (so lists stay lists).
    Any referenced field that is missing or ``None`` makes the result :data:`OMIT`.
    """
    single = _SINGLE_FIELD.match(template)
    if single:
        value = values.get(single["field"])
        return OMIT if value is None else value

    referenced = [name for _, name, _, _ in string.Formatter().parse(template) if name]
    if any(values.get(name) is None for name in referenced):
        return OMIT
    return template.format(**{name: values[name] for name in referenced})


def map_tools(neutral_tools: Iterable[str], tools: ToolsSpec) -> tuple[list[str], list[str]]:
    """Translate neutral tool names; return ``(provider_tools, unmapped_neutral_tools)``."""
    mapped: list[str] = []
    unmapped: list[str] = []
    for tool in neutral_tools:
        mcp = MCP_TOOL_PATTERN.match(tool)
        if mcp:
            names = [tools.mcp.format(server=mcp["server"], tool=mcp["tool"])]
        elif tool in tools.map:
            names = tools.map[tool]
        else:
            unmapped.append(tool)
            continue
        mapped.extend(name for name in names if name not in mapped)
    return mapped, unmapped


def apply_rule(rule: FieldRule, values: Mapping[str, Any], tools: ToolsSpec) -> tuple[Any, list[str]]:
    """Apply a field rule; return ``(value or OMIT, unmapped_tools)``."""
    value = values.get(rule.from_)
    if value is None:
        return (OMIT if rule.default is None else rule.default), []

    if rule.transform == "join":
        return (rule.sep or ", ").join(value) if isinstance(value, list) else value, []
    if rule.transform == "tools":
        provider_tools, unmapped = map_tools(value, tools)
        return (rule.sep.join(provider_tools) if rule.sep is not None else provider_tools), unmapped
    return value, []


def build_front_matter(
    spec: Mapping[str, FrontMatterValue],
    values: Mapping[str, Any],
    tools: ToolsSpec,
) -> tuple[dict[str, Any], list[str]]:
    """Build a provider's front matter from a profile mapping; return ``(front_matter, unmapped_tools)``."""
    front_matter: dict[str, Any] = {}
    unmapped: list[str] = []
    for provider_field, rule in spec.items():
        if isinstance(rule, FieldRule):
            value, missing = apply_rule(rule, values, tools)
            unmapped.extend(missing)
        elif isinstance(rule, str):
            value = render_template(rule, values)
        else:
            value = rule
        if value is not OMIT:
            front_matter[provider_field] = value
    return front_matter, unmapped


def render_placeholders(text: str, placeholders: Placeholders) -> str:
    """Replace neutral ``{{arguments}}`` and ``{{env:NAME}}`` tokens with the provider's syntax."""
    text = text.replace(_ARGUMENTS_PLACEHOLDER, placeholders.arguments)
    return _ENV_TOKEN.sub(lambda match: placeholders.env.format(name=match["name"]), text)


def render_structure(template: object, values: Mapping[str, Any], placeholders: Placeholders) -> object:
    """Render a nested template (dicts, lists, strings); fields rendering to OMIT are dropped."""
    if isinstance(template, dict):
        rendered = {key: render_structure(value, values, placeholders) for key, value in template.items()}
        return {key: value for key, value in rendered.items() if value is not OMIT}
    if isinstance(template, list):
        items = [render_structure(item, values, placeholders) for item in template]
        return [item for item in items if item is not OMIT]
    if isinstance(template, str):
        value = render_template(template, values)
        return value if value is OMIT else _placeholders_in(value, placeholders)
    return template


def _placeholders_in(value: object, placeholders: Placeholders) -> object:
    """Apply placeholder rendering to every string inside a value."""
    if isinstance(value, str):
        return render_placeholders(value, placeholders)
    if isinstance(value, list):
        return [_placeholders_in(item, placeholders) for item in value]
    if isinstance(value, dict):
        return {key: _placeholders_in(item, placeholders) for key, item in value.items()}
    return value
