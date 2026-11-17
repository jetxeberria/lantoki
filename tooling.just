# Shared tooling recipes.
#
# Imported by the galtzagorri repository Justfile and by the Justfile of
# every project generated from the template, so both use the same tools.
#
# Keep this file next to the Justfile that imports it: just 1.21 runs
# imported recipes in the imported file's folder, not the Justfile's, and
# the recipes expect the project root. galtzagorri imports it through the
# tooling.just symlink at its root for the same reason.
#
# Tool layers:
#   system  apt packages, need sudo .......... install-system
#   user    ~/.local/bin (uv, pdm, yamlfmt, .. install-user
#           gh)
#   python  project .venv managed by PDM ..... install-env
#           (ruff, yamllint, pytest, copier,
#           pre-commit: pinned in pdm.lock)
#   git     pre-push hooks (Git LFS, then .... install-hooks
#           `just check` via pre-commit)
#
# Every aggregate recipe (install, fmt, fmt-check, lint) is a chain of
# atomic recipes that can also be run on their own, e.g. `just lint-yaml`.
#
# Output policy: nothing is silenced. Single-line recipes are echoed by just;
# multi-line (shebang) recipes echo each command through `run`, the same way.
# `info` messages only add what the command line does not already show.

# xclip (X11) and wl-clipboard (Wayland) let CLIs such as `gh auth login`
# copy one-time codes to the clipboard
system_packages := "git git-lfs curl jq shellcheck shfmt clang-format clang-tidy xclip wl-clipboard"
yamlfmt_version := "0.21.0"
gh_version := "2.104.0"
bin_dir := env_var("HOME") + "/.local/bin"
build_dir := "build"
profile := env_var("HOME") + "/.profile"

# User tools must be found even before ~/.local/bin is in the login PATH
original_path := env_var("PATH")
export PATH := bin_dir + ":" + original_path

# Developer messages: `{{ info }} "text"` and `{{ warn }} "text"`
info := "printf '\\033[1;34m==>\\033[0m %s\\n'"
warn := "printf '\\033[1;33m==> %s\\033[0m\\n' >&2"

# Shebang recipes start with `{{ run }}`, then prefix commands with `run` so
# they are echoed (bold, to stderr) exactly like just echoes its own lines
run := 'run() { printf "\033[1m%s\033[0m\n" "$*" >&2; "$@"; }'

# Tracked and untracked (but not ignored) files matching the given globs
ls_files := "git ls-files -z --cached --others --exclude-standard --"
shell_files := "'*.sh'"
yaml_files := "'*.yml' '*.yaml' '.clang-format'"
json_files := "'*.json'"
c_sources := "'*.c' '*.cc' '*.cpp' '*.cxx'"
c_headers := "'*.h' '*.hh' '*.hpp' '*.hxx'"

# ---------------------------------------------------------------- install ---

# Install everything needed to operate the repository
install: install-system install-user install-env

# System layer: apt packages and Git LFS (asks for sudo)
install-system: install-apt install-git-lfs

# Install system packages with apt (asks for sudo)
install-apt:
    @{{ info }} "sudo asks for your password"
    sudo apt-get update
    sudo apt-get install -y {{ system_packages }}

# Enable Git LFS filters for your user
install-git-lfs:
    @{{ info }} "registers the LFS filters in ~/.gitconfig; repo hooks come from install-hooks"
    git lfs install --skip-repo

# User layer: uv, pdm, yamlfmt and gh in ~/.local/bin
install-user: install-path install-uv install-pdm install-yamlfmt install-gh

# Make sure ~/.local/bin is in your login PATH (~/.profile)
install-path:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    run mkdir -pv "{{ bin_dir }}"
    case ":{{ original_path }}:" in
        *":{{ bin_dir }}:"*)
            {{ info }} "{{ bin_dir }} already in PATH, nothing to do"
            ;;
        *)
            if run grep -n '\.local/bin' "{{ profile }}"; then
                {{ warn }} "{{ profile }} already adds {{ bin_dir }}: log in again to apply"
            else
                {{ info }} "appending a PATH line to {{ profile }}"
                printf '\n# Added by just install-path\nexport PATH="$HOME/.local/bin:$PATH"\n' | run tee -a "{{ profile }}"
                {{ warn }} "log in again (or source {{ profile }}) to apply"
            fi
            ;;
    esac

