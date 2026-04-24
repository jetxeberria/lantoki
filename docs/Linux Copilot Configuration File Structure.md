Here is the complete file tree tailored specifically for **Linux** environments.
This structure divides your central sync repository into two clear domains: **User-Level** (your global settings applied to every workspace) and **Project-Level** (the standardized files you will selectively symlink into specific project repositories).

### ---

**1\. Your Central Sync Repository (lantoki/)**

This is the repository you will push to GitHub/GitLab to sync your configurations across your Linux machines.

Plaintext

lantoki/
│
├── user-level/ \# Global configurations for your Linux profile
│ │
│ ├── instructions/ \# Global instructions (applied to ALL chats)
│ │ ├── general.instructions.md
│ │ └── linux-dev.instructions.md
│ │
│ ├── prompts/ \# Global slash commands (e.g., /refactor)
│ │ ├── refactor.prompt.md
│ │ └── pr-review.prompt.md
│ │
│ ├── skills/ \# Global skills commands (e.g., /domain-logic-extractor)
│ │ └── domain-logic-extractor/
│ │ └── SKILL.md
│ │
│ └── mcp/ \# Global tool connections (Databases, local APIs, etc.)
│ ├── vscode-mcp.json \# For GitHub Copilot Chat in VS Code
│ └── cli-mcp-config.json \# For GitHub Copilot CLI (schema differs slightly)
│
└── project-level/ \# Templates to symlink into specific codebases
│ │
│ ├── global-repo/ \# Core repository files
│ │ ├── copilot-instructions.md \# General project architecture and rules
│ │ └── AGENTS.md \# Always-on instructions for autonomous agents
│ │
│ ├── scoped-instructions/ \# Path-specific rules (requires YAML frontmatter)
│ │ ├── react.instructions.md \# e.g., applyTo: \["\*\*/components/\*\*/\*.tsx"\]
│ │ ├── python.instructions.md \# e.g., applyTo: \["\*\*/\*.py"\]
│ │ └── tests.instructions.md \# e.g., applyTo: \["\*\*/tests/\*\*"\]
│ │
│ ├── project-prompts/ \# Project-specific macros
│ │ └── generate-docs.prompt.md
│ │
│ ├── project-mcp/ \# Project-specific tool connections
│ │ └── shared-mcp.json
│ │
│ └── project-skills/ \# Reusable agent capabilities
│ │ └── lint-python/
│ │ │ ├── SKILL.md
│ │ │ └── run-linter.sh

### ---

**2\. How the Symlinks Map to Your Linux Filesystem**

When you clone your sync repository to a new Linux machine (e.g., \~/lantoki), your initialization script will create symlinks pointing from the system/project locations _to_ your synced repository.

#### **User-Level Symlink Targets (Global Settings)**

VS Code on Linux stores its user profile data in \~/.config/Code/User/. The Copilot CLI stores its data in \~/.copilot/.

| File/Folder in Sync Repo           | Target Linux Path (Where Copilot looks) |
| :--------------------------------- | :-------------------------------------- |
| user-level/instructions/           | \~/.config/Code/User/instructions/      |
| user-level/prompts/                | \~/.config/Code/User/prompts/           |
| user-level/mcp/vscode-mcp.json     | \~/.config/Code/User/mcp.json           |
| user-level/mcp/cli-mcp-config.json | \~/.copilot/mcp-config.json             |

_(Note: If you use VS Code Insiders, replace Code with Code \- Insiders in the paths)._

#### **Project-Level Symlink Targets (Per Repository)**

When you initialize a new coding project (e.g., \~/Projects/my-new-app), you will symlink files from the project-level directory of your sync repo into the specific project folder.

| File/Folder in Sync Repo                             | Target Project Path (Where Copilot looks)                |
| :--------------------------------------------------- | :------------------------------------------------------- |
| project-level/global-repo/copilot-instructions.md    | \<project-root\>/.github/copilot-instructions.md         |
| project-level/global-repo/AGENTS.md                  | \<project-root\>/AGENTS.md                               |
| project-level/scoped-instructions/\*.instructions.md | \<project-root\>/.github/instructions/\*.instructions.md |
| project-level/project-prompts/\*.prompt.md           | \<project-root\>/.github/prompts/\*.prompt.md            |
| project-level/project-mcp/shared-mcp.json            | \<project-root\>/.vscode/mcp.json                        |
| project-level/project-skills/<skill-name>/           | \<project-root\>/.github/skills/<skill-name>/            |

### ---

**3\. A Critical Detail on MCP JSONs**

Notice that the user-level MCP folder contains **two** files. This is because the JSON schema expected by VS Code and the Copilot CLI currently differ slightly:

- **VS Code (mcp.json)** uses a top-level "servers" key.
- **Copilot CLI (mcp-config.json)** uses a top-level "mcpServers" key and enforces stricter naming conventions (no slashes in server names).

Keeping them separated in your sync repository prevents annoying parsing errors when you switch between the terminal and your IDE.
