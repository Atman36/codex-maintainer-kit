# PR Factory Kit: non-duplicated follow-up improvements

Date: 2026-03-11

Этот файл очищен от пунктов, уже перенесённых в [Audit Report.md](Audit%20Report.md) и отдельные спеки в [specs/audit-report-2026-03-11/INDEX.md](specs/audit-report-2026-03-11/INDEX.md).

Ниже оставлены только идеи, которые не дублируют аудит как отдельные задачи.

## 1. Configurable pipeline modes instead of hardcoded stage order

Why:
- `MODE_ANALYSIS_STAGE_ORDER` is still hardcoded in `tools/run_pipeline.py`.
- Supporting new mode combinations currently requires changing runner code instead of data.

Evidence:
- `tools/run_pipeline.py`

What to do:
- Move pipeline mode definitions into a config file such as `config/pipeline_modes.json`.
- Let the runner load stage order from config instead of embedding all modes in code.

## 2. Parallelize independent analysis stages where contracts allow it

Why:
- Some analysis work may be parallelizable once contracts are stabilized.
- The most plausible candidate is running Critic in parallel with another analysis stage if both consume the same upstream candidate set and do not depend on each other.

Constraints:
- Do not implement before contract/input normalization is complete.
- Parallelism must preserve determinism, lineage, and failure visibility.

What to do:
- Re-evaluate the stage graph after placeholder and schema work is finished.
- Add parallel execution only if artifacts and handoff contracts stay clear.
