"""Compile neutral sources into provider artifacts using provider profiles (SPECIFICATION §7).

Compilation is pure: it reads sources and profiles and returns artifacts; it never writes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from lantoki import frontmatter, transforms
from lantoki.exceptions import CompileError
from lantoki.sources import Kind, Scope, Source


if TYPE_CHECKING:
    from collections.abc import Iterable

    from lantoki.profiles import Output, Profile


Mode = Literal["symlink", "copy", "command"]


@dataclass(frozen=True)
class Artifact:
    """One compiled output for one target.

    ``content`` holds generated text; ``link_source`` is set when the target links straight to a
    source (``directory`` format). With ``file``, the target is a folder and ``content`` is the
    file of that name inside it (D-011). Command artifacts carry ``apply``/``remove`` argv templates in
    which ``{cli}`` is resolved at install time.
    """

    target: str
    mode: Mode
    providers: tuple[str, ...]
    sources: tuple[str, ...]
    content: str | None = None
    link_source: Path | None = None
    file: str | None = None
    apply: tuple[str, ...] = ()
    remove: tuple[str, ...] = ()
    cli_candidates: tuple[str, ...] = ()

    @property
    def installed_path(self) -> str:
        """The path of the generated file itself: the target, or ``file`` inside it."""
        return str(Path(self.target) / self.file) if self.file else self.target

    @property
    def is_command(self) -> bool:
        """Whether the artifact is installed by running a provider CLI."""
        return self.mode == "command"

    def same_output(self, other: Artifact) -> bool:
        """Return True when two artifacts would install exactly the same thing."""
        return (self.mode, self.content, self.link_source, self.file, self.apply, self.remove) == (
            other.mode,
            other.content,
            other.link_source,
            other.file,
            other.apply,
            other.remove,
        )


@dataclass
class CompileResult:
    """Artifacts plus everything that could not be mapped (PRI-7)."""

    artifacts: list[Artifact] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CompileContext:
    """Where the scope being compiled lives."""

    scope: Scope
    home: Path
    sources_root: Path
    repo: Path | None = None

    def target_values(self, name: str | None = None) -> dict[str, str]:
        """Values available to ``target`` templates."""
        values = {"home": str(self.home)}
        if self.repo is not None:
            values["repo"] = str(self.repo)
        if name is not None:
            values["name"] = name
        return values


def _target(output: Output, context: CompileContext, name: str | None = None) -> str:
    template = output.target or ""
    try:
        return str(Path(template.format(**context.target_values(name))))
    except KeyError as error:
        msg = f"target {template!r} uses unknown placeholder {error.args[0]!r} for scope {context.scope}"
        raise CompileError(msg, target=template) from error


def _provenance(source: Source, context: CompileContext) -> str:
    return str(source.path.relative_to(context.sources_root))


def _markdown(
    source: Source, output: Output, profile: Profile, context: CompileContext, result: CompileResult
) -> Artifact:
    front_matter, unmapped = transforms.build_front_matter(output.front_matter, source.fields(), profile.tools)
    front_matter.update(source.overrides.get(profile.id, {}))
    if unmapped:
        result.warnings.append(f"{profile.id}: {source.key} uses tools with no {profile.id} equivalent: {unmapped}")
    body = transforms.render_placeholders(source.body, profile.placeholders)
    return Artifact(
        target=_target(output, context, source.name),
        mode=output.link,
        providers=(profile.id,),
        sources=(source.key,),
        content=frontmatter.render(front_matter, body, _provenance(source, context)),
        file=output.file,
    )


def _directory(source: Source, output: Output, profile: Profile, context: CompileContext) -> Artifact:
    return Artifact(
        target=_target(output, context, source.name),
        mode=output.link,
        providers=(profile.id,),
        sources=(source.key,),
        link_source=source.path,
    )


def _server(source: Source, output: Output, profile: Profile) -> object:
    return transforms.render_structure(output.server, source.fields(), profile.placeholders)


def _json(sources: list[Source], output: Output, profile: Profile, context: CompileContext) -> Artifact:
    document: dict[str, Any] = dict(output.document)
    document[output.root_key or ""] = {source.name: _server(source, output, profile) for source in sources}
    return Artifact(
        target=_target(output, context),
        mode=output.link,
        providers=(profile.id,),
        sources=tuple(source.key for source in sources),
        content=json.dumps(document, indent=2) + "\n",
    )


def _command(source: Source, output: Output, profile: Profile, context: CompileContext) -> Artifact:
    values = {"name": source.name, "server_json": json.dumps(_server(source, output, profile)), "cli": "{cli}"}

    def argv(template: list[str]) -> tuple[str, ...]:
        return tuple(str(part).format(**values) for part in template)

    return Artifact(
        target=f"command:{profile.id}:{context.scope}:{source.name}",
        mode="command",
        providers=(profile.id,),
        sources=(source.key,),
        apply=argv(output.apply),
        remove=argv(output.remove),
        cli_candidates=tuple(candidate.format(home=context.home) for candidate in profile.cli.candidates),
    )


def _compile_output(
    output: Output,
    sources: list[Source],
    profile: Profile,
    context: CompileContext,
    result: CompileResult,
) -> list[Artifact]:
    if output.format == "json":
        return [_json(sources, output, profile, context)] if sources else []
    builders = {
        "markdown": lambda source: _markdown(source, output, profile, context, result),
        "directory": lambda source: _directory(source, output, profile, context),
        "command": lambda source: _command(source, output, profile, context),
    }
    return [builders[output.format](source) for source in sources]


def _merge(artifacts: Iterable[Artifact]) -> list[Artifact]:
    """Merge identical artifacts on the same target; fail on conflicting ones (CMP-2)."""
    by_target: dict[str, Artifact] = {}
    for artifact in artifacts:
        existing = by_target.get(artifact.target)
        if existing is None:
            by_target[artifact.target] = artifact
            continue
        if not existing.same_output(artifact):
            msg = (
                f"{artifact.target}: {existing.providers} and {artifact.providers} produce different content "
                "for the same target"
            )
            raise CompileError(msg, target=artifact.target)
        by_target[artifact.target] = Artifact(
            **{**existing.__dict__, "providers": tuple(dict.fromkeys(existing.providers + artifact.providers))},
        )
    return list(by_target.values())


def compile_scope(sources: list[Source], profiles: list[Profile], context: CompileContext) -> CompileResult:
    """Compile every source of ``context.scope`` for every profile.

    Raises:
        CompileError: Two artifacts claim the same target with different content, or a target
            template is invalid for the scope.
    """
    result = CompileResult()
    scoped = [source for source in sources if source.scope is context.scope]
    produced: list[Artifact] = []
    for profile in profiles:
        outputs = profile.outputs_for(context.scope)
        for output in outputs:
            matching = [source for source in scoped if source.kind is output.kind]
            produced.extend(_compile_output(output, matching, profile, context, result))
        supported = {output.kind for output in outputs}
        for kind in sorted({source.kind for source in scoped} - supported):
            count = sum(source.kind is kind for source in scoped)
            result.warnings.append(f"{profile.id}: does not support {kind} at {context.scope} scope ({count} skipped)")
    result.artifacts = sorted(_merge(produced), key=lambda artifact: artifact.target)
    return result


__all__ = ["Artifact", "CompileContext", "CompileResult", "Kind", "compile_scope"]
