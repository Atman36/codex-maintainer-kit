## Prepared PR Drafts (2026-03-10)

### PR 1: Resolve hookify rules from the project root

- `repo:` `/Users/Apple/Developer/claude-code`
- `base:` `origin/main` at `f6dbf44`
- `worktree:` `/Users/Apple/Developer/claude-code-pr1`
- `branch:` `codex/hookify-project-root`
- `commit:` `7af972ea789b1ed31cedb3642266352d7237dbc3`
- `status:` implemented locally, verified, not published
- `files:` `plugins/hookify/core/config_loader.py`, `plugins/hookify/tests/test_config_loader.py`
- `verification:`
  - `python3 -m unittest plugins.hookify.tests.test_config_loader`
  - `python3 -m py_compile plugins/hookify/core/config_loader.py plugins/hookify/tests/test_config_loader.py`

**PR title**

Resolve hookify rules from the project root

**PR body**

````md
## What
Resolve hookify rule discovery from the project root instead of assuming the current working directory is the repo root.

Add a unit test that covers loading rules both with `CLAUDE_PROJECT_DIR` set and when the process starts from a nested directory.

## Why
Hookify rule files live in the project's `.claude/` directory, but the loader currently looks for `.claude/hookify.*.local.md` relative to the current working directory.

That causes hooks to silently stop finding configured rules when Claude Code is launched or resumed from a subdirectory.

## How to verify
```bash
python3 -m unittest plugins.hookify.tests.test_config_loader
python3 -m py_compile plugins/hookify/core/config_loader.py plugins/hookify/tests/test_config_loader.py
```

## Notes
No workflow or plugin manifest changes. Scope is limited to rule discovery and regression coverage.
````

**Merge rationale**

Низкий риск: меняется только путь поиска hookify-правил и добавляется узкий регрессионный тест. Поведение из корня проекта сохраняется, а сценарий запуска из вложенной директории перестаёт ломать пользовательские правила.

[Подробный markdown-отчёт](sandbox:/mnt/data/claude-code_audit_pr_report.md)

## Audit Summary

### Repo snapshot

Это не “ядро” Claude Code, а публичный control plane вокруг продукта: GitHub automation, issue triage/dedupe, example plugins, devcontainer, docs. По локальному снимку тут 13 плагинов, 12 workflow-файлов, 5 TypeScript-скриптов в `scripts/` и ровно ноль автоматических тестов в исходном состоянии. Такой репозиторий живёт не за счёт сложной бизнес-логики, а за счёт качества инструкций, guardrails и отсутствия drift. Как ни странно, именно то, что люди обычно недолюбливают поддерживать, потом и ломает агентный контур.

С точки зрения agent-first engineering это место просит не “больше магии”, а больше legibility: короткую карту репозитория вместо монолитной инструкции, механические проверки для метаданных и явные feedback loops. Это очень хорошо совпадает и с OpenAI-шным подходом из harness engineering, где упор делается на repository knowledge as system of record, progressive disclosure и mechanical validation, и с присланным вами анализом по Anthropic-style governance, где ключевые критерии приёма вкладов это AI-readiness и автономная верификация. ([OpenAI][1])  Что сейчас важно по моделям

Для таких workflow-репозиториев разумный базовый выбор сейчас такой: **Sonnet 4.6** как default backbone для issue automation, широких coding-задач, agent workflows и computer use, а **Opus 4.6** как escalation path для самых тяжёлых рефакторингов, многоагентной координации и задач, где цена ошибки выше цены токенов. Anthropic прямо позиционирует `claude-sonnet-4-6` как best speed/intelligence model, а Opus 4.6 как strongest option for deepest reasoning; в официальных материалах отдельно отмечены refactoring и coordinating multiple agents как territory Opus. ([platform.claude.com][2]) Top issues

