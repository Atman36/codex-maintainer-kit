# Критерии Оценки (Evaluation Criteria)

Детальное руководство по оценке предложенных изменений.

## 1. Necessity (Необходимость)

### Сильная Необходимость

**Признаки:**
- Reported bug с issue номером
- Crash/exception в production
- Security vulnerability
- Measurement gap (coverage <80%, perf regression)
- Explicit maintainer request
- Documented user pain

**Примеры:**

✅ **Сильная необходимость:**
```
"Функция parseURL крашится при null. Reported в issue #123.
Воспроизводится в error handling paths у пользователей."
```

✅ **Сильная необходимость:**
```
"Coverage для validation.ts = 75%, target = 95% (CONTRIBUTING.md).
Не хватает тестов для edge cases (empty string, null)."
```

### Слабая Необходимость

**Признаки:**
- "Would be nice" без конкретной проблемы
- Субъективное улучшение ("cleaner", "better")
- Premature optimization без metrics
- Feature без запроса

**Примеры:**

❌ **Слабая необходимость:**
```
"Validation module выглядит немного неаккуратно.
Refactor на class-based архитектуру был бы cleaner."
```

❌ **Слабая необходимость:**
```
"Добавим dark mode в docs. Многие любят dark mode."
(Нет issue, нет запроса, нет metrics)
```

### Вопросы для Проверки

- Есть ли issue/bug report?
- Есть ли metrics (coverage, perf, error rate)?
- Maintainer просил это?
- Пользователи жалуются?
- Что сломано/отсутствует?

**Если НЕТ ответа ни на один вопрос → слабая необходимость → reject или issue first.**

## 2. Maintainer Fit (Соответствие Проекту)

### Хорошее Соответствие

**Признаки:**
- Follows CONTRIBUTING.md rules
- Matches existing code style
- Similar PRs merged recently
- Aligns with stated roadmap/goals
- Small, focused improvement

**Как проверить:**

1. **Прочитай CONTRIBUTING.md:**
   - Есть ли rules для PRs?
   - Есть ли coding standards?
   - Есть ли запреты (например, "no style PRs without issue")?

2. **Посмотри на merged PRs:**
   - Какого scope обычно принимают?
   - Какие patterns используют?
   - Есть ли похожие PRs?

3. **Посмотри на rejected PRs:**
   - Почему отклонили?
   - Какие patterns НЕ хотят?

4. **Проверь issues/discussions:**
   - Есть ли request на это?
   - Maintainer обсуждал это?

**Примеры:**

✅ **Хорошее соответствие:**
```
Repo has strong test culture:
- CONTRIBUTING.md says "all PRs must include tests"
- Current coverage: 95%
- Recent merged PRs: #456 (test), #478 (test+bugfix)
→ Test-only PR will fit perfectly
```

❌ **Плохое соответствие:**
```
Proposal: Replace Jest with Vitest
Repo:
- Jest used everywhere
- PR #789 (switch to Vitest) rejected with comment "we're happy with Jest"
→ Will likely be rejected
```

### Red Flags

- Нарушает explicit rule в CONTRIBUTING.md
- Противоречит stated direction
- Similar PR rejected недавно
- Вводит new dependency без discussion
- Меняет architecture без RFC

## 3. Scope Control (Контроль Объёма)

### Minimal Scope Правила

**Golden Rules:**
- <50 LOC changed (insertions + deletions)
- <3 files touched
- One clear value (можно описать в одном предложении)
- No "and also" (нет "и заодно")

### Техники Уменьшения Scope

#### Техника 1: Split into Multiple PRs

**До:**
```
"Improve validation module"
- Add null checks (3 functions)
- Add tests (10 tests)
- Update docs (API.md)
- Refactor for clarity
Files: 6, LOC: 200
```

**После (split на 4 PR):**
```
PR 1: "Add null check in parseURL" (1 file, 5 LOC)
PR 2: "Add test for parseURL edge cases" (1 file, 15 LOC)
PR 3: "Add docstring for parseURL" (1 file, 8 LOC)
PR 4: "Extract EMAIL_REGEX constant" (2 files, 20 LOC)
```

**Выгода:**
- Каждый PR reviewable за 2-3 минуты
- Можно merge по отдельности
- Если PR 3 отклонят, PR 1-2 уже merged

#### Техника 2: Remove Nice-to-Haves

**До:**
```
"Add comprehensive test suite for validation"
- 20 new tests
- Test all edge cases
- Add integration tests
LOC: 300
```

**После:**
```
"Add test for validateEmail with empty string"
- 1 test
- Covers most critical edge case
LOC: 12
```

**Выгода:**
- 25x меньше LOC
- Faster review
- Lower risk

#### Техника 3: One Function at a Time

**До:**
```
"Add tests for all util functions"
Files: 5 test files
Tests: 30
```

**После:**
```
"Add test for validateEmail with empty string"
Files: 1
Tests: 1
```

