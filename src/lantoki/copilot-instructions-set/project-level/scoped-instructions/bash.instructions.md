---
name: bash-engineering-standards
description: Enforce ShellCheck compliance, robust error handling, and maintainable shell scripts.
applyTo: "/*.sh"
---

# Bash Programming Standards

## I. Naming, Formatting & Tooling (Strict Consistency)

* Naming Conventions: snake\_case for variables and functions; UPPER\_SNAKE\_CASE for environment variables and constants.
* Explicit Naming: \- Avoid single-letters: Use index instead of i unless in a very short local loop.
  * Local Scope: Always use the local keyword for variables inside functions to prevent global namespace pollution.
* Automation: \- ShellCheck: Every script MUST pass ShellCheck without warnings. Use \# shellcheck disable=... only for documented edge cases.
  * shfmt: Use shfmt \-i 2 \-ci for consistent indentation and formatting.

## II. Logic & Structure

* Fail Fast (The "Safety Header"): Every script must start with:
  set \-euo pipefail
  IFS=$'\\n\\t'

  *(e: errexit, u: nounset, o pipefail: catches errors in pipes).*
* Single Responsibility (SRP):
  * Move logic into functions. A script's global scope should ideally only contain a main function call and constant definitions.
  * The "And" Test: If a function "downloads and parses," split it.
* Complexity:
  * Guard Clauses: Return early if requirements (like dependencies or arguments) are missing.
  * AHA Principle: If a script grows beyond 500 lines or requires complex data structures, split the scope into more but smaller files.

## III. Idiomatic & Robust Bash

* Quoting: Always quote variable expansions "$VAR" and command substitutions "$(cmd)" to prevent word splitting and globbing.
* Tests: Use \[\[ ... \]\] for conditional expressions instead of \[ ... \] or test. It is safer and more powerful.
* Command Substitution: Use $(command) instead of backticks \`command\`.
* Paths: Use ${BASH\_SOURCE\[0\]} to determine the script's directory rather than assuming PWD.

## IV. Reliability, Documentation & Maintenance

* Purposeful Commenting: \- Use headers for functions explaining arguments ($1, $2) and exit codes.
  * Explain the "Why" for complex regex or non-obvious pipe chains.
* Logging Implementation:
  * Redirect logs/errors to stderr: echo "message" \>&2.
  * For production scripts, implement a simple log() function that includes timestamps.
* Cleanup: Use trap to catch signals (EXIT, INT, TERM) and remove temporary files or release locks.
* The Boy Scout Rule: Clean up legacy "spaghetti" logic or unquoted variables when modifying older scripts.

## V. Security & Environment

* Secrets: Never hardcode passwords or API keys. Use environment variables or secret managers.
* Shebang: Use \#\!/usr/bin/env bash for better portability across different systems.
* Input Validation: Always validate that required arguments exist and that paths are writable before beginning execution.
* Absolute Paths: Prefer absolute paths or paths relative to the script location over relative paths based on the user's current shell location.