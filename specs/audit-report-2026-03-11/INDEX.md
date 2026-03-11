# Audit Report Spec Index

Источник: [Audit Report.md](../../Audit%20Report.md)

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
| 08 | Require `gatekeeper.status=success` before PR fan-out | done | 2026-03-11 | 7c8097b | Gatekeeper now blocks PR fan-out unless both decision is `pr` and top-level status is `success`, with regression coverage. |
| 09 | Scan root docs for contract drift and remove dead `{{CONTEXT}}` | done | 2026-03-11 | 02ea3a1 | Added root-doc contract scanning, replaced the dead README placeholder, and covered root-doc failures with regression tests. |
| 10 | Preserve architect candidate in `top_improvements` | done | 2026-03-11 | fe11ebc | Summary collection now preserves single-object architect candidates and regression coverage keeps architecture-mode `top_improvements` populated. |
| 11 | Validate pipeline summary at runtime and write it to a stable artifact dir | done | 2026-03-11 | fe11ebc | Added runtime `PipelineSummary` validation and moved the default summary artifact path into stable repo-owned `analysis_report/` output. |
| 12 | Canonicalize portability-breaking docs and stale examples | done | 2026-03-11 | 02ea3a1 | Replaced hardcoded local analysis artifact paths in prompts/skills/docs with portable `{{ARTIFACT_DIR}}` guidance. |
| 13 | Rebalance Critic approvals and reduce Gatekeeper overlap | done | 2026-03-11 | 02ea3a1 | Added Critic fast-approve guidance for narrow low-risk work and refocused Gatekeeper on post-approval scope shaping. |
| 14 | Replace hardcoded analysis artifact paths with `ARTIFACT_DIR` / `REPORT_PATH` | done | 2026-03-11 | 02ea3a1 | Added `ARTIFACT_DIR` to the contract/runner, switched analysis-stage instructions to placeholder paths, and added runtime regression coverage. |
| 15 | Add `pyproject.toml` for editable-install packaging | done | 2026-03-11 | c2e186e | Added minimal setuptools-based editable-install metadata, kept `requirements.txt`, and documented local setup. |
| 16 | Add `run_id` and artifact lineage to pipeline outputs | done | 2026-03-11 | 065f268 | Added first-class `run_id`, stable per-run artifact persistence, pipeline summary lineage, and regression coverage for shared run identity. |
| 17 | Move pipeline mode definitions out of `run_pipeline.py` | done | 2026-03-11 | 065f268 | Moved mode analysis order into `config/pipeline_modes.json`, added early config validation, and covered missing/invalid config cases. |

## Update Rule

Когда спека выполнена:
1. Меняй `Status` на `done` или `partial`.
2. Заполняй `Done At` в формате `YYYY-MM-DD`.
3. Записывай commit SHA в `Commit`.
4. Кратко фиксируй результат в `What Was Done`.