**Follow-up PRs:**
- PR 2: parseURL tests
- PR 3: formatDate tests
- etc.

### Когда Scope Можно НЕ Уменьшать

**Исключения:**
- Atomic change (refactor + тесты должны идти вместе)
- Cascade change (rename function → update all call sites)
- Security fix (нужно fix + tests + docs immediately)

**Пример atomic change:**
```
"Extract duplicate regex into EMAIL_REGEX constant"
Files: 4 (1 definition + 3 call sites)
LOC: 20
→ OK, нельзя split (все call sites должны update вместе)
```

### Scope Cut Template

```json
{
  "scope_cut": {
    "keep": [
      "Add null check in parseURL (highest priority)"
    ],
    "drop": [
      "Refactor entire validation module (too large, low priority)"
    ],
    "split_into_separate_prs": [
      "PR 1: Add null check (5 LOC, high priority)",
      "PR 2: Add tests (15 LOC, medium priority)",
      "PR 3: Update docs (8 LOC, low priority)"
    ]
  }
}
```

## 4. Risk (Оценка Риска)

### Low Risk

**Характеристики:**
- Test-only changes
- Documentation only
- CI config (если broken CI → не merges anyway)
- Obvious bug fixes WITH tests

**Примеры:**
- Добавить test
- Исправить typo в README
- Add null check (defensive code)

### Medium Risk

**Характеристики:**
- Production code changes WITH good test coverage
- Refactoring WITH comprehensive tests
- Dependency updates (minor/patch versions)

**Примеры:**
- Extract duplicate code into function
- Rename confusing variable (многие call sites)
- Update lodash 4.17.20 → 4.17.21

### High Risk

**Характеристики:**
- Public API changes
- Breaking changes
- Database migrations
- Security/crypto/auth code
- Logic changes in core functions WITHOUT tests
- Dependency updates (major versions)

**Примеры:**
- Change function signature
- Remove deprecated API
- Migrate database schema
- Implement authentication

### Risk Assessment Template

```json
{
  "risk": "low",
  "risk_factors": {
    "breaking_change": false,
    "api_change": false,
    "core_logic_change": false,
    "test_coverage": "high",
    "rollback_easy": true
  },
  "mitigation": [
    "All changes covered by tests",
    "Backward compatible",
    "Easy to revert (single commit)"
  ]
}
```

### Hard Reject по Risk

**Автоматически reject если:**
- High risk БЕЗ maintainer buy-in
- Security/crypto БЕЗ domain expertise
- Breaking change БЕЗ RFC/discussion
- Database migration БЕЗ rollback plan

## 5. Testability (Тестируемость)

### Высокая Тестируемость

**Признаки:**
- Automated tests exist
- Exact verification commands provided
- Clear success criteria
- Pass/fail objective

**Пример:**
```json
{
  "test_plan": [
    "npm test -- parseURL.test.ts",
    "Manual: parseURL(null) should return null, not throw"
  ],
  "acceptance_criteria": [
    "All existing tests pass",
    "parseURL(null) returns null",
    "No other behavior changed"
  ]
}
```

### Низкая Тестируемость

**Признаки:**
- "Test it manually" (как?)
- No success criteria
- Subjective verification ("looks better")
- Requires deep domain knowledge

**Пример плохого test plan:**
```json
{
  "test_plan": ["Run tests and make sure it works"],
  "acceptance_criteria": ["Code is cleaner"]
}
```

### Вопросы для Проверки

- Есть ли automated tests?
- Можно ли verify за <5 минут?
- Success criteria objective?
- Можно ли fail clearly?

**Если НЕТ → требуй конкретный test plan в must_fix_before_implement.**

## 6. Reviewability (Читаемость)

### Легко Review

**Характеристики:**
- Minimal diff (<100 LOC)
- <5 files touched
- Clear intent (one thing)
- No mass formatting
- Logical commits

**Пример:**
```
Files changed: 1
Insertions: 12
Deletions: 0
Intent: Add null check
→ Review time: 2-3 minutes
```

### Трудно Review

**Характеристики:**
- Large diff (>200 LOC)
- 10+ files touched
- Mixed intent (bug fix + refactor + tests)
- Mass formatting mixed with logic
- Hard to verify correctness

**Пример:**
```
Files changed: 15
Insertions: 500
Deletions: 300
Intent: "Improve validation module"
→ Review time: 30+ minutes, high cognitive load
```

### Mass Formatting Detection

**Red flags:**
- LOC changed >> functional changes
- Whitespace changes dominate diff
- Many files touched but similar changes

**Пример:**
```
Changed: 50 files
LOC: 2000
Actual logic changes: 20 LOC
→ 98% formatting noise → hard reject
```

## 7. Opportunity Cost (Альтернативы)

### Вопрос

**"Нельзя ли решить проще?"**

### Альтернативы к Code Change

#### Alternative 1: Documentation

**Вместо:**
```
"Refactor parseURL for clarity" (50 LOC changed)
```

