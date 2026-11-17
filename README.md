# lantoki

**The single entry point for all AI coding-assistant customization.** Instructions, rules, prompts, skills, agents and MCP servers are written once, in a provider-neutral format, and compiled into the configuration every harness expects: GitHub Copilot (VS Code and CLI), Claude Code (CLI and the desktop app's Code tab), and any provider added later with a single profile file.

The authority on what lantoki does and why is the **[master specification](docs/SPECIFICATION.md)**. Changes to behaviour are recorded there first.

## How it works

```
customizations/            neutral sources (what you edit)
src/lantoki/providers/     one TOML profile per provider (paths, fields, tool names, formats)
        │
        ▼  lantoki sync
~/.claude, ~/.copilot, ~/.config/Code/User, <repo>/.github, <repo>/.claude, …
```

- Edit only `customizations/`. Never edit a harness's own config folders.
- `lantoki sync` compiles each source with each provider profile and installs the result as symlinks (copies only where a provider cannot follow symlinks). A manifest tracks what lantoki installed, so it never touches your own files, and it removes outputs whose source was deleted.
- New provider? Add `src/lantoki/providers/<id>.toml`. No code changes. See [provider profiles](docs/provider-profiles.md).

## Getting started

```bash
sudo apt install just   # bootstrap: everything else is installed by `just install`
just install            # system packages, user tools and the PDM environment
just                    # list recipes
```

Common recipes: `just fmt`, `just lint`, `just test`, `just check`,
`just add <package>`, `just update` (pull template changes).

`just install-tool` installs the project's `[project.scripts]` on `PATH`
(`uv tool install --editable`, so the commands follow the working tree).

## Using lantoki

```bash
just install-tools    # put `lantoki` and `python-verification-gate` on PATH (editable)

just validate         # check every source and profile
just plan-user        # dry-run: what would change in your home directory
just sync-user        # install user-level customizations for every provider
just sync-repo ~/code/my-app --all   # install project-level customizations into a repository
```

`lantoki sync repo` asks which project sources apply to the repository and remembers the answer (`--select` to ask again, `--all` for everything). Add the installed paths to that repository's `.gitignore`: they are machine-specific.

## Writing customizations

See [source format](docs/source-format.md). In short:

| Kind | Where | Example |
|---|---|---|
| Instruction | `customizations/{user,project}/instructions/<name>.md` | coding standards, optionally scoped with `applies_to` globs |
| Prompt | `customizations/{user,project}/prompts/<name>.md` | a slash command; `{{arguments}}` is what the user types after it |
| Agent | `customizations/user/agents/<name>.md` | a specialised agent with a neutral `tools` list |
| Skill | `customizations/{user,project}/skills/<name>/SKILL.md` | Agent Skills standard, used as-is |
| MCP servers | `customizations/{user,project}/mcp.toml` | `[servers.<name>]` with `command`, `args`, `env` |
| Repo instructions | `customizations/project/repo-instructions.md` | always-on instructions for a repository |

## Development

The development tooling comes from the [galtzagorri](https://github.com/jetxeberria/galtzagorri) template (D-012).

```bash
just check    # formatting, linters (Ruff ALL, YAML, JSON, shell) and tests with coverage
just test     # pytest with coverage (fails under 75 %); `just test --no-cov tests/test_x.py` for one file
just docs     # build the documentation site
```

## Dependencies

- `dependencies` (runtime) and the `dev` group belong to this project.
- The `base` group belongs to the template: minimum versions of the tools its
  recipes use. Do not edit it; to need a newer one, add a higher floor to `dev`
  (e.g. `just add -dG dev "ruff>=0.15"`). PDM resolves all groups into one `pdm.lock`.

## Template updates

`just update` merges the latest template, relocks (`pdm lock --update-reuse`),
reinstalls, and runs `just check`; commit the result together with `pdm.lock`.
It stops on merge conflicts; resolve them, then run `just update-sync`.

The Python version is a template answer (`python_min`, kept in
`.copier-answers.yml`), so updates never change it. Raise it on a branch:
`just update --data python_min=3.16`.

Every `git push` runs `just check` first (pre-commit hook, installed by
`just install-hooks` as part of `just install`; config in `.pre-commit-config.yaml`).
