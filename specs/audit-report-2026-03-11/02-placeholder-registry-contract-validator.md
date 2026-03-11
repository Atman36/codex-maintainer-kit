# Spec 02: Add placeholder registry and static contract validator

Источник:
- [Audit Report.md](../../Audit%20Report.md)
- Section: `Top issues -> 1`
- Section: `Improvement opportunities`
- Section: `Best 7 -> 2`
- Section: `Ready-to-Implement PR Specs -> PRSpec 2`

## Why This Spec Exists

The audit found real contract drift between prompts, skills, metadata, docs, and the runtime runner. Examples called out explicitly:
- `prompts/pr_writer.md` and `prompts/reviewer.md` expect `{{IMPLEMENT_RESULT_JSON}}`, but the runner injects `{{IMPLEMENT_JSON}}`.
- Gatekeeper prompts/skills expect `{{CANDIDATES_JSON}}`, while runtime uses `SCOUT_JSON`, `ANALYST_JSON`, or `ARCHITECT_JSON`.
- Some docs claim JSON-only outputs, while runtime and parser support `SAVED_JSON_PATH=...`.
- `skills/*/metadata.json` marks `*_JSON` inputs as `type: object`, although runtime actually passes file paths.

Right now these mismatches are discovered late, often only when an agent handoff already failed.

## Goal

Create a canonical placeholder registry and a static validator that checks prompts, skills, and metadata for contract mismatches before runtime.

## Scope

Touch only the contract-lint layer:
- new registry file or module, for example `tools/contract_registry.py` or `contracts/placeholders.json`
- validator logic in `tools/validate_skills.py` or a new `tools/validate_contracts.py`
- `tools/tests/test_contracts.py`
- `tools/README.md`

Do not change runner behavior in this spec. Runtime compatibility aliases belong to Spec 03.

## Problem Statement

The repository uses prose as the system of record more often than enforceable tooling. That creates silent drift across:
- `prompts/*.md`
- `skills/pr-factory-*/SKILL.md`
- `skills/pr-factory-*/metadata.json`
- top-level docs

The audit recommendation is to move these invariants out of prose and into machine-checkable validation.

## Smallest Safe Change

- Add one canonical registry of supported placeholders and explicit aliases.
- Make a validator scan prompts, skills, and metadata against that registry.
- Fail on unknown placeholders and explicitly flag metadata path-vs-object mismatches.
- Decide whether aliases should pass or warn, but make the behavior explicit and test-covered.

## Acceptance Criteria

- A single supported-placeholder registry exists in the repo.
- Static validation checks prompts, PR Factory skills, and metadata.
- Unknown placeholders fail deterministically.
- Metadata entries that claim `type: object` for path-like `*_JSON` inputs are flagged.
- Validation is documented and runnable locally.

## Tests To Add Or Update

- valid prompt placeholder set passes
- unknown placeholder fails
- `IMPLEMENT_RESULT_JSON` alias is either accepted or explicitly reported
- metadata path-vs-object mismatch is flagged

## Verification

Run exactly:

```bash
python3 tools/validate_skills.py
python3 -m unittest tools/tests/test_validate_skills.py tools/tests/test_contracts.py
```

## Reviewer Concerns To Preempt

- Scope: validate only skills or also docs/prompts.
- Policy: aliases should warn or fail.
- Treatment of legacy artifacts vs active contracts.

## Out Of Scope

- Runtime alias resolution
- Schema validation at stage execution time
- Path portability cleanup
- CI workflow wiring

## Suggested Commit Message

```text
feat(contracts): add placeholder registry and static contract validation
```
