set shell := ["bash", "-euo", "pipefail", "-c"]

# Exits the shebang recipe successfully when the project declares no commands
require_scripts := "grep -q '^\\[project.scripts\\]' pyproject.toml || { " + info + " 'no [project.scripts] in pyproject.toml: no commands to install'; exit 0; }"

import 'tooling.just'

# Project-owned recipes: add them to project.just, never to this file (JUS-1)
import? 'project.just'

# List available recipes
default:
    @just --list --unsorted

# Make this checkout ready to work, on a new machine too; safe to run again (INI-1)
init: init-git install install-tool-editable init-hook init-ai check
    @{{ info }} "ready to work"

# Create the git repository and stage the files, unless it already exists
init-git:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    if git rev-parse --git-dir >/dev/null 2>&1; then
        {{ info }} "already a git repository, skipping"
        exit 0
    fi
    run git init
    run git add -A -v
    {{ info }} "staged files are ready for the first commit"

# Run the project's own setup (recipe init-project in project.just), if it defines one
init-hook:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    if ! just --show init-project >/dev/null 2>&1; then
        {{ info }} "project.just defines no init-project recipe, skipping"
        exit 0
    fi
    run just init-project

# Install the AI-assistant customization for this repository with lantoki, when installed
init-ai:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    if ! command -v lantoki >/dev/null 2>&1; then
        {{ warn }} "lantoki not found, skipping the AI-assistant setup; to get it:"
        {{ warn }} "  git clone git@github.com:jetxeberria/lantoki.git ~/repos/lantoki && just -f ~/repos/lantoki/Justfile init"
        exit 0
    fi
    {{ info }} "asks once per machine which project sources apply (lantoki sync repo . --select to change)"
    run lantoki sync repo .

# Run every check: formatting, linters, tests and the package on its own
check: fmt-check lint test check-package
    @{{ info }} "all checks passed"

# Run the test suite (extra arguments go to pytest)
test *args:
    @{{ info }} "config: [tool.pytest.ini_options] in pyproject.toml"
    pdm run pytest {{ args }}

# Add dependencies, e.g. `just add requests` or `just add -dG dev pytest-cov`
add +args:
    @{{ info }} "edits pyproject.toml and pdm.lock, then syncs both environments"
    pdm add --no-sync {{ args }}
    just sync

# Remove dependencies, e.g. `just remove requests`
remove +args:
    @{{ info }} "edits pyproject.toml and pdm.lock, then syncs both environments"
    pdm remove --no-sync {{ args }}
    just sync

# Upgrade dependencies (all of them when none are given)
upgrade *args:
    @{{ info }} "within the pyproject.toml constraints; rewrites pdm.lock, then syncs both environments"
    pdm update --no-sync {{ args }}
    just sync

# Update from the template and leave a working repository: merge, relock, reinstall, check.
# Extra arguments go to copier, e.g. `just update --data python_min=3.16`
update *args:
    @{{ info }} "two just runs: the second one uses the recipes the merge just brought in"
    just update-template {{ args }}
    just update-sync

# Finish a template update: stop on conflicts, relock, reinstall, check
update-sync: update-conflicts install-plugins sync install-hooks check
    @{{ info }} "review the changes, then commit them together with pdm.lock"

# Apply the latest template changes with copier (needs a clean working tree)
update-template *args:
    @{{ info }} "answers from .copier-answers.yml unless overridden; needs a clean working tree"
    pdm run copier update --defaults {{ args }}

# Fail if the template merge left conflict markers
update-conflicts:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    {{ info }} "copier marks the lines it could not merge with 'before updating' / 'after updating'"
    if run git grep -nE '^(<{7} before updating|>{7} after updating)'; then
        {{ warn }} "resolve the conflicts above, then run: just update-sync"
        exit 1
    fi
    if run git ls-files --others --exclude-standard -- '*.rej' | grep .; then
        {{ warn }} "resolve the rejected hunks above (*.rej), then run: just update-sync"
        exit 1
    fi

# Bump the version: major, minor, micro, pre-release, no-pre-release, ... (see `pdm bump -h`)
bump part:
    @{{ info }} "rewrites version in pyproject.toml (pdm-bump plugin)"
    pdm bump {{ part }}

# Build the sdist and wheel into dist/
build:
    @{{ info }} "output in dist/ (cleaned first)"
    pdm build

# Build the package and install its [project.scripts] on PATH from the wheel (uv tool)
install-tool:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    {{ require_scripts }}
    run just build
    wheels=(dist/*.whl)
    [ ${#wheels[@]} -eq 1 ] || { {{ warn }} "expected one wheel in dist/, found ${#wheels[@]}"; exit 1; }
    {{ info }} "installed as a user would get it (production requirements, ranges resolved by uv); run it again to pick up code changes"
    run uv tool install --force "${wheels[0]}"

# Install [project.scripts] on PATH from the sources, for development: edits apply without reinstalling
install-tool-editable:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    {{ require_scripts }}
    {{ info }} "editable: the commands follow the working tree; reinstall after changing [project.scripts]"
    run uv tool install --force --editable .

# Install the built package alone in a throwaway environment: it must import and load its commands (ENV-5)
check-package:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    run just build
    wheels=(dist/*.whl)
    [ ${#wheels[@]} -eq 1 ] || { {{ warn }} "expected one wheel in dist/, found ${#wheels[@]}"; exit 1; }
    version=$(sed -nE 's/^requires-python = ">=([0-9]+\.[0-9]+)"$/\1/p' pyproject.toml)
    mapfile -t modules < <(find src -mindepth 2 -maxdepth 2 -name __init__.py -printf '%h\n' | xargs -rn1 basename | sort)
    [ ${#modules[@]} -gt 0 ] || { {{ warn }} "no package under src/ to import"; exit 1; }
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    {{ info }} "only the wheel and its production requirements; removed on exit"
    run uv venv --quiet --python "$version" "$tmp/venv"
    run uv pip install --quiet --python "$tmp/venv/bin/python" "${wheels[0]}"
    dist=$(basename "${wheels[0]}" | cut -d- -f1)
    run "$tmp/venv/bin/python" - "$dist" "${modules[@]}" <<'PY'
    import importlib
    import importlib.metadata
    import sys

    dist, *modules = sys.argv[1:]
    for module in modules:
        importlib.import_module(module)
        print(f"import {module}: ok")
    for entry in importlib.metadata.distribution(dist).entry_points.select(group="console_scripts"):
        entry.load()
        print(f"command {entry.name} -> {entry.value}: ok")
    PY

# Remove the commands installed by install-tool or install-tool-editable
uninstall-tool:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    name=$(sed -nE 's/^name = "(.*)"$/\1/p' pyproject.toml | head -n 1)
    if ! uv tool list | grep -q "^$name "; then
        {{ info }} "$name is not installed as a uv tool, nothing to do"
        exit 0
    fi
    run uv tool uninstall "$name"

# Remove build artefacts and caches
clean:
    rm -rfv {{ build_dir }} dist .pytest_cache .ruff_cache
    find . -path ./.venv -prune -o -type d -name __pycache__ -prune -print -exec rm -rf {} +
