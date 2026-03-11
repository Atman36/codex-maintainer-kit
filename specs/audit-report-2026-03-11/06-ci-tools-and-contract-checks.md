# Spec 06: Add CI for tools and contract checks

Источник:
- [Audit Report.md](/Users/Apple/Developer/pr-factory-kit/Audit%20Report.md)
- Section: `Top issues -> 8`
- Section: `Best 7 -> 6`
- Section: `System Upgrade Plan -> Foundation PRs`

## Why This Spec Exists

The audit states that the repository has useful local tests, but no CI workflow under `.github/workflows/`. That means regressions in tooling, contracts, or test coverage remain invisible until somebody runs the checks manually.

This is especially risky here because the repo is a harness/contract repo, not an app. Reliability depends on machine-enforced checks, not only on documentation.

## Goal

Add a minimal GitHub Actions workflow that runs the relevant unit tests and contract validation on each push/PR.

## Scope

Touch only:
- `.github/workflows/test.yml` (new)
- small doc updates only if needed

Keep the workflow minimal. Do not expand into release automation, matrix builds, or publish automation.

## Problem Statement

The repo currently lacks automated enforcement for:
- `tools/tests/test_run_pipeline.py`
- `tools/tests/test_validate_skills.py`
- placeholder/contract validation

Without CI, drift becomes a surprise instead of a visible red build.

## Smallest Safe Change

- Add a GitHub Actions workflow for Python-based tool checks.
- Run the existing unittest suites and the skill/contract validator.
- Keep dependencies minimal and aligned with current repo tooling.

## Acceptance Criteria

- A workflow exists under `.github/workflows/`.
- It runs the core unittest suites.
- It runs `python3 tools/validate_skills.py`.
- The workflow is understandable and cheap enough to keep enabled by default.

## Tests To Add Or Update

No new product tests required. The workflow should execute existing checks.

## Verification

Run locally before finalizing:

```bash
python3 -m unittest tools/tests/test_run_pipeline.py tools/tests/test_validate_skills.py
python3 tools/validate_skills.py
```

If Spec 02 lands first and adds `tools/tests/test_contracts.py`, include it in the workflow as well.

## Reviewer Concerns To Preempt

- Keep the workflow fast and deterministic.
- Avoid over-coupling CI to optional local tools.
- If contract validation becomes separate from `validate_skills.py`, wire both explicitly.

## Out Of Scope

- Release workflows
- Publish automation
- Multi-version Python matrix unless clearly needed
- Coverage upload or badges

## Suggested Commit Message

```text
ci: add GitHub Actions for tool tests and contract validation
```
