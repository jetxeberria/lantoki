---
name: bash-to-python-translator
description: 'Translate Bash/Shell automation into Python implementations using structured discovery and TDD planning inputs. Use for behavior-preserving migration, Pythonic redesign, subprocess minimization, SOLID refactoring, and test-aligned implementation deltas.'
argument-hint: 'Provide raw legacy artifact paths, structured discovery outputs, structured TDD outputs, and implementation constraints.'
user-invocable: true
---

# Bash to Python Translator

Implement Python code from Bash/Shell behavior contracts while preserving validated business behavior and satisfying tests-first planning constraints.

## When to Use
- Implementing Phase 3 of a Bash-to-Python migration workflow.
- Converting shell automation to Python with behavior parity.
- Translating operational scripts into maintainable Python modules and public interfaces.
- Producing implementation deltas aligned to pre-defined test scenarios.

## Boundaries and Composition
- This skill is implementation-focused.
- This skill requires structured upstream artifacts and raw legacy artifacts.
- This skill does not perform domain discovery as a primary responsibility.
- This skill does not design TDD architecture as a primary responsibility.
- This skill does not execute linting, typing, security, or test gates.

## Required Inputs
Inputs are mandatory from three classes:
1. Raw legacy artifacts
   - Bash/Shell scripts and related runtime/config files required for behavioral fidelity.
2. Structured discovery outputs
   - Capability, dependency, risk, and uncertainty model from a discovery process.
3. Structured TDD planning outputs
   - Public-interface test surface, scenarios, and execution slice plan.

Optional inputs:
- Target Python version and packaging constraints.
- Environment and platform constraints.
- Security and reliability constraints.

## Input Contract
Minimum required sections from structured inputs:
- From discovery artifacts:
  - domain_capabilities
  - assumptions_and_unknowns
  - risks_and_constraints
  - confidence_by_capability
- From TDD planning artifacts:
  - public_interface_test_surface
  - test_scenarios_by_capability
  - tdd_execution_slices
  - readiness_gate_decision

If any required section is missing or contradictory, stop and request clarification before implementing code.

## Non-Goals
- Do not redesign behavior that has already been validated unless explicitly requested.
- Do not couple implementation to private test internals.
- Do not default to subprocess when a suitable Python library exists.
- Do not bypass unresolved critical ambiguities.

## Procedure
1. Validate implementation readiness.
   - Verify all required structured sections are present.
   - Verify readiness_gate_decision allows implementation.
   - If blocked, return explicit missing or conflicting inputs and stop.

2. Build capability-to-code plan.
   - Map each capability to target Python public interfaces.
   - Map each scenario to the implementation slice that should satisfy it.
   - Prioritize slices by risk and confidence, while preserving TDD order.

3. Translate behavior, not syntax.
   - Preserve observable behavior and side effects defined by contracts.
   - Replace shell idioms with Pythonic constructs and standard libraries where feasible.
   - Isolate infrastructure concerns behind small, explicit abstractions.

4. Minimize subprocess usage.
   - Prefer established Python libraries for filesystem, process metadata, HTTP, archive, parsing, and templating tasks.
   - Use subprocess only when no robust library alternative exists or when native command behavior is mandatory.
   - When subprocess is necessary, encapsulate it, validate inputs, and handle errors explicitly.

5. Implement in thin vertical slices.
   - Implement only what is needed for the next failing scenario set.
   - Keep interfaces stable and explicit.
   - Apply SOLID principles and clean code standards throughout.

6. Emit implementation report.
   - Provide implementation deltas tied to scenarios/capabilities.
   - Report assumptions carried forward and unresolved uncertainties.

## Decision Logic
- If behavior in raw scripts conflicts with structured inputs, structured inputs are authoritative unless user overrides.
- If structured inputs contain low-confidence critical capabilities, ask for user clarification before coding those slices.
- If a library replacement changes externally observable behavior, preserve behavior first and document trade-offs.
- If platform-specific shell behavior cannot be replicated safely, escalate constraints and propose bounded alternatives.

## Quality Checklist
- Every code change maps to one or more planned scenarios.
- Public interfaces satisfy contract-defined behavior.
- Subprocess usage is justified, minimal, and isolated.
- Error handling is explicit and typed where practical.
- Implementation remains maintainable, testable, and SOLID-aligned.
- Output clearly links deltas to capabilities and tests.

## Output Contract
Return in this order:
1. input_validation_report
2. capability_to_slice_mapping
3. implementation_deltas_by_capability
4. subprocess_usage_decisions
5. unresolved_assumptions_and_risks
6. handoff_to_verification