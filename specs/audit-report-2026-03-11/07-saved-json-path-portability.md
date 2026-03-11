# Spec 07: Support quoted and space-containing `SAVED_JSON_PATH` values

Источник:
- [Audit Report.md](/Users/Apple/Developer/pr-factory-kit/Audit%20Report.md)
- Section: `Top issues -> 3`
- Section: `Best 7 -> 7`

## Why This Spec Exists

The audit reports a reproduced portability bug: `parse_stage_output()` cannot correctly parse `SAVED_JSON_PATH` when the path contains spaces or is quoted. This breaks agent handoff on perfectly valid filesystem paths and reduces portability of the whole kit.

## Goal

Fix `SAVED_JSON_PATH` parsing so stage output works with quoted paths and paths containing spaces.

## Scope

Touch only:
- `tools/pr_factory_lib/json_utils.py`
- `tools/tests/test_json_utils.py` (new or updated)

Keep the fix tightly scoped to parsing behavior.

## Problem Statement

Today the parser supports the `SAVED_JSON_PATH=...` pattern in principle, but mishandles paths such as:

```text
SAVED_JSON_PATH="/tmp/with spaces/result.json"
SAVED_JSON_PATH=/tmp/with spaces/result.json
```

This causes otherwise valid outputs to fail in environments where artifact paths are not simple single-token strings.

## Smallest Safe Change

- Update the parser in `json_utils.py` to accept quoted and space-containing path values.
- Keep existing behavior for plain paths and direct JSON output.
- Add regression tests for the path formats that currently fail.

## Acceptance Criteria

- Quoted `SAVED_JSON_PATH` values are parsed correctly.
- Space-containing `SAVED_JSON_PATH` values are parsed correctly.
- Existing no-space path handling still works.
- Direct JSON parsing behavior remains unchanged.

## Tests To Add Or Update

- parse stage output with quoted `SAVED_JSON_PATH`
- parse stage output with space-containing `SAVED_JSON_PATH`
- parse stage output with legacy plain path

## Verification

Run exactly:

```bash
python3 -m unittest tools/tests/test_json_utils.py
```

Manual check:

```bash
python3 - <<'PY'
from tools.pr_factory_lib.json_utils import parse_stage_output
print(parse_stage_output('SAVED_JSON_PATH=\"/tmp/with spaces/out.json\"'))
PY
```

Adjust the import path if the module layout requires running from repo root.

## Reviewer Concerns To Preempt

- Backward compatibility for existing plain-path parsing
- Shell-escaping edge cases
- Whether unquoted paths with spaces should be supported or only quoted ones

## Out Of Scope

- Placeholder validation
- Artifact directory redesign
- Runner preflight changes

## Suggested Commit Message

```text
fix(json-utils): support quoted SAVED_JSON_PATH values with spaces
```
