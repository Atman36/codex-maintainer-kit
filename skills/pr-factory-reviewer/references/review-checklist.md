# Reviewer Checklist (Post-Implementation)

## Scope Discipline

- `changed_files` must be subset of the PRSpec `files_touched` list (unless explicitly justified).
- Diff size should be close to PRSpec estimate (roughly within ±20-30%).
- No hidden broad refactors.

## Hygiene

- No tool state directories (`.claude/`, `.agentplane/`, `.codex/`, etc.).
- No debug leftovers (`console.log`, `print(...)`, temporary comments).
- No accidental generated artifacts.

## Verification Integrity

- Implementer ran the commands promised in `test_plan`.
- Failures were either fixed or clearly reported.
- Result should be reproducible from `commands_run`.

## Decision Mapping

- `status=success` + `data.decision=pass`: all checks green.
- `status=retryable` + required fixes: Implementer should patch and rerun.
- `status=needs_human`: change requires maintainer decision, not mechanical fix.
