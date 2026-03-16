---
name: python-engineering-standards
description: Enforce PEP8, Idiomatic Python, and SOLID principles.
applyTo: "**/*.py"
---
# Python Programming Standards

## I. Naming, Formatting & Tooling
- **Naming:** `snake_case` for variables/functions/methods; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants (however, constants should be avoided for testing purposes).
- **Formatting:** Follow ruff defaults or customized rules if present. Use `ruff check --fix` to automatically apply safe formatting fixes.
- **Automation:** Use **Ruff** for automated formatting consistency.

## II. Idiomatic & Pythonic Code
- **Resources:** Always use the `with` statement for files, network connections, or locks.
- **Comprehensions:** Use list/dict/set comprehensions for simple loops. Use standard `for` loops for complex nested logic.
- **Iteration:** Use `enumerate()` for index+value and `zip()` for simultaneous iteration.
- **Strings:** Use f-strings (`f"..."`) for all string formatting.

## III. Reliability & Maintenance
- **Logging Implementation:** - Stop using `print()` for debugging; use the `structlog` module.
    - **Enforce Contextual Logging:** All dynamic data (ids, timestamps, status codes) MUST be passed as structured keyword fields.
    - **Prohibited:** `logger.info(f"User {id} logged in")` (Interpolation is forbidden).
    - **Required:** `logger.info("user_logged_in", user_id=id)`.
- **Exceptions:** Catch specific exceptions; never use a bare `except:`.
- **Exceptions:** Every exception must be logged, showing the traceback.
- **Typing:** Use Type Hints to improve readability and allow static type checking.
- **Documentation:** Write meaningful PEP 257 docstrings explaining the *why* and *what*.
- **DRY:** Abstract code into functions/classes if a block is repeated three times.
- **Complexity:** Use "early return" (guard clauses) to avoid deep nesting.

## IV. SOLID Principles
- **SRP:** A class/function must have only one reason to change.
- **OCP:** Open for extension, closed for modification (use inheritance/ABCs).
- **LSP:** Subclasses must be swappable for parents without breaking behavior.
- **ISP:** Use specific `typing.Protocol` or focused ABCs rather than "god-classes."
- **DIP:** Depend on abstractions; pass dependencies via `__init__`.

## V. Security & Imports
- **Secrets:** Never hardcode secrets. Use environment variables or `.env` files.
- **Imports:** Always prefer absolute imports over relative imports.