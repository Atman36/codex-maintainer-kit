# Prompts

These prompts are designed to be *short* and stack-agnostic.

## Integration pattern
- Fill placeholders (e.g. `{{REPO_ROOT}}`) in your orchestrator.
- Provide any large inputs (candidate JSON, diff summary) via files and inject *paths*,
  not giant inline text.

## Output
All prompts request **JSON only** conforming to `schemas/execution_result.schema.json`.
Role-specific payload goes into `ExecutionResult.data`.

## Recommended entrypoint
- Use `prompts/pipeline.md` for end-to-end ordered workflow:
  `Scout -> Analyst/Architect -> Critic -> Gatekeeper -> Implementer -> PR Writer`.
- This is the default prompt when user asks "проанализируй директорию с помощью агентов" and mentions `deepresearch`.
