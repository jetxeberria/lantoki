---
name: domain-logic-extractor
description: 'Extract domain behavior from automation/code targets regardless of source language or downstream purpose. Use for capability inventory, dependency mapping, business value identification, ambiguity tracking, and structured knowledge handoff.'
argument-hint: 'Provide target path(s), known domain context, and desired depth of analysis.'
user-invocable: true
---

# Domain Logic Extractor

Extract a reliable, implementation-agnostic understanding of system behavior and domain value from any target source.

## When to Use
- Understanding unknown automation or codebases.
- Recovering business/domain behavior from technical artifacts.
- Producing reusable analysis for design, migration, testing, documentation, or audit workflows.
- Creating a structured handoff that other skills, agents, or humans can interpret consistently.

## Boundaries and Composition
- This skill is language-agnostic and purpose-agnostic.
- This skill focuses on domain behavior, dependencies, and business value extraction.
- This skill does not own implementation, translation, test authoring, or quality gate execution.
- This skill can feed language-specific parser/translator skills, implementation skills, testing skills, or governance workflows.

## Required Inputs
- Target path(s): files and/or directories.
- Optional domain context (team, owner, SLAs, environment, business process).
- Optional analysis constraints (depth, scope boundaries, security sensitivity).

## Non-Goals
- Do not write tests.
- Do not implement or refactor production code.
- Do not assume a downstream purpose unless explicitly provided.

## Procedure
1. Scope and guardrails.
   - Confirm exact target path(s) to analyze.
   - Confirm this phase is discovery-only.
   - If path is missing or inaccessible, stop and report blocker.

2. Collect evidence from all relevant artifacts.
   - Read target files recursively when directories are provided.
   - Include context artifacts that influence behavior:
     - runtime/config files (env, ini, yaml, json, toml, conf)
     - orchestration/scheduling files (CI, cron, workflow, task runners)
     - operational docs or runbooks tied to execution
   - Build an artifact catalog with purpose hypothesis per item.

3. Build dependency and interaction map.
   - For each relevant artifact, extract:
     - internal calls/invocations and control flow
     - external command dependencies
     - environment variables read/written
     - files/directories read/written/deleted
     - network/API interactions
     - privileged/system operations
   - Build a dependency graph and identify orchestration/ordering behavior.
   - Keep extraction semantic: represent capabilities and dependencies independently of syntax details.

4. Infer business behavior.
   - Translate technical flow into business capabilities.
   - For each capability, identify:
     - trigger (manual, scheduled, event-driven)
     - required inputs
     - outputs/artifacts
     - expected success criteria
     - failure modes and fallback behavior
   - Distinguish business rules from infrastructure glue.

5. Assess risks and confidence.
   - Flag ambiguity, hidden coupling, side effects, and unsafe assumptions.
   - Rate confidence per capability: high, medium, or low.
   - If confidence is low or reasoning is doubtful, discuss uncertainty with the user, including evidence and alternative interpretations.

6. Produce structured output for reuse.
   - Return discovery findings only, without prescribing implementation.
   - Use this output structure:
     - scope_summary
     - artifact_inventory
     - dependency_and_flow_map
     - domain_capabilities
     - business_value_hypotheses
     - assumptions_and_unknowns
     - risks_and_constraints
     - confidence_by_capability
     - user_questions_for_uncertainty
   - Keep the structure stable so other agents/skills can consume it.

## Decision Logic
- If multiple plausible business purposes exist, present ranked alternatives with confidence and evidence.
- If behavior depends on environment not present in source (secrets manager, CI variables, external config), explicitly mark as unresolved dependency.
- If automation behavior is mostly command wrapping, still identify business intent behind the wrapped commands.
- If any feature understanding is doubtful, surface the reasoning and discuss it with the user before finalizing conclusions.

## Quality Checklist
- Every relevant artifact in scope was read.
- Dependency relationships are explicit and traceable.
- Business capabilities are separated from technical mechanics.
- Findings are not coupled to a specific source language or a specific downstream purpose.
- Assumptions are visible and testable.
- Output is understandable by non-authors of the legacy scripts.
- Output follows the defined reusable structure exactly.

## Output Contract
Return in this order:
1. scope_summary
2. artifact_inventory
3. dependency_and_flow_map
4. domain_capabilities
5. business_value_hypotheses
6. assumptions_and_unknowns
7. risks_and_constraints
8. confidence_by_capability
9. user_questions_for_uncertainty
