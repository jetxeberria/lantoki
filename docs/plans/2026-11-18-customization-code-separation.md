# Plan: customization code out of the core

| | |
|---|---|
| **Status** | Approved and executed 2026-11-18 |
| **Implements** | D-016 (SRC-9, CLI-2, DEV-7) in the [specification](../SPECIFICATION.md) |
| **Date** | 2026-11-18 |

## Starting point

Facts checked on 2026-11-18:

- `src/lantoki/python_verification_gate.py` (457 lines) is the MCP server declared in `customizations/user/mcp.toml` (`command = "python-verification-gate"`). It is the only module in `src/lantoki/` that belongs to a customization; nothing else in `src/` imports it.
- `pyproject.toml` exposes it as a second script of lantoki (`python-verification-gate = "lantoki.python_verification_gate:main"`), and `mcp>=2` is a runtime dependency of lantoki only because of it.
- `tests/test_python_verification_gate.py` (352 lines) loads the module by file path `src/lantoki/python_verification_gate.py`.
- Skills already follow the target rule: `customizations/project/skills/lint-python/run-linter.sh` sits in its skill folder.
- `sources.py` discovers only the known kind folders (`instructions`, `prompts`, `agents`, `skills`) and `mcp.toml`; an unknown folder like `servers/` is not read. To confirm with a test, not assume.
- `just init` runs the template's `install-tool-editable` (`uv tool install --editable .`, lantoki only), then `init-project` (today `sync-user`).
- References to the old location: `pyproject.toml`, `project.just` (comment), `README.md`, `docs/source-format.md`, `CHANGELOG.md` (history, left as is), `docs/SPECIFICATION.md` (updated in this change).

## Target layout

```
customizations/user/
  mcp.toml                                   # unchanged declaration
  servers/python-verification-gate/
    server.py                                # PEP 723 script: dependencies = ["mcp>=2"]
    tests/test_python_verification_gate.py
```

No second package and no second `pyproject.toml`: the owner rejected that first attempt. The script declares its own dependency inline and `uv` runs it.

## Phase 1: move the server (SRC-9)

1. `git mv` the module and its tests into the layout above, keeping history; add the PEP 723 header and shebang; mark it executable. Fix the test's module path.
2. lantoki's `pyproject.toml`: remove the `python-verification-gate` script and `mcp>=2`. The tests load `server.py` by path with a fake `mcp`, so the development environment needs nothing from the server.
3. Point pytest (`testpaths`) and coverage (`--cov`) at `customizations/` too, and bandit at the server scripts, so `just check` keeps covering them. Ruff `INP001` is ignored for server files: they are standalone, not packages.

**Check:** `just check` green, coverage ≥ 75 %; the wheel no longer requires `mcp` (`just check-package`).

## Phase 2: installation (CLI-2, DEV-7)

1. `project.just`: `install-servers` symlinks every `customizations/*/servers/<name>/server.py` to `~/.local/bin/<name>`; `install-tools` becomes `install-tool-editable install-servers`; `init-project` becomes `install-servers sync-user`.
2. Remove the earlier `uv tool` install of the server; verify the link starts and answers an MCP `initialize` and `tools/list`.

**Check:** `lantoki plan user` identical to the current output; golden tests unchanged.

## Phase 3: tests and docs

1. Test that `servers/` under a scope is ignored by the loader.
2. Update `README.md`, `docs/source-format.md`, `AGENTS.md` and the `project.just` comments.

## Risks

- **`uv` on `PATH`** is needed to run the server; `just init` installs it before `init-project`.
- **Template-owned lines.** `testpaths`/`--cov` are project configuration (DEV-4), not template-owned; the `Justfile` is not touched.
- **The running Claude Code session** uses the old executable until the MCP server is restarted.

## Results (2026-11-18)

- `just check` green; Ruff and bandit cover the server script.
- lantoki's wheel no longer requires `mcp`.
- `~/.local/bin/python-verification-gate` links to `server.py`; it answers MCP `initialize` and lists its 17 tools.
- `lantoki plan user`: 25 unchanged.

## Out of scope

- lantoki itself building or installing server projects during `sync` (a new core capability; would need its own decision).
- Moving the server to its own repository.
- Any change to the server's behaviour or tools.
