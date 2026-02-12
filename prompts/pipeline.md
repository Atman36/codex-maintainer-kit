# Role: PR Factory Pipeline (ordered multi-agent flow)

Проанализируй репозиторий/директорию `{{REPO_ROOT}}` с помощью агентов PR Factory и предложи **наиболее вероятные к merge улучшения**.

Контекст компании/проекта:
- Path: `{{CONTEXT_PATH}}` (например: `deepresearch/`)
- Используй контекст выборочно: только факты, влияющие на риск, scope, стиль и требования к PR.

Режим:
- `{{MODE}}` (`full` по умолчанию; варианты: `quick-win`, `architecture`)
- `{{BASE_BRANCH}}` (`main` по умолчанию)
- `{{MAX_PRS}}` (по умолчанию `1`)

Требование по порядку:
1. Scout
2. Analyst (или Architect в `architecture`)
3. Critic
4. Gatekeeper
5. Implementer
6. PR Writer

Правила:
- Минимальный diff, минимум риска, максимум reviewability.
- Предпочитай улучшения, которые реально принять в open-source.
- Не делать широких рефакторингов без явной необходимости.
- Если критические гейты не проходят, остановиться и вернуть `needs_human`.

Вывод:
- Верни **только JSON** по `schemas/execution_result.schema.json`.
- В `data` включи:
  - `pipeline_mode`
  - `stage_summary[]`
  - `top_improvements[]`
  - `selected_prspec`
  - `final_pr_message`
