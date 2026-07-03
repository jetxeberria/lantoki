---
name: python-engineering-standards
description: Enforce PEP8, Idiomatic Python, SOLID and Clean Code principles.
applyTo: "**/*.py"
---
# Python Programming Standards

## I. Naming, Formatting & Tooling (Strict Consistency)

* Naming Conventions: snake\_case for variables/functions; PascalCase for classes; UPPER\_SNAKE\_CASE for constants. Constants must be avoided when possible; prefer configuration via environment variables or config files.
* Explicit Naming: \- Intent over Implementation: Name by *what* it represents, not its type (e.g., user\_list \-\> active\_subscribers).
  * Avoid Generic Terms: Prohibit "Manager," "Data," or "Info."
  * Searchability: Use names unique enough to be found easily via global search.
* Automation: Use Ruff for automated formatting (ruff check \--fix). Consistency is more important than personal preference.

## II. Logic & Structure

* Single Responsibility (SRP): \- A function or class must have only one reason to change.
  * The "And" Test: If describing a function's purpose requires the word "and," it must be split.
* Fail Fast & Complexity:
  * Guard Clauses: Handle invalid states and errors at the start of functions to avoid deep if/else nesting.
  * Early Return: Exit the function as soon as the result is determined.
* Abstraction Balance:
  * DRY (Don't Repeat Yourself): Abstract logic used in 3+ places.
  * AHA (Avoid Hasty Abstractions): Prefer minor duplication over a rigid, complex abstraction that is difficult to modify.

## III. Idiomatic & Pythonic Code

* Resources: Always use the with statement for files, network connections, or locks.
* Comprehensions: Use list/dict/set comprehensions for simple loops. Use standard for loops for complex nested logic.
* Iteration: Use enumerate() for index+value and zip() for simultaneous iteration.
* Strings: Use f-strings (f"...") for all string formatting.

## IV. Reliability, Documentation & Maintenance

* Purposeful Commenting:
  * Code for "How": If logic is complex, refactor it into well-named variables/functions instead of explaining it.
  * Comments for "Why": Use PEP 257 docstrings and comments to explain business logic, constraints, or non-obvious decisions.
* Logging Implementation:
  * Use structlog. Never use print() for debugging.
  * Enforce Contextual Logging: Pass dynamic data (IDs, status codes) as structured keyword fields.
  * *Prohibited:* logger.info(f"User {id} logged in").
  * *Required:* logger.info("user\_logged\_in", user\_id=id).
* Exceptions: Catch specific exceptions; never use a bare except:. Every exception must be logged with its traceback.
* Typing: Use Type Hints for readability and static type checking.
* The Boy Scout Rule: Leave every file slightly better than you found it (e.g., fixing a typo, renaming a vague variable, or removing dead code).

## V. SOLID Principles

* SRP: (See Section II).
* OCP: Open for extension, closed for modification (use inheritance/ABCs).
* LSP: Subclasses must be swappable for parents without breaking behavior.
* ISP: Use specific typing.Protocol or focused ABCs rather than "god-classes."
* DIP: Depend on abstractions; pass dependencies via \_\_init\_\_.

## VI. Security & Imports

* Secrets: Never hardcode secrets. Use environment variables or .env files.
* Imports: Always prefer absolute imports over relative imports.

## VII. Configuration Loading & Validation

* Mandatory Loader: Configuration must be loaded with dynaconf. Do not read configuration directly with ad-hoc os.environ parsing, raw TOML/JSON/YAML readers, or scattered constants.
* Context-Bound Requirements: Every runtime context (for example: user setup, repo setup, CLI mode, service mode) must define an explicit minimum required configuration contract.
* Fail Fast on Missing Keys: Validate required configuration at startup for the active context and raise a clear error that names the missing key and context.
* Separate Contracts by Context: Keep required keys grouped by context to avoid over-validating unrelated paths and to keep extension points clear.
* Test Enforcement: Add or update tests to assert that missing required configuration for a context fails deterministically with an actionable error.

## VIII. Module Boundaries for Exceptions and Config

* Exception Location Rule: Define all custom exception classes in an exceptions.py module for the package or bounded context. Do not scatter exception class definitions across feature modules.
* Controlled Exception Hierarchy Rule: All custom exceptions must inherit from one main controlled custom exception (for example, `BaseApplicationError`) that centralizes shared behavior.
* Shared Exception Logic Rule: Cross-cutting exception behavior (for example, structured self-logging when instantiated/raised, error metadata normalization, or common serialization fields) must live in the controlled base exception, not duplicated in subclasses.
* Configuration Location Rule: Define all configuration loading and parsing logic in a config.py module for the package or bounded context. Avoid duplicating loading logic in CLI, service, or utility modules.
* Import Usage Rule: Other modules should import exceptions and configuration access from these dedicated modules instead of re-implementing them.
* Test Pairing Rule: Each exceptions.py and config.py must have a dedicated corresponding test file (for example: test_exceptions.py and test_config.py).