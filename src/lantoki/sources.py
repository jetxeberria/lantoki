"""Discover and validate customization sources written in lantoki's neutral format (SPECIFICATION §5).

Layout under the sources root::

    user/     instructions/*.md  prompts/*.md  agents/*.md  skills/<name>/  mcp/<name>/server.toml
    project/  repo-instructions.md  instructions/*.md  prompts/*.md  skills/<name>/  mcp/<name>/server.toml
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from lantoki import frontmatter
from lantoki.exceptions import SourceError


if TYPE_CHECKING:
    from pathlib import Path


class Kind(StrEnum):
    """Kinds of customization (SPECIFICATION §3)."""

    INSTRUCTION = "instruction"
    PROMPT = "prompt"
    AGENT = "agent"
    SKILL = "skill"
    MCP = "mcp"
    REPO_INSTRUCTIONS = "repo_instructions"


class Scope(StrEnum):
    """Where a customization applies (SCO-1)."""

    USER = "user"
    PROJECT = "project"


NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NEUTRAL_TOOLS = frozenset(
    {"read", "search", "edit", "write", "execute", "web_fetch", "web_search", "todo", "subagent"},
)
MCP_TOOL_PATTERN = re.compile(r"^mcp:(?P<server>[A-Za-z0-9_.-]+)/(?P<tool>[A-Za-z0-9_.-]+|\*)$")


def validate_tool(tool: str) -> str:
    """Return the tool unchanged if it belongs to the neutral vocabulary (SRC-5)."""
    if tool in NEUTRAL_TOOLS or MCP_TOOL_PATTERN.match(tool):
        return tool
    allowed = ", ".join(sorted(NEUTRAL_TOOLS))
    msg = f"unknown tool {tool!r}; use one of {allowed} or 'mcp:<server>/<tool>'"
    raise ValueError(msg)


class _Metadata(BaseModel):
    """Front-matter fields shared by every markdown kind (SRC-3)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    description: str = Field(min_length=1)
    title: str | None = None
    overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)


class InstructionMetadata(_Metadata):
    """Front matter of an instruction; no ``applies_to`` means it applies everywhere."""

    applies_to: list[str] | None = Field(default=None, min_length=1)


class _ToolUsingMetadata(_Metadata):
    """Front matter of kinds that can restrict tools."""

    argument_hint: str | None = None
    tools: list[str] | None = None

    @field_validator("tools")
    @classmethod
    def _check_tools(cls, tools: list[str] | None) -> list[str] | None:
        if tools is not None:
            for tool in tools:
                validate_tool(tool)
        return tools


class PromptMetadata(_ToolUsingMetadata):
    """Front matter of a prompt (a user-invoked command)."""


class AgentMetadata(_ToolUsingMetadata):
    """Front matter of an agent."""


class RepoInstructionsMetadata(_Metadata):
    """Front matter of a repository's always-on instructions."""


