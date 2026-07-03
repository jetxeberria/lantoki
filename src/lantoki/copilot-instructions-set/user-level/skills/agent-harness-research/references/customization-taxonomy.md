# Universal Customization Taxonomy

A harness-agnostic vocabulary for reasoning about *any* coding agent's customization surfaces.
Use it to (a) map a specific harness's features onto common categories, (b) reason about how
surfaces overlap, and (c) avoid being fooled by vocabulary that collides across harnesses.

This file is a thinking framework, not a fact sheet. The *categories* are stable; whether a
given harness implements a category, and under what name and file path, must be verified live.

## Contents
1. Artifact types (the customization surfaces)
2. Scope / application domains
3. Precedence and merging
4. Overlap: which artifact for which job
5. Naming collisions across harnesses
6. Cross-harness equivalence map
7. Checklist of customization points to cover

---

## 1. Artifact types

Think of these as *roles*. A harness may implement several, one, or none of each, under its
own names. When researching, ask for each role: does this harness have it? what is it called?
where does the file live? what format? what scope? stable or experimental?

**Canonical order.** The eleven roles below (A–K) are the fixed row order for the
"Customization surfaces" table in the output contract. Always emit all eleven, in this order,
marking absent ones `Not supported` — that is what keeps documents comparable row-by-row.

**A. Instruction / context files.** Persistent natural-language guidance auto-loaded into the
agent's context (project conventions, style, do/don't). The most universal surface. Usually
layered by scope and often merged. Examples of the *role*: CLAUDE.md, AGENTS.md, GEMINI.md,
`.cursor/rules/*.mdc`, `.github/copilot-instructions.md`, Aider conventions files, Windsurf
rules. Key questions: which filenames are honored, do they nest per-directory, are they merged
or does the nearest win, is there an import/include mechanism, is there a size budget.

**B. System-prompt / persona override.** Replacing or augmenting the base system prompt
wholesale. Rarer and riskier; some harnesses expose it (fully or as an append), many do not.
Distinct from instruction files because it can change the agent's core behavior, not just add
project context.

**C. Slash / custom commands (reusable prompts).** Named, often parameterized prompts the user
invokes on demand (e.g. `/review`, `/test`). Stored as files the harness discovers. The role
is "a saved prompt I trigger explicitly." Watch for argument/placeholder syntax and whether
commands can run shell or call tools.

**D. Skills.** Packaged, progressively-disclosed capabilities — a metadata blob that's always
visible plus a body and bundled resources loaded on demand, often model-invoked rather than
user-invoked. Newer concept; "skill" is heavily overloaded across the industry, so verify what
a given harness means by it. Key questions: model-invoked vs user-invoked, can it bundle
scripts/assets, how is it discovered, what scopes.

**E. Subagents / agents.** Delegated specialized agents with their own prompt, tool set, and
often their own context window, spawned by the main agent. The role is "hand a sub-task to a
focused worker." Watch the collision: "agent" sometimes means the whole harness, sometimes a
configurable sub-worker.

**F. MCP servers (external tools/data/prompts).** Model Context Protocol servers that supply
tools, resources, and sometimes prompts from outside the harness. Configured in a settings
file or registry; scoped (user vs project vs local). Questions: transport (stdio/SSE/HTTP),
where registered, per-scope config, whether MCP-provided *prompts* surface as commands.

**G. Hooks.** Event-driven callbacks (shell commands or programs) fired at lifecycle points —
before/after a tool call, on session start/stop, on user prompt submit, on file edit, etc.
The role is **deterministic enforcement and automation** that doesn't rely on the model
choosing to comply. Questions: which events exist, can a hook block/modify an action, what
data it receives, what scope.

**H. Tool / permission / autonomy configuration.** Allow/deny lists for tools, approval modes,
sandboxing, network and filesystem boundaries, "auto-run" vs "ask first." Often the highest-
stakes surface for safety. Questions: granularity, per-scope, can it be set per-command/per-
session.