**Сделай:**
```
"Add docstring explaining parseURL behavior" (8 LOC added)
```

**Выгода:**
- Zero risk
- Faster review
- Same outcome (users understand code)

#### Alternative 2: Comment

**Вместо:**
```
"Rename variable `x` to `parsedUrl`" (20 files changed)
```

**Сделай:**
```
Add comment: "// x is the parsed URL object"
```

**Выгода:**
- 1 LOC vs 100 LOC
- Zero risk of breaking

#### Alternative 3: Smaller Refactor

**Вместо:**
```
"Refactor entire validation module" (300 LOC)
```

**Сделай:**
```
"Extract EMAIL_REGEX constant" (20 LOC)
```

**Выгода:**
- 15x smaller
- Same benefit (reduce duplication)
- Lower risk

#### Alternative 4: Do Nothing

**Иногда лучший выбор — ничего не менять.**

**Примеры:**
- "Make code more functional" → субъективно, не нужно
- "Update to latest dependency" → works fine now
- "Reorganize folder structure" → cosmetic, no value

### Cost-Benefit Analysis

```
Value = (User impact + Maintainability gain) - (Review time + Risk + Future maintenance)
```

**Примеры:**

✅ **High value:**
```
Bug fix: parseURL crashes
- User impact: High (crash)
- Review time: 5 min
- Risk: Low (defensive code)
- Value: HIGH
```

❌ **Low value:**
```
Refactor for "cleaner code"
- User impact: Zero
- Review time: 30 min
- Risk: Medium (may introduce bugs)
- Value: NEGATIVE
```

## Примеры Решений

### Пример 1: Approve (Bug Fix)

**Proposal:**
```
"Add null check in parseURL to prevent crash"
Files: 1 (parseURL.ts)
LOC: 5
```

**Evaluation:**
1. ✅ Necessity: Crash reported (#123)
2. ✅ Fit: Obvious fix
3. ✅ Scope: Minimal (1 file, 5 LOC)
4. ✅ Risk: Low (defensive code)
5. ✅ Testability: Clear test plan
6. ✅ Reviewability: 2-minute review
7. ✅ Opportunity cost: No simpler alternative

**Decision:**
```json
{
  "decision": "approve",
  "merge_probability": {
    "estimate": 0.95
  }
}
```

### Пример 2: Revise (Scope Too Large)

**Proposal:**
```
"Improve validation module"
Files: 6
LOC: 200
- Add null checks (3 functions)
- Add tests (10 tests)
- Refactor for clarity
- Update docs
```

**Evaluation:**
1. ✅ Necessity: Null checks needed
2. ✅ Fit: Aligns with project
3. ❌ Scope: Too large (6 files, 200 LOC)
4. ⚠️  Risk: Medium (refactor + logic)
5. ⚠️  Testability: Test plan vague
6. ❌ Reviewability: 30+ min review
7. ✅ Opportunity cost: Can split

**Decision:**
```json
{
  "decision": "revise",
  "must_fix_before_implement": [
    "Split into 3 PRs",
    "Start with null checks only (highest priority)"
  ],
  "scope_cut": {
    "split_into_separate_prs": [
      "PR 1: Add null checks (priority: high)",
      "PR 2: Add tests (priority: medium)",
      "PR 3: Refactor + docs (priority: low)"
    ]
  }
}
```

### Пример 3: Reject (Subjective Refactor)

**Proposal:**
```
"Refactor validation to class-based architecture"
Files: 4
LOC: 300
Reason: "Would be cleaner and more OOP"
```

**Evaluation:**
1. ❌ Necessity: No problem stated
2. ❓ Fit: Unknown (no similar PRs)
3. ❌ Scope: Large (300 LOC)
4. ❌ Risk: High (architectural change)
5. ⚠️  Testability: Unclear if behavior preserved
6. ❌ Reviewability: Hard (architectural review)
7. ❌ Opportunity cost: Better to do nothing

**Decision:**
```json
{
  "decision": "reject",
  "top_reasons": [
    "No clear necessity (subjective improvement)",
    "Large scope without maintainer buy-in",
    "High risk of introducing bugs",
    "No proof of benefit"
  ],
  "merge_probability": {
    "estimate": 0.1,
    "drivers_negative": [
      "Subjective claim",
      "No issue/discussion",
      "Architectural change without RFC"
    ]
  }
}
```

## Summary Checklist

Перед финальным решением:

- [ ] **Necessity**: Есть ли clear problem/value?
- [ ] **Fit**: Aligns with project direction?
- [ ] **Scope**: Minimal? Can split?
- [ ] **Risk**: Acceptable? Mitigated?
- [ ] **Testability**: Clear test plan?
- [ ] **Reviewability**: Easy to review?
- [ ] **Opportunity cost**: No simpler alternative?
- [ ] **Merge probability**: >0.5?

**Если НЕТ хотя бы на 2 вопроса → revise или reject.**
