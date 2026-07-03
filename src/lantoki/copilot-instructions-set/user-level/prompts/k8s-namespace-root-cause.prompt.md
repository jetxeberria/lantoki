---
name: "K8s Namespace Root Cause"
description: "Investigate Kubernetes namespace health, iterate to true root causes, and return evidence-backed findings"
argument-hint: "Namespace name and optional focus (e.g., airflow-3, focus on scheduler)"
agent: "agent"
tools: [kubernetes/*]
---
Investigate the target Kubernetes namespace and identify the true root causes of failures.

Inputs:
- Namespace: ${input}
- Optional focus: workload, pod, job, or service name if provided in the input

Method:
1. Start with a health snapshot: pods, deployments/statefulsets/jobs, services/endpoints, and recent warning events.
2. Identify blockers and failure chains (for example: init crash -> migration job failure -> dependency unavailable).
3. Iterate deeper until you can explain *why* each blocker exists, not only *what* is failing.
4. Prioritize Kubernetes MCP tools for evidence collection. If MCP cannot retrieve a needed detail, state that and use kubectl as fallback.
5. Verify assumptions with direct checks (for example: service endpoints, secret/config references, dependency connectivity).
6. Distinguish primary causes from secondary symptoms.

Output format:
- Executive summary (3-6 lines)
- Findings (ordered by severity)
  - Severity
  - Resource(s)
  - Evidence
  - Why this is root cause vs symptom
  - Confidence (High/Medium/Low)
- Dependency map
- Immediate remediation plan (numbered, include concrete commands when safe)
- Validation steps after fix (numbered, include concrete commands/checks)
- Open questions / unknowns

Rules:
- Do not expose credentials or secret values.
- Be explicit about confidence level for each finding.
- Avoid stopping at CrashLoopBackOff or BackOff labels; keep drilling down to the underlying dependency/configuration issue.
