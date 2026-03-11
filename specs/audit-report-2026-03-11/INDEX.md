# Audit Report Spec Index

Источник: [Audit Report.md](/Users/Apple/Developer/pr-factory-kit/Audit%20Report.md)

Назначение:
- Каждая спека ниже самодостаточна и рассчитана на отдельный чат.
- Для запуска достаточно сослаться на номер: `выполни спеку 01`.
- После завершения спеки AI должен обновить этот индекс: статус, дату, краткий итог, commit SHA.

## Status Board

| Spec | Title | Status | Done At | Commit | What Was Done |
| --- | --- | --- | --- | --- | --- |
| 01 | Fix `quality_gate.py` autoclean crash and add regression tests | done | 2026-03-11 | 304edf3 | Repaired autoclean subprocess calls and added tracked/untracked regression coverage. |
| 02 | Add placeholder registry and static contract validator | done | 2026-03-11 | same commit | Added canonical placeholder registry, contract validation, metadata path-type checks, and regression tests. |
| 03 | Add runner placeholder aliases and unresolved-placeholder preflight | done | 2026-03-11 | 3cdd06f | Added backward-compatible placeholder aliases, unresolved-template fail-fast checks, and regression coverage/docs. |
| 04 | Validate stage payloads against `ExecutionResult` and `PRSpec` schemas at runtime | done | 2026-03-11 | b715afd | Enforced runtime schema checks for stage payloads and embedded PRSpecs, added local `$ref` resolution, and covered invalid/legacy payload failures with tests. |
| 05 | Relax non-publish preflight for local-only analysis runs | done | 2026-03-11 | 27a20d2 | Allowed non-publish preflight to fall back to local base branch or HEAD with warnings, while keeping publish checks strict. |
| 06 | Add CI for tools and contract checks | done | 2026-03-11 | 27a20d2 | Added a minimal GitHub Actions workflow for tool unit tests plus `tools/validate_skills.py` contract validation. |
| 07 | Support quoted and space-containing `SAVED_JSON_PATH` values | done | 2026-03-11 | 27a20d2 | Fixed `SAVED_JSON_PATH` parsing for quoted and spaced paths and added regression coverage. |
| 08 | Require `gatekeeper.status=success` before PR fan-out | todo |  |  | Separate correctness fix for unsafe gate behavior. |
| 09 | Scan root docs for contract drift and remove dead `{{CONTEXT}}` | todo |  |  | Expand static contract lint to root docs and remove dead placeholder. |
| 10 | Preserve architect candidate in `top_improvements` | todo |  |  | Summary-layer regression fix for architecture mode. |
| 11 | Validate pipeline summary at runtime and write it to a stable artifact dir | todo |  |  | Stabilize summary artifact contract and default output location. |
| 12 | Canonicalize portability-breaking docs and stale examples | todo |  |  | Remove hardcoded local artifact paths and stale portability guidance. |
| 13 | Rebalance Critic approvals and reduce Gatekeeper overlap | todo |  |  | Prompt/policy tuning for low-risk approvals and cleaner role separation. |
| 14 | Replace hardcoded analysis artifact paths with `ARTIFACT_DIR` / `REPORT_PATH` | todo |  |  | Runtime portability follow-up for analysis-stage artifact paths. |
| 15 | Add `pyproject.toml` for editable-install packaging | todo |  |  | Packaging follow-up after `requirements.txt`. |
| 16 | Add `run_id` and artifact lineage to pipeline outputs | todo |  |  | Introduce first-class run identity and machine-readable lineage. |
| 17 | Move pipeline mode definitions out of `run_pipeline.py` | todo |  |  | Replace hardcoded mode graph with config-backed data. |

## Update Rule

Когда спека выполнена:
1. Меняй `Status` на `done` или `partial`.
2. Заполняй `Done At` в формате `YYYY-MM-DD`.
3. Записывай commit SHA в `Commit`.
4. Кратко фиксируй результат в `What Was Done`.
