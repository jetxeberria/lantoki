"""Shared fixtures: an isolated home, a sample source tree and the fictional ``acme`` provider."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from lantoki.app import Workspace
from lantoki.config import load_settings


FIXTURES = Path(__file__).resolve().parent / "fixtures"
FAKE_PROVIDERS_DIR = FIXTURES / "providers"
REAL_PROVIDERS_DIR = Path(__file__).resolve().parents[1] / "src" / "lantoki" / "providers"

SAMPLE_SOURCES = {
    "user/instructions/general.md": "---\ndescription: Applies everywhere\n---\nBe kind.\n",
    "user/instructions/python.md": (
        "---\ndescription: Python rules\ntitle: Python Standards\n"
        "applies_to: ['**/*.py', '**/*.pyi']\n---\nUse types.\n"
    ),
    "user/prompts/review.md": (
        "---\ndescription: Review code\nargument_hint: path\ntools: [read, 'mcp:gate/*']\n"
        "overrides:\n  acme:\n    color: blue\n---\nReview {{arguments}} now.\n"
    ),
    "user/agents/helper.md": (
        "---\ndescription: Helps\ntools: [read, search, execute, 'mcp:gate/run_lint']\n---\nHelp with {{arguments}}.\n"
    ),
    "user/skills/demo/SKILL.md": "---\nname: demo\ndescription: Demo skill\n---\nDo demo things.\n",
    "user/mcp/gate/server.toml": ('command = "gate"\nargs = ["--fast"]\nenv = { TOKEN = "{{env:GATE_TOKEN}}" }\n'),
    "user/mcp/gate/server.py": "print('the server code is not a source')\n",
    "user/mcp/gate/tests/test_gate.py": "def test_gate() -> None: ...\n",
    "project/repo-instructions.md": "---\ndescription: Repo rules\n---\nKeep it tidy.\n",
    "project/instructions/python.md": "---\ndescription: Py\napplies_to: ['**/*.py']\n---\nTyped.\n",
    "project/instructions/airflow.md": "---\ndescription: Airflow\napplies_to: ['dags/**']\n---\nDAGs.\n",
    "project/prompts/docs.md": "---\ndescription: Write docs\n---\nDocument {{arguments}}.\n",
    "project/skills/lint/SKILL.md": "---\nname: lint\ndescription: Lint\n---\nRun the linter.\n",
    "project/mcp/db/server.toml": 'command = "db-mcp"\n',
}


def write_tree(root: Path, files: dict[str, str]) -> Path:
    """Write ``files`` (relative path -> text) under ``root``."""
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


@dataclass
class FakeRunner:
    """Records CLI calls instead of running them (QLT-5)."""

    returncode: int = 0
    calls: list[list[str]] = field(default_factory=list)

    def __call__(self, argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        """Record the call and succeed, or fail with ``returncode`` for non-removal commands."""
        self.calls.append(list(argv))
        failing = self.returncode if "rm" not in argv and "remove" not in argv else 0
        return subprocess.CompletedProcess(argv, failing, "", "boom" if failing else "")


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide an empty home directory as HOME, with XDG dirs inside it."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    for name in ("SOURCES_ROOT", "PROVIDERS_DIR", "COMPILED_DIR", "MANIFESTS_DIR", "ENABLED_PROVIDERS"):
        monkeypatch.delenv(f"LANTOKI_{name}", raising=False)
    return home_dir


@pytest.fixture
def sources_root(tmp_path: Path) -> Path:
    """Write a sample source tree covering every kind and both scopes."""
    return write_tree(tmp_path / "customizations", SAMPLE_SOURCES)


@pytest.fixture
def acme_env(home: Path, sources_root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point lantoki at the sample sources and the fictional ``acme`` provider only."""
    monkeypatch.setenv("LANTOKI_SOURCES_ROOT", str(sources_root))
    monkeypatch.setenv("LANTOKI_PROVIDERS_DIR", str(FAKE_PROVIDERS_DIR))
    return home


@pytest.fixture
def acme_workspace(acme_env: Path) -> Workspace:
    """Load a workspace with the sample sources and the ``acme`` provider."""
    del acme_env
    return Workspace.load(load_settings())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Provide an empty target repository."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    return repo_dir