# Install uv (Python package installer, used by PDM as its backend)
install-uv:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    if run command -v uv; then
        run uv --version
        {{ info }} "already installed, skipping"
        exit 0
    fi
    {{ info }} "official installer, into {{ bin_dir }} without touching shell profiles"
    printf '\033[1m%s\033[0m\n' "curl -LSf https://astral.sh/uv/install.sh | UV_NO_MODIFY_PATH=1 sh" >&2
    curl -LSf https://astral.sh/uv/install.sh | UV_NO_MODIFY_PATH=1 sh

# Install or upgrade PDM as a uv tool
install-pdm:
    @{{ info }} "isolated in its own venv, executable linked into {{ bin_dir }}"
    uv tool install --upgrade pdm

# Install yamlfmt from its GitHub release (checksum-verified)
install-yamlfmt:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    if run command -v yamlfmt && run yamlfmt -version | tee /dev/stderr | grep -qF "yamlfmt {{ yamlfmt_version }} "; then
        {{ info }} "v{{ yamlfmt_version }} already installed, skipping"
        exit 0
    fi
    {{ info }} "v{{ yamlfmt_version }} from GitHub releases (not packaged in apt), checksum-verified"
    case "$(uname -m)" in
        x86_64) arch=x86_64 ;;
        aarch64 | arm64) arch=arm64 ;;
        *) {{ warn }} "unsupported architecture: $(uname -m)"; exit 1 ;;
    esac
    tarball="yamlfmt_{{ yamlfmt_version }}_Linux_${arch}.tar.gz"
    url="https://github.com/google/yamlfmt/releases/download/v{{ yamlfmt_version }}"
    tmp=$(mktemp -d)
    trap 'rm -rfv "$tmp"' EXIT
    run curl -fSL -o "$tmp/$tarball" "$url/$tarball"
    run curl -fSL -o "$tmp/checksums.txt" "$url/checksums.txt"
    cd "$tmp"
    grep " $tarball\$" checksums.txt | run sha256sum -c -
    run tar -xvzf "$tarball" yamlfmt
    run install -v -m 0755 yamlfmt "{{ bin_dir }}/yamlfmt"

# Install the GitHub CLI from its GitHub release (checksum-verified)
install-gh:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    if run command -v gh && run gh --version | tee /dev/stderr | grep -qF "gh version {{ gh_version }} "; then
        {{ info }} "v{{ gh_version }} already installed, skipping"
        exit 0
    fi
    {{ info }} "v{{ gh_version }} from GitHub releases (apt's gh lags behind), checksum-verified"
    case "$(uname -m)" in
        x86_64) arch=amd64 ;;
        aarch64 | arm64) arch=arm64 ;;
        *) {{ warn }} "unsupported architecture: $(uname -m)"; exit 1 ;;
    esac
    name="gh_{{ gh_version }}_linux_${arch}"
    url="https://github.com/cli/cli/releases/download/v{{ gh_version }}"
    tmp=$(mktemp -d)
    trap 'rm -rfv "$tmp"' EXIT
    run curl -fSL -o "$tmp/$name.tar.gz" "$url/$name.tar.gz"
    run curl -fSL -o "$tmp/checksums.txt" "$url/gh_{{ gh_version }}_checksums.txt"
    cd "$tmp"
    grep " $name.tar.gz\$" checksums.txt | run sha256sum -c -
    run tar -xvzf "$name.tar.gz" "$name/bin/gh"
    run install -v -m 0755 "$name/bin/gh" "{{ bin_dir }}/gh"

# Python layer: interpreter, PDM plugins and dependencies in .venv, then the git hooks
install-env: install-python install-plugins install-deps install-hooks

