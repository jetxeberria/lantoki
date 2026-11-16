# Source Map — Starting Points to Verify

Leads for finding each harness's authoritative docs and changelog. **These are search
starting points, not facts.** URLs migrate, products rebrand, and file conventions change —
always confirm the page still resolves and reflects the current version before quoting it. Do
not state file paths, version numbers, or feature details from this file; get those live.

If a harness isn't listed, it isn't exotic — it's just not enumerated here. Search for it the
same way: `<name> documentation`, `<name> changelog`, `<name> github`.

For each harness, look for four things: (1) official docs home, (2) configuration/customization
reference, (3) changelog / release notes, (4) source repository.

## Claude Code (Anthropic)
- Search: `Claude Code documentation`, `Claude Code changelog`, `Claude Code settings`.
- Leads: Anthropic's docs site (docs.* under anthropic/claude) and Anthropic's GitHub.
- Fast-moving areas to re-check every time: instruction files, skills, subagents, hooks,
  MCP config, slash commands, permissions/settings scopes, plugins/marketplace.
- Note: behavior can differ between the CLI and IDE integrations — confirm which the user means.

## OpenAI Codex CLI
- Search: `OpenAI Codex CLI docs`, `Codex CLI config`, `Codex CLI changelog`.
- Leads: OpenAI's developer docs and the Codex CLI GitHub repo (README + docs folder + example
  config).
- Re-check: config file format/location, AGENTS.md handling, approval/sandbox modes, MCP support.

## Cursor
- Search: `Cursor docs rules`, `Cursor changelog`, `Cursor MCP`.
- Leads: Cursor's official docs site and changelog page.
- Re-check: the rules system (format and location have changed across versions), modes
  (ask/agent), MCP config, memory features.

## Windsurf
- Search: `Windsurf docs`, `Windsurf rules`, `Windsurf changelog`.
- Leads: the vendor's docs site and changelog.
- Re-check: rules/instruction files, MCP, modes, memory.

## Aider
- Search: `Aider docs`, `Aider conventions`, `Aider config`, `Aider releases`.
- Leads: Aider's docs site and GitHub repo/release history.
- Re-check: conventions file usage, config file scopes, model config, repo map behavior.

## Gemini CLI (Google)
- Search: `Gemini CLI docs`, `Gemini CLI GEMINI.md`, `Gemini CLI changelog`.
- Leads: Google's Gemini CLI GitHub repo and docs.
- Re-check: GEMINI.md handling and scope, MCP, extensions/commands, settings.

## GitHub Copilot (Coding Agent, chat, CLI)
- Search: `GitHub Copilot custom instructions docs`, `Copilot coding agent`, `Copilot changelog`.
- Leads: GitHub Docs and the GitHub changelog/blog.
- Re-check: instruction files location, agent vs chat differences, MCP support, repository
  custom instructions vs personal.

## Cline / Roo Code
- Search: `Cline docs rules`, `Cline MCP`, `Roo Code docs`, plus changelog/releases.
- Leads: the projects' docs sites and GitHub repos.
- Re-check: rules files, custom modes, MCP marketplace, memory.

## Amp (Sourcegraph)
- Search: `Amp agent docs`, `Amp changelog`.
- Leads: Sourcegraph's Amp docs and changelog.

## Zed (agent features)
- Search: `Zed agent docs`, `Zed assistant rules`, `Zed changelog`.
- Leads: Zed's docs and release notes.

## OpenCode / Continue / others
- Search: `<name> docs`, `<name> config`, `<name> changelog`, `<name> github`.
- Leads: the project's docs site and repo.

## Cross-cutting things to look up regardless of harness
- **AGENTS.md adoption** — search `AGENTS.md <harness>` to confirm whether and how this harness
  reads it *today*; adoption is changing across the ecosystem.
- **MCP** — the Model Context Protocol spec and the harness's MCP config docs; transports and
  config keys differ and evolve.
- **Enterprise/managed config** — many harnesses have admin-imposed settings that are easy to
  miss; search `<harness> enterprise settings` / `managed settings`.
