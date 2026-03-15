#!/usr/bin/env bash
set -euo pipefail

# Run lints for Python sources. Pass through optional args to ruff.
ruff check src tests "$@"
