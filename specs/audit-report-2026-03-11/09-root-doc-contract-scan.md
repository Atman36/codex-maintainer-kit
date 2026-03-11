# Spec 09: Scan root docs for contract drift and remove dead `{{CONTEXT}}`

Источник:
- [Audit Report.md](../../Audit%20Report.md)
- `AUDIT_SECOND_PASS_PROGRESS_2026-03-11.md`

## Why This Spec Exists

The contract validator currently scans prompts, PR Factory skills, `skills/README.md`, and `tools/README.md`, but it still does not scan root docs. As a result, dead placeholders in `README.md` or `AGENTS.md` can survive outside mechanical enforcement.

This is already visible on the current tree: `README.md` still contains dead `{{CONTEXT}}`, while `tools/contract_registry.py` does not include root docs in `DOC_FILES`.

## Goal

Expand static contract enforcement to root docs and remove the dead placeholder from `README.md`.

## Scope

Touch only:
- `tools/contract_registry.py`
- `README.md`
- `AGENTS.md` if needed
- `tools/tests/test_contracts.py`

## Smallest Safe Change

- Add root `README.md` and `AGENTS.md` to `DOC_FILES`.
- Replace `{{CONTEXT}}` in `README.md` with canonical wording or `{{CONTEXT_PATH}}`, depending on what the doc really means.
- Add a regression test showing that an unknown placeholder in a root doc is reported.

## Acceptance Criteria

- Root docs are part of the static contract scan.
- `README.md` no longer contains dead `{{CONTEXT}}`.
- Unknown placeholders in root docs fail deterministically.

## Verification

Run exactly:

```bash
python3 -m unittest tools.tests.test_contracts.ContractRegistryTests.test_root_docs_are_scanned_for_unknown_placeholders
python3 tools/validate_skills.py
```

## Reviewer Concerns To Preempt

- Whether root docs should influence validation: yes, because they guide both human and agent behavior.
- Whether `AGENTS.md` should be scanned even if it is repo-specific: yes, because it is part of the operating contract.

## Out Of Scope

- Prompt alias cleanup
- Runtime placeholder handling
- Broad doc portability sweep

## Suggested Commit Message

```text
fix(contracts): lint root docs and remove dead context placeholder
```
