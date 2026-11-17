"""Tests for provider profiles (SPECIFICATION §6)."""

import tomllib
lazy from pathlib import Path

import pytest
import tomli_w

from lantoki.exceptions import ProfileError
from lantoki.profiles import load_profile, load_profiles
from lantoki.sources import Kind, Scope
from tests.conftest import FAKE_PROVIDERS_DIR, REAL_PROVIDERS_DIR


def _acme() -> dict[str, object]:
    return tomllib.loads((FAKE_PROVIDERS_DIR / "acme.toml").read_text(encoding="utf-8"))


def _write_profile(directory: Path, data: dict[str, object], name: str = "acme") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.toml"
    path.write_text(tomli_w.dumps(data), encoding="utf-8")
    return path


@pytest.mark.parametrize("provider_id", ["claude-code", "github-copilot"])
def test_given_shipped_profile_when_loading_then_it_is_valid_and_covers_every_kind(provider_id: str) -> None:
    profile = load_profile(REAL_PROVIDERS_DIR / f"{provider_id}.toml")

    user_kinds = {output.kind for output in profile.outputs_for(Scope.USER)}
    project_kinds = {output.kind for output in profile.outputs_for(Scope.PROJECT)}
    assert profile.id == provider_id
    assert profile.provider.docs
    assert user_kinds == set(Kind) - {Kind.REPO_INSTRUCTIONS}
    assert project_kinds == set(Kind) - {Kind.AGENT}


def test_given_directory_and_enabled_ids_when_loading_then_only_enabled_profiles_are_returned(tmp_path: Path) -> None:
    _write_profile(tmp_path, _acme())
    other = _acme() | {"provider": {**_acme()["provider"], "id": "other"}}  # type: ignore[dict-item]
    _write_profile(tmp_path, other, "other")

    assert [profile.id for profile in load_profiles(tmp_path)] == ["acme", "other"]
    assert [profile.id for profile in load_profiles(tmp_path, ("other",))] == ["other"]


def _break(path: tuple[str, ...], value: object) -> dict[str, object]:
    data = _acme()
    node: dict[str, object] = data
    for key in path[:-1]:
        node = node[key] if not key.isdigit() else node[int(key)]  # type: ignore[index,assignment]
    if value is None:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return data


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (_break(("provider", "id"), "renamed"), "must match the file name"),
        (_break(("provider", "id"), "Bad Id"), "provider id must match"),
        (_break(("provider", "surprise"), 1), "Extra inputs are not permitted"),
        (_break(("provider", "docs"), []), "at least 1 item"),
        (_break(("tools", "map", "teleport"), ["x"]), "unknown neutral tools"),
        (_break(("cli", "candidates"), []), "command outputs require"),
        (_acme() | {"outputs": [{"kind": "skill", "scope": "user", "format": "markdown", "target": "x"}]}, "supports"),
        (_acme() | {"outputs": [{"kind": "mcp", "scope": "user", "format": "json", "target": "x"}]}, "root_key"),
        (_acme() | {"outputs": [{"kind": "agent", "scope": "user", "format": "markdown"}]}, "requires target"),
        (_acme() | {"outputs": []}, "at least 1 item"),
        (
            _acme()
            | {"outputs": [{"kind": "skill", "scope": "user", "format": "directory", "target": "x", "file": "a"}]},
            "only applies to markdown",
        ),
        (
            _acme()
            | {"outputs": [{"kind": "agent", "scope": "user", "format": "markdown", "target": "x", "file": "a/b"}]},
            "plain file name",
        ),
    ],
)
def test_given_invalid_profile_when_loading_then_profile_error_explains_it(
    tmp_path: Path,
    data: dict[str, object],
    expected: str,
) -> None:
    _write_profile(tmp_path, data)

    with pytest.raises(ProfileError, match=expected):
        load_profiles(tmp_path)


def test_given_command_output_with_copy_link_when_loading_then_it_is_rejected(tmp_path: Path) -> None:
    data = _acme()
    command = next(output for output in data["outputs"] if output["format"] == "command")  # type: ignore[attr-defined]
    command["link"] = "copy"
    _write_profile(tmp_path, data)

    with pytest.raises(ProfileError, match="'link' does not apply"):
        load_profiles(tmp_path)


@pytest.mark.parametrize(
    ("setup", "expected"),
    [
        (lambda directory: (directory / "acme.toml").write_text("[provider\n", encoding="utf-8"), "cannot read"),
        (lambda _directory: None, "No provider profiles found"),
        (lambda directory: _write_profile(directory, _acme()), "Enabled providers without a profile"),
    ],
)
def test_given_unusable_profile_directory_when_loading_then_profile_error_is_raised(
    tmp_path: Path,
    setup: object,
    expected: str,
) -> None:
    tmp_path.mkdir(exist_ok=True)
    setup(tmp_path)  # type: ignore[operator]

    with pytest.raises(ProfileError, match=expected):
        load_profiles(tmp_path, ("missing",) if "Enabled" in expected else ())
