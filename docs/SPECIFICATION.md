# lantoki — Master Specification

| | |
|---|---|
| **Status** | Active |
| **Owner** | jetxeberria |
| **Last change** | 2026-11-18 — D-014, D-015 (`just init` reproduces the setup; lantoki excludes its repo outputs from git) |

This document is the authority on what lantoki is, what it must do and **why**. Every requirement has an ID and a rationale. Code, tests and docs implement these requirements and cite their IDs; when they disagree with this document, this document wins until it is changed through [§10 Change control](#10-change-control).

---

## 1. Purpose

**PUR-1. lantoki is the single entry point for all AI coding-assistant customization.** Instructions, rules, prompts, skills, agents and MCP servers are written once in lantoki and compiled into the configuration each AI harness (GitHub Copilot, Claude Code, and future ones) expects.

> **Why.** Every harness invents its own folders, file names, front-matter fields, tool names and MCP formats, and the set of harnesses keeps growing. Maintaining one copy per harness means the copies drift: a rule fixed for one assistant stays broken in another, and nobody knows which copy is right. One source of truth, compiled per harness, removes the drift and makes switching or combining assistants free.

**PUR-2. lantoki is portable personal infrastructure.** Cloning the repository and running one command on a new Linux machine must reproduce the whole setup.

> **Why.** Customization is accumulated knowledge (standards, workflows, agents). It must survive machine changes and be versioned like code.

## 2. Scope

**SCO-1. In scope:** user-level customization (applies to every project on the machine) and project-level customization (applied to a chosen repository), for every supported harness.

**SCO-2. Supported harnesses** are exactly those with a provider profile in `src/lantoki/providers/` (see §5). At the time of writing: GitHub Copilot (VS Code and Copilot CLI) and Claude Code (CLI and the desktop app's Code tab).

**SCO-3. Platform:** Linux. Paths follow XDG conventions.

> **Why.** It is the only platform in use; supporting others would add untested branches (Windows symlink privileges, macOS paths) with no current benefit. Revisit through change control if needed.

## 3. Glossary

| Term | Meaning |
|---|---|
| **Harness / provider** | An AI coding assistant that reads customization files (Copilot, Claude Code, …). |
| **Source** | A customization written in lantoki's neutral format under `customizations/`. |
| **Kind** | The type of a source: `instruction`, `prompt`, `agent`, `skill`, `mcp`, `repo_instructions`. |
| **Scope** | `user` (all projects on the machine) or `project` (one repository). |
| **Profile** | A TOML file describing how one provider stores each kind: paths, fields, tool names, placeholders, formats. |
| **Core** | lantoki's provider-agnostic Python code. |
| **Artifact** | One compiled output for one provider (a file, a linked directory, or a command). |
| **Target** | The path (or registration) where a provider expects an artifact. |
| **Compiled store** | `~/.local/share/lantoki/compiled/`, where generated artifacts live before being linked to their targets. |
| **Manifest** | lantoki's record of every target it installed, per scope. |
| **Template** | [galtzagorri](https://github.com/jetxeberria/galtzagorri), the copier template that owns the shared development tooling (§9.1). |

## 4. Principles

**PRI-1. Single source of truth.** Each customization exists exactly once, in the neutral format. Provider copies are always generated, never edited.

> **Why.** PUR-1. Two editable copies will diverge.

**PRI-2. Never edit a harness's configuration directly.** Changes to `~/.claude/`, `~/.copilot/`, `~/.config/Code/User/`, a repo's `.github/` or `.claude/`, etc. are made in lantoki's sources and installed by lantoki. This applies to humans and to AI assistants.

> **Why.** A direct edit is invisible to lantoki: it is lost on the next sync or silently diverges from the other harnesses. Observed: an assistant wrote a dependency rule straight into `~/.claude/CLAUDE.md`, bypassing lantoki (D-001).

**PRI-3. Provider-agnostic core, provider knowledge as data.** The core contains no provider names, paths or formats. Everything provider-specific lives in that provider's profile.

> **Why.** The number of harnesses will grow. If provider logic lives in code, every new harness touches the core, risks regressions for the others and needs a developer. As data, it is reviewable, diffable and isolated.

**PRI-4. Adding a provider = adding one profile file.** No Python changes. The core only changes to add a new *generic* capability (a new output format or field transform) that any profile can then use.

> **Why.** PRI-3 made measurable. A test enforces it (QLT-2).

**PRI-5. Never destroy what lantoki does not own.** lantoki only modifies or removes targets recorded in its manifest (or recognisably created by an earlier lantoki version). Anything else is a conflict, reported and left untouched.

> **Why.** Harness config folders also contain the user's own files and other tools' files. Losing them is unacceptable; a reported conflict costs one manual decision.

**PRI-6. Deterministic and idempotent.** The same sources and profiles always produce the same artifacts; running sync twice changes nothing the second time.

> **Why.** Makes sync safe to run any time (after every edit, on a new machine, in automation) and makes diffs meaningful.

**PRI-7. Explicit over silent.** Anything lantoki cannot map (a kind a provider lacks, a tool with no equivalent, a missing CLI) is reported, never silently dropped or guessed.

> **Why.** Silent gaps make a harness behave differently from the others without anyone noticing, which defeats PUR-1.

**PRI-8. Profiles are evidence-based.** Each profile cites the provider documentation it was written from and the provider version and date it was verified against.

> **Why.** Harness formats change frequently. Without provenance, nobody can tell whether a profile is still right or which assumption broke.

## 5. Source model (neutral format)

All sources live under `customizations/` at the repository root:

```
customizations/
  user/      instructions/*.md   prompts/*.md   agents/*.md   skills/<name>/   mcp/<name>/
  project/   repo-instructions.md   instructions/*.md   prompts/*.md   skills/<name>/   mcp/<name>/
```

Every customization is one file or one folder: deleting it removes the customization and everything only it uses (SRC-9).

**SRC-1. Neutral dialect.** Sources use lantoki's own front-matter fields, placeholders and tool names, not any provider's.

> **Why.** If sources used one provider's dialect, that provider would be privileged and its quirks would leak into every other profile (D-002). Before D-002 sources were written in Copilot's dialect, and the Claude Code mapping had to translate Copilot concepts.

**SRC-2. Names.** A source's name is its file name without extension (or its folder name for skills and MCP servers), restricted to `[a-z0-9-]+`. An optional `title` holds a human-readable name.

> **Why.** It is the intersection of what every known provider accepts (Claude Code rejects `:` and leading `-` in agent names; command names derive from file names). Validating once avoids per-provider failures.

**SRC-3. Front-matter fields** (markdown kinds). Unknown fields are rejected.

| Field | Kinds | Meaning |
|---|---|---|
| `description` | all | Required. What it is and when to use it. Providers use it for discovery. |
| `title` | all | Optional display name. |
| `applies_to` | `instruction` | List of globs. **Absent = applies everywhere.** |
| `argument_hint` | `prompt`, `agent` | Hint shown when invoking. |
| `tools` | `prompt`, `agent` | Neutral tool list (SRC-5). Absent = the provider's default (usually all tools). |
| `overrides` | all | `{ <provider-id>: { <field>: value } }`, merged verbatim into that provider's output only. |

> **Why "absent = everywhere".** Providers express "always" differently (Copilot `applyTo: "**"`, Claude Code no `paths` field). A neutral absence maps cleanly to both. **Why reject unknown fields:** a typo (`applies-to`) would otherwise silently make a scoped rule global.
> **Why `overrides`.** Some provider features have no neutral equivalent. A per-source escape hatch keeps them possible without polluting the neutral model; using it is a signal that the model may need a new neutral field (change control).

**SRC-4. Placeholders.** Bodies use `{{arguments}}` for the text the user typed after a prompt's command; MCP values use `{{env:NAME}}` for environment variables. Profiles define each provider's syntax.

> **Why.** Copilot uses `${input:…}`, Claude Code uses `$ARGUMENTS`; VS Code uses `${env:NAME}`, Claude Code `${NAME}`.

**SRC-5. Tool vocabulary** for prompts and agents: `read`, `search`, `edit`, `write`, `execute`, `web_fetch`, `web_search`, `todo`, `subagent`, and MCP tools as `mcp:<server>/<tool>` or `mcp:<server>/*`.

> **Why.** Agents restrict tools, and each provider names them differently (`read` vs `Read`, `kubernetes/pods_list` vs `mcp__kubernetes__pods_list`). A small neutral vocabulary covers the common capabilities; profiles map it.

**SRC-6. Skills** follow the open Agent Skills standard (`<name>/SKILL.md` + supporting files) and are used as-is.

> **Why.** Copilot, Claude Code and others already share this format, so no compilation is needed and supporting files keep working.

**SRC-7. MCP servers** are folders, `<scope>/mcp/<name>/`, each declaring one server in `server.toml` with the top-level keys `command`, `args`, `env` (unknown keys are rejected). The folder may also hold the server's own code (SRC-9). A folder without `server.toml` is an error. A scope-level `mcp.toml` is no longer read: if one exists, validation fails and names the folders to move its servers to (PRI-7). *Amended by D-017: servers were previously declared together as `[servers.<name>]` tables in one `mcp.toml` per scope.*

> **Why one folder per server.** With one shared `mcp.toml`, removing a server meant deleting its code folder and editing the shared file; now it is deleting one folder, like a skill (D-017).
> **Why.** Copilot VS Code (`servers`), Copilot CLI (`mcpServers`, `type = "local"`) and Claude Code (`mcpServers`, or a CLI registration at user scope) all differ; one neutral declaration is compiled to each.

**SRC-8. `repo_instructions`** (`project/repo-instructions.md`) holds always-on instructions for a repository, compiled to each provider's repo-wide instructions file. Providers that read the same file (`AGENTS.md`) share one target (CMP-2).

**SRC-9. Code that belongs to a customization lives with it, never in the core.** `src/lantoki/` holds only lantoki's core (loading, compiling, installing); `customizations/` holds the customizations and everything only they use, grouped so that removing one is deleting its file or folder. A skill's scripts stay in its folder (SRC-6). An MCP server's code stays in its folder (SRC-7), `customizations/<scope>/mcp/<name>/`, beside `server.toml`: `server.py`, a single-file script with its dependencies in an inline metadata block (PEP 723) and the shebang `#!/usr/bin/env -S uv run --script`, plus its tests in `tests/`. There is no second package or `pyproject.toml`: the server is part of lantoki's repository and the dependencies it alone needs stay out of lantoki's. The loader reads only `server.toml`; the code and tests are never compiled or installed into a harness. *Amended by D-017: the code previously lived in a separate `servers/<name>/` folder.*

> **Why.** The `python-verification-gate` server sat in `src/lantoki/` beside the compiler, and its `mcp` dependency was one of lantoki's, although only one MCP declaration uses it. Separating core from customization code makes each easier to work on, and a customization trivial to delete. A PEP 723 script keeps the server's dependency declared next to it without building a second package (D-016).

> **Why one file.** Before D-010 there were two placeholder sources (`AGENTS.md`, `copilot-instructions.md`); Copilot reads either, so keeping both would load the same instructions twice.

## 6. Provider profile model

**PRF-1. One TOML file per provider** in `src/lantoki/providers/<provider-id>.toml`, loaded and validated by the core. Unknown keys are rejected. The file name must equal `provider.id`.

> **Why TOML.** Consistent with `pyproject.toml` and the existing dynaconf configuration (D-004).
> **Why not read through dynaconf.** Application settings (`settings.toml`) are loaded with dynaconf, as the Python standards require. Profiles are read with the standard `tomllib` instead, because their keys are case-sensitive provider field names (`applyTo`, `argument-hint`) that a settings loader normalises (D-010).

**PRF-2. Provenance block** (`[provider]`): `id`, `name`, `docs` (URLs), `verified_with` (provider version), `verified_on` (date). → PRI-8.

**PRF-3. Outputs.** A list of `[[outputs]]`, each declaring: `kind`, `scope`, `target` (path template), `format`, optional `link` mode, and format-specific settings (front-matter mapping, JSON root key and server template, command argv). A provider may declare several outputs for one kind; a kind with no output is *unsupported* for that provider (reported, PRI-7).

> **Why several outputs per kind.** One provider can have several clients reading different files (Copilot: VS Code `mcp.json` and Copilot CLI `mcp-config.json`).

**PRF-4. Generic formats** implemented by the core:

| Format | Produces | Used for |
|---|---|---|
| `markdown` | Front matter (mapped from the source) + body with placeholders rendered; with `file`, the target is a folder holding that one file | instructions, prompts, agents, repo instructions |
| `directory` | The source directory itself | skills |
| `json` | A JSON document with a configurable root key and per-server template | MCP config files |
| `command` | `apply` / `remove` argv templates run through a CLI | MCP registrations stored in files lantoki must not own (e.g. `~/.claude.json`) |

> **Why `file`.** Some providers read a generated document only as a fixed file name inside a folder named after the source (Claude Code reads a prompt as `skills/<name>/SKILL.md`). With `file`, the target is that folder and INS-1 links the folder as a whole, so the provider's folder points into lantoki like any other skill instead of being a real folder that holds one link (D-011).

**PRF-5. Front-matter mapping.** Each provider field is a template (`"{description}"`), a constant, or a rule `{ from, transform, omit_when, default, sep }`. Transforms are a small, generic, documented set (template, constant, join, list, tools, globs).

> **Why a closed set.** An open expression language would turn profiles into code (violating PRI-3) and make them hard to review. New needs add a generic transform via change control.

**PRF-6. Tool map** (`[tools]`): neutral tool → list of provider tool names; `mcp` is a template with `{server}` and `{tool}`. Unmapped neutral tools are dropped with a warning (PRI-7).

**PRF-7. Placeholders** (`[placeholders]`): provider syntax for `arguments` and `env`.

**PRF-8. CLI discovery** (`[cli].candidates`): commands looked up on `PATH`, and globs whose newest version-numbered match is used.

> **Why globs.** The Claude desktop app bundles its CLI under a versioned folder (`~/.config/Claude/claude-code/<version>/<hash>/claude`) that is not on `PATH`.

## 7. Compilation

**CMP-1.** For each enabled provider, each output in its profile and each matching source, the core produces one artifact. The process is pure (no file-system writes) so it can be shown as a plan.

**CMP-2. Target collisions.** Two artifacts with the same target and identical content are merged; with different content, compilation fails before anything is written.

**CMP-4. Empty aggregates.** A `json` output with no matching sources produces no artifact (an empty MCP config is not installed).

> **Why.** Two providers may legitimately target the same file (e.g. both read `AGENTS.md`); different contents would make the last writer win silently.

**CMP-3. Validation** of all sources and profiles runs before compilation and reports every error with file and field.

## 8. Installation

**INS-1. Symlinks by default.** Each target is a symlink: to the source itself when the provider reads the neutral format unchanged (skills), otherwise to the compiled artifact in the compiled store.

> **Why.** Decided by the owner (D-003): targets stay pointers to lantoki-managed content, so it is always clear where a file comes from and lantoki can refresh content in one place. Accepted consequence: symlinks are absolute and machine-specific, so repos should not commit them (INS-9).

**INS-2. Copies only where a provider cannot follow symlinks**, declared per output with `link = "copy"`.

> **Why.** Claude Code does not load path-scoped project rules that are symlinked from outside the project ([memory docs](https://code.claude.com/docs/en/memory), D-007). The exception is per output, not a global switch, so other providers keep symlinks.

**INS-3. Manifest.** Each scope has a manifest at `~/.local/state/lantoki/manifests/<scope-key>.json` listing every installed target with provider, source, mode, content hash and (for commands) the remove argv.

> **Why.** It is the basis for PRI-5 (ownership), INS-5 (pruning) and INS-7 (selections). Markers inside files are not enough: JSON files cannot hold comments, and CLI registrations are not files.

**INS-4. Conflicts.** A target that exists and is not owned by lantoki is skipped and reported; the run exits non-zero. Nothing is overwritten.

**INS-5. Pruning.** When a source is deleted or renamed, or a provider is disabled, its previously installed targets are removed on the next sync, if lantoki still owns them.

> **Why.** Without pruning, stale rules keep influencing assistants after their source is gone.

**INS-6. Adoption.** On the first run, existing targets that are symlinks into lantoki or files carrying lantoki's generated-file marker are taken into the manifest instead of reported as conflicts.

> **Why.** Smooth migration from earlier lantoki versions, which installed without a manifest.

A real folder is adopted when it is not empty and everything in it is itself adoptable. Prunes are applied before installs, so a target that moves from a file inside a folder to the folder itself (D-011) never has its new content removed by the prune of its old path.

CLI registrations (`command` outputs) cannot be inspected for ownership. A registration that already exists under the same name is only replaced with `--adopt-commands`, which runs the profile's `remove` before `apply`.

**INS-7. Repo selection.** For project scope the user chooses which sources apply to the repository (interactively or with `--all`). The selection is stored in the manifest so re-syncing does not ask again.

> **Why.** Not every standard fits every repo (e.g. Airflow rules), but re-answering on every sync discourages syncing.

Sources added since the last sync are asked about when a terminal is available; otherwise they are skipped and reported, never installed silently. Deselecting a source prunes its targets (INS-5).

**INS-8. Dry run.** `lantoki plan …` shows every create, update, adopt, prune and conflict without changing anything.

**INS-9. Repositories never commit lantoki's outputs, and lantoki makes sure of it.** Outputs installed into a repo are machine-specific (INS-1). `sync repo` lists every target it owns in that repository, relative to its root, in a lantoki-managed block of the repository's local exclude file (`.git/info/exclude`, found through git, so worktrees work), and keeps the block in step with the manifest: pruned targets leave it, and a repository with no lantoki targets has no block. Lines outside the block are never touched (PRI-5). A target the repository already tracks in git is not excluded; `plan repo` reports it as a warning. *Amended by D-015: repositories previously had to add the paths to their own `.gitignore`.*

> **Why.** Observed: lantoki's own repo committed absolute symlinks to a former path (`~/projects/test_repositories/…`); all five broke when the repo moved. Asking each repository to list the paths in `.gitignore` copies provider knowledge (folder names) into every project, goes stale when a profile changes, and a broad entry such as `/AGENTS.md` hides a project's own committed file. lantoki already knows its exact targets (INS-3), and `.git/info/exclude` is per clone, like the outputs themselves, so nothing about a machine's selection is committed.

## 9. Interface and quality

**CLI-1.** `lantoki validate`, `lantoki providers`, `lantoki plan user`, `lantoki plan repo <path> [--all]`, `lantoki sync user`, `lantoki sync repo <path> [--all|--select]`; `--provider` limits a run to some providers, `--adopt-commands` enables INS-6 for CLI registrations. Exit codes: 0 ok, 1 conflicts or failed steps, 2 invalid sources, profiles or options. `just` recipes wrap them.

**CLI-2.** Supporting executables are installed on `PATH` with `just install-tools`, so profiles and MCP declarations never contain absolute paths: `lantoki` itself, and each MCP server script as `~/.local/bin/<name>`, a symlink to `customizations/<scope>/mcp/<name>/server.py` (SRC-9) that `uv` runs with the script's own dependencies. *Amended by D-016: the `python-verification-gate` server used to be a second script of lantoki's own package.*

> **Why.** MCP configs with an absolute path to the repo broke when the repo moved (D-006).

**QLT-1.** Python standards from `customizations/project/instructions/python.md` and `tests.md` apply to lantoki itself (Ruff `ALL`, pytest Given-When-Then, coverage ≥ 75%).

**QLT-2.** A test compiles every kind with a fake provider profile that exists only as a test fixture, proving PRI-4.

**QLT-3.** Each real profile has golden tests comparing its compiled output for a fixture set of sources.

**QLT-4.** Dependencies are kept at their latest compatible versions; an upper bound requires a comment explaining the incompatibility (D-005).

**QLT-5.** Tests never touch the real home directory or the real provider CLIs.

### 9.1 Development tooling

**DEV-1. The repository follows the galtzagorri template.** It is linked to the template through copier (`.copier-answers.yml`) and kept in sync with `just update`, which merges the template, relocks, reinstalls and runs `just check`, leaving a working repository ready to commit.

> **Why.** Every personal project shares the same tooling (system packages, user tools, formatters, linters, hooks). Hand-maintained copies drift exactly like the per-harness copies PUR-1 removes: a fix made in one project never reaches the others. With the template as the single owner, a tooling fix is made once and reaches every project through an update that proves itself with the checks.

**DEV-2. PDM (uv backend) and just.** Dependencies are managed with PDM and locked in `pdm.lock`, which is committed; `uv.lock` and the `[tool.uv]` configuration are removed. Ownership of dependency declarations:

| Declaration | Owner | Content |
|---|---|---|
| `base` group | template | minimum versions of the tools the template's recipes need; never edited here |
| `dependencies` | lantoki | runtime dependencies |
| `dev` group | lantoki | lantoki's own development tools (coverage, bandit, pytest plugins, …), and higher floors for `base` tools when lantoki needs them |
| `docs` group | lantoki | documentation build |

> **Why.** It is the template's layout (DEV-1). Keeping template-owned and project-owned lines apart is what lets updates merge without conflicts: tested with copier, a project that edited the template's lines got a conflict on every update that touched them, while separate groups merged cleanly. PDM resolves all groups into one lock, so the next developer gets the same versions with one command.

**DEV-3. Python ≥ 3.15** (`python_min` template answer). *Supersedes the `>=3.12,<3.13` pin.*

> **Why.** QLT-4: the latest compatible version, and an upper bound needs a stated incompatibility; the old pin had none. Verified 2026-11-17 on Python 3.15.2: every runtime, dev and docs dependency installs and the 133 tests pass. PyYAML 6.0.3 has no 3.15 wheel and is built from source without the libyaml C extension; the pure-Python parser is fast enough for files of lantoki's size. Raising the minimum later is a deliberate `just update --data python_min=3.X` on a branch, never a side effect of a template update.

**DEV-4. Template recipes keep their meaning; lantoki configures them through `pyproject.toml`.** `just check`, `just test`, `just fmt`, `just lint` and the pre-push hook are the template's. lantoki's requirements on them are tool configuration: pytest runs with coverage and fails under 75 % (QLT-1) through `[tool.pytest.ini_options]`, and Ruff `ALL` through `[tool.ruff]`. lantoki's own recipes (`validate`, `providers`, `plan-user`, `sync-user`, `sync-repo`, `install-tools`, `security`, `docs-*`) live in `project.just`, which lantoki owns; the `Justfile` is wholly the template's and imports it (galtzagorri JUS-1). *Amended by D-013: they previously lived below a project-specific marker in the Justfile.*

> **Why.** If lantoki redefined template recipes, every update touching them would conflict, and `just check` would mean different things in different projects. Tool configuration is the extension point the template leaves to projects. A separate file for lantoki's recipes means no file is edited by both lantoki and the template, so updates replace the Justfile without conflicts. `just check` now also lints YAML, JSON and shell files, which lantoki's old recipes skipped.

**DEV-5. lantoki stays an installable package.** It keeps `[project.scripts]` and a PEP 517 build backend, and the template's `just install-tool-editable` (galtzagorri PKG-2) installs it on `PATH` with `uv tool install --editable`; `just install-tools` stays as lantoki's name for it (CLI-2). The template's `just install-tool` installs the built wheel instead, to check the package as a user would get it. *Amended by D-014: the recipe now comes from the template.*

> **Why.** CLI-2 needs `lantoki` and `python-verification-gate` on `PATH`. The template generates non-installable projects (`distribution = false`), so packaging is either a template option (preferred, see the [adoption plan](plans/2026-11-17-galtzagorri-adoption.md)) or a deliberate override of template-owned lines that every update must keep.

**DEV-6. Adopting the template changes no compiled output.** After the migration, `lantoki plan user` and the golden tests report exactly what they reported before.

> **Why.** The migration is tooling only. PRI-6 makes this measurable: identical sources and profiles must give identical artifacts, so any difference is a migration bug.

**DEV-7. `just init` reproduces the whole setup on a new machine (PUR-2).** lantoki uses the template's `just init` (galtzagorri INI-1), and its `project.just` defines the `init-project` hook as `install-servers` then `sync-user`. On a fresh Linux machine, `git clone` + `sudo apt install just` + `just init` then: installs the tooling and the environment, puts `lantoki` on `PATH` (`install-tool-editable`, DEV-5) and links every MCP server script after it (`install-servers`, CLI-2, SRC-9), installs every user-level customization for every provider (`sync user`), installs lantoki's own project-level customizations (the template's `init-ai`) and runs `just check`.

> **Why.** PUR-2 requires that cloning the repository and running one command reproduces the whole setup; before this, it took `just setup`, `just install-tools` and `just sync-user`, in that order. The template already provides the entry point and the order (INI-1): `install-tool-editable` runs before `init-project`, so `lantoki` is on `PATH` when `sync-user` needs it. lantoki only adds what is specific to it.

## 10. Non-goals

- **NG-1.** Settings stored only on a provider's servers (e.g. personal preferences in the Claude desktop app's Chat tab, claude.ai project instructions) cannot be managed from files and are out of scope.
- **NG-2.** Harness application settings unrelated to customization (themes, keybindings, permissions) are out of scope; they belong to each tool's own settings.
- **NG-3.** Organisation-wide distribution (managed policies) is out of scope.

## 11. Provider facts (evidence)

Facts the profiles rely on. Update with the date verified.

| Provider | Fact | Source | Verified |
|---|---|---|---|
| Claude Code | User rules in `~/.claude/rules/` load in every project; symlinks allowed; a rule without `paths` always loads. | [memory](https://code.claude.com/docs/en/memory) | 2026-11-16 |
| Claude Code | Project rules symlinked from outside the project need approval, and then only rules **without** `paths` load. | [memory](https://code.claude.com/docs/en/memory) | 2026-11-16 |
| Claude Code | Reads `AGENTS.md` when no `CLAUDE.md` exists (v2.1.277+). | [memory](https://code.claude.com/docs/en/memory) | 2026-11-16 |
| Claude Code | Subagents in `~/.claude/agents/`, `.claude/agents/`; `tools` comma string or list, omitted = inherit all; MCP tools `mcp__<server>__<tool>`, `mcp__<server>__*`. | [sub-agents](https://code.claude.com/docs/en/sub-agents) | 2026-11-16 |
| Claude Code | Skills in `~/.claude/skills/<name>/SKILL.md`, `.claude/skills/`; symlinked skill dirs supported; `$ARGUMENTS`; `disable-model-invocation`. | [skills](https://code.claude.com/docs/en/skills) | 2026-11-16 |
| Claude Code | User MCP servers live in `~/.claude.json`; manage with `claude mcp add-json/remove --scope user`; project servers in `.mcp.json` (`mcpServers`). | [mcp](https://code.claude.com/docs/en/mcp) | 2026-11-16 |
| Claude Code | Desktop app bundles the CLI at `~/.config/Claude/claude-code/<version>/<hash>/claude` (not on `PATH`). | observed | 2026-11-16 |
| GitHub Copilot | User skills `~/.copilot/skills/`; project skills `.github/skills/`. | [agent skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills) | 2026-11-16 |
| GitHub Copilot | User agents `~/.copilot/agents/` (`.agent.md`); project agents `.github/agents/`. | [custom agent reference](https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference) | 2026-11-16 |
| GitHub Copilot | VS Code `mcp.json` uses top-level `servers`; Copilot CLI `mcp-config.json` uses `mcpServers`. | earlier version of this document | 2026-03 |
| GitHub Copilot | VS Code user instructions/prompts in `~/.config/Code/User/{instructions,prompts}/`; repo files in `.github/`. | earlier version of this document | 2026-03 |
| GitHub Copilot | Project instructions are `.github/copilot-instructions.md` **or** `AGENTS.md`. | [custom instructions](https://code.visualstudio.com/docs/copilot/customization/custom-instructions) | 2026-11-16 |
| GitHub Copilot | Prompt variables use `${input:<name>}`. | [prompt files](https://code.visualstudio.com/docs/copilot/customization/prompt-files) | to verify |

## 12. Change control

**CHG-1.** A change to what lantoki must do (a requirement, principle, model or provider fact) is first written here: edit the affected section and add an entry to the decision log below. Only then is the code changed.

**CHG-2.** Commits and pull requests that change behaviour cite the requirement or decision IDs they implement (e.g. `feat(installer): prune stale targets (INS-5)`).

**CHG-3.** IDs are never reused. A superseded requirement is marked *Superseded by D-xxx*, not deleted.

> **Why.** Every code change must be traceable to a reason. Specs drift silently otherwise, and the next person (or assistant) cannot tell a deliberate decision from an accident.

### Decision log

| ID | Date | Decision | Reason |
|---|---|---|---|
| D-001 | 2026-11-16 | lantoki is the single, multi-provider entry point for all AI customization (PUR-1, PRI-1, PRI-2). | Formalises the project's purpose after customization was written outside lantoki. |
| D-002 | 2026-11-16 | Sources use a neutral dialect; existing Copilot-dialect sources are migrated (SRC-1). | Copilot dialect made Copilot privileged and leaked its quirks into other providers. |
| D-003 | 2026-11-16 | Installed targets are symlinks, to the source or to the compiled store (INS-1). | Owner's choice: one place to refresh content and clear provenance; machine-specific links accepted. |
| D-004 | 2026-11-16 | Provider profiles are TOML, validated by a schema (PRF-1). | Consistent with existing configuration files. |
| D-005 | 2026-11-16 | Always use the latest compatible dependency versions (QLT-4). | Owner's standing policy. |
| D-006 | 2026-11-16 | Supporting executables are installed on `PATH`; configs never hold absolute repo paths (CLI-2). | Absolute paths broke when the repo moved. |
| D-007 | 2026-11-16 | Claude Code path-scoped project rules are copied, not symlinked (INS-2). | Claude Code ignores them when symlinked from outside the project. |
| D-008 | 2026-11-16 | Ownership is tracked in a per-scope manifest (INS-3), with adoption of earlier installs (INS-6). | Markers cannot be put in JSON or CLI registrations; needed for safe pruning. |
| D-009 | 2026-11-16 | Provider logic is data in profiles; the core is provider-agnostic (PRI-3, PRI-4). | The number of providers will grow; adding one must be trivial and risk-free. |
| D-010 | 2026-11-16 | Implementation clarifications: `tools` allowed in prompts (SRC-3); one repo-instructions source shared through `AGENTS.md` (SRC-8); profiles read with `tomllib` (PRF-1); no empty JSON aggregates (CMP-4); `--adopt-commands` for CLI registrations (INS-6); new repo sources never installed silently (INS-7); exit codes (CLI-1). | Found while migrating the existing sources and comparing against the previous installer's output (`tests/fixtures/baseline`). |
| D-011 | 2026-11-16 | A `markdown` output may set `file`: the target is a folder holding that one generated file, and the folder is what gets linked (PRF-4, INS-1, INS-6). Claude Code prompts use it for `skills/<name>/SKILL.md`. | Claude Code prompts were installed as a real folder holding only a `SKILL.md` symlink, unlike every other skill; the owner wants the folder itself to be the link. |
| D-012 | 2026-11-17 | The repository's development tooling follows the galtzagorri template: copier link, PDM + just, template-owned `base` group, Python ≥ 3.15, template recipes configured through `pyproject.toml`, packaging kept (DEV-1 … DEV-6). Executed by the [adoption plan](plans/2026-11-17-galtzagorri-adoption.md). | lantoki's hand-written uv tooling had drifted from the owner's other projects; a single template keeps them aligned and makes updates verifiable. |
| D-013 | 2026-11-18 | lantoki's own recipes move from below the Justfile's project marker to `project.just`; the `Justfile` becomes wholly template-owned (DEV-4, galtzagorri G-005 / JUS-1). | One owner per file: template updates replace the Justfile without conflicts. Owner's request. |
| D-014 | 2026-11-18 | `just init` (galtzagorri INI-1) is the one command that reproduces lantoki's setup on a new machine; lantoki's `init-project` hook runs `sync-user` (DEV-7); `install-tools` becomes lantoki's name for the template's `install-tool-editable` (DEV-5). | PUR-2 asked for one command; the template now provides it, in the right order. Owner's request. |
| D-015 | 2026-11-18 | `sync repo` keeps its targets out of git through a managed block in `.git/info/exclude`, instead of asking each repository to list them in `.gitignore` (INS-9). | Needed for `just init` (D-014) to leave a clean tree in any project, without the template duplicating lantoki's provider knowledge. |
| D-016 | 2026-11-18 | Code only a customization uses lives with it under `customizations/`, never in `src/lantoki/` (SRC-9). An MCP server is one folder, `customizations/<scope>/servers/<name>/`, holding a PEP 723 single-file script and its tests, linked onto `PATH` by `just install-tools` (CLI-2, DEV-7); `python-verification-gate` moves there and `mcp` leaves lantoki's dependencies. No second package. Executed by the [separation plan](plans/2026-11-18-customization-code-separation.md). | Customization code was mixed with the core modules; a clear separation eases development and makes deleting a customization deleting a folder. Owner's request; a separate `pyproject.toml` per server was rejected as a second package. |
| D-017 | 2026-11-18 | Each MCP server is a folder, `<scope>/mcp/<name>/`, holding its declaration (`server.toml`) and, if lantoki provides it, its code and tests; the scope-level `mcp.toml` is retired, and a leftover one fails validation (SRC-7, SRC-2, SRC-9, CLI-2). Executed by the [MCP folders plan](plans/2026-11-18-mcp-server-folders.md). | Deleting a customization must be deleting one folder (owner's request); one shared `mcp.toml` kept a server's declaration apart from its code. |
