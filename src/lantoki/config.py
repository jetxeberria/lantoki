"""Application settings: where sources, profiles, compiled artifacts and manifests live."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dynaconf import Dynaconf

from lantoki.exceptions import ConfigError


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent.parent
SETTINGS_FILE = PACKAGE_DIR / "settings.toml"

_REQUIRED_PATH_KEYS = ("sources_root", "providers_dir", "compiled_dir", "manifests_dir")


@dataclass(frozen=True)
class Settings:
    """Resolved application settings."""

    project_root: Path
    sources_root: Path
    providers_dir: Path
    compiled_dir: Path
    manifests_dir: Path
    enabled_providers: tuple[str, ...]


def _placeholders() -> dict[str, str]:
    """Return the values available to path templates in the settings file."""
    home = Path.home()
    return {
        "home": str(home),
        "project_root": str(PROJECT_ROOT),
        "package_dir": str(PACKAGE_DIR),
        "xdg_data_home": os.environ.get("XDG_DATA_HOME") or str(home / ".local" / "share"),
        "xdg_state_home": os.environ.get("XDG_STATE_HOME") or str(home / ".local" / "state"),
    }


def _resolve(template: str, placeholders: dict[str, str], key: str) -> Path:
    """Expand a path template, naming the key when a placeholder is unknown."""
    try:
        return Path(template.format(**placeholders)).expanduser()
    except KeyError as error:
        msg = f"Unknown placeholder {error.args[0]!r} in setting {key!r}"
        raise ConfigError(msg, key=key) from error


def load_settings(settings_file: Path = SETTINGS_FILE) -> Settings:
    """Load settings from the settings file and LANTOKI_* environment variables.

    Raises:
        ConfigError: A required setting is missing or a path template is invalid.
    """
    raw = Dynaconf(envvar_prefix="LANTOKI", settings_files=[str(settings_file)])
    placeholders = _placeholders()

    paths: dict[str, Path] = {}
    for key in _REQUIRED_PATH_KEYS:
        value = raw.get(key)
        if not value:
            msg = f"Missing required setting: {key}"
            raise ConfigError(msg, key=key, settings_file=str(settings_file))
        paths[key] = _resolve(str(value), placeholders, key)

    enabled = raw.get("enabled_providers") or []
    return Settings(
        project_root=PROJECT_ROOT,
        enabled_providers=tuple(str(provider) for provider in enabled),
        **paths,
    )
