# Plan: adopt the galtzagorri template

| | |
|---|---|
| **Status** | Proposed, awaiting approval |
| **Implements** | D-012 (DEV-1 … DEV-6 in the [specification](../SPECIFICATION.md#91-development-tooling)) |
| **Date** | 2026-11-17 |

The specification says *what* changes and *why*. This plan says *how*, in what order, and how each step is verified. No code changes before it is approved.

## Starting point

Facts checked on 2026-11-17:

- lantoki uses uv (`uv.lock`, `[tool.uv]`), a hand-written Justfile, `uv_build`, commitizen config, and Python `>=3.12,<3.13`.
- It was not generated from galtzagorri: there is no `.copier-answers.yml`, so `just update` cannot apply.
- **Python 3.15:** every runtime, dev and docs dependency installs on 3.15.2, and all 133 tests pass. PyYAML has no 3.15 wheel, so it is built from source as the pure-Python parser.
- **Template checks run on today's files:**
  - Ruff on the whole repository passes.
  - Shellcheck and shfmt pass on both `.sh` files.
  - yamllint finds 3 issues in `mkdocs.yml`.
  - One JSON fixture is not jq-formatted: `tests/fixtures/baseline/v0-installer-output.json`. The golden tests parse it with `json.loads`, so reformatting it is safe.

## Phases

Each phase ends with its check and its own commit citing D-012 / DEV-x. The work happens on a branch, `chore/adopt-galtzagorri`, merged when Phase 5 passes.

### Phase 0: galtzagorri prerequisites (separate repository)

**0.1 A specification for galtzagorri.** galtzagorri has none. Following the spec-first rule, it gets a `docs/SPECIFICATION.md`. It records the decisions already made (`base` group, `python_min`, self-checking `just update`) and the one below, each with its reason.

**0.2 Packaging as a template answer (DEV-5).** A boolean copier question, `packaged` (default `false`). When it is `true`:

- The template renders `distribution = true` and a `[build-system]` using `pdm-backend`.
- It adds an `install-tool` recipe running `uv tool install --editable .`.

The project still declares its own `[project.scripts]`.

**Why do this in the template?** Without it, lantoki would have to change the template's own lines. Every update that touches them would then conflict. harness-harvest needs the same thing: its MDD distributes it with `uv tool install`.

**Check:** galtzagorri's `just check`, which renders the template both with `packaged=false` and with `packaged=true` and runs the generated project's checks.

**If you decline 0.2,** lantoki edits `distribution` and `[build-system]` by hand and resolves the resulting conflicts on each update.

### Phase 1: link to the template

**Command:**

```bash
pdm run copier copy --overwrite gh:jetxeberria/galtzagorri . \
  --data project_name=lantoki --data python_min=3.15 --data packaged=true \
  --data "project_description=<current description>"
```

Then reconcile every file with `git diff` against the table below:

| File | Decision | Reason |
|---|---|---|
| `.copier-answers.yml`, `tooling.just`, `pdm.toml`, `.editorconfig`, `.yamlfmt.yaml`, `.yamllint.yaml`, `.clang-format`, `.gitattributes` | take the template's | template-owned (DEV-1) |
| `.pre-commit-config.yaml` | take the template's (one `just check` hook) | same checks as before plus YAML/JSON/shell (DEV-4) |
| `.gitignore` | template's, plus lantoki's extra entries (`docs/_build/`, `public/`, `.env`, …) | both sets are needed |
| `pyproject.toml` | template skeleton, plus lantoki's metadata, `dependencies`, `[project.scripts]`, `dev` and `docs` groups, Ruff `ALL` (line length 120) and pytest/coverage options; drop `[tool.uv]`, `[tool.commitizen]` and `uv_build` | DEV-2, DEV-4, DEV-5 |
| `Justfile` | template's, plus lantoki recipes below the project marker (mapping below) | DEV-4 |
| `README.md` | lantoki's text, with Prerequisites/Quickstart replaced by the template's *Getting started*, *Dependencies* and *Template updates* | the template's sections describe the new tooling |
| `LICENSE` | template's (adds the owner's name) | same MIT text |
| `src/lantoki/__init__.py`, `tests/__init__.py` | keep lantoki's | lantoki's code |
| `tests/test_package.py` | take the template's | trivial import smoke test, owned by the template |
| `docs/.gitkeep` | do not add | `docs/` already exists |
| `uv.lock` | delete | replaced by `pdm.lock` (DEV-2) |

**How the `dev` group splits:**

- `pytest`, `ruff` and `pre-commit` move out of it: they come from `base`.
- `bandit`, `coverage`, `pytest-cov`, `pytest-html`, `pytest-randomly`, `pytest-xdist` and `tomli-w` stay in lantoki's `dev` group.

**Recipe mapping:**

| Today | After | Note |
|---|---|---|
| `setup`, `setup-env`, `env-sync`, `check-git-lfs`, `setup-git-lfs` | `just install` (or `install-env`) | template |
| `setup-git` | `just install-hooks` | template |
| `env-lock` / `env-list` / `env-add` / `env-update` | `pdm lock` / `pdm list --tree` / `just add` / `just upgrade` | template |
| `version-bump` (commitizen) | `just bump` (pdm-bump) | template; commitizen is not installed today anyway |
| `format` / `format --check` / `lint --fix` | `just fmt` / `just fmt-check` / `just fix` | template |
| `lint` | `just lint` | template; it now also checks YAML, JSON, shell and C |
| `test` (coverage flags in the recipe) | `just test` (flags in `[tool.pytest.ini_options] addopts`) | DEV-4 |
| `check` (format + lint) | `just check` (fmt-check + lint + test) | template; tests run on every push, as today |
| `clean` | `just clean` + project `clean-docs` (`docs/_build`, `public/`) | the template's `clean` does not know lantoki's report folders |
| `validate`, `providers`, `plan-user`, `sync-user`, `sync-repo`, `install-tools`, `security`, `docs`, `docs-build`, `docs-serve` | kept, `uv run` → `pdm run` | lantoki-specific |
| `version`, `check-direnv`, `clean-env` | dropped | no `.envrc` is tracked; `pdm show --version`; `rm -rf .venv` |

**Check:**

```bash
just install && pdm run pytest -q
```

### Phase 2: pass the template's checks

**Fixes:**

- The 3 yamllint issues in `mkdocs.yml`.
- `jq --indent 2` on the baseline JSON fixture.

**Check:** `just check` passes. That means formatting, Ruff, shell, YAML, JSON and tests with coverage ≥ 75 %.

### Phase 3: documentation

- `AGENTS.md` *Working on this repo*: change `uv + just` to `PDM + just (galtzagorri template; just update)`.
- README: the new sections.
- Any `uv run` left in the docs.

**Check:** `grep -rn "uv run\|uv sync\|uv lock" --exclude-dir=.venv .` finds nothing.

### Phase 4: prove nothing else changed (DEV-6)

1. Before Phase 1, save `lantoki plan user` and `lantoki plan repo <repo> --all` for one project as a baseline.
2. After Phase 3, run them again. The output must be identical, and the golden tests must pass.
3. `just install-tools`, then `lantoki --help` and `python-verification-gate --help` run from `PATH`.

### Phase 5: prove updates work (DEV-1)

1. Commit, then run `just update`. With no new template change it must finish with *all checks passed* and an empty `git status`.
2. Push. The pre-push hook runs `just check`.

## Risks

| Risk | Mitigation |
|---|---|
| Running one test file (`just test tests/test_x.py`) fails the 75 % coverage gate, because the gate now lives in `addopts` | Use `just test --no-cov tests/test_x.py`. Documented in `AGENTS.md`. |
| A template change to its Ruff or pytest lines conflicts with lantoki's override | `just update` stops at the conflict marker. Keep lantoki's values and run `just update-sync`. |
| PyYAML runs without its C extension on 3.15 | Acceptable for lantoki's file sizes. A 3.15 wheel will remove it when released. |
| `mkdocs build` may already be broken (its `nav` points to pages that do not exist) | Not caused by this migration. Record today's result before Phase 1 and compare. Fixing it is separate work. |

## Out of scope

- Behaviour changes to lantoki itself: sources, profiles, compiler, installer.
- Fixing the documentation site (see Risks).