1. `scripts/auto-close-duplicates.ts` мог трогать PR вместо issue, потому что GitHub Issues API возвращает и issues, и PR, различая их по `pull_request` key. Плюс он закрывал issue через update payload с `labels`, а это заменяет весь набор labels, а не аккуратно добавляет `duplicate`. Это не “теоретический риск”, это прямой способ тихо затереть triage state. ([octokit.github.io][3])`scripts/backfill-duplicate-comments.ts` игнорировал `DAYS_BACK`, жёстко хардкодил `anthropics/claude-code` и ходил по диапазону issue numbers с `state=all`, а workflow при этом обещал “days_back”. Классический drift между intent и implementation.

2. В plugin catalog уже был фактический drift: `plugins/plugin-dev/` без `.claude-plugin/plugin.json`, `plugins/security-guidance/` без README. Никакой механической проверки на это не было.

3. `claude-dedupe-issues.yml` всё ещё сидел на Sonnet 4.5, хотя текущий API model ID для Sonnet 4.6 это `claude-sonnet-4-6`, и Sonnet 4.6 уже лучше подходит для этого контура по instruction following и agent reliability. ([platform.claude.com][2])`.claude/commands/dedupe.md` был в правильную сторону, но недостаточно строгим для high-precision dedupe. Для агентной системы это важнее, чем кажется: одна плохая duplicate-comment инструкция потом тиражирует ложные совпадения быстрее, чем человек успевает раздражиться.

4. Follow-up, не взятый в выбранные PR: `.devcontainer/init-firewall.sh` валидирует GitHub meta ranges как IPv4-only, хотя GitHub meta endpoint возвращает и IPv4, и IPv6. Это хрупкое место для devcontainer bootstrap. ([GitHub Docs][4]) Improvement opportunities

Главная линия улучшений здесь не “рефакторить всё подряд”, а сделать репозиторий более проверяемым машиной:

* script-level unit tests для automation logic
* CI-проверки целостности plugin catalog и doc metadata
* более точные agent instructions для `.claude/commands/*`
* короткий top-level `AGENTS.md` или `CLAUDE.md`, который будет картой репозитория, а не простынёй судьбы

### New feature opportunities

1. **Top-level repo map for agents**
   Маленький `AGENTS.md`/`CLAUDE.md` с картой: где issue automation, где plugin catalog invariants, как проверять изменения, какие workflow считаются source of truth. Это почти textbook-ответ на “give the agent a map, not a 1000-page manual”. ([OpenAI][1])**Generic Claude 4.6 upgrade skill/plugin**
   В репо уже есть узкий `claude-opus-4-5-migration`, но продуктовый мир уже уехал дальше. Небольшой `claude-4-6-upgrade` skill с decision tree “Sonnet vs Opus”, model-string updates и prompt adjustments выглядел бы естественным продолжением.

2. **Environment/harness plugin for agentic repos**
   Небольшой официальный plugin/skill для repo legibility, worktree-based verification, docs freshness, maybe validation hooks. Это хорошо ложится и на current trends из harness engineering, и на более широкий сценарий использования Claude/OpenClaw не только для кодинга, но и для everyday/business automation. ([OpenAI][1])Top PR Candidates

Я собрал 10 кандидатов и выбрал 5 с наибольшей вероятностью принятия.

1. **Preserve existing labels when auto-closing duplicate issues**
   `change_type:` bugfix; `why_it_matters:` не затирает labels и не трогает PR; `targets:` `scripts/auto-close-duplicates.ts`; `est_loc:` ~120; `risk:` low; `verification:` `node --experimental-strip-types --test tests/auto-close-duplicates.test.mjs`; `merge_probability:` high.

2. **Respect `days_back` when backfilling duplicate comments**
   `change_type:` bugfix; `why_it_matters:` чинит расхождение между workflow input и фактическим поведением; `targets:` `scripts/backfill-duplicate-comments.ts`; `est_loc:` ~180; `risk:` low-medium; `verification:` `node --experimental-strip-types --test tests/backfill-duplicate-comments.test.mjs`; `merge_probability:` high.

