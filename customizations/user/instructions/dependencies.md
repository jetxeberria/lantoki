---
description: Keep every package at its latest version and migrate code to new major versions.
---
# Dependencies

- Keep every package at its most recent version, following the currently most endorsed tools and practices.
- If upgrading a package (including a new major version) is technically compatible with the environment, do it without asking: migrate the code to the new API and keep tests and checks green.
- Pin an upper bound only when a newer version is genuinely incompatible, and say why next to the pin.

## Environments and packaging

- One development environment per project. It always follows the project's requirement declarations (`pyproject.toml`) and changes only by syncing it with them, whatever triggered the change: adding, removing, upgrading or downgrading a dependency, a template update, or a pulled change. The resolver does not care where a requirement came from.
- The testing environment holds the production requirements plus development and test tools, all resolved together, so tests run on the same versions of the production packages. Declare each requirement once: production requirements are the base, and development groups only add to them.
- Never keep a production environment on the development machine: production is wherever the package is installed.
- Build the package from production requirements only, as version ranges, never pins. Rely on the dependencies' semantic versioning: a version within the range is expected to work; adopt a new major version deliberately, with an upgrade and the checks. Installing the package must not need the project's development tools.
