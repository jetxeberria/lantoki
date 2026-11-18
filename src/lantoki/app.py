"""Provider-agnostic orchestration of validate, plan and sync (SPECIFICATION §7-§9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from lantoki.compiler import CompileContext, CompileResult, compile_scope
from lantoki.gitexclude import Git, relative_targets, sync_block, tracked_warnings
from lantoki.installer import Installer, Plan, Report
from lantoki.manifest import Manifest, scope_key
from lantoki.profiles import Profile, load_profiles
from lantoki.sources import Scope, Source, load_sources


if TYPE_CHECKING:
    from collections.abc import Callable

    from lantoki.config import Settings
    from lantoki.installer import CommandRunner


class Selection(StrEnum):
    """How project-scope sources are chosen for a repository (INS-7)."""

    REMEMBERED = "remembered"
    ALL = "all"
    ASK = "ask"


@dataclass
class Outcome:
    """Result of planning (and optionally applying) one scope."""

    plan: Plan
    warnings: list[str] = field(default_factory=list)
    report: Report | None = None
    selected: list[str] = field(default_factory=list)
    skipped_new_sources: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Whether nothing conflicted or failed."""
        return not self.plan.conflicts and not (self.report and self.report.failed)


@dataclass(frozen=True)
class Workspace:
    """Everything loaded from settings: sources and enabled profiles."""

    settings: Settings
    sources: list[Source]
    profiles: list[Profile]

    @classmethod
    def load(cls, settings: Settings, providers: tuple[str, ...] = ()) -> Workspace:
        """Load and validate sources and profiles (CMP-3)."""
        enabled = providers or settings.enabled_providers
        return cls(
            settings=settings,
            sources=load_sources(settings.sources_root),
            profiles=load_profiles(settings.providers_dir, enabled),
        )

    def compile(self, scope: Scope, repo: Path | None = None) -> CompileResult:
        """Compile every source of ``scope``."""
        context = CompileContext(scope=scope, home=Path.home(), sources_root=self.settings.sources_root, repo=repo)
        return compile_scope(self.sources, self.profiles, context)


def _choose_sources(
    workspace: Workspace,
    manifest: Manifest,
    selection: Selection,
    ask: Callable[[Source], bool] | None,
) -> tuple[set[str], list[str]]:
    """Return (selected source keys, new sources skipped because nobody could be asked)."""
    candidates = [source for source in workspace.sources if source.scope is Scope.PROJECT]
    keys = {source.key for source in candidates}
    if selection is Selection.ALL:
        return keys, []

    remembered = set(manifest.selection or []) if selection is Selection.REMEMBERED else set()
    known = set(manifest.known_sources) if selection is Selection.REMEMBERED else set()
    chosen = remembered & keys
    skipped: list[str] = []
    for source in candidates:
        if source.key in known:
            continue
        if ask is None:
            skipped.append(source.key)
        elif ask(source):
            chosen.add(source.key)
    return chosen, skipped


def run_scope(
    workspace: Workspace,
    scope: Scope,
    repo: Path | None = None,
    *,
    selection: Selection = Selection.REMEMBERED,
    ask: Callable[[Source], bool] | None = None,
    apply: bool = False,
    adopt_commands: bool = False,
    run_command: CommandRunner | None = None,
) -> Outcome:
    """Compile, plan and (when ``apply``) install one scope, then save its manifest."""
    settings = workspace.settings
    key = scope_key(scope, repo)
    manifest_path = settings.manifests_dir / f"{key}.json"
    root = repo.resolve() if repo is not None else Path.home()
    manifest = Manifest.load(manifest_path, scope, root)

    compiled = workspace.compile(scope, repo.resolve() if repo is not None else None)
    artifacts = compiled.artifacts
    outcome = Outcome(plan=Plan(), warnings=list(compiled.warnings))
    if scope is Scope.PROJECT:
        chosen, outcome.skipped_new_sources = _choose_sources(workspace, manifest, selection, ask)
        outcome.selected = sorted(chosen)
        artifacts = [artifact for artifact in artifacts if set(artifact.sources) & chosen]

    installer_args = {"run_command": run_command} if run_command is not None else {}
    installer = Installer(
        manifest,
        store_dir=settings.compiled_dir / key,
        owned_roots=(settings.project_root, settings.compiled_dir),
        **installer_args,
    )
    outcome.plan = installer.plan(artifacts, adopt_commands=adopt_commands)
    git = Git(root) if scope is Scope.PROJECT else None
    if git is not None and not apply:
        planned = relative_targets(root, (artifact.target for artifact in artifacts if not artifact.is_command))
        outcome.warnings.extend(tracked_warnings(git, planned))
    if apply:
        outcome.report = installer.apply(outcome.plan)
        if scope is Scope.PROJECT:
            manifest.selection = outcome.selected
            manifest.known_sources = sorted(
                {source.key for source in workspace.sources if source.scope is Scope.PROJECT}
                - set(outcome.skipped_new_sources),
            )
        manifest.save(manifest_path)
        if git is not None:
            owned = relative_targets(
                root, (target for target, entry in manifest.entries.items() if entry.mode != "command")
            )
            outcome.warnings.extend(sync_block(git, owned))
    return outcome
