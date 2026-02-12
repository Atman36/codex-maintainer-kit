## Skills

Локальные skills для этого репозитория находятся в `skills/`.

### Available skills

- `pr-factory-pipeline`: Оркестратор полного PR Factory flow (по этапам и в правильном порядке). Использовать, когда нужен end-to-end запуск или «собери PR по пайплайну».
- `pr-factory-scout`: Быстрый triage репозитория и поиск 3-7 low-risk кандидатов.
- `pr-factory-analyst`: Глубокий анализ и 5 качественных кандидатов в заданном фокусе.
- `pr-factory-critic`: Критическая пред-оценка идей/PRSpec до реализации (approve/revise/reject).
- `pr-factory-gatekeeper`: Отбор кандидатов и формирование минимального mergeable PRSpec.
- `pr-factory-implementer`: Безопасная реализация PRSpec с проверками.
- `pr-factory-pr-writer`: Формирование финального PR title/body.
- `pr-factory-publisher`: Публикация изменений: форк/пуш/создание PR (только по явному запросу пользователя).
- `pr-factory-architect`: Небольшие архитектурные улучшения (<200 LOC) как альтернативный вход.

### Trigger rules

- Если пользователь просит «полный пайплайн», «по порядку», «автоматизировать PR end-to-end»:
  - сначала использовать `pr-factory-pipeline`.
- Если пользователь пишет в стиле:
  - «проанализируй репозиторий/директорию ... с помощью агентов»
  - «напиши возможные улучшения»
  - «контекст в папке deepresearch»
  - сначала использовать `pr-factory-pipeline` в режиме `full` и передавать `CONTEXT_PATH`.
- Если пользователь явно называет skill, использовать названный skill.
- Если запрос про конкретный этап, запускать соответствующий skill напрямую.

### Group order (default)

1. `pr-factory-scout`
2. `pr-factory-analyst` (или `pr-factory-architect` для архитектурного фокуса)
3. `pr-factory-critic`
4. `pr-factory-gatekeeper`
5. `pr-factory-implementer`
6. `pr-factory-pr-writer`
7. `pr-factory-publisher` (опционально: только если пользователь просит опубликовать PR)

### Scope

- Эти правила применяются в пределах текущего workspace: `/Users/Apple/Developer/pr-factory-kit`.
- Целевой репозиторий для анализа/изменений можно задавать через абсолютный `{{REPO_ROOT}}`, в том числе на соседнюю директорию.
