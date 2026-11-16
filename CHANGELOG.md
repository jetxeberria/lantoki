# Changelog

## Unreleased

### Added

* Master specification `docs/SPECIFICATION.md` with numbered, justified requirements and a decision log (D-001 … D-011).
* Provider-agnostic core: neutral sources (`customizations/`), declarative provider profiles (`src/lantoki/providers/*.toml`), compiler, installer with manifest-based ownership, adoption and pruning.
* Profiles for Claude Code and GitHub Copilot; adding a provider is adding one profile file.
* `lantoki` CLI: `validate`, `providers`, `plan`, `sync` (user and repo scopes); `just` recipes.
* `markdown` outputs accept `file`: the target is a folder holding that one generated file, linked as a whole. Claude Code prompts now install as a `skills/<name>` symlink, like every other skill (D-011).

### Changed

* Sources migrated from Copilot's dialect to the neutral format.
* `python-verification-gate` runs as an installed command on mcp 2.x.

### Removed

* `setup_copilot.py`/`.toml`/`.sh` and the Copilot-only source tree `copilot-instructions-set/`.

## 0.1.0 (2026-03-11)

### Added

* Created project boilerplate.
