# PR Factory Kit — Руководство пользователя

## Что это такое

PR Factory Kit — инструмент для сопровождающих open-source проектов. Он помогает находить маленькие безопасные улучшения, формировать PRSpec, запускать агентов Codex и сохранять проверяемый отчёт. Публикация Pull Request выполняется только по явному запросу человека.

**Порядок агентов:**
```
Scout → Analyst/Architect → Critic → Gatekeeper → Implementer → Reviewer → PR Writer → Publisher
```

Каждый агент — отдельный скилл с собственным промптом. Все выходы — строгий JSON по схеме `ExecutionResult`.

---

## Установка

```bash
# 1. Клонировать репозиторий
git clone <url> pr-factory-kit
cd pr-factory-kit

# 2. Установить зависимости (только jsonschema)
pip install -e .
# или
pip install -r requirements.txt
```

Требования: Python 3.9+, jsonschema ≥ 4.0.

---

## Запуск

Если нужен **один короткий entrypoint для агента**, начинай с `program.md`. Он сводит воедино: что читать первым, какой workflow считать основным и какие ограничения нельзя нарушать.

### Вариант 1 — Скилл `pr-factory-pipeline` (рекомендуется)

Просто скажи агенту в Claude:

```
Проанализируй репозиторий /путь/к/repo и предложи наиболее вероятные к merge улучшения.
```

или используй готовый шаблон из `prompts/user-pipeline-full.md` — скопируй его и подставь переменные:

```
REPO_ROOT    = /absolute/path/to/your/repo
REPO_URL     = https://github.com/owner/repo
CONTEXT_PATH = deepresearch/        # папка с дополнительным контекстом (необязательно)
MODE         = full                  # full | quick-win | architecture
BASE_BRANCH  = main
MAX_PRS      = 1
```

**Режимы пайплайна:**

| Режим | Стадии анализа | Когда использовать |
|---|---|---|
| `full` | Scout → Analyst → Critic → Gatekeeper | Стандартный режим |
| `quick-win` | Scout → Gatekeeper | Быстрый поиск малорискованных улучшений |
| `architecture` | Architect → Critic → Gatekeeper | Архитектурные изменения (<200 LOC) |

### Вариант 2 — Только анализ (без реализации)

Используй шаблон `prompts/user-analysis-only.md`. Пайплайн остановится после Gatekeeper, вернёт список кандидатов и PRSpec, но **не будет писать код и создавать ветки**.

```
Проанализируй репозиторий /путь/к/repo. Только анализ, без реализации изменений.
```

### Вариант 3 — Точечные правки без пайплайна

Для баг-фиксов и небольших изменений:

```
Исправь баг в файле src/foo.py — точечные изменения без полного пайплайна.
```

Будет использован скилл `pr-factory-code-editor`.

### Вариант 4 — Детерминированный запуск через CLI

```bash
python tools/run_pipeline.py --help
```

Полный CLI-вызов с обязательными `--stage-command` смотри в `tools/README.md`.
Короткий пример выше заменён намеренно: без `--stage-command` `run_pipeline.py` не запускается, и старый сниппет был некорректным.

---

## Если у тебя уже есть аудит кодовой базы

Если ты уже провёл аудит репозитория (например, отчёт от другого инструмента, собственный анализ, результаты предыдущего запуска) — **не нужно запускать пайплайн с самого начала**.

### Куда положить файл аудита

Положи файл(ы) в папку `deepresearch/`:

```
deepresearch/
├── audit.md          # или .json, .txt — любой формат
├── tech_stack.md     # дополнительный контекст (необязательно)
└── constraints.md    # ограничения проекта (необязательно)
```

### Как передать контекст агенту

В запросе укажи `CONTEXT_PATH`:

```
Проанализируй репозиторий /путь/к/repo. Контекст проекта — в папке deepresearch/.
```

или в шаблоне `prompts/user-pipeline-full.md`:

```
CONTEXT_PATH = deepresearch/
```

Агент прочитает папку `deepresearch/` и использует контекст **выборочно** — только факты, влияющие на риск, scope и стиль PR.

### Если хочешь пропустить Scout/Analyst

Если аудит уже сделан и ты хочешь сразу перейти к выбору кандидата и реализации:

```
У меня готов список кандидатов для PR. Запусти pr-factory-gatekeeper с этим списком: [...]
```

Или запусти конкретный скилл напрямую:

```
Запусти pr-factory-implementer для PRSpec в файле analysis_report/prspec.json
```

---

## Структура стадий

