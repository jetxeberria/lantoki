"""Tests for the Python verification gate MCP server."""

import importlib.util
import itertools
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


_MODULE_COUNTER = itertools.count()


class FakeFastMCP:
    def __init__(self, name: str) -> None:
        self.name = name
        self.registered_tools: list[str] = []
        self.run_calls: list[str] = []

    def tool(self):
        def decorator(function):
            self.registered_tools.append(function.__name__)
            return function

        return decorator

    def run(self, transport: str) -> None:
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
    fake_fastmcp_module = ModuleType("mcp.server.fastmcp")
    fake_fastmcp_module.FastMCP = FakeFastMCP
    fake_server_module.fastmcp = fake_fastmcp_module
    fake_mcp_module.server = fake_server_module

    monkeypatch.setitem(sys.modules, "mcp", fake_mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", fake_server_module)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fake_fastmcp_module)

    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "src" / "lantoki" / "python_verification_gate.py"
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
    monkeypatch.setattr(gate_module.shutil, "which", lambda command: command_map.get(command))


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

    def fake_run(command, cwd=None, check=False, capture_output=False, text=False, env=None):
        assert cwd == repo_path.resolve()

        if command == ["/usr/bin/just", "--list", "--unsorted"]:
            return _completed_process(command, stdout="format\n")

        if command == ["/usr/bin/just", "format"]:
            return _completed_process(command, stdout="formatted\n")

        raise AssertionError(command)

    monkeypatch.setattr(gate_module.subprocess, "run", fake_run)

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

    def fake_run(command, cwd=None, check=False, capture_output=False, text=False, env=None):
        assert cwd == repo_path.resolve()
        assert env is not None
        assert "VIRTUAL_ENV" not in env
        return _completed_process(command, stdout="linted\n")

    monkeypatch.setattr(gate_module.subprocess, "run", fake_run)

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

    def fake_run(command, cwd=None, check=False, capture_output=False, text=False, env=None):
        assert cwd == repo_path.resolve()
        assert env is not None
        assert "VIRTUAL_ENV" not in env
        return _completed_process(command, stdout="secure\n")

    monkeypatch.setattr(gate_module.subprocess, "run", fake_run)

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

    def fake_run(command, cwd=None, check=False, capture_output=False, text=False, env=None):
        assert cwd == repo_path.resolve()
        return _completed_process(command, stdout="typed\n")

    monkeypatch.setattr(gate_module.subprocess, "run", fake_run)

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

    def fake_run(command, cwd=None, check=False, capture_output=False, text=False, env=None):
        assert cwd == repo_path.resolve()
        return _completed_process(command, stdout="tested\n")

    monkeypatch.setattr(gate_module.subprocess, "run", fake_run)

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

    def fake_run(command, cwd=None, check=False, capture_output=False, text=False, env=None):
        assert cwd == repo_path.resolve()
        return _completed_process(command, stdout="checked\n")

    monkeypatch.setattr(gate_module.subprocess, "run", fake_run)

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

    monkeypatch.setattr(gate_module, canonical_name, lambda repository_path=".": sentinel_result)

    result = getattr(gate_module, alias_name)("/tmp/repository")

    assert result is sentinel_result


def test_given_main_when_called_then_stdio_transport_is_used(gate_module: ModuleType) -> None:
    gate_module.main()

    assert gate_module.mcp.run_calls == ["stdio"]
