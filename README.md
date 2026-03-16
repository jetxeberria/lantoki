# lantoki

## Prerequisites

- Install [just](https://github.com/casey/just#installation)
- Install [uv](https://docs.astral.sh/uv/)

## Quickstart

```bash
# Set environment
just env-lock
just env-sync

# Linting
just lint --fix     # Apply safe fixes via execute uv run ruff check --fix src with a nice help command instructions if linting fails
just check          # Execute format and lint

# Environment management
just env-add --help    # Prints uv add help
just env-add --group docs mkdocs-mermaid2-plugin
just env-add --group docs mkdocs-material-extensions

# Development workflow
just docs            # Generate documentation
just test            # Run all test and coverage

```
