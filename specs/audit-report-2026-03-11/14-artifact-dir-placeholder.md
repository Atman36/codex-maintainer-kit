# Spec 14: Replace hardcoded analysis artifact paths with `ARTIFACT_DIR` / `REPORT_PATH`

Источник:
- `deepresearch/external-audits/audit-2026-03-11-second-pass.md`
- `AUDIT_SECOND_PASS_PROGRESS_2026-03-11.md`

## Why This Spec Exists

The remaining portability problem is not only docs wording. Analysis-stage prompts and skills still instruct agents to write JSON into a machine-specific path:

`<repo>/analysis_report/...`

That path is not portable, and it is still embedded in the operating contract. The second-pass audit explicitly recommends replacing it with `REPORT_PATH` or `ARTIFACT_DIR` and letting the runtime inject the actual location.

## Goal

Introduce a portable artifact-path placeholder contract for analysis stages and thread it through runtime/template expansion.

## Scope

Touch only:
- `tools/contract_registry.py`
- `tools/run_pipeline.py`
- analysis-stage prompts
- analysis-stage `SKILL.md` files
- minimal tests that cover placeholder injection

## Smallest Safe Change

- Add canonical placeholder support for `ARTIFACT_DIR` if `REPORT_PATH` is too narrow.
- Inject the chosen artifact path from the runner with a stable default such as repo-relative `analysis_report/`.
- Replace hardcoded `<repo>/analysis_report/...` strings in analysis prompts/skills with the placeholder-driven form.
- Keep backward-compatible behavior for existing local runs.

## Acceptance Criteria

- No analysis-stage prompt or skill hardcodes machine-specific `analysis_report/` paths.
- Runner can expand the portable artifact placeholder during stage command construction.
- Default artifact directory remains deterministic and local-run friendly.

## Verification

Run exactly:

```bash
rg -n "/Users/Apple/Developer/pr-factory-kit/analysis_report/" skills prompts README.md AGENTS.md tools FRAMEWORK_IMPROVEMENTS_2026-03-11.md
python3 tools/validate_skills.py
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

## Reviewer Concerns To Preempt

- Placeholder naming: use one canonical artifact-path placeholder instead of multiple overlapping variants.
- Backward compatibility: existing users should still get a sensible default artifact directory without extra flags.

## Out Of Scope

- Artifact lineage manifest
- GC / cleanup policy for old artifacts
- Summary schema redesign

## Suggested Commit Message

```text
fix(artifacts): replace hardcoded analysis paths with placeholder contract
```
