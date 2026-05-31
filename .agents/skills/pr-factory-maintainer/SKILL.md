---
name: pr-factory-maintainer
description: Prepare small, safe, reviewable OSS pull-request changes with PR Factory Kit. Use for maintainer triage, PRSpec creation, approved implementation, review, and PR drafting. Never publish without an explicit maintainer request.
---

# PR Factory Maintainer

Use this repo-local workflow for open-source maintenance tasks.

## Workflow

1. Read `program.md` and the relevant target-repository instructions.
2. Select `full`, `quick-win`, or `architecture` mode.
3. Run analysis in order:
   - `full`: Scout -> Analyst -> Critic -> Gatekeeper
   - `quick-win`: Scout -> Gatekeeper
   - `architecture`: Architect -> Critic -> Gatekeeper
4. Stop after Gatekeeper when the maintainer requests analysis only.
5. For an approved PRSpec, run Implementer -> Reviewer -> PR Writer.
6. Run Publisher only when the maintainer explicitly requests fork, push, or pull-request creation.

## Safety rules

- Keep the selected change small and reviewable.
- Treat `schemas/prspec.schema.json` as the approved file scope.
- Return stage results that conform to `schemas/execution_result.schema.json`.
- Use `tools/quality_gate.py` before handoff.
- Preserve audit artifacts; do not claim files exist unless they were written.
- Prefer read-only Codex runs before granting write access.

## Deterministic orchestration

For automated runs, use `tools/run_pipeline.py` with explicit `--stage-command` values. Do not present a shortened command that omits required stage commands. See `tools/README.md`.

## Output

Return a concise maintainer-facing summary:

1. selected mode and candidate;
2. approved PRSpec scope;
3. changed files and checks run, if implementation was requested;
4. blockers or residual risks;
5. publication status.
