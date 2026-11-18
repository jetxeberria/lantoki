# Plan: one folder per MCP server

| | |
|---|---|
| **Status** | Approved and executed 2026-11-18 |
| **Implements** | D-017 (SRC-7, SRC-2, SRC-9, CLI-2) in the [specification](../SPECIFICATION.md) |
| **Depends on** | D-016, the [separation plan](2026-11-18-customization-code-separation.md), committed first on its own |
| **Date** | 2026-11-18 |

## Starting point

Facts checked on 2026-11-18:

- `sources._Loader.load_mcp` reads `<scope>/mcp.toml`, validates each `[servers.<name>]` table with `McpServer` (`command`, `args`, `env`, `extra="forbid"`) and creates one `Source(Kind.MCP, scope, name, path=<mcp.toml>, server=…)` per server.
- An MCP source's `path` is used only for markdown provenance (`compiler._provenance`) and directory links (`compiler._directory`); MCP outputs are `json` aggregates and CLI registrations, so the compiled content does not depend on it.
- `customizations/user/mcp.toml` declares `python-verification-gate`; `customizations/project/mcp.toml` holds only a commented example. The server's code is in `customizations/user/servers/python-verification-gate/` (D-016).
- Tests that write `mcp.toml`: `tests/conftest.py` (sample tree: `gate` in user, `db` in project), `tests/test_sources.py` (two error cases), `tests/test_installer.py:223` (empty user `mcp.toml`). Golden sources: `tests/fixtures/golden/sources/{user,project}/mcp.toml`.
- `project.just` `install-servers` globs `customizations/*/servers/*/server.py`; `pyproject.toml` (Ruff `INP001`, coverage `omit`) and `just security` use the same path.

## Target layout

```
customizations/user/mcp/python-verification-gate/
  server.toml                                # command = "python-verification-gate", args = []
  server.py                                  # PEP 723 script (D-016)
  tests/test_python_verification_gate.py
```

No `customizations/*/mcp.toml` and no `servers/` folder remain.

## Phase 1: loader (SRC-7, SRC-2)

1. Tests first, in `tests/test_sources.py`:
   - a folder with `server.toml` becomes an `mcp` source named after the folder, with `path` the folder;
   - a folder without `server.toml`, an invalid name, invalid TOML, a missing `command` and an unknown key each give an error naming the file;
   - a scope-level `mcp.toml` fails validation, naming `mcp/<name>/server.toml` for each server it declares;
   - `server.py` and `tests/` beside `server.toml` are ignored.
2. `sources.py`: replace `load_mcp` with a folder loader modelled on `load_skills`; `MCP_FILE` becomes `MCP_DIR = "mcp"` and `SERVER_FILE = "server.toml"`; a leftover `mcp.toml` is reported. The `McpServer` model is unchanged.
3. Move the sample tree in `conftest.py`, the error cases and `test_installer.py` to the folder form. Remove the "`servers/` is ignored" test, replaced by the one above.

**Check:** `just test`.

## Phase 2: move the sources

1. `git mv customizations/user/servers/python-verification-gate customizations/user/mcp/python-verification-gate`; write its `server.toml` from the `mcp.toml` entry; delete both `customizations/*/mcp.toml`.
2. Golden sources: `tests/fixtures/golden/sources/user/mcp/python-verification-gate/server.toml`; delete both golden `mcp.toml`.
3. Paths: `install-servers` globs `customizations/*/mcp/*/server.py`; update `pyproject.toml` (Ruff per-file ignore, coverage `omit`) and `just security`.

**Check:** `just check` green; golden tests unchanged (compiled output identical); `lantoki plan user` reports 25 unchanged; `just install-servers` relinks `~/.local/bin/python-verification-gate` to the new path and the server answers MCP `initialize` and `tools/list`.

## Phase 3: docs

`docs/source-format.md` (MCP section and layout), `README.md` (kinds table), `AGENTS.md` (where things are), `sources.py` module docstring, and the D-016 plan's layout note pointing to D-017.

**Check:** `just docs-build`.

## Risks

- **Manifest entries record the source key (`mcp:<name>`), not its path**, so moving the declaration must not cause updates or prunes. Verified by `lantoki plan user` before `sync`.
- **The old symlink** in `~/.local/bin` points to the moved `server.py` until `install-servers` relinks it; Phase 2 does that.
- **Projects already synced** with an MCP selection in their manifest keep the same key; no re-selection needed.

## Results (2026-11-18)

- `just check` green: 151 tests, coverage 97 %.
- `lantoki plan user`: 25 unchanged; golden tests unchanged.
- `~/.local/bin/python-verification-gate` relinked to `customizations/user/mcp/python-verification-gate/server.py`; it answers MCP `initialize` and lists its 17 tools.
- `just docs-build` fails, before and after this change, because `mkdocs.yml` sets a `custom_dir` (`docs/theme`) that does not exist. Not caused by this plan; left as is.

## Out of scope

- Per-server metadata beyond `command`, `args`, `env` (description, per-provider overrides).
- lantoki itself linking server scripts during `sync` (would be a new core capability).
