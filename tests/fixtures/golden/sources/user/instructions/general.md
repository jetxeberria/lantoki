---
description: Global instructions applied to all chats.
---
# General Instructions

## Assistant customization lives in lantoki

All AI-assistant customization (instructions, rules, skills, agents, prompts, MCP servers) is managed in the lantoki repository (`~/repos/lantoki`), the single entry point mapped to every harness (GitHub Copilot, Claude Code, ...). Never create or edit a harness's own config files directly (`~/.claude/`, `~/.copilot/`, `~/.config/Code/User/`, a repo's `.github/` or `.claude/`). Make the change in lantoki's sources and map it through its installer; see lantoki's `AGENTS.md`.
