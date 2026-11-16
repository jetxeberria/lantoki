# Research Methodology

How to establish the *current* truth about a harness and reliably separate it from what's
obsolete. The goal is that every claim in your answer traces to a source you fetched this
session, with a date attached.

## Why this is strict

Agent harnesses ship changes weekly. Across a single quarter, harnesses have renamed their
instruction file, moved config paths, replaced one customization system with another, changed
precedence rules, and deprecated whole features. Anything you "know" from training is a
hypothesis to confirm, not an answer. The most damaging errors are the confident, specific,
and wrong ones (a file path that moved, a flag that was renamed).

## Source hierarchy (prefer top to bottom)

1. **Official documentation site** for the harness — the canonical reference for file paths,
   formats, and scopes.
2. **The vendor's changelog / release notes** — the only reliable way to learn what is *new*,
   *changed*, or *deprecated*, and when. Always pull this; it's where obsolescence is decided.
3. **The vendor's source repository** (README, docs folder, schema files, example configs) —
   useful when docs lag the code, and for confirming exact file names and config keys.
4. **Official blog / release announcements** — good for feature launches and dates.
5. **High-quality community sources** (well-known practitioners, the project's discussions/
   issues) — use to *find* what to verify, then confirm against 1–3. Don't cite as ground
   truth on their own.

Avoid: undated tutorials, SEO listicles, and AI-generated summaries — they're the main vector
for stale or hallucinated paths. If the only source for a claim is one of these, label the
claim unverified.

## Procedure

1. **Resolve the harness and its docs.** Search `<harness> documentation <current year>` and
   `<harness> docs`. Confirm you've got the *current* official site (vendors migrate domains).
   `references/source-map.md` gives starting leads — verify they still resolve.

2. **Establish the current version and date.** Search the changelog/releases. Record the
   latest version and its date so your whole answer can be stamped "as of."

3. **Pull the changelog for deltas.** Read recent release notes specifically for: renamed or
   moved files, new customization surfaces, deprecations, removed features, changed defaults,
   changed precedence. This directly feeds the "Obsolete / no longer recommended" section.

4. **Get the configuration reference.** Find the page(s) that enumerate config file
   locations, instruction-file names, command/skill/subagent/hook/MCP setup, and scopes. These
   are the load-bearing facts; quote exact paths and file names from the docs, not memory.

5. **Verify per-surface using the taxonomy checklist** (section 7 of
   `customization-taxonomy.md`). For each artifact role, confirm: supported? name? path?
   format? scope(s)? stable or experimental? If docs are silent, say so — don't infer.

6. **Resolve conflicts and recency.** When two sources disagree, prefer the most recent
   official one and note the discrepancy. Fast-moving areas (skills, hooks, subagents, AGENTS.md
   adoption) deserve extra searches because they change fastest.

7. **Date-stamp everything.** Each major claim should be traceable to a dated source. The
   answer's header carries the overall "as of" date.

## Search hygiene

- Use the current year/date in queries; a stale year returns stale results.
- Keep queries short and specific; reformulate rather than repeating a query that missed.
- Fetch full pages for exact file paths and config keys — snippets routinely omit the detail
  that matters (the precise filename, the precise directory).
- When comparing harnesses, research each independently before tabulating, so one harness's
  vocabulary doesn't contaminate your read of another's.

## Judging documented vs experimental

State the maturity of each feature. Look for explicit "beta/experimental/preview" labels,
features that live only in release notes but not the main docs, and config keys that exist in
the repo but aren't documented. Tell the user which surfaces are safe to depend on and which
may change.

## Calibrating effort

- Narrow factual question ("where does the hooks config live?") → confirm against docs +
  changelog; a few searches.
- Full customization map for one harness → docs + changelog + config reference + per-surface
  checks; often 8–15 searches.
- Multi-harness comparison → repeat the per-harness research for each; can exceed 20. If it
  would balloon beyond ~30, tell the user and suggest narrowing or staging.

## When you can't verify

Say so plainly and scope the uncertainty ("the docs don't currently specify nesting behavior
for this file; verify in your version before relying on it"). Never paper over a gap with a
remembered detail. A smaller, fully-grounded answer is the success condition.