**I. Settings / config files.** The harness's own configuration: model selection, env, MCP
registration, feature toggles, theme. Often JSON/TOML/YAML with a clear scope hierarchy
(global vs project vs local-uncommitted). Frequently the file that *contains* several of the
above as sub-sections.

**J. Output styles / modes / personas.** Toggleable presentation or behavior modes (concise,
explanatory, "plan mode," "ask vs agent mode"). Questions: built-in vs user-defined, scope.

**K. Memory.** Persistent learned facts the agent writes/reads across sessions. Overlaps
heavily with instruction files; the distinction is *who authors it* (agent-written and updated
vs human-authored convention) and *whether it's auto-managed*.

---

## 2. Scope / application domains

The same artifact type usually exists at multiple scopes. Always determine which scopes a
harness supports and which file path corresponds to each. The seven layers below are the fixed
row order for the "Scopes & precedence" table in the output contract — always emit all seven,
broadest to narrowest, marking absent ones `Not supported`:

- **Enterprise / managed / org policy** — administrator-imposed config that users can't
  override (MDM, managed settings). Increasingly common; easy to forget.
- **System / machine-wide** — applies to all users on the host.
- **User / global** — per-user, in the home directory; applies across all the user's projects.
- **Workspace / project** — at the repository or workspace root; shared with the team via
  version control. The most common place customization actually lives.
- **Directory / nested / subtree** — per-subdirectory overrides inside a project (matters a
  lot in monorepos). Determine whether nesting merges or whether nearest-wins.
- **Local / uncommitted** — a parallel file (often `*.local.*` or gitignored) for personal
  overrides not shared with the team. The committed-vs-personal split is a frequent source of
  confusion.
- **Session / runtime** — CLI flags, environment variables, in-session toggles that apply only
  to the current run and usually trump files.

Map every artifact type from section 1 against this list: e.g. "instruction files exist at
user, project, and nested-directory scope; MCP config at user and project; hooks at user and
project; permissions at enterprise, user, project, and local."

---

## 3. Precedence and merging

When the same setting is defined at multiple scopes, the harness resolves it some way. Always
state the rule explicitly — getting this wrong silently breaks setups. Common patterns:

- **Override (nearest/narrowest wins)** — project beats user beats system; runtime flag beats
  all files.
- **Merge / concatenate** — instruction files from multiple scopes are all loaded and combined
  (sometimes with a documented order; sometimes deduped).
- **Additive with enterprise lock** — managed policy can forbid narrower scopes from changing
  certain keys.
- **First-match / last-match** — for list-like configs (allow/deny rules), order can decide.

Don't assume a harness uses the same precedence rule for every artifact type — instruction
files might merge while permissions override. Verify per surface, and verify the *direction*
(does local beat global, or the reverse?). Note that "local" sometimes means
machine-uncommitted and sometimes means narrowest-directory — disambiguate.

---

## 4. Overlap: which artifact for which job

Harnesses increasingly offer several surfaces that can accomplish overlapping goals. The user
needs a decision rule, not just a list. General heuristics (state the harness-specific reality
after verifying):

- **Always-on project context** → instruction/context file. Cheap, persistent, but the model
  *may* ignore it; it's guidance, not a guarantee.
- **A prompt I run on demand** → slash/custom command. Explicit, user-triggered, good for
  repeatable workflows ("run my PR review checklist").
- **A capability the agent should reach for on its own** → skill. Model-invoked, progressively
  disclosed; good when the agent should *decide* to use it.
- **A focused sub-task with its own context budget** → subagent. Good for isolating a noisy or
  long sub-job so it doesn't pollute the main context.
- **External tools or data** → MCP server. The bridge to systems outside the harness.
- **A guarantee that something happens regardless of the model** → hook. Deterministic;
  enforcement, formatting, blocking, logging. Use when "the model should remember to…" is not
  good enough.
