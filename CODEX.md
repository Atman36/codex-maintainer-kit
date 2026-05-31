# Using PR Factory Kit with Codex

PR Factory Kit is a maintainer automation toolkit for preparing small, reviewable pull requests with explicit quality gates.

## Repo-local skill

Start Codex in the repository and ask it to use:

```text
$pr-factory-maintainer analyze this repository in quick-win mode and prepare one reviewable improvement. Do not publish a pull request.
```

The repo-local entrypoint is `.agents/skills/pr-factory-maintainer/SKILL.md`. The detailed stage skills remain under `skills/`.

## Non-interactive Codex

Codex CLI supports scripted runs through `codex exec`:

```bash
codex exec --sandbox read-only \
  '$pr-factory-maintainer analyze this repository in quick-win mode. Stop after Gatekeeper and return one PRSpec.'
```

Allow edits only for an approved implementation:

```bash
codex exec --sandbox workspace-write \
  '$pr-factory-maintainer implement the approved PRSpec, run the required checks, and stop before publishing.'
```

For deterministic stage orchestration, use `tools/run_pipeline.py` with explicit `--stage-command` values. See `tools/README.md` for the complete command shape.

## Human approval boundary

Publisher is optional. Do not fork, push, or open a pull request unless the maintainer explicitly requests publication.

## Contracts

- `schemas/prspec.schema.json` defines the approved change scope.
- `schemas/execution_result.schema.json` defines stage output.
- `SAFETY.md` documents the enforced quality gates.
