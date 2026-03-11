# User Prompt Template: PR Factory framework audit

Проведи глубокий аудит фреймворка `PR Factory Kit` как продукта для AI-агентов и как инженерной среды для полуавтономной / автономной разработки.

## Роль

Выступи в роли:
- Staff+ инженера;
- архитектора agentic systems;
- специалиста по environment / harness engineering для LMM/LLM;
- reviewer-а инфраструктурных репозиториев.

Смотри на репозиторий через призму harness engineering:
- repository knowledge is the system of record;
- agent legibility важнее красивой документации;
- инварианты нужно кодировать в tooling / validators / tests / CI, а не только описывать текстом;
- feedback loops, observability и reproducibility важнее “умных” промптов;
- по мере роста throughput растут требования к merge/review philosophy;
- нужен entropy control и garbage collection для agent-generated systems;
- среда должна помогать агенту безопасно делать правильное действие по умолчанию.

Дополнительно изучи и учти:
- [Harness engineering](https://openai.com/index/harness-engineering/)

## Контекст репозитория

- Репозиторий: `{{REPO_ROOT}}`
- Это не обычное приложение, а набор skills / prompts / schemas / tools для многоэтапного PR pipeline:
  `Scout -> Analyst/Architect -> Critic -> Gatekeeper -> Implementer -> Reviewer -> PR Writer -> Publisher`
- Особенно важны:
  - детерминизм;
  - contract integrity;
  - portability;
  - качество handoff между стадиями;
  - reviewability;
  - безопасность публикации;
  - legibility для AI-агентов;
  - воспроизводимость локального и CI запуска.

## Что обязательно прочитать до выводов

- `AGENTS.md`
- `README.md`
- `skills/README.md`
- `skills/pr-factory-pipeline/SKILL.md`
- все релевантные `skills/pr-factory-*/SKILL.md`
- `CLAUDE.md` как краткий project-facing digest, если он есть
- `prompts/README.md`
- релевантные файлы в `prompts/`
- `tools/README.md`
- `tools/run_pipeline.py`
- `tools/quality_gate.py`
- `tools/validate_skills.py`
- `tools/contract_registry.py`
- `tools/make_agent_audit_archive.py`
- тесты в `tools/tests/`
- схемы в `schemas/`
- `config/pipeline_modes.json`
- workflow-файлы в `.github/workflows/`

Не компенсируй пробелы догадками. Если информации не хватает, дочитай код и документы.

## Важно: что уже, вероятно, исправлено

В репозитории уже было несколько волн доработок runner/contracts/docs/tests. Не повторяй автоматически старые pain points как “open” только потому, что ты ожидаешь увидеть их в таком фреймворке.

Если у тебя есть внешний аудит в `deepresearch/` или другом переданном контексте, используй его как набор гипотез для проверки, а не как источник истины.

Перепроверь фактическое состояние и для каждого такого пункта дай один из статусов:
- `resolved` — действительно исправлено и подтверждается кодом / тестами / docs;
- `partially_resolved` — стало лучше, но есть дыры;
- `regressed` — было исправлено, но снова сломано или контракт расползся;
- `obsolete` — идея потеряла смысл после других изменений;
- `still_open` — проблема по сути жива.

Особенно перепроверь:
- placeholder registry / placeholder drift;
- runtime schema validation;
- relaxed preflight для local-only analysis;
- CI для tools / contract checks;
- parsing `SAVED_JSON_PATH`;
- alias handling между prompts / skills / runner.

## Цель аудита

Нужно:
1. найти баги, регрессии, contract drift, хрупкие места и архитектурные риски;
2. найти low-risk / high-leverage улучшения, которые реально стоит делать отдельными implementation specs;
3. предложить новые функции на ближайшие 3–6 месяцев;
4. собрать конкретный execution plan, пригодный как инструкция для Codex или Claude Code;
5. оценить не только runtime, но и “окружающую инженерию”: prompts, skills, schemas, tools, tests, docs, CI, artifact flow, local assumptions, publish safety, branch safety, review ergonomics;
6. отдельно проверить, не стал ли Critic слишком жёстким и не режет ли он хорошие high-signal / low-risk идеи вместо реального мусора.

## Как проводить аудит

Проверяй не только код, но и всю среду:
- prompts;
- skills;
- schemas;
- tools;
- tests;
- docs;
- CI;
- artifact flow;
- local assumptions;
- placeholder contracts;
- branch / publish safety;
- review ergonomics;
- observability;
- reproducibility.

Сверяй, совпадают ли:
- названия стадий;
- placeholder names;
- metadata inputs;
- schema contracts;
- примеры в docs;
- фактическое поведение `tools/run_pipeline.py`;
- ожидания `skills/*`;
- формулировки в prompt templates;
- тестовое покрытие на эти инварианты.

Ищи:
- ошибки корректности;
- edge cases;
- расхождения между prompt contract и runtime;
- несовместимость между skills и runner;
- silent failure paths;
- плохие сообщения об ошибках;
- неудобные preflight assumptions;
- portable-path проблемы;
- слабые места quality gate;
- пробелы в тестах и CI;
- проблемы review ergonomics;
- лишнюю ручную работу, которую нужно превращать в артефакты, проверки или автоматику;
- слепые зоны в lineage / audit trail / reproducibility.

## Отдельные проверки

### 1. Critic / Gatekeeper behavior

Проверь, что:
- Critic режет мусор, а не хорошие идеи;
- Critic не дублирует работу Gatekeeper;
- Gatekeeper после `approve` в основном занимается минимизацией scope и формированием executable spec;
- между `critic` и `gatekeeper` нет vocabulary drift или конфликта решений;
- reject / revise / approve логично соотносятся с merge probability и реальным risk profile.

Если видишь, что Critic склонен к false negatives, это важный сигнал и отдельная improvement opportunity.

### 2. Artifact discipline

Оцени:
- где сейчас появляются артефакты анализа и pipeline;
- достаточно ли этого для audit trail;
- хватает ли lineage между run, stage outputs, PRSpec и publish;
- какие артефакты создаются вручную, но должны создаваться tooling’ом;
- насколько repo остаётся чистым после repeated agent runs.

### 3. Portability

Ищи:
- абсолютные пути;
- локальные path assumptions;
- команды и примеры, завязанные на конкретную оболочку / OS / `python` vs `python3`;
- места, где локальная среда implicit, а не codified.

### 4. 3–6 month horizon

Отдельно поймай тренды, которые скоро станут важны:
- contract registries и prompt/runner compatibility checks;
- eval harness и synthetic regression tasks;
- artifact lineage / audit trail;
- agent-facing observability;
- recurring cleanup / drift-control workflows;
- policy-as-code для publish / review / branch safety;
- reproducible worktree-local environments;
- cost / latency / reliability metrics для pipeline runs;
- накопление repository-level taste / quality rules;
- garbage collection для agent-generated artifacts.

Предлагай только то, что можно нарезать на реалистичные, локальные, mergeable implementation specs.

## Правила отбора улучшений

- Предпочитай low-risk / high-signal улучшения.
- Предпочитай изменения, которые легко проверить и легко откатить.
- Избегай абстрактных идей без конкретных мест в коде.
- Избегай больших рефакторингов без локальной пользы.
- Не обновляй зависимости без сильного обоснования.
- Если идея хорошая, но рискованная или ещё не созрела, помечай как `follow-up`.
- Если находишь крупную проблему, выделяй минимальный безопасный slice для первого implementation spec.

Для каждого кандидата указывай:
- почему это важно maintainers и пользователям;
- где конкретно менять: файлы, модули, функции;
- примерный scope и LOC;
- риск: `low | medium | high`;
- как проверить: точные команды, тесты, manual steps;
- почему это отдельный spec, а не часть большого рефакторинга;
- вероятность принятия: `high | medium | low`.

## Если у пользователя уже есть внешний аудит

Если уже есть готовый аудит или deep research в формате, отличном от PR Factory:
- для одноразового контекста добавляй его в `deepresearch/`:
  - лучше всего `deepresearch/external-audits/<slug>.md`;
- если это должен быть долгоживущий system-of-record, не храни его только как большой narrative:
  - разрежь на versioned implementation specs в `specs/<audit-slug>/`;
  - добавь индекс вида `specs/<audit-slug>/INDEX.md`;
- если это просто фон для одного запуска, не смешивай его с каноническими contracts, а передавай как external context.

## Ограничения

- Код не меняй.
- PR не публикуй.
- Не создавай ветки и коммиты.
- Не отвечай JSON.
- Ответ пиши в чат, в Markdown.
- Не лей воду.
- Если приходится выбирать между широтой и глубиной, выбирай глубину.

## Формат ответа

Дай результат ровно в 4 блоках.

### Блок 1. Audit Report

Дай короткий, но плотный аудит:
- repo snapshot: стек, структура, skills / prompts / tools / schemas / tests / CI, качество сигналов;
- top issues: баги, contract drift, хрупкие места, архитектурные риски;
- improvement opportunities: системные улучшения;
- new feature opportunities: 3–7 небольших и уместных функций;
- resolved vs still-open: какие ранее известные проблемы и гипотезы уже закрыты, а какие ещё живы, частично закрыты или регресснули.

### Блок 2. Candidate List

Сначала собери расширенный пул кандидатов, затем выбери лучшие.

Для каждого выбранного кандидата укажи:
- `title`
- `change_type` (`bugfix`, `tests`, `refactor`, `docs`, `ci`, `dx`, `feature`, `safety`, `contracts`)
- `why_it_matters`
- `targets`
- `est_loc`
- `risk`
- `verification`
- `merge_probability`
- `why_separate_spec`

### Блок 3. System Upgrade Plan

Собери приоритезированный план доработки без привязки к количеству PR:
- `Now` — ближайшие implementation specs;
- `Next` — следующие implementation specs;
- `Later` — follow-up;
- отдельно выдели:
  - `foundation changes` — что повышает надёжность всего pipeline;
  - `vision changes` — маленькие, но стратегически важные функции для следующей волны agent tooling.

### Блок 4. Ready-to-Implement Specs

Для нескольких лучших кандидатов дай мини-spec:
- `title`
- `problem`
- `smallest_safe_change`
- `files_to_touch`
- `tests_to_add_or_update`
- `exact_verification_commands`
- `rollback_plan`
- `why_safe`
- `expected_reviewer_concerns`
- `commit_message_draft`

## Финальная проверка перед ответом

Перед тем как отвечать, проверь:
- ты реально понял, что делает проект;
- ты не предлагаешь уже закрытые задачи как новые;
- ты не перепутал contracts, alias names и stage vocabulary;
- ты не требуешь там, где нужен analysis-only;
- Critic в твоём разборе не получился “слишком умным rejector”, который душит хорошие low-risk идеи;
- каждое предложение можно превратить в отдельный, проверяемый implementation spec.
- Пойми суть проекта, что он делает и тд.
- Не торопись. Качество анализа важнее скорости
