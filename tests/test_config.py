"""Tests for application settings."""

from pathlib import Path

import pytest

from lantoki.config import PROJECT_ROOT, load_settings
from lantoki.exceptions import ConfigError


def test_given_default_settings_when_loading_then_paths_follow_project_and_xdg_defaults(home: Path) -> None:
    settings = load_settings()

    assert settings.sources_root == PROJECT_ROOT / "customizations"
    assert settings.providers_dir == PROJECT_ROOT / "src" / "lantoki" / "providers"
    assert settings.compiled_dir == home / ".local" / "share" / "lantoki" / "compiled"
    assert settings.manifests_dir == home / ".local" / "state" / "lantoki" / "manifests"
    assert settings.enabled_providers == ()


def test_given_xdg_and_lantoki_variables_when_loading_then_they_override_defaults(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("LANTOKI_SOURCES_ROOT", "{home}/my-sources")
    monkeypatch.setenv("LANTOKI_ENABLED_PROVIDERS", '@json ["claude-code"]')

    settings = load_settings()

    assert settings.compiled_dir == tmp_path / "data" / "lantoki" / "compiled"
    assert settings.sources_root == home / "my-sources"
    assert settings.enabled_providers == ("claude-code",)


@pytest.mark.parametrize(
    ("settings_text", "message"),
    [
        ('providers_dir = "x"\ncompiled_dir = "x"\nmanifests_dir = "x"\n', "Missing required setting: sources_root"),
        (
            'sources_root = "{nowhere}/x"\nproviders_dir = "x"\ncompiled_dir = "x"\nmanifests_dir = "x"\n',
            "Unknown placeholder 'nowhere' in setting 'sources_root'",
        ),
    ],
)
def test_given_incomplete_settings_file_when_loading_then_config_error_names_the_problem(
    home: Path,
    tmp_path: Path,
    settings_text: str,
    message: str,
) -> None:
    settings_file = tmp_path / "settings.toml"
    settings_file.write_text(settings_text, encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_settings(settings_file)

    assert home.is_dir()
