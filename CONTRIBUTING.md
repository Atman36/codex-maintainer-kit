# Contributing

Thanks for considering a contribution to Codex Maintainer Kit.

This project is intentionally conservative: changes should be small, reviewable, and easy for a maintainer to verify.

## Good first contributions

- Improve documentation for existing workflows.
- Add focused tests for `tools/quality_gate.py` or pipeline behavior.
- Tighten an existing prompt, schema, or check without changing its public contract.
- Add a small maintainer workflow only when it has a clear human approval boundary.

## Development setup

```bash
python3 -m pip install -e .
```

Run the relevant checks before opening a pull request:

```bash
python3 -m pytest
python3 tools/quality_gate.py --help
```

If a repository does not use `pytest`, include the exact verification command you ran in the pull request.

## Pull request expectations

- Keep the diff narrow and tied to one problem.
- Explain the maintainer workflow or safety boundary affected by the change.
- Do not include local logs, generated session files, secrets, or private repository data.
- Update docs when behavior changes.
- Include tests or a clear manual verification note for behavior changes.

## Human approval boundary

Codex Maintainer Kit may help prepare analysis, diffs, and pull request text. It must not publish, push, or merge on behalf of a maintainer without explicit human approval.
