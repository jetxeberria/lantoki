"""Plan and apply the installation of compiled artifacts (SPECIFICATION §8).

``plan`` only inspects the file system; ``apply`` executes a plan. Both are provider-agnostic.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from lantoki import frontmatter
from lantoki.manifest import Entry, Manifest, digest_path, digest_text, digest_tree, link_destination


if TYPE_CHECKING:
    from collections.abc import Callable

    from lantoki.compiler import Artifact

    CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


LOGGER = structlog.get_logger(__name__)


class Action(StrEnum):
    """What installing one target will do."""

    CREATE = "create"
    UPDATE = "update"
    ADOPT = "adopt"
    UNCHANGED = "unchanged"
    PRUNE = "prune"
    CONFLICT = "conflict"
    SKIP = "skip"


@dataclass(frozen=True)
class Step:
    """One planned action on one target."""

    action: Action
    target: str
    detail: str = ""
    artifact: Artifact | None = None
    entry: Entry | None = None
    cli: str | None = None


@dataclass
class Plan:
    """Every step needed to bring a scope in line with its artifacts."""

    steps: list[Step] = field(default_factory=list)

    @property
    def conflicts(self) -> list[Step]:
        """Steps that could not be planned because lantoki does not own the target."""
        return [step for step in self.steps if step.action is Action.CONFLICT]

    def count(self, action: Action) -> int:
        """Count the steps with ``action``."""
        return sum(step.action is action for step in self.steps)


@dataclass
class Report:
    """Outcome of applying a plan."""

    applied: list[Step] = field(default_factory=list)
    failed: list[tuple[Step, str]] = field(default_factory=list)


def _version_key(path: Path) -> tuple[int, ...]:
    match = re.search(r"\d+(?:\.\d+)+", str(path))
    return tuple(int(part) for part in match.group().split(".")) if match else ()


def resolve_cli(candidates: tuple[str, ...]) -> str | None:
    """Return the first usable CLI: a command on PATH, or the newest match of a glob (PRF-8)."""
    for candidate in candidates:
        if "*" in candidate:
            matches = sorted(Path("/").glob(candidate.lstrip("/")), key=_version_key)
            executables = [str(match) for match in matches if match.is_file() and os.access(match, os.X_OK)]
            if executables:
                return executables[-1]
            continue
        resolved = shutil.which(candidate)
        if resolved is not None:
            return resolved
    return None


class Installer:
    """Installs artifacts into one scope, tracking ownership in that scope's manifest."""

    def __init__(
        self,
        manifest: Manifest,
        store_dir: Path,
        owned_roots: tuple[Path, ...],
        run_command: CommandRunner = subprocess.run,
    ) -> None:
        """Create an installer.

        Args:
            manifest: The scope's manifest (updated in place by :meth:`apply`).
            store_dir: Where compiled artifacts for this scope are stored (INS-1).
            owned_roots: Paths whose symlinks count as lantoki's when adopting (INS-6).
            run_command: Runs provider CLI commands; injectable for tests (QLT-5).
        """
        self.manifest = manifest
        self.store_dir = store_dir
        self.owned_roots = tuple(root.resolve() for root in owned_roots)
        self.run_command = run_command

    # ------------------------------------------------------------------ planning

    def store_path(self, artifact: Artifact) -> Path:
        """Where the compiled content of a file artifact is kept."""
        return self.store_dir / artifact.target.lstrip("/")

    def _store_file(self, artifact: Artifact) -> Path:
        """Where the generated text itself is kept: the store path, or ``file`` inside it (D-011)."""
        store = self.store_path(artifact)
        return store / artifact.file if artifact.file else store

    def _desired_link(self, artifact: Artifact) -> Path:
        return artifact.link_source if artifact.link_source is not None else self.store_path(artifact)

    def _digest(self, artifact: Artifact) -> str:
        if artifact.is_command:
            return digest_text("\0".join(artifact.apply))
        if artifact.content is not None and artifact.file:
            return digest_tree({artifact.file: artifact.content.encode()})
        if artifact.content is not None:
            return digest_text(artifact.content)
        return digest_path(artifact.link_source) if artifact.link_source else ""

    def _is_lantoki_path(self, target: Path) -> bool:
        destination = link_destination(target)
        if destination is not None:
            resolved = Path(os.path.normpath(destination))
            return any(resolved.is_relative_to(root) for root in self.owned_roots)
        if target.is_file():
            try:
                return frontmatter.is_generated(target.read_text(encoding="utf-8"))
            except UnicodeDecodeError, OSError:
                return False
        if target.is_dir():
            children = list(target.iterdir())
            return bool(children) and all(self._is_lantoki_path(child) for child in children)
        return False

    def _matches(self, artifact: Artifact, target: Path) -> bool:
        if artifact.mode == "symlink":
            destination = link_destination(target)
            store_file = self._store_file(artifact)
            store_ok = artifact.content is None or (
                store_file.is_file() and store_file.read_text(encoding="utf-8") == artifact.content
            )
            return destination == self._desired_link(artifact) and store_ok
        return not target.is_symlink() and digest_path(target) == self._digest(artifact)

    def _modified_since_install(self, entry: Entry, target: Path) -> bool:
        if entry.mode == "symlink":
            destination = link_destination(target)
            return destination is None or str(destination) != entry.link_to
        return target.is_symlink() or digest_path(target) != entry.digest

    def _plan_file(self, artifact: Artifact) -> Step:
        target = Path(artifact.target)
        entry = self.manifest.entries.get(artifact.target)
        if not (target.exists() or target.is_symlink()):
            return Step(Action.CREATE, artifact.target, artifact=artifact)
        if entry is None:
            if not self._is_lantoki_path(target):
                return Step(Action.CONFLICT, artifact.target, "exists and was not installed by lantoki", artifact)
            return Step(Action.ADOPT, artifact.target, "taking over an earlier lantoki install", artifact)
        if self._matches(artifact, target):
            return Step(Action.UNCHANGED, artifact.target, artifact=artifact, entry=entry)
        if self._modified_since_install(entry, target):
            return Step(
                Action.CONFLICT, artifact.target, "changed by someone else since lantoki installed it", artifact
            )
        return Step(Action.UPDATE, artifact.target, artifact=artifact, entry=entry)

    def _plan_command(self, artifact: Artifact, *, adopt: bool) -> Step:
        entry = self.manifest.entries.get(artifact.target)
        if entry is not None and entry.digest == self._digest(artifact):
            return Step(Action.UNCHANGED, artifact.target, artifact=artifact, entry=entry)
        cli = resolve_cli(artifact.cli_candidates)
        if cli is None:
            return Step(Action.SKIP, artifact.target, "provider CLI not found", artifact)
        if entry is not None:
            return Step(Action.UPDATE, artifact.target, artifact=artifact, entry=entry, cli=cli)
        detail = "replacing any existing registration" if adopt else ""
        return Step(Action.ADOPT if adopt else Action.CREATE, artifact.target, detail, artifact, cli=cli)

    def _plan_prune(self, entry: Entry) -> Step:
        if entry.mode == "command":
            return Step(Action.PRUNE, entry.target, "unregister", entry=entry)
        target = Path(entry.target)
        if not (target.exists() or target.is_symlink()):
            return Step(Action.PRUNE, entry.target, "already gone", entry=entry)
        if self._modified_since_install(entry, target):
            return Step(
                Action.CONFLICT, entry.target, "source removed but target was changed; left in place", entry=entry
            )
        return Step(Action.PRUNE, entry.target, entry=entry)

    def plan(self, artifacts: list[Artifact], *, adopt_commands: bool = False) -> Plan:
        """Plan installing ``artifacts`` and pruning manifest entries that no longer have one."""
        plan = Plan()
        wanted = {artifact.target for artifact in artifacts}
        for artifact in artifacts:
            if artifact.is_command:
                plan.steps.append(self._plan_command(artifact, adopt=adopt_commands))
            else:
                plan.steps.append(self._plan_file(artifact))
        for target, entry in sorted(self.manifest.entries.items()):
            if target not in wanted:
                plan.steps.append(self._plan_prune(entry))
        return plan

    # ------------------------------------------------------------------ applying

    def _remove_target(self, target: Path) -> None:
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)

    def _make_parents(self, target: Path) -> None:
        missing: list[Path] = []
        parent = target.parent
        while not parent.exists():
            missing.append(parent)
            parent = parent.parent
        target.parent.mkdir(parents=True, exist_ok=True)
        self.manifest.created_dirs.extend(str(directory) for directory in missing)

    def _install_file(self, artifact: Artifact) -> Entry:
        target = Path(artifact.target)
        if artifact.content is not None:
            store = self._store_file(artifact)
            store.parent.mkdir(parents=True, exist_ok=True)
            store.write_text(artifact.content, encoding="utf-8")
        if target.exists() or target.is_symlink():
            self._remove_target(target)
        self._make_parents(target)
        if artifact.target in self.manifest.created_dirs:
            self.manifest.created_dirs.remove(artifact.target)

        link_to: str | None = None
        if artifact.mode == "symlink":
            destination = self._desired_link(artifact)
            target.symlink_to(destination, target_is_directory=destination.is_dir())
            link_to = str(destination)
        elif artifact.content is not None and artifact.file:
            target.mkdir()
            (target / artifact.file).write_text(artifact.content, encoding="utf-8")
        elif artifact.content is not None:
            target.write_text(artifact.content, encoding="utf-8")
        elif artifact.link_source is not None:
            shutil.copytree(artifact.link_source, target)
        return Entry(
            target=artifact.target,
            mode=artifact.mode,
            providers=list(artifact.providers),
            sources=list(artifact.sources),
            digest=self._digest(artifact),
            link_to=link_to,
        )

    def _run(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        return self.run_command(argv, check=False, capture_output=True, text=True)

    def _install_command(self, step: Step) -> Entry:
        artifact = step.artifact
        if artifact is None or step.cli is None:
            msg = "command step without artifact or CLI"
            raise ValueError(msg)
        remove = [part.replace("{cli}", step.cli) for part in artifact.remove]
        if step.action in {Action.UPDATE, Action.ADOPT}:
            self._run(remove)
        completed = self._run([part.replace("{cli}", step.cli) for part in artifact.apply])
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "command failed")
        return Entry(
            target=artifact.target,
            mode="command",
            providers=list(artifact.providers),
            sources=list(artifact.sources),
            digest=self._digest(artifact),
            remove=remove,
        )

    def _prune(self, step: Step) -> None:
        entry = step.entry
        if entry is None:
            return
        if entry.mode == "command":
            if entry.remove:
                self._run(entry.remove)
        else:
            target = Path(entry.target)
            if target.exists() or target.is_symlink():
                self._remove_target(target)
            store = self.store_dir / entry.target.lstrip("/")
            if store.is_file():
                store.unlink()
            elif store.is_dir():
                shutil.rmtree(store)
            self._remove_empty_created_dirs()
        del self.manifest.entries[entry.target]

    def _remove_empty_created_dirs(self) -> None:
        for directory in sorted(set(self.manifest.created_dirs), key=len, reverse=True):
            path = Path(directory)
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
                self.manifest.created_dirs.remove(directory)

    def apply(self, plan: Plan) -> Report:
        """Execute a plan; conflicts and skips are left untouched (INS-4).

        Prunes run first, so removing an old target never removes what a new one installed under
        the same path (INS-6, D-011).
        """
        report = Report()
        for step in sorted(plan.steps, key=lambda step: step.action is not Action.PRUNE):
            if step.action in {Action.CONFLICT, Action.SKIP}:
                continue
            try:
                if step.action is Action.PRUNE:
                    self._prune(step)
                elif step.action is Action.UNCHANGED:
                    pass
                elif step.artifact is not None and step.artifact.is_command:
                    self.manifest.entries[step.target] = self._install_command(step)
                elif step.artifact is not None:
                    self.manifest.entries[step.target] = self._install_file(step.artifact)
            except (OSError, RuntimeError, ValueError) as error:
                report.failed.append((step, str(error)))
                LOGGER.warning("install_step_failed", target=step.target, action=str(step.action), error=str(error))
                continue
            report.applied.append(step)
        return report
