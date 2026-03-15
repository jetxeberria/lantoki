set shell := ["bash", "-c"]

current_version := `grep -m 1 version pyproject.toml | tr -s ' ' | tr -d '"' | tr -d "'" | cut -d' ' -f3`
current_uid := `id -u $USER`
current_gid := `id -g $USER`
current_user := current_uid + ":" + current_gid
rootdir := justfile_directory()

image_name := env('IMAGE_NAME', 'copier_python_http_generated')
image_version := env('IMAGE_VERSION', current_version)

# HELP AND INFORMATION
##############################################################################

# List available recipes
default:
    @just --list

# Show current project version
version:
    @echo {{current_version}}

# ENVIRONMENT SETUP
##############################################################################

# Check if direnv is installed
check-direnv:
    #!/usr/bin/env bash
    if ! command -v direnv &> /dev/null; then
        echo "Direnv is not installed. Please install direnv first."
        exit 1
    fi

# Check if git-lfs is installed
check-git-lfs:
    #!/usr/bin/env bash
    if ! command -v git-lfs &> /dev/null; then
        echo "Git LFS is not installed. Please install Git LFS first."
        echo "Visit: https://git-lfs.github.io/ for installation instructions"
        exit 1
    fi

# Set up development environment
setup-env:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Setting up development environment..."

    # Copy .env.example to .env if .env doesn't exist
    if [[ ! -f ".env" ]] && [[ -f ".env.example" ]]; then
        echo "Copying .env.example to .env..."
        cp .env.example .env
    fi

    # Check if uv is installed
    if ! command -v uv >/dev/null 2>&1; then
        echo "ERROR: uv package manager is not installed"
        echo "Please install uv first: https://docs.astral.sh/uv/"
        exit 1
    fi

    # Create lock file if it doesn't exist
    if [[ ! -f "uv.lock" ]]; then
        echo "Creating uv.lock file..."
        just env-lock
    fi

    # Create/sync virtual environment
    if [[ ! -d ".venv" ]] || ! uv run python --version >/dev/null 2>&1; then
        echo "Creating virtual environment..."
        just env-sync
    fi

# Set up git-lfs tracking
setup-git-lfs: check-git-lfs
    @git lfs install
    @git lfs track --lockable

# Set up pre-commit hooks
setup-git: setup-git-lfs
    @pre-commit install -t pre-push
    @pre-commit run --all-files

# Set up complete project environment
setup: setup-env
    @echo "Setup complete."
    @echo "If you want to use git:"
    @echo "  git init . --initial-branch=master"
    @echo "  just setup-git"

# Clean Python caches and build artifacts
clean:
    #!/usr/bin/env bash
    rm -rf .pytest_cache
    rm -rf build/
    rm -rf dist/
    rm -rf public/
    rm -rf docs/_build
    rm -rf *.egg-info
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true

# Clean virtual environment
clean-env:
    #!/usr/bin/env bash
    if [[ -d ".venv" ]]; then
        echo "Removing .venv directory..."
        rm -rf .venv
        echo "Virtual environment removed."
    else
        echo "No .venv directory found."
    fi

# DEPENDENCY MANAGEMENT
##############################################################################

# Lock dependencies to specific versions (pass extra args)
env-lock *args="":
    uv lock {{args}}

# Sync dependencies with lockfile (pass extra args)
env-sync *args="":
    uv sync {{args}}

# List installed dependencies (pass extra args)
env-list *args="":
    uv tree {{args}}

# Add dependencies (add --group dev or --group docs for non-production dependencies)
env-add *args:
    #!/usr/bin/env bash
    if [[ -z "{{args}}" ]]; then
        echo "Usage: just env-add [--group GROUP] package1 package2 ..."
        echo "Examples:"
        echo "  just env-add requests fastapi           # Add production dependencies"
        echo "  just env-add --group dev pytest ruff    # Add development dependencies"
        echo "  just env-add --group docs mkdocs        # Add documentation dependencies"
        exit 1
    fi
    uv add {{args}}

# Update dependencies (add --group dev or --group docs to update specific groups)
env-update *args="":
    #!/usr/bin/env bash
    if [[ -z "{{args}}" ]]; then
        echo "Updating all dependencies..."
        uv lock --upgrade
    else
        echo "Updating with args: {{args}}"
        uv lock --upgrade {{args}}
    fi

# VERSIONING
##############################################################################

# Bump version (usage: just version-bump MAJOR|MINOR|PATCH or just version-bump 1.2.3)
version-bump increment *extra_args="":
    #!/usr/bin/env bash
    if [[ -z "{{increment}}" ]]; then
        echo "Usage: just version-bump MAJOR|MINOR|PATCH [extra_args]"
        echo "   or: just version-bump 1.2.3 [extra_args]"
        exit 1
    fi

    increment="{{increment}}"
    extra_args="{{extra_args}}"

    if [[ "$increment" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        # Specific version format (e.g., 1.2.3)
        uv run cz bump "$increment" $extra_args
    else
        # Increment type (MAJOR, MINOR, PATCH)
        uv run cz bump --increment "$increment" $extra_args
    fi

# CODE QUALITY AND TESTING
##############################################################################

# Run all tests
test:
    #!/usr/bin/env bash
    COVERAGE_FILE=docs/_build/coverage/test/.coverage \
    uv run pytest tests \
        --cov src \
        --cov-report term-missing \
        --cov-fail-under 75 \
        --cov-report html:docs/_build/coverage/unit \
        --cov-report xml:docs/_build/coverage/unit/coverage.xml \
        --html=docs/_build/test-reports/unit/index.html \
        --junitxml=docs/_build/test-reports/unit/junit.xml \
        -o junit_suite_name=unit-test

# Format code with ruff (pass extra args)
format *args="":
    uv run ruff format {{args}} .

# Lint code with ruff (pass extra args)
lint *args="":
    #!/usr/bin/env bash
    if ! uv run ruff check {{args}} src; then
        echo ""
        echo "Linting failed! Review the changes and/or use --fix and/or --unsafe-fixes for auto-repair"
        echo "Examples:"
        echo "  just lint --fix                  # Apply safe fixes"
        echo "  just lint --fix --unsafe-fixes   # Apply all available fixes"
        exit 1
    fi

# Run security analysis (pass extra args)
security *args="":
    uv run bandit -v -r src/copier_python_http_generated {{args}}

# Run all code quality checks
check: format lint

# DOCUMENTATION
##############################################################################

# Build complete documentation
docs: docs-build

# Build documentation site (pass extra args)
docs-build *args="":
    uv run mkdocs build --verbose --strict {{args}}

# Serve documentation locally (pass extra args)
docs-serve *args="":
    uv run mkdocs serve --dev-addr=0.0.0.0:8001 --verbose {{args}}

