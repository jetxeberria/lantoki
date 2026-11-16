# Provider profiles

A provider profile is everything lantoki knows about one AI harness, as data (SPECIFICATION §6). Adding `src/lantoki/providers/<id>.toml` is all it takes to support a new provider (PRI-4). Unknown keys are errors; run `lantoki validate` after editing.

The shipped profiles are the best examples: [`claude-code.toml`](../src/lantoki/providers/claude-code.toml), [`github-copilot.toml`](../src/lantoki/providers/github-copilot.toml), and the fictional test provider [`acme.toml`](../tests/fixtures/providers/acme.toml), which uses every feature.

## `[provider]` — identity and provenance

| Key | Required | Meaning |
|---|:-:|---|
| `id` | ✓ | Must equal the file name. Lowercase, digits, hyphens. Used in `overrides` and on the CLI. |
| `name` | ✓ | Display name. |
| `docs` | ✓ | Documentation URLs the profile was written from (PRI-8). |
| `verified_with` | ✓ | Provider version (or docs snapshot) the profile was checked against. |
| `verified_on` | ✓ | Date of that check (TOML date). |

## `[placeholders]` — body and value syntax

| Key | Meaning | Claude Code | Copilot |
|---|---|---|---|
| `arguments` | Replaces `{{arguments}}` | `$ARGUMENTS` | `${input:arguments}` |
| `env` | Replaces `{{env:NAME}}`; `{name}` is the variable | `${{{name}}}` → `${NAME}` | `${{env:{name}}}` → `${env:NAME}` |

## `[tools]` — tool names

```toml
[tools]
mcp = "mcp__{server}__{tool}"     # how MCP tools are named; {tool} may be "*"

[tools.map]                        # neutral name -> provider names (one or more)
read = ["Read"]
search = ["Grep", "Glob"]
```

Neutral tools missing from `map` are dropped for this provider with a warning.

## `[cli]` — command-line tool

`candidates`: commands looked up on `PATH`, or globs (`{home}` allowed) whose newest version-numbered match is used. Required when any output uses `format = "command"`.

## `[[outputs]]` — where the provider reads each kind

One entry per place the provider reads a kind of customization. A provider may have several outputs for one kind (e.g. two MCP files for two clients); a kind with no output is reported as unsupported.

| Key | Meaning |
|---|---|
| `kind` | `instruction`, `prompt`, `agent`, `skill`, `mcp`, `repo_instructions` |
| `scope` | `user` or `project` |
| `format` | `markdown`, `directory`, `json` or `command` (allowed per kind below) |
| `target` | Path template: `{home}`, `{repo}` (project scope), `{name}` |
| `link` | `symlink` (default) or `copy`, only where the provider cannot follow symlinks (INS-2) |
| `file` | `markdown` only: `target` is a folder and the generated document is written inside it under this name; the folder is what gets linked (D-011) |

| Kind | Formats |
|---|---|
| instruction, prompt, agent, repo_instructions | `markdown` |
| skill | `directory` |
| mcp | `json`, `command` |

### `format = "markdown"`

`[outputs.front_matter]` maps provider fields, in output order:

| Value | Result |
|---|---|
| `"{field}"` | That source field as-is (lists stay lists); omitted if the field is absent. |
| `"text {field} …"` | String template; omitted if any referenced field is absent. |
| `true`, `3`, `["x"]` | Constant. |
| `{ from = "field", transform = "join", sep = ", ", default = "**" }` | Joins a list; `default` when the field is absent. |
| `{ from = "tools", transform = "tools", sep = ", " }` | Maps neutral tools; joined with `sep`, or a list without it. |

Source fields: `name`, `title`, `description`, `applies_to`, `argument_hint`, `tools`. A source's `overrides.<provider-id>` is merged last. Bodies get placeholders rendered and a generated-file marker.

### `format = "directory"`

Links the source folder (skills).

### `format = "json"`

All sources of the kind are aggregated into one document: `document` (static keys) plus `root_key` → `{ <server-name>: server }`, where `server` is a template over `command`, `args`, `env`, `name`. Keys whose value is absent are omitted.

```toml
root_key = "servers"
document = { inputs = [] }
server = { type = "stdio", command = "{command}", args = "{args}", env = "{env}" }
```

### `format = "command"`

For configuration stored where lantoki must not own the file: one registration per source, run through the provider CLI.

```toml
apply  = ["{cli}", "mcp", "add-json", "--scope", "user", "{name}", "{server_json}"]
remove = ["{cli}", "mcp", "remove", "--scope", "user", "{name}"]
server = { command = "{command}", args = "{args}", env = "{env}" }
```

`{server_json}` is the rendered `server` as JSON. `remove` is recorded in the manifest and run when the source disappears; with `--adopt-commands` it also runs before the first `apply`, replacing an existing registration of the same name.

## Checklist for a new profile

1. Every `target` and field comes from the provider's documentation; cite it in `docs`.
2. Facts that drove non-obvious choices (e.g. `link = "copy"`) go in SPECIFICATION §11 with dates.
3. `lantoki validate` and `lantoki plan user` show the expected targets and no unexpected warnings.
4. Add golden tests for the new profile's output.
