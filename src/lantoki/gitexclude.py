"""Keep lantoki's repository outputs out of git: a managed block in the local exclude file (INS-9)."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - runs git with fixed arguments, never a shell
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    GitRunner = Callable[..., subprocess.CompletedProcess[str]]

BEGIN = "# >>> lantoki: managed by `lantoki sync repo`, do not edit >>>"
END = "# <<< lantoki <<<"


def render_block(paths: Iterable[str]) -> str:
    """Return the managed block for ``paths`` (relative to the repository), or ``""`` when there are none."""
    entries = sorted({"/" + path.strip("/") for path in paths})
    if not entries:
        return ""
    return "\n".join([BEGIN, *entries, END]) + "\n"


def merge(existing: str, block: str) -> str:
    """Replace, add or remove the managed block in ``existing``, leaving every other line untouched."""
    kept: list[str] = []
    inside = False
    for line in existing.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        if stripped == BEGIN:
            inside = True
        elif stripped == END and inside:
            inside = False
        elif not inside:
            kept.append(line)
    text = "".join(kept)
    if not block:
        return text
    if text and not text.endswith("\n"):
        text += "\n"
    return text + block


class Git:
    """The few git queries lantoki needs about one repository."""

    def __init__(self, repo: Path, run: GitRunner = subprocess.run) -> None:
        """Bind to ``repo``; ``run`` is injectable for tests (QLT-5)."""
        self.repo = repo
        self.run = run
        self.executable = shutil.which("git")

    def _git(self, *args: str) -> subprocess.CompletedProcess[str] | None:
        if self.executable is None:
            return None
        return self.run([self.executable, "-C", str(self.repo), *args], check=False, capture_output=True, text=True)

    def exclude_file(self) -> Path | None:
        """Return the repository's local exclude file, or ``None`` outside a git repository or without git."""
        completed = self._git("rev-parse", "--git-path", "info/exclude")
        if completed is None or completed.returncode != 0:
            return None
        return (self.repo / completed.stdout.strip()).resolve()

    def tracked(self, paths: list[str]) -> set[str]:
        """Return which of ``paths`` (relative to the repository) git already tracks."""
        if not paths:
            return set()
        completed = self._git("ls-files", "-z", "--", *paths)
        if completed is None or completed.returncode != 0:
            return set()
        listed = {item for item in completed.stdout.split("\0") if item}
        return {path for path in paths if path in listed or any(item.startswith(path + "/") for item in listed)}


def relative_targets(repo: Path, targets: Iterable[str]) -> list[str]:
    """Return the targets under ``repo``, relative to it, as POSIX paths."""
    root = repo.resolve()
    relative: list[str] = []
    for target in targets:
        path = Path(target)
        if path.is_relative_to(root):
            relative.append(path.relative_to(root).as_posix())
    return sorted(relative)


def tracked_warnings(git: Git, paths: list[str]) -> list[str]:
    """Return one warning per target git already tracks (they cannot be excluded)."""
    return [
        f"{path} is tracked by git: lantoki cannot keep it out of git; remove it from the index (git rm --cached)"
        for path in sorted(git.tracked(paths))
    ]


def sync_block(git: Git, paths: list[str]) -> list[str]:
    """Write the managed block for ``paths`` into the exclude file and return warnings."""
    exclude = git.exclude_file()
    if exclude is None:
        return [f"{git.repo} is not a git repository (or git is missing): its lantoki outputs are not excluded"]
    tracked = git.tracked(paths)
    existing = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    updated = merge(existing, render_block(path for path in paths if path not in tracked))
    if updated != existing:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text(updated, encoding="utf-8")
    return tracked_warnings(git, paths)
