# User Prompt Template: PR Factory (full)

Проанализируй репозиторий `{{REPO_ROOT}}` (URL: `{{REPO_URL}}`) с помощью агентов PR Factory.

Контекст:
- Используй контекст из `{{CONTEXT_PATH}}` (например: `deepresearch/`).
- Используй контекст выборочно: только факты, влияющие на риск, scope, стиль и требования к PR.

Режим:
- `MODE`: `full`
- `BASE_BRANCH`: `main`
- `MAX_PRS`: `1`

Нужен результат:
1) Наиболее вероятные к merge улучшения (список кандидатов).
2) Итоговый PRSpec (готовый к публикации).
3) Итоговый PR message (title + body_markdown).
4) Post-implementation reviewer verdict (pass/fix_required/human_required).

Ограничения:
- Публиковать PR (форк/пуш/gh pr create) **НЕ нужно**, если я отдельно это не попросил.
- Нельзя “выдумывать” артефакты: если файл не создан, не указывай его в `artifacts`.

Вывод:
- Верни **только JSON** по `schemas/execution_result.schema.json`.
- `stage` = `pipeline`.
- В `pr_spec` положи финальный PRSpec.
- В `data` включи: `pipeline_mode`, `stage_summary[]`, `top_improvements[]`, `selected_prspec`, `final_pr_message`.
