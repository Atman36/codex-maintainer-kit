# Schemas

- `prspec.schema.json` — intended PR metadata/body/test plan/etc.
- `execution_result.schema.json` — uniform envelope returned by every CLI agent run.

`ExecutionResult.data` is intentionally flexible so you can evolve role outputs
without breaking the top-level contract.

`ExecutionResult.stage` includes pipeline-oriented values like `pipeline`, `reviewer`, `publish`, etc.

Examples are in `schemas/examples/`.
