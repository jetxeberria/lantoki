# lantoki: agent instructions

lantoki is the single source of truth for all AI coding-assistant customization, compiled into every supported harness. **[docs/SPECIFICATION.md](docs/SPECIFICATION.md) is the authority**: read it before changing behaviour.

## Rules

1. **Spec first (CHG-1).** A change to what lantoki must do is written in `docs/SPECIFICATION.md` (affected section + a decision-log entry) before the code changes. Commits cite requirement or decision IDs, e.g. `feat(installer): prune stale targets (INS-5)`.
2. **Never edit a harness's config directly (PRI-2).** Customizations are changed in `customizations/` and installed with `lantoki sync`, never in `~/.claude/`, `~/.copilot/`, `~/.config/Code/User/`, or a repo's `.github/`, `.claude/`.
3. **The core stays provider-agnostic (PRI-3, PRI-4).** No provider names, paths, field names or formats in Python. Provider knowledge goes in `src/lantoki/providers/<id>.toml`. The core only changes to add a *generic* format or transform any profile can use, and that change goes through the spec.
4. **Never overwrite what lantoki does not own (PRI-5).** Installer changes must keep the manifest-based ownership, conflict and adoption rules.

## Where things are

| Path | Role |
|---|---|
| `customizations/` | neutral sources ([format](docs/source-format.md)) |
| `src/lantoki/providers/*.toml` | provider profiles ([schema](docs/provider-profiles.md)) — the only provider-specific files |
| `src/lantoki/sources.py`, `profiles.py` | load and validate sources and profiles |
| `src/lantoki/transforms.py`, `compiler.py` | generic compilation (pure, no writes) |
| `src/lantoki/installer.py`, `manifest.py` | plan/apply, ownership, adoption, pruning |
| `src/lantoki/app.py`, `cli.py` | orchestration and the `lantoki` command |
| `tests/fixtures/providers/acme.toml` | fictional provider proving a profile is all a provider needs (QLT-2) |
| `tests/fixtures/baseline`, `tests/fixtures/golden` | regression baseline for the shipped profiles (QLT-3) |

## Adding a provider

1. Collect evidence from the provider's documentation; add the facts to SPECIFICATION §11 with dates.
2. Create `src/lantoki/providers/<id>.toml` ([schema](docs/provider-profiles.md)), citing the docs and the version verified.
3. `just validate`, then `just plan-user` to review the targets before `just sync-user`.
4. Add golden tests for the profile's compiled output.

## Working on this repo

- Tooling: `uv` + `just`. Run `just check` (format + Ruff `ALL`) and `just test` (pytest, coverage ≥ 75%) before finishing.
- Python and test standards come from lantoki itself: `customizations/project/instructions/python.md` and `tests.md`.
- Dependencies stay at their latest compatible versions (QLT-4).
