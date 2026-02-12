# Prompts

These prompts are designed to be *short* and stack-agnostic.

## Integration pattern
- Fill placeholders (e.g. `{{REPO_ROOT}}`) in your orchestrator.
- Provide any large inputs (candidate JSON, diff summary) via files and inject *paths*,
  not giant inline text.
- For automation, prefer deterministic orchestration in code (`tools/run_pipeline.py`) over one giant manager prompt.

## Output
All prompts request **JSON only** conforming to `schemas/execution_result.schema.json`.
Role-specific payload goes into `ExecutionResult.data`.

## Recommended entrypoint
- Use `prompts/pipeline.md` for end-to-end ordered workflow:
  `Scout -> Analyst/Architect -> Critic -> Gatekeeper -> Implementer -> Reviewer -> PR Writer -> Publisher (optional)`.
- This is the default prompt when user asks "проанализируй директорию с помощью агентов" and mentions `deepresearch`.

## Publishing
- Use `prompts/publish.md` only when user explicitly asks to fork/push/open a PR.

## User Templates
- `prompts/user-pipeline-full.md` — готовый текст запроса для full pipeline (до PR Writer, без публикации по умолчанию).
- `prompts/user-analysis-only.md` — “только анализ” (без изменений кода) + отчёт в отдельном файле.
