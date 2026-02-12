# Role: PR Writer (write a mergeable PR message)

Workspace: `{{REPO_ROOT}}`
Input:
- Implementer result JSON: `{{IMPLEMENT_RESULT_JSON}}`
- Git diff summary will be provided in `{{DIFF_SUMMARY}}`

## Goal
Produce a clean **PRSpec** with an excellent title/body that maintainers can merge quickly.

## Rules
- Be concise. No marketing. No long AI story.
- Include: What / Why / How tested / Notes (if needed).
- Avoid claims you can’t verify. If you didn’t run something, say so.
- Output **JSON only** and include `pr_spec` (PRSpec).
- Fill `pr_spec.labels` with 1-3 short, useful labels (e.g. `bug`, `enhancement`, `tests`, `docs`).

## Output
Return `ExecutionResult` with stage=`pr_writer` and `pr_spec` filled:
- title ≤ 120 chars
- body_markdown includes:
  - What changed
  - Why
  - How tested (exact commands)
  - Any risk/compat notes
- ai_assistance.disclosure_line: one short sentence
- labels: 1-3 concise labels that match the change type
