set shell := ["bash", "-euo", "pipefail", "-c"]

import 'tooling.just'

# Rendered only for packaged projects (template answer `packaged`)
import? 'packaging.just'

# Project-owned recipes: add them to project.just, never to this file (JUS-1)
import? 'project.just'

# List available recipes
default:
    @just --list --unsorted

# Initialise git and its hooks (run once, right after generating the project)
init: init-git install-hooks

# Create the git repository and stage the generated files
init-git:
    @{{ info }} "staged files are ready for the first commit"
    git init
    git add -A -v

# Run every check: formatting, linters and tests
check: fmt-check lint test
    @{{ info }} "all checks passed"

# Run the test suite (extra arguments go to pytest)
test *args:
    @{{ info }} "config: [tool.pytest.ini_options] in pyproject.toml"
    pdm run pytest {{ args }}

# Add dependencies, e.g. `just add requests` or `just add -dG dev pytest-cov`
add +args:
    @{{ info }} "updates pyproject.toml and pdm.lock, then installs"
    pdm add {{ args }}

# Remove dependencies, e.g. `just remove requests`
remove +args:
    @{{ info }} "updates pyproject.toml and pdm.lock, then uninstalls"
    pdm remove {{ args }}

# Upgrade dependencies (all of them when none are given)
upgrade *args:
    @{{ info }} "within the pyproject.toml constraints; rewrites pdm.lock"
    pdm update {{ args }}

# Update from the template and leave a working repository: merge, relock, reinstall, check.
# Extra arguments go to copier, e.g. `just update --data python_min=3.16`
update *args:
    @{{ info }} "two just runs: the second one uses the recipes the merge just brought in"
    just update-template {{ args }}
    just update-sync

# Finish a template update: stop on conflicts, relock, reinstall, check
update-sync: update-conflicts install-python update-lock install-plugins install-deps install-hooks check
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

# Re-resolve pdm.lock for the new constraints, keeping the locked versions that still fit
update-lock:
    @{{ info }} "-G :all: groups the template adds too; --update-reuse: only what pyproject.toml requires changes"
    pdm lock -G :all --update-reuse

# Bump the version: major, minor, micro, pre-release, no-pre-release, ... (see `pdm bump -h`)
bump part:
    @{{ info }} "rewrites version in pyproject.toml (pdm-bump plugin)"
    pdm bump {{ part }}

# Build the sdist and wheel into dist/
build:
    @{{ info }} "output in dist/"
    pdm build

# Remove build artefacts and caches
clean:
    rm -rfv {{ build_dir }} dist .pytest_cache .ruff_cache
    find . -path ./.venv -prune -o -type d -name __pycache__ -prune -print -exec rm -rf {} +
