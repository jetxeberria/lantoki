"""Per-scope record of what lantoki installed (INS-3).

The manifest is the basis for ownership (PRI-5), pruning (INS-5), adoption (INS-6) and
remembered repository selections (INS-7).
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from lantoki.exceptions import InstallError
from lantoki.sources import Scope


MANIFEST_VERSION = 1


@dataclass
class Entry:
    """One installed target."""

    target: str
    mode: str
    providers: list[str]
    sources: list[str]
    digest: str
    link_to: str | None = None
    remove: list[str] | None = None


@dataclass
class Manifest:
    """Everything lantoki installed into one scope."""

    scope: str
    root: str
    entries: dict[str, Entry] = field(default_factory=dict)
    created_dirs: list[str] = field(default_factory=list)
    selection: list[str] | None = None
    known_sources: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path, scope: Scope, root: Path) -> Manifest:
        """Load a manifest, or start an empty one when none exists.

        Raises:
            InstallError: The manifest exists but cannot be read.
        """
        if not path.is_file():
            return cls(scope=str(scope), root=str(root))
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            entries = {target: Entry(**entry) for target, entry in raw.get("entries", {}).items()}
        except (OSError, ValueError, TypeError) as error:
            msg = f"Cannot read manifest {path}: {error}"
            raise InstallError(msg, path=str(path)) from error
        return cls(
            scope=raw["scope"],
            root=raw["root"],
            entries=entries,
            created_dirs=raw.get("created_dirs", []),
            selection=raw.get("selection"),
            known_sources=raw.get("known_sources", []),
        )

    def save(self, path: Path) -> None:
        """Write the manifest atomically."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": MANIFEST_VERSION,
            "scope": self.scope,
            "root": self.root,
            "selection": self.selection,
            "known_sources": sorted(set(self.known_sources)),
            "created_dirs": sorted(set(self.created_dirs)),
            "entries": {target: asdict(entry) for target, entry in sorted(self.entries.items())},
        }
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        Path(handle.name).replace(path)


def scope_key(scope: Scope, repo: Path | None = None) -> str:
    """Return a stable, file-system-safe key for a scope (``user`` or ``repo-<name>-<hash>``)."""
    if scope is Scope.USER or repo is None:
        return "user"
    resolved = str(repo.resolve())
    digest = hashlib.sha256(resolved.encode()).hexdigest()[:12]
    return f"repo-{repo.resolve().name}-{digest}"


def digest_text(text: str) -> str:
    """Return a content digest."""
    return hashlib.sha256(text.encode()).hexdigest()


def digest_tree(files: dict[str, bytes]) -> str:
    """Digest a directory tree given as relative path -> contents, like :func:`digest_path`."""
    hasher = hashlib.sha256()
    for relative in sorted(files, key=lambda relative: Path(relative).parts):
        hasher.update(relative.encode())
        hasher.update(files[relative])
    return hasher.hexdigest()


def digest_path(path: Path) -> str:
    """Digest a file or a directory tree (names and contents), without following the path itself."""
    if path.is_dir():
        return digest_tree(
            {str(child.relative_to(path)): child.read_bytes() for child in path.rglob("*") if child.is_file()}
        )
    return hashlib.sha256(path.read_bytes() if path.is_file() else b"").hexdigest()


def link_destination(path: Path) -> Path | None:
    """Return where a symlink points (absolute, even if broken), or None for non-links."""
    if not path.is_symlink():
        return None
    destination = path.readlink()
    return destination if destination.is_absolute() else (path.parent / destination)
