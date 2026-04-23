---
name: tdd-architect
description: 'Design test-first architecture from structured behavior specifications, independent of source language and input origin. Use for public-interface test planning, scenario modeling, acceptance criteria design, and implementation-agnostic migration sequencing.'
argument-hint: 'Provide behavior-spec input path(s), target constraints, and desired planning depth.'
user-invocable: true
---

# TDD Architect

Build a tests-first strategy from structured behavior inputs, without relying on source code inspection.

## When to Use
- Creating a TDD plan from discovery outputs.
- Designing implementation-agnostic tests for public interfaces.
- Producing reusable test architecture that can target different languages/frameworks.
- Converting domain behavior into executable test scenarios.

## Boundaries and Composition
- This skill is input-contract driven, not source-code driven.
- This skill is agnostic to source language and to the producer of its inputs.
- This skill does not require inputs to come from any specific skill.
- This skill does not implement production code.
- This skill does not run quality gates.
- This skill can feed implementation skills and verification workflows.

## Required Inputs
- One or more structured behavior-spec artifacts.
- Optional target constraints:
  - test framework preferences
  - platform/runtime constraints
  - non-functional priorities (performance, security, reliability)

## Input Contract
Each behavior-spec artifact must provide enough information to derive testable outcomes. Minimum required sections:
- scope_summary
- domain_capabilities
- assumptions_and_unknowns
- confidence_by_capability

Optional but recommended sections:
- dependency_and_flow_map
- risks_and_constraints
- business_value_hypotheses

If sections are missing, stop and request the missing data before planning tests.

## Non-Goals
- Do not infer hidden behavior from raw code.
- Do not generate implementation details.
- Do not couple tests to private/internal implementation.
- Do not proceed when critical ambiguity remains unresolved.

## Procedure
1. Validate input contract.
   - Verify required sections exist.
   - Identify contradictory or incomplete behavior definitions.
   - If contract validation fails, return missing fields and stop.

2. Normalize behavior model.
   - Merge capabilities from all input artifacts.
   - Resolve duplicate capabilities by preserving most explicit acceptance signals.
   - Tag each capability with confidence and unresolved assumptions.

3. Define public interface test surface.
   - For each capability, define observable entry points and outcomes.
   - Keep interface definitions implementation-agnostic.
   - Explicitly reject private/internal-only test targets.

4. Design tests-first blueprint.
   - For each capability, define:
     - acceptance scenarios
     - negative scenarios
     - edge-case scenarios
     - failure-handling scenarios
   - Map each scenario to expected observable behavior.
   - Add traceability links from scenarios to capability IDs.

5. Build implementation sequencing plan.
   - Order work in thin vertical slices:
     - first failing acceptance test
     - minimal implementation goal
     - follow-up refactor objective
   - Sequence by risk and confidence:
     - high-risk or low-confidence capabilities first, with explicit discovery questions.

6. Produce reusable planning output.
   - Return a stable structure that downstream implementation skills can consume.
   - Include unresolved questions that must be answered before coding starts.

## Decision Logic
- If a capability lacks observable outcomes, do not draft tests for it; request clarification.
- If confidence is low for a critical capability, produce a clarification gate before test authoring for that capability.
- If target framework is unspecified, provide framework-neutral scenarios and an adaptation note.
- If non-functional requirements conflict with functional behavior, escalate conflict explicitly and ask the user to prioritize.

## Quality Checklist
- All planned tests map to public interfaces only.
- Each capability has scenario coverage across happy path, negative, and edge cases.
- Traceability from capability to scenario is explicit.
- Plan is independent of source language and input provenance.
- Missing/ambiguous requirements are surfaced before implementation.
- Output structure is stable and machine- or human-consumable.

## Output Contract
Return in this order:
1. input_validation_report
2. normalized_capability_model
3. public_interface_test_surface
4. test_scenarios_by_capability
5. test_traceability_matrix
6. tdd_execution_slices
7. open_questions_and_clarifications
8. readiness_gate_decision
