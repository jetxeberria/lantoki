# Project-owned recipes (galtzagorri JUS-1).
#
# The Justfile belongs to the galtzagorri template and imports this file;
# `just update` never changes it. Recipe names must not repeat those of the
# Justfile, tooling.just or packaging.just.

# Put `lantoki` and `python-verification-gate` on PATH, editable (CLI-2, DEV-5)
install-tools: install-tool

# Validate every source and provider profile
validate *args:
    pdm run lantoki validate {{ args }}

# List providers and the kinds each supports
providers *args:
    pdm run lantoki providers {{ args }}

# Dry-run: show what `sync-user` would change
plan-user *args:
    pdm run lantoki plan user {{ args }}

# Install user-level customizations for every provider
sync-user *args:
    pdm run lantoki sync user {{ args }}

# Install project-level customizations into a repository (--all, --select, --adopt-commands)
sync-repo path *args:
    pdm run lantoki sync repo {{ path }} {{ args }}

# Run security analysis (bandit; extra arguments go to it)
security *args:
    pdm run bandit -v -r src/lantoki {{ args }}

# Build the documentation site
docs: docs-build

# Build the documentation site (extra arguments go to mkdocs)
docs-build *args:
    pdm run mkdocs build --verbose --strict {{ args }}

# Serve the documentation locally (extra arguments go to mkdocs)
docs-serve *args:
    pdm run mkdocs serve --dev-addr=0.0.0.0:8001 --verbose {{ args }}

# Remove the documentation and test reports (docs/_build, public/)
clean-docs:
    rm -rfv docs/_build public