3. **Validate plugin catalog consistency in CI**
   `change_type:` ci/tests; `why_it_matters:` ловит drift между `plugins/`, `plugins/README.md` и `.claude-plugin/marketplace.json`; `targets:` new validator script + workflow; `est_loc:` ~200; `risk:` low; `verification:` `node --test tests/validate-plugin-catalog.test.mjs` and `node scripts/validate-plugin-catalog.mjs`; `merge_probability:` high.

4. **Upgrade duplicate-detection workflow to Sonnet 4.6**
   `change_type:` dx; `why_it_matters:` приводит automation к current model baseline; `targets:` `.github/workflows/claude-dedupe-issues.yml`; `est_loc:` 1-3; `risk:` low; `verification:` YAML parse + assert model arg; `merge_probability:` high.

5. **Tighten `/dedupe` guidance for higher precision**
   `change_type:` docs/dx; `why_it_matters:` улучшает instruction quality для агентов, снижает false positives; `targets:` `.claude/commands/dedupe.md`; `est_loc:` ~25; `risk:` low; `verification:` manual/grep check of new rules; `merge_probability:` high.

6. **Make devcontainer firewall IPv6-tolerant**
   `change_type:` bugfix; `why_it_matters:` GitHub meta returns IPv4 and IPv6; current bootstrap can fail hard; `targets:` `.devcontainer/init-firewall.sh`; `est_loc:` ~30-60; `risk:` medium; `verification:` shell test + mocked meta payload; `merge_probability:` medium-high. ([GitHub Docs][4]) top-level AGENTS.md / CLAUDE.md repo map**
   `change_type:` docs/feature; `why_it_matters:` improves agent legibility and contributor onboarding; `targets:` new top-level map + verification section; `est_loc:` ~80-150; `risk:` low; `verification:` human review; `merge_probability:` medium-high. ([OpenAI][1]) `claude-4-6-upgrade` migration skill**
   `change_type:` feature; `why_it_matters:` current bundled migration story is stale; `targets:` new plugin/skill + marketplace entry; `est_loc:` ~150-300; `risk:` medium; `verification:` skill docs review + installation path check; `merge_probability:` medium.

7. **Validate plugin install docs against current setup guidance**
   `change_type:` docs/ci; `why_it_matters:` root README already says npm install is deprecated, plugin docs still lag; `targets:` `plugins/README.md` + optional link checker; `est_loc:` ~20-50; `risk:` low; `verification:` manual review; `merge_probability:` medium-high.

8. **Add lint/validation for `.claude/commands` frontmatter and allowed-tools**
   `change_type:` ci; `why_it_matters:` agent instructions become machine-checkable; `targets:` new command validator; `est_loc:` ~120-200; `risk:` medium; `verification:` node tests + CI; `merge_probability:` medium.

---

## Selected PR Queue

### 1) `pr1-auto-close`

* **title:** Preserve existing labels when auto-closing duplicate issues
* **rationale:** самый явный correctness bug, легко проверить, легко откатить
* **files expected to change:** `scripts/auto-close-duplicates.ts`, `tests/auto-close-duplicates.test.mjs`
* **test plan:** `node --experimental-strip-types --test tests/auto-close-duplicates.test.mjs`
* **estimated risk:** low

### 2) `pr2-backfill`

* **title:** Respect `days_back` when backfilling duplicate comments
* **rationale:** workflow уже обещает это поведение; код просто не выполнял обещание
* **files expected to change:** `scripts/backfill-duplicate-comments.ts`, `tests/backfill-duplicate-comments.test.mjs`
* **test plan:** `node --experimental-strip-types --test tests/backfill-duplicate-comments.test.mjs`
* **estimated risk:** low-medium

### 3) `pr3-plugin-catalog`

