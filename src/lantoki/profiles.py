"""Provider profiles: everything provider-specific, as validated data (SPECIFICATION §6).

Profiles are read with :mod:`tomllib` rather than dynaconf because provider field names are
case-sensitive data (``applyTo``, ``argument-hint``) that a settings loader would normalise.
"""

from __future__ import annotations

import re
import tomllib
from datetime import date  # noqa: TC003 - pydantic resolves field types at runtime
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from lantoki.exceptions import ProfileError
from lantoki.sources import NEUTRAL_TOOLS, Kind, Scope


if TYPE_CHECKING:
    from pathlib import Path


PROVIDER_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

_FORMATS_BY_KIND: dict[Kind, frozenset[str]] = {
    Kind.INSTRUCTION: frozenset({"markdown"}),
    Kind.PROMPT: frozenset({"markdown"}),
    Kind.AGENT: frozenset({"markdown"}),
    Kind.REPO_INSTRUCTIONS: frozenset({"markdown"}),
    Kind.SKILL: frozenset({"directory"}),
    Kind.MCP: frozenset({"json", "command"}),
}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class FieldRule(_Strict):
    """Maps one source field into one provider field (PRF-5).

    ``transform``: ``value`` copies it, ``join`` joins a list with ``sep``, ``tools`` maps
    neutral tool names through the profile's tool map (joined with ``sep`` when given,
    otherwise kept as a list). ``default`` is used when the source field is absent; with no
    default, the provider field is omitted.
    """

    from_: str = Field(alias="from")
    transform: Literal["value", "join", "tools"] = "value"
    sep: str | None = None
    default: Any = None


FrontMatterValue = FieldRule | str | bool | int | float | list[Any]


class ProviderInfo(_Strict):
    """Provenance of a profile (PRF-2, PRI-8)."""

    id: str
    name: str = Field(min_length=1)
    docs: list[str] = Field(min_length=1)
    verified_with: str = Field(min_length=1)
    verified_on: date

    @field_validator("id")
    @classmethod
    def _check_id(cls, provider_id: str) -> str:
        if not PROVIDER_ID_PATTERN.match(provider_id):
            msg = f"provider id must match {PROVIDER_ID_PATTERN.pattern}"
            raise ValueError(msg)
        return provider_id


class Placeholders(_Strict):
    """Provider syntax for neutral body and value placeholders (PRF-7, SRC-4)."""

    arguments: str
    env: str = Field(description="Template with {name}, e.g. '${{{name}}}' renders ${NAME}")


class ToolsSpec(_Strict):
    """Neutral tool names → provider tool names (PRF-6)."""

    map: dict[str, list[str]] = Field(default_factory=dict)
    mcp: str = Field(description="Template with {server} and {tool}")

    @field_validator("map")
    @classmethod
    def _check_neutral_names(cls, tool_map: dict[str, list[str]]) -> dict[str, list[str]]:
        unknown = sorted(set(tool_map) - NEUTRAL_TOOLS)
        if unknown:
            msg = f"unknown neutral tools {unknown}; allowed: {sorted(NEUTRAL_TOOLS)}"
            raise ValueError(msg)
        return tool_map


class CliSpec(_Strict):
    """Where to find the provider's command-line tool (PRF-8)."""

    candidates: list[str] = Field(default_factory=list)


class Output(_Strict):
    """One place where the provider reads one kind of customization (PRF-3, PRF-4)."""

    kind: Kind
    scope: Scope
    format: Literal["markdown", "directory", "json", "command"]
    target: str | None = None
    link: Literal["symlink", "copy"] = "symlink"
    file: str | None = None
    front_matter: dict[str, FrontMatterValue] = Field(default_factory=dict)
    root_key: str | None = None
    document: dict[str, Any] = Field(default_factory=dict)
    server: dict[str, Any] = Field(default_factory=dict)
    apply: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_format(self) -> Self:
        allowed = _FORMATS_BY_KIND[self.kind]
        if self.format not in allowed:
            msg = f"kind {self.kind} supports formats {sorted(allowed)}, not {self.format!r}"
            raise ValueError(msg)
        problems = {
            "markdown": [] if self.target else ["target"],
            "directory": [] if self.target else ["target"],
            "json": [
                name
                for name, value in (("target", self.target), ("root_key", self.root_key), ("server", self.server))
                if not value
            ],
            "command": [
                name
                for name, value in (("apply", self.apply), ("remove", self.remove), ("server", self.server))
                if not value
            ],
        }[self.format]
        if problems:
            msg = f"format {self.format!r} requires {', '.join(problems)}"
            raise ValueError(msg)
        if self.file is not None and (self.format != "markdown" or not self.file or "/" in self.file):
            msg = "'file' is a plain file name and only applies to markdown outputs"
            raise ValueError(msg)
        if self.format == "command" and self.link != "symlink":
            msg = "'link' does not apply to command outputs"
            raise ValueError(msg)
        return self


class Profile(_Strict):
    """A complete provider profile."""

    provider: ProviderInfo
    placeholders: Placeholders
    tools: ToolsSpec
    cli: CliSpec = Field(default_factory=CliSpec)
    outputs: Annotated[list[Output], Field(min_length=1)]

    @property
    def id(self) -> str:
        """The provider id."""
        return self.provider.id

    @model_validator(mode="after")
    def _check_cli(self) -> Self:
        if any(output.format == "command" for output in self.outputs) and not self.cli.candidates:
            msg = "command outputs require [cli].candidates"
            raise ValueError(msg)
        return self

    def outputs_for(self, scope: Scope) -> list[Output]:
        """Return the outputs that install into ``scope``."""
        return [output for output in self.outputs if output.scope is scope]


def _describe(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc']) or 'profile'}: {item['msg']}" for item in error.errors()
    )


def load_profile(path: Path) -> Profile:
    """Load and validate one profile file whose name must be ``<provider-id>.toml``.

    Raises:
        ProfileError: The file is unreadable, invalid TOML, or does not match the schema.
    """
    try:
        profile = Profile.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError) as error:
        msg = f"{path.name}: cannot read profile: {error}"
        raise ProfileError(msg, path=str(path)) from error
    except ValidationError as error:
        msg = f"{path.name}: {_describe(error)}"
        raise ProfileError(msg, path=str(path)) from error
    if profile.id != path.stem:
        msg = f"{path.name}: provider.id {profile.id!r} must match the file name"
        raise ProfileError(msg, path=str(path))
    return profile


def load_profiles(directory: Path, enabled: tuple[str, ...] = ()) -> list[Profile]:
    """Load every ``*.toml`` profile in ``directory``, optionally keeping only ``enabled`` ids.

    Raises:
        ProfileError: A profile is invalid, none exist, or an enabled id has no profile.
    """
    errors: list[str] = []
    profiles: list[Profile] = []
    for path in sorted(directory.glob("*.toml")):
        try:
            profiles.append(load_profile(path))
        except ProfileError as error:
            errors.append(error.message)
    if errors:
        msg = "Invalid provider profiles:\n  " + "\n  ".join(errors)
        raise ProfileError(msg, directory=str(directory))
    if not profiles:
        msg = f"No provider profiles found in {directory}"
        raise ProfileError(msg, directory=str(directory))

    if not enabled:
        return profiles
    unknown = sorted(set(enabled) - {profile.id for profile in profiles})
    if unknown:
        msg = f"Enabled providers without a profile: {unknown}"
        raise ProfileError(msg, directory=str(directory))
    return [profile for profile in profiles if profile.id in enabled]
