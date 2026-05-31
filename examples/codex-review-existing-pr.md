# Codex Review of an Existing PR

Use this workflow when you want Codex to summarize an open pull request, map risks, and suggest test gaps.

## Fetch PR comments

```bash
python tools/fetch_pr_comments.py \
  --repo owner/repo \
  --pr 123 \
  --output analysis_report/pr_123_comments.json
```

## Summarize with Codex

```bash
codex exec --sandbox read-only \
  'Summarize the PR discussion in analysis_report/pr_123_comments.json. Identify unresolved review threads, risk areas, and whether tests cover the changed paths.'
```

## Map touched files to tests

```bash
git diff --name-only origin/main...pr-branch
```

Then ask Codex:

```text
These files were changed in PR #123: src/foo.py, src/bar.py.
Compare with tests/ and list any uncovered paths or missing unit tests.
```

## Output rule

All Codex stage outputs should conform to `schemas/execution_result.schema.json` so they can be fed back into the pipeline as context for the next run.
