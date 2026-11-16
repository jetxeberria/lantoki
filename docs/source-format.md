# Source format

The neutral format every customization is written in (SPECIFICATION §5). lantoki validates it on every command; unknown fields are errors.

## Layout

```
customizations/
  user/                          # applies to every project on this machine
    instructions/<name>.md
    prompts/<name>.md
    agents/<name>.md
    skills/<name>/SKILL.md (+ supporting files)
    mcp.toml
  project/                       # chosen per repository with `lantoki sync repo`
    repo-instructions.md
    instructions/<name>.md
    prompts/<name>.md
    skills/<name>/SKILL.md
    mcp.toml
```

`<name>` is the file (or folder) name: lowercase letters, digits and single hyphens (`python`, `k8s-root-cause`).

## Markdown kinds

YAML front matter, then the body.

| Field | instruction | prompt | agent | repo-instructions | Meaning |
|---|:-:|:-:|:-:|:-:|---|
| `description` | required | required | required | required | What it is / when to use it. |
| `title` | ✓ | ✓ | ✓ | ✓ | Human-readable name (providers that show one). |
| `applies_to` | ✓ | | | | List of globs. **Omit to apply everywhere.** |
| `argument_hint` | | ✓ | ✓ | | Hint shown when invoking. |
| `tools` | | ✓ | ✓ | | Neutral tool list (below). Omit for the provider's default. |
| `overrides` | ✓ | ✓ | ✓ | ✓ | `{<provider-id>: {<field>: value}}`: extra fields for one provider only. |

```markdown
---
description: Python coding standards.
title: Python Engineering Standards
applies_to: ["**/*.py"]
---
# Python standards
...
```

### Tools

`read`, `search`, `edit`, `write`, `execute`, `web_fetch`, `web_search`, `todo`, `subagent`, and MCP tools as `mcp:<server>/<tool>` or `mcp:<server>/*`. A tool a provider has no equivalent for is dropped for that provider and reported as a warning.

### Placeholders

- `{{arguments}}`: in prompt and agent bodies, the text the user typed after the command.
- `{{env:NAME}}`: in MCP values, an environment variable.

### Provider-only fields

Use `overrides` sparingly; it signals a capability the neutral model lacks (consider proposing a neutral field through the spec):

```yaml
overrides:
  github-copilot:
    agent: agent
```

## Skills

A folder following the [Agent Skills](https://agentskills.io) standard, installed as-is: `SKILL.md` with `name` and `description` front matter, plus any supporting files.

## MCP servers

```toml
[servers.python-verification-gate]
command = "python-verification-gate"   # on PATH (CLI-2); never an absolute repo path
args = []
env = { API_TOKEN = "{{env:API_TOKEN}}" }
```
