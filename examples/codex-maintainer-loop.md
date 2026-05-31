# Codex Maintainer Loop

Full cycle: issue/idea → PRSpec → implementation → review → PR body.

## 1. Analysis (read-only)

```bash
codex exec --sandbox read-only \
  '$pr-factory-maintainer analyze this repository in quick-win mode. Stop after Gatekeeper and return one PRSpec.'
```

This produces a JSON `ExecutionResult` conforming to `schemas/execution_result.schema.json`. The data field contains the PRSpec candidate.

## 2. Review the PRSpec

Read the produced PRSpec and decide whether to approve implementation.

Example PRSpec (excerpt):

```json
{
  "title": "Add explicit TypeError in parser.py",
  "files_touched": ["src/click/parser.py"],
  "risk": "low",
  "test_plan": ["pytest tests/test_parser.py"]
}
```

## 3. Approved implementation (workspace-write)

```bash
codex exec --sandbox workspace-write \
  '$pr-factory-maintainer implement the approved PRSpec, run the required checks, and stop before publishing.'
```

## 4. Review the diff

```bash
git diff HEAD
python tools/quality_gate.py --repo . --prspec analysis_report/<run_id>/gatekeeper.json --enforce-files-touched --json
```

## 5. Draft PR body

```bash
codex exec --sandbox read-only \
  '$pr-factory-pr-writer draft a PR title and body from the reviewer output in analysis_report/<run_id>/reviewer.json. Do not publish.'
```

## 6. Publish (only on explicit request)

```bash
codex exec --sandbox workspace-write \
  '$pr-factory-publisher fork, push, and open a pull request for the approved branch.'
```

**Never run Publisher without an explicit maintainer request.**
