---
name: lint-python
description: Run Python lint checks for a repository.
---

# lint-python

This skill runs lint checks for Python code in the current repository.

## Inputs

- Optional extra flags to pass to `ruff`.

## Behavior

- Executes `run-linter.sh` from this skill directory.
- Fails with a non-zero exit code if linting finds issues.

## Output

- Lint diagnostics from `ruff`.
