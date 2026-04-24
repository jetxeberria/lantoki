"""MCP server that runs Python verification gates in the target repository runtime."""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP


if TYPE_CHECKING:
    from collections.abc import Callable


mcp = FastMCP("python-verification-gate")

_TARGET_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s*:(?!=)")
_IGNORED_TOP_LEVEL_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "docs",
    "node_modules",
    "venv",
}


@dataclass(frozen=True)
class FallbackCommandSpec:
    """Fallback command plus optional uv-injected package name."""

    executable: str
    args: list[str]
    uv_package: str | None = None


def _has_command(command: str) -> bool:
    """Return True if command exists in PATH."""
    return shutil.which(command) is not None


def _resolve_executable(executable: str) -> str:
    """Resolve an executable to an absolute path."""
    if "/" in executable:
        return executable
    resolved = shutil.which(executable)
    if resolved is None:
        msg = f"Executable not found in PATH: {executable}"
        raise FileNotFoundError(msg)
    return resolved


def _resolve_local_venv_executable(repository_path: Path, executable: str) -> str | None:
    """Resolve an executable from a repository-local virtual environment."""
    scripts_dir = "Scripts" if os.name == "nt" else "bin"
    candidate_names = [executable]
    if os.name == "nt":
        candidate_names.append(f"{executable}.exe")

    for candidate_name in candidate_names:
        candidate = repository_path / ".venv" / scripts_dir / candidate_name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _discover_source_roots(repository_path: Path) -> list[str]:
    """Discover likely Python source roots for source-oriented fallbacks."""
    discovered: list[str] = []

    if (repository_path / "src").is_dir():
        discovered.append("src")

    for child in sorted(repository_path.iterdir()):
        if not child.is_dir() or child.name in _IGNORED_TOP_LEVEL_DIRS:
            continue
        if (child / "__init__.py").is_file():
            discovered.append(child.name)

    if not discovered:
        discovered.extend(sorted(path.name for path in repository_path.glob("*.py")))

    if not discovered:
        discovered.append(".")

    return discovered


def _primary_source_root(repository_path: Path) -> str:
    """Return the primary source root for recursive scanners like Bandit."""
    return _discover_source_roots(repository_path)[0]


def _collect_make_targets(repository_path: Path) -> set[str]:
    """Collect Makefile targets from known Makefile names."""
    target_names: set[str] = set()
    for name in ("Makefile", "makefile"):
        file_path = repository_path / name
        if not file_path.is_file():
            continue
        for line in file_path.read_text(encoding="utf-8").splitlines():
            match = _TARGET_RE.match(line)
            if match:
                target_names.add(match.group(1))
    return target_names