| Скилл | Что делает | Входные данные | Выход |
|---|---|---|---|
| `pr-factory-scout` | Быстрый triage, 3–7 low-risk кандидатов | REPO_ROOT | scout.json |
| `pr-factory-analyst` | Глубокий анализ, 5 кандидатов | scout.json | analyst.json |
| `pr-factory-architect` | Архитектурные улучшения <200 LOC | REPO_ROOT | architect.json |
| `pr-factory-critic` | approve / revise / reject по каждому кандидату | analyst.json | critic.json |
| `pr-factory-gatekeeper` | Выбор финального кандидата + PRSpec | critic.json | gatekeeper.json (PRSpec) |
| `pr-factory-implementer` | Реализация PRSpec, коммит | PRSpec | implement.json |
| `pr-factory-reviewer` | Ревью diff, поиск шума и debug leftovers | implement.json + git diff | reviewer.json |
| `pr-factory-pr-writer` | Формирование title + body PR | reviewer.json | pr_writer.json |
| `pr-factory-publisher` | Форк / push / gh pr create | pr_writer.json | publish.json |

**Publisher запускается только по явному запросу** — он создаёт реальные PR на GitHub.

---

## Артефакты

Все выходы сохраняются в `analysis_report/`:

```
analysis_report/
└── <run_id>/
    ├── scout.json
    ├── analyst.json
    ├── critic.json
    ├── gatekeeper.json
    ├── implement.json
    ├── reviewer.json
    ├── pr_writer.json
    └── summary.json
```

Каждый файл — `ExecutionResult` JSON по схеме `schemas/execution_result.schema.json`.

---

## Качественные гейты

Перед публикацией автоматически проверяются:

- **Forbidden files** — нет секретов (PEM, GitHub PAT, AWS keys, OpenAI keys и т.д.)
- **files_touched** — изменены только объявленные в PRSpec файлы
- **Merge probability** — оценка вероятности принятия PR
- **Autoclean** — опция `--autoclean-unplanned` удаляет незапланированные файлы

Запустить гейт вручную:

```bash
python tools/quality_gate.py --prspec analysis_report/<run_id>/gatekeeper.json
python tools/quality_gate.py --autoclean-unplanned --prspec <path>
```

---

## Валидация и тесты

```bash
# Тесты инструментов
pytest tools/tests/

# Валидация контрактов скиллов
python tools/validate_skills.py

# Проверка типов (если редактировал Python-файлы)
# Не нужен отдельный шаг — jsonschema валидация встроена в run_pipeline.py
```

---

## Плейсхолдеры

Все промпты используют плейсхолдеры вида `{{NAME}}`. Ключевые:

| Плейсхолдер | Значение |
|---|---|
| `{{REPO_ROOT}}` | Абсолютный путь к целевому репозиторию |
| `{{REPO_URL}}` | URL репозитория на GitHub |
| `{{BASE_BRANCH}}` | Базовая ветка (обычно `main`) |
| `{{HEAD_BRANCH}}` | Ветка с изменениями |
| `{{CONTEXT_PATH}}` | Путь к папке с дополнительным контекстом |
| `{{MODE}}` | Режим пайплайна: `full`, `quick-win`, `architecture` |
| `{{ARTIFACT_DIR}}` | Папка для выходных артефактов (default: `analysis_report/`) |
| `{{REPORT_PATH}}` | Путь для Markdown-отчёта |

Нераскрытые плейсхолдеры вызывают fail-fast при запуске пайплайна.

---

## Типичные сценарии

### «Хочу найти улучшения в чужом репозитории»

```
Проанализируй репозиторий /Users/me/projects/some-lib.
Режим: full. Без публикации.
```

### «Хочу полный цикл до готового PR»

```
Запусти полный пайплайн для репозитория /Users/me/projects/some-lib.
BASE_BRANCH=main, MODE=full.
```

### «У меня есть аудит, хочу сразу получить PRSpec»

```
Контекст аудита — в deepresearch/audit.md.
Репозиторий: /Users/me/projects/some-lib.
Запусти pr-factory-gatekeeper на основе контекста из deepresearch/.
```

### «Хочу только быстро исправить баги»

```
Исправь ошибку в src/utils.py — без полного пайплайна.
```

### «Хочу опубликовать готовый PR»

```
Опубликуй PR по PRSpec из analysis_report/<run_id>/gatekeeper.json.
Форк и gh pr create.
```

---

## Структура репозитория

```
pr-factory-kit/
├── program.md            # Самый короткий entrypoint для агента
├── prompts/               # Промпты для каждого агента + user-шаблоны
│   ├── user-pipeline-full.md    # Шаблон: полный запуск
│   ├── user-analysis-only.md   # Шаблон: только анализ
│   └── user-framework-audit.md # Шаблон: аудит самого фреймворка
├── schemas/               # JSON-схемы (ExecutionResult, PRSpec)
├── skills/                # Локальные скиллы для Claude
├── tools/                 # CLI-инструменты
│   ├── run_pipeline.py    # Оркестратор
│   ├── quality_gate.py    # Качественный гейт
│   └── contract_registry.py # Реестр плейсхолдеров
├── config/
│   └── pipeline_modes.json # Порядок стадий по режимам
├── deepresearch/          # Сюда кладём внешний контекст / аудиты
├── analysis_report/       # Выходные артефакты пайплайна
├── AGENTS.md              # Список скиллов и правила триггеров
└── GUIDE.md               # Этот файл
```
