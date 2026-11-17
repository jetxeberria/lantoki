---
description: Global instructions applied to all chats.
---
# General Instructions

## Assistant customization lives in lantoki

All AI-assistant customization (instructions, rules, skills, agents, prompts, MCP servers) is managed in the lantoki repository (`~/repos/lantoki`), the single entry point mapped to every harness (GitHub Copilot, Claude Code, ...). Never create or edit a harness's own config files directly (`~/.claude/`, `~/.copilot/`, `~/.config/Code/User/`, a repo's `.github/` or `.claude/`). Make the change in lantoki's sources and map it through its installer; see lantoki's `AGENTS.md`.

## Specification and plan before code

For any software project, a change that is more than a small fix starts with documents, not code:

1. **Specification.** Write the change in the project's specification: the affected requirements and a decision-log entry, each with its reason. If the project has no specification, propose creating one first.
2. **Plan.** Write a plan: phases in order, how each is verified, risks, and what is out of scope. Base it on facts checked in the repository, not on assumptions.
3. **Approval.** Stop and ask the owner to review both. Change code only after they approve.

Commits then cite the decision or requirement IDs they implement.
