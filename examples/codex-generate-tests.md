# Codex Test Generation

Detect gaps between a diff and the existing test suite.

## 1. Compute the diff

```bash
git diff HEAD~1 --name-only > analysis_report/changed_files.txt
```

## 2. Identify test gaps

```bash
codex exec --sandbox read-only \
  'Given the changed files in analysis_report/changed_files.txt and the test directory tests/, list which changed paths lack direct unit-test coverage. Propose minimal test cases in pytest style.'
```

## 3. Generate tests

If the maintainer approves, run:

```bash
codex exec --sandbox workspace-write \
  'Write the proposed unit tests into the appropriate test files under tests/. Do not change production code.'
```

## 4. Run the new tests

```bash
pytest tests/ -k "<new_test_prefix>"
```

## Quality gate

After test generation, enforce the PRSpec boundary:

```bash
python tools/quality_gate.py \
  --repo . \
  --prspec analysis_report/<run_id>/gatekeeper.json \
  --enforce-files-touched
```

**Rule:** test-only changes are low-risk and often mergeable, but still require human approval before publication.
