# User Prompt Template: PR Factory (analysis-only, no code changes)

Проанализируй репозиторий `{{REPO_ROOT}}` (URL: `{{REPO_URL}}`) с помощью PR Factory, но **без реализации изменений** и без публикации.

Контекст:
- Используй контекст из `{{CONTEXT_PATH}}` (например: `deepresearch/`).
- Используй контекст выборочно: только факты, влияющие на риск, scope, стиль и требования к PR.

Режим:
- `MODE`: `full` (но остановиться до Implementer/Publisher)
- `BASE_BRANCH`: `main`
- `MAX_PRS`: `1`

Что сделать:
1) Scout → Analyst → Critic → Gatekeeper.
2) Сформировать 3–7 наиболее вероятных к merge улучшений и выбрать 1 лучший кандидат.
3) Сформировать PRSpec (как план), но **не вносить изменения в код** и **не создавать ветки/коммиты**.

Отчёт:
- Сгенерируй короткий отчёт в отдельном файле `{{REPORT_PATH}}` (Markdown), структура:
  - Repo snapshot (локальные сигналы: CI/tests/lint/build)
  - Top candidates (3–7)
  - Critic decision + rationale
  - Gatekeeper decision + PRSpec summary (title, files_touched, test_plan)
  - Why this is likely to merge
  - Next steps to implement/publish (если потребуется)

Вывод в чат:
- Верни **только JSON** по `schemas/execution_result.schema.json`.
- `stage` = `pipeline`, `status` = `success|needs_human|failed`.
- В `artifacts` добавь запись про отчёт: `{ "kind": "report", "path": "{{REPORT_PATH}}" }` (только если файл реально создан).
- В `data` включи: `pipeline_mode`, `stage_summary[]`, `top_improvements[]`, `selected_prspec`, `final_pr_message` (может быть пустым), `report_path`.