* **title:** Validate plugin catalog consistency
* **rationale:** mechanical validation сразу снижает drift и делает repo более agent-friendly
* **files expected to change:** validator script, workflow, unit tests, minimal catalog normalization
* **test plan:** `node --test tests/validate-plugin-catalog.test.mjs` and `node scripts/validate-plugin-catalog.mjs`
* **estimated risk:** low

### 4) `pr4-sonnet46`

* **title:** Upgrade dedupe workflow to Sonnet 4.6
* **rationale:** low-risk refresh to current recommended model baseline for this workflow
* **files expected to change:** `.github/workflows/claude-dedupe-issues.yml`
* **test plan:** parse workflow YAML and assert `claude_args == --model claude-sonnet-4-6`
* **estimated risk:** low

### 5) `pr5-dedupe-instructions`

* **title:** Tighten duplicate-detection guidance for agents
* **rationale:** вы сами подсветили главное: в agent repos хорошая инструкция дороже “умного” патча
* **files expected to change:** `.claude/commands/dedupe.md`
* **test plan:** check presence of new precision rules; manual review of prompt clarity
* **estimated risk:** low

---

## Execution Result Per PR

### PR 1

* **branch:** `pr1-auto-close`

* **commit hash:** `bbd7c79c4ada08dd2c0eaa5077bf9087ddf5331a`

* **tests/status:** passed
  `node --experimental-strip-types --test tests/auto-close-duplicates.test.mjs`

* **PR title:** Preserve existing labels when auto-closing duplicate issues

* **PR body:**

```md
## Summary

- skip pull requests when scanning repository issues for duplicate auto-close candidates
- preserve existing issue labels by adding `duplicate` through the labels endpoint instead of replacing the full label set
- skip self-referential duplicate comments
- add unit tests for duplicate extraction, issue filtering, and the close request sequence

## Why

The issues API can return pull requests, and the previous close flow updated `labels` as part of the issue PATCH request. That risks acting on PRs and replacing the full label set on issues that are being closed as duplicates.

## Testing

- `node --experimental-strip-types --test tests/auto-close-duplicates.test.mjs`
```

* **summary:** исправил два correctness-риска в одном локальном участке: PR filtering и label clobber.
* **residual risks:** эвристика duplicate-comment всё ещё завязана на bot comment text; если формат бот-комментария поменяется, логика не заметит это.

### PR 2

* **branch:** `pr2-backfill`

* **commit hash:** `213312e9ab552eb374419cc5dc8a7b360825d35f`

* **tests/status:** passed
  `node --experimental-strip-types --test tests/backfill-duplicate-comments.test.mjs`

* **PR title:** Respect `days_back` when backfilling duplicate comments

* **PR body:**

```md
## Summary

- honor `DAYS_BACK` by filtering candidate issues on creation time
- derive repository owner/name from the environment instead of hardcoding `anthropics/claude-code`
- limit backfill to open repository issues and skip pull requests/locked issues
- stop pagination once the configured search boundary is exhausted
- only sleep between workflow dispatches when the script is not in dry-run mode
- add unit tests for config parsing, candidate filtering, and pagination stopping

## Why

The workflow exposes a `days_back` input, but the script previously ignored it and scanned issue-number ranges across all issue states. This change makes the implementation match the workflow contract and reduces unnecessary dispatches.

## Testing

- `node --experimental-strip-types --test tests/backfill-duplicate-comments.test.mjs`
```

* **summary:** вернул соответствие между workflow contract и script behavior.
* **residual risks:** я интерпретировал `days_back` как “issues created within the last N days”. Это выглядит наиболее естественно, но если maintainer имел в виду другой временной срез, semantics можно уточнить в follow-up.

### PR 3

* **branch:** `pr3-plugin-catalog`

* **commit hash:** `d0393bfaf3e520d781404d8cf32b6664d80d0e79`

* **tests/status:** passed
  `node --test tests/validate-plugin-catalog.test.mjs`
  `node scripts/validate-plugin-catalog.mjs`

* **PR title:** Validate plugin catalog consistency