- **MCP prompt vs slash command** — both surface as invokable prompts; MCP prompts come from an
  external server (portable across harnesses that support MCP), commands are local files. If
  the user already runs the MCP server, its prompts may duplicate a local command.

The recurring trap: instruction files *suggest*, hooks *enforce*. If correctness depends on it
happening every time, an instruction line is the wrong tool.

---

## 5. Naming collisions across harnesses

Same word, different meaning — verify per harness:

- **"Rules"** — in some harnesses a structured, file-based instruction system with
  glob-scoped activation; in others just a flat instruction file; in others not used at all.
- **"Agents"** — sometimes the whole product, sometimes configurable sub-workers, sometimes the
  name of the cross-harness instruction file (AGENTS.md). Three unrelated meanings.
- **"Skills"** — packaged progressive-disclosure capabilities in one ecosystem; elsewhere may
  mean plugins, or nothing.
- **"Memory"** — agent-authored persistent notes in one harness; a synonym for the instruction
  file in another; an MCP server in a third.
- **"Commands"** — user-invoked prompts in one, shell aliases in another, built-in app actions
  in a third.
- **"Plan mode" / "ask mode" / "agent mode"** — autonomy/output modes whose exact semantics
  differ; don't assume parity.

Different word, same role (the auto-loaded context file): CLAUDE.md, AGENTS.md, GEMINI.md,
`.cursor/rules`, `.windsurfrules`, `.github/copilot-instructions.md`, Aider conventions. Note
the emerging **AGENTS.md** convention that multiple harnesses have moved to honor — verify
*which* harnesses read it today and whether they read it natively or via a shim, because
adoption is in flux.

---

## 6. Cross-harness equivalence map (verify before relying)

Use this only as a hypothesis to confirm against current docs — entries go stale.

| Universal role | Typically appears as (verify currency) |
|---|---|
| Instruction/context file | CLAUDE.md / AGENTS.md / GEMINI.md / `.cursor/rules/*.mdc` / `.github/copilot-instructions.md` / Aider conventions / `.windsurfrules` |
| Slash/custom command | per-harness command files (e.g. a `commands/` dir); MCP-provided prompts |
| Skill | SKILL.md-style packaged skills where supported |
| Subagent | configurable sub-agent definitions where supported |
| MCP server | `mcp`/`mcpServers` config block in the settings file or a dedicated registry |
| Hook | lifecycle hook config in settings (events vary widely by harness) |
| Permissions/autonomy | allow/deny + approval-mode settings; sandbox flags |
| Settings file | JSON/TOML/YAML at global + project + local scopes |
| Memory | agent-managed memory store or a designated memory file |

---

## 7. Checklist of customization points to cover

When producing the answer, make sure you've considered each of these for the harness (mark
"n/a" where it genuinely doesn't apply rather than omitting silently):

- [ ] Instruction/context files: names, locations, nesting, merge behavior, imports, size limits
- [ ] System-prompt override / append (if any)
- [ ] Slash/custom commands: location, argument syntax, can they run tools/shell
- [ ] Skills: supported? model- vs user-invoked, discovery, bundling, scope
- [ ] Subagents: supported? definition format, tool/context isolation, scope
- [ ] MCP: config location(s), transports, per-scope, prompts surfaced
- [ ] Hooks: event list, blocking ability, payload, scope
- [ ] Tool/permission/autonomy: granularity, approval modes, sandbox, per-scope
- [ ] Settings/config: format, scope hierarchy, key features
- [ ] Output styles/modes
- [ ] Memory: who authors, auto-managed?, scope, overlap with instructions
- [ ] Scopes available + precedence/merge rule per surface
- [ ] Local vs shared (committed vs personal) split
- [ ] Model selection / routing
- [ ] Environment variables
- [ ] Plugins / marketplaces / extensions
- [ ] Telemetry / privacy / data controls
- [ ] IDE vs CLI vs web behavior differences
- [ ] Deprecated / renamed / removed features and their replacements
