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
| 03 | Add runner placeholder aliases and unresolved-placeholder preflight | todo |  |  |  |
| 04 | Validate stage payloads against `ExecutionResult` and `PRSpec` schemas at runtime | todo |  |  |  |
| 05 | Relax non-publish preflight for local-only analysis runs | todo |  |  |  |
| 06 | Add CI for tools and contract checks | todo |  |  |  |
| 07 | Support quoted and space-containing `SAVED_JSON_PATH` values | todo |  |  |  |

## Update Rule

Когда спека выполнена:
1. Меняй `Status` на `done` или `partial`.
2. Заполняй `Done At` в формате `YYYY-MM-DD`.
3. Записывай commit SHA в `Commit`.
4. Кратко фиксируй результат в `What Was Done`.