# Select the minimum Python version in requires-python (PDM downloads it if missing)
install-python:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    version=$(run sed -nE 's/^requires-python = ">=([0-9]+\.[0-9]+)"$/\1/p' pyproject.toml)
    [ -n "$version" ] || { {{ warn }} 'pyproject.toml needs requires-python = ">=3.X"'; exit 1; }
    {{ info }} "Python $version, from requires-python in pyproject.toml"
    if ! run pdm use --first "$version"; then
        {{ warn }} "Python $version not found on the system: downloading a standalone build"
        run pdm python install "$version"
        run pdm use --first "$version"
    fi

# Install the PDM plugins declared in pyproject.toml
install-plugins:
    @{{ info }} "plugins listed in [tool.pdm] plugins of pyproject.toml"
    pdm install --plugins

# Install Python dependencies from pdm.lock into .venv (uv backend, see pdm.toml)
install-deps:
    @{{ info }} "into .venv from pdm.lock (created if missing); uv does the work (use_uv in pdm.toml)"
    pdm install

# Install the git hooks: Git LFS, then pre-commit running `just check` before each push
install-hooks:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        {{ warn }} "not a git repository yet, skipping: run it again after git init"
        exit 0
    fi
    {{ info }} "--force: pre-commit owns pre-push after the first run, and LFS refuses to share it"
    run git lfs install --local --force
    if ! run pdm run pre-commit --version; then
        {{ warn }} "pre-commit is not installed yet: run just install-env"
        exit 0
    fi
    {{ info }} "config: .pre-commit-config.yaml; the LFS hook is kept as pre-push.legacy and still runs"
    run pdm run pre-commit install

# ----------------------------------------------------------------- format ---

# Format all files in place
fmt: fmt-python fmt-shell fmt-yaml fmt-json fmt-c

# Format Python files with ruff
fmt-python:
    @{{ info }} "config: [tool.ruff] in pyproject.toml"
    pdm run ruff format .