def _collect_just_targets(repository_path: Path) -> set[str]:
    """Collect available recipes by querying just."""
    justfile_exists = any((repository_path / name).is_file() for name in ("Justfile", "justfile"))
    if not justfile_exists or not _has_command("just"):
        return set()

    process = subprocess.run(  # noqa: S603  # nosec B603
        [_resolve_executable("just"), "--list", "--unsorted"],
        cwd=repository_path,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        return set()

    recipes: set[str] = set()
    for line in process.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        recipe_name = stripped.split()[0]
        if re.match(r"^[A-Za-z0-9_.-]+$", recipe_name):
            recipes.add(recipe_name)
    return recipes


def _run_command(repository_path: Path, command: list[str]) -> dict[str, Any]:
    """Run a command and return structured output."""
    resolved_command = [
        _resolve_executable(command[0]),
        *command[1:],
    ]
    environment = os.environ.copy()
    # Avoid the MCP bootstrap environment leaking into repo-local tool runners.
    environment.pop("VIRTUAL_ENV", None)

    process = subprocess.run(  # noqa: S603  # nosec B603
        resolved_command,
        cwd=repository_path,
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )
    return {
        "command": resolved_command,
        "exit_code": process.returncode,
        "success": process.returncode == 0,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def _resolve_repository_fallback_command(
    repository_path: Path,
    fallback_spec: FallbackCommandSpec,
) -> dict[str, Any]:
    """Resolve fallback command against the target repository runtime."""
    executable = fallback_spec.executable
    args = fallback_spec.args

    local_venv_executable = _resolve_local_venv_executable(repository_path, executable)
    if local_venv_executable is not None:
        return {
            "runner": "project-venv",
            "target": None,
            "used_fallback": True,
            "command": [local_venv_executable, *args],
        }

    if (repository_path / "Pipfile").is_file() and _has_command("pipenv"):
        return {
            "runner": "pipenv",
            "target": None,
            "used_fallback": True,
            "command": ["pipenv", "run", executable, *args],
        }

    if (repository_path / "poetry.lock").is_file() and _has_command("poetry"):
        return {
            "runner": "poetry",
            "target": None,
            "used_fallback": True,
            "command": ["poetry", "run", executable, *args],
        }

    if ((repository_path / "uv.lock").is_file() or (repository_path / "pyproject.toml").is_file()) and _has_command(
        "uv",
    ):
        command = ["uv", "run"]
        runner = "uv"
        if fallback_spec.uv_package is not None:
            command.extend(["--with", fallback_spec.uv_package])
            runner = "uv-with"
        command.extend([executable, *args])
        return {
            "runner": runner,
            "target": None,
            "used_fallback": True,
            "command": command,
        }

    if _has_command(executable):
        return {
            "runner": "global",
            "target": None,
            "used_fallback": True,
            "command": [executable, *args],
        }

    return {
        "runner": "unavailable",
        "target": None,
        "used_fallback": True,
        "command": [executable, *args],
    }


def _resolve_primary_command(
    repository_path: Path,
    preferred_targets: list[str],
    fallback_spec: FallbackCommandSpec,
) -> dict[str, Any]:
    """Resolve command via Just/Make target first, then fallback."""
    just_targets = _collect_just_targets(repository_path)
    for target in preferred_targets:
        if target in just_targets:
            return {
                "runner": "just",
                "target": target,
                "used_fallback": False,
                "command": ["just", target],
            }

    if _has_command("make"):
        make_targets = _collect_make_targets(repository_path)
        for target in preferred_targets:
            if target in make_targets:
                return {
                    "runner": "make",
                    "target": target,
                    "used_fallback": False,
                    "command": ["make", target],
                }

    return _resolve_repository_fallback_command(repository_path, fallback_spec)


def _normalize_repository_path(repository_path: str) -> Path:
    """Resolve and validate repository path input."""
    resolved = Path(repository_path).expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        msg = f"Invalid repository_path: {repository_path}"
        raise ValueError(msg)
    return resolved


def _run_gate(
    repository_path: str,
    preferred_targets: list[str],
    fallback_builder: Callable[[Path], FallbackCommandSpec],
) -> dict[str, Any]:
    """Execute one verification gate command with target-aware resolution."""
    repo_path = _normalize_repository_path(repository_path)
    resolution = _resolve_primary_command(repo_path, preferred_targets, fallback_builder(repo_path))

    if resolution["runner"] == "unavailable":
        return {
            "repository_path": str(repo_path),
            **resolution,
            "exit_code": 127,
            "success": False,
            "stdout": "",
            "stderr": f"Unable to resolve a repository-local or global runtime for: {resolution['command'][0]}",
        }

    result = _run_command(repo_path, resolution["command"])
    return {
        "repository_path": str(repo_path),
        **resolution,
        **result,
    }


def _ruff_check_command(_: Path) -> FallbackCommandSpec:
    """Build the default Ruff check command."""
    return FallbackCommandSpec("ruff", ["check", "."], uv_package="ruff")


def _mypy_command(repository_path: Path) -> FallbackCommandSpec:
    """Build the default mypy command."""
    return FallbackCommandSpec("mypy", _discover_source_roots(repository_path), uv_package="mypy")


def _bandit_command(repository_path: Path) -> FallbackCommandSpec:
    """Build the default bandit command."""
    return FallbackCommandSpec("bandit", ["-r", _primary_source_root(repository_path)], uv_package="bandit")


def _pytest_command(_: Path) -> FallbackCommandSpec:
    """Build the default pytest command."""
    return FallbackCommandSpec("pytest", [], uv_package="pytest")


def _format_check_command(_: Path) -> FallbackCommandSpec:
    """Build the default Ruff format validation command."""
    return FallbackCommandSpec("ruff", ["format", "--check", "."], uv_package="ruff")


@mcp.tool()
def run_ruff_check(repository_path: str = ".") -> dict[str, Any]:
    """Run Ruff checks using the target repository runtime."""
    return _run_gate(
        repository_path=repository_path,
        preferred_targets=["lint"],
        fallback_builder=_ruff_check_command,
    )


@mcp.tool()
def run_mypy(repository_path: str = ".") -> dict[str, Any]:
    """Run static typing using the target repository runtime."""
    return _run_gate(
        repository_path=repository_path,
        preferred_targets=["type"],
        fallback_builder=_mypy_command,
    )


@mcp.tool()
def run_bandit(repository_path: str = ".") -> dict[str, Any]:
    """Run bandit using the target repository runtime."""
    return _run_gate(
        repository_path=repository_path,
        preferred_targets=[],
        fallback_builder=_bandit_command,
    )


@mcp.tool()
def run_pytest(repository_path: str = ".") -> dict[str, Any]:
    """Run test suite using the target repository runtime."""
    return _run_gate(
        repository_path=repository_path,
        preferred_targets=["test"],
        fallback_builder=_pytest_command,
    )


@mcp.tool()
def run_format_check(repository_path: str = ".") -> dict[str, Any]:
    """Run format checks using the target repository runtime."""
    return _run_gate(
        repository_path=repository_path,
        preferred_targets=["format"],
        fallback_builder=_format_check_command,
    )


@mcp.tool()
def run_ruff(repository_path: str = ".") -> dict[str, Any]:
    """Alias for the Ruff check gate."""
    return run_ruff_check(repository_path)


@mcp.tool()
def run_format(repository_path: str = ".") -> dict[str, Any]:
    """Alias for the format check gate."""
    return run_format_check(repository_path)


@mcp.tool()
def run_pytest_check(repository_path: str = ".") -> dict[str, Any]:
    """Alias for the pytest gate."""
    return run_pytest(repository_path)


@mcp.tool()
def run_type_check(repository_path: str = ".") -> dict[str, Any]:
    """Alias for the mypy gate."""
    return run_mypy(repository_path)


@mcp.tool()
def run_bandit_check(repository_path: str = ".") -> dict[str, Any]:
    """Alias for the bandit gate."""
    return run_bandit(repository_path)


@mcp.tool()
def run_test_check(repository_path: str = ".") -> dict[str, Any]:
    """Alias for the pytest gate."""
    return run_pytest(repository_path)


@mcp.tool()
def run_mypy_check(repository_path: str = ".") -> dict[str, Any]:
    """Alias for the mypy gate."""
    return run_mypy(repository_path)


@mcp.tool()
def run_lint_check(repository_path: str = ".") -> dict[str, Any]:
    """Alias for the Ruff check gate."""
    return run_ruff_check(repository_path)


@mcp.tool()
def run_test(repository_path: str = ".") -> dict[str, Any]:
    """Alias for the pytest gate to keep generic gate naming stable."""
    return run_pytest(repository_path)


@mcp.tool()
def run_type(repository_path: str = ".") -> dict[str, Any]:
    """Alias for the mypy gate to keep generic gate naming stable."""
    return run_mypy(repository_path)


@mcp.tool()
def run_lint(repository_path: str = ".") -> dict[str, Any]:
    """Alias for the Ruff gate to keep generic gate naming stable."""
    return run_ruff_check(repository_path)


@mcp.tool()
def run_formatting(repository_path: str = ".") -> dict[str, Any]:
    """Alias for the format gate to keep generic gate naming stable."""
    return run_format_check(repository_path)


def main() -> None:
    """Run the MCP server using stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
