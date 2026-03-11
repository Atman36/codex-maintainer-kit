# Spec 03: Add runner placeholder aliases and unresolved-placeholder preflight

Источник:
- [Audit Report.md](/Users/Apple/Developer/pr-factory-kit/Audit%20Report.md)
- Section: `Top issues -> 1`
- Section: `Best 7 -> 3`
- Section: `Ready-to-Implement PR Specs -> PRSpec 3`

## Why This Spec Exists

The audit found a mismatch between placeholders promised by prompts/skills and placeholders actually injected by `tools/run_pipeline.py`. It also found that unresolved `{{...}}` placeholders can survive template expansion and only fail later, indirectly, inside a stage.

Examples explicitly called out:
- `CANDIDATES_JSON` is expected by Gatekeeper artifacts, but the runner works with `SCOUT_JSON`, `ANALYST_JSON`, and `ARCHITECT_JSON`.
- `IMPLEMENT_RESULT_JSON` is expected by some prompts, but runtime exports `IMPLEMENT_JSON`.

## Goal

Make the runner backward-compatible with the known placeholder aliases and fail fast when any unresolved placeholder remains after template expansion.

## Scope

Touch only:
- `tools/run_pipeline.py`
- `tools/tests/test_run_pipeline.py`
- `tools/README.md`

Do not add schema validation in this spec. That belongs to Spec 04.

## Problem Statement

Today the pipeline can silently hand a malformed command template to a stage. That creates noisy, hard-to-debug failures that look like agent mistakes but are actually runner contract bugs.

## Smallest Safe Change

- Add alias support in `run_pipeline.py`:
  - `CANDIDATES_JSON` resolves to the latest candidate-producing stage in order of preference: `ANALYST_JSON`, `ARCHITECT_JSON`, `SCOUT_JSON`
  - `IMPLEMENT_RESULT_JSON` resolves to `IMPLEMENT_JSON`
- After template expansion, scan for leftover `{{...}}`.
- If anything remains unresolved, fail deterministically before stage execution with a readable error.

## Acceptance Criteria

- Stages using `{{IMPLEMENT_RESULT_JSON}}` run successfully.
- Stages using `{{CANDIDATES_JSON}}` run successfully in quick-win, full, and architecture-relevant paths.
- Unknown placeholders fail before command execution.
- Existing non-aliased placeholders continue to work unchanged.

## Tests To Add Or Update

- stage command with `{{IMPLEMENT_RESULT_JSON}}` resolves
- stage command with `{{CANDIDATES_JSON}}` resolves
- unknown placeholder causes deterministic failure before stage execution

## Verification

Run exactly:

```bash
python3 -m unittest tools/tests/test_run_pipeline.py
```

Manual smoke check is acceptable if it proves alias resolution on a quick-win or full run.

## Reviewer Concerns To Preempt

- Alias precedence for `CANDIDATES_JSON`
- Whether analyst output should win over scout output
- Whether more aliases should be introduced now or later

## Out Of Scope

- Placeholder registry and static validation
- Runtime schema validation
- CI workflow
- Artifact path portability

## Suggested Commit Message

```text
fix(pipeline): add placeholder aliases and fail fast on unresolved templates
```
