# Scout Input Examples

Examples of inputs for the Scout skill for testing and development.

## Example 1: Basic Repository Analysis

### Inputs

```json
{
  "REPO_ROOT": "/path/to/nodejs-project",
  "REPO_URL": "https://github.com/example/utils-lib",
  "BASE_BRANCH": "main"
}
```

### Expected Behavior

- Read README.md, CONTRIBUTING.md, LICENSE
- Detect package.json, tsconfig.json, jest.config.js
- Identify test command: `npm test`
- Generate 3-7 candidates (docs, tests, bugfix focus)

---

## Example 2: Python Project

### Inputs

```json
{
  "REPO_ROOT": "/path/to/python-project",
  "REPO_URL": "https://github.com/example/py-utils",
  "BASE_BRANCH": "master"
}
```

### Expected Behavior

- Detect requirements.txt, setup.py, or pyproject.toml
- Identify pytest or unittest
- Generate candidates focused on type hints, docstrings, tests

---

## Example 3: Rust Project

### Inputs

```json
{
  "REPO_ROOT": "/path/to/rust-project",
  "REPO_URL": "https://github.com/example/rust-lib",
  "BASE_BRANCH": "main"
}
```

### Expected Behavior

- Detect Cargo.toml
- Identify cargo test, cargo clippy
- Generate candidates for docs, clippy fixes, tests

---

## Example 4: Minimal Project (No CI)

### Inputs

```json
{
  "REPO_ROOT": "/path/to/small-project",
  "REPO_URL": "https://github.com/example/small-lib",
  "BASE_BRANCH": "main"
}
```

### Expected Behavior

- Lower repo score (no CI detected)
- Focus on docs and simple bugfixes
- May return fewer candidates

---

## Command Line Testing

```bash
# Set inputs as environment variables
export REPO_ROOT=/path/to/repo
export REPO_URL=https://github.com/owner/repo
export BASE_BRANCH=main

# Run Scout
python -m pr_factory_scout
```

Or with explicit JSON input:

```bash
echo '{
  "REPO_ROOT": "/path/to/repo",
  "REPO_URL": "https://github.com/owner/repo",
  "BASE_BRANCH": "main"
}' | python -m pr_factory_scout --stdin
```
