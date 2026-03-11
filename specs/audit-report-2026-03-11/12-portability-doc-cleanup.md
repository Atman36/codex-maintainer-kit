# Spec 12: Canonicalize portability-breaking docs and stale examples

Источник:
- [Audit Report.md](../../Audit%20Report.md)
- `AUDIT_SECOND_PASS_PROGRESS_2026-03-11.md`

## Why This Spec Exists

Hardcoded `<repo>/analysis_report/...` paths still exist across prompts, skills, and docs. These are portability-breaking instructions for a harness repo and can mislead agents into treating one local machine layout as part of the contract.

The current tree still contains those paths in multiple files.

## Goal

Remove local-machine-specific artifact paths from prompts/skills/docs and replace them with portable wording or placeholders.

## Scope

Touch only documentation and prompt text:
- `skills/README.md`
- `prompts/README.md`
- analysis-stage `SKILL.md` files
- analysis-stage prompt files
- related docs that still embed machine-specific `analysis_report/` paths

Avoid runner code changes in this spec.

## Smallest Safe Change

- Replace hardcoded local paths with portable wording such as:
  - `analysis_report/<stage>-<timestamp>.json`
  - `{{REPORT_PATH}}`
  - repo-relative artifact guidance
- Keep current runtime behavior description accurate.
- Re-scan for remaining occurrences after edits.

## Acceptance Criteria

- Prompt and skill docs no longer hardcode machine-specific `analysis_report/` paths.
- Artifact-path guidance is portable and consistent.
- No runtime behavior is changed in this slice.

## Verification

Run exactly:

```bash
rg -n "/Users/Apple/Developer/pr-factory-kit/analysis_report/" skills prompts README.md AGENTS.md tools FRAMEWORK_IMPROVEMENTS_2026-03-11.md
python3 tools/validate_skills.py
```

## Reviewer Concerns To Preempt

- Large file count: this is docs-only cleanup across the operating surface, not code churn.
- Placeholder choice: prefer wording that matches real runtime transport and artifact handling.

## Out Of Scope

- Stable artifact-dir runtime change
- Lineage manifest
- Prompt-policy recalibration

## Suggested Commit Message

```text
docs: remove hardcoded local analysis report paths
```
