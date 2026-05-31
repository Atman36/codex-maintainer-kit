# Safety Policy

Codex Maintainer Kit prepares reviewable changes. It does not bypass maintainer approval.

## Human-gated publishing

The `pr-factory-publisher` stage is optional and runs only after an explicit maintainer request. Analysis, implementation, review, and PR drafting do not imply permission to fork, push, or open a pull request.

## Quality gates

`tools/quality_gate.py` provides local checks:

- `DEFAULT_FORBIDDEN_GLOBS` blocks tool state, environment files, and likely secret-bearing paths.
- `SECRET_REGEXES` scans changed text files for likely credentials and redacts snippets in reports.
- `allowed_files_from_prspec()` and `detect_unplanned_paths()` compare the working tree with approved `files_touched`.
- `cleanup_unplanned_paths()` supports explicit cleanup of files outside the PRSpec.
- `merge_probability()` provides a conservative local heuristic based on diff size, repository signals, test plans, and blockers.

The pipeline modes in `config/pipeline_modes.json` control analysis depth. They do not remove the publication approval boundary.

## Automation guidance

- Prefer read-only analysis first.
- Grant write access only for an approved implementation.
- Keep stage outputs and audit artifacts for review.
- For future CI integration, use the official `openai/codex-action` pattern with least-privilege jobs and separate write permissions.
