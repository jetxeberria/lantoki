"""Tests for the Python verification gate MCP server."""

import importlib.util
import itertools
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import TypeVar

import pytest


_MODULE_COUNTER = itertools.count()
_ToolFunction = TypeVar("_ToolFunction", bound=Callable[..., object])


class FakeMCPServer:
    """In-memory stand-in for MCPServer that records registered tools and run calls."""

    def __init__(self, name: str) -> None:
        """Store the server name and start with empty call records."""
        self.name = name
        self.registered_tools: list[str] = []
        self.run_calls: list[str] = []

    def tool(self) -> Callable[[_ToolFunction], _ToolFunction]:
        """Return a decorator that records the tool name and leaves the function unchanged."""

        def decorator(function: _ToolFunction) -> _ToolFunction:
            self.registered_tools.append(function.__name__)
            return function

        return decorator

    def run(self, transport: str) -> None:
        """Record the transport the server was started with."""
        self.run_calls.append(transport)


def _completed_process(
    command: list[str],
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def _load_python_verification_gate_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    fake_mcp_module = ModuleType("mcp")
    fake_server_module = ModuleType("mcp.server")
    fake_mcpserver_module = ModuleType("mcp.server.mcpserver")
    fake_mcpserver_module.MCPServer = FakeMCPServer
    fake_server_module.mcpserver = fake_mcpserver_module
    fake_mcp_module.server = fake_server_module

    monkeypatch.setitem(sys.modules, "mcp", fake_mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", fake_server_module)
    monkeypatch.setitem(sys.modules, "mcp.server.mcpserver", fake_mcpserver_module)

    project_root = Path(__file__).resolve().parents[1]
    module_path = project_root / "server.py"
    module_name = f"python_verification_gate_test_{next(_MODULE_COUNTER)}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def _stub_command_lookup(
    gate_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    command_map: dict[str, str],
) -> None:
    monkeypatch.setattr(gate_module.shutil, "which", command_map.get)


def _stub_subprocess_run(
    gate_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    expected_cwd: Path,
    stdout: str = "",
    *,
    stdout_by_command: dict[tuple[str, ...], str] | None = None,
    expect_virtual_env_removed: bool = False,
) -> None:
    """Replace subprocess.run with a fake that checks the call and returns canned output.

    With ``stdout_by_command``, only the listed commands are allowed and each returns its
    own output; any other command fails the test.
    """

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs.get("cwd") == expected_cwd
        if expect_virtual_env_removed:
            env = kwargs.get("env")
            assert isinstance(env, dict)
            assert "VIRTUAL_ENV" not in env

        if stdout_by_command is None:
            return _completed_process(command, stdout=stdout)
        if tuple(command) not in stdout_by_command:
            raise AssertionError(command)
        return _completed_process(command, stdout=stdout_by_command[tuple(command)])

    monkeypatch.setattr(gate_module.subprocess, "run", fake_run)


@pytest.fixture
def gate_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return _load_python_verification_gate_module(monkeypatch)


def test_given_format_recipe_when_running_format_check_then_just_runner_is_used(
    gate_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "Justfile").write_text("format:\n\t@echo format\n", encoding="utf-8")

    _stub_command_lookup(gate_module, monkeypatch, {"just": "/usr/bin/just"})

    _stub_subprocess_run(
        gate_module,
        monkeypatch,
        repo_path.resolve(),
        stdout_by_command={
            ("/usr/bin/just", "--list", "--unsorted"): "format\n",
            ("/usr/bin/just", "format"): "formatted\n",
        },
    )

    result = gate_module.run_format_check(str(repo_path))

    assert result["runner"] == "just"
    assert result["target"] == "format"
    assert result["used_fallback"] is False
    assert result["success"] is True
    assert result["command"] == ["/usr/bin/just", "format"]


def test_given_lint_target_when_running_ruff_check_then_make_runner_is_used(
    gate_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "Makefile").write_text("lint:\n\t@echo lint\n", encoding="utf-8")
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/bootstrap-venv")

    _stub_command_lookup(gate_module, monkeypatch, {"make": "/usr/bin/make"})

    _stub_subprocess_run(
        gate_module,
        monkeypatch,
        repo_path.resolve(),
        "linted\n",
        expect_virtual_env_removed=True,
    )

    result = gate_module.run_ruff_check(str(repo_path))

    assert result["runner"] == "make"
    assert result["target"] == "lint"
    assert result["used_fallback"] is False
    assert result["success"] is True
    assert result["command"] == ["/usr/bin/make", "lint"]


def test_given_project_virtual_environment_when_running_bandit_then_local_runner_is_used(
    gate_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "src").mkdir()
    bandit_path = repo_path / ".venv" / "bin" / "bandit"
    bandit_path.parent.mkdir(parents=True)
    bandit_path.write_text("#!/bin/sh\n", encoding="utf-8")
    bandit_path.chmod(0o755)
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/bootstrap-venv")

    _stub_command_lookup(gate_module, monkeypatch, {})

    _stub_subprocess_run(
        gate_module,
        monkeypatch,
        repo_path.resolve(),
        "secure\n",
        expect_virtual_env_removed=True,
    )

    result = gate_module.run_bandit(str(repo_path))

    assert result["runner"] == "project-venv"
    assert result["used_fallback"] is True
    assert result["success"] is True
    assert result["command"] == [str(bandit_path), "-r", "src"]


def test_given_uv_repository_when_running_mypy_then_uv_with_runner_is_used(
    gate_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "pyproject.toml").write_text("[project]\nname='repo'\n", encoding="utf-8")
    (repo_path / "src").mkdir()
    (repo_path / "tests").mkdir()
    (repo_path / "tests" / "__init__.py").write_text("", encoding="utf-8")

    _stub_command_lookup(gate_module, monkeypatch, {"uv": "/usr/bin/uv"})

    _stub_subprocess_run(gate_module, monkeypatch, repo_path.resolve(), "typed\n")

    result = gate_module.run_mypy(str(repo_path))

    assert result["runner"] == "uv-with"
    assert result["used_fallback"] is True
    assert result["success"] is True
    assert result["command"] == ["/usr/bin/uv", "run", "--with", "mypy", "mypy", "src", "tests"]


@pytest.mark.parametrize(
    ("marker_name", "launcher_name", "expected_runner"),
    [
        ("Pipfile", "pipenv", "pipenv"),
        ("poetry.lock", "poetry", "poetry"),
    ],
)
def test_given_repo_launcher_file_when_running_pytest_then_repo_launcher_is_used(
    gate_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    marker_name: str,
    launcher_name: str,
    expected_runner: str,
) -> None:
    repo_path = tmp_path / marker_name
    repo_path.mkdir()
    (repo_path / marker_name).write_text("", encoding="utf-8")

    _stub_command_lookup(gate_module, monkeypatch, {launcher_name: f"/usr/bin/{launcher_name}"})

    _stub_subprocess_run(gate_module, monkeypatch, repo_path.resolve(), "tested\n")

    result = gate_module.run_pytest(str(repo_path))

    assert result["runner"] == expected_runner
    assert result["used_fallback"] is True
    assert result["success"] is True
    assert result["command"] == [f"/usr/bin/{launcher_name}", "run", "pytest"]


def test_given_global_executable_when_running_format_check_then_global_runner_is_used(
    gate_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    _stub_command_lookup(gate_module, monkeypatch, {"ruff": "/usr/bin/ruff"})

    _stub_subprocess_run(gate_module, monkeypatch, repo_path.resolve(), "checked\n")

    result = gate_module.run_format_check(str(repo_path))

    assert result["runner"] == "global"
    assert result["used_fallback"] is True
    assert result["success"] is True
    assert result["command"] == ["/usr/bin/ruff", "format", "--check", "."]


def test_given_missing_runtime_when_running_ruff_check_then_unavailable_result_is_reported(
    gate_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    _stub_command_lookup(gate_module, monkeypatch, {})

    result = gate_module.run_ruff_check(str(repo_path))

    assert result["runner"] == "unavailable"
    assert result["used_fallback"] is True
    assert result["success"] is False
    assert result["exit_code"] == 127
    assert result["command"] == ["ruff", "check", "."]
    assert "Unable to resolve" in result["stderr"]


def test_given_missing_repository_when_running_test_then_value_error_is_raised(
    gate_module: ModuleType,
    tmp_path: Path,
) -> None:
    missing_repo_path = tmp_path / "missing-repo"

    with pytest.raises(ValueError, match="Invalid repository_path"):
        gate_module.run_test(str(missing_repo_path))


@pytest.mark.parametrize(
    ("alias_name", "canonical_name"),
    [
        ("run_ruff", "run_ruff_check"),
        ("run_format", "run_format_check"),
        ("run_pytest_check", "run_pytest"),
        ("run_type_check", "run_mypy"),
        ("run_bandit_check", "run_bandit"),
        ("run_test_check", "run_pytest"),
        ("run_mypy_check", "run_mypy"),
        ("run_lint_check", "run_ruff_check"),
        ("run_test", "run_pytest"),
        ("run_type", "run_mypy"),
        ("run_lint", "run_ruff_check"),
        ("run_formatting", "run_format_check"),
    ],
)
def test_given_alias_tool_when_called_then_canonical_tool_is_used(
    gate_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    alias_name: str,
    canonical_name: str,
) -> None:
    sentinel_result = {"tool": canonical_name}

    monkeypatch.setattr(gate_module, canonical_name, lambda _repository_path=".": sentinel_result)

    result = getattr(gate_module, alias_name)("/tmp/repository")

    assert result is sentinel_result


def test_given_main_when_called_then_stdio_transport_is_used(gate_module: ModuleType) -> None:
    gate_module.main()

    assert gate_module.mcp.run_calls == ["stdio"]
