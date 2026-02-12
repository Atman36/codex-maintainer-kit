# quality_gate.py

A minimal “pre-publish” gate for PR-factory runs.

## What it does
1) Lists changed/untracked files.
2) Flags forbidden tool-state paths (agent directories, local env files, etc.).
3) Runs a conservative “secret-ish” regex scan on changed text files.
4) Computes a local-only merge probability heuristic.

## Usage

```bash
python tools/quality_gate.py --repo /path/to/repo --base-ref origin/main
# optional PRSpec integration:
python tools/quality_gate.py --repo /path/to/repo --base-ref origin/main --prspec prspec.json --json
```

Exit codes:
- `0` => OK
- `2` => failed gate (forbidden paths or potential secrets)

## Tuning
- Override forbidden globs:
  `--forbidden ".agentplane/**" ".opencode/**" ...`
- Adjust regexes and patterns inside `quality_gate.py` as needed.
