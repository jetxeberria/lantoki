# Changelog

## Unreleased

### Added

* Master specification `docs/SPECIFICATION.md` with numbered, justified requirements and a decision log (D-001 … D-018).
* Provider-agnostic core: neutral sources (`customizations/`), declarative provider profiles (`src/lantoki/providers/*.toml`), compiler, installer with manifest-based ownership, adoption and pruning.
* Profiles for Claude Code and GitHub Copilot; adding a provider is adding one profile file.
* `lantoki` CLI: `validate`, `providers`, `plan`, `sync` (user and repo scopes); `just` recipes.
* `markdown` outputs accept `file`: the target is a folder holding that one generated file, linked as a whole. Claude Code prompts now install as a `skills/<name>` symlink, like every other skill (D-011).
* `lantoki sync repo` keeps its outputs out of git through a managed block in `.git/info/exclude` (D-015, INS-9).
* `just init` reproduces the whole setup on a new machine (D-014, DEV-7); `just install-servers` links every MCP server script onto `PATH` (CLI-2).

### Changed

* Sources migrated from Copilot's dialect to the neutral format.
* Development tooling follows the galtzagorri template: PDM + just, Python ≥ 3.15 (D-012, DEV-1 … DEV-6); lantoki's own recipes live in `project.just` (D-013, DEV-4).
* `python-verification-gate` moved out of `src/lantoki/` into `customizations/user/mcp/python-verification-gate/` as a PEP 723 script on mcp 2.x; `mcp` is no longer a lantoki dependency (D-016, SRC-9).
* MCP servers are declared one folder each, `<scope>/mcp/<name>/server.toml`; a scope-level `mcp.toml` fails validation (D-017, SRC-7).
* Every test lives under the root `tests/` folder, customization tests in `tests/customizations/` (D-018, QLT-6).

### Removed

* `setup_copilot.py`/`.toml`/`.sh` and the Copilot-only source tree `copilot-instructions-set/`.
* `uv.lock` and the `[tool.uv]` configuration, replaced by `pdm.lock` (D-012, DEV-2).
* The executed implementation plans under `docs/plans/`; their decisions are in the specification.

## 0.1.0 (2026-03-11)

### Added

* Created project boilerplate.