# Format shell scripts with shfmt (style from .editorconfig)
fmt-shell:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    mapfile -d '' files < <({{ ls_files }} {{ shell_files }})
    [ ${#files[@]} -gt 0 ] || { {{ info }} "no {{ shell_files }} files in git, skipping"; exit 0; }
    {{ info }} "${#files[@]} file(s); style from .editorconfig; -l lists the files it changes"
    run shfmt -w -l "${files[@]}"

# Format YAML files with yamlfmt (style from .yamlfmt.yaml)
fmt-yaml:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    mapfile -d '' files < <({{ ls_files }} {{ yaml_files }})
    [ ${#files[@]} -gt 0 ] || { {{ info }} "no {{ yaml_files }} files in git, skipping"; exit 0; }
    {{ info }} "${#files[@]} file(s); config: .yamlfmt.yaml"
    run yamlfmt "${files[@]}"

# Format JSON files with jq (2-space indent)
fmt-json:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    mapfile -d '' files < <({{ ls_files }} {{ json_files }})
    [ ${#files[@]} -gt 0 ] || { {{ info }} "no {{ json_files }} files in git, skipping"; exit 0; }
    {{ info }} "${#files[@]} file(s); rewritten through a temp file"
    for f in "${files[@]}"; do
        run jq --indent 2 . "$f" > "$f.fmt"
        run mv -v "$f.fmt" "$f"
    done

# Format C/C++ files with clang-format (style from .clang-format)
fmt-c:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    mapfile -d '' files < <({{ ls_files }} {{ c_sources }} {{ c_headers }})
    [ ${#files[@]} -gt 0 ] || { {{ info }} "no C/C++ files in git, skipping"; exit 0; }
    {{ info }} "${#files[@]} file(s); style from .clang-format"
    run clang-format -i --verbose "${files[@]}"

# Check formatting without modifying files
fmt-check: fmt-check-python fmt-check-shell fmt-check-yaml fmt-check-json fmt-check-c

# Check Python formatting (ruff)
fmt-check-python:
    @{{ info }} "config: [tool.ruff] in pyproject.toml"
    pdm run ruff format --check .

# Check shell script formatting (shfmt)
fmt-check-shell:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    mapfile -d '' files < <({{ ls_files }} {{ shell_files }})
    [ ${#files[@]} -gt 0 ] || { {{ info }} "no {{ shell_files }} files in git, skipping"; exit 0; }
    {{ info }} "${#files[@]} file(s); style from .editorconfig; prints a diff per unformatted file"
    run shfmt -d "${files[@]}"

# Check YAML formatting (yamlfmt)
fmt-check-yaml:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    mapfile -d '' files < <({{ ls_files }} {{ yaml_files }})
    [ ${#files[@]} -gt 0 ] || { {{ info }} "no {{ yaml_files }} files in git, skipping"; exit 0; }
    {{ info }} "${#files[@]} file(s); config: .yamlfmt.yaml; silent when all are formatted"
    run yamlfmt -lint "${files[@]}"

# Check JSON formatting (jq)
fmt-check-json:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    mapfile -d '' files < <({{ ls_files }} {{ json_files }})
    [ ${#files[@]} -gt 0 ] || { {{ info }} "no {{ json_files }} files in git, skipping"; exit 0; }
    {{ info }} "${#files[@]} file(s); diff against jq --indent 2 output"
    status=0
    for f in "${files[@]}"; do
        run diff -u --label "$f" --label "$f (formatted)" "$f" <(jq --indent 2 . "$f") || status=1
    done
    exit $status

# Check C/C++ formatting (clang-format)
fmt-check-c:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    mapfile -d '' files < <({{ ls_files }} {{ c_sources }} {{ c_headers }})
    [ ${#files[@]} -gt 0 ] || { {{ info }} "no C/C++ files in git, skipping"; exit 0; }
    {{ info }} "${#files[@]} file(s); style from .clang-format"
    run clang-format --dry-run --Werror --verbose "${files[@]}"

# ------------------------------------------------------------------- lint ---

# Apply automatic lint fixes (ruff)
fix:
    @{{ info }} "config: [tool.ruff] in pyproject.toml; only safe fixes"
    pdm run ruff check --fix .

# Run all linters and validators
lint: lint-python lint-shell lint-yaml lint-json lint-c

# Lint Python files (ruff)
lint-python:
    @{{ info }} "config: [tool.ruff] in pyproject.toml"
    pdm run ruff check .

# Lint shell scripts (shellcheck)
lint-shell:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    mapfile -d '' files < <({{ ls_files }} {{ shell_files }})
    [ ${#files[@]} -gt 0 ] || { {{ info }} "no {{ shell_files }} files in git, skipping"; exit 0; }
    {{ info }} "${#files[@]} file(s); silent when clean"
    run shellcheck "${files[@]}"

# Lint YAML files (yamllint, config in .yamllint.yaml)
lint-yaml:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    mapfile -d '' files < <({{ ls_files }} {{ yaml_files }})
    [ ${#files[@]} -gt 0 ] || { {{ info }} "no {{ yaml_files }} files in git, skipping"; exit 0; }
    {{ info }} "${#files[@]} file(s); config: .yamllint.yaml; silent when clean"
    run pdm run yamllint --strict "${files[@]}"

# Validate JSON files (jq)
lint-json:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    mapfile -d '' files < <({{ ls_files }} {{ json_files }})
    [ ${#files[@]} -gt 0 ] || { {{ info }} "no {{ json_files }} files in git, skipping"; exit 0; }
    {{ info }} "${#files[@]} file(s); jq empty fails on invalid JSON"
    for f in "${files[@]}"; do run jq empty "$f"; done

# Lint C/C++ sources (clang-tidy, needs build/compile_commands.json)
lint-c:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ run }}
    mapfile -d '' files < <({{ ls_files }} {{ c_sources }})
    [ ${#files[@]} -gt 0 ] || { {{ info }} "no C/C++ sources in git, skipping"; exit 0; }
    if [ ! -f "{{ build_dir }}/compile_commands.json" ]; then
        {{ warn }} "skipped: {{ build_dir }}/compile_commands.json not found"
        {{ warn }} "generate it with: cmake -B {{ build_dir }} -DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
        exit 0
    fi
    {{ info }} "${#files[@]} file(s); compile flags from {{ build_dir }}/compile_commands.json"
    run clang-tidy -p "{{ build_dir }}" "${files[@]}"