class McpServer(BaseModel):
    """One MCP server declared in ``mcp/<name>/server.toml`` (SRC-7)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: str = Field(min_length=1)
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] | None = None


@dataclass(frozen=True)
class Source:
    """One validated customization source."""

    kind: Kind
    scope: Scope
    name: str
    path: Path
    metadata: _Metadata | None = None
    body: str = ""
    server: McpServer | None = None
    overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def key(self) -> str:
        """Stable identifier used for repository selections (INS-7)."""
        return f"{self.kind}:{self.name}"

    def fields(self) -> dict[str, Any]:
        """Return the values profile templates can reference for this source."""
        values: dict[str, Any] = {"name": self.name}
        if self.metadata is not None:
            values.update(self.metadata.model_dump(exclude={"overrides"}))
        if self.server is not None:
            values.update(self.server.model_dump())
        return values


_MARKDOWN_KINDS: dict[Kind, tuple[str, type[_Metadata]]] = {
    Kind.INSTRUCTION: ("instructions", InstructionMetadata),
    Kind.PROMPT: ("prompts", PromptMetadata),
    Kind.AGENT: ("agents", AgentMetadata),
}
SKILLS_DIR = "skills"
MCP_DIR = "mcp"
SERVER_FILE = "server.toml"
RETIRED_MCP_FILE = "mcp.toml"
REPO_INSTRUCTIONS_FILE = "repo-instructions.md"


def _format_validation_error(error: ValidationError) -> str:
    """Summarise a pydantic error as ``field: message`` pairs."""
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc']) or 'front matter'}: {item['msg']}" for item in error.errors()
    )


class _Loader:
    """Collects sources and every validation problem so all errors are reported at once (CMP-3)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.sources: list[Source] = []
        self.errors: list[str] = []

    def error(self, path: Path, message: str) -> None:
        self.errors.append(f"{path.relative_to(self.root)}: {message}")

    def check_name(self, path: Path, name: str) -> bool:
        if NAME_PATTERN.match(name):
            return True
        self.error(path, f"name {name!r} must match {NAME_PATTERN.pattern} (SRC-2)")
        return False

    def load_markdown(self, path: Path, kind: Kind, scope: Scope, model: type[_Metadata], name: str) -> None:
        if not self.check_name(path, name):
            return
        try:
            document = frontmatter.parse(path.read_text(encoding="utf-8"))
            metadata = model.model_validate(document.front_matter)
        except ValidationError as error:
            self.error(path, _format_validation_error(error))
            return
        except (TypeError, ValueError) as error:
            self.error(path, str(error))
            return
        self.sources.append(
            Source(kind, scope, name, path, metadata, document.body, overrides=dict(metadata.overrides)),
        )

    def load_skills(self, directory: Path, scope: Scope) -> None:
        for skill_dir in sorted(path for path in directory.iterdir() if path.is_dir()):
            if not self.check_name(skill_dir, skill_dir.name):
                continue
            if not (skill_dir / "SKILL.md").is_file():
                self.error(skill_dir, "a skill directory needs a SKILL.md (SRC-6)")
                continue
            self.sources.append(Source(Kind.SKILL, scope, skill_dir.name, skill_dir))

    def load_mcp_servers(self, directory: Path, scope: Scope) -> None:
        for server_dir in sorted(path for path in directory.iterdir() if path.is_dir()):
            if not self.check_name(server_dir, server_dir.name):
                continue
            declaration = server_dir / SERVER_FILE
            if not declaration.is_file():
                self.error(server_dir, f"an MCP server directory needs a {SERVER_FILE} (SRC-7)")
                continue
            try:
                server = McpServer.model_validate(tomllib.loads(declaration.read_text(encoding="utf-8")))
            except tomllib.TOMLDecodeError as error:
                self.error(declaration, f"invalid TOML: {error}")
                continue
            except ValidationError as error:
                self.error(declaration, _format_validation_error(error))
                continue
            self.sources.append(Source(Kind.MCP, scope, server_dir.name, server_dir, server=server))

    def report_retired_mcp_file(self, path: Path) -> None:
        """Reject a scope-level ``mcp.toml``, which would otherwise be silently ignored (SRC-7, PRI-7)."""
        try:
            names = sorted(tomllib.loads(path.read_text(encoding="utf-8")).get("servers", {}))
        except tomllib.TOMLDecodeError:
            names = []
        destinations = (
            ", ".join(f"{MCP_DIR}/{name}/{SERVER_FILE}" for name in names) or f"{MCP_DIR}/<name>/{SERVER_FILE}"
        )
        self.error(path, f"{RETIRED_MCP_FILE} is no longer read; declare each server in {destinations} (SRC-7, D-017)")

    def load_scope(self, scope: Scope) -> None:
        scope_dir = self.root / scope
        if not scope_dir.is_dir():
            return
        for kind, (folder, model) in _MARKDOWN_KINDS.items():
            directory = scope_dir / folder
            if directory.is_dir():
                for path in sorted(directory.glob("*.md")):
                    self.load_markdown(path, kind, scope, model, path.stem)
        if (scope_dir / SKILLS_DIR).is_dir():
            self.load_skills(scope_dir / SKILLS_DIR, scope)
        if (scope_dir / MCP_DIR).is_dir():
            self.load_mcp_servers(scope_dir / MCP_DIR, scope)
        if (scope_dir / RETIRED_MCP_FILE).is_file():
            self.report_retired_mcp_file(scope_dir / RETIRED_MCP_FILE)
        repo_instructions = scope_dir / REPO_INSTRUCTIONS_FILE
        if scope is Scope.PROJECT and repo_instructions.is_file():
            self.load_markdown(
                repo_instructions,
                Kind.REPO_INSTRUCTIONS,
                scope,
                RepoInstructionsMetadata,
                repo_instructions.stem,
            )


def load_sources(root: Path) -> list[Source]:
    """Load and validate every source under ``root``.

    Raises:
        SourceError: The root is missing or any source is invalid; the message lists every problem.
    """
    if not root.is_dir():
        msg = f"Sources root not found: {root}"
        raise SourceError(msg, root=str(root))

    loader = _Loader(root)
    for scope in Scope:
        loader.load_scope(scope)
    if loader.errors:
        msg = "Invalid sources:\n  " + "\n  ".join(loader.errors)
        raise SourceError(msg, root=str(root), error_count=len(loader.errors))
    return loader.sources
