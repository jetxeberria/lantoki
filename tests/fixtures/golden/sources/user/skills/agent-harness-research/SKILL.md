---
name: agent-harness-research
description: >-
  Research and explain the CURRENT, verified behavior of a specific agentic coding harness
  (Claude Code, Codex CLI, Cursor, Windsurf, Aider, Gemini CLI, GitHub Copilot, Cline, Zed,
  Amp, OpenCode, and others), focused on customization. Use WHENEVER the user asks how a coding
  agent / AI IDE / CLI agent / "harness" works or how to configure it — instruction/context
  files (CLAUDE.md, AGENTS.md, .cursor/rules, GEMINI.md, copilot-instructions), slash/custom
  commands, skills, subagents, MCP servers, hooks, tool permissions, memory, settings files,
  where files must live, which scope (system / user / workspace / directory / enterprise)
  applies, how layers override each other, what is deprecated, or how two harnesses differ even
  when they reuse the same word. Trigger even for a narrow "where does X go?" question, because
  the answer depends on the latest release and training data is almost certainly stale. Do NOT
  answer harness-customization questions from memory — this skill forces live verification.
---

# Agent Harness Research

## What this skill is for

An "agent harness" is the software wrapper that turns a model into an autonomous coding
agent: it owns the system prompt, the tool loop, context management, permissions, and the
configuration surfaces a user can customize. Examples: Claude Code, OpenAI Codex CLI, Cursor,
Windsurf, Aider, Gemini CLI, GitHub Copilot (Coding Agent / chat), Cline, Roo Code, Amp, Zed
agent, OpenCode, Continue, and new entrants that appear monthly.

This skill answers questions of the form *"how does harness X actually work right now, and how
do I customize it?"* — with special depth on the **customization surfaces** (the artifacts a
user can author), **where each artifact must live**, **which scope it applies at**, **how the
layers override one another**, and **what has become obsolete**.

## The one rule that matters most: do not trust your training data

Harness behavior, file names, directory conventions, and feature sets change on a scale of
weeks. Features you "remember" are frequently renamed, relocated, deprecated, or replaced. A
confident answer from memory is the primary failure mode for this skill and is usually wrong
in at least one detail that breaks the user's setup.

Therefore: **every factual claim about a harness's current behavior must be grounded in a
source you retrieved during this session**, and dated. If you cannot verify a claim, say so
explicitly rather than filling the gap from memory. Treat the current date in your context as
the "as of" date and search with it.

## Workflow

Follow these steps in order. Do not skip the research step even if you feel certain.

### 1. Pin down the harness and the question

Identify the exact harness and surface/version if the user gave one (e.g. "Claude Code on the
CLI" vs "Claude in the IDE extension" can differ; "Cursor rules" changed format across
versions). If the harness is ambiguous ("the OpenAI one", "the terminal agent"), ask a single
clarifying question. If the user names a harness you do not recognize, do not guess — search
for it; it may be new since your cutoff.