* **PR body:**

```md
## Summary

- add a lightweight validator for plugin catalog consistency across:
  - plugin directories
  - plugin manifests
  - `plugins/README.md`
  - `.claude-plugin/marketplace.json`
- add unit tests for the validator
- add a GitHub Actions workflow to run the validator on plugin-catalog changes
- normalize the current catalog by adding:
  - a missing manifest for `plugins/plugin-dev`
  - a missing README for `plugins/security-guidance`

## Why

This repository is plugin-heavy, but the original snapshot had no mechanical check preventing catalog drift. The new validator catches missing manifests, missing READMEs, missing marketplace entries, and stale README references before they land.

## Testing

- `node --test tests/validate-plugin-catalog.test.mjs`
- `node scripts/validate-plugin-catalog.mjs`
```

* **summary:** добавил именно тот boring machinery, который потом экономит часы на “почему marketplace сломан”.
* **residual risks:** validator пока проверяет только catalog invariants, не валидирует каждый внутренний command/agent/skill path.

### PR 4

* **branch:** `pr4-sonnet46`

* **commit hash:** `f32eebe7c7ebb9c25cd8594ce58cda7732c9ae49`

* **tests/status:** passed
  workflow YAML parsed; asserted `claude_args == --model claude-sonnet-4-6`

* **PR title:** Upgrade dedupe workflow to Sonnet 4.6

* **PR body:**

```md
## Summary

- update the duplicate-detection workflow to use `claude-sonnet-4-6`

## Why

Sonnet 4.6 is the current best speed/intelligence default for coding and agent workflows. This keeps the dedupe automation aligned with the current model baseline without changing the workflow shape.

## Testing

- parse `.github/workflows/claude-dedupe-issues.yml`
- assert `claude_args` is `--model claude-sonnet-4-6`
```

* **summary:** минимальный safe refresh без побочных изменений.
* **residual risks:** используется alias, не dated pin. Если maintainers предпочитают жестко pinned IDs, это можно поменять отдельно.

### PR 5

* **branch:** `pr5-dedupe-instructions`

* **commit hash:** `b02db794bc5f337b4d70dd8e968469f8379928f9`

* **tests/status:** passed manual/grep verification
  checked the new precision rules are present in `.claude/commands/dedupe.md`

* **PR title:** Tighten duplicate-detection guidance for agents

* **PR body:**

```md
## Summary

- explicitly prioritize precision over recall for duplicate comments
- require stronger issue summaries before search
- clarify that only open issues should be suggested
- forbid self-matches and repeated matches
- bias matching toward overlapping repro steps, exact error text, platform, and user-visible failure mode
- allow fewer than 3 suggestions when only one or two are strong
- instruct the agent to do nothing when confidence is low

## Why

For issue dedupe, the biggest failure mode is not missing a duplicate. It is posting a low-confidence duplicate comment that creates noise and loses trust. This tightens the workflow instructions in favor of precision.

## Testing

- verify the new precision rules are present in `.claude/commands/dedupe.md`
- manual review for clarity and internal consistency
```

* **summary:** это самый “environment engineering” PR из пачки: он улучшает не код, а поведение системы через более грамотную инструкцию.
* **residual risks:** это всё ещё prompt-level control, а не hard guarantee; без downstream eval loop качество dedupe останется partly model-dependent.

---

Если смотреть стратегически, я бы следующей волной делал не ещё 20 косметических PR, а 2 вещи: короткий top-level agent map и узкий harness/plugin для repo legibility. Именно там через полгода будет реальная ценность, а не в очередной торжественной перестановке скобок.

[1]: https://openai.com/index/harness-engineering/ "https://openai.com/index/harness-engineering/"
[2]: https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-6 "https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-6"
[3]: https://octokit.github.io/rest.js/v21/ "https://octokit.github.io/rest.js/v21/"
[4]: https://docs.github.com/rest/reference/meta "https://docs.github.com/rest/reference/meta"