Note what they actually want: a full customization map, or a narrow point ("where do hooks
go?"). Answer the narrow thing first, then offer the fuller map.

### 2. Research the current truth (mandatory)

Read `references/research-methodology.md` for the full procedure. In short:

- Find the harness's **authoritative docs** (official documentation site, the vendor's repo,
  the vendor's changelog/release notes). `references/source-map.md` lists known starting
  points per harness — but treat those as leads to verify, not as facts, since URLs and
  structures move.
- Search with the current year/date and the harness name. Prefer official docs and the
  project's own changelog over blog posts and forum threads.
- Pull the **changelog / release notes** specifically to learn what is *new*, *changed*, or
  *deprecated*. This is where "obsolete vs current" gets decided.
- Note version numbers and dates on everything. Distinguish **stable / documented** features
  from **beta / experimental / undocumented** ones, and say which is which.
- When sources conflict, prefer the most recent official one and surface the conflict.

Scale the searches to the question: a narrow "where does file X live" may need 2–4 searches;
a full customization map for a fast-moving harness can warrant 8–15+ across docs, changelog,
and the config reference.

### 3. Map the harness onto the universal taxonomy

Read `references/customization-taxonomy.md`. It defines a harness-agnostic vocabulary for the
artifact types (instruction/context files, system-prompt overrides, slash/custom commands,
skills, subagents, MCP servers, hooks, tool/permission config, settings, output styles,
memory) and for the scope layers (system / user / workspace / directory / enterprise; local
vs shared; session/runtime). It also covers the two hard problems you must address explicitly:

- **Overlap** — when a harness offers several artifacts that can do a similar job (e.g. a
  slash command vs a skill vs a subagent vs an MCP prompt), say which to reach for and why.
- **Naming collisions** — the same word means different things across harnesses ("rules",
  "agents", "skills", "memory", "commands"), and different words mean the same thing
  (CLAUDE.md / AGENTS.md / GEMINI.md / .cursor/rules / copilot-instructions all play the
  auto-loaded-context role). Map the harness's local vocabulary onto the universal taxonomy so
  the user is not misled by a familiar-sounding term.

Map only what you verified in step 2. If the harness lacks a given surface, say so — absence
is useful information.

### 4. Always write the standard Markdown document

The deliverable is **always a Markdown file**, never just an inline answer. Write it to
`/mnt/user-data/outputs/harness-research-<slug>.md` where `<slug>` is the lowercased,
hyphenated harness name (e.g. `claude-code`, `codex-cli`, `cursor`). Then present the file and
keep the chat reply to a 2–4 sentence summary plus the most important caveat. Do not paste the
whole document into chat.

#### The output contract is fixed — this is what makes documents comparable

The user runs many of these researches and compares them. A comparator (human or another
agent) can only line up two documents if they share the **same sections in the same order, the
same table columns, the same row keys in the same order, and the same field names**. Treat the
template below as a rigid schema, not a suggestion:

- Use the section headings **verbatim**, in the order given.
- In the two locked tables (Customization surfaces, Scopes), include **every canonical row
  every time, in the canonical order**, even when the harness lacks that surface or scope —
  mark it `Not supported` rather than omitting the row. A missing row breaks alignment; an
  explicit "Not supported" is a comparable data point.
- Key every surface row on the **universal role name** (left column), not the vendor's term.
  The vendor's term goes in the "Local name" column. This is what lets row N of one document
  mean the same thing as row N of another.
- Keep the metadata block's keys identical across all documents.
- Don't add, rename, reorder, or split sections. If you have extra findings, put them under
  "Other customization points" or "Notes", never as new top-level sections.

#### Template (reproduce exactly)

````
---
harness: <Official name>
slug: <lowercase-hyphenated>
version_researched: <version or "unknown">
research_date: <YYYY-MM-DD>
surfaces: <CLI | IDE extension | web | desktop — list all that apply>
models: <model(s) it drives, or "configurable">
---

# <Harness> — Customization Map

## 1. Snapshot
One short paragraph: what the harness is, how its agent loop works at a high level right now,
which surfaces it runs on, and which model(s) it drives. State the version/date this reflects.

## 2. How it works right now
Current runtime behavior relevant to customization: how/when it loads context and instruction
files, how the tool loop and permission flow work, how context is managed or compacted. Flag
anything that changed recently.

## 3. Quick comparison table
At-a-glance fixed-key summary for fast diffing. Reproduce these rows verbatim, in this order:

| Key | Value |
|---|---|
| Instruction file name(s) | |
| Slash/custom command location | |
| Skills supported | Yes / No / Experimental |
| Subagents supported | Yes / No / Experimental |
| Hooks supported | Yes / No / Experimental |
| MCP supported | Yes / No / Experimental |
| AGENTS.md honored | Yes / No / Via shim / Unknown |
| Scopes available | <list from the canonical ladder> |
| Precedence rule (1 line) | |

## 4. Customization surfaces
Include all 11 canonical rows in this exact order. Mark unsupported surfaces `Not supported`.

| Universal role | Local name | Supported? | File / location | Format | Scope(s) | Maturity |
|---|---|---|---|---|---|---|
| Instruction / context files | | | | | | |
| System-prompt override | | | | | | |
| Slash / custom commands | | | | | | |
| Skills | | | | | | |
| Subagents | | | | | | |
| MCP servers | | | | | | |
| Hooks | | | | | | |
| Tool / permission / autonomy | | | | | | |
| Settings / config files | | | | | | |
| Output styles / modes | | | | | | |
| Memory | | | | | | |

## 5. Scopes & precedence
Include all 7 canonical scope rows in this exact order. Mark unsupported scopes `Not supported`.

| Scope | Supported? | Where (path / mechanism) | Notes |
|---|---|---|---|
| Enterprise / managed | | | |
| System / machine | | | |
| User / global | | | |
| Workspace / project | | | |
| Directory / nested | | | |
| Local / uncommitted | | | |
| Session / runtime | | | |

**Precedence:** state the exact resolution order and whether surfaces merge or override.
Note per-surface differences if precedence isn't uniform.

## 6. Which artifact for which job (overlap guidance)
Decision rules where surfaces overlap: command vs skill vs subagent vs MCP prompt vs
instruction file; deterministic enforcement (hooks) vs suggestion (instructions).

## 7. Naming caveats
Terms in this harness that collide with other harnesses, and the cross-harness equivalents, so
the reader isn't tripped up moving between tools.

## 8. Obsolete / no longer recommended
Use this table; one row per item.

| Item | Status | Changed in (version / date) | Replacement |
|---|---|---|---|

## 9. Other customization points
Model selection/routing, environment variables, sandboxing/autonomy, telemetry/privacy,
plugins/marketplaces, themes/status line, IDE-vs-CLI differences — whatever else is real.

## 10. Sources
Official docs/changelog pages used, each with the date. List any gaps you could not verify.
````

### 5. Be honest about gaps

If part of the document couldn't be verified, write `Unverified` (or `Not supported` where you
confirmed absence) in the relevant cell rather than leaving it blank or guessing from memory.
Never drop a locked row to hide a gap — an explicit `Unverified` keeps the document comparable.
A smaller well-grounded document beats a complete-looking one padded with stale memory.

## Comparing two or more harnesses

Because every single-harness document already follows the locked schema, two of them can be
compared directly row-by-row outside this skill — that is the intended workflow. If the user
instead asks for a comparison *in one document*, research each harness independently (step 2
per harness), then build one file `harness-research-compare-<slugs>.md` whose surface and scope
tables use the **same canonical rows** with one column per harness, so equivalent surfaces line
up. Anchor on the universal role, never on the vendor's chosen word — this is exactly where
naming collisions bite.

## Reference files

- `references/research-methodology.md` — how to find authoritative sources, date-check, read
  changelogs for deprecations, and judge documented vs experimental. Read before step 2.
- `references/customization-taxonomy.md` — the universal vocabulary for artifacts and scopes,
  plus overlap decision rules and the cross-harness naming map. Read before step 3.
- `references/source-map.md` — known documentation/changelog starting points per harness.
  Leads to verify, not facts; harnesses not listed are not exotic, just absent — search for
  them.
